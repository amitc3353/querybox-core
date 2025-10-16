# Step 7: Document Query Endpoints - Technical Documentation

**Status**: Implementation Plan
**Estimated Time**: 3 hours
**Dependencies**: Step 1-6 (Database, Storage, Metadata Management)
**Week**: 1, Day 4

---

## 1. FEATURE OVERVIEW

### What This Step Accomplishes
Step 7 implements comprehensive document query and retrieval endpoints that allow clients to:
- Retrieve individual documents by ID with full metadata
- List documents with pagination, sorting, and filtering
- Filter documents by status, type, date ranges, and tags
- Search documents by name or content metadata
- Get document processing status and history

### Why This Step Is Necessary
This step transforms the upload system from write-only to a full-fledged document management system by:
- **Enabling Document Discovery**: Users can find their uploaded documents
- **Status Monitoring**: Track processing progress for each document
- **Analytics Foundation**: Provides data for usage metrics and reporting
- **Integration Support**: Other services can query document information
- **User Experience**: Essential for building document management UIs

### Dependencies on Previous Steps
- **Step 1**: Requires PostgreSQL database with `documents` table
- **Step 2**: Uses FastAPI routing structure and middleware
- **Step 3**: Depends on document records created during upload
- **Step 4**: Relies on validated file metadata
- **Step 5**: Uses storage paths for file access
- **Step 6**: Leverages rich metadata for filtering and search

### What Future Steps Depend on This
- **Step 8**: Upload status tracking builds on query endpoints
- **Step 11-12**: Large file routing needs document status queries
- **Step 15-16**: Processing queue depends on document lookups
- **Week 3 (Steps 21-30)**: Processing pipeline queries documents continuously
- **Week 4 (Step 36)**: Monitoring dashboard uses these endpoints

---

## 2. TECHNICAL IMPLEMENTATION

### Files to Create

#### 1. `/app/api/v1/endpoints/documents.py` (Complete Implementation)
**Purpose**: Main document query endpoints
**Size**: ~350 lines

**Key Components**:
```python
# Endpoints:
- GET  /api/v1/documents                    # List with pagination
- GET  /api/v1/documents/{document_id}      # Get by ID
- GET  /api/v1/documents/search             # Search documents
- GET  /api/v1/documents/stats              # Document statistics
- DELETE /api/v1/documents/{document_id}    # Soft delete
```

#### 2. `/app/schemas/document.py` (Update/Expand)
**Purpose**: Request/response models for document queries
**Size**: ~250 lines

**Key Classes**:
```python
class DocumentResponse(BaseModel)           # Full document response
class DocumentListResponse(BaseModel)       # Paginated list response
class DocumentFilterParams(BaseModel)       # Query filter parameters
class DocumentSearchRequest(BaseModel)      # Search query model
class DocumentStatsResponse(BaseModel)      # Statistics response
class PaginationParams(BaseModel)           # Reusable pagination
```

#### 3. `/app/services/document_service.py` (New)
**Purpose**: Business logic for document operations
**Size**: ~200 lines

**Key Methods**:
```python
class DocumentService:
    def get_document_by_id(document_id: UUID) -> Document
    def list_documents(filters, pagination) -> List[Document]
    def search_documents(query: str) -> List[Document]
    def get_document_stats() -> Dict[str, Any]
    def soft_delete_document(document_id: UUID) -> bool
    def get_documents_by_status(status: DocumentStatusEnum) -> List[Document]
```

#### 4. `/tests/api/test_documents.py` (New)
**Purpose**: API endpoint tests
**Size**: ~400 lines

**Test Coverage**:
- Test get document by ID (success, not found)
- Test list documents (pagination, filters, sorting)
- Test search functionality
- Test statistics endpoint
- Test delete operations
- Test authorization checks

### Files to Modify

#### 1. `/app/api/v1/router.py`
**Change**: Register documents router (if not already done)
```python
from app.api.v1.endpoints import documents

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["documents"]
)
```

#### 2. `/app/models/document.py`
**Change**: Add helper methods for querying
```python
class Document(Base):
    # ... existing fields ...

    @property
    def is_processing(self) -> bool:
        return self.status == DocumentStatusEnum.PROCESSING

    @property
    def file_size_mb(self) -> float:
        return self.file_size / (1024 * 1024)

    def to_dict(self) -> dict:
        # Serialize to dictionary
```

### Database Tables Used

#### Primary Table: `documents`
**Columns Queried**:
- `id` (UUID) - Primary key for lookups
- `document_name` - User-facing filename
- `original_name` - Original upload filename
- `mime_type` - File type filtering
- `file_extension` - Extension-based filtering
- `file_size` - Size range queries
- `checksum` - Deduplication checks
- `storage_provider` - Provider filtering
- `storage_path` - File location
- `status` - Status filtering (PENDING, PROCESSING, COMPLETED, FAILED)
- `document_metadata` - JSONB search and filtering
- `tags` - Tag-based filtering (ARRAY column)
- `created_at` - Date range queries
- `updated_at` - Recent activity sorting
- `last_accessed_at` - Access tracking
- `access_count` - Popularity metrics
- `is_deleted` - Soft delete filtering
- `deleted_at` - Deletion audit

#### Related Tables (via JOINs):
- `processing_status` - Get detailed processing info
- `document_versions` - Version history
- `embeddings` - Check if embedded (future)

### API Endpoints Specification

#### 1. GET `/api/v1/documents`
**Purpose**: List documents with pagination and filtering

**Query Parameters**:
```python
{
    "page": int = 1,           # Page number (1-indexed)
    "page_size": int = 20,     # Items per page (max 100)
    "sort_by": str = "created_at",  # Sort field
    "sort_order": str = "desc",     # asc or desc
    "status": str = None,           # Filter by status
    "mime_type": str = None,        # Filter by MIME type
    "file_extension": str = None,   # Filter by extension
    "tags": List[str] = None,       # Filter by tags (AND logic)
    "created_after": datetime = None,   # Date range start
    "created_before": datetime = None,  # Date range end
    "min_size": int = None,         # Minimum file size (bytes)
    "max_size": int = None,         # Maximum file size (bytes)
    "include_deleted": bool = False # Include soft-deleted docs
}
```

**Response** (200 OK):
```json
{
    "items": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "document_name": "report_2024.pdf",
            "original_name": "Q4 Report.pdf",
            "mime_type": "application/pdf",
            "file_extension": ".pdf",
            "file_size": 2457600,
            "file_size_mb": 2.34,
            "checksum": "sha256:abc123...",
            "storage_provider": "local",
            "status": "completed",
            "document_metadata": {
                "title": "Q4 Financial Report",
                "author": "Finance Team",
                "page_count": 45
            },
            "tags": ["finance", "quarterly", "2024"],
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:35:00Z",
            "last_accessed_at": "2024-01-16T08:00:00Z",
            "access_count": 12
        }
    ],
    "total": 156,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "has_next": true,
    "has_previous": false
}
```

