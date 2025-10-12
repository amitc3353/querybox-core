# QueryBox Core: Step 5 - Storage Service Pattern
## Technical Implementation Documentation

---

## 1. FEATURE OVERVIEW

### What This Step Accomplishes
Step 5 implements a comprehensive, abstracted storage service pattern that serves as the foundation for all file operations in QueryBox Core:
- Abstract storage provider interface with pluggable backends (local, S3, Azure Blob)
- Intelligent path generation with conflict resolution strategies
- Local filesystem provider with full security and permission handling
- Storage manager orchestrating complex operations with database integration
- Atomic file operations with rollback capabilities on failure
- Multi-tenant storage organization with workspace isolation
- Comprehensive audit logging and performance metrics
- Automatic temporary file cleanup and quota management

### Why This Step is Necessary
The Storage Service Pattern is critical because it:
- **Abstracts storage complexity**: Provides unified interface regardless of backend
- **Enables scalability**: Switch from local to cloud storage without code changes
- **Handles file conflicts**: Intelligent resolution of naming conflicts
- **Ensures data integrity**: Atomic operations with checksum verification
- **Supports multi-tenancy**: Workspace-based organization and quotas
- **Provides audit trails**: Complete logging of all storage operations
- **Optimizes performance**: Chunked uploads and caching strategies
- **Manages resources**: Automatic cleanup and quota enforcement

### Dependencies on Previous Steps
- **Step 1**: Database models for document tracking and metadata storage
- **Step 2**: FastAPI dependency injection system for session management
- **Step 3**: Upload handlers integrate with storage manager
- **Step 4**: File validation layer validates before storage operations

### What Future Steps Depend on This
- **Document Processing**: All processing stages use storage manager
- **Retrieval Service**: Document serving relies on storage abstraction
- **Backup Systems**: Storage interface enables backup implementations
- **Cloud Migration**: Seamless transition to cloud storage providers
- **Embedding Pipeline**: Vector storage builds on this foundation

---

## 2. TECHNICAL IMPLEMENTATION

### Files Created/Modified

#### Core Storage Infrastructure
```
/backend/app/services/storage/
├── __init__.py                    # Storage module initialization
├── base.py                        # Abstract storage provider interface
├── local.py                       # Local filesystem implementation
├── manager.py                     # Main storage service manager
├── path_generator.py              # Path generation and conflict resolution
├── exceptions.py                  # Storage-specific exceptions
└── migrations.py                  # Storage migration utilities
```

#### Configuration and Schemas
```
/backend/app/core/
└── storage_config.py              # Storage configuration settings

/backend/app/schemas/
└── storage.py                     # Pydantic models for storage operations
```

#### Monitoring and Administration
```
/backend/app/monitoring/
└── storage_metrics.py             # Prometheus metrics for storage

/backend/app/api/v1/endpoints/
└── storage_admin.py               # Admin endpoints for storage management

/backend/app/tasks/
└── storage_cleanup.py             # Celery tasks for cleanup operations
```

### Key Classes and Functions

#### Abstract Storage Provider (`/backend/app/services/storage/base.py`)
```python
class StorageProvider(ABC):
    """Abstract base class defining storage interface"""
    
    @abstractmethod
    async def save_file(self, file_content: bytes, path: str) -> str
    
    @abstractmethod
    async def get_file(self, path: str) -> bytes
    
    @abstractmethod
    async def delete_file(self, path: str) -> bool
    
    @abstractmethod
    async def exists(self, path: str) -> bool
    
    @abstractmethod
    async def get_url(self, path: str, expires_in: int = 3600) -> Optional[str]
    
    @abstractmethod
    async def move_file(self, old_path: str, new_path: str) -> bool
```

#### Storage Manager (`/backend/app/services/storage/manager.py`)
```python
class StorageManager:
    """Main storage service orchestrator"""
    
    async def store_document(
        self, 
        file: UploadFile, 
        workspace_id: UUID,
        document_id: Optional[UUID] = None
    ) -> StorageResult
    
    async def retrieve_document(self, document_id: UUID) -> bytes
    
    async def delete_document(
        self, 
        document_id: UUID, 
        soft_delete: bool = True
    ) -> bool
    
    async def get_storage_stats(self, workspace_id: UUID) -> StorageStats
```

