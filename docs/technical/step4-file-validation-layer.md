# QueryBox Core: Step 4 - File Validation Layer
## Technical Implementation Documentation

---

## 1. FEATURE OVERVIEW

### What This Step Accomplishes
Step 4 implements a comprehensive file validation layer that serves as the security gatekeeper for all document uploads into QueryBox Core:
- **File Size Validation**: Enforces 30MB upload limit with configurable thresholds
- **File Type Checking**: Validates allowed file extensions against whitelist
- **MIME Type Verification**: Uses python-magic for content-based type detection
- **Security Validation**: Prevents malicious file uploads and path traversal attacks
- **Detailed Error Reporting**: Provides specific validation failure messages
- **Performance Optimization**: Early validation prevents processing of invalid files

### Why This Step is Necessary
The File Validation Layer is critical because it:
- **Protects System Security**: Prevents upload of executable files and malicious content
- **Ensures Data Quality**: Validates files meet processing requirements before storage
- **Optimizes Resource Usage**: Rejects invalid files early in the pipeline
- **Provides User Feedback**: Clear error messages help users understand upload failures
- **Maintains System Stability**: Prevents system overload from oversized files
- **Enables Compliance**: Supports regulatory requirements for file type restrictions

### Dependencies on Previous Steps
- **Step 1**: Database schema for storing validation results and file metadata
- **Step 2**: FastAPI error handling framework for validation error responses
- **Step 3**: Upload handler infrastructure for integrating validation checks
- **External Dependencies**: python-magic library for MIME type detection

### What Future Steps Depend on This
- **Document Processing Pipeline**: Validated files proceed to extraction and chunking
- **Storage Management**: Validation results determine storage tier and retention
- **Security Scanning**: Additional security checks build on basic validation
- **Content Analysis**: Document type determines processing strategies
- **Compliance Reporting**: Validation logs support audit and compliance requirements

---

## 2. TECHNICAL IMPLEMENTATION

### Files Created/Modified

#### Core Validation Implementation
```
/backend/app/services/validation/
├── __init__.py                    # Validation module initialization
├── file_validator.py             # Main file validation service
├── size_validator.py             # File size validation logic
├── type_validator.py             # File type and MIME validation
├── security_validator.py         # Security-focused validation
└── validation_results.py         # Validation result models

/backend/app/core/
├── validation_config.py          # Validation configuration
└── file_config.py                # File type and size configuration

/backend/app/utils/
├── mime_detector.py              # MIME type detection utilities
├── file_analyzer.py              # File content analysis
└── security_scanner.py           # Security scanning utilities
```

#### Enhanced Upload Integration
```
/backend/app/api/v1/endpoints/
└── upload.py                     # Enhanced with validation layer

/backend/app/schemas/
├── validation.py                 # Validation request/response schemas
└── errors.py                     # Validation error schemas

/backend/app/exceptions/
├── validation_exceptions.py      # Custom validation exceptions
└── file_exceptions.py            # File-specific exceptions
```

#### Configuration Updates
```
/backend/app/core/
├── config.py                     # Enhanced with validation settings
└── settings/
    ├── file_limits.py            # File size and type limits
    ├── mime_types.py             # MIME type configurations
    └── security_rules.py         # Security validation rules
```

### Key Classes and Functions

#### Main File Validator (`/backend/app/services/validation/file_validator.py`)
```python
class FileValidator:
    """Comprehensive file validation service"""
    
    def __init__(self, config: ValidationConfig):
        self.config = config
        self.size_validator = SizeValidator(config.size_limits)
        self.type_validator = TypeValidator(config.allowed_types)
        self.security_validator = SecurityValidator(config.security_rules)
        self.mime_detector = MimeDetector()
    
    async def validate_file(
        self, 
        file: UploadFile,
        context: ValidationContext = None
    ) -> ValidationResult:
        """
        Comprehensive file validation with detailed results
        
        Performs:
        - File size validation
        - Extension validation  
        - MIME type verification
        - Security scanning
        - Content analysis
        """
        
    async def validate_batch(
        self,
        files: List[UploadFile]
    ) -> List[ValidationResult]:
        """Validate multiple files efficiently"""
        
    def get_validation_summary(
        self,
        results: List[ValidationResult]
    ) -> ValidationSummary:
        """Generate validation summary for batch operations"""
```

#### Size Validator (`/backend/app/services/validation/size_validator.py`)
```python
class SizeValidator:
    """File size validation with configurable limits"""
    
    def __init__(self, size_config: SizeConfig):
        self.max_size = size_config.max_file_size
        self.min_size = size_config.min_file_size
        self.large_file_threshold = size_config.large_file_threshold
    
    async def validate_size(self, file: UploadFile) -> SizeValidationResult:
        """
        Validate file size with memory-efficient checking
        
        Features:
        - Streaming size calculation
        - Early termination on oversized files
        - Large file detection
        - Memory usage optimization
        """
        
    def get_size_category(self, size: int) -> str:
        """Categorize file size for processing optimization"""
        
    def estimate_processing_time(self, size: int) -> timedelta:
        """Estimate processing time based on file size"""
```

#### Type Validator (`/backend/app/services/validation/type_validator.py`)
```python
class TypeValidator:
    """File type validation with extension and MIME checking"""
    
    def __init__(self, type_config: TypeConfig):
        self.allowed_extensions = type_config.allowed_extensions
        self.allowed_mime_types = type_config.allowed_mime_types
        self.mime_mapping = type_config.extension_mime_mapping
    
    async def validate_type(
        self, 
        filename: str, 
        content: bytes
    ) -> TypeValidationResult:
        """
        Two-tier file type validation:
        1. Extension whitelist checking
        2. Content-based MIME detection
        """
        
    async def detect_actual_type(self, content: bytes) -> str:
        """Detect actual file type from content using python-magic"""
        
    def is_extension_allowed(self, filename: str) -> bool:
        """Check if file extension is in whitelist"""
        
    def validate_mime_consistency(
        self, 
        filename: str, 
        detected_mime: str
    ) -> bool:
        """Verify MIME type matches file extension"""
```

#### Security Validator (`/backend/app/services/validation/security_validator.py`)
```python
class SecurityValidator:
    """Security-focused file validation"""
    
    def __init__(self, security_config: SecurityConfig):
        self.dangerous_signatures = security_config.dangerous_signatures
        self.suspicious_patterns = security_config.suspicious_patterns
        self.quarantine_rules = security_config.quarantine_rules
    
    async def validate_security(
        self, 
        filename: str, 
        content: bytes
    ) -> SecurityValidationResult:
        """
        Comprehensive security validation:
        - Malicious file signature detection
        - Executable content scanning
        - Suspicious pattern matching
        - Path traversal prevention
        """
        
    def scan_file_signatures(self, content: bytes) -> List[SecurityThreat]:
        """Scan for known malicious file signatures"""
        
    def validate_filename_security(self, filename: str) -> SecurityValidationResult:
        """Validate filename for security issues"""
        
    def should_quarantine(self, validation_result: ValidationResult) -> bool:
        """Determine if file should be quarantined"""
```

### Enhanced Upload Endpoint Integration
```python
@router.post("/", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = Form(default="default"),
    document_name: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    validator: FileValidator = Depends(get_file_validator)
) -> UploadResponse:
    """Enhanced upload endpoint with comprehensive validation"""
    
    # File validation (Step 4)
    validation_result = await validator.validate_file(file)
    
    if not validation_result.is_valid:
        raise ValidationException(
            detail=validation_result.error_details,
            validation_errors=validation_result.errors
        )
    
    # Proceed with upload if validation passes
    return await process_upload(file, validation_result, db)
```

### Database Tables Enhanced

#### validation_results Table
```sql
-- Validation result tracking
CREATE TABLE validation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id),
    
    -- Validation metadata
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    declared_mime_type VARCHAR(100),
    detected_mime_type VARCHAR(100),
    
    -- Validation status
    is_valid BOOLEAN NOT NULL,
    validation_stage VARCHAR(50), -- size|type|security|content
    
    -- Size validation
    size_valid BOOLEAN NOT NULL,
    size_category VARCHAR(20), -- small|medium|large|very_large
    
    -- Type validation  
    extension_valid BOOLEAN NOT NULL,
    mime_valid BOOLEAN NOT NULL,
    type_consistent BOOLEAN NOT NULL,
    
    -- Security validation
    security_valid BOOLEAN NOT NULL,
    security_threats TEXT[], -- Array of detected threats
    quarantined BOOLEAN DEFAULT FALSE,
    
    -- Error details
    error_code VARCHAR(50),
    error_message TEXT,
    error_details JSONB,
    
    -- Timestamps
    validated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_validation_results_document_id ON validation_results(document_id);
CREATE INDEX idx_validation_results_valid ON validation_results(is_valid);
CREATE INDEX idx_validation_results_quarantined ON validation_results(quarantined);
CREATE INDEX idx_validation_results_validated_at ON validation_results(validated_at);
```

