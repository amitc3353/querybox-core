# QueryBox Core: Step 6 - Metadata Management
## Technical Implementation Documentation

---

## 1. FEATURE OVERVIEW

### What This Step Accomplishes
Step 6 implements comprehensive metadata management that transforms QueryBox Core from a simple file storage system into an intelligent document processing platform:
- Structured metadata schemas leveraging existing JSONB fields for flexibility
- **Docling service integration** for intelligent document parsing (PDF, DOCX, PPTX, HTML, MD)
- Enhanced processing status tracking with granular progress monitoring
- Automatic document classification and language detection via Docling
- Content quality assessment using Docling's analysis capabilities
- Real-time status updates with progress estimation
- Atomic metadata operations integrated with storage transactions
- Simple fallback extractors for unsupported file types (TXT, CSV)
- Comprehensive audit trail for all metadata changes

### Why This Step is Necessary
Metadata Management is critical because it:
- **Enables intelligent search**: Rich metadata powers advanced search and filtering
- **Improves processing decisions**: Quality scores guide OCR and extraction strategies
- **Provides transparency**: Users see real-time progress and understand processing status
- **Supports compliance**: Complete audit trails for document lifecycle tracking
- **Optimizes performance**: Metadata caching reduces repeated analysis
- **Enhances user experience**: Automatic title, author, and content type detection
- **Enables analytics**: Structured data for document corpus analysis
- **Facilitates integration**: Standard metadata format for external systems

### Dependencies on Previous Steps
- **Step 1**: Database models with JSONB fields for metadata storage
- **Step 2**: FastAPI structure for metadata API endpoints
- **Step 3**: Upload pipeline to trigger metadata extraction
- **Step 4**: File validation provides clean input for extraction
- **Step 5**: Storage service for atomic file and metadata operations

### What Future Steps Depend on This
- **Document Processing**: Metadata guides chunking and embedding strategies
- **Search Implementation**: Metadata fields become searchable attributes
- **User Interface**: Display extracted metadata and processing progress
- **Analytics Dashboard**: Aggregate metadata for insights
- **ML Pipeline**: Document classification improves over time

---

## 2. TECHNICAL IMPLEMENTATION

### Files Created/Modified (Complete List)

#### Metadata Schema Definitions
```
/backend/app/schemas/
└── metadata.py (EXISTING - ENHANCED)    # Comprehensive metadata schemas
    - DocumentMetadata (434 lines)
    - ProcessingMetadata
    - VersionMetadata
    - MetadataExtractionRequest/Response
    - ContentQuality, DocumentType, ProcessingEngine enums
```

#### Metadata Service Implementation
```
/backend/app/services/metadata/
├── __init__.py (NEW)                    # Module exports and initialization
├── docling_service.py (NEW - 402 lines) # Main Docling orchestration service
│   └── DoclingMetadataService class
│       ├── extract_metadata() - Core extraction with fallback
│       ├── _extract_with_docling() - Docling API integration
│       ├── _extract_with_fallback() - Fallback handling
│       ├── is_healthy() - Service health check with 30s cache
│       └── refresh_metadata() - Force re-extraction
│
├── docling_client.py (NEW - 343 lines)  # Async HTTP client for Docling
│   └── DoclingClient class
│       ├── analyze_document() - Document analysis with retry
│       ├── health_check() - Docling service availability
│       ├── get_supported_formats() - Query supported MIME types
│       └── _parse_docling_response() - Response transformation
│   └── DoclingAnalysisResult dataclass
│
├── metadata_mapper.py (NEW - 397 lines) # Transform Docling → Our schema
│   └── DoclingMetadataMapper class
│       ├── map_docling_result() - Main mapping function
│       ├── create_processing_metadata() - Processing details
│       ├── _classify_document_type() - Pattern-based classification
│       ├── _assess_content_quality() - Quality scoring
│       ├── _normalize_language() - ISO 639-1 conversion
│       └── _calculate_completeness_score() - Metadata completeness
│
├── validators.py (NEW - 415 lines)      # Metadata validation utilities
│   └── MetadataValidator class
│       ├── validate_metadata() - Full DocumentMetadata validation
│       ├── validate_processing_metadata() - ProcessingMetadata checks
│       ├── _validate_title/author/keywords/etc() - Field validators
│       ├── _validate_quality_consistency() - Score/enum alignment
│       └── is_metadata_complete() - Completeness check
│   └── Helper functions:
│       ├── validate_document_metadata()
│       ├── validate_processing_metadata()
│       ├── is_metadata_complete()
│       └── get_metadata_completeness_score()
│
└── fallback_extractors/
    ├── __init__.py (NEW)
    └── text_extractor.py (NEW - 381 lines) # Simple extractors for TXT/CSV
        └── TextMetadataExtractor class
            ├── extract_metadata() - Main extraction
            ├── _decode_content() - Multi-encoding support
            ├── _extract_keywords() - Frequency-based extraction
            ├── _detect_language_basic() - Simple language detection
            ├── _calculate_quality_score() - Heuristic quality
            └── _detect_tables() - Table pattern detection
```

#### Processing Status Tracking
```
/backend/app/services/processing/
└── status_tracker.py (NEW - 410 lines)  # Enhanced status tracking
    └── ProcessingStatusTracker class
        ├── update_status() - Atomic status updates with validation
        ├── update_progress() - Real-time percentage updates
        ├── get_overall_progress() - Multi-stage progress calculation
        ├── mark_stage_completed() - Success helper
        ├── mark_stage_failed() - Failure helper with retry tracking
        ├── _validate_status_transition() - State machine enforcement
        └── _merge_processing_metadata() - JSONB merging
    └── VALID_TRANSITIONS dictionary - State machine rules
```