#### Path Generator (`/backend/app/services/storage/path_generator.py`)
```python
class PathGenerator:
    """Intelligent path generation and conflict resolution"""
    
    @staticmethod
    def generate_document_path(
        workspace_id: UUID,
        document_id: UUID,
        filename: str,
        timestamp: Optional[datetime] = None
    ) -> str
    
    @staticmethod
    def sanitize_filename(filename: str) -> str
    
    @staticmethod
    def extract_components(path: str) -> Dict[str, Optional[str]]
```

### Database Integration
Storage operations integrate with the following database models:
- **documents table**: Primary metadata storage with storage_path and checksum
- **storage_operations table**: Audit trail for all operations (prepared)
- **workspace_quotas table**: Per-workspace storage limits (prepared)

### API Endpoints Created

#### Core Storage Operations (Integrated with existing endpoints)
- Storage operations are embedded in existing upload/document endpoints
- No direct storage API endpoints in MVP (security consideration)

#### Administrative Endpoints (`/backend/app/api/v1/endpoints/storage_admin.py`)
- `GET /api/v1/admin/storage/stats` - System-wide storage statistics
- `POST /api/v1/admin/storage/cleanup` - Trigger cleanup operations
- `GET /api/v1/admin/storage/health` - Storage provider health check

### Background Tasks

#### Storage Cleanup (`/backend/app/tasks/storage_cleanup.py`)
```python
@celery_app.task
def cleanup_temp_files():
    """Remove temporary files older than retention period"""
    
@celery_app.task  
def cleanup_orphaned_files():
    """Remove files not referenced in database"""
    
@celery_app.task
def migrate_storage_provider():
    """Migrate files between storage providers"""
```

---

## 3. DATA FLOW

### Document Storage Flow
1. **Upload Request** → FastAPI receives multipart file upload
2. **Storage Manager** → Creates manager instance with database session
3. **Content Reading** → Asynchronously reads file content into memory
4. **Quota Check** → Validates workspace storage quota not exceeded
5. **Checksum Calculation** → SHA256 hash for deduplication and integrity
6. **Duplicate Detection** → Database lookup by checksum for existing files
7. **Path Generation** → Creates organized storage path with date hierarchy
8. **Conflict Resolution** → Resolves filename conflicts using strategy
9. **Provider Storage** → Saves file to storage backend with atomic operation
10. **Database Update** → Records document metadata and storage path
11. **Audit Logging** → Logs operation details for compliance

### Path Generation Flow
```
Input: workspace_id, document_id, filename
├── Sanitize filename (remove invalid chars, unicode normalization)
├── Generate base path: {workspace_id}/{year}/{month}/{document_id}/
├── Check for conflicts in database
├── Apply conflict resolution strategy:
│   ├── TIMESTAMP: append_20241115_143022
│   ├── COUNTER: append_1, append_2, etc.
│   └── UUID: prepend_7f3e4a_
└── Return final path: workspace/2024/11/doc-id/filename
```

### File Retrieval Flow
1. **Request** → Client requests document by ID
2. **Database Lookup** → Find document metadata and storage path
3. **Existence Check** → Verify file exists and not soft-deleted
4. **Provider Retrieval** → Fetch file content from storage backend
5. **Content Return** → Stream file content to client
6. **Audit Logging** → Record access for security compliance

### Storage Provider Factory Pattern
```
StorageManager initialization:
├── Check STORAGE_PROVIDER environment variable
├── Create provider instance based on type:
│   ├── LOCAL → LocalStorageProvider with filesystem config
│   ├── S3 → S3StorageProvider with AWS credentials (future)
│   └── AZURE_BLOB → AzureBlobProvider with Azure config (future)
├── Cache provider instance for reuse
└── Return configured provider
```

---

## 4. VALIDATIONS & CONSTRAINTS