#### Enhanced documents Table
```sql
-- Add validation tracking to documents table
ALTER TABLE documents ADD COLUMN validation_id UUID REFERENCES validation_results(id);
ALTER TABLE documents ADD COLUMN validation_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE documents ADD COLUMN validation_errors JSONB;
ALTER TABLE documents ADD COLUMN security_scanned BOOLEAN DEFAULT FALSE;
ALTER TABLE documents ADD COLUMN quarantine_reason TEXT;
```

### API Endpoints Enhanced

#### Validation-specific Endpoints
```http
# Validate file without uploading
POST /api/v1/validate/file
Content-Type: multipart/form-data
Form Data: file (required)

Response 200 OK:
{
    "valid": true,
    "validation_id": "uuid",
    "size_validation": {
        "valid": true,
        "size_bytes": 1048576,
        "size_category": "medium"
    },
    "type_validation": {
        "valid": true,
        "extension": ".pdf",
        "detected_mime": "application/pdf",
        "consistent": true
    },
    "security_validation": {
        "valid": true,
        "threats_detected": [],
        "quarantine_required": false
    }
}

# Get validation rules
GET /api/v1/validate/rules
Response: Current validation configuration

# Batch validation
POST /api/v1/validate/batch
Content-Type: multipart/form-data
Form Data: files[] (multiple files)
```

### Validation Schemas

#### Validation Result Schema
```python
class ValidationResult(BaseModel):
    """Comprehensive validation result"""
    
    validation_id: UUID
    is_valid: bool
    validation_timestamp: datetime
    
    # File metadata
    filename: str
    file_size: int
    declared_mime_type: Optional[str]
    detected_mime_type: str
    
    # Validation components
    size_validation: SizeValidationResult
    type_validation: TypeValidationResult
    security_validation: SecurityValidationResult
    
    # Error details
    errors: List[ValidationError]
    warnings: List[ValidationWarning]
    
    # Processing recommendations
    recommended_action: str  # proceed|reject|quarantine|review
    processing_hints: Dict[str, Any]

class ValidationError(BaseModel):
    """Validation error details"""
    
    error_code: str
    error_type: str  # size|type|security|content
    message: str
    field: Optional[str]
    details: Optional[Dict[str, Any]]
    severity: str  # error|warning|info
```

---

## 3. DATA FLOW

### Complete Validation Flow
```
1. File Upload Request → FastAPI receives multipart form data
2. Pre-validation Setup → Extract file metadata and prepare validation context
3. Size Validation → Stream-based size checking with early termination
4. Type Validation → Extension checking + MIME type detection
5. Security Validation → Malicious content scanning and threat detection
6. Result Aggregation → Combine all validation results into unified response
7. Database Logging → Store validation results for audit and analysis
8. Decision Making → Proceed, reject, or quarantine based on validation
9. Response Generation → Return detailed validation results to client
```

### Detailed Validation Steps

#### Step 1: Pre-validation Setup
```python
# Extract file metadata
file_info = {
    'filename': file.filename,
    'declared_size': file.size,
    'declared_mime': file.content_type,
    'upload_context': {
        'workspace_id': workspace_id,
        'user_agent': request.headers.get('user-agent'),
        'ip_address': request.client.host
    }
}

# Create validation context
validation_context = ValidationContext(
    file_info=file_info,
    validation_rules=get_validation_rules(workspace_id),
    security_level=get_security_level(workspace_id)
)
```

#### Step 2: Size Validation Flow
```python
# Memory-efficient size validation
async def validate_file_size(file: UploadFile) -> SizeValidationResult:
    total_size = 0
    chunk_size = 8192
    max_size = config.MAX_FILE_SIZE
    
    # Stream file content for size calculation
    while chunk := await file.read(chunk_size):
        total_size += len(chunk)
        
        # Early termination for oversized files
        if total_size > max_size:
            return SizeValidationResult(
                valid=False,
                actual_size=total_size,
                max_allowed=max_size,
                error_code="FILE_TOO_LARGE",
                error_message=f"File exceeds maximum size of {max_size/1024/1024:.1f}MB"
            )
    
    # Reset file position for further processing
    await file.seek(0)
    
    return SizeValidationResult(
        valid=True,
        actual_size=total_size,
        size_category=get_size_category(total_size)
    )
```

#### Step 3: Type Validation Flow
```python
# Two-tier type validation
async def validate_file_type(filename: str, content: bytes) -> TypeValidationResult:
    result = TypeValidationResult()
    
    # Tier 1: Extension validation
    file_extension = os.path.splitext(filename)[1].lower()
    result.extension = file_extension
    result.extension_valid = file_extension in ALLOWED_EXTENSIONS
    
    if not result.extension_valid:
        result.valid = False
        result.error_code = "EXTENSION_NOT_ALLOWED"
        result.error_message = f"File extension '{file_extension}' is not allowed"
        return result
    
    # Tier 2: MIME type detection
    detected_mime = magic.from_buffer(content, mime=True)
    result.detected_mime = detected_mime
    result.declared_mime = get_declared_mime(filename)
    
    # Consistency check
    expected_mime = EXTENSION_MIME_MAPPING.get(file_extension)
    result.mime_consistent = detected_mime == expected_mime
    result.mime_valid = detected_mime in ALLOWED_MIME_TYPES
    
    if not result.mime_valid:
        result.valid = False
        result.error_code = "MIME_TYPE_NOT_ALLOWED"
        result.error_message = f"MIME type '{detected_mime}' is not allowed"
    elif not result.mime_consistent:
        result.valid = False
        result.error_code = "MIME_EXTENSION_MISMATCH"
        result.error_message = f"File content ({detected_mime}) doesn't match extension ({file_extension})"
    else:
        result.valid = True
    
    return result
```

#### Step 4: Security Validation Flow
```python
# Comprehensive security scanning
async def validate_file_security(filename: str, content: bytes) -> SecurityValidationResult:
    result = SecurityValidationResult()
    threats = []
    
    # Filename security check
    if is_suspicious_filename(filename):
        threats.append(SecurityThreat(
            type="SUSPICIOUS_FILENAME",
            severity="medium",
            description="Filename contains suspicious patterns"
        ))
    
    # File signature scanning
    for signature, threat_info in DANGEROUS_SIGNATURES.items():
        if content.startswith(signature):
            threats.append(SecurityThreat(
                type="MALICIOUS_SIGNATURE",
                severity="high", 
                description=f"File contains {threat_info['description']} signature",
                details=threat_info
            ))
    
    # Content pattern scanning
    for pattern in SUSPICIOUS_PATTERNS:
        if pattern.search(content):
            threats.append(SecurityThreat(
                type="SUSPICIOUS_CONTENT",
                severity="medium",
                description=f"File contains suspicious content pattern"
            ))
    
    # Determine final security status
    high_threats = [t for t in threats if t.severity == "high"]
    
    result.threats = threats
    result.valid = len(high_threats) == 0
    result.quarantine_required = len(high_threats) > 0
    
    if not result.valid:
        result.error_code = "SECURITY_THREAT_DETECTED"
        result.error_message = f"Detected {len(high_threats)} high-severity security threats"
    
    return result
```

#### Step 5: Result Aggregation and Decision
```python
# Combine all validation results
def aggregate_validation_results(
    size_result: SizeValidationResult,
    type_result: TypeValidationResult, 
    security_result: SecurityValidationResult
) -> ValidationResult:
    
    # Overall validation status
    is_valid = all([
        size_result.valid,
        type_result.valid,
        security_result.valid
    ])
    
    # Collect all errors
    errors = []
    if not size_result.valid:
        errors.extend(size_result.errors)
    if not type_result.valid:
        errors.extend(type_result.errors)
    if not security_result.valid:
        errors.extend(security_result.errors)
    
    # Determine recommended action
    if security_result.quarantine_required:
        recommended_action = "quarantine"
    elif is_valid:
        recommended_action = "proceed"
    else:
        recommended_action = "reject"
    
    return ValidationResult(
        validation_id=uuid.uuid4(),
        is_valid=is_valid,
        recommended_action=recommended_action,
        size_validation=size_result,
        type_validation=type_result,
        security_validation=security_result,
        errors=errors
    )
```

---

## 4. VALIDATIONS & CONSTRAINTS

### File Size Constraints
```python
class SizeConstraints:
    # Size limits (configurable)
    MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB default
    MIN_FILE_SIZE = 1  # 1 byte minimum
    LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB threshold
    
    # Size categories for processing optimization
    SIZE_CATEGORIES = {
        'tiny': (0, 1024),  # 0-1KB
        'small': (1024, 1024 * 1024),  # 1KB-1MB
        'medium': (1024 * 1024, 10 * 1024 * 1024),  # 1MB-10MB
        'large': (10 * 1024 * 1024, 30 * 1024 * 1024),  # 10MB-30MB
    }
    
    # Processing time estimates
    PROCESSING_TIME_ESTIMATES = {
        'tiny': 0.1,    # 100ms
        'small': 1.0,   # 1 second
        'medium': 5.0,  # 5 seconds
        'large': 15.0,  # 15 seconds
    }
```

