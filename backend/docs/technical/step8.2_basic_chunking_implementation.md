# Step 8.2: Basic Chunking Implementation - Technical Documentation

**Version:** 1.0
**Last Updated:** 2025-10-23
**Status:** Design & Planning
**Author:** QueryBox Core Team
**Related Steps:** Step 8.1 (Text Extraction), Step 9.1 (Embeddings)

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

Step 8.2 implements **semantic text chunking** that splits extracted document text into overlapping chunks suitable for embedding generation and retrieval. This is a critical component of the RAG (Retrieval-Augmented Generation) pipeline.

**Key Capabilities:**
- **Fixed-size chunking**: 1000 characters per chunk with 200-character overlap
- **Sentence boundary preservation**: Chunks break at sentence boundaries to maintain context
- **Position tracking**: Each chunk records its position in the original document
- **Database persistence**: Chunks stored in the `embeddings` table (without vectors initially)
- **Async processing**: Chunking happens in background Celery workers
- **Metadata enrichment**: Tracks chunk count, token estimates, and processing metrics

**Business Value:**
- Enables semantic search over large documents
- Maintains context through overlapping windows
- Prepares content for embedding generation (Step 9)
- Optimizes retrieval accuracy by preserving sentence coherence

### 1.2 Why This Step Is Necessary

**RAG Pipeline Requirements:**
1. **Embedding Models Have Token Limits**: OpenAI ada-002 supports ~8191 tokens, but optimal chunk size is 512-1024 tokens
2. **Retrieval Accuracy**: Smaller, focused chunks improve retrieval precision
3. **Context Preservation**: Overlap ensures critical information isn't lost at chunk boundaries
4. **Search Performance**: Chunked content enables faster vector similarity search

**Alternative Approaches (Not Used):**
- ❌ **No chunking**: Poor retrieval accuracy on large documents
- ❌ **Page-based chunking**: Arbitrary boundaries break semantic units
- ❌ **Paragraph-only chunking**: Too variable in size (10-5000 chars)

**Chosen Approach:**
✅ **Character-based with sentence boundary awareness**: Balances consistency and coherence

### 1.3 Dependencies on Previous Steps

| Step | Dependency | Why Required |
|------|-----------|--------------|
| **Step 1** | Database setup | Requires PostgreSQL with `embeddings` table |
| **Step 2** | FastAPI structure | API endpoints for status checking |
| **Step 3** | Upload handler | Documents must be uploaded before chunking |
| **Step 6** | Metadata management | Uses `processing_status` table for tracking |
| **Step 7** | Document query endpoints | Retrieves document details for processing |
| **Step 8.1** | Text extraction | **CRITICAL**: Requires extracted text in `document_texts` table |

**Blocking Requirement:**
- Step 8.1 MUST be complete - chunking operates on extracted text from `document_texts.full_text`

### 1.4 What Future Steps Depend on This

| Future Step | How It Uses Chunking |
|------------|---------------------|
| **Step 9.1** | Embedding generation reads chunks from `embeddings` table |
| **Step 9.2** | BGE-M3 batch processing iterates over chunks |
| **Step 10.1** | Hybrid retrieval searches chunk-level content |
| **Step 10.3** | Citation extraction maps chunks back to source positions |
| **Step 11.2** | Chain-of-verification validates claims at chunk level |

**Critical for:**
- All semantic search functionality
- Citation accuracy (chunk position → page/paragraph mapping)
- Answer generation context windows

---

## 2. TECHNICAL IMPLEMENTATION

### 2.1 Files to Create/Modify

#### **New Files (6 files):**

1. **`backend/app/services/chunking/chunking_service.py`**
   - Core chunking logic
   - Sentence boundary detection
   - Overlap calculation
   - ~300 lines

2. **`backend/app/services/chunking/__init__.py`**
   - Package initialization
   - Export `ChunkingService` and `get_chunking_service()`
   - ~20 lines

3. **`backend/app/tasks/chunking_tasks.py`**
   - Celery task: `chunk_document_text(document_id)`
   - Status tracking integration
   - Error handling
   - ~150 lines

4. **`backend/tests/unit/services/test_chunking_service.py`**
   - Unit tests for chunking logic
   - Sentence boundary edge cases
   - Overlap validation
   - ~200 lines

5. **`backend/db/migrations/003_add_chunk_metadata.sql`** *(Optional)*
   - Add indexes for chunk retrieval performance
   - Only if not already in base schema
   - ~50 lines

6. **`backend/docs/technical/step8.2_basic_chunking_implementation.md`**
   - This documentation file
   - Implementation guide

#### **Modified Files (4 files):**

1. **`backend/app/models/__init__.py`**
   - Ensure `Embedding` model is exported (likely already done)
   - ~5 lines added

2. **`backend/app/celery_app.py`**
   - Add `chunking` queue routing
   - Import chunking tasks
   - ~10 lines added

3. **`backend/app/tasks/extraction_tasks.py`**
   - Chain chunking task after extraction completes
   - Add: `chunk_document_text.delay(document_id)` at end
   - ~5 lines added

4. **`backend/app/api/v1/endpoints/documents.py`** *(Enhancement)*
   - Add GET `/documents/{id}/chunks` endpoint (optional for testing)
   - Returns chunk count and sample
   - ~30 lines added

### 2.2 Key Classes, Functions, and Methods

#### **Class: `ChunkingService` (chunking_service.py)**

```python
class ChunkingService:
    """
    Document text chunking service with sentence boundary preservation

    Features:
    - Fixed 1000-char chunks with 200-char overlap
    - Sentence boundary detection (periods, question marks, exclamation)
    - Position tracking (start/end character positions)
    - Token estimation for downstream embedding
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        """Initialize chunking service with configuration"""

    async def chunk_text(
        self,
        text: str,
        document_id: UUID,
        db: Session
    ) -> ChunkingResult:
        """
        Split text into overlapping chunks with sentence boundaries

        Args:
            text: Full document text to chunk
            document_id: Document UUID for database linking
            db: Database session for persistence

        Returns:
            ChunkingResult with chunk count and metadata
        """

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex patterns"""

    def _create_chunks(self, sentences: List[str]) -> List[ChunkData]:
        """Group sentences into chunks respecting size and overlap"""

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough: chars / 4)"""

    async def save_chunks(
        self,
        chunks: List[ChunkData],
        document_id: UUID,
        db: Session
    ) -> int:
        """Save chunks to embeddings table, returns chunk count"""
```

#### **Data Classes:**

```python
@dataclass
class ChunkData:
    """Single chunk with metadata"""
    text: str
    chunk_index: int
    start_position: int
    end_position: int
    token_estimate: int

@dataclass
class ChunkingResult:
    """Result of chunking operation"""
    success: bool
    chunk_count: int
    total_chars: int
    avg_chunk_size: int
    processing_time_ms: int
    error_message: Optional[str] = None
```

#### **Celery Task: `chunk_document_text` (chunking_tasks.py)**

```python
@celery_app.task(
    bind=True,
    name="app.tasks.chunking_tasks.chunk_document_text",
    max_retries=3,
    default_retry_delay=60
)
def chunk_document_text(self, document_id: str) -> dict:
    """
    Background task: Chunk extracted text for a document

    Flow:
    1. Update processing_status: chunking=IN_PROGRESS
    2. Fetch extracted text from document_texts table
    3. Call ChunkingService.chunk_text()
    4. Save chunks to embeddings table
    5. Update processing_status: chunking=COMPLETED
    6. Update document.last_indexed_at (placeholder for now)

    Args:
        document_id: Document UUID (string)

    Returns:
        dict with chunk_count and processing stats
    """
```

### 2.3 Database Tables and Columns Used

#### **Primary Table: `embeddings`**

Chunks are stored in the existing `embeddings` table (from schema.sql):

| Column | Type | Purpose | Step 8.2 Usage |
|--------|------|---------|----------------|
| `id` | UUID | Primary key | Auto-generated |
| `document_id` | UUID | Foreign key to documents | Links chunk to source doc |
| `chunk_index` | INTEGER | Chunk sequence number | 0, 1, 2, ... n |
| `chunk_text` | TEXT | The chunk content | Extracted sentence groups |
| `chunk_tokens` | INTEGER | Token count estimate | chars / 4 (rough estimate) |
| `start_position` | INTEGER | Char position in original | Start index in full_text |
| `end_position` | INTEGER | Char position in original | End index in full_text |
| `page_number` | INTEGER | Page reference | NULL for now (future: parse Docling metadata) |
| `embedding` | VECTOR(1536) | Embedding vector | NULL (added in Step 9) |
| `embedding_model` | VARCHAR(100) | Model name | 'pending' or NULL |
| `created_at` | TIMESTAMP | Creation time | NOW() |

**Unique Constraint:** `(document_id, chunk_index)` - prevents duplicate chunks

#### **Secondary Table: `processing_status`**

Tracks chunking progress:

| Column | Value for Chunking |
|--------|-------------------|
| `document_id` | Document being chunked |
| `stage` | `'chunking'` (from `processing_stage_enum`) |
| `status` | `'not_started'` → `'in_progress'` → `'completed'` |
| `result_data` | `{"chunk_count": 47, "avg_size": 982}` |
| `duration_ms` | Time taken to chunk |
| `error_message` | Error details if failed |

#### **Input Table: `document_texts`**

Source of text to chunk:

| Column | Usage |
|--------|-------|
| `document_id` | Lookup document to chunk |
| `full_text` | Input text for chunking |
| `text_length` | Validate sufficient content |

