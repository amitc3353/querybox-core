"""
Upload endpoint - Week 1, Day 2 + Day 3, Step 5
Enhanced file upload with StorageManager integration
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import magic
from datetime import datetime, timezone
from pathlib import Path
import logging
from typing import Optional
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.storage_config import storage_settings
from app.db.database import get_db
from app.models.document import Document, DocumentStatusEnum, StorageProviderEnum
from app.models.processing_status import ProcessingStatus, ProcessingStageEnum, StageStatusEnum
from app.services.storage import StorageManager
from app.services.storage.exceptions import StorageException, StorageQuotaExceeded
from app.schemas.storage import StorageResult
from app.tasks.extraction_tasks import extract_document_text

logger = logging.getLogger(__name__)

router = APIRouter()

def get_storage_manager(db: Session = Depends(get_db)) -> StorageManager:
    """Dependency to provide StorageManager instance"""
    return StorageManager(db)


def _get_processing_summary(db: Session, document_id: UUID) -> dict:
    """
    Get processing status summary for a document

    Returns status for all stages and determines:
    - ready_for_search: All stages completed successfully
    - can_retry: Any stage failed (user can re-upload with force_new=true)
    - next_action: Guidance on what to do next
    """
    # Get all processing status records
    statuses = db.query(ProcessingStatus).filter(
        ProcessingStatus.document_id == document_id
    ).all()

    # Build status map
    status_map = {
        'extraction': 'not_started',
        'chunking': 'not_started',
        'embedding': 'not_started'
    }

    for status in statuses:
        status_map[status.stage.value] = status.status.value

    # Determine ready_for_search
    ready_for_search = all(
        status_map[stage] == 'completed'
        for stage in ['extraction', 'chunking', 'embedding']
    )

    # Determine can_retry
    has_failures = any(
        status_map[stage] == 'failed'
        for stage in ['extraction', 'chunking', 'embedding']
    )

    # Determine next action
    next_action = None
    if ready_for_search:
        next_action = "ready_for_search"
    elif has_failures:
        # Find first failed stage
        for stage in ['extraction', 'chunking', 'embedding']:
            if status_map[stage] == 'failed':
                next_action = f"retry_{stage}"
                break
    elif status_map['extraction'] == 'completed' and status_map['chunking'] == 'completed':
        next_action = "wait_for_embedding"
    elif status_map['extraction'] == 'completed':
        next_action = "wait_for_chunking"
    else:
        next_action = "wait_for_extraction"

    return {
        'extraction_status': status_map['extraction'],
        'chunking_status': status_map['chunking'],
        'embedding_status': status_map['embedding'],
        'ready_for_search': ready_for_search,
        'can_retry': has_failures,
        'next_action': next_action
    }


@router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: Optional[str] = None,  # For future multi-tenant support
    force_new: bool = Query(
        default=False,
        description="Bypass content-based deduplication (useful for testing). Creates a new document even if identical content exists."
    ),
    db: Session = Depends(get_db),
    storage: StorageManager = Depends(get_storage_manager)
):
    """
    Upload a single document with enhanced storage management
    Day 3, Step 5: StorageManager integration with atomic operations

    Features:
    - Advanced file validation (size, extension, MIME type)
    - Content-based deduplication (unless force_new=true)
    - Organized storage with conflict resolution
    - Atomic operations with rollback on failure
    - Comprehensive error handling and logging
    - Database integration with audit trail

    Query Parameters:
    - force_new: Set to true to bypass deduplication for testing
    """
    document_id = uuid4()
    temp_storage_result = None

    try:
        # Log upload request details
        logger.info(
            f"Upload request received: filename={file.filename}, "
            f"content_type={file.content_type}, size={file.size}, force_new={force_new}"
        )

        # Convert workspace_id to UUID (use default for MVP)
        if workspace_id:
            workspace_uuid = UUID(workspace_id)
        else:
            # Default workspace for MVP (single-tenant)
            workspace_uuid = UUID("00000000-0000-0000-0000-000000000000")
        
        # Step 1: Basic validation
        # Note: file.size might be None for some uploads, we'll check actual size later
        if file.size and file.size > settings.MAX_FILE_SIZE:
            logger.warning(f"File size exceeds limit: {file.size} > {settings.MAX_FILE_SIZE}")
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE / (1024 * 1024):.1f}MB"
            )

        # Step 2: Extension validation
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.ALLOWED_EXTENSIONS:
            logger.warning(f"File type not allowed: {file_extension}, filename: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_extension}' not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        # Step 3: MIME type validation
        file_content = await file.read()
        mime = magic.Magic(mime=True)
        
        # Create temporary file for MIME detection
        temp_path = f"/tmp/upload_validation_{document_id}"
        with open(temp_path, "wb") as temp_file:
            temp_file.write(file_content)
        
        try:
            detected_mime = mime.from_file(temp_path)
        finally:
            # Clean up temp validation file
            Path(temp_path).unlink(missing_ok=True)
        
        # Verify MIME type is in allowed list
        if detected_mime not in storage_settings.ALLOWED_MIME_TYPES:
            logger.warning(
                f"MIME type not allowed: {detected_mime} for file {file.filename}. "
                f"Allowed types: {storage_settings.ALLOWED_MIME_TYPES}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"MIME type '{detected_mime}' not allowed. Allowed types: {', '.join(storage_settings.ALLOWED_MIME_TYPES)}"
            )
        
        # Reset file for StorageManager
        await file.seek(0)
        
        # Step 4: Store document using StorageManager
        # This handles: conflict resolution, organized paths, checksums, duplicates
        temp_storage_result = await storage.store_document(
            file=file,
            workspace_id=workspace_uuid,
            document_id=document_id
        )
        
        # Step 5: Create database record with deduplication
        # Note: Transaction is already started by FastAPI's Depends(get_db)
        try:
            # Check for duplicate by content checksum (content-based deduplication)
            # Skip if force_new=true (for testing purposes)
            existing_doc = None
            if not force_new:
                existing_doc = db.query(Document).filter(
                    Document.checksum == temp_storage_result.checksum,
                    Document.is_deleted == False
                ).first()

            if existing_doc:
                # Verify the existing document's file actually exists
                existing_file_path = Path(storage_settings.LOCAL_STORAGE_ROOT) / existing_doc.storage_path

                if not existing_file_path.exists():
                    # Stale record: DB entry exists but file is missing
                    # Clean up and proceed with new upload
                    logger.warning(
                        f"Stale record detected: Document {existing_doc.id} exists in DB but file missing at {existing_doc.storage_path}. "
                        f"Deleting stale record and using new upload."
                    )
                    db.delete(existing_doc)
                    db.commit()
                    # Fall through to create new document
                else:
                    # True duplicate: Same content exists with valid file
                    # Clean up newly uploaded file and return existing document
                    try:
                        await storage.provider.delete_file(temp_storage_result.path)
                        logger.info(f"Content-based duplicate detected. Cleaned up new upload: {temp_storage_result.path}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup duplicate file: {cleanup_error}")

                    # Get processing status for duplicate document
                    processing_summary = _get_processing_summary(db, existing_doc.id)

                    logger.info(
                        f"Duplicate document detected by content hash: {existing_doc.id}",
                        extra={
                            "document_id": str(existing_doc.id),
                            "original_filename": file.filename,
                            "existing_filename": existing_doc.original_name,
                            "checksum": temp_storage_result.checksum,
                            "processing_status": processing_summary
                        }
                    )

                    return JSONResponse(
                        status_code=200,
                        content={
                            "success": True,
                            "message": "File already exists (duplicate detected by content hash)",
                            "duplicate": True,
                            "document": {
                                "id": str(existing_doc.id),
                                "filename": existing_doc.original_name,
                                "storage_filename": existing_doc.document_name,
                                "size": existing_doc.file_size,
                                "mime_type": existing_doc.mime_type,
                                "checksum": existing_doc.checksum,
                                "status": existing_doc.status.value,
                                "created_at": existing_doc.created_at.isoformat()
                            },
                            "processing_status": processing_summary
                        }
                    )

            # No duplicate found - create new document
            doc = Document(
                id=temp_storage_result.document_id,
                document_name=Path(temp_storage_result.path).name,
                original_name=file.filename,
                mime_type=temp_storage_result.mime_type,
                file_extension=file_extension,
                file_size=temp_storage_result.size,
                checksum=temp_storage_result.checksum,
                storage_provider=StorageProviderEnum.LOCAL,
                storage_path=temp_storage_result.path,
                status=DocumentStatusEnum.COMPLETED,
                document_metadata={
                    "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                    "uploaded_via": "api",
                    "workspace_id": str(workspace_uuid),
                    "conflict_strategy": storage_settings.CONFLICT_STRATEGY.value,
                    "operation_time_ms": temp_storage_result.operation_time_ms
                }
            )

            db.add(doc)
            db.commit()

            logger.info(
                f"Document uploaded successfully: {doc.id}",
                extra={
                    "document_id": str(doc.id),
                    "original_filename": file.filename,
                    "size": temp_storage_result.size,
                    "storage_path": temp_storage_result.path,
                    "operation_time_ms": temp_storage_result.operation_time_ms
                }
            )

            # Trigger text extraction for supported formats
            # PDF, DOCX, and text-based formats (markdown, text, HTML)
            extractable_mimes = [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/markdown",
                "text/plain",
                "text/html",
                "application/octet-stream"  # Fallback for markdown files
            ]

            if detected_mime in extractable_mimes:
                try:
                    # Queue async text extraction task
                    task = extract_document_text.delay(str(doc.id))
                    logger.info(f"Queued text extraction task {task.id} for document {doc.id}")
                except Exception as task_error:
                    # Don't fail upload if task queueing fails
                    logger.error(f"Failed to queue extraction task: {task_error}")

            # Return enhanced response with storage details
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "File uploaded successfully",
                    "document": {
                        "id": str(doc.id),
                        "filename": doc.original_name,
                        "storage_filename": doc.document_name,
                        "size": temp_storage_result.size,
                        "mime_type": temp_storage_result.mime_type,
                        "checksum": temp_storage_result.checksum,
                        "status": doc.status.value,
                        "created_at": doc.created_at.isoformat()
                    },
                    "storage": {
                        "provider": temp_storage_result.provider.value,
                        "path": temp_storage_result.path,
                        "operation_time_ms": temp_storage_result.operation_time_ms
                    }
                }
            )
            
        except SQLAlchemyError as db_error:
            # Rollback database transaction
            db.rollback()
            
            # Clean up storage on database failure
            if temp_storage_result:
                try:
                    await storage.provider.delete_file(temp_storage_result.path)
                    logger.info(f"Cleaned up storage file after DB error: {temp_storage_result.path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup storage after DB error: {cleanup_error}")
            
            logger.error(f"Database error during upload: {db_error}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save document information"
            )
            
    except StorageQuotaExceeded as quota_error:
        logger.warning(f"Storage quota exceeded: {quota_error}")
        raise HTTPException(
            status_code=413,
            detail=f"Storage quota exceeded. Used: {quota_error.used_bytes / (1024*1024):.1f}MB, Limit: {quota_error.quota_bytes / (1024*1024):.1f}MB"
        )
        
    except StorageException as storage_error:
        logger.error(f"Storage error: {storage_error}")
        raise HTTPException(
            status_code=500,
            detail=f"Storage operation failed: {storage_error.message}"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
        
    except Exception as e:
        logger.error(f"Unexpected upload error: {str(e)}", exc_info=True)
        
        # Emergency cleanup
        if temp_storage_result:
            try:
                await storage.provider.delete_file(temp_storage_result.path)
            except:
                pass  # Don't fail the error response due to cleanup issues
        
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during upload"
        )


@router.get("/allowed-types")
async def get_allowed_file_types():
    """
    Get list of allowed file types
    Helper endpoint for frontend validation
    """
    return {
        "allowed_extensions": settings.ALLOWED_EXTENSIONS,
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024)
    }