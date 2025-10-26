"""
Storage Provider Base Class
Day 3, Step 5: Abstract base class for storage providers

Defines the interface that all storage providers must implement.
Supports local, S3, Azure Blob, and other storage backends.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import asyncio
from pathlib import Path


class StorageProvider(ABC):
    """
    Abstract base class for storage providers.
    
    All storage providers (Local, S3, Azure, etc.) must implement these methods
    to ensure consistent behavior across different storage backends.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize storage provider with configuration.
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
    
    @abstractmethod
    async def save_file(self, file_content: bytes, path: str) -> str:
        """
        Save file content to storage.
        
        Args:
            file_content: The file content as bytes
            path: The storage path (relative to storage root)
            
        Returns:
            The final storage path where file was saved
            
        Raises:
            StorageException: If save operation fails
            StorageQuotaExceeded: If storage quota is exceeded
            InvalidPathError: If path is invalid
        """
        pass
    
    @abstractmethod
    async def get_file(self, path: str) -> bytes:
        """
        Retrieve file content from storage.
        
        Args:
            path: The storage path (relative to storage root)
            
        Returns:
            The file content as bytes
            
        Raises:
            FileNotFoundError: If file does not exist
            PermissionDeniedError: If access is denied
            StorageException: For other storage errors
        """
        pass
    
    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            path: The storage path (relative to storage root)
            
        Returns:
            True if file was deleted, False if file didn't exist
            
        Raises:
            PermissionDeniedError: If deletion is not permitted
            StorageException: For other storage errors
        """
        pass
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            path: The storage path (relative to storage root)
            
        Returns:
            True if file exists, False otherwise
            
        Raises:
            StorageException: For storage access errors
        """
        pass
    
    @abstractmethod
    async def get_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get a URL for accessing the file.
        
        For local storage, returns None. For cloud storage, returns
        a presigned URL valid for the specified duration.
        
        Args:
            path: The storage path (relative to storage root)
            expires_in: URL expiration time in seconds (default 1 hour)
            
        Returns:
            URL string for cloud storage, None for local storage
            
        Raises:
            FileNotFoundError: If file does not exist
            StorageException: For other storage errors
        """
        pass
    
    @abstractmethod
    async def move_file(self, old_path: str, new_path: str) -> bool:
        """
        Move or rename a file within storage.
        
        Args:
            old_path: Current file path (relative to storage root)
            new_path: New file path (relative to storage root)
            
        Returns:
            True if move was successful
            
        Raises:
            FileNotFoundError: If source file does not exist
            InvalidPathError: If new path is invalid
            PermissionDeniedError: If operation is not permitted
            StorageException: For other storage errors
        """
        pass
    
    # Utility methods that can be overridden if needed
    
    async def get_file_size(self, path: str) -> int:
        """
        Get the size of a file in bytes.
        
        Default implementation retrieves the file and checks its length.
        Providers should override with more efficient implementations.
        
        Args:
            path: The storage path (relative to storage root)
            
        Returns:
            File size in bytes
            
        Raises:
            FileNotFoundError: If file does not exist
        """
        content = await self.get_file(path)
        return len(content)
    
    async def list_files(self, prefix: str = "", recursive: bool = True) -> list[str]:
        """
        List files in storage with optional prefix filter.
        
        Args:
            prefix: Path prefix to filter results
            recursive: Include files in subdirectories
            
        Returns:
            List of file paths matching the criteria
            
        Raises:
            StorageException: For storage access errors
        """
        raise NotImplementedError("list_files not implemented for this provider")
    
    def validate_path(self, path: str) -> bool:
        """
        Validate that a path is safe and valid.

        Checks for path traversal attempts and invalid characters.

        Args:
            path: Path to validate

        Returns:
            True if path is valid, raises exception otherwise

        Raises:
            InvalidPathError: If path is invalid
        """
        from .exceptions import InvalidPathError

        # Check for null bytes
        if '\x00' in path:
            raise InvalidPathError(path, "Path contains null bytes")

        # Check for absolute paths
        if path.startswith('/') or path.startswith('\\'):
            raise InvalidPathError(path, "Absolute paths not allowed")

        # Check for Windows absolute paths (C:, D:, etc.)
        if len(path) >= 2 and path[1] == ':':
            raise InvalidPathError(path, "Absolute paths not allowed")

        # Check for path traversal patterns
        if '..' in path:
            raise InvalidPathError(path, "Path traversal detected")

        # Check for other dangerous patterns
        if '//' in path or '\\\\' in path:
            raise InvalidPathError(path, "Invalid path separators")

        return True
    
    def __repr__(self) -> str:
        """String representation of the storage provider"""
        return f"{self.__class__.__name__}(config={self.config})"