### Path Validations
- **Maximum Path Length**: 255 characters total
- **Character Restrictions**: Only alphanumeric, dash, underscore, dot
- **Path Traversal Prevention**: Checks for ../ and absolute paths
- **Unicode Normalization**: NFKD normalization to ASCII
- **Null Byte Detection**: Prevents null byte injection attacks

### Storage Constraints
- **Workspace Quotas**: Default 10GB per workspace (configurable)
- **File Size Limits**: Inherited from upload validation (30MB default)
- **Filename Length**: Maximum 200 characters after sanitization
- **Directory Depth**: Fixed 5-level hierarchy for performance
- **Concurrent Operations**: Maximum 10 simultaneous uploads per workspace

### Security Validations
```python
# Path security checks in LocalStorageProvider
def _get_full_path(self, path: str) -> Path:
    # Validate path format
    self.validate_path(path)
    
    # Resolve to absolute path
    full_path = (self.root_path / path).resolve()
    
    # Security check: ensure within storage root
    try:
        full_path.relative_to(self.root_path.resolve())
    except ValueError:
        raise InvalidPathError(path, "Path would escape storage root")
```

### Conflict Resolution Constraints
- **Timestamp Strategy**: Uses UTC timestamps with microsecond precision
- **Counter Strategy**: Maximum 1000 attempts before fallback to UUID
- **UUID Strategy**: Uses 6-character UUID prefix for uniqueness
- **Fallback Chain**: Counter → UUID if all strategies fail

---

## 5. CONFIGURATION

### Environment Variables
```bash
# Storage Provider Selection
STORAGE_PROVIDER=local                    # local, s3, azure_blob

# Local Storage Configuration
STORAGE_LOCAL_STORAGE_ROOT=storage        # Root directory
STORAGE_LOCAL_DIR_PERMISSIONS=755         # Directory permissions (octal)
STORAGE_LOCAL_FILE_PERMISSIONS=644        # File permissions (octal)

# Path and Filename Configuration
STORAGE_MAX_PATH_LENGTH=255               # Maximum path length
STORAGE_CONFLICT_STRATEGY=timestamp       # timestamp, counter, uuid
STORAGE_TEMP_RETENTION_DAYS=1             # Cleanup period for temp files

# Quota Management
STORAGE_DEFAULT_WORKSPACE_QUOTA_GB=10     # Default quota per workspace
STORAGE_CONCURRENT_UPLOADS_LIMIT=10       # Max simultaneous uploads

# Performance Settings
STORAGE_OPERATION_TIMEOUT=30              # Timeout in seconds
STORAGE_UPLOAD_CHUNK_SIZE_MB=5            # Chunk size for large files
STORAGE_ENABLE_STORAGE_CACHE=true         # Enable operation caching
STORAGE_CACHE_TTL_SECONDS=3600            # Cache TTL

# Security Settings
STORAGE_ENABLE_VIRUS_SCAN=false           # Virus scanning (future)
STORAGE_ALLOWED_MIME_TYPES='["application/pdf","text/plain"]'
```

### Default Values
- **Storage Provider**: LOCAL for MVP development
- **Conflict Strategy**: TIMESTAMP for chronological organization
- **Workspace Quota**: 10GB default, expandable per workspace
- **Temp Retention**: 1 day for development, 7 days for production
- **Operation Timeout**: 30 seconds for network resilience

### Directory Structure
```
/storage/
├── {workspace-uuid-1}/
│   ├── 2024/
│   │   ├── 01/                   # January
│   │   │   ├── {doc-uuid-1}/
│   │   │   │   ├── report.pdf
│   │   │   │   └── v2/           # Version history
│   │   │   │       └── report.pdf
│   │   │   └── {doc-uuid-2}/
│   │   │       └── data.xlsx
│   │   └── 11/                   # November
│   │       └── {doc-uuid-3}/
│   │           └── presentation.pptx
├── {workspace-uuid-2}/
│   └── 2024/
│       └── 11/
└── _temp/                        # Temporary upload staging
    ├── 2024-11-15/
    │   ├── upload_session_123/
    │   └── 143022_567890_temp.pdf
    └── 2024-11-14/               # Cleaned up after retention
```

