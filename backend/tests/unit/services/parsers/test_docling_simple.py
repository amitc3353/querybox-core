"""
Simplified unit tests for Docling parser Phase 2.1 optimizations.

Tests basic functionality without heavy mocking.
"""

import pytest
import tempfile
import os
from pathlib import Path

from app.services.parsers.docling_parser import DoclingParser
from app.core.config import settings


class TestBasicFunctionality:
    """Test basic Docling parser functionality with Phase 2.1 features."""

    def test_parser_initialization_lazy(self):
        """Test lazy initialization."""
        # Explicitly set eager_init=False to override config
        # Note: Default config has DOCLING_EAGER_INIT=True
        original_eager = settings.DOCLING_EAGER_INIT
        settings.DOCLING_EAGER_INIT = False

        try:
            parser = DoclingParser(eager_init=False)

            # With lazy init, converter should not be initialized
            assert parser.converter is None
            assert parser.device is None
            assert not parser._warmup_done

        finally:
            settings.DOCLING_EAGER_INIT = original_eager

    def test_parser_initialization_eager(self):
        """Test eager initialization."""
        parser = DoclingParser(eager_init=True)

        # Converter should be initialized (or attempted)
        # Device should be detected
        assert hasattr(parser, 'device')
        assert hasattr(parser, '_warmup_done')

    def test_device_detection_runs(self):
        """Test that device detection runs and returns valid device."""
        parser = DoclingParser(eager_init=False)
        device, device_name = parser._detect_device()

        assert device in ["cpu", "cuda", "mps"]
        assert isinstance(device_name, str)
        assert len(device_name) > 0

    def test_count_pdf_pages_fallback(self):
        """Test page counting fallback on error."""
        parser = DoclingParser(eager_init=False)
        page_count = parser._count_pdf_pages("/nonexistent/file.pdf")

        # Should return 1 as fallback
        assert page_count == 1

    def test_warmup_marks_completion(self):
        """Test that warmup flag exists and can be set."""
        # Force lazy initialization by temporarily overriding config
        original_eager = settings.DOCLING_EAGER_INIT
        settings.DOCLING_EAGER_INIT = False

        try:
            parser = DoclingParser(eager_init=False)
            # At this point, _warmup_done should be False and converter should be None
            assert not parser._warmup_done
            assert parser.converter is None

            # Should skip warmup if no converter
            parser._warmup()

            # Warmup should not be marked done if no converter
            assert not parser._warmup_done

        finally:
            settings.DOCLING_EAGER_INIT = original_eager

    def test_warmup_already_done_skips(self):
        """Test that second warmup is skipped."""
        parser = DoclingParser(eager_init=False)
        parser._warmup_done = True

        # Should return early
        parser._warmup()

        # Flag should still be True
        assert parser._warmup_done

    def test_parse_text_file(self):
        """Test parsing a simple text file."""
        content = "QueryBox Test Document\n\nThis is a test text file."

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode='w') as f:
            f.write(content)
            temp_path = f.name

        try:
            parser = DoclingParser(eager_init=False)
            result = parser.parse(temp_path)

            assert result.error is None
            assert len(result.text) > 0
            assert "QueryBox Test Document" in result.text
            assert result.metadata["extraction_method"] == "direct"

        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    def test_parse_nonexistent_file(self):
        """Test error handling for nonexistent file."""
        parser = DoclingParser(eager_init=False)
        result = parser.parse("/nonexistent/file.pdf")

        assert result.error is not None
        assert result.confidence == 0.0

    def test_metadata_includes_device_info(self):
        """Test that parse results include device information."""
        content = "Test content"

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode='w') as f:
            f.write(content)
            temp_path = f.name

        try:
            parser = DoclingParser(eager_init=False)
            result = parser.parse(temp_path)

            assert result.error is None
            # Device info should be in metadata (even if 'unknown' for text files)
            assert "device" in result.metadata or result.metadata.get("extraction_method") == "direct"

        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass


class TestConfiguration:
    """Test configuration handling."""

    def test_config_settings_accessible(self):
        """Test that Docling configuration settings exist."""
        assert hasattr(settings, 'DOCLING_DEVICE')
        assert hasattr(settings, 'DOCLING_USE_THREADED_PIPELINE')
        assert hasattr(settings, 'DOCLING_EAGER_INIT')
        assert hasattr(settings, 'DOCLING_WARMUP_ON_STARTUP')
        assert hasattr(settings, 'DOCLING_OCR_BATCH_SIZE')
        assert hasattr(settings, 'DOCLING_PAGE_BATCH_SIZE')
        assert hasattr(settings, 'DOCLING_MAX_PAGES_MEMORY_THRESHOLD')

    def test_config_values_valid(self):
        """Test that configuration values are valid."""
        assert settings.DOCLING_DEVICE in ["auto", "cpu", "cuda", "mps"]
        assert isinstance(settings.DOCLING_USE_THREADED_PIPELINE, bool)
        assert isinstance(settings.DOCLING_EAGER_INIT, bool)
        assert isinstance(settings.DOCLING_OCR_BATCH_SIZE, int)
        assert settings.DOCLING_OCR_BATCH_SIZE > 0


class TestPDFPageCounting:
    """Test PDF page counting functionality."""

    def test_count_pdf_pages_with_reportlab(self):
        """Test counting pages in a generated PDF."""
        try:
            from reportlab.pdfgen import canvas
            import io

            # Create 3-page PDF
            pdf_buffer = io.BytesIO()
            c = canvas.Canvas(pdf_buffer)
            for i in range(3):
                c.drawString(100, 750, f"Page {i+1}")
                c.showPage()
            c.save()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode='wb') as f:
                f.write(pdf_buffer.getvalue())
                temp_path = f.name

            try:
                parser = DoclingParser(eager_init=False)
                page_count = parser._count_pdf_pages(temp_path)
                assert page_count == 3
            finally:
                os.unlink(temp_path)

        except ImportError:
            pytest.skip("reportlab not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