### File Type Constraints
```python
class TypeConstraints:
    # Allowed file extensions (whitelist approach)
    ALLOWED_EXTENSIONS = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
        '.html': 'text/html',
        '.csv': 'text/csv',
        '.json': 'application/json',
        '.xml': 'application/xml'
    }
    
    # Allowed MIME types
    ALLOWED_MIME_TYPES = set(ALLOWED_EXTENSIONS.values())
    
    # MIME type aliases (some files may have slightly different MIME types)
    MIME_ALIASES = {
        'text/x-markdown': 'text/markdown',
        'application/x-json': 'application/json',
        'text/xml': 'application/xml'
    }
    
    # Dangerous file types (explicitly blocked)
    BLOCKED_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif',
        '.vbs', '.js', '.jar', '.app', '.deb', '.rpm',
        '.dmg', '.pkg', '.msi', '.dll', '.so', '.dylib'
    }
```

### Security Constraints
```python
class SecurityConstraints:
    # Dangerous file signatures (magic bytes)
    DANGEROUS_SIGNATURES = {
        b'\x4d\x5a': {'type': 'PE_EXECUTABLE', 'description': 'Windows executable'},
        b'\x7f\x45\x4c\x46': {'type': 'ELF_EXECUTABLE', 'description': 'Linux executable'},
        b'\xca\xfe\xba\xbe': {'type': 'MACH_O', 'description': 'macOS executable'},
        b'\x50\x4b\x03\x04\x14\x00\x06\x00': {'type': 'OFFICE_MACRO', 'description': 'Office file with macros'},
        b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1': {'type': 'OLE_COMPOUND', 'description': 'OLE compound document'},
    }
    
    # Suspicious filename patterns
    SUSPICIOUS_PATTERNS = [
        r'\.exe\.',  # Double extension
        r'\.scr\.',  # Screen saver extension
        r'\.\w{2,4}\.exe$',  # Multiple extensions ending in exe
        r'^\.{1,2}[/\\]',  # Path traversal attempts
        r'[<>:"|?*]',  # Invalid filename characters
        r'^\s*$',  # Empty or whitespace-only names
    ]
    
    # Content scanning patterns (regex)
    MALICIOUS_CONTENT_PATTERNS = [
        rb'eval\s*\(',  # JavaScript eval
        rb'<script[^>]*>',  # Script tags
        rb'document\.write',  # DOM manipulation
        rb'base64_decode',  # Base64 decoding (potential obfuscation)
        rb'shell_exec',  # Shell execution
    ]
    
    # Quarantine rules
    QUARANTINE_RULES = {
        'high_threat_count': 1,  # Quarantine if 1+ high-severity threats
        'medium_threat_threshold': 3,  # Quarantine if 3+ medium-severity threats
        'suspicious_filename': True,  # Quarantine suspicious filenames
        'unknown_mime_type': False,  # Don't quarantine unknown MIME types
    }
```

### Validation Business Rules
```python
class ValidationRules:
    # File validation order (fail-fast approach)
    VALIDATION_ORDER = [
        'filename_security',  # Check filename first (fastest)
        'file_size',          # Check size before reading content
        'file_extension',     # Check extension before MIME detection
        'mime_type',          # Detect and validate MIME type
        'content_security',   # Deep content scanning (slowest)
    ]
    
    # Validation timeouts
    VALIDATION_TIMEOUTS = {
        'size_check': 5.0,      # 5 seconds max for size validation
        'mime_detection': 10.0,  # 10 seconds max for MIME detection
        'security_scan': 30.0,   # 30 seconds max for security scanning
        'total_validation': 60.0, # 1 minute max total validation time
    }
    
    # Memory limits for validation
    MAX_CONTENT_SCAN_SIZE = 50 * 1024 * 1024  # 50MB max for content scanning
    CHUNK_SIZE_FOR_SCANNING = 1024 * 1024     # 1MB chunks for large files
    
    # Validation bypass rules (for admin operations)
    BYPASS_CONDITIONS = {
        'admin_upload': False,      # Admins must still follow validation
        'system_migration': True,   # System migrations can bypass validation
        'trusted_source': False,    # No trusted sources by default
    }
```

---

## 5. CONFIGURATION

### Environment Variables
```bash
# File Size Configuration
MAX_FILE_SIZE=31457280                    # 30MB in bytes
MIN_FILE_SIZE=1                           # 1 byte minimum
LARGE_FILE_THRESHOLD=10485760             # 10MB threshold

# File Type Configuration
ALLOWED_EXTENSIONS='[".pdf",".docx",".xlsx",".pptx",".txt",".md",".html",".csv",".json",".xml"]'
ENABLE_MIME_VALIDATION=true               # Enable MIME type checking
STRICT_MIME_CHECKING=true                 # Strict MIME/extension consistency

# Security Configuration
ENABLE_SECURITY_SCANNING=true            # Enable security threat detection
QUARANTINE_SUSPICIOUS_FILES=true         # Quarantine files with threats
SECURITY_SCAN_TIMEOUT=30                  # Security scan timeout in seconds
MAX_SECURITY_SCAN_SIZE=52428800          # 50MB max for security scanning

# Validation Performance
VALIDATION_TIMEOUT=60                     # Total validation timeout in seconds
VALIDATION_CHUNK_SIZE=1048576            # 1MB chunks for large files
PARALLEL_VALIDATION=true                 # Enable parallel validation steps
CACHE_VALIDATION_RESULTS=true           # Cache validation results

# Error Handling
DETAILED_VALIDATION_ERRORS=true         # Return detailed error messages
LOG_VALIDATION_FAILURES=true            # Log validation failures
VALIDATION_METRICS_ENABLED=true         # Collect validation metrics

# Integration Settings
VALIDATION_DATABASE_LOGGING=true        # Store validation results in database
VALIDATION_RESULT_TTL=86400             # Validation result cache TTL (24 hours)
ASYNC_VALIDATION_ENABLED=false          # Async validation (future feature)
```

### Default Configuration Values
```python
class ValidationConfig:
    # File constraints
    MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB
    MIN_FILE_SIZE = 1
    LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB
    
    # Validation timeouts
    SIZE_VALIDATION_TIMEOUT = 5.0
    TYPE_VALIDATION_TIMEOUT = 10.0
    SECURITY_VALIDATION_TIMEOUT = 30.0
    TOTAL_VALIDATION_TIMEOUT = 60.0
    
    # Performance settings
    CHUNK_SIZE = 1024 * 1024  # 1MB
    MAX_PARALLEL_VALIDATIONS = 5
    VALIDATION_CACHE_SIZE = 1000
    
    # Security settings
    ENABLE_CONTENT_SCANNING = True
    QUARANTINE_THREATS = True
    SECURITY_SCAN_DEPTH = 'standard'  # light|standard|deep
    
    # Error handling
    FAIL_ON_FIRST_ERROR = True
    COLLECT_ALL_ERRORS = False
    RETURN_DETAILED_ERRORS = True
```

### Validation Rules Configuration
```python
# validation_rules.json
{
    "file_size": {
        "max_size_bytes": 31457280,
        "min_size_bytes": 1,
        "size_categories": {
            "small": [0, 1048576],
            "medium": [1048576, 10485760],
            "large": [10485760, 31457280]
        }
    },
    "file_types": {
        "allowed_extensions": [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md", ".html", ".csv", ".json", ".xml"],
        "allowed_mime_types": [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/markdown",
            "text/html",
            "text/csv",
            "application/json",
            "application/xml"
        ],
        "strict_mime_checking": true
    },
    "security": {
        "enable_signature_scanning": true,
        "enable_content_scanning": true,
        "quarantine_policy": "auto",
        "threat_sensitivity": "medium"
    }
}
```

### Docker Dependencies
```yaml
services:
  backend:
    environment:
      # Validation configuration
      - MAX_FILE_SIZE=31457280
      - ENABLE_SECURITY_SCANNING=true
      - VALIDATION_TIMEOUT=60
    volumes:
      # Mount validation rules
      - ./config/validation_rules.json:/app/config/validation_rules.json:ro
      # Mount quarantine directory
      - ./storage/quarantine:/app/storage/quarantine
    
  # External dependencies for validation
  clamav:  # Future: Antivirus scanning
    image: clamav/clamav:latest
    container_name: querybox-clamav
    volumes:
      - clamav_data:/var/lib/clamav
    networks:
      - querybox-network
```

---

## 6. ERROR HANDLING

