"""
Storage Metrics for Prometheus
Day 3, Step 5: Prometheus metrics collection for storage monitoring

Provides metrics for:
- Storage usage and capacity
- File operations performance
- Document processing statistics
- Error rates and health status
"""

import time
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from contextlib import asynccontextmanager

try:
    from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Create mock classes for when prometheus_client is not available
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    
    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def time(self): return asynccontextmanager(lambda: (yield))()
        def labels(self, *args, **kwargs): return self
    
    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    
    class Info:
        def __init__(self, *args, **kwargs): pass
        def info(self, *args, **kwargs): pass

from app.core.config import settings
from app.core.storage_config import storage_settings


# Storage Operation Metrics
storage_operations_total = Counter(
    'storage_operations_total',
    'Total number of storage operations',
    ['operation_type', 'provider', 'status']
)

storage_operation_duration = Histogram(
    'storage_operation_duration_seconds',
    'Duration of storage operations in seconds',
    ['operation_type', 'provider'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

storage_operation_size = Histogram(
    'storage_operation_size_bytes',
    'Size of files in storage operations',
    ['operation_type', 'provider'],
    buckets=[1024, 10240, 102400, 1048576, 10485760, 104857600, 1073741824]  # 1KB to 1GB
)

# File Upload Metrics
file_uploads_total = Counter(
    'file_uploads_total',
    'Total number of file uploads',
    ['status', 'file_type', 'size_category']
)

file_upload_duration = Histogram(
    'file_upload_duration_seconds',
    'Duration of file uploads in seconds',
    ['file_type', 'size_category'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 300.0]
)

file_upload_size = Histogram(
    'file_upload_size_bytes',
    'Size of uploaded files in bytes',
    ['file_type'],
    buckets=[1024, 10240, 102400, 1048576, 10485760, 104857600, 1073741824]
)

# Storage Capacity Metrics
storage_capacity_total = Gauge(
    'storage_capacity_total_bytes',
    'Total storage capacity in bytes'
)

storage_capacity_used = Gauge(
    'storage_capacity_used_bytes',
    'Used storage capacity in bytes'
)

storage_capacity_available = Gauge(
    'storage_capacity_available_bytes',
    'Available storage capacity in bytes'
)

storage_usage_percentage = Gauge(
    'storage_usage_percentage',
    'Storage usage as percentage of total capacity'
)

# Document Metrics
documents_total = Gauge(
    'documents_total',
    'Total number of documents',
    ['status', 'provider']
)

documents_size_total = Gauge(
    'documents_size_total_bytes',
    'Total size of all documents in bytes',
    ['status', 'provider']
)

# Temporary Files Metrics
temp_files_count = Gauge(
    'temp_files_count',
    'Number of temporary files'
)

temp_files_size = Gauge(
    'temp_files_size_bytes',
    'Total size of temporary files in bytes'
)

temp_files_age_max = Gauge(
    'temp_files_age_max_hours',
    'Age of oldest temporary file in hours'
)

# Cleanup Metrics
cleanup_operations_total = Counter(
    'cleanup_operations_total',
    'Total number of cleanup operations',
    ['cleanup_type', 'status']
)

cleanup_files_removed = Counter(
    'cleanup_files_removed_total',
    'Total number of files removed by cleanup',
    ['cleanup_type']
)

cleanup_bytes_freed = Counter(
    'cleanup_bytes_freed_total',
    'Total bytes freed by cleanup operations',
    ['cleanup_type']
)

cleanup_duration = Histogram(
    'cleanup_duration_seconds',
    'Duration of cleanup operations in seconds',
    ['cleanup_type'],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0]
)

# Error Metrics
storage_errors_total = Counter(
    'storage_errors_total',
    'Total number of storage errors',
    ['operation_type', 'error_type', 'provider']
)

# Health Check Metrics
storage_health_status = Gauge(
    'storage_health_status',
    'Storage health status (1=healthy, 0.5=degraded, 0=unhealthy)'
)

storage_health_check_duration = Histogram(
    'storage_health_check_duration_seconds',
    'Duration of storage health checks in seconds',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

# System Information
storage_info = Info(
    'storage_info',
    'Storage system information'
)

# Initialize system info
if PROMETHEUS_AVAILABLE:
    storage_info.info({
        'storage_path': settings.STORAGE_PATH,
        'storage_provider': 'local',
        'max_file_size_mb': str(settings.MAX_FILE_SIZE / (1024 * 1024)),
        'temp_retention_days': str(storage_settings.TEMP_RETENTION_DAYS),
        'conflict_strategy': str(storage_settings.CONFLICT_STRATEGY.value)
    })


class StorageMetricsCollector:
    """
    Collector class for storage metrics.
    
    Provides methods to update metrics and collect system statistics.
    """
    
    def __init__(self):
        self.enabled = PROMETHEUS_AVAILABLE
        
    def record_storage_operation(
        self,
        operation_type: str,
        provider: str = "local",
        status: str = "success",
        duration: Optional[float] = None,
        size_bytes: Optional[int] = None
    ):
        """Record a storage operation"""
        if not self.enabled:
            return
            
        storage_operations_total.labels(
            operation_type=operation_type,
            provider=provider,
            status=status
        ).inc()
        
        if duration is not None:
            storage_operation_duration.labels(
                operation_type=operation_type,
                provider=provider
            ).observe(duration)
        
        if size_bytes is not None:
            storage_operation_size.labels(
                operation_type=operation_type,
                provider=provider
            ).observe(size_bytes)
    
    def record_file_upload(
        self,
        status: str,
        file_type: str,
        size_bytes: int,
        duration: Optional[float] = None
    ):
        """Record a file upload"""
        if not self.enabled:
            return
            
        # Categorize file size
        if size_bytes < 1024 * 1024:  # < 1MB
            size_category = "small"
        elif size_bytes < 10 * 1024 * 1024:  # < 10MB
            size_category = "medium"
        elif size_bytes < 100 * 1024 * 1024:  # < 100MB
            size_category = "large"
        else:
            size_category = "very_large"
        
        file_uploads_total.labels(
            status=status,
            file_type=file_type,
            size_category=size_category
        ).inc()
        
        file_upload_size.labels(file_type=file_type).observe(size_bytes)
        
        if duration is not None:
            file_upload_duration.labels(
                file_type=file_type,
                size_category=size_category
            ).observe(duration)
    
    def record_error(
        self,
        operation_type: str,
        error_type: str,
        provider: str = "local"
    ):
        """Record a storage error"""
        if not self.enabled:
            return
            
        storage_errors_total.labels(
            operation_type=operation_type,
            error_type=error_type,
            provider=provider
        ).inc()
    
    def record_cleanup_operation(
        self,
        cleanup_type: str,
        status: str,
        files_removed: int = 0,
        bytes_freed: int = 0,
        duration: Optional[float] = None
    ):
        """Record a cleanup operation"""
        if not self.enabled:
            return
            
        cleanup_operations_total.labels(
            cleanup_type=cleanup_type,
            status=status
        ).inc()
        
        if files_removed > 0:
            cleanup_files_removed.labels(cleanup_type=cleanup_type).inc(files_removed)
        
        if bytes_freed > 0:
            cleanup_bytes_freed.labels(cleanup_type=cleanup_type).inc(bytes_freed)
        
        if duration is not None:
            cleanup_duration.labels(cleanup_type=cleanup_type).observe(duration)
    
    async def update_storage_capacity_metrics(self):
        """Update storage capacity metrics"""
        if not self.enabled:
            return
            
        try:
            storage_path = Path(settings.STORAGE_PATH)
            if storage_path.exists():
                stat = os.statvfs(storage_path)
                total_bytes = stat.f_blocks * stat.f_frsize
                available_bytes = stat.f_available * stat.f_frsize
                used_bytes = total_bytes - available_bytes
                usage_percentage = (used_bytes / total_bytes) * 100
                
                storage_capacity_total.set(total_bytes)
                storage_capacity_used.set(used_bytes)
                storage_capacity_available.set(available_bytes)
                storage_usage_percentage.set(usage_percentage)
        except Exception:
            pass  # Silently handle errors in metrics collection
    
    async def update_document_metrics(self, db_session):
        """Update document-related metrics"""
        if not self.enabled:
            return
            
        try:
            from app.models.document import Document, DocumentStatusEnum, StorageProviderEnum
            
            # Reset gauges
            documents_total._value.clear()
            documents_size_total._value.clear()
            
            # Count documents by status and provider
            for status in DocumentStatusEnum:
                for provider in StorageProviderEnum:
                    count = db_session.query(Document).filter(
                        Document.status == status,
                        Document.storage_provider == provider,
                        Document.deleted_at.is_(None)
                    ).count()
                    
                    if count > 0:
                        documents_total.labels(
                            status=status.value,
                            provider=provider.value
                        ).set(count)
                        
                        # Calculate total size
                        total_size = db_session.query(
                            db_session.func.sum(Document.file_size)
                        ).filter(
                            Document.status == status,
                            Document.storage_provider == provider,
                            Document.deleted_at.is_(None)
                        ).scalar() or 0
                        
                        documents_size_total.labels(
                            status=status.value,
                            provider=provider.value
                        ).set(total_size)
                        
        except Exception:
            pass  # Silently handle errors in metrics collection
    
    async def update_temp_file_metrics(self):
        """Update temporary file metrics"""
        if not self.enabled:
            return
            
        try:
            from app.services.storage.local import LocalStorageProvider
            from app.services.storage.path_generator import PathGenerator
            
            provider = LocalStorageProvider()
            temp_files = await provider.list_files(
                prefix=PathGenerator.TEMP_DIR,
                recursive=True
            )
            
            temp_files_count.set(len(temp_files))
            
            total_size = 0
            oldest_file_age = 0
            current_time = datetime.now(timezone.utc)
            
            for temp_file in temp_files:
                try:
                    size = await provider.get_file_size(temp_file)
                    total_size += size
                    
                    # Calculate file age (simplified - would need enhanced provider)
                    # For now, just estimate based on path structure
                    
                except Exception:
                    continue
            
            temp_files_size.set(total_size)
            temp_files_age_max.set(oldest_file_age)
            
        except Exception:
            pass  # Silently handle errors in metrics collection
    
    def update_health_status(self, health_status: str, check_duration: float):
        """Update health status metrics"""
        if not self.enabled:
            return
            
        # Convert health status to numeric value
        status_values = {
            "healthy": 1.0,
            "warning": 0.8,
            "degraded": 0.5,
            "critical": 0.2,
            "unhealthy": 0.0
        }
        
        storage_health_status.set(status_values.get(health_status, 0.0))
        storage_health_check_duration.observe(check_duration)
    
    @asynccontextmanager
    async def time_operation(self, operation_type: str, provider: str = "local"):
        """Context manager to time storage operations"""
        start_time = time.time()
        try:
            yield
            duration = time.time() - start_time
            self.record_storage_operation(
                operation_type=operation_type,
                provider=provider,
                status="success",
                duration=duration
            )
        except Exception as e:
            duration = time.time() - start_time
            self.record_storage_operation(
                operation_type=operation_type,
                provider=provider,
                status="error",
                duration=duration
            )
            self.record_error(
                operation_type=operation_type,
                error_type=type(e).__name__,
                provider=provider
            )
            raise
    
    async def collect_all_metrics(self, db_session=None):
        """Collect all storage metrics"""
        if not self.enabled:
            return
            
        await self.update_storage_capacity_metrics()
        await self.update_temp_file_metrics()
        
        if db_session:
            await self.update_document_metrics(db_session)


# Global metrics collector instance
metrics_collector = StorageMetricsCollector()


def get_metrics():
    """Get Prometheus metrics in text format"""
    if not PROMETHEUS_AVAILABLE:
        return "# Prometheus client not available\n"
    
    return generate_latest()


def get_metrics_content_type():
    """Get the content type for Prometheus metrics"""
    if not PROMETHEUS_AVAILABLE:
        return "text/plain"
    
    return CONTENT_TYPE_LATEST


# Convenience functions for common operations
async def time_file_upload(file_type: str, size_bytes: int):
    """Context manager for timing file uploads"""
    return metrics_collector.time_operation("upload")


async def record_successful_upload(file_type: str, size_bytes: int, duration: float):
    """Record a successful file upload"""
    metrics_collector.record_file_upload("success", file_type, size_bytes, duration)


async def record_failed_upload(file_type: str, size_bytes: int, error_type: str):
    """Record a failed file upload"""
    metrics_collector.record_file_upload("error", file_type, size_bytes)
    metrics_collector.record_error("upload", error_type)


async def record_cleanup_success(cleanup_type: str, files_removed: int, bytes_freed: int, duration: float):
    """Record a successful cleanup operation"""
    metrics_collector.record_cleanup_operation(
        cleanup_type=cleanup_type,
        status="success",
        files_removed=files_removed,
        bytes_freed=bytes_freed,
        duration=duration
    )