**Error Responses**:
- 400: Invalid query parameters
- 401: Unauthorized (if auth enabled)
- 500: Server error

---

#### 2. GET `/api/v1/documents/{document_id}`
**Purpose**: Get single document with full metadata

**Path Parameters**:
- `document_id` (UUID): Document identifier

**Query Parameters**:
```python
{
    "include_processing_status": bool = True,  # Include processing details
    "include_versions": bool = False,          # Include version history
    "include_embeddings": bool = False         # Include embedding status (future)
}
```

**Response** (200 OK):
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "document_name": "report_2024.pdf",
    "original_name": "Q4 Report.pdf",
    "alternate_name": "Financial Report Q4",
    "mime_type": "application/pdf",
    "file_extension": ".pdf",
    "file_size": 2457600,
    "file_size_mb": 2.34,
    "checksum": "sha256:abc123def456...",
    "storage_provider": "local",
    "storage_path": "documents/2024/01/550e8400.../report_2024.pdf",
    "storage_bucket": null,
    "storage_region": null,
    "status": "completed",
    "is_versioned_file": false,
    "current_version": 1,
    "mutation_count": 1,
    "document_metadata": {
        "title": "Q4 Financial Report",
        "author": "Finance Team",
        "created_date": "2024-01-10",
        "page_count": 45,
        "language": "en",
        "keywords": ["finance", "quarterly", "analysis"]
    },
    "tags": ["finance", "quarterly", "2024"],
    "last_extraction_at": "2024-01-15T10:32:00Z",
    "last_embedding_at": null,
    "last_indexed_at": null,
    "last_accessed_at": "2024-01-16T08:00:00Z",
    "access_count": 12,
    "storage_size": 2400000,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z",
    "is_deleted": false,
    "is_dirty": false,
    "processing_status": {
        "extraction": {
            "status": "completed",
            "started_at": "2024-01-15T10:30:30Z",
            "completed_at": "2024-01-15T10:32:00Z",
            "progress": 100.0
        },
        "chunking": {
            "status": "not_started"
        },
        "embedding": {
            "status": "not_started"
        }
    }
}
```

**Error Responses**:
- 404: Document not found
- 401: Unauthorized
- 500: Server error

---

#### 3. GET `/api/v1/documents/search`
**Purpose**: Search documents by name or metadata content

**Query Parameters**:
```python
{
    "q": str,                      # Search query (required)
    "search_fields": List[str] = ["document_name", "metadata"],
    "page": int = 1,
    "page_size": int = 20,
    "status": str = None           # Filter by status
}
```

**Search Behavior**:
- Case-insensitive text matching
- Searches in: `document_name`, `original_name`, `document_metadata` (JSONB)
- Uses PostgreSQL `ILIKE` for text fields
- Uses JSONB operators for metadata searches

**Response** (200 OK):
```json
{
    "query": "financial report",
    "items": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "document_name": "report_2024.pdf",
            "relevance_score": 0.95,
            "matched_fields": ["document_name", "metadata.title"],
            "snippet": "...Q4 Financial Report...",
            ...
        }
    ],
    "total": 8,
    "page": 1,
    "total_pages": 1
}
```

**Error Responses**:
- 400: Missing or invalid query
- 500: Search error

---

#### 4. GET `/api/v1/documents/stats`
**Purpose**: Get document statistics and analytics

**Query Parameters**:
```python
{
    "group_by": str = "status",    # Group by: status, mime_type, date
    "date_range": str = "30d"      # 7d, 30d, 90d, 1y, all
}
```

**Response** (200 OK):
```json
{
    "total_documents": 1523,
    "total_size_bytes": 15728640000,
    "total_size_gb": 14.65,
    "by_status": {
        "completed": 1420,
        "processing": 45,
        "pending": 32,
        "failed": 26
    },
    "by_mime_type": {
        "application/pdf": 892,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": 345,
        "text/plain": 198,
        "application/vnd.ms-excel": 88
    },
    "upload_trend": [
        {"date": "2024-01-01", "count": 45},
        {"date": "2024-01-02", "count": 67},
        ...
    ],
    "avg_file_size_mb": 10.12,
    "most_used_tags": [
        {"tag": "finance", "count": 234},
        {"tag": "quarterly", "count": 198}
    ]
}
```

---

#### 5. DELETE `/api/v1/documents/{document_id}`
**Purpose**: Soft delete a document

**Path Parameters**:
- `document_id` (UUID): Document to delete

**Query Parameters**:
```python
{
    "hard_delete": bool = False,   # Actually delete vs soft delete
    "delete_files": bool = True    # Delete physical files
}
```

**Response** (200 OK):
```json
{
    "success": true,
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "deleted_at": "2024-01-16T10:00:00Z",
    "hard_delete": false,
    "files_deleted": true
}
```

**Error Responses**:
- 404: Document not found
- 409: Document is being processed
- 500: Deletion failed

---

## 3. DATA FLOW

### Flow 1: Get Document by ID

```
Client Request
    ↓
[API Endpoint] GET /documents/{id}
    ↓
[Authentication Middleware] (if enabled)
    ↓
[DocumentService.get_document_by_id(id)]
    ↓
[Database Query]
    SELECT * FROM documents WHERE id = ? AND is_deleted = FALSE
    ↓
[Join Processing Status] (if include_processing_status=true)
    LEFT JOIN processing_status ON ...
    ↓
[Load Metadata] (JSONB deserialize)
    ↓
[Increment Access Counter]
    UPDATE documents SET access_count = access_count + 1,
                        last_accessed_at = NOW()
    ↓
[Transform to Response Model]
    Document → DocumentResponse (Pydantic)
    ↓
[Return JSON Response]
```

**State Changes**:
- `access_count` incremented
- `last_accessed_at` updated to current timestamp

---

### Flow 2: List Documents with Filters

```
Client Request
    ↓
[API Endpoint] GET /documents?status=completed&page=1&page_size=20
    ↓
[Validate Query Parameters]
    PaginationParams validation
    DocumentFilterParams validation
    ↓
[DocumentService.list_documents(filters, pagination)]
    ↓
[Build SQL Query]
    SELECT * FROM documents
    WHERE is_deleted = FALSE
      AND status = 'completed'
    ORDER BY created_at DESC
    LIMIT 20 OFFSET 0
    ↓