### Validation Exception Hierarchy
```python
# Base validation exceptions
class ValidationException(HTTPException):
    """Base validation exception with detailed error information"""
    
    def __init__(
        self,
        detail: str,
        validation_errors: List[ValidationError] = None,
        status_code: int = 400
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.validation_errors = validation_errors or []

# Specific validation exceptions
class FileSizeValidationError(ValidationException):
    """File size validation failure"""
    
    def __init__(self, actual_size: int, max_size: int):
        detail = f"File size {actual_size/1024/1024:.1f}MB exceeds maximum {max_size/1024/1024:.1f}MB"
        super().__init__(detail=detail, status_code=413)

class FileTypeValidationError(ValidationException):
    """File type validation failure"""
    
    def __init__(self, filename: str, detected_type: str, reason: str):
        detail = f"File '{filename}' validation failed: {reason}"
        super().__init__(detail=detail, status_code=400)

class SecurityValidationError(ValidationException):
    """Security validation failure"""
    
    def __init__(self, threats: List[SecurityThreat]):
        threat_count = len(threats)
        detail = f"Security validation failed: {threat_count} threat(s) detected"
        super().__init__(detail=detail, status_code=400)

class ValidationTimeoutError(ValidationException):
    """Validation timeout exceeded"""
    
    def __init__(self, timeout_seconds: int, stage: str):
        detail = f"Validation timeout ({timeout_seconds}s) exceeded during {stage}"
        super().__init__(detail=detail, status_code=408)
```

### Error Response Format
```json
{
    "detail": "File validation failed",
    "error_code": "VALIDATION_FAILED",
    "validation_errors": [
        {
            "error_type": "file_size",
            "error_code": "FILE_TOO_LARGE",
            "message": "File size 35.5MB exceeds maximum 30.0MB",
            "field": "file",
            "severity": "error",
            "details": {
                "actual_size_bytes": 37224448,
                "max_size_bytes": 31457280,
                "size_category": "oversized"
            }
        },
        {
            "error_type": "file_type",
            "error_code": "EXTENSION_NOT_ALLOWED",
            "message": "File extension '.exe' is not allowed",
            "field": "file.filename",
            "severity": "error",
            "details": {
                "extension": ".exe",
                "allowed_extensions": [".pdf", ".docx", ".txt", "..."]
            }
        }
    ],
    "validation_summary": {
        "total_errors": 2,
        "total_warnings": 0,
        "validation_time_ms": 125,
        "recommended_action": "reject"
    }
}
```

### Error Recovery Mechanisms
```python
async def validate_with_recovery(
    file: UploadFile,
    max_retries: int = 3
) -> ValidationResult:
    """Validation with automatic retry for transient failures"""
    
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            # Reset file position before retry
            await file.seek(0)
            
            # Attempt validation
            return await validator.validate_file(file)
            
        except ValidationTimeoutError as e:
            # Retry on timeout
            retry_count += 1
            last_exception = e
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
            
        except (IOError, OSError) as e:
            # Retry on I/O errors
            retry_count += 1
            last_exception = e
            await asyncio.sleep(1)
            
        except ValidationException as e:
            # Don't retry validation logic errors
            raise e
    
    # All retries exhausted
    raise ValidationException(
        detail=f"Validation failed after {max_retries} retries: {str(last_exception)}",
        status_code=500
    )
```

### Quarantine Handling
```python
async def handle_quarantine_file(
    file: UploadFile,
    validation_result: ValidationResult,
    threats: List[SecurityThreat]
) -> QuarantineResult:
    """Handle files that need quarantine"""
    
    # Generate quarantine ID
    quarantine_id = uuid.uuid4()
    quarantine_path = f"quarantine/{quarantine_id}"
    
    try:
        # Store file in quarantine
        quarantine_content = await file.read()
        await storage.store_quarantine_file(quarantine_content, quarantine_path)
        
        # Create quarantine record
        quarantine_record = QuarantineRecord(
            id=quarantine_id,
            original_filename=file.filename,
            quarantine_reason="Security threats detected",
            threats=threats,
            quarantined_at=datetime.utcnow(),
            review_required=True,
            auto_delete_at=datetime.utcnow() + timedelta(days=30)
        )
        
        # Log quarantine action
        logger.warning("File quarantined", extra={
            "quarantine_id": str(quarantine_id),
            "filename": file.filename,
            "threats": [t.type for t in threats],
            "threat_count": len(threats)
        })
        
        return QuarantineResult(
            quarantined=True,
            quarantine_id=quarantine_id,
            review_required=True,
            threats=threats
        )
        
    except Exception as e:
        logger.error("Quarantine operation failed", extra={
            "filename": file.filename,
            "error": str(e)
        })
        raise ValidationException(
            detail="Failed to quarantine suspicious file",
            status_code=500
        )
```

### Validation Logging
```python
# Comprehensive validation logging
class ValidationLogger:
    def log_validation_start(self, filename: str, file_size: int):
        logger.info("Validation started", extra={
            "event": "validation_started",
            "filename": filename,
            "file_size": file_size,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def log_validation_success(self, result: ValidationResult):
        logger.info("Validation successful", extra={
            "event": "validation_success",
            "validation_id": str(result.validation_id),
            "filename": result.filename,
            "validation_time_ms": result.processing_time_ms,
            "size_category": result.size_validation.size_category
        })
    
    def log_validation_failure(self, result: ValidationResult):
        logger.warning("Validation failed", extra={
            "event": "validation_failed",
            "validation_id": str(result.validation_id),
            "filename": result.filename,
            "error_count": len(result.errors),
            "errors": [e.error_code for e in result.errors],
            "recommended_action": result.recommended_action
        })
    
    def log_security_threat(self, threat: SecurityThreat, filename: str):
        logger.error("Security threat detected", extra={
            "event": "security_threat",
            "filename": filename,
            "threat_type": threat.type,
            "severity": threat.severity,
            "description": threat.description
        })
```

---

## 7. TESTING CHECKLIST

### Size Validation Testing
```bash
# Create test files of various sizes
dd if=/dev/zero of=tiny.txt bs=1 count=100          # 100 bytes
dd if=/dev/zero of=small.txt bs=1024 count=100      # 100KB
dd if=/dev/zero of=medium.txt bs=1024 count=5120    # 5MB
dd if=/dev/zero of=large.txt bs=1024 count=20480    # 20MB
dd if=/dev/zero of=max.txt bs=1024 count=30720      # 30MB (at limit)
dd if=/dev/zero of=oversized.txt bs=1024 count=35840 # 35MB (over limit)

# Test size validation
curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@tiny.txt"
# Expected: Success, size_category="tiny"

curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@oversized.txt"
# Expected: 413 error, FILE_TOO_LARGE
```

### Type Validation Testing
```bash
# Test allowed file types
curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@document.pdf"
# Expected: Success, type validation passes

curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@document.docx"
# Expected: Success, Office document validated

curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@data.csv"
# Expected: Success, CSV format validated

# Test blocked file types
curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@malware.exe"
# Expected: 400 error, EXTENSION_NOT_ALLOWED

# Test MIME type consistency
# Create fake PDF (rename .exe to .pdf)
cp malware.exe fake_document.pdf
curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@fake_document.pdf"
# Expected: 400 error, MIME_EXTENSION_MISMATCH
```

### Security Validation Testing
```bash
# Test executable files
curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@program.exe"
# Expected: 400 error, security threat detected

# Test suspicious filenames
curl -X POST http://localhost:8000/api/v1/validate/file \
    -F "file=@document.pdf" \
    -F "filename=../../../etc/passwd"
# Expected: 400 error, suspicious filename

# Test double extensions
curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@document.pdf.exe"
# Expected: 400 error, suspicious filename pattern

# Test empty files
touch empty.txt
curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@empty.txt"
# Expected: Success (empty files are allowed)
```

### Batch Validation Testing
```bash
# Test multiple files validation
curl -X POST http://localhost:8000/api/v1/validate/batch \
    -F "files=@document1.pdf" \
    -F "files=@document2.docx" \
    -F "files=@data.csv" \
    -F "files=@malware.exe"
# Expected: Mixed results - 3 success, 1 failure
```

### Performance Testing
```bash
# Test validation timeout
# Create very large file (near limit)
dd if=/dev/zero of=near_max.txt bs=1024 count=30000  # ~30MB

time curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@near_max.txt"
# Expected: Complete within 60 seconds (validation timeout)

# Test concurrent validation
for i in {1..10}; do
    curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@test$i.pdf" &
done
wait
# Expected: All validations complete successfully
```

### Error Handling Testing
```bash
# Test invalid requests
curl -X POST http://localhost:8000/api/v1/validate/file
# Expected: 422 error, missing file

curl -X POST http://localhost:8000/api/v1/validate/file -F "notafile=test"
# Expected: 422 error, invalid field name

# Test corrupted file
echo "corrupted content" > corrupted.pdf
curl -X POST http://localhost:8000/api/v1/validate/file -F "file=@corrupted.pdf"
# Expected: 400 error, MIME type mismatch
```

