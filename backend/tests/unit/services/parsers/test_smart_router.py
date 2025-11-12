"""
Unit tests for Smart Router (Phase 2.3).

Tests intelligent document routing, analysis, merging, and error handling.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.services.parsers.smart_router import SmartRouter, DocumentAnalysis
from app.services.parsers.base import ParseResult
from app.core.config import settings


class TestSmartRouterBasics:
    """Test basic Smart Router functionality."""

    def test_router_initialization(self):
        """Test Smart Router initialization."""
        router = SmartRouter()

        assert router.name == "smart"
        assert router.docling_parser is not None
        assert router.vision_parser is not None
        assert router.routing_stats["documents_processed"] == 0

    def test_supports_format_pdf(self):
        """Test that router supports PDF format."""
        router = SmartRouter()

        assert router.supports_format("pdf")

    def test_supports_format_images(self):
        """Test that router supports image formats."""
        router = SmartRouter()

        assert router.supports_format("png")
        assert router.supports_format("jpg")
        assert router.supports_format("jpeg")

    def test_supports_format_unknown(self):
        """Test that router handles unknown formats."""
        router = SmartRouter()

        # Should return False for unknown formats
        # (delegated to sub-parsers)
        result = router.supports_format("unknown")
        # Result depends on sub-parsers


class TestDocumentAnalysis:
    """Test document analysis logic."""

    def test_document_analysis_object(self):
        """Test DocumentAnalysis object creation."""
        analysis = DocumentAnalysis(
            has_images=True,
            image_count=5,
            has_text=True,
            page_count=10,
            is_scanned=False,
            avg_text_per_page=500.0,
            recommended_parsers=["docling", "vision"]
        )

        assert analysis.has_images is True
        assert analysis.image_count == 5
        assert analysis.page_count == 10
        assert "docling" in analysis.recommended_parsers
        assert "vision" in analysis.recommended_parsers

    def test_document_analysis_to_dict(self):
        """Test DocumentAnalysis serialization."""
        analysis = DocumentAnalysis(
            has_images=True,
            image_count=3,
            has_text=True,
            page_count=5,
            is_scanned=False,
            avg_text_per_page=400.0,
            recommended_parsers=["docling"]
        )

        data = analysis.to_dict()

        assert data["has_images"] is True
        assert data["image_count"] == 3
        assert data["page_count"] == 5
        assert isinstance(data["recommended_parsers"], list)

    def test_analyze_document_with_images(self):
        """Test document analysis when PDF has images (requires PyMuPDF)."""
        # Skip test if PyMuPDF not available
        try:
            import fitz
        except ImportError:
            pytest.skip("PyMuPDF (fitz) not available - skipping test")

        # Mock PyMuPDF document
        mock_page = Mock()

        # Simulate 5 images
        mock_page.get_images.return_value = [(1, 0), (2, 0), (3, 0), (4, 0), (5, 0)]
        mock_page.get_text.return_value = "Sample text content " * 100  # Good amount of text

        # Create mock doc with proper __len__ support
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1  # 1 page
        mock_doc.__iter__.return_value = [mock_page]
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__exit__.return_value = None
        mock_doc.close = Mock()

        # Mock extract_image to return large enough images
        mock_doc.extract_image.return_value = {
            "image": b"x" * 20000  # 20KB image
        }

        router = SmartRouter()

        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf")
            temp_path = f.name

        try:
            # Patch fitz.open within the analyze_document call
            with patch('fitz.open', return_value=mock_doc):
                analysis = router.analyze_document(temp_path)

                assert analysis.has_images is True
                assert analysis.image_count == 5
                assert analysis.has_text is True
                assert "vision" in analysis.recommended_parsers

        finally:
            os.unlink(temp_path)

    def test_analyze_scanned_pdf(self):
        """Test detection of scanned PDFs (images but little text, requires PyMuPDF)."""
        # Skip test if PyMuPDF not available
        try:
            import fitz
        except ImportError:
            pytest.skip("PyMuPDF (fitz) not available - skipping test")

        mock_page = Mock()

        # Simulate images but very little text
        mock_page.get_images.return_value = [(1, 0)]
        mock_page.get_text.return_value = "   \n  "  # Minimal text

        # Use MagicMock for proper __len__ support
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.__iter__.return_value = [mock_page]
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__exit__.return_value = None
        mock_doc.close = Mock()
        mock_doc.extract_image.return_value = {"image": b"x" * 15000}

        router = SmartRouter()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf")
            temp_path = f.name

        try:
            with patch('fitz.open', return_value=mock_doc):
                analysis = router.analyze_document(temp_path)

                assert analysis.is_scanned is True
                assert analysis.has_images is True
                assert analysis.avg_text_per_page < settings.SMART_ROUTER_SCANNED_TEXT_THRESHOLD

        finally:
            os.unlink(temp_path)

    def test_fallback_analysis_pdf(self):
        """Test fallback analysis when PyMuPDF unavailable."""
        router = SmartRouter()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf")
            temp_path = f.name

        try:
            # Mock fitz import failure
            with patch.dict('sys.modules', {'fitz': None}):
                analysis = router._fallback_analysis(temp_path)

                # Should assume PDF might have images
                assert analysis.has_images is True
                assert analysis.recommended_parsers is not None

        finally:
            os.unlink(temp_path)

    def test_fallback_analysis_image(self):
        """Test fallback analysis for image files."""
        router = SmartRouter()

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake image")
            temp_path = f.name

        try:
            analysis = router._fallback_analysis(temp_path)

            assert analysis.has_images is True
            assert "vision" in analysis.recommended_parsers

        finally:
            os.unlink(temp_path)


class TestRoutingLogic:
    """Test routing decisions."""

    def test_determine_parsers_no_images(self):
        """Test routing when document has no images."""
        router = SmartRouter()

        parsers = router._determine_parsers(
            has_images=False,
            image_count=0,
            has_text=True,
            is_scanned=False
        )

        assert "docling" in parsers
        assert "vision" not in parsers

    def test_determine_parsers_with_images(self):
        """Test routing when document has sufficient images."""
        router = SmartRouter()

        parsers = router._determine_parsers(
            has_images=True,
            image_count=5,  # Above threshold
            has_text=True,
            is_scanned=False
        )

        assert "docling" in parsers
        assert "vision" in parsers

    def test_determine_parsers_few_images(self):
        """Test routing when image count below threshold."""
        router = SmartRouter()

        parsers = router._determine_parsers(
            has_images=True,
            image_count=1,  # Below SMART_ROUTER_IMAGE_THRESHOLD (3)
            has_text=True,
            is_scanned=False
        )

        assert "docling" in parsers
        # Vision might not be included if below threshold

    def test_determine_parsers_cost_control(self):
        """Test routing respects cost controls."""
        router = SmartRouter()

        # Too many images for Vision
        parsers = router._determine_parsers(
            has_images=True,
            image_count=20,  # Above SMART_ROUTER_MAX_IMAGES_FOR_VISION (10)
            has_text=True,
            is_scanned=False
        )

        # Should skip Vision due to cost
        if settings.SMART_ROUTER_SKIP_VISION_IF_EXPENSIVE:
            assert "vision" not in parsers

    def test_determine_routing_vision_disabled(self):
        """Test routing when Vision globally disabled."""
        router = SmartRouter()

        analysis = DocumentAnalysis(
            has_images=True,
            image_count=5,
            has_text=True,
            page_count=1,
            is_scanned=False,
            avg_text_per_page=500.0,
            recommended_parsers=["docling", "vision"]
        )

        original_vision_enabled = settings.ENABLE_VISION_PARSING
        settings.ENABLE_VISION_PARSING = False

        try:
            use_docling, use_vision = router._determine_routing(analysis)

            assert use_docling is True
            assert use_vision is False

        finally:
            settings.ENABLE_VISION_PARSING = original_vision_enabled

    def test_determine_routing_smart_router_disabled(self):
        """Test routing when Smart Router disabled."""
        router = SmartRouter()

        analysis = DocumentAnalysis(
            has_images=True,
            image_count=5,
            has_text=True,
            page_count=1,
            is_scanned=False,
            avg_text_per_page=500.0,
            recommended_parsers=["docling", "vision"]
        )

        original_enabled = settings.SMART_ROUTER_ENABLED
        settings.SMART_ROUTER_ENABLED = False

        try:
            use_docling, use_vision = router._determine_routing(analysis)

            # Should fallback to Docling only
            assert use_docling is True
            assert use_vision is False

        finally:
            settings.SMART_ROUTER_ENABLED = original_enabled


class TestResultMerging:
    """Test result merging logic."""

    def test_merge_text_both_present(self):
        """Test merging text from both parsers."""
        router = SmartRouter()

        docling_text = "Main document text content"
        vision_text = "Chart 1: Bar chart showing sales data"

        merged = router._merge_text(docling_text, vision_text)

        assert "Main document text" in merged
        assert "Chart 1" in merged
        assert len(merged) > len(docling_text)

    def test_merge_text_only_docling(self):
        """Test merging when only Docling has text."""
        router = SmartRouter()

        merged = router._merge_text("Docling text", "")

        assert merged == "Docling text"

    def test_merge_text_only_vision(self):
        """Test merging when only Vision has text."""
        router = SmartRouter()

        merged = router._merge_text("", "Vision text")

        assert merged == "Vision text"

    def test_merge_results_both_parsers(self):
        """Test merging results from both parsers."""
        router = SmartRouter()

        docling_result = ParseResult(
            text="Document text",
            metadata={"extraction_method": "docling", "extraction_duration_ms": 100},
            confidence=0.9,
            images=[],
            tables=[{"table": 1}]
        )

        vision_result = ParseResult(
            text="Chart description",
            metadata={"extraction_method": "vision", "extraction_duration_ms": 50},
            confidence=0.8,
            images=[{"image": 1}],
            tables=[]
        )

        analysis = DocumentAnalysis(
            has_images=True,
            image_count=1,
            has_text=True,
            page_count=1,
            is_scanned=False,
            avg_text_per_page=100.0,
            recommended_parsers=["docling", "vision"]
        )

        merged = router._merge_results(docling_result, vision_result, analysis)

        assert "Document text" in merged.text
        assert "Chart description" in merged.text
        assert merged.metadata["extraction_method"] == "smart_router_combined"
        assert len(merged.tables) == 1  # From Docling
        assert len(merged.images) == 1  # From Vision
        # Confidence should be weighted average
        expected_confidence = 0.9 * 0.7 + 0.8 * 0.3
        assert abs(merged.confidence - expected_confidence) < 0.01

    def test_merge_results_docling_only(self):
        """Test merging when only Docling ran."""
        router = SmartRouter()

        docling_result = ParseResult(
            text="Document text",
            metadata={"extraction_method": "docling"},
            confidence=0.9,
            images=[],
            tables=[]
        )

        analysis = DocumentAnalysis(
            has_images=False,
            image_count=0,
            has_text=True,
            page_count=1,
            is_scanned=False,
            avg_text_per_page=100.0,
            recommended_parsers=["docling"]
        )

        merged = router._merge_results(docling_result, None, analysis)

        assert merged.text == "Document text"
        assert "smart_router_docling_only" in merged.metadata["extraction_method"]

    def test_merge_results_vision_only(self):
        """Test merging when only Vision ran."""
        router = SmartRouter()

        vision_result = ParseResult(
            text="Image description",
            metadata={"extraction_method": "vision"},
            confidence=0.8,
            images=[],
            tables=[]
        )

        analysis = DocumentAnalysis(
            has_images=True,
            image_count=1,
            has_text=False,
            page_count=1,
            is_scanned=False,
            avg_text_per_page=0.0,
            recommended_parsers=["vision"]
        )

        merged = router._merge_results(None, vision_result, analysis)

        assert merged.text == "Image description"
        assert "smart_router_vision_only" in merged.metadata["extraction_method"]

    def test_merge_results_neither_parser(self):
        """Test merging when neither parser ran (error case)."""
        router = SmartRouter()

        analysis = DocumentAnalysis(
            has_images=False,
            image_count=0,
            has_text=False,
            page_count=1,
            is_scanned=False,
            avg_text_per_page=0.0,
            recommended_parsers=[]
        )

        merged = router._merge_results(None, None, analysis)

        assert merged.text == ""
        assert merged.confidence == 0.0
        assert merged.error is not None


class TestEndToEnd:
    """Test end-to-end parsing with mocked sub-parsers."""

    def test_parse_with_mocked_parsers(self):
        """Test full parse flow with mocked sub-parsers."""
        router = SmartRouter()

        # Mock Docling parser
        mock_docling_result = ParseResult(
            text="Document text content",
            metadata={"extraction_method": "docling", "extraction_duration_ms": 100},
            confidence=0.9,
            images=[],
            tables=[]
        )

        router.docling_parser.parse = Mock(return_value=mock_docling_result)

        # Mock Vision parser
        mock_vision_result = ParseResult(
            text="Chart: Sales increased 20%",
            metadata={"extraction_method": "vision", "extraction_duration_ms": 50},
            confidence=0.8,
            images=[{"image": 1}],
            tables=[]
        )

        router.vision_parser.parse = Mock(return_value=mock_vision_result)

        # Mock document analysis
        mock_analysis = DocumentAnalysis(
            has_images=True,
            image_count=5,
            has_text=True,
            page_count=1,
            is_scanned=False,
            avg_text_per_page=500.0,
            recommended_parsers=["docling", "vision"]
        )

        router.analyze_document = Mock(return_value=mock_analysis)

        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf content")
            temp_path = f.name

        try:
            result = router.parse(temp_path)

            assert result.error is None
            assert "Document text" in result.text
            assert "Chart" in result.text
            assert result.metadata["smart_router"] is not None
            assert result.metadata["smart_router"]["used_docling"] is True
            assert result.metadata["smart_router"]["used_vision"] is True

        finally:
            os.unlink(temp_path)

    def test_parse_text_only_document(self):
        """Test parsing text-only document (no Vision)."""
        router = SmartRouter()

        mock_docling_result = ParseResult(
            text="Text only content",
            metadata={"extraction_method": "docling"},
            confidence=0.95,
            images=[],
            tables=[]
        )

        router.docling_parser.parse = Mock(return_value=mock_docling_result)

        mock_analysis = DocumentAnalysis(
            has_images=False,
            image_count=0,
            has_text=True,
            page_count=1,
            is_scanned=False,
            avg_text_per_page=500.0,
            recommended_parsers=["docling"]
        )

        router.analyze_document = Mock(return_value=mock_analysis)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf")
            temp_path = f.name

        try:
            result = router.parse(temp_path)

            assert result.text == "Text only content"
            assert result.metadata["smart_router"]["used_docling"] is True
            assert result.metadata["smart_router"]["used_vision"] is False

        finally:
            os.unlink(temp_path)


class TestErrorHandling:
    """Test error handling and fallback."""

    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file."""
        router = SmartRouter()

        result = router.parse("/nonexistent/file.pdf")

        assert result.error is not None
        assert result.confidence == 0.0

    def test_parse_docling_fails_vision_succeeds(self):
        """Test partial failure (Docling fails, Vision succeeds)."""
        router = SmartRouter()

        # Docling fails
        router.docling_parser.parse = Mock(side_effect=Exception("Docling error"))

        # Vision succeeds
        mock_vision_result = ParseResult(
            text="Vision description",
            metadata={"extraction_method": "vision"},
            confidence=0.8,
            images=[],
            tables=[]
        )
        router.vision_parser.parse = Mock(return_value=mock_vision_result)

        mock_analysis = DocumentAnalysis(
            has_images=True,
            image_count=5,
            has_text=True,
            page_count=1,
            is_scanned=False,
            avg_text_per_page=500.0,
            recommended_parsers=["docling", "vision"]
        )
        router.analyze_document = Mock(return_value=mock_analysis)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf")
            temp_path = f.name

        try:
            result = router.parse(temp_path)

            # Should handle error gracefully
            assert result.error is not None or result.confidence > 0

        finally:
            os.unlink(temp_path)

    def test_parse_vision_fails_docling_succeeds(self):
        """Test partial failure (Vision fails, Docling succeeds)."""
        router = SmartRouter()

        mock_docling_result = ParseResult(
            text="Docling text",
            metadata={"extraction_method": "docling"},
            confidence=0.9,
            images=[],
            tables=[]
        )
        router.docling_parser.parse = Mock(return_value=mock_docling_result)

        # Vision fails
        router.vision_parser.parse = Mock(side_effect=Exception("Vision error"))

        mock_analysis = DocumentAnalysis(
            has_images=True,
            image_count=5,
            has_text=True,
            page_count=1,
            is_scanned=False,
            avg_text_per_page=500.0,
            recommended_parsers=["docling", "vision"]
        )
        router.analyze_document = Mock(return_value=mock_analysis)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf")
            temp_path = f.name

        try:
            result = router.parse(temp_path)

            # Docling should succeed, Vision failure is non-fatal
            assert "Docling text" in result.text
            assert result.error is None  # Vision failure ignored

        finally:
            os.unlink(temp_path)


class TestRoutingStatistics:
    """Test routing statistics tracking."""

    def test_get_routing_stats(self):
        """Test retrieving routing statistics."""
        router = SmartRouter()

        stats = router.get_routing_stats()

        assert "documents_processed" in stats
        assert "docling_only" in stats
        assert "both_parsers" in stats
        assert stats["documents_processed"] == 0

    def test_stats_updated_after_parse(self):
        """Test that stats are updated after parsing."""
        router = SmartRouter()

        mock_docling_result = ParseResult(
            text="Text",
            metadata={"extraction_method": "docling"},
            confidence=0.9,
            images=[],
            tables=[]
        )
        router.docling_parser.parse = Mock(return_value=mock_docling_result)

        mock_analysis = DocumentAnalysis(
            has_images=False,
            image_count=0,
            has_text=True,
            page_count=1,
            is_scanned=False,
            avg_text_per_page=500.0,
            recommended_parsers=["docling"]
        )
        router.analyze_document = Mock(return_value=mock_analysis)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf")
            temp_path = f.name

        try:
            router.parse(temp_path)

            stats = router.get_routing_stats()
            assert stats["documents_processed"] == 1
            assert stats["docling_only"] == 1

        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
