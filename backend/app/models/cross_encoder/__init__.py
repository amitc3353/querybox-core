"""
Cross-Encoder Model Package for Step 10.2

Handles loading and caching of cross-encoder models.
"""
from app.models.cross_encoder.model_loader import load_cross_encoder_model

__all__ = ["load_cross_encoder_model"]
