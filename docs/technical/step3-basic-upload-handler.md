# QueryBox Core: Step 3 - Basic Upload Handler
## Technical Implementation Documentation

---

## 1. FEATURE OVERVIEW

### What This Step Accomplishes
Step 3 implements the core document upload functionality that serves as the entry point for all documents into the QueryBox Core system:
- **Multipart Form Data Reception**: Handles file uploads via HTTP multipart forms
- **File Validation & Processing**: Validates file types, sizes, and content integrity
- **Temporary File Management**: Secure handling of files during upload process
- **Local Storage Integration**: Stores files in organized directory structure
- **Database Metadata Storage**: Persists document metadata with full audit trail
- **Atomic Operations**: Ensures consistency between file storage and database records
- **Error Recovery**: Automatic cleanup on failures with transaction rollback

### Why This Step is Necessary
The Basic Upload Handler is essential because it:
- Provides the primary interface for document ingestion into the system
- Establishes security boundaries with file validation and sanitization
- Creates the foundation for document processing pipeline
- Implements atomic operations ensuring data consistency
- Enables tracking of document lifecycle from upload onwards
- Sets up the storage organization that supports future features

### Dependencies on Previous Steps
- **Step 1**: Database schema and storage directory structure for metadata persistence
- **Step 1**: Connection pooling for database operations and Redis for session management
- **Step 2**: FastAPI routing structure and error handling framework
- **Step 2**: Health check endpoints that verify storage system readiness

### What Future Steps Depend on This
- **Document Processing Pipeline**: Uploaded documents trigger processing workflows
- **Storage Management**: Advanced storage features build on basic upload functionality
- **Document Versioning**: Version control extends the basic upload mechanism
- **Batch Operations**: Multiple document handling extends single upload patterns
- **Cloud Storage**: Multi-provider storage builds on local storage foundation

---

## 2. TECHNICAL IMPLEMENTATION

### Files Created/Modified

#### Core Upload Implementation
```
/backend/app/api/v1/endpoints/
└── upload.py                     # Main upload endpoint implementation

/backend/app/schemas/
├── upload.py                     # Upload request/response schemas
└── document.py                   # Document metadata schemas

/backend/app/services/
├── upload_service.py             # Upload business logic
├── file_processor.py             # File validation and processing
└── storage_service.py            # Storage operations abstraction
```

#### Configuration Updates
```
/backend/app/core/
├── config.py                     # Enhanced with upload-specific settings
└── upload_config.py              # Upload-specific configuration

/backend/app/utils/
├── file_utils.py                 # File utility functions
├── validation.py                 # Input validation helpers
└── crypto_utils.py               # Checksum and hash utilities
```

#### Enhanced Models
```
/backend/app/models/
├── document.py                   # Enhanced with upload tracking
└── upload_session.py             # Upload session tracking (optional)
```

### Key Classes and Functions

#### Upload Endpoint (`/backend/app/api/v1/endpoints/upload.py`)
```python
@router.post("/", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = Form(default="default"),
    document_name: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    db: Session = Depends(get_db)
) -> UploadResponse:
    """
    Upload a document with metadata storage and validation.
    
    Features:
    - Multipart file upload with form data
    - File type and size validation
    - Checksum calculation for integrity
    - Atomic storage and database operations
    - Comprehensive error handling
    """
```

#### Upload Service (`/backend/app/services/upload_service.py`)
```python
class UploadService:
    def __init__(self, db: Session, storage_service: StorageService):
        self.db = db
        self.storage = storage_service
    
    async def process_upload(
        self, 
        file: UploadFile,
        workspace_id: str,
        metadata: dict
    ) -> UploadResult:
        """Main upload processing logic with atomic operations"""
        
    async def validate_file(self, file: UploadFile) -> ValidationResult:
        """Comprehensive file validation"""
        
    async def calculate_checksum(self, content: bytes) -> str:
        """SHA-256 checksum calculation"""
        
    async def create_document_record(
        self, 
        file_metadata: dict,
        storage_path: str
    ) -> Document:
        """Create database record with transaction handling"""
```

#### File Processor (`/backend/app/services/file_processor.py`)
```python
class FileProcessor:
    @staticmethod
    async def validate_file_type(file: UploadFile) -> bool:
        """Validate file type using MIME detection"""
        
    @staticmethod
    async def validate_file_size(file: UploadFile) -> bool:
        """Check file size against limits"""
        
    @staticmethod
    async def sanitize_filename(filename: str) -> str:
        """Clean and secure filename"""
        
    @staticmethod
    async def detect_mime_type(content: bytes) -> str:
        """Detect actual MIME type from content"""
```

### Database Tables Used

#### documents Table (Enhanced)
```sql
-- Core document metadata
id UUID PRIMARY KEY,
document_name VARCHAR(255) NOT NULL,
original_name VARCHAR(255) NOT NULL,
mime_type VARCHAR(100) NOT NULL,
file_extension VARCHAR(10) NOT NULL,
file_size BIGINT NOT NULL,
checksum VARCHAR(64) NOT NULL UNIQUE,

-- Storage information  
storage_provider VARCHAR(50) DEFAULT 'local',
storage_path TEXT NOT NULL,
storage_bucket VARCHAR(100),

-- Upload tracking
upload_session_id UUID,
uploaded_by VARCHAR(255),
upload_ip_address INET,
upload_user_agent TEXT,

-- Status and timestamps
status VARCHAR(50) DEFAULT 'uploaded',
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW(),

-- Soft delete support
is_deleted BOOLEAN DEFAULT FALSE,
deleted_at TIMESTAMP NULL
```

