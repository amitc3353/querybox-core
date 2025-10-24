"""
Text Extraction Service using Docling
Extracts full text from documents with smart OCR fallback
"""
# CRITICAL: Disable MPS BEFORE any imports (Apple Silicon fix)
import os
os.environ['PYTORCH_ENABLE_MPS'] = '0'
os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.document_text import DocumentText
from app.models.document import Document


logger = logging.getLogger(__name__)


class TextExtractionResult:
    """Result of text extraction operation"""

    def __init__(
        self,
        success: bool,
        full_text: str = "",
        text_length: int = 0,
        extraction_method: str = "unknown",
        extraction_engine: str = "unknown",
        extraction_quality: float = 0.0,
        pages_with_ocr: int = 0,
        total_pages: int = 0,
        extraction_duration_ms: int = 0,
        detected_language: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.full_text = full_text
        self.text_length = text_length
        self.extraction_method = extraction_method
        self.extraction_engine = extraction_engine
        self.extraction_quality = extraction_quality
        self.pages_with_ocr = pages_with_ocr
        self.total_pages = total_pages
        self.extraction_duration_ms = extraction_duration_ms
        self.detected_language = detected_language
        self.error_message = error_message


class DocumentTextExtractor:
    """
    Docling-based text extraction service

    Features:
    - Smart OCR fallback (only OCRs pages when needed)
    - Multiple format support (PDF, DOCX, PPTX, HTML, Markdown)
    - Quality assessment
    - Language detection
    """

    def __init__(self):
        self.converter = None
        # Don't initialize immediately - do it lazily when needed

    def _initialize_converter(self):
        """Initialize Docling converter with OCR enabled"""
        try:
            # CRITICAL: Force disable MPS at multiple levels (Apple Silicon fix)
            import os
            os.environ['PYTORCH_ENABLE_MPS'] = '0'
            os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
            os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

            # Monkey-patch torch to disable MPS detection completely
            import torch
            if hasattr(torch.backends, 'mps'):
                # Override is_available to always return False
                original_is_available = torch.backends.mps.is_available
                torch.backends.mps.is_available = lambda: False
                torch.backends.mps.is_built = lambda: False
                logger.info("Force-disabled MPS via monkey-patch (Apple Silicon Celery workaround)")

            # Lazy import docling dependencies (only when actually needed)
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions

            # Configure PDF pipeline with OCR support
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True  # Enable smart OCR fallback
            pipeline_options.do_table_structure = True  # Extract table structure

            # Create converter with PDF format options
            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )

            logger.info("Docling converter initialized with OCR support")

        except Exception as e:
            logger.error(f"Failed to initialize Docling converter: {e}")
            self.converter = None

    async def extract_text(
        self,
        file_path: str,
        document_id: UUID,
        mime_type: str,
    ) -> TextExtractionResult:
        """
        Extract text from document using Docling

        Args:
            file_path: Path to document file
            document_id: Document UUID for tracking
            mime_type: MIME type of document

        Returns:
            TextExtractionResult with extraction details
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Check if file exists
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Document file not found: {file_path}")

            if not self.converter:
                self._initialize_converter()

            # If Docling not available, fall back to PyPDF2 for PDF files
            if not self.converter and mime_type == "application/pdf":
                logger.warning(f"Docling not available, falling back to PyPDF2 for document {document_id}")
                return await self._extract_with_pypdf2(file_path, document_id, start_time)

            if not self.converter:
                raise Exception("Docling converter not available and no fallback for this file type")

            logger.info(f"Starting text extraction for document {document_id} ({mime_type})")

            # Convert document to Docling format
            result = self.converter.convert(file_path)

            # Extract text from result
            full_text = result.document.export_to_markdown()

            # Calculate extraction metrics
            text_length = len(full_text)
            pages_with_ocr = self._count_ocr_pages(result)
            total_pages = self._count_total_pages(result)
            extraction_quality = self._assess_quality(full_text, pages_with_ocr, total_pages)
            detected_language = self._detect_language(full_text)

            # Determine extraction method
            if pages_with_ocr > 0:
                extraction_method = "docling_ocr"
                extraction_engine = "easyocr"  # Docling default
            else:
                extraction_method = "docling"
                extraction_engine = "native"

            # Calculate duration
            end_time = datetime.now(timezone.utc)
            extraction_duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.info(
                f"Text extraction completed for document {document_id}: "
                f"{text_length} chars, {pages_with_ocr}/{total_pages} pages with OCR, "
                f"{extraction_duration_ms}ms"
            )

            return TextExtractionResult(
                success=True,
                full_text=full_text,
                text_length=text_length,
                extraction_method=extraction_method,
                extraction_engine=extraction_engine,
                extraction_quality=extraction_quality,
                pages_with_ocr=pages_with_ocr,
                total_pages=total_pages,
                extraction_duration_ms=extraction_duration_ms,
                detected_language=detected_language,
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            extraction_duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.error(f"Text extraction failed for document {document_id}: {e}", exc_info=True)

            return TextExtractionResult(
                success=False,
                extraction_duration_ms=extraction_duration_ms,
                error_message=str(e),
            )

    def _count_ocr_pages(self, result) -> int:
        """Count pages that required OCR"""
        try:
            # Docling provides OCR information in page metadata
            ocr_count = 0
            if hasattr(result, "pages"):
                for page in result.pages:
                    if hasattr(page, "ocr_applied") and page.ocr_applied:
                        ocr_count += 1
            return ocr_count
        except Exception:
            return 0

    def _count_total_pages(self, result) -> int:
        """Count total pages in document"""
        try:
            if hasattr(result, "pages"):
                return len(result.pages)
            if hasattr(result.document, "pages"):
                return len(result.document.pages)
            return 1  # Default to 1 page if unknown
        except Exception:
            return 1

    def _assess_quality(self, text: str, pages_with_ocr: int, total_pages: int) -> float:
        """
        Assess extraction quality (0.0 - 1.0)

        Factors:
        - Text length (longer is generally better)
        - OCR ratio (lower is better - native extraction is more reliable)
        - Text characteristics (word/char ratio, punctuation)
        """
        if not text:
            return 0.0

        quality_score = 0.0

        # Factor 1: Text length (max 0.3)
        if len(text) > 1000:
            quality_score += 0.3
        elif len(text) > 100:
            quality_score += 0.15

        # Factor 2: OCR ratio (max 0.4)
        if total_pages > 0:
            ocr_ratio = pages_with_ocr / total_pages
            quality_score += (1.0 - ocr_ratio) * 0.4

        # Factor 3: Text characteristics (max 0.3)
        words = text.split()
        if words:
            avg_word_length = sum(len(word) for word in words) / len(words)
            if 3 < avg_word_length < 10:  # Reasonable word length
                quality_score += 0.15

        punct_count = sum(1 for char in text if char in ".,!?;:")
        if punct_count > len(text) * 0.01:  # At least 1% punctuation
            quality_score += 0.15

        return min(quality_score, 1.0)

    def _detect_language(self, text: str) -> Optional[str]:
        """Basic language detection"""
        if not text or len(text) < 100:
            return None

        text_lower = text.lower()

        # Simple heuristic based on common words
        english_words = ["the", "and", "is", "to", "a", "in", "that", "have", "i", "it"]
        english_score = sum(1 for word in english_words if f" {word} " in text_lower)

        if english_score >= 3:
            return "en"

        return "en"  # Default to English

    async def _extract_with_pypdf2(
        self,
        file_path: str,
        document_id: UUID,
        start_time: datetime
    ) -> TextExtractionResult:
        """
        Fallback PDF extraction using PyPDF2

        Args:
            file_path: Path to PDF file
            document_id: Document UUID for tracking
            start_time: Extraction start time

        Returns:
            TextExtractionResult with extraction details
        """
        try:
            import PyPDF2

            logger.info(f"Starting PyPDF2 extraction for document {document_id}")

            full_text = ""
            total_pages = 0

            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)

                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        text = page.extract_text()
                        if text:
                            full_text += f"\n--- Page {page_num} ---\n{text}"
                    except Exception as page_error:
                        logger.warning(f"Failed to extract page {page_num}: {page_error}")
                        continue

            # Calculate metrics
            text_length = len(full_text)
            extraction_quality = self._assess_quality(full_text, 0, total_pages)
            detected_language = self._detect_language(full_text)

            # Calculate duration
            end_time = datetime.now(timezone.utc)
            extraction_duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.info(
                f"PyPDF2 extraction completed for document {document_id}: "
                f"{text_length} chars, {total_pages} pages, {extraction_duration_ms}ms"
            )

            return TextExtractionResult(
                success=True,
                full_text=full_text,
                text_length=text_length,
                extraction_method="pypdf2",
                extraction_engine="pypdf2",
                extraction_quality=extraction_quality,
                pages_with_ocr=0,
                total_pages=total_pages,
                extraction_duration_ms=extraction_duration_ms,
                detected_language=detected_language,
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            extraction_duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.error(f"PyPDF2 extraction failed for document {document_id}: {e}", exc_info=True)

            return TextExtractionResult(
                success=False,
                extraction_duration_ms=extraction_duration_ms,
                error_message=f"PyPDF2 extraction failed: {str(e)}",
            )

    async def save_extracted_text(
        self,
        db: Session,
        document_id: UUID,
        result: TextExtractionResult,
    ) -> Optional[DocumentText]:
        """
        Save extracted text to database

        Args:
            db: Database session
            document_id: Document UUID
            result: Extraction result

        Returns:
            DocumentText instance if successful, None otherwise
        """
        try:
            # Check if text already exists (update scenario)
            existing = db.query(DocumentText).filter(
                DocumentText.document_id == document_id
            ).first()

            if existing:
                # Update existing record
                existing.full_text = result.full_text
                existing.text_length = result.text_length
                existing.extraction_method = result.extraction_method
                existing.extraction_engine = result.extraction_engine
                existing.extraction_quality = result.extraction_quality
                existing.pages_with_ocr = result.pages_with_ocr
                existing.total_pages = result.total_pages
                existing.extraction_duration_ms = result.extraction_duration_ms
                existing.detected_language = result.detected_language
                existing.extracted_at = datetime.now(timezone.utc)

                db.commit()
                db.refresh(existing)

                logger.info(f"Updated extracted text for document {document_id}")
                return existing

            else:
                # Create new record
                document_text = DocumentText(
                    document_id=document_id,
                    full_text=result.full_text,
                    text_length=result.text_length,
                    extraction_method=result.extraction_method,
                    extraction_engine=result.extraction_engine,
                    extraction_quality=result.extraction_quality,
                    pages_with_ocr=result.pages_with_ocr,
                    total_pages=result.total_pages,
                    extraction_duration_ms=result.extraction_duration_ms,
                    detected_language=result.detected_language,
                    extracted_at=datetime.now(timezone.utc),
                )

                db.add(document_text)
                db.commit()
                db.refresh(document_text)

                # Update document's last_extraction_at timestamp
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    document.last_extraction_at = datetime.now(timezone.utc)
                    db.commit()

                logger.info(f"Saved extracted text for document {document_id}")
                return document_text

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save extracted text for document {document_id}: {e}")
            return None


# Global extractor instance
_text_extractor: Optional[DocumentTextExtractor] = None


def get_text_extractor() -> DocumentTextExtractor:
    """Get or create global text extractor instance"""
    global _text_extractor
    if _text_extractor is None:
        _text_extractor = DocumentTextExtractor()
    return _text_extractor