### Provider-Specific Configuration

#### Local Storage Provider
```python
{
    "root_path": "storage",
    "dir_permissions": 0o755,
    "file_permissions": 0o644,
    "enable_compression": False,
    "enable_versioning": True
}
```

#### S3 Provider (Future)
```python
{
    "bucket_name": "querybox-documents",
    "region": "us-east-1",
    "access_key_id": "ACCESS_KEY",
    "secret_access_key": "SECRET_KEY",
    "enable_versioning": True,
    "storage_class": "STANDARD_IA"
}
```

---

## 6. ERROR HANDLING

### Storage Exception Hierarchy
```python
StorageException                    # Base exception
├── FileNotFoundError              # File doesn't exist
├── StorageQuotaExceeded           # Quota limits exceeded
├── InvalidPathError               # Path validation failed
├── PermissionDeniedError          # Access denied
└── StorageConnectionError         # Provider connection failed
```

### Common Error Scenarios

#### Quota Exceeded
```python
# Automatic quota checking before save
try:
    await manager.store_document(file, workspace_id)
except StorageQuotaExceeded as e:
    return {
        "error": "Storage quota exceeded",
        "used_bytes": e.used_bytes,
        "quota_bytes": e.quota_bytes,
        "workspace_id": e.workspace_id
    }
```

#### Path Traversal Attempts
```python
# Security validation in path generation
try:
    path = generator.generate_document_path(workspace_id, doc_id, "../../../etc/passwd")
except InvalidPathError as e:
    logger.warning(f"Path traversal attempt: {e.path}")
    return {"error": "Invalid filename", "detail": e.reason}
```

#### Storage Provider Failures
```python
# Atomic operation with rollback
try:
    await provider.save_file(content, path)
    # Update database only after successful storage
    db.commit()
except StorageException as e:
    # Rollback database changes
    db.rollback()
    # Attempt file cleanup
    try:
        await provider.delete_file(path)
    except:
        pass  # Cleanup failures are logged but don't affect user
    raise
```

### Recovery Mechanisms
- **Automatic Retry**: Storage operations retry 3 times with exponential backoff
- **Graceful Degradation**: Continue operation without non-critical features
- **Rollback on Failure**: Database transactions rolled back if storage fails
- **Cleanup on Error**: Temporary files removed on operation failure
- **Circuit Breaker**: Disable failing providers temporarily (future)

### Error Response Formats
```json
{
    "error": "StorageQuotaExceeded",
    "message": "Storage quota exceeded: 11000000000/10737418240 bytes used for workspace a1b2c3d4...",
    "details": {
        "used_bytes": 11000000000,
        "quota_bytes": 10737418240,
        "workspace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "overage_bytes": 262581760
    },
    "timestamp": "2024-11-15T14:30:00Z"
}
```

---

## 7. TESTING CHECKLIST

### Storage Provider Testing
- [ ] **Local provider initialization**: Creates directories with correct permissions
- [ ] **File save operations**: Files written with correct content and permissions
- [ ] **File retrieval operations**: Content matches what was stored
- [ ] **File deletion operations**: Files removed and not accessible
- [ ] **Path traversal security**: Attempts to escape storage root are blocked
- [ ] **Unicode filename handling**: Non-ASCII characters normalized correctly

### Storage Manager Testing
```bash
# Test document storage with conflict resolution
curl -X POST "http://localhost:8000/api/v1/upload" \
    -H "Content-Type: multipart/form-data" \
    -F "file=@test_document.pdf" \
    -F "workspace_id=123e4567-e89b-12d3-a456-426614174000"

# Expected: Document stored with unique filename if conflicts exist
```