### Expected Behaviors
- **Validation Speed**: Files under 10MB validated in <5 seconds
- **Accuracy**: 100% accuracy in detecting file types and sizes
- **Security**: All executable files and malicious content blocked
- **Error Details**: Clear, actionable error messages for all failures
- **Performance**: Handle 50+ concurrent validations without degradation

---

## 8. MONITORING & METRICS

### Validation Metrics Collection
```python
# Validation-specific metrics
validation_total = Counter(
    'file_validations_total',
    'Total file validations performed',
    ['status', 'file_type', 'size_category']
)

validation_duration = Histogram(
    'file_validation_duration_seconds',
    'Time spent validating files',
    ['validation_type', 'file_size_category'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

validation_errors = Counter(
    'file_validation_errors_total',
    'File validation errors by type',
    ['error_type', 'error_code']
)

security_threats = Counter(
    'security_threats_detected_total',
    'Security threats detected during validation',
    ['threat_type', 'severity']
)

quarantine_actions = Counter(
    'quarantine_actions_total',
    'Files quarantined due to security threats',
    ['quarantine_reason']
)

# File type distribution
file_type_distribution = Counter(
    'validated_file_types_total',
    'Distribution of validated file types',
    ['mime_type', 'extension']
)

# Size distribution
file_size_distribution = Histogram(
    'validated_file_sizes_bytes',
    'Distribution of validated file sizes',
    buckets=[1024, 10240, 102400, 1048576, 10485760, 31457280]  # 1KB to 30MB
)
```

### Validation Log Entries
```json
// Successful validation
{
    "timestamp": "2024-11-15T10:30:00Z",
    "level": "INFO",
    "event": "validation_completed",
    "validation_id": "val-uuid",
    "filename": "report.pdf",
    "file_size": 2048576,
    "mime_type": "application/pdf",
    "size_category": "medium",
    "validation_time_ms": 125,
    "security_threats": 0,
    "result": "valid"
}

// Validation failure
{
    "timestamp": "2024-11-15T10:31:00Z",
    "level": "WARNING", 
    "event": "validation_failed",
    "validation_id": "val-uuid",
    "filename": "malware.exe",
    "file_size": 1024000,
    "declared_mime": "application/octet-stream",
    "detected_mime": "application/x-executable",
    "error_code": "SECURITY_THREAT_DETECTED",
    "security_threats": 1,
    "threat_types": ["MALICIOUS_SIGNATURE"],
    "result": "rejected"
}

// Security threat detection
{
    "timestamp": "2024-11-15T10:32:00Z",
    "level": "ERROR",
    "event": "security_threat_detected",
    "filename": "suspicious.pdf",
    "threat_type": "MALICIOUS_SIGNATURE", 
    "severity": "high",
    "description": "File contains Windows executable signature",
    "quarantine_id": "quar-uuid",
    "action_taken": "quarantined"
}

// Performance warning
{
    "timestamp": "2024-11-15T10:33:00Z",
    "level": "WARNING",
    "event": "validation_slow",
    "filename": "large_document.pdf",
    "file_size": 29360128,
    "validation_time_ms": 8500,
    "threshold_ms": 5000,
    "size_category": "large"
}
```

### Health Check Integration
```json
// Enhanced health check with validation status
{
    "status": "healthy",
    "timestamp": "2024-11-15T10:30:00Z",
    "checks": {
        "validation_system": {
            "status": "healthy",
            "recent_validations": 156,
            "success_rate": 0.94,
            "average_validation_time_ms": 234,
            "security_threats_detected": 2,
            "files_quarantined": 1,
            "validation_errors": 9
        },
        "validation_components": {
            "size_validator": "healthy",
            "type_validator": "healthy", 
            "security_validator": "healthy",
            "mime_detector": "healthy"
        }
    }
}
```

### Performance Dashboards
```python
# Validation performance tracking
class ValidationMetricsCollector:
    def record_validation_start(self, filename: str, file_size: int):
        size_category = self.get_size_category(file_size)
        file_type = self.get_file_type(filename)
        
        # Start timing
        self.validation_start_time = time.time()
        
        # Record attempt
        validation_total.labels(
            status='started',
            file_type=file_type,
            size_category=size_category
        ).inc()
    
    def record_validation_complete(self, result: ValidationResult):
        duration = time.time() - self.validation_start_time
        
        # Record completion
        validation_total.labels(
            status='completed' if result.is_valid else 'failed',
            file_type=result.detected_mime_type,
            size_category=result.size_validation.size_category
        ).inc()
        
        # Record duration
        validation_duration.labels(
            validation_type='full',
            file_size_category=result.size_validation.size_category
        ).observe(duration)
        
        # Record errors
        for error in result.errors:
            validation_errors.labels(
                error_type=error.error_type,
                error_code=error.error_code
            ).inc()
        
        # Record security threats
        for threat in result.security_validation.threats:
            security_threats.labels(
                threat_type=threat.type,
                severity=threat.severity
            ).inc()
```

### Alerting Rules
```yaml
# Prometheus alerting rules for validation system
groups:
  - name: validation_alerts
    rules:
      - alert: ValidationErrorRateHigh
        expr: rate(file_validation_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High validation error rate detected"
          description: "Validation error rate is {{ $value }} errors/sec"
      
      - alert: SecurityThreatsDetected
        expr: increase(security_threats_detected_total[1h]) > 5
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Multiple security threats detected"
          description: "{{ $value }} security threats detected in the last hour"
      
      - alert: ValidationLatencyHigh
        expr: histogram_quantile(0.95, rate(file_validation_duration_seconds_bucket[5m])) > 10
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Validation latency is high"
          description: "95th percentile validation time is {{ $value }}s"
```

---

## 9. SECURITY CONSIDERATIONS

### Input Validation Security
```python
# Comprehensive input sanitization
class InputValidator:
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent security issues"""
        
        # Remove null bytes and control characters
        filename = ''.join(char for char in filename if ord(char) >= 32)
        
        # Remove or replace dangerous characters
        dangerous_chars = '<>:"/\\|?*'
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Prevent path traversal
        filename = os.path.basename(filename)
        
        # Normalize Unicode to prevent bypass attempts
        filename = unicodedata.normalize('NFKC', filename)
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        # Prevent empty filenames
        if not filename or filename.isspace():
            filename = f"unnamed_{uuid.uuid4().hex[:8]}.txt"
        
        # Prevent Windows reserved names
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + \
                        [f'COM{i}' for i in range(1,10)] + \
                        [f'LPT{i}' for i in range(1,10)]
        
        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            filename = f"file_{filename}"
        
        return filename
    
    @staticmethod
    def validate_workspace_id(workspace_id: str) -> bool:
        """Validate workspace ID format and content"""
        
        # Length check
        if len(workspace_id) > 36:
            return False
        
        # Character whitelist
        allowed_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
        if not allowed_pattern.match(workspace_id):
            return False
        
        # Prevent special values
        forbidden_values = ['..', '.', 'admin', 'system', 'root']
        if workspace_id.lower() in forbidden_values:
            return False
        
        return True
```