### 2.4 API Endpoints

#### **New Endpoint (Optional for Testing):**

**GET `/api/v1/documents/{document_id}/chunks`**

```python
# Response Schema
{
    "success": true,
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "chunk_count": 47,
    "chunks": [
        {
            "chunk_index": 0,
            "chunk_text": "This is the first chunk...",
            "token_estimate": 245,
            "start_position": 0,
            "end_position": 982
        },
        # ... more chunks
    ],
    "processing_status": {
        "stage": "chunking",
        "status": "completed",
        "completed_at": "2025-10-23T14:30:25Z"
    }
}
```

**Purpose:** Debugging and verification during development

#### **Modified Endpoint: Upload Pipeline**

No new API endpoint, but `POST /api/v1/upload` now triggers:
1. Text extraction (Step 8.1) →
2. **Chunking (Step 8.2)** ← *NEW*

### 2.5 Background Tasks / Workers

#### **Celery Task Configuration:**

```python
# In app/celery_app.py
task_routes = {
    'app.tasks.extraction_tasks.extract_document_text': {'queue': 'extraction'},
    'app.tasks.chunking_tasks.chunk_document_text': {'queue': 'chunking'},  # NEW
}
```

#### **Worker Command:**

```bash
# Start dedicated chunking worker
celery -A app.celery_app worker \
    --loglevel=info \
    --queues=chunking \
    --concurrency=4 \
    --hostname=chunking@%h
```

**Why Separate Queue:**
- Isolation from slower extraction tasks
- Higher concurrency (chunking is CPU-bound, not I/O)
- Independent scaling

#### **Task Chaining:**

```python
# In extraction_tasks.py (modified)
# After extraction completes successfully:
from app.tasks.chunking_tasks import chunk_document_text

# Chain chunking task
chunk_document_text.delay(str(document_id))
logger.info(f"Queued chunking task for document {document_id}")
```

---

## 3. DATA FLOW

### 3.1 High-Level Flow Diagram

```
┌─────────────────┐
│ Upload Complete │
│   (Step 8.1)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Text Extraction Task    │
│ (extract_document_text) │
└────────┬────────────────┘
         │ Saves to document_texts
         ▼
┌─────────────────────────┐
│ Queue Chunking Task     │
│ (chunk_document_text)   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Update Status:          │
│ chunking=IN_PROGRESS    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Fetch Extracted Text    │
│ FROM document_texts     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ ChunkingService:        │
│ 1. Split sentences      │
│ 2. Group into chunks    │
│ 3. Add overlap          │
│ 4. Track positions      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Save to embeddings:     │
│ - chunk_text            │
│ - chunk_index           │
│ - start/end_position    │
│ - token_estimate        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Update Status:          │
│ chunking=COMPLETED      │
│ + metadata              │
└─────────────────────────┘
```

### 3.2 Detailed Step-by-Step Data Journey

#### **Step 1: Task Initialization (chunking_tasks.py)**

```python
Input:
  - document_id: "550e8400-e29b-41d4-a716-446655440000"

Actions:
  1. Validate document exists
  2. Check if already chunked (embeddings table)
  3. Create processing_status record:
     - stage='chunking'
     - status='in_progress'
     - started_at=NOW()

Database Transaction:
  INSERT INTO processing_status (document_id, stage, status, started_at)
  VALUES ($1, 'chunking', 'in_progress', NOW())
```

#### **Step 2: Fetch Source Text**

```python
Query:
  SELECT full_text, text_length
  FROM document_texts
  WHERE document_id = $1

Validation:
  - text_length >= 100 (minimum viable content)
  - full_text is not NULL or empty

Output:
  full_text = "Chapter 1: Introduction\n\nThis document describes..."
  text_length = 45230
```

#### **Step 3: Sentence Splitting (chunking_service.py)**

```python
Input:
  full_text = "This is sentence one. This is sentence two! Is this three?"

Regex Pattern:
  r'(?<=[.!?])\s+(?=[A-Z])'
  # Split on: period/exclamation/question + whitespace + capital letter

Output (sentences list):
  [
    "This is sentence one.",
    "This is sentence two!",
    "Is this three?"
  ]
```

#### **Step 4: Chunk Creation with Overlap**

```python
Configuration:
  chunk_size = 1000 chars
  overlap = 200 chars

Algorithm:
  current_chunk = ""
  chunks = []

  for sentence in sentences:
      if len(current_chunk) + len(sentence) <= chunk_size:
          current_chunk += sentence
      else:
          # Save current chunk
          chunks.append(current_chunk)

          # Start new chunk with overlap
          overlap_text = current_chunk[-overlap:]
          current_chunk = overlap_text + sentence

Example Output (chunks):
  [
    {
      chunk_index: 0,
      text: "This is sentence one. This is sentence two!...",  # 982 chars
      start_position: 0,
      end_position: 982
    },
    {
      chunk_index: 1,
      text: "...sentence two! Is this three? Next sentence...",  # 995 chars
      start_position: 782,  # 982 - 200 overlap
      end_position: 1777
    },
    # ... more chunks
  ]
```

#### **Step 5: Database Persistence**

```python
For each chunk:
  INSERT INTO embeddings (
    id,
    document_id,
    chunk_index,
    chunk_text,
    chunk_tokens,
    start_position,
    end_position,
    embedding_model,
    created_at
  ) VALUES (
    uuid_generate_v4(),
    '550e8400-e29b-41d4-a716-446655440000',
    0,  # increments: 0, 1, 2, ...
    'This is sentence one. This is...',
    245,  # estimated: len(text) / 4
    0,
    982,
    'pending',  # No embedding yet
    NOW()
  )

Transaction:
  BEGIN;
  DELETE FROM embeddings WHERE document_id = $1;  # Clean old chunks
  INSERT INTO embeddings ... (bulk insert all chunks)
  COMMIT;
```

#### **Step 6: Status Update**

```python
Update processing_status:
  UPDATE processing_status
  SET
    status = 'completed',
    completed_at = NOW(),
    duration_ms = <calculated>,
    result_data = '{"chunk_count": 47, "avg_size": 982}'
  WHERE document_id = $1 AND stage = 'chunking'

Update document:
  UPDATE documents
  SET last_indexed_at = NOW()  -- Indicates chunking completed
  WHERE id = $1
```

### 3.3 Database State Changes

#### **Before Chunking:**

**document_texts:**
| document_id | full_text | text_length |
|-------------|-----------|-------------|
| 550e8400... | "Chapter 1: Introduction..." | 45230 |

**embeddings:**
| document_id | chunk_index | chunk_text |
|-------------|-------------|------------|
| *(empty)* | | |

**processing_status:**
| document_id | stage | status |
|-------------|-------|--------|
| 550e8400... | extraction | completed |
| 550e8400... | chunking | not_started |

#### **After Chunking:**

**embeddings:**
| id | document_id | chunk_index | chunk_text | start_pos | end_pos | tokens |
|----|-------------|-------------|------------|-----------|---------|--------|
| uuid1 | 550e8400... | 0 | "Chapter 1:..." | 0 | 982 | 245 |
| uuid2 | 550e8400... | 1 | "...Introduction..." | 782 | 1777 | 248 |
| ... | ... | ... | ... | ... | ... | ... |
| uuid47 | 550e8400... | 46 | "...conclusion." | 44200 | 45230 | 257 |

**processing_status:**
| document_id | stage | status | result_data |
|-------------|-------|--------|-------------|
| 550e8400... | extraction | completed | {...} |
| 550e8400... | chunking | **completed** | `{"chunk_count": 47}` |

**documents:**
| id | last_indexed_at |
|----|-----------------|
| 550e8400... | **2025-10-23 14:35:00** |

### 3.4 File System Operations

**None** - Chunking operates purely in-memory and database.

No files are read/written during chunking (text already extracted to DB in Step 8.1).

---

## 4. VALIDATIONS & CONSTRAINTS

### 4.1 Input Validations

#### **Document Validation:**

```python
# In chunking_tasks.py

# 1. Document exists
document = db.query(Document).filter(Document.id == document_id).first()
if not document:
    raise ValueError(f"Document {document_id} not found")

# 2. Document has extracted text
document_text = db.query(DocumentText).filter(
    DocumentText.document_id == document_id
).first()
if not document_text:
    raise ValueError(f"No extracted text found for document {document_id}")

# 3. Text is not empty
if not document_text.full_text or document_text.text_length < 100:
    raise ValueError(f"Document text too short ({document_text.text_length} chars)")
```

#### **Text Content Validation:**

```python
# In chunking_service.py

def chunk_text(self, text: str, ...) -> ChunkingResult:
    # 1. Type validation
    if not isinstance(text, str):
        raise TypeError("Text must be string")

    # 2. Length validation
    if len(text) < self.min_chunk_size:
        raise ValueError(f"Text too short: {len(text)} < {self.min_chunk_size}")

    # 3. Character encoding check
    try:
        text.encode('utf-8')
    except UnicodeEncodeError:
        raise ValueError("Text contains invalid unicode characters")
```

### 4.2 Business Rules Enforced

| Rule | Enforcement | Rationale |
|------|------------|-----------|
| **Chunk size: 800-1200 chars** | Soft limit (target 1000) | Balance between context and precision |
| **Overlap: 200 chars** | Hard limit | Ensures context continuity |
| **Min chunk: 100 chars** | Hard limit | Too small = poor retrieval quality |
| **Sentence boundary** | Best effort | Preserve semantic coherence |
| **No duplicate chunks** | Database constraint | `UNIQUE(document_id, chunk_index)` |
| **Chunk index sequential** | Application logic | 0, 1, 2, ... n (no gaps) |
| **Position non-negative** | Database check | `start_position >= 0` |
| **End > Start** | Application logic | `end_position > start_position` |