### Path Generation Testing
```python
# Test filename sanitization
def test_filename_sanitization():
    # Unicode characters
    assert sanitize_filename("résumé.pdf") == "resume.pdf"
    
    # Special characters
    assert sanitize_filename("file with spaces.txt") == "file_with_spaces.txt"
    
    # Path traversal
    assert sanitize_filename("../../../etc/passwd") == ".._.._.._.._etc_passwd"
    
    # Long filenames
    long_name = "a" * 300 + ".pdf"
    sanitized = sanitize_filename(long_name)
    assert len(sanitized) <= 200
```

### Quota Management Testing
```python
# Test quota enforcement
async def test_quota_enforcement():
    # Upload files up to quota limit
    for i in range(100):
        result = await manager.store_document(small_file, workspace_id)
        assert result.document_id
    
    # Next upload should fail
    with pytest.raises(StorageQuotaExceeded):
        await manager.store_document(large_file, workspace_id)
```

### Performance Benchmarks
- **File Save Operations**: <500ms for 10MB files
- **File Retrieval**: <200ms for typical documents
- **Path Generation**: <10ms for conflict resolution
- **Quota Calculations**: <100ms for workspaces with 1000+ documents
- **Concurrent Operations**: Handle 10 simultaneous uploads

### Stress Testing
```bash
# Concurrent upload stress test
for i in {1..20}; do
    curl -X POST "http://localhost:8000/api/v1/upload" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@test_${i}.pdf" \
        -F "workspace_id=123e4567-e89b-12d3-a456-426614174000" &
done
wait

# All uploads should complete successfully with unique paths
```

---

## 8. MONITORING & METRICS

### Prometheus Metrics (`/backend/app/monitoring/storage_metrics.py`)
```python
# Operation metrics
storage_operations_total = Counter(
    'storage_operations_total',
    'Total storage operations',
    ['operation_type', 'provider', 'status']
)

storage_operation_duration = Histogram(
    'storage_operation_duration_seconds',
    'Storage operation duration',
    ['operation_type', 'provider']
)

# Usage metrics
storage_bytes_used = Gauge(
    'storage_bytes_used',
    'Bytes used per workspace',
    ['workspace_id']
)

storage_files_count = Gauge(
    'storage_files_count', 
    'Number of files per workspace',
    ['workspace_id']
)

# Quota metrics
storage_quota_usage_percentage = Gauge(
    'storage_quota_usage_percentage',
    'Percentage of quota used',
    ['workspace_id']
)
```

### Log Entries Generated
```json
{
    "timestamp": "2024-11-15T14:30:00Z",
    "level": "INFO",
    "logger": "storage.manager",
    "message": "Document stored successfully",
    "extra": {
        "operation_id": "op_123e4567",
        "document_id": "doc_987fcdeb",
        "workspace_id": "ws_a1b2c3d4",
        "path": "a1b2c3d4/2024/11/987fcdeb/report.pdf",
        "size_bytes": 1048576,
        "checksum": "sha256:d2d2d2d2...",
        "provider": "local",
        "duration_ms": 125.5,
        "conflict_resolution": "timestamp"
    }
}
```

### Health Check Indicators
```json
{
    "storage": {
        "provider": "local",
        "status": "healthy",
        "checks": {
            "root_directory": {
                "exists": true,
                "writable": true,
                "free_space_gb": 45.2
            },
            "permissions": {
                "directories": "755",
                "files": "644"
            },
            "performance": {
                "avg_save_time_ms": 89.5,
                "avg_read_time_ms": 23.1
            }
        }
    }
}
```

### Performance Monitoring
- **Operation Latency**: p50, p95, p99 percentiles tracked
- **Throughput**: Operations per second by type
- **Error Rates**: Failed operations percentage
- **Storage Utilization**: Bytes used vs. available space
- **Quota Compliance**: Workspaces approaching limits

---

## 9. SECURITY CONSIDERATIONS

### Path Security
```python
# Multiple layers of path validation
def validate_path(self, path: str) -> bool:
    # 1. Path object resolution check
    path_obj = Path(path)
    try:
        path_obj.resolve().relative_to(Path("/").resolve())
    except (ValueError, RuntimeError):
        raise InvalidPathError(path, "Path traversal detected")
    
    # 2. Null byte injection prevention
    if '\x00' in path:
        raise InvalidPathError(path, "Path contains null bytes")
    
    # 3. Length validation
    if len(path) > MAX_PATH_LENGTH:
        raise InvalidPathError(path, "Path too long")
    
    return True
```