#### upload_sessions Table (Optional tracking)
```sql
-- Upload session tracking
id UUID PRIMARY KEY,
workspace_id UUID NOT NULL,
session_token VARCHAR(255),
ip_address INET,
user_agent TEXT,
started_at TIMESTAMP DEFAULT NOW(),
completed_at TIMESTAMP NULL,
status VARCHAR(50) DEFAULT 'in_progress'
```

### API Endpoints

#### Primary Upload Endpoint
```http
POST /api/v1/upload/
Content-Type: multipart/form-data

Form Data:
- file: File (required) - The document file to upload
- workspace_id: String (optional) - Workspace identifier
- document_name: String (optional) - Custom document name
- metadata: JSON String (optional) - Additional metadata

Response 201 Created:
{
    "document_id": "uuid",
    "filename": "sanitized_name.pdf",
    "original_name": "user_file.pdf",
    "size": 1048576,
    "mime_type": "application/pdf",
    "checksum": "sha256_hash",
    "storage_path": "workspace/2024/11/doc_id/file.pdf",
    "upload_time": "2024-11-15T10:30:00Z",
    "status": "uploaded"
}
```

#### Supporting Endpoints
```http
# Upload status check
GET /api/v1/upload/{upload_id}/status
Response: {"status": "completed", "progress": 100}

# Upload metadata
GET /api/v1/upload/{upload_id}/metadata  
Response: {"filename": "...", "size": 123, ...}

# Cancel upload (future)
DELETE /api/v1/upload/{upload_id}
Response: {"cancelled": true}
```

### Request/Response Schemas

#### Upload Request Schema
```python
class UploadRequest(BaseModel):
    workspace_id: str = Field(default="default", max_length=36)
    document_name: Optional[str] = Field(None, max_length=255)
    metadata: Optional[Dict[str, Any]] = Field(None)
    
    class Config:
        schema_extra = {
            "example": {
                "workspace_id": "workspace-uuid",
                "document_name": "Financial Report Q3",
                "metadata": {
                    "department": "Finance",
                    "quarter": "Q3",
                    "year": 2024
                }
            }
        }
```

#### Upload Response Schema
```python
class UploadResponse(BaseModel):
    document_id: UUID
    filename: str
    original_name: str
    size: int
    mime_type: str
    checksum: str
    storage_path: str
    upload_time: datetime
    status: str
    workspace_id: str
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }
```

---

## 3. DATA FLOW

### Complete Upload Flow
```
1. Client Request → Multipart form data with file
2. FastAPI Reception → File stored in memory/temp disk
3. File Validation → Type, size, content checks
4. Checksum Calculation → SHA-256 hash for integrity
5. Storage Path Generation → Organized directory structure
6. File Storage → Atomic write to storage location
7. Database Transaction → Metadata record creation
8. Response Generation → Upload result with metadata
9. Cleanup → Temporary resources released
```

### Detailed Processing Steps

#### Step 1: Request Reception
```python
# FastAPI receives multipart form data
file: UploadFile = File(...)  # Temporary file or memory
workspace_id: str = Form(default="default")
metadata: Optional[str] = Form(None)

# File object provides:
# - file.filename: Original filename
# - file.content_type: Declared MIME type  
# - file.file: File-like object
# - file.size: Content length (if available)
```

#### Step 2: File Validation
```python
# Size validation
if file.size > MAX_FILE_SIZE:
    raise HTTPException(413, "File too large")

# Type validation (extension + MIME)
allowed_extensions = ['.pdf', '.docx', '.txt', ...]
if not filename.endswith(tuple(allowed_extensions)):
    raise HTTPException(400, "File type not allowed")

# Content validation
content = await file.read()
detected_mime = magic.from_buffer(content, mime=True)
if detected_mime not in ALLOWED_MIME_TYPES:
    raise HTTPException(400, "Invalid file content")
```

#### Step 3: Storage Operations
```python
# Generate storage path
storage_path = f"{workspace_id}/{datetime.now().year}/{datetime.now().month}/{document_id}/{sanitized_filename}"

# Atomic file write
try:
    # Create directory structure
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # Write file atomically (temp file + rename)
    temp_path = f"{full_path}.tmp"
    with open(temp_path, 'wb') as f:
        f.write(content)
    os.rename(temp_path, full_path)
    
    # Set proper permissions
    os.chmod(full_path, 0o644)
    
except Exception as e:
    # Cleanup partial write
    if os.path.exists(temp_path):
        os.unlink(temp_path)
    raise StorageException(f"Storage failed: {e}")
```

#### Step 4: Database Transaction
```python
# Atomic database operation
try:
    with db.begin():
        document = Document(
            id=document_id,
            document_name=document_name or original_filename,
            original_name=original_filename,
            mime_type=detected_mime,
            file_size=len(content),
            checksum=sha256_hash,
            storage_path=storage_path,
            workspace_id=workspace_id,
            status='uploaded'
        )
        db.add(document)
        db.commit()
        
        return document
        
except Exception as e:
    # Cleanup stored file on database failure
    if os.path.exists(full_path):
        os.unlink(full_path)
    raise DatabaseException(f"Database operation failed: {e}")
```

### Error Recovery Flow
```
Storage Failure → Cleanup temporary files → Return error
Database Failure → Remove stored file → Rollback transaction → Return error
Validation Failure → Immediate rejection → No cleanup needed
System Error → Cleanup all resources → Log error → Return 500
```

---

## 4. VALIDATIONS & CONSTRAINTS

