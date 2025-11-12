"""
Ollama LLM provider implementation.

Wraps the existing Ollama client logic in the LLMProvider interface.
"""

import logging
import time
from typing import List, Dict, Optional
import httpx
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type
)

from app.services.llm.base import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base exception for Ollama errors"""
    pass


class OllamaProvider(LLMProvider):
    """
    Ollama LLM provider.

    Features:
    - Local LLM inference (tinyllama, qwen2, etc.)
    - Async HTTP communication
    - Automatic retry logic
    - Health monitoring
    - Token counting and latency tracking
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "tinyllama",
        timeout: float = 60.0
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama server URL
            model: Model name (e.g., "tinyllama", "qwen2:7b")
            timeout: Request timeout in seconds
        """
        super().__init__(name="ollama", model=model)

        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

        logger.info(
            f"Ollama Provider initialized: url={base_url}, model={model}, "
            f"timeout={timeout}s"
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text completion from Ollama.

        Note: This is a synchronous wrapper around async generation.
        For async code, use generate_async() directly.

        Args:
            prompt: The prompt text
            context: Optional context (will be prepended to prompt)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate (default: 2000)
            **kwargs: Additional parameters:
                - stop_sequences: List of stop sequences

        Returns:
            LLMResponse with generated text and metadata
        """
        # Validate prompt
        self.validate_prompt(prompt)

        # Build full prompt with context if provided
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n{prompt}"

        # Run async generation (this requires an event loop)
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.generate_async(
                full_prompt,
                temperature=temperature,
                max_tokens=max_tokens or 2000,
                **kwargs
            )
        )

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
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            LLMResponse with generated text and metadata
        """
        # Validate messages
        self.validate_messages(messages)

        # Convert messages to a single prompt
        # Format: role1: content1\nrole2: content2\n...
        prompt_parts = []
        for msg in messages:
            role = msg["role"].upper()
            content = msg["content"]
            prompt_parts.append(f"{role}: {content}")

        prompt = "\n\n".join(prompt_parts)
        prompt += "\n\nASSISTANT:"  # Prompt for response

        return self.generate(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

    async def generate_async(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        stop_sequences: Optional[List[str]] = None
    ) -> LLMResponse:
        """
        Generate text completion from Ollama (async version).

        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stop_sequences: Optional list of stop sequences

        Returns:
            LLMResponse with generated text and metadata
        """
        # Wrap the actual generation with retry logic
        @retry(
            wait=wait_exponential(multiplier=1, min=1, max=10),
            stop=stop_after_attempt(3),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
            reraise=True
        )
        async def _generate_with_retry():
            start_time = time.perf_counter()

            if stop_sequences is None:
                stop_seq = ["QUESTION:", "PASSAGES:"]
            else:
                stop_seq = stop_sequences

            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": 0.9,
                    "stop": stop_seq,
                    "num_thread": 8,  # Use 8 CPU threads
                }
            }

            logger.debug(
                f"Sending generate request: model={self.model}, "
                f"temp={temperature}, max_tokens={max_tokens}, "
                f"prompt_length={len(prompt)}"
            )

            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()

            result = response.json()

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Extract response text
            response_text = result.get("response", "")

            # Parse token counts
            prompt_tokens = result.get("prompt_eval_count", 0)
            output_tokens = result.get("eval_count", 0)

            logger.info(
                f"Generation completed: response_length={len(response_text)}, "
                f"time={elapsed_ms:.2f}ms, "
                f"input_tokens={prompt_tokens}, "
                f"output_tokens={output_tokens}"
            )

            return LLMResponse(
                text=response_text,
                model=result.get("model", self.model),
                tokens_input=prompt_tokens,
                tokens_output=output_tokens,
                latency_ms=elapsed_ms,
                metadata={
                    "total_duration_ns": result.get("total_duration", 0),
                    "load_duration_ns": result.get("load_duration", 0),
                }
            )

        # Execute with retry and convert exceptions
        try:
            return await _generate_with_retry()

        except httpx.TimeoutException as e:
            logger.error(f"Ollama request timeout after retries: {e}")
            raise RuntimeError(f"Request timeout: {e}")

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}: {e}")
            raise RuntimeError(f"Connection failed: {e}")

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Ollama HTTP error: status={e.response.status_code}, "
                f"body={e.response.text}"
            )
            raise RuntimeError(f"HTTP {e.response.status_code}: {e.response.text}")

        except Exception as e:
            logger.error(f"Unexpected error in Ollama generation: {e}", exc_info=True)
            raise RuntimeError(f"Generation failed: {e}")

    async def health_check(self) -> Dict:
        """
        Check if Ollama service is healthy.

        Returns:
            Dictionary with health status
        """
        start_time = time.perf_counter()

        try:
            # Try to list models as health check
            response = await self.client.get(
                f"{self.base_url}/api/tags",
                timeout=5.0  # Short timeout for health check
            )
            response.raise_for_status()

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            models_data = response.json()
            models = models_data.get("models", [])

            # Check if our model is loaded
            model_names = [m.get("name", "") for m in models]
            model_loaded = self.model in model_names

            logger.info(
                f"Ollama health check passed: {len(models)} models loaded, "
                f"target_model={self.model}, loaded={model_loaded}, "
                f"time={elapsed_ms:.2f}ms"
            )

            return {
                "status": "healthy",
                "model": self.model if model_loaded else None,
                "available_models": model_names,
                "response_time_ms": int(elapsed_ms),
                "error": None
            }

        except httpx.TimeoutException:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"Ollama health check timeout after {elapsed_ms:.2f}ms")
            return {
                "status": "unhealthy",
                "model": None,
                "error": "Health check timeout",
                "response_time_ms": int(elapsed_ms)
            }

        except httpx.ConnectError as e:
            logger.warning(f"Ollama health check connection failed: {e}")
            return {
                "status": "unhealthy",
                "model": None,
                "error": f"Connection failed: {e}",
                "response_time_ms": None
            }

        except Exception as e:
            logger.error(f"Ollama health check error: {e}", exc_info=True)
            return {
                "status": "unhealthy",
                "model": None,
                "error": str(e),
                "response_time_ms": None
            }

    def get_metadata(self) -> Dict:
        """Get metadata about this LLM provider."""
        metadata = super().get_metadata()
        metadata.update({
            "base_url": self.base_url,
            "timeout": self.timeout,
        })
        return metadata