### 4.3 Security Checks Implemented

#### **1. SQL Injection Prevention:**

```python
# Use parameterized queries ALWAYS
db.query(DocumentText).filter(DocumentText.document_id == document_id)  # ✅ Safe
# NOT: f"SELECT * FROM document_texts WHERE document_id = '{document_id}'"  # ❌ Unsafe
```

#### **2. Resource Exhaustion Protection:**

```python
# Max document size check
MAX_DOCUMENT_SIZE = 10_000_000  # 10MB text

if document_text.text_length > MAX_DOCUMENT_SIZE:
    raise ValueError(f"Document too large: {document_text.text_length} chars")

# Max chunk count limit
MAX_CHUNKS = 10_000

estimated_chunks = document_text.text_length / (chunk_size - overlap)
if estimated_chunks > MAX_CHUNKS:
    raise ValueError(f"Too many chunks: {estimated_chunks}")
```

#### **3. Memory Safety:**

```python
# Process in batches for very large documents
BATCH_SIZE = 1000  # chunks

for i in range(0, len(all_chunks), BATCH_SIZE):
    batch = all_chunks[i:i+BATCH_SIZE]
    db.bulk_insert_mappings(Embedding, batch)
    db.flush()  # Free memory
```

### 4.4 Error Conditions Handled

| Error Condition | Detection | Handling |
|----------------|-----------|----------|
| **Document not found** | Database query returns None | Raise `ValueError`, fail task |
| **No extracted text** | `document_texts` entry missing | Raise `ValueError`, mark chunking=failed |
| **Empty text** | `text_length == 0` | Raise `ValueError`, skip chunking |
| **Text too short** | `len(text) < 100` | Log warning, create single chunk |
| **Database error** | `except SQLAlchemyError` | Rollback transaction, retry task |
| **Memory error** | `except MemoryError` | Log error, fail task (no retry) |
| **Unicode error** | Text encoding fails | Log error, attempt UTF-8 fix |
| **Timeout** | Celery task timeout (10 min) | Fail task, log for investigation |

### 4.5 Rate Limits / Quotas

**Celery Task Limits:**

```python
@celery_app.task(
    time_limit=600,  # 10 minutes hard limit
    soft_time_limit=540,  # 9 minutes soft warning
    max_retries=3,
    default_retry_delay=60  # 1 minute between retries
)
```

**Concurrent Processing:**

```bash
# Worker concurrency
--concurrency=4  # Process 4 documents simultaneously

# Queue max length (Redis)
maxlen=10000  # Queue up to 10k documents
```

**No user-facing rate limits** - internal processing queue manages throughput.

---

## 5. CONFIGURATION

### 5.1 Environment Variables

**Add to `.env` / `.env.local`:**

```bash
# ============================================
# CHUNKING SERVICE CONFIGURATION (Step 8.2)
# ============================================

# Chunk size configuration
CHUNK_SIZE=1000                    # Target characters per chunk
CHUNK_OVERLAP=200                  # Overlap between chunks
MIN_CHUNK_SIZE=100                 # Minimum viable chunk size

# Processing limits
MAX_DOCUMENT_SIZE=10000000         # 10MB text limit
MAX_CHUNKS_PER_DOCUMENT=10000      # Max chunks allowed

# Sentence detection
SENTENCE_ENDINGS=.!?               # Characters that end sentences

# Task timeout
CHUNKING_TIMEOUT=600               # 10 minutes max per document

# Retry configuration
CHUNKING_MAX_RETRIES=3
CHUNKING_RETRY_DELAY=60            # Seconds between retries

# Batch processing
CHUNK_BATCH_SIZE=1000              # Chunks per database batch insert
```

### 5.2 Default Values and Limits

**Chunking Service Defaults:**

```python
# In chunking_service.py
class ChunkingService:
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_OVERLAP = 200
    DEFAULT_MIN_CHUNK = 100

    MAX_DOCUMENT_LENGTH = 10_000_000  # 10MB
    MAX_CHUNK_COUNT = 10_000

    SENTENCE_PATTERN = r'(?<=[.!?])\s+(?=[A-Z])'
    TOKEN_CHAR_RATIO = 4  # Rough estimate: 1 token ≈ 4 chars
```

**Celery Task Defaults:**

```python
# In chunking_tasks.py
TASK_TIME_LIMIT = 600  # 10 minutes
TASK_SOFT_LIMIT = 540  # 9 minutes (warning threshold)
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds
```

### 5.3 File Paths and Directory Structure

**No new directories required** - uses existing database structure.

**Updated Project Structure:**

```
backend/
├── app/
│   ├── services/
│   │   ├── chunking/              # ← NEW
│   │   │   ├── __init__.py        # ← NEW
│   │   │   └── chunking_service.py  # ← NEW
│   │   └── extraction/
│   │       └── text_extraction_service.py
│   ├── tasks/
│   │   ├── extraction_tasks.py    # ← MODIFIED
│   │   └── chunking_tasks.py      # ← NEW
│   ├── models/
│   │   └── embedding.py           # ← USED (existing)
│   └── celery_app.py              # ← MODIFIED
├── tests/
│   └── unit/
│       └── services/
│           └── test_chunking_service.py  # ← NEW
└── db/
    └── migrations/
        └── 003_add_chunk_metadata.sql  # ← NEW (optional)
```

### 5.4 Docker Services Required

**No new services** - uses existing infrastructure:

✅ **PostgreSQL** (from Step 1) - stores chunks in `embeddings` table
✅ **Redis** (from Step 1) - Celery broker for task queue
✅ **Celery Worker** - needs `chunking` queue added

**Updated docker-compose.yml** (if needed):

```yaml
services:
  celery-chunking:  # Optional: dedicated chunking worker
    build: ./backend
    command: celery -A app.celery_app worker --loglevel=info --queues=chunking --concurrency=4
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - CHUNK_SIZE=1000
      - CHUNK_OVERLAP=200
    depends_on:
      - postgres
      - redis
```

**Or run manually:**

```bash
# Single worker for all queues
celery -A app.celery_app worker \
    --loglevel=info \
    --queues=extraction,chunking \
    --concurrency=6

# Or dedicated workers
celery -A app.celery_app worker --loglevel=info --queues=chunking --concurrency=4 --hostname=chunking@%h
```

---

## 6. ERROR HANDLING

### 6.1 Possible Failure Scenarios

| Scenario | Probability | Impact | Detection |
|----------|------------|--------|-----------|
| **No extracted text** | Low | High | Query returns None |
| **Database connection lost** | Medium | High | SQLAlchemy exception |
| **Out of memory** | Low | Critical | MemoryError |
| **Malformed text (bad unicode)** | Low | Medium | UnicodeDecodeError |
| **Task timeout** | Low | Medium | Celery SoftTimeLimitExceeded |
| **Duplicate chunks** | Low | Low | Unique constraint violation |
| **Sentence regex failure** | Very Low | Medium | No sentences detected |

### 6.2 Error Messages and Codes

**Structured Error Codes:**

```python
# In chunking_service.py
class ChunkingError(Exception):
    """Base exception for chunking errors"""
    pass

class TextNotFoundError(ChunkingError):
    code = "CHUNK_001"
    message = "No extracted text found for document"

class TextTooShortError(ChunkingError):
    code = "CHUNK_002"
    message = "Document text too short to chunk"

class DatabaseError(ChunkingError):
    code = "CHUNK_003"
    message = "Failed to save chunks to database"

class MemoryLimitError(ChunkingError):
    code = "CHUNK_004"
    message = "Document too large to process in available memory"
```

**User-Facing Error Messages:**

```python
# Saved to processing_status.error_message
{
    "CHUNK_001": "Document text extraction not complete. Please wait for extraction to finish.",
    "CHUNK_002": "Document contains insufficient text for chunking (minimum 100 characters).",
    "CHUNK_003": "Failed to store document chunks. Please try again.",
    "CHUNK_004": "Document is too large to process. Maximum size is 10MB of text."
}
```

### 6.3 Recovery Mechanisms

#### **1. Automatic Retry (Celery):**

```python
@celery_app.task(bind=True, max_retries=3)
def chunk_document_text(self, document_id: str):
    try:
        # Chunking logic
        pass
    except (DatabaseError, OperationalError) as exc:
        # Retry on transient errors
        raise self.retry(exc=exc, countdown=60)  # Wait 1 min
    except (TextNotFoundError, TextTooShortError):
        # Don't retry validation errors
        raise
```

#### **2. Transaction Rollback:**

```python
try:
    db.begin()
    # Delete old chunks
    db.query(Embedding).filter(Embedding.document_id == doc_id).delete()
    # Insert new chunks
    db.bulk_insert_mappings(Embedding, chunks)
    db.commit()
except Exception:
    db.rollback()  # Rollback on any error
    raise
```

#### **3. Status Tracking Recovery:**

```python
# If task crashes, status remains 'in_progress'
# Cleanup job (cron):
UPDATE processing_status
SET status = 'failed',
    error_message = 'Task timed out or crashed'
WHERE status = 'in_progress'
  AND stage = 'chunking'
  AND updated_at < NOW() - INTERVAL '1 hour'
```

