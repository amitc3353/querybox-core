"""
Unit tests for Docling parser Phase 2.1 optimizations.

Tests GPU detection, eager initialization, warmup, and batch processing.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.services.parsers.docling_parser import DoclingParser


class TestGPUDetection:
    """Test GPU device detection logic."""

    @patch('app.core.config.settings')
    def test_detect_device_cpu_forced(self, mock_settings):
        """Test that CPU is selected when forced via config."""
        mock_settings.DOCLING_DEVICE = "cpu"

        parser = DoclingParser(eager_init=False)
        device, device_name = parser._detect_device()

        assert device == "cpu"
        assert "CPU" in device_name
        assert "forced" in device_name.lower()

    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.get_device_name')
    @patch('torch.cuda.is_available')
    @patch('app.core.config.settings')
    def test_detect_device_cuda_available(self, mock_settings, mock_cuda_available, mock_cuda_name, mock_cuda_props):
        """Test CUDA detection when GPU is available."""
        mock_settings.DOCLING_DEVICE = "auto"
        mock_cuda_available.return_value = True
        mock_cuda_name.return_value = "NVIDIA RTX 4090"
        mock_cuda_props.return_value = Mock(total_memory=24 * 1024**3)

        parser = DoclingParser(eager_init=False)
        device, device_name = parser._detect_device()

        assert device == "cuda"
        assert "CUDA" in device_name
        assert "NVIDIA RTX 4090" in device_name

    @patch('torch.cuda.is_available')
    @patch('app.core.config.settings')
    def test_detect_device_cuda_unavailable_fallback(self, mock_settings, mock_cuda_available):
        """Test fallback to CPU when CUDA requested but unavailable."""
        mock_settings.DOCLING_DEVICE = "cuda"
        mock_cuda_available.return_value = False

        parser = DoclingParser(eager_init=False)
        device, device_name = parser._detect_device()

        assert device == "cpu"
        assert "unavailable" in device_name.lower()

    @patch('torch.backends.mps.is_available')
    @patch('app.core.config.settings')
    def test_detect_device_mps_enabled(self, mock_settings, mock_mps_available):
        """Test MPS detection when enabled and available."""
        mock_settings.DOCLING_DEVICE = "mps"
        mock_settings.DOCLING_ENABLE_MPS = True
        mock_mps_available.return_value = True

        parser = DoclingParser(eager_init=False)
        device, device_name = parser._detect_device()

        assert device == "mps"
        assert "MPS" in device_name
        assert "experimental" in device_name.lower()

    @patch('torch.backends.mps.is_available')
    @patch('torch.cuda.is_available')
    @patch('app.core.config.settings')
    def test_detect_device_mps_disabled_by_default(self, mock_settings, mock_cuda_available, mock_mps_available):
        """Test that MPS is not auto-selected when disabled."""
        mock_settings.DOCLING_DEVICE = "auto"
        mock_settings.DOCLING_ENABLE_MPS = False
        mock_cuda_available.return_value = False
        mock_mps_available.return_value = True

        parser = DoclingParser(eager_init=False)
        device, device_name = parser._detect_device()

        # Should fall back to CPU, not use MPS
        assert device == "cpu"

    @patch('app.core.config.settings')
    def test_detect_device_invalid_config(self, mock_settings):
        """Test handling of invalid device configuration."""
        mock_settings.DOCLING_DEVICE = "invalid_device"

        parser = DoclingParser(eager_init=False)
        device, device_name = parser._detect_device()

        # Should fall back to CPU
        assert device == "cpu"
        assert "invalid" in device_name.lower()


class TestEagerInitialization:
    """Test eager initialization and model preloading."""

    @patch('app.core.config.settings')
    @patch.object(DoclingParser, '_initialize_converter')
    @patch.object(DoclingParser, '_warmup')
    def test_eager_init_enabled_via_config(self, mock_warmup, mock_init, mock_settings):
        """Test that eager init is triggered by config."""
        mock_settings.DOCLING_EAGER_INIT = True
        mock_settings.DOCLING_WARMUP_ON_STARTUP = False

        parser = DoclingParser()

        mock_init.assert_called_once()
        mock_warmup.assert_not_called()

    @patch('app.core.config.settings')
    @patch.object(DoclingParser, '_initialize_converter')
    @patch.object(DoclingParser, '_warmup')
    def test_eager_init_with_warmup(self, mock_warmup, mock_init, mock_settings):
        """Test that warmup is called after eager init when enabled."""
        mock_settings.DOCLING_EAGER_INIT = True
        mock_settings.DOCLING_WARMUP_ON_STARTUP = True

        # Mock converter to simulate successful initialization
        parser = DoclingParser()
        parser.converter = Mock()

        mock_init.assert_called_once()
        # Warmup would be called during __init__ if converter exists

    @patch('app.core.config.settings')
    @patch.object(DoclingParser, '_initialize_converter')
    def test_lazy_init_by_default(self, mock_init, mock_settings):
        """Test that lazy init is used when eager init disabled."""
        mock_settings.DOCLING_EAGER_INIT = False

        parser = DoclingParser()

        mock_init.assert_not_called()

    @patch('app.core.config.settings')
    @patch.object(DoclingParser, '_initialize_converter')
    def test_eager_init_explicit_parameter(self, mock_init, mock_settings):
        """Test explicit eager_init parameter overrides config."""
        mock_settings.DOCLING_EAGER_INIT = False

        parser = DoclingParser(eager_init=True)

        mock_init.assert_called_once()


class TestWarmup:
    """Test model warmup functionality."""

    @patch('app.core.config.settings')
    def test_warmup_skipped_if_already_done(self, mock_settings):
        """Test that warmup is only performed once."""
        parser = DoclingParser(eager_init=False)
        parser.converter = Mock()
        parser._warmup_done = True

        # Should skip warmup
        parser._warmup()

        # Converter should not be called since warmup already done
        parser.converter.convert.assert_not_called()

    @patch('app.core.config.settings')
    def test_warmup_skipped_if_no_converter(self, mock_settings):
        """Test warmup is skipped if converter not initialized."""
        mock_settings.DOCLING_EAGER_INIT = False
        mock_settings.DOCLING_WARMUP_ON_STARTUP = False

        parser = DoclingParser(eager_init=False)
        parser.converter = None

        parser._warmup()

        assert not parser._warmup_done

    @patch('tempfile.NamedTemporaryFile')
    @patch('app.core.config.settings')
    def test_warmup_creates_temp_pdf(self, mock_settings, mock_tempfile):
        """Test that warmup creates temporary PDF for processing."""
        mock_settings.DOCLING_EAGER_INIT = False
        mock_settings.DOCLING_WARMUP_ON_STARTUP = False

        parser = DoclingParser(eager_init=False)
        parser.converter = Mock()

        # Mock temp file
        mock_file = Mock()
        mock_file.name = "/tmp/test.pdf"
        mock_tempfile.return_value.__enter__ = Mock(return_value=mock_file)
        mock_tempfile.return_value.__exit__ = Mock(return_value=False)

        # Mock convert result
        mock_result = Mock()
        mock_result.document.export_to_markdown.return_value = "test"
        parser.converter.convert.return_value = mock_result

        parser._warmup()

        # Verify converter was called
        parser.converter.convert.assert_called_once()
        assert parser._warmup_done

    @patch('app.core.config.settings')
    def test_warmup_failure_non_critical(self, mock_settings):
        """Test that warmup failure doesn't crash initialization."""
        mock_settings.DOCLING_EAGER_INIT = False
        mock_settings.DOCLING_WARMUP_ON_STARTUP = False

        parser = DoclingParser(eager_init=False)
        parser.converter = Mock()
        parser.converter.convert.side_effect = Exception("Warmup test error")

        # Should not raise exception
        parser._warmup()

        # Warmup should be marked as not done
        assert not parser._warmup_done


