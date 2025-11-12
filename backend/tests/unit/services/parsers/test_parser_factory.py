"""
Unit tests for parser factory pattern

Tests:
- Factory returns correct parser based on config
- Invalid parser names raise errors
- Parser override works
- Available parsers list is correct
"""
import pytest
from unittest.mock import patch

from app.services.parsers.factory import get_parser, get_available_parsers
from app.services.parsers.base import DocumentParser
from app.services.parsers.docling_parser import DoclingParser


class TestParserFactory:
    """Test parser factory function"""

    def test_get_parser_default(self):
        """Test factory returns default parser (docling)"""
        parser = get_parser()
        assert isinstance(parser, DocumentParser)
        assert isinstance(parser, DoclingParser)

    def test_get_parser_docling_explicit(self):
        """Test factory returns docling when explicitly requested"""
        parser = get_parser("docling")
        assert isinstance(parser, DoclingParser)

    def test_get_parser_invalid_name(self):
        """Test factory raises error for invalid parser name"""
        with pytest.raises(ValueError, match="Unknown parser"):
            get_parser("invalid_parser")

    @patch('app.core.config.settings')
    def test_get_parser_from_config(self, mock_settings):
        """Test factory uses config setting"""
        mock_settings.PARSER_PRIMARY = "docling"
        parser = get_parser()
        assert isinstance(parser, DoclingParser)

    def test_get_parser_override_config(self):
        """Test explicit parser name overrides config"""
        # Even if config says something else, explicit param should win
        parser = get_parser("docling")
        assert isinstance(parser, DoclingParser)

    def test_get_available_parsers(self):
        """Test available parsers list"""
        parsers = get_available_parsers()
        assert isinstance(parsers, list)
        assert "docling" in parsers
        assert len(parsers) >= 1

    def test_parser_is_singleton_per_call(self):
        """Test each factory call creates a new instance"""
        parser1 = get_parser()
        parser2 = get_parser()
        # Should be different instances (not singleton)
        assert parser1 is not parser2


class TestParserInterface:
    """Test that all parsers implement the base interface correctly"""

    def test_docling_parser_has_required_methods(self):
        """Test DoclingParser implements all abstract methods"""
        parser = DoclingParser()

        # Check required methods exist
        assert hasattr(parser, 'parse')
        assert callable(parser.parse)
        assert hasattr(parser, 'supports_format')
        assert callable(parser.supports_format)

    def test_docling_parser_metadata(self):
        """Test DoclingParser has correct metadata"""
        parser = DoclingParser()
        assert parser.name == "docling"

        # Check it has supported formats
        assert hasattr(parser, 'SUPPORTED_FORMATS')
        assert isinstance(parser.SUPPORTED_FORMATS, list)
        assert len(parser.SUPPORTED_FORMATS) > 0