### 6.4 Rollback Procedures

**Scenario: Chunking fails mid-process**

```sql
-- Manual rollback script
BEGIN;

-- 1. Delete incomplete chunks
DELETE FROM embeddings
WHERE document_id = '550e8400-e29b-41d4-a716-446655440000';

-- 2. Reset processing status
UPDATE processing_status
SET status = 'not_started',
    error_message = NULL,
    result_data = NULL
WHERE document_id = '550e8400-e29b-41d4-a716-446655440000'
  AND stage = 'chunking';

-- 3. Clear timestamp
UPDATE documents
SET last_indexed_at = NULL
WHERE id = '550e8400-e29b-41d4-a716-446655440000';

COMMIT;
```

**Retry chunking:**

```python
from app.tasks.chunking_tasks import chunk_document_text

# Manually trigger retry
chunk_document_text.delay('550e8400-e29b-41d4-a716-446655440000')
```

### 6.5 Logging Points

**Structured Logging (with context):**

```python
import structlog
logger = structlog.get_logger()

# 1. Task start
logger.info(
    "chunking_started",
    document_id=str(document_id),
    text_length=document_text.text_length
)

# 2. Sentence splitting complete
logger.debug(
    "sentences_detected",
    document_id=str(document_id),
    sentence_count=len(sentences)
)

# 3. Chunks created
logger.info(
    "chunks_created",
    document_id=str(document_id),
    chunk_count=len(chunks),
    avg_chunk_size=avg_size
)

# 4. Database save
logger.info(
    "chunks_saved",
    document_id=str(document_id),
    chunk_count=saved_count,
    duration_ms=duration
)

# 5. Task completion
logger.info(
    "chunking_completed",
    document_id=str(document_id),
    chunk_count=result.chunk_count,
    processing_time_ms=result.processing_time_ms
)

# 6. Errors
logger.error(
    "chunking_failed",
    document_id=str(document_id),
    error_code="CHUNK_003",
    error_message=str(exc),
    exc_info=True
)
```

**Log Levels:**

- **DEBUG**: Sentence detection, chunk boundaries
- **INFO**: Task lifecycle, chunk counts, performance
- **WARNING**: Text too short, unusual chunk counts
- **ERROR**: Database failures, validation errors
- **CRITICAL**: Out of memory, data corruption

---

## 7. TESTING CHECKLIST

### 7.1 Manual Testing Steps

#### **Test 1: Basic Chunking Flow**

```bash
# 1. Upload a PDF
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@sample_10pages.pdf"

# Response should include document_id
DOCUMENT_ID="550e8400-e29b-41d4-a716-446655440000"

# 2. Wait for extraction (check logs)
# Celery extraction worker should show:
# [INFO] Text extraction completed for document 550e8400...

# 3. Wait for chunking (check logs)
# Celery chunking worker should show:
# [INFO] Chunking started for document 550e8400...
# [INFO] Chunks created: 47 chunks
# [INFO] Chunking completed: 47 chunks in 2345ms

# 4. Verify chunks in database
psql -h localhost -U querybox -d querybox_core -c "
SELECT
    COUNT(*) as chunk_count,
    AVG(LENGTH(chunk_text)) as avg_chunk_length,
    MIN(chunk_index) as min_index,
    MAX(chunk_index) as max_index
FROM embeddings
WHERE document_id = '$DOCUMENT_ID';
"

# Expected output:
#  chunk_count | avg_chunk_length | min_index | max_index
# -------------+------------------+-----------+-----------
#           47 |              982 |         0 |        46
```

#### **Test 2: Sentence Boundary Preservation**

```sql
-- Check a sample chunk
SELECT
    chunk_index,
    LEFT(chunk_text, 100) as chunk_start,
    RIGHT(chunk_text, 100) as chunk_end
FROM embeddings
WHERE document_id = '550e8400-...'
ORDER BY chunk_index
LIMIT 5;

-- Verify:
-- ✓ Chunks start with capital letter (new sentence)
-- ✓ Chunks end with period/question/exclamation (sentence boundary)
```

#### **Test 3: Overlap Verification**

```sql
-- Check overlap between consecutive chunks
WITH chunk_pairs AS (
    SELECT
        c1.chunk_index,
        c1.end_position as chunk1_end,
        c2.start_position as chunk2_start,
        c1.end_position - c2.start_position as overlap
    FROM embeddings c1
    JOIN embeddings c2
        ON c1.document_id = c2.document_id
        AND c1.chunk_index = c2.chunk_index - 1
    WHERE c1.document_id = '550e8400-...'
)
SELECT
    AVG(overlap) as avg_overlap,
    MIN(overlap) as min_overlap,
    MAX(overlap) as max_overlap
FROM chunk_pairs;

-- Expected:
--  avg_overlap | min_overlap | max_overlap
-- -------------+-------------+-------------
--          200 |         180 |         220
-- (Variance due to sentence boundaries)
```

#### **Test 4: Error Handling**

```python
# Trigger chunking on document without extracted text
from app.tasks.chunking_tasks import chunk_document_text

# This should fail gracefully
result = chunk_document_text.delay('non-existent-uuid')

# Check logs:
# [ERROR] Chunking failed: No extracted text found

# Verify status
psql -c "
SELECT stage, status, error_message
FROM processing_status
WHERE document_id = 'non-existent-uuid'
  AND stage = 'chunking';
"

# Expected:
#   stage   | status | error_message
# ----------+--------+------------------
#  chunking | failed | No extracted text found
```

### 7.2 Expected Successful Behavior

**✅ Success Criteria:**

1. **Chunks Created:**
   - Chunk count roughly matches `text_length / (chunk_size - overlap)`
   - Example: 45,000 chars → ~56 chunks (45000 / 800)

2. **Chunk Quality:**
   - Average chunk size: 800-1200 chars
   - No chunk < 100 chars (except last chunk)
   - Chunks end with sentence terminators (. ! ?)

3. **Database State:**
   - All chunks saved to `embeddings` table
   - `chunk_index` sequential: 0, 1, 2, ... n
   - `start_position` and `end_position` consistent
   - No duplicate `(document_id, chunk_index)` pairs

4. **Processing Status:**
   - `processing_status.status = 'completed'`
   - `result_data` contains `{"chunk_count": X}`
   - `duration_ms` recorded (typically 1000-5000ms)

5. **Performance:**
   - Chunking completes in < 10 seconds for 100-page PDFs
   - No memory errors

### 7.3 Edge Cases to Verify

| Edge Case | Test Input | Expected Behavior |
|-----------|-----------|-------------------|
| **Very short text** | 50 chars | Single chunk created, warning logged |
| **No sentences** | "onelongwordwithnoperiods" | Single chunk, no sentence splitting |
| **Only periods** | "a. b. c. d. e. ..." | Many tiny chunks (may need handling) |
| **Unicode text** | "Café résumé naïve" | Handles correctly, no encoding errors |
| **Special characters** | "$$$ ### @@@ !!!" | Preserved in chunks |
| **Very long sentence** | 5000-char sentence | Split at chunk boundary even mid-sentence |
| **Empty paragraphs** | "Text\n\n\n\nMore text" | Whitespace normalized |
| **Code blocks** | "```python\ncode\n```" | Preserved as-is |
| **Tables** | Markdown/CSV tables | Preserved (formatting may break) |
| **Already chunked** | Re-run task | Old chunks deleted, new ones created |

### 7.4 Performance Benchmarks

**Target Metrics:**

| Document Size | Expected Time | Max Chunks | Max Memory |
|---------------|---------------|------------|------------|
| 10 pages (5KB) | < 1 second | ~6 chunks | < 50MB |
| 50 pages (25KB) | < 2 seconds | ~31 chunks | < 100MB |
| 100 pages (50KB) | < 5 seconds | ~62 chunks | < 200MB |
| 500 pages (250KB) | < 15 seconds | ~312 chunks | < 500MB |
| 1000 pages (500KB) | < 30 seconds | ~625 chunks | < 1GB |

**Benchmark Test:**

```bash
# Time chunking task
time python -c "
from app.tasks.chunking_tasks import chunk_document_text
result = chunk_document_text('550e8400-...')
print(result)
"

# Should output timing like:
# real    0m3.245s
# user    0m2.890s
# sys     0m0.120s
```

---

## 8. MONITORING & METRICS

### 8.1 Metrics Collected

**Prometheus Metrics (add to app):**

```python
# In app/core/metrics.py (create if needed)
from prometheus_client import Counter, Histogram, Gauge

# Chunk creation metrics
chunks_created_total = Counter(
    'chunks_created_total',
    'Total chunks created',
    ['document_type']
)

chunking_duration_seconds = Histogram(
    'chunking_duration_seconds',
    'Time to chunk document',
    ['document_type'],
    buckets=[0.5, 1, 2, 5, 10, 30]
)

avg_chunk_size = Gauge(
    'avg_chunk_size_chars',
    'Average chunk size in characters'
)

chunking_errors_total = Counter(
    'chunking_errors_total',
    'Chunking task failures',
    ['error_code']
)
```

**Business Metrics:**

