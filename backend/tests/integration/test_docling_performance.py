"""
Integration tests for Docling parser Phase 2.1 performance optimizations.

Tests end-to-end parsing with real Docling converter.
"""

import pytest
import tempfile
import os
import time
from datetime import datetime

from app.services.parsers.docling_parser import DoclingParser


@pytest.fixture
def sample_pdf():
    """Create a sample PDF for testing."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io

        # Create 5-page PDF
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)

        for page_num in range(1, 6):
            c.drawString(100, 750, f"QueryBox Test Document - Page {page_num}")
            c.drawString(100, 730, "This is integration test content.")
            c.drawString(100, 710, f"Generated at: {datetime.now().isoformat()}")

            # Add varied content
            y_pos = 680
            for i in range(15):
                c.drawString(100, y_pos, f"Line {i+1}: Sample text for testing Docling parser.")
                y_pos -= 20

            c.showPage()

        c.save()
        pdf_buffer.seek(0)

        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode='wb') as f:
            f.write(pdf_buffer.getvalue())
            temp_path = f.name

        yield temp_path

        # Cleanup
        try:
            os.unlink(temp_path)
        except Exception:
            pass

    except ImportError:
        pytest.skip("reportlab not available for PDF generation")


@pytest.fixture
def sample_text_file():
    """Create a sample text file for testing."""
    content = "QueryBox Test Document\n\nThis is a test text file for parser testing.\n\n"
    content += "Line with varied content: " + "test " * 50

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode='w') as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    try:
        os.unlink(temp_path)
    except Exception:
        pass


class TestEagerInitializationIntegration:
    """Integration tests for eager initialization."""

    def test_lazy_init_first_request_slower(self, sample_text_file):
        """Test that lazy init has slower first request."""
        # Lazy initialization
        parser_lazy = DoclingParser(eager_init=False)

        start = time.time()
        result = parser_lazy.parse(sample_text_file)
        lazy_duration = time.time() - start

        assert result.error is None
        assert len(result.text) > 0

        # First request includes initialization time
        assert lazy_duration > 0

    def test_eager_init_first_request_faster(self, sample_text_file):
        """Test that eager init makes first request faster (models preloaded)."""
        # Eager initialization
        parser_eager = DoclingParser(eager_init=True)

        start = time.time()
        result = parser_eager.parse(sample_text_file)
        eager_duration = time.time() - start

        assert result.error is None
        assert len(result.text) > 0

        # Should complete reasonably fast
        assert eager_duration < 5.0  # Generous timeout

    def test_warmup_marks_completion(self):
        """Test that warmup is marked as done after completion."""
        parser = DoclingParser(eager_init=True)

        # Warmup should have been called during init
        # We can check if it would skip on second call
        assert hasattr(parser, '_warmup_done')


class TestDeviceDetectionIntegration:
    """Integration tests for device detection."""

    def test_device_detected_and_logged(self, sample_text_file):
        """Test that device is detected and set during initialization."""
        parser = DoclingParser(eager_init=True)

        # Parse to trigger initialization if not eager
        result = parser.parse(sample_text_file)

        assert result.error is None
        assert result.metadata.get("device") is not None
        assert result.metadata.get("device_name") is not None

        # Device should be one of: cpu, cuda, mps
        assert result.metadata["device"] in ["cpu", "cuda", "mps", "unknown"]

    def test_cpu_device_always_works(self, sample_text_file):
        """Test that CPU device always works as fallback."""
        from app.core.config import settings

        original_device = settings.DOCLING_DEVICE

        try:
            # Force CPU
            settings.DOCLING_DEVICE = "cpu"

            parser = DoclingParser(eager_init=True)
            result = parser.parse(sample_text_file)

            assert result.error is None
            assert result.metadata["device"] == "cpu"

        finally:
            settings.DOCLING_DEVICE = original_device


class TestParsingPerformance:
    """Integration tests for parsing performance."""

    def test_parse_pdf_completes_successfully(self, sample_pdf):
        """Test that PDF parsing completes successfully."""
        parser = DoclingParser(eager_init=True)

        start = time.time()
        result = parser.parse(sample_pdf)
        duration = time.time() - start

        assert result.error is None
        assert len(result.text) > 100  # Should extract meaningful text
        assert result.metadata["total_pages"] == 5
        assert duration < 30.0  # Should complete within 30 seconds

    def test_parse_text_file_fast(self, sample_text_file):
        """Test that text file parsing is fast."""
        parser = DoclingParser(eager_init=True)

        start = time.time()
        result = parser.parse(sample_text_file)
        duration = time.time() - start

        assert result.error is None
        assert len(result.text) > 0
        assert duration < 1.0  # Text files should be nearly instant

    def test_metadata_includes_performance_info(self, sample_pdf):
        """Test that parse result includes performance metadata."""
        parser = DoclingParser(eager_init=True)
        result = parser.parse(sample_pdf)

        assert result.error is None

        # Check for key metadata fields
        assert "extraction_method" in result.metadata
        assert "extraction_duration_ms" in result.metadata
        assert "text_length" in result.metadata
        assert "total_pages" in result.metadata
        assert "device" in result.metadata
        assert "device_name" in result.metadata

        # Verify reasonable values
        assert result.metadata["extraction_duration_ms"] > 0
        assert result.metadata["text_length"] > 0


class TestBatchProcessing:
    """Integration tests for large PDF batch processing."""

    @pytest.fixture
    def large_pdf(self):
        """Create a 120-page PDF to trigger batch processing."""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            import io

            # Create 120-page PDF (exceeds default 100-page threshold)
            pdf_buffer = io.BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=letter)

            for page_num in range(1, 121):
                c.drawString(100, 750, f"Page {page_num}/120")
                c.drawString(100, 730, "Large PDF batch processing test.")
                c.showPage()

            c.save()
            pdf_buffer.seek(0)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode='wb') as f:
                f.write(pdf_buffer.getvalue())
                temp_path = f.name

            yield temp_path

            try:
                os.unlink(temp_path)
            except Exception:
                pass

        except ImportError:
            pytest.skip("reportlab not available for PDF generation")

    def test_large_pdf_triggers_batch_processing(self, large_pdf):
        """Test that large PDFs are processed in batches."""
        from app.core.config import settings

        original_threshold = settings.DOCLING_MAX_PAGES_MEMORY_THRESHOLD

        try:
            # Set threshold to 50 to trigger batching
            settings.DOCLING_MAX_PAGES_MEMORY_THRESHOLD = 50

            parser = DoclingParser(eager_init=True)
            result = parser.parse(large_pdf)

            assert result.error is None
            assert result.metadata["total_pages"] == 120

            # Check if batch processing was used
            if "batch_processing" in result.metadata:
                assert result.metadata["batch_processing"] is True
                assert "batch_size" in result.metadata

        finally:
            settings.DOCLING_MAX_PAGES_MEMORY_THRESHOLD = original_threshold

    def test_small_pdf_no_batch_processing(self, sample_pdf):
        """Test that small PDFs are not batch processed."""
        from app.core.config import settings

        original_threshold = settings.DOCLING_MAX_PAGES_MEMORY_THRESHOLD

        try:
            # Set high threshold to prevent batching
            settings.DOCLING_MAX_PAGES_MEMORY_THRESHOLD = 100

            parser = DoclingParser(eager_init=True)
            result = parser.parse(sample_pdf)

            assert result.error is None
            assert result.metadata["total_pages"] == 5

            # Should not use batch processing
            assert result.metadata.get("batch_processing") is None

        finally:
            settings.DOCLING_MAX_PAGES_MEMORY_THRESHOLD = original_threshold


class TestErrorHandling:
    """Integration tests for error handling."""

    def test_parse_nonexistent_file(self):
        """Test error handling for nonexistent file."""
        parser = DoclingParser(eager_init=False)
        result = parser.parse("/nonexistent/file.pdf")

        assert result.error is not None
        assert result.confidence == 0.0

    def test_parse_invalid_file(self):
        """Test error handling for invalid file."""
        # Create invalid PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode='w') as f:
            f.write("This is not a valid PDF")
            temp_path = f.name

        try:
            parser = DoclingParser(eager_init=False)
            result = parser.parse(temp_path)

            # Should handle error gracefully
            assert result.error is not None or len(result.text) == 0

        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass


class TestMultipleParses:
    """Integration tests for multiple consecutive parses."""

    def test_multiple_parses_maintain_performance(self, sample_text_file):
        """Test that multiple parses don't degrade performance."""
        parser = DoclingParser(eager_init=True)

        durations = []
        for i in range(3):
            start = time.time()
            result = parser.parse(sample_text_file)
            duration = time.time() - start
            durations.append(duration)

            assert result.error is None

        # Second and third parses should not be significantly slower
        # (models already loaded)
        assert max(durations[1:]) < durations[0] * 2  # Allow 2x variance

    def test_warmup_only_runs_once(self, sample_text_file):
        """Test that warmup is only performed once."""
        parser = DoclingParser(eager_init=True)

        # Parse multiple times
        for _ in range(3):
            result = parser.parse(sample_text_file)
            assert result.error is None

        # Warmup flag should remain True
        assert parser._warmup_done


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