#### Docling Configuration
```
/backend/app/config/
└── docling_config.py (NEW - 182 lines)  # Docling service configuration
    └── DoclingSettings (Pydantic BaseSettings)
        - DOCLING_SERVICE_URL
        - DOCLING_API_KEY
        - DOCLING_REQUEST_TIMEOUT (30s default)
        - DOCLING_RETRY_ATTEMPTS (3 attempts)
        - DOCLING_MAX_FILE_SIZE_MB (100MB)
        - DOCLING_QUALITY_LEVEL (fast/balanced/high_quality)
        - DOCLING_EXTRACT_IMAGES/TABLES
        - DOCLING_OCR_ENABLED
        - DOCLING_LANGUAGE_DETECTION
        - DOCLING_FALLBACK_ENABLED
    └── Constants:
        - DOCLING_SUPPORTED_FORMATS (Set[str])
        - FALLBACK_REQUIRED_FORMATS (Set[str])
        - DOCLING_FORMAT_CONFIG (Dict[str, Dict])
    └── Helper functions:
        - is_docling_supported()
        - requires_fallback()
        - get_format_config()
        - get_max_file_size()
```

#### API Endpoints
```
/backend/app/api/v1/endpoints/
└── metadata.py (NEW - 340 lines)        # Complete REST API
    └── Endpoints:
        ├── GET /documents/{id}/metadata
        │   └── Returns: metadata, extraction_status, processing_info
        │
        ├── POST /documents/{id}/metadata/extract
        │   └── Body: MetadataExtractionRequest
        │   └── Returns: task_id, status, queued confirmation
        │
        ├── POST /documents/{id}/metadata/refresh
        │   └── Force re-extraction (always fresh)
        │   └── Returns: task_id, status
        │
        ├── GET /documents/{id}/metadata/status
        │   └── Returns: extraction_status, progress_percentage,
        │                current_operation, duration_ms, error_message
        │
        ├── POST /documents/metadata/batch-extract
        │   └── Body: List[UUID], force_reextraction flag
        │   └── Returns: task_id, document_count, queued confirmation
        │   └── Limit: Max 100 documents per batch
        │
        ├── GET /metadata/service/health
        │   └── Returns: overall_status, docling_service status,
        │                supported_formats, fallback availability
        │
        └── GET /metadata/service/info
            └── Returns: service version, capabilities, features,
                        supported formats for Docling and fallback
```

#### Background Tasks
```
/backend/app/tasks/
└── metadata_tasks.py (NEW - 341 lines)  # Celery async tasks
    └── Tasks:
        ├── extract_metadata_task(document_id, file_path, storage_path, force_reextraction)
        │   └── Decorator: @celery_app.task(bind=True, max_retries=3)
        │   └── Progress updates: 10% → 25% → 40% → 75% → 100%
        │   └── Retry: Exponential backoff (2^retry_count seconds)
        │   └── Operations:
        │       1. Set status to IN_PROGRESS
        │       2. Load file from storage
        │       3. Extract metadata via Docling service
        │       4. Store in document_metadata JSONB
        │       5. Update last_extraction_at timestamp
        │       6. Mark stage COMPLETED/FAILED
        │
        ├── refresh_metadata_task(document_id)
        │   └── Wrapper that calls extract_metadata_task with force=True
        │
        └── batch_extract_metadata_task(document_ids, force_reextraction)
            └── Validates all documents exist
            └── Queues individual extraction tasks
            └── Returns: queued_count, error_count, results
```

#### Database Migrations
```
/backend/db/migrations/
└── 006_add_metadata_indexes.sql (NEW - 235 lines)
    └── Indexes Created (18 total):
        # JSONB Indexes
        ├── idx_documents_metadata_gin (GIN on document_metadata)
        ├── idx_documents_metadata_path_ops (GIN with jsonb_path_ops)

        # Specific Field Indexes
        ├── idx_documents_metadata_title
        ├── idx_documents_metadata_author
        ├── idx_documents_metadata_language
        ├── idx_documents_metadata_doc_type
        ├── idx_documents_metadata_quality_score (numeric cast)
        ├── idx_documents_metadata_engine

        # Processing Status Indexes
        ├── idx_processing_status_active (WHERE status='in_progress')
        ├── idx_processing_status_failed (WHERE status='failed')
        ├── idx_processing_status_duration
        ├── idx_processing_status_metadata_gin

        # Extraction Timestamp Indexes
        ├── idx_documents_last_extraction
        ├── idx_documents_needs_extraction

        # Composite Indexes
        ├── idx_documents_status_extraction
        ├── idx_documents_mime_extraction
        ├── idx_documents_search_composite
        └── idx_documents_file_size

    └── Includes: Query examples, maintenance notes, rollback script
```

