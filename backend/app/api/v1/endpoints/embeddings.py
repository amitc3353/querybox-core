"""
Embedding Endpoints
Step 9.2: BGE-M3 Embedding Generation

Endpoints:
- POST /documents/{document_id}/embeddings/generate  - Trigger embedding generation
- GET  /documents/{document_id}/embeddings/status    - Check embedding status
"""
from fastapi import APIRouter, Depends, Path, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
import logging

from app.db.database import get_db
from app.models.document import Document
from app.tasks.embedding_tasks import generate_embeddings

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class EmbeddingGenerateRequest(BaseModel):
    """Request to generate embeddings"""
    force_regenerate: bool = False
    batch_size: int = 100


class EmbeddingGenerateResponse(BaseModel):
    """Response from embedding generation trigger"""
    task_id: str
    document_id: str
    status: str
    message: str


class EmbeddingStatusResponse(BaseModel):
    """Embedding status response"""
    document_id: str
    total_chunks: int
    chunks_with_embeddings: int
    completion_percentage: float
    embedding_model: Optional[str]
    processing_status: Optional[str]
    last_embedding_at: Optional[str]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_uuid(document_id: str) -> UUID:
    """Validate and convert document ID string to UUID"""
    try:
        return UUID(document_id)
    except ValueError:
        logger.warning(f"Invalid UUID format: {document_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/{document_id}/embeddings/generate",
    response_model=EmbeddingGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate embeddings for document",
    description="Trigger BGE-M3 embedding generation for all chunks of a document"
)
async def generate_document_embeddings(
    document_id: str = Path(..., description="Document UUID"),
    request_body: Optional[EmbeddingGenerateRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Trigger embedding generation for a document

    Args:
        document_id: Document UUID
        request_body: Optional parameters (force_regenerate, batch_size)
        db: Database session

    Returns:
        Task ID and status

    Raises:
        400: Invalid UUID
        404: Document not found
        400: No chunks found
    """
    logger.info(f"POST /documents/{document_id}/embeddings/generate")

    # Validate UUID
    doc_uuid = validate_uuid(document_id)

    # Get document
    document = db.query(Document).filter(Document.id == doc_uuid).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}"
        )

    # Check if chunks exist
    from app.models.embedding import Embedding
    chunk_count = db.query(Embedding).filter(
        Embedding.document_id == doc_uuid
    ).count()

    if chunk_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chunks found. Document must be chunked before embedding generation."
        )

    # Check if embeddings already exist
    if request_body is None or not request_body.force_regenerate:
        existing_embeddings = db.query(Embedding).filter(
            Embedding.document_id == doc_uuid,
            Embedding.embedding.isnot(None)
        ).count()

        if existing_embeddings > 0:
            logger.info(
                f"Document {document_id} already has {existing_embeddings} embeddings, "
                "use force_regenerate=true to regenerate"
            )
            return EmbeddingGenerateResponse(
                task_id="n/a",
                document_id=document_id,
                status="SKIPPED",
                message=f"Embeddings already exist ({existing_embeddings} chunks). "
                        "Use force_regenerate=true to regenerate."
            )

    # Queue embedding generation task
    task = generate_embeddings.apply_async(args=[document_id])

    logger.info(
        f"Embedding generation queued for document {document_id}, "
        f"task_id={task.id}"
    )

    return EmbeddingGenerateResponse(
        task_id=task.id,
        document_id=document_id,
        status="QUEUED",
        message=f"Embedding generation queued for {chunk_count} chunks"
    )


@router.get(
    "/{document_id}/embeddings/status",
    response_model=EmbeddingStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get embedding status",
    description="Check embedding generation status and progress for a document"
)
async def get_embedding_status(
    document_id: str = Path(..., description="Document UUID"),
    db: Session = Depends(get_db)
):
    """
    Get embedding status for a document

    Args:
        document_id: Document UUID
        db: Database session

    Returns:
        Embedding status with completion percentage

    Raises:
        400: Invalid UUID
        404: Document not found
    """
    logger.info(f"GET /documents/{document_id}/embeddings/status")

    # Validate UUID
    doc_uuid = validate_uuid(document_id)

    # Get document
    document = db.query(Document).filter(Document.id == doc_uuid).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}"
        )

    # Get embedding status using BatchProcessor
    from app.services.embeddings import BatchProcessor
    batch_processor = BatchProcessor(db)

    status_data = batch_processor.get_embedding_status(doc_uuid)

    # Get processing status
    from app.models.processing_status import ProcessingStatus
    from app.models.document import ProcessingStageEnum

    processing_status_record = db.query(ProcessingStatus).filter(
        ProcessingStatus.document_id == doc_uuid,
        ProcessingStatus.stage == ProcessingStageEnum.EMBEDDING
    ).first()

    processing_status_str = (
        processing_status_record.status.value
        if processing_status_record else None
    )

    # Get last_embedding_at
    last_embedding_at = (
        document.last_embedding_at.isoformat()
        if document.last_embedding_at else None
    )

    logger.info(
        f"Embedding status for document {document_id}: "
        f"{status_data['chunks_with_embeddings']}/{status_data['total_chunks']} "
        f"({status_data['completion_percentage']}%)"
    )

    return EmbeddingStatusResponse(
        document_id=document_id,
        total_chunks=status_data["total_chunks"],
        chunks_with_embeddings=status_data["chunks_with_embeddings"],
        completion_percentage=status_data["completion_percentage"],
        embedding_model=status_data["embedding_model"],
        processing_status=processing_status_str,
        last_embedding_at=last_embedding_at
    )