[Execute COUNT Query] (for pagination)
    SELECT COUNT(*) FROM documents WHERE ...
    ↓
[Execute Data Query]
    ↓
[Transform Results]
    List[Document] → List[DocumentResponse]
    ↓
[Build Pagination Metadata]
    total_pages = ceil(total / page_size)
    has_next = page < total_pages
    has_previous = page > 1
    ↓
[Return DocumentListResponse]
```

**No State Changes** (read-only operation)

---

### Flow 3: Search Documents

```
Client Request
    ↓
[API Endpoint] GET /documents/search?q=financial+report
    ↓
[Validate Search Query]
    Check query length (min 3 chars)
    ↓
[DocumentService.search_documents(query)]
    ↓
[Build Search Query]
    SELECT * FROM documents
    WHERE is_deleted = FALSE
      AND (
        document_name ILIKE '%financial%report%'
        OR original_name ILIKE '%financial%report%'
        OR document_metadata::text ILIKE '%financial%report%'
      )
    ORDER BY updated_at DESC
    ↓
[Calculate Relevance Scores] (optional)
    ts_rank for full-text search (future enhancement)
    ↓
[Extract Snippets]
    Highlight matching text
    ↓
[Return Search Results]
```

---

### Flow 4: Get Statistics

```
Client Request
    ↓
[API Endpoint] GET /documents/stats?group_by=status
    ↓
[DocumentService.get_document_stats()]
    ↓
[Execute Aggregation Queries]

    Query 1: Total Count
    SELECT COUNT(*) FROM documents WHERE is_deleted = FALSE

    Query 2: Total Size
    SELECT SUM(file_size) FROM documents WHERE is_deleted = FALSE

    Query 3: Group by Status
    SELECT status, COUNT(*) as count
    FROM documents
    WHERE is_deleted = FALSE
    GROUP BY status

    Query 4: Group by MIME Type
    SELECT mime_type, COUNT(*) as count
    FROM documents
    WHERE is_deleted = FALSE
    GROUP BY mime_type
    ORDER BY count DESC
    LIMIT 10

    Query 5: Upload Trend (last 30 days)
    SELECT DATE(created_at) as date, COUNT(*) as count
    FROM documents
    WHERE is_deleted = FALSE
      AND created_at >= NOW() - INTERVAL '30 days'
    GROUP BY DATE(created_at)
    ORDER BY date
    ↓
[Combine Results]
    ↓
[Return DocumentStatsResponse]
```

---

### Flow 5: Delete Document

```
Client Request
    ↓
[API Endpoint] DELETE /documents/{id}?hard_delete=false
    ↓
[Get Document]
    SELECT * FROM documents WHERE id = ?
    ↓
[Validation Checks]
    - Document exists?
    - Not already deleted?
    - Not currently processing?
    ↓
[START TRANSACTION]
    ↓
    [Soft Delete]
        UPDATE documents
        SET is_deleted = TRUE,
            deleted_at = NOW(),
            deleted_by_user_id = ? (if auth enabled)
        WHERE id = ?
    ↓
    [Queue Cleanup Task] (if delete_files=true)
        Celery task: cleanup_document_files(document_id)
    ↓
[COMMIT TRANSACTION]
    ↓
[Return Success Response]
```

**State Changes**:
- `is_deleted` set to `TRUE`
- `deleted_at` set to current timestamp
- `deleted_by_user_id` set (if authenticated)
- Physical files queued for deletion (async)

---

## 4. VALIDATIONS & CONSTRAINTS

### Input Validations

#### Pagination Parameters
```python
class PaginationParams(BaseModel):
    page: int = Field(ge=1, le=10000, default=1)
    page_size: int = Field(ge=1, le=100, default=20)

    # Validation: page_size cannot exceed 100
    # Validation: page must be positive
```

#### Filter Parameters
```python
class DocumentFilterParams(BaseModel):
    status: Optional[DocumentStatusEnum] = None
    mime_type: Optional[str] = Field(max_length=100)
    file_extension: Optional[str] = Field(regex=r"^\.[a-z0-9]+$")
    tags: Optional[List[str]] = Field(max_items=10)
    min_size: Optional[int] = Field(ge=0)
    max_size: Optional[int] = Field(le=10*1024*1024*1024)  # 10GB max

    @field_validator('max_size')
    def validate_size_range(cls, v, values):
        if 'min_size' in values and v < values['min_size']:
            raise ValueError('max_size must be >= min_size')
        return v
```

#### Search Query Validation
```python
class DocumentSearchRequest(BaseModel):
    q: str = Field(min_length=3, max_length=200)
    search_fields: List[str] = Field(default=["document_name", "metadata"])

    @field_validator('search_fields')
    def validate_search_fields(cls, v):
        allowed = ["document_name", "original_name", "metadata", "tags"]
        if not all(f in allowed for f in v):
            raise ValueError(f'Invalid search fields. Allowed: {allowed}')
        return v
```

### Business Rules

1. **Deleted Documents**: By default, exclude `is_deleted=TRUE` from all queries
2. **Access Tracking**: Increment `access_count` only for GET by ID requests
3. **Pagination Limits**: Maximum 100 items per page
4. **Search Query**: Minimum 3 characters, maximum 200 characters
5. **Processing Documents**: Cannot delete documents with `status=PROCESSING`
6. **Date Ranges**: `created_before` must be after `created_after`
7. **Tag Filtering**: AND logic (document must have ALL specified tags)

### Security Checks

1. **Document ID Validation**: Must be valid UUID format
2. **SQL Injection Prevention**: Use parameterized queries only
3. **Path Traversal Prevention**: Never expose `storage_path` in unauthenticated contexts
4. **Metadata Sanitization**: Escape HTML/JS in metadata fields when displaying
5. **Rate Limiting** (future): Max 100 requests/minute per IP

### Error Conditions Handled

```python
# Document not found
raise HTTPException(status_code=404, detail="Document not found")

# Invalid UUID format
raise HTTPException(status_code=400, detail="Invalid document ID format")

# Invalid pagination parameters
raise HTTPException(status_code=400, detail="page_size must be between 1 and 100")

# Invalid date range
raise HTTPException(status_code=400, detail="created_before must be after created_after")

# Document being processed
raise HTTPException(status_code=409, detail="Cannot delete document while processing")

# Database error
raise HTTPException(status_code=500, detail="Failed to retrieve documents")

# Search query too short
raise HTTPException(status_code=400, detail="Search query must be at least 3 characters")
```

---

## 5. CONFIGURATION

### Environment Variables

```bash
# Database (from Step 1)
DATABASE_URL=postgresql://querybox:querybox_dev_2024@localhost:5432/querybox_core

