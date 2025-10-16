"""
Document Schemas - Request/Response models for document endpoints
Step 7: Document Query Endpoints
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class DocumentStatusEnum(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StorageProviderEnum(str, Enum):
    """Storage provider types"""
    LOCAL = "local"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"


class SortOrderEnum(str, Enum):
    """Sort order options"""
    ASC = "asc"
    DESC = "desc"


# ============================================================================
# PAGINATION MODELS
# ============================================================================

class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints

    Validation:
    - page must be >= 1 and <= 10000
    - page_size must be between 1 and 100
    """
    page: int = Field(
        default=1,
        ge=1,
        le=10000,
        description="Page number (1-indexed)"
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Items per page (max 100)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "page": 1,
                    "page_size": 20
                }
            ]
        }
    }


# ============================================================================
# FILTER MODELS
# ============================================================================

class DocumentFilterParams(BaseModel):
    """
    Filter parameters for document list endpoint

    Validations:
    - file_extension must match pattern: ^\.[a-z0-9]+$
    - max_size must be >= min_size
    - created_before must be after created_after
    - tags limited to max 10 items
    """
    status: Optional[DocumentStatusEnum] = Field(
        default=None,
        description="Filter by document status"
    )
    mime_type: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Filter by MIME type"
    )
    file_extension: Optional[str] = Field(
        default=None,
        pattern=r"^\.[a-z0-9]+$",
        description="Filter by file extension (e.g., '.pdf')"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="Filter by tags (AND logic)"
    )
    created_after: Optional[datetime] = Field(
        default=None,
        description="Filter documents created after this date"
    )
    created_before: Optional[datetime] = Field(
        default=None,
        description="Filter documents created before this date"
    )
    min_size: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum file size in bytes"
    )
    max_size: Optional[int] = Field(
        default=None,
        le=10 * 1024 * 1024 * 1024,  # 10GB max
        description="Maximum file size in bytes"
    )
    storage_provider: Optional[StorageProviderEnum] = Field(
        default=None,
        description="Filter by storage provider"
    )
    include_deleted: bool = Field(
        default=False,
        description="Include soft-deleted documents"
    )

    @model_validator(mode='after')
    def validate_size_range(self):
        """Validate that max_size >= min_size"""
        if self.min_size is not None and self.max_size is not None:
            if self.max_size < self.min_size:
                raise ValueError('max_size must be >= min_size')
        return self

    @model_validator(mode='after')
    def validate_date_range(self):
        """Validate that created_before > created_after"""
        if self.created_after is not None and self.created_before is not None:
            if self.created_before < self.created_after:
                raise ValueError('created_before must be after created_after')
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "completed",
                    "mime_type": "application/pdf",
                    "tags": ["finance", "quarterly"],
                    "min_size": 1024,
                    "max_size": 10485760
                }
            ]
        }
    }


class DocumentSortParams(BaseModel):
    """Sort parameters for document list"""
    sort_by: str = Field(
        default="created_at",
        description="Field to sort by"
    )
    sort_order: SortOrderEnum = Field(
        default=SortOrderEnum.DESC,
        description="Sort order (asc or desc)"
    )

    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v: str) -> str:
        """Validate sort_by field is allowed"""
        allowed_fields = [
            "created_at", "updated_at", "document_name",
            "file_size", "access_count", "status"
        ]
        if v not in allowed_fields:
            raise ValueError(f'Invalid sort_by field. Allowed: {allowed_fields}')
        return v


# ============================================================================
# SEARCH MODELS
# ============================================================================

class DocumentSearchRequest(BaseModel):
    """
    Document search request

    Validations:
    - q must be between 3 and 200 characters
    - search_fields must be valid field names
    """
    q: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Search query (minimum 3 characters)"
    )
    search_fields: List[str] = Field(
        default=["document_name", "metadata"],
        description="Fields to search in"
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: Optional[DocumentStatusEnum] = Field(
        default=None,
        description="Filter by status"
    )

    @field_validator('search_fields')
    @classmethod
    def validate_search_fields(cls, v: List[str]) -> List[str]:
        """Validate search fields are allowed"""
        allowed = ["document_name", "original_name", "metadata", "tags"]
        for field in v:
            if field not in allowed:
                raise ValueError(f'Invalid search field "{field}". Allowed: {allowed}')
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "q": "financial report",
                    "search_fields": ["document_name", "metadata"],
                    "page": 1,
                    "page_size": 20
                }
            ]
        }
    }


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class ProcessingStatusDetail(BaseModel):
    """Processing status for a specific stage"""
    status: str = Field(..., description="Stage status")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class DocumentResponse(BaseModel):
    """
    Full document response with all metadata
    Used for GET /documents/{id}
    """
    # Core identification
    id: str = Field(..., description="Document UUID")
    document_name: str = Field(..., description="User-facing document name")
    original_name: str = Field(..., description="Original uploaded filename")
    alternate_name: Optional[str] = Field(None, description="Alternative name")

    # File metadata
    mime_type: str = Field(..., description="MIME type")
    file_extension: str = Field(..., description="File extension")
    file_size: int = Field(..., description="File size in bytes")
    file_size_mb: float = Field(..., description="File size in megabytes")
    checksum: str = Field(..., description="File checksum (SHA-256)")

    # Storage information
    storage_provider: str = Field(..., description="Storage provider type")
    storage_path: str = Field(..., description="Storage path")
    storage_bucket: Optional[str] = Field(None, description="Storage bucket name")
    storage_region: Optional[str] = Field(None, description="Storage region")

    # Status and versioning
    status: str = Field(..., description="Document processing status")
    is_versioned_file: bool = Field(..., description="Whether file has versions")
    current_version: int = Field(..., description="Current version number")
    mutation_count: int = Field(..., description="Number of mutations")

    # Metadata
    document_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata (JSONB)"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Document tags"
    )

    # Processing timestamps
    last_extraction_at: Optional[str] = Field(None, description="Last extraction timestamp")
    last_embedding_at: Optional[str] = Field(None, description="Last embedding timestamp")
    last_indexed_at: Optional[str] = Field(None, description="Last indexing timestamp")

    # Audit trail
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    # Flags
    is_deleted: bool = Field(False, description="Soft delete flag")
    is_dirty: bool = Field(False, description="Needs reprocessing flag")
    processing_reason: Optional[str] = Field(None, description="Processing reason")

    # Optional processing status (included when requested)
    processing_status: Optional[Dict[str, ProcessingStatusDetail]] = Field(
        None,
        description="Processing status by stage"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "document_name": "report_2024.pdf",
                    "original_name": "Q4 Report.pdf",
                    "mime_type": "application/pdf",
                    "file_extension": ".pdf",
                    "file_size": 2457600,
                    "file_size_mb": 2.34,
                    "checksum": "sha256:abc123...",
                    "storage_provider": "local",
                    "status": "completed",
                    "tags": ["finance", "quarterly"],
                    "access_count": 12
                }
            ]
        }
    }


