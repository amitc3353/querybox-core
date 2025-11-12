"""
Abstract base class for LLM providers.

This module defines the interface that all LLM providers must implement,
enabling swappable LLM strategies (OpenRouter, Ollama, OpenAI, Anthropic, etc.)
without changing the core application logic.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """
    Standardized response object returned by all LLM providers.

    Attributes:
        text: Generated text content
        model: Model name used for generation
        tokens_input: Number of input tokens (if available)
        tokens_output: Number of output tokens (if available)
        latency_ms: Generation latency in milliseconds (if available)
        metadata: Provider-specific metadata
    """
    text: str
    model: str
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    latency_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "model": self.model,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata or {}
        }


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM implementations (OpenRouter, Ollama, OpenAI, Anthropic, etc.) must
    inherit from this class and implement its abstract methods.

    Example:
        class OpenRouterProvider(LLMProvider):
            def generate(self, prompt: str, **kwargs) -> LLMResponse:
                # Implementation here
                pass
    """

    def __init__(self, name: str, model: str):
        """
        Initialize LLM provider.

        Args:
            name: Human-readable name for this provider (e.g., "openrouter", "ollama")
            model: Default model to use (e.g., "openai/gpt-4o-mini", "tinyllama")
        """
        self.name = name
        self.model = model

    @abstractmethod
    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text completion from a prompt.

        Args:
            prompt: The prompt text (system + user instruction)
            context: Optional context (e.g., retrieved passages for RAG)
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific options (e.g., top_p, stop_sequences)

        Returns:
            LLMResponse object containing generated text and metadata

        Raises:
            ValueError: If prompt is empty or invalid
            Exception: For API errors or generation failures
        """
        pass

    @abstractmethod
    def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text using chat message format.

        Args:
            messages: List of message dicts with 'role' and 'content'
                      Example: [{"role": "user", "content": "Hello"}]
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific options

        Returns:
            LLMResponse object containing generated text and metadata

        Raises:
            ValueError: If messages list is empty or invalid
            Exception: For API errors or generation failures
        """
        pass

    def get_model_name(self) -> str:
        """
        Get the current model name.

        Returns:
            Model identifier string
        """
        return self.model

    def set_model(self, model: str) -> None:
        """
        Change the model to use for generation.

        Args:
            model: New model identifier
        """
        self.model = model

    def validate_prompt(self, prompt: str) -> None:
        """
        Validate that prompt is not empty.

        Args:
            prompt: Prompt text to validate

        Raises:
            ValueError: If prompt is empty or whitespace-only
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

    def validate_messages(self, messages: List[Dict[str, str]]) -> None:
        """
        Validate that messages list is properly formatted.

        Args:
            messages: List of message dicts to validate

        Raises:
            ValueError: If messages list is empty or improperly formatted
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")

        for i, msg in enumerate(messages):
            if "role" not in msg:
                raise ValueError(f"Message {i} missing 'role' field")
            if "content" not in msg:
                raise ValueError(f"Message {i} missing 'content' field")
            if not msg["content"].strip():
                raise ValueError(f"Message {i} has empty content")

    def estimate_cost(
        self,
        tokens_input: int,
        tokens_output: int,
        cost_per_1m_input: float,
        cost_per_1m_output: float
    ) -> float:
        """
        Estimate cost for a generation based on token counts.

        Args:
            tokens_input: Number of input tokens
            tokens_output: Number of output tokens
            cost_per_1m_input: Cost per 1 million input tokens (USD)
            cost_per_1m_output: Cost per 1 million output tokens (USD)

        Returns:
            Estimated cost in USD
        """
        input_cost = (tokens_input / 1_000_000) * cost_per_1m_input
        output_cost = (tokens_output / 1_000_000) * cost_per_1m_output
        return input_cost + output_cost

    def format_rag_prompt(
        self,
        query: str,
        contexts: List[str],
        instruction: Optional[str] = None
    ) -> str:
        """
        Format a standard RAG prompt with query and context passages.

        This is a helper method that can be used by subclasses or overridden
        for provider-specific prompt formats.

        Args:
            query: User query
            contexts: List of retrieved context passages
            instruction: Optional system instruction

        Returns:
            Formatted prompt string
        """
        instruction = instruction or (
            "You are a helpful assistant. Answer the question based on the "
            "provided passages. Include citations [1], [2], etc."
        )

        passages = "\n\n".join([
            f"[{i+1}] {context}"
            for i, context in enumerate(contexts)
        ])

        prompt = f"""{instruction}

PASSAGES:
{passages}

QUESTION: {query}

ANSWER:"""

        return prompt

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this LLM provider.

        Returns:
            Dictionary containing provider name, model, and other info
        """
        return {
            "name": self.name,
            "model": self.model,
            "provider_type": self.__class__.__name__
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', model='{self.model}')"
