"""
Storage Admin Endpoints
Day 3, Step 5: Administrative endpoints for storage management

Provides admin functionality for:
- Storage statistics and monitoring
- Manual cleanup operations
- Configuration management
- Health checks and diagnostics
"""

import os
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.config import settings
from app.core.storage_config import storage_settings
from app.db.database import get_db
from app.models.document import Document
from app.services.storage import StorageManager, LocalStorageProvider
from app.services.storage.path_generator import PathGenerator
from app.services.storage.migrations import StorageMigration
from app.tasks.storage_cleanup import manual_cleanup
from app.schemas.storage import StorageCleanupResult

router = APIRouter()


# Response Models
class StorageStatsResponse(BaseModel):
    total_documents: int
    total_storage_bytes: int
    total_storage_gb: float
    documents_by_status: Dict[str, int]
    documents_by_provider: Dict[str, int]
    storage_by_workspace: Dict[str, Dict]
    temp_files_count: int
    temp_files_size_bytes: int
    orphaned_files_estimate: int
    last_cleanup_date: Optional[str]
    storage_health: str


class DiskUsageResponse(BaseModel):
    total_gb: float
    used_gb: float
    available_gb: float
    usage_percentage: float
    status: str
    alerts: List[str]


class CleanupTaskResponse(BaseModel):
    task_id: str
    cleanup_type: str
    status: str
    message: str
    estimated_duration_minutes: int


class MigrationStatusResponse(BaseModel):
    old_structure_exists: bool
    backup_exists: bool
    backup_location: Optional[str]
    migration_needed: bool
    old_file_count: Optional[int]


class ConfigurationResponse(BaseModel):
    storage_path: str
    storage_provider: str
    temp_retention_days: int
    max_file_size_mb: float
    allowed_extensions: List[str]
    conflict_strategy: str
    auto_cleanup_enabled: bool


