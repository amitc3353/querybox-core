"""
Storage Migrations
Day 3, Step 5: Migrate existing files to new organized structure

Handles migration from old flat storage structure to new organized paths
with backup and rollback capabilities.
"""

import os
import shutil
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
import logging

from app.core.config import settings
from app.core.storage_config import storage_settings
from app.models.document import Document
from app.services.storage.path_generator import PathGenerator
from app.services.storage.local import LocalStorageProvider
from app.services.storage.exceptions import StorageException

logger = logging.getLogger(__name__)


class StorageMigration:
    """
    Handles migration of existing files to new storage structure.
    
    Features:
    - Backup creation before migration
    - Dry-run mode for testing
    - Rollback capability
    - Progress tracking
    - Error recovery
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.path_generator = PathGenerator()
        self.storage_provider = LocalStorageProvider()
        self.backup_dir = Path(settings.STORAGE_PATH) / "_migration_backup"
        
    def _create_backup_info(self, files: List[Dict]) -> str:
        """Create backup metadata file"""
        backup_info = {
            "migration_date": datetime.now(timezone.utc).isoformat(),
            "total_files": len(files),
            "backup_location": str(self.backup_dir),
            "original_storage_path": settings.STORAGE_PATH,
            "files": files
        }
        
        backup_info_file = self.backup_dir / "migration_info.json"
        with open(backup_info_file, 'w') as f:
            json.dump(backup_info, f, indent=2)
        
        return str(backup_info_file)
    
    def _scan_existing_files(self) -> List[Dict]:
        """
        Scan existing storage for files to migrate.
        
        Returns:
            List of file information dictionaries
        """
        old_upload_dir = Path(settings.STORAGE_PATH) / "uploads"
        files_to_migrate = []
        
        if not old_upload_dir.exists():
            logger.info("No existing uploads directory found")
            return files_to_migrate
        
        for file_path in old_upload_dir.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                
                file_info = {
                    "original_path": str(file_path),
                    "relative_path": str(file_path.relative_to(old_upload_dir)),
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "created_time": datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat()
                }
                
                # Try to match with database record
                db_record = self._find_database_record(file_path.name, stat.st_size)
                if db_record:
                    file_info.update({
                        "document_id": str(db_record.id),
                        "original_name": db_record.original_name,
                        "mime_type": db_record.mime_type,
                        "checksum": db_record.checksum
                    })
                else:
                    file_info["document_id"] = None
                    logger.warning(f"No database record found for file: {file_path.name}")
                
                files_to_migrate.append(file_info)
        
        logger.info(f"Found {len(files_to_migrate)} files to migrate")
        return files_to_migrate
    
    def _find_database_record(self, filename: str, file_size: int) -> Optional[Document]:
        """Find matching database record for a file"""
        # Try exact filename match first
        record = self.db.query(Document).filter(
            Document.document_name == filename,
            Document.file_size == file_size
        ).first()
        
        if record:
            return record
        
        # Try original name match
        record = self.db.query(Document).filter(
            Document.original_name.like(f"%{filename.split('_', 1)[-1]}%"),
            Document.file_size == file_size
        ).first()
        
        return record
    
    def _generate_new_path(self, file_info: Dict) -> str:
        """Generate new organized path for a file"""
        workspace_id = UUID("00000000-0000-0000-0000-000000000000")  # Default workspace
        
        if file_info.get("document_id"):
            document_id = UUID(file_info["document_id"])
        else:
            # Generate new document ID for orphaned files
            document_id = uuid4()
            file_info["document_id"] = str(document_id)
        
        # Use file creation time for path organization
        created_time = datetime.fromisoformat(file_info["created_time"].replace("Z", "+00:00"))
        
        original_name = file_info.get("original_name", file_info["filename"])
        
        new_path = self.path_generator.generate_document_path(
            workspace_id=workspace_id,
            document_id=document_id,
            filename=original_name,
            timestamp=created_time
        )
        
        return new_path
    
    async def migrate_existing_files(
        self,
        dry_run: bool = True,
        create_backup: bool = True
    ) -> Dict[str, any]:
        """
        Migrate existing files to new organized structure.
        
        Args:
            dry_run: If True, only simulate migration
            create_backup: If True, create backup before migration
            
        Returns:
            Migration result dictionary
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Step 1: Scan existing files
            logger.info("Scanning existing files for migration...")
            files_to_migrate = self._scan_existing_files()
            
            if not files_to_migrate:
                return {
                    "success": True,
                    "message": "No files found to migrate",
                    "files_processed": 0,
                    "duration_seconds": 0
                }
            
            # Step 2: Create backup if requested
            backup_info_file = None
            if create_backup and not dry_run:
                logger.info("Creating backup before migration...")
                self.backup_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy all existing files to backup
                for file_info in files_to_migrate:
                    original_path = Path(file_info["original_path"])
                    backup_path = self.backup_dir / file_info["relative_path"]
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(original_path, backup_path)
                
                backup_info_file = self._create_backup_info(files_to_migrate)
                logger.info(f"Backup created at: {backup_info_file}")
            
            # Step 3: Process migration
            results = {
                "success": True,
                "dry_run": dry_run,
                "total_files": len(files_to_migrate),
                "migrated_files": 0,
                "failed_files": 0,
                "database_updates": 0,
                "errors": [],
                "backup_location": str(self.backup_dir) if create_backup else None,
                "backup_info_file": backup_info_file,
                "file_details": []
            }
            
            for file_info in files_to_migrate:
                try:
                    # Generate new path
                    new_path = self._generate_new_path(file_info)
                    old_path = Path(file_info["original_path"])
                    
                    file_result = {
                        "original_path": file_info["original_path"],
                        "new_path": new_path,
                        "filename": file_info["filename"],
                        "size": file_info["size"],
                        "document_id": file_info.get("document_id"),
                        "status": "pending"
                    }
                    
                    if dry_run:
                        # Just simulate the migration
                        file_result["status"] = "simulated"
                        logger.info(f"DRY RUN: Would migrate {old_path} -> {new_path}")
                    else:
                        # Perform actual migration
                        await self.storage_provider.move_file(
                            str(old_path.relative_to(settings.STORAGE_PATH)),
                            new_path
                        )
                        
                        # Update database record if exists
                        if file_info.get("document_id"):
                            document = self.db.query(Document).filter_by(
                                id=UUID(file_info["document_id"])
                            ).first()
                            
                            if document:
                                document.storage_path = new_path
                                document.updated_at = datetime.now(timezone.utc)
                                results["database_updates"] += 1
                        
                        file_result["status"] = "migrated"
                        logger.info(f"Migrated: {old_path} -> {new_path}")
                    
                    results["migrated_files"] += 1
                    results["file_details"].append(file_result)
                    
                except Exception as e:
                    error_msg = f"Failed to migrate {file_info['original_path']}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    results["failed_files"] += 1
                    
                    file_result["status"] = "failed"
                    file_result["error"] = str(e)
                    results["file_details"].append(file_result)
            
            # Commit database changes
            if not dry_run and results["database_updates"] > 0:
                self.db.commit()
                logger.info(f"Updated {results['database_updates']} database records")
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            results["duration_seconds"] = duration
            
            if results["failed_files"] > 0:
                results["success"] = False
                results["message"] = f"Migration completed with {results['failed_files']} failures"
            else:
                results["message"] = f"Migration completed successfully. Processed {results['migrated_files']} files"
            
            logger.info(f"Migration completed: {results['message']}")
            return results
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}", exc_info=True)
            raise StorageException(f"Migration failed: {str(e)}")
    
    async def rollback_migration(self, backup_info_file: str) -> Dict[str, any]:
        """
        Rollback migration using backup information.
        
        Args:
            backup_info_file: Path to backup info JSON file
            
        Returns:
            Rollback result dictionary
        """
        try:
            # Load backup information
            with open(backup_info_file, 'r') as f:
                backup_info = json.load(f)
            
            logger.info(f"Starting rollback of {backup_info['total_files']} files")
            
            results = {
                "success": True,
                "total_files": backup_info["total_files"],
                "restored_files": 0,
                "failed_files": 0,
                "errors": []
            }
            
            backup_dir = Path(backup_info["backup_location"])
            
            for file_info in backup_info["files"]:
                try:
                    backup_path = backup_dir / file_info["relative_path"]
                    original_path = Path(file_info["original_path"])
                    
                    # Restore file
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_path, original_path)
                    
                    # Restore database record if needed
                    if file_info.get("document_id"):
                        document = self.db.query(Document).filter_by(
                            id=UUID(file_info["document_id"])
                        ).first()
                        
                        if document:
                            old_relative_path = str(original_path.relative_to(settings.STORAGE_PATH))
                            document.storage_path = old_relative_path
                            document.updated_at = datetime.now(timezone.utc)
                    
                    results["restored_files"] += 1
                    logger.info(f"Restored: {original_path}")
                    
                except Exception as e:
                    error_msg = f"Failed to restore {file_info['original_path']}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    results["failed_files"] += 1
            
            # Commit database changes
            if results["restored_files"] > 0:
                self.db.commit()
            
            if results["failed_files"] > 0:
                results["success"] = False
                results["message"] = f"Rollback completed with {results['failed_files']} failures"
            else:
                results["message"] = f"Rollback completed successfully. Restored {results['restored_files']} files"
            
            logger.info(f"Rollback completed: {results['message']}")
            return results
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}", exc_info=True)
            raise StorageException(f"Rollback failed: {str(e)}")
    
    def get_migration_status(self) -> Dict[str, any]:
        """Get current migration status"""
        old_upload_dir = Path(settings.STORAGE_PATH) / "uploads"
        backup_exists = self.backup_dir.exists()
        
        status = {
            "old_structure_exists": old_upload_dir.exists(),
            "backup_exists": backup_exists,
            "backup_location": str(self.backup_dir) if backup_exists else None,
            "migration_needed": False
        }
        
        if old_upload_dir.exists():
            old_files = list(old_upload_dir.rglob("*"))
            old_file_count = len([f for f in old_files if f.is_file()])
            status.update({
                "old_file_count": old_file_count,
                "migration_needed": old_file_count > 0
            })
        
        return status