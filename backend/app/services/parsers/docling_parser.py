"""
Docling document parser implementation.

Wraps the existing Docling extraction logic in the DocumentParser interface.
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

from app.services.parsers.base import DocumentParser, ParseResult

logger = logging.getLogger(__name__)


class DoclingParser(DocumentParser):
    """
    Docling-based document parser.

    Features:
    - Smart OCR fallback (only OCRs pages when needed)
    - Multiple format support (PDF, DOCX, PPTX, HTML, Markdown)
    - Quality assessment
    - Language detection
    - Fallback to PyPDF2 for PDFs if Docling unavailable
    - Direct text extraction for .md, .txt files
    """

    SUPPORTED_FORMATS = [
        "pdf", "docx", "pptx", "html", "htm",
        "md", "markdown", "txt", "rst", "text"
    ]

    def __init__(self):
        super().__init__(name="docling")
        self.converter = None
        # Lazy initialization - only load Docling when actually needed

    def supports_format(self, file_extension: str) -> bool:
        """Check if Docling supports this file format."""
        return file_extension.lower() in self.SUPPORTED_FORMATS

    def parse(self, file_path: str, **kwargs) -> ParseResult:
        """
        Parse document using Docling.

        Args:
            file_path: Path to the document
            **kwargs: Optional parameters:
                - mime_type: MIME type hint
                - enable_ocr: Force OCR on/off (default: auto)

        Returns:
            ParseResult with extracted text and metadata
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Validate file exists
            self.validate_file(file_path)

            # Get file info
            file_extension = self.get_file_extension(file_path)
            mime_type = kwargs.get("mime_type", "")

            # Check if this is a text file (direct extraction)
            if self._is_text_file(file_extension, mime_type):
                logger.info(f"Using direct text extraction for {file_extension} file")
                return self._extract_text_file(file_path, start_time)

            # Initialize Docling converter if needed
            if not self.converter:
                self._initialize_converter()

            # If Docling not available and this is a PDF, fall back to PyPDF2
            if not self.converter and file_extension == "pdf":
                logger.warning("Docling not available, falling back to PyPDF2")
                return self._extract_with_pypdf2(file_path, start_time)

            # If still no converter, fail
            if not self.converter:
                raise Exception(
                    f"Docling converter not available and no fallback for {file_extension}"
                )

            # Use Docling to convert the document
            logger.info(f"Starting Docling extraction for {file_extension} file")
            result = self.converter.convert(file_path)

            # Extract text in markdown format
            full_text = result.document.export_to_markdown()

            # Calculate metrics
            text_length = len(full_text)
            pages_with_ocr = self._count_ocr_pages(result)
            total_pages = self._count_total_pages(result)
            confidence = self._assess_quality(full_text, pages_with_ocr, total_pages)
            language = self._detect_language(full_text)

            # Determine extraction method
            if pages_with_ocr > 0:
                extraction_method = "docling_ocr"
                extraction_engine = "easyocr"
            else:
                extraction_method = "docling"
                extraction_engine = "native"

            # Calculate duration
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Extract images and tables metadata
            images = self._extract_images_metadata(result)
            tables = self._extract_tables_metadata(result)

            logger.info(
                f"Docling extraction completed: {text_length} chars, "
                f"{pages_with_ocr}/{total_pages} pages with OCR, {duration_ms}ms"
            )

            return ParseResult(
                text=full_text,
                metadata={
                    "extraction_method": extraction_method,
                    "extraction_engine": extraction_engine,
                    "text_length": text_length,
                    "pages_with_ocr": pages_with_ocr,
                    "total_pages": total_pages,
                    "extraction_duration_ms": duration_ms,
                    "detected_language": language,
                    "file_extension": file_extension,
                },
                confidence=confidence,
                images=images,
                tables=tables
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.error(f"Docling parsing failed: {e}", exc_info=True)

            return ParseResult(
                text="",
                metadata={
                    "extraction_method": "failed",
                    "extraction_duration_ms": duration_ms,
                },
                confidence=0.0,
                error=str(e)
            )

    def _initialize_converter(self):
        """Initialize Docling converter with OCR enabled."""
        try:
            # CRITICAL: Force disable MPS at multiple levels
            import os
            os.environ['PYTORCH_ENABLE_MPS'] = '0'
            os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
            os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

            # Monkey-patch torch to disable MPS detection
            import torch
            if hasattr(torch.backends, 'mps'):
                torch.backends.mps.is_available = lambda: False
                torch.backends.mps.is_built = lambda: False
                logger.info("Force-disabled MPS (Apple Silicon workaround)")

            # Import Docling dependencies
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions

            # Configure PDF pipeline
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True  # Smart OCR fallback
            pipeline_options.do_table_structure = True  # Extract tables

            # Create converter
            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )

            logger.info("Docling converter initialized with OCR support")

        except Exception as e:
            logger.error(f"Failed to initialize Docling converter: {e}")
            self.converter = None

    def _is_text_file(self, file_extension: str, mime_type: str) -> bool:
        """Check if this is a plain text file."""
        text_extensions = ['md', 'txt', 'markdown', 'rst', 'text']
        text_mime_types = ['text/markdown', 'text/plain', 'text/x-markdown']

        return (
            file_extension in text_extensions or
            mime_type in text_mime_types
        )

    def _extract_text_file(self, file_path: str, start_time: datetime) -> ParseResult:
        """Direct text extraction for text-based files."""
        try:
            # Try multiple encodings
            full_text = ""
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        full_text = f.read()
                    logger.info(f"Successfully read file with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    if encoding == encodings[-1]:
                        raise
                    continue

            # Calculate metrics
            text_length = len(full_text)
            confidence = self._assess_quality(full_text, 0, 1)
            language = self._detect_language(full_text)

            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.info(f"Direct text extraction completed: {text_length} chars, {duration_ms}ms")

            return ParseResult(
                text=full_text,
                metadata={
                    "extraction_method": "direct",
                    "extraction_engine": "python_io",
                    "text_length": text_length,
                    "pages_with_ocr": 0,
                    "total_pages": 1,
                    "extraction_duration_ms": duration_ms,
                    "detected_language": language,
                },
                confidence=confidence
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.error(f"Direct text extraction failed: {e}", exc_info=True)

            return ParseResult(
                text="",
                metadata={
                    "extraction_method": "direct_failed",
                    "extraction_duration_ms": duration_ms,
                },
                confidence=0.0,
                error=str(e)
            )

    def _extract_with_pypdf2(self, file_path: str, start_time: datetime) -> ParseResult:
        """Fallback PDF extraction using PyPDF2."""
        try:
            import PyPDF2

            logger.info("Starting PyPDF2 extraction")

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
            confidence = self._assess_quality(full_text, 0, total_pages)
            language = self._detect_language(full_text)

            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.info(
                f"PyPDF2 extraction completed: {text_length} chars, "
                f"{total_pages} pages, {duration_ms}ms"
            )

            return ParseResult(
                text=full_text,
                metadata={
                    "extraction_method": "pypdf2",
                    "extraction_engine": "pypdf2",
                    "text_length": text_length,
                    "pages_with_ocr": 0,
                    "total_pages": total_pages,
                    "extraction_duration_ms": duration_ms,
                    "detected_language": language,
                },
                confidence=confidence
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.error(f"PyPDF2 extraction failed: {e}", exc_info=True)

            return ParseResult(
                text="",
                metadata={
                    "extraction_method": "pypdf2_failed",
                    "extraction_duration_ms": duration_ms,
                },
                confidence=0.0,
                error=str(e)
            )

    def _count_ocr_pages(self, result) -> int:
        """Count pages that required OCR."""
        try:
            ocr_count = 0
            if hasattr(result, "pages"):
                for page in result.pages:
                    if hasattr(page, "ocr_applied") and page.ocr_applied:
                        ocr_count += 1
            return ocr_count
        except Exception:
            return 0

    def _count_total_pages(self, result) -> int:
        """Count total pages in document."""
        try:
            if hasattr(result, "pages"):
                return len(result.pages)
            if hasattr(result.document, "pages"):
                return len(result.document.pages)
            return 1
        except Exception:
            return 1

    def _assess_quality(self, text: str, pages_with_ocr: int, total_pages: int) -> float:
        """
        Assess extraction quality (0.0 - 1.0).

        Factors:
        - Text length (longer is better)
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
            if 3 < avg_word_length < 10:
                quality_score += 0.15

        punct_count = sum(1 for char in text if char in ".,!?;:")
        if punct_count > len(text) * 0.01:
            quality_score += 0.15

        return min(quality_score, 1.0)

    def _detect_language(self, text: str) -> Optional[str]:
        """Basic language detection."""
        if not text or len(text) < 100:
            return None

        text_lower = text.lower()

        # Simple heuristic based on common English words
        english_words = ["the", "and", "is", "to", "a", "in", "that", "have", "i", "it"]
        english_score = sum(1 for word in english_words if f" {word} " in text_lower)

        if english_score >= 3:
            return "en"

        return "en"  # Default to English

    def _extract_images_metadata(self, result) -> list:
        """Extract metadata about images in the document."""
        images = []
        try:
            if hasattr(result.document, "pictures"):
                for i, picture in enumerate(result.document.pictures):
                    images.append({
                        "index": i,
                        "type": "image",
                        "caption": getattr(picture, "caption", ""),
                    })
        except Exception as e:
            logger.debug(f"Could not extract image metadata: {e}")

        return images

    def _extract_tables_metadata(self, result) -> list:
        """Extract metadata about tables in the document."""
        tables = []
        try:
            if hasattr(result.document, "tables"):
                for i, table in enumerate(result.document.tables):
                    tables.append({
                        "index": i,
                        "type": "table",
                        "rows": getattr(table, "num_rows", 0),
                        "cols": getattr(table, "num_cols", 0),
                    })
        except Exception as e:
            logger.debug(f"Could not extract table metadata: {e}")

        return tables