#### Tests
```
/backend/tests/services/metadata/
├── __init__.py (NEW)
└── test_validators.py (NEW - 340 lines)
    └── Test Classes:
        ├── TestMetadataValidator (13 test methods)
        │   ├── test_valid_metadata
        │   ├── test_empty_title
        │   ├── test_title_too_long
        │   ├── test_invalid_language_code
        │   ├── test_negative_page_count
        │   ├── test_invalid_quality_score
        │   ├── test_low_quality_warning
        │   ├── test_quality_consistency
        │   ├── test_future_timestamp
        │   ├── test_too_many_keywords
        │   └── test_invalid_confidence_scores
        │
        ├── TestProcessingMetadataValidation (4 test methods)
        │   ├── test_valid_processing_metadata
        │   ├── test_invalid_percentage
        │   ├── test_negative_duration
        │   └── test_invalid_priority
        │
        ├── TestMetadataCompletenessChecks (3 test methods)
        │   ├── test_complete_metadata
        │   ├── test_minimal_metadata
        │   └── test_incomplete_metadata
        │
        └── TestConvenienceFunctions (2 test methods)
            ├── test_validate_document_metadata_function
            └── test_strict_mode
```

#### Environment Configuration
```
/.env.example (UPDATED)
└── Added Section: "METADATA EXTRACTION CONFIGURATION (Step 6)"
    ├── Docling Service: URL, API key, timeout, retry settings
    ├── File Limits: Max size (100MB), max pages (1000)
    ├── Processing Options: Quality level, image/table extraction, OCR
    ├── Fallback: Enable/disable fallback extractors
    ├── Metadata Settings: Timeout, quality thresholds, confidence scores
    └── Feature Flags: Language detection, classification, quality assessment
```

### Key Classes and Functions

#### Metadata Schemas (`/backend/app/schemas/metadata.py`)
```python
class DocumentMetadata(BaseModel):
    """Core metadata schema for document_metadata JSONB field"""
    # File Properties
    title: Optional[str]
    author: Optional[str]
    subject: Optional[str]
    keywords: List[str]
    creator_application: Optional[str]
    
    # Technical Specifications
    page_count: Optional[int]
    word_count: Optional[int]
    character_count: Optional[int]
    language: Optional[str]
    
    # Content Analysis
    document_type: Optional[DocumentType]
    content_quality: ContentQuality
    text_quality_score: Optional[float]
    
    # Processing Metadata
    extraction_version: str
    processing_engine: str
    confidence_scores: Dict[str, float]

class ProcessingMetadata(BaseModel):
    """Enhanced metadata for status_metadata JSONB field"""
    percentage_complete: float
    current_operation: Optional[str]
    estimated_completion: Optional[datetime]
    processing_duration_ms: Optional[int]
    error_category: Optional[str]
```

#### Docling Integration Service (`/backend/app/services/metadata/docling_service.py`)
```python
class DoclingService:
    async def extract_metadata(self, file_path: str, file_content: bytes, mime_type: str) -> DocumentMetadata
    
    async def analyze_document(self, document_data: bytes) -> DoclingAnalysisResult
    
    def is_supported_format(self, mime_type: str) -> bool
    
    async def health_check(self) -> bool
```

#### Status Tracker (`/backend/app/services/processing/status_tracker.py`)
```python
class ProcessingStatusTracker:
    async def update_status(
        self,
        document_id: str,
        stage: ProcessingStageEnum,
        status: StageStatusEnum,
        metadata: Optional[ProcessingMetadata] = None
    ) -> ProcessingStatus
    
    async def update_progress(
        self,
        document_id: str,
        stage: ProcessingStageEnum,
        percentage: float,
        current_operation: Optional[str] = None
    ) -> None
    
    async def get_overall_progress(self, document_id: str) -> Dict[str, Any]
```

### Database Schema Extensions

#### Metadata Indexes for Performance
```sql
-- Text search indexes
CREATE INDEX idx_documents_metadata_title 
ON documents ((document_metadata->>'title')) 
WHERE document_metadata IS NOT NULL;

CREATE INDEX idx_documents_metadata_author 
ON documents ((document_metadata->>'author')) 
WHERE document_metadata IS NOT NULL;

-- Filter indexes
CREATE INDEX idx_documents_metadata_language 
ON documents ((document_metadata->>'language'));

CREATE INDEX idx_documents_metadata_type 
ON documents ((document_metadata->>'document_type'));

-- Date range queries
CREATE INDEX idx_documents_metadata_creation_date 
ON documents ((document_metadata->>'creation_date')::timestamp);

-- Composite index for active processing
CREATE INDEX idx_processing_status_active 
ON processing_status (document_id, stage, status) 
WHERE status IN ('in_progress', 'failed');
```

### API Endpoints Created

#### Metadata Operations
- `GET /api/v1/documents/{document_id}/metadata` - Retrieve document metadata
- `POST /api/v1/documents/{document_id}/metadata/refresh` - Re-extract metadata
- `GET /api/v1/documents/{document_id}/status` - Get processing status with progress
- `GET /api/v1/documents/search/metadata` - Search by metadata fields (future)

### Background Tasks

#### Metadata Extraction Task (`/backend/app/tasks/metadata_tasks.py`)
```python
@celery_app.task(bind=True, max_retries=3)
def extract_metadata_task(
    self,
    document_id: str,
    file_path: str,
    storage_path: str
) -> Dict[str, Any]:
    """Async metadata extraction with progress tracking"""
```

---

## 3. DATA FLOW

