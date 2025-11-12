"""
Unit tests for Vision API parser (Phase 2.4).

Tests Vision API integration, cost tracking, image processing, and error handling.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.services.parsers.vision_parser import VisionParser, VisionCostTracker
from app.core.config import settings


class TestVisionCostTracker:
    """Test Vision API cost tracking."""

    def test_cost_tracker_initialization(self):
        """Test cost tracker starts at zero."""
        tracker = VisionCostTracker()

        assert tracker.images_processed == 0
        assert tracker.total_tokens == 0
        assert tracker.estimated_cost == 0.0
        assert tracker.warnings == []

    def test_track_single_image(self):
        """Test tracking a single image."""
        tracker = VisionCostTracker()
        tracker.track_image(tokens_used=100)

        assert tracker.images_processed == 1
        assert tracker.total_tokens == 100
        assert tracker.estimated_cost == settings.VISION_COST_PER_IMAGE

    def test_track_multiple_images(self):
        """Test tracking multiple images."""
        tracker = VisionCostTracker()

        for i in range(5):
            tracker.track_image(tokens_used=100)

        assert tracker.images_processed == 5
        assert tracker.total_tokens == 500
        assert tracker.estimated_cost == settings.VISION_COST_PER_IMAGE * 5

    def test_cost_warning_threshold(self):
        """Test warning when cost approaches limit."""
        tracker = VisionCostTracker()

        # Process enough images to trigger warning
        images_needed = int(settings.VISION_WARN_COST_THRESHOLD / settings.VISION_COST_PER_IMAGE) + 1

        for _ in range(images_needed):
            tracker.track_image()

        # Should have warning
        assert len(tracker.warnings) > 0
        assert "Warning" in tracker.warnings[0]

    def test_cost_max_threshold(self):
        """Test warning when cost exceeds maximum."""
        tracker = VisionCostTracker()

        # Process enough images to exceed max
        images_needed = int(settings.VISION_MAX_COST_PER_DOC / settings.VISION_COST_PER_IMAGE) + 1

        for _ in range(images_needed):
            tracker.track_image()

        # Should have max cost warning
        assert any("Maximum cost" in w for w in tracker.warnings)

    def test_get_summary(self):
        """Test cost summary generation."""
        tracker = VisionCostTracker()
        tracker.track_image(tokens_used=150)

        summary = tracker.get_summary()

        assert summary["images_processed"] == 1
        assert summary["total_tokens"] == 150
        assert summary["estimated_cost"] > 0
        assert "warnings" in summary


class TestVisionParserBasics:
    """Test basic Vision parser functionality."""

    def test_parser_initialization(self):
        """Test Vision parser initialization."""
        parser = VisionParser()

        assert parser.name == "vision"
        assert isinstance(parser.cost_tracker, VisionCostTracker)

    def test_supports_format_images(self):
        """Test that parser supports image formats."""
        parser = VisionParser()

        assert parser.supports_format("png")
        assert parser.supports_format("jpg")
        assert parser.supports_format("jpeg")
        assert parser.supports_format("gif")

    def test_supports_format_pdf(self):
        """Test that parser supports PDF format."""
        parser = VisionParser()

        assert parser.supports_format("pdf")

    def test_does_not_support_unknown_format(self):
        """Test that parser rejects unknown formats."""
        parser = VisionParser()

        assert not parser.supports_format("docx")
        assert not parser.supports_format("txt")
        assert not parser.supports_format("unknown")

    def test_check_api_key_missing(self):
        """Test warning when API key missing."""
        original_key = settings.OPENAI_API_KEY
        settings.OPENAI_API_KEY = None

        try:
            parser = VisionParser()
            # Should not raise, just log warning
            assert parser.client is None

        finally:
            settings.OPENAI_API_KEY = original_key

    def test_vision_prompt_building(self):
        """Test vision prompt template building."""
        parser = VisionParser()

        prompt = parser._build_vision_prompt()

        assert "visualization" in prompt.lower()
        assert "data" in prompt.lower()
        assert "insights" in prompt.lower()

    def test_vision_prompt_with_context(self):
        """Test vision prompt with additional context."""
        parser = VisionParser()

        prompt = parser._build_vision_prompt(context="Financial report Q4 2024")

        assert "Financial report Q4 2024" in prompt
        assert "visualization" in prompt.lower()

    def test_is_likely_chart(self):
        """Test chart detection heuristic."""
        parser = VisionParser()

        # Should detect as chart
        assert parser._is_likely_chart("This is a bar chart showing sales data")
        assert parser._is_likely_chart("Line graph with trend over time")
        assert parser._is_likely_chart("Pie chart distribution")

        # Should not detect as chart
        assert not parser._is_likely_chart("A photo of a building")
        assert not parser._is_likely_chart("Portrait image")


class TestVisionParserWithMocks:
    """Test Vision parser with mocked API calls."""

    def test_parse_disabled_config(self):
        """Test parsing when vision is disabled in config."""
        original_enabled = settings.ENABLE_VISION_PARSING
        settings.ENABLE_VISION_PARSING = False

        try:
            parser = VisionParser()

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(b"fake image data")
                temp_path = f.name

            try:
                result = parser.parse(temp_path)

                assert result.error is not None
                assert "disabled" in result.error.lower()
                assert result.confidence == 0.0

            finally:
                os.unlink(temp_path)

        finally:
            settings.ENABLE_VISION_PARSING = original_enabled

    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file."""
        parser = VisionParser()
        result = parser.parse("/nonexistent/file.jpg")

        assert result.error is not None
        assert result.confidence == 0.0

    def test_parse_single_image_success(self):
        """Test successful parsing of single image."""
        # Mock OpenAI client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="A bar chart showing sales growth"))]
        mock_response.usage = Mock(total_tokens=150)
        mock_client.chat.completions.create.return_value = mock_response

        parser = VisionParser()
        parser.client = mock_client

        # Create fake image file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, mode='wb') as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            result = parser.parse(temp_path)

            assert result.error is None
            assert "sales growth" in result.text.lower()
            assert result.confidence > 0
            assert result.metadata["extraction_method"] == "vision_single_image"

            # Check cost tracking
            cost_summary = result.metadata.get("vision_cost_tracking")
            assert cost_summary is not None
            assert cost_summary["images_processed"] == 1

        finally:
            os.unlink(temp_path)

    def test_interpret_image_api_call(self):
        """Test that Vision API is called correctly."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test description"))]
        mock_response.usage = Mock(total_tokens=100)
        mock_client.chat.completions.create.return_value = mock_response

        parser = VisionParser()
        parser.client = mock_client

        # Test interpret_image_data
        image_data = b"fake image bytes"
        description = parser.interpret_image_data(image_data)

        assert description == "Test description"
        assert mock_client.chat.completions.create.called

        # Check API call parameters
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == settings.VISION_API_MODEL
        assert call_args.kwargs["max_tokens"] == settings.VISION_API_MAX_TOKENS

    def test_interpret_image_api_failure(self):
        """Test handling of Vision API failure."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        parser = VisionParser()
        parser.client = mock_client

        image_data = b"fake image bytes"
        description = parser.interpret_image_data(image_data)

        # Should return empty string on error
        assert description == ""

        # Should still track cost
        assert parser.cost_tracker.images_processed == 1


