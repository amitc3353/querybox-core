#!/usr/bin/env python3
"""
Download Cross-Encoder Model for Step 10.2

Downloads the ms-marco-MiniLM-L6-v2 cross-encoder model from HuggingFace
and caches it locally for faster startup times.

Usage:
    python backend/scripts/download_cross_encoder_model.py
"""
import os
import sys
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sentence_transformers import CrossEncoder
from app.core.config import settings


def download_cross_encoder_model(
    model_name: str = None,
    cache_dir: str = None,
    device: str = "cpu"
):
    """
    Download cross-encoder model from HuggingFace

    Args:
        model_name: Model to download (default from settings)
        cache_dir: Directory to save model (default from settings)
        device: Device for initial load ("cpu" recommended for download)
    """
    model_name = model_name or settings.CROSS_ENCODER_MODEL_NAME
    cache_dir = cache_dir or settings.MODEL_CACHE_DIR

    print(f"\n{'='*60}")
    print(f"Downloading Cross-Encoder Model: {model_name}")
    print(f"Cache Directory: {cache_dir}")
    print(f"{'='*60}\n")

    # Create cache directory
    os.makedirs(cache_dir, exist_ok=True)
    print(f"✓ Created cache directory: {cache_dir}")

    try:
        # Download model (sentence-transformers handles caching)
        print(f"\n📥 Downloading model from HuggingFace...")
        print(f"   Model: {model_name}")
        print(f"   This may take a few minutes on first download...\n")

        model = CrossEncoder(
            model_name,
            max_length=512,
            device=device
        )

        print(f"\n✓ Model downloaded successfully!")
        print(f"  Model: {model_name}")
        print(f"  Device: {device}")

        # Test model with dummy inference
        print(f"\n🧪 Testing model with dummy inference...")
        test_scores = model.predict([
            ("test query", "test document 1"),
            ("test query", "test document 2")
        ])

        print(f"✓ Model test successful!")
        print(f"  Test scores: {test_scores}")

        print(f"\n{'='*60}")
        print(f"✅ Cross-Encoder Model Ready")
        print(f"{'='*60}\n")

        return model

    except Exception as e:
        print(f"\n❌ Error downloading model: {e}")
        print(f"\nTroubleshooting:")
        print(f"  1. Check internet connection")
        print(f"  2. Verify HuggingFace is accessible")
        print(f"  3. Check disk space in {cache_dir}")
        print(f"  4. Try setting environment variable: export TRANSFORMERS_CACHE={cache_dir}")
        sys.exit(1)


def main():
    """Main entry point"""
    print(f"\n🚀 QueryBox Core - Cross-Encoder Model Downloader")

    # Download model
    model = download_cross_encoder_model()

    print(f"\n📊 Model Information:")
    print(f"  Name: {settings.CROSS_ENCODER_MODEL_NAME}")
    print(f"  Max Length: {settings.CROSS_ENCODER_MAX_LENGTH}")
    print(f"  Batch Size: {settings.CROSS_ENCODER_BATCH_SIZE}")
    print(f"  Device: {settings.CROSS_ENCODER_DEVICE}")

    print(f"\n💡 Next Steps:")
    print(f"  1. Model is cached and ready for use")
    print(f"  2. Start the backend: uvicorn app.main:app --reload")
    print(f"  3. Model will load automatically at startup")

    print(f"\n✅ Done!\n")


if __name__ == "__main__":
    main()