```sql
-- Dashboard query: Daily chunking stats
SELECT
    DATE(created_at) as date,
    COUNT(DISTINCT document_id) as documents_chunked,
    COUNT(*) as total_chunks_created,
    AVG(LENGTH(chunk_text)) as avg_chunk_size,
    MAX(chunk_index) as max_chunk_index
FROM embeddings
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
  "event": "chunking_started",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "text_length": 45230,
  "chunk_config": {
    "chunk_size": 1000,
    "overlap": 200
  }
}

{
  "timestamp": "2025-10-23T14:30:17.890Z",
  "level": "INFO",
  "event": "chunks_created",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "chunk_count": 47,
  "avg_chunk_size": 982,
  "processing_time_ms": 2656
}

{
  "timestamp": "2025-10-23T14:30:18.120Z",
  "level": "INFO",
  "event": "chunking_completed",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "chunk_count": 47,
  "duration_ms": 2886,
  "status": "completed"
}
```

**Log Aggregation Queries (if using ELK/Loki):**

```
# Chunking success rate
event="chunking_completed" | stats count() by status

# Average processing time
event="chunking_completed" | stats avg(duration_ms) by document_type

# Error breakdown
event="chunking_failed" | stats count() by error_code
```

### 8.3 Health Check Indicators

**Add to `/health` endpoint:**

```python
# In app/api/v1/endpoints/health.py

@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    health = {
        # ... existing checks ...
        "chunking": {
            "status": "unknown",
            "last_chunk_created": None,
            "pending_chunks": 0
        }
    }

    # Check recent chunking activity
    try:
        last_chunk = db.query(Embedding).order_by(
            Embedding.created_at.desc()
        ).first()

        if last_chunk:
            health["chunking"]["status"] = "healthy"
            health["chunking"]["last_chunk_created"] = last_chunk.created_at.isoformat()

        # Check pending chunking tasks
        pending = db.query(ProcessingStatus).filter(
            ProcessingStatus.stage == 'chunking',
            ProcessingStatus.status == 'in_progress'
        ).count()

        health["chunking"]["pending_chunks"] = pending

    except Exception as e:
        health["chunking"]["status"] = "unhealthy"
        health["chunking"]["error"] = str(e)

    return health
```

### 8.4 Performance Measurements

**Key Performance Indicators (KPIs):**

1. **Chunking Throughput**
   ```sql
   -- Documents chunked per hour
   SELECT
       DATE_TRUNC('hour', completed_at) as hour,
       COUNT(*) as documents_chunked
   FROM processing_status
   WHERE stage = 'chunking' AND status = 'completed'
   GROUP BY hour
   ORDER BY hour DESC;
   ```

2. **Average Chunking Time**
   ```sql
   -- P50, P95, P99 latencies
   SELECT
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as p50_ms,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_ms,
       PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms) as p99_ms
   FROM processing_status
   WHERE stage = 'chunking' AND status = 'completed';
   ```

3. **Chunk Quality Distribution**
   ```sql
   -- Chunk size distribution
   SELECT
       CASE
           WHEN LENGTH(chunk_text) < 500 THEN '0-500'
           WHEN LENGTH(chunk_text) < 1000 THEN '500-1000'
           WHEN LENGTH(chunk_text) < 1500 THEN '1000-1500'
           ELSE '1500+'
       END as size_bucket,
       COUNT(*) as chunk_count
   FROM embeddings
   GROUP BY size_bucket;
   ```

4. **Error Rate**
   ```sql
   -- Chunking failure rate (last 24 hours)
   SELECT
       COUNT(*) FILTER (WHERE status = 'completed') as success_count,
       COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'failed') / COUNT(*), 2) as error_rate_pct
   FROM processing_status
   WHERE stage = 'chunking'
     AND created_at >= NOW() - INTERVAL '24 hours';
   ```

**Grafana Dashboard (example queries):**

```promql
# Chunking rate (chunks/second)
rate(chunks_created_total[5m])

# P95 chunking latency
histogram_quantile(0.95, chunking_duration_seconds_bucket)

# Error rate
rate(chunking_errors_total[5m]) / rate(chunks_created_total[5m])
```

---

## 9. SECURITY CONSIDERATIONS

### 9.1 Authentication / Authorization Checks

**Current State (MVP):**
- ✅ **No user authentication** in MVP (single-tenant mode)
- ✅ **API key validation** at upload endpoint (inherited from Step 3)
- ⏸️ **Authorization**: Not implemented (all documents accessible)

**Security Model:**

```python
# Chunking tasks operate on already-uploaded documents
# Security enforced at upload time (Step 3)

# In chunking_tasks.py:
# No additional auth checks needed - document already validated
# Document ID from trusted internal queue (not user input)
```

**Future (Multi-Tenant):**

```python
# Add workspace_id validation
def chunk_document_text(document_id: str, workspace_id: str):
    # Verify document belongs to workspace
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.workspace_id == workspace_id  # Future column
    ).first()

    if not document:
        raise PermissionDenied("Document not found or access denied")
```

### 9.2 Input Sanitization

**Text Content Sanitization:**

```python
# In chunking_service.py

def _sanitize_text(self, text: str) -> str:
    """
    Sanitize extracted text before chunking

    Security checks:
    1. Remove null bytes (database incompatibility)
    2. Normalize unicode (prevent encoding attacks)
    3. Limit control characters
    """
    # Remove null bytes
    text = text.replace('\x00', '')

    # Normalize unicode to NFKC form
    import unicodedata
    text = unicodedata.normalize('NFKC', text)

    # Remove other control characters (except \n, \t, \r)
    text = ''.join(
        char for char in text
        if unicodedata.category(char)[0] != 'C' or char in '\n\t\r'
    )

    return text
```

**Database Parameter Sanitization:**

```python
# ALWAYS use parameterized queries
# ✅ SAFE
db.query(DocumentText).filter(DocumentText.document_id == document_id)

# ❌ NEVER DO THIS
query = f"SELECT * FROM document_texts WHERE document_id = '{document_id}'"
db.execute(query)  # SQL injection vulnerability!
```

### 9.3 Path Traversal Prevention

**Not Applicable** - Chunking does not access filesystem.

All data flows through database:
- Input: `document_texts.full_text` (database column)
- Output: `embeddings.chunk_text` (database column)

No file reads or writes during chunking.

### 9.4 SQL Injection Prevention

**SQLAlchemy ORM Protections:**

```python
# All queries use ORM (automatically parameterized)

# ✅ Safe query construction
document_text = db.query(DocumentText).filter(
    DocumentText.document_id == document_id
).first()

# ✅ Safe bulk insert
db.bulk_insert_mappings(Embedding, chunk_dicts)

# ✅ Safe update
db.query(ProcessingStatus).filter(
    ProcessingStatus.document_id == document_id,
    ProcessingStatus.stage == 'chunking'
).update({"status": "completed"})
```

**Raw SQL (if needed):**

```python
# Use parameterized queries with text()
from sqlalchemy import text

# ✅ Safe
query = text("""
    SELECT COUNT(*) FROM embeddings
    WHERE document_id = :doc_id
""")
result = db.execute(query, {"doc_id": document_id})

# ❌ NEVER concatenate
query = f"SELECT * FROM embeddings WHERE document_id = '{document_id}'"  # UNSAFE!
```

### 9.5 File Type Restrictions

**Not Applicable** - Chunking operates on extracted text, not files.

File type validation already done in:
- Step 3: Upload validation (MIME type checking)
- Step 8.1: Text extraction (format-specific parsers)

Chunking receives only plain text (UTF-8 strings).

**Additional Safety:**

```python
# Verify text encoding
def _validate_text_encoding(self, text: str) -> bool:
    """Ensure text is valid UTF-8"""
    try:
        text.encode('utf-8').decode('utf-8')
        return True
    except UnicodeError:
        logger.warning("Invalid UTF-8 text detected")
        return False
```

---

## 10. CODE PATTERNS & CONVENTIONS

### 10.1 Design Patterns Used

#### **1. Service Layer Pattern**

```python
# Service encapsulates business logic
class ChunkingService:
    """Single Responsibility: Text chunking logic"""

    def chunk_text(self, text: str, ...) -> ChunkingResult:
        # Pure business logic, no I/O concerns
        pass

    async def save_chunks(self, chunks: List[ChunkData], ...):
        # Persistence logic separated
        pass
```

**Benefits:**
- Testable without database
- Reusable across different contexts (API, CLI, tasks)
- Clear separation of concerns

#### **2. Repository Pattern (Implicit)**

```python
# Database access through ORM models
class Embedding(Base):
    # Model defines structure
    pass

# Access pattern
embeddings = db.query(Embedding).filter(...).all()
```

**Benefits:**
- Abstraction over database details
- Easy to mock for testing
- Consistent query interface

#### **3. Result Object Pattern**

```python
@dataclass
class ChunkingResult:
    """Encapsulates operation result with metadata"""
    success: bool
    chunk_count: int
    processing_time_ms: int
    error_message: Optional[str] = None
```

**Benefits:**
- Explicit success/failure handling
- Rich metadata for logging/monitoring
- Type-safe return values

#### **4. Factory Pattern (Singleton Service)**

```python
# Global service instance
_chunking_service: Optional[ChunkingService] = None

def get_chunking_service() -> ChunkingService:
    """Factory function for service instance"""
    global _chunking_service
    if _chunking_service is None:
        _chunking_service = ChunkingService()
    return _chunking_service
```

**Benefits:**
- Lazy initialization
- Consistent instance across app
- Easy to override for testing

### 10.2 Naming Conventions Followed

**PEP 8 Compliance:**