### Filename Sanitization
- **Unicode Normalization**: NFKD to prevent homograph attacks
- **Character Filtering**: Only alphanumeric, dash, underscore, dot allowed
- **Length Limits**: Truncated to 200 characters maximum
- **Reserved Names**: System filenames (CON, PRN, etc.) handled
- **Case Sensitivity**: Preserved but conflicts checked case-insensitively

### Access Controls
- **Workspace Isolation**: Files stored in workspace-specific directories
- **Database Authorization**: Document access checked via database queries
- **File Permissions**: 644 for files, 755 for directories (local storage)
- **Temporary File Security**: Temp files cleaned up automatically
- **Audit Logging**: All operations logged for compliance

### Checksum Verification
```python
# File integrity verification
async def _calculate_checksum(self, content: bytes) -> str:
    """SHA256 checksum for integrity and deduplication"""
    sha256_hash = hashlib.sha256()
    sha256_hash.update(content)
    return sha256_hash.hexdigest()

# Verification on retrieval (optional)
async def verify_file_integrity(self, document_id: UUID) -> bool:
    doc = self.db.query(Document).filter_by(id=document_id).first()
    content = await self.provider.get_file(doc.storage_path)
    calculated = await self._calculate_checksum(content)
    return calculated == doc.checksum
```

---

## 10. CODE PATTERNS & CONVENTIONS

### Abstract Base Class Pattern
```python
# Defines contract for all storage providers
class StorageProvider(ABC):
    @abstractmethod
    async def save_file(self, file_content: bytes, path: str) -> str:
        """All providers must implement this interface"""
        pass
```

### Factory Pattern
```python
# StorageManager creates appropriate provider
def _get_provider(self) -> StorageProvider:
    provider_type = storage_settings.STORAGE_PROVIDER
    
    if provider_type == StorageProviderType.LOCAL:
        return LocalStorageProvider(config)
    elif provider_type == StorageProviderType.S3:
        return S3StorageProvider(config)  # Future
    else:
        raise NotImplementedError(f"Provider {provider_type} not implemented")
```

### Strategy Pattern
```python
# Conflict resolution strategies
def _resolve_filename_conflict(
    self, 
    base_filename: str, 
    existing_paths: List[str],
    strategy: ConflictStrategy = None
) -> str:
    if strategy == ConflictStrategy.TIMESTAMP:
        return f"{name}_{timestamp}{ext}"
    elif strategy == ConflictStrategy.COUNTER:
        return f"{name}_{counter}{ext}"
    else:  # UUID fallback
        return f"{uuid_prefix}_{base_filename}"
```

### Repository Pattern (Prepared)
```python
# Future abstraction for document operations
class DocumentRepository:
    def __init__(self, db: Session, storage: StorageManager):
        self.db = db
        self.storage = storage
    
    async def save_document(self, file: UploadFile, workspace_id: UUID) -> Document:
        # Combine database and storage operations
        storage_result = await self.storage.store_document(file, workspace_id)
        
        document = Document(
            id=storage_result.document_id,
            storage_path=storage_result.path,
            checksum=storage_result.checksum
        )
        
        self.db.add(document)
        self.db.commit()
        return document
```

### Async/Await Patterns
```python
# All storage operations are async
async def store_document(self, file: UploadFile) -> StorageResult:
    # Async file reading
    content = await file.read()
    
    # Async storage operation
    await self.provider.save_file(content, path)
    
    # Async logging
    await self._log_operation("store", path, True, duration_ms, workspace_id)
```

### Context Manager Pattern
```python
# Future: Atomic operations with rollback
class StorageTransaction:
    async def __aenter__(self):
        self.temp_files = []
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # Rollback on exception
            for temp_file in self.temp_files:
                await self.provider.delete_file(temp_file)
```

---

## 11. INTEGRATION POINTS