### Complete Metadata Extraction Flow (End-to-End)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DOCUMENT UPLOAD COMPLETE                        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Upload Endpoint (/api/v1/upload)                                   │
│  • Document saved to storage                                         │
│  • Document record created in database                               │
│  • Queue metadata extraction task                                    │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Celery Queue (Redis)                                                │
│  Task: extract_metadata_task(document_id, file_path, storage_path) │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Celery Worker Picks Up Task                                        │
│  • Binds to task instance                                            │
│  • Max retries: 3                                                    │
│  • Starts execution                                                  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 1: Initialize Status (10% complete)                           │
│  • DB: Create ProcessingStatus record                                │
│  • Stage: EXTRACTION                                                 │
│  • Status: IN_PROGRESS                                               │
│  • Metadata: {"percentage_complete": 10.0,                          │
│               "current_operation": "Initializing extraction"}       │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 2: Check Existing Metadata                                    │
│  • Query: document.document_metadata                                 │
│  • If exists AND not force_reextraction → Skip to completion        │
│  • If not exists OR force_reextraction → Continue                   │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 3: Load File from Storage (25% complete)                      │
│  • Call: storage_provider.load_file(storage_path)                   │
│  • Returns: bytes content                                            │
│  • Update: status_tracker.update_progress(25%)                      │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 4: Select Extraction Strategy (40% complete)                  │
│  • Get: metadata_service = get_docling_metadata_service()           │
│  • Check: is_docling_supported(mime_type)                           │
│  • Decision Point: Docling vs Fallback                              │
└─────────────────────┬───────────────────────┬───────────────────────┘
                      │                       │
         ┌────────────┘                       └────────────┐
         ▼                                                  ▼
┌────────────────────────┐                    ┌────────────────────────┐
│  Docling Path          │                    │  Fallback Path         │
│  (PDF, DOCX, PPTX,     │                    │  (TXT, CSV, JSON)      │
│   HTML, MD)            │                    │                        │
└───────┬────────────────┘                    └───────┬────────────────┘
        │                                              │
        ▼                                              ▼
┌────────────────────────┐                    ┌────────────────────────┐
│ Call Docling Service   │                    │ Text Extractor         │
│ • API: /analyze        │                    │ • Decode content       │
│ • Timeout: 30s         │                    │ • Extract keywords     │
│ • Retry: 3 attempts    │                    │ • Detect language      │
│ • Returns:             │                    │ • Calculate quality    │
│   DoclingAnalysisResult│                    │ • Returns:             │
└───────┬────────────────┘                    │   DocumentMetadata     │
        │                                     └───────┬────────────────┘
        ▼                                              │
┌────────────────────────┐                            │
│ Map Docling Response   │                            │
│ • metadata_mapper      │                            │
│ • Transform to our     │                            │
│   schema               │                            │
│ • Classify doc type    │                            │
│ • Assess quality       │                            │
└───────┬────────────────┘                            │
        │                                              │
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 5: Store Metadata (75% complete)                              │
│  • Validate: validate_document_metadata(metadata)                   │
│  • DB Transaction:                                                   │
│    ├── UPDATE documents                                              │
│    │   SET document_metadata = metadata.dict(),                     │
│    │       last_extraction_at = NOW()                               │
│    │   WHERE id = document_id                                       │
│    └── COMMIT                                                        │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 6: Mark Completion (100% complete)                            │
│  • Call: status_tracker.mark_stage_completed()                      │
│  • Update ProcessingStatus:                                          │
│    ├── status = COMPLETED                                            │
│    ├── completed_at = NOW()                                          │
│    ├── duration_ms = (completed_at - started_at) * 1000            │
│    └── status_metadata = {                                          │
│          "percentage_complete": 100.0,                              │
│          "extraction_quality": 0.92,                                │
│          "completeness_score": 0.88                                 │
│        }                                                             │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SUCCESS RESPONSE                                                    │
│  {                                                                   │
│    "success": true,                                                  │
│    "document_id": "...",                                            │
│    "metadata": { ... },                                             │
│    "processing_time_ms": 2341,                                      │
│    "processing_engine": "docling"                                   │
│  }                                                                   │
└─────────────────────────────────────────────────────────────────────┘


ERROR HANDLING PATH:
┌─────────────────────────────────────────────────────────────────────┐
│  ANY STEP FAILS                                                      │
│  • Exception caught                                                  │
│  • DB rollback                                                       │
│  • Mark status as FAILED                                             │
│  • Increment retry_count                                             │
│  • Check retry_count < max_retries (3)                              │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
        ┌──────────────────────┐    ┌──────────────────────┐
        │  Retries Remaining   │    │  Max Retries Reached │
        │  • Delay: 2^retry    │    │  • Return FAILED     │
        │  • Re-queue task     │    │  • Log error         │
        └──────────────────────┘    │  • Update status     │
                                    └──────────────────────┘
```

### Detailed Component Data Flow

#### 1. Docling Service Data Flow
```
File Content (bytes)
    │
    ▼
DoclingClient.analyze_document()
    │
    ├─→ Prepare request data:
    │   ├── file: bytes content
    │   ├── filename: original name
    │   ├── mime_type: document type
    │   └── options: {quality_level, extract_images, etc}
    │
    ▼
HTTP POST → Docling Service API
    │
    ├─→ Response: {
    │       "document": {
    │           "metadata": {title, author, ...},
    │           "content": {text, word_count, ...}
    │       },
    │       "analysis": {
    │           "language": "en",
    │           "text_quality_score": 0.85,
    │           "confidence": {...}
    │       }
    │   }
    │
    ▼
DoclingAnalysisResult (dataclass)
    │
    ▼
DoclingMetadataMapper.map_docling_result()
    │
    ├─→ Extract title (or fallback to filename)
    ├─→ Normalize language (ISO 639-1)
    ├─→ Classify document type (pattern matching)
    ├─→ Assess content quality (score → enum)
    ├─→ Calculate completeness (10 key fields)
    └─→ Build confidence_scores dict
    │
    ▼
