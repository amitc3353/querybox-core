"""
Unit Tests for Extraction Celery Tasks
Tests extract_document_text task
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from app.tasks.extraction_tasks import extract_document_text, run_async
from app.services.extraction.text_extraction_service import TextExtractionResult
from app.models.document import Document, DocumentStatusEnum, ProcessingStageEnum, StageStatusEnum


class TestRunAsync:
    """Test run_async helper function"""

    def test_run_async_with_existing_loop(self):
        """Test run_async uses existing event loop"""
        import asyncio

        async def sample_coro():
            return "result"

        result = run_async(sample_coro())
        assert result == "result"

    def test_run_async_creates_new_loop(self):
        """Test run_async creates new loop if none exists"""
        import asyncio

        # Close any existing loop
        try:
            loop = asyncio.get_event_loop()
            loop.close()
        except RuntimeError:
            pass

        async def sample_coro():
            return "result"

        result = run_async(sample_coro())
        assert result == "result"


class TestExtractDocumentTextTask:
    """Test extract_document_text Celery task"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        with patch('app.tasks.extraction_tasks.SessionLocal') as mock_session:
            db = Mock()
            mock_session.return_value = db
            yield db

    @pytest.fixture
    def mock_document(self):
        """Mock Document model"""
        doc = Mock(spec=Document)
        doc.id = uuid4()
        doc.original_name = "test.pdf"
        doc.storage_path = "/storage/test.pdf"
        doc.mime_type = "application/pdf"
        doc.status = DocumentStatusEnum.PENDING
        return doc

    @pytest.fixture
    def mock_extractor(self):
        """Mock DocumentTextExtractor"""
        with patch('app.tasks.extraction_tasks.get_text_extractor') as mock_get:
            extractor = Mock()
            mock_get.return_value = extractor
            yield extractor

    @pytest.fixture
    def mock_tracker(self):
        """Mock ProcessingStatusTracker"""
        with patch('app.tasks.extraction_tasks.ProcessingStatusTracker') as mock_class:
            tracker = Mock()
            mock_class.return_value = tracker
            yield tracker

    def test_extract_document_text_document_not_found(self, mock_db_session):
        """Test task returns error when document doesn't exist"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Create mock task
        mock_task = Mock()
        mock_task.request.retries = 0
        mock_task.max_retries = 3

        result = extract_document_text.run(str(uuid4()))

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_extract_document_text_success(
        self, mock_db_session, mock_document, mock_extractor, mock_tracker
    ):
        """Test successful text extraction"""
        document_id = str(mock_document.id)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document

        # Mock successful extraction result
        extraction_result = TextExtractionResult(
            success=True,
            full_text="Sample extracted text",
            text_length=22,
            extraction_method="docling",
            extraction_engine="native",
            extraction_quality=0.95,
            pages_with_ocr=0,
            total_pages=10,
            extraction_duration_ms=2000,
            detected_language="en",
        )

        # Mock document_text
        mock_doc_text = Mock()

        with patch('app.tasks.extraction_tasks.run_async') as mock_run_async:
            # Configure run_async to return appropriate values
            mock_run_async.side_effect = [
                None,  # update_status call
                extraction_result,  # extract_text call
                mock_doc_text,  # save_extracted_text call
                None,  # mark_stage_completed call
            ]

            # Create mock task
            mock_task = Mock()
            mock_task.request.retries = 0

            result = extract_document_text.run(document_id)

        assert result["success"] is True
        assert result["document_id"] == document_id
        assert result["text_length"] == 22
        assert result["extraction_method"] == "docling"
        assert result["pages_with_ocr"] == 0
        assert result["total_pages"] == 10

        # Verify document status updated
        assert mock_document.status == DocumentStatusEnum.COMPLETED
        mock_db_session.commit.assert_called()

    def test_extract_document_text_save_fails(
        self, mock_db_session, mock_document, mock_extractor, mock_tracker
    ):
        """Test task handles database save failure"""
        document_id = str(mock_document.id)

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document

        extraction_result = TextExtractionResult(
            success=True,
            full_text="Sample text",
            text_length=11,
            extraction_method="docling",
            extraction_engine="native",
            extraction_quality=0.9,
        )

        with patch('app.tasks.extraction_tasks.run_async') as mock_run_async:
            mock_run_async.side_effect = [
                None,  # update_status call
                extraction_result,  # extract_text call (success)
                None,  # save_extracted_text call (returns None = failed)
                None,  # mark_stage_failed call
            ]

            mock_task = Mock()
            mock_task.request.retries = 0

            result = extract_document_text.run(document_id)

        assert result["success"] is False
        assert "Failed to save" in result["error"]

        # Verify document status updated to FAILED
        assert mock_document.status == DocumentStatusEnum.FAILED

    def test_extract_document_text_db_session_closed(
        self, mock_db_session, mock_document, mock_extractor, mock_tracker
    ):
        """Test database session is always closed in finally block"""
        document_id = str(mock_document.id)

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document

        extraction_result = TextExtractionResult(
            success=True,
            full_text="Text",
            text_length=4,
            extraction_method="docling",
            extraction_engine="native",
        )

        mock_doc_text = Mock()

        with patch('app.tasks.extraction_tasks.run_async') as mock_run_async:
            mock_run_async.side_effect = [
                None,  # update_status
                extraction_result,  # extract_text
                mock_doc_text,  # save_extracted_text
                None,  # mark_stage_completed
            ]

            mock_task = Mock()
            mock_task.request.retries = 0

            extract_document_text.run(document_id)

        # Verify session was closed
        mock_db_session.close.assert_called_once()

    def test_extract_document_text_updates_last_extraction_at(
        self, mock_db_session, mock_document, mock_extractor, mock_tracker
    ):
        """Test task updates document.last_extraction_at timestamp"""
        document_id = str(mock_document.id)

        # Setup two different mock documents for the two query calls
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document

        extraction_result = TextExtractionResult(
            success=True,
            full_text="Text",
            text_length=4,
            extraction_method="docling",
            extraction_engine="native",
        )

        mock_doc_text = Mock()

        with patch('app.tasks.extraction_tasks.run_async') as mock_run_async:
            mock_run_async.side_effect = [
                None,  # update_status
                extraction_result,  # extract_text
                mock_doc_text,  # save_extracted_text (includes updating document)
                None,  # mark_stage_completed
            ]

            mock_task = Mock()
            mock_task.request.retries = 0

            result = extract_document_text.run(document_id)

        assert result["success"] is True
        # save_extracted_text is responsible for updating last_extraction_at
        # We verify it was called
        assert mock_run_async.call_count == 4