### File Size Constraints
```python
# Configurable limits
MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB default
LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB threshold

# Size validation
async def validate_file_size(file: UploadFile) -> None:
    # Memory-efficient size check
    total_size = 0
    chunk_size = 8192
    
    while chunk := await file.read(chunk_size):
        total_size += len(chunk)
        if total_size > MAX_FILE_SIZE:
            raise HTTPException(413, f"File exceeds maximum size of {MAX_FILE_SIZE/1024/1024:.1f}MB")
    
    await file.seek(0)  # Reset for processing
```

### File Type Validation
```python
# Allowed file extensions
ALLOWED_EXTENSIONS = {
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.txt': 'text/plain',
    '.md': 'text/markdown',
    '.html': 'text/html',
    '.csv': 'text/csv',
    '.json': 'application/json',
    '.xml': 'application/xml'
}

# MIME type validation
ALLOWED_MIME_TYPES = set(ALLOWED_EXTENSIONS.values())

# Two-tier validation
def validate_file_type(filename: str, content: bytes) -> bool:
    # 1. Extension check
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    
    # 2. Content-based MIME detection
    detected_mime = magic.from_buffer(content, mime=True)
    expected_mime = ALLOWED_EXTENSIONS[ext]
    
    return detected_mime == expected_mime
```

### Filename Sanitization
```python
def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove null bytes and control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Limit length
    name, ext = os.path.splitext(filename)
    if len(name) > 200:
        name = name[:200]
    
    # Prevent empty names
    if not name:
        name = f"unnamed_{uuid.uuid4().hex[:8]}"
    
    # Prevent system names (Windows)
    reserved = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1,10)] + [f'LPT{i}' for i in range(1,10)]
    if name.upper() in reserved:
        name = f"{name}_file"
    
    return f"{name}{ext}"
```

### Workspace Validation
```python
def validate_workspace_id(workspace_id: str) -> bool:
    """Validate workspace identifier"""
    # UUID format check
    try:
        UUID(workspace_id)
        return True
    except ValueError:
        # Allow 'default' workspace
        return workspace_id == "default"
```

---

## 5. CONFIGURATION

### Environment Variables
```bash
# File Upload Configuration
MAX_FILE_SIZE=31457280              # 30MB in bytes
LARGE_FILE_THRESHOLD=10485760       # 10MB threshold for large files
UPLOAD_TEMP_DIR=/tmp/uploads        # Temporary upload directory
UPLOAD_CHUNK_SIZE=8192              # Read chunk size for validation

# Storage Configuration
STORAGE_ROOT=/app/storage           # Base storage directory
STORAGE_PERMISSIONS=644             # File permissions (octal)
STORAGE_DIR_PERMISSIONS=755         # Directory permissions (octal)

# Security Configuration
ALLOWED_EXTENSIONS="['.pdf','.docx','.txt','.md','.html','.csv','.json','.xml']"
ENABLE_MIME_VALIDATION=true         # Enable content-based MIME checking
UPLOAD_RATE_LIMIT=100               # Uploads per minute per IP

# Processing Configuration
CALCULATE_CHECKSUM=true             # Enable SHA-256 checksum calculation
ENABLE_DEDUPLICATION=true           # Check for duplicate files
ASYNC_PROCESSING=false              # Process uploads synchronously (MVP)

# Database Configuration
UPLOAD_SESSION_TRACKING=false       # Track upload sessions (optional)
UPLOAD_AUDIT_LOGGING=true           # Log upload operations
```

### Default Values and Limits
```python
class UploadConfig:
    # File constraints
    MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB
    MIN_FILE_SIZE = 1  # 1 byte minimum
    MAX_FILENAME_LENGTH = 255
    
    # Allowed file types
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md', '.html', '.csv', '.json', '.xml'}
    
    # Storage settings
    STORAGE_ROOT = "storage"
    TEMP_DIR = "storage/temp"
    UPLOAD_DIR = "storage/uploads"
    
    # Performance settings
    CHUNK_SIZE = 8192  # 8KB chunks
    MAX_CONCURRENT_UPLOADS = 10
    
    # Security settings
    ENABLE_VIRUS_SCAN = False  # Future feature
    QUARANTINE_SUSPICIOUS = False  # Future feature
```

### Directory Structure
```
/storage/
├── uploads/                    # Successful uploads by workspace
│   ├── default/               # Default workspace
│   │   ├── 2024/
│   │   │   ├── 11/           # Year/Month organization
│   │   │   │   ├── {doc_id_1}/
│   │   │   │   │   └── document.pdf
│   │   │   │   └── {doc_id_2}/
│   │   │   │       └── report.docx
│   │   │   └── 12/
│   │   └── 2025/
│   └── {workspace_id}/        # Other workspaces
├── temp/                      # Temporary upload processing
│   ├── {session_id}/         # Per-session temp files
│   └── processing/           # Files being processed
├── failed/                   # Failed upload attempts
└── quarantine/               # Suspicious files (future)
```

### Docker Service Dependencies
```yaml
# Required services for upload functionality
services:
  postgres:                    # Database for metadata storage
    depends_on: [postgres]
  
  redis:                      # Session management and caching
    depends_on: [redis]
  
  storage:                    # Storage volume for file persistence
    volumes:
      - ./storage:/app/storage
```

---

## 6. ERROR HANDLING

### File Validation Errors
```python
# File size errors
class FileSizeError(HTTPException):
    def __init__(self, actual_size: int, max_size: int):
        detail = f"File size {actual_size/1024/1024:.1f}MB exceeds maximum {max_size/1024/1024:.1f}MB"
        super().__init__(status_code=413, detail=detail)

# File type errors
class FileTypeError(HTTPException):
    def __init__(self, filename: str, detected_type: str):
        detail = f"File type '{detected_type}' not allowed for '{filename}'"
        super().__init__(status_code=400, detail=detail)

# Content validation errors
class FileContentError(HTTPException):
    def __init__(self, message: str):
        super().__init__(status_code=400, detail=f"Invalid file content: {message}")
```