DocumentMetadata (Pydantic model)
```

#### 2. Fallback Extractor Data Flow
```
File Content (bytes)
    │
    ▼
TextMetadataExtractor._decode_content()
    │
    ├─→ Try encodings: utf-8, utf-16, latin-1, cp1252, ascii
    ├─→ Fallback: utf-8 with error='replace'
    └─→ Returns: str (decoded text)
    │
    ▼
Extract metadata fields:
    │
    ├─→ _extract_title()
    │   └── First non-code line OR filename
    │
    ├─→ _extract_keywords()
    │   ├── Tokenize text
    │   ├── Remove stop words
    │   ├── Calculate frequency
    │   └── Top 20 frequent words (freq > 1)
    │
    ├─→ _detect_language_basic()
    │   ├── Count common words (en/es/fr)
    │   └── Return highest scoring language
    │
    ├─→ _calculate_quality_score()
    │   ├── Length factor
    │   ├── Word diversity
    │   ├── Sentence structure
    │   ├── Capitalization
    │   └── Punctuation presence
    │
    ├─→ _count_words()
    ├─→ _estimate_page_count()
    └─→ _detect_tables() (delimiter patterns)
    │
    ▼
DocumentMetadata (with processing_engine=FALLBACK_TEXT)
```

#### 3. Status Tracking State Machine
```
Status Transition Flow:

NOT_STARTED ──┬──→ IN_PROGRESS ──┬──→ COMPLETED (terminal)
              │                   │
              │                   └──→ FAILED ──→ IN_PROGRESS (retry)
              │
              └──→ SKIPPED (terminal)

Validation Rules:
• NOT_STARTED → [IN_PROGRESS, SKIPPED]
• IN_PROGRESS → [COMPLETED, FAILED]
• COMPLETED → [] (no transitions allowed)
• FAILED → [IN_PROGRESS] (allow retry)
• SKIPPED → [] (no transitions allowed)

Database Operations:
1. SELECT current status
2. Validate transition
3. UPDATE status fields:
   ├── status (enum)
   ├── updated_at (timestamp)
   ├── started_at (if entering IN_PROGRESS)
   ├── completed_at (if entering terminal state)
   ├── duration_ms (calculate if completed)
   ├── error_message (if FAILED)
   ├── retry_count (increment if FAILED)
   └── status_metadata (merge with existing)
4. COMMIT transaction
5. Log state change
```

### Status Tracking Flow
```
Status Update Request
├── Validate transition (state machine)
├── Update status enum
├── Update timestamps
├── Merge ProcessingMetadata
├── Calculate duration if completed
├── Increment retry count if applicable
├── Commit transaction
└── Log status change
```

### Progress Calculation Flow
```
Progress Update
├── Find active processing record
├── Update percentage_complete
├── Calculate estimated_completion
├── Update current_operation
├── Store in status_metadata JSONB
└── Emit real-time update (future WebSocket)
```

---

## 4. VALIDATIONS & CONSTRAINTS

### Metadata Field Validations
- **Title**: Maximum 500 characters, sanitized for display
- **Author**: Maximum 200 characters, normalized format
- **Keywords**: Maximum 50 keywords, 100 chars each
- **Language**: Valid ISO 639-1 code
- **Page Count**: Positive integer, maximum 100,000
- **Quality Score**: Float between 0.0 and 1.0
- **Dates**: Valid datetime, not future dates

### Status Transition Rules
```python
VALID_TRANSITIONS = {
    NOT_STARTED: [IN_PROGRESS, SKIPPED],
    IN_PROGRESS: [COMPLETED, FAILED],
    COMPLETED: [],  # Terminal state
    FAILED: [IN_PROGRESS],  # Allow retry
    SKIPPED: []  # Terminal state
}
```

### Extraction Constraints
- **File Size**: Maximum 100MB for metadata extraction
- **Timeout**: 30 seconds per extraction attempt
- **Memory**: Maximum 200MB per extraction task
- **Retry**: Maximum 3 attempts with exponential backoff
- **Concurrency**: Maximum 10 concurrent extractions

### Content Analysis Rules
- **Language Detection**: Minimum 100 characters required
- **OCR Detection**: Based on character distribution analysis
- **Quality Assessment**: Weighted scoring of multiple factors
- **Type Classification**: Confidence threshold of 0.7

---

## 5. CONFIGURATION

### Environment Variables
```bash
# Metadata Extraction Configuration
METADATA_EXTRACTION_ENABLED=true
METADATA_EXTRACTION_TIMEOUT=30
METADATA_MAX_FILE_SIZE_MB=100
METADATA_MAX_MEMORY_MB=200

# Language Detection
LANGUAGE_DETECTION_ENABLED=true
LANGUAGE_DETECTION_MIN_CHARS=100
DEFAULT_LANGUAGE=en

# Quality Thresholds
MIN_TEXT_QUALITY_SCORE=0.3
OCR_DETECTION_THRESHOLD=0.5

# Extraction Versions
PDF_EXTRACTOR_VERSION=1.0.0
DOCX_EXTRACTOR_VERSION=1.0.0
XLSX_EXTRACTOR_VERSION=1.0.0
TEXT_EXTRACTOR_VERSION=1.0.0

# Status Tracking
STATUS_UPDATE_BATCH_SIZE=100
PROGRESS_UPDATE_INTERVAL_MS=1000