# Pagination defaults
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
MAX_SEARCH_RESULTS=1000

# Feature flags
ENABLE_DOCUMENT_SEARCH=true
ENABLE_DOCUMENT_STATS=true
ENABLE_SOFT_DELETE=true

# Performance
DOCUMENT_QUERY_TIMEOUT_MS=5000
ENABLE_QUERY_CACHING=false  # Future: Redis cache

# Security
REQUIRE_AUTH_FOR_DOCUMENTS=false  # Future: authentication
EXPOSE_STORAGE_PATHS=false
```

### Default Values

```python
# Pagination
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Sorting
DEFAULT_SORT_BY = "created_at"
DEFAULT_SORT_ORDER = "desc"
ALLOWED_SORT_FIELDS = [
    "created_at", "updated_at", "document_name",
    "file_size", "access_count"
]

# Search
MIN_SEARCH_QUERY_LENGTH = 3
MAX_SEARCH_QUERY_LENGTH = 200
SEARCH_RESULT_SNIPPET_LENGTH = 200

# Statistics
STATS_DATE_RANGES = {
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
    "1y": timedelta(days=365),
    "all": None
}
```

### File Paths
No new file paths created in this step (read-only operations on existing storage)

### Docker Services Required
- **PostgreSQL**: Database queries
- **Redis** (future): Query result caching

---

## 6. ERROR HANDLING

### Failure Scenarios

#### 1. Document Not Found
**Scenario**: Client requests non-existent document ID
**Error Code**: 404
**Message**: `"Document not found"`
**Recovery**: Client should verify document ID and retry
**Logging**: `logger.warning(f"Document {document_id} not found")`

#### 2. Invalid UUID Format
**Scenario**: Malformed document ID
**Error Code**: 400
**Message**: `"Invalid document ID format"`
**Recovery**: Client validates UUID before sending
**Logging**: `logger.debug(f"Invalid UUID format: {document_id}")`

#### 3. Database Connection Lost
**Scenario**: PostgreSQL unavailable
**Error Code**: 503
**Message**: `"Service temporarily unavailable"`
**Recovery**: Automatic retry with exponential backoff
**Logging**: `logger.error(f"Database connection lost: {error}")`

#### 4. Query Timeout
**Scenario**: Complex query exceeds 5 second timeout
**Error Code**: 504
**Message**: `"Request timeout"`
**Recovery**: Simplify query, reduce page size, add indexes
**Logging**: `logger.error(f"Query timeout for: {query}")`

#### 5. Invalid Filter Parameters
**Scenario**: Client provides invalid filter combinations
**Error Code**: 400
**Message**: `"Invalid filter: max_size must be >= min_size"`
**Recovery**: Client corrects filter parameters
**Logging**: `logger.debug(f"Invalid filter params: {params}")`

### Error Response Format

```json
{
    "detail": "Document not found",
    "error_code": "DOCUMENT_NOT_FOUND",
    "timestamp": "2024-01-16T10:30:00Z",
    "request_id": "req-abc123",
    "path": "/api/v1/documents/550e8400-e29b-41d4-a716-446655440000"
}
```

### Rollback Procedures

**Read Operations**: No rollback needed (no state changes)

**Delete Operation Rollback**:
```python
try:
    # Soft delete
    document.is_deleted = True
    document.deleted_at = datetime.utcnow()
    db.commit()
except Exception as e:
    db.rollback()
    logger.error(f"Failed to delete document {document_id}: {e}")
    raise HTTPException(status_code=500, detail="Deletion failed")
```

### Logging Points

```python
# Request start
logger.info(f"GET /documents - user={user_id}, filters={filters}")

# Query execution
logger.debug(f"Executing query: {sql_query}")

# Results
logger.info(f"Returned {len(results)} documents in {elapsed_ms}ms")

# Errors
logger.error(f"Document query failed: {error}", exc_info=True)

# Performance warnings
if elapsed_ms > 1000:
    logger.warning(f"Slow query detected: {elapsed_ms}ms")

# Access tracking
logger.debug(f"Document {document_id} accessed by {user_id}")
```

---

## 7. TESTING CHECKLIST

### Manual Testing Steps

#### Test 1: Get Document by ID
```bash
# Success case
curl http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440000

# Expected: 200 OK with full document JSON
# Verify: All fields populated, metadata correct, timestamps valid

# Not found case
curl http://localhost:8000/api/v1/documents/00000000-0000-0000-0000-000000000000

# Expected: 404 Not Found
# Verify: Clear error message

# Invalid UUID
curl http://localhost:8000/api/v1/documents/invalid-id

# Expected: 400 Bad Request
# Verify: "Invalid document ID format"
```

#### Test 2: List Documents with Pagination
```bash
# Basic list
curl "http://localhost:8000/api/v1/documents?page=1&page_size=10"

# Expected: 200 OK with 10 documents
# Verify: total, page, page_size, has_next, has_previous fields correct

# Large page size
curl "http://localhost:8000/api/v1/documents?page_size=500"

# Expected: 400 Bad Request
# Verify: "page_size must be between 1 and 100"

# Filter by status
curl "http://localhost:8000/api/v1/documents?status=completed&page_size=20"

# Expected: 200 OK, all returned docs have status="completed"

# Filter by date range
curl "http://localhost:8000/api/v1/documents?created_after=2024-01-01&created_before=2024-01-31"

# Expected: All docs created in January 2024
```

#### Test 3: Search Documents
```bash
# Basic search
curl "http://localhost:8000/api/v1/documents/search?q=financial+report"

# Expected: 200 OK with matching documents
# Verify: Relevance scores, matched fields, snippets

# Empty results
curl "http://localhost:8000/api/v1/documents/search?q=nonexistentquery123"

# Expected: 200 OK with empty items array

# Query too short
curl "http://localhost:8000/api/v1/documents/search?q=ab"

# Expected: 400 Bad Request
# Verify: "Search query must be at least 3 characters"
```

#### Test 4: Document Statistics
```bash
# Overall stats
curl "http://localhost:8000/api/v1/documents/stats"

# Expected: 200 OK with counts, sizes, distributions
# Verify: total_documents > 0, by_status counts sum to total

# Stats by MIME type
curl "http://localhost:8000/api/v1/documents/stats?group_by=mime_type"

# Expected: Breakdown by file types
# Verify: PDF, DOCX, etc. counts

# Date range stats
curl "http://localhost:8000/api/v1/documents/stats?date_range=30d"

# Expected: Only last 30 days data
```

#### Test 5: Delete Document
```bash
# Soft delete
curl -X DELETE "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440000"