### Content Security Scanning
```python
class ContentSecurityScanner:
    """Advanced content security scanning"""
    
    # Known malicious file signatures
    MALICIOUS_SIGNATURES = {
        # PE executables
        b'\x4d\x5a\x90\x00': 'Windows PE executable',
        b'\x4d\x5a\x80\x00': 'Windows PE executable (alternate)',
        
        # ELF executables  
        b'\x7f\x45\x4c\x46': 'Linux ELF executable',
        
        # Mach-O executables
        b'\xca\xfe\xba\xbe': 'macOS Mach-O executable (big endian)',
        b'\xbe\xba\xfe\xca': 'macOS Mach-O executable (little endian)',
        
        # Script files with shebang
        b'#!/bin/sh': 'Shell script',
        b'#!/bin/bash': 'Bash script',
        b'#!/usr/bin/python': 'Python script',
        
        # Office documents with macros
        b'\x50\x4b\x03\x04\x14\x00\x06\x00': 'ZIP with encryption (potential macro)',
    }
    
    # Suspicious content patterns
    SUSPICIOUS_PATTERNS = [
        # JavaScript patterns
        (rb'<script[^>]*>', 'Embedded JavaScript'),
        (rb'javascript:', 'JavaScript URL'),
        (rb'eval\s*\(', 'JavaScript eval function'),
        
        # Command execution patterns
        (rb'cmd\.exe', 'Windows command execution'),
        (rb'/bin/sh', 'Unix shell execution'),
        (rb'powershell', 'PowerShell execution'),
        
        # Encoding/obfuscation patterns
        (rb'base64_decode', 'Base64 decoding'),
        (rb'hex2bin', 'Hexadecimal decoding'),
        (rb'urldecode', 'URL decoding'),
        
        # Network patterns
        (rb'http://[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', 'Hardcoded IP address'),
        (rb'wget\s+', 'File download command'),
        (rb'curl\s+', 'File download command'),
    ]
    
    async def scan_content_security(
        self, 
        content: bytes, 
        filename: str
    ) -> SecurityScanResult:
        """Perform comprehensive content security scan"""
        
        threats = []
        
        # Signature-based detection
        signature_threats = self.scan_file_signatures(content)
        threats.extend(signature_threats)
        
        # Pattern-based detection
        pattern_threats = self.scan_content_patterns(content)
        threats.extend(pattern_threats)
        
        # Filename-based detection
        filename_threats = self.scan_filename_security(filename)
        threats.extend(filename_threats)
        
        # Determine overall security status
        high_severity_threats = [t for t in threats if t.severity == 'high']
        
        return SecurityScanResult(
            clean=len(high_severity_threats) == 0,
            threats=threats,
            scan_time=time.time() - start_time,
            recommendation='quarantine' if high_severity_threats else 'allow'
        )
    
    def scan_file_signatures(self, content: bytes) -> List[SecurityThreat]:
        """Scan for known malicious file signatures"""
        threats = []
        
        for signature, description in self.MALICIOUS_SIGNATURES.items():
            if content.startswith(signature):
                threats.append(SecurityThreat(
                    type='MALICIOUS_SIGNATURE',
                    severity='high',
                    description=f'File contains {description} signature',
                    pattern=signature.hex(),
                    offset=0
                ))
        
        return threats
    
    def scan_content_patterns(self, content: bytes) -> List[SecurityThreat]:
        """Scan for suspicious content patterns"""
        threats = []
        
        # Limit scan size for performance
        scan_content = content[:self.MAX_SCAN_SIZE]
        
        for pattern, description in self.SUSPICIOUS_PATTERNS:
            matches = re.finditer(pattern, scan_content, re.IGNORECASE)
            
            for match in matches:
                threats.append(SecurityThreat(
                    type='SUSPICIOUS_PATTERN',
                    severity='medium',
                    description=f'Suspicious content detected: {description}',
                    pattern=pattern.decode('utf-8', errors='ignore'),
                    offset=match.start()
                ))
        
        return threats
```

### Access Control Integration
```python
# Future: Role-based validation rules
class ValidationAccessControl:
    """Access control for validation operations"""
    
    @staticmethod
    async def check_validation_permissions(
        user_id: str,
        workspace_id: str,
        operation: str  # validate|upload|admin
    ) -> bool:
        """Check if user has permission for validation operation"""
        
        # Get user roles
        user_roles = await get_user_roles(user_id, workspace_id)
        
        # Permission matrix
        permissions = {
            'validate': ['member', 'admin', 'owner'],
            'upload': ['member', 'admin', 'owner'],
            'admin': ['admin', 'owner'],
            'quarantine_review': ['admin', 'owner'],
            'security_override': ['owner']
        }
        
        required_roles = permissions.get(operation, [])
        return any(role in user_roles for role in required_roles)
    
    @staticmethod
    async def get_validation_rules_for_user(
        user_id: str,
        workspace_id: str
    ) -> ValidationRules:
        """Get validation rules based on user permissions"""
        
        user_roles = await get_user_roles(user_id, workspace_id)
        
        # Admins might have relaxed validation rules
        if 'admin' in user_roles or 'owner' in user_roles:
            return ValidationRules(
                max_file_size=100 * 1024 * 1024,  # 100MB for admins
                allowed_extensions=EXTENDED_ALLOWED_EXTENSIONS,
                security_level='relaxed'
            )
        
        # Regular users get standard rules
        return ValidationRules(
            max_file_size=30 * 1024 * 1024,   # 30MB for regular users
            allowed_extensions=STANDARD_ALLOWED_EXTENSIONS,
            security_level='strict'
        )
```

### Audit Trail Security
```python
class ValidationAuditLogger:
    """Secure audit logging for validation operations"""
    
    async def log_validation_attempt(
        self,
        user_id: str,
        filename: str,
        file_hash: str,
        ip_address: str,
        user_agent: str,
        result: ValidationResult
    ):
        """Log validation attempt with security context"""
        
        audit_entry = {
            'event_type': 'file_validation',
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'session_id': get_session_id(),
            'ip_address': ip_address,
            'user_agent': user_agent,
            'file_metadata': {
                'filename': filename,
                'sha256_hash': file_hash,
                'size': result.file_size,
                'mime_type': result.detected_mime_type
            },
            'validation_result': {
                'valid': result.is_valid,
                'validation_id': str(result.validation_id),
                'errors': [e.error_code for e in result.errors],
                'security_threats': len(result.security_validation.threats),
                'action_taken': result.recommended_action
            }
        }
        
        # Store in secure audit log
        await self.audit_store.log_event(audit_entry)
        
        # Alert on suspicious activity
        if not result.is_valid and result.security_validation.threats:
            await self.alert_security_team(audit_entry)
```

---

## 10. CODE PATTERNS & CONVENTIONS

### Strategy Pattern for Validation
```python
# Strategy pattern for different validation approaches
class ValidationStrategy(ABC):
    """Abstract validation strategy"""
    
    @abstractmethod
    async def validate(self, file: UploadFile) -> ValidationResult:
        pass

class StrictValidationStrategy(ValidationStrategy):
    """Strict validation for production environments"""
    
    async def validate(self, file: UploadFile) -> ValidationResult:
        # Perform all validation checks
        size_result = await self.validate_size(file)
        type_result = await self.validate_type(file)
        security_result = await self.validate_security(file)
        
        # Fail on any validation error
        return self.combine_results([size_result, type_result, security_result])

class LenientValidationStrategy(ValidationStrategy):
    """Lenient validation for development/testing"""
    
    async def validate(self, file: UploadFile) -> ValidationResult:
        # Only perform basic validation
        size_result = await self.validate_size(file)
        type_result = await self.validate_type_basic(file)
        
        # Allow warnings but fail on errors
        return self.combine_results([size_result, type_result], allow_warnings=True)

# Validation context determines strategy
class ValidationContext:
    def __init__(self, environment: str, user_role: str):
        self.environment = environment
        self.user_role = user_role
    
    def get_validation_strategy(self) -> ValidationStrategy:
        if self.environment == 'production':
            return StrictValidationStrategy()
        elif self.user_role == 'admin':
            return LenientValidationStrategy()
        else:
            return StrictValidationStrategy()
```

### Chain of Responsibility for Validation Steps
```python
# Chain of responsibility for validation pipeline
class ValidationHandler(ABC):
    """Abstract validation handler"""
    
    def __init__(self):
        self.next_handler: Optional[ValidationHandler] = None
    
    def set_next(self, handler: 'ValidationHandler') -> 'ValidationHandler':
        self.next_handler = handler
        return handler
    
    async def handle(self, request: ValidationRequest) -> ValidationResult:
        result = await self.validate(request)
        
        if result.should_continue() and self.next_handler:
            next_result = await self.next_handler.handle(request)
            return self.merge_results(result, next_result)
        
        return result
    
    @abstractmethod
    async def validate(self, request: ValidationRequest) -> ValidationResult:
        pass

class SizeValidationHandler(ValidationHandler):
    """Handle file size validation"""
    
    async def validate(self, request: ValidationRequest) -> ValidationResult:
        file = request.file
        
        if file.size > self.max_size:
            return ValidationResult(
                valid=False,
                error_code="FILE_TOO_LARGE",
                should_continue=False  # Stop pipeline on size error
            )
        
        return ValidationResult(valid=True, should_continue=True)

class TypeValidationHandler(ValidationHandler):
    """Handle file type validation"""
    
    async def validate(self, request: ValidationRequest) -> ValidationResult:
        # Type validation logic
        pass

class SecurityValidationHandler(ValidationHandler):
    """Handle security validation"""
    
    async def validate(self, request: ValidationRequest) -> ValidationResult:
        # Security validation logic
        pass

# Build validation pipeline
def build_validation_pipeline() -> ValidationHandler:
    size_handler = SizeValidationHandler()
    type_handler = TypeValidationHandler()
    security_handler = SecurityValidationHandler()
    
    # Chain handlers
    size_handler.set_next(type_handler).set_next(security_handler)
    
    return size_handler
```

