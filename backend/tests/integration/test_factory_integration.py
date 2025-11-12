"""
Integration tests for factory pattern

Tests the complete factory system working together:
- All factories can be imported
- All factories return correct types
- Config-driven selection works
- Service integration works
"""
import pytest
from unittest.mock import Mock, patch

from app.services.parsers.factory import get_parser
from app.services.embeddings.factory import get_embedding_provider
from app.services.search.vector_stores.factory import get_vector_store
from app.services.llm.factory import get_llm_provider

from app.services.parsers.base import DocumentParser
from app.services.embeddings.base import EmbeddingProvider
from app.services.search.vector_stores.base import VectorStore
from app.services.llm.base import LLMProvider


class TestFactoryIntegration:
    """Test all factories work together"""

    def test_all_factories_importable(self):
        """Test all factory modules can be imported"""
        # If this test runs, all imports succeeded
        assert get_parser is not None
        assert get_embedding_provider is not None
        assert get_vector_store is not None
        assert get_llm_provider is not None

    def test_all_factories_return_correct_types(self):
        """Test all factories return instances of correct base classes"""
        # Parser
        parser = get_parser()
        assert isinstance(parser, DocumentParser)

        # Embedding provider
        embedder = get_embedding_provider()
        assert isinstance(embedder, EmbeddingProvider)

        # Vector store (requires db)
        mock_db = Mock()
        store = get_vector_store(db=mock_db)
        assert isinstance(store, VectorStore)

        # LLM provider
        llm = get_llm_provider()
        assert isinstance(llm, LLMProvider)

    def test_factories_work_with_config_override(self):
        """Test all factories accept explicit provider names"""
        # Parser
        parser = get_parser("docling")
        assert parser is not None

        # Embedding
        embedder = get_embedding_provider("bge-m3")
        assert embedder is not None

        # Vector store
        mock_db = Mock()
        store = get_vector_store("pgvector", db=mock_db)
        assert store is not None

        # LLM
        llm = get_llm_provider("ollama")
        assert llm is not None

    def test_invalid_providers_raise_errors(self):
        """Test all factories raise errors for invalid providers"""
        # Parser
        with pytest.raises(ValueError):
            get_parser("invalid")

        # Embedding
        with pytest.raises(ValueError):
            get_embedding_provider("invalid")

        # Vector store
        with pytest.raises(ValueError):
            mock_db = Mock()
            get_vector_store("invalid", db=mock_db)

        # LLM
        with pytest.raises(ValueError):
            get_llm_provider("invalid")


class TestServiceIntegration:
    """Test factories integrate correctly with services"""

    def test_text_extraction_service_uses_parser_factory(self):
        """Test TextExtractionService uses parser factory"""
        from app.services.extraction.text_extraction_service import DocumentTextExtractor

        extractor = DocumentTextExtractor()
        parser = extractor._get_parser()

        assert isinstance(parser, DocumentParser)

    def test_embedding_service_uses_provider_factory(self):
        """Test EmbeddingService uses embedding provider factory"""
        from app.services.embeddings.embedding_service import EmbeddingService

        service = EmbeddingService()
        provider = service._get_provider()

        assert isinstance(provider, EmbeddingProvider)
        assert service.get_embedding_dimension() > 0

    def test_answer_service_uses_llm_factory(self):
        """Test AnswerService uses LLM provider factory"""
        from app.services.answer_service import AnswerService

        service = AnswerService()
        llm = service._get_llm_provider()

        assert isinstance(llm, LLMProvider)

    def test_services_can_override_providers(self):
        """Test services accept provider overrides"""
        from app.services.extraction.text_extraction_service import DocumentTextExtractor
        from app.services.embeddings.embedding_service import EmbeddingService
        from app.services.answer_service import AnswerService

        # Create providers
        parser = get_parser()
        embedder = get_embedding_provider()
        llm = get_llm_provider()

        # Pass to services
        extractor = DocumentTextExtractor(parser=parser)
        embedding_svc = EmbeddingService(provider=embedder)
        answer_svc = AnswerService(llm_provider=llm)

        # Verify they use the provided instances
        assert extractor.parser is parser
        assert embedding_svc.provider is embedder
        assert answer_svc.llm_provider is llm


class TestConfigDrivenSelection:
    """Test config-driven provider selection"""

    @patch('app.core.config.settings')
    def test_parser_uses_config_setting(self, mock_settings):
        """Test parser factory reads PARSER_PRIMARY from config"""
        mock_settings.PARSER_PRIMARY = "docling"
        parser = get_parser()
        assert parser is not None

    @patch('app.core.config.settings')
    def test_embedding_uses_config_setting(self, mock_settings):
        """Test embedding factory reads EMBEDDING_PROVIDER from config"""
        mock_settings.EMBEDDING_PROVIDER = "bge-m3"
        embedder = get_embedding_provider()
        assert embedder is not None

    @patch('app.core.config.settings')
    def test_vector_store_uses_config_setting(self, mock_settings):
        """Test vector store factory reads VECTOR_STORE from config"""
        mock_settings.VECTOR_STORE = "pgvector"
        mock_db = Mock()
        store = get_vector_store(db=mock_db)
        assert store is not None

    @patch('app.core.config.settings')
    def test_llm_uses_config_setting(self, mock_settings):
        """Test LLM factory reads LLM_PROVIDER from config"""
        mock_settings.LLM_PROVIDER = "ollama"
        llm = get_llm_provider()
        assert llm is not None
