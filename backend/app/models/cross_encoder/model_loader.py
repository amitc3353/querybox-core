"""
Cross-Encoder Model Loader for Step 10.2

Handles downloading, caching, and loading cross-encoder models.
"""
from typing import Optional
import os
import structlog
from sentence_transformers import CrossEncoder

from app.core.config import settings

logger = structlog.get_logger()


def load_cross_encoder_model(
    model_name: Optional[str] = None,
    device: Optional[str] = None,
    max_length: Optional[int] = None,
    cache_dir: Optional[str] = None
) -> CrossEncoder:
    """
    Load cross-encoder model from HuggingFace or local cache

    Args:
        model_name: HuggingFace model name (default from settings)
        device: Device to load model on ("cpu" or "cuda")
        max_length: Maximum sequence length
        cache_dir: Directory to cache model files

    Returns:
        Loaded CrossEncoder model

    Raises:
        Exception: If model loading fails
    """
    model_name = model_name or settings.CROSS_ENCODER_MODEL_NAME
    device = device or settings.CROSS_ENCODER_DEVICE
    max_length = max_length or settings.CROSS_ENCODER_MAX_LENGTH
    cache_dir = cache_dir or settings.MODEL_CACHE_DIR

    logger.info(
        "loading_cross_encoder_model",
        model_name=model_name,
        device=device,
        max_length=max_length,
        cache_dir=cache_dir
    )

    try:
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)

        # Load model (will download if not cached)
        model = CrossEncoder(
            model_name,
            max_length=max_length,
            device=device
        )

        logger.info(
            "cross_encoder_model_loaded",
            model_name=model_name,
            device=device
        )

        return model

    except Exception as e:
        logger.error(
            "cross_encoder_model_loading_failed",
            model_name=model_name,
            error=str(e),
            exc_info=True
        )
        raise


def warm_up_model(model: CrossEncoder, query: str = "test query", document: str = "test document") -> None:
    """
    Warm up model with a dummy inference to reduce first-request latency

    Args:
        model: Loaded CrossEncoder model
        query: Test query string
        document: Test document string
    """
    try:
        logger.info("warming_up_cross_encoder_model")

        # Run dummy inference
        model.predict([(query, document)])

        logger.info("cross_encoder_model_warmed_up")

    except Exception as e:
        logger.warning(
            "cross_encoder_warmup_failed",
            error=str(e)
        )
