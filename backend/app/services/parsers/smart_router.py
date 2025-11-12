"""
Smart Router for intelligent document parsing (Phase 2.3).

Automatically analyzes documents and routes to optimal parser(s):
- Docling for text and tables
- Vision API for charts and graphs
- Combined results for documents with mixed content

The router detects:
- Number of images/charts in document
- Whether PDF is scanned (image-only)
- Document complexity

It then:
- Selects appropriate parser(s) based on analysis
- Orchestrates parsing (sequential or parallel)
- Merges results intelligently
- Respects cost controls and fallback gracefully
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from app.services.parsers.base import DocumentParser, ParseResult
from app.services.parsers.docling_parser import DoclingParser
from app.services.parsers.vision_parser import VisionParser
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentAnalysis:
    """
    Results of document analysis.

    Used to determine routing strategy.
    """

    def __init__(
        self,
        has_images: bool,
        image_count: int,
        has_text: bool,
        page_count: int,
        is_scanned: bool,
        avg_text_per_page: float,
        recommended_parsers: List[str]
    ):
        self.has_images = has_images
        self.image_count = image_count
        self.has_text = has_text
        self.page_count = page_count
        self.is_scanned = is_scanned
        self.avg_text_per_page = avg_text_per_page
        self.recommended_parsers = recommended_parsers

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/metadata."""
        return {
            "has_images": self.has_images,
            "image_count": self.image_count,
            "has_text": self.has_text,
            "page_count": self.page_count,
            "is_scanned": self.is_scanned,
            "avg_text_per_page": self.avg_text_per_page,
            "recommended_parsers": self.recommended_parsers
        }