# Expected: 200 OK with success message
# Verify: Document no longer appears in list (unless include_deleted=true)
# Verify: is_deleted=TRUE in database

# Try deleting again
curl -X DELETE "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440000"

# Expected: 404 Not Found (already deleted)

# Delete processing document
# (First upload a doc and start processing)
curl -X DELETE "http://localhost:8000/api/v1/documents/{processing_doc_id}"

# Expected: 409 Conflict
# Verify: "Cannot delete document while processing"
```

### Edge Cases to Verify

1. **Empty Database**: List returns empty array with total=0
2. **Single Document**: Pagination works with 1 item
3. **Exact Page Boundary**: page_size=20, total=20 returns has_next=false
4. **Special Characters in Search**: Query with "quotes", <html>, etc.
5. **Very Large Metadata**: Documents with >1MB JSONB metadata
6. **Concurrent Access**: Two clients get same document simultaneously
7. **Soft-Deleted Documents**: Don't appear unless `include_deleted=true`
8. **Missing Metadata**: Documents with null or empty metadata
9. **Tag Filtering**: Document with tags ["a", "b"] matches filter tags=["a"]
10. **Sort by Null Fields**: Documents without `last_accessed_at`

### Performance Benchmarks

```
GET /documents/{id}           < 50ms (p95)
GET /documents?page_size=20   < 100ms (p95)
GET /documents/search?q=...   < 200ms (p95)
GET /documents/stats          < 500ms (p95)
DELETE /documents/{id}        < 100ms (p95)

Database query times:
- Get by ID:           < 5ms
- List with filters:   < 50ms
- Search query:        < 100ms
- Stats aggregation:   < 200ms

Memory usage:
- List 100 documents:  < 5MB
- Stats calculation:   < 10MB
```

---

## 8. MONITORING & METRICS

### Metrics Collected

#### Request Metrics
```python
# Prometheus metrics
document_requests_total = Counter(
    "document_requests_total",
    "Total document API requests",
    ["endpoint", "method", "status_code"]
)

document_request_duration = Histogram(
    "document_request_duration_seconds",
    "Document API request duration",
    ["endpoint"]
)

document_results_returned = Histogram(
    "document_results_returned",
    "Number of documents returned per request",
    ["endpoint"]
)
```

#### Database Metrics
```python
database_query_duration = Histogram(
    "database_query_duration_seconds",
    "Database query execution time",
    ["query_type"]
)

database_query_errors = Counter(
    "database_query_errors_total",
    "Database query errors",
    ["error_type"]
)
```

#### Business Metrics
```python
documents_accessed = Counter(
    "documents_accessed_total",
    "Total document accesses",
    ["access_type"]  # by_id, list, search
)

documents_deleted = Counter(
    "documents_deleted_total",
    "Total documents deleted",
    ["delete_type"]  # soft, hard
)

search_queries_executed = Counter(
    "search_queries_executed_total",
    "Total search queries",
    ["has_results"]  # true, false
)
```

### Log Entries Generated

```python
# INFO level
logger.info(f"Document {document_id} retrieved in {elapsed_ms}ms")
logger.info(f"Listed {count} documents with filters: {filters}")
logger.info(f"Search query '{query}' returned {count} results")
logger.info(f"Document {document_id} soft deleted by user {user_id}")

# DEBUG level
logger.debug(f"SQL query: {query}")
logger.debug(f"Pagination: page={page}, size={page_size}")
logger.debug(f"Filter params: {filter_params}")

# WARNING level
logger.warning(f"Slow query detected: {elapsed_ms}ms > 1000ms")
logger.warning(f"Document {document_id} accessed {access_count} times")
logger.warning(f"Search query returned 0 results: {query}")

# ERROR level
logger.error(f"Failed to retrieve document {document_id}: {error}")
logger.error(f"Database query failed: {error}", exc_info=True)
logger.error(f"Document deletion failed: {error}")
```

### Health Check Indicators

```python
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "checks": {
            "database": await check_database_connection(),
            "documents_table": await check_documents_table_exists(),
            "query_performance": await check_query_performance()
        }
    }

async def check_query_performance():
    """Verify queries complete within acceptable time"""
    start = time.time()
    await db.execute("SELECT 1")
    elapsed = time.time() - start

    return {
        "status": "healthy" if elapsed < 0.1 else "degraded",
        "latency_ms": elapsed * 1000
    }
```

### Performance Measurements

```python
# Track query performance
@middleware("http")
async def track_query_performance(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    elapsed = time.time() - start_time

    # Log slow queries
    if elapsed > 1.0:
        logger.warning(
            f"Slow request: {request.method} {request.url.path} "
            f"took {elapsed:.2f}s"
        )

    # Add header
    response.headers["X-Response-Time"] = f"{elapsed:.3f}"

    return response
```

---

## 9. SECURITY CONSIDERATIONS

### Authentication/Authorization
```python
# Future: Add authentication dependency
from app.core.auth import get_current_user

@router.get("/documents/{document_id}")
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user)  # Future
):
    # Check user has permission to access document
    if not has_document_access(current_user, document_id):
        raise HTTPException(status_code=403, detail="Access denied")
    ...
```

### Input Sanitization
```python
# Sanitize search queries to prevent injection
def sanitize_search_query(query: str) -> str:
    """Remove SQL injection attempts"""
    # Use parameterized queries (already handled by SQLAlchemy)
    # Escape special characters for LIKE queries
    return query.replace("%", "\\%").replace("_", "\\_")

# Validate UUID format
from uuid import UUID

def validate_document_id(document_id: str) -> UUID:
    try:
        return UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID format"
        )
```

### Path Traversal Prevention
```python
# NEVER expose raw storage_path in API responses
# Use sanitized paths only

def get_safe_storage_path(document: Document) -> Optional[str]:
    """Return storage path only if authorized"""
    # Only return to authenticated admin users
    if not current_user or not current_user.is_admin:
        return None
    return document.storage_path

# In response model
class DocumentResponse(BaseModel):
    storage_path: Optional[str] = None  # Only for admins
```

### SQL Injection Prevention
```python
# ALWAYS use parameterized queries
# SQLAlchemy handles this automatically

# GOOD ✅
query = db.query(Document).filter(Document.id == document_id)

# BAD ❌ (Never do this)
query = db.execute(f"SELECT * FROM documents WHERE id = '{document_id}'")

# For LIKE queries, use bind parameters
query = db.query(Document).filter(
    Document.document_name.ilike(f"%{sanitized_query}%")
)
```

### Metadata XSS Prevention
```python
# Escape HTML/JavaScript in metadata when returning to clients
import html