# Performance
METADATA_CACHE_TTL_SECONDS=3600
METADATA_EXTRACTION_WORKERS=4
```

### Default Values
- **Extraction Timeout**: 30 seconds
- **Max File Size**: 100MB for extraction
- **Default Language**: English (en)
- **Retry Attempts**: 3 with delays [2s, 4s, 8s]
- **Cache TTL**: 1 hour for extracted metadata

### Extractor Configuration
```python
EXTRACTOR_CONFIG = {
    'pdf': {
        'engines': ['pypdf2', 'pdfplumber'],
        'ocr_enabled': True,
        'max_pages_for_analysis': 10
    },
    'docx': {
        'extract_styles': True,
        'extract_comments': False,
        'extract_revisions': False
    },
    'xlsx': {
        'extract_formulas': True,
        'max_sheets': 10,
        'sample_rows': 1000
    },
    'text': {
        'encoding_detection': True,
        'language_detection': True,
        'structure_analysis': True
    }
}
```

---

## 6. ERROR HANDLING

### Extraction Error Scenarios

#### Corrupted File Handling
```python
try:
    metadata = await extractor.extract(file_path, content)
except CorruptedFileError as e:
    metadata = DocumentMetadata(
        processing_engine=extractor_name,
        processing_warnings=[f"File corrupted: {str(e)}"],
        content_quality=ContentQuality.LOW,
        requires_ocr=True
    )
```

#### Timeout Handling
```python
async def extract_with_timeout(extractor, file_path, content):
    try:
        return await asyncio.wait_for(
            extractor.extract(file_path, content),
            timeout=settings.METADATA_EXTRACTION_TIMEOUT
        )
    except asyncio.TimeoutError:
        raise ExtractionTimeoutError(f"Extraction exceeded {timeout}s limit")
```

#### Memory Limit Protection
```python
@memory_limit(settings.METADATA_MAX_MEMORY_MB * 1024 * 1024)
async def extract_metadata(self, file_path: str, content: bytes):
    # Extraction logic with memory monitoring
```

### Recovery Strategies
- **Partial Extraction**: Save whatever metadata was extracted before failure
- **Fallback Extractors**: Try alternative extraction methods
- **Degraded Mode**: Basic metadata only (size, type, checksum)
- **Manual Review Queue**: Flag for human inspection

### Error Response Formats
```json
{
    "error_type": "ExtractionError",
    "message": "Failed to extract metadata from PDF",
    "details": {
        "extractor": "pdf_extractor_v1",
        "stage": "content_analysis",
        "file_size": 15728640,
        "partial_metadata_available": true
    },
    "recovery_suggestions": [
        "Try with OCR enabled",
        "Check if file is password protected",
        "Verify file is not corrupted"
    ]
}
```

---

## 7. TESTING CHECKLIST

### Unit Tests
- [ ] Each metadata extractor with sample files
- [ ] Content quality analysis accuracy
- [ ] Language detection for multiple languages
- [ ] Confidence score calculations
- [ ] Status transition validation
- [ ] Progress percentage calculations

### Integration Tests
- [ ] Upload → Metadata extraction flow
- [ ] Concurrent metadata extractions
- [ ] Database transaction rollbacks
- [ ] Celery task retry mechanism
- [ ] API endpoint responses
- [ ] Storage service integration

### Performance Tests
```bash
# Single file extraction
time curl -X POST localhost:8000/api/v1/documents/{id}/metadata/refresh

# Concurrent extractions
ab -n 100 -c 10 -p upload.txt localhost:8000/api/v1/upload

# Large file handling
curl -X POST -F "file=@large_document.pdf" localhost:8000/api/v1/upload

# Memory usage monitoring
docker stats backend_worker --format "table {{.MemUsage}}"
```

### Edge Cases
- [ ] Zero-byte files
- [ ] Password-protected PDFs
- [ ] Corrupted file headers
- [ ] Unicode filenames
- [ ] Files with no extractable text
- [ ] Deeply nested ZIP files
- [ ] Files requiring OCR
- [ ] Mixed language documents

### Expected Performance
- **PDF Extraction**: <3 seconds for 100-page document
- **DOCX Extraction**: <1 second for typical document
- **Text Analysis**: <500ms for 1MB text file
- **Status Updates**: <100ms API response time
- **Memory Usage**: <200MB per extraction task
- **Concurrent Capacity**: 10 simultaneous extractions

---

## 8. MONITORING & METRICS

### Prometheus Metrics
```python
# Extraction metrics
metadata_extraction_duration = Histogram(
    'metadata_extraction_duration_seconds',
    'Time spent extracting metadata',
    ['file_type', 'extractor', 'status']
)

metadata_extraction_total = Counter(
    'metadata_extraction_total',
    'Total metadata extractions',
    ['file_type', 'status']
)

