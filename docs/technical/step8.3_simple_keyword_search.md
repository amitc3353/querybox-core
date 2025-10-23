# Step 8.3: Simple Keyword Search - Technical Documentation

**Version:** 1.0
**Last Updated:** 2025-10-23
**Status:** Design & Planning
**Author:** QueryBox Core Team
**Related Steps:** Step 8.1 (Text Extraction), Step 8.2 (Chunking), Step 9.1 (Embeddings)

---

## Table of Contents
1. [Feature Overview](#1-feature-overview)
2. [Technical Implementation](#2-technical-implementation)
3. [Data Flow](#3-data-flow)
4. [Validations & Constraints](#4-validations--constraints)
5. [Configuration](#5-configuration)
6. [Error Handling](#6-error-handling)
7. [Testing Checklist](#7-testing-checklist)
8. [Monitoring & Metrics](#8-monitoring--metrics)
9. [Security Considerations](#9-security-considerations)
10. [Code Patterns & Conventions](#10-code-patterns--conventions)
11. [Integration Points](#11-integration-points)
12. [Troubleshooting Guide](#12-troubleshooting-guide)

---

## 1. FEATURE OVERVIEW

### 1.1 What This Step Accomplishes

Step 8.3 implements **keyword-based document search** that enables users to search through uploaded documents using text queries. This is the foundation for the retrieval system before semantic/vector search is implemented.

**Key Capabilities:**
- **Full-text search**: Search across document content and chunks using PostgreSQL's text search
- **Multi-source search**: Searches both `document_texts.full_text` and `embeddings.chunk_text`
- **Relevance ranking**: Orders results by relevance using ts_rank
- **Context snippets**: Returns highlighted text excerpts with matched keywords
- **Metadata filtering**: Filter by document type, date, status
- **Pagination support**: Handles large result sets efficiently
- **Quality validation**: Includes extraction quality metrics for testing

**Business Value:**
- Enables immediate document search without embeddings
- Validates extraction quality (Step 8.1) and chunking (Step 8.2)
- Provides baseline retrieval for comparison with semantic search (Step 9)
- Delivers MVP search functionality quickly

### 1.2 Why This Step Is Necessary

**RAG Pipeline Requirements:**
1. **Early Testing**: Validate text extraction and chunking before investing in embeddings
2. **Fallback Search**: Provides keyword search when vector search isn't available
3. **Hybrid Foundation**: Prepares for BM25 + Vector hybrid retrieval (Step 10)
4. **Quality Assurance**: Processes 10+ sample documents to ensure system stability

**Alternative Approaches (Not Used):**
- ❌ **No keyword search**: Too risky - can't validate extraction quality
- ❌ **Jump to vector search**: Wasteful if extraction/chunking is broken
- ❌ **External search engine**: Over-engineering for MVP

**Chosen Approach:**
✅ **PostgreSQL Full-Text Search with ts_vector**: Native, fast, sufficient for MVP

### 1.3 Dependencies on Previous Steps

| Step | Dependency | Why Required |
|------|-----------|--------------|
| **Step 1** | Database setup | PostgreSQL with text search capabilities |
| **Step 2** | FastAPI structure | REST API endpoints |
| **Step 3** | Upload handler | Documents must be uploaded first |
| **Step 8.1** | Text extraction | **CRITICAL**: Searches extracted text from `document_texts` |
| **Step 8.2** | Chunking | **CRITICAL**: Searches chunks from `embeddings` table |

**Blocking Requirements:**
- Steps 8.1 and 8.2 MUST be complete
- At least 10 sample documents uploaded and processed

### 1.4 What Future Steps Depend on This

| Future Step | How It Uses Keyword Search |
|------------|---------------------------|
| **Step 9.1** | Benchmark vector search against keyword baseline |
| **Step 10.1** | BM25 + Vector hybrid retrieval uses this keyword search |
| **Step 10.3** | Citation extraction builds on search result structure |
| **Step 11.1** | Answer generation uses search results as context |
| **Step 12.1** | Semantic cache compares query similarity |

**Critical for:**
- Hybrid retrieval accuracy (BM25 component)
- Search quality benchmarking
- Result formatting and citation structure

---

## 2. TECHNICAL IMPLEMENTATION

### 2.1 Files to Create/Modify

#### **New Files (8 files):**

1. **`backend/app/services/search/keyword_search_service.py`**
   - Core keyword search logic
   - PostgreSQL full-text search implementation
   - Result ranking and snippet generation
   - ~400 lines

2. **`backend/app/services/search/__init__.py`**
   - Package initialization
   - Export `KeywordSearchService` and factory
   - ~30 lines

3. **`backend/app/schemas/search.py`** *(May already exist)*
   - Pydantic models for search requests/responses
   - `SearchQuery`, `SearchResponse`, `SearchResult`
   - ~150 lines

4. **`backend/app/services/search/quality_validator.py`**
   - Extraction quality validation
   - Document processing verification
   - ~200 lines

5. **`backend/tests/unit/services/test_keyword_search.py`**
   - Unit tests for search logic
   - Query parsing tests
   - Ranking validation
   - ~250 lines

6. **`backend/tests/integration/test_search_pipeline.py`**
   - End-to-end search testing
   - 10+ sample document processing
   - Quality metrics validation
   - ~300 lines

7. **`backend/scripts/process_sample_documents.py`**
   - Script to process 10+ sample PDFs
   - Validation and reporting
   - ~200 lines

8. **`backend/docs/technical/step8.3_simple_keyword_search.md`**
   - This documentation file

#### **Modified Files (5 files):**

1. **`backend/app/api/v1/endpoints/search.py`**
   - Implement POST `/api/v1/search` endpoint
   - Add GET `/api/v1/search/validate` for quality checks
   - Replace stub with full implementation
   - ~200 lines (complete rewrite)

2. **`backend/app/api/v1/endpoints/documents.py`**
   - Add GET `/documents/{id}/search-quality` endpoint
   - Returns extraction and chunking quality metrics
   - ~50 lines added

3. **`backend/app/schemas/__init__.py`**
   - Export search schemas
   - ~5 lines added

4. **`backend/app/db/database.py`** *(Optional)*
   - Add search-specific indexes if needed
   - ~10 lines added

5. **`backend/db/migrations/004_add_search_indexes.sql`**
   - Add GIN indexes for full-text search
   - Add materialized view for search performance
   - ~100 lines

### 2.2 Key Classes, Functions, and Methods

#### **Class: `KeywordSearchService` (keyword_search_service.py)**

```python
class KeywordSearchService:
    """
    Keyword-based document search using PostgreSQL full-text search

    Features:
    - Full-text search with ts_vector
    - Searches both full documents and chunks
    - Relevance ranking with ts_rank
    - Context snippet generation
    - Metadata filtering
    """

    def __init__(
        self,
        db: Session,
        default_limit: int = 10,
        snippet_length: int = 200
    ):
        """Initialize search service"""

    async def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 10,
        offset: int = 0
    ) -> SearchResponse:
        """
        Execute keyword search across documents

        Args:
            query: Search query string
            filters: Optional metadata filters (document_type, date_range, etc.)
            limit: Max results to return
            offset: Pagination offset

        Returns:
            SearchResponse with ranked results and metadata
        """

    def _build_tsquery(self, query: str) -> str:
        """Convert user query to PostgreSQL tsquery format"""

    async def _search_full_documents(
        self,
        tsquery: str,
        filters: Optional[SearchFilters],
        limit: int
    ) -> List[DocumentMatch]:
        """Search full document texts"""

    async def _search_chunks(
        self,
        tsquery: str,
        filters: Optional[SearchFilters],
        limit: int
    ) -> List[ChunkMatch]:
        """Search individual chunks"""

    def _merge_results(
        self,
        doc_matches: List[DocumentMatch],
        chunk_matches: List[ChunkMatch],
        limit: int
    ) -> List[SearchResult]:
        """Merge and deduplicate document and chunk results"""

    def _generate_snippet(
        self,
        text: str,
        query_terms: List[str],
        max_length: int = 200
    ) -> str:
        """Generate highlighted context snippet"""

    def _calculate_relevance_score(
        self,
        ts_rank: float,
        text_length: int,
        extraction_quality: float
    ) -> float:
        """Calculate final relevance score"""
```

#### **Class: `QualityValidator` (quality_validator.py)**

```python
class QualityValidator:
    """
    Validates extraction and processing quality

    Used for testing and quality assurance of Steps 8.1 and 8.2
    """

    def __init__(self, db: Session):
        """Initialize validator with database session"""

    async def validate_document_extraction(
        self,
        document_id: UUID
    ) -> ExtractionQualityReport:
        """
        Validate extraction quality for a document

        Checks:
        - Text extracted successfully
        - Extraction quality score > threshold
        - Text length reasonable (not empty, not too short)
        - OCR usage tracked correctly
        - Language detected
        """

    async def validate_document_chunking(
        self,
        document_id: UUID
    ) -> ChunkingQualityReport:
        """
        Validate chunking quality

        Checks:
        - Chunks created successfully
        - Chunk count matches expected
        - Chunk sizes within acceptable range
        - No gaps in chunk_index
        - Overlap exists between chunks
        """

    async def validate_search_readiness(
        self,
        document_id: UUID
    ) -> SearchReadinessReport:
        """
        Check if document is ready for search

        Validates entire pipeline: upload → extract → chunk → search-ready
        """

    async def batch_validate_documents(
        self,
        document_ids: List[UUID]
    ) -> BatchValidationReport:
        """
        Validate multiple documents (for 10+ sample doc test)

        Returns aggregate metrics and per-document results
        """
```

#### **Pydantic Schemas (search.py)**

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SearchFilters(BaseModel):
    """Optional filters for search queries"""
    document_types: Optional[List[str]] = None  # ['pdf', 'docx']
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_quality: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[List[str]] = None

class SearchQuery(BaseModel):
    """Search request schema"""
    query: str = Field(..., min_length=1, max_length=500)
    filters: Optional[SearchFilters] = None
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)
    include_snippets: bool = True
    include_metadata: bool = True

class SearchResultItem(BaseModel):
    """Individual search result"""
    document_id: str
    document_name: str
    relevance_score: float
    snippet: Optional[str] = None
    chunk_index: Optional[int] = None
    chunk_position: Optional[dict] = None  # {start: int, end: int}
    extraction_quality: Optional[float] = None
    matched_at: datetime

class SearchResponse(BaseModel):
    """Search response with results and metadata"""
    success: bool
    query: str
    total_results: int
    returned_results: int
    results: List[SearchResultItem]
    processing_time_ms: int
    filters_applied: Optional[SearchFilters] = None
    suggestions: Optional[List[str]] = None  # Query suggestions

class ExtractionQualityReport(BaseModel):
    """Extraction quality validation report"""
    document_id: str
    document_name: str
    extraction_status: str  # 'passed', 'failed', 'warning'
    text_length: int
    extraction_quality: float
    extraction_method: str
    pages_with_ocr: int
    total_pages: int
    detected_language: Optional[str]
    issues: List[str]
    recommendations: List[str]

class SearchReadinessReport(BaseModel):
    """Overall search readiness status"""
    document_id: str
    is_search_ready: bool
    extraction_passed: bool
    chunking_passed: bool
    overall_quality_score: float
    issues: List[str]
```

### 2.3 Database Tables and Columns Used

#### **Primary Tables:**

**1. `document_texts` (from Step 8.1)**

| Column | Type | Usage in Search |
|--------|------|----------------|
| `document_id` | UUID | Join with documents table |
| `full_text` | TEXT | Full-text search source |
| `text_length` | INTEGER | Quality validation |
| `extraction_quality` | FLOAT | Filter low-quality docs |
| `extraction_method` | VARCHAR | Metadata for filtering |
| `detected_language` | VARCHAR | Language filtering |

**2. `embeddings` (from Step 8.2)**

| Column | Type | Usage in Search |
|--------|------|----------------|
| `document_id` | UUID | Join with documents |
| `chunk_index` | INTEGER | Result ordering |
| `chunk_text` | TEXT | Chunk-level search |
| `start_position` | INTEGER | Snippet positioning |
| `end_position` | INTEGER | Snippet positioning |
| `chunk_tokens` | INTEGER | Quality metric |

**3. `documents` (existing)**

| Column | Type | Usage in Search |
|--------|------|----------------|
| `id` | UUID | Primary key |
| `document_name` | VARCHAR | Display in results |
| `status` | ENUM | Filter only 'completed' |
| `mime_type` | VARCHAR | Type filtering |
| `created_at` | TIMESTAMP | Date filtering |
| `metadata` | JSONB | Custom filtering |
| `tags` | TEXT[] | Tag filtering |

#### **New Indexes (migration 004_add_search_indexes.sql):**

```sql
-- Full-text search indexes
CREATE INDEX idx_document_texts_fulltext
ON document_texts USING GIN(to_tsvector('english', full_text));

CREATE INDEX idx_embeddings_chunk_fulltext
ON embeddings USING GIN(to_tsvector('english', chunk_text));

-- Quality filtering
CREATE INDEX idx_document_texts_quality
ON document_texts(extraction_quality)
WHERE extraction_quality IS NOT NULL;

-- Combined search index
CREATE INDEX idx_document_texts_search_ready
ON document_texts(document_id, extraction_quality, text_length)
WHERE text_length > 0;
```

### 2.4 API Endpoints

#### **Primary Endpoint: POST `/api/v1/search`**

**Request:**
```json
{
  "query": "machine learning algorithms",
  "filters": {
    "document_types": ["pdf"],
    "date_from": "2025-01-01T00:00:00Z",
    "min_quality": 0.7,
    "tags": ["research"]
  },
  "limit": 10,
  "offset": 0,
  "include_snippets": true,
  "include_metadata": true
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "query": "machine learning algorithms",
  "total_results": 47,
  "returned_results": 10,
  "results": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "document_name": "ML_Research_Paper.pdf",
      "relevance_score": 0.92,
      "snippet": "...various **machine learning algorithms** including neural networks, decision trees, and support vector machines...",
      "chunk_index": 5,
      "chunk_position": {
        "start": 4200,
        "end": 5150
      },
      "extraction_quality": 0.95,
      "matched_at": "2025-10-23T14:30:00Z"
    },
    // ... more results
  ],
  "processing_time_ms": 45,
  "filters_applied": {
    "document_types": ["pdf"],
    "min_quality": 0.7
  },
  "suggestions": [
    "deep learning algorithms",
    "supervised learning"
  ]
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "error": "SEARCH_001",
  "message": "Query string cannot be empty",
  "query": ""
}
```

---

#### **Quality Validation Endpoint: GET `/api/v1/documents/{document_id}/search-quality`**

**Response (200 OK):**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_name": "sample.pdf",
  "is_search_ready": true,
  "extraction_passed": true,
  "chunking_passed": true,
  "overall_quality_score": 0.88,
  "extraction_details": {
    "text_length": 45230,
    "extraction_quality": 0.92,
    "extraction_method": "docling",
    "pages_with_ocr": 2,
    "total_pages": 10
  },
  "chunking_details": {
    "chunk_count": 47,
    "avg_chunk_size": 982,
    "chunks_in_range": 46,
    "has_proper_overlap": true
  },
  "issues": [],
  "recommendations": [
    "Quality is good for search"
  ]
}
```

---

#### **Batch Validation Endpoint: POST `/api/v1/search/validate-batch`**

**Request:**
```json
{
  "document_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001",
    // ... more IDs
  ]
}
```

**Response:**
```json
{
  "success": true,
  "total_documents": 12,
  "passed": 10,
  "failed": 2,
  "avg_quality_score": 0.85,
  "results": [
    {
      "document_id": "550e8400-...",
      "status": "passed",
      "quality_score": 0.92
    },
    // ... more results
  ],
  "summary": {
    "avg_extraction_quality": 0.87,
    "avg_chunk_count": 52,
    "total_chunks": 624,
    "languages_detected": ["en", "es"]
  }
}
```

### 2.5 Background Tasks / Workers

**No new background tasks** - Search is synchronous (real-time API response).

However, we may add optional async tasks:

#### **Optional Task: `reindex_document_search`**

```python
@celery_app.task(name="app.tasks.search_tasks.reindex_document_search")
def reindex_document_search(document_id: str) -> dict:
    """
    Rebuild search indexes for a document

    Use cases:
    - Document updated/re-extracted
    - Search index corruption
    - Manual reindexing
    """
    # Refresh materialized view
    # Update search metadata
    # Validate search readiness
```

---

## 3. DATA FLOW

### 3.1 High-Level Flow Diagram

```
┌─────────────────┐
│ User Submits    │
│ Search Query    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ POST /api/v1/search     │
│ - Validate query        │
│ - Parse filters         │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ KeywordSearchService    │
│ - Build tsquery         │
│ - Apply filters         │
└────────┬────────────────┘
         │
         ├──────────────────────┬─────────────────────┐
         ▼                      ▼                     ▼
┌──────────────────┐   ┌──────────────────┐  ┌──────────────────┐
│ Search Full Docs │   │ Search Chunks    │  │ Apply Filters    │
│ (document_texts) │   │ (embeddings)     │  │ (quality, date)  │
└────────┬─────────┘   └────────┬─────────┘  └────────┬─────────┘
         │                      │                     │
         └──────────────────────┴─────────────────────┘
                               │
                               ▼
                    ┌─────────────────────────┐
                    │ Merge & Deduplicate     │
                    │ - Rank by ts_rank       │
                    │ - Remove duplicates     │
                    │ - Apply limit/offset    │
                    └────────┬────────────────┘
                             │
                             ▼
                    ┌─────────────────────────┐
                    │ Generate Snippets       │
                    │ - Extract context       │
                    │ - Highlight keywords    │
                    └────────┬────────────────┘
                             │
                             ▼
                    ┌─────────────────────────┐
                    │ Format Response         │
                    │ - Add metadata          │
                    │ - Calculate timing      │
                    └────────┬────────────────┘
                             │
                             ▼
                    ┌─────────────────────────┐
                    │ Return SearchResponse   │
                    │ to User                 │
                    └─────────────────────────┘
```

### 3.2 Detailed Step-by-Step Data Journey

#### **Step 1: Query Parsing and Validation**

```python
Input:
  query = "machine learning algorithms"
  filters = {"document_types": ["pdf"], "min_quality": 0.7}
  limit = 10

Validation:
  1. Check query length: 1-500 chars ✓
  2. Validate filters:
     - document_types in allowed types ✓
     - min_quality between 0.0-1.0 ✓
  3. Sanitize query (remove SQL injection attempts)
  4. Normalize whitespace

Output:
  validated_query = "machine learning algorithms"
  validated_filters = SearchFilters(document_types=["pdf"], min_quality=0.7)
```

#### **Step 2: Build PostgreSQL tsquery**

```python
Input:
  query = "machine learning algorithms"

Processing:
  1. Tokenize: ["machine", "learning", "algorithms"]
  2. Remove stopwords: ["machine", "learning", "algorithms"] (none removed)
  3. Build tsquery: "machine & learning & algorithms"
  4. Add phrase proximity: "machine <-> learning & algorithms"

SQL Output:
  tsquery = to_tsquery('english', 'machine <-> learning & algorithms')
```

#### **Step 3: Search Full Documents**

```sql
-- Search in document_texts table
SELECT
    dt.document_id,
    d.document_name,
    ts_rank(to_tsvector('english', dt.full_text), query) as rank,
    ts_headline(
        'english',
        dt.full_text,
        query,
        'MaxWords=50, MinWords=30, MaxFragments=1'
    ) as snippet,
    dt.extraction_quality,
    dt.text_length
FROM document_texts dt
JOIN documents d ON dt.document_id = d.id
WHERE
    to_tsvector('english', dt.full_text) @@ to_tsquery('english', 'machine <-> learning & algorithms')
    AND d.status = 'completed'
    AND d.mime_type = 'application/pdf'  -- from filters
    AND dt.extraction_quality >= 0.7     -- from filters
ORDER BY rank DESC
LIMIT 10;

Result:
  [
    {
      document_id: '550e8400-...',
      document_name: 'ML_Research.pdf',
      rank: 0.92,
      snippet: '...various machine learning algorithms including...',
      extraction_quality: 0.95
    },
    // ... more results
  ]
```

#### **Step 4: Search Chunks**

```sql
-- Search in embeddings table (chunks)
SELECT
    e.document_id,
    d.document_name,
    e.chunk_index,
    e.chunk_text,
    e.start_position,
    e.end_position,
    ts_rank(to_tsvector('english', e.chunk_text), query) as rank,
    ts_headline('english', e.chunk_text, query) as snippet
FROM embeddings e
JOIN documents d ON e.document_id = d.id
JOIN document_texts dt ON e.document_id = dt.document_id
WHERE
    to_tsvector('english', e.chunk_text) @@ to_tsquery('english', 'machine <-> learning & algorithms')
    AND d.status = 'completed'
    AND d.mime_type = 'application/pdf'
    AND dt.extraction_quality >= 0.7
ORDER BY rank DESC
LIMIT 20;  -- Get more chunks since we'll deduplicate

Result:
  [
    {
      document_id: '550e8400-...',
      chunk_index: 5,
      rank: 0.88,
      snippet: '...machine learning algorithms are used for...'
    },
    {
      document_id: '550e8400-...',  -- Same document, different chunk
      chunk_index: 12,
      rank: 0.75,
      snippet: '...comparing various algorithms...'
    },
    // ... more chunks
  ]
```

#### **Step 5: Merge and Deduplicate**

```python
Input:
  doc_matches = [10 full document matches]
  chunk_matches = [20 chunk matches]

Algorithm:
  1. Group chunks by document_id
  2. For each document:
     - If in both doc_matches and chunk_matches:
       - Use higher rank score
       - Prefer chunk snippet if more specific
     - Else use available match
  3. Sort by final rank score
  4. Apply limit (10)

Output:
  merged_results = [
    {
      document_id: '550e8400-...',
      rank: 0.92,  # from doc match
      snippet: '...machine learning algorithms...',  # from chunk match (more specific)
      chunk_index: 5
    },
    {
      document_id: '660e8400-...',
      rank: 0.85,
      snippet: '...',
      chunk_index: None  # From doc-level match only
    },
    // ... 8 more results
  ]
```

#### **Step 6: Snippet Enhancement**

```python
For each result:
  1. If snippet exists: use it
  2. Else: generate snippet from chunk_text or full_text
  3. Highlight query terms: wrap in ** markers
  4. Trim to max 200 characters
  5. Add ellipsis if truncated

Example:
  raw_snippet = "In this paper we discuss various machine learning algorithms including neural networks, decision trees, and support vector machines which are commonly used in classification tasks."

  highlighted = "...various **machine learning algorithms** including neural networks, decision trees, and support vector machines..."

  final_snippet = "...various **machine learning algorithms** including neural networks, decision trees, and support vector machines..." (196 chars)
```

#### **Step 7: Response Formatting**

```python
response = SearchResponse(
    success=True,
    query="machine learning algorithms",
    total_results=47,  # Total matches before limit
    returned_results=10,  # Actual results returned
    results=[...],  # SearchResultItem list
    processing_time_ms=45,
    filters_applied=SearchFilters(...),
    suggestions=["deep learning algorithms", "supervised learning"]
)
```

### 3.3 Database State Changes

**Read-Only Operations** - Search does not modify database state.

Only read operations:
- SELECT from `document_texts`
- SELECT from `embeddings`
- SELECT from `documents`

### 3.4 File System Operations

**None** - Search operates entirely in-database.

No file reads or writes during search.

---

## 4. VALIDATIONS & CONSTRAINTS

### 4.1 Input Validations

#### **Query Validation:**

```python
class SearchQuery(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query string"
    )

    @validator('query')
    def validate_query(cls, v):
        # Remove leading/trailing whitespace
        v = v.strip()

        # Check not empty after stripping
        if not v:
            raise ValueError("Query cannot be empty")

        # Check for SQL injection patterns
        dangerous_patterns = [';--', 'DROP', 'DELETE', 'INSERT', 'UPDATE']
        v_upper = v.upper()
        for pattern in dangerous_patterns:
            if pattern in v_upper:
                raise ValueError(f"Query contains forbidden pattern: {pattern}")

        return v
```

#### **Filter Validation:**

```python
class SearchFilters(BaseModel):
    document_types: Optional[List[str]] = Field(None, max_items=10)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_quality: Optional[float] = Field(None, ge=0.0, le=1.0)
    tags: Optional[List[str]] = Field(None, max_items=20)

    @validator('date_to')
    def validate_date_range(cls, v, values):
        if v and values.get('date_from'):
            if v < values['date_from']:
                raise ValueError("date_to must be after date_from")
        return v

    @validator('document_types')
    def validate_document_types(cls, v):
        allowed_types = ['pdf', 'docx', 'xlsx', 'pptx', 'txt', 'md', 'html']
        if v:
            invalid = [t for t in v if t not in allowed_types]
            if invalid:
                raise ValueError(f"Invalid document types: {invalid}")
        return v
```

### 4.2 Business Rules Enforced

| Rule | Enforcement | Rationale |
|------|------------|-----------|
| **Query length: 1-500 chars** | Pydantic validation | Prevent abuse, reasonable query size |
| **Max results: 100** | API limit | Pagination required for more |
| **Min quality: 0.0-1.0** | Float validation | Valid quality score range |
| **Only completed docs** | SQL WHERE clause | Don't search processing/failed docs |
| **Non-deleted docs** | SQL WHERE clause | `is_deleted = false` |
| **Min extraction quality** | Optional filter | Skip low-quality extractions |
| **Pagination required** | limit + offset | Prevent loading too many results |

### 4.3 Security Checks Implemented

#### **1. SQL Injection Prevention:**

```python
# ALWAYS use parameterized queries
from sqlalchemy import text

# ✅ Safe - parameterized
query = text("""
    SELECT * FROM document_texts
    WHERE to_tsvector('english', full_text) @@ to_tsquery('english', :query)
""")
result = db.execute(query, {"query": sanitized_query})

# ❌ NEVER do this
query = f"SELECT * FROM document_texts WHERE full_text LIKE '%{user_query}%'"  # UNSAFE!
```

#### **2. Input Sanitization:**

```python
def sanitize_query(query: str) -> str:
    """Remove potentially dangerous characters"""
    # Remove null bytes
    query = query.replace('\x00', '')

    # Remove excessive whitespace
    query = ' '.join(query.split())

    # Escape special characters for tsquery
    special_chars = ['&', '|', '!', '(', ')', '<', '>', ':']
    for char in special_chars:
        query = query.replace(char, f'\\{char}')

    return query
```

#### **3. Rate Limiting:**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/search")
@limiter.limit("100/minute")  # 100 searches per minute per IP
async def search_documents(query: SearchQuery):
    # ...
```

### 4.4 Error Conditions Handled

| Error Condition | Detection | Handling |
|----------------|-----------|----------|
| **Empty query** | Pydantic validation | HTTP 400 with error message |
| **Invalid filters** | Pydantic validation | HTTP 400 with field errors |
| **No results found** | Result count = 0 | HTTP 200 with empty results |
| **Database error** | `except SQLAlchemyError` | HTTP 500 with generic message |
| **Timeout** | Query timeout | HTTP 504 with timeout message |
| **Invalid document_id** | UUID validation | HTTP 400 with validation error |
| **Document not found** | Query returns None | HTTP 404 with document not found |
| **Malformed tsquery** | PostgreSQL error | HTTP 400 with query syntax error |

### 4.5 Rate Limits / Quotas

**API Rate Limits:**

```python
# Search endpoint limits
@limiter.limit("100/minute")  # Per IP address
@limiter.limit("1000/hour")   # Per IP address (hourly)

# Quality validation endpoint
@limiter.limit("30/minute")

# Batch validation endpoint
@limiter.limit("10/minute")   # More expensive operation
```

**Query Complexity Limits:**

```python
MAX_QUERY_LENGTH = 500  # characters
MAX_FILTER_DOCUMENT_TYPES = 10
MAX_FILTER_TAGS = 20
MAX_RESULTS_PER_REQUEST = 100
MAX_OFFSET = 10000  # Prevent deep pagination abuse
```

---

## 5. CONFIGURATION

### 5.1 Environment Variables

**Add to `.env` / `.env.local`:**

```bash
# ============================================
# SEARCH SERVICE CONFIGURATION (Step 8.3)
# ============================================

# Search behavior
SEARCH_DEFAULT_LIMIT=10               # Default results per page
SEARCH_MAX_LIMIT=100                  # Maximum results allowed
SEARCH_SNIPPET_LENGTH=200             # Max snippet characters
SEARCH_MIN_QUERY_LENGTH=1             # Minimum query length
SEARCH_MAX_QUERY_LENGTH=500           # Maximum query length

# Quality filters
SEARCH_MIN_EXTRACTION_QUALITY=0.0     # Minimum extraction quality (0.0 = no filter)
SEARCH_MIN_TEXT_LENGTH=100            # Minimum document text length

# Performance
SEARCH_QUERY_TIMEOUT=5000             # Query timeout in milliseconds
SEARCH_ENABLE_CACHING=true            # Cache search results (future)
SEARCH_CACHE_TTL=300                  # Cache TTL in seconds

# Full-text search configuration
SEARCH_LANGUAGE=english               # PostgreSQL text search language
SEARCH_USE_PHRASE_SEARCH=true        # Enable phrase proximity search

# Rate limiting
SEARCH_RATE_LIMIT_PER_MINUTE=100     # Searches per minute per IP
SEARCH_RATE_LIMIT_PER_HOUR=1000      # Searches per hour per IP

# Quality validation
VALIDATION_MIN_CHUNK_SIZE=100         # Minimum chunk size for quality check
VALIDATION_MAX_CHUNK_SIZE=1500        # Maximum chunk size for quality check
VALIDATION_EXPECTED_OVERLAP=200       # Expected overlap between chunks
```

### 5.2 Default Values and Limits

**Search Service Defaults:**

```python
# In keyword_search_service.py
class KeywordSearchService:
    DEFAULT_LIMIT = 10
    MAX_LIMIT = 100
    DEFAULT_SNIPPET_LENGTH = 200
    MIN_QUERY_LENGTH = 1
    MAX_QUERY_LENGTH = 500

    QUERY_TIMEOUT_MS = 5000

    # PostgreSQL text search configuration
    TSVECTOR_LANGUAGE = 'english'

    # Ranking weights
    RANK_WEIGHT_TITLE = 1.0
    RANK_WEIGHT_CONTENT = 0.4
    RANK_WEIGHT_QUALITY = 0.2
```

**Quality Validator Defaults:**

```python
# In quality_validator.py
class QualityValidator:
    MIN_EXTRACTION_QUALITY = 0.5
    MIN_TEXT_LENGTH = 100
    MIN_CHUNK_SIZE = 100
    MAX_CHUNK_SIZE = 1500
    EXPECTED_CHUNK_OVERLAP = 200
    OVERLAP_TOLERANCE = 50  # ±50 chars
```

### 5.3 File Paths and Directory Structure

**Updated Project Structure:**

```
backend/
├── app/
│   ├── services/
│   │   ├── search/                    # ← NEW
│   │   │   ├── __init__.py            # ← NEW
│   │   │   ├── keyword_search_service.py  # ← NEW
│   │   │   └── quality_validator.py   # ← NEW
│   │   ├── chunking/
│   │   └── extraction/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           └── search.py          # ← MODIFIED
│   ├── schemas/
│   │   └── search.py                  # ← NEW/MODIFIED
│   └── tasks/
├── tests/
│   ├── unit/
│   │   └── services/
│   │       └── test_keyword_search.py # ← NEW
│   └── integration/
│       └── test_search_pipeline.py    # ← NEW
├── scripts/
│   └── process_sample_documents.py    # ← NEW
├── db/
│   └── migrations/
│       └── 004_add_search_indexes.sql # ← NEW
└── docs/
    └── technical/
        └── step8.3_simple_keyword_search.md  # ← NEW (this file)
```

### 5.4 Docker Services Required

**No new services** - uses existing infrastructure:

✅ **PostgreSQL** (from Step 1) - full-text search
✅ **Redis** (from Step 1) - optional result caching (future)
✅ **FastAPI** - search endpoint

**PostgreSQL Configuration (for full-text search):**

```yaml
# docker-compose.yml (if modifications needed)
services:
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=querybox
      # Full-text search is built-in, no special config needed
    volumes:
      - ./db/migrations:/docker-entrypoint-initdb.d
```

---

## 6. ERROR HANDLING

### 6.1 Possible Failure Scenarios

| Scenario | Probability | Impact | Detection |
|----------|------------|--------|-----------|
| **Empty search results** | High | Low | Result count = 0 |
| **Database connection lost** | Medium | High | SQLAlchemy exception |
| **Invalid tsquery syntax** | Low | Medium | PostgreSQL error |
| **Query timeout** | Low | Medium | Query exceeds timeout |
| **Rate limit exceeded** | Medium | Low | Too many requests |
| **Malformed query** | Medium | Low | Validation error |
| **No searchable documents** | Low | High | All docs failed processing |

### 6.2 Error Messages and Codes

**Structured Error Codes:**

```python
# In keyword_search_service.py
class SearchError(Exception):
    """Base exception for search errors"""
    pass

class QueryValidationError(SearchError):
    code = "SEARCH_001"
    message = "Invalid search query"

class NoResultsError(SearchError):
    code = "SEARCH_002"
    message = "No results found for query"

class DatabaseError(SearchError):
    code = "SEARCH_003"
    message = "Database error during search"

class TimeoutError(SearchError):
    code = "SEARCH_004"
    message = "Search query timed out"

class RateLimitError(SearchError):
    code = "SEARCH_005"
    message = "Rate limit exceeded"
```

**User-Facing Error Messages:**

```python
ERROR_MESSAGES = {
    "SEARCH_001": "Your search query contains invalid characters or is malformed. Please try a different query.",
    "SEARCH_002": "No documents found matching your search. Try different keywords or remove filters.",
    "SEARCH_003": "An error occurred while searching. Please try again later.",
    "SEARCH_004": "Your search is taking too long. Try a more specific query or add filters.",
    "SEARCH_005": "You've made too many search requests. Please wait a moment and try again."
}
```

### 6.3 Recovery Mechanisms

#### **1. Automatic Retry (for transient errors):**

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def execute_search_query(query: str, filters: SearchFilters):
    """Execute search with automatic retry on transient errors"""
    try:
        # Execute query
        pass
    except OperationalError as e:
        # Retry on connection errors
        raise
    except Exception:
        # Don't retry on other errors
        raise
```

#### **2. Fallback Search:**

```python
async def search_with_fallback(query: str, filters: SearchFilters):
    """Try advanced search, fall back to simple if fails"""
    try:
        # Try phrase proximity search (more accurate)
        return await search_with_proximity(query, filters)
    except QuerySyntaxError:
        # Fall back to simple AND search
        logger.warning("Phrase search failed, falling back to simple search")
        return await search_simple(query, filters)
```

#### **3. Graceful Degradation:**

```python
async def search_documents(query: SearchQuery):
    try:
        results = await search_service.search(query)
        return results
    except DatabaseError:
        # Return cached results if available
        cached = await get_cached_results(query)
        if cached:
            logger.warning("Using cached results due to database error")
            cached['warning'] = "Results may be outdated"
            return cached
        raise
```

### 6.4 Rollback Procedures

**Not Applicable** - Search is read-only, no database modifications.

### 6.5 Logging Points

**Structured Logging:**

```python
import structlog
logger = structlog.get_logger()

# 1. Search request received
logger.info(
    "search_request",
    query=query,
    filters=filters,
    user_ip=request.client.host
)

# 2. Query parsing
logger.debug(
    "query_parsed",
    original_query=query,
    tsquery=tsquery_string,
    filters_applied=filters
)

# 3. Database query execution
logger.debug(
    "search_query_executing",
    query_type="full_text",
    timeout_ms=timeout
)

# 4. Results retrieved
logger.info(
    "search_results",
    query=query,
    total_results=total_count,
    returned_results=len(results),
    processing_time_ms=duration
)

# 5. Errors
logger.error(
    "search_failed",
    query=query,
    error_code="SEARCH_003",
    error_message=str(exc),
    exc_info=True
)

# 6. Performance warnings
if duration > 1000:
    logger.warning(
        "slow_search",
        query=query,
        duration_ms=duration,
        result_count=total_count
    )
```

---

## 7. TESTING CHECKLIST

### 7.1 Manual Testing Steps

#### **Test 1: Basic Search Flow**

```bash
# 1. Upload and process a PDF
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@sample.pdf"

# Get document_id from response
DOCUMENT_ID="550e8400-e29b-41d4-a716-446655440000"

# 2. Wait for processing (check status)
curl http://localhost:8000/api/v1/documents/$DOCUMENT_ID

# 3. Execute search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "limit": 10
  }'

# Expected: Results returned with snippets
```

#### **Test 2: Search with Filters**

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "neural networks",
    "filters": {
      "document_types": ["pdf"],
      "min_quality": 0.7,
      "date_from": "2025-01-01T00:00:00Z"
    },
    "limit": 5
  }'

# Verify:
# - Only PDFs returned
# - All have extraction_quality >= 0.7
# - All created after 2025-01-01
```

#### **Test 3: Quality Validation**

```bash
# Check document search readiness
curl http://localhost:8000/api/v1/documents/$DOCUMENT_ID/search-quality

# Expected response:
# {
#   "is_search_ready": true,
#   "extraction_passed": true,
#   "chunking_passed": true,
#   "overall_quality_score": 0.85,
#   ...
# }
```

#### **Test 4: Batch Processing (10+ Documents)**

```bash
# Run sample document processing script
cd backend
python scripts/process_sample_documents.py

# Expected output:
# ✓ Processed 12 documents
# ✓ 10 passed quality checks
# ✓ 2 failed (low quality)
# ✓ Average quality: 0.87
```

### 7.2 Expected Successful Behavior

**✅ Success Criteria:**

1. **Search Functionality:**
   - Returns results for valid queries
   - Results ranked by relevance
   - Snippets include highlighted keywords
   - Empty results return gracefully (not error)

2. **Result Quality:**
   - Top results contain query terms
   - Snippets provide context
   - Relevance scores decrease down the list
   - No duplicate documents

3. **Performance:**
   - Most queries < 100ms
   - P95 < 500ms
   - No queries timeout

4. **Filtering:**
   - All filters correctly applied
   - Combined filters work (AND logic)
   - Invalid filters rejected with clear errors

5. **Quality Validation:**
   - 10+ sample documents processed successfully
   - Extraction quality > 0.7 for most docs
   - Chunking produces reasonable chunk counts
   - All processed docs are searchable

### 7.3 Edge Cases to Verify

| Edge Case | Test Input | Expected Behavior |
|-----------|-----------|-------------------|
| **Empty query** | `""` | HTTP 400 validation error |
| **Single character query** | `"a"` | Valid, returns results |
| **Very long query** | 501 chars | HTTP 400 validation error |
| **Special characters** | `"@#$%^&*"` | Sanitized, returns results or no results |
| **SQL injection attempt** | `"'; DROP TABLE--"` | Sanitized, treated as literal text |
| **No documents in DB** | Any query | HTTP 200 with `results: []` |
| **All documents failed processing** | Any query | HTTP 200 with `results: []` |
| **Query with stopwords only** | `"the and or"` | Returns results (stopwords handled) |
| **Unicode query** | `"café résumé"` | Correctly searches unicode text |
| **Phrase search** | `"exact phrase match"` | Finds phrase matches prioritized |
| **Wildcard attempts** | `"test*"` | Literal star or converted to prefix search |
| **Empty filters** | `filters: {}` | Same as no filters |
| **Invalid date range** | `date_to < date_from` | HTTP 400 validation error |
| **Limit = 0** | `limit: 0` | HTTP 400 validation error |
| **Offset > total results** | `offset: 10000` | HTTP 200 with `results: []` |

### 7.4 Performance Benchmarks

**Target Metrics:**

| Query Type | Expected Time | Max Time |
|------------|---------------|----------|
| Simple keyword (1-2 terms) | < 50ms | < 200ms |
| Complex query (5+ terms) | < 100ms | < 500ms |
| Filtered search | < 150ms | < 600ms |
| First page (offset=0) | < 50ms | < 200ms |
| Deep pagination (offset=1000) | < 200ms | < 1000ms |

**Benchmark Test Script:**

```python
# backend/scripts/benchmark_search.py
import time
import statistics
from app.services.search import KeywordSearchService

queries = [
    "machine learning",
    "neural networks deep learning",
    "classification algorithms supervised learning methods",
]

def benchmark_search():
    latencies = []

    for query in queries:
        start = time.time()
        results = search_service.search(query, limit=10)
        duration_ms = (time.time() - start) * 1000
        latencies.append(duration_ms)
        print(f"Query: '{query}' - {duration_ms:.2f}ms - {len(results)} results")

    print(f"\nP50: {statistics.median(latencies):.2f}ms")
    print(f"P95: {statistics.quantiles(latencies, n=20)[18]:.2f}ms")
    print(f"Max: {max(latencies):.2f}ms")

if __name__ == "__main__":
    benchmark_search()
```

---

## 8. MONITORING & METRICS

### 8.1 Metrics Collected

**Prometheus Metrics:**

```python
# In app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Search request metrics
search_requests_total = Counter(
    'search_requests_total',
    'Total search requests',
    ['status']  # success, failed, timeout
)

search_duration_seconds = Histogram(
    'search_duration_seconds',
    'Search request duration',
    ['query_complexity'],  # simple, medium, complex
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

search_results_count = Histogram(
    'search_results_count',
    'Number of results returned',
    buckets=[0, 1, 5, 10, 50, 100, 500]
)

# Quality metrics
documents_searchable = Gauge(
    'documents_searchable_total',
    'Number of searchable documents'
)

avg_extraction_quality = Gauge(
    'avg_extraction_quality',
    'Average extraction quality score'
)

# Error metrics
search_errors_total = Counter(
    'search_errors_total',
    'Search errors by type',
    ['error_code']
)
```

**Business Metrics:**

```sql
-- Dashboard query: Daily search stats
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_searches,
    AVG(processing_time_ms) as avg_latency_ms,
    COUNT(*) FILTER (WHERE total_results > 0) as searches_with_results,
    COUNT(*) FILTER (WHERE total_results = 0) as searches_no_results
FROM search_logs  -- If we add search logging table
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### 8.2 Log Entries Generated

**Sample Log Output (JSON structured):**

```json
{
  "timestamp": "2025-10-23T14:30:15.234Z",
  "level": "INFO",
  "event": "search_request",
  "query": "machine learning",
  "filters": {"document_types": ["pdf"]},
  "limit": 10,
  "offset": 0,
  "user_ip": "192.168.1.100"
}

{
  "timestamp": "2025-10-23T14:30:15.280Z",
  "level": "INFO",
  "event": "search_results",
  "query": "machine learning",
  "total_results": 47,
  "returned_results": 10,
  "processing_time_ms": 45,
  "query_complexity": "simple"
}

{
  "timestamp": "2025-10-23T14:30:16.120Z",
  "level": "WARNING",
  "event": "slow_search",
  "query": "complex multi-term query with many filters",
  "duration_ms": 1234,
  "result_count": 100
}
```

### 8.3 Health Check Indicators

**Add to `/health` endpoint:**

```python
# In app/api/v1/endpoints/health.py

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    health = {
        # ... existing checks ...
        "search": {
            "status": "unknown",
            "searchable_documents": 0,
            "avg_search_time_ms": None,
            "last_search": None
        }
    }

    try:
        # Check searchable documents count
        searchable_count = db.query(DocumentText).filter(
            DocumentText.text_length > 0
        ).count()

        health["search"]["searchable_documents"] = searchable_count

        # Test search functionality
        start = time.time()
        test_results = await search_service.search("test", limit=1)
        duration = (time.time() - start) * 1000

        health["search"]["status"] = "healthy"
        health["search"]["avg_search_time_ms"] = duration
        health["search"]["last_search"] = datetime.now().isoformat()

    except Exception as e:
        health["search"]["status"] = "unhealthy"
        health["search"]["error"] = str(e)

    return health
```

### 8.4 Performance Measurements

**Key Performance Indicators (KPIs):**

1. **Search Latency**
   ```sql
   -- P50, P95, P99 search latencies
   -- (If we add search_logs table)
   SELECT
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as p50_ms,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_ms,
       PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as p99_ms
   FROM search_logs
   WHERE created_at >= NOW() - INTERVAL '1 hour';
   ```

2. **Result Relevance**
   ```sql
   -- Average position of clicked results (if we track clicks)
   SELECT AVG(result_position) as avg_clicked_position
   FROM search_click_logs
   WHERE created_at >= NOW() - INTERVAL '24 hours';
   ```

3. **Search Coverage**
   ```sql
   -- Percentage of searches that return results
   SELECT
       COUNT(*) FILTER (WHERE total_results > 0) * 100.0 / COUNT(*) as coverage_pct
   FROM search_logs
   WHERE created_at >= NOW() - INTERVAL '24 hours';
   ```

---

## 9. SECURITY CONSIDERATIONS

### 9.1 Authentication / Authorization Checks

**Current State (MVP):**
- ✅ **No user authentication** in MVP (single-tenant mode)
- ✅ **API key validation** at search endpoint (inherited from base API)
- ⏸️ **Authorization**: Not implemented (all documents accessible)

**Security Model:**

```python
# Search operates on already-uploaded documents
# Security enforced at upload time

# Future (Multi-Tenant):
# Add workspace_id filtering
async def search(query: str, workspace_id: str, user_id: str):
    # Filter documents by workspace
    filters.workspace_id = workspace_id
```

### 9.2 Input Sanitization

**Query Sanitization:**

```python
def sanitize_search_query(query: str) -> str:
    """
    Sanitize user search query

    Security measures:
    1. Remove null bytes
    2. Normalize unicode
    3. Escape special characters for tsquery
    4. Remove SQL injection patterns
    """
    # Remove null bytes
    query = query.replace('\x00', '')

    # Normalize unicode
    import unicodedata
    query = unicodedata.normalize('NFKC', query)

    # Remove control characters
    query = ''.join(
        char for char in query
        if unicodedata.category(char)[0] != 'C' or char in '\n\t\r'
    )

    # Escape for tsquery (PostgreSQL-specific)
    # This prevents tsquery syntax injection
    query = query.replace("'", "''")  # Escape single quotes

    return query
```

**Filter Sanitization:**

```python
# Pydantic automatically validates and sanitizes filters
# Additional checks:

@validator('tags')
def sanitize_tags(cls, v):
    if v:
        # Remove special characters from tags
        sanitized = []
        for tag in v:
            # Only allow alphanumeric and hyphens
            clean_tag = re.sub(r'[^a-zA-Z0-9\-_]', '', tag)
            if clean_tag:
                sanitized.append(clean_tag)
        return sanitized
    return v
```

### 9.3 Path Traversal Prevention

**Not Applicable** - Search operates entirely in database.

No file system access during search operations.

### 9.4 SQL Injection Prevention

**SQLAlchemy ORM + Parameterized Queries:**

```python
# ✅ Safe - using ORM with parameters
results = db.query(DocumentText).filter(
    func.to_tsvector('english', DocumentText.full_text).op('@@')(
        func.to_tsquery('english', tsquery)
    )
).all()

# ✅ Safe - parameterized raw SQL
from sqlalchemy import text
query = text("""
    SELECT * FROM document_texts
    WHERE to_tsvector('english', full_text) @@ to_tsquery('english', :query)
""")
results = db.execute(query, {"query": sanitized_query})

# ❌ NEVER do string concatenation
query = f"SELECT * FROM document_texts WHERE full_text LIKE '%{user_query}%'"  # UNSAFE!
```

### 9.5 File Type Restrictions

**Not Applicable** - Search doesn't access files.

Search operates on extracted text already in database.

File type validation handled in upload step (Step 3).

---

## 10. CODE PATTERNS & CONVENTIONS

### 10.1 Design Patterns Used

#### **1. Service Layer Pattern**

```python
# Service encapsulates business logic
class KeywordSearchService:
    """Single Responsibility: Search logic"""

    async def search(self, query: str, ...) -> SearchResponse:
        # Pure business logic
        pass

# Separation from API layer
@router.post("/search")
async def search_endpoint(query: SearchQuery, service: KeywordSearchService = Depends()):
    # API layer delegates to service
    return await service.search(query.query, query.filters)
```

#### **2. Factory Pattern**

```python
# Service factory
_search_service: Optional[KeywordSearchService] = None

def get_search_service(db: Session = Depends(get_db)) -> KeywordSearchService:
    """Factory function for search service"""
    return KeywordSearchService(db=db)

# Used as dependency injection
@router.post("/search")
async def search(query: SearchQuery, service: KeywordSearchService = Depends(get_search_service)):
    return await service.search(...)
```

#### **3. Repository Pattern (Implicit via ORM)**

```python
# Database access abstracted through ORM
class SearchRepository:
    def __init__(self, db: Session):
        self.db = db

    async def search_documents(self, tsquery: str) -> List[DocumentText]:
        return self.db.query(DocumentText).filter(...).all()

    async def search_chunks(self, tsquery: str) -> List[Embedding]:
        return self.db.query(Embedding).filter(...).all()
```

#### **4. Builder Pattern (Query Construction)**

```python
class TSQueryBuilder:
    """Build PostgreSQL tsquery from user input"""

    def __init__(self, language: str = 'english'):
        self.language = language
        self.terms = []

    def add_term(self, term: str, operator: str = '&'):
        self.terms.append((term, operator))
        return self

    def add_phrase(self, phrase: str):
        words = phrase.split()
        # Build proximity search: word1 <-> word2 <-> word3
        return self

    def build(self) -> str:
        # Construct final tsquery
        return query_string
```

### 10.2 Naming Conventions Followed

**PEP 8 Compliance:**

| Element | Convention | Example |
|---------|-----------|---------|
| **Modules** | lowercase_with_underscores | `keyword_search_service.py` |
| **Classes** | PascalCase | `KeywordSearchService` |
| **Functions** | lowercase_with_underscores | `search_documents()` |
| **Constants** | UPPERCASE_WITH_UNDERSCORES | `DEFAULT_LIMIT` |
| **Private methods** | _leading_underscore | `_build_tsquery()` |
| **Variables** | lowercase_with_underscores | `total_results` |

### 10.3 Async/Await Patterns

**FastAPI Endpoints (Async):**

```python
# Always async for FastAPI endpoints
@router.post("/search")
async def search_documents(query: SearchQuery) -> SearchResponse:
    results = await search_service.search(query.query)
    return results
```

**Service Methods (Sync or Async):**

```python
# Async for I/O-bound operations (database queries)
class KeywordSearchService:
    async def search(self, query: str) -> SearchResponse:
        # Database I/O - async preferred
        doc_results = await self._search_full_documents(query)
        chunk_results = await self._search_chunks(query)

        # CPU-bound processing - sync is fine
        merged = self._merge_results(doc_results, chunk_results)
        return merged

    def _merge_results(self, docs, chunks):
        # Pure CPU work - synchronous
        # No await needed
        pass
```

### 10.4 Transaction Boundaries

**Read-Only Transactions:**

```python
# Search operations are read-only
# Lightweight transaction for consistency

@router.post("/search")
async def search_documents(query: SearchQuery, db: Session = Depends(get_db)):
    # Implicit read transaction
    results = search_service.search(query, db=db)
    # No commit needed - read-only
    return results
```

### 10.5 Error Propagation Strategy

**Layered Error Handling:**

```
┌─────────────────────────────────────────┐
│ API Endpoint (search.py)                │
│ - Catch service exceptions              │
│ - Convert to HTTP responses             │
│ - Log user-facing errors                │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ Service Layer (keyword_search_service.py)│
│ - Raise specific exceptions:            │
│   - QueryValidationError                │
│   - DatabaseError                       │
│ - Include context in exception          │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ Database Layer (SQLAlchemy)             │
│ - Let SQLAlchemy exceptions propagate   │
│ - Catch at service level                │
└─────────────────────────────────────────┘
```

**Example:**

```python
# Service raises specific errors
class KeywordSearchService:
    async def search(self, query: str) -> SearchResponse:
        if not query:
            raise QueryValidationError("Query cannot be empty")

        try:
            results = await self._execute_search(query)
        except OperationalError as exc:
            raise DatabaseError(f"Search failed: {exc}") from exc

        return results

# API converts to HTTP responses
@router.post("/search")
async def search_endpoint(query: SearchQuery):
    try:
        return await search_service.search(query.query)

    except QueryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except DatabaseError as exc:
        logger.error("Database error in search", exc_info=exc)
        raise HTTPException(status_code=500, detail="Search temporarily unavailable")

    except Exception as exc:
        logger.exception("Unexpected error in search")
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## 11. INTEGRATION POINTS

### 11.1 How This Connects to Other Components

**Upstream Dependencies:**

```
Upload (Step 3) → Extraction (Step 8.1) → Chunking (Step 8.2) → Search (Step 8.3)
     ↓                 ↓                      ↓                      ↓
documents        document_texts           embeddings            search_results
```

**Downstream Consumers:**

```
Search (Step 8.3) → Vector Search (Step 9) → Hybrid Retrieval (Step 10)
      ↓                    ↓                        ↓
keyword_results      vector_results         combined_results
```

**Component Interactions:**

| Component | Interaction Type | Data Exchange |
|-----------|-----------------|---------------|
| **Upload API** | Indirect | Documents must be uploaded first |
| **Text Extraction** | Data dependency | Reads `document_texts.full_text` |
| **Chunking** | Data dependency | Reads `embeddings.chunk_text` |
| **Documents** | Direct read | Joins with documents for metadata |
| **Database** | Direct read | Full-text search queries |
| **Quality Validator** | Direct call | Validates search readiness |

### 11.2 Database Queries Executed

**Query 1: Search Full Documents**

```sql
SELECT
    dt.document_id,
    d.document_name,
    d.mime_type,
    d.created_at,
    dt.extraction_quality,
    ts_rank(
        to_tsvector('english', dt.full_text),
        to_tsquery('english', :query)
    ) as rank,
    ts_headline(
        'english',
        dt.full_text,
        to_tsquery('english', :query),
        'MaxWords=50, MinWords=30'
    ) as snippet
FROM document_texts dt
JOIN documents d ON dt.document_id = d.id
WHERE
    to_tsvector('english', dt.full_text) @@ to_tsquery('english', :query)
    AND d.status = 'completed'
    AND d.is_deleted = false
    AND (:document_types IS NULL OR d.mime_type = ANY(:document_types))
    AND (:min_quality IS NULL OR dt.extraction_quality >= :min_quality)
ORDER BY rank DESC
LIMIT :limit OFFSET :offset;

-- Execution plan: Index scan on idx_document_texts_fulltext
-- Performance: 20-100ms for typical query
```

**Query 2: Search Chunks**

```sql
SELECT
    e.document_id,
    d.document_name,
    e.chunk_index,
    e.chunk_text,
    e.start_position,
    e.end_position,
    ts_rank(
        to_tsvector('english', e.chunk_text),
        to_tsquery('english', :query)
    ) as rank,
    ts_headline(
        'english',
        e.chunk_text,
        to_tsquery('english', :query)
    ) as snippet
FROM embeddings e
JOIN documents d ON e.document_id = d.id
JOIN document_texts dt ON e.document_id = dt.document_id
WHERE
    to_tsvector('english', e.chunk_text) @@ to_tsquery('english', :query)
    AND d.status = 'completed'
    AND d.is_deleted = false
    AND (:document_types IS NULL OR d.mime_type = ANY(:document_types))
    AND (:min_quality IS NULL OR dt.extraction_quality >= :min_quality)
ORDER BY rank DESC
LIMIT :limit * 2;  -- Get more chunks for merging

-- Execution plan: Index scan on idx_embeddings_chunk_fulltext
-- Performance: 30-150ms
```

**Query 3: Quality Validation**

```sql
-- Check document search readiness
SELECT
    d.id as document_id,
    d.document_name,
    d.status,
    dt.text_length,
    dt.extraction_quality,
    dt.extraction_method,
    COUNT(e.id) as chunk_count,
    AVG(LENGTH(e.chunk_text))::int as avg_chunk_size
FROM documents d
LEFT JOIN document_texts dt ON d.id = dt.document_id
LEFT JOIN embeddings e ON d.id = e.document_id
WHERE d.id = :document_id
GROUP BY d.id, d.document_name, d.status, dt.text_length, dt.extraction_quality, dt.extraction_method;

-- Performance: <10ms (indexed)
```

### 11.3 External Services Called

**None** - Search is entirely local.

No external API calls:
- ❌ No OpenAI API calls
- ❌ No S3 access
- ❌ No web requests

All processing local with PostgreSQL.

### 11.4 Events Published/Consumed

**Events Consumed:**

None - Search is triggered by API requests, not events.

**Events Published (Optional):**

```python
# Could publish search analytics events (future)
{
    "event_type": "search_executed",
    "query": "machine learning",
    "total_results": 47,
    "returned_results": 10,
    "processing_time_ms": 45,
    "timestamp": "2025-10-23T14:35:00Z"
}

# Consumer: Analytics service (future)
```

---

## 12. TROUBLESHOOTING GUIDE

### 12.1 Common Issues and Solutions

#### **Issue 1: No search results found**

**Symptoms:**
- Query returns 0 results
- Documents are uploaded and processed
- Quality validation passes

**Root Causes:**
1. Query doesn't match document content
2. Documents filtered out by quality/type filters
3. Search index not created

**Debugging:**

```sql
-- 1. Check if documents have extracted text
SELECT
    COUNT(*) as total_docs,
    COUNT(dt.id) as docs_with_text,
    AVG(dt.text_length) as avg_text_length
FROM documents d
LEFT JOIN document_texts dt ON d.id = dt.document_id
WHERE d.status = 'completed';

-- 2. Check if full-text index exists
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'document_texts'
  AND indexname = 'idx_document_texts_fulltext';

-- 3. Test search directly
SELECT
    document_id,
    LEFT(full_text, 100) as text_preview
FROM document_texts
WHERE to_tsvector('english', full_text) @@ to_tsquery('english', 'test');
```

**Solutions:**

```bash
# 1. If no index exists, create it
psql -d querybox_core -c "
CREATE INDEX idx_document_texts_fulltext
ON document_texts USING GIN(to_tsvector('english', full_text));
"

# 2. If text extraction missing, re-process documents
python -c "
from app.tasks.extraction_tasks import extract_document_text
extract_document_text.delay('550e8400-...')
"

# 3. Try simpler query
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 10}'
```

---

#### **Issue 2: Search is very slow (>1 second)**

**Symptoms:**
- Queries take > 1000ms
- Database CPU usage high
- Timeout errors

**Root Causes:**
1. Missing full-text indexes
2. Large result set (no limit)
3. Complex query
4. Database needs vacuuming

**Debugging:**

```sql
-- 1. Check query execution plan
EXPLAIN ANALYZE
SELECT *
FROM document_texts
WHERE to_tsvector('english', full_text) @@ to_tsquery('english', 'query');

-- 2. Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read
FROM pg_stat_user_indexes
WHERE tablename IN ('document_texts', 'embeddings')
ORDER BY idx_scan DESC;

-- 3. Check table bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE tablename IN ('document_texts', 'embeddings');
```

**Solutions:**

```bash
# 1. Create missing indexes (if needed)
psql -f backend/db/migrations/004_add_search_indexes.sql

# 2. Vacuum and analyze tables
psql -d querybox_core -c "
VACUUM ANALYZE document_texts;
VACUUM ANALYZE embeddings;
"

# 3. Add query limits in code
# Ensure all queries have LIMIT clause

# 4. Use connection pooling
# Check DATABASE_URL has pool_size configured
```

---

#### **Issue 3: Snippets don't highlight keywords**

**Symptoms:**
- Search results return
- Snippets displayed but no highlighting
- Keywords not wrapped in ** markers

**Root Cause:**
- ts_headline configuration incorrect
- Snippet post-processing broken

**Debugging:**

```sql
-- Test ts_headline directly
SELECT ts_headline(
    'english',
    'This is a test document about machine learning algorithms.',
    to_tsquery('english', 'machine & learning'),
    'StartSel=**, StopSel=**, MaxWords=20'
);

-- Expected: ...about **machine** **learning** algorithms...
```

**Solutions:**

```python
# Fix snippet generation in keyword_search_service.py
def _generate_snippet(self, text: str, query_terms: List[str], max_length: int = 200):
    # Use ts_headline from database (preferred)
    snippet = ts_headline(text, query_terms)

    # OR manual highlighting (fallback)
    for term in query_terms:
        text = re.sub(
            f'\\b{re.escape(term)}\\b',
            f'**{term}**',
            text,
            flags=re.IGNORECASE
        )
    return text[:max_length]
```

---

#### **Issue 4: Quality validation fails for good documents**

**Symptoms:**
- Document appears correctly processed
- Search works
- But `search-quality` endpoint reports issues

**Root Cause:**
- Validation thresholds too strict
- Edge case in validation logic

**Debugging:**

```bash
# Check document details
curl http://localhost:8000/api/v1/documents/{document_id}/search-quality

# Check raw data
psql -d querybox_core -c "
SELECT
    d.document_name,
    dt.text_length,
    dt.extraction_quality,
    COUNT(e.id) as chunk_count
FROM documents d
JOIN document_texts dt ON d.id = dt.document_id
LEFT JOIN embeddings e ON d.id = e.document_id
WHERE d.id = '550e8400-...'
GROUP BY d.id, d.document_name, dt.text_length, dt.extraction_quality;
"
```

**Solutions:**

```python
# Adjust validation thresholds in quality_validator.py
class QualityValidator:
    MIN_EXTRACTION_QUALITY = 0.5  # Lower from 0.7
    MIN_TEXT_LENGTH = 50          # Lower from 100
    MIN_CHUNK_SIZE = 50            # Lower from 100
```

---

#### **Issue 5: Batch validation script fails**

**Symptoms:**
- `process_sample_documents.py` crashes
- Some documents fail processing
- Unclear which step failed

**Root Cause:**
- Document processing not complete
- Task queue not running
- Invalid document format

**Debugging:**

```bash
# 1. Check Celery workers
celery -A app.celery_app inspect active

# 2. Check processing status
psql -d querybox_core -c "
SELECT
    d.document_name,
    ps.stage,
    ps.status,
    ps.error_message
FROM documents d
JOIN processing_status ps ON d.id = ps.document_id
WHERE ps.status = 'failed'
ORDER BY ps.created_at DESC
LIMIT 10;
"

# 3. Check sample documents directory
ls -la backend/tests/fixtures/sample_documents/
```

**Solutions:**

```bash
# 1. Ensure Celery workers running
celery -A app.celery_app worker --loglevel=info --queues=extraction,chunking

# 2. Re-run failed documents
python backend/scripts/process_sample_documents.py --retry-failed

# 3. Add more sample documents
# Copy PDFs to tests/fixtures/sample_documents/
```

---

### 12.2 Debug Commands

**1. Check Search Index Status**

```bash
psql -d querybox_core -c "
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('document_texts', 'embeddings')
  AND indexname LIKE '%fulltext%';
"
```

**2. Count Searchable Documents**

```bash
psql -d querybox_core -c "
SELECT
    COUNT(*) as total_documents,
    COUNT(dt.id) as documents_with_text,
    COUNT(e.document_id) FILTER (WHERE e.chunk_index = 0) as documents_with_chunks,
    AVG(dt.extraction_quality) as avg_quality
FROM documents d
LEFT JOIN document_texts dt ON d.id = dt.document_id
LEFT JOIN embeddings e ON d.id = e.document_id
WHERE d.status = 'completed'
  AND d.is_deleted = false;
"
```

**3. Test Search Query**

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}' | jq

# Direct SQL
psql -d querybox_core -c "
SELECT
    d.document_name,
    ts_rank(to_tsvector('english', dt.full_text), to_tsquery('english', 'test')) as rank
FROM document_texts dt
JOIN documents d ON dt.document_id = d.id
WHERE to_tsvector('english', dt.full_text) @@ to_tsquery('english', 'test')
ORDER BY rank DESC
LIMIT 5;
"
```

**4. Validate Document Quality**

```bash
# Single document
curl http://localhost:8000/api/v1/documents/{document_id}/search-quality | jq

# Batch
curl -X POST http://localhost:8000/api/v1/search/validate-batch \
  -H "Content-Type: application/json" \
  -d '{
    "document_ids": ["550e8400-...", "660e8400-..."]
  }' | jq
```

**5. Monitor Search Performance**

```bash
# Real-time search logs
tail -f /var/log/querybox/app.log | grep "search_"

# Search latency stats
psql -d querybox_core -c "
-- If we add search_logs table
SELECT
    COUNT(*) as total_searches,
    AVG(processing_time_ms) as avg_ms,
    MAX(processing_time_ms) as max_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY processing_time_ms) as p95_ms
FROM search_logs
WHERE created_at >= NOW() - INTERVAL '1 hour';
"
```

### 12.3 Log Locations

**Application Logs:**

```bash
# FastAPI logs (Docker)
docker logs querybox-backend

# FastAPI logs (local)
tail -f logs/app.log

# Structured logs
cat logs/app.log | jq 'select(.event == "search_request")'
```

**Database Logs:**

```bash
# PostgreSQL slow query log
tail -f /var/log/postgresql/postgresql-15-main.log | grep "duration:"

# Enable slow query logging (if not already):
# In postgresql.conf:
# log_min_duration_statement = 1000  # Log queries > 1s
```

### 12.4 Database Queries for Verification

**Query 1: End-to-End Pipeline Check**

```sql
SELECT
    d.document_name,
    d.status as doc_status,
    dt.text_length,
    dt.extraction_quality,
    COUNT(e.id) as chunk_count,
    MAX(ps_extract.status) as extraction_status,
    MAX(ps_chunk.status) as chunking_status,
    CASE
        WHEN dt.text_length > 0 AND COUNT(e.id) > 0 THEN 'ready'
        ELSE 'not_ready'
    END as search_ready
FROM documents d
LEFT JOIN document_texts dt ON d.id = dt.document_id
LEFT JOIN embeddings e ON d.id = e.document_id
LEFT JOIN processing_status ps_extract
    ON d.id = ps_extract.document_id AND ps_extract.stage = 'extraction'
LEFT JOIN processing_status ps_chunk
    ON d.id = ps_chunk.document_id AND ps_chunk.stage = 'chunking'
WHERE d.is_deleted = false
GROUP BY d.id, d.document_name, d.status, dt.text_length, dt.extraction_quality
ORDER BY d.created_at DESC;
```

**Query 2: Search Coverage Analysis**

```sql
-- How many documents are searchable?
WITH searchable_docs AS (
    SELECT
        d.id,
        CASE
            WHEN dt.text_length > 100 AND dt.extraction_quality >= 0.5 THEN true
            ELSE false
        END as is_searchable
    FROM documents d
    LEFT JOIN document_texts dt ON d.id = dt.document_id
    WHERE d.status = 'completed' AND d.is_deleted = false
)
SELECT
    COUNT(*) as total_documents,
    COUNT(*) FILTER (WHERE is_searchable) as searchable_documents,
    ROUND(100.0 * COUNT(*) FILTER (WHERE is_searchable) / COUNT(*), 2) as coverage_pct
FROM searchable_docs;
```

**Query 3: Quality Distribution**

```sql
-- Distribution of extraction quality scores
SELECT
    CASE
        WHEN extraction_quality >= 0.9 THEN '0.9-1.0 (excellent)'
        WHEN extraction_quality >= 0.7 THEN '0.7-0.9 (good)'
        WHEN extraction_quality >= 0.5 THEN '0.5-0.7 (fair)'
        ELSE '0.0-0.5 (poor)'
    END as quality_range,
    COUNT(*) as document_count,
    AVG(text_length)::int as avg_text_length
FROM document_texts
GROUP BY quality_range
ORDER BY quality_range DESC;
```

---

## 13. APPENDIX

### 13.1 Complete File Listing

**Files to Create:**

1. `backend/app/services/search/keyword_search_service.py` (400 lines)
2. `backend/app/services/search/__init__.py` (30 lines)
3. `backend/app/services/search/quality_validator.py` (200 lines)
4. `backend/app/schemas/search.py` (150 lines)
5. `backend/tests/unit/services/test_keyword_search.py` (250 lines)
6. `backend/tests/integration/test_search_pipeline.py` (300 lines)
7. `backend/scripts/process_sample_documents.py` (200 lines)
8. `backend/db/migrations/004_add_search_indexes.sql` (100 lines)
9. `backend/docs/technical/step8.3_simple_keyword_search.md` (this file)

**Files to Modify:**

1. `backend/app/api/v1/endpoints/search.py` (~200 lines - complete rewrite)
2. `backend/app/api/v1/endpoints/documents.py` (+50 lines)
3. `backend/app/schemas/__init__.py` (+5 lines)
4. `backend/app/db/database.py` (+10 lines - optional)

**Total:** 9 new files, 4 modified files

### 13.2 Environment Variables Summary

```bash
# Required
SEARCH_DEFAULT_LIMIT=10
SEARCH_MAX_LIMIT=100
SEARCH_SNIPPET_LENGTH=200

# Optional (with defaults)
SEARCH_QUERY_TIMEOUT=5000
SEARCH_MIN_EXTRACTION_QUALITY=0.0
SEARCH_LANGUAGE=english
SEARCH_RATE_LIMIT_PER_MINUTE=100
```

### 13.3 Database Schema Changes

**New Tables:** None

**New Indexes:**

```sql
-- In 004_add_search_indexes.sql
CREATE INDEX idx_document_texts_fulltext
ON document_texts USING GIN(to_tsvector('english', full_text));

CREATE INDEX idx_embeddings_chunk_fulltext
ON embeddings USING GIN(to_tsvector('english', chunk_text));

CREATE INDEX idx_document_texts_quality
ON document_texts(extraction_quality)
WHERE extraction_quality IS NOT NULL;
```

### 13.4 Success Metrics

**Step 8.3 Complete When:**

✅ Search endpoint implemented and tested
✅ Full-text search working with PostgreSQL
✅ Results ranked by relevance
✅ Snippets generated with highlighting
✅ Filters (type, quality, date) working
✅ Quality validation endpoints functional
✅ 10+ sample documents processed successfully
✅ Documentation complete

**Performance Targets:**

- ⏱️ **Search latency**: <100ms P95
- 📊 **Result quality**: Top 3 results relevant for most queries
- 📏 **Coverage**: >90% of processed documents searchable
- ✅ **Success rate**: >95% of searches return results
- 🔄 **Quality**: >80% of sample documents pass validation

---

## 14. NEXT STEPS (Step 9.1: Embeddings)

After completing Step 8.3, proceed to:

**Step 9.1: Embedding Generation**
- Install embedding model (OpenAI or BGE-M3)
- Create `EmbeddingService` to generate vectors
- Celery task: `generate_embeddings(document_id)`
- Populate `embeddings.embedding` column
- Enable vector similarity search
- Compare semantic vs keyword search quality

**Dependencies:**
- Step 8.3 chunks must be searchable
- OpenAI API key or local embedding model installed
- pgvector extension enabled and tested

---

**END OF DOCUMENTATION**

*For questions or issues, refer to Troubleshooting Guide (Section 12) or contact the development team.*