### Storage Operation Errors
```python
# Storage space errors
class StorageFullError(HTTPException):
    def __init__(self, available_space: int):
        detail = f"Insufficient storage space. Available: {available_space/1024/1024:.1f}MB"
        super().__init__(status_code=507, detail=detail)

# Permission errors
class StoragePermissionError(HTTPException):
    def __init__(self, path: str):
        detail = f"Permission denied accessing storage path: {path}"
        super().__init__(status_code=500, detail=detail)

# I/O errors
class StorageIOError(HTTPException):
    def __init__(self, operation: str, error: str):
        detail = f"Storage {operation} failed: {error}"
        super().__init__(status_code=500, detail=detail)
```

### Database Operation Errors
```python
# Duplicate file errors
class DuplicateFileError(HTTPException):
    def __init__(self, checksum: str, existing_doc_id: str):
        detail = f"File already exists with checksum {checksum[:16]}... (Document ID: {existing_doc_id})"
        super().__init__(status_code=409, detail=detail)

# Database constraint errors
class DatabaseConstraintError(HTTPException):
    def __init__(self, constraint: str):
        detail = f"Database constraint violation: {constraint}"
        super().__init__(status_code=400, detail=detail)
```

### Error Recovery Mechanisms
```python
async def upload_with_recovery(file: UploadFile, metadata: dict) -> UploadResponse:
    """Upload with automatic error recovery and cleanup"""
    temp_files = []
    db_transaction = None
    
    try:
        # Stage 1: File validation and temp storage
        temp_path = await store_temp_file(file)
        temp_files.append(temp_path)
        
        # Stage 2: Content validation
        await validate_file_content(temp_path)
        
        # Stage 3: Permanent storage
        storage_path = await move_to_permanent_storage(temp_path)
        
        # Stage 4: Database transaction
        db_transaction = db.begin()
        document = await create_document_record(metadata, storage_path)
        await db_transaction.commit()
        
        return UploadResponse.from_document(document)
        
    except Exception as e:
        # Cleanup on any failure
        await cleanup_upload_failure(temp_files, storage_path, db_transaction)
        raise e
    
    finally:
        # Always cleanup temp files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
```

### Logging Points
```python
# Upload operation logging
logger.info("Upload started", extra={
    "filename": file.filename,
    "size": file.size,
    "workspace_id": workspace_id,
    "ip_address": request.client.host
})

logger.info("Upload completed", extra={
    "document_id": document.id,
    "storage_path": document.storage_path,
    "checksum": document.checksum,
    "duration_ms": (end_time - start_time) * 1000
})

# Error logging
logger.error("Upload failed", extra={
    "filename": file.filename,
    "error_type": type(e).__name__,
    "error_message": str(e),
    "stage": "file_validation"  # validation|storage|database
})
```

---

## 7. TESTING CHECKLIST

### Basic Upload Testing
```bash
# Test successful PDF upload
curl -X POST http://localhost:8000/api/v1/upload/ \
  -F "file=@test.pdf" \
  -F "workspace_id=test-workspace" \
  -F "document_name=Test Document"

# Expected: 201 Created with document metadata
```

### File Type Validation Testing
```bash
# Test allowed file types
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@document.pdf"    # Should succeed
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@document.docx"   # Should succeed  
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@document.txt"    # Should succeed
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@script.exe"      # Should fail (400)

# Test MIME type validation
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@malicious.exe"   # Should fail (400)
# (Even if renamed to .pdf, content detection should catch it)
```

### File Size Testing
```bash
# Create test files of various sizes
dd if=/dev/zero of=small.txt bs=1024 count=100      # 100KB
dd if=/dev/zero of=medium.txt bs=1024 count=10240   # 10MB  
dd if=/dev/zero of=large.txt bs=1024 count=30720    # 30MB
dd if=/dev/zero of=toolarge.txt bs=1024 count=40960 # 40MB

# Test uploads
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@small.txt"    # Should succeed
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@medium.txt"   # Should succeed
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@large.txt"    # Should succeed  
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@toolarge.txt" # Should fail (413)
```

### Security Testing
```bash
# Path traversal attempts
curl -X POST http://localhost:8000/api/v1/upload/ \
  -F "file=@test.pdf" \
  -F "document_name=../../../etc/passwd"
# Should succeed but filename should be sanitized

# Special character handling
curl -X POST http://localhost:8000/api/v1/upload/ \
  -F "file=@test.pdf" \
  -F "document_name=file<>:|?*.pdf"
# Should succeed with sanitized filename

# Empty file test
touch empty.txt
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@empty.txt"
# Should succeed (0 bytes is allowed)
```

### Duplicate Detection Testing
```bash
# Upload same file twice
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@document.pdf"
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@document.pdf"
# Second upload should return 409 Conflict with existing document info
```

### Concurrent Upload Testing
```bash
# Test multiple simultaneous uploads
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@test$i.pdf" \
    -F "workspace_id=test-$i" &
done
wait
# All should complete successfully without conflicts
```

### Performance Benchmarks
```bash
# Large file upload performance
time curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@25MB_file.pdf"
# Should complete in <10 seconds

# Concurrent upload performance  
ab -n 100 -c 10 -p test_file.pdf -T 'multipart/form-data' \
   http://localhost:8000/api/v1/upload/
# Should handle 10 concurrent uploads with <5s average response time
```

