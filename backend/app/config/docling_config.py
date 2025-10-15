"""
Docling Service Configuration
Step 6: Docling integration settings and supported formats

Configures the Docling service connection and processing options
following PipesHub architecture patterns.
"""

import os
from typing import Dict, Any, Set
from pydantic_settings import BaseSettings
from pydantic import Field
from enum import Enum


class DoclingQualityLevel(str, Enum):
    """Quality levels for Docling processing"""
    FAST = "fast"
    BALANCED = "balanced"
    HIGH_QUALITY = "high_quality"


class DoclingSettings(BaseSettings):
    """Docling service configuration settings"""

    # Service Connection
    DOCLING_SERVICE_URL: str = Field(
        default="http://localhost:8080",
        description="Docling service base URL"
    )
    DOCLING_API_KEY: str = Field(
        default="",
        description="API key for Docling service authentication"
    )
    DOCLING_REQUEST_TIMEOUT: int = Field(
        default=30,
        description="Request timeout in seconds"
    )
    DOCLING_RETRY_ATTEMPTS: int = Field(
        default=3,
        description="Number of retry attempts for failed requests"
    )
    DOCLING_RETRY_DELAY: float = Field(
        default=1.0,
        description="Initial delay between retries in seconds"
    )

    # File Processing Limits
    DOCLING_MAX_FILE_SIZE_MB: int = Field(
        default=100,
        description="Maximum file size for Docling processing in MB"
    )
    DOCLING_MAX_PAGES: int = Field(
        default=1000,
        description="Maximum pages to process per document"
    )

    # Processing Options
    DOCLING_QUALITY_LEVEL: DoclingQualityLevel = Field(
        default=DoclingQualityLevel.BALANCED,
        description="Processing quality level"
    )
    DOCLING_EXTRACT_IMAGES: bool = Field(
        default=True,
        description="Extract images from documents"
    )
    DOCLING_EXTRACT_TABLES: bool = Field(
        default=True,
        description="Extract table data from documents"
    )
    DOCLING_OCR_ENABLED: bool = Field(
        default=True,
        description="Enable OCR for scanned documents"
    )
    DOCLING_LANGUAGE_DETECTION: bool = Field(
        default=True,
        description="Enable automatic language detection"
    )

    # Fallback Configuration
    DOCLING_FALLBACK_ENABLED: bool = Field(
        default=True,
        description="Enable fallback extraction when Docling fails"
    )

    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


# Supported MIME types for Docling processing
DOCLING_SUPPORTED_FORMATS: Set[str] = {
    # PDF documents
    "application/pdf",
    
    # Microsoft Office documents
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # PPTX
    
    # Web documents
    "text/html",
    "application/xhtml+xml",
    
    # Markdown
    "text/markdown",
    "text/x-markdown",
}

# Formats that require fallback extraction
FALLBACK_REQUIRED_FORMATS: Set[str] = {
    "text/plain",
    "text/csv",
    "application/json",
    "application/xml",
    "text/xml",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
}

# Docling processing configuration by format
DOCLING_FORMAT_CONFIG: Dict[str, Dict[str, Any]] = {
    "application/pdf": {
        "max_size_mb": 100,
        "ocr_enabled": True,
        "extract_images": True,
        "extract_tables": True,
        "quality_level": "balanced"
    },
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
        "max_size_mb": 50,
        "extract_images": True,
        "extract_tables": True,
        "quality_level": "fast"
    },
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": {
        "max_size_mb": 50,
        "extract_images": True,
        "extract_tables": False,
        "quality_level": "fast"
    },
    "text/html": {
        "max_size_mb": 10,
        "extract_images": False,
        "extract_tables": True,
        "quality_level": "fast"
    },
    "text/markdown": {
        "max_size_mb": 10,
        "extract_images": False,
        "extract_tables": True,
        "quality_level": "fast"
    }
}


def get_docling_settings() -> DoclingSettings:
    """Get Docling settings instance"""
    return DoclingSettings()


def is_docling_supported(mime_type: str) -> bool:
    """Check if a MIME type is supported by Docling"""
    return mime_type in DOCLING_SUPPORTED_FORMATS


def requires_fallback(mime_type: str) -> bool:
    """Check if a MIME type requires fallback extraction"""
    return mime_type in FALLBACK_REQUIRED_FORMATS


def get_format_config(mime_type: str) -> Dict[str, Any]:
    """Get configuration for a specific format"""
    return DOCLING_FORMAT_CONFIG.get(mime_type, {})


def get_max_file_size(mime_type: str) -> int:
    """Get maximum file size for a format in bytes"""
    config = get_format_config(mime_type)
    max_size_mb = config.get("max_size_mb", 30)  # Default 30MB
    return max_size_mb * 1024 * 1024


# Global settings instance
docling_settings = get_docling_settings()