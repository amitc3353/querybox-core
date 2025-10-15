"""
Metadata Schemas for Document Processing
Step 6: Pydantic models for document metadata management

Defines comprehensive metadata structures that leverage existing JSONB fields
for flexible storage and easy extension.
"""

from enum import Enum
from typing import Optional, Dict, List, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ContentQuality(str, Enum):
    """Content quality assessment levels"""
    EXCELLENT = "excellent"  # >0.9 quality score
    HIGH = "high"           # 0.7-0.9 quality score
    MEDIUM = "medium"       # 0.5-0.7 quality score
    LOW = "low"            # 0.3-0.5 quality score
    POOR = "poor"          # <0.3 quality score


class DocumentType(str, Enum):
    """Document type classification"""
    ARTICLE = "article"
    REPORT = "report"
    PRESENTATION = "presentation"
    SPREADSHEET = "spreadsheet"
    MANUAL = "manual"
    FORM = "form"
    INVOICE = "invoice"
    CONTRACT = "contract"
    RESUME = "resume"
    EMAIL = "email"
    WEB_PAGE = "web_page"
    OTHER = "other"


class ProcessingEngine(str, Enum):
    """Processing engines used for metadata extraction"""
    DOCLING = "docling"
    FALLBACK_TEXT = "fallback_text"
    FALLBACK_BASIC = "fallback_basic"
    MANUAL = "manual"


class DocumentMetadata(BaseModel):
    """
    Core metadata schema for document_metadata JSONB field.
    
    This schema captures rich document metadata extracted via Docling
    or fallback extractors, providing structured data for search and analysis.
    """
    
    # Document Properties
    title: Optional[str] = Field(
        None, 
        max_length=500,
        description="Document title or first heading"
    )
    author: Optional[str] = Field(
        None,
        max_length=200,
        description="Document author or creator"
    )
    subject: Optional[str] = Field(
        None,
        max_length=500,
        description="Document subject or description"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Extracted keywords and topics"
    )
    creator_application: Optional[str] = Field(
        None,
        max_length=100,
        description="Application used to create document"
    )
    
    # Technical Specifications
    page_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of pages in document"
    )
    word_count: Optional[int] = Field(
        None,
        ge=0,
        description="Estimated word count"
    )
    character_count: Optional[int] = Field(
        None,
        ge=0,
        description="Character count including spaces"
    )
    language: Optional[str] = Field(
        None,
        min_length=2,
        max_length=10,
        description="Detected language (ISO 639-1 code)"
    )
    
    # Content Analysis
    document_type: Optional[DocumentType] = Field(
        None,
        description="Classified document type"
    )
    content_quality: ContentQuality = Field(
        ContentQuality.MEDIUM,
        description="Assessed content quality"
    )
    text_quality_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Numeric quality score (0.0-1.0)"
    )
    has_images: bool = Field(
        False,
        description="Document contains images"
    )
    has_tables: bool = Field(
        False,
        description="Document contains tables"
    )
    is_scanned: bool = Field(
        False,
        description="Document appears to be scanned/OCR"
    )
    requires_ocr: bool = Field(
        False,
        description="Document requires OCR processing"
    )
    
    # Processing Metadata
    extraction_version: str = Field(
        "1.0.0",
        description="Version of extraction algorithm used"
    )
    processing_engine: ProcessingEngine = Field(
        ProcessingEngine.DOCLING,
        description="Engine used for metadata extraction"
    )
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores for extracted fields"
    )
    processing_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings encountered during processing"
    )
    
    # Timestamps
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When metadata was extracted"
    )
    
    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v):
        """Validate and clean keywords list"""
        if not isinstance(v, list):
            return []
        # Limit to 50 keywords, max 100 chars each
        return [str(kw)[:100].strip() for kw in v if str(kw).strip()][:50]

    @field_validator('text_quality_score')
    @classmethod
    def validate_quality_score(cls, v):
        """Ensure quality score matches content_quality enum"""
        # Note: In Pydantic v2, we can't modify other fields in validators
        # Quality consistency will be checked in a separate validator if needed
        return v

    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        json_schema_extra={
            "example": {
                "title": "QueryBox Core Architecture Guide",
                "author": "Development Team",
                "subject": "Technical documentation for document processing system",
                "keywords": ["architecture", "document processing", "RAG", "metadata"],
                "creator_application": "Microsoft Word",
                "page_count": 42,
                "word_count": 8500,
                "character_count": 52000,
                "language": "en",
                "document_type": "manual",
                "content_quality": "high",
                "text_quality_score": 0.85,
                "has_images": True,
                "has_tables": True,
                "is_scanned": False,
                "requires_ocr": False,
                "extraction_version": "1.0.0",
                "processing_engine": "docling",
                "confidence_scores": {
                    "title": 0.95,
                    "author": 0.8,
                    "language": 0.9,
                    "document_type": 0.75
                },
                "processing_warnings": [],
                "extracted_at": "2024-11-15T14:30:00Z"
            }
        }
    )


