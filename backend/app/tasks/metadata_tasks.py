"""
Metadata Extraction Tasks
Step 6: Celery tasks for async metadata processing

Provides asynchronous document metadata extraction using Docling service
with comprehensive error handling and progress tracking.
"""

import logging
import asyncio
from typing import Dict, Any
from uuid import UUID
from celery import current_task

from app.celery_app import celery_app
from app.db.database import get_db
from app.models.document import Document, ProcessingStageEnum, StageStatusEnum
from app.services.metadata.docling_service import get_docling_metadata_service
from app.services.processing.status_tracker import get_status_tracker
from app.services.storage import StorageManager
from app.schemas.metadata import ProcessingMetadata


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def extract_metadata_task(
    self,
    document_id: str,
    file_path: str,  # Original filename, kept for API compatibility
    storage_path: str,
    force_reextraction: bool = False
) -> Dict[str, Any]:
    """
    Async task for document metadata extraction.

    Args:
        document_id: Document UUID as string
        file_path: Original file path/name (for reference)
        storage_path: Path to stored file
        force_reextraction: Force re-extraction even if metadata exists

    Returns:
        Dictionary with extraction results
    """
    _ = file_path  # Keep for API compatibility, actual file loaded from storage_path
    doc_id = UUID(document_id)
    
    # Get database session
    db = next(get_db())
    status_tracker = get_status_tracker(db)
    
    try:
        logger.info(f"Starting metadata extraction for document {document_id}")
        
        # Update status to in progress
        asyncio.run(status_tracker.update_status(
            document_id=doc_id,
            stage=ProcessingStageEnum.EXTRACTION,
            status=StageStatusEnum.IN_PROGRESS,
            processing_metadata=ProcessingMetadata(
                percentage_complete=10.0,
                current_operation="Initializing metadata extraction",
                worker_id=current_task.request.id
            )
        ))
        
        # Get document from database
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Check if metadata already exists and extraction not forced
        if (document.document_metadata and 
            not force_reextraction and 
            document.document_metadata.get('extracted_at')):
            logger.info(f"Metadata already exists for {document_id}, skipping extraction")
            
            asyncio.run(status_tracker.mark_stage_completed(
                document_id=doc_id,
                stage=ProcessingStageEnum.EXTRACTION,
                processing_metadata=ProcessingMetadata(
                    percentage_complete=100.0,
                    current_operation="Skipped - metadata already exists"
                )
            ))
            
            return {
                "success": True,
                "document_id": document_id,
                "message": "Metadata already exists",
                "skipped": True
            }
        
        # Update progress
        asyncio.run(status_tracker.update_progress(
            document_id=doc_id,
            stage=ProcessingStageEnum.EXTRACTION,
            percentage=25.0,
            current_operation="Loading file from storage"
        ))

        # Load file content from storage
        storage_manager = StorageManager(db)
        file_content = asyncio.run(storage_manager.load_file(storage_path))
        
        if not file_content:
            raise ValueError(f"Failed to load file content from {storage_path}")
        
        # Update progress
        asyncio.run(status_tracker.update_progress(
            document_id=doc_id,
            stage=ProcessingStageEnum.EXTRACTION,
            percentage=40.0,
            current_operation="Analyzing document with Docling service"
        ))
        
        # Extract metadata using Docling service
        metadata_service = asyncio.run(get_docling_metadata_service())
        extraction_result = asyncio.run(metadata_service.extract_metadata(
            file_content=file_content,
            filename=document.original_name,
            mime_type=document.mime_type,
            document_id=document_id
        ))
        
        # Update progress
        asyncio.run(status_tracker.update_progress(
            document_id=doc_id,
            stage=ProcessingStageEnum.EXTRACTION,
            percentage=75.0,
            current_operation="Storing extracted metadata"
        ))
        
        if extraction_result.success:
            # Store metadata in document
            document.document_metadata = extraction_result.metadata.model_dump()
            document.last_extraction_at = extraction_result.metadata.extracted_at
            
            db.commit()
            
            # Mark extraction as completed
            asyncio.run(status_tracker.mark_stage_completed(
                document_id=doc_id,
                stage=ProcessingStageEnum.EXTRACTION,
                processing_metadata=extraction_result.processing_metadata
            ))
            
            logger.info(
                f"Metadata extraction completed successfully for {document_id}. "
                f"Engine: {extraction_result.metadata.processing_engine.value}, "
                f"Time: {extraction_result.extraction_time_ms:.1f}ms"
            )
            
            return {
                "success": True,
                "document_id": document_id,
                "metadata": extraction_result.metadata.model_dump(),
                "processing_time_ms": extraction_result.extraction_time_ms,
                "processing_engine": extraction_result.metadata.processing_engine.value
            }
        
        else:
            # Handle extraction failure
            error_msg = extraction_result.error_message or "Unknown extraction error"
            
            asyncio.run(status_tracker.mark_stage_failed(
                document_id=doc_id,
                stage=ProcessingStageEnum.EXTRACTION,
                error_message=error_msg,
                processing_metadata=ProcessingMetadata(
                    error_category="extraction_failed",
                    error_details=error_msg
                )
            ))
            
            logger.error(f"Metadata extraction failed for {document_id}: {error_msg}")
            
            # Retry if retries remaining
            if self.request.retries < self.max_retries:
                countdown = 2 ** self.request.retries  # Exponential backoff
                logger.info(f"Retrying metadata extraction for {document_id} in {countdown}s")
                raise self.retry(countdown=countdown)
            
            return {
                "success": False,
                "document_id": document_id,
                "error": error_msg,
                "processing_time_ms": extraction_result.extraction_time_ms
            }
    
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        
        logger.error(f"Metadata extraction task failed for {document_id}: {error_msg}")
        
        # Mark as failed
        try:
            asyncio.run(status_tracker.mark_stage_failed(
                document_id=doc_id,
                stage=ProcessingStageEnum.EXTRACTION,
                error_message=error_msg,
                processing_metadata=ProcessingMetadata(
                    error_category="task_exception",
                    error_details=error_msg,
                    retry_count=self.request.retries
                )
            ))
        except Exception as status_error:
            logger.error(f"Failed to update status: {status_error}")
        
        # Retry if retries remaining
        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries
            logger.info(f"Retrying metadata extraction for {document_id} in {countdown}s")
            raise self.retry(countdown=countdown, exc=e)
        
        return {
            "success": False,
            "document_id": document_id,
            "error": error_msg,
            "retries": self.request.retries
        }
    
    finally:
        db.close()


