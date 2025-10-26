"""
Local Storage Provider
Day 3, Step 5: Local filesystem implementation of StorageProvider

Implements storage operations for local filesystem with security checks
and proper permission handling.
"""

import os
import shutil
import aiofiles
import aiofiles.os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from app.core.config import settings
from .base import StorageProvider
from .exceptions import (
    FileNotFoundError,
    StorageException,
    InvalidPathError,
    PermissionDeniedError
)

logger = logging.getLogger(__name__)


class LocalStorageProvider(StorageProvider):
    """
    Local filesystem storage provider implementation.
    
    Stores files on the local filesystem with proper permission handling
    and security checks. This is the default provider for MVP phase.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize local storage provider.
        
        Args:
            config: Optional configuration, defaults to settings
        """
        default_config = {
            'root_path': settings.STORAGE_PATH,
            'dir_permissions': 0o755,
            'file_permissions': 0o644
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)
        
        # Ensure root storage directory exists
        self.root_path = Path(self.config['root_path'])
        self.root_path.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root_path, self.config['dir_permissions'])
    
    def _get_full_path(self, path: str) -> Path:
        """
        Convert relative path to full filesystem path.
        
        Args:
            path: Relative storage path
            
        Returns:
            Full filesystem path
            
        Raises:
            InvalidPathError: If path would escape storage root
        """
        # Validate the path first
        self.validate_path(path)
        
        full_path = (self.root_path / path).resolve()
        
        # Security check: ensure path is within storage root
        try:
            full_path.relative_to(self.root_path.resolve())
        except ValueError:
            raise InvalidPathError(path, "Path would escape storage root")
        
        return full_path
    
    async def save_file(self, file_content: bytes, path: str) -> str:
        """
        Save file to local filesystem.
        
        Creates parent directories if needed and sets proper permissions.
        """
        try:
            full_path = self._get_full_path(path)
            
            # Create parent directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Set directory permissions
            for parent in full_path.parents:
                if parent.is_relative_to(self.root_path) and parent != self.root_path:
                    os.chmod(parent, self.config['dir_permissions'])
            
            # Write file asynchronously
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(file_content)
            
            # Set file permissions
            os.chmod(full_path, self.config['file_permissions'])
            
            logger.info(f"File saved successfully: {path}")
            return path

        except (InvalidPathError, FileNotFoundError, PermissionDeniedError):
            # Re-raise storage-specific exceptions without wrapping
            raise
        except OSError as e:
            logger.error(f"Failed to save file {path}: {e}")
            if e.errno == 28:  # No space left on device
                from .exceptions import StorageQuotaExceeded
                # Get disk usage info
                stat = os.statvfs(self.root_path)
                used = (stat.f_blocks - stat.f_available) * stat.f_frsize
                total = stat.f_blocks * stat.f_frsize
                raise StorageQuotaExceeded(used, total)
            raise StorageException(f"Failed to save file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error saving file {path}: {e}")
            raise StorageException(f"Failed to save file: {e}")
    
    async def get_file(self, path: str) -> bytes:
        """Retrieve file from local filesystem."""
        try:
            full_path = self._get_full_path(path)
            
            if not full_path.exists():
                raise FileNotFoundError(path)
            
            if not full_path.is_file():
                raise InvalidPathError(path, "Path is not a file")
            
            # Read file asynchronously
            async with aiofiles.open(full_path, 'rb') as f:
                content = await f.read()
            
            logger.debug(f"File retrieved successfully: {path}")
            return content
            
        except FileNotFoundError:
            raise
        except PermissionError:
            raise PermissionDeniedError("read", path)
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            raise StorageException(f"Failed to read file: {e}")
    
    async def delete_file(self, path: str) -> bool:
        """Delete file from local filesystem."""
        try:
            full_path = self._get_full_path(path)
            
            if not full_path.exists():
                return False
            
            if not full_path.is_file():
                raise InvalidPathError(path, "Path is not a file")
            
            # Delete file asynchronously
            await aiofiles.os.remove(full_path)
            
            logger.info(f"File deleted successfully: {path}")
            return True
            
        except PermissionError:
            raise PermissionDeniedError("delete", path)
        except Exception as e:
            logger.error(f"Failed to delete file {path}: {e}")
            raise StorageException(f"Failed to delete file: {e}")
    
    async def exists(self, path: str) -> bool:
        """Check if file exists in local filesystem."""
        try:
            full_path = self._get_full_path(path)
            return full_path.exists() and full_path.is_file()
        except InvalidPathError:
            return False
        except Exception as e:
            logger.error(f"Failed to check file existence {path}: {e}")
            raise StorageException(f"Failed to check file existence: {e}")
    
    async def get_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Local storage doesn't support URLs.
        
        Returns None as files must be accessed through the application.
        """
        # Verify file exists
        if not await self.exists(path):
            raise FileNotFoundError(path)
        
        # Local storage doesn't provide direct URLs
        return None
    
    async def move_file(self, old_path: str, new_path: str) -> bool:
        """Move or rename file within local filesystem."""
        try:
            old_full_path = self._get_full_path(old_path)
            new_full_path = self._get_full_path(new_path)
            
            if not old_full_path.exists():
                raise FileNotFoundError(old_path)
            
            if not old_full_path.is_file():
                raise InvalidPathError(old_path, "Source is not a file")
            
            # Create parent directories for destination
            new_full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(str(old_full_path), str(new_full_path))
            
            # Set permissions on new file
            os.chmod(new_full_path, self.config['file_permissions'])
            
            logger.info(f"File moved successfully: {old_path} -> {new_path}")
            return True
            
        except FileNotFoundError:
            raise
        except PermissionError:
            raise PermissionDeniedError("move", f"{old_path} -> {new_path}")
        except Exception as e:
            logger.error(f"Failed to move file {old_path} -> {new_path}: {e}")
            raise StorageException(f"Failed to move file: {e}")
    
    async def get_file_size(self, path: str) -> int:
        """Get file size efficiently using stat."""
        try:
            full_path = self._get_full_path(path)
            
            if not full_path.exists():
                raise FileNotFoundError(path)
            
            stat = await aiofiles.os.stat(full_path)
            return stat.st_size
            
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get file size {path}: {e}")
            raise StorageException(f"Failed to get file size: {e}")
    
    async def list_files(self, prefix: str = "", recursive: bool = True) -> list[str]:
        """List files in storage with optional prefix filter."""
        try:
            results = []
            search_path = self._get_full_path(prefix) if prefix else self.root_path

            # Resolve root_path to handle symlinks (e.g., /var -> /private/var on macOS)
            resolved_root = self.root_path.resolve()

            if search_path.is_file():
                # If prefix points to a file, return just that file
                rel_path = search_path.resolve().relative_to(resolved_root)
                return [str(rel_path)]

            if not search_path.is_dir():
                return []

            # Walk directory tree
            if recursive:
                for root, _, files in os.walk(search_path):
                    root_path = Path(root)
                    for file in files:
                        file_path = root_path / file
                        # Resolve symlinks before computing relative path
                        rel_path = file_path.resolve().relative_to(resolved_root)
                        results.append(str(rel_path))
            else:
                # List only immediate children
                for item in search_path.iterdir():
                    if item.is_file():
                        # Resolve symlinks before computing relative path
                        rel_path = item.resolve().relative_to(resolved_root)
                        results.append(str(rel_path))

            return results

        except Exception as e:
            logger.error(f"Failed to list files with prefix {prefix}: {e}")
            raise StorageException(f"Failed to list files: {e}")