def sanitize_metadata(metadata: dict) -> dict:
    """Escape HTML in metadata values"""
    return {
        key: html.escape(str(value)) if isinstance(value, str) else value
        for key, value in metadata.items()
    }

# In endpoint
response_metadata = sanitize_metadata(document.document_metadata)
```

### Rate Limiting (Future)
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/documents")
@limiter.limit("100/minute")  # Max 100 requests per minute
async def list_documents(...):
    ...

@router.get("/documents/search")
@limiter.limit("50/minute")   # Search is more expensive
async def search_documents(...):
    ...
```

### File Type Restrictions
```python
# Don't expose documents with dangerous MIME types
BLOCKED_MIME_TYPES = [
    "application/x-executable",
    "application/x-msdownload",
    "application/x-sh"
]

def validate_document_access(document: Document):
    if document.mime_type in BLOCKED_MIME_TYPES:
        raise HTTPException(
            status_code=403,
            detail="Access to this file type is restricted"
        )
```

---

## 10. CODE PATTERNS & CONVENTIONS

### Design Patterns Used

#### 1. Repository Pattern
```python
class DocumentRepository:
    """Data access layer for documents"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, document_id: UUID) -> Optional[Document]:
        return self.db.query(Document).filter(
            Document.id == document_id,
            Document.is_deleted == False
        ).first()

    def list(self, filters: DocumentFilterParams,
             pagination: PaginationParams) -> List[Document]:
        query = self.db.query(Document).filter(
            Document.is_deleted == False
        )

        # Apply filters
        query = self._apply_filters(query, filters)

        # Apply sorting
        query = self._apply_sorting(query, filters)

        # Apply pagination
        offset = (pagination.page - 1) * pagination.page_size
        query = query.offset(offset).limit(pagination.page_size)

        return query.all()
```

#### 2. Service Layer Pattern
```python
class DocumentService:
    """Business logic for document operations"""

    def __init__(self, db: Session):
        self.repository = DocumentRepository(db)

    async def get_document(
        self,
        document_id: UUID,
        include_processing_status: bool = True
    ) -> DocumentResponse:
        """Get document with business logic"""
        document = self.repository.get_by_id(document_id)

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Track access
        await self._track_access(document)

        # Load processing status if requested
        if include_processing_status:
            processing_status = await self._get_processing_status(document_id)

        return self._to_response(document, processing_status)
```

#### 3. Dependency Injection
```python
def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    """Dependency injection for service layer"""
    return DocumentService(db)

@router.get("/documents/{document_id}")
async def get_document(
    document_id: UUID,
    service: DocumentService = Depends(get_document_service)
):
    return await service.get_document(document_id)
```

### Naming Conventions

```python
# Classes: PascalCase
class DocumentService
class DocumentRepository
class DocumentFilterParams

# Functions/Methods: snake_case
def get_document_by_id()
async def list_documents()
def _apply_filters()  # Private method (prefix with _)

# Constants: UPPER_SNAKE_CASE
DEFAULT_PAGE_SIZE = 20
MAX_SEARCH_QUERY_LENGTH = 200

# Variables: snake_case
document_id = UUID(...)
filter_params = DocumentFilterParams(...)

# Pydantic Models: PascalCase
class DocumentResponse(BaseModel)
class PaginationParams(BaseModel)

# API Endpoints: kebab-case (in URLs)
GET /api/v1/documents
GET /api/v1/documents/search
GET /api/v1/documents/stats
```

### Async/Await Patterns

```python
# Use async for I/O-bound operations
async def get_document(document_id: UUID) -> Document:
    # Database query (async if using async driver)
    document = await db.get(Document, document_id)

    # Multiple async operations in parallel
    processing_status, access_count = await asyncio.gather(
        get_processing_status(document_id),
        increment_access_count(document_id)
    )

    return document

# Use sync for CPU-bound operations
def calculate_relevance_score(query: str, document: Document) -> float:
    # Pure computation, no I/O
    score = ...
    return score
```

### Transaction Boundaries

```python
# Explicit transaction for multi-step operations
from sqlalchemy.orm import Session

async def delete_document(document_id: UUID, db: Session):
    try:
        # Start transaction (implicit with db context)
        document = db.query(Document).filter_by(id=document_id).first()

        if not document:
            raise HTTPException(status_code=404, detail="Not found")

        # Update document
        document.is_deleted = True
        document.deleted_at = datetime.utcnow()

        # Update related records
        db.query(ProcessingStatus).filter_by(
            document_id=document_id
        ).update({"is_active": False})

        # Commit transaction
        db.commit()

        # Queue async cleanup (outside transaction)
        cleanup_document_files.delay(str(document_id))

        return {"success": True}

    except Exception as e:
        # Rollback on any error
        db.rollback()
        logger.error(f"Delete failed: {e}")
        raise
```

### Error Propagation Strategy

```python
# Layer 1: Repository (Data Access)
class DocumentRepository:
    def get_by_id(self, document_id: UUID) -> Optional[Document]:
        # Return None if not found (no exception)
        return self.db.query(Document).filter_by(id=document_id).first()

# Layer 2: Service (Business Logic)
class DocumentService:
    def get_document(self, document_id: UUID) -> Document:
        document = self.repository.get_by_id(document_id)

        # Raise business logic exception
        if not document:
            raise DocumentNotFoundError(f"Document {document_id} not found")

        return document

# Layer 3: API (Presentation)
@router.get("/documents/{document_id}")
async def get_document_endpoint(document_id: UUID):
    try:
        service = DocumentService(db)
        document = service.get_document(document_id)
        return DocumentResponse.from_orm(document)

    except DocumentNotFoundError as e:
        # Convert to HTTP exception
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## 11. INTEGRATION POINTS

### Database Queries Executed

#### Query 1: Get Document by ID
```sql
SELECT
    d.*,
    ps.stage,
    ps.status as stage_status,
    ps.started_at,
    ps.completed_at
FROM documents d
LEFT JOIN processing_status ps ON d.id = ps.document_id
WHERE d.id = $1 AND d.is_deleted = FALSE
```

#### Query 2: List Documents with Filters
```sql
SELECT * FROM documents
WHERE is_deleted = FALSE
  AND ($1::text IS NULL OR status = $1)
  AND ($2::text IS NULL OR mime_type = $2)
  AND ($3::bigint IS NULL OR file_size >= $3)
  AND ($4::bigint IS NULL OR file_size <= $4)
  AND ($5::timestamptz IS NULL OR created_at >= $5)
  AND ($6::timestamptz IS NULL OR created_at <= $6)
ORDER BY created_at DESC
LIMIT $7 OFFSET $8
```

#### Query 3: Count Documents
```sql
SELECT COUNT(*) FROM documents
WHERE is_deleted = FALSE
  AND (/* same filters as Query 2 */)
