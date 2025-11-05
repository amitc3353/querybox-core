"""
Storage Configuration
Day 3, Step 5: Storage-specific configuration settings

Centralizes storage configuration with environment variable support.
"""

import os
import re
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings

from app.schemas.storage import ConflictStrategy, StorageProviderType


class StorageSettings(BaseSettings):
    """Storage-specific configuration settings"""
    
    # Path constraints
    MAX_PATH_LENGTH: int = Field(
        default=255,
        description="Maximum allowed path length"
    )
    
    # Filename sanitization pattern
    # Allows alphanumeric, dash, underscore, dot
    ALLOWED_CHARS_PATTERN: str = Field(
        default=r'[^a-zA-Z0-9._-]',
        description="Regex pattern for invalid filename characters"
    )
    
    # Conflict resolution
    CONFLICT_STRATEGY: ConflictStrategy = Field(
        default=ConflictStrategy.TIMESTAMP,
        description="Strategy for handling filename conflicts"
    )
    
    # Temporary file management
    TEMP_RETENTION_DAYS: int = Field(
        default=1,
        description="Days to retain temporary files before cleanup"
    )
    
    # Storage quotas (in bytes)
    DEFAULT_WORKSPACE_QUOTA_GB: int = Field(
        default=10,
        description="Default storage quota per workspace in GB"
    )
    
    @property
    def DEFAULT_WORKSPACE_QUOTA_BYTES(self) -> int:
        """Convert GB quota to bytes"""
        return self.DEFAULT_WORKSPACE_QUOTA_GB * 1024 * 1024 * 1024
    
    # Storage provider
    STORAGE_PROVIDER: StorageProviderType = Field(
        default=StorageProviderType.LOCAL,
        description="Active storage provider"
    )
    
    # Provider-specific settings
    # Local storage
    LOCAL_STORAGE_ROOT: str = Field(
        default="storage",
        description="Root directory for local storage"
    )
    
    LOCAL_DIR_PERMISSIONS: int = Field(
        default=0o755,
        description="Directory permissions for local storage"
    )
    
    LOCAL_FILE_PERMISSIONS: int = Field(
        default=0o644,
        description="File permissions for local storage"
    )
    
    # S3 settings (for future use)
    S3_BUCKET_NAME: Optional[str] = Field(
        default=None,
        description="S3 bucket name"
    )
    
    S3_REGION: Optional[str] = Field(
        default="us-east-1",
        description="S3 region"
    )
    
    S3_ACCESS_KEY_ID: Optional[str] = Field(
        default=None,
        description="S3 access key ID"
    )
    
    S3_SECRET_ACCESS_KEY: Optional[str] = Field(
        default=None,
        description="S3 secret access key"
    )
    
    # Azure Blob settings (for future use)
    AZURE_STORAGE_ACCOUNT: Optional[str] = Field(
        default=None,
        description="Azure storage account name"
    )
    
    AZURE_STORAGE_KEY: Optional[str] = Field(
        default=None,
        description="Azure storage account key"
    )
    
    AZURE_CONTAINER_NAME: Optional[str] = Field(
        default=None,
        description="Azure blob container name"
    )
    
    # Performance settings
    STORAGE_OPERATION_TIMEOUT: int = Field(
        default=30,
        description="Timeout for storage operations in seconds"
    )
    
    CONCURRENT_UPLOADS_LIMIT: int = Field(
        default=10,
        description="Maximum concurrent upload operations"
    )
    
    # Chunking for large files
    UPLOAD_CHUNK_SIZE_MB: int = Field(
        default=5,
        description="Size of chunks for multipart uploads in MB"
    )
    
    @property
    def UPLOAD_CHUNK_SIZE_BYTES(self) -> int:
        """Convert MB chunk size to bytes"""
        return self.UPLOAD_CHUNK_SIZE_MB * 1024 * 1024
    
    # Caching
    ENABLE_STORAGE_CACHE: bool = Field(
        default=True,
        description="Enable caching for storage operations"
    )
    
    CACHE_TTL_SECONDS: int = Field(
        default=3600,
        description="Cache TTL in seconds"
    )
    
    # Security
    ENABLE_VIRUS_SCAN: bool = Field(
        default=False,
        description="Enable virus scanning for uploads"
    )
    
    ALLOWED_MIME_TYPES: list[str] = Field(
        default=[
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "text/plain",
            "text/markdown",
            "text/html",
            "text/csv",
            "application/json",
            "application/xml",
            "text/xml"
        ],
        description="Allowed MIME types for uploads"
    )
    
    class Config:
        env_file = ".env"
        env_prefix = "STORAGE_"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables not defined in Settings
        
        json_schema_extra = {
            "example": {
                "MAX_PATH_LENGTH": 255,
                "CONFLICT_STRATEGY": "timestamp",
                "TEMP_RETENTION_DAYS": 1,
                "DEFAULT_WORKSPACE_QUOTA_GB": 10,
                "STORAGE_PROVIDER": "local",
                "LOCAL_STORAGE_ROOT": "storage"
            }
        }

    def get_provider_config(self) -> dict:
        """Get configuration for the active storage provider"""
        if self.STORAGE_PROVIDER == StorageProviderType.LOCAL:
            return {
                "root_path": self.LOCAL_STORAGE_ROOT,
                "dir_permissions": self.LOCAL_DIR_PERMISSIONS,
                "file_permissions": self.LOCAL_FILE_PERMISSIONS
            }
        elif self.STORAGE_PROVIDER == StorageProviderType.S3:
            return {
                "bucket_name": self.S3_BUCKET_NAME,
                "region": self.S3_REGION,
                "access_key_id": self.S3_ACCESS_KEY_ID,
                "secret_access_key": self.S3_SECRET_ACCESS_KEY
            }
        elif self.STORAGE_PROVIDER == StorageProviderType.AZURE_BLOB:
            return {
                "account_name": self.AZURE_STORAGE_ACCOUNT,
                "account_key": self.AZURE_STORAGE_KEY,
                "container_name": self.AZURE_CONTAINER_NAME
            }
        else:
            raise ValueError(f"Unknown storage provider: {self.STORAGE_PROVIDER}")
    
    def validate_settings(self) -> bool:
        """Validate that required settings are present for the active provider"""
        if self.STORAGE_PROVIDER == StorageProviderType.S3:
            required = [
                self.S3_BUCKET_NAME,
                self.S3_ACCESS_KEY_ID,
                self.S3_SECRET_ACCESS_KEY
            ]
            if not all(required):
                raise ValueError("S3 storage requires bucket_name, access_key_id, and secret_access_key")
        
        elif self.STORAGE_PROVIDER == StorageProviderType.AZURE_BLOB:
            required = [
                self.AZURE_STORAGE_ACCOUNT,
                self.AZURE_STORAGE_KEY,
                self.AZURE_CONTAINER_NAME
            ]
            if not all(required):
                raise ValueError("Azure storage requires account_name, account_key, and container_name")
        
        return True


# Global storage settings instance
storage_settings = StorageSettings()