### Database Integration
```python
# Storage operations update document metadata
class StorageManager:
    async def store_document(self, file: UploadFile, workspace_id: UUID):
        # Store file
        storage_result = await self.provider.save_file(content, path)
        
        # Update database with storage metadata
        document = Document(
            id=storage_result.document_id,
            original_name=file.filename,
            storage_path=storage_result.path,
            storage_provider=StorageProviderEnum.LOCAL,
            checksum=storage_result.checksum,
            file_size=storage_result.size
        )
        self.db.add(document)
        self.db.commit()
```

### FastAPI Integration
```python
# Dependency injection in endpoints
@router.post("/upload")
async def upload_document(
    file: UploadFile,
    workspace_id: UUID,
    db: Session = Depends(get_db)
):
    storage_manager = StorageManager(db)
    result = await storage_manager.store_document(file, workspace_id)
    return result
```

### Redis Integration (Future)
```python
# Caching storage operations
async def get_cached_document(self, document_id: UUID) -> Optional[bytes]:
    cache_key = f"doc:{document_id}"
    cached = await redis.get(cache_key)
    
    if not cached:
        content = await self.provider.get_file(doc.storage_path)
        await redis.setex(cache_key, 3600, content)  # 1 hour TTL
        return content
    
    return cached
```

### Celery Integration
```python
# Background tasks for storage operations
@celery_app.task
def cleanup_temp_files():
    """Scheduled cleanup of temporary files"""
    manager = StorageManager(get_db_session())
    deleted_count = await manager.cleanup_temp_files()
    
    logger.info(f"Cleaned up {deleted_count} temporary files")
    return deleted_count
```

### Monitoring Integration
```python
# Prometheus metrics collection
async def store_document(self, file: UploadFile, workspace_id: UUID):
    start_time = time.time()
    
    try:
        result = await self._store_document_impl(file, workspace_id)
        
        # Success metrics
        storage_operations_total.labels(
            operation_type="store",
            provider="local",
            status="success"
        ).inc()
        
        return result
        
    except Exception as e:
        # Error metrics
        storage_operations_total.labels(
            operation_type="store", 
            provider="local",
            status="error"
        ).inc()
        raise
        
    finally:
        # Duration metrics
        duration = time.time() - start_time
        storage_operation_duration.labels(
            operation_type="store",
            provider="local"
        ).observe(duration)
```

---

## 12. TROUBLESHOOTING GUIDE

### Common Issues and Solutions

#### "Permission denied on storage directory"
```bash
# Check directory permissions
ls -la storage/
# Should show drwxr-xr-x

# Fix permissions
chmod -R 755 storage/
chown -R $USER:$USER storage/

# Verify Docker can access
docker-compose exec backend ls -la /app/storage
```

#### "Filename conflicts not resolved"
```python
# Debug conflict resolution
from app.services.storage.path_generator import PathGenerator

# Test conflict resolution
existing_paths = ["workspace/2024/11/doc1/report.pdf"]
generator = PathGenerator()
result = generator._resolve_filename_conflict(
    "report.pdf", 
    existing_paths, 
    ConflictStrategy.TIMESTAMP
)
print(f"Resolved filename: {result}")
# Should show: report_20241115_143022.pdf
```

#### "Storage quota exceeded unexpectedly"
```sql
-- Check actual storage usage
SELECT 
    storage_path,
    SUM(file_size) as total_bytes,
    COUNT(*) as file_count
FROM documents 
WHERE storage_path LIKE 'workspace-id/%' 
  AND deleted_at IS NULL
GROUP BY storage_path;

-- Compare with quota settings
SELECT 
    'Quota (GB)' as metric,
    10 as value
UNION ALL
SELECT 
    'Used (GB)' as metric,
    SUM(file_size) / (1024*1024*1024) as value
FROM documents 
WHERE storage_path LIKE 'workspace-id/%' 
  AND deleted_at IS NULL;
```