### Expected Behaviors
- **Upload Success Rate**: >99% for valid files under normal conditions
- **Response Time**: <2s for files under 10MB, <10s for files under 30MB
- **Storage Integrity**: Checksum verification shows 100% data integrity
- **Database Consistency**: No orphaned files or missing database records
- **Error Recovery**: No partial uploads or corrupted files after failures

---

## 8. MONITORING & METRICS

### Upload Metrics Collection
```python
# Upload operation metrics
upload_total = Counter('uploads_total', 'Total upload attempts', ['status', 'file_type'])
upload_duration = Histogram('upload_duration_seconds', 'Upload processing time', ['file_size_category'])
upload_file_size = Histogram('upload_file_size_bytes', 'Uploaded file sizes')
upload_errors = Counter('upload_errors_total', 'Upload errors', ['error_type'])

# Storage metrics
storage_operations = Counter('storage_operations_total', 'Storage operations', ['operation'])
storage_space_used = Gauge('storage_space_used_bytes', 'Storage space used')
storage_file_count = Gauge('storage_file_count', 'Number of stored files')

# Database metrics
db_operations = Counter('database_operations_total', 'Database operations', ['table', 'operation'])
db_query_duration = Histogram('database_query_duration_seconds', 'Database query time')
```

### Log Entries Generated
```json
// Successful upload
{
    "timestamp": "2024-11-15T10:30:00Z",
    "level": "INFO",
    "event": "upload_completed",
    "document_id": "doc-uuid",
    "filename": "report.pdf",
    "original_name": "Financial Report Q3.pdf", 
    "file_size": 1048576,
    "mime_type": "application/pdf",
    "checksum": "sha256-hash",
    "workspace_id": "workspace-uuid",
    "storage_path": "workspace/2024/11/doc-uuid/report.pdf",
    "duration_ms": 1250,
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
}

// Upload error
{
    "timestamp": "2024-11-15T10:31:00Z", 
    "level": "ERROR",
    "event": "upload_failed",
    "filename": "malicious.exe",
    "error_type": "FileTypeError",
    "error_message": "File type 'application/x-executable' not allowed",
    "stage": "validation",
    "ip_address": "192.168.1.100"
}

// Storage operation
{
    "timestamp": "2024-11-15T10:30:30Z",
    "level": "INFO", 
    "event": "file_stored",
    "storage_path": "workspace/2024/11/doc-uuid/report.pdf",
    "file_size": 1048576,
    "operation": "write",
    "duration_ms": 45
}
```

### Health Check Integration
```json
// Enhanced health check including upload system
{
    "status": "healthy",
    "timestamp": "2024-11-15T10:30:00Z",
    "checks": {
        "upload_system": {
            "status": "healthy",
            "storage_writable": true,
            "temp_dir_accessible": true,
            "recent_uploads": 45,
            "recent_errors": 0,
            "storage_space_available_gb": 25.5
        }
    }
}
```

### Performance Measurements
```python
# Upload performance tracking
@router.post("/upload")
async def upload_endpoint(file: UploadFile):
    start_time = time.time()
    
    try:
        result = await process_upload(file)
        
        # Record success metrics
        duration = time.time() - start_time
        upload_duration.labels(file_size_category=get_size_category(file.size)).observe(duration)
        upload_total.labels(status='success', file_type=file.content_type).inc()
        upload_file_size.observe(file.size)
        
        return result
        
    except Exception as e:
        # Record error metrics
        upload_total.labels(status='error', file_type=file.content_type).inc()
        upload_errors.labels(error_type=type(e).__name__).inc()
        raise
```

---

## 9. SECURITY CONSIDERATIONS

### Input Sanitization
```python
def sanitize_upload_inputs(
    filename: str, 
    workspace_id: str, 
    document_name: Optional[str],
    metadata: Optional[str]
) -> dict:
    """Comprehensive input sanitization for upload endpoint"""
    
    # Filename sanitization (prevents path traversal)
    clean_filename = sanitize_filename(filename)
    
    # Workspace ID validation (prevents injection)
    if not re.match(r'^[a-zA-Z0-9-_]{1,36}$', workspace_id):
        raise ValueError("Invalid workspace ID format")
    
    # Document name sanitization
    if document_name:
        document_name = html.escape(document_name[:255])
    
    # Metadata validation (prevents JSON injection)
    if metadata:
        try:
            parsed_metadata = json.loads(metadata)
            # Limit metadata size and depth
            if len(json.dumps(parsed_metadata)) > 10240:  # 10KB limit
                raise ValueError("Metadata too large")
        except json.JSONDecodeError:
            raise ValueError("Invalid metadata JSON")
    
    return {
        "filename": clean_filename,
        "workspace_id": workspace_id,
        "document_name": document_name,
        "metadata": parsed_metadata
    }
```

### File Type Restrictions
```python
# Multi-layer file type validation
class FileTypeValidator:
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md', '.html', '.csv', '.json', '.xml'}
    
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/markdown', 
        'text/html',
        'text/csv',
        'application/json',
        'application/xml'
    }
    
    # Dangerous file signatures to reject
    DANGEROUS_SIGNATURES = [
        b'\x4d\x5a',  # PE executable
        b'\x7f\x45\x4c\x46',  # ELF executable  
        b'\xca\xfe\xba\xbe',  # Mach-O executable
        b'\x50\x4b\x03\x04',  # ZIP (could contain executables)
    ]
    
    @classmethod
    async def validate_file_safety(cls, content: bytes, filename: str) -> bool:
        # Check file signature against dangerous patterns
        for signature in cls.DANGEROUS_SIGNATURES:
            if content.startswith(signature):
                return False
        
        # Extension validation
        ext = os.path.splitext(filename)[1].lower()
        if ext not in cls.ALLOWED_EXTENSIONS:
            return False
        
        # MIME type validation using python-magic
        detected_mime = magic.from_buffer(content, mime=True)
        if detected_mime not in cls.ALLOWED_MIME_TYPES:
            return False
        
        return True
```

