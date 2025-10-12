"""
Storage Service Exceptions
Day 3, Step 5: Custom exceptions for storage operations

Provides specific exception types for different storage failure scenarios.
"""

from typing import Optional


class StorageException(Exception):
    """Base exception for all storage-related errors"""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class FileNotFoundError(StorageException):
    """Raised when a requested file does not exist in storage"""
    
    def __init__(self, path: str, details: Optional[dict] = None):
        message = f"File not found: {path}"
        super().__init__(message, details)
        self.path = path


class StorageQuotaExceeded(StorageException):
    """Raised when storage quota limits are exceeded"""
    
    def __init__(self, 
                 used_bytes: int, 
                 quota_bytes: int, 
                 workspace_id: Optional[str] = None,
                 details: Optional[dict] = None):
        message = f"Storage quota exceeded: {used_bytes}/{quota_bytes} bytes used"
        if workspace_id:
            message += f" for workspace {workspace_id}"
        super().__init__(message, details)
        self.used_bytes = used_bytes
        self.quota_bytes = quota_bytes
        self.workspace_id = workspace_id


class InvalidPathError(StorageException):
    """Raised when a path is invalid or contains illegal characters"""
    
    def __init__(self, path: str, reason: str, details: Optional[dict] = None):
        message = f"Invalid path '{path}': {reason}"
        super().__init__(message, details)
        self.path = path
        self.reason = reason


class PermissionDeniedError(StorageException):
    """Raised when storage operation is not permitted"""
    
    def __init__(self, 
                 operation: str, 
                 path: str, 
                 details: Optional[dict] = None):
        message = f"Permission denied for {operation} on '{path}'"
        super().__init__(message, details)
        self.operation = operation
        self.path = path


class StorageConnectionError(StorageException):
    """Raised when connection to storage backend fails"""
    
    def __init__(self, 
                 provider: str, 
                 reason: str, 
                 details: Optional[dict] = None):
        message = f"Failed to connect to {provider} storage: {reason}"
        super().__init__(message, details)
        self.provider = provider
        self.reason = reason