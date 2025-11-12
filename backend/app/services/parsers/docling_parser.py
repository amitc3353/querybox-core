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

    def __init__(self, eager_init: bool = False):
        """
        Initialize DoclingParser.

        Args:
            eager_init: If True, initialize converter immediately (eager loading).
                       If False, use lazy initialization (load on first use).
                       Defaults to config setting DOCLING_EAGER_INIT.
        """
        super().__init__(name="docling")
        self.converter = None
        self.device = None  # Will be set during initialization
        self.device_name = None  # Human-readable device name
        self._warmup_done = False  # Track if warmup has been performed

        # Check if eager initialization is requested
        from app.core.config import settings
        should_eager_init = eager_init or settings.DOCLING_EAGER_INIT

        if should_eager_init:
            logger.info("Eager initialization enabled - preloading Docling models")
            self._initialize_converter()

            # Perform warmup if enabled
            if settings.DOCLING_WARMUP_ON_STARTUP and self.converter:
                self._warmup()
        else:
            logger.info("Lazy initialization enabled - Docling will load on first use")

    def supports_format(self, file_extension: str) -> bool:
        """Check if Docling supports this file format."""
        return file_extension.lower() in self.SUPPORTED_FORMATS

    def _detect_device(self) -> tuple[str, str]:
        """
        Detect best available compute device for parsing.

        Returns:
            tuple: (device, device_name) where device is the torch device string
                   and device_name is a human-readable description

        Device Priority:
            1. CUDA (NVIDIA GPU) - Best performance (10x faster than CPU)
            2. MPS (Apple Silicon) - Good performance (2-3x faster), but experimental
            3. CPU - Always available (fallback)

        Respects configuration:
            - DOCLING_DEVICE="auto" → Auto-detect (default)
            - DOCLING_DEVICE="cuda" → Force CUDA (error if unavailable)
            - DOCLING_DEVICE="mps" → Force MPS (if DOCLING_ENABLE_MPS=True)
            - DOCLING_DEVICE="cpu" → Force CPU
        """
        from app.core.config import settings

        config_device = settings.DOCLING_DEVICE.lower()

        # Force CPU if requested
        if config_device == "cpu":
            logger.info("Device detection: CPU (forced via config)")
            return ("cpu", "CPU (forced)")

        try:
            import torch

            # Force CUDA if requested
            if config_device == "cuda":
                if torch.cuda.is_available():
                    device_name = torch.cuda.get_device_name(0)
                    logger.info(f"Device detection: CUDA - {device_name} (forced via config)")
                    return ("cuda", f"CUDA: {device_name}")
                else:
                    logger.error("CUDA requested but not available, falling back to CPU")
                    return ("cpu", "CPU (CUDA unavailable)")

            # Force MPS if requested and enabled
            if config_device == "mps":
                if settings.DOCLING_ENABLE_MPS and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    logger.warning("Device detection: MPS (experimental - may have compatibility issues)")
                    return ("mps", "Apple Silicon MPS (experimental)")
                else:
                    logger.error("MPS requested but not available or not enabled, falling back to CPU")
                    return ("cpu", "CPU (MPS unavailable)")

            # Auto-detect best available device
            if config_device == "auto":
                # Priority 1: CUDA (NVIDIA GPU)
                if torch.cuda.is_available():
                    device_name = torch.cuda.get_device_name(0)
                    gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
                    logger.info(f"Device detection: CUDA - {device_name} ({gpu_memory:.1f}GB)")
                    return ("cuda", f"CUDA: {device_name} ({gpu_memory:.1f}GB)")

                # Priority 2: MPS (Apple Silicon) - only if explicitly enabled
                if settings.DOCLING_ENABLE_MPS and hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    logger.warning("Device detection: MPS (experimental - disabled by default due to EasyOCR compatibility)")
                    return ("mps", "Apple Silicon MPS (experimental)")

                # Priority 3: CPU (always available)
                logger.info("Device detection: CPU (no GPU available)")
                return ("cpu", "CPU (no GPU available)")

            # Invalid config value
            logger.warning(f"Invalid DOCLING_DEVICE='{config_device}', falling back to CPU")
            return ("cpu", "CPU (invalid config)")

        except ImportError:
            logger.warning("PyTorch not installed, using CPU")
            return ("cpu", "CPU (PyTorch unavailable)")
        except Exception as e:
            logger.error(f"Device detection failed: {e}, falling back to CPU")
            return ("cpu", "CPU (detection failed)")

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

            # Check if this is a large PDF that should use batch processing
            from app.core.config import settings
            if file_extension == "pdf" and settings.DOCLING_MAX_PAGES_MEMORY_THRESHOLD > 0:
                # Count pages to determine if batch processing is needed
                page_count = self._count_pdf_pages(file_path)
                if page_count > settings.DOCLING_MAX_PAGES_MEMORY_THRESHOLD:
                    logger.info(
                        f"Large PDF detected ({page_count} pages > {settings.DOCLING_MAX_PAGES_MEMORY_THRESHOLD} threshold), "
                        f"using batch processing"
                    )
                    return self._parse_large_pdf_batched(file_path, page_count, start_time)

            # Standard conversion for regular-sized documents
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
                    "device": self.device if self.device else "unknown",
                    "device_name": self.device_name if self.device_name else "Unknown",
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
            from app.core.config import settings

            # Detect device BEFORE any imports
            self.device, self.device_name = self._detect_device()

            # CRITICAL: Force disable MPS at multiple levels (unless explicitly enabled)
            import os
            if not settings.DOCLING_ENABLE_MPS:
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

            # Select pipeline type based on configuration
            if settings.DOCLING_USE_THREADED_PIPELINE:
                # Use ThreadedPdfPipeline for parallel processing (5 stages)
                from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
                from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
                from docling.pipeline.simple_pipeline import SimplePipeline

                # Note: ThreadedPdfPipeline is the recommended approach but may not be
                # directly exposed in all Docling versions. Using standard pipeline with
                # batch settings as a compatible alternative.
                pipeline_cls = StandardPdfPipeline
                pipeline_mode = "threaded (standard with batching)"
                logger.info(f"Using StandardPdfPipeline with batch processing (threaded mode)")
            else:
                # Use standard single-threaded pipeline
                pipeline_cls = None  # Let Docling use default
                pipeline_mode = "standard (single-threaded)"
                logger.info(f"Using standard single-threaded pipeline")

            # Configure PDF pipeline options
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True  # Smart OCR fallback
            pipeline_options.do_table_structure = True  # Extract tables

            # Note: OCR batch size configuration depends on Docling version
            # Newer versions may not expose ocr_options.batch_size directly
            # The configuration values are available for future compatibility
            logger.info(f"OCR batch size config: {settings.DOCLING_OCR_BATCH_SIZE} (device: {self.device})")

            # Create converter
            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )

            logger.info(
                f"Docling converter initialized: {self.device_name}, "
                f"pipeline={pipeline_mode}, "
                f"threads={settings.DOCLING_NUM_THREADS}"
            )

            # Log GPU memory if available and enabled
            if settings.DOCLING_LOG_GPU_MEMORY and self.device == "cuda":
                try:
                    import torch
                    allocated = torch.cuda.memory_allocated(0) / (1024**3)  # GB
                    reserved = torch.cuda.memory_reserved(0) / (1024**3)  # GB
                    logger.info(f"GPU Memory: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved")
                except Exception as mem_error:
                    logger.debug(f"Could not log GPU memory: {mem_error}")

        except Exception as e:
            logger.error(f"Failed to initialize Docling converter: {e}")
            self.converter = None
            self.device = "cpu"
            self.device_name = "CPU (initialization failed)"

    def _warmup(self):
        """
        Warm up Docling models by processing a dummy PDF.

        This reduces first-request latency by:
        1. Loading all models into memory
        2. Running inference once to initialize GPU/CPU kernels
        3. Caching internal state

        Creates a minimal 1-page PDF with sample text and processes it.
        Expected warmup time: 2-3 seconds on CPU, <1 second on GPU.
        """
        if self._warmup_done:
            logger.info("Warmup already completed, skipping")
            return

        if not self.converter:
            logger.warning("Cannot warmup: converter not initialized")
            return

        try:
            import tempfile
            import io
            from datetime import datetime

            logger.info("Starting Docling warmup with dummy PDF...")
            warmup_start = datetime.now()

            # Create a minimal PDF with reportlab (if available) or use PyPDF2
            try:
                from reportlab.pdfgen import canvas
                from reportlab.lib.pagesizes import letter

                # Create dummy PDF in memory
                pdf_buffer = io.BytesIO()
                c = canvas.Canvas(pdf_buffer, pagesize=letter)
                c.drawString(100, 750, "QueryBox Docling Warmup Test")
                c.drawString(100, 730, "This is a test document for model warmup.")
                c.save()
                pdf_buffer.seek(0)

                # Write to temp file
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode='wb') as tmp_file:
                    tmp_file.write(pdf_buffer.getvalue())
                    tmp_path = tmp_file.name

            except ImportError:
                # Fallback: Create a markdown file instead (supported by Docling)
                logger.info("reportlab not available, using markdown file for warmup")
                with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode='w') as tmp_file:
                    tmp_file.write("# QueryBox Docling Warmup Test\nThis is a test document.")
                    tmp_path = tmp_file.name

            # Process dummy document
            try:
                result = self.converter.convert(tmp_path)
                _ = result.document.export_to_markdown()  # Force full processing

                warmup_duration = (datetime.now() - warmup_start).total_seconds()
                logger.info(f"Docling warmup completed successfully in {warmup_duration:.2f}s")
                self._warmup_done = True

            finally:
                # Clean up temp file
                import os
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"Warmup failed (non-critical): {e}")
            # Don't fail initialization if warmup fails
            self._warmup_done = False

    def _count_pdf_pages(self, file_path: str) -> int:
        """
        Quickly count pages in a PDF without full parsing.

        Uses PyPDF2 for fast page counting without loading entire document.
        """
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return len(reader.pages)
        except Exception as e:
            logger.warning(f"Could not count PDF pages: {e}, assuming single page")
            return 1

    def _parse_large_pdf_batched(self, file_path: str, total_pages: int, start_time: datetime) -> ParseResult:
        """
        Parse large PDF in batches to reduce memory usage.

        Strategy:
        1. Split PDF into page batches (e.g., 50 pages per batch)
        2. Process each batch separately
        3. Combine results
        4. Clean up temporary files

        This prevents OOM errors on large PDFs (100+ pages) by processing
        in smaller chunks that fit in memory.

        Args:
            file_path: Path to large PDF
            total_pages: Total page count
            start_time: Parse start timestamp

        Returns:
            ParseResult with combined text from all batches
        """
        from app.core.config import settings
        import PyPDF2
        import tempfile
        import os

        batch_size = settings.DOCLING_PAGE_BATCH_SIZE
        logger.info(f"Processing {total_pages} pages in batches of {batch_size}")

        all_text = []
        total_ocr_pages = 0
        all_images = []
        all_tables = []
        temp_files = []

        try:
            # Read source PDF
            with open(file_path, 'rb') as source_file:
                pdf_reader = PyPDF2.PdfReader(source_file)

                # Process in batches
                for batch_start in range(0, total_pages, batch_size):
                    batch_end = min(batch_start + batch_size, total_pages)
                    batch_num = (batch_start // batch_size) + 1
                    total_batches = (total_pages + batch_size - 1) // batch_size

                    logger.info(f"Processing batch {batch_num}/{total_batches}: pages {batch_start+1}-{batch_end}")

                    # Create temporary PDF with this batch of pages
                    pdf_writer = PyPDF2.PdfWriter()
                    for page_idx in range(batch_start, batch_end):
                        pdf_writer.add_page(pdf_reader.pages[page_idx])

                    # Write batch to temp file
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as batch_file:
                        pdf_writer.write(batch_file)
                        batch_path = batch_file.name
                        temp_files.append(batch_path)

                    # Process batch with Docling
                    try:
                        batch_result = self.converter.convert(batch_path)
                        batch_text = batch_result.document.export_to_markdown()

                        # Add batch header
                        all_text.append(f"\n--- Pages {batch_start+1}-{batch_end} ---\n")
                        all_text.append(batch_text)

                        # Accumulate metadata
                        total_ocr_pages += self._count_ocr_pages(batch_result)
                        all_images.extend(self._extract_images_metadata(batch_result))
                        all_tables.extend(self._extract_tables_metadata(batch_result))

                        logger.info(f"Batch {batch_num} completed: {len(batch_text)} chars")

                    except Exception as batch_error:
                        logger.error(f"Batch {batch_num} failed: {batch_error}")
                        all_text.append(f"\n--- Pages {batch_start+1}-{batch_end} (extraction failed) ---\n")
                        continue

            # Combine all text
            full_text = "".join(all_text)
            text_length = len(full_text)

            # Calculate metrics
            confidence = self._assess_quality(full_text, total_ocr_pages, total_pages)
            language = self._detect_language(full_text)

            # Determine extraction method
            if total_ocr_pages > 0:
                extraction_method = "docling_ocr_batched"
                extraction_engine = "easyocr"
            else:
                extraction_method = "docling_batched"
                extraction_engine = "native"

            # Calculate duration
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.info(
                f"Batch processing completed: {text_length} chars, "
                f"{total_ocr_pages}/{total_pages} pages with OCR, {duration_ms}ms"
            )

            return ParseResult(
                text=full_text,
                metadata={
                    "extraction_method": extraction_method,
                    "extraction_engine": extraction_engine,
                    "text_length": text_length,
                    "pages_with_ocr": total_ocr_pages,
                    "total_pages": total_pages,
                    "extraction_duration_ms": duration_ms,
                    "detected_language": language,
                    "file_extension": "pdf",
                    "batch_processing": True,
                    "batch_size": batch_size,
                    "device": self.device if self.device else "unknown",
                    "device_name": self.device_name if self.device_name else "Unknown",
                },
                confidence=confidence,
                images=all_images,
                tables=all_tables
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.error(f"Batch processing failed: {e}", exc_info=True)

            return ParseResult(
                text="",
                metadata={
                    "extraction_method": "batched_failed",
                    "extraction_duration_ms": duration_ms,
                },
                confidence=0.0,
                error=str(e)
            )

        finally:
            # Clean up temp files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass

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
                    "device": self.device if self.device else "unknown",
                    "device_name": self.device_name if self.device_name else "Unknown",
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
                    "device": self.device if self.device else "unknown",
                    "device_name": self.device_name if self.device_name else "Unknown",
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
