"""
Storage Path Generator
Day 3, Step 5: Path generation and filename sanitization

Generates organized storage paths following the pattern:
{workspace_id}/{year}/{month}/{document_id}/{filename}
"""

import re
import unicodedata
from datetime import datetime
from uuid import UUID
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PathGenerator:
    """
    Generates and manages storage paths for documents.
    
    Follows the organizational pattern from PROJECT.md to handle
    millions of documents efficiently without filesystem limitations.
    """
    
    # Pattern for valid filename characters (alphanumeric, dash, underscore, dot)
    VALID_FILENAME_PATTERN = re.compile(r'[^a-zA-Z0-9._-]')
    
    # Maximum filename length (leave room for path components)
    MAX_FILENAME_LENGTH = 200
    
    # Temporary directory name
    TEMP_DIR = "_temp"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to remove invalid characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for storage
            
        Process:
        1. Normalize unicode characters
        2. Replace spaces with underscores
        3. Remove invalid characters
        4. Preserve file extension
        5. Truncate if too long
        """
        # Normalize unicode characters
        filename = unicodedata.normalize('NFKD', filename)
        filename = filename.encode('ascii', 'ignore').decode('ascii')
        
        # Split name and extension
        name_parts = filename.rsplit('.', 1)
        name = name_parts[0]
        ext = f".{name_parts[1]}" if len(name_parts) > 1 else ""
        
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        
        # Remove invalid characters
        name = PathGenerator.VALID_FILENAME_PATTERN.sub('', name)
        
        # Ensure name is not empty
        if not name:
            name = "unnamed"
        
        # Truncate if necessary (leave room for extension)
        max_name_length = PathGenerator.MAX_FILENAME_LENGTH - len(ext)
        if len(name) > max_name_length:
            name = name[:max_name_length]
        
        # Reconstruct filename
        sanitized = f"{name}{ext}"
        
        logger.debug(f"Sanitized filename: '{filename}' -> '{sanitized}'")
        return sanitized
    
    @staticmethod
    def generate_document_path(
        workspace_id: UUID,
        document_id: UUID,
        filename: str,
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Generate organized storage path for a document.
        
        Args:
            workspace_id: Workspace UUID (for future multi-tenant support)
            document_id: Document UUID
            filename: Original filename
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Path string following pattern:
            {workspace_id}/{year}/{month}/{document_id}/{filename}
            
        Example:
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890/2024/11/
             f9e8d7c6-b5a4-3210-9876-543210fedcba/report.pdf"
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Extract date components
        year = timestamp.strftime("%Y")
        month = timestamp.strftime("%m")
        
        # Sanitize filename
        safe_filename = PathGenerator.sanitize_filename(filename)
        
        # Build path components
        path_components = [
            str(workspace_id),
            year,
            month,
            str(document_id),
            safe_filename
        ]
        
        # Join with forward slashes (works on all platforms)
        path = "/".join(path_components)
        
        logger.debug(f"Generated document path: {path}")
        return path
    
    @staticmethod
    def generate_temp_path(
        filename: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Generate temporary storage path for uploads.
        
        Args:
            filename: Original filename
            session_id: Optional upload session ID
            
        Returns:
            Temporary path like: _temp/2024-11-15/session_id/filename
            or: _temp/2024-11-15/filename
        """
        # Current date for organization
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Sanitize filename
        safe_filename = PathGenerator.sanitize_filename(filename)
        
        # Build path
        if session_id:
            path = f"{PathGenerator.TEMP_DIR}/{date_str}/{session_id}/{safe_filename}"
        else:
            # Add timestamp to prevent conflicts
            timestamp = datetime.utcnow().strftime("%H%M%S_%f")[:10]
            path = f"{PathGenerator.TEMP_DIR}/{date_str}/{timestamp}_{safe_filename}"
        
        logger.debug(f"Generated temp path: {path}")
        return path
    
    @staticmethod
    def extract_components(path: str) -> Dict[str, Optional[str]]:
        """
        Extract components from a storage path.
        
        Args:
            path: Storage path to parse
            
        Returns:
            Dictionary with extracted components:
            - workspace_id: UUID string or None
            - year: Year string or None
            - month: Month string or None
            - document_id: UUID string or None
            - filename: Filename or None
            - is_temp: Boolean indicating if this is a temp path
            
        Example:
            Input: "a1b2c3d4.../2024/11/f9e8d7c6.../report.pdf"
            Output: {
                'workspace_id': 'a1b2c3d4...',
                'year': '2024',
                'month': '11',
                'document_id': 'f9e8d7c6...',
                'filename': 'report.pdf',
                'is_temp': False
            }
        """
        components = {
            'workspace_id': None,
            'year': None,
            'month': None,
            'document_id': None,
            'filename': None,
            'is_temp': False
        }
        
        # Convert to Path object for easier handling
        path_obj = Path(path)
        parts = path_obj.parts
        
        if not parts:
            return components
        
        # Check if it's a temporary path
        if parts[0] == PathGenerator.TEMP_DIR:
            components['is_temp'] = True
            # For temp paths, the last part is the filename
            if len(parts) > 1:
                components['filename'] = parts[-1]
            return components
        
        # Parse standard document path
        if len(parts) >= 5:
            # Full path with all components
            components['workspace_id'] = parts[0]
            components['year'] = parts[1]
            components['month'] = parts[2]
            components['document_id'] = parts[3]
            components['filename'] = parts[4]
        elif len(parts) == 4:
            # Missing filename
            components['workspace_id'] = parts[0]
            components['year'] = parts[1]
            components['month'] = parts[2]
            components['document_id'] = parts[3]
        elif len(parts) >= 1:
            # Partial path - try to identify components
            # This is a best-effort parsing
            try:
                # Check if first part looks like a UUID
                UUID(parts[0])
                components['workspace_id'] = parts[0]
                
                if len(parts) > 1 and parts[1].isdigit() and len(parts[1]) == 4:
                    components['year'] = parts[1]
                    
                if len(parts) > 2 and parts[2].isdigit() and len(parts[2]) == 2:
                    components['month'] = parts[2]
                    
                if len(parts) > 3:
                    try:
                        UUID(parts[3])
                        components['document_id'] = parts[3]
                        if len(parts) > 4:
                            components['filename'] = parts[4]
                    except ValueError:
                        # Not a UUID, might be filename
                        components['filename'] = parts[3]
            except ValueError:
                # First part is not a UUID, might be a simple filename
                components['filename'] = parts[-1]
        
        return components
    
    @staticmethod
    def is_valid_document_path(path: str) -> bool:
        """
        Check if a path follows the expected document storage pattern.
        
        Args:
            path: Path to validate
            
        Returns:
            True if path matches expected pattern
        """
        components = PathGenerator.extract_components(path)
        
        # For document paths, we need all components except temp flag
        required = ['workspace_id', 'year', 'month', 'document_id', 'filename']
        
        for field in required:
            if not components.get(field):
                return False
        
        # Validate year and month
        try:
            year = int(components['year'])
            month = int(components['month'])
            
            if year < 2000 or year > 2100:  # Reasonable year range
                return False
            if month < 1 or month > 12:
                return False
            
            # Validate UUIDs
            UUID(components['workspace_id'])
            UUID(components['document_id'])
            
        except (ValueError, TypeError):
            return False
        
        return True
    
    @staticmethod
    def get_versioned_path(path: str, version: int) -> str:
        """
        Generate a versioned path for document history.
        
        Args:
            path: Current document path
            version: Version number
            
        Returns:
            Versioned path with version directory inserted
            
        Example:
            Input: ".../document_id/file.pdf", version=2
            Output: ".../document_id/v2/file.pdf"
        """
        components = PathGenerator.extract_components(path)
        
        if not components['filename']:
            raise ValueError("Cannot create versioned path without filename")
        
        # Rebuild path with version directory
        if components['is_temp']:
            # Don't version temporary files
            return path
        
        path_parts = []
        if components['workspace_id']:
            path_parts.append(components['workspace_id'])
        if components['year']:
            path_parts.append(components['year'])
        if components['month']:
            path_parts.append(components['month'])
        if components['document_id']:
            path_parts.append(components['document_id'])
        
        # Add version directory
        path_parts.append(f"v{version}")
        
        # Add filename
        path_parts.append(components['filename'])
        
        return "/".join(path_parts)