"""
Chunking Celery Tasks
Async tasks for splitting document text into chunks
"""
import logging
import asyncio
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.celery_app import celery_app
from app.db.database import SessionLocal
from app.models.document import Document, ProcessingStageEnum, StageStatusEnum
from app.models.document_text import DocumentText
from app.models.processing_status import ProcessingStatus
from app.services.chunking import get_chunking_service
from app.services.processing.status_tracker import ProcessingStatusTracker


logger = logging.getLogger(__name__)


def validate_chunk_quality(document_id: UUID, db) -> float:
    """
    Validate chunk quality based on business rules (section 4.2)

    Quality scoring (additive, max 1.0):
    - Avg chunk size 400-600 tokens: +0.3
    - >80% chunks have headings: +0.3
    - Semantic density 0.5-0.8: +0.2
    - No chunks < 100 tokens: +0.2

    Args:
        document_id: Document UUID
        db: Database session

    Returns:
        Quality score from 0.0 to 1.0
    """
    from app.models.embedding import Embedding

    # Query all chunks for this document
    chunks = db.query(Embedding).filter(
        Embedding.document_id == document_id
    ).all()

    if not chunks:
        return 0.0

    quality_score = 0.0

    # 1. Avg chunk size 400-600 tokens: +0.3
    total_tokens = sum(c.chunk_tokens for c in chunks if c.chunk_tokens)
    avg_tokens = total_tokens / len(chunks) if chunks else 0
    if 400 <= avg_tokens <= 600:
        quality_score += 0.3
        logger.debug(f"Quality check passed: avg_tokens={avg_tokens:.0f} (400-600) +0.3")
    else:
        logger.debug(f"Quality check failed: avg_tokens={avg_tokens:.0f} (expected 400-600)")

    # 2. >80% chunks have headings: +0.3
    chunks_with_headings = sum(
        1 for c in chunks
        if c.section_heading is not None and c.section_heading.strip()
    )
    heading_coverage = chunks_with_headings / len(chunks) if chunks else 0
    if heading_coverage > 0.8:
        quality_score += 0.3
        logger.debug(f"Quality check passed: heading_coverage={heading_coverage:.1%} (>80%) +0.3")
    else:
        logger.debug(f"Quality check failed: heading_coverage={heading_coverage:.1%} (expected >80%)")

    # 3. Semantic density 0.5-0.8: +0.2
    densities = [c.semantic_density for c in chunks if c.semantic_density is not None]
    avg_density = sum(densities) / len(densities) if densities else 0
    if 0.5 <= avg_density <= 0.8:
        quality_score += 0.2
        logger.debug(f"Quality check passed: avg_density={avg_density:.2f} (0.5-0.8) +0.2")
    else:
        logger.debug(f"Quality check failed: avg_density={avg_density:.2f} (expected 0.5-0.8)")

    # 4. No chunks < 100 tokens: +0.2
    small_chunks = [c for c in chunks if c.chunk_tokens and c.chunk_tokens < 100]
    if not small_chunks:
        quality_score += 0.2
        logger.debug(f"Quality check passed: no chunks < 100 tokens +0.2")
    else:
        logger.debug(f"Quality check failed: {len(small_chunks)} chunks < 100 tokens")

    logger.info(
        f"Chunk quality validation for document {document_id}: "
        f"score={quality_score:.2f}, avg_tokens={avg_tokens:.0f}, "
        f"heading_coverage={heading_coverage:.1%}, avg_density={avg_density:.2f}, "
        f"small_chunks={len(small_chunks)}"
    )

    return round(quality_score, 2)


