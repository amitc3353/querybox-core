"""
Vision API Parser for chart and image interpretation.

Uses GPT-4o-mini Vision API to interpret charts, graphs, diagrams, and other
visual elements that traditional text parsers cannot handle.
"""

import logging
import base64
import io
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
import tempfile

from app.services.parsers.base import DocumentParser, ParseResult
from app.core.config import settings

logger = logging.getLogger(__name__)


class VisionCostTracker:
    """Track Vision API usage and costs."""

    def __init__(self):
        self.images_processed = 0
        self.total_tokens = 0
        self.estimated_cost = 0.0
        self.warnings = []

    def track_image(self, tokens_used: int = 0):
        """Track a single image processed."""
        self.images_processed += 1
        self.total_tokens += tokens_used
        self.estimated_cost += settings.VISION_COST_PER_IMAGE

        # Check cost thresholds
        if self.estimated_cost >= settings.VISION_MAX_COST_PER_DOC:
            self.warnings.append(
                f"Maximum cost per document exceeded: ${self.estimated_cost:.4f} >= ${settings.VISION_MAX_COST_PER_DOC}"
            )
        elif self.estimated_cost >= settings.VISION_WARN_COST_THRESHOLD:
            if not any("Warning threshold" in w for w in self.warnings):
                self.warnings.append(
                    f"Warning: Cost approaching limit: ${self.estimated_cost:.4f}"
                )

    def get_summary(self) -> Dict[str, Any]:
        """Get cost tracking summary."""
        return {
            "images_processed": self.images_processed,
            "total_tokens": self.total_tokens,
            "estimated_cost": round(self.estimated_cost, 4),
            "warnings": self.warnings,
        }