class DocumentListResponse(BaseModel):
    """
    Paginated list of documents
    Used for GET /documents
    """
    items: List[DocumentResponse] = Field(
        ...,
        description="List of documents for current page"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of documents matching filters"
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number"
    )
    page_size: int = Field(
        ...,
        ge=1,
        le=100,
        description="Items per page"
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages"
    )
    has_next: bool = Field(
        ...,
        description="Whether there is a next page"
    )
    has_previous: bool = Field(
        ...,
        description="Whether there is a previous page"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "items": [],
                    "total": 156,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 8,
                    "has_next": True,
                    "has_previous": False
                }
            ]
        }
    }


class DocumentSearchResponse(BaseModel):
    """
    Document search results
    Used for GET /documents/search
    """
    query: str = Field(..., description="Search query string")
    items: List[DocumentResponse] = Field(
        ...,
        description="Matching documents"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total matching documents"
    )
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "financial report",
                    "items": [],
                    "total": 8,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 1
                }
            ]
        }
    }


# ============================================================================
# STATISTICS MODELS
# ============================================================================

class UploadTrendItem(BaseModel):
    """Upload trend data point"""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    count: int = Field(..., ge=0, description="Number of uploads")


class TagUsageItem(BaseModel):
    """Tag usage statistics"""
    tag: str = Field(..., description="Tag name")
    count: int = Field(..., ge=0, description="Usage count")


class DocumentStatsResponse(BaseModel):
    """
    Document statistics and analytics
    Used for GET /documents/stats
    """
    # Overall metrics
    total_documents: int = Field(
        ...,
        ge=0,
        description="Total number of documents"
    )
    total_size_bytes: int = Field(
        ...,
        ge=0,
        description="Total storage size in bytes"
    )
    total_size_gb: float = Field(
        ...,
        ge=0,
        description="Total storage size in gigabytes"
    )

    # Breakdown by status
    by_status: Dict[str, int] = Field(
        default_factory=dict,
        description="Document counts by status"
    )

    # Breakdown by MIME type (top 10)
    by_mime_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Document counts by MIME type"
    )

    # Breakdown by storage provider
    by_storage_provider: Dict[str, int] = Field(
        default_factory=dict,
        description="Document counts by storage provider"
    )

    # Upload trends
    upload_trend: List[UploadTrendItem] = Field(
        default_factory=list,
        description="Upload trend over time"
    )

    # Average metrics
    avg_file_size_mb: float = Field(
        ...,
        ge=0,
        description="Average file size in megabytes"
    )

    # Tag statistics
    most_used_tags: List[TagUsageItem] = Field(
        default_factory=list,
        description="Most frequently used tags"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total_documents": 1523,
                    "total_size_bytes": 15728640000,
                    "total_size_gb": 14.65,
                    "by_status": {
                        "completed": 1420,
                        "processing": 45,
                        "pending": 32,
                        "failed": 26
                    },
                    "by_mime_type": {
                        "application/pdf": 892,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": 345
                    },
                    "avg_file_size_mb": 10.12,
                    "most_used_tags": [
                        {"tag": "finance", "count": 234},
                        {"tag": "quarterly", "count": 198}
                    ]
                }
            ]
        }
    }


# ============================================================================
# DELETE RESPONSE
# ============================================================================

class DocumentDeleteResponse(BaseModel):
    """
    Document deletion confirmation
    Used for DELETE /documents/{id}
    """
    success: bool = Field(..., description="Whether deletion succeeded")
    document_id: str = Field(..., description="Deleted document UUID")
    deleted_at: str = Field(..., description="Deletion timestamp")
    hard_delete: bool = Field(
        default=False,
        description="Whether this was a hard delete"
    )
    files_deleted: bool = Field(
        default=False,
        description="Whether physical files were deleted"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "document_id": "550e8400-e29b-41d4-a716-446655440000",
                    "deleted_at": "2024-01-16T10:00:00Z",
                    "hard_delete": False,
                    "files_deleted": True
                }
            ]
        }
    }


# ============================================================================
# ERROR RESPONSE
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: Optional[str] = Field(None, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID")
    path: Optional[str] = Field(None, description="Request path")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": "Document not found",
                    "error_code": "DOCUMENT_NOT_FOUND",
                    "timestamp": "2024-01-16T10:30:00Z",
                    "path": "/api/v1/documents/550e8400-e29b-41d4-a716-446655440000"
                }
            ]
        }
    }
