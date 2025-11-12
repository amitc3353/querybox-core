"""
LLM provider factory for config-driven LLM selection.

Enables swapping LLM providers via configuration without code changes.
"""

import logging
from typing import Optional

from app.services.llm.base import LLMProvider
from app.services.llm.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


def get_llm_provider(provider_name: Optional[str] = None) -> LLMProvider:
    """
    Get LLM provider based on configuration.

    This factory function returns the appropriate LLM provider
    based on the LLM_PROVIDER config setting (or override parameter).

    Args:
        provider_name: Optional provider name to override config
                      Options: "ollama", "openrouter", "openai", "claude"
                      If None, uses settings.LLM_PROVIDER

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider_name is unknown

    Example:
        # Use default from config
        llm = get_llm_provider()
        response = llm.generate("What is RAG?")

        # Override for specific use case
        openrouter_llm = get_llm_provider("openrouter")
        response = openrouter_llm.generate("Complex query", temperature=0.7)
    """
    # Import settings here to avoid circular imports
    from app.core.config import settings

    # Use provided name or fall back to config
    name = provider_name or settings.LLM_PROVIDER

    logger.debug(f"Creating LLM provider: {name}")

    if name == "ollama":
        return OllamaProvider()

    # Future providers (uncomment when implemented):
    # elif name == "openrouter":
    #     from app.services.llm.openrouter_provider import OpenRouterProvider
    #     return OpenRouterProvider()
    #
    # elif name == "openai":
    #     from app.services.llm.openai_provider import OpenAIProvider
    #     return OpenAIProvider()
    #
    # elif name == "claude":
    #     from app.services.llm.claude_provider import ClaudeProvider
    #     return ClaudeProvider()

    else:
        available = ["ollama"]  # Add others as implemented
        raise ValueError(
            f"Unknown LLM provider: '{name}'. "
            f"Available options: {', '.join(available)}"
        )


def get_available_llm_providers() -> list[str]:
    """
    Get list of available LLM provider names.

    Returns:
        List of provider names that can be used with get_llm_provider()
    """
    return ["ollama"]  # Add others as implemented