class TestPDFImageExtraction:
    """Test PDF image extraction functionality."""

    @pytest.fixture
    def sample_pdf_with_images(self):
        """Create a sample PDF with embedded images."""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from PIL import Image
            import io

            # Create a simple image
            img = Image.new('RGB', (100, 100), color='red')
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)

            # Create PDF with image
            pdf_buffer = io.BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=letter)
            c.drawString(100, 750, "PDF with image")

            # Note: Adding image to PDF with reportlab requires more setup
            # For now, just create simple PDF
            c.save()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode='wb') as f:
                f.write(pdf_buffer.getvalue())
                temp_path = f.name

            yield temp_path

            os.unlink(temp_path)

        except ImportError:
            pytest.skip("reportlab or Pillow not available")

    def test_extract_images_from_pdf_no_pymupdf(self):
        """Test graceful handling when PyMuPDF not available."""
        parser = VisionParser()

        with patch.dict('sys.modules', {'fitz': None}):
            images = parser.extract_images_from_pdf("/fake/path.pdf")

            # Should return empty list, not raise
            assert images == []


class TestVisionConfiguration:
    """Test Vision API configuration."""

    def test_config_settings_exist(self):
        """Test that all Vision configuration settings exist."""
        assert hasattr(settings, 'ENABLE_VISION_PARSING')
        assert hasattr(settings, 'VISION_API_MODEL')
        assert hasattr(settings, 'VISION_API_MAX_IMAGES_PER_DOC')
        assert hasattr(settings, 'VISION_COST_PER_IMAGE')
        assert hasattr(settings, 'VISION_ENABLE_COST_TRACKING')

    def test_config_values_valid(self):
        """Test that configuration values are valid."""
        assert settings.VISION_API_MODEL in ["gpt-4o-mini", "gpt-4o", "gpt-4-vision-preview"]
        assert settings.VISION_API_MAX_TOKENS > 0
        assert settings.VISION_API_MAX_IMAGES_PER_DOC > 0
        assert settings.VISION_COST_PER_IMAGE >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