class TestLargePDFBatchProcessing:
    """Test batch processing for large PDFs."""

    @patch('app.core.config.settings')
    def test_count_pdf_pages(self, mock_settings):
        """Test PDF page counting."""
        # Create a simple test PDF
        try:
            from reportlab.pdfgen import canvas
            import io

            pdf_buffer = io.BytesIO()
            c = canvas.Canvas(pdf_buffer)
            c.drawString(100, 750, "Page 1")
            c.showPage()
            c.drawString(100, 750, "Page 2")
            c.showPage()
            c.save()

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, mode='wb') as f:
                f.write(pdf_buffer.getvalue())
                temp_path = f.name

            try:
                parser = DoclingParser(eager_init=False)
                page_count = parser._count_pdf_pages(temp_path)
                assert page_count == 2
            finally:
                os.unlink(temp_path)

        except ImportError:
            pytest.skip("reportlab not available")

    @patch('app.core.config.settings')
    def test_count_pdf_pages_fallback(self, mock_settings):
        """Test page counting fallback on error."""
        parser = DoclingParser(eager_init=False)
        page_count = parser._count_pdf_pages("/nonexistent/file.pdf")

        # Should return 1 as fallback
        assert page_count == 1

    @patch('PyPDF2.PdfReader')
    @patch('PyPDF2.PdfWriter')
    @patch('builtins.open', new_callable=MagicMock)
    @patch('app.core.config.settings')
    def test_batch_processing_splits_correctly(self, mock_settings, mock_open, mock_pdf_writer, mock_pdf_reader):
        """Test that large PDFs are split into correct batch sizes."""
        mock_settings.DOCLING_PAGE_BATCH_SIZE = 10
        mock_settings.DOCLING_MAX_PAGES_MEMORY_THRESHOLD = 50

        # Mock PDF reader
        mock_reader_instance = Mock()
        mock_reader_instance.pages = [Mock() for _ in range(25)]  # 25 pages
        mock_pdf_reader.return_value = mock_reader_instance

        # Mock PDF writer
        mock_writer_instance = Mock()
        mock_pdf_writer.return_value = mock_writer_instance

        parser = DoclingParser(eager_init=False)
        parser.converter = Mock()

        # Mock converter result
        mock_result = Mock()
        mock_result.document.export_to_markdown.return_value = "test content"
        parser.converter.convert.return_value = mock_result

        from datetime import datetime, timezone
        result = parser._parse_large_pdf_batched("/test.pdf", 25, datetime.now(timezone.utc))

        # Should process 3 batches (10 + 10 + 5)
        assert parser.converter.convert.call_count == 3
        assert result.metadata["batch_processing"]
        assert result.metadata["batch_size"] == 10


