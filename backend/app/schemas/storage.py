"""
Storage Schemas
Day 3, Step 5: Pydantic models for storage operations

Defines data models for storage operations, results, and configuration.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ConflictStrategy(str, Enum):
    """
    Strategies for handling filename conflicts.
    
    TIMESTAMP: Append timestamp (report_20241115_143022.pdf)
    COUNTER: Append incrementing number (report_1.pdf, report_2.pdf)
    UUID: Prepend short UUID (7f3e4a_report.pdf)
    """
    TIMESTAMP = "timestamp"
    COUNTER = "counter"
    UUID = "uuid"


class StorageProviderType(str, Enum):
    """Supported storage provider types"""
    LOCAL = "local"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"


class StorageResult(BaseModel):
    """Result of a storage operation"""
    
    # File identification
    document_id: UUID = Field(..., description="Unique document identifier")
    path: str = Field(..., description="Storage path relative to root")
    
    # File metadata
    size: int = Field(..., description="File size in bytes")
    checksum: str = Field(..., description="SHA256 checksum of file content")
    mime_type: str = Field(..., description="Detected MIME type")
    
    # Storage details
    provider: StorageProviderType = Field(..., description="Storage provider used")
    storage_url: Optional[str] = Field(None, description="Public URL if available")
    
    # Operation metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    operation_time_ms: float = Field(..., description="Operation duration in milliseconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "path": "workspace/2024/11/123e4567/report.pdf",
                "size": 1048576,
                "checksum": "d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2",
                "mime_type": "application/pdf",
                "provider": "local",
                "storage_url": None,
                "created_at": "2024-11-15T14:30:00Z",
                "operation_time_ms": 125.5
            }
        }


class StorageStats(BaseModel):
    """Storage statistics for a workspace"""
    
    workspace_id: UUID = Field(..., description="Workspace identifier")
    
    # Storage usage
    used_bytes: int = Field(..., description="Total bytes used")
    file_count: int = Field(..., description="Number of files stored")
    
    # Quotas
    quota_bytes: Optional[int] = Field(None, description="Storage quota in bytes")
    quota_percentage: Optional[float] = Field(None, description="Percentage of quota used")
    
    # Breakdown by type
    usage_by_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Bytes used per file type"
    )
    
    # Temporal stats
    last_upload: Optional[datetime] = Field(None, description="Last upload timestamp")
    oldest_file: Optional[datetime] = Field(None, description="Oldest file timestamp")
    
    # Calculated fields
    average_file_size: Optional[float] = Field(None, description="Average file size in bytes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
                "used_bytes": 104857600,
                "file_count": 42,
                "quota_bytes": 1073741824,
                "quota_percentage": 9.77,
                "usage_by_type": {
                    "pdf": 52428800,
                    "docx": 31457280,
                    "xlsx": 20971520
                },
                "last_upload": "2024-11-15T14:30:00Z",
                "oldest_file": "2024-01-01T00:00:00Z",
                "average_file_size": 2496800.0
            }
        }


class StorageConfig(BaseModel):
    """Configuration for storage providers"""
    
    provider: StorageProviderType = Field(..., description="Storage provider type")
    
    # Common settings
    root_path: Optional[str] = Field(None, description="Root storage path")
    max_file_size: int = Field(31457280, description="Maximum file size (default 30MB)")
    
    # Provider-specific settings
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific configuration"
    )
    
    # Features
    enable_versioning: bool = Field(False, description="Enable file versioning")
    enable_compression: bool = Field(False, description="Enable automatic compression")
    
    class Config:
        json_schema_extra = {
            "example": {
                "provider": "local",
                "root_path": "/app/storage",
                "max_file_size": 31457280,
                "settings": {
                    "dir_permissions": "755",
                    "file_permissions": "644"
                },
                "enable_versioning": False,
                "enable_compression": False
            }
        }


class StorageOperation(BaseModel):
    """Record of a storage operation for audit trail"""
    
    operation_id: UUID = Field(default_factory=UUID, description="Unique operation ID")
    operation_type: str = Field(..., description="Type of operation (save, retrieve, delete)")
    
    # Target
    document_id: Optional[UUID] = Field(None, description="Document ID if applicable")
    path: str = Field(..., description="Storage path")
    
    # Metadata
    workspace_id: UUID = Field(..., description="Workspace performing operation")
    user_id: Optional[UUID] = Field(None, description="User performing operation")
    
    # Results
    success: bool = Field(..., description="Whether operation succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: float = Field(..., description="Operation duration")
    
    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StorageCleanupResult(BaseModel):
    """Result of storage cleanup operation"""
    
    temp_files_deleted: int = Field(..., description="Number of temp files deleted")
    orphaned_files_deleted: int = Field(..., description="Number of orphaned files deleted")
    bytes_freed: int = Field(..., description="Total bytes freed")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")
    duration_seconds: float = Field(..., description="Cleanup duration")