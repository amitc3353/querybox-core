"""
Embedding Celery Tasks
Async tasks for generating BGE-M3 embeddings
"""
import logging
import asyncio
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.celery_app import celery_app
from app.db.database import SessionLocal
from app.models.document import Document, ProcessingStageEnum, StageStatusEnum
from app.models.embedding import Embedding
from app.models.processing_status import ProcessingStatus
from app.services.embeddings import BatchProcessor
from app.services.processing.status_tracker import ProcessingStatusTracker

logger = logging.getLogger(__name__)


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
    name="app.tasks.embedding_tasks.generate_embeddings",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Retry after 60 seconds
)
def generate_embeddings(self, document_id: str):
    """
    Generate BGE-M3 embeddings for all document chunks

    This task:
    1. Updates processing status to IN_PROGRESS
    2. Fetches chunks without embeddings
    3. Generates embeddings in batches of 100
    4. Updates database with vectors
    5. Updates processing status to COMPLETED/FAILED
    6. Updates document.last_embedding_at timestamp

    Args:
        document_id: Document UUID string

    Returns:
        {
            "success": bool,
            "document_id": str,
            "chunks_processed": int,
            "processing_time_ms": int,
            "embeddings_per_second": float
        }
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
            f"Starting embedding generation for document {document_id} "
            f"({document.original_name})"
        )

        # Initialize status tracker
        tracker = ProcessingStatusTracker(db)

        # Mark embedding stage as IN_PROGRESS
        run_async(tracker.update_status(
            document_id=doc_uuid,
            stage=ProcessingStageEnum.EMBEDDING,
            status=StageStatusEnum.IN_PROGRESS,
        ))

        # Initialize batch processor
        batch_processor = BatchProcessor(db)

        # Check if chunks exist
        chunk_count = db.query(Embedding).filter(
            Embedding.document_id == doc_uuid
        ).count()

        if chunk_count == 0:
            error_msg = "No chunks found. Document must be chunked before embedding."
            logger.error(f"{error_msg} for document {document_id}")

            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.EMBEDDING,
                error_message=error_msg,
            ))

            return {
                "success": False,
                "error": error_msg,
                "document_id": document_id,
            }

        # Process document chunks
        logger.info(f"Processing {chunk_count} chunks for document {document_id}")

        result = batch_processor.process_document_chunks(
            document_id=doc_uuid,
            batch_size=100
        )

        if not result.success:
            # Embedding generation failed
            logger.error(
                f"Embedding generation failed for document {document_id}: "
                f"{result.error_message}"
            )

            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.EMBEDDING,
                error_message=result.error_message or "Embedding generation failed",
            ))

            # Retry if possible
            if self.request.retries < self.max_retries:
                logger.info(f"Retrying embedding generation for document {document_id}")
                raise self.retry(exc=Exception(result.error_message))

            return {
                "success": False,
                "error": result.error_message,
                "document_id": document_id,
            }

        # Embedding generation successful
        # Mark stage as COMPLETED
        run_async(tracker.mark_stage_completed(
            document_id=doc_uuid,
            stage=ProcessingStageEnum.EMBEDDING,
        ))

        # Update result_data
        status_record = db.query(ProcessingStatus).filter(
            ProcessingStatus.document_id == doc_uuid,
            ProcessingStatus.stage == ProcessingStageEnum.EMBEDDING
        ).first()

        if status_record:
            status_record.result_data = {
                "chunks_processed": result.chunks_processed,
                "processing_time_ms": result.processing_time_ms,
                "embeddings_per_second": result.embeddings_per_second,
                "model": "BAAI/bge-m3"
            }
            status_record.duration_ms = result.processing_time_ms
            db.commit()

        # Update document.last_embedding_at timestamp
        document.last_embedding_at = datetime.now(timezone.utc)
        db.commit()

        logger.info(
            f"Embedding generation completed for document {document_id}: "
            f"{result.chunks_processed} chunks, "
            f"{result.embeddings_per_second:.2f} emb/s, "
            f"{result.processing_time_ms}ms"
        )

        return {
            "success": True,
            "document_id": document_id,
            "chunks_processed": result.chunks_processed,
            "processing_time_ms": result.processing_time_ms,
            "embeddings_per_second": result.embeddings_per_second,
        }

    except ValueError as e:
        # Validation errors - don't retry
        logger.warning(
            f"Validation error in embedding task for document {document_id}: {e}"
        )

        try:
            tracker = ProcessingStatusTracker(db)
            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.EMBEDDING,
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
            f"Database error in embedding task for document {document_id}: {e}",
            exc_info=True,
        )

        try:
            tracker = ProcessingStatusTracker(db)
            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.EMBEDDING,
                error_message=f"Database error: {str(e)}",
            ))
        except Exception as status_error:
            logger.error(f"Failed to update status after database error: {status_error}")

        # Retry if possible
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying embedding after database error for document {document_id}")
            raise self.retry(exc=e)

        return {
            "success": False,
            "error": f"Database error: {str(e)}",
            "document_id": document_id,
        }

    except Exception as e:
        # Unexpected errors - retry
        logger.error(
            f"Unexpected error in embedding task for document {document_id}: {e}",
            exc_info=True,
        )

        try:
            tracker = ProcessingStatusTracker(db)
            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.EMBEDDING,
                error_message=str(e),
            ))
        except Exception as status_error:
            logger.error(f"Failed to update status after error: {status_error}")

        # Retry if possible
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying embedding after unexpected error for document {document_id}")
            raise self.retry(exc=e)

        return {
            "success": False,
            "error": str(e),
            "document_id": document_id,
        }

    finally:
        db.close()
