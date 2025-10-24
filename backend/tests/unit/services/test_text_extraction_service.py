"""
Unit Tests for Text Extraction Service
Tests DocumentTextExtractor without external dependencies
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from uuid import UUID, uuid4
from datetime import datetime, timezone
from pathlib import Path

from app.services.extraction.text_extraction_service import (
    DocumentTextExtractor,
    TextExtractionResult,
    get_text_extractor,
)
from app.models.document_text import DocumentText
from app.models.document import Document


class TestTextExtractionResult:
    """Test TextExtractionResult dataclass"""

    def test_successful_result(self):
        """Test creating a successful extraction result"""
        result = TextExtractionResult(
            success=True,
            full_text="Sample extracted text",
            text_length=22,
            extraction_method="docling",
            extraction_engine="native",
            extraction_quality=0.95,
            pages_with_ocr=0,
            total_pages=10,
            extraction_duration_ms=1500,
            detected_language="en",
        )

        assert result.success is True
        assert result.full_text == "Sample extracted text"
        assert result.text_length == 22
        assert result.extraction_method == "docling"
        assert result.extraction_quality == 0.95
        assert result.error_message is None

    def test_failed_result(self):
        """Test creating a failed extraction result"""
        result = TextExtractionResult(
            success=False,
            error_message="File not found",
            extraction_duration_ms=100,
        )

        assert result.success is False
        assert result.error_message == "File not found"
        assert result.text_length == 0
        assert result.full_text == ""


class TestDocumentTextExtractor:
    """Test DocumentTextExtractor service"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance with mocked converter"""
        extractor = DocumentTextExtractor()
        # Converter is None by default now (lazy initialization)
        return extractor

    @pytest.fixture
    def mock_doc_result(self):
        """Mock Docling conversion result"""
        mock_result = Mock()
        mock_result.document.export_to_markdown.return_value = "# Sample Document\n\nThis is sample text."
        mock_result.pages = [Mock(ocr_applied=False) for _ in range(10)]
        return mock_result

    @pytest.mark.asyncio
    async def test_extract_text_success_no_ocr(self, extractor, mock_doc_result):
        """Test successful text extraction without OCR"""
        document_id = uuid4()
        file_path = "/tmp/test.pdf"

        # Mock file existence and converter
        with patch('pathlib.Path.exists', return_value=True):
            extractor.converter = Mock()
            extractor.converter.convert.return_value = mock_doc_result

            result = await extractor.extract_text(
                file_path=file_path,
                document_id=document_id,
                mime_type="application/pdf",
            )

        assert result.success is True
        assert "Sample Document" in result.full_text
        assert result.text_length > 0
        assert result.extraction_method == "docling"
        assert result.extraction_engine == "native"
        assert result.pages_with_ocr == 0
        assert result.total_pages == 10
        assert result.extraction_quality > 0

    @pytest.mark.asyncio
    async def test_extract_text_success_with_ocr(self, extractor):
        """Test successful text extraction with OCR on some pages"""
        document_id = uuid4()
        file_path = "/tmp/scanned.pdf"

        # Mock result with OCR applied to some pages
        mock_result = Mock()
        mock_result.document.export_to_markdown.return_value = "Extracted text from scanned document."
        mock_result.pages = [
            Mock(ocr_applied=False) for _ in range(8)
        ] + [
            Mock(ocr_applied=True) for _ in range(2)  # 2 pages with OCR
        ]

        with patch('pathlib.Path.exists', return_value=True):
            extractor.converter = Mock()
            extractor.converter.convert.return_value = mock_result

            result = await extractor.extract_text(
                file_path=file_path,
                document_id=document_id,
                mime_type="application/pdf",
            )

        assert result.success is True
        assert result.extraction_method == "docling_ocr"  # OCR was used
        assert result.extraction_engine == "easyocr"
        assert result.pages_with_ocr == 2
        assert result.total_pages == 10

    @pytest.mark.asyncio
    async def test_extract_text_file_not_found(self, extractor):
        """Test extraction fails when file doesn't exist"""
        document_id = uuid4()
        file_path = "/nonexistent/file.pdf"

        # Set converter to Mock to avoid actual initialization
        extractor.converter = Mock()

        with patch('pathlib.Path.exists', return_value=False):
            result = await extractor.extract_text(
                file_path=file_path,
                document_id=document_id,
                mime_type="application/pdf",
            )

        assert result.success is False
        assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_extract_text_converter_not_initialized(self, extractor):
        """Test extraction fails when converter is None"""
        extractor.converter = None

        # Mock file exists check and initialization to fail
        with patch('pathlib.Path.exists', return_value=True):
            with patch.object(extractor, '_initialize_converter'):
                result = await extractor.extract_text(
                    file_path="/tmp/test.docx",
                    document_id=uuid4(),
                    mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

        assert result.success is False
        assert "not available" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_extract_text_conversion_exception(self, extractor, mock_doc_result):
        """Test extraction handles Docling conversion exceptions"""
        document_id = uuid4()

        with patch('pathlib.Path.exists', return_value=True):
            extractor.converter = Mock()
            extractor.converter.convert.side_effect = Exception("Docling conversion failed")

            result = await extractor.extract_text(
                file_path="/tmp/test.pdf",
                document_id=document_id,
                mime_type="application/pdf",
            )

        assert result.success is False
        assert "Docling conversion failed" in result.error_message

    def test_assess_quality_high_quality_text(self, extractor):
        """Test quality assessment for high-quality text"""
        text = "This is a well-formatted document with proper punctuation. " * 20
        quality = extractor._assess_quality(text, pages_with_ocr=0, total_pages=10)

        assert quality > 0.7  # Should be high quality

    def test_assess_quality_low_quality_text(self, extractor):
        """Test quality assessment for low-quality text"""
        text = "badtextnospacesnopunctuation" * 10
        quality = extractor._assess_quality(text, pages_with_ocr=0, total_pages=10)

        assert quality < 0.6  # Should be low quality (adjusted threshold)

    def test_assess_quality_ocr_penalty(self, extractor):
        """Test OCR usage reduces quality score"""
        text = "Sample text. " * 100

        quality_no_ocr = extractor._assess_quality(text, pages_with_ocr=0, total_pages=10)
        quality_with_ocr = extractor._assess_quality(text, pages_with_ocr=10, total_pages=10)

        assert quality_no_ocr > quality_with_ocr  # OCR reduces quality

    def test_assess_quality_empty_text(self, extractor):
        """Test quality assessment for empty text"""
        quality = extractor._assess_quality("", pages_with_ocr=0, total_pages=1)
        assert quality == 0.0

    def test_detect_language_english(self, extractor):
        """Test language detection for English text"""
        text = "This is an English document. The text contains many English words and phrases. " * 10
        language = extractor._detect_language(text)

        assert language == "en"

    def test_detect_language_short_text(self, extractor):
        """Test language detection with insufficient text"""
        text = "Hi"
        language = extractor._detect_language(text)

        assert language is None  # Too short to detect

    def test_count_ocr_pages(self, extractor):
        """Test counting OCR pages from Docling result"""
        mock_result = Mock()
        mock_result.pages = [
            Mock(ocr_applied=True),
            Mock(ocr_applied=False),
            Mock(ocr_applied=True),
            Mock(ocr_applied=False),
        ]

        count = extractor._count_ocr_pages(mock_result)
        assert count == 2

    def test_count_ocr_pages_no_pages(self, extractor):
        """Test counting OCR pages when result has no pages attribute"""
        mock_result = Mock(spec=[])  # No pages attribute
        count = extractor._count_ocr_pages(mock_result)
        assert count == 0

    def test_count_total_pages(self, extractor):
        """Test counting total pages"""
        mock_result = Mock()
        mock_result.pages = [Mock() for _ in range(15)]

        count = extractor._count_total_pages(mock_result)
        assert count == 15

    def test_count_total_pages_fallback(self, extractor):
        """Test total page count fallback"""
        mock_result = Mock(spec=[])  # No pages attribute
        count = extractor._count_total_pages(mock_result)
        assert count == 1  # Default to 1

    @pytest.mark.asyncio
    async def test_save_extracted_text_new_record(self, extractor):
        """Test saving extracted text creates new record"""
        document_id = uuid4()
        result = TextExtractionResult(
            success=True,
            full_text="Sample text",
            text_length=11,
            extraction_method="docling",
            extraction_engine="native",
            extraction_quality=0.9,
            pages_with_ocr=0,
            total_pages=5,
            extraction_duration_ms=2000,
            detected_language="en",
        )

        # Mock database session
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing record

        mock_document = Mock(spec=Document)
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            None,  # First call: no DocumentText
            mock_document,  # Second call: Document exists
        ]

        document_text = await extractor.save_extracted_text(
            db=mock_db,
            document_id=document_id,
            result=result,
        )

        # Verify DocumentText was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
        assert document_text is not None

    @pytest.mark.asyncio
    async def test_save_extracted_text_update_existing(self, extractor):
        """Test saving extracted text updates existing record"""
        document_id = uuid4()
        result = TextExtractionResult(
            success=True,
            full_text="Updated text",
            text_length=12,
            extraction_method="docling_ocr",
            extraction_engine="easyocr",
            extraction_quality=0.85,
            pages_with_ocr=3,
            total_pages=10,
            extraction_duration_ms=5000,
            detected_language="en",
        )

        # Mock existing DocumentText
        existing_text = Mock(spec=DocumentText)
        existing_text.document_id = document_id

        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_text

        document_text = await extractor.save_extracted_text(
            db=mock_db,
            document_id=document_id,
            result=result,
        )

        # Verify existing record was updated
        assert existing_text.full_text == "Updated text"
        assert existing_text.extraction_method == "docling_ocr"
        mock_db.commit.assert_called()
        mock_db.refresh.assert_called_once_with(existing_text)

    @pytest.mark.asyncio
    async def test_save_extracted_text_handles_db_error(self, extractor):
        """Test saving extracted text handles database errors"""
        document_id = uuid4()
        result = TextExtractionResult(
            success=True,
            full_text="Sample text",
            text_length=11,
            extraction_method="docling",
            extraction_engine="native",
            extraction_quality=0.9,
        )

        # Mock database session that raises exception
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.commit.side_effect = Exception("Database error")

        document_text = await extractor.save_extracted_text(
            db=mock_db,
            document_id=document_id,
            result=result,
        )

        # Should return None on error
        assert document_text is None
        mock_db.rollback.assert_called_once()


class TestGetTextExtractor:
    """Test get_text_extractor singleton"""

    def test_get_text_extractor_returns_instance(self):
        """Test get_text_extractor returns DocumentTextExtractor instance"""
        # Reset global instance
        import app.services.extraction.text_extraction_service as service
        service._text_extractor = None

        extractor = get_text_extractor()
        assert extractor is not None
        assert isinstance(extractor, DocumentTextExtractor)

    def test_get_text_extractor_singleton(self):
        """Test get_text_extractor returns same instance"""
        # Reset global instance
        import app.services.extraction.text_extraction_service as service
        service._text_extractor = None

        extractor1 = get_text_extractor()
        extractor2 = get_text_extractor()

        # Should return the same instance
        assert extractor1 is extractor2