### Path Traversal Prevention
```python
def secure_storage_path(workspace_id: str, document_id: str, filename: str) -> str:
    """Generate secure storage path preventing directory traversal"""
    
    # Validate all components
    if '..' in workspace_id or '/' in workspace_id:
        raise SecurityError("Invalid workspace ID")
    
    if '..' in document_id or '/' in document_id:
        raise SecurityError("Invalid document ID")
    
    # Sanitize filename (remove path components)
    filename = os.path.basename(filename)
    filename = sanitize_filename(filename)
    
    # Build path with date organization
    now = datetime.utcnow()
    path = f"{workspace_id}/{now.year}/{now.month:02d}/{document_id}/{filename}"
    
    # Normalize and validate final path
    normalized_path = os.path.normpath(path)
    if normalized_path.startswith('/') or '..' in normalized_path:
        raise SecurityError("Invalid storage path generated")
    
    return normalized_path
```

### SQL Injection Prevention
```python
# All database operations use parameterized queries via SQLAlchemy ORM
async def create_document_record(metadata: dict) -> Document:
    """Create document record with SQL injection protection"""
    
    # SQLAlchemy ORM automatically parameterizes queries
    document = Document(
        id=metadata['document_id'],
        document_name=metadata['document_name'],  # Automatically escaped
        original_name=metadata['original_name'],  # Automatically escaped
        mime_type=metadata['mime_type'],
        file_size=metadata['file_size'],
        checksum=metadata['checksum'],
        storage_path=metadata['storage_path'],
        workspace_id=metadata['workspace_id']
    )
    
    # Parameterized insert via ORM
    db.add(document)
    await db.commit()
    
    return document

# Raw queries (if needed) use bound parameters
async def find_duplicate_by_checksum(checksum: str) -> Optional[Document]:
    """Find duplicate using parameterized query"""
    query = select(Document).where(Document.checksum == :checksum)
    result = await db.execute(query, {"checksum": checksum})
    return result.scalar_one_or_none()
```

### Authentication Framework (Prepared)
```python
# API key authentication middleware (ready for implementation)
async def verify_upload_permissions(
    api_key: str = Header(..., alias="X-API-Key"),
    workspace_id: str = Form(...)
) -> bool:
    """Verify upload permissions for workspace"""
    
    # Validate API key
    if not await validate_api_key(api_key):
        raise HTTPException(401, "Invalid API key")
    
    # Check workspace permissions
    if not await check_workspace_access(api_key, workspace_id):
        raise HTTPException(403, "Access denied to workspace")
    
    return True

# Usage in upload endpoint
@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = Form(...),
    _: bool = Depends(verify_upload_permissions)  # Future authentication
):
    # Upload logic here
    pass
```

---

## 10. CODE PATTERNS & CONVENTIONS

### Service Layer Pattern
```python
# Upload service encapsulates business logic
class UploadService:
    def __init__(self, db: Session, storage: StorageService):
        self.db = db
        self.storage = storage
    
    async def process_upload(self, file: UploadFile, metadata: dict) -> UploadResult:
        """Main upload processing with business logic separation"""
        
        # Validation layer
        await self.validate_upload(file, metadata)
        
        # Business logic
        checksum = await self.calculate_checksum(file)
        existing_doc = await self.check_duplicate(checksum)
        
        if existing_doc:
            return UploadResult.from_existing(existing_doc)
        
        # Storage layer
        storage_path = await self.storage.store_file(file, metadata)
        
        # Persistence layer  
        document = await self.create_document_record(file, metadata, storage_path)
        
        return UploadResult.from_document(document)
```

### Repository Pattern
```python
# Document repository for data access
class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db
    
    async def create(self, document_data: dict) -> Document:
        """Create new document record"""
        document = Document(**document_data)
        self.db.add(document)
        await self.db.commit()
        return document
    
    async def find_by_checksum(self, checksum: str) -> Optional[Document]:
        """Find document by checksum for duplicate detection"""
        return self.db.query(Document).filter(
            Document.checksum == checksum,
            Document.is_deleted == False
        ).first()
    
    async def update_status(self, document_id: UUID, status: str) -> bool:
        """Update document status"""
        document = await self.get_by_id(document_id)
        if document:
            document.status = status
            document.updated_at = datetime.utcnow()
            await self.db.commit()
            return True
        return False
```

### Factory Pattern for File Processors
```python
# File processor factory based on MIME type
class FileProcessorFactory:
    _processors = {
        'application/pdf': PDFProcessor,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DOCXProcessor,
        'text/plain': TextProcessor,
        'text/markdown': MarkdownProcessor,
    }
    
    @classmethod
    def get_processor(cls, mime_type: str) -> FileProcessor:
        """Get appropriate processor for file type"""
        processor_class = cls._processors.get(mime_type, GenericProcessor)
        return processor_class()
    
    @classmethod
    def register_processor(cls, mime_type: str, processor_class: type):
        """Register new file processor"""
        cls._processors[mime_type] = processor_class

# Usage
processor = FileProcessorFactory.get_processor(file.content_type)
processed_content = await processor.process(file_content)
```