class VisionParser(DocumentParser):
    """
    Vision API parser for interpreting images and charts in documents.

    Features:
    - Extract images from documents (PDF, DOCX, etc.)
    - Interpret charts, graphs, diagrams with GPT-4o-mini Vision API
    - Cost tracking and limits
    - Caching to avoid reprocessing
    - Image preprocessing (resize, format conversion)
    """

    SUPPORTED_IMAGE_FORMATS = ["png", "jpg", "jpeg", "gif", "bmp", "tiff"]
    SUPPORTED_DOC_FORMATS = ["pdf"]  # Can be extended

    def __init__(self):
        super().__init__(name="vision")
        self.client = None
        self.cost_tracker = VisionCostTracker()
        self._check_api_key()

    def _check_api_key(self):
        """Verify OpenAI API key is configured."""
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not configured. Vision parsing will be unavailable.")
        else:
            logger.info("Vision API configured with OpenAI")

    def _initialize_client(self):
        """Lazy initialize OpenAI client."""
        if self.client is None:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info(f"OpenAI Vision client initialized (model: {settings.VISION_API_MODEL})")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None

    def supports_format(self, file_extension: str) -> bool:
        """Check if Vision parser supports this file format."""
        ext = file_extension.lower().lstrip('.')
        return ext in self.SUPPORTED_DOC_FORMATS + self.SUPPORTED_IMAGE_FORMATS

    def parse(self, file_path: str, **kwargs) -> ParseResult:
        """
        Parse document and interpret images with Vision API.

        Args:
            file_path: Path to document or image
            **kwargs: Optional parameters:
                - extract_images_only: Only extract images, don't interpret (bool)
                - max_images: Override max images limit (int)

        Returns:
            ParseResult with image interpretations and cost tracking
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Validate file exists
            self.validate_file(file_path)
            file_extension = self.get_file_extension(file_path)

            # Check if vision parsing is enabled
            if not settings.ENABLE_VISION_PARSING:
                return ParseResult(
                    text="",
                    metadata={"extraction_method": "vision_disabled"},
                    confidence=0.0,
                    error="Vision parsing is disabled in configuration"
                )

            # Initialize client if needed
            if not self.client:
                self._initialize_client()

            if not self.client:
                return ParseResult(
                    text="",
                    metadata={"extraction_method": "vision_unavailable"},
                    confidence=0.0,
                    error="Vision API client not available (check OPENAI_API_KEY)"
                )

            # Reset cost tracker for this document
            self.cost_tracker = VisionCostTracker()

            # Handle single image file
            if file_extension in self.SUPPORTED_IMAGE_FORMATS:
                return self._parse_single_image(file_path, start_time)

            # Handle document with multiple images (PDF)
            if file_extension == "pdf":
                return self._parse_pdf_with_images(file_path, start_time, **kwargs)

            # Unsupported format
            return ParseResult(
                text="",
                metadata={"extraction_method": "vision_unsupported"},
                confidence=0.0,
                error=f"Unsupported format for vision parsing: {file_extension}"
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.error(f"Vision parsing failed: {e}", exc_info=True)

            return ParseResult(
                text="",
                metadata={
                    "extraction_method": "vision_failed",
                    "extraction_duration_ms": duration_ms,
                },
                confidence=0.0,
                error=str(e)
            )

    def _parse_single_image(self, image_path: str, start_time: datetime) -> ParseResult:
        """Parse a single image file."""
        try:
            # Interpret image
            description = self.interpret_image(image_path)

            # Calculate metrics
            text_length = len(description)
            confidence = 0.8 if description else 0.0  # High confidence for successful API call

            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            cost_summary = self.cost_tracker.get_summary()

            logger.info(f"Single image interpreted: {text_length} chars, {duration_ms}ms, cost: ${cost_summary['estimated_cost']}")

            return ParseResult(
                text=description,
                metadata={
                    "extraction_method": "vision_single_image",
                    "extraction_engine": "gpt-4o-mini",
                    "text_length": text_length,
                    "extraction_duration_ms": duration_ms,
                    "vision_cost_tracking": cost_summary,
                },
                confidence=confidence,
                images=[{
                    "index": 0,
                    "type": "image",
                    "description": description,
                }]
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.error(f"Single image parsing failed: {e}")

            return ParseResult(
                text="",
                metadata={
                    "extraction_method": "vision_single_image_failed",
                    "extraction_duration_ms": duration_ms,
                },
                confidence=0.0,
                error=str(e)
            )

    def _parse_pdf_with_images(self, pdf_path: str, start_time: datetime, **kwargs) -> ParseResult:
        """Extract and interpret images from PDF."""
        try:
            # Extract images from PDF
            images = self.extract_images_from_pdf(pdf_path, max_images=kwargs.get("max_images"))

            if not images:
                logger.info("No images found in PDF")
                return ParseResult(
                    text="",
                    metadata={
                        "extraction_method": "vision_no_images",
                        "extraction_duration_ms": 0,
                    },
                    confidence=0.0
                )

            # Interpret each image
            interpretations = []
            for i, image_data in enumerate(images):
                if self.cost_tracker.estimated_cost >= settings.VISION_MAX_COST_PER_DOC:
                    logger.warning(f"Cost limit reached, stopping at image {i}/{len(images)}")
                    break

                try:
                    description = self.interpret_image_data(image_data)
                    interpretations.append({
                        "index": i,
                        "type": "chart" if self._is_likely_chart(description) else "image",
                        "description": description,
                    })
                except Exception as img_error:
                    logger.warning(f"Failed to interpret image {i}: {img_error}")
                    interpretations.append({
                        "index": i,
                        "type": "image",
                        "description": "",
                        "error": str(img_error),
                    })

            # Combine descriptions
            full_text = "\n\n".join([
                f"[Image {i['index']+1}]: {i['description']}"
                for i in interpretations
                if i.get("description")
            ])

            # Calculate metrics
            text_length = len(full_text)
            confidence = 0.8 if interpretations else 0.0

            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            cost_summary = self.cost_tracker.get_summary()

            logger.info(
                f"PDF vision parsing complete: {len(interpretations)} images, "
                f"{text_length} chars, {duration_ms}ms, cost: ${cost_summary['estimated_cost']}"
            )

            return ParseResult(
                text=full_text,
                metadata={
                    "extraction_method": "vision_pdf",
                    "extraction_engine": "gpt-4o-mini",
                    "text_length": text_length,
                    "images_found": len(images),
                    "images_interpreted": len(interpretations),
                    "extraction_duration_ms": duration_ms,
                    "vision_cost_tracking": cost_summary,
                },
                confidence=confidence,
                images=interpretations
            )

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            logger.error(f"PDF vision parsing failed: {e}")

            return ParseResult(
                text="",
                metadata={
                    "extraction_method": "vision_pdf_failed",
                    "extraction_duration_ms": duration_ms,
                },
                confidence=0.0,
                error=str(e)
            )

    def extract_images_from_pdf(self, pdf_path: str, max_images: Optional[int] = None) -> List[bytes]:
        """
        Extract images from PDF.

        Args:
            pdf_path: Path to PDF file
            max_images: Max images to extract (defaults to config)

        Returns:
            List of image data (bytes)
        """
        max_images = max_images or settings.VISION_API_MAX_IMAGES_PER_DOC

        try:
            import fitz  # PyMuPDF
            images = []

            doc = fitz.open(pdf_path)

            for page_num in range(len(doc)):
                if len(images) >= max_images:
                    break

                page = doc[page_num]
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    if len(images) >= max_images:
                        break

                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_data = base_image["image"]
                        images.append(image_data)

                    except Exception as img_error:
                        logger.warning(f"Failed to extract image {img_index} from page {page_num}: {img_error}")
                        continue

            doc.close()

            logger.info(f"Extracted {len(images)} images from PDF (max: {max_images})")
            return images

        except ImportError:
            logger.error("PyMuPDF (fitz) not installed. Install with: pip install PyMuPDF")
            return []
        except Exception as e:
            logger.error(f"Failed to extract images from PDF: {e}")
            return []

    def interpret_image(self, image_path: str, context: str = "") -> str:
        """
        Interpret an image file with Vision API.

        Args:
            image_path: Path to image file
            context: Optional context about the document

        Returns:
            Image description/interpretation
        """
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()

            return self.interpret_image_data(image_data, context)

        except Exception as e:
            logger.error(f"Failed to read image file: {e}")
            return ""

    def interpret_image_data(self, image_data: bytes, context: str = "") -> str:
        """
        Interpret image data with Vision API.

        Args:
            image_data: Raw image bytes
            context: Optional context

        Returns:
            Image description/interpretation
        """
        try:
            # Encode image to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')

            # Build prompt
            prompt = self._build_vision_prompt(context)

            # Call Vision API
            response = self.client.chat.completions.create(
                model=settings.VISION_API_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": settings.VISION_IMAGE_QUALITY
                                }
                            }
                        ]
                    }
                ],
                max_tokens=settings.VISION_API_MAX_TOKENS,
                temperature=settings.VISION_API_TEMPERATURE,
                timeout=settings.VISION_API_TIMEOUT_SECONDS,
            )

            # Extract description
            description = response.choices[0].message.content.strip()

            # Track cost
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0
            self.cost_tracker.track_image(tokens_used)

            logger.debug(f"Vision API response: {len(description)} chars, {tokens_used} tokens")

            return description

        except Exception as e:
            logger.error(f"Vision API call failed: {e}")
            # Track failed attempt (still counts as image processed for cost)
            self.cost_tracker.track_image(0)
            return ""

    def _build_vision_prompt(self, context: str = "") -> str:
        """Build vision prompt template for chart/image interpretation."""
        base_prompt = """Describe this chart, graph, or image in detail. Include:

1. **Type of visualization**: Identify if it's a bar chart, line graph, pie chart, scatter plot, diagram, flowchart, table, or other visual element.

2. **Data being shown**: Describe the axes, labels, values, and any data series or categories present.

3. **Key insights or trends**: Highlight important patterns, trends, comparisons, or conclusions that can be drawn from the visual.

4. **Annotations or markers**: Note any important annotations, legends, markers, or callouts.

5. **Overall purpose**: Explain what this visualization is meant to communicate.

Be concise but thorough. Focus on factual description and data interpretation."""

        if context:
            return f"{base_prompt}\n\nDocument context: {context}"

        return base_prompt

    def _is_likely_chart(self, description: str) -> bool:
        """Heuristic to determine if description indicates a chart/graph."""
        chart_keywords = [
            "chart", "graph", "plot", "diagram", "bar", "line",
            "pie", "scatter", "histogram", "axis", "axes", "trend"
        ]

        description_lower = description.lower()
        return any(keyword in description_lower for keyword in chart_keywords)
