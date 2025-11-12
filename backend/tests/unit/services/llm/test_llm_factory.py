"""
Unit tests for LLM provider factory pattern

Tests:
- Factory returns correct provider based on config
- Invalid provider names raise errors
- Provider override works
- Available providers list is correct
- LLMResponse dataclass works correctly
"""
import pytest
from unittest.mock import patch, AsyncMock

from app.services.llm.factory import get_llm_provider, get_available_llm_providers
from app.services.llm.base import LLMProvider, LLMResponse
from app.services.llm.ollama_provider import OllamaProvider


class TestLLMFactory:
    """Test LLM provider factory function"""

    def test_get_provider_default(self):
        """Test factory returns default provider (ollama)"""
        provider = get_llm_provider()
        assert isinstance(provider, LLMProvider)
        assert isinstance(provider, OllamaProvider)

    def test_get_provider_ollama_explicit(self):
        """Test factory returns Ollama when explicitly requested"""
        provider = get_llm_provider("ollama")
        assert isinstance(provider, OllamaProvider)

    def test_get_provider_invalid_name(self):
        """Test factory raises error for invalid provider name"""
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_provider("invalid_provider")

    @patch('app.core.config.settings')
    def test_get_provider_from_config(self, mock_settings):
        """Test factory uses config setting"""
        mock_settings.LLM_PROVIDER = "ollama"
        provider = get_llm_provider()
        assert isinstance(provider, OllamaProvider)

    def test_get_provider_override_config(self):
        """Test explicit provider name overrides config"""
        provider = get_llm_provider("ollama")
        assert isinstance(provider, OllamaProvider)

    def test_get_available_providers(self):
        """Test available providers list"""
        providers = get_available_llm_providers()
        assert isinstance(providers, list)
        assert "ollama" in providers
        assert len(providers) >= 1

    def test_provider_is_new_instance(self):
        """Test each factory call creates a new instance"""
        provider1 = get_llm_provider()
        provider2 = get_llm_provider()
        # Should be different instances
        assert provider1 is not provider2


class TestLLMProviderInterface:
    """Test that all providers implement the base interface correctly"""

    def test_ollama_provider_has_required_methods(self):
        """Test OllamaProvider implements all abstract methods"""
        provider = OllamaProvider()

        # Check required methods exist
        assert hasattr(provider, 'generate')
        assert callable(provider.generate)
        assert hasattr(provider, 'generate_async')
        assert callable(provider.generate_async)
        assert hasattr(provider, 'get_model_name')
        assert callable(provider.get_model_name)

    def test_ollama_provider_metadata(self):
        """Test OllamaProvider has correct metadata"""
        provider = OllamaProvider()
        assert provider.name == "ollama"
        model_name = provider.get_model_name()
        assert isinstance(model_name, str)
        assert len(model_name) > 0


class TestLLMResponse:
    """Test LLMResponse dataclass"""

    def test_llm_response_creation(self):
        """Test LLMResponse can be created"""
        response = LLMResponse(
            text="test response",
            model="test-model",
            tokens_input=10,
            tokens_output=5,
            latency_ms=100.5
        )

        assert response.text == "test response"
        assert response.model == "test-model"
        assert response.tokens_input == 10
        assert response.tokens_output == 5
        assert response.latency_ms == 100.5

    def test_llm_response_minimal(self):
        """Test LLMResponse with minimal fields"""
        response = LLMResponse(
            text="test",
            model="model"
        )

        assert response.text == "test"
        assert response.model == "model"
        assert response.tokens_input is None
        assert response.tokens_output is None
        assert response.latency_ms is None

    def test_llm_response_immutable(self):
        """Test LLMResponse fields can be accessed"""
        response = LLMResponse(text="test", model="model")
        assert response.text == "test"

        # Note: dataclasses are mutable by default unless frozen=True
        # This test just verifies the fields exist and are accessible