```

#### Query 4: Search Documents
```sql
SELECT * FROM documents
WHERE is_deleted = FALSE
  AND (
    document_name ILIKE $1
    OR original_name ILIKE $1
    OR document_metadata::text ILIKE $1
  )
ORDER BY updated_at DESC
LIMIT $2 OFFSET $3
```

#### Query 5: Statistics Aggregation
```sql
-- Total count and size
SELECT
    COUNT(*) as total_documents,
    SUM(file_size) as total_size
FROM documents
WHERE is_deleted = FALSE;

-- By status
SELECT status, COUNT(*) as count
FROM documents
WHERE is_deleted = FALSE
GROUP BY status;

-- By MIME type
SELECT mime_type, COUNT(*) as count
FROM documents
WHERE is_deleted = FALSE
GROUP BY mime_type
ORDER BY count DESC
LIMIT 10;

-- Upload trend
SELECT
    DATE(created_at) as date,
    COUNT(*) as count
FROM documents
WHERE is_deleted = FALSE
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date;
```

#### Query 6: Increment Access Counter
```sql
UPDATE documents
SET
    access_count = access_count + 1,
    last_accessed_at = NOW()
WHERE id = $1
```

### External Services Called

1. **Database (PostgreSQL)**:
   - Connection pool managed by SQLAlchemy
   - Timeout: 5 seconds per query
   - Retry: 3 attempts with exponential backoff

2. **Processing Status Service** (internal):
   - Called when `include_processing_status=true`
   - Returns detailed processing stage information
   - Async call, non-blocking

3. **Storage Service** (future):
   - May call to verify file existence
   - Generate presigned download URLs

### Events Published

```python
# Document accessed event (future: event bus)
{
    "event_type": "document.accessed",
    "document_id": "550e8400-...",
    "user_id": "user-123",
    "access_type": "view",  # view, download, list
    "timestamp": "2024-01-16T10:30:00Z"
}

# Document deleted event
{
    "event_type": "document.deleted",
    "document_id": "550e8400-...",
    "deleted_by": "user-123",
    "delete_type": "soft",  # soft, hard
    "timestamp": "2024-01-16T11:00:00Z"
}

# Search performed event
{
    "event_type": "document.search",
    "query": "financial report",
    "results_count": 8,
    "user_id": "user-123",
    "timestamp": "2024-01-16T10:45:00Z"
}
```

### Events Consumed
None (Step 7 is primarily read-only, doesn't consume events)

---

## 12. TROUBLESHOOTING GUIDE

### Common Issues and Solutions

#### Issue 1: "Document not found" but document exists in database
**Symptoms**: GET request returns 404, but SELECT query shows document exists

**Possible Causes**:
1. Document has `is_deleted=TRUE`
2. UUID format mismatch (string vs UUID type)
3. Different database connection/schema

**Debug Commands**:
```sql
-- Check if document exists
SELECT id, document_name, is_deleted, status
FROM documents
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

-- Check if it's soft deleted
SELECT * FROM documents
WHERE id = '550e8400-...' AND is_deleted = TRUE;
```

**Solution**:
- If `is_deleted=TRUE`: Document was soft deleted, use `include_deleted=true` param
- If UUID mismatch: Ensure client sends proper UUID format
- If schema issue: Verify database connection string

---

#### Issue 2: Pagination returns incorrect total count
**Symptoms**: `total_pages` doesn't match actual data

**Possible Causes**:
1. Filters applied to data query but not count query
2. Concurrent inserts/deletes during pagination
3. Soft-deleted documents included in count

**Debug Commands**:
```sql
-- Manual count with same filters
SELECT COUNT(*) FROM documents
WHERE is_deleted = FALSE
  AND status = 'completed';

-- Check for timing issues
SELECT COUNT(*), is_deleted, status
FROM documents
GROUP BY is_deleted, status;
```

**Solution**:
- Ensure count query uses identical WHERE clause as data query
- Add transaction isolation if needed
- Log both queries for comparison

---

#### Issue 3: Search returns no results for known documents
**Symptoms**: Search query returns empty results, but manual query finds documents

**Possible Causes**:
1. Search query too short (< 3 characters)
2. Special characters not escaped in ILIKE
3. Case sensitivity issues
4. Metadata not being searched

**Debug Commands**:
```sql
-- Test manual search
SELECT document_name, original_name
FROM documents
WHERE document_name ILIKE '%financial%';

-- Check metadata structure
SELECT document_metadata
FROM documents
WHERE id = '550e8400-...';

-- Test JSONB search
SELECT * FROM documents
WHERE document_metadata::text ILIKE '%financial%';
```

**Solution**:
- Verify query length >= 3 characters
- Escape special characters: `%`, `_`, `\`
- Use PostgreSQL full-text search for better results (future enhancement)

---

#### Issue 4: Slow query performance (>1 second)
**Symptoms**: GET /documents takes multiple seconds

**Possible Causes**:
1. Missing database indexes
2. Large page_size (e.g., 100)
3. Complex JSONB queries
4. Table scan instead of index usage

**Debug Commands**:
```sql
-- Check query execution plan
EXPLAIN ANALYZE
SELECT * FROM documents
WHERE status = 'completed'
ORDER BY created_at DESC
LIMIT 20;

-- Check existing indexes
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'documents';

-- Check table statistics
SELECT
    schemaname,
    tablename,
    n_live_tup,
    n_dead_tup
FROM pg_stat_user_tables
WHERE tablename = 'documents';
```

**Solution**:
```sql
-- Add missing indexes
CREATE INDEX idx_documents_status ON documents(status)
WHERE is_deleted = FALSE;

CREATE INDEX idx_documents_created_at ON documents(created_at DESC)
WHERE is_deleted = FALSE;

CREATE INDEX idx_documents_mime_type ON documents(mime_type)
WHERE is_deleted = FALSE;

-- For metadata search (GIN index)
CREATE INDEX idx_documents_metadata_gin ON documents
USING GIN (document_metadata);

-- Analyze table
ANALYZE documents;
```

---

#### Issue 5: Access count not incrementing
**Symptoms**: `access_count` stays at 0 despite document views

**Possible Causes**:
1. UPDATE query not executing
2. Transaction not committing
3. Database permissions issue

**Debug Commands**:
```sql
-- Check current access count
SELECT id, document_name, access_count, last_accessed_at
FROM documents
WHERE id = '550e8400-...';

-- Manual increment test
UPDATE documents
SET access_count = access_count + 1,
    last_accessed_at = NOW()
