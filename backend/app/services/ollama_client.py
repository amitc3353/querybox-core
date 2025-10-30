"""
Ollama Client Service for Step 11.1 - LLM Integration

Handles communication with Ollama server for answer generation.
Implements retry logic and health monitoring.
"""
import httpx
import time
import logging
from typing import Optional, Dict, Any
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base exception for Ollama client errors"""
    pass


class OllamaConnectionError(OllamaError):
    """Raised when cannot connect to Ollama service"""
    pass


class OllamaGenerationError(OllamaError):
    """Raised when generation fails"""
    pass


class OllamaClient:
    """
    Client for Ollama API

    Handles:
    - Answer generation with retry logic
    - Health checks
    - Timeout management
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0,
        model: str = "qwen2:7b"
    ):
        """
        Initialize Ollama client

        Args:
            base_url: Ollama server URL
            timeout: Request timeout in seconds
            model: Model name to use
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.model = model
        self.client = httpx.AsyncClient(timeout=timeout)

        logger.info(
            f"OllamaClient initialized: url={base_url}, model={model}, "
            f"timeout={timeout}s"
        )

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        stop_sequences: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Generate text completion from Ollama

        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stop_sequences: Optional list of stop sequences

        Returns:
            Dictionary with response text and metadata

        Raises:
            OllamaConnectionError: If cannot connect to Ollama
            OllamaGenerationError: If generation fails
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

            # Parse metadata
            metadata = {
                "model": result.get("model", self.model),
                "total_duration_ns": result.get("total_duration", 0),
                "load_duration_ns": result.get("load_duration", 0),
                "prompt_eval_count": result.get("prompt_eval_count", 0),
                "eval_count": result.get("eval_count", 0),
                "processing_time_ms": int(elapsed_ms)
            }

            logger.info(
                f"Generation completed: response_length={len(response_text)}, "
                f"time={elapsed_ms:.2f}ms, "
                f"input_tokens={metadata['prompt_eval_count']}, "
                f"output_tokens={metadata['eval_count']}"
            )

            return {
                "response": response_text,
                "metadata": metadata
            }

        # Execute with retry and convert exceptions
        try:
            return await _generate_with_retry()

        except httpx.TimeoutException as e:
            logger.error(f"Ollama request timeout after retries: {e}")
            raise OllamaConnectionError(f"Request timeout: {e}")

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}: {e}")
            raise OllamaConnectionError(f"Connection failed: {e}")

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Ollama HTTP error: status={e.response.status_code}, "
                f"body={e.response.text}"
            )
            raise OllamaGenerationError(f"HTTP {e.response.status_code}: {e.response.text}")

        except Exception as e:
            logger.error(f"Unexpected error in Ollama generation: {e}", exc_info=True)
            raise OllamaGenerationError(f"Generation failed: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if Ollama service is healthy

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

    async def test_generation(self) -> bool:
        """
        Test generation with simple prompt

        Returns:
            True if generation successful, False otherwise
        """
        try:
            result = await self.generate(
                prompt="Respond with 'OK'",
                max_tokens=10,
                temperature=0.0
            )

            response_text = result.get("response", "").strip()
            success = len(response_text) > 0

            logger.info(f"Test generation: success={success}, response='{response_text}'")
            return success

        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return False


# Singleton instance for dependency injection
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client(
    base_url: Optional[str] = None,
    timeout: Optional[float] = None,
    model: Optional[str] = None
) -> OllamaClient:
    """
    Get or create Ollama client singleton

    Args:
        base_url: Ollama server URL (uses default if None)
        timeout: Request timeout (uses default if None)
        model: Model name (uses default if None)

    Returns:
        OllamaClient instance
    """
    global _ollama_client

    # Create client if not exists or parameters changed
    if _ollama_client is None:
        from app.core.config import settings

        _ollama_client = OllamaClient(
            base_url=base_url or settings.OLLAMA_BASE_URL,
            timeout=timeout or settings.OLLAMA_TIMEOUT,
            model=model or settings.OLLAMA_MODEL
        )

        logger.info("Created new OllamaClient singleton")

    return _ollama_client


async def close_ollama_client():
    """Close the Ollama client singleton"""
    global _ollama_client

    if _ollama_client:
        await _ollama_client.close()
        _ollama_client = None
        logger.info("Closed OllamaClient singleton")