def run_async(coro):
    """Helper to run async coroutines in sync Celery tasks"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@celery_app.task(
    name="app.tasks.chunking_tasks.chunk_document_text",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Retry after 60 seconds
)
def chunk_document_text(self, document_id: str):
    """
    Split document text into chunks for embedding generation

    Args:
        document_id: Document UUID string

    This task:
    1. Updates processing status to IN_PROGRESS
    2. Fetches extracted text from document_texts table
    3. Splits text into chunks using ChunkingService
    4. Saves chunks to embeddings table
    5. Updates processing status to COMPLETED/FAILED
    6. Updates document.last_indexed_at timestamp
    """
    db = SessionLocal()
    doc_uuid = UUID(document_id)

    try:
        # Get document from database
        document = db.query(Document).filter(Document.id == doc_uuid).first()

        if not document:
            logger.error(f"Document {document_id} not found")
            return {"success": False, "error": "Document not found"}

        logger.info(
            f"Starting chunking task for document {document_id} "
            f"({document.original_name})"
        )

        # Initialize status tracker
        tracker = ProcessingStatusTracker(db)

        # Mark chunking stage as IN_PROGRESS
        run_async(tracker.update_status(
            document_id=doc_uuid,
            stage=ProcessingStageEnum.CHUNKING,
            status=StageStatusEnum.IN_PROGRESS,
        ))

        # Fetch extracted text
        document_text = db.query(DocumentText).filter(
            DocumentText.document_id == doc_uuid
        ).first()

        if not document_text:
            error_msg = "No extracted text found. Text extraction must complete first."
            logger.error(f"{error_msg} for document {document_id}")

            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.CHUNKING,
                error_message=error_msg,
            ))

            return {
                "success": False,
                "error": error_msg,
                "document_id": document_id,
            }

        # Validate text length
        if not document_text.full_text or document_text.text_length < 100:
            error_msg = f"Document text too short for chunking ({document_text.text_length} chars)"
            logger.warning(f"{error_msg} for document {document_id}")

            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.CHUNKING,
                error_message=error_msg,
            ))

            return {
                "success": False,
                "error": error_msg,
                "document_id": document_id,
            }

        # Get chunking service
        chunking_service = get_chunking_service()

        # Perform chunking
        logger.info(f"Chunking {document_text.text_length} chars for document {document_id}")

        result = chunking_service.chunk_text(
            text=document_text.full_text,
            document_id=doc_uuid,
            db=db,
        )

        if not result.success:
            # Chunking failed
            logger.error(
                f"Chunking failed for document {document_id}: {result.error_message}"
            )

            tracker.mark_stage_failed_sync(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.CHUNKING,
                error_message=result.error_message or "Chunking failed",
            )

            # Retry if possible
            if self.request.retries < self.max_retries:
                logger.info(f"Retrying chunking for document {document_id}")
                raise self.retry(exc=Exception(result.error_message))

            return {
                "success": False,
                "error": result.error_message,
                "document_id": document_id,
            }

        # Chunking successful - validate quality using business rules
        quality_score = validate_chunk_quality(doc_uuid, db)

        if quality_score < 0.6:
            logger.warning(
                f"Low chunk quality for document {document_id} ({document.original_name}): "
                f"quality_score={quality_score:.2f}, threshold=0.6 (MIN_QUALITY_SCORE)"
            )

        # Mark stage as COMPLETED
        # Note: ProcessingStatusTracker.mark_stage_completed doesn't support result_data parameter
        # We'll store it in the processing_status table via direct update
        run_async(tracker.mark_stage_completed(
            document_id=doc_uuid,
            stage=ProcessingStageEnum.CHUNKING,
        ))

        # Update result_data with quality_score
        status_record = db.query(ProcessingStatus).filter(
            ProcessingStatus.document_id == doc_uuid,
            ProcessingStatus.stage == ProcessingStageEnum.CHUNKING
        ).first()
        if status_record:
            status_record.result_data = {
                "chunk_count": result.chunk_count,
                "total_chars": result.total_chars,
                "avg_chunk_size": result.avg_chunk_size,
                "quality_score": quality_score,  # Use validated quality score
            }
            status_record.duration_ms = result.processing_time_ms
            db.commit()

        # Update document.last_indexed_at timestamp
        document.last_indexed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            f"Chunking completed for document {document_id}: "
            f"{result.chunk_count} chunks, avg size {result.avg_chunk_size} chars, "
            f"quality_score={quality_score:.2f}, {result.processing_time_ms}ms"
        )

        return {
            "success": True,
            "document_id": document_id,
            "chunk_count": result.chunk_count,
            "avg_chunk_size": result.avg_chunk_size,
            "quality_score": quality_score,  # Use validated quality score
            "processing_time_ms": result.processing_time_ms,
        }

    except ValueError as e:
        # Validation errors - don't retry
        logger.warning(
            f"Validation error in chunking task for document {document_id}: {e}"
        )

        try:
            tracker = ProcessingStatusTracker(db)
            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.CHUNKING,
                error_message=str(e),
            ))
        except Exception as status_error:
            logger.error(f"Failed to update status after validation error: {status_error}")

        return {
            "success": False,
            "error": str(e),
            "document_id": document_id,
        }

    except SQLAlchemyError as e:
        # Database errors - retry
        logger.error(
            f"Database error in chunking task for document {document_id}: {e}",
            exc_info=True,
        )

        try:
            tracker = ProcessingStatusTracker(db)
            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.CHUNKING,
                error_message=f"Database error: {str(e)}",
            ))
        except Exception as status_error:
            logger.error(f"Failed to update status after database error: {status_error}")

        # Retry if possible
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying chunking after database error for document {document_id}")
            raise self.retry(exc=e)

        return {
            "success": False,
            "error": f"Database error: {str(e)}",
            "document_id": document_id,
        }

    except Exception as e:
        # Unexpected errors - retry
        logger.error(
            f"Unexpected error in chunking task for document {document_id}: {e}",
            exc_info=True,
        )

        try:
            tracker = ProcessingStatusTracker(db)
            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.CHUNKING,
                error_message=str(e),
            ))
        except Exception as status_error:
            logger.error(f"Failed to update status after error: {status_error}")

        # Retry if possible
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying chunking after unexpected error for document {document_id}")
            raise self.retry(exc=e)

        return {
            "success": False,
            "error": str(e),
            "document_id": document_id,
        }

    finally:
        db.close()
