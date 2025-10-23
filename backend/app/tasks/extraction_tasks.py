"""
Text Extraction Celery Tasks
Async tasks for document text extraction using Docling
"""
import logging
import asyncio
from uuid import UUID

from app.celery_app import celery_app
from app.db.database import SessionLocal
from app.models.document import Document, ProcessingStageEnum, StageStatusEnum, DocumentStatusEnum
from app.services.extraction import get_text_extractor
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
    name="app.tasks.extraction_tasks.extract_document_text",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Retry after 60 seconds
)
def extract_document_text(self, document_id: str):
    """
    Extract text from document using Docling

    Args:
        document_id: Document UUID string

    This task:
    1. Updates processing status to IN_PROGRESS
    2. Extracts text using Docling (with smart OCR fallback)
    3. Saves extracted text to document_texts table
    4. Updates processing status to COMPLETED/FAILED
    5. Updates document.last_extraction_at timestamp
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
            f"Starting text extraction task for document {document_id} "
            f"({document.original_name})"
        )

        # Initialize status tracker
        tracker = ProcessingStatusTracker(db)

        # Mark extraction stage as IN_PROGRESS
        run_async(tracker.update_status(
            document_id=doc_uuid,
            stage=ProcessingStageEnum.EXTRACTION,
            status=StageStatusEnum.IN_PROGRESS,
        ))

        # Update document status to PROCESSING
        document.status = DocumentStatusEnum.PROCESSING
        db.commit()

        # Get text extractor
        extractor = get_text_extractor()

        # Extract text (async operation wrapped)
        result = run_async(extractor.extract_text(
            file_path=document.storage_path,
            document_id=doc_uuid,
            mime_type=document.mime_type,
        ))

        if not result.success:
            # Extraction failed
            logger.error(
                f"Text extraction failed for document {document_id}: "
                f"{result.error_message}"
            )

            # Mark extraction stage as FAILED
            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.EXTRACTION,
                error_message=result.error_message or "Text extraction failed",
            ))

            # Update document status to FAILED
            document.status = DocumentStatusEnum.FAILED
            document.processing_reason = result.error_message
            db.commit()

            # Retry if possible
            if self.request.retries < self.max_retries:
                logger.info(f"Retrying text extraction for document {document_id}")
                raise self.retry(exc=Exception(result.error_message))

            return {
                "success": False,
                "error": result.error_message,
                "document_id": document_id,
            }

        # Extraction successful - save text to database
        document_text = run_async(extractor.save_extracted_text(
            db=db,
            document_id=doc_uuid,
            result=result,
        ))

        if not document_text:
            error_msg = "Failed to save extracted text to database"
            logger.error(f"{error_msg} for document {document_id}")

            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.EXTRACTION,
                error_message=error_msg,
            ))

            document.status = DocumentStatusEnum.FAILED
            document.processing_reason = error_msg
            db.commit()

            return {
                "success": False,
                "error": error_msg,
                "document_id": document_id,
            }

        # Mark extraction stage as COMPLETED
        run_async(tracker.mark_stage_completed(
            document_id=doc_uuid,
            stage=ProcessingStageEnum.EXTRACTION,
        ))

        # Update document status to COMPLETED (for now - later we'll chain chunking)
        document.status = DocumentStatusEnum.COMPLETED
        db.commit()

        logger.info(
            f"Text extraction completed for document {document_id}: "
            f"{result.text_length} chars, {result.pages_with_ocr}/{result.total_pages} OCR pages, "
            f"quality={result.extraction_quality:.2f}"
        )

        return {
            "success": True,
            "document_id": document_id,
            "text_length": result.text_length,
            "extraction_method": result.extraction_method,
            "pages_with_ocr": result.pages_with_ocr,
            "total_pages": result.total_pages,
            "extraction_quality": result.extraction_quality,
            "extraction_duration_ms": result.extraction_duration_ms,
        }

    except Exception as e:
        logger.error(
            f"Unexpected error in text extraction task for document {document_id}: {e}",
            exc_info=True,
        )

        # Update status to FAILED
        try:
            tracker = ProcessingStatusTracker(db)
            run_async(tracker.mark_stage_failed(
                document_id=doc_uuid,
                stage=ProcessingStageEnum.EXTRACTION,
                error_message=str(e),
            ))

            document = db.query(Document).filter(Document.id == doc_uuid).first()
            if document:
                document.status = DocumentStatusEnum.FAILED
                document.processing_reason = str(e)
                db.commit()

        except Exception as status_error:
            logger.error(f"Failed to update status after error: {status_error}")

        # Retry if possible
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        return {
            "success": False,
            "error": str(e),
            "document_id": document_id,
        }

    finally:
        db.close()