class SmartRouter(DocumentParser):
    """
    Intelligent document router that selects optimal parser(s).

    Analysis → Routing → Orchestration → Merging

    Features:
    - Automatic image/chart detection
    - Scanned PDF detection
    - Cost-aware Vision API usage
    - Intelligent result merging
    - Graceful fallback

    Example:
        router = SmartRouter()
        result = router.parse("document.pdf")
        # Automatically uses Docling + Vision if images detected
    """

    def __init__(self):
        """Initialize Smart Router with sub-parsers."""
        super().__init__(name="smart")

        # Initialize sub-parsers
        self.docling_parser = DoclingParser()
        self.vision_parser = VisionParser()

        # Track routing statistics
        self.routing_stats = {
            "documents_processed": 0,
            "docling_only": 0,
            "vision_only": 0,
            "both_parsers": 0,
            "failures": 0
        }

        logger.info("SmartRouter initialized with Docling + Vision parsers")

    def supports_format(self, file_extension: str) -> bool:
        """
        Check if any sub-parser supports this format.

        Args:
            file_extension: File extension (e.g., "pdf", "png")

        Returns:
            True if any sub-parser supports the format
        """
        return (
            self.docling_parser.supports_format(file_extension) or
            self.vision_parser.supports_format(file_extension)
        )

    def parse(self, file_path: str, **kwargs) -> ParseResult:
        """
        Intelligently parse document using optimal parser(s).

        Process:
        1. Analyze document characteristics
        2. Determine routing strategy
        3. Parse with appropriate parser(s)
        4. Merge results if multiple parsers used
        5. Return unified ParseResult

        Args:
            file_path: Path to document
            **kwargs: Additional options (passed to sub-parsers)

        Returns:
            ParseResult with merged content from optimal parser(s)
        """
        start_time = time.time()

        logger.info(f"SmartRouter parsing: {file_path}")

        try:
            # Validate file
            self.validate_file(file_path)
            file_ext = self.get_file_extension(file_path)
            # Step 1: Analyze document
            analysis = self.analyze_document(file_path)

            if settings.SMART_ROUTER_LOG_ANALYSIS_RESULTS:
                logger.info(f"Document analysis: {analysis.to_dict()}")

            # Step 2: Determine routing strategy
            use_docling, use_vision = self._determine_routing(analysis)

            if settings.SMART_ROUTER_LOG_ROUTING_DECISIONS:
                parsers_to_use = []
                if use_docling:
                    parsers_to_use.append("docling")
                if use_vision:
                    parsers_to_use.append("vision")
                logger.info(f"Routing decision: {', '.join(parsers_to_use)}")

            # Step 3: Parse with selected parser(s)
            docling_result = None
            vision_result = None

            if use_docling:
                logger.info("Parsing with Docling...")
                docling_result = self.docling_parser.parse(file_path, **kwargs)

            if use_vision and settings.ENABLE_VISION_PARSING:
                logger.info("Parsing with Vision API...")
                try:
                    vision_result = self.vision_parser.parse(file_path, **kwargs)
                except Exception as e:
                    logger.warning(f"Vision parsing failed: {e}")
                    if not settings.SMART_ROUTER_FALLBACK_TO_DOCLING:
                        raise

            # Step 4: Merge results
            final_result = self._merge_results(docling_result, vision_result, analysis)

            # Step 5: Add routing metadata
            duration_ms = (time.time() - start_time) * 1000
            final_result.metadata.update({
                "smart_router": {
                    "analysis": analysis.to_dict(),
                    "used_docling": use_docling,
                    "used_vision": use_vision,
                    "routing_duration_ms": duration_ms
                }
            })

            # Update statistics
            self.routing_stats["documents_processed"] += 1
            if use_docling and use_vision:
                self.routing_stats["both_parsers"] += 1
            elif use_docling:
                self.routing_stats["docling_only"] += 1
            elif use_vision:
                self.routing_stats["vision_only"] += 1

            logger.info(f"SmartRouter completed in {duration_ms:.2f}ms")
            return final_result

        except Exception as e:
            self.routing_stats["failures"] += 1
            logger.error(f"SmartRouter parsing failed: {e}", exc_info=True)

            # Return error result
            return ParseResult(
                text="",
                metadata={
                    "extraction_method": "smart_router_failed",
                    "error_details": str(e)
                },
                confidence=0.0,
                error=f"Smart routing failed: {str(e)}"
            )

    def analyze_document(self, file_path: str) -> DocumentAnalysis:
        """
        Analyze document to determine routing strategy.

        Uses PyMuPDF to examine:
        - Number and size of images
        - Amount of extractable text
        - Whether document is scanned (image-only)

        Args:
            file_path: Path to document

        Returns:
            DocumentAnalysis object with characteristics
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF not available for document analysis, using fallback")
            return self._fallback_analysis(file_path)

        try:
            doc = fitz.open(file_path)

            total_images = 0
            total_text_length = 0
            page_count = len(doc)

            for page_num in range(page_count):
                page = doc[page_num]

                # Count images (filter by size threshold)
                images = page.get_images()
                for img in images:
                    # Get image size (approximate)
                    xref = img[0]
                    try:
                        img_dict = doc.extract_image(xref)
                        img_size = len(img_dict["image"])
                        if img_size >= settings.SMART_ROUTER_MIN_IMAGE_SIZE_BYTES:
                            total_images += 1
                    except Exception:
                        # Count anyway if we can't get size
                        total_images += 1

                # Get text to detect scanned vs native
                text = page.get_text()
                total_text_length += len(text.strip())

            doc.close()

            # Calculate metrics
            avg_text_per_page = total_text_length / page_count if page_count > 0 else 0
            has_text = total_text_length > 0
            has_images = total_images > 0

            # Detect scanned PDF (has images but little text)
            is_scanned = False
            if settings.SMART_ROUTER_DETECT_SCANNED_PDF:
                is_scanned = (
                    has_images and
                    avg_text_per_page < settings.SMART_ROUTER_SCANNED_TEXT_THRESHOLD
                )

            # Determine recommended parsers
            recommended_parsers = self._determine_parsers(
                has_images=has_images,
                image_count=total_images,
                has_text=has_text,
                is_scanned=is_scanned
            )

            analysis = DocumentAnalysis(
                has_images=has_images,
                image_count=total_images,
                has_text=has_text,
                page_count=page_count,
                is_scanned=is_scanned,
                avg_text_per_page=avg_text_per_page,
                recommended_parsers=recommended_parsers
            )

            return analysis

        except Exception as e:
            logger.warning(f"Document analysis failed: {e}, using fallback")
            return self._fallback_analysis(file_path)

    def _fallback_analysis(self, file_path: str) -> DocumentAnalysis:
        """
        Fallback analysis when PyMuPDF unavailable.

        Assumes document may have images and uses conservative routing.
        """
        file_ext = self.get_file_extension(file_path)

        # Conservative assumptions
        if file_ext == "pdf":
            # Assume PDF might have images
            return DocumentAnalysis(
                has_images=True,
                image_count=5,  # Conservative estimate
                has_text=True,
                page_count=1,
                is_scanned=False,
                avg_text_per_page=500.0,
                recommended_parsers=["docling", "vision"]
            )
        elif file_ext in ["png", "jpg", "jpeg", "gif"]:
            # Single image
            return DocumentAnalysis(
                has_images=True,
                image_count=1,
                has_text=False,
                page_count=1,
                is_scanned=False,
                avg_text_per_page=0.0,
                recommended_parsers=["vision"]
            )
        else:
            # Unknown format, try Docling
            return DocumentAnalysis(
                has_images=False,
                image_count=0,
                has_text=True,
                page_count=1,
                is_scanned=False,
                avg_text_per_page=1000.0,
                recommended_parsers=["docling"]
            )

    def _determine_parsers(
        self,
        has_images: bool,
        image_count: int,
        has_text: bool,
        is_scanned: bool
    ) -> List[str]:
        """
        Determine which parser(s) to recommend based on document characteristics.

        Args:
            has_images: Document contains images
            image_count: Number of images detected
            has_text: Document contains extractable text
            is_scanned: Document is scanned (image-only)

        Returns:
            List of recommended parser names
        """
        parsers = []

        # Always use Docling for text extraction
        if settings.SMART_ROUTER_ALWAYS_USE_DOCLING:
            parsers.append("docling")

        # Decide on Vision API usage
        should_use_vision = False

        if has_images and settings.SMART_ROUTER_PREFER_VISION_FOR_CHARTS:
            # Check if we should use Vision based on image count
            if image_count >= settings.SMART_ROUTER_IMAGE_THRESHOLD:
                # Check cost controls
                if settings.SMART_ROUTER_SKIP_VISION_IF_EXPENSIVE:
                    if image_count <= settings.SMART_ROUTER_MAX_IMAGES_FOR_VISION:
                        should_use_vision = True
                else:
                    should_use_vision = True

        # Special case: image-only documents
        if not has_text and has_images:
            if not settings.SMART_ROUTER_SKIP_VISION_IF_NO_TEXT:
                should_use_vision = True

        if should_use_vision and "vision" not in parsers:
            parsers.append("vision")

        # Fallback: if no parsers recommended, use Docling
        if not parsers:
            parsers.append("docling")

        return parsers

    def _determine_routing(self, analysis: DocumentAnalysis) -> Tuple[bool, bool]:
        """
        Determine which parsers to actually use based on analysis.

        Args:
            analysis: Document analysis results

        Returns:
            Tuple of (use_docling: bool, use_vision: bool)
        """
        use_docling = "docling" in analysis.recommended_parsers
        use_vision = "vision" in analysis.recommended_parsers

        # Apply configuration overrides
        if not settings.SMART_ROUTER_ENABLED:
            # If smart router disabled, just use Docling
            use_docling = True
            use_vision = False

        if not settings.ENABLE_VISION_PARSING:
            # If Vision globally disabled, don't use it
            use_vision = False

        return use_docling, use_vision

    def _merge_results(
        self,
        docling_result: Optional[ParseResult],
        vision_result: Optional[ParseResult],
        analysis: DocumentAnalysis
    ) -> ParseResult:
        """
        Merge results from multiple parsers into unified ParseResult.

        Strategy:
        - Text: Concatenate with separator (or interleave if configured)
        - Metadata: Combine both
        - Confidence: Weighted average
        - Images: Union of both lists
        - Tables: From Docling
        - Errors: Combine if any

        Args:
            docling_result: Result from Docling parser (or None)
            vision_result: Result from Vision parser (or None)
            analysis: Document analysis results

        Returns:
            Merged ParseResult
        """
        # Handle case where neither parser ran (shouldn't happen)
        if docling_result is None and vision_result is None:
            return ParseResult(
                text="",
                metadata={"extraction_method": "smart_router_no_parsers"},
                confidence=0.0,
                error="No parsers executed"
            )

        # Handle case where only one parser ran
        if docling_result is None:
            vision_result.metadata["extraction_method"] = "smart_router_vision_only"
            return vision_result

        if vision_result is None:
            docling_result.metadata["extraction_method"] = "smart_router_docling_only"
            return docling_result

        # Both parsers ran - merge results
        logger.info("Merging results from Docling + Vision...")

        # Merge text
        merged_text = self._merge_text(docling_result.text, vision_result.text)

        # Merge metadata
        merged_metadata = {
            "extraction_method": "smart_router_combined",
            "docling_metadata": docling_result.metadata,
            "vision_metadata": vision_result.metadata,
            "text_length": len(merged_text),
            "docling_duration_ms": docling_result.metadata.get("extraction_duration_ms", 0),
            "vision_duration_ms": vision_result.metadata.get("extraction_duration_ms", 0),
            "total_duration_ms": (
                docling_result.metadata.get("extraction_duration_ms", 0) +
                vision_result.metadata.get("extraction_duration_ms", 0)
            ),
            "images_from_docling": len(docling_result.images),
            "images_from_vision": len(vision_result.images),
            "vision_cost_tracking": vision_result.metadata.get("vision_cost_tracking"),
        }

        # Merge confidence (weighted average)
        docling_weight = settings.SMART_ROUTER_CONFIDENCE_WEIGHT_TEXT
        vision_weight = settings.SMART_ROUTER_CONFIDENCE_WEIGHT_VISION
        merged_confidence = (
            docling_result.confidence * docling_weight +
            vision_result.confidence * vision_weight
        )

        # Merge images (union)
        merged_images = docling_result.images + vision_result.images

        # Tables from Docling
        merged_tables = docling_result.tables

        # Merge errors
        merged_error = None
        if docling_result.error and vision_result.error:
            merged_error = f"Docling: {docling_result.error}; Vision: {vision_result.error}"
        elif docling_result.error:
            merged_error = f"Docling failed: {docling_result.error} (Vision succeeded)"
        elif vision_result.error:
            # Vision error is non-fatal (it's supplementary)
            merged_error = None

        return ParseResult(
            text=merged_text,
            metadata=merged_metadata,
            confidence=merged_confidence,
            images=merged_images,
            tables=merged_tables,
            error=merged_error
        )

    def _merge_text(self, docling_text: str, vision_text: str) -> str:
        """
        Merge text from Docling and Vision parsers.

        Args:
            docling_text: Text from Docling (main document content)
            vision_text: Text from Vision (image descriptions)

        Returns:
            Merged text string
        """
        if not docling_text and not vision_text:
            return ""

        if not docling_text:
            return vision_text

        if not vision_text:
            return docling_text

        # Both have content - merge with separator
        separator = settings.SMART_ROUTER_VISION_TEXT_SEPARATOR

        # TODO: Implement interleaving if SMART_ROUTER_INTERLEAVE_VISION_TEXT=True
        # For now, just append

        return f"{docling_text}{separator}{vision_text}"

    def get_routing_stats(self) -> Dict[str, Any]:
        """
        Get routing statistics.

        Returns:
            Dictionary with routing statistics
        """
        return self.routing_stats.copy()