### Async Context Manager for Cleanup
```python
class UploadContext:
    """Context manager for upload operations with automatic cleanup"""
    
    def __init__(self, file: UploadFile):
        self.file = file
        self.temp_files = []
        self.db_transaction = None
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup on success or failure
        await self.cleanup()
        
        if exc_type:
            # Additional error handling
            logger.error(f"Upload failed: {exc_val}")
            
    async def add_temp_file(self, file_path: str):
        """Track temporary file for cleanup"""
        self.temp_files.append(file_path)
        
    async def cleanup(self):
        """Clean up all temporary resources"""
        # Remove temporary files
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except OSError:
                pass
        
        # Rollback database transaction if needed
        if self.db_transaction and self.db_transaction.is_active:
            await self.db_transaction.rollback()

# Usage
async with UploadContext(file) as ctx:
    temp_path = await store_temp_file(file)
    ctx.add_temp_file(temp_path)
    
    result = await process_upload(temp_path)
    # Automatic cleanup happens here
```

### Error Propagation Strategy
```python
# Hierarchical exception handling
class UploadException(Exception):
    """Base exception for upload operations"""
    pass

class ValidationError(UploadException):
    """File validation failures"""
    pass

class StorageError(UploadException):
    """Storage operation failures"""
    pass

class DatabaseError(UploadException):
    """Database operation failures"""
    pass

# Exception handler maps exceptions to HTTP responses
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "type": "validation_error"}
    )

@app.exception_handler(StorageError)
async def storage_error_handler(request: Request, exc: StorageError):
    return JSONResponse(
        status_code=500,
        content={"detail": "Storage operation failed", "type": "storage_error"}
    )
```

### Naming Conventions
- **Endpoints**: `/upload`, `/upload/{id}/status` (kebab-case URLs)
- **Functions**: `process_upload()`, `validate_file_type()` (snake_case)
- **Classes**: `UploadService`, `FileProcessor` (PascalCase)
- **Constants**: `MAX_FILE_SIZE`, `ALLOWED_EXTENSIONS` (UPPER_SNAKE_CASE)
- **Variables**: `file_content`, `storage_path` (snake_case)

---

## 11. INTEGRATION POINTS

### Database Integration
```python
# Upload service integrates with document model
async def create_document_record(
    file_metadata: dict,
    storage_path: str,
    db: Session
) -> Document:
    """Create document record with full metadata"""
    
    document = Document(
        id=uuid.uuid4(),
        document_name=file_metadata['document_name'],
        original_name=file_metadata['original_name'],
        mime_type=file_metadata['mime_type'],
        file_extension=file_metadata['file_extension'],
        file_size=file_metadata['file_size'], 
        checksum=file_metadata['checksum'],
        storage_provider='local',
        storage_path=storage_path,
        workspace_id=file_metadata['workspace_id'],
        status='uploaded',
        metadata=file_metadata.get('metadata', {})
    )
    
    db.add(document)
    await db.commit()
    
    return document
```

### Storage System Integration  
```python
# Upload service integrates with storage abstraction
class StorageService:
    def __init__(self, provider: str = 'local'):
        self.provider = self._get_provider(provider)
    
    async def store_file(
        self, 
        content: bytes, 
        storage_path: str
    ) -> str:
        """Store file using configured provider"""
        return await self.provider.save_file(content, storage_path)
    
    async def ensure_directory(self, directory_path: str):
        """Ensure storage directory exists"""
        await self.provider.create_directory(directory_path)

# Usage in upload endpoint
storage = StorageService()
storage_path = await storage.store_file(file_content, organized_path)
```

### FastAPI Integration
```python
# Upload endpoint integrates with FastAPI dependency injection
@router.post("/", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = Form(default="default"),
    document_name: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service)
) -> UploadResponse:
    """Upload endpoint with dependency injection"""
    
    upload_service = UploadService(db, storage)
    result = await upload_service.process_upload(file, {
        'workspace_id': workspace_id,
        'document_name': document_name,
        'metadata': metadata
    })
    
    return UploadResponse.from_result(result)
```

### Event System Integration (Future)
```python
# Upload service can publish events for other components
class UploadEventPublisher:
    async def publish_upload_completed(self, document: Document):
        """Publish upload completion event"""
        event = {
            'event_type': 'document_uploaded',
            'document_id': str(document.id),
            'workspace_id': document.workspace_id,
            'mime_type': document.mime_type,
            'file_size': document.file_size,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Future: Publish to message queue (Celery/Redis)
        await self.publisher.publish('document.uploaded', event)

# Integration in upload service
async def process_upload(self, file: UploadFile) -> UploadResult:
    # ... upload processing ...
    
    # Publish event for downstream processing
    await self.event_publisher.publish_upload_completed(document)
    
    return result
```

### Monitoring Integration
```python
# Upload operations integrate with metrics collection
from app.monitoring.metrics import upload_metrics

async def process_upload_with_metrics(file: UploadFile) -> UploadResult:
    """Upload processing with metrics collection"""
    
    start_time = time.time()
    file_size_category = get_file_size_category(file.size)
    
    try:
        result = await process_upload(file)
        
        # Record success metrics
        duration = time.time() - start_time
        upload_metrics.record_success(
            file_type=file.content_type,
            size_category=file_size_category,
            duration=duration
        )
        
        return result
        
    except Exception as e:
        # Record failure metrics
        upload_metrics.record_failure(
            file_type=file.content_type,
            error_type=type(e).__name__
        )
        raise
```

---

## 12. TROUBLESHOOTING GUIDE

### Common Upload Issues

