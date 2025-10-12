"""
Storage Service Package
Day 3, Step 5: Storage Service Pattern Implementation

This package provides abstracted storage operations supporting multiple providers.
Currently implements local storage with future support for S3, Azure Blob, etc.
"""

from .base import StorageProvider
from .local import LocalStorageProvider
from .path_generator import PathGenerator
from .manager import StorageManager
from .exceptions import (
    StorageException,
    FileNotFoundError,
    StorageQuotaExceeded,
    InvalidPathError,
    PermissionDeniedError,
    StorageConnectionError
)

__all__ = [
    'StorageProvider',
    'LocalStorageProvider',
    'PathGenerator',
    'StorageManager',
    'StorageException',
    'FileNotFoundError',
    'StorageQuotaExceeded',
    'InvalidPathError',
    'PermissionDeniedError',
    'StorageConnectionError'
]