| Element | Convention | Example |
|---------|-----------|---------|
| **Modules** | lowercase_with_underscores | `chunking_service.py` |
| **Classes** | PascalCase | `ChunkingService` |
| **Functions** | lowercase_with_underscores | `chunk_text()` |
| **Constants** | UPPERCASE_WITH_UNDERSCORES | `DEFAULT_CHUNK_SIZE` |
| **Private methods** | _leading_underscore | `_split_into_sentences()` |
| **Variables** | lowercase_with_underscores | `chunk_count` |

**Domain-Specific Terms:**

- **chunk** (noun): A text segment
- **chunking** (verb): The process of splitting text
- **overlap**: Shared characters between adjacent chunks
- **boundary**: Sentence/paragraph delimiter
- **position**: Character index in original text

**Database Naming:**

- Tables: `plural_lowercase` (e.g., `embeddings`)
- Columns: `lowercase_with_underscores` (e.g., `chunk_index`)
- Enums: `snake_case_enum` (e.g., `stage_status_enum`)

### 10.3 Async/Await Patterns

**Celery Tasks (Sync):**

```python
# Celery tasks are synchronous by default
@celery_app.task
def chunk_document_text(document_id: str) -> dict:
    # Standard synchronous code
    db = SessionLocal()
    try:
        # Blocking database calls are fine in Celery workers
        document_text = db.query(DocumentText).filter(...).first()
        # ...
    finally:
        db.close()
```

**Service Methods (Can be Async):**

```python
# Use async for I/O-bound operations
class ChunkingService:
    async def chunk_text(self, text: str, ...) -> ChunkingResult:
        # CPU-bound chunking logic (runs in executor if needed)
        chunks = await asyncio.to_thread(self._create_chunks, sentences)
        return ChunkingResult(...)

    async def save_chunks(self, chunks: List[ChunkData], ...):
        # I/O-bound database operation
        await db.execute(...)
        await db.commit()
```

**When to Use Async:**

- ✅ **FastAPI endpoints**: Always async
- ✅ **Database operations**: Use async SQLAlchemy if available
- ⏸️ **Celery tasks**: Sync is fine (worker pool handles concurrency)
- ❌ **Heavy CPU work**: Use `asyncio.to_thread()` or multiprocessing

### 10.4 Transaction Boundaries

**Explicit Transactions:**

```python
# Pattern: Begin → Execute → Commit/Rollback
try:
    db.begin()

    # 1. Delete old chunks (cleanup)
    db.query(Embedding).filter(
        Embedding.document_id == document_id
    ).delete()

    # 2. Insert new chunks (bulk operation)
    db.bulk_insert_mappings(Embedding, chunk_dicts)

    # 3. Update status
    db.query(ProcessingStatus).filter(...).update({...})

    db.commit()  # All or nothing

except Exception as exc:
    db.rollback()  # Undo all changes
    logger.error(f"Transaction failed: {exc}")
    raise
```

**Transaction Scope Guidelines:**

1. **One transaction per document**: All chunks for a document saved atomically
2. **Cleanup + Insert**: Delete old chunks, then insert new ones (in same transaction)
3. **Status updates**: Include in same transaction as chunk insertion
4. **No nested transactions**: SQLAlchemy doesn't support true nested transactions
5. **Rollback on any error**: Ensure database consistency

**Isolation Level:**

```python
# Default: READ COMMITTED (PostgreSQL)
# Sufficient for chunking (no concurrent writes expected)

# If needed, increase isolation:
db.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
```

### 10.5 Error Propagation Strategy

**Layered Error Handling:**

```
┌─────────────────────────────────────────┐
│ Celery Task (chunking_tasks.py)        │
│ - Catch all exceptions                  │
│ - Update processing_status = 'failed'   │
│ - Log error with context                │
│ - Decide: retry or fail permanently     │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ Service Layer (chunking_service.py)     │
│ - Raise specific exceptions:            │
│   - TextNotFoundError                   │
│   - DatabaseError                       │
│ - Include error context in exception    │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ Database Layer (SQLAlchemy)             │
│ - Let SQLAlchemy exceptions propagate   │
│ - Catch at service/task level           │
└─────────────────────────────────────────┘
```

**Example Implementation:**

```python
# Service layer raises specific errors
class ChunkingService:
    async def chunk_text(self, text: str, ...) -> ChunkingResult:
        if not text:
            raise TextNotFoundError("Empty text provided")

        try:
            chunks = self._create_chunks(sentences)
            await self.save_chunks(chunks, db)
        except SQLAlchemyError as exc:
            raise DatabaseError(f"Failed to save chunks: {exc}") from exc

        return ChunkingResult(success=True, ...)

# Task layer catches and handles
@celery_app.task(bind=True)
def chunk_document_text(self, document_id: str):
    try:
        service = get_chunking_service()
        result = service.chunk_text(...)

        # Update status: completed
        update_status(document_id, 'chunking', 'completed')

    except TextNotFoundError as exc:
        # Don't retry - permanent failure
        logger.warning(f"Chunking skipped: {exc}")
        update_status(document_id, 'chunking', 'failed', error=str(exc))

    except DatabaseError as exc:
        # Retry transient errors
        logger.error(f"Database error: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)

    except Exception as exc:
        # Unexpected error - log and fail
        logger.exception(f"Unexpected error in chunking: {exc}")
        update_status(document_id, 'chunking', 'failed', error=str(exc))
        raise
```

**Error Metadata:**

```python
# Always include context in errors
class ChunkingError(Exception):
    def __init__(self, message: str, document_id: UUID = None, **kwargs):
        super().__init__(message)
        self.document_id = document_id
        self.metadata = kwargs

    def to_dict(self):
        return {
            "error": self.__class__.__name__,
            "message": str(self),
            "document_id": str(self.document_id) if self.document_id else None,
            **self.metadata
        }
```

---

## 11. INTEGRATION POINTS

### 11.1 How This Connects to Other Components

**Upstream Dependencies:**

```
Upload (Step 3) → Extraction (Step 8.1) → Chunking (Step 8.2)
         ↓                 ↓                    ↓
    documents         document_texts       embeddings
```

**Downstream Consumers:**

```
Chunking (Step 8.2) → Embeddings (Step 9.1) → Vector Search (Step 10)
         ↓                    ↓                      ↓
    embeddings          embeddings.vector      Search Results
   (chunk_text)        (populated field)
```

**Component Interactions:**

| Component | Interaction Type | Data Exchange |
|-----------|-----------------|---------------|
| **Upload API** | Indirect (via queue) | Document ID queued |
| **Text Extraction** | Direct trigger | Extraction completes → Chunking starts |
| **Database** | Direct read/write | Reads `document_texts`, writes `embeddings` |
| **Celery Queue** | Async messaging | Task published to `chunking` queue |
| **Status Tracker** | Direct update | Updates `processing_status` table |
| **Embedding Service** | Data dependency | Reads chunks from `embeddings` table |

### 11.2 Database Queries Executed

**Query 1: Fetch Source Text**

```sql
-- In chunking_tasks.py
SELECT
    full_text,
    text_length,
    extraction_quality
FROM document_texts
WHERE document_id = $1;

-- Execution plan: Index scan on document_texts_pkey
-- Performance: <5ms (single row lookup)
```

**Query 2: Check for Existing Chunks**

```sql
-- Before chunking (optional cleanup check)
SELECT COUNT(*) as existing_chunks
FROM embeddings
WHERE document_id = $1;

-- If count > 0, delete before re-chunking
```

**Query 3: Delete Old Chunks**

```sql
-- In save_chunks()
DELETE FROM embeddings
WHERE document_id = $1;

-- Cascade: Also deletes dependent rows (none currently)
-- Performance: <50ms for 100 chunks
```

**Query 4: Bulk Insert Chunks**

```sql
-- Using SQLAlchemy bulk_insert_mappings
INSERT INTO embeddings (
    id, document_id, chunk_index, chunk_text,
    chunk_tokens, start_position, end_position,
    embedding_model, created_at
) VALUES
    (uuid_generate_v4(), $1, 0, $2, $3, $4, $5, 'pending', NOW()),
    (uuid_generate_v4(), $1, 1, $6, $7, $8, $9, 'pending', NOW()),
    -- ... (bulk insert all chunks)
;

-- Performance: ~100ms for 100 chunks (single batch)
```

**Query 5: Update Processing Status**

```sql
-- Mark chunking as completed
UPDATE processing_status
SET
    status = 'completed',
    completed_at = NOW(),
    duration_ms = $2,
    result_data = $3
WHERE document_id = $1
  AND stage = 'chunking';

-- Performance: <10ms (indexed on document_id + stage)
```

**Query 6: Update Document Timestamp**

```sql
-- Update last_indexed_at (indicates chunking done)
UPDATE documents
SET last_indexed_at = NOW()
WHERE id = $1;

-- Performance: <5ms (primary key lookup)
```

### 11.3 External Services Called

**None** - Chunking is entirely local.

No external API calls:
- ❌ No OpenAI API calls (embeddings in Step 9)
- ❌ No S3 access (text already in database)
- ❌ No web requests

All processing happens in-memory with local database access.

### 11.4 Events Published/Consumed

**Events Consumed:**

```python
# Celery task receives event from extraction
# Event: "Text extraction completed for document X"
# Trigger: chunk_document_text.delay(document_id)

# Event source: extraction_tasks.py
from app.tasks.chunking_tasks import chunk_document_text

# After extraction succeeds:
chunk_document_text.delay(str(document_id))
```

**Events Published:**