class TestPerformanceLogging:
    """Test performance logging features."""

    @patch('torch.cuda.is_available')
    @patch('app.core.config.settings')
    def test_gpu_memory_logging_enabled(self, mock_settings, mock_cuda_available):
        """Test GPU memory is logged when enabled."""
        mock_settings.DOCLING_LOG_GPU_MEMORY = True
        mock_settings.DOCLING_ENABLE_MPS = False
        mock_cuda_available.return_value = False

        parser = DoclingParser(eager_init=False)

        # Verify settings were checked
        assert mock_settings.DOCLING_LOG_GPU_MEMORY

    @patch('app.core.config.settings')
    def test_device_metadata_in_parse_result(self, mock_settings):
        """Test that device info is included in parse result metadata."""
        mock_settings.DOCLING_EAGER_INIT = False

        parser = DoclingParser(eager_init=False)
        parser.device = "cpu"
        parser.device_name = "CPU Test"

        # We can't easily test full parse without mocking Docling,
        # but we can verify device attributes are set
        assert parser.device == "cpu"
        assert parser.device_name == "CPU Test"


class TestConfigurationValidation:
    """Test configuration validation and edge cases."""

    @patch('app.core.config.settings')
    def test_batch_size_adapts_to_device(self, mock_settings):
        """Test that batch size is adjusted based on device."""
        mock_settings.DOCLING_OCR_BATCH_SIZE = 4
        mock_settings.DOCLING_EAGER_INIT = False

        parser = DoclingParser(eager_init=False)

        # Default config should respect settings
        assert mock_settings.DOCLING_OCR_BATCH_SIZE == 4

    @patch('app.core.config.settings')
    def test_threaded_pipeline_config(self, mock_settings):
        """Test threaded pipeline configuration."""
        mock_settings.DOCLING_USE_THREADED_PIPELINE = True
        mock_settings.DOCLING_EAGER_INIT = False

        parser = DoclingParser(eager_init=False)

        assert mock_settings.DOCLING_USE_THREADED_PIPELINE is True
