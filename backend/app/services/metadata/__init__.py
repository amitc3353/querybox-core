"""
Metadata Services Module
Step 6: Initialization and exports for metadata services

Provides centralized access to all metadata-related services and utilities.
"""

from .docling_service import (
    DoclingMetadataService,
    get_docling_metadata_service,
    extract_document_metadata
)
from .docling_client import (
    DoclingClient,
    get_docling_client,
    DoclingAnalysisResult,
    DoclingServiceError,
    DoclingTimeoutError,
    DoclingUnsupportedFormatError
)
from .metadata_mapper import (
    DoclingMetadataMapper,
    map_docling_to_metadata,
    create_docling_processing_metadata
)
from .fallback_extractors import (
    extract_basic_metadata,
    TextMetadataExtractor
)

__all__ = [
    # Main services
    'DoclingMetadataService',
    'get_docling_metadata_service',
    'extract_document_metadata',
    
    # Docling client
    'DoclingClient',
    'get_docling_client',
    'DoclingAnalysisResult',
    'DoclingServiceError',
    'DoclingTimeoutError',
    'DoclingUnsupportedFormatError',
    
    # Metadata mapping
    'DoclingMetadataMapper',
    'map_docling_to_metadata',
    'create_docling_processing_metadata',
    
    # Fallback extractors
    'extract_basic_metadata',
    'TextMetadataExtractor'
]