# Quality metrics
document_quality_score = Histogram(
    'document_quality_score',
    'Distribution of document quality scores',
    ['document_type'],
    buckets=[0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
)

# Status tracking metrics
processing_stage_duration = Histogram(
    'processing_stage_duration_seconds',
    'Duration of each processing stage',
    ['stage', 'status']
)

processing_queue_depth = Gauge(
    'processing_queue_depth',
    'Number of documents in processing queue',
    ['stage']
)
```

### Log Entries
```json
{
    "timestamp": "2024-11-15T10:30:00Z",
    "level": "INFO",
    "logger": "metadata.extractor.pdf",
    "message": "Metadata extracted successfully",
    "extra": {
        "document_id": "123e4567-e89b-12d3-a456-426614174000",
        "file_type": "pdf",
        "page_count": 42,
        "extraction_time_ms": 2341,
        "quality_score": 0.85,
        "language": "en",
        "warnings": []
    }
}
```

### Health Indicators
```python
# Extraction service health
GET /health/metadata
{
    "status": "healthy",
    "extractors": {
        "pdf": {"status": "ready", "version": "1.0.0"},
        "docx": {"status": "ready", "version": "1.0.0"},
        "xlsx": {"status": "ready", "version": "1.0.0"},
        "text": {"status": "ready", "version": "1.0.0"}
    },
    "queue_depth": 5,
    "active_extractions": 2,
    "avg_extraction_time_ms": 1845,
    "error_rate_percentage": 0.5
}
```

### Performance Dashboards
- **Extraction Performance**: Time by file type and size
- **Quality Distribution**: Document quality scores over time
- **Language Distribution**: Detected languages in corpus
- **Error Analysis**: Common extraction failures
- **Processing Pipeline**: Stage completion rates

---

## 9. SECURITY CONSIDERATIONS

### Input Validation
```python
# File type validation before extraction
ALLOWED_MIME_TYPES_FOR_EXTRACTION = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain',
    'text/markdown'
}

# Filename sanitization
def sanitize_metadata_field(value: str, max_length: int = 500) -> str:
    # Remove null bytes and control characters
    sanitized = value.replace('\x00', '').strip()
    # Limit length
    return sanitized[:max_length]
```

### Resource Protection
- **Memory Limits**: Process isolation with memory caps
- **CPU Limits**: Maximum execution time per extraction
- **Disk I/O**: Rate limiting for concurrent reads
- **Network**: No external calls during extraction

### Metadata Privacy
```python
# Sensitive data detection
SENSITIVE_PATTERNS = {
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
}

# Redaction in metadata
def redact_sensitive_metadata(metadata: DocumentMetadata) -> DocumentMetadata:
    # Implement redaction logic for sensitive fields
    pass
```

### Audit Trail
```python
# Log all metadata operations
@audit_log("metadata_extraction")
async def extract_metadata(self, document_id: str):
    # Extraction logic with full audit trail
    pass
```

---

## 10. CODE PATTERNS & CONVENTIONS

### Design Patterns

#### Strategy Pattern (Extractors)
```python
class MetadataExtractionContext:
    def __init__(self, strategy: MetadataExtractor):
        self._strategy = strategy
    
    async def extract(self, file_path: str, content: bytes) -> DocumentMetadata:
        return await self._strategy.extract(file_path, content)
```

#### Factory Pattern (Extractor Selection)
```python
class ExtractorFactory:
    @staticmethod
    def create_extractor(file_type: str) -> MetadataExtractor:
        extractors = {
            'pdf': PDFMetadataExtractor,
            'docx': DocxMetadataExtractor,
            'xlsx': XlsxMetadataExtractor,
            'text': TextMetadataExtractor
        }
        extractor_class = extractors.get(file_type, TextMetadataExtractor)
        return extractor_class()
```

#### Observer Pattern (Status Updates)
```python
class StatusObserver(ABC):
    @abstractmethod
    async def on_status_change(self, document_id: str, old_status: str, new_status: str):
        pass

class WebSocketStatusObserver(StatusObserver):
    async def on_status_change(self, document_id: str, old_status: str, new_status: str):
        # Send WebSocket update to connected clients
        pass
```

### Async Patterns
```python
# Concurrent metadata extraction
async def extract_multiple(documents: List[Document]) -> List[DocumentMetadata]:
    tasks = [extract_metadata(doc) for doc in documents]
    return await asyncio.gather(*tasks, return_exceptions=True)

# Streaming large file processing
async def extract_streaming(file_path: str) -> AsyncIterator[Dict[str, Any]]:
    async with aiofiles.open(file_path, 'rb') as file:
        async for chunk in file.iter_chunked(1024 * 1024):  # 1MB chunks
            yield await process_chunk(chunk)
```

### Error Propagation
```python
class MetadataExtractionError(Exception):
    def __init__(self, message: str, extractor: str, document_id: str, details: Dict = None):
        super().__init__(message)
        self.extractor = extractor
        self.document_id = document_id
        self.details = details or {}
```

### Naming Conventions
- **Services**: `{Domain}Service` (e.g., `MetadataExtractionService`)
- **Extractors**: `{FileType}MetadataExtractor` (e.g., `PDFMetadataExtractor`)
- **Tasks**: `{action}_{object}_task` (e.g., `extract_metadata_task`)
- **Schemas**: `{Entity}Metadata` (e.g., `DocumentMetadata`)

---

## 11. INTEGRATION POINTS

### Upload Pipeline Integration
```python
# In upload endpoint after storage
if storage_result.document_id:
    # Queue metadata extraction
    extract_metadata_task.delay(
        document_id=str(storage_result.document_id),
        file_path=file.filename,
        storage_path=storage_result.path
    )
```

### Storage Service Integration
```python
# Atomic metadata updates with storage operations
async with storage_transaction():
    # Save file
    storage_path = await storage_manager.save_file(content, path)
    # Extract and save metadata atomically
    metadata = await metadata_service.extract_and_save(document_id, content)
