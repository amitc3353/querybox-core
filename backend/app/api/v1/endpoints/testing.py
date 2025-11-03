"""
Testing utilities endpoint - For development and testing only
Provides endpoints to clean up test data and reset state
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Path as PathParam
from sqlalchemy.orm import Session
from pathlib import Path
import logging
from uuid import UUID
from typing import Optional

from app.db.database import get_db
from app.models.document import Document
from app.core.storage_config import storage_settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.delete("/documents/{document_id}/hard-delete")
async def hard_delete_document(
    document_id: str = PathParam(..., description="Document UUID to hard delete"),
    delete_file: bool = Query(default=True, description="Also delete physical file"),
    db: Session = Depends(get_db)
):
    """
    **FOR TESTING ONLY**: Hard delete a document from database and optionally physical file

    This completely removes the document from the database (not just soft delete)
    and optionally deletes the physical file from storage.

    Use this for cleaning up test data between test runs.
    """
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    # Find document (including soft-deleted)
    document = db.query(Document).filter(Document.id == doc_uuid).first()

    if not document:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    storage_path = document.storage_path
    file_deleted = False

    # Delete physical file if requested
    if delete_file and storage_path:
        try:
            file_path = Path(storage_settings.LOCAL_STORAGE_ROOT) / storage_path
            if file_path.exists():
                file_path.unlink()
                file_deleted = True
                logger.info(f"Deleted physical file: {file_path}")
            else:
                logger.warning(f"Physical file not found: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete physical file: {e}")

    # Hard delete from database
    db.delete(document)
    db.commit()

    logger.info(f"Hard deleted document {document_id} from database")

    return {
        "success": True,
        "document_id": str(document_id),
        "database_deleted": True,
        "file_deleted": file_deleted,
        "message": "Document hard deleted successfully"
    }


@router.delete("/documents/cleanup")
async def cleanup_test_documents(
    delete_files: bool = Query(default=True, description="Also delete physical files"),
    status_filter: Optional[str] = Query(default=None, description="Only delete documents with this status"),
    db: Session = Depends(get_db)
):
    """
    **FOR TESTING ONLY**: Cleanup multiple test documents

    Deletes all documents matching the criteria. Use with caution!
    """
    query = db.query(Document)

    if status_filter:
        query = query.filter(Document.status == status_filter)

    documents = query.all()

    deleted_count = 0
    files_deleted = 0

    for doc in documents:
        # Delete physical file if requested
        if delete_files and doc.storage_path:
            try:
                file_path = Path(storage_settings.LOCAL_STORAGE_ROOT) / doc.storage_path
                if file_path.exists():
                    file_path.unlink()
                    files_deleted += 1
            except Exception as e:
                logger.error(f"Failed to delete file for {doc.id}: {e}")

        # Delete from database
        db.delete(doc)
        deleted_count += 1

    db.commit()

    logger.info(f"Cleaned up {deleted_count} documents, deleted {files_deleted} files")

    return {
        "success": True,
        "documents_deleted": deleted_count,
        "files_deleted": files_deleted,
        "message": f"Cleaned up {deleted_count} documents"
    }


@router.post("/documents/{document_id}/reset-status")
async def reset_document_status(
    document_id: str = PathParam(..., description="Document UUID to reset"),
    db: Session = Depends(get_db)
):
    """
    **FOR TESTING ONLY**: Reset a document's processing status

    Sets status back to 'pending' and clears all processing timestamps.
    Useful for re-testing the pipeline with an existing document.
    """
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    document = db.query(Document).filter(Document.id == doc_uuid).first()

    if not document:
        raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    # Reset status
    from app.models.document import DocumentStatusEnum
    document.status = DocumentStatusEnum.PENDING
    document.last_extraction_at = None
    document.last_embedding_at = None
    document.last_indexed_at = None
    document.is_dirty = True

    db.commit()

    logger.info(f"Reset status for document {document_id}")

    return {
        "success": True,
        "document_id": str(document_id),
        "new_status": "pending",
        "message": "Document status reset successfully"
    }