```python
# After chunking completes, could publish event for embedding generation
# (Step 9 - future implementation)

# Example event:
{
    "event_type": "chunking_completed",
    "document_id": "550e8400-...",
    "chunk_count": 47,
    "timestamp": "2025-10-23T14:35:00Z"
}

# Consumer: Embedding generation task (Step 9.1)
# Trigger: generate_embeddings.delay(document_id)
```

**Event Bus (Future):**

```python
# Optional: Use Redis pub/sub or RabbitMQ for events
# For MVP: Direct task chaining is sufficient

# Current (Step 8.2):
chunk_document_text.delay(doc_id)

# Future (Step 9):
from app.tasks.embedding_tasks import generate_embeddings
generate_embeddings.delay(doc_id)  # Chain after chunking
```

**Database Triggers (Existing):**

```sql
-- Automatic updated_at trigger (from schema.sql)
CREATE TRIGGER update_processing_status_updated_at
BEFORE UPDATE ON processing_status
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- No custom triggers for chunking
```

---

## 12. TROUBLESHOOTING GUIDE

### 12.1 Common Issues and Solutions

#### **Issue 1: No chunks created (chunk_count = 0)**

**Symptoms:**
- Task completes successfully
- `processing_status.status = 'completed'`
- But `SELECT COUNT(*) FROM embeddings WHERE document_id = ...` returns 0

**Root Causes:**
1. Text extraction not complete
2. Text too short (< 100 chars)
3. Database transaction rollback

**Debugging:**

```sql
-- Check if text exists
SELECT document_id, text_length, full_text IS NOT NULL as has_text
FROM document_texts
WHERE document_id = '550e8400-...';

-- Expected: text_length > 100, has_text = true
```

**Solutions:**

```bash
# 1. Verify extraction completed
psql -c "
SELECT stage, status, completed_at
FROM processing_status
WHERE document_id = '550e8400-...'
  AND stage = 'extraction';
"

# If extraction = 'failed', re-run extraction:
python -c "
from app.tasks.extraction_tasks import extract_document_text
extract_document_text.delay('550e8400-...')
"

# 2. Check text length
psql -c "
SELECT text_length FROM document_texts
WHERE document_id = '550e8400-...';
"

# If < 100, document may be empty PDF (scanned image without OCR)

# 3. Check logs for transaction errors
grep "chunking_failed" /var/log/celery/worker.log
```

---

#### **Issue 2: Chunking task stuck in 'in_progress'**

**Symptoms:**
- `processing_status.status = 'in_progress'` for > 10 minutes
- No error logs
- Celery worker appears idle

**Root Causes:**
1. Worker crashed mid-task
2. Database connection timeout
3. Task killed by system (OOM)

**Debugging:**

```bash
# 1. Check Celery worker status
celery -A app.celery_app inspect active

# Look for stuck task with document_id

# 2. Check worker logs
tail -f /var/log/celery/worker.log
# Look for MemoryError, TimeoutError, or killed messages

# 3. Check system resources
free -h  # Check available memory
top      # Check CPU usage
```

**Solutions:**

```sql
-- 1. Reset stuck status (manual recovery)
UPDATE processing_status
SET status = 'failed',
    error_message = 'Task timeout - manually reset'
WHERE document_id = '550e8400-...'
  AND stage = 'chunking'
  AND status = 'in_progress'
  AND updated_at < NOW() - INTERVAL '10 minutes';

-- 2. Re-queue chunking task
```

```python
from app.tasks.chunking_tasks import chunk_document_text
chunk_document_text.delay('550e8400-...')
```

```bash
# 3. Restart Celery worker if needed
pkill -f "celery.*worker"
celery -A app.celery_app worker --loglevel=info --queues=chunking --concurrency=4
```

---

#### **Issue 3: Chunks are too small/large**

**Symptoms:**
- Chunk sizes consistently outside 800-1200 char range
- Example: All chunks ~200 chars or all ~2000 chars

**Root Cause:**
- Configuration error (CHUNK_SIZE env var)
- Sentence detection failing

**Debugging:**

```sql
-- Check chunk size distribution
SELECT
    CASE
        WHEN LENGTH(chunk_text) < 500 THEN '0-500'
        WHEN LENGTH(chunk_text) < 1000 THEN '500-1000'
        WHEN LENGTH(chunk_text) < 1500 THEN '1000-1500'
        ELSE '1500+'
    END as size_range,
    COUNT(*) as chunk_count
FROM embeddings
WHERE document_id = '550e8400-...'
GROUP BY size_range;
```

```python
# Check configuration
import os
print(f"CHUNK_SIZE: {os.getenv('CHUNK_SIZE', 'not set')}")
print(f"CHUNK_OVERLAP: {os.getenv('CHUNK_OVERLAP', 'not set')}")
```

**Solutions:**

```bash
# 1. Verify environment variables
cat .env | grep CHUNK

# Should show:
# CHUNK_SIZE=1000
# CHUNK_OVERLAP=200

# 2. Restart workers to pick up new config
pkill -f celery
celery -A app.celery_app worker ... (restart command)

# 3. Re-chunk document with corrected config
python -c "
from app.tasks.chunking_tasks import chunk_document_text
chunk_document_text.delay('550e8400-...')
"
```

---

#### **Issue 4: Sentence boundaries not preserved**

**Symptoms:**
- Chunks start mid-sentence: "...ple of text. This is a sa"
- Chunks end mid-word: "This is an exam"

**Root Cause:**
- Regex pattern not matching sentence endings
- Document has unusual punctuation

**Debugging:**

```sql
-- Check chunk start/end characters
SELECT
    chunk_index,
    LEFT(chunk_text, 50) as chunk_start,
    RIGHT(chunk_text, 50) as chunk_end
FROM embeddings
WHERE document_id = '550e8400-...'
ORDER BY chunk_index
LIMIT 10;

-- Expect:
-- chunk_start: Starts with capital letter
-- chunk_end: Ends with . ! ? or natural ending
```

```python
# Test sentence detection
text = "This is sentence one. This is sentence two! Is this three?"
import re
sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
print(sentences)
# Expected: ['This is sentence one.', 'This is sentence two!', 'Is this three?']
```

**Solutions:**

```python
# 1. Update sentence detection pattern (in chunking_service.py)
# Current pattern: r'(?<=[.!?])\s+(?=[A-Z])'

# Enhanced pattern (handles more cases):
SENTENCE_PATTERN = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?]["\')\]])\s+(?=[A-Z])'

# Handles: "Quote." Next sentence
#          Example! (citation) Next sentence

# 2. Add fallback chunking (if no sentences detected)
if len(sentences) == 1 and len(text) > chunk_size * 2:
    # Fallback: split at whitespace boundaries
    words = text.split()
    # Group words into chunks...
```

---

#### **Issue 5: Duplicate key error (chunk_index)**

**Symptoms:**
- Error: `duplicate key value violates unique constraint "embeddings_unique_chunk"`
- Task fails with IntegrityError

**Root Cause:**
- Previous chunking didn't complete cleanup
- Concurrent chunking tasks for same document

**Debugging:**

```sql
-- Check for existing chunks
SELECT chunk_index, created_at
FROM embeddings
WHERE document_id = '550e8400-...'
ORDER BY chunk_index;

-- Check for concurrent tasks
SELECT id, status, started_at, updated_at
FROM processing_status
WHERE document_id = '550e8400-...'
  AND stage = 'chunking'
ORDER BY started_at DESC;
```

**Solutions:**

```sql
-- 1. Manual cleanup
DELETE FROM embeddings
WHERE document_id = '550e8400-...';

-- 2. Reset processing status
UPDATE processing_status
SET status = 'not_started'
WHERE document_id = '550e8400-...'
  AND stage = 'chunking';
```

```python
# 3. Add idempotency to task
@celery_app.task
def chunk_document_text(document_id: str):
    # Check if already chunking
    existing = db.query(ProcessingStatus).filter(
        ProcessingStatus.document_id == document_id,
        ProcessingStatus.stage == 'chunking',
        ProcessingStatus.status == 'in_progress'
    ).first()

    if existing:
        logger.warning(f"Chunking already in progress for {document_id}")
        return {"status": "already_processing"}

    # Proceed with chunking...
```

---

### 12.2 Debug Commands

**1. Check Chunking Status**

```bash
# Via psql
psql -h localhost -U querybox -d querybox_core -c "
SELECT
    d.document_name,
    ps.stage,
    ps.status,
    ps.started_at,
    ps.completed_at,
    ps.duration_ms,
    ps.error_message
FROM processing_status ps
JOIN documents d ON ps.document_id = d.id
WHERE ps.stage = 'chunking'
ORDER BY ps.started_at DESC
LIMIT 10;
"
```

**2. Count Chunks per Document**

```bash
psql -c "
SELECT
    document_id,
    COUNT(*) as chunk_count,
    AVG(LENGTH(chunk_text))::int as avg_chunk_size,
    MIN(chunk_index) as min_index,
    MAX(chunk_index) as max_index
FROM embeddings
GROUP BY document_id
ORDER BY chunk_count DESC;
"
```

**3. Inspect Specific Chunk**

```bash
# View chunk content
psql -c "
SELECT
    chunk_index,
    LENGTH(chunk_text) as length,
    start_position,
    end_position,
    chunk_text
FROM embeddings
WHERE document_id = '550e8400-...'
  AND chunk_index = 0;
" | less
```

**4. Check Celery Queue Length**

```bash
# Redis queue inspection
redis-cli LLEN chunking

# Expected: 0-10 (small queue)
# If > 100: Worker may be overwhelmed

# Check pending tasks
redis-cli LRANGE chunking 0 5
```