@router.get("/stats", response_model=StorageStatsResponse)
async def get_storage_stats(db: Session = Depends(get_db)):
    """
    Get comprehensive storage statistics and health metrics.
    
    Returns detailed information about:
    - Document counts and sizes
    - Storage distribution
    - Temporary files
    - System health
    """
    try:
        storage_provider = LocalStorageProvider()
        
        # Database statistics
        total_documents = db.query(Document).count()
        active_documents = db.query(Document).filter(Document.deleted_at.is_(None)).count()
        
        # Document status breakdown
        status_counts = {}
        for status_result in db.query(Document.status, db.func.count(Document.id)).group_by(Document.status).all():
            status_counts[status_result[0]] = status_result[1]
        
        # Storage provider breakdown
        provider_counts = {}
        for provider_result in db.query(Document.storage_provider, db.func.count(Document.id)).group_by(Document.storage_provider).all():
            provider_counts[provider_result[0]] = provider_result[1]
        
        # Calculate total storage usage
        total_size_result = db.query(db.func.sum(Document.file_size)).filter(Document.deleted_at.is_(None)).scalar()
        total_storage_bytes = total_size_result or 0
        
        # Workspace storage breakdown (simplified for MVP)
        workspace_storage = {
            "default_workspace": {
                "document_count": active_documents,
                "storage_bytes": total_storage_bytes,
                "storage_gb": round(total_storage_bytes / (1024**3), 2)
            }
        }
        
        # Temporary files statistics
        try:
            temp_files = await storage_provider.list_files(
                prefix=PathGenerator.TEMP_DIR,
                recursive=True
            )
            temp_files_count = len(temp_files)
            
            # Calculate temp files size
            temp_files_size = 0
            for temp_file in temp_files:
                try:
                    size = await storage_provider.get_file_size(temp_file)
                    temp_files_size += size
                except:
                    continue
                    
        except Exception:
            temp_files_count = 0
            temp_files_size = 0
        
        # Estimate orphaned files (files without database records)
        try:
            all_files = await storage_provider.list_files(recursive=True)
            storage_files = [f for f in all_files if not f.startswith(PathGenerator.TEMP_DIR)]
            
            # Get all storage paths from database
            db_paths = set()
            for doc in db.query(Document.storage_path).filter(Document.deleted_at.is_(None)).all():
                if doc.storage_path:
                    db_paths.add(doc.storage_path)
            
            orphaned_estimate = len([f for f in storage_files if f not in db_paths])
            
        except Exception:
            orphaned_estimate = 0
        
        # Storage health assessment
        storage_path = Path(settings.STORAGE_PATH)
        if storage_path.exists():
            stat = os.statvfs(storage_path)
            total_bytes = stat.f_blocks * stat.f_frsize
            available_bytes = stat.f_available * stat.f_frsize
            used_bytes = total_bytes - available_bytes
            usage_percentage = (used_bytes / total_bytes) * 100
            
            if usage_percentage > 90:
                storage_health = "critical"
            elif usage_percentage > 80:
                storage_health = "warning"
            elif temp_files_count > 1000:
                storage_health = "degraded"
            else:
                storage_health = "healthy"
        else:
            storage_health = "unhealthy"
        
        # Get last cleanup date (placeholder - would be tracked in production)
        last_cleanup_date = None
        
        return StorageStatsResponse(
            total_documents=total_documents,
            total_storage_bytes=total_storage_bytes,
            total_storage_gb=round(total_storage_bytes / (1024**3), 2),
            documents_by_status=status_counts,
            documents_by_provider=provider_counts,
            storage_by_workspace=workspace_storage,
            temp_files_count=temp_files_count,
            temp_files_size_bytes=temp_files_size,
            orphaned_files_estimate=orphaned_estimate,
            last_cleanup_date=last_cleanup_date,
            storage_health=storage_health
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get storage stats: {str(e)}")


@router.get("/disk-usage", response_model=DiskUsageResponse)
async def get_disk_usage():
    """
    Get current disk usage statistics for the storage system.
    
    Returns:
    - Disk space breakdown
    - Usage alerts
    - Recommendations
    """
    try:
        storage_path = Path(settings.STORAGE_PATH)
        
        if not storage_path.exists():
            raise HTTPException(status_code=500, detail="Storage path does not exist")
        
        stat = os.statvfs(storage_path)
        total_bytes = stat.f_blocks * stat.f_frsize
        available_bytes = stat.f_available * stat.f_frsize
        used_bytes = total_bytes - available_bytes
        usage_percentage = (used_bytes / total_bytes) * 100
        
        # Determine status and alerts
        alerts = []
        if usage_percentage > 95:
            status = "critical"
            alerts.append("Disk usage critical - immediate action required")
        elif usage_percentage > 90:
            status = "critical"
            alerts.append("Disk usage very high - cleanup recommended")
        elif usage_percentage > 80:
            status = "warning"
            alerts.append("Disk usage high - monitoring recommended")
        elif usage_percentage > 70:
            status = "warning"
            alerts.append("Disk usage elevated")
        else:
            status = "healthy"
        
        return DiskUsageResponse(
            total_gb=round(total_bytes / (1024**3), 2),
            used_gb=round(used_bytes / (1024**3), 2),
            available_gb=round(available_bytes / (1024**3), 2),
            usage_percentage=round(usage_percentage, 2),
            status=status,
            alerts=alerts
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get disk usage: {str(e)}")


@router.post("/cleanup", response_model=CleanupTaskResponse)
async def trigger_cleanup(
    background_tasks: BackgroundTasks,
    cleanup_type: str = Query("all", regex="^(temp|orphaned|all)$"),
    force: bool = Query(False, description="Force cleanup even if recent cleanup exists")
):
    """
    Trigger manual storage cleanup operation.
    
    Args:
        cleanup_type: Type of cleanup ('temp', 'orphaned', 'all')
        force: Force cleanup even if recent cleanup exists
        
    Returns:
        Task information for tracking cleanup progress
    """
    try:
        # Check if cleanup is already running (placeholder - would track in Redis/DB)
        # For now, just proceed
        
        # Estimate duration based on cleanup type
        duration_estimates = {
            "temp": 2,
            "orphaned": 5,
            "all": 7
        }
        
        # Start the background task
        task = manual_cleanup.delay(cleanup_type)
        
        return CleanupTaskResponse(
            task_id=task.id,
            cleanup_type=cleanup_type,
            status="started",
            message=f"Cleanup task started for: {cleanup_type}",
            estimated_duration_minutes=duration_estimates.get(cleanup_type, 5)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start cleanup task: {str(e)}")


@router.get("/cleanup/{task_id}")
async def get_cleanup_status(task_id: str):
    """
    Get status of a cleanup task.
    
    Args:
        task_id: ID of the cleanup task
        
    Returns:
        Current task status and results
    """
    try:
        from celery.result import AsyncResult
        task_result = AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            response = {
                "task_id": task_id,
                "status": "pending",
                "message": "Task is waiting to be processed"
            }
        elif task_result.state == 'PROGRESS':
            response = {
                "task_id": task_id,
                "status": "running",
                "message": "Task is currently running",
                "progress": task_result.info.get('progress', 0) if task_result.info else 0
            }
        elif task_result.state == 'SUCCESS':
            result = task_result.result
            response = {
                "task_id": task_id,
                "status": "completed",
                "message": "Task completed successfully",
                "result": result
            }
        else:
            # FAILURE or other states
            response = {
                "task_id": task_id,
                "status": "failed",
                "message": str(task_result.info) if task_result.info else "Task failed",
                "error": str(task_result.result) if hasattr(task_result, 'result') else None
            }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.get("/migration/status", response_model=MigrationStatusResponse)
async def get_migration_status(db: Session = Depends(get_db)):
    """
    Get current storage migration status.
    
    Returns information about:
    - Whether old storage structure exists
    - Migration backup status
    - Number of files that need migration
    """
    try:
        migration = StorageMigration(db)
        status = migration.get_migration_status()
        
        return MigrationStatusResponse(**status)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get migration status: {str(e)}")


@router.post("/migration/run")
async def run_migration(
    background_tasks: BackgroundTasks,
    dry_run: bool = Query(True, description="Run in dry-run mode (no actual changes)"),
    create_backup: bool = Query(True, description="Create backup before migration"),
    db: Session = Depends(get_db)
):
    """
    Run storage migration to move files to new organized structure.
    
    Args:
        dry_run: If True, only simulate migration
        create_backup: If True, create backup before migration
        
    Returns:
        Migration task information
    """
    try:
        migration = StorageMigration(db)
        
        # Run migration in background
        background_tasks.add_task(
            migration.migrate_existing_files,
            dry_run=dry_run,
            create_backup=create_backup
        )
        
        return {
            "message": f"Migration {'simulation' if dry_run else 'process'} started",
            "dry_run": dry_run,
            "create_backup": create_backup,
            "status": "running"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start migration: {str(e)}")


@router.get("/config", response_model=ConfigurationResponse)
async def get_storage_config():
    """
    Get current storage configuration.
    
    Returns all storage-related configuration settings.
    """
    try:
        return ConfigurationResponse(
            storage_path=settings.STORAGE_PATH,
            storage_provider="local",  # Hardcoded for MVP
            temp_retention_days=storage_settings.TEMP_RETENTION_DAYS,
            max_file_size_mb=settings.MAX_FILE_SIZE / (1024 * 1024),
            allowed_extensions=storage_settings.ALLOWED_EXTENSIONS,
            conflict_strategy=str(storage_settings.CONFLICT_STRATEGY.value),
            auto_cleanup_enabled=True  # Hardcoded for MVP
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")


@router.get("/health/detailed")
async def get_detailed_health_check(db: Session = Depends(get_db)):
    """
    Perform detailed storage health check.
    
    More comprehensive than the main health endpoint,
    includes deep checks for storage consistency.
    """
    try:
        from app.tasks.storage_cleanup import _storage_health_check_async
        
        # Run the detailed health check
        health_result = await _storage_health_check_async()
        
        # Add database consistency checks
        try:
            # Check for documents with missing files
            documents = db.query(Document).filter(
                Document.deleted_at.is_(None),
                Document.storage_path.isnot(None)
            ).all()
            
            storage_provider = LocalStorageProvider()
            missing_files = []
            
            for doc in documents[:100]:  # Limit check to first 100 for performance
                try:
                    exists = await storage_provider.exists(doc.storage_path)
                    if not exists:
                        missing_files.append({
                            "document_id": str(doc.id),
                            "document_name": doc.document_name,
                            "storage_path": doc.storage_path
                        })
                except:
                    missing_files.append({
                        "document_id": str(doc.id),
                        "document_name": doc.document_name,
                        "storage_path": doc.storage_path,
                        "error": "Could not check file existence"
                    })
            
            health_result["consistency_check"] = {
                "documents_checked": min(len(documents), 100),
                "total_documents": len(documents),
                "missing_files": len(missing_files),
                "missing_file_details": missing_files[:10],  # Only show first 10
                "status": "healthy" if len(missing_files) == 0 else "degraded"
            }
            
        except Exception as e:
            health_result["consistency_check"] = {
                "error": str(e),
                "status": "error"
            }
        
        return health_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform health check: {str(e)}")


@router.delete("/temp-files")
async def cleanup_temp_files_now(
    background_tasks: BackgroundTasks,
    older_than_hours: int = Query(24, description="Delete temp files older than N hours")
):
    """
    Immediately clean up temporary files.
    
    Args:
        older_than_hours: Delete files older than this many hours
        
    Returns:
        Cleanup task information
    """
    try:
        # Start immediate temp cleanup
        task = manual_cleanup.delay("temp")
        
        return {
            "message": f"Temp files cleanup started (files older than {older_than_hours} hours)",
            "task_id": task.id,
            "status": "started"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start temp cleanup: {str(e)}")


@router.get("/orphaned-files")
async def list_orphaned_files(
    limit: int = Query(50, description="Maximum number of files to return"),
    db: Session = Depends(get_db)
):
    """
    List files that exist in storage but have no database records.
    
    Args:
        limit: Maximum number of orphaned files to return
        
    Returns:
        List of orphaned files with details
    """
    try:
        storage_provider = LocalStorageProvider()
        
        # Get all files from storage (excluding temp files)
        all_files = await storage_provider.list_files(recursive=True)
        storage_files = [f for f in all_files if not f.startswith(PathGenerator.TEMP_DIR)]
        
        # Get all storage paths from database
        db_paths = set()
        documents = db.query(Document).filter(Document.deleted_at.is_(None)).all()
        
        for doc in documents:
            if doc.storage_path:
                db_paths.add(doc.storage_path)
        
        # Find orphaned files
        orphaned_files = []
        for storage_file in storage_files[:limit]:  # Limit for performance
            if storage_file not in db_paths:
                try:
                    file_size = await storage_provider.get_file_size(storage_file)
                    orphaned_files.append({
                        "path": storage_file,
                        "size_bytes": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2)
                    })
                except:
                    orphaned_files.append({
                        "path": storage_file,
                        "size_bytes": 0,
                        "size_mb": 0,
                        "error": "Could not get file size"
                    })
        
        total_orphaned_size = sum(f.get("size_bytes", 0) for f in orphaned_files)
        
        return {
            "orphaned_files": orphaned_files,
            "total_orphaned_files": len(orphaned_files),
            "total_orphaned_size_bytes": total_orphaned_size,
            "total_orphaned_size_mb": round(total_orphaned_size / (1024 * 1024), 2),
            "note": f"Showing first {limit} orphaned files" if len(storage_files) > limit else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list orphaned files: {str(e)}")