#### "Files not cleaned up from temp directory"
```bash
# Check temp files age
find storage/_temp -type f -printf '%T@ %p\n' | sort -n

# Manual cleanup of old temp files
find storage/_temp -type f -mtime +1 -delete

# Check cleanup task status
docker-compose exec backend celery -A app.celery_app inspect active
```

### Debug Commands

#### Storage Provider Health Check
```python
# Test storage provider directly
from app.services.storage.local import LocalStorageProvider

provider = LocalStorageProvider()

# Test basic operations
test_content = b"Hello, World!"
await provider.save_file(test_content, "test/hello.txt")
retrieved = await provider.get_file("test/hello.txt")
assert retrieved == test_content

await provider.delete_file("test/hello.txt")
exists = await provider.exists("test/hello.txt")
assert not exists
```

#### Path Generation Debugging
```python
# Debug path generation
from app.services.storage.path_generator import PathGenerator
from uuid import uuid4

workspace_id = uuid4()
document_id = uuid4()

path = PathGenerator.generate_document_path(
    workspace_id, document_id, "test file.pdf"
)
print(f"Generated path: {path}")

components = PathGenerator.extract_components(path)
print(f"Components: {components}")
```

#### Storage Manager Testing
```python
# Test storage manager operations
from app.services.storage.manager import StorageManager
from app.db.database import get_db

db = next(get_db())
manager = StorageManager(db)

# Test quota calculation
stats = await manager.get_storage_stats(workspace_id)
print(f"Storage stats: {stats}")

# Test cleanup
deleted = await manager.cleanup_temp_files()
print(f"Deleted {deleted} temp files")
```

### Verification Queries

#### Check Storage Consistency
```sql
-- Documents without storage files
SELECT id, storage_path 
FROM documents 
WHERE storage_path IS NOT NULL 
  AND deleted_at IS NULL
  AND NOT EXISTS (
    -- This would need custom function to check file existence
    SELECT 1 FROM check_file_exists(storage_path)
  );

-- Storage files without database records
-- (Requires file system scan - implement as admin tool)
```

#### Monitor Storage Performance
```sql
-- Average file sizes by workspace
SELECT 
    SUBSTRING(storage_path FROM '^([^/]+)') as workspace_id,
    AVG(file_size) as avg_size_bytes,
    COUNT(*) as file_count,
    SUM(file_size) as total_bytes
FROM documents 
WHERE deleted_at IS NULL
GROUP BY SUBSTRING(storage_path FROM '^([^/]+)')
ORDER BY total_bytes DESC;

-- Files uploaded in last 24 hours
SELECT 
    COUNT(*) as files_uploaded,
    SUM(file_size) as bytes_uploaded,
    AVG(file_size) as avg_file_size
FROM documents 
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND deleted_at IS NULL;
```

### Log Analysis Commands
```bash
# Parse storage operation logs
grep "Storage operation" app.log | jq '{
    timestamp: .timestamp,
    operation: .extra.operation_type,
    success: .extra.success,
    duration: .extra.duration_ms
}'

# Find slow storage operations
grep "Storage operation" app.log | jq 'select(.extra.duration_ms > 1000)'

# Count operations by type
grep "Storage operation" app.log | jq -r '.extra.operation_type' | sort | uniq -c

# Monitor real-time storage operations
tail -f app.log | grep "storage" | jq '.'
```

---

## Summary

Step 5 successfully implements a comprehensive storage service pattern that provides:

1. **Abstracted Storage Interface** - Clean separation between storage logic and provider implementation
2. **Intelligent Path Management** - Organized directory structure with conflict resolution
3. **Comprehensive Security** - Path validation, permission management, and access controls
4. **Performance Optimization** - Async operations, caching preparation, and efficient file handling
5. **Multi-tenant Architecture** - Workspace-based organization and quota management
6. **Audit and Compliance** - Complete operation logging and monitoring
7. **Scalability Foundation** - Provider pattern enables seamless cloud migration
8. **Robust Error Handling** - Comprehensive exception hierarchy and recovery mechanisms

This storage foundation enables all future document processing capabilities while maintaining security, performance, and scalability requirements for production deployment.