**5. Monitor Chunking Performance**

```bash
# Real-time log monitoring
tail -f /var/log/celery/worker.log | grep "chunking"

# Expected output:
# [INFO] chunking_started document_id=550e8400...
# [INFO] chunks_created chunk_count=47 duration_ms=2345
# [INFO] chunking_completed document_id=550e8400...
```

**6. Re-run Chunking for Document**

```python
# Python shell
from app.tasks.chunking_tasks import chunk_document_text
from app.db.database import SessionLocal

# Get document ID
db = SessionLocal()
doc = db.query(Document).filter(Document.document_name == 'sample.pdf').first()

# Queue chunking task
task = chunk_document_text.delay(str(doc.id))
print(f"Task ID: {task.id}")

# Check task status
from app.celery_app import celery_app
result = celery_app.AsyncResult(task.id)
print(f"Status: {result.status}")
print(f"Result: {result.result}")
```

### 12.3 Log Locations

**Celery Worker Logs:**

```bash
# Default location (depends on deployment)
/var/log/celery/worker.log

# Or stdout if running in foreground
celery -A app.celery_app worker ... (logs to stdout)

# Docker container logs
docker logs querybox-celery-chunking

# Systemd service logs
journalctl -u celery-chunking -f
```

**Application Logs (FastAPI):**

```bash
# Uvicorn logs
/var/log/querybox/app.log

# Or stdout
uvicorn app.main:app --reload  (logs to stdout)
```

**Database Logs (PostgreSQL):**

```bash
# Query logs (if enabled)
/var/log/postgresql/postgresql-15-main.log

# Enable query logging:
# In postgresql.conf:
# log_statement = 'all'
# log_duration = on
```

**Log Filtering:**

```bash
# Filter for specific document
grep "550e8400-e29b-41d4-a716-446655440000" /var/log/celery/worker.log

# Filter for errors
grep -i "error\|exception" /var/log/celery/worker.log | grep chunking

# Filter for performance issues
grep "duration_ms" /var/log/celery/worker.log | awk '{print $NF}' | sort -n

# Tail live logs for chunking only
tail -f /var/log/celery/worker.log | grep --line-buffered chunking
```

### 12.4 Database Queries for Verification

**Query 1: Verify End-to-End Pipeline**

```sql
-- Check document progress through pipeline
SELECT
    d.document_name,
    d.status as doc_status,
    dt.text_length,
    COUNT(e.id) as chunk_count,
    MAX(ps_extract.status) as extraction_status,
    MAX(ps_chunk.status) as chunking_status
FROM documents d
LEFT JOIN document_texts dt ON d.id = dt.document_id
LEFT JOIN embeddings e ON d.id = e.document_id
LEFT JOIN processing_status ps_extract
    ON d.id = ps_extract.document_id AND ps_extract.stage = 'extraction'
LEFT JOIN processing_status ps_chunk
    ON d.id = ps_chunk.document_id AND ps_chunk.stage = 'chunking'
WHERE d.document_name = 'sample.pdf'
GROUP BY d.id, d.document_name, d.status, dt.text_length;
```

**Expected Output:**
| document_name | doc_status | text_length | chunk_count | extraction_status | chunking_status |
|---------------|------------|-------------|-------------|-------------------|-----------------|
| sample.pdf | completed | 45230 | 47 | completed | completed |

---

**Query 2: Validate Chunk Continuity**

```sql
-- Ensure no gaps in chunk_index
WITH chunk_sequence AS (
    SELECT
        document_id,
        chunk_index,
        LEAD(chunk_index) OVER (PARTITION BY document_id ORDER BY chunk_index) as next_index
    FROM embeddings
    WHERE document_id = '550e8400-...'
)
SELECT
    chunk_index,
    next_index,
    next_index - chunk_index as gap
FROM chunk_sequence
WHERE next_index - chunk_index > 1;  -- Find gaps

-- Expected: 0 rows (no gaps)
```

---

**Query 3: Validate Overlap**

```sql
-- Check overlap between consecutive chunks
WITH chunk_overlap AS (
    SELECT
        c1.chunk_index,
        c1.end_position as chunk1_end,
        c2.start_position as chunk2_start,
        c1.end_position - c2.start_position as overlap_chars
    FROM embeddings c1
    JOIN embeddings c2
        ON c1.document_id = c2.document_id
        AND c1.chunk_index = c2.chunk_index - 1
    WHERE c1.document_id = '550e8400-...'
)
SELECT
    COUNT(*) as chunk_pairs,
    AVG(overlap_chars)::int as avg_overlap,
    MIN(overlap_chars) as min_overlap,
    MAX(overlap_chars) as max_overlap
FROM chunk_overlap;
```

**Expected Output:**
| chunk_pairs | avg_overlap | min_overlap | max_overlap |
|-------------|-------------|-------------|-------------|
| 46 | 200 | 180 | 220 |

---

**Query 4: Find Problematic Chunks**

```sql
-- Chunks that are too small or too large
SELECT
    chunk_index,
    LENGTH(chunk_text) as chunk_size,
    CASE
        WHEN LENGTH(chunk_text) < 100 THEN 'TOO_SMALL'
        WHEN LENGTH(chunk_text) > 1500 THEN 'TOO_LARGE'
        ELSE 'OK'
    END as issue
FROM embeddings
WHERE document_id = '550e8400-...'
  AND (LENGTH(chunk_text) < 100 OR LENGTH(chunk_text) > 1500);

-- Expected: 0-1 rows (last chunk may be small)
```

---

**Query 5: Performance Analysis**

```sql
-- Chunking performance over time
SELECT
    DATE(completed_at) as date,
    COUNT(*) as documents_chunked,
    AVG(duration_ms)::int as avg_duration_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms)::int as p50_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms)::int as p95_ms,
    MAX(duration_ms) as max_duration_ms
FROM processing_status
WHERE stage = 'chunking'
  AND status = 'completed'
  AND completed_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(completed_at)
ORDER BY date DESC;
```

**Expected Output:**
| date | documents_chunked | avg_duration_ms | p50_ms | p95_ms | max_duration_ms |
|------|-------------------|-----------------|--------|--------|-----------------|
| 2025-10-23 | 15 | 2340 | 2100 | 4500 | 8900 |

---

## 13. APPENDIX

### 13.1 Complete File Listing

**Files to Create:**

1. `backend/app/services/chunking/chunking_service.py` (300 lines)
2. `backend/app/services/chunking/__init__.py` (20 lines)
3. `backend/app/tasks/chunking_tasks.py` (150 lines)
4. `backend/tests/unit/services/test_chunking_service.py` (200 lines)
5. `backend/db/migrations/003_add_chunk_metadata.sql` (50 lines - optional)
6. `backend/docs/technical/step8.2_basic_chunking_implementation.md` (this file)

**Files to Modify:**

1. `backend/app/models/__init__.py` (+5 lines)
2. `backend/app/celery_app.py` (+10 lines)
3. `backend/app/tasks/extraction_tasks.py` (+5 lines)
4. `backend/app/api/v1/endpoints/documents.py` (+30 lines - optional)

**Total:** 6 new files, 4 modified files

### 13.2 Environment Variables Summary

```bash
# Required
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MIN_CHUNK_SIZE=100

# Optional (with defaults)
MAX_DOCUMENT_SIZE=10000000
MAX_CHUNKS_PER_DOCUMENT=10000
CHUNKING_TIMEOUT=600
CHUNKING_MAX_RETRIES=3
CHUNKING_RETRY_DELAY=60
CHUNK_BATCH_SIZE=1000
```

### 13.3 Database Schema Changes

**New Tables:** None (uses existing `embeddings` table)

**New Columns:** None (all columns already exist in schema.sql)

**New Indexes (optional migration):**

```sql
-- In 003_add_chunk_metadata.sql
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_length
ON embeddings ((LENGTH(chunk_text)));

CREATE INDEX IF NOT EXISTS idx_embeddings_position
ON embeddings (start_position, end_position);

-- For debugging/analytics
```

### 13.4 Success Metrics

**Step 8.2 Complete When:**

✅ Chunking service created and tested
✅ Celery task `chunk_document_text` functional
✅ Chunks saved to `embeddings` table with correct positions
✅ Sentence boundaries preserved in >90% of chunks
✅ Overlap validated (avg ~200 chars)
✅ End-to-end test: Upload PDF → Extract → Chunk → Verify
✅ Documentation complete

**Performance Targets:**

- ⏱️ **Chunking time**: <5 seconds for 100-page PDF
- 📊 **Chunk count**: ~50-60 chunks per 100 pages
- 📏 **Chunk size**: 800-1200 chars (avg ~1000)
- 🔄 **Overlap**: 180-220 chars (avg ~200)
- ✅ **Success rate**: >99% (failures only on malformed data)

---

## 14. NEXT STEPS (Step 9.1: Embeddings)

After completing Step 8.2, proceed to:

**Step 9.1: Embedding Generation**
- Install `openai` or `sentence-transformers` library
- Create `EmbeddingService` to generate vectors
- Celery task: `generate_embeddings(document_id)`
- Populate `embeddings.embedding` column (currently NULL)
- Chain after chunking: `chunk → generate_embeddings`

**Dependencies:**
- Step 8.2 chunks must exist in `embeddings` table
- OpenAI API key or local embedding model
- pgvector extension enabled

---

**END OF DOCUMENTATION**

*For questions or issues, refer to Troubleshooting Guide (Section 12) or contact the development team.*