```

### Processing Queue Integration
```python
# Chain metadata extraction with next processing stage
chain = (
    extract_metadata_task.si(document_id) |
    chunk_document_task.si(document_id) |
    generate_embeddings_task.si(document_id)
)
chain.apply_async()
```

### Search Service Integration (Future)
```python
# Metadata fields become searchable
search_fields = [
    "document_metadata.title",
    "document_metadata.author",
    "document_metadata.keywords",
    "document_metadata.content"
]
```

### Event System Integration
```python
# Publish metadata extraction events
await event_publisher.publish(
    "document.metadata.extracted",
    {
        "document_id": document_id,
        "metadata": metadata.dict(),
        "quality_score": metadata.text_quality_score
    }
)
```

---

## 12. TROUBLESHOOTING GUIDE

### Common Issues and Solutions

#### "Metadata extraction timing out"
```bash
# Check extraction duration
SELECT 
    document_id,
    stage,
    duration_ms
FROM processing_status
WHERE stage = 'extraction'
AND duration_ms > 30000
ORDER BY created_at DESC;

# Solutions:
# 1. Increase timeout: METADATA_EXTRACTION_TIMEOUT=60
# 2. Reduce file size limit
# 3. Add more extraction workers
# 4. Check for PDF complexity (many images)
```

#### "Language detection failing"
```bash
# Debug language detection
curl -X POST localhost:8000/api/v1/documents/{id}/metadata/refresh \
    -H "X-Debug: true"

# Check response headers for debug info
# Common issues:
# - Text too short (< 100 chars)
# - Multiple languages in document
# - Poor OCR quality

# Solution: Set default language
DEFAULT_LANGUAGE=en
```

#### "Memory errors during extraction"
```bash
# Monitor memory usage
docker stats backend_worker

# Check for memory leaks
grep "MemoryError" /var/log/querybox/worker.log

# Solutions:
# 1. Reduce METADATA_MAX_MEMORY_MB
# 2. Process files in smaller chunks
# 3. Increase worker memory limits
# 4. Enable swap for large files
```

#### "Inconsistent metadata quality"
```python
# Analyze quality scores
SELECT 
    document_metadata->>'document_type' as doc_type,
    AVG((document_metadata->>'text_quality_score')::float) as avg_quality,
    COUNT(*) as count
FROM documents
WHERE document_metadata IS NOT NULL
GROUP BY doc_type
ORDER BY avg_quality DESC;

# Improve quality:
# 1. Enable OCR for low-quality PDFs
# 2. Update extractor versions
# 3. Adjust quality thresholds
# 4. Add manual review queue
```

### Debug Commands
```bash
# Test individual extractor
python -m app.services.metadata.extractors.pdf_extractor test.pdf

# Check extraction queue depth
celery -A app.celery_app inspect active

# Force metadata refresh for all documents
python scripts/refresh_all_metadata.py --batch-size=10

# Export metadata for analysis
psql -d querybox_core -c "
    SELECT id, document_metadata 
    FROM documents 
    WHERE document_metadata IS NOT NULL
" --output=metadata_export.json

# Validate metadata schema
python -m app.schemas.metadata validate metadata_export.json
```

### Performance Tuning
```bash
# Analyze slow extractions
SELECT 
    d.original_name,
    d.file_size,
    ps.duration_ms,
    ps.status_metadata->>'error_category' as error
FROM documents d
JOIN processing_status ps ON d.id = ps.document_id
WHERE ps.stage = 'extraction'
AND ps.duration_ms > 5000
ORDER BY ps.duration_ms DESC
LIMIT 20;

# Optimize indexes
ANALYZE documents;
REINDEX INDEX idx_documents_metadata_title;

# Check extraction worker performance
celery -A app.celery_app inspect stats

# Tune extraction concurrency
METADATA_EXTRACTION_WORKERS=8
CELERY_WORKER_PREFETCH_MULTIPLIER=2
```

### Recovery Procedures

#### Retry Failed Extractions
```python
# Script to retry failed metadata extractions
from app.models import Document, ProcessingStatus
from app.tasks import extract_metadata_task

failed_docs = db.query(Document).join(ProcessingStatus).filter(
    ProcessingStatus.stage == ProcessingStageEnum.EXTRACTION,
    ProcessingStatus.status == StageStatusEnum.FAILED
).all()

for doc in failed_docs:
    extract_metadata_task.apply_async(
        args=[str(doc.id), doc.original_name, doc.storage_path],
        countdown=60  # Delay 1 minute
    )
```

#### Bulk Metadata Updates
```sql
-- Update all documents missing language detection
UPDATE documents
SET document_metadata = 
    jsonb_set(
        COALESCE(document_metadata, '{}'::jsonb),
        '{language}',
        '"en"'
    )
WHERE document_metadata->>'language' IS NULL;

-- Fix corrupted metadata
UPDATE documents
SET document_metadata = '{
    "processing_engine": "manual_fix",
    "extraction_version": "1.0.0",
    "processing_warnings": ["Metadata corrupted, reset to defaults"]
}'::jsonb
WHERE jsonb_typeof(document_metadata) != 'object';
```

---

## Summary

Step 6 successfully implements comprehensive metadata management that:

1. **Leverages Existing Infrastructure** - Uses JSONB fields and current models without schema changes
2. **Provides Deep Content Analysis** - Extracts rich metadata with quality assessment
3. **Enables Real-time Tracking** - Granular progress updates with time estimates
4. **Supports Multiple Formats** - Specialized extractors for each file type
5. **Ensures Data Quality** - Validation, confidence scoring, and error handling
6. **Scales Horizontally** - Celery tasks with configurable workers
7. **Maintains Compatibility** - Seamless integration with existing services
8. **Prepares for Search** - Indexed metadata fields ready for querying

This metadata foundation transforms document storage into intelligent document management, enabling advanced features while maintaining the simplicity and reliability of the QueryBox Core architecture.