WHERE id = '550e8400-...'
RETURNING access_count, last_accessed_at;
```

**Solution**:
- Ensure `db.commit()` is called after UPDATE
- Check application logs for UPDATE errors
- Verify database user has UPDATE permission

---

#### Issue 6: Delete endpoint returns 409 "Cannot delete while processing"
**Symptoms**: DELETE request rejected even though document appears idle

**Possible Causes**:
1. Stale processing status in database
2. Processing task stuck/crashed
3. Race condition with processing start

**Debug Commands**:
```sql
-- Check processing status
SELECT
    d.id,
    d.status,
    ps.stage,
    ps.status as stage_status,
    ps.started_at,
    ps.completed_at
FROM documents d
LEFT JOIN processing_status ps ON d.id = ps.document_id
WHERE d.id = '550e8400-...';

-- Check for stuck processing
SELECT * FROM processing_status
WHERE document_id = '550e8400-...'
  AND status = 'in_progress'
  AND started_at < NOW() - INTERVAL '1 hour';
```

**Solution**:
```sql
-- Reset stuck processing status
UPDATE documents
SET status = 'failed'
WHERE id = '550e8400-...'
  AND status = 'processing';

-- Or force delete (admin only)
DELETE FROM processing_status
WHERE document_id = '550e8400-...'
  AND status = 'in_progress'
  AND started_at < NOW() - INTERVAL '1 hour';
```

---

### Log Locations

```bash
# Application logs
/var/log/querybox/app.log
/var/log/querybox/error.log

# Access logs
/var/log/querybox/access.log

# Database query logs (if enabled)
/var/log/postgresql/postgresql-14-main.log

# Docker logs
docker logs querybox-backend
docker logs querybox-postgres
```

### Debug Queries for Verification

```sql
-- 1. Verify document exists and is accessible
SELECT
    id,
    document_name,
    status,
    is_deleted,
    created_at
FROM documents
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

-- 2. Check document counts by status
SELECT
    status,
    COUNT(*) as count,
    SUM(file_size) as total_size
FROM documents
WHERE is_deleted = FALSE
GROUP BY status;

-- 3. Find recently accessed documents
SELECT
    id,
    document_name,
    access_count,
    last_accessed_at
FROM documents
WHERE last_accessed_at IS NOT NULL
ORDER BY last_accessed_at DESC
LIMIT 10;

-- 4. Check for orphaned processing status
SELECT
    ps.document_id,
    ps.stage,
    ps.status,
    d.id IS NULL as orphaned
FROM processing_status ps
LEFT JOIN documents d ON ps.document_id = d.id
WHERE d.id IS NULL;

-- 5. Performance: Slowest queries
SELECT
    query,
    calls,
    total_time / calls as avg_time_ms,
    total_time
FROM pg_stat_statements
WHERE query LIKE '%documents%'
ORDER BY total_time DESC
LIMIT 10;

-- 6. Find documents without metadata
SELECT
    id,
    document_name,
    document_metadata
FROM documents
WHERE document_metadata IS NULL
   OR document_metadata = '{}'::jsonb;

-- 7. Check soft-deleted documents
SELECT
    id,
    document_name,
    deleted_at,
    deleted_by_user_id
FROM documents
WHERE is_deleted = TRUE
ORDER BY deleted_at DESC
LIMIT 20;
```

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Core Endpoints (1.5 hours)
- [ ] Create `/app/services/document_service.py`
- [ ] Implement `DocumentService.get_document_by_id()`
- [ ] Implement `DocumentService.list_documents()`
- [ ] Update `/app/schemas/document.py` with full response models
- [ ] Implement GET `/api/v1/documents/{document_id}` endpoint
- [ ] Implement GET `/api/v1/documents` with pagination
- [ ] Add access counter increment on document retrieval
- [ ] Test both endpoints with Postman/curl

### Phase 2: Search & Stats (1 hour)
- [ ] Implement `DocumentService.search_documents()`
- [ ] Implement `DocumentService.get_document_stats()`
- [ ] Create search request/response schemas
- [ ] Implement GET `/api/v1/documents/search` endpoint
- [ ] Implement GET `/api/v1/documents/stats` endpoint
- [ ] Add database indexes for search performance
- [ ] Test search with various queries

### Phase 3: Delete & Tests (0.5 hours)
- [ ] Implement `DocumentService.soft_delete_document()`
- [ ] Implement DELETE `/api/v1/documents/{document_id}` endpoint
- [ ] Create `/tests/api/test_documents.py`
- [ ] Write unit tests for all endpoints
- [ ] Write integration tests for filters and pagination
- [ ] Test edge cases (empty DB, invalid UUIDs, etc.)
- [ ] Document API with OpenAPI examples

---

## DEPENDENCIES & PREREQUISITES

### Required from Previous Steps:
✅ Step 1: PostgreSQL with `documents` table
✅ Step 2: FastAPI application structure
✅ Step 3: Document upload creates records
✅ Step 4: File validation populates metadata
✅ Step 5: Storage paths recorded in database
✅ Step 6: Rich metadata available for filtering

### New Dependencies to Install:
None (uses existing FastAPI, SQLAlchemy, Pydantic)

### Database Migrations:
```sql
-- Add indexes for query performance (if not exist)
CREATE INDEX IF NOT EXISTS idx_documents_status_not_deleted
ON documents(status) WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_documents_created_at_desc
ON documents(created_at DESC) WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_documents_mime_type
ON documents(mime_type) WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_documents_metadata_gin
ON documents USING GIN (document_metadata);

CREATE INDEX IF NOT EXISTS idx_documents_tags_gin
ON documents USING GIN (tags);
```

---

## SUCCESS CRITERIA

✅ **Functional Requirements**:
- [ ] Can retrieve any document by UUID in < 50ms
- [ ] List endpoint supports pagination (max 100 items/page)
- [ ] Filtering works for status, MIME type, date ranges, tags
- [ ] Search returns relevant results in < 200ms
- [ ] Statistics endpoint provides accurate counts and aggregations
- [ ] Soft delete prevents document from appearing in queries
- [ ] Access counter increments on every GET by ID request

✅ **Non-Functional Requirements**:
- [ ] All endpoints have comprehensive error handling
- [ ] Input validation prevents invalid queries
- [ ] Database queries use proper indexes
- [ ] API responses follow consistent schema
- [ ] Pagination metadata is accurate
- [ ] Logging captures all important events

✅ **Testing**:
- [ ] Unit tests cover all service methods
- [ ] Integration tests verify endpoint behavior
- [ ] Edge cases handled (empty DB, invalid inputs)
- [ ] Performance benchmarks met

---

**End of Document**