@celery_app.task
def refresh_metadata_task(document_id: str) -> Dict[str, Any]:
    """
    Task to refresh metadata for a specific document.
    
    Args:
        document_id: Document UUID as string
        
    Returns:
        Dictionary with refresh results
    """
    db = next(get_db())
    
    try:
        # Get document
        document = db.query(Document).filter(Document.id == UUID(document_id)).first()
        if not document:
            return {
                "success": False,
                "error": f"Document {document_id} not found"
            }
        
        # Call main extraction task with force flag
        return extract_metadata_task.delay(
            document_id=document_id,
            file_path=document.original_name,
            storage_path=document.storage_path,
            force_reextraction=True
        ).get()
        
    except Exception as e:
        logger.error(f"Metadata refresh task failed for {document_id}: {e}")
        return {
            "success": False,
            "document_id": document_id,
            "error": str(e)
        }
    
    finally:
        db.close()


@celery_app.task
def batch_extract_metadata_task(document_ids: list, force_reextraction: bool = False) -> Dict[str, Any]:
    """
    Task to extract metadata for multiple documents in batch.
    
    Args:
        document_ids: List of document UUID strings
        force_reextraction: Force re-extraction for all documents
        
    Returns:
        Dictionary with batch processing results
    """
    db = next(get_db())
    results = []
    
    try:
        logger.info(f"Starting batch metadata extraction for {len(document_ids)} documents")
        
        for doc_id in document_ids:
            try:
                # Get document
                document = db.query(Document).filter(Document.id == UUID(doc_id)).first()
                if not document:
                    results.append({
                        "document_id": doc_id,
                        "success": False,
                        "error": "Document not found"
                    })
                    continue
                
                # Queue extraction task
                task_result = extract_metadata_task.delay(
                    document_id=doc_id,
                    file_path=document.original_name,
                    storage_path=document.storage_path,
                    force_reextraction=force_reextraction
                )
                
                results.append({
                    "document_id": doc_id,
                    "task_id": task_result.id,
                    "queued": True
                })
                
            except Exception as e:
                logger.error(f"Failed to queue metadata extraction for {doc_id}: {e}")
                results.append({
                    "document_id": doc_id,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "total_documents": len(document_ids),
            "queued_count": len([r for r in results if r.get("queued")]),
            "error_count": len([r for r in results if not r.get("queued")]),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch metadata extraction failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": results
        }
    
    finally:
        db.close()