class ProcessingMetadata(BaseModel):
    """
    Enhanced metadata for status_metadata JSONB field.
    
    Tracks detailed processing progress and performance metrics.
    """
    
    # Progress Tracking
    percentage_complete: float = Field(
        0.0,
        ge=0.0,
        le=100.0,
        description="Processing completion percentage"
    )
    current_operation: Optional[str] = Field(
        None,
        max_length=200,
        description="Current processing operation"
    )
    estimated_completion: Optional[datetime] = Field(
        None,
        description="Estimated completion time"
    )
    
    # Performance Metrics
    processing_duration_ms: Optional[int] = Field(
        None,
        ge=0,
        description="Processing duration in milliseconds"
    )
    memory_usage_mb: Optional[float] = Field(
        None,
        ge=0.0,
        description="Peak memory usage in MB"
    )
    
    # Error Information
    error_category: Optional[str] = Field(
        None,
        max_length=100,
        description="Category of error if processing failed"
    )
    error_details: Optional[str] = Field(
        None,
        max_length=1000,
        description="Detailed error information"
    )
    retry_count: int = Field(
        0,
        ge=0,
        description="Number of processing retries"
    )
    
    # Quality Metrics
    extraction_quality: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Quality of metadata extraction (0.0-1.0)"
    )
    completeness_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Completeness of extracted metadata"
    )
    
    # Processing Context
    worker_id: Optional[str] = Field(
        None,
        max_length=100,
        description="ID of worker that processed document"
    )
    processing_priority: int = Field(
        5,
        ge=1,
        le=10,
        description="Processing priority (1=highest, 10=lowest)"
    )
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        json_schema_extra={
            "example": {
                "percentage_complete": 85.5,
                "current_operation": "Extracting metadata via Docling",
                "estimated_completion": "2024-11-15T14:32:00Z",
                "processing_duration_ms": 2500,
                "memory_usage_mb": 45.2,
                "error_category": None,
                "error_details": None,
                "retry_count": 0,
                "extraction_quality": 0.92,
                "completeness_score": 0.88,
                "worker_id": "worker-01",
                "processing_priority": 5
            }
        }
    )


class VersionMetadata(BaseModel):
    """
    Version metadata for version_metadata JSONB field.
    
    Tracks document versions and changes over time.
    """
    
    version_number: int = Field(
        1,
        ge=1,
        description="Version number"
    )
    version_reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for new version"
    )
    changes_summary: Optional[str] = Field(
        None,
        max_length=1000,
        description="Summary of changes in this version"
    )
    created_by: Optional[UUID] = Field(
        None,
        description="User who created this version"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When version was created"
    )
    
    # Size comparison with previous version
    size_change_bytes: Optional[int] = Field(
        None,
        description="Size change from previous version (can be negative)"
    )
    size_change_percentage: Optional[float] = Field(
        None,
        ge=-100.0,
        description="Percentage size change from previous version"
    )
    
    # Content changes
    content_changed: bool = Field(
        True,
        description="Whether document content changed"
    )
    metadata_changed: bool = Field(
        False,
        description="Whether metadata was updated"
    )
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
    )


class MetadataExtractionRequest(BaseModel):
    """Request model for metadata extraction operations"""
    
    document_id: UUID = Field(..., description="Document ID to process")
    force_reextraction: bool = Field(
        False,
        description="Force re-extraction even if metadata exists"
    )
    use_fallback: bool = Field(
        True,
        description="Use fallback extraction if Docling fails"
    )
    processing_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional processing options"
    )


class MetadataExtractionResponse(BaseModel):
    """Response model for metadata extraction operations"""
    
    document_id: UUID = Field(..., description="Processed document ID")
    success: bool = Field(..., description="Whether extraction succeeded")
    metadata: Optional[DocumentMetadata] = Field(None, description="Extracted metadata")
    processing_metadata: Optional[ProcessingMetadata] = Field(
        None,
        description="Processing details"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    extraction_time_ms: float = Field(..., description="Total extraction time")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "success": True,
                "metadata": {
                    "title": "Sample Document",
                    "author": "John Doe",
                    "language": "en",
                    "processing_engine": "docling"
                },
                "processing_metadata": {
                    "percentage_complete": 100.0,
                    "processing_duration_ms": 2500
                },
                "error_message": None,
                "extraction_time_ms": 2500.0
            }
        }
    )