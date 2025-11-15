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
from app.services.parsers.factory import get_parser
from app.services.parsers.base import DocumentParser


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
    Modular text extraction service using factory pattern

    Features:
    - Parser selection via configuration (Docling, MinerU, etc.)
    - Smart OCR fallback (parser-dependent)
    - Multiple format support (PDF, DOCX, PPTX, HTML, Markdown)
    - Quality assessment
    - Language detection
    """

    def __init__(self, parser: Optional[DocumentParser] = None):
        """
        Initialize text extractor

        Args:
            parser: Optional parser instance. If None, uses factory to get default parser.
        """
        self.parser = parser
        # Backward compatibility: tests expect 'converter' attribute
        self.converter = None
        # Don't initialize parser immediately - do it lazily when needed

    def _get_parser(self) -> DocumentParser:
        """Get or initialize parser instance"""
        if self.parser is None:
            self.parser = get_parser()
            logger.info(f"Initialized parser: {type(self.parser).__name__}")
        return self.parser

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

            # Handle text-based files directly (markdown, txt, etc.)
            file_extension = Path(file_path).suffix.lower()
            text_extensions = ['.md', '.txt', '.markdown', '.rst', '.text']
            text_mime_types = ['text/markdown', 'text/plain', 'text/x-markdown', 'application/octet-stream']

            if file_extension in text_extensions or mime_type in text_mime_types:
                # For text files, check extension takes precedence
                if file_extension in text_extensions:
                    logger.info(f"Using direct text extraction for {file_extension} file: {document_id}")
                    return await self._extract_text_file(file_path, document_id, start_time)
                # If MIME is text-based but extension is unknown, still try direct read
                elif mime_type in ['text/markdown', 'text/plain', 'text/x-markdown']:
                    logger.info(f"Using direct text extraction for {mime_type} file: {document_id}")
                    return await self._extract_text_file(file_path, document_id, start_time)

            # Backward compatibility: Check if tests are using converter directly
            if self.converter is not None:
                # Tests have set converter directly, use it instead of parser
                logger.info(f"Starting text extraction for document {document_id} ({mime_type}) using converter (test mode)")
                result = self.converter.convert(file_path)

                # Extract text and metadata from result
                full_text = result.document.export_to_markdown()
                text_length = len(full_text)
                pages_with_ocr = self._count_ocr_pages(result)
                total_pages = self._count_total_pages(result)
                extraction_quality = self._assess_quality(full_text, pages_with_ocr, total_pages)
                detected_language = self._detect_language(full_text)

                # Determine extraction method
                if pages_with_ocr > 0:
                    extraction_method = "docling_ocr"
                    extraction_engine = "easyocr"
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

            # Get parser from factory (lazy initialization)
            parser = self._get_parser()

            # Verify parser was initialized successfully
            if parser is None:
                raise Exception("Text extraction service not available")

            logger.info(f"Starting text extraction for document {document_id} ({mime_type}) using {type(parser).__name__}")

            # Use parser to extract text
            parse_result = parser.parse(file_path)

            if parse_result.error:
                # Parser failed, try PyPDF2 fallback for PDFs
                if mime_type == "application/pdf":
                    logger.warning(f"Parser failed, falling back to PyPDF2 for document {document_id}: {parse_result.error}")
                    return await self._extract_with_pypdf2(file_path, document_id, start_time)
                else:
                    raise Exception(f"Parser failed: {parse_result.error}")

            # Extract text and metadata from parse result
            full_text = parse_result.text
            metadata = parse_result.metadata

            # Calculate extraction metrics
            text_length = len(full_text)
            pages_with_ocr = metadata.get("pages_with_ocr", 0)
            total_pages = metadata.get("total_pages", 1)
            extraction_quality = parse_result.confidence
            detected_language = metadata.get("language", self._detect_language(full_text))

            # Determine extraction method from metadata
            extraction_method = metadata.get("extraction_method", "parser")
            extraction_engine = metadata.get("extraction_engine", type(parser).__name__.lower())

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

    def _count_ocr_pages(self, result) -> int:
        """
        Count pages with OCR applied (backward compatibility for tests)

        Args:
            result: Docling conversion result

        Returns:
            Number of pages with OCR applied
        """
        try:
            if hasattr(result, 'pages'):
                return sum(1 for page in result.pages if hasattr(page, 'ocr_applied') and page.ocr_applied)
            return 0
        except Exception:
            return 0

    def _count_total_pages(self, result) -> int:
        """
        Count total pages (backward compatibility for tests)

        Args:
            result: Docling conversion result

        Returns:
            Total number of pages
        """
        try:
            if hasattr(result, 'pages'):
                return len(result.pages)
            return 1
        except Exception:
            return 1

    def _initialize_converter(self):
        """
        Initialize converter (backward compatibility for tests)
        This is a no-op in the new implementation
        """
        pass

    async def _extract_text_file(
        self,
        file_path: str,
        document_id: UUID,
        start_time: datetime
    ) -> TextExtractionResult:
        """
        Direct text extraction for text-based files (markdown, txt, etc.)

        Args:
            file_path: Path to text file
            document_id: Document UUID for tracking
            start_time: Extraction start time

        Returns:
            TextExtractionResult with extraction details
        """
        try:
            logger.info(f"Starting direct text extraction for document {document_id}")

            # Read file with common encodings
            full_text = ""
            encoding_attempts = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

            for encoding in encoding_attempts:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        full_text = f.read()
                    logger.info(f"Successfully read file with {encoding} encoding")
                    break
                except UnicodeDecodeError:
                    if encoding == encoding_attempts[-1]:
                        # Last attempt failed
                        raise
                    continue

            # Calculate metrics
            text_length = len(full_text)
            total_pages = 1  # Text files are single-page
            extraction_quality = self._assess_quality(full_text, 0, total_pages)
            detected_language = self._detect_language(full_text)

            # Calculate duration
            end_time = datetime.now(timezone.utc)
            extraction_duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.info(
                f"Direct text extraction completed for document {document_id}: "
                f"{text_length} chars, {extraction_duration_ms}ms"
            )

            return TextExtractionResult(
                success=True,
                full_text=full_text,
                text_length=text_length,
                extraction_method="direct",
                extraction_engine="python_io",
                extraction_quality=extraction_quality,
                pages_with_ocr=0,
                total_pages=total_pages,
                extraction_duration_ms=extraction_duration_ms,
                detected_language=detected_language,
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            extraction_duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.error(f"Direct text extraction failed for document {document_id}: {e}", exc_info=True)

            return TextExtractionResult(
                success=False,
                extraction_duration_ms=extraction_duration_ms,
                error_message=f"Direct text extraction failed: {str(e)}",
            )

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
            # Clean text: Remove NULL bytes (PostgreSQL doesn't allow them)
            cleaned_text = result.full_text.replace('\x00', '') if result.full_text else ''

            # Check if text already exists (update scenario)
            existing = db.query(DocumentText).filter(
                DocumentText.document_id == document_id
            ).first()

            if existing:
                # Update existing record
                existing.full_text = cleaned_text
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
                    full_text=cleaned_text,
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