### Factory Pattern for Validators
```python
# Factory pattern for creating validators
class ValidatorFactory:
    """Factory for creating appropriate validators"""
    
    _validators = {
        'size': SizeValidator,
        'type': TypeValidator, 
        'security': SecurityValidator,
        'content': ContentValidator,
        'metadata': MetadataValidator
    }
    
    @classmethod
    def create_validator(
        cls, 
        validator_type: str, 
        config: dict
    ) -> ValidationHandler:
        """Create validator instance"""
        
        validator_class = cls._validators.get(validator_type)
        if not validator_class:
            raise ValueError(f"Unknown validator type: {validator_type}")
        
        return validator_class(config)
    
    @classmethod
    def create_validation_pipeline(
        cls, 
        pipeline_config: List[dict]
    ) -> ValidationHandler:
        """Create complete validation pipeline from configuration"""
        
        handlers = []
        for step_config in pipeline_config:
            validator_type = step_config['type']
            validator_config = step_config.get('config', {})
            
            handler = cls.create_validator(validator_type, validator_config)
            handlers.append(handler)
        
        # Chain handlers together
        for i in range(len(handlers) - 1):
            handlers[i].set_next(handlers[i + 1])
        
        return handlers[0] if handlers else None

# Usage
pipeline_config = [
    {'type': 'size', 'config': {'max_size': 30 * 1024 * 1024}},
    {'type': 'type', 'config': {'allowed_extensions': ['.pdf', '.docx']}},
    {'type': 'security', 'config': {'strict_mode': True}}
]

validator = ValidatorFactory.create_validation_pipeline(pipeline_config)
```

### Observer Pattern for Validation Events
```python
# Observer pattern for validation events
class ValidationObserver(ABC):
    """Abstract observer for validation events"""
    
    @abstractmethod
    async def on_validation_start(self, event: ValidationStartEvent):
        pass
    
    @abstractmethod 
    async def on_validation_complete(self, event: ValidationCompleteEvent):
        pass
    
    @abstractmethod
    async def on_security_threat(self, event: SecurityThreatEvent):
        pass

class MetricsObserver(ValidationObserver):
    """Observer that collects validation metrics"""
    
    async def on_validation_start(self, event: ValidationStartEvent):
        validation_total.labels(status='started').inc()
    
    async def on_validation_complete(self, event: ValidationCompleteEvent):
        status = 'success' if event.result.is_valid else 'failed'
        validation_total.labels(status=status).inc()
        validation_duration.observe(event.duration)
    
    async def on_security_threat(self, event: SecurityThreatEvent):
        security_threats.labels(
            threat_type=event.threat.type,
            severity=event.threat.severity
        ).inc()

class AuditObserver(ValidationObserver):
    """Observer that logs validation events for audit"""
    
    async def on_validation_complete(self, event: ValidationCompleteEvent):
        await audit_logger.log_validation(
            event.validation_id,
            event.result,
            event.context
        )
    
    async def on_security_threat(self, event: SecurityThreatEvent):
        await audit_logger.log_security_threat(
            event.threat,
            event.filename,
            event.context
        )

# Observable validation service
class ObservableValidator:
    def __init__(self):
        self.observers: List[ValidationObserver] = []
    
    def add_observer(self, observer: ValidationObserver):
        self.observers.append(observer)
    
    async def notify_validation_start(self, event: ValidationStartEvent):
        for observer in self.observers:
            await observer.on_validation_start(event)
    
    async def notify_validation_complete(self, event: ValidationCompleteEvent):
        for observer in self.observers:
            await observer.on_validation_complete(event)
```

