"""
Metadata API Endpoints
Step 6: REST API endpoints for metadata operations

Provides comprehensive metadata management endpoints including extraction,
retrieval, and status monitoring with proper error handling.
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.document import Document, ProcessingStageEnum
from app.schemas.metadata import (
    MetadataExtractionRequest,
    MetadataExtractionResponse,
    DocumentMetadata
)
from app.services.metadata.docling_service import get_docling_metadata_service
from app.services.processing.status_tracker import get_status_tracker
from app.queue import get_task_queue  # Use abstraction instead of direct Celery import


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/documents/{document_id}/metadata", response_model=Dict[str, Any])
async def get_document_metadata(
    document_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get metadata for a specific document.
    
    Returns the current metadata stored in the document_metadata JSONB field
    along with extraction information and processing status.
    """
    try:
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get processing status for extraction stage
        status_tracker = get_status_tracker(db)
        progress_info = await status_tracker.get_overall_progress(document_id)
        extraction_stage = progress_info.get("stages", {}).get("extraction", {})
        
        return {
            "document_id": str(document_id),
            "metadata": document.document_metadata,
            "last_extraction_at": document.last_extraction_at.isoformat() if document.last_extraction_at else None,
            "extraction_status": extraction_stage.get("status"),
            "processing_info": {
                "overall_progress": progress_info.get("overall_progress", 0.0),
                "current_stage": progress_info.get("current_stage"),
                "extraction_stage": extraction_stage
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metadata for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/documents/{document_id}/metadata/extract", response_model=Dict[str, Any])
async def extract_document_metadata(
    document_id: UUID,
    request: MetadataExtractionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start metadata extraction for a document.
    
    Queues an async task to extract metadata using Docling service
    or fallback extractors.
    """
    try:
        # Validate document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if extraction already in progress
        status_tracker = get_status_tracker(db)
        progress = await status_tracker.get_overall_progress(document_id)
        extraction_stage = progress.get("stages", {}).get("extraction", {})
        
        if (extraction_stage.get("status") == "in_progress" and 
            not request.force_reextraction):
            raise HTTPException(
                status_code=409, 
                detail="Metadata extraction already in progress"
            )
        
        # Queue extraction task using abstraction
        queue = get_task_queue()
        task_id = queue.enqueue_task(
            task_name="extract_metadata_task",
            kwargs={
                "document_id": str(document_id),
                "file_path": document.original_name,
                "storage_path": document.storage_path,
                "force_reextraction": request.force_reextraction
            },
            queue="metadata",
            priority=5
        )

        logger.info(f"Queued metadata extraction for document {document_id}, task {task_id}")

        return {
            "document_id": str(document_id),
            "task_id": task_id,
            "status": "queued",
            "message": "Metadata extraction task queued successfully",
            "force_reextraction": request.force_reextraction
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start metadata extraction for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/documents/{document_id}/metadata/refresh", response_model=Dict[str, Any])
async def refresh_document_metadata(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Refresh metadata for a document (force re-extraction).
    
    Always performs fresh metadata extraction, even if metadata already exists.
    """
    try:
        # Validate document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Queue refresh task using abstraction
        queue = get_task_queue()
        task_id = queue.enqueue_task(
            task_name="refresh_metadata_task",
            kwargs={"document_id": str(document_id)},
            queue="metadata",
            priority=5
        )

        logger.info(f"Queued metadata refresh for document {document_id}, task {task_id}")

        return {
            "document_id": str(document_id),
            "task_id": task_id,
            "status": "queued",
            "message": "Metadata refresh task queued successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh metadata for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/{document_id}/metadata/status", response_model=Dict[str, Any])
async def get_metadata_extraction_status(
    document_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get metadata extraction status and progress for a document.
    """
    try:
        # Validate document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get processing status
        status_tracker = get_status_tracker(db)
        progress_info = await status_tracker.get_overall_progress(document_id)
        extraction_stage = progress_info.get("stages", {}).get("extraction", {})
        
        return {
            "document_id": str(document_id),
            "extraction_status": extraction_stage.get("status", "not_started"),
            "progress_percentage": extraction_stage.get("metadata", {}).get("percentage_complete", 0.0),
            "current_operation": extraction_stage.get("metadata", {}).get("current_operation"),
            "started_at": extraction_stage.get("started_at"),
            "completed_at": extraction_stage.get("completed_at"),
            "duration_ms": extraction_stage.get("duration_ms"),
            "error_message": extraction_stage.get("error_message"),
            "retry_count": extraction_stage.get("retry_count", 0),
            "overall_progress": progress_info.get("overall_progress", 0.0),
            "estimated_completion": extraction_stage.get("metadata", {}).get("estimated_completion")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get extraction status for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/documents/metadata/batch-extract", response_model=Dict[str, Any])
async def batch_extract_metadata(
    document_ids: list[UUID],
    force_reextraction: bool = Query(False, description="Force re-extraction for all documents"),
    db: Session = Depends(get_db)
):
    """
    Start metadata extraction for multiple documents.
    
    Queues extraction tasks for all specified documents.
    """
    try:
        if not document_ids:
            raise HTTPException(status_code=400, detail="No document IDs provided")
        
        if len(document_ids) > 100:
            raise HTTPException(status_code=400, detail="Too many documents (max 100)")
        
        # Validate all documents exist
        document_ids_str = [str(doc_id) for doc_id in document_ids]
        existing_docs = db.query(Document).filter(Document.id.in_(document_ids)).all()
        existing_ids = {str(doc.id) for doc in existing_docs}
        
        missing_ids = set(document_ids_str) - existing_ids
        if missing_ids:
            raise HTTPException(
                status_code=404, 
                detail=f"Documents not found: {list(missing_ids)}"
            )
        
        # Queue batch extraction task using abstraction
        queue = get_task_queue()
        task_id = queue.enqueue_task(
            task_name="batch_extract_metadata_task",
            kwargs={
                "document_ids": document_ids_str,
                "force_reextraction": force_reextraction
            },
            queue="metadata",
            priority=5
        )

        logger.info(f"Queued batch metadata extraction for {len(document_ids)} documents, task {task_id}")

        return {
            "task_id": task_id,
            "status": "queued",
            "document_count": len(document_ids),
            "force_reextraction": force_reextraction,
            "message": "Batch metadata extraction task queued successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start batch metadata extraction: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/metadata/service/health", response_model=Dict[str, Any])
async def get_metadata_service_health():
    """
    Get health status of metadata extraction services.
    
    Checks Docling service availability and overall system health.
    """
    try:
        # Check Docling service
        docling_service = await get_docling_metadata_service()
        docling_healthy = await docling_service.is_healthy()
        docling_info = await docling_service.get_service_info()
        supported_formats = await docling_service.get_supported_formats()
        
        return {
            "overall_status": "healthy" if docling_healthy else "degraded",
            "docling_service": {
                "status": "healthy" if docling_healthy else "unhealthy",
                "info": docling_info,
                "supported_formats": supported_formats
            },
            "fallback_extraction": {
                "status": "healthy",
                "available": True
            },
            "timestamp": "2024-11-15T14:30:00Z"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-11-15T14:30:00Z"
        }


@router.get("/metadata/service/info", response_model=Dict[str, Any])
async def get_metadata_service_info():
    """
    Get detailed information about metadata extraction capabilities.
    """
    try:
        # Get Docling service info
        docling_service = await get_docling_metadata_service()
        supported_formats = await docling_service.get_supported_formats()
        service_info = await docling_service.get_service_info()
        
        return {
            "service": "QueryBox Core Metadata Service",
            "version": "1.0.0",
            "docling_integration": {
                "enabled": True,
                "supported_formats": supported_formats,
                "service_info": service_info
            },
            "fallback_extraction": {
                "enabled": True,
                "supported_formats": [
                    "text/plain",
                    "text/csv",
                    "application/json",
                    "application/xml"
                ]
            },
            "features": {
                "async_extraction": True,
                "batch_processing": True,
                "progress_tracking": True,
                "retry_mechanism": True,
                "quality_assessment": True,
                "language_detection": True
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get service info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")