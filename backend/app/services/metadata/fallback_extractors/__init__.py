"""
Fallback Extractors
Step 6: Simple metadata extractors for formats not supported by Docling

Provides basic metadata extraction capabilities for file types that
cannot be processed by the Docling service.
"""

from .text_extractor import extract_basic_metadata, TextMetadataExtractor

__all__ = [
    'extract_basic_metadata',
    'TextMetadataExtractor'
]