### Naming Conventions
- **Classes**: PascalCase (`FileValidator`, `SecurityScanner`)
- **Methods**: snake_case (`validate_file`, `scan_content`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_FILE_SIZE`, `ALLOWED_EXTENSIONS`)
- **Variables**: snake_case (`validation_result`, `file_content`)
- **Error Codes**: UPPER_SNAKE_CASE (`FILE_TOO_LARGE`, `MIME_TYPE_MISMATCH`)
- **Event Names**: snake_case (`validation_started`, `security_threat_detected`)

---

## 11. INTEGRATION POINTS

### Upload Service Integration
```python
# Integration with upload service
class EnhancedUploadService:
    def __init__(
        self,
        validator: FileValidator,
        storage: StorageService,
        db: Session
    ):
        self.validator = validator
        self.storage = storage
        self.db = db
    
    async def process_upload_with_validation(
        self,
        file: UploadFile,
        workspace_id: str,
        metadata: dict
    ) -> UploadResult:
        """Upload processing with integrated validation"""
        
        # Step 1: Validate file
        validation_result = await self.validator.validate_file(file)
        
        if not validation_result.is_valid:
            # Store validation failure for audit
            await self.store_validation_result(validation_result)
            
            raise ValidationException(
                detail="File validation failed",
                validation_errors=validation_result.errors
            )
        
        # Step 2: Handle quarantine if needed
        if validation_result.recommended_action == 'quarantine':
            return await self.quarantine_file(file, validation_result)
        
        # Step 3: Proceed with normal upload
        upload_result = await self.store_validated_file(
            file, 
            validation_result,
            workspace_id,
            metadata
        )
        
        return upload_result
```

### Database Integration
```python
# Database integration for validation results
class ValidationRepository:
    def __init__(self, db: Session):
        self.db = db
    
    async def store_validation_result(
        self,
        result: ValidationResult,
        document_id: Optional[UUID] = None
    ) -> ValidationRecord:
        """Store validation result in database"""
        
        validation_record = ValidationRecord(
            id=result.validation_id,
            document_id=document_id,
            filename=result.filename,
            file_size=result.file_size,
            declared_mime_type=result.declared_mime_type,
            detected_mime_type=result.detected_mime_type,
            is_valid=result.is_valid,
            validation_stage=result.validation_stage,
            size_valid=result.size_validation.valid,
            size_category=result.size_validation.size_category,
            extension_valid=result.type_validation.extension_valid,
            mime_valid=result.type_validation.mime_valid,
            type_consistent=result.type_validation.mime_consistent,
            security_valid=result.security_validation.valid,
            security_threats=[t.type for t in result.security_validation.threats],
            quarantined=result.recommended_action == 'quarantine',
            error_code=result.errors[0].error_code if result.errors else None,
            error_message=result.errors[0].message if result.errors else None,
            error_details=result.get_error_details_json(),
            validated_at=datetime.utcnow()
        )
        
        self.db.add(validation_record)
        await self.db.commit()
        
        return validation_record
    
    async def get_validation_stats(
        self,
        workspace_id: str,
        days: int = 7
    ) -> ValidationStats:
        """Get validation statistics for workspace"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stats_query = self.db.query(
            func.count(ValidationRecord.id).label('total_validations'),
            func.sum(case([(ValidationRecord.is_valid == True, 1)], else_=0)).label('successful_validations'),
            func.sum(case([(ValidationRecord.quarantined == True, 1)], else_=0)).label('quarantined_files'),
            func.avg(ValidationRecord.file_size).label('avg_file_size')
        ).filter(
            ValidationRecord.validated_at >= cutoff_date
        )
        
        return stats_query.first()
```

### Security Service Integration
```python
# Integration with security monitoring
class SecurityIntegration:
    def __init__(self, security_service: SecurityService):
        self.security_service = security_service
    
    async def handle_security_threat(
        self,
        threat: SecurityThreat,
        file_info: dict,
        user_context: dict
    ):
        """Handle detected security threat"""
        
        # Create security incident
        incident = SecurityIncident(
            incident_type='file_upload_threat',
            severity=threat.severity,
            description=threat.description,
            file_hash=file_info.get('hash'),
            filename=file_info.get('filename'),
            user_id=user_context.get('user_id'),
            ip_address=user_context.get('ip_address'),
            detected_at=datetime.utcnow()
        )
        
        # Report to security service
        await self.security_service.report_incident(incident)
        
        # Update threat intelligence
        if threat.severity == 'high':
            await self.security_service.update_threat_signatures(
                threat.pattern,
                threat.description
            )
        
        # Notify security team for high-severity threats
        if threat.severity == 'high':
            await self.security_service.notify_security_team(incident)
```

### Event System Integration
```python
# Event-driven integration
class ValidationEventPublisher:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def publish_validation_events(self, result: ValidationResult):
        """Publish validation events for other services"""
        
        # Base validation event
        await self.event_bus.publish(ValidationCompletedEvent(
            validation_id=result.validation_id,
            filename=result.filename,
            is_valid=result.is_valid,
            file_size=result.file_size,
            mime_type=result.detected_mime_type
        ))
        
        # Security events
        if result.security_validation.threats:
            for threat in result.security_validation.threats:
                await self.event_bus.publish(SecurityThreatDetectedEvent(
                    threat_type=threat.type,
                    severity=threat.severity,
                    filename=result.filename,
                    description=threat.description
                ))
        
        # Quarantine events
        if result.recommended_action == 'quarantine':
            await self.event_bus.publish(FileQuarantinedEvent(
                filename=result.filename,
                quarantine_reason=result.get_quarantine_reason(),
                threats=result.security_validation.threats
            ))
```

### Monitoring Integration
```python
# Integration with monitoring systems
class ValidationMonitoringIntegration:
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
    
    async def record_validation_metrics(self, result: ValidationResult):
        """Record validation metrics for monitoring"""
        
        # Performance metrics
        self.metrics.record_validation_duration(
            result.processing_time_ms,
            result.size_validation.size_category
        )
        
        # Success/failure metrics
        status = 'success' if result.is_valid else 'failed'
        self.metrics.record_validation_attempt(
            status,
            result.detected_mime_type,
            result.size_validation.size_category
        )
        
        # Security metrics
        if result.security_validation.threats:
            for threat in result.security_validation.threats:
                self.metrics.record_security_threat(
                    threat.type,
                    threat.severity
                )
        
        # Error metrics
        for error in result.errors:
            self.metrics.record_validation_error(
                error.error_type,
                error.error_code
            )
```

---

## 12. TROUBLESHOOTING GUIDE

### Common Validation Issues

#### "MIME type detection fails"
```bash
# Check python-magic installation
python3 -c "import magic; print(magic.version)"

# Test MIME detection manually
python3 -c "
import magic
with open('test.pdf', 'rb') as f:
    content = f.read()
    mime_type = magic.from_buffer(content, mime=True)
    print(f'Detected MIME type: {mime_type}')
"

# Solution: Reinstall python-magic and libmagic
pip uninstall python-magic
pip install python-magic==0.4.27

# On macOS
brew install libmagic

# On Ubuntu/Debian
sudo apt-get install libmagic1 libmagic-dev
```

#### "File size validation inconsistent"
```bash
# Check file size detection
curl -X POST http://localhost:8000/api/v1/validate/file \
    -F "file=@test.pdf" \
    -v

# Compare file sizes
ls -l test.pdf  # Actual file size
stat test.pdf   # Detailed file info

# Debug in Python
python3 -c "
import os
file_path = 'test.pdf'
size = os.path.getsize(file_path)
print(f'File size: {size} bytes ({size/1024/1024:.2f} MB)')
"

# Solution: Check for streaming vs content-length differences
# Ensure file.seek(0) after size calculation
```

#### "Security validation false positives"
```bash
# Check file signatures
hexdump -C test.pdf | head -5

# Test signature detection manually
python3 -c "
with open('test.pdf', 'rb') as f:
    content = f.read(100)  # First 100 bytes
    print(content.hex())
    print('PDF signature found:', content.startswith(b'%PDF'))
"

# Solution: Update signature database or add whitelist entries
```

#### "Validation timeout errors"
```bash
# Check validation performance
time curl -X POST http://localhost:8000/api/v1/validate/file \
    -F "file=@large_file.pdf"

# Monitor system resources during validation
top -p $(pgrep -f uvicorn)
iostat -x 1

# Solution: Increase validation timeout or optimize file handling
export VALIDATION_TIMEOUT=120  # 2 minutes
```

### Debug Commands

#### Validation Process Debugging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export VALIDATION_DEBUG=true

# Test validation with detailed output
curl -X POST http://localhost:8000/api/v1/validate/file \
    -F "file=@test.pdf" \
    -H "Accept: application/json" | jq .

# Check validation logs
tail -f logs/validation.log | grep -E "(validation_started|validation_completed|validation_failed)"
```

#### File Analysis Debugging
```python
# Manual file analysis script
python3 << 'EOF'
import asyncio
from app.services.validation.file_validator import FileValidator
from app.core.validation_config import ValidationConfig

async def debug_file_validation():
    config = ValidationConfig()
    validator = FileValidator(config)
    
    # Test file
    with open('problematic_file.pdf', 'rb') as f:
        file_content = f.read()
    
    # Debug size validation
    print(f"File size: {len(file_content)} bytes")
    print(f"Max allowed: {config.MAX_FILE_SIZE} bytes")
    print(f"Size valid: {len(file_content) <= config.MAX_FILE_SIZE}")
    
    # Debug MIME detection
    import magic
    detected_mime = magic.from_buffer(file_content, mime=True)
    print(f"Detected MIME: {detected_mime}")
    
    # Debug security scanning
    from app.services.validation.security_validator import SecurityValidator
    security_validator = SecurityValidator(config.security_rules)
    security_result = await security_validator.validate_security(
        'problematic_file.pdf', 
        file_content
    )
    print(f"Security threats: {len(security_result.threats)}")
    for threat in security_result.threats:
        print(f"  - {threat.type}: {threat.description}")

asyncio.run(debug_file_validation())
EOF
```

#### Performance Analysis
```bash
# Profile validation performance
py-spy top --pid $(pgrep -f uvicorn) --duration 60

# Memory usage analysis
memory_profiler python3 -c "
from app.services.validation.file_validator import FileValidator
# ... validation code
"

# I/O analysis
strace -e trace=read,write,open,close -p $(pgrep -f uvicorn)
```

### Database Verification Queries
```sql
-- Check validation statistics
SELECT 
    DATE(validated_at) as validation_date,
    COUNT(*) as total_validations,
    COUNT(CASE WHEN is_valid THEN 1 END) as successful_validations,
    COUNT(CASE WHEN quarantined THEN 1 END) as quarantined_files,
    AVG(file_size) as avg_file_size
FROM validation_results 
WHERE validated_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(validated_at)
ORDER BY validation_date;

-- Check validation errors by type
SELECT 
    error_code,
    COUNT(*) as error_count,
    array_agg(DISTINCT filename) as sample_files
FROM validation_results 
WHERE is_valid = false
    AND validated_at >= NOW() - INTERVAL '24 hours'
GROUP BY error_code
ORDER BY error_count DESC;

-- Check security threats detected
SELECT 
    validation_id,
    filename,
    security_threats,
    quarantined,
    validated_at
FROM validation_results 
WHERE array_length(security_threats, 1) > 0
ORDER BY validated_at DESC
LIMIT 20;

-- Check file type distribution
SELECT 
    detected_mime_type,
    COUNT(*) as file_count,
    AVG(file_size) as avg_size,
    COUNT(CASE WHEN is_valid THEN 1 END) as valid_count
FROM validation_results 
WHERE validated_at >= NOW() - INTERVAL '7 days'
GROUP BY detected_mime_type
ORDER BY file_count DESC;

-- Check validation performance
SELECT 
    size_category,
    COUNT(*) as file_count,
    AVG(EXTRACT(EPOCH FROM (validated_at - created_at)) * 1000) as avg_validation_time_ms
FROM validation_results 
WHERE validated_at >= NOW() - INTERVAL '24 hours'
GROUP BY size_category
ORDER BY avg_validation_time_ms DESC;
```

### Log Analysis Commands
```bash
# Parse validation logs for errors
grep -E "(validation_failed|security_threat)" logs/validation.log | \
    jq -r '[.timestamp, .filename, .error_code, .threat_type] | @tsv'

# Count validation results by status
grep "validation_completed" logs/validation.log | \
    jq -r '.result' | sort | uniq -c

# Find slow validations (>5 seconds)
grep "validation_completed" logs/validation.log | \
    jq 'select(.validation_time_ms > 5000)' | \
    jq -r '[.filename, .file_size, .validation_time_ms] | @tsv'

# Monitor validation throughput
grep "validation_started" logs/validation.log | \
    awk '{print substr($1,1,16)}' | \
    sort | uniq -c | tail -10

# Security threat analysis
grep "security_threat_detected" logs/validation.log | \
    jq -r '[.threat_type, .severity, .filename] | @tsv' | \
    sort | uniq -c
```

### Recovery Procedures
```bash
# Reset validation cache
redis-cli FLUSHDB

# Clear stuck validation records
psql -d querybox_core -c "
DELETE FROM validation_results 
WHERE validation_stage = 'in_progress' 
    AND created_at < NOW() - INTERVAL '1 hour';
"

# Reprocess failed validations
python3 scripts/reprocess_validations.py --failed --days=1

# Update security signatures
curl -X POST http://localhost:8000/api/v1/admin/security/update-signatures

# Check quarantine files
ls -la storage/quarantine/
python3 scripts/review_quarantine.py --pending
```

---

## Summary

Step 4 successfully implements a comprehensive File Validation Layer for QueryBox Core, providing:

1. **Multi-Layered Security Validation** with file size, type, MIME, and content security checks
2. **Advanced Threat Detection** using signature scanning and pattern matching
3. **Robust Error Handling** with detailed error messages and recovery mechanisms
4. **Performance Optimization** with streaming validation and timeout controls
5. **Comprehensive Monitoring** with metrics, logging, and audit trails
6. **Flexible Architecture** supporting different validation strategies and rules
7. **Database Integration** for validation result tracking and analytics
8. **Security-First Design** with quarantine capabilities and threat intelligence

This validation layer serves as the critical security gatekeeper for QueryBox Core, ensuring only safe, valid documents enter the system while providing detailed feedback for rejected files and comprehensive monitoring for security threats. The implementation follows established design patterns and provides extensibility for future security enhancements.