#### "File upload fails with 413 error"
```bash
# Check file size
ls -lh problematic_file.pdf

# Verify size limits
grep MAX_FILE_SIZE backend/app/core/config.py

# Test with smaller file
curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@small_test.pdf"

# Solution: Increase MAX_FILE_SIZE or compress file
export MAX_FILE_SIZE=52428800  # 50MB
```

#### "File type not allowed error"
```bash
# Check file extension and MIME type
file --mime-type suspicious_file.pdf

# Check if extension is in allowed list
grep ALLOWED_EXTENSIONS backend/app/core/config.py

# Test MIME detection
python3 -c "
import magic
print(magic.from_buffer(open('file.pdf', 'rb').read(), mime=True))
"

# Solution: Add file type to allowed list or convert file
```

#### "Database connection errors during upload"
```bash
# Check database connectivity
docker-compose exec postgres pg_isready -U querybox

# Check connection pool status
curl http://localhost:8000/health

# View database logs
docker-compose logs postgres | tail -50

# Solution: Restart database or check connection limits
docker-compose restart postgres
```

#### "Storage permission denied"
```bash
# Check storage directory permissions
ls -la storage/
ls -la storage/uploads/

# Fix permissions
chmod -R 755 storage/
chown -R $USER:$USER storage/

# Check Docker volume mounts
docker-compose exec backend ls -la /app/storage

# Solution: Fix filesystem permissions
sudo chown -R 1000:1000 storage/  # If using Docker
```

### Debug Commands

#### Upload Process Debugging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload --log-level debug

# Test upload with verbose output
curl -X POST http://localhost:8000/api/v1/upload/ \
  -F "file=@test.pdf" \
  -F "workspace_id=debug-test" \
  -v

# Check upload processing logs
tail -f logs/upload.log | grep -E "(upload_started|upload_completed|upload_failed)"
```

#### File Validation Debugging
```python
# Test file validation manually
python3 -c "
from app.services.file_processor import FileProcessor
import asyncio

async def test_file():
    with open('test.pdf', 'rb') as f:
        content = f.read()
    
    # Test MIME detection
    mime_type = FileProcessor.detect_mime_type(content)
    print(f'Detected MIME: {mime_type}')
    
    # Test validation
    is_valid = FileProcessor.validate_file_type('test.pdf', content)
    print(f'Valid: {is_valid}')

asyncio.run(test_file())
"
```

#### Storage Debugging
```bash
# Check storage operations
strace -e trace=file python3 -c "
import os
os.makedirs('storage/test/2024/11/doc-123', exist_ok=True)
with open('storage/test/2024/11/doc-123/test.txt', 'w') as f:
    f.write('test')
"

# Monitor disk space during uploads
watch -n 1 'df -h | grep storage'

# Check for orphaned temp files
find storage/temp -type f -mtime +1 -ls
```

### Database Verification Queries
```sql
-- Check recent uploads
SELECT 
    document_name,
    original_name,
    file_size,
    mime_type,
    status,
    created_at
FROM documents 
ORDER BY created_at DESC 
LIMIT 10;

-- Check for duplicate checksums
SELECT 
    checksum,
    COUNT(*) as count,
    array_agg(document_name) as documents
FROM documents 
GROUP BY checksum 
HAVING COUNT(*) > 1;

-- Check upload statistics
SELECT 
    DATE(created_at) as upload_date,
    COUNT(*) as uploads,
    SUM(file_size) as total_bytes,
    AVG(file_size) as avg_size
FROM documents 
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY upload_date;

-- Check failed uploads (if status tracking implemented)
SELECT 
    document_name,
    status,
    created_at,
    updated_at
FROM documents 
WHERE status = 'failed'
ORDER BY updated_at DESC;
```

### Performance Investigation
```bash
# Monitor upload performance
time curl -X POST http://localhost:8000/api/v1/upload/ \
  -F "file=@large_file.pdf"

# Check system resources during upload
top -p $(pgrep -f uvicorn)

# Monitor I/O during upload
iostat -x 1

# Profile upload endpoint
py-spy top --pid $(pgrep -f uvicorn) --duration 60

# Load test uploads
ab -n 50 -c 5 -p small_test.pdf \
   -T 'multipart/form-data; boundary=1234567890' \
   http://localhost:8000/api/v1/upload/
```

### Log Analysis
```bash
# Parse upload logs for errors
grep ERROR logs/upload.log | jq '.'

# Count uploads by status
grep "upload_completed\|upload_failed" logs/upload.log | \
  awk '{print $5}' | sort | uniq -c

# Find slow uploads (>5 seconds)
grep "upload_completed" logs/upload.log | \
  jq 'select(.duration_ms > 5000)' | \
  jq '{filename: .filename, duration: .duration_ms}'

# Monitor upload patterns
grep "upload_started" logs/upload.log | \
  jq -r '.timestamp' | \
  awk '{print substr($1,1,13)}' | \
  sort | uniq -c
```

---

## Summary

Step 3 successfully implements a comprehensive document upload system for QueryBox Core, providing:

1. **Robust File Upload Processing** with multipart form data handling and validation
2. **Security-First Design** with file type validation, MIME detection, and input sanitization  
3. **Atomic Operations** ensuring consistency between file storage and database records
4. **Organized Storage Structure** with workspace/date-based organization for scalability
5. **Comprehensive Error Handling** with automatic cleanup and transaction rollback
6. **Performance Optimization** with efficient file processing and concurrent upload support
7. **Monitoring and Observability** with detailed logging and metrics collection
8. **Future-Ready Architecture** with extension points for cloud storage and processing pipeline

This upload handler serves as the critical entry point for all documents into the QueryBox Core system, establishing the foundation for document processing, search, and retrieval functionality while maintaining high security, performance, and reliability standards.