# QueryBox Core: Additional Features Implemented
## Technical Implementation Documentation

---

## 1. FEATURE OVERVIEW

### What This Step Accomplishes
The Additional Features Implementation enhances QueryBox Core with critical enterprise-ready capabilities that transform the basic upload system into a production-grade document management platform:
- **SHA256 Checksum System**: Cryptographic integrity verification for all uploaded documents
- **Duplicate File Detection**: Intelligent deduplication preventing storage waste and redundancy
- **Comprehensive Error Handling**: Robust error management with detailed diagnostics and recovery
- **Enhanced Database Model**: Complete schema with all fields required for document lifecycle management
- **Atomic Operations**: Transaction-safe operations ensuring data consistency
- **Audit Trail**: Complete tracking of document operations for compliance and debugging

### Why This Step is Necessary
These additional features are essential because they:
- **Ensure Data Integrity**: SHA256 checksums provide cryptographic proof of file integrity
- **Optimize Storage Efficiency**: Duplicate detection prevents redundant storage usage
- **Improve System Reliability**: Comprehensive error handling ensures graceful failure management
- **Enable Enterprise Features**: Rich metadata supports advanced document management workflows
- **Support Compliance**: Audit trails and integrity checks meet regulatory requirements
- **Facilitate Debugging**: Detailed error information accelerates issue resolution

### Dependencies on Previous Steps
- **Step 1**: Database schema foundation and storage infrastructure
- **Step 2**: FastAPI application structure for error handling integration
- **Step 3**: Basic upload handler for checksum calculation integration
- **Step 4**: File validation layer for enhanced error reporting
- **External Dependencies**: hashlib (Python standard library) for SHA256 calculation

### What Future Steps Depend on This
- **Document Processing Pipeline**: Duplicate detection prevents reprocessing of identical files
- **Storage Management**: Checksum-based storage optimization and verification
- **Document Versioning**: Enhanced metadata supports version tracking and comparison
- **Search and Retrieval**: Rich metadata enables advanced search capabilities
- **Analytics and Reporting**: Comprehensive data model supports usage analytics
- **Backup and Recovery**: Checksums enable integrity verification during backup/restore

---

## 2. TECHNICAL IMPLEMENTATION

### Files Created/Modified

#### Core Checksum and Deduplication System
```
/backend/app/services/
├── checksum_service.py            # SHA256 checksum calculation and verification
├── deduplication_service.py       # Duplicate file detection and handling
└── integrity_service.py           # File integrity verification and monitoring

/backend/app/utils/
├── crypto_utils.py                # Cryptographic utilities and hash functions
├── file_comparison.py             # File comparison and similarity detection
└── metadata_extractor.py          # Enhanced metadata extraction
```

#### Enhanced Error Handling System
```
/backend/app/exceptions/
├── __init__.py                    # Exception module initialization
├── base_exceptions.py             # Base exception classes
├── upload_exceptions.py           # Upload-specific exceptions
├── validation_exceptions.py       # Validation error exceptions
├── storage_exceptions.py          # Storage operation exceptions
├── integrity_exceptions.py        # Checksum and integrity exceptions
└── deduplication_exceptions.py    # Duplicate detection exceptions

/backend/app/handlers/
├── error_handlers.py              # Global error handling middleware
├── exception_mappers.py           # Exception to HTTP response mapping
└── recovery_handlers.py           # Automatic error recovery logic
```

#### Enhanced Database Models
```
/backend/app/models/
├── document.py                    # Enhanced document model with checksums
├── checksum.py                    # Checksum verification records
├── duplicate_group.py             # Duplicate file grouping
├── error_log.py                   # Error tracking and logging
└── audit_trail.py                 # Document operation audit trail

/backend/app/schemas/
├── checksum.py                    # Checksum request/response schemas
├── deduplication.py               # Duplicate detection schemas
├── error_response.py              # Standardized error response schemas
└── audit.py                       # Audit trail schemas
```

#### Enhanced Upload Integration
```
/backend/app/api/v1/endpoints/
├── upload.py                      # Enhanced with checksum and deduplication
├── documents.py                   # Enhanced with duplicate management
├── integrity.py                   # Integrity verification endpoints
└── deduplication.py               # Duplicate management endpoints
```

### Key Classes and Functions

#### Checksum Service (`/backend/app/services/checksum_service.py`)
```python
class ChecksumService:
    """SHA256 checksum calculation and verification service"""
    
    def __init__(self, chunk_size: int = 65536):
        self.chunk_size = chunk_size
        self.algorithm = 'sha256'
    
    async def calculate_file_checksum(
        self, 
        file: UploadFile
    ) -> ChecksumResult:
        """
        Calculate SHA256 checksum for uploaded file
        
        Features:
        - Memory-efficient streaming calculation
        - Progress tracking for large files
        - Integrity verification
        - Performance optimization
        """
        
    async def verify_file_integrity(
        self,
        file_path: str,
        expected_checksum: str
    ) -> IntegrityResult:
        """Verify file integrity against expected checksum"""
        
    async def calculate_content_checksum(
        self,
        content: bytes
    ) -> str:
        """Calculate checksum for file content in memory"""
        
    def compare_checksums(
        self,
        checksum1: str,
        checksum2: str
    ) -> bool:
        """Secure checksum comparison"""
```

#### Deduplication Service (`/backend/app/services/deduplication_service.py`)
```python
class DeduplicationService:
    """Intelligent duplicate file detection and management"""
    
    def __init__(self, db: Session, storage: StorageService):
        self.db = db
        self.storage = storage
        self.checksum_service = ChecksumService()
    
    async def check_for_duplicates(
        self,
        checksum: str,
        workspace_id: str = None
    ) -> DuplicateCheckResult:
        """
        Check if file with given checksum already exists
        
        Features:
        - Workspace-scoped duplicate detection
        - Global duplicate detection
        - Metadata comparison
        - Storage optimization recommendations
        """
        
    async def handle_duplicate_upload(
        self,
        file: UploadFile,
        existing_document: Document,
        upload_context: dict
    ) -> DuplicateHandlingResult:
        """Handle upload of duplicate file"""
        
    async def create_duplicate_group(
        self,
        documents: List[Document]
    ) -> DuplicateGroup:
        """Group duplicate documents together"""
        
    async def get_duplicate_statistics(
        self,
        workspace_id: str = None
    ) -> DuplicateStats:
        """Get deduplication statistics and storage savings"""
```

#### Enhanced Error Handler (`/backend/app/handlers/error_handlers.py`)
```python
class ComprehensiveErrorHandler:
    """Comprehensive error handling with recovery capabilities"""
    
    def __init__(self, logger: Logger, metrics: MetricsCollector):
        self.logger = logger
        self.metrics = metrics
        self.recovery_strategies = self._load_recovery_strategies()
    
    async def handle_upload_error(
        self,
        error: Exception,
        context: UploadContext
    ) -> ErrorHandlingResult:
        """
        Handle upload errors with automatic recovery
        
        Features:
        - Error classification and routing
        - Automatic retry with backoff
        - Resource cleanup
        - Detailed error reporting
        - Recovery strategy execution
        """
        
    async def handle_validation_error(
        self,
        error: ValidationException,
        file_info: dict
    ) -> ValidationErrorResult:
        """Handle file validation errors"""
        
    async def handle_storage_error(
        self,
        error: StorageException,
        operation_context: dict
    ) -> StorageErrorResult:
        """Handle storage operation errors"""
        
    def log_error_with_context(
        self,
        error: Exception,
        context: dict,
        user_info: dict = None
    ):
        """Log error with comprehensive context information"""
```

### Enhanced Database Schema

#### Enhanced Documents Table
```sql
-- Enhanced documents table with checksum and metadata
ALTER TABLE documents ADD COLUMN IF NOT EXISTS
    -- Checksum and integrity
    checksum VARCHAR(64) NOT NULL UNIQUE,
    checksum_algorithm VARCHAR(20) DEFAULT 'sha256',
    integrity_verified BOOLEAN DEFAULT FALSE,
    last_integrity_check TIMESTAMP,
    
    -- Deduplication
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_group_id UUID REFERENCES duplicate_groups(id),
    original_document_id UUID REFERENCES documents(id),
    duplicate_count INTEGER DEFAULT 0,
    
    -- Enhanced metadata
    file_extension VARCHAR(10) NOT NULL,
    alternate_name VARCHAR(255),
    description TEXT,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    
    -- Processing tracking
    processing_stage VARCHAR(50) DEFAULT 'uploaded',
    processing_progress INTEGER DEFAULT 0,
    last_processed_at TIMESTAMP,
    processing_errors JSONB DEFAULT '[]',
    
    -- Access tracking
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP,
    last_accessed_by VARCHAR(255),
    
    -- Storage optimization
    storage_tier VARCHAR(20) DEFAULT 'standard',
    compression_ratio DECIMAL(5,3),
    storage_cost_cents INTEGER DEFAULT 0;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_checksum ON documents(checksum);
CREATE INDEX IF NOT EXISTS idx_documents_duplicate_group ON documents(duplicate_group_id);
CREATE INDEX IF NOT EXISTS idx_documents_processing_stage ON documents(processing_stage);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN(metadata);
```

#### Duplicate Groups Table
```sql
-- Duplicate file grouping
CREATE TABLE IF NOT EXISTS duplicate_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Group metadata
    checksum VARCHAR(64) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    
    -- Group statistics
    document_count INTEGER DEFAULT 1,
    storage_saved_bytes BIGINT DEFAULT 0,
    first_uploaded_at TIMESTAMP NOT NULL,
    last_duplicate_at TIMESTAMP,
    
    -- Group management
    canonical_document_id UUID REFERENCES documents(id),
    group_status VARCHAR(20) DEFAULT 'active',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_duplicate_groups_checksum ON duplicate_groups(checksum);
CREATE INDEX idx_duplicate_groups_canonical ON duplicate_groups(canonical_document_id);
```

#### Error Logs Table
```sql
-- Comprehensive error logging
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Error identification
    error_code VARCHAR(50) NOT NULL,
    error_type VARCHAR(50) NOT NULL,
    error_category VARCHAR(30) NOT NULL, -- upload|validation|storage|processing
    
    -- Error context
    operation_id UUID,
    document_id UUID REFERENCES documents(id),
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    
    -- Error details
    error_message TEXT NOT NULL,
    error_details JSONB DEFAULT '{}',
    stack_trace TEXT,
    
    -- Request context
    request_path VARCHAR(500),
    request_method VARCHAR(10),
    request_headers JSONB,
    request_body_hash VARCHAR(64),
    
    -- System context
    hostname VARCHAR(255),
    process_id INTEGER,
    thread_id VARCHAR(50),
    memory_usage_mb INTEGER,
    cpu_usage_percent DECIMAL(5,2),
    
    -- Resolution tracking
    resolved BOOLEAN DEFAULT FALSE,
    resolution_action VARCHAR(100),
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(255),
    
    -- Timestamps
    occurred_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for error analysis
CREATE INDEX idx_error_logs_error_code ON error_logs(error_code);
CREATE INDEX idx_error_logs_error_type ON error_logs(error_type);
CREATE INDEX idx_error_logs_occurred_at ON error_logs(occurred_at);
CREATE INDEX idx_error_logs_document_id ON error_logs(document_id);
CREATE INDEX idx_error_logs_resolved ON error_logs(resolved);
```

### Enhanced API Endpoints

#### Enhanced Upload Endpoint
```python
@router.post("/", response_model=EnhancedUploadResponse)
async def upload_document_enhanced(
    file: UploadFile = File(...),
    workspace_id: str = Form(default="default"),
    document_name: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    check_duplicates: bool = Form(True),
    db: Session = Depends(get_db)
) -> EnhancedUploadResponse:
    """
    Enhanced upload with checksum calculation and duplicate detection
    
    Features:
    - Automatic SHA256 checksum calculation
    - Duplicate detection and handling
    - Enhanced metadata storage
    - Comprehensive error handling
    - Transaction-safe operations
    """
```

#### Duplicate Management Endpoints
```http
# Check for duplicates
POST /api/v1/duplicates/check
Request: {"checksum": "sha256_hash", "workspace_id": "uuid"}
Response: {"has_duplicates": true, "duplicate_count": 3, "documents": [...]}

# Get duplicate groups
GET /api/v1/duplicates/groups?workspace_id=uuid
Response: {"groups": [...], "total_groups": 5, "storage_saved_mb": 125.5}

# Resolve duplicate group
POST /api/v1/duplicates/groups/{group_id}/resolve
Request: {"action": "keep_canonical", "canonical_id": "uuid"}
Response: {"resolved": true, "action_taken": "...", "storage_freed_mb": 25.5}

# Get deduplication statistics
GET /api/v1/duplicates/stats?workspace_id=uuid
Response: {"duplicate_files": 45, "storage_saved_gb": 2.3, "efficiency": 0.15}
```

#### Integrity Verification Endpoints
```http
# Verify file integrity
POST /api/v1/integrity/verify/{document_id}
Response: {"valid": true, "checksum_match": true, "file_exists": true}

# Batch integrity check
POST /api/v1/integrity/verify/batch
Request: {"document_ids": ["uuid1", "uuid2", "..."]}
Response: {"results": [...], "valid_count": 8, "invalid_count": 1}

# Recalculate checksums
POST /api/v1/integrity/recalculate/{document_id}
Response: {"recalculated": true, "old_checksum": "...", "new_checksum": "..."}
```

### Enhanced Response Schemas

#### Enhanced Upload Response
```python
class EnhancedUploadResponse(BaseModel):
    """Enhanced upload response with checksum and duplicate information"""
    
    # Basic upload info
    document_id: UUID
    filename: str
    original_name: str
    size: int
    mime_type: str
    
    # Checksum information
    checksum: str
    checksum_algorithm: str
    integrity_verified: bool
    
    # Duplicate information
    is_duplicate: bool
    duplicate_group_id: Optional[UUID]
    original_document_id: Optional[UUID]
    duplicate_count: int
    storage_saved: bool
    
    # Enhanced metadata
    tags: List[str]
    metadata: Dict[str, Any]
    processing_stage: str
    
    # Timestamps
    upload_time: datetime
    last_modified: datetime
    
    # Storage information
    storage_path: str
    storage_tier: str
    workspace_id: str
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }
```

#### Comprehensive Error Response
```python
class ComprehensiveErrorResponse(BaseModel):
    """Comprehensive error response with context and recovery information"""
    
    # Error identification
    error_id: UUID
    error_code: str
    error_type: str
    error_category: str
    
    # Error message
    message: str
    detail: str
    user_message: str
    
    # Error context
    operation_id: Optional[UUID]
    document_id: Optional[UUID]
    file_info: Optional[Dict[str, Any]]
    
    # Validation errors (if applicable)
    validation_errors: List[ValidationError] = []
    
    # Recovery information
    recoverable: bool
    retry_after_seconds: Optional[int]
    recovery_suggestions: List[str]
    
    # Support information
    support_reference: str
    documentation_links: List[str]
    
    # Timestamps
    occurred_at: datetime
    
    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat()
        }
```

---

## 3. DATA FLOW

### Enhanced Upload Flow with Checksum and Deduplication
```
1. File Upload Request → FastAPI receives multipart form data
2. Pre-processing Setup → Extract metadata and prepare upload context
3. File Validation → Size, type, and security validation (Step 4)
4. Checksum Calculation → Stream-based SHA256 calculation
5. Duplicate Detection → Database lookup by checksum
6. Duplicate Handling → Route to duplicate or new file processing
7. Storage Decision → Determine storage strategy based on duplication
8. Database Transaction → Atomic record creation with full metadata
9. Post-processing → Update duplicate groups and statistics
10. Response Generation → Enhanced response with checksum and duplicate info
11. Audit Logging → Record operation for compliance and debugging
```

### Detailed Processing Steps

#### Step 4: Checksum Calculation Flow
```python
# Memory-efficient checksum calculation
async def calculate_file_checksum(file: UploadFile) -> ChecksumResult:
    hash_sha256 = hashlib.sha256()
    total_size = 0
    chunk_size = 65536  # 64KB chunks
    
    # Reset file position
    await file.seek(0)
    
    # Stream-based calculation
    while chunk := await file.read(chunk_size):
        hash_sha256.update(chunk)
        total_size += len(chunk)
        
        # Progress tracking for large files
        if total_size % (10 * 1024 * 1024) == 0:  # Every 10MB
            progress = (total_size / file.size) * 100 if file.size else 0
            logger.debug(f"Checksum calculation progress: {progress:.1f}%")
    
    # Reset file position for further processing
    await file.seek(0)
    
    checksum = hash_sha256.hexdigest()
    
    return ChecksumResult(
        checksum=checksum,
        algorithm='sha256',
        file_size=total_size,
        calculation_time_ms=(time.time() - start_time) * 1000
    )
```

#### Step 5: Duplicate Detection Flow
```python
# Intelligent duplicate detection
async def check_for_duplicates(
    checksum: str,
    workspace_id: str,
    file_size: int
) -> DuplicateCheckResult:
    
    # Check workspace-scoped duplicates first
    workspace_duplicate = db.query(Document).filter(
        Document.checksum == checksum,
        Document.workspace_id == workspace_id,
        Document.is_deleted == False
    ).first()
    
    if workspace_duplicate:
        return DuplicateCheckResult(
            is_duplicate=True,
            scope='workspace',
            existing_document=workspace_duplicate,
            storage_saved=True
        )
    
    # Check global duplicates
    global_duplicate = db.query(Document).filter(
        Document.checksum == checksum,
        Document.is_deleted == False
    ).first()
    
    if global_duplicate:
        return DuplicateCheckResult(
            is_duplicate=True,
            scope='global',
            existing_document=global_duplicate,
            storage_saved=False,  # Different workspace, copy needed
            cross_workspace=True
        )
    
    return DuplicateCheckResult(
        is_duplicate=False,
        scope=None,
        storage_saved=False
    )
```

#### Step 6: Duplicate Handling Decision Tree
```python
async def handle_duplicate_file(
    file: UploadFile,
    duplicate_result: DuplicateCheckResult,
    upload_context: dict
) -> DuplicateHandlingResult:
    
    existing_doc = duplicate_result.existing_document
    
    if duplicate_result.scope == 'workspace':
        # Same workspace duplicate - return existing document
        await update_duplicate_statistics(existing_doc)
        
        return DuplicateHandlingResult(
            action='reference_existing',
            document_id=existing_doc.id,
            storage_saved=True,
            message="File already exists in workspace"
        )
    
    elif duplicate_result.scope == 'global':
        # Cross-workspace duplicate - create new record, reference storage
        new_document = await create_duplicate_document_record(
            file,
            existing_doc,
            upload_context
        )
        
        return DuplicateHandlingResult(
            action='create_reference',
            document_id=new_document.id,
            original_document_id=existing_doc.id,
            storage_saved=True,
            message="File exists globally, created workspace reference"
        )
    
    else:
        # New file - proceed with normal upload
        return DuplicateHandlingResult(
            action='upload_new',
            storage_saved=False,
            message="New file, proceeding with upload"
        )
```

#### Step 8: Enhanced Database Transaction
```python
# Atomic transaction with full metadata
async def create_enhanced_document_record(
    file_metadata: dict,
    checksum_result: ChecksumResult,
    duplicate_info: DuplicateHandlingResult,
    upload_context: dict
) -> Document:
    
    try:
        with db.begin():
            # Create main document record
            document = Document(
                id=uuid.uuid4(),
                document_name=file_metadata['document_name'],
                original_name=file_metadata['original_name'],
                alternate_name=file_metadata.get('alternate_name'),
                file_extension=file_metadata['file_extension'],
                mime_type=file_metadata['mime_type'],
                file_size=file_metadata['file_size'],
                
                # Checksum information
                checksum=checksum_result.checksum,
                checksum_algorithm=checksum_result.algorithm,
                integrity_verified=True,
                
                # Duplicate information
                is_duplicate=duplicate_info.is_duplicate,
                duplicate_group_id=duplicate_info.duplicate_group_id,
                original_document_id=duplicate_info.original_document_id,
                
                # Enhanced metadata
                description=file_metadata.get('description'),
                tags=file_metadata.get('tags', []),
                metadata=file_metadata.get('metadata', {}),
                
                # Storage information
                storage_provider='local',
                storage_path=file_metadata['storage_path'],
                storage_tier='standard',
                
                # Processing status
                processing_stage='uploaded',
                processing_progress=0,
                
                # Workspace and user info
                workspace_id=upload_context['workspace_id'],
                uploaded_by=upload_context.get('user_id'),
                
                # Timestamps
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(document)
            
            # Update duplicate group if applicable
            if duplicate_info.duplicate_group_id:
                await update_duplicate_group(duplicate_info.duplicate_group_id, document)
            
            # Create audit trail entry
            audit_entry = AuditTrail(
                operation='document_upload',
                document_id=document.id,
                operation_details={
                    'checksum': checksum_result.checksum,
                    'is_duplicate': duplicate_info.is_duplicate,
                    'file_size': file_metadata['file_size'],
                    'mime_type': file_metadata['mime_type']
                },
                performed_by=upload_context.get('user_id'),
                performed_at=datetime.utcnow()
            )
            
            db.add(audit_entry)
            db.commit()
            
            return document
            
    except Exception as e:
        db.rollback()
        logger.error(f"Database transaction failed: {str(e)}")
        raise StorageException(f"Failed to create document record: {str(e)}")
```

### Error Handling Flow
```
Error Occurrence → Error Classification → Context Collection → Recovery Strategy → Error Logging → User Response
```

#### Error Classification and Recovery
```python
async def classify_and_handle_error(
    error: Exception,
    context: dict
) -> ErrorHandlingResult:
    
    error_class = type(error).__name__
    
    # Transient errors - retry with backoff
    if error_class in ['ConnectionError', 'TimeoutError', 'TemporaryFailure']:
        return ErrorHandlingResult(
            action='retry',
            retry_after_seconds=calculate_backoff(context.get('retry_count', 0)),
            recoverable=True,
            user_message="Temporary issue, retrying automatically"
        )
    
    # Validation errors - return to user
    elif error_class in ['ValidationException', 'FileSizeError', 'FileTypeError']:
        return ErrorHandlingResult(
            action='reject',
            recoverable=False,
            user_message=str(error),
            suggestions=get_validation_suggestions(error)
        )
    
    # Storage errors - attempt recovery
    elif error_class in ['StorageException', 'DiskFullError']:
        cleanup_result = await attempt_storage_cleanup()
        return ErrorHandlingResult(
            action='retry_after_cleanup' if cleanup_result.success else 'reject',
            recoverable=cleanup_result.success,
            user_message="Storage issue detected, attempting recovery"
        )
    
    # Unknown errors - safe rejection
    else:
        return ErrorHandlingResult(
            action='reject',
            recoverable=False,
            user_message="An unexpected error occurred",
            requires_investigation=True
        )
```

---

## 4. VALIDATIONS & CONSTRAINTS

### Checksum Validation Constraints
```python
class ChecksumConstraints:
    # Supported algorithms
    SUPPORTED_ALGORITHMS = ['sha256', 'sha1', 'md5']
    DEFAULT_ALGORITHM = 'sha256'
    
    # Checksum format validation
    CHECKSUM_PATTERNS = {
        'sha256': r'^[a-fA-F0-9]{64}$',
        'sha1': r'^[a-fA-F0-9]{40}$',
        'md5': r'^[a-fA-F0-9]{32}$'
    }
    
    # Performance constraints
    MAX_CHECKSUM_CALCULATION_TIME = 300  # 5 minutes
    CHECKSUM_CHUNK_SIZE = 65536  # 64KB
    PROGRESS_REPORT_INTERVAL = 10 * 1024 * 1024  # 10MB
    
    # Integrity validation
    INTEGRITY_CHECK_REQUIRED = True
    INTEGRITY_CHECK_INTERVAL_DAYS = 30
    INTEGRITY_FAILURE_THRESHOLD = 3  # Max failed checks before quarantine
```

### Deduplication Business Rules
```python
class DeduplicationRules:
    # Duplicate detection scope
    WORKSPACE_SCOPED_DETECTION = True
    GLOBAL_DUPLICATE_DETECTION = True
    CROSS_WORKSPACE_REFERENCES = True
    
    # Storage optimization
    ENABLE_STORAGE_DEDUPLICATION = True
    DEDUPE_DIFFERENT_WORKSPACES = True
    PRESERVE_WORKSPACE_METADATA = True
    
    # Duplicate group management
    MAX_DUPLICATES_PER_GROUP = 1000
    AUTO_RESOLVE_IDENTICAL_METADATA = False
    CANONICAL_DOCUMENT_SELECTION = 'first_uploaded'  # first_uploaded|largest_metadata|manual
    
    # Duplicate handling policies
    DUPLICATE_UPLOAD_ACTION = 'reference_existing'  # reference_existing|create_copy|reject
    STORAGE_SAVINGS_TRACKING = True
    DUPLICATE_NOTIFICATION_ENABLED = True
```

### Enhanced Metadata Constraints
```python
class MetadataConstraints:
    # Field length limits
    MAX_DOCUMENT_NAME_LENGTH = 255
    MAX_ALTERNATE_NAME_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 2000
    MAX_TAG_LENGTH = 50
    MAX_TAGS_COUNT = 20
    
    # Metadata size limits
    MAX_METADATA_JSON_SIZE = 10240  # 10KB
    MAX_METADATA_NESTING_DEPTH = 5
    
    # Tag validation
    TAG_PATTERN = r'^[a-zA-Z0-9_-]+$'
    RESERVED_TAGS = ['system', 'internal', 'admin']
    
    # Processing stage validation
    VALID_PROCESSING_STAGES = [
        'uploaded', 'validating', 'processing', 'chunking',
        'embedding', 'indexed', 'completed', 'failed'
    ]
    
    # Storage tier validation
    VALID_STORAGE_TIERS = ['hot', 'standard', 'cold', 'archive']
```

### Error Handling Constraints
```python
class ErrorHandlingConstraints:
    # Retry policies
    MAX_RETRY_ATTEMPTS = 3
    RETRY_BACKOFF_MULTIPLIER = 2
    MAX_RETRY_DELAY_SECONDS = 300
    
    # Error tracking limits
    MAX_ERROR_MESSAGE_LENGTH = 2000
    MAX_STACK_TRACE_LENGTH = 8000
    MAX_ERROR_DETAILS_SIZE = 5120  # 5KB JSON
    
    # Error resolution timeouts
    AUTO_RESOLVE_TIMEOUT_HOURS = 24
    MANUAL_REVIEW_TIMEOUT_DAYS = 7
    ERROR_LOG_RETENTION_DAYS = 90
    
    # Error rate limits
    MAX_ERRORS_PER_USER_PER_HOUR = 100
    MAX_ERRORS_PER_IP_PER_HOUR = 200
    ERROR_RATE_CIRCUIT_BREAKER_THRESHOLD = 0.5  # 50% error rate
```

---

## 5. CONFIGURATION

### Environment Variables
```bash
# Checksum Configuration
CHECKSUM_ALGORITHM=sha256                    # Default algorithm for new files
ENABLE_INTEGRITY_VERIFICATION=true          # Enable integrity checks
INTEGRITY_CHECK_INTERVAL_DAYS=30            # Days between integrity checks
CHECKSUM_CHUNK_SIZE=65536                   # Chunk size for calculation (64KB)
CHECKSUM_CALCULATION_TIMEOUT=300            # Max time for checksum calculation

# Deduplication Configuration
ENABLE_DEDUPLICATION=true                   # Enable duplicate detection
WORKSPACE_SCOPED_DEDUPLICATION=true        # Check duplicates within workspace
GLOBAL_DEDUPLICATION=true                  # Check duplicates across workspaces
STORAGE_DEDUPLICATION=true                 # Enable storage-level deduplication
DUPLICATE_NOTIFICATION=true                # Notify users of duplicates

# Enhanced Metadata Configuration
MAX_TAGS_PER_DOCUMENT=20                   # Maximum tags per document
MAX_METADATA_SIZE_KB=10                    # Maximum metadata JSON size
ENABLE_METADATA_INDEXING=true              # Index metadata for search
METADATA_VALIDATION_STRICT=true           # Strict metadata validation

# Error Handling Configuration
ENABLE_COMPREHENSIVE_ERROR_LOGGING=true    # Enable detailed error logging
ERROR_LOG_RETENTION_DAYS=90                # Keep error logs for 90 days
MAX_RETRY_ATTEMPTS=3                       # Maximum retry attempts
RETRY_BACKOFF_MULTIPLIER=2                 # Exponential backoff multiplier
AUTO_ERROR_RESOLUTION=true                 # Enable automatic error resolution

# Performance Configuration
ASYNC_CHECKSUM_CALCULATION=true            # Calculate checksums asynchronously
BATCH_DUPLICATE_CHECKING=true              # Batch duplicate checks
DUPLICATE_CACHE_SIZE=10000                 # Cache size for duplicate checks
INTEGRITY_CHECK_BATCH_SIZE=100             # Batch size for integrity checks

# Database Configuration
ENABLE_AUDIT_TRAIL=true                    # Enable audit trail logging
AUDIT_TRAIL_RETENTION_DAYS=365             # Keep audit trail for 1 year
DATABASE_QUERY_TIMEOUT=30                  # Database query timeout in seconds
CONNECTION_POOL_SIZE=20                    # Database connection pool size
```

### Default Configuration Values
```python
class EnhancedConfiguration:
    # Checksum settings
    DEFAULT_CHECKSUM_ALGORITHM = 'sha256'
    CHECKSUM_ALGORITHMS = ['sha256', 'sha1', 'md5']
    CHECKSUM_CHUNK_SIZE = 65536  # 64KB
    INTEGRITY_CHECK_INTERVAL = timedelta(days=30)
    
    # Deduplication settings
    ENABLE_DEDUPLICATION = True
    DUPLICATE_DETECTION_SCOPE = 'both'  # workspace|global|both
    STORAGE_DEDUPLICATION = True
    CANONICAL_SELECTION_STRATEGY = 'first_uploaded'
    
    # Error handling settings
    MAX_RETRY_ATTEMPTS = 3
    RETRY_BASE_DELAY = 1.0  # seconds
    RETRY_MAX_DELAY = 300.0  # seconds
    ERROR_LOG_LEVEL = 'INFO'
    
    # Metadata settings
    MAX_DOCUMENT_NAME_LENGTH = 255
    MAX_TAGS_COUNT = 20
    MAX_METADATA_SIZE = 10240  # 10KB
    METADATA_INDEXING = True
    
    # Performance settings
    ASYNC_PROCESSING = True
    BATCH_SIZE = 100
    CACHE_SIZE = 10000
    QUERY_TIMEOUT = 30.0
```

### Enhanced Directory Structure
```
/storage/
├── uploads/                         # Organized by workspace and date
│   ├── {workspace_id}/
│   │   ├── 2024/
│   │   │   ├── 11/
│   │   │   │   ├── {document_id}/
│   │   │   │   │   ├── document.pdf
│   │   │   │   │   └── checksums/
│   │   │   │   │       ├── sha256.txt
│   │   │   │   │       └── integrity.log
│   │   │   │   └── duplicates/
│   │   │   │       └── references.json
│   │   │   └── 12/
│   │   └── 2025/
│   └── global_deduplication/
│       ├── by_checksum/
│       │   ├── ab/cd/ef.../
│       │   │   └── canonical_file.pdf
│       │   └── references.json
│       └── integrity_reports/
├── temp/                           # Temporary processing
│   ├── checksums/                 # Checksum calculation temp files
│   ├── duplicates/                # Duplicate detection temp data
│   └── error_recovery/            # Error recovery temp files
├── backup/                        # Backup and recovery
│   ├── checksums/                 # Checksum verification backups
│   └── integrity/                 # Integrity check results
└── logs/                          # Enhanced logging
    ├── checksums/                 # Checksum operation logs
    ├── duplicates/                # Deduplication logs
    ├── errors/                    # Comprehensive error logs
    └── audit/                     # Audit trail logs
```

### Docker Service Configuration
```yaml
services:
  backend:
    environment:
      # Enhanced configuration
      - CHECKSUM_ALGORITHM=sha256
      - ENABLE_DEDUPLICATION=true
      - COMPREHENSIVE_ERROR_LOGGING=true
      - METADATA_INDEXING=true
    volumes:
      # Enhanced storage structure
      - ./storage:/app/storage
      - ./logs:/app/logs
      - ./config/enhanced_config.json:/app/config/enhanced_config.json:ro
    
  # Enhanced monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: querybox-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./monitoring/rules:/etc/prometheus/rules:ro
    networks:
      - querybox-network
  
  # Error tracking service
  sentry:
    image: sentry:latest
    container_name: querybox-sentry
    environment:
      - SENTRY_SECRET_KEY=${SENTRY_SECRET_KEY}
    ports:
      - "9000:9000"
    networks:
      - querybox-network
```

---

## 6. ERROR HANDLING

### Comprehensive Error Classification
```python
# Enhanced error taxonomy
class ErrorTaxonomy:
    # Error categories
    CATEGORIES = {
        'validation': 'Input validation failures',
        'authentication': 'Authentication and authorization failures',
        'upload': 'File upload process failures',
        'storage': 'Storage operation failures',
        'checksum': 'Checksum calculation or verification failures',
        'deduplication': 'Duplicate detection process failures',
        'database': 'Database operation failures',
        'network': 'Network communication failures',
        'system': 'System resource failures',
        'business_logic': 'Business rule violations'
    }
    
    # Error severities
    SEVERITIES = {
        'critical': 'System-critical errors requiring immediate attention',
        'high': 'High-impact errors affecting user operations',
        'medium': 'Medium-impact errors with workarounds available',
        'low': 'Low-impact errors with minimal user disruption',
        'info': 'Informational errors for logging purposes'
    }
    
    # Recovery strategies
    RECOVERY_STRATEGIES = {
        'retry': 'Automatic retry with exponential backoff',
        'failover': 'Switch to alternative service or resource',
        'degrade': 'Graceful degradation of functionality',
        'circuit_break': 'Temporarily disable failing component',
        'manual': 'Requires manual intervention',
        'none': 'No recovery possible, log and continue'
    }
```

### Specific Error Scenarios

#### Checksum Calculation Errors
```python
class ChecksumCalculationError(Exception):
    """Checksum calculation failed"""
    
    def __init__(self, filename: str, algorithm: str, stage: str, original_error: str):
        self.filename = filename
        self.algorithm = algorithm
        self.stage = stage
        self.original_error = original_error
        
        message = f"Checksum calculation failed for {filename} using {algorithm} at stage {stage}: {original_error}"
        super().__init__(message)

# Error handling
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((IOError, OSError))
)
async def calculate_checksum_with_recovery(file: UploadFile) -> ChecksumResult:
    """Calculate checksum with automatic retry and recovery"""
    
    try:
        return await checksum_service.calculate_file_checksum(file)
    
    except MemoryError as e:
        # Handle large file memory issues
        logger.warning(f"Memory error during checksum calculation, using streaming approach")
        return await checksum_service.calculate_streaming_checksum(file)
    
    except TimeoutError as e:
        # Handle timeout for very large files
        logger.warning(f"Checksum calculation timeout, file too large: {file.filename}")
        raise ChecksumCalculationError(
            filename=file.filename,
            algorithm='sha256',
            stage='calculation',
            original_error='Timeout exceeded'
        )
    
    except Exception as e:
        # Log and re-raise unexpected errors
        logger.error(f"Unexpected checksum calculation error: {str(e)}", exc_info=True)
        raise ChecksumCalculationError(
            filename=file.filename,
            algorithm='sha256',
            stage='unknown',
            original_error=str(e)
        )
```

#### Deduplication Errors
```python
class DeduplicationError(Exception):
    """Duplicate detection process failed"""
    
    def __init__(self, checksum: str, operation: str, details: dict):
        self.checksum = checksum
        self.operation = operation
        self.details = details
        
        message = f"Deduplication failed for checksum {checksum[:16]}... during {operation}"
        super().__init__(message)

async def handle_deduplication_error(
    error: DeduplicationError,
    context: dict
) -> DeduplicationErrorResult:
    """Handle deduplication errors with fallback strategies"""
    
    if error.operation == 'database_lookup':
        # Database query failed - proceed without deduplication
        logger.warning(f"Database lookup failed, proceeding without deduplication check")
        return DeduplicationErrorResult(
            action='proceed_without_dedup',
            fallback_used=True,
            error_logged=True
        )
    
    elif error.operation == 'duplicate_group_creation':
        # Group creation failed - create individual record
        logger.warning(f"Duplicate group creation failed, creating individual record")
        return DeduplicationErrorResult(
            action='create_individual_record',
            fallback_used=True,
            error_logged=True
        )
    
    else:
        # Unknown deduplication error - log and proceed
        logger.error(f"Unknown deduplication error: {str(error)}", exc_info=True)
        return DeduplicationErrorResult(
            action='proceed_with_logging',
            fallback_used=False,
            error_logged=True,
            requires_investigation=True
        )
```

#### Database Transaction Errors
```python
async def handle_database_transaction_error(
    error: Exception,
    operation_context: dict
) -> TransactionErrorResult:
    """Handle database transaction errors with rollback and recovery"""
    
    try:
        # Attempt rollback
        if 'transaction' in operation_context:
            await operation_context['transaction'].rollback()
            logger.info("Database transaction rolled back successfully")
        
        # Classify error type
        if 'duplicate key' in str(error).lower():
            return TransactionErrorResult(
                action='duplicate_key_conflict',
                recoverable=True,
                suggested_retry_delay=1.0,
                user_message="Document already exists with this checksum"
            )
        
        elif 'connection' in str(error).lower():
            return TransactionErrorResult(
                action='connection_failure',
                recoverable=True,
                suggested_retry_delay=5.0,
                user_message="Database connection issue, please retry"
            )
        
        elif 'timeout' in str(error).lower():
            return TransactionErrorResult(
                action='query_timeout',
                recoverable=True,
                suggested_retry_delay=10.0,
                user_message="Database operation timed out, please retry"
            )
        
        else:
            return TransactionErrorResult(
                action='unknown_database_error',
                recoverable=False,
                user_message="Database operation failed",
                requires_investigation=True
            )
    
    except Exception as rollback_error:
        logger.error(f"Rollback failed: {str(rollback_error)}", exc_info=True)
        return TransactionErrorResult(
            action='rollback_failed',
            recoverable=False,
            user_message="Database operation failed critically",
            requires_immediate_attention=True
        )
```

### Error Recovery Strategies
```python
class ErrorRecoveryManager:
    """Manages error recovery strategies and automatic resolution"""
    
    def __init__(self):
        self.recovery_strategies = {
            'transient_network': self._handle_transient_network_error,
            'storage_full': self._handle_storage_full_error,
            'database_connection': self._handle_database_connection_error,
            'checksum_mismatch': self._handle_checksum_mismatch_error,
            'duplicate_conflict': self._handle_duplicate_conflict_error
        }
    
    async def attempt_recovery(
        self,
        error: Exception,
        context: dict,
        max_attempts: int = 3
    ) -> RecoveryResult:
        """Attempt automatic error recovery"""
        
        error_type = self._classify_error(error)
        recovery_strategy = self.recovery_strategies.get(error_type)
        
        if not recovery_strategy:
            return RecoveryResult(
                success=False,
                action='no_recovery_strategy',
                message="No recovery strategy available for this error type"
            )
        
        attempt = 0
        while attempt < max_attempts:
            try:
                recovery_result = await recovery_strategy(error, context, attempt)
                
                if recovery_result.success:
                    logger.info(f"Error recovery successful after {attempt + 1} attempts")
                    return recovery_result
                
                attempt += 1
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as recovery_error:
                logger.error(f"Recovery attempt {attempt + 1} failed: {str(recovery_error)}")
                attempt += 1
        
        return RecoveryResult(
            success=False,
            action='recovery_exhausted',
            message=f"Recovery failed after {max_attempts} attempts"
        )
    
    async def _handle_storage_full_error(
        self,
        error: Exception,
        context: dict,
        attempt: int
    ) -> RecoveryResult:
        """Handle storage full errors by cleaning up temporary files"""
        
        # Clean up temporary files
        cleanup_result = await cleanup_temporary_files()
        
        if cleanup_result.space_freed_mb > 100:  # 100MB freed
            return RecoveryResult(
                success=True,
                action='storage_cleanup',
                message=f"Freed {cleanup_result.space_freed_mb}MB of storage space"
            )
        
        # Try compressing old files
        compression_result = await compress_old_files()
        
        if compression_result.space_saved_mb > 50:  # 50MB saved
            return RecoveryResult(
                success=True,
                action='storage_compression',
                message=f"Saved {compression_result.space_saved_mb}MB through compression"
            )
        
        return RecoveryResult(
            success=False,
            action='insufficient_cleanup',
            message="Could not free sufficient storage space"
        )
```

### Comprehensive Error Logging
```python
class ComprehensiveErrorLogger:
    """Advanced error logging with context and analysis"""
    
    async def log_error_with_full_context(
        self,
        error: Exception,
        operation_context: dict,
        user_context: dict = None,
        system_context: dict = None
    ):
        """Log error with comprehensive context information"""
        
        error_id = uuid.uuid4()
        timestamp = datetime.utcnow()
        
        # Collect system context
        system_info = system_context or await self._collect_system_context()
        
        # Create comprehensive error record
        error_record = {
            'error_id': str(error_id),
            'timestamp': timestamp.isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_category': self._categorize_error(error),
            'severity': self._assess_severity(error),
            
            # Operation context
            'operation': operation_context.get('operation'),
            'operation_id': operation_context.get('operation_id'),
            'document_id': operation_context.get('document_id'),
            'file_info': operation_context.get('file_info', {}),
            
            # User context
            'user_id': user_context.get('user_id') if user_context else None,
            'session_id': user_context.get('session_id') if user_context else None,
            'ip_address': user_context.get('ip_address') if user_context else None,
            'user_agent': user_context.get('user_agent') if user_context else None,
            
            # System context
            'hostname': system_info.get('hostname'),
            'process_id': system_info.get('process_id'),
            'memory_usage_mb': system_info.get('memory_usage_mb'),
            'cpu_usage_percent': system_info.get('cpu_usage_percent'),
            'disk_usage_percent': system_info.get('disk_usage_percent'),
            
            # Stack trace (for debugging)
            'stack_trace': traceback.format_exc() if hasattr(error, '__traceback__') else None,
            
            # Recovery information
            'recovery_attempted': False,
            'recovery_successful': False,
            'recovery_strategy': None
        }
        
        # Store in database
        await self._store_error_record(error_record)
        
        # Log to application logger
        logger.error(
            f"Error {error_id}: {error_record['error_message']}",
            extra=error_record
        )
        
        # Send to external monitoring if critical
        if error_record['severity'] in ['critical', 'high']:
            await self._send_to_external_monitoring(error_record)
        
        return error_id
```

---

## 7. TESTING CHECKLIST

### Checksum Functionality Testing
```bash
# Test checksum calculation
curl -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@test.pdf" \
    -F "workspace_id=test-checksum"

# Verify checksum in response
# Expected: 64-character SHA256 hash

# Test checksum verification
document_id=$(curl -s -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@test.pdf" | jq -r '.document_id')

curl -X POST http://localhost:8000/api/v1/integrity/verify/$document_id
# Expected: {"valid": true, "checksum_match": true}

# Test large file checksum calculation
dd if=/dev/zero of=large_test.pdf bs=1024 count=25600  # 25MB
time curl -X POST http://localhost:8000/api/v1/upload/ -F "file=@large_test.pdf"
# Expected: Complete within reasonable time with valid checksum
```

### Duplicate Detection Testing
```bash
# Test workspace-scoped duplicate detection
curl -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@document.pdf" \
    -F "workspace_id=test-workspace-1"

# Upload same file to same workspace
curl -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@document.pdf" \
    -F "workspace_id=test-workspace-1"
# Expected: 409 Conflict or duplicate reference response

# Test cross-workspace duplicate detection
curl -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@document.pdf" \
    -F "workspace_id=test-workspace-2"
# Expected: New document created with duplicate reference

# Test duplicate statistics
curl http://localhost:8000/api/v1/duplicates/stats?workspace_id=test-workspace-1
# Expected: Statistics showing duplicate counts and storage savings
```

### Error Handling Testing
```bash
# Test file validation errors
curl -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@malware.exe"
# Expected: 400 error with detailed validation information

# Test storage errors (simulate disk full)
# Fill up storage space first, then:
curl -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@test.pdf"
# Expected: 507 error with storage full message and recovery suggestions

# Test database connection errors
# Stop database service, then:
curl -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@test.pdf"
# Expected: 500 error with database connection failure message

# Test timeout errors
curl -X POST http://localhost:8000/api/v1/upload/ \
    --max-time 1 \
    -F "file=@very_large_file.pdf"
# Expected: 408 timeout error with retry suggestions
```

### Enhanced Metadata Testing
```bash
# Test metadata storage
curl -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@test.pdf" \
    -F "document_name=Financial Report Q3" \
    -F "tags=finance,quarterly,2024" \
    -F 'metadata={"department":"Finance","quarter":"Q3","year":2024}'

# Verify metadata in response
# Expected: Full metadata returned in response

# Test metadata validation
curl -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@test.pdf" \
    -F "tags=$(printf '%*s' 1000 | tr ' ' 'a')"  # Very long tag
# Expected: 400 error with tag length validation failure

# Test metadata search (if implemented)
curl "http://localhost:8000/api/v1/documents/search?tags=finance&metadata.department=Finance"
# Expected: Documents matching metadata criteria
```

### Performance and Stress Testing
```bash
# Test concurrent uploads with checksum calculation
for i in {1..20}; do
    curl -X POST http://localhost:8000/api/v1/upload/ \
        -F "file=@test_$i.pdf" \
        -F "workspace_id=stress-test" &
done
wait
# Expected: All uploads complete successfully with unique checksums

# Test large file handling
dd if=/dev/zero of=max_size.pdf bs=1024 count=30720  # 30MB (at limit)
time curl -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@max_size.pdf"
# Expected: Complete within 60 seconds with valid checksum

# Test duplicate detection performance
# Upload 100 identical files
for i in {1..100}; do
    curl -s -X POST http://localhost:8000/api/v1/upload/ \
        -F "file=@identical.pdf" \
        -F "workspace_id=perf-test-$((i % 10))" > /dev/null &
    
    if (( i % 10 == 0 )); then
        wait  # Wait for batch to complete
    fi
done
# Expected: Fast duplicate detection, storage optimization
```

### Integration Testing
```bash
# Test full upload-to-retrieval workflow
upload_response=$(curl -s -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@test.pdf" \
    -F "workspace_id=integration-test")

document_id=$(echo $upload_response | jq -r '.document_id')
checksum=$(echo $upload_response | jq -r '.checksum')

# Verify document exists
curl http://localhost:8000/api/v1/documents/$document_id
# Expected: Document metadata with matching checksum

# Verify file integrity
curl -X POST http://localhost:8000/api/v1/integrity/verify/$document_id
# Expected: Integrity verification passes

# Test duplicate detection
curl -X POST http://localhost:8000/api/v1/duplicates/check \
    -H "Content-Type: application/json" \
    -d "{\"checksum\":\"$checksum\",\"workspace_id\":\"integration-test\"}"
# Expected: Duplicate found with document reference
```

### Expected Behaviors
- **Checksum Calculation**: 100% accuracy, complete within 2x file size in seconds
- **Duplicate Detection**: 100% accuracy, sub-second response for cached results
- **Error Recovery**: >90% automatic recovery rate for transient errors
- **Metadata Storage**: Support for 10KB metadata, 20 tags per document
- **Performance**: Handle 100+ concurrent uploads with checksums and deduplication

---

## 8. MONITORING & METRICS

### Enhanced Metrics Collection
```python
# Checksum-related metrics
checksum_calculations_total = Counter(
    'checksum_calculations_total',
    'Total checksum calculations performed',
    ['algorithm', 'file_size_category', 'status']
)

checksum_calculation_duration = Histogram(
    'checksum_calculation_duration_seconds',
    'Time spent calculating checksums',
    ['algorithm', 'file_size_category'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 300.0]
)

integrity_checks_total = Counter(
    'integrity_checks_total',
    'Total file integrity checks performed',
    ['status', 'check_type']
)

# Deduplication metrics
duplicate_detections_total = Counter(
    'duplicate_detections_total',
    'Total duplicate file detections',
    ['scope', 'action_taken']
)

storage_savings_bytes = Gauge(
    'storage_savings_bytes_total',
    'Total storage space saved through deduplication'
)

duplicate_groups_count = Gauge(
    'duplicate_groups_count',
    'Number of active duplicate groups'
)

deduplication_cache_hits = Counter(
    'deduplication_cache_hits_total',
    'Cache hits during duplicate detection',
    ['cache_type']
)

# Error handling metrics
errors_total = Counter(
    'errors_total',
    'Total errors by category and type',
    ['category', 'error_type', 'severity', 'recovery_status']
)

error_recovery_attempts = Counter(
    'error_recovery_attempts_total',
    'Error recovery attempts by strategy',
    ['recovery_strategy', 'success']
)

error_resolution_duration = Histogram(
    'error_resolution_duration_seconds',
    'Time to resolve errors',
    ['error_category', 'resolution_type'],
    buckets=[1, 5, 30, 300, 1800, 3600, 86400]  # 1s to 1 day
)

# Enhanced metadata metrics
metadata_operations_total = Counter(
    'metadata_operations_total',
    'Metadata operations performed',
    ['operation_type', 'field_type']
)

metadata_size_distribution = Histogram(
    'metadata_size_bytes',
    'Distribution of metadata sizes',
    buckets=[100, 500, 1024, 2048, 5120, 10240]  # Up to 10KB
)

tag_usage_distribution = Counter(
    'tag_usage_total',
    'Tag usage distribution',
    ['tag_name']
)
```

### Comprehensive Log Entries
```json
// Enhanced upload with checksum and deduplication
{
    "timestamp": "2024-11-15T10:30:00Z",
    "level": "INFO",
    "event": "enhanced_upload_completed",
    "operation_id": "op-uuid",
    "document_id": "doc-uuid",
    "filename": "financial_report.pdf",
    "file_size": 2048576,
    "mime_type": "application/pdf",
    "checksum": {
        "algorithm": "sha256",
        "hash": "a1b2c3d4e5f6...",
        "calculation_time_ms": 125,
        "verified": true
    },
    "deduplication": {
        "is_duplicate": false,
        "scope_checked": "both",
        "check_time_ms": 15,
        "storage_saved": false
    },
    "metadata": {
        "tags_count": 3,
        "tags": ["finance", "quarterly", "2024"],
        "metadata_size_bytes": 245,
        "custom_fields": 5
    },
    "processing_time_ms": 1250,
    "workspace_id": "workspace-uuid"
}

// Duplicate detection event
{
    "timestamp": "2024-11-15T10:31:00Z",
    "level": "INFO",
    "event": "duplicate_detected",
    "operation_id": "op-uuid",
    "filename": "report_copy.pdf",
    "checksum": "a1b2c3d4e5f6...",
    "duplicate_info": {
        "scope": "workspace",
        "existing_document_id": "doc-uuid",
        "duplicate_group_id": "group-uuid",
        "action_taken": "reference_existing",
        "storage_saved_bytes": 2048576
    },
    "detection_time_ms": 8
}

// Error with recovery information
{
    "timestamp": "2024-11-15T10:32:00Z",
    "level": "ERROR",
    "event": "upload_error_with_recovery",
    "error_id": "error-uuid",
    "operation_id": "op-uuid",
    "filename": "problematic.pdf",
    "error": {
        "type": "ChecksumCalculationError",
        "category": "checksum",
        "severity": "medium",
        "message": "Checksum calculation timeout",
        "code": "CHECKSUM_TIMEOUT",
        "stage": "calculation"
    },
    "recovery": {
        "attempted": true,
        "strategy": "retry_with_streaming",
        "attempts": 2,
        "successful": true,
        "recovery_time_ms": 5000
    },
    "final_outcome": "success",
    "total_time_ms": 7500
}

// Integrity check result
{
    "timestamp": "2024-11-15T10:33:00Z",
    "level": "WARNING",
    "event": "integrity_check_failed",
    "document_id": "doc-uuid",
    "filename": "corrupted.pdf",
    "integrity_check": {
        "expected_checksum": "a1b2c3d4e5f6...",
        "calculated_checksum": "b2c3d4e5f6a1...",
        "file_exists": true,
        "file_size_match": true,
        "checksum_match": false,
        "corruption_detected": true
    },
    "action_taken": "quarantine_file",
    "notification_sent": true
}
```

### Dashboard Metrics
```python
class EnhancedMetricsDashboard:
    """Enhanced metrics collection for comprehensive monitoring"""
    
    async def collect_upload_metrics(self) -> UploadMetrics:
        """Collect comprehensive upload metrics"""
        
        # Get time-series data
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        return UploadMetrics(
            # Upload volumes
            uploads_last_hour=await self.count_uploads(hour_ago, now),
            uploads_last_day=await self.count_uploads(day_ago, now),
            
            # Success rates
            success_rate_hour=await self.calculate_success_rate(hour_ago, now),
            success_rate_day=await self.calculate_success_rate(day_ago, now),
            
            # Performance metrics
            avg_upload_time_ms=await self.avg_upload_time(hour_ago, now),
            avg_checksum_time_ms=await self.avg_checksum_time(hour_ago, now),
            
            # Storage metrics
            total_storage_used_gb=await self.total_storage_used(),
            storage_saved_by_dedup_gb=await self.storage_saved_by_deduplication(),
            
            # Duplicate statistics
            duplicate_detection_rate=await self.duplicate_detection_rate(day_ago, now),
            active_duplicate_groups=await self.count_active_duplicate_groups(),
            
            # Error statistics
            error_rate_hour=await self.error_rate(hour_ago, now),
            recovery_success_rate=await self.recovery_success_rate(day_ago, now),
            
            # System health
            checksum_calculation_health=await self.checksum_system_health(),
            deduplication_system_health=await self.deduplication_system_health()
        )
    
    async def collect_error_analytics(self) -> ErrorAnalytics:
        """Collect detailed error analytics"""
        
        day_ago = datetime.utcnow() - timedelta(days=1)
        
        return ErrorAnalytics(
            # Error distribution
            errors_by_category=await self.errors_by_category(day_ago),
            errors_by_severity=await self.errors_by_severity(day_ago),
            
            # Top error types
            top_error_types=await self.top_error_types(day_ago, limit=10),
            
            # Recovery analytics
            recovery_strategies_used=await self.recovery_strategies_used(day_ago),
            recovery_success_by_strategy=await self.recovery_success_by_strategy(day_ago),
            
            # Resolution analytics
            avg_resolution_time_by_category=await self.avg_resolution_time_by_category(day_ago),
            unresolved_errors_count=await self.count_unresolved_errors(),
            
            # Trending
            error_trend_7_days=await self.error_trend(days=7),
            resolution_trend_7_days=await self.resolution_trend(days=7)
        )
    
    async def generate_health_report(self) -> SystemHealthReport:
        """Generate comprehensive system health report"""
        
        return SystemHealthReport(
            timestamp=datetime.utcnow().isoformat(),
            overall_health=await self.calculate_overall_health(),
            
            # Component health
            upload_system_health=await self.upload_system_health(),
            checksum_system_health=await self.checksum_system_health(),
            deduplication_system_health=await self.deduplication_system_health(),
            storage_system_health=await self.storage_system_health(),
            database_health=await self.database_health(),
            
            # Performance indicators
            response_times=await self.get_response_time_metrics(),
            throughput=await self.get_throughput_metrics(),
            error_rates=await self.get_error_rate_metrics(),
            
            # Resource utilization
            cpu_usage=await self.get_cpu_usage(),
            memory_usage=await self.get_memory_usage(),
            disk_usage=await self.get_disk_usage(),
            
            # Alerts and recommendations
            active_alerts=await self.get_active_alerts(),
            recommendations=await self.generate_recommendations()
        )
```

### Alerting Configuration
```yaml
# Prometheus alerting rules for enhanced features
groups:
  - name: checksum_alerts
    rules:
      - alert: ChecksumCalculationFailureRateHigh
        expr: rate(checksum_calculations_total{status="failed"}[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High checksum calculation failure rate"
          description: "Checksum calculation failure rate is {{ $value }} failures/sec"
      
      - alert: ChecksumCalculationSlow
        expr: histogram_quantile(0.95, rate(checksum_calculation_duration_seconds_bucket[5m])) > 60
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Checksum calculations are slow"
          description: "95th percentile checksum calculation time is {{ $value }}s"
  
  - name: deduplication_alerts
    rules:
      - alert: DeduplicationSystemDown
        expr: rate(duplicate_detections_total[5m]) == 0 and rate(file_uploads_total[5m]) > 0
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "Deduplication system appears to be down"
          description: "No duplicate detections while uploads are occurring"
      
      - alert: DuplicateDetectionCacheMissRateHigh
        expr: rate(deduplication_cache_hits_total[5m]) / rate(duplicate_detections_total[5m]) < 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Deduplication cache miss rate is high"
          description: "Cache hit rate is {{ $value }}, consider increasing cache size"
  
  - name: error_handling_alerts
    rules:
      - alert: ErrorRecoveryFailureRateHigh
        expr: rate(error_recovery_attempts_total{success="false"}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error recovery failure rate"
          description: "Error recovery failure rate is {{ $value }} failures/sec"
      
      - alert: UnresolvedErrorsAccumulating
        expr: increase(errors_total{recovery_status="unresolved"}[1h]) > 10
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Unresolved errors are accumulating"
          description: "{{ $value }} unresolved errors in the last hour"
```

---

## 9. SECURITY CONSIDERATIONS

### Checksum Security
```python
class ChecksumSecurity:
    """Security measures for checksum operations"""
    
    @staticmethod
    def secure_checksum_comparison(checksum1: str, checksum2: str) -> bool:
        """Constant-time checksum comparison to prevent timing attacks"""
        import hmac
        return hmac.compare_digest(checksum1, checksum2)
    
    @staticmethod
    def validate_checksum_format(checksum: str, algorithm: str) -> bool:
        """Validate checksum format and prevent injection"""
        patterns = {
            'sha256': r'^[a-fA-F0-9]{64}$',
            'sha1': r'^[a-fA-F0-9]{40}$',
            'md5': r'^[a-fA-F0-9]{32}$'
        }
        
        pattern = patterns.get(algorithm)
        if not pattern:
            return False
        
        return re.match(pattern, checksum) is not None
    
    @classmethod
    async def calculate_secure_checksum(
        cls,
        content: bytes,
        algorithm: str = 'sha256'
    ) -> str:
        """Calculate checksum with security validations"""
        
        # Validate algorithm
        allowed_algorithms = ['sha256', 'sha1', 'md5']
        if algorithm not in allowed_algorithms:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        # Calculate checksum
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(content)
        checksum = hash_obj.hexdigest()
        
        # Validate result format
        if not cls.validate_checksum_format(checksum, algorithm):
            raise ValueError(f"Invalid checksum format generated")
        
        return checksum
```

### Deduplication Security
```python
class DeduplicationSecurity:
    """Security measures for deduplication operations"""
    
    @staticmethod
    async def validate_duplicate_access(
        user_id: str,
        original_document: Document,
        target_workspace: str
    ) -> bool:
        """Validate user access to reference duplicate documents"""
        
        # Check if user has access to original document's workspace
        original_access = await check_workspace_access(
            user_id,
            original_document.workspace_id
        )
        
        # Check if user has access to target workspace
        target_access = await check_workspace_access(user_id, target_workspace)
        
        # User must have access to both workspaces to create cross-workspace reference
        return original_access and target_access
    
    @staticmethod
    def sanitize_duplicate_metadata(metadata: dict) -> dict:
        """Sanitize metadata from duplicate sources to prevent data leakage"""
        
        # Remove sensitive fields that shouldn't be copied
        sensitive_fields = [
            'original_uploader_id',
            'internal_notes',
            'security_classification',
            'access_control_list'
        ]
        
        sanitized = metadata.copy()
        for field in sensitive_fields:
            sanitized.pop(field, None)
        
        return sanitized
    
    @staticmethod
    async def audit_duplicate_operation(
        operation: str,
        user_id: str,
        source_document_id: UUID,
        target_workspace_id: str,
        action_taken: str
    ):
        """Audit duplicate operations for security monitoring"""
        
        audit_entry = {
            'event_type': 'duplicate_operation',
            'operation': operation,
            'user_id': user_id,
            'source_document_id': str(source_document_id),
            'target_workspace_id': target_workspace_id,
            'action_taken': action_taken,
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': get_client_ip(),
            'user_agent': get_user_agent()
        }
        
        await security_logger.log_audit_event(audit_entry)
```

### Enhanced Input Validation
```python
class EnhancedInputValidator:
    """Enhanced input validation for additional features"""
    
    @staticmethod
    def validate_metadata_input(metadata: dict) -> dict:
        """Validate and sanitize metadata input"""
        
        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a JSON object")
        
        # Size limit
        metadata_json = json.dumps(metadata)
        if len(metadata_json) > 10240:  # 10KB limit
            raise ValidationError("Metadata exceeds 10KB limit")
        
        # Depth limit (prevent deeply nested objects)
        if get_json_depth(metadata) > 5:
            raise ValidationError("Metadata nesting depth exceeds limit of 5")
        
        # Sanitize string values
        sanitized = {}
        for key, value in metadata.items():
            # Validate key
            if not isinstance(key, str) or len(key) > 100:
                continue
            
            # Sanitize key
            clean_key = re.sub(r'[^\w\-_.]', '_', key)[:100]
            
            # Sanitize value
            if isinstance(value, str):
                # HTML escape and length limit
                clean_value = html.escape(value)[:1000]
            elif isinstance(value, (int, float, bool)):
                clean_value = value
            elif isinstance(value, list):
                # Limit list size and sanitize elements
                clean_value = [html.escape(str(item))[:100] for item in value[:20]]
            else:
                # Convert other types to string and sanitize
                clean_value = html.escape(str(value))[:1000]
            
            sanitized[clean_key] = clean_value
        
        return sanitized
    
    @staticmethod
    def validate_tags_input(tags: List[str]) -> List[str]:
        """Validate and sanitize tags input"""
        
        if not isinstance(tags, list):
            raise ValidationError("Tags must be a list")
        
        if len(tags) > 20:
            raise ValidationError("Maximum 20 tags allowed")
        
        sanitized_tags = []
        tag_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
        
        for tag in tags:
            if not isinstance(tag, str):
                continue
            
            # Clean and validate tag
            clean_tag = tag.strip().lower()[:50]
            
            if not clean_tag:
                continue
            
            if not tag_pattern.match(clean_tag):
                # Replace invalid characters with underscores
                clean_tag = re.sub(r'[^\w-]', '_', clean_tag)
            
            # Prevent reserved tags
            reserved_tags = ['system', 'internal', 'admin', 'deleted']
            if clean_tag not in reserved_tags:
                sanitized_tags.append(clean_tag)
        
        return list(set(sanitized_tags))  # Remove duplicates
    
    @staticmethod
    def validate_workspace_reference(
        workspace_id: str,
        user_id: str,
        operation: str
    ) -> bool:
        """Validate workspace reference for security"""
        
        # Validate workspace ID format
        try:
            UUID(workspace_id)
        except ValueError:
            if workspace_id != 'default':
                raise ValidationError("Invalid workspace ID format")
        
        # Check workspace access permissions
        if not check_workspace_access(user_id, workspace_id):
            raise PermissionError(f"Access denied to workspace {workspace_id}")
        
        # Check operation-specific permissions
        required_permissions = {
            'upload': ['write', 'admin'],
            'duplicate_reference': ['read', 'write', 'admin'],
            'metadata_update': ['write', 'admin'],
            'delete': ['admin']
        }
        
        user_permissions = get_user_workspace_permissions(user_id, workspace_id)
        required = required_permissions.get(operation, ['read'])
        
        if not any(perm in user_permissions for perm in required):
            raise PermissionError(f"Insufficient permissions for {operation}")
        
        return True
```

### Error Information Security
```python
class SecureErrorHandling:
    """Secure error handling to prevent information disclosure"""
    
    @staticmethod
    def sanitize_error_response(
        error: Exception,
        user_context: dict,
        is_admin: bool = False
    ) -> dict:
        """Sanitize error response to prevent information leakage"""
        
        # Base error response
        sanitized_response = {
            'error': True,
            'error_code': getattr(error, 'error_code', 'GENERIC_ERROR'),
            'message': 'An error occurred during processing'
        }
        
        # Admin users get more detailed information
        if is_admin:
            sanitized_response.update({
                'error_type': type(error).__name__,
                'detailed_message': str(error),
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # Specific error types with safe messages
        if isinstance(error, ValidationError):
            sanitized_response['message'] = str(error)
            sanitized_response['user_actionable'] = True
        
        elif isinstance(error, PermissionError):
            sanitized_response['message'] = 'Access denied'
            sanitized_response['user_actionable'] = False
        
        elif isinstance(error, (ConnectionError, TimeoutError)):
            sanitized_response['message'] = 'Service temporarily unavailable'
            sanitized_response['retry_suggested'] = True
        
        else:
            # Generic error - don't expose internal details
            sanitized_response['message'] = 'An unexpected error occurred'
            sanitized_response['support_reference'] = generate_support_reference()
        
        return sanitized_response
    
    @staticmethod
    def log_security_relevant_error(
        error: Exception,
        context: dict,
        user_info: dict
    ):
        """Log security-relevant errors for monitoring"""
        
        security_relevant_errors = [
            'PermissionError',
            'AuthenticationError',
            'ValidationError',
            'SecurityViolationError',
            'SuspiciousActivityError'
        ]
        
        error_type = type(error).__name__
        
        if error_type in security_relevant_errors:
            security_log_entry = {
                'event_type': 'security_relevant_error',
                'error_type': error_type,
                'error_message': str(error),
                'user_id': user_info.get('user_id'),
                'ip_address': user_info.get('ip_address'),
                'user_agent': user_info.get('user_agent'),
                'operation': context.get('operation'),
                'resource': context.get('resource'),
                'timestamp': datetime.utcnow().isoformat(),
                'severity': assess_security_severity(error, context)
            }
            
            security_logger.warning(
                f"Security-relevant error: {error_type}",
                extra=security_log_entry
            )
            
            # Alert security team for high-severity issues
            if security_log_entry['severity'] == 'high':
                asyncio.create_task(
                    notify_security_team(security_log_entry)
                )
```

---

## 10. CODE PATTERNS & CONVENTIONS

### Repository Pattern for Enhanced Data Access
```python
# Enhanced repository pattern with checksum and metadata support
class EnhancedDocumentRepository:
    """Enhanced document repository with checksum and metadata support"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_with_checksum(
        self,
        document_data: dict,
        checksum_data: dict,
        metadata: dict = None
    ) -> Document:
        """Create document with checksum and metadata in single transaction"""
        
        try:
            with self.db.begin():
                # Create main document record
                document = Document(
                    **document_data,
                    checksum=checksum_data['checksum'],
                    checksum_algorithm=checksum_data['algorithm'],
                    integrity_verified=True,
                    metadata=metadata or {},
                    created_at=datetime.utcnow()
                )
                
                self.db.add(document)
                
                # Create checksum verification record
                checksum_record = ChecksumRecord(
                    document_id=document.id,
                    checksum=checksum_data['checksum'],
                    algorithm=checksum_data['algorithm'],
                    calculation_time_ms=checksum_data.get('calculation_time_ms'),
                    verified_at=datetime.utcnow()
                )
                
                self.db.add(checksum_record)
                self.db.commit()
                
                return document
                
        except Exception as e:
            self.db.rollback()
            raise RepositoryException(f"Failed to create document with checksum: {str(e)}")
    
    async def find_by_checksum(
        self,
        checksum: str,
        workspace_id: str = None,
        include_deleted: bool = False
    ) -> List[Document]:
        """Find documents by checksum with optional workspace scoping"""
        
        query = self.db.query(Document).filter(Document.checksum == checksum)
        
        if workspace_id:
            query = query.filter(Document.workspace_id == workspace_id)
        
        if not include_deleted:
            query = query.filter(Document.is_deleted == False)
        
        return query.all()
    
    async def update_metadata(
        self,
        document_id: UUID,
        metadata_updates: dict,
        user_id: str = None
    ) -> bool:
        """Update document metadata with audit trail"""
        
        try:
            with self.db.begin():
                document = self.db.query(Document).filter(
                    Document.id == document_id
                ).first()
                
                if not document:
                    return False
                
                # Store old metadata for audit
                old_metadata = document.metadata.copy()
                
                # Update metadata
                document.metadata.update(metadata_updates)
                document.updated_at = datetime.utcnow()
                
                # Create audit trail entry
                audit_entry = AuditTrail(
                    operation='metadata_update',
                    document_id=document_id,
                    operation_details={
                        'old_metadata': old_metadata,
                        'new_metadata': document.metadata,
                        'updated_fields': list(metadata_updates.keys())
                    },
                    performed_by=user_id,
                    performed_at=datetime.utcnow()
                )
                
                self.db.add(audit_entry)
                self.db.commit()
                
                return True
                
        except Exception as e:
            self.db.rollback()
            raise RepositoryException(f"Failed to update metadata: {str(e)}")
```

### Factory Pattern for Service Creation
```python
class EnhancedServiceFactory:
    """Factory for creating enhanced services with proper dependencies"""
    
    def __init__(self, db: Session, config: Config):
        self.db = db
        self.config = config
        self._service_cache = {}
    
    def create_checksum_service(self) -> ChecksumService:
        """Create checksum service with configuration"""
        
        if 'checksum' not in self._service_cache:
            self._service_cache['checksum'] = ChecksumService(
                algorithm=self.config.CHECKSUM_ALGORITHM,
                chunk_size=self.config.CHECKSUM_CHUNK_SIZE,
                timeout=self.config.CHECKSUM_TIMEOUT
            )
        
        return self._service_cache['checksum']
    
    def create_deduplication_service(self) -> DeduplicationService:
        """Create deduplication service with dependencies"""
        
        if 'deduplication' not in self._service_cache:
            checksum_service = self.create_checksum_service()
            storage_service = self.create_storage_service()
            
            self._service_cache['deduplication'] = DeduplicationService(
                db=self.db,
                checksum_service=checksum_service,
                storage_service=storage_service,
                config=self.config.deduplication_config
            )
        
        return self._service_cache['deduplication']
    
    def create_enhanced_upload_service(self) -> EnhancedUploadService:
        """Create upload service with all enhancements"""
        
        if 'enhanced_upload' not in self._service_cache:
            checksum_service = self.create_checksum_service()
            deduplication_service = self.create_deduplication_service()
            validation_service = self.create_validation_service()
            storage_service = self.create_storage_service()
            error_handler = self.create_error_handler()
            
            self._service_cache['enhanced_upload'] = EnhancedUploadService(
                db=self.db,
                checksum_service=checksum_service,
                deduplication_service=deduplication_service,
                validation_service=validation_service,
                storage_service=storage_service,
                error_handler=error_handler
            )
        
        return self._service_cache['enhanced_upload']
```

### Strategy Pattern for Error Recovery
```python
# Strategy pattern for different error recovery approaches
class ErrorRecoveryStrategy(ABC):
    """Abstract error recovery strategy"""
    
    @abstractmethod
    async def can_handle(self, error: Exception, context: dict) -> bool:
        """Check if this strategy can handle the error"""
        pass
    
    @abstractmethod
    async def recover(self, error: Exception, context: dict) -> RecoveryResult:
        """Attempt to recover from the error"""
        pass

class RetryWithBackoffStrategy(ErrorRecoveryStrategy):
    """Retry strategy with exponential backoff"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
    
    async def can_handle(self, error: Exception, context: dict) -> bool:
        """Handle transient errors that may succeed on retry"""
        transient_errors = [
            'ConnectionError',
            'TimeoutError', 
            'TemporaryFailure',
            'ServiceUnavailable'
        ]
        return type(error).__name__ in transient_errors
    
    async def recover(self, error: Exception, context: dict) -> RecoveryResult:
        """Retry operation with exponential backoff"""
        
        attempt = context.get('retry_count', 0)
        
        if attempt >= self.max_attempts:
            return RecoveryResult(
                success=False,
                action='retry_exhausted',
                message=f"Max retry attempts ({self.max_attempts}) exceeded"
            )
        
        # Calculate delay
        delay = self.base_delay * (2 ** attempt)
        
        # Wait before retry
        await asyncio.sleep(delay)
        
        return RecoveryResult(
            success=True,
            action='retry_scheduled',
            message=f"Retry scheduled after {delay}s delay",
            retry_after_seconds=delay
        )

class StorageCleanupStrategy(ErrorRecoveryStrategy):
    """Recovery strategy that cleans up storage to free space"""
    
    async def can_handle(self, error: Exception, context: dict) -> bool:
        """Handle storage-related errors"""
        storage_errors = ['DiskFullError', 'StorageQuotaExceeded', 'InsufficientSpace']
        return type(error).__name__ in storage_errors
    
    async def recover(self, error: Exception, context: dict) -> RecoveryResult:
        """Attempt to free storage space"""
        
        # Clean temporary files
        temp_cleanup = await cleanup_temporary_files()
        
        # Clean old duplicate files
        duplicate_cleanup = await cleanup_old_duplicates()
        
        # Total space freed
        total_freed = temp_cleanup.space_freed + duplicate_cleanup.space_freed
        
        if total_freed > 100 * 1024 * 1024:  # 100MB freed
            return RecoveryResult(
                success=True,
                action='storage_cleanup',
                message=f"Freed {total_freed / 1024 / 1024:.1f}MB of storage space"
            )
        
        return RecoveryResult(
            success=False,
            action='insufficient_cleanup',
            message="Could not free sufficient storage space"
        )

# Recovery manager using strategies
class ErrorRecoveryManager:
    """Manages error recovery using different strategies"""
    
    def __init__(self):
        self.strategies = [
            RetryWithBackoffStrategy(),
            StorageCleanupStrategy(),
            FallbackServiceStrategy(),
            GracefulDegradationStrategy()
        ]
    
    async def attempt_recovery(
        self,
        error: Exception,
        context: dict
    ) -> RecoveryResult:
        """Attempt recovery using appropriate strategy"""
        
        for strategy in self.strategies:
            if await strategy.can_handle(error, context):
                return await strategy.recover(error, context)
        
        return RecoveryResult(
            success=False,
            action='no_strategy_available',
            message="No recovery strategy available for this error"
        )
```

### Observer Pattern for Enhanced Events
```python
# Observer pattern for enhanced event handling
class EnhancedEventObserver(ABC):
    """Abstract observer for enhanced events"""
    
    @abstractmethod
    async def on_checksum_calculated(self, event: ChecksumCalculatedEvent):
        pass
    
    @abstractmethod
    async def on_duplicate_detected(self, event: DuplicateDetectedEvent):
        pass
    
    @abstractmethod
    async def on_error_recovered(self, event: ErrorRecoveredEvent):
        pass
    
    @abstractmethod
    async def on_metadata_updated(self, event: MetadataUpdatedEvent):
        pass

class MetricsObserver(EnhancedEventObserver):
    """Observer that collects enhanced metrics"""
    
    async def on_checksum_calculated(self, event: ChecksumCalculatedEvent):
        checksum_calculations_total.labels(
            algorithm=event.algorithm,
            file_size_category=event.size_category,
            status='success'
        ).inc()
        
        checksum_calculation_duration.labels(
            algorithm=event.algorithm,
            file_size_category=event.size_category
        ).observe(event.duration_ms / 1000)
    
    async def on_duplicate_detected(self, event: DuplicateDetectedEvent):
        duplicate_detections_total.labels(
            scope=event.scope,
            action_taken=event.action_taken
        ).inc()
        
        if event.storage_saved_bytes > 0:
            storage_savings_bytes.inc(event.storage_saved_bytes)
    
    async def on_error_recovered(self, event: ErrorRecoveredEvent):
        error_recovery_attempts.labels(
            recovery_strategy=event.strategy,
            success='true' if event.success else 'false'
        ).inc()
        
        if event.success:
            error_resolution_duration.labels(
                error_category=event.error_category,
                resolution_type='automatic'
            ).observe(event.recovery_time_ms / 1000)

class AuditObserver(EnhancedEventObserver):
    """Observer that creates audit trail entries"""
    
    async def on_duplicate_detected(self, event: DuplicateDetectedEvent):
        await audit_logger.log_event({
            'event_type': 'duplicate_detected',
            'checksum': event.checksum,
            'scope': event.scope,
            'action_taken': event.action_taken,
            'storage_saved_bytes': event.storage_saved_bytes,
            'timestamp': event.timestamp
        })
    
    async def on_metadata_updated(self, event: MetadataUpdatedEvent):
        await audit_logger.log_event({
            'event_type': 'metadata_updated',
            'document_id': str(event.document_id),
            'updated_fields': event.updated_fields,
            'user_id': event.user_id,
            'timestamp': event.timestamp
        })
```

### Naming Conventions for Enhanced Features
- **Services**: `{Feature}Service` (ChecksumService, DeduplicationService)
- **Repositories**: `Enhanced{Entity}Repository` (EnhancedDocumentRepository)
- **Events**: `{Action}{Entity}Event` (ChecksumCalculatedEvent, DuplicateDetectedEvent)
- **Strategies**: `{Purpose}Strategy` (RetryWithBackoffStrategy, StorageCleanupStrategy)
- **Results**: `{Operation}Result` (ChecksumResult, DeduplicationResult, RecoveryResult)
- **Exceptions**: `{Feature}Exception` (ChecksumException, DeduplicationException)
- **Configurations**: `{Feature}Config` (ChecksumConfig, DeduplicationConfig)

---

## 11. INTEGRATION POINTS

### Enhanced Upload Service Integration
```python
class EnhancedUploadOrchestrator:
    """Orchestrates enhanced upload process with all features"""
    
    def __init__(
        self,
        validation_service: FileValidator,
        checksum_service: ChecksumService,
        deduplication_service: DeduplicationService,
        storage_service: StorageService,
        metadata_service: MetadataService,
        error_handler: ErrorHandler,
        db: Session
    ):
        self.validation_service = validation_service
        self.checksum_service = checksum_service
        self.deduplication_service = deduplication_service
        self.storage_service = storage_service
        self.metadata_service = metadata_service
        self.error_handler = error_handler
        self.db = db
    
    async def process_enhanced_upload(
        self,
        file: UploadFile,
        upload_context: UploadContext
    ) -> EnhancedUploadResult:
        """Process upload with all enhanced features integrated"""
        
        operation_id = uuid.uuid4()
        
        try:
            # Step 1: File validation (from Step 4)
            validation_result = await self.validation_service.validate_file(file)
            if not validation_result.is_valid:
                raise ValidationException(validation_result.errors)
            
            # Step 2: Calculate checksum
            checksum_result = await self.checksum_service.calculate_file_checksum(file)
            
            # Step 3: Check for duplicates
            duplicate_result = await self.deduplication_service.check_for_duplicates(
                checksum_result.checksum,
                upload_context.workspace_id
            )
            
            # Step 4: Handle duplicate or proceed with new upload
            if duplicate_result.is_duplicate:
                return await self._handle_duplicate_upload(
                    file,
                    checksum_result,
                    duplicate_result,
                    upload_context
                )
            
            # Step 5: Store file and create database record
            storage_result = await self.storage_service.store_file(
                file,
                upload_context.generate_storage_path()
            )
            
            # Step 6: Process and store enhanced metadata
            metadata_result = await self.metadata_service.process_metadata(
                upload_context.metadata,
                upload_context.tags,
                file.filename
            )
            
            # Step 7: Create comprehensive database record
            document = await self._create_enhanced_document_record(
                file,
                validation_result,
                checksum_result,
                storage_result,
                metadata_result,
                upload_context
            )
            
            # Step 8: Publish events for downstream processing
            await self._publish_upload_events(document, upload_context)
            
            return EnhancedUploadResult(
                success=True,
                document=document,
                checksum=checksum_result.checksum,
                is_duplicate=False,
                storage_saved=False,
                operation_id=operation_id
            )
            
        except Exception as e:
            # Enhanced error handling with recovery
            recovery_result = await self.error_handler.handle_upload_error(
                e,
                upload_context,
                operation_id
            )
            
            if recovery_result.success:
                # Retry with recovery
                return await self.process_enhanced_upload(file, upload_context)
            else:
                raise EnhancedUploadException(
                    message=recovery_result.message,
                    operation_id=operation_id,
                    recovery_attempted=True,
                    original_error=e
                )
```

### Database Integration with Enhanced Schema
```python
class EnhancedDatabaseIntegration:
    """Enhanced database operations with checksum and metadata support"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_document_with_enhancements(
        self,
        document_data: dict,
        checksum_data: dict,
        duplicate_info: dict,
        metadata: dict,
        audit_context: dict
    ) -> Document:
        """Create document record with all enhancements in single transaction"""
        
        try:
            async with self.db.begin():
                # Create main document
                document = Document(
                    id=uuid.uuid4(),
                    **document_data,
                    
                    # Checksum fields
                    checksum=checksum_data['checksum'],
                    checksum_algorithm=checksum_data['algorithm'],
                    integrity_verified=True,
                    last_integrity_check=datetime.utcnow(),
                    
                    # Duplicate fields
                    is_duplicate=duplicate_info.get('is_duplicate', False),
                    duplicate_group_id=duplicate_info.get('group_id'),
                    original_document_id=duplicate_info.get('original_id'),
                    
                    # Enhanced metadata
                    metadata=metadata.get('custom_fields', {}),
                    tags=metadata.get('tags', []),
                    description=metadata.get('description'),
                    
                    # Timestamps
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                self.db.add(document)
                
                # Create checksum record
                checksum_record = ChecksumRecord(
                    document_id=document.id,
                    checksum=checksum_data['checksum'],
                    algorithm=checksum_data['algorithm'],
                    calculation_time_ms=checksum_data.get('calculation_time_ms'),
                    file_size=document.file_size,
                    verified_at=datetime.utcnow()
                )
                
                self.db.add(checksum_record)
                
                # Update duplicate group if applicable
                if duplicate_info.get('group_id'):
                    await self._update_duplicate_group(
                        duplicate_info['group_id'],
                        document
                    )
                
                # Create audit trail
                audit_entry = AuditTrail(
                    operation='enhanced_document_creation',
                    document_id=document.id,
                    operation_details={
                        'checksum': checksum_data['checksum'],
                        'is_duplicate': duplicate_info.get('is_duplicate', False),
                        'metadata_fields': list(metadata.keys()),
                        'file_size': document.file_size
                    },
                    performed_by=audit_context.get('user_id'),
                    ip_address=audit_context.get('ip_address'),
                    user_agent=audit_context.get('user_agent'),
                    performed_at=datetime.utcnow()
                )
                
                self.db.add(audit_entry)
                
                await self.db.commit()
                return document
                
        except Exception as e:
            await self.db.rollback()
            raise DatabaseIntegrationException(
                f"Failed to create enhanced document record: {str(e)}"
            )
```

### Event System Integration
```python
class EnhancedEventPublisher:
    """Enhanced event publishing for downstream service integration"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def publish_checksum_events(
        self,
        document: Document,
        checksum_result: ChecksumResult
    ):
        """Publish checksum-related events"""
        
        # Checksum calculated event
        await self.event_bus.publish(ChecksumCalculatedEvent(
            document_id=document.id,
            checksum=checksum_result.checksum,
            algorithm=checksum_result.algorithm,
            calculation_time_ms=checksum_result.calculation_time_ms,
            file_size=document.file_size,
            timestamp=datetime.utcnow()
        ))
        
        # If duplicate detected
        if document.is_duplicate:
            await self.event_bus.publish(DuplicateDetectedEvent(
                document_id=document.id,
                checksum=document.checksum,
                original_document_id=document.original_document_id,
                duplicate_group_id=document.duplicate_group_id,
                workspace_id=document.workspace_id,
                storage_saved_bytes=document.file_size,
                timestamp=datetime.utcnow()
            ))
    
    async def publish_metadata_events(
        self,
        document: Document,
        metadata_changes: dict = None
    ):
        """Publish metadata-related events"""
        
        if metadata_changes:
            await self.event_bus.publish(MetadataUpdatedEvent(
                document_id=document.id,
                updated_fields=list(metadata_changes.keys()),
                old_metadata=metadata_changes.get('old', {}),
                new_metadata=metadata_changes.get('new', {}),
                timestamp=datetime.utcnow()
            ))
        
        # Tag-related events
        if document.tags:
            for tag in document.tags:
                await self.event_bus.publish(TagAssignedEvent(
                    document_id=document.id,
                    tag=tag,
                    workspace_id=document.workspace_id,
                    timestamp=datetime.utcnow()
                ))
    
    async def publish_error_events(
        self,
        error: Exception,
        context: dict,
        recovery_result: RecoveryResult = None
    ):
        """Publish error and recovery events"""
        
        # Error occurred event
        await self.event_bus.publish(ErrorOccurredEvent(
            error_type=type(error).__name__,
            error_message=str(error),
            operation=context.get('operation'),
            document_id=context.get('document_id'),
            user_id=context.get('user_id'),
            timestamp=datetime.utcnow()
        ))
        
        # Recovery attempted event
        if recovery_result:
            await self.event_bus.publish(ErrorRecoveryAttemptedEvent(
                error_type=type(error).__name__,
                recovery_strategy=recovery_result.strategy,
                recovery_success=recovery_result.success,
                recovery_time_ms=recovery_result.duration_ms,
                timestamp=datetime.utcnow()
            ))
```

### External Service Integration
```python
class ExternalServiceIntegrator:
    """Integration with external services for enhanced features"""
    
    def __init__(self, config: Config):
        self.config = config
    
    async def integrate_with_virus_scanner(
        self,
        document: Document,
        file_content: bytes
    ) -> VirusScanResult:
        """Integrate with external virus scanning service"""
        
        if not self.config.ENABLE_VIRUS_SCANNING:
            return VirusScanResult(scanned=False, clean=True)
        
        try:
            # Example integration with ClamAV
            scan_result = await self._scan_with_clamav(file_content)
            
            # Update document with scan results
            document.virus_scanned = True
            document.virus_scan_clean = scan_result.clean
            document.virus_scan_date = datetime.utcnow()
            
            return scan_result
            
        except Exception as e:
            logger.error(f"Virus scan failed: {str(e)}")
            return VirusScanResult(
                scanned=False,
                clean=False,
                error=str(e)
            )
    
    async def integrate_with_backup_service(
        self,
        document: Document,
        checksum: str
    ) -> BackupResult:
        """Integrate with backup service for checksum verification"""
        
        try:
            # Schedule backup with checksum verification
            backup_job = await backup_service.schedule_backup(
                document_id=document.id,
                file_path=document.storage_path,
                expected_checksum=checksum,
                verification_required=True
            )
            
            return BackupResult(
                scheduled=True,
                backup_job_id=backup_job.id,
                verification_enabled=True
            )
            
        except Exception as e:
            logger.error(f"Backup scheduling failed: {str(e)}")
            return BackupResult(
                scheduled=False,
                error=str(e)
            )
    
    async def integrate_with_search_index(
        self,
        document: Document,
        metadata: dict
    ) -> IndexingResult:
        """Integrate with search indexing service"""
        
        try:
            # Prepare document for indexing
            index_document = {
                'id': str(document.id),
                'filename': document.document_name,
                'content_type': document.mime_type,
                'file_size': document.file_size,
                'checksum': document.checksum,
                'tags': document.tags,
                'metadata': document.metadata,
                'created_at': document.created_at.isoformat(),
                'workspace_id': document.workspace_id
            }
            
            # Submit to search index
            index_result = await search_service.index_document(index_document)
            
            return IndexingResult(
                indexed=True,
                index_id=index_result.id,
                searchable=True
            )
            
        except Exception as e:
            logger.error(f"Search indexing failed: {str(e)}")
            return IndexingResult(
                indexed=False,
                error=str(e)
            )
```

---

## 12. TROUBLESHOOTING GUIDE

### Common Issues with Enhanced Features

#### "Checksum calculation failures"
```bash
# Check available memory for large files
free -h
cat /proc/meminfo | grep Available

# Test checksum calculation manually
python3 -c "
import hashlib
import time

start = time.time()
with open('large_file.pdf', 'rb') as f:
    hash_sha256 = hashlib.sha256()
    while chunk := f.read(65536):
        hash_sha256.update(chunk)
    checksum = hash_sha256.hexdigest()
    
end = time.time()
print(f'Checksum: {checksum}')
print(f'Time: {end - start:.2f}s')
"

# Check for timeout issues
curl -m 300 -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@large_file.pdf"

# Solution: Increase timeout or implement streaming calculation
export CHECKSUM_CALCULATION_TIMEOUT=600  # 10 minutes
```

#### "Duplicate detection not working"
```bash
# Check database for existing checksums
psql -d querybox_core -c "
SELECT checksum, COUNT(*) as count, 
       array_agg(document_name) as documents
FROM documents 
WHERE is_deleted = false
GROUP BY checksum 
HAVING COUNT(*) > 1;
"

# Test duplicate detection manually
checksum="a1b2c3d4e5f6..."  # Known checksum
curl -X POST http://localhost:8000/api/v1/duplicates/check \
    -H "Content-Type: application/json" \
    -d "{\"checksum\":\"$checksum\",\"workspace_id\":\"test\"}"

# Check deduplication cache
redis-cli KEYS "dedup:*"
redis-cli GET "dedup:checksum:$checksum"

# Solution: Clear cache and verify database state
redis-cli FLUSHDB
```

#### "Enhanced metadata not saving"
```bash
# Check metadata size
metadata='{"key1":"value1","key2":"value2"}'
echo $metadata | wc -c  # Should be < 10240 bytes

# Test metadata validation
curl -X POST http://localhost:8000/api/v1/upload/ \
    -F "file=@test.pdf" \
    -F "metadata=$metadata" \
    -v

# Check database metadata column
psql -d querybox_core -c "
SELECT document_name, metadata, tags 
FROM documents 
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 5;
"

# Solution: Validate metadata format and size
python3 -c "
import json
metadata = {'test': 'value'}
json_str = json.dumps(metadata)
print(f'Size: {len(json_str)} bytes')
print(f'Valid JSON: {json.loads(json_str) == metadata}')
"
```

#### "Error recovery not working"
```bash
# Check error logs
tail -f logs/error.log | grep -E "(recovery_attempted|recovery_failed)"

# Check recovery strategy configuration
curl http://localhost:8000/api/v1/admin/error-recovery/config

# Test specific error recovery
curl -X POST http://localhost:8000/api/v1/admin/error-recovery/test \
    -H "Content-Type: application/json" \
    -d '{"error_type":"ConnectionError","simulate":true}'

# Check recovery metrics
curl http://localhost:8000/metrics | grep error_recovery

# Solution: Verify recovery strategy registration
python3 -c "
from app.handlers.error_handlers import ErrorRecoveryManager
manager = ErrorRecoveryManager()
print('Available strategies:', [s.__class__.__name__ for s in manager.strategies])
"
```

### Database Debugging for Enhanced Features

#### Checksum and Integrity Issues
```sql
-- Check checksum calculation status
SELECT 
    document_name,
    checksum,
    checksum_algorithm,
    integrity_verified,
    last_integrity_check,
    created_at
FROM documents 
WHERE integrity_verified = false 
   OR last_integrity_check < NOW() - INTERVAL '30 days'
ORDER BY created_at DESC;

-- Check for duplicate checksums
SELECT 
    checksum,
    COUNT(*) as duplicate_count,
    array_agg(document_name) as filenames,
    array_agg(workspace_id::text) as workspaces,
    SUM(file_size) as total_size_bytes
FROM documents 
WHERE is_deleted = false
GROUP BY checksum 
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;

-- Check checksum verification records
SELECT 
    cr.checksum,
    cr.algorithm,
    cr.calculation_time_ms,
    cr.verified_at,
    d.document_name,
    d.file_size
FROM checksum_records cr
JOIN documents d ON cr.document_id = d.id
WHERE cr.verified_at > NOW() - INTERVAL '24 hours'
ORDER BY cr.calculation_time_ms DESC;
```

#### Duplicate Group Analysis
```sql
-- Check duplicate group statistics
SELECT 
    dg.id as group_id,
    dg.checksum,
    dg.document_count,
    dg.storage_saved_bytes,
    dg.first_uploaded_at,
    dg.last_duplicate_at,
    d.document_name as canonical_document
FROM duplicate_groups dg
LEFT JOIN documents d ON dg.canonical_document_id = d.id
WHERE dg.group_status = 'active'
ORDER BY dg.storage_saved_bytes DESC;

-- Find orphaned duplicate references
SELECT 
    d.id,
    d.document_name,
    d.duplicate_group_id,
    d.original_document_id
FROM documents d
LEFT JOIN duplicate_groups dg ON d.duplicate_group_id = dg.id
WHERE d.is_duplicate = true 
  AND (dg.id IS NULL OR d.original_document_id IS NULL);

-- Calculate total storage savings
SELECT 
    COUNT(*) as total_duplicate_groups,
    SUM(document_count) as total_duplicate_documents,
    SUM(storage_saved_bytes) as total_storage_saved_bytes,
    SUM(storage_saved_bytes) / 1024 / 1024 as total_storage_saved_mb
FROM duplicate_groups
WHERE group_status = 'active';
```

#### Error and Recovery Analysis
```sql
-- Check error frequency by category
SELECT 
    error_category,
    error_type,
    COUNT(*) as error_count,
    COUNT(CASE WHEN resolved = true THEN 1 END) as resolved_count,
    AVG(EXTRACT(EPOCH FROM (resolved_at - occurred_at))) as avg_resolution_time_seconds
FROM error_logs 
WHERE occurred_at > NOW() - INTERVAL '24 hours'
GROUP BY error_category, error_type
ORDER BY error_count DESC;

-- Check unresolved errors
SELECT 
    error_id,
    error_code,
    error_message,
    document_id,
    user_id,
    occurred_at,
    AGE(NOW(), occurred_at) as age
FROM error_logs 
WHERE resolved = false
ORDER BY occurred_at DESC;

-- Check recovery effectiveness
SELECT 
    DATE(occurred_at) as error_date,
    error_category,
    COUNT(*) as total_errors,
    COUNT(CASE WHEN resolved = true THEN 1 END) as resolved_errors,
    ROUND(
        COUNT(CASE WHEN resolved = true THEN 1 END)::decimal / COUNT(*) * 100, 
        2
    ) as resolution_rate_percent
FROM error_logs 
WHERE occurred_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(occurred_at), error_category
ORDER BY error_date DESC, resolution_rate_percent ASC;
```

### Performance Analysis Commands

#### Checksum Performance Analysis
```bash
# Monitor checksum calculation performance
grep "checksum_calculation" logs/app.log | \
    jq -r '[.filename, .file_size, .calculation_time_ms] | @tsv' | \
    awk '{print $2/1024/1024 " MB", $3 " ms", $3/($2/1024/1024) " ms/MB"}' | \
    sort -k3 -n | tail -10

# Check for slow checksum calculations
psql -d querybox_core -c "
SELECT 
    document_name,
    file_size / 1024 / 1024 as size_mb,
    calculation_time_ms,
    calculation_time_ms / (file_size / 1024 / 1024) as ms_per_mb
FROM checksum_records cr
JOIN documents d ON cr.document_id = d.id
WHERE calculation_time_ms > 5000  -- Slower than 5 seconds
ORDER BY ms_per_mb DESC;
"

# Profile checksum calculation
py-spy top --pid $(pgrep -f uvicorn) --duration 60 --function calculate_checksum
```

#### Duplicate Detection Performance
```bash
# Monitor duplicate detection cache performance
redis-cli INFO stats | grep -E "(keyspace_hits|keyspace_misses)"

# Check duplicate detection query performance
psql -d querybox_core -c "
EXPLAIN ANALYZE
SELECT * FROM documents 
WHERE checksum = 'sample_checksum' 
  AND workspace_id = 'sample_workspace' 
  AND is_deleted = false;
"

# Monitor duplicate detection latency
grep "duplicate_detection" logs/app.log | \
    jq -r '.detection_time_ms' | \
    awk '{sum+=$1; count++} END {print "Avg:", sum/count "ms", "Count:", count}'
```

#### Error Recovery Performance
```bash
# Check recovery attempt frequency
grep "recovery_attempted" logs/app.log | \
    jq -r '[.error_type, .recovery_strategy, .recovery_success] | @tsv' | \
    sort | uniq -c | sort -nr

# Monitor recovery success rates
psql -d querybox_core -c "
SELECT 
    resolution_action,
    COUNT(*) as attempts,
    COUNT(CASE WHEN resolved = true THEN 1 END) as successes,
    ROUND(
        COUNT(CASE WHEN resolved = true THEN 1 END)::decimal / COUNT(*) * 100,
        2
    ) as success_rate_percent
FROM error_logs 
WHERE resolution_action IS NOT NULL
GROUP BY resolution_action
ORDER BY success_rate_percent DESC;
"
```

### Recovery Procedures for Enhanced Features

#### Checksum Data Recovery
```bash
# Recalculate checksums for documents missing them
python3 << 'EOF'
import asyncio
from app.services.checksum_service import ChecksumService
from app.db.database import SessionLocal
from app.models.document import Document

async def recalculate_missing_checksums():
    db = SessionLocal()
    checksum_service = ChecksumService()
    
    # Find documents without checksums
    documents = db.query(Document).filter(
        Document.checksum.is_(None)
    ).all()
    
    for doc in documents:
        try:
            with open(doc.storage_path, 'rb') as f:
                content = f.read()
                checksum = await checksum_service.calculate_content_checksum(content)
                
                doc.checksum = checksum
                doc.checksum_algorithm = 'sha256'
                doc.integrity_verified = True
                doc.last_integrity_check = datetime.utcnow()
                
                print(f"Updated checksum for {doc.document_name}: {checksum}")
        
        except Exception as e:
            print(f"Failed to update {doc.document_name}: {str(e)}")
    
    db.commit()
    db.close()

asyncio.run(recalculate_missing_checksums())
EOF
```

#### Duplicate Group Reconciliation
```bash
# Rebuild duplicate groups
python3 << 'EOF'
from app.services.deduplication_service import DeduplicationService
from app.db.database import SessionLocal

def rebuild_duplicate_groups():
    db = SessionLocal()
    dedup_service = DeduplicationService(db)
    
    # Clear existing duplicate groups
    db.execute("DELETE FROM duplicate_groups")
    db.execute("UPDATE documents SET duplicate_group_id = NULL, is_duplicate = false")
    
    # Group documents by checksum
    checksum_groups = db.execute("""
        SELECT checksum, array_agg(id) as document_ids
        FROM documents 
        WHERE is_deleted = false AND checksum IS NOT NULL
        GROUP BY checksum 
        HAVING COUNT(*) > 1
    """).fetchall()
    
    for group in checksum_groups:
        document_ids = group.document_ids
        
        # Create duplicate group
        duplicate_group = dedup_service.create_duplicate_group(document_ids)
        print(f"Created duplicate group {duplicate_group.id} for checksum {group.checksum}")
    
    db.commit()
    db.close()

rebuild_duplicate_groups()
EOF
```

#### Error Log Cleanup
```bash
# Clean up old resolved errors
psql -d querybox_core -c "
DELETE FROM error_logs 
WHERE resolved = true 
  AND resolved_at < NOW() - INTERVAL '90 days';
"

# Archive old error logs
psql -d querybox_core -c "
INSERT INTO error_logs_archive 
SELECT * FROM error_logs 
WHERE occurred_at < NOW() - INTERVAL '1 year';

DELETE FROM error_logs 
WHERE occurred_at < NOW() - INTERVAL '1 year';
"
```

---

## Summary

The Additional Features Implementation successfully enhances QueryBox Core with enterprise-grade capabilities:

1. **SHA256 Checksum System** providing cryptographic integrity verification for all documents
2. **Intelligent Duplicate Detection** with workspace-scoped and global deduplication capabilities
3. **Comprehensive Error Handling** with automatic recovery strategies and detailed diagnostics
4. **Enhanced Database Model** supporting rich metadata, audit trails, and relationship tracking
5. **Advanced Monitoring** with detailed metrics collection and performance analytics
6. **Security Enhancements** including secure checksum comparison and metadata sanitization
7. **Production-Ready Architecture** with proper error recovery, logging, and integration points

These features transform QueryBox Core from a basic upload system into a production-grade document management platform with:
- **Data Integrity**: Cryptographic verification of all stored documents
- **Storage Efficiency**: Automatic deduplication preventing redundant storage
- **Reliability**: Comprehensive error handling with automatic recovery
- **Observability**: Detailed logging and metrics for monitoring and debugging
- **Extensibility**: Clean integration points for future enhancements

You can find the complete documentation at:
`/Users/amitchandel/Documents/workspace/build5M/querybox-core/docs/technical/additional-features-implemented.md`

This implementation establishes QueryBox Core as a robust, secure, and efficient document management system ready for enterprise deployment and future feature expansion.