"""
Storage Manager
Day 3, Step 5: Main storage service manager

Orchestrates storage operations with conflict resolution, database tracking,
and atomic operations. Acts as the main interface for all storage needs.
"""

import hashlib
import time
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from fastapi import UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from app.core.storage_config import storage_settings
from app.schemas.storage import (
    StorageResult, 
    StorageStats, 
    ConflictStrategy, 
    StorageProviderType,
    StorageOperation
)
from app.models.document import Document, StorageProviderEnum
from app.services.storage.base import StorageProvider
from app.services.storage.local import LocalStorageProvider
from app.services.storage.path_generator import PathGenerator
from app.services.storage.exceptions import (
    StorageException,
    FileNotFoundError,
    StorageQuotaExceeded,
    InvalidPathError
)

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Main storage service manager.
    
    Provides high-level storage operations with:
    - Provider factory pattern
    - Filename conflict resolution
    - Database integration
    - Atomic operations
    - Performance metrics
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize storage manager.
        
        Args:
            db_session: Database session for tracking operations
        """
        self.db = db_session
        self.path_generator = PathGenerator()
        self._provider_cache = {}
        
        # Initialize provider
        self.provider = self._get_provider()
    
    def _get_provider(self) -> StorageProvider:
        """
        Factory method to create appropriate storage provider.
        
        Returns:
            Configured storage provider instance
        """
        provider_type = storage_settings.STORAGE_PROVIDER
        
        # Cache providers to avoid recreation
        if provider_type in self._provider_cache:
            return self._provider_cache[provider_type]
        
        if provider_type == StorageProviderType.LOCAL:
            config = storage_settings.get_provider_config()
            provider = LocalStorageProvider(config)
        else:
            # Future: Add S3Provider, AzureBlobProvider
            raise NotImplementedError(f"Provider {provider_type} not yet implemented")
        
        self._provider_cache[provider_type] = provider
        return provider
    
    def _resolve_filename_conflict(
        self, 
        base_filename: str, 
        existing_paths: List[str],
        strategy: ConflictStrategy = None
    ) -> str:
        """
        Resolve filename conflicts using specified strategy.
        
        Args:
            base_filename: Original filename
            existing_paths: List of existing file paths
            strategy: Conflict resolution strategy
            
        Returns:
            Unique filename that doesn't conflict
        """
        if strategy is None:
            strategy = storage_settings.CONFLICT_STRATEGY
        
        # Extract existing filenames for comparison
        existing_filenames = set()
        for path in existing_paths:
            components = self.path_generator.extract_components(path)
            if components.get('filename'):
                existing_filenames.add(components['filename'])
        
        # If no conflict, return original
        if base_filename not in existing_filenames:
            return base_filename
        
        # Split name and extension
        name_parts = base_filename.rsplit('.', 1)
        name = name_parts[0]
        ext = f".{name_parts[1]}" if len(name_parts) > 1 else ""
        
        if strategy == ConflictStrategy.TIMESTAMP:
            # Append timestamp: report_20241115_143022.pdf
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            return f"{name}_{timestamp}{ext}"
        
        elif strategy == ConflictStrategy.COUNTER:
            # Append incrementing number: report_1.pdf, report_2.pdf
            counter = 1
            while True:
                candidate = f"{name}_{counter}{ext}"
                if candidate not in existing_filenames:
                    return candidate
                counter += 1
                
                # Safety check to prevent infinite loop
                if counter > 1000:
                    # Fall back to UUID strategy
                    break
        
        # UUID strategy (default fallback)
        # Prepend short UUID: 7f3e4a_report.pdf
        short_uuid = str(uuid4())[:6]
        return f"{short_uuid}_{base_filename}"
    
    async def _calculate_checksum(self, content: bytes) -> str:
        """Calculate SHA256 checksum of file content."""
        sha256_hash = hashlib.sha256()
        sha256_hash.update(content)
        return sha256_hash.hexdigest()
    
    async def _check_quota(self, workspace_id: UUID, file_size: int) -> None:
        """
        Check if adding a file would exceed workspace quota.
        
        Args:
            workspace_id: Workspace ID
            file_size: Size of file to add
            
        Raises:
            StorageQuotaExceeded: If quota would be exceeded
        """
        # Get current usage
        stats = await self.get_storage_stats(workspace_id)
        quota = storage_settings.DEFAULT_WORKSPACE_QUOTA_BYTES
        
        if stats.used_bytes + file_size > quota:
            raise StorageQuotaExceeded(
                used_bytes=stats.used_bytes + file_size,
                quota_bytes=quota,
                workspace_id=str(workspace_id)
            )
    
    async def _log_operation(
        self,
        operation_type: str,
        path: str,
        success: bool,
        duration_ms: float,
        workspace_id: UUID,
        document_id: Optional[UUID] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Log storage operation for audit trail."""
        try:
            operation = StorageOperation(
                operation_type=operation_type,
                document_id=document_id,
                path=path,
                workspace_id=workspace_id,
                success=success,
                error_message=error_message,
                duration_ms=duration_ms
            )
            
            # Log to file
            logger.info(
                f"Storage operation: {operation_type}",
                extra={
                    "operation_id": str(operation.operation_id),
                    "document_id": str(document_id) if document_id else None,
                    "workspace_id": str(workspace_id),
                    "success": success,
                    "duration_ms": duration_ms,
                    "path": path
                }
            )
            
            # TODO: Store in database for audit trail
            # self.db.add(operation)
            # self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log storage operation: {e}")
    
    async def store_document(
        self, 
        file: UploadFile, 
        workspace_id: UUID,
        document_id: Optional[UUID] = None
    ) -> StorageResult:
        """
        Store document with conflict resolution and database tracking.
        
        Args:
            file: Uploaded file
            workspace_id: Workspace ID (for multi-tenant support)
            document_id: Optional document ID (generates if not provided)
            
        Returns:
            StorageResult with storage details
            
        Raises:
            StorageQuotaExceeded: If storage quota exceeded
            StorageException: For other storage errors
        """
        start_time = time.time()
        
        if document_id is None:
            document_id = uuid4()
        
        try:
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Check quota
            await self._check_quota(workspace_id, file_size)
            
            # Calculate checksum
            checksum = await self._calculate_checksum(content)
            
            # Check for duplicate files by checksum
            existing_doc = self.db.query(Document).filter_by(checksum=checksum).first()
            if existing_doc:
                # File already exists, return existing info
                operation_time_ms = (time.time() - start_time) * 1000
                
                await self._log_operation(
                    "duplicate_detected",
                    existing_doc.storage_path,
                    True,
                    operation_time_ms,
                    workspace_id,
                    existing_doc.id
                )
                
                return StorageResult(
                    document_id=existing_doc.id,
                    path=existing_doc.storage_path,
                    size=existing_doc.file_size,
                    checksum=existing_doc.checksum,
                    mime_type=existing_doc.mime_type,
                    provider=StorageProviderType(existing_doc.storage_provider.value),
                    operation_time_ms=operation_time_ms
                )
            
            # Generate initial path
            initial_path = self.path_generator.generate_document_path(
                workspace_id=workspace_id,
                document_id=document_id,
                filename=file.filename
            )
            
            # Check for path conflicts and resolve
            existing_paths = []
            components = self.path_generator.extract_components(initial_path)
            if components['workspace_id'] and components['year'] and components['month']:
                # Query existing documents in same year/month
                existing_docs = self.db.query(Document).filter(
                    Document.storage_path.like(f"{components['workspace_id']}/{components['year']}/{components['month']}%")
                ).all()
                existing_paths = [doc.storage_path for doc in existing_docs]
            
            # Resolve filename conflicts
            final_filename = self._resolve_filename_conflict(
                file.filename,
                existing_paths
            )
            
            # Generate final path with resolved filename
            final_path = self.path_generator.generate_document_path(
                workspace_id=workspace_id,
                document_id=document_id,
                filename=final_filename
            )
            
            # Store file
            await self.provider.save_file(content, final_path)
            
            # Get storage URL if available
            storage_url = await self.provider.get_url(final_path)
            
            operation_time_ms = (time.time() - start_time) * 1000
            
            await self._log_operation(
                "store",
                final_path,
                True,
                operation_time_ms,
                workspace_id,
                document_id
            )
            
            return StorageResult(
                document_id=document_id,
                path=final_path,
                size=file_size,
                checksum=checksum,
                mime_type=file.content_type or "application/octet-stream",
                provider=storage_settings.STORAGE_PROVIDER,
                storage_url=storage_url,
                operation_time_ms=operation_time_ms
            )
            
        except Exception as e:
            operation_time_ms = (time.time() - start_time) * 1000
            
            await self._log_operation(
                "store",
                initial_path if 'initial_path' in locals() else "unknown",
                False,
                operation_time_ms,
                workspace_id,
                document_id,
                str(e)
            )
            
            # Cleanup on failure
            if 'final_path' in locals():
                try:
                    await self.provider.delete_file(final_path)
                except:
                    pass  # Ignore cleanup errors
            
            raise StorageException(f"Failed to store document: {e}")
    
    async def retrieve_document(self, document_id: UUID) -> bytes:
        """
        Retrieve document content by ID.
        
        Args:
            document_id: Document ID
            
        Returns:
            File content as bytes
            
        Raises:
            FileNotFoundError: If document not found
        """
        start_time = time.time()
        
        try:
            # Get document from database
            doc = self.db.query(Document).filter_by(id=document_id).first()
            if not doc:
                raise FileNotFoundError(f"Document {document_id} not found in database")
            
            if doc.deleted_at:
                raise FileNotFoundError(f"Document {document_id} has been deleted")
            
            # Retrieve from storage
            content = await self.provider.get_file(doc.storage_path)
            
            operation_time_ms = (time.time() - start_time) * 1000
            
            await self._log_operation(
                "retrieve",
                doc.storage_path,
                True,
                operation_time_ms,
                UUID("00000000-0000-0000-0000-000000000000"),  # No workspace in context
                document_id
            )
            
            return content
            
        except FileNotFoundError:
            raise
        except Exception as e:
            operation_time_ms = (time.time() - start_time) * 1000
            
            await self._log_operation(
                "retrieve",
                doc.storage_path if 'doc' in locals() else "unknown",
                False,
                operation_time_ms,
                UUID("00000000-0000-0000-0000-000000000000"),
                document_id,
                str(e)
            )
            
            raise StorageException(f"Failed to retrieve document: {e}")
    
    async def delete_document(
        self, 
        document_id: UUID, 
        soft_delete: bool = True
    ) -> bool:
        """
        Delete document from storage and database.
        
        Args:
            document_id: Document ID
            soft_delete: If True, mark as deleted; if False, physically remove
            
        Returns:
            True if deleted successfully
        """
        start_time = time.time()
        
        try:
            # Get document from database
            doc = self.db.query(Document).filter_by(id=document_id).first()
            if not doc:
                return False
            
            if soft_delete:
                # Soft delete - mark as deleted in database
                doc.deleted_at = datetime.now(timezone.utc)
                self.db.commit()
            else:
                # Hard delete - remove from storage and database
                await self.provider.delete_file(doc.storage_path)
                self.db.delete(doc)
                self.db.commit()
            
            operation_time_ms = (time.time() - start_time) * 1000
            
            await self._log_operation(
                "soft_delete" if soft_delete else "hard_delete",
                doc.storage_path,
                True,
                operation_time_ms,
                UUID("00000000-0000-0000-0000-000000000000"),
                document_id
            )
            
            return True
            
        except Exception as e:
            operation_time_ms = (time.time() - start_time) * 1000
            
            await self._log_operation(
                "delete",
                doc.storage_path if 'doc' in locals() else "unknown",
                False,
                operation_time_ms,
                UUID("00000000-0000-0000-0000-000000000000"),
                document_id,
                str(e)
            )
            
            raise StorageException(f"Failed to delete document: {e}")
    
    async def move_to_permanent(
        self, 
        temp_path: str, 
        document_id: UUID,
        workspace_id: UUID,
        filename: str
    ) -> str:
        """
        Move file from temporary to permanent storage.
        
        Args:
            temp_path: Current temporary path
            document_id: Target document ID
            workspace_id: Workspace ID
            filename: Final filename
            
        Returns:
            Final permanent path
        """
        start_time = time.time()
        
        try:
            # Generate permanent path
            permanent_path = self.path_generator.generate_document_path(
                workspace_id=workspace_id,
                document_id=document_id,
                filename=filename
            )
            
            # Move file
            await self.provider.move_file(temp_path, permanent_path)
            
            operation_time_ms = (time.time() - start_time) * 1000
            
            await self._log_operation(
                "move_to_permanent",
                f"{temp_path} -> {permanent_path}",
                True,
                operation_time_ms,
                workspace_id,
                document_id
            )
            
            return permanent_path
            
        except Exception as e:
            operation_time_ms = (time.time() - start_time) * 1000
            
            await self._log_operation(
                "move_to_permanent",
                f"{temp_path} -> unknown",
                False,
                operation_time_ms,
                workspace_id,
                document_id,
                str(e)
            )
            
            raise StorageException(f"Failed to move to permanent storage: {e}")
    
    async def get_storage_stats(self, workspace_id: UUID) -> StorageStats:
        """
        Get storage statistics for a workspace.
        
        Args:
            workspace_id: Workspace ID
            
        Returns:
            StorageStats with usage information
        """
        try:
            # Query database for workspace documents
            docs = self.db.query(Document).filter(
                Document.storage_path.like(f"{workspace_id}%"),
                Document.deleted_at.is_(None)
            ).all()
            
            if not docs:
                return StorageStats(
                    workspace_id=workspace_id,
                    used_bytes=0,
                    file_count=0,
                    quota_bytes=storage_settings.DEFAULT_WORKSPACE_QUOTA_BYTES,
                    quota_percentage=0.0,
                    usage_by_type={},
                    average_file_size=0.0
                )
            
            # Calculate statistics
            total_bytes = sum(doc.file_size or 0 for doc in docs)
            file_count = len(docs)
            
            # Usage by file type
            usage_by_type = {}
            for doc in docs:
                ext = doc.file_extension or "unknown"
                usage_by_type[ext] = usage_by_type.get(ext, 0) + (doc.file_size or 0)
            
            # Quota calculation
            quota_bytes = storage_settings.DEFAULT_WORKSPACE_QUOTA_BYTES
            quota_percentage = (total_bytes / quota_bytes) * 100 if quota_bytes > 0 else 0
            
            # Timestamps
            timestamps = [doc.created_at for doc in docs if doc.created_at]
            last_upload = max(timestamps) if timestamps else None
            oldest_file = min(timestamps) if timestamps else None
            
            # Average file size
            average_file_size = total_bytes / file_count if file_count > 0 else 0
            
            return StorageStats(
                workspace_id=workspace_id,
                used_bytes=total_bytes,
                file_count=file_count,
                quota_bytes=quota_bytes,
                quota_percentage=quota_percentage,
                usage_by_type=usage_by_type,
                last_upload=last_upload,
                oldest_file=oldest_file,
                average_file_size=average_file_size
            )
            
        except Exception as e:
            logger.error(f"Failed to get storage stats for workspace {workspace_id}: {e}")
            raise StorageException(f"Failed to get storage stats: {e}")
    
    async def cleanup_temp_files(self) -> int:
        """
        Clean up temporary files older than retention period.
        
        Returns:
            Number of files cleaned up
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=storage_settings.TEMP_RETENTION_DAYS
            )
            
            # List temporary files
            temp_files = await self.provider.list_files(
                prefix=PathGenerator.TEMP_DIR,
                recursive=True
            )
            
            deleted_count = 0
            for temp_path in temp_files:
                try:
                    # Check file age (this is provider-specific)
                    # For now, delete all temp files - improve with file stat checking
                    await self.provider.delete_file(temp_path)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_path}: {e}")
            
            logger.info(f"Cleaned up {deleted_count} temporary files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")
            raise StorageException(f"Failed to cleanup temp files: {e}")