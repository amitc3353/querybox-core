"""
OpenRouter LLM Provider

Provides access to multiple LLM models (GPT, Claude, Gemini, etc.) through
OpenRouter's unified API.

OpenRouter is a proxy service that provides access to multiple LLM APIs
with a single interface and automatic fallbacks.
"""

import time
from typing import Dict, List, Optional, Any
import structlog
from openai import OpenAI, APIError, APIConnectionError, RateLimitError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .base import LLMProvider, LLMResponse

logger = structlog.get_logger(__name__)


class OpenRouterProvider(LLMProvider):
    """
    OpenRouter LLM provider implementation.

    Supports multiple models through OpenRouter's API:
    - OpenAI: gpt-4o-mini, gpt-4o, gpt-3.5-turbo
    - Anthropic: claude-3.5-sonnet, claude-3-haiku
    - Google: gemini-2.0-flash-exp
    - Meta: llama-3.1-405b, llama-3.1-70b

    Features:
    - Automatic retries with exponential backoff
    - Token usage tracking and cost estimation
    - Support for both chat and completion formats
    - Configurable temperature, max_tokens, etc.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "openai/gpt-4o-mini",
        app_name: str = "QueryBox Core",
        site_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        """
        Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key (get from openrouter.ai)
            base_url: OpenRouter API base URL (default: https://openrouter.ai/api/v1)
            model: Model identifier (e.g., "openai/gpt-4o-mini")
            app_name: Your app name (for OpenRouter rankings)
            site_url: Your site URL (optional, for OpenRouter rankings)
            temperature: Default temperature for generation (0.0-1.0)
            max_tokens: Default max tokens for generation
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.app_name = app_name
        self.site_url = site_url
        self.default_temperature = temperature
        self.default_max_tokens = max_tokens

        # Initialize OpenAI client with OpenRouter base URL
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        logger.info(
            "openrouter_provider_initialized",
            model=model,
            base_url=base_url,
            app_name=app_name,
        )

    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text from a prompt (converts to messages format).

        Args:
            prompt: The prompt/question
            context: Optional context to include
            temperature: Generation temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional generation parameters

        Returns:
            LLMResponse with generated text and metadata
        """
        # Validate prompt
        self.validate_prompt(prompt)

        # Convert prompt + context to messages format
        messages = []

        if context:
            messages.append({
                "role": "system",
                "content": f"Use the following context to answer the question:\n\n{context}"
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        # Call generate_with_messages
        return self.generate_with_messages(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text from chat messages (primary method).

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Generation temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional generation parameters

        Returns:
            LLMResponse with generated text and metadata
        """
        # Validate messages
        self.validate_messages(messages)

        # Use defaults if not provided
        temperature = temperature if temperature is not None else self.default_temperature
        max_tokens = max_tokens if max_tokens is not None else self.default_max_tokens

        # Make API request with retry logic
        start_time = time.time()

        try:
            response = self._make_request_with_retry(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract response data
            generated_text = response.choices[0].message.content
            tokens_input = response.usage.prompt_tokens
            tokens_output = response.usage.completion_tokens
            finish_reason = response.choices[0].finish_reason

            # Calculate cost (rough estimates - OpenRouter provides actual costs)
            cost_input = tokens_input / 1_000_000 * self._get_input_cost()
            cost_output = tokens_output / 1_000_000 * self._get_output_cost()
            total_cost = cost_input + cost_output

            # Build response
            llm_response = LLMResponse(
                text=generated_text,
                model=self.model,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=latency_ms,
                metadata={
                    "provider": "openrouter",
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "finish_reason": finish_reason,
                    "cost_usd": round(total_cost, 6),
                    "cost_input_usd": round(cost_input, 6),
                    "cost_output_usd": round(cost_output, 6),
                },
            )

            logger.info(
                "openrouter_generation_success",
                model=self.model,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                latency_ms=latency_ms,
                cost_usd=round(total_cost, 6),
            )

            return llm_response

        except Exception as e:
            logger.error(
                "openrouter_generation_failed",
                model=self.model,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise RuntimeError(f"OpenRouter generation failed: {str(e)}") from e

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=20),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((APIConnectionError, APITimeoutError, RateLimitError)),
        reraise=True,
    )
    def _make_request_with_retry(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> Any:
        """
        Make API request with retry logic.

        Retries on:
        - Connection errors
        - Timeout errors
        - Rate limit errors (with exponential backoff)

        Args:
            messages: Chat messages
            temperature: Generation temperature
            max_tokens: Max tokens to generate
            **kwargs: Additional parameters

        Returns:
            OpenAI API response object
        """
        # Prepare headers for OpenRouter
        extra_headers = {
            "HTTP-Referer": self.site_url or "https://github.com/yourusername/querybox",
            "X-Title": self.app_name,
        }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                extra_headers=extra_headers,
                **kwargs,
            )
            return response

        except RateLimitError as e:
            logger.warning(
                "openrouter_rate_limit",
                model=self.model,
                error=str(e),
            )
            raise  # Will be retried by tenacity

        except APIConnectionError as e:
            logger.warning(
                "openrouter_connection_error",
                model=self.model,
                error=str(e),
            )
            raise  # Will be retried by tenacity

        except APITimeoutError as e:
            logger.warning(
                "openrouter_timeout",
                model=self.model,
                error=str(e),
            )
            raise  # Will be retried by tenacity

        except APIError as e:
            # Don't retry on API errors (bad request, etc.)
            logger.error(
                "openrouter_api_error",
                model=self.model,
                error=str(e),
                status_code=getattr(e, 'status_code', None),
            )
            raise RuntimeError(f"OpenRouter API error: {str(e)}") from e

    def _get_input_cost(self) -> float:
        """
        Get input cost per million tokens for current model.

        Returns:
            Cost in USD per 1M input tokens
        """
        # Rough cost estimates (OpenRouter provides actual costs in response)
        costs = {
            "openai/gpt-4o-mini": 0.15,
            "openai/gpt-4o": 2.50,
            "openai/gpt-3.5-turbo": 0.50,
            "anthropic/claude-3.5-sonnet": 3.00,
            "anthropic/claude-3-haiku": 0.25,
            "google/gemini-2.0-flash-exp": 0.00,  # Free during preview
            "meta-llama/llama-3.1-405b": 2.70,
            "meta-llama/llama-3.1-70b": 0.52,
        }
        return costs.get(self.model, 1.0)  # Default to $1 if unknown

    def _get_output_cost(self) -> float:
        """
        Get output cost per million tokens for current model.

        Returns:
            Cost in USD per 1M output tokens
        """
        # Rough cost estimates (usually 3-5x input cost)
        costs = {
            "openai/gpt-4o-mini": 0.60,
            "openai/gpt-4o": 10.00,
            "openai/gpt-3.5-turbo": 1.50,
            "anthropic/claude-3.5-sonnet": 15.00,
            "anthropic/claude-3-haiku": 1.25,
            "google/gemini-2.0-flash-exp": 0.00,  # Free during preview
            "meta-llama/llama-3.1-405b": 2.70,
            "meta-llama/llama-3.1-70b": 0.80,
        }
        return costs.get(self.model, 3.0)  # Default to $3 if unknown

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get provider metadata.

        Returns:
            Dict with provider information
        """
        return {
            "provider": "openrouter",
            "model": self.model,
            "base_url": self.base_url,
            "app_name": self.app_name,
            "default_temperature": self.default_temperature,
            "default_max_tokens": self.default_max_tokens,
            "supports_streaming": False,  # Not implemented yet
            "supports_function_calling": True,  # OpenRouter supports this
            "context_window": self._get_context_window(),
        }

    def _get_context_window(self) -> int:
        """
        Get context window size for current model.

        Returns:
            Context window size in tokens
        """
        windows = {
            "openai/gpt-4o-mini": 128_000,
            "openai/gpt-4o": 128_000,
            "openai/gpt-3.5-turbo": 16_385,
            "anthropic/claude-3.5-sonnet": 200_000,
            "anthropic/claude-3-haiku": 200_000,
            "google/gemini-2.0-flash-exp": 1_000_000,
            "meta-llama/llama-3.1-405b": 128_000,
            "meta-llama/llama-3.1-70b": 128_000,
        }
        return windows.get(self.model, 8_000)  # Conservative default
