"""
Storage Cleanup Tasks
Day 3, Step 5: Celery tasks for storage maintenance

Automated cleanup tasks for:
- Temporary files older than retention period
- Orphaned files without database records
- Storage quota monitoring
"""

import os
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict
from sqlalchemy.orm import sessionmaker
from celery import Celery
from celery.schedules import crontab
import logging

from app.core.config import settings
from app.core.storage_config import storage_settings
from app.db.database import engine
from app.models.document import Document
from app.services.storage import StorageManager, LocalStorageProvider
from app.services.storage.path_generator import PathGenerator
from app.schemas.storage import StorageCleanupResult

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    'storage_cleanup',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Scheduled tasks
celery_app.conf.beat_schedule = {
    'cleanup-temp-files': {
        'task': 'app.tasks.storage_cleanup.cleanup_temp_files',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'cleanup-orphaned-files': {
        'task': 'app.tasks.storage_cleanup.cleanup_orphaned_files',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    'storage-health-check': {
        'task': 'app.tasks.storage_cleanup.storage_health_check',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
}

# Database session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@celery_app.task(bind=True, name='app.tasks.storage_cleanup.cleanup_temp_files')
def cleanup_temp_files(self):
    """
    Clean up temporary files older than retention period.
    
    Removes:
    - Files in _temp directory older than TEMP_RETENTION_DAYS
    - Failed upload remnants
    - Incomplete multipart uploads
    """
    task_id = self.request.id
    logger.info(f"Starting temp files cleanup task: {task_id}")
    
    try:
        # Run async cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_cleanup_temp_files_async())
        loop.close()
        
        logger.info(f"Temp files cleanup completed: {result}")
        return {
            "task_id": task_id,
            "success": True,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Temp files cleanup failed: {str(e)}", exc_info=True)
        return {
            "task_id": task_id,
            "success": False,
            "error": str(e)
        }


@celery_app.task(bind=True, name='app.tasks.storage_cleanup.cleanup_orphaned_files')
def cleanup_orphaned_files(self):
    """
    Clean up orphaned files that have no database records.
    
    Identifies and removes:
    - Files in storage without corresponding database entries
    - Files from deleted documents (soft-deleted more than 30 days ago)
    """
    task_id = self.request.id
    logger.info(f"Starting orphaned files cleanup task: {task_id}")
    
    try:
        # Run async cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_cleanup_orphaned_files_async())
        loop.close()
        
        logger.info(f"Orphaned files cleanup completed: {result}")
        return {
            "task_id": task_id,
            "success": True,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Orphaned files cleanup failed: {str(e)}", exc_info=True)
        return {
            "task_id": task_id,
            "success": False,
            "error": str(e)
        }


@celery_app.task(bind=True, name='app.tasks.storage_cleanup.storage_health_check')
def storage_health_check(self):
    """
    Monitor storage health and send alerts if needed.
    
    Checks:
    - Available disk space
    - Storage quota utilization
    - File system errors
    - Large file accumulation
    """
    task_id = self.request.id
    logger.info(f"Starting storage health check task: {task_id}")
    
    try:
        # Run async health check
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_storage_health_check_async())
        loop.close()
        
        logger.info(f"Storage health check completed: {result}")
        return {
            "task_id": task_id,
            "success": True,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Storage health check failed: {str(e)}", exc_info=True)
        return {
            "task_id": task_id,
            "success": False,
            "error": str(e)
        }


async def _cleanup_temp_files_async() -> Dict:
    """Async implementation of temp files cleanup"""
    start_time = datetime.now(timezone.utc)
    storage_provider = LocalStorageProvider()
    
    try:
        # Calculate cutoff date
        cutoff_date = datetime.now(timezone.utc) - timedelta(
            days=storage_settings.TEMP_RETENTION_DAYS
        )
        
        # List all temp files
        temp_files = await storage_provider.list_files(
            prefix=PathGenerator.TEMP_DIR,
            recursive=True
        )
        
        deleted_count = 0
        failed_count = 0
        bytes_freed = 0
        errors = []
        
        for temp_file_path in temp_files:
            try:
                # Get file stats (this would need enhancement in LocalStorageProvider)
                full_path = storage_provider._get_full_path(temp_file_path)
                
                if full_path.exists():
                    stat = full_path.stat()
                    file_mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                    
                    # Check if file is older than cutoff
                    if file_mtime < cutoff_date:
                        file_size = stat.st_size
                        
                        # Delete the file
                        await storage_provider.delete_file(temp_file_path)
                        
                        deleted_count += 1
                        bytes_freed += file_size
                        
                        logger.debug(f"Deleted temp file: {temp_file_path}")
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"Failed to process temp file {temp_file_path}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return {
            "temp_files_deleted": deleted_count,
            "orphaned_files_deleted": 0,  # Not applicable for this function
            "bytes_freed": bytes_freed,
            "errors": errors,
            "duration_seconds": duration,
            "cutoff_date": cutoff_date.isoformat(),
            "total_temp_files_found": len(temp_files),
            "failed_deletions": failed_count
        }
        
    except Exception as e:
        logger.error(f"Temp files cleanup failed: {str(e)}")
        raise


async def _cleanup_orphaned_files_async() -> Dict:
    """Async implementation of orphaned files cleanup"""
    start_time = datetime.now(timezone.utc)
    storage_provider = LocalStorageProvider()
    
    try:
        # Get database session
        db = SessionLocal()
        
        try:
            # Get all storage paths from database
            db_paths = set()
            documents = db.query(Document).filter(Document.deleted_at.is_(None)).all()
            
            for doc in documents:
                if doc.storage_path:
                    db_paths.add(doc.storage_path)
            
            # Get all files from storage (excluding temp files)
            all_files = await storage_provider.list_files(recursive=True)
            storage_files = [f for f in all_files if not f.startswith(PathGenerator.TEMP_DIR)]
            
            # Find orphaned files
            orphaned_files = []
            for storage_file in storage_files:
                if storage_file not in db_paths:
                    orphaned_files.append(storage_file)
            
            # Clean up orphaned files
            deleted_count = 0
            bytes_freed = 0
            errors = []
            
            for orphaned_file in orphaned_files:
                try:
                    # Get file size before deletion
                    file_size = await storage_provider.get_file_size(orphaned_file)
                    
                    # Delete the orphaned file
                    await storage_provider.delete_file(orphaned_file)
                    
                    deleted_count += 1
                    bytes_freed += file_size
                    
                    logger.info(f"Deleted orphaned file: {orphaned_file}")
                    
                except Exception as e:
                    error_msg = f"Failed to delete orphaned file {orphaned_file}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
            
            # Also clean up soft-deleted documents older than 30 days
            soft_delete_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            old_deleted_docs = db.query(Document).filter(
                Document.deleted_at < soft_delete_cutoff
            ).all()
            
            for doc in old_deleted_docs:
                try:
                    # Delete the file from storage
                    if await storage_provider.exists(doc.storage_path):
                        file_size = await storage_provider.get_file_size(doc.storage_path)
                        await storage_provider.delete_file(doc.storage_path)
                        bytes_freed += file_size
                        deleted_count += 1
                    
                    # Hard delete from database
                    db.delete(doc)
                    
                    logger.info(f"Permanently deleted old document: {doc.id}")
                    
                except Exception as e:
                    error_msg = f"Failed to delete old document {doc.id}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
            
            db.commit()
            
        finally:
            db.close()
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return {
            "temp_files_deleted": 0,  # Not applicable for this function
            "orphaned_files_deleted": deleted_count,
            "bytes_freed": bytes_freed,
            "errors": errors,
            "duration_seconds": duration,
            "total_storage_files": len(storage_files),
            "orphaned_files_found": len(orphaned_files),
            "old_deleted_documents": len(old_deleted_docs) if 'old_deleted_docs' in locals() else 0
        }
        
    except Exception as e:
        logger.error(f"Orphaned files cleanup failed: {str(e)}")
        raise


async def _storage_health_check_async() -> Dict:
    """Async implementation of storage health check"""
    start_time = datetime.now(timezone.utc)
    storage_provider = LocalStorageProvider()
    
    try:
        health_status = {
            "timestamp": start_time.isoformat(),
            "overall_status": "healthy",
            "checks": {},
            "alerts": [],
            "recommendations": []
        }
        
        # Check 1: Disk space
        try:
            storage_path = Path(settings.STORAGE_PATH)
            stat = os.statvfs(storage_path)
            
            total_bytes = stat.f_blocks * stat.f_frsize
            available_bytes = stat.f_available * stat.f_frsize
            used_bytes = total_bytes - available_bytes
            usage_percentage = (used_bytes / total_bytes) * 100
            
            health_status["checks"]["disk_space"] = {
                "status": "healthy",
                "total_gb": round(total_bytes / (1024**3), 2),
                "used_gb": round(used_bytes / (1024**3), 2),
                "available_gb": round(available_bytes / (1024**3), 2),
                "usage_percentage": round(usage_percentage, 2)
            }
            
            # Alert if disk usage is high
            if usage_percentage > 90:
                health_status["overall_status"] = "critical"
                health_status["alerts"].append(f"Disk usage critical: {usage_percentage:.1f}%")
            elif usage_percentage > 80:
                health_status["overall_status"] = "warning"
                health_status["alerts"].append(f"Disk usage high: {usage_percentage:.1f}%")
                
        except Exception as e:
            health_status["checks"]["disk_space"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["overall_status"] = "degraded"
        
        # Check 2: Temp files accumulation
        try:
            temp_files = await storage_provider.list_files(
                prefix=PathGenerator.TEMP_DIR,
                recursive=True
            )
            
            health_status["checks"]["temp_files"] = {
                "status": "healthy",
                "count": len(temp_files)
            }
            
            if len(temp_files) > 1000:
                health_status["alerts"].append(f"High temp file count: {len(temp_files)}")
                health_status["recommendations"].append("Consider running temp file cleanup")
                
        except Exception as e:
            health_status["checks"]["temp_files"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check 3: Storage provider connectivity
        try:
            # Test basic operations
            test_path = "_health_check_test.txt"
            test_content = b"health check test"
            
            await storage_provider.save_file(test_content, test_path)
            retrieved_content = await storage_provider.get_file(test_path)
            await storage_provider.delete_file(test_path)
            
            health_status["checks"]["storage_provider"] = {
                "status": "healthy",
                "test_successful": retrieved_content == test_content
            }
            
        except Exception as e:
            health_status["checks"]["storage_provider"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["overall_status"] = "critical"
        
        # Check 4: Database connectivity
        try:
            db = SessionLocal()
            try:
                doc_count = db.query(Document).count()
                health_status["checks"]["database"] = {
                    "status": "healthy",
                    "document_count": doc_count
                }
            finally:
                db.close()
                
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["overall_status"] = "critical"
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        health_status["duration_seconds"] = duration
        
        # Log alerts
        for alert in health_status["alerts"]:
            logger.warning(f"Storage health alert: {alert}")
        
        return health_status
        
    except Exception as e:
        logger.error(f"Storage health check failed: {str(e)}")
        raise


# Manual cleanup functions for API endpoints
@celery_app.task(bind=True, name='app.tasks.storage_cleanup.manual_cleanup')
def manual_cleanup(self, cleanup_type: str = "all"):
    """
    Manual cleanup task that can be triggered via API.
    
    Args:
        cleanup_type: Type of cleanup ('temp', 'orphaned', 'all')
    """
    task_id = self.request.id
    logger.info(f"Starting manual cleanup task: {task_id}, type: {cleanup_type}")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = {"task_id": task_id, "cleanup_type": cleanup_type}
        
        if cleanup_type in ["temp", "all"]:
            temp_result = loop.run_until_complete(_cleanup_temp_files_async())
            result["temp_cleanup"] = temp_result
        
        if cleanup_type in ["orphaned", "all"]:
            orphaned_result = loop.run_until_complete(_cleanup_orphaned_files_async())
            result["orphaned_cleanup"] = orphaned_result
        
        loop.close()
        
        logger.info(f"Manual cleanup completed: {result}")
        return {
            "success": True,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Manual cleanup failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }