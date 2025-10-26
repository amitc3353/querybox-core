# Step 9.2: BGE-M3 Embedding Generation - Technical Documentation

**Version:** 1.0
**Last Updated:** October 25, 2024
**Status:** Planning Phase
**Timeline:** 2-3 days
**Dependencies:** Step 9.1 (Chunking Improvements), Step 9.0 (pgvector Setup)

---

## 1. FEATURE OVERVIEW

### 1.1 What This Step Accomplishes

Step 9.2 implements the embedding generation pipeline that converts text chunks into dense vector representations using the BGE-M3 model. This step:

1. **Generates Embeddings**: Converts text chunks to 1024-dimensional vectors using BAAI/bge-m3
2. **Batch Processing**: Processes up to 100 chunks at a time for efficiency
3. **Async Task Queue**: Uses Celery for non-blocking embedding generation
4. **Vector Storage**: Stores embeddings in PostgreSQL with pgvector extension
5. **Model Caching**: Downloads and caches BGE-M3 model locally for fast inference
6. **Status Tracking**: Updates processing status through the entire pipeline

### 1.2 Why This Step is Necessary

**Current State (Post Step 9.1):**
- ✅ High-quality chunks exist in `embeddings` table
- ✅ Rich metadata attached (headings, chunk_type, semantic_density)
- ❌ No vector representations → Can't perform semantic search
- ❌ Only keyword search available (limited accuracy)

**Problems Without Embeddings:**
- **Semantic Gap**: "How do I reset my password?" won't match "Password recovery instructions"
- **Synonym Blindness**: "automobile" won't match "car" or "vehicle"
- **Context Loss**: Can't understand query intent vs. literal keywords
- **Poor Ranking**: BM25 keyword search has ~60-70% accuracy vs. 85-95% with vectors

**Impact on System Performance:**
- Retrieval accuracy limited to exact keyword matches
- No multi-lingual support (BGE-M3 supports 100+ languages)
- Can't leverage hybrid search (BM25 + Vector fusion)
- Missing foundation for LLM-based answer generation

### 1.3 Dependencies on Previous Steps

| Step | Dependency | Required Data/Functionality |
|------|-----------|----------------------------|
| **Step 9.0** | pgvector Setup | `embeddings.embedding` column exists as `Vector(1024)` |
| **Step 9.1** | Chunking Improvements | High-quality chunks stored in `embeddings` table with metadata |
| **Step 8.3** | Keyword Search | Baseline search to compare against semantic search |
| **Celery Setup** | Task Queue | Celery workers running for async processing |

**Required Database Schema:**
```sql
-- embeddings table must have:
- id (UUID, primary key)
- document_id (UUID, foreign key to documents)
- chunk_text (TEXT, the content to embed)
- chunk_tokens (INTEGER, for validation)
- embedding (VECTOR(1024), pgvector type) -- Added in Step 9.0
- embedding_model (VARCHAR, to track model version)
- created_at (TIMESTAMP)
```

**Required Infrastructure:**
- PostgreSQL with pgvector extension installed
- Redis for Celery broker
- Celery workers running (at least 1 worker for embeddings queue)
- ~2GB disk space for BGE-M3 model cache
- ~4GB RAM minimum for model inference

### 1.4 What Future Steps Depend on This

| Step | Dependency Reason |
|------|------------------|
| **Step 9.3** | Vector Similarity Search requires embeddings in database |
| **Step 10.1** | Hybrid Retrieval (BM25 + Vector) needs both keyword and vector indexes |
| **Step 10.2** | Cross-encoder reranking needs initial vector retrieval candidates |
| **Step 11.1** | LLM answer generation relies on accurate semantic retrieval |
| **Step 12.1** | Cascade retrieval and semantic caching depend on vector similarity |

**Key Deliverable:** All document chunks have corresponding 1024-dimensional BGE-M3 embeddings stored in pgvector, ready for semantic search with <200ms p99 latency.

---

## 2. TECHNICAL IMPLEMENTATION

### 2.1 Files to Create/Modify

```
backend/
├── app/
│   ├── services/
│   │   └── embeddings/
│   │       ├── __init__.py (NEW)
│   │       ├── embedding_service.py (NEW - core embedding logic)
│   │       ├── model_manager.py (NEW - BGE-M3 model loading/caching)
│   │       └── batch_processor.py (NEW - batch processing optimization)
│   ├── tasks/
│   │   └── embedding_tasks.py (NEW - Celery tasks)
│   ├── schemas/
│   │   └── embedding.py (NEW - Pydantic schemas)
│   └── core/
│       └── config.py (MODIFY - add embedding settings)
├── tests/
│   └── unit/
│       └── services/
│           └── embeddings/
│               ├── test_embedding_service.py (NEW)
│               ├── test_model_manager.py (NEW)
│               └── test_batch_processor.py (NEW)
└── requirements.txt (MODIFY - add sentence-transformers, torch)
```

### 2.2 Key Classes and Functions

#### **EmbeddingService** (`app/services/embeddings/embedding_service.py`)

```python
class EmbeddingService:
    """
    Core service for generating BGE-M3 embeddings

    Responsibilities:
    - Load and manage BGE-M3 model
    - Generate embeddings for text chunks
    - Normalize vectors to unit length
    - Handle batch processing
    """

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        """Initialize with BGE-M3 model"""

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate single embedding vector

        Args:
            text: Text to embed (max 8192 tokens for BGE-M3)

        Returns:
            1024-dimensional normalized vector
        """

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of texts to embed
            batch_size: Internal batch size (32 for BGE-M3)

        Returns:
            List of 1024-dimensional vectors
        """

    def get_embedding_dimension(self) -> int:
        """Return 1024 for BGE-M3"""
```

#### **ModelManager** (`app/services/embeddings/model_manager.py`)

```python
class ModelManager:
    """
    Manages BGE-M3 model lifecycle

    Responsibilities:
    - Download model from HuggingFace (first run)
    - Cache model locally (~2GB)
    - Load model into memory with GPU/CPU detection
    - Handle model device placement (CUDA/MPS/CPU)
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        cache_dir: str = "/app/models"
    ):
        """Initialize model manager"""

    def load_model(self) -> SentenceTransformer:
        """
        Load BGE-M3 model with device auto-detection

        Device priority:
        1. CUDA (if available) - fastest
        2. CPU (fallback) - slower but works everywhere

        Note: MPS disabled for Apple Silicon due to Celery fork issues
        """

    def is_model_cached(self) -> bool:
        """Check if model exists locally"""

    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata (size, dimension, max_tokens)"""
```

#### **BatchProcessor** (`app/services/embeddings/batch_processor.py`)

```python
class BatchProcessor:
    """
    Optimized batch processing for embeddings

    Responsibilities:
    - Fetch unprocessed chunks from database
    - Process in batches of 100 chunks
    - Update database with generated embeddings
    - Track progress and errors
    """

    def __init__(self, db: Session, embedding_service: EmbeddingService):
        """Initialize with database and embedding service"""

    def process_document_chunks(
        self,
        document_id: UUID,
        batch_size: int = 100
    ) -> ProcessingResult:
        """
        Process all chunks for a document

        Args:
            document_id: Document UUID
            batch_size: Number of chunks per batch (default: 100)

        Returns:
            ProcessingResult with counts and timing
        """

    def get_unprocessed_chunks(
        self,
        document_id: UUID,
        limit: int = 100
    ) -> List[Embedding]:
        """
        Fetch chunks without embeddings

        Query:
        SELECT * FROM embeddings
        WHERE document_id = :doc_id
          AND embedding IS NULL
        ORDER BY chunk_index
        LIMIT :limit
        """
```

#### **Celery Task** (`app/tasks/embedding_tasks.py`)

```python
@celery_app.task(
    name="app.tasks.embedding_tasks.generate_embeddings",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_embeddings(self, document_id: str):
    """
    Async task to generate embeddings for all document chunks

    This task:
    1. Updates processing status to IN_PROGRESS
    2. Fetches chunks without embeddings
    3. Generates embeddings in batches of 100
    4. Updates database with vectors
    5. Creates pgvector index if needed
    6. Updates processing status to COMPLETED/FAILED
    7. Updates document.last_embedding_at timestamp

    Args:
        document_id: Document UUID string

    Returns:
        {
            "success": bool,
            "document_id": str,
            "chunks_processed": int,
            "processing_time_ms": int,
            "embeddings_per_second": float
        }
    """
```

### 2.3 Database Tables and Columns Used

#### **embeddings** (Modified in Step 9.0)
```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Chunk data (from Step 9.1)
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_tokens INTEGER,

    -- Embedding vector (Step 9.2)
    embedding VECTOR(1024),  -- BGE-M3 dimension
    embedding_model VARCHAR(100) DEFAULT 'BAAI/bge-m3',

    -- Metadata
    start_position INTEGER,
    end_position INTEGER,
    section_heading VARCHAR(500),
    chunk_type VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX idx_embeddings_document_id ON embeddings(document_id);
CREATE INDEX idx_embeddings_no_vector ON embeddings(document_id)
    WHERE embedding IS NULL;  -- Find unprocessed chunks

-- Vector similarity index (HNSW for speed)
CREATE INDEX idx_embeddings_vector_hnsw ON embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

#### **processing_status** (Existing)
```sql
-- Track embedding stage progress
INSERT INTO processing_status (
    document_id,
    stage,
    status,
    started_at
) VALUES (
    :doc_id,
    'EMBEDDING',  -- New stage
    'IN_PROGRESS',
    NOW()
);
```

#### **documents** (Existing)
```sql
-- Update last_embedding_at timestamp
UPDATE documents
SET last_embedding_at = NOW()
WHERE id = :doc_id;
```

### 2.4 API Endpoints

#### **Trigger Embedding Generation** (Optional - usually triggered automatically)
```
POST /api/v1/documents/{document_id}/embeddings/generate
```

**Request:**
```json
{
    "force_regenerate": false,  // Re-generate even if embeddings exist
    "batch_size": 100
}
```

**Response:**
```json
{
    "task_id": "abc-123-def-456",
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "PENDING",
    "message": "Embedding generation queued"
}
```

#### **Check Embedding Status**
```
GET /api/v1/documents/{document_id}/embeddings/status
```

**Response:**
```json
{
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "total_chunks": 150,
    "chunks_with_embeddings": 150,
    "completion_percentage": 100.0,
    "embedding_model": "BAAI/bge-m3",
    "last_embedding_at": "2024-10-25T10:30:00Z",
    "processing_status": "COMPLETED"
}
```

### 2.5 Background Tasks and Workers

#### **Celery Queue Configuration**
```python
# celery_app.py
celery_app.conf.task_routes = {
    "app.tasks.embedding_tasks.*": {
        "queue": "embeddings",
        "routing_key": "embeddings"
    }
}
```

#### **Worker Command**
```bash
# Start embedding worker
celery -A app.celery_app worker \
    --loglevel=info \
    --queues=embeddings \
    --concurrency=2 \
    --max-tasks-per-child=100 \
    --hostname=embeddings@%h
```

**Worker Resource Requirements:**
- **Memory**: 4-6GB per worker (BGE-M3 model + batch processing)
- **CPU**: 2+ cores recommended
- **GPU**: Optional (speeds up by ~3-5x, but not required)
- **Disk**: 2GB for model cache

---

## 3. DATA FLOW

### 3.1 End-to-End Data Journey

```mermaid
sequenceDiagram
    participant API as FastAPI Endpoint
    participant Queue as Celery/Redis
    participant Worker as Embedding Worker
    participant Model as BGE-M3 Model
    participant DB as PostgreSQL+pgvector

    API->>Queue: Enqueue generate_embeddings(doc_id)
    Queue->>Worker: Assign task to worker

    Worker->>DB: UPDATE processing_status SET status='IN_PROGRESS'
    Worker->>DB: SELECT chunks WHERE embedding IS NULL (LIMIT 100)

    loop For each batch of 100 chunks
        Worker->>Model: encode(texts, batch_size=32)
        Model-->>Worker: Return 1024-dim vectors
        Worker->>DB: UPDATE embeddings SET embedding=vector
    end

    Worker->>DB: CREATE INDEX IF NOT EXISTS (HNSW)
    Worker->>DB: UPDATE processing_status SET status='COMPLETED'
    Worker->>DB: UPDATE documents SET last_embedding_at=NOW()
    Worker-->>Queue: Return success result
```

### 3.2 Step-by-Step Processing

#### **Step 1: Task Enqueuing** (Auto-triggered after chunking completes)

```python
# In chunking_tasks.py (after successful chunking)
from app.tasks.embedding_tasks import generate_embeddings

# Chain tasks: chunking -> embedding
generate_embeddings.apply_async(
    args=[str(document_id)],
    countdown=5  # Wait 5 seconds before starting
)
```

**Database State:**
```sql
-- processing_status
stage='EMBEDDING', status='NOT_STARTED'

-- embeddings
embedding=NULL, embedding_model='pending'
```

#### **Step 2: Worker Picks Up Task**

```python
# embedding_tasks.py
@celery_app.task(...)
def generate_embeddings(self, document_id: str):
    db = SessionLocal()
    doc_uuid = UUID(document_id)

    # Update status
    tracker.update_status(
        document_id=doc_uuid,
        stage='EMBEDDING',
        status='IN_PROGRESS'
    )
```

**Database State:**
```sql
-- processing_status
stage='EMBEDDING', status='IN_PROGRESS', started_at='2024-10-25 10:00:00'
```

#### **Step 3: Load BGE-M3 Model** (First time only)

```python
# model_manager.py
model_manager = ModelManager()
model = model_manager.load_model()

# Downloads from HuggingFace (first run):
# ~/.cache/huggingface/hub/models--BAAI--bge-m3/
# - pytorch_model.bin (1.7GB)
# - config.json
# - tokenizer files
```

**Filesystem:**
```
/app/models/BAAI--bge-m3/
├── pytorch_model.bin (1.7GB)
├── config.json
├── tokenizer.json
└── special_tokens_map.json
```

#### **Step 4: Fetch Unprocessed Chunks**

```python
# batch_processor.py
chunks = db.query(Embedding).filter(
    Embedding.document_id == doc_uuid,
    Embedding.embedding.is_(None)
).order_by(Embedding.chunk_index).limit(100).all()
```

**Database Query:**
```sql
SELECT id, chunk_text, chunk_index
FROM embeddings
WHERE document_id = '550e8400-e29b-41d4-a716-446655440000'
  AND embedding IS NULL
ORDER BY chunk_index
LIMIT 100;
```

#### **Step 5: Generate Embeddings (Batch of 100)**

```python
# embedding_service.py
texts = [chunk.chunk_text for chunk in chunks]
vectors = embedding_service.generate_embeddings_batch(
    texts=texts,
    batch_size=32  # Internal batching for GPU efficiency
)

# vectors = [
#     [0.023, -0.145, 0.678, ..., 0.234],  # 1024 dims
#     [0.156, 0.089, -0.234, ..., -0.123], # 1024 dims
#     ...
# ]
```

**Model Processing:**
- Input: 100 text chunks (avg 512 tokens each)
- Tokenization: ~51,200 tokens total
- GPU Processing Time: ~5-10 seconds (with GPU)
- CPU Processing Time: ~30-60 seconds (without GPU)
- Output: 100 × 1024 float32 vectors

#### **Step 6: Update Database with Vectors**

```python
# batch_processor.py
for chunk, vector in zip(chunks, vectors):
    chunk.embedding = vector
    chunk.embedding_model = "BAAI/bge-m3"
    chunk.updated_at = datetime.now(timezone.utc)

db.commit()
```

**Database Transaction:**
```sql
BEGIN;

UPDATE embeddings
SET
    embedding = '[0.023,-0.145,0.678,...,0.234]'::vector,
    embedding_model = 'BAAI/bge-m3',
    updated_at = NOW()
WHERE id = '123e4567-e89b-12d3-a456-426614174000';

-- Repeat for all 100 chunks

COMMIT;
```

#### **Step 7: Create Vector Index** (If not exists)

```python
# After all batches processed
db.execute(text("""
    CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw
    ON embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
"""))
```

**Index Creation:**
- **HNSW**: Hierarchical Navigable Small World graph
- **m = 16**: Max connections per layer (higher = better recall, more memory)
- **ef_construction = 64**: Size of dynamic candidate list (higher = slower build, better quality)
- **Build Time**: ~10-30 seconds for 10,000 vectors

#### **Step 8: Update Processing Status**

```python
# Mark embedding stage complete
tracker.mark_stage_completed(
    document_id=doc_uuid,
    stage='EMBEDDING',
    result_data={
        "chunks_processed": 150,
        "processing_time_ms": 45000,
        "embeddings_per_second": 3.33,
        "model": "BAAI/bge-m3"
    }
)

# Update document timestamp
document.last_embedding_at = datetime.now(timezone.utc)
db.commit()
```

**Final Database State:**
```sql
-- processing_status
stage='EMBEDDING', status='COMPLETED',
completed_at='2024-10-25 10:01:00',
duration_ms=60000,
result_data='{"chunks_processed": 150, ...}'

-- documents
last_embedding_at='2024-10-25 10:01:00'

-- embeddings (all 150 chunks)
embedding=[vector data], embedding_model='BAAI/bge-m3'
```

### 3.3 Database Transactions

#### **Transaction 1: Status Update (Start)**
```sql
BEGIN;
UPDATE processing_status
SET status='IN_PROGRESS', started_at=NOW()
WHERE document_id=:doc_id AND stage='EMBEDDING';
COMMIT;
```

#### **Transaction 2: Batch Embedding Update** (Repeated for each batch)
```sql
BEGIN;

-- Update batch of 100 chunks
UPDATE embeddings
SET embedding = :vector_data,
    embedding_model = 'BAAI/bge-m3',
    updated_at = NOW()
WHERE id IN (:chunk_ids);  -- 100 IDs

COMMIT;
```

#### **Transaction 3: Status Update (Complete)**
```sql
BEGIN;

UPDATE processing_status
SET status='COMPLETED',
    completed_at=NOW(),
    duration_ms=:duration,
    result_data=:metrics::jsonb
WHERE document_id=:doc_id AND stage='EMBEDDING';

UPDATE documents
SET last_embedding_at=NOW()
WHERE id=:doc_id;

COMMIT;
```

### 3.4 File System Operations

#### **Model Download** (First Run Only)
```
~/.cache/huggingface/hub/models--BAAI--bge-m3/
└── snapshots/
    └── 5617a9f61063b0e4293b2bb7c2e2d0c9c7b9a123/
        ├── pytorch_model.bin (1.7GB)
        ├── config.json (2KB)
        ├── tokenizer.json (2.1MB)
        ├── tokenizer_config.json (1KB)
        └── special_tokens_map.json (1KB)
```

#### **Model Cache Check**
```python
import os
from pathlib import Path

cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
model_path = cache_dir / "models--BAAI--bge-m3"

if model_path.exists():
    print("Model cached locally, no download needed")
else:
    print("Downloading model (~1.7GB, first time only)")
```

---

## 4. VALIDATIONS & CONSTRAINTS

### 4.1 Input Validations

#### **Document Validation**
```python
# Check document exists
document = db.query(Document).filter(Document.id == doc_uuid).first()
if not document:
    raise ValueError(f"Document {document_id} not found")

# Check chunking completed
if document.last_indexed_at is None:
    raise ValueError("Document must be chunked before embedding generation")

# Check chunks exist
chunk_count = db.query(Embedding).filter(
    Embedding.document_id == doc_uuid
).count()
if chunk_count == 0:
    raise ValueError("No chunks found for document")
```

#### **Chunk Text Validation**
```python
# Validate chunk text length
MAX_TOKENS = 8192  # BGE-M3 max sequence length

for chunk in chunks:
    if not chunk.chunk_text or len(chunk.chunk_text.strip()) == 0:
        logger.warning(f"Skipping empty chunk {chunk.id}")
        continue

    if chunk.chunk_tokens > MAX_TOKENS:
        logger.warning(
            f"Chunk {chunk.id} exceeds max tokens "
            f"({chunk.chunk_tokens} > {MAX_TOKENS}), truncating"
        )
        # Truncate to max tokens
        chunk.chunk_text = truncate_to_tokens(chunk.chunk_text, MAX_TOKENS)
```

#### **Embedding Vector Validation**
```python
def validate_embedding(vector: List[float]) -> bool:
    """Validate embedding vector"""
    # Check dimension
    if len(vector) != 1024:
        raise ValueError(f"Invalid dimension: {len(vector)}, expected 1024")

    # Check for NaN or Inf
    if any(math.isnan(v) or math.isinf(v) for v in vector):
        raise ValueError("Embedding contains NaN or Inf values")

    # Check normalization (BGE-M3 returns normalized vectors)
    magnitude = sum(v ** 2 for v in vector) ** 0.5
    if not (0.99 <= magnitude <= 1.01):
        logger.warning(f"Vector not normalized: magnitude={magnitude:.4f}")

    return True
```

### 4.2 Business Rules Enforced

#### **Rule 1: No Re-embedding Unless Forced**
```python
# Check if embeddings already exist
existing_count = db.query(Embedding).filter(
    Embedding.document_id == doc_uuid,
    Embedding.embedding.isnot(None)
).count()

if existing_count > 0 and not force_regenerate:
    return {
        "success": True,
        "message": "Embeddings already exist, skipping",
        "chunks_processed": 0
    }
```

#### **Rule 2: Atomic Batch Processing**
```python
# All chunks in batch must succeed or entire batch rolls back
try:
    db.begin_nested()  # Savepoint

    for chunk, vector in zip(chunks, vectors):
        chunk.embedding = vector

    db.commit()  # Commit savepoint
except Exception as e:
    db.rollback()  # Rollback entire batch
    logger.error(f"Batch failed: {e}")
    raise
```

#### **Rule 3: Index Creation After Embeddings**
```python
# Only create index after at least 1000 vectors exist
vector_count = db.query(Embedding).filter(
    Embedding.embedding.isnot(None)
).count()

if vector_count >= 1000 and not index_exists():
    create_hnsw_index()
```

#### **Rule 4: Model Version Tracking**
```python
# Track which model version generated each embedding
EMBEDDING_MODEL_VERSION = "BAAI/bge-m3"

chunk.embedding_model = EMBEDDING_MODEL_VERSION

# Later: Query by model version
chunks_v1 = db.query(Embedding).filter(
    Embedding.embedding_model == "text-embedding-ada-002"
).all()  # Old OpenAI embeddings

chunks_v2 = db.query(Embedding).filter(
    Embedding.embedding_model == "BAAI/bge-m3"
).all()  # New BGE-M3 embeddings
```

### 4.3 Security Checks Implemented

#### **Resource Limits**
```python
# Prevent memory exhaustion
MAX_BATCH_SIZE = 100
MAX_CONCURRENT_DOCUMENTS = 5

if batch_size > MAX_BATCH_SIZE:
    raise ValueError(f"Batch size {batch_size} exceeds limit {MAX_BATCH_SIZE}")

# Check concurrent processing
processing_count = db.query(ProcessingStatus).filter(
    ProcessingStatus.stage == 'EMBEDDING',
    ProcessingStatus.status == 'IN_PROGRESS'
).count()

if processing_count >= MAX_CONCURRENT_DOCUMENTS:
    raise HTTPException(
        status_code=429,
        detail="Too many documents being processed, try again later"
    )
```

#### **Input Sanitization**
```python
# Prevent injection attacks in text
def sanitize_text(text: str) -> str:
    """Remove potentially malicious content"""
    # Remove null bytes
    text = text.replace('\x00', '')

    # Limit length
    MAX_CHUNK_LENGTH = 50000  # ~8192 tokens * 6 chars/token
    if len(text) > MAX_CHUNK_LENGTH:
        text = text[:MAX_CHUNK_LENGTH]

    return text

# Apply before embedding
chunk.chunk_text = sanitize_text(chunk.chunk_text)
```

### 4.4 Error Conditions Handled

#### **Error 1: Model Download Failure**
```python
try:
    model = SentenceTransformer("BAAI/bge-m3")
except (OSError, ConnectionError) as e:
    logger.error(f"Failed to download model: {e}")
    raise HTTPException(
        status_code=503,
        detail="Embedding model unavailable, check internet connection"
    )
```

#### **Error 2: GPU Out of Memory**
```python
try:
    vectors = model.encode(texts, device='cuda')
except RuntimeError as e:
    if "out of memory" in str(e):
        logger.warning("GPU OOM, falling back to CPU")
        torch.cuda.empty_cache()
        vectors = model.encode(texts, device='cpu')
    else:
        raise
```

#### **Error 3: Database Connection Lost**
```python
try:
    db.commit()
except OperationalError as e:
    logger.error(f"Database connection lost: {e}")
    db.rollback()

    # Retry with exponential backoff
    if self.request.retries < self.max_retries:
        raise self.retry(exc=e, countdown=60)
    else:
        raise
```

#### **Error 4: Invalid Vector Data**
```python
try:
    validate_embedding(vector)
except ValueError as e:
    logger.error(f"Invalid embedding for chunk {chunk.id}: {e}")

    # Skip this chunk, continue with others
    failed_chunks.append({
        "chunk_id": str(chunk.id),
        "error": str(e)
    })
    continue
```

### 4.5 Rate Limits and Quotas

#### **Worker Concurrency**
```python
# Celery worker configuration
worker_concurrency = 2  # Max 2 tasks simultaneously
worker_max_tasks_per_child = 100  # Restart after 100 tasks (prevent memory leaks)
```

#### **Batch Size Limits**
```python
# Configuration
MIN_BATCH_SIZE = 10
MAX_BATCH_SIZE = 100
DEFAULT_BATCH_SIZE = 100

def validate_batch_size(batch_size: int) -> int:
    """Validate and clamp batch size"""
    if batch_size < MIN_BATCH_SIZE:
        logger.warning(f"Batch size {batch_size} too small, using {MIN_BATCH_SIZE}")
        return MIN_BATCH_SIZE

    if batch_size > MAX_BATCH_SIZE:
        logger.warning(f"Batch size {batch_size} too large, using {MAX_BATCH_SIZE}")
        return MAX_BATCH_SIZE

    return batch_size
```

#### **Task Time Limits**
```python
# Celery task configuration
task_time_limit = 30 * 60  # 30 minutes hard limit
task_soft_time_limit = 25 * 60  # 25 minutes soft limit

# For 1000 chunks at ~2 chunks/second = 500 seconds = 8.3 minutes
# Plenty of headroom for slower CPUs
```

---

## 5. CONFIGURATION

### 5.1 Environment Variables

```bash
# ============================================================================
# EMBEDDING SERVICE CONFIGURATION
# ============================================================================

# Model Configuration
EMBEDDING_MODEL_NAME="BAAI/bge-m3"
EMBEDDING_DIMENSION=1024
EMBEDDING_MAX_TOKENS=8192

# Model Cache (HuggingFace downloads models here)
TRANSFORMERS_CACHE="/app/models"
HF_HOME="/app/models"
HF_DATASETS_CACHE="/app/models/datasets"

# Device Configuration
# Options: "cuda", "cpu", "auto"
# "auto" = Use CUDA if available, else CPU
EMBEDDING_DEVICE="auto"

# Apple Silicon MPS Workaround (disable MPS in Celery workers)
PYTORCH_ENABLE_MPS="0"
PYTORCH_MPS_HIGH_WATERMARK_RATIO="0.0"
PYTORCH_ENABLE_MPS_FALLBACK="1"

# Batch Processing
EMBEDDING_BATCH_SIZE=100  # Number of chunks per batch
EMBEDDING_INTERNAL_BATCH_SIZE=32  # GPU batch size

# Performance Tuning
EMBEDDING_MAX_WORKERS=2  # Number of concurrent embedding workers
EMBEDDING_WORKER_MEMORY_LIMIT="6GB"  # Max memory per worker

# Retry Configuration
EMBEDDING_MAX_RETRIES=3
EMBEDDING_RETRY_DELAY=60  # seconds

# ============================================================================
# CELERY QUEUE CONFIGURATION
# ============================================================================

# Queue Names
CELERY_EMBEDDING_QUEUE="embeddings"

# Task Routing
CELERY_TASK_ROUTES='{"app.tasks.embedding_tasks.*": {"queue": "embeddings"}}'

# ============================================================================
# POSTGRESQL + PGVECTOR CONFIGURATION
# ============================================================================

# Vector Index Settings
PGVECTOR_INDEX_TYPE="hnsw"  # or "ivfflat"
PGVECTOR_HNSW_M=16  # Max connections per layer (8-64, higher = better recall)
PGVECTOR_HNSW_EF_CONSTRUCTION=64  # Build quality (40-200, higher = slower build)

# Index Creation Threshold
PGVECTOR_MIN_VECTORS_FOR_INDEX=1000  # Don't create index until 1000 vectors

# ============================================================================
# LOGGING
# ============================================================================

# Embedding-specific logging
EMBEDDING_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR
EMBEDDING_LOG_FILE="/app/logs/embeddings.log"
```

### 5.2 Default Values and Limits

```python
# app/core/config.py

class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Embedding Model Configuration
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_MAX_TOKENS: int = 8192
    EMBEDDING_DEVICE: str = "auto"

    # Batch Processing Limits
    EMBEDDING_BATCH_SIZE: int = 100
    EMBEDDING_MIN_BATCH_SIZE: int = 10
    EMBEDDING_MAX_BATCH_SIZE: int = 100
    EMBEDDING_INTERNAL_BATCH_SIZE: int = 32

    # Worker Configuration
    EMBEDDING_MAX_WORKERS: int = 2
    EMBEDDING_WORKER_MEMORY_LIMIT: str = "6GB"

    # Retry Policy
    EMBEDDING_MAX_RETRIES: int = 3
    EMBEDDING_RETRY_DELAY: int = 60

    # Model Cache
    TRANSFORMERS_CACHE: str = "/app/models"
    HF_HOME: str = "/app/models"

    # Vector Index Configuration
    PGVECTOR_INDEX_TYPE: str = "hnsw"
    PGVECTOR_HNSW_M: int = 16
    PGVECTOR_HNSW_EF_CONSTRUCTION: int = 64
    PGVECTOR_MIN_VECTORS_FOR_INDEX: int = 1000

    # Performance Thresholds
    EMBEDDING_SPEED_THRESHOLD: float = 1.0  # Min embeddings/second
    EMBEDDING_TIMEOUT_SECONDS: int = 1500  # 25 minutes

    class Config:
        env_file = ".env"
        case_sensitive = True
```

### 5.3 File Paths and Directory Structure

```
/app/
├── models/                          # Model cache directory
│   └── BAAI--bge-m3/
│       ├── pytorch_model.bin        # 1.7GB model weights
│       ├── config.json
│       ├── tokenizer.json
│       └── special_tokens_map.json
│
├── logs/                            # Application logs
│   ├── embeddings.log               # Embedding-specific logs
│   ├── celery.log                   # Celery worker logs
│   └── app.log                      # General app logs
│
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   └── embeddings/
│   │   │       ├── __init__.py
│   │   │       ├── embedding_service.py
│   │   │       ├── model_manager.py
│   │   │       └── batch_processor.py
│   │   ├── tasks/
│   │   │   └── embedding_tasks.py
│   │   └── core/
│   │       └── config.py
│   └── tests/
│
└── data/                            # Database data (PostgreSQL)
    └── pgdata/
        └── pg_wal/
```

### 5.4 Docker Services Required

```yaml
# docker-compose.yml

version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: querybox
      POSTGRES_USER: querybox_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U querybox_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  celery-embedding-worker:
    build: ./backend
    command: >
      celery -A app.celery_app worker
      --loglevel=info
      --queues=embeddings
      --concurrency=2
      --max-tasks-per-child=100
      --hostname=embeddings@%h
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - DATABASE_URL=postgresql://querybox_user:${DB_PASSWORD}@postgres:5432/querybox
      - EMBEDDING_MODEL_NAME=BAAI/bge-m3
      - EMBEDDING_DEVICE=cpu
      - TRANSFORMERS_CACHE=/app/models
      - PYTORCH_ENABLE_MPS=0
    volumes:
      - ./backend:/app
      - model_cache:/app/models
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          memory: 6G
        reservations:
          memory: 4G

volumes:
  pgdata:
  redis_data:
  model_cache:
```

---

## 6. ERROR HANDLING

### 6.1 Possible Failure Scenarios

#### **Scenario 1: Model Download Failure**

**Cause:** Network issues, HuggingFace downtime, firewall blocking

**Symptoms:**
```
OSError: Can't load the model for 'BAAI/bge-m3'.
If you were trying to load it from 'https://huggingface.co/models',
make sure you don't have a local directory with the same name.
```

**Recovery:**
```python
def load_model_with_retry(max_retries=3):
    """Load model with retry logic"""
    for attempt in range(max_retries):
        try:
            model = SentenceTransformer("BAAI/bge-m3")
            return model
        except (OSError, ConnectionError) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt * 10  # Exponential backoff
                logger.warning(
                    f"Model download failed (attempt {attempt + 1}/{max_retries}), "
                    f"retrying in {wait_time}s: {e}"
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to download model after {max_retries} attempts")
                raise
```

#### **Scenario 2: GPU Out of Memory**

**Cause:** Batch size too large for GPU memory

**Symptoms:**
```
RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB
(GPU 0; 11.91 GiB total capacity; 9.87 GiB already allocated)
```

**Recovery:**
```python
def generate_embeddings_with_fallback(texts, device='auto'):
    """Generate embeddings with GPU→CPU fallback"""
    try:
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'

        vectors = model.encode(texts, device=device, batch_size=32)
        return vectors

    except RuntimeError as e:
        if "out of memory" in str(e) and device == 'cuda':
            logger.warning("GPU OOM, falling back to CPU")
            torch.cuda.empty_cache()

            # Retry on CPU with smaller batch size
            vectors = model.encode(texts, device='cpu', batch_size=16)
            return vectors
        else:
            raise
```

#### **Scenario 3: Database Connection Lost**

**Cause:** Network issues, database restart, connection timeout

**Symptoms:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError)
server closed the connection unexpectedly
```

**Recovery:**
```python
@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def generate_embeddings(self, document_id: str):
    """Task with automatic retry on database errors"""
    db = SessionLocal()

    try:
        # ... embedding logic ...
        db.commit()

    except OperationalError as e:
        logger.error(f"Database error: {e}")
        db.rollback()

        # Celery will automatically retry with exponential backoff
        raise

    finally:
        db.close()
```

#### **Scenario 4: Corrupted/Invalid Chunk Data**

**Cause:** Null text, invalid encoding, corrupt database record

**Symptoms:**
```
ValueError: Embedding contains NaN values
TypeError: 'NoneType' object is not subscriptable
```

**Recovery:**
```python
def process_chunk_safely(chunk):
    """Process chunk with error handling"""
    try:
        # Validate chunk
        if not chunk.chunk_text or len(chunk.chunk_text.strip()) == 0:
            logger.warning(f"Skipping empty chunk {chunk.id}")
            return None

        # Generate embedding
        vector = embedding_service.generate_embedding(chunk.chunk_text)

        # Validate embedding
        validate_embedding(vector)

        return vector

    except Exception as e:
        logger.error(
            f"Failed to process chunk {chunk.id}: {e}",
            extra={
                "chunk_id": str(chunk.id),
                "chunk_length": len(chunk.chunk_text) if chunk.chunk_text else 0,
                "error_type": type(e).__name__
            }
        )
        return None

# Usage
vectors = []
failed_chunks = []

for chunk in chunks:
    vector = process_chunk_safely(chunk)
    if vector is not None:
        vectors.append((chunk, vector))
    else:
        failed_chunks.append(chunk.id)
```

#### **Scenario 5: Worker Crashes Mid-Processing**

**Cause:** OOM, segfault, killed by OS

**Symptoms:**
- Task stuck in "IN_PROGRESS" forever
- No error message in logs
- Worker disappeared from Celery status

**Recovery:**
```python
# Celery task with time limits
@celery_app.task(
    time_limit=1800,  # 30 minutes hard limit
    soft_time_limit=1500,  # 25 minutes soft limit
)
def generate_embeddings(self, document_id: str):
    """Task with time limits to prevent hanging"""

    try:
        # ... processing logic ...

    except SoftTimeLimitExceeded:
        logger.warning(f"Task approaching time limit, gracefully stopping")

        # Mark as failed but retriable
        tracker.mark_stage_failed(
            document_id=doc_uuid,
            stage='EMBEDDING',
            error_message="Task timeout, will retry with smaller batch"
        )

        # Retry with smaller batch size
        raise self.retry(countdown=120, kwargs={'batch_size': 50})
```

**Manual Recovery:**
```python
# Script to detect and retry stuck tasks
def recover_stuck_embedding_tasks():
    """Find and retry tasks stuck in IN_PROGRESS for >30 minutes"""
    from datetime import datetime, timedelta

    threshold = datetime.now(timezone.utc) - timedelta(minutes=30)

    stuck_tasks = db.query(ProcessingStatus).filter(
        ProcessingStatus.stage == 'EMBEDDING',
        ProcessingStatus.status == 'IN_PROGRESS',
        ProcessingStatus.started_at < threshold
    ).all()

    for task in stuck_tasks:
        logger.warning(f"Recovering stuck task for document {task.document_id}")

        # Reset status
        task.status = 'FAILED'
        task.error_message = "Task timeout, auto-recovering"
        db.commit()

        # Retry
        generate_embeddings.apply_async(args=[str(task.document_id)])
```

### 6.2 Error Messages and Codes

```python
class EmbeddingError(Enum):
    """Standard error codes for embedding generation"""

    # Model errors (5xx - retryable)
    MODEL_DOWNLOAD_FAILED = ("EMB_001", "Failed to download embedding model", 503)
    MODEL_LOAD_FAILED = ("EMB_002", "Failed to load embedding model into memory", 503)
    GPU_OOM = ("EMB_003", "GPU out of memory", 503)

    # Data errors (4xx - not retryable)
    DOCUMENT_NOT_FOUND = ("EMB_101", "Document not found", 404)
    NO_CHUNKS_FOUND = ("EMB_102", "No chunks found for document", 400)
    CHUNKS_NOT_READY = ("EMB_103", "Document must be chunked before embedding", 400)
    INVALID_CHUNK_TEXT = ("EMB_104", "Chunk text is empty or invalid", 400)

    # Processing errors (5xx - retryable)
    DATABASE_ERROR = ("EMB_201", "Database connection error", 503)
    EMBEDDING_GENERATION_FAILED = ("EMB_202", "Failed to generate embedding", 500)
    BATCH_PROCESSING_FAILED = ("EMB_203", "Batch processing failed", 500)

    # Timeout errors (5xx - retryable with smaller batch)
    TASK_TIMEOUT = ("EMB_301", "Task exceeded time limit", 504)
    WORKER_CRASHED = ("EMB_302", "Worker process crashed", 503)

def format_error_response(error: EmbeddingError, details: str = None):
    """Format standardized error response"""
    code, message, http_status = error.value

    return {
        "error_code": code,
        "error_message": message,
        "details": details,
        "http_status": http_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

### 6.3 Logging Points

```python
# Critical logging points for debugging

# 1. Task Start
logger.info(
    f"Starting embedding generation for document {document_id}",
    extra={
        "document_id": document_id,
        "task_id": self.request.id,
        "worker": self.request.hostname
    }
)

# 2. Model Loading
logger.info(
    f"Loading embedding model {model_name}",
    extra={
        "model": model_name,
        "device": device,
        "cache_hit": model_cached
    }
)

# 3. Batch Processing Start
logger.debug(
    f"Processing batch {batch_num}/{total_batches}",
    extra={
        "batch_size": len(chunks),
        "batch_num": batch_num,
        "total_batches": total_batches
    }
)

# 4. Embedding Generation
logger.debug(
    f"Generated embeddings for {len(texts)} chunks in {elapsed_ms}ms",
    extra={
        "chunk_count": len(texts),
        "processing_time_ms": elapsed_ms,
        "embeddings_per_second": len(texts) / (elapsed_ms / 1000)
    }
)

# 5. Database Update
logger.debug(
    f"Updated {len(chunks)} chunks with embeddings",
    extra={
        "chunk_ids": [str(c.id) for c in chunks[:5]],  # First 5 IDs
        "transaction_time_ms": transaction_time_ms
    }
)

# 6. Index Creation
logger.info(
    f"Creating vector index with {vector_count} vectors",
    extra={
        "index_type": "hnsw",
        "m": 16,
        "ef_construction": 64,
        "vector_count": vector_count
    }
)

# 7. Task Completion
logger.info(
    f"Embedding generation completed for document {document_id}",
    extra={
        "document_id": document_id,
        "chunks_processed": chunks_processed,
        "processing_time_ms": total_time_ms,
        "embeddings_per_second": chunks_processed / (total_time_ms / 1000)
    }
)

# 8. Error Logging
logger.error(
    f"Embedding generation failed for document {document_id}",
    extra={
        "document_id": document_id,
        "error_code": error_code,
        "error_message": str(error),
        "failed_chunk_ids": failed_chunks,
        "retry_count": self.request.retries
    },
    exc_info=True  # Include stack trace
)
```

### 6.4 Rollback Procedures

#### **Rollback on Batch Failure**
```python
def process_batch_with_rollback(chunks, embedding_service, db):
    """Process batch with automatic rollback on failure"""

    # Create savepoint
    savepoint = db.begin_nested()

    try:
        # Generate embeddings
        texts = [c.chunk_text for c in chunks]
        vectors = embedding_service.generate_embeddings_batch(texts)

        # Update database
        for chunk, vector in zip(chunks, vectors):
            chunk.embedding = vector
            chunk.embedding_model = "BAAI/bge-m3"

        # Commit savepoint
        savepoint.commit()

        logger.info(f"Successfully processed batch of {len(chunks)} chunks")
        return True

    except Exception as e:
        # Rollback savepoint (batch only, not entire transaction)
        savepoint.rollback()

        logger.error(f"Batch processing failed, rolled back: {e}")
        return False
```

#### **Rollback on Task Failure**
```python
def rollback_failed_task(document_id: UUID, db: Session):
    """Rollback failed embedding task"""

    # 1. Reset processing status
    db.query(ProcessingStatus).filter(
        ProcessingStatus.document_id == document_id,
        ProcessingStatus.stage == 'EMBEDDING'
    ).update({
        'status': 'FAILED',
        'completed_at': datetime.now(timezone.utc),
        'error_message': 'Task failed, rolled back'
    })

    # 2. Clear partial embeddings (optional - depends on retry strategy)
    # Option A: Keep partial embeddings for next retry
    logger.info(f"Keeping {count} partial embeddings for retry")

    # Option B: Clear all embeddings and start fresh
    # db.query(Embedding).filter(
    #     Embedding.document_id == document_id
    # ).update({'embedding': None, 'embedding_model': 'pending'})

    db.commit()
```

---

## 7. TESTING CHECKLIST

### 7.1 Manual Testing Steps

#### **Test 1: Single Document Embedding**

```bash
# 1. Upload a document
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@test.pdf" \
  -H "X-API-Key: dev-key"

# Response: {"document_id": "550e8400-e29b-41d4-a716-446655440000"}

# 2. Wait for chunking to complete (check logs)
tail -f backend/logs/app.log | grep "Chunking completed"

# 3. Trigger embedding generation
curl -X POST http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440000/embeddings/generate \
  -H "X-API-Key: dev-key"

# Response: {"task_id": "abc-123", "status": "PENDING"}

# 4. Check embedding status
curl http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440000/embeddings/status \
  -H "X-API-Key: dev-key"

# Expected Response:
# {
#   "total_chunks": 42,
#   "chunks_with_embeddings": 42,
#   "completion_percentage": 100.0,
#   "embedding_model": "BAAI/bge-m3",
#   "processing_status": "COMPLETED"
# }
```

#### **Test 2: Verify Vector Data in Database**

```sql
-- Check embeddings exist
SELECT
    document_id,
    COUNT(*) as total_chunks,
    COUNT(embedding) as chunks_with_embeddings,
    embedding_model
FROM embeddings
WHERE document_id = '550e8400-e29b-41d4-a716-446655440000'
GROUP BY document_id, embedding_model;

-- Expected:
-- total_chunks | chunks_with_embeddings | embedding_model
-- 42           | 42                     | BAAI/bge-m3

-- Verify vector dimensions
SELECT
    id,
    chunk_index,
    array_length(embedding, 1) as vector_dimension,
    LEFT(chunk_text, 50) as chunk_preview
FROM embeddings
WHERE document_id = '550e8400-e29b-41d4-a716-446655440000'
LIMIT 5;

-- Expected vector_dimension: 1024 for all rows
```

#### **Test 3: Verify Vector Index Created**

```sql
-- Check HNSW index exists
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'embeddings'
  AND indexname LIKE '%vector%';

-- Expected:
-- indexname: idx_embeddings_vector_hnsw
-- indexdef: CREATE INDEX ... USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)
```

#### **Test 4: Test Vector Similarity Search**

```sql
-- Generate a test query vector (in real app, this comes from embedding the query)
-- For testing, use an existing chunk's vector
WITH query_vector AS (
    SELECT embedding
    FROM embeddings
    WHERE document_id = '550e8400-e29b-41d4-a716-446655440000'
    LIMIT 1
)
SELECT
    e.id,
    e.chunk_index,
    LEFT(e.chunk_text, 100) as chunk_text,
    1 - (e.embedding <=> q.embedding) as cosine_similarity
FROM embeddings e, query_vector q
WHERE e.document_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY e.embedding <=> q.embedding
LIMIT 10;

-- Expected:
-- Top result should be the same chunk (similarity = 1.0)
-- Other results should have similarity < 1.0
```

#### **Test 5: Batch Processing Performance**

```bash
# Upload 10 documents
for i in {1..10}; do
    curl -X POST http://localhost:8000/api/v1/upload \
      -F "file=@test_${i}.pdf" \
      -H "X-API-Key: dev-key"
done

# Monitor Celery worker logs
celery -A app.celery_app inspect active

# Check processing times
tail -f backend/logs/embeddings.log | grep "embeddings_per_second"

# Expected: >1.0 embeddings/second with CPU, >3.0 with GPU
```

### 7.2 Expected Successful Behavior

#### **Success Criteria:**
1. ✅ All chunks have non-null `embedding` values
2. ✅ All embeddings have exactly 1024 dimensions
3. ✅ `embedding_model` = "BAAI/bge-m3" for all chunks
4. ✅ `processing_status.stage='EMBEDDING'` shows `status='COMPLETED'`
5. ✅ `documents.last_embedding_at` timestamp is updated
6. ✅ HNSW index exists on `embeddings.embedding` column
7. ✅ Vector similarity queries return results in <200ms

#### **Performance Benchmarks:**
- **CPU**: 1-2 embeddings/second (100 chunks in ~50-100 seconds)
- **GPU**: 3-5 embeddings/second (100 chunks in ~20-33 seconds)
- **Batch Size**: 100 chunks optimal for database efficiency
- **Memory**: <4GB per worker on CPU, <6GB with GPU

### 7.3 Edge Cases to Verify

#### **Edge Case 1: Empty Chunks**
```python
# Create chunk with empty text
chunk = Embedding(
    document_id=doc_id,
    chunk_index=99,
    chunk_text="   ",  # Whitespace only
    chunk_tokens=0
)
db.add(chunk)
db.commit()

# Expected: Skip chunk, log warning, continue processing
```

#### **Edge Case 2: Very Long Chunks**
```python
# Create chunk exceeding max tokens
long_text = "word " * 10000  # ~10,000 tokens

chunk = Embedding(
    document_id=doc_id,
    chunk_index=100,
    chunk_text=long_text,
    chunk_tokens=10000
)

# Expected: Truncate to 8192 tokens, log warning, process successfully
```

#### **Edge Case 3: Special Characters**
```python
# Chunk with unicode, emojis, math symbols
special_text = "Hello 👋 Math: ∑∫∂ Code: <?php echo 'test'; ?>"

chunk = Embedding(
    document_id=doc_id,
    chunk_index=101,
    chunk_text=special_text,
    chunk_tokens=20
)

# Expected: Process without errors, sanitize null bytes only
```

#### **Edge Case 4: Concurrent Document Processing**
```bash
# Trigger 5 documents simultaneously
for doc_id in doc1 doc2 doc3 doc4 doc5; do
    curl -X POST "http://localhost:8000/api/v1/documents/${doc_id}/embeddings/generate" \
      -H "X-API-Key: dev-key" &
done

# Expected: All 5 process successfully, no deadlocks, workers share load
```

#### **Edge Case 5: Re-embedding Same Document**
```bash
# Try to embed already-embedded document
curl -X POST http://localhost:8000/api/v1/documents/550e8400.../embeddings/generate \
  -H "X-API-Key: dev-key"

# Expected: Skip with message "Embeddings already exist"

# Force re-embedding
curl -X POST http://localhost:8000/api/v1/documents/550e8400.../embeddings/generate \
  -H "X-API-Key: dev-key" \
  -d '{"force_regenerate": true}'

# Expected: Re-generate all embeddings, update timestamps
```

### 7.4 Performance Benchmarks

#### **Target Metrics:**

| Metric | Target | Measured |
|--------|--------|----------|
| Embeddings/second (CPU) | >1.0 | _____ |
| Embeddings/second (GPU) | >3.0 | _____ |
| Batch processing time (100 chunks, CPU) | <100s | _____ |
| Batch processing time (100 chunks, GPU) | <35s | _____ |
| Database update time (100 chunks) | <2s | _____ |
| Index creation time (10k vectors) | <30s | _____ |
| Vector search latency (p99) | <200ms | _____ |
| Memory per worker | <6GB | _____ |

#### **Benchmark Script:**

```python
# scripts/benchmark_embeddings.py

import time
from app.services.embeddings import EmbeddingService

def benchmark_embedding_speed():
    """Measure embedding generation speed"""

    service = EmbeddingService()
    test_texts = ["This is a test sentence."] * 100

    # Warmup
    service.generate_embeddings_batch(test_texts[:10])

    # Measure
    start = time.time()
    vectors = service.generate_embeddings_batch(test_texts)
    elapsed = time.time() - start

    embeddings_per_sec = len(test_texts) / elapsed

    print(f"Generated {len(vectors)} embeddings in {elapsed:.2f}s")
    print(f"Speed: {embeddings_per_sec:.2f} embeddings/second")

    # Verify dimensions
    assert all(len(v) == 1024 for v in vectors), "Invalid dimensions"

    return embeddings_per_sec

if __name__ == "__main__":
    speed = benchmark_embedding_speed()

    if speed >= 3.0:
        print("✅ EXCELLENT: GPU performance")
    elif speed >= 1.0:
        print("✅ GOOD: CPU performance")
    else:
        print("❌ SLOW: Check worker configuration")
```

---

## 8. MONITORING & METRICS

### 8.1 Metrics to Collect

#### **Processing Metrics**
```python
# Prometheus metrics (app/monitoring/metrics.py)

from prometheus_client import Counter, Histogram, Gauge

# Total embeddings generated
embeddings_generated_total = Counter(
    'embeddings_generated_total',
    'Total number of embeddings generated',
    ['model', 'device']
)

# Processing time histogram
embedding_processing_time_seconds = Histogram(
    'embedding_processing_time_seconds',
    'Time to generate embeddings in seconds',
    ['batch_size'],
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

# Embeddings per second gauge
embeddings_per_second = Gauge(
    'embeddings_per_second',
    'Current embedding generation speed',
    ['worker']
)

# Active embedding tasks
active_embedding_tasks = Gauge(
    'active_embedding_tasks',
    'Number of embedding tasks currently processing'
)

# Failed embeddings counter
embedding_failures_total = Counter(
    'embedding_failures_total',
    'Total number of failed embedding generations',
    ['error_type']
)

# Database update time
embedding_db_update_seconds = Histogram(
    'embedding_db_update_seconds',
    'Time to update database with embeddings',
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)
```

#### **Resource Metrics**
```python
# Model memory usage
model_memory_bytes = Gauge(
    'model_memory_bytes',
    'Memory used by embedding model',
    ['model']
)

# Worker memory usage
worker_memory_bytes = Gauge(
    'worker_memory_bytes',
    'Memory used by embedding worker',
    ['worker']
)

# Model cache size
model_cache_size_bytes = Gauge(
    'model_cache_size_bytes',
    'Size of model cache on disk'
)
```

#### **Business Metrics**
```python
# Documents with embeddings
documents_embedded_total = Gauge(
    'documents_embedded_total',
    'Total documents with embeddings'
)

# Chunks with embeddings
chunks_embedded_total = Gauge(
    'chunks_embedded_total',
    'Total chunks with embeddings'
)

# Average chunks per document
average_chunks_per_document = Gauge(
    'average_chunks_per_document',
    'Average number of chunks per document'
)
```

### 8.2 Log Entries Generated

#### **Structured Logging Format**
```python
import structlog

logger = structlog.get_logger()

# Task start
logger.info(
    "embedding_task_started",
    document_id=str(document_id),
    task_id=task_id,
    worker=worker_hostname,
    timestamp=datetime.now(timezone.utc).isoformat()
)

# Batch processing
logger.debug(
    "embedding_batch_processed",
    document_id=str(document_id),
    batch_num=batch_num,
    batch_size=len(chunks),
    processing_time_ms=elapsed_ms,
    embeddings_per_second=speed
)

# Database update
logger.debug(
    "embedding_db_updated",
    document_id=str(document_id),
    chunks_updated=len(chunks),
    transaction_time_ms=transaction_ms
)

# Index creation
logger.info(
    "vector_index_created",
    index_name="idx_embeddings_vector_hnsw",
    vector_count=vector_count,
    creation_time_ms=creation_ms
)

# Task completion
logger.info(
    "embedding_task_completed",
    document_id=str(document_id),
    chunks_processed=total_chunks,
    total_time_ms=total_ms,
    avg_embeddings_per_second=avg_speed,
    success=True
)

# Task failure
logger.error(
    "embedding_task_failed",
    document_id=str(document_id),
    error_code=error_code,
    error_message=str(error),
    failed_at_batch=batch_num,
    retry_count=retry_count,
    success=False,
    exc_info=True
)
```

### 8.3 Health Check Indicators

#### **Embedding Service Health**
```python
# app/api/routes/health.py

@router.get("/health/embeddings")
async def embedding_health():
    """Check embedding service health"""

    health = {
        "status": "healthy",
        "checks": {}
    }

    # Check 1: Model loaded
    try:
        from app.services.embeddings import get_embedding_service
        service = get_embedding_service()
        health["checks"]["model_loaded"] = {
            "status": "pass",
            "model": service.model_name,
            "device": str(service.device)
        }
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["model_loaded"] = {
            "status": "fail",
            "error": str(e)
        }

    # Check 2: Can generate embedding
    try:
        test_vector = service.generate_embedding("test")
        assert len(test_vector) == 1024
        health["checks"]["embedding_generation"] = {
            "status": "pass",
            "dimension": len(test_vector)
        }
    except Exception as e:
        health["status"] = "degraded"
        health["checks"]["embedding_generation"] = {
            "status": "fail",
            "error": str(e)
        }

    # Check 3: Celery workers available
    from app.celery_app import celery_app
    inspect = celery_app.control.inspect()
    active_workers = inspect.active()

    if active_workers and 'embeddings@' in str(active_workers):
        health["checks"]["workers"] = {
            "status": "pass",
            "active_workers": len(active_workers)
        }
    else:
        health["status"] = "degraded"
        health["checks"]["workers"] = {
            "status": "warn",
            "message": "No embedding workers found"
        }

    # Check 4: Vector index exists
    from sqlalchemy import text
    result = db.execute(text("""
        SELECT COUNT(*) FROM pg_indexes
        WHERE indexname = 'idx_embeddings_vector_hnsw'
    """))
    index_exists = result.scalar() > 0

    health["checks"]["vector_index"] = {
        "status": "pass" if index_exists else "warn",
        "exists": index_exists
    }

    return health

# Example response:
# {
#   "status": "healthy",
#   "checks": {
#     "model_loaded": {"status": "pass", "model": "BAAI/bge-m3", "device": "cpu"},
#     "embedding_generation": {"status": "pass", "dimension": 1024},
#     "workers": {"status": "pass", "active_workers": 2},
#     "vector_index": {"status": "pass", "exists": true}
#   }
# }
```

### 8.4 Performance Measurements

#### **Real-Time Performance Dashboard**
```python
# app/api/routes/metrics.py

@router.get("/metrics/embeddings")
async def embedding_metrics(db: Session = Depends(get_db)):
    """Get embedding performance metrics"""

    # Query processing_status table
    recent_tasks = db.query(ProcessingStatus).filter(
        ProcessingStatus.stage == 'EMBEDDING',
        ProcessingStatus.status.in_(['COMPLETED', 'FAILED']),
        ProcessingStatus.completed_at >= datetime.now(timezone.utc) - timedelta(hours=24)
    ).all()

    # Calculate metrics
    total_tasks = len(recent_tasks)
    successful = sum(1 for t in recent_tasks if t.status == 'COMPLETED')
    failed = sum(1 for t in recent_tasks if t.status == 'FAILED')

    processing_times = [t.duration_ms for t in recent_tasks if t.duration_ms]
    avg_time_ms = sum(processing_times) / len(processing_times) if processing_times else 0

    # Calculate embeddings/second
    total_chunks = sum(
        t.result_data.get('chunks_processed', 0)
        for t in recent_tasks
        if t.result_data and t.status == 'COMPLETED'
    )

    total_time_sec = sum(processing_times) / 1000 if processing_times else 1
    avg_speed = total_chunks / total_time_sec if total_time_sec > 0 else 0

    # Database stats
    total_embeddings = db.query(Embedding).filter(
        Embedding.embedding.isnot(None)
    ).count()

    total_documents_embedded = db.query(Embedding.document_id).filter(
        Embedding.embedding.isnot(None)
    ).distinct().count()

    return {
        "time_window": "24h",
        "tasks": {
            "total": total_tasks,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total_tasks if total_tasks > 0 else 0
        },
        "performance": {
            "avg_processing_time_ms": round(avg_time_ms, 2),
            "avg_embeddings_per_second": round(avg_speed, 2),
            "p50_time_ms": sorted(processing_times)[len(processing_times)//2] if processing_times else 0,
            "p95_time_ms": sorted(processing_times)[int(len(processing_times)*0.95)] if processing_times else 0
        },
        "database": {
            "total_embeddings": total_embeddings,
            "total_documents_embedded": total_documents_embedded,
            "avg_chunks_per_document": total_embeddings / total_documents_embedded if total_documents_embedded > 0 else 0
        }
    }
```

---

## 9. SECURITY CONSIDERATIONS

### 9.1 Authentication & Authorization

#### **API Key Validation**
```python
# All embedding endpoints require API key

from app.core.security import require_api_key

@router.post("/documents/{document_id}/embeddings/generate")
async def generate_embeddings_endpoint(
    document_id: UUID,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """Trigger embedding generation (requires API key)"""

    # Verify document belongs to authenticated user/workspace
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")

    # TODO: Add workspace/user ownership check
    # if document.workspace_id != api_key.workspace_id:
    #     raise HTTPException(403, "Access denied")

    # ... trigger embedding generation ...
```

#### **Worker-Level Security**
```python
# Celery workers should NOT expose public endpoints
# All task triggering goes through API layer with auth

# ❌ BAD: Direct task invocation from client
# generate_embeddings.delay(document_id)

# ✅ GOOD: API endpoint with auth → Queue task
@router.post("/documents/{id}/embeddings/generate")
async def trigger_embedding(id: UUID, api_key: str = Depends(require_api_key)):
    generate_embeddings.apply_async(args=[str(id)])
```

### 9.2 Input Sanitization

#### **Prevent SQL Injection**
```python
# ✅ Safe: Use SQLAlchemy ORM (parameterized queries)
chunks = db.query(Embedding).filter(
    Embedding.document_id == doc_uuid,  # Parameterized
    Embedding.embedding.is_(None)
).all()

# ❌ UNSAFE: Raw SQL with string interpolation
# db.execute(f"SELECT * FROM embeddings WHERE document_id = '{doc_id}'")

# ✅ Safe: Use text() with bound parameters
from sqlalchemy import text
db.execute(
    text("SELECT * FROM embeddings WHERE document_id = :doc_id"),
    {"doc_id": str(doc_uuid)}
)
```

#### **Sanitize Chunk Text**
```python
def sanitize_chunk_text(text: str) -> str:
    """Sanitize chunk text before embedding"""

    # Remove null bytes (can cause database errors)
    text = text.replace('\x00', '')

    # Remove other control characters except newlines/tabs
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')

    # Limit length to prevent memory exhaustion
    MAX_LENGTH = 50000  # ~8192 tokens * 6 chars/token
    if len(text) > MAX_LENGTH:
        logger.warning(f"Truncating chunk text from {len(text)} to {MAX_LENGTH} chars")
        text = text[:MAX_LENGTH]

    return text
```

### 9.3 Resource Limits (DoS Prevention)

#### **Rate Limiting**
```python
# Limit concurrent embedding tasks per user/workspace

from app.core.rate_limit import check_rate_limit

@router.post("/documents/{document_id}/embeddings/generate")
async def generate_embeddings_endpoint(
    document_id: UUID,
    api_key: str = Depends(require_api_key)
):
    # Check rate limit
    workspace_id = api_key.workspace_id

    if not check_rate_limit(
        key=f"embedding:{workspace_id}",
        limit=5,  # Max 5 concurrent tasks
        window=300  # Per 5 minutes
    ):
        raise HTTPException(
            status_code=429,
            detail="Too many embedding tasks, please wait"
        )

    # ... proceed with task ...
```

#### **Memory Limits**
```python
# Docker resource limits in docker-compose.yml

services:
  celery-embedding-worker:
    deploy:
      resources:
        limits:
          memory: 6G  # Hard limit: kill worker if exceeded
          cpus: '2.0'
        reservations:
          memory: 4G  # Soft reservation
          cpus: '1.0'
```

#### **Task Timeouts**
```python
# Prevent runaway tasks

@celery_app.task(
    time_limit=1800,  # 30 min hard limit (SIGKILL)
    soft_time_limit=1500,  # 25 min soft limit (exception)
)
def generate_embeddings(self, document_id: str):
    """Task with strict time limits"""

    try:
        # ... processing ...

    except SoftTimeLimitExceeded:
        logger.warning("Task approaching time limit, stopping gracefully")

        # Save progress before termination
        tracker.mark_stage_failed(
            document_id=doc_uuid,
            stage='EMBEDDING',
            error_message="Task timeout"
        )

        # Cleanup
        db.close()
        raise
```

### 9.4 Model Security

#### **Verify Model Integrity**
```python
def verify_model_checksum(model_path: Path):
    """Verify downloaded model hasn't been tampered with"""

    import hashlib

    # Known good checksum for BAAI/bge-m3
    KNOWN_CHECKSUMS = {
        "pytorch_model.bin": "a1b2c3d4e5f6..."  # SHA256 hash
    }

    for file_name, expected_hash in KNOWN_CHECKSUMS.items():
        file_path = model_path / file_name

        if not file_path.exists():
            logger.warning(f"Model file missing: {file_name}")
            continue

        # Calculate SHA256
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)

        actual_hash = sha256.hexdigest()

        if actual_hash != expected_hash:
            raise SecurityError(
                f"Model file checksum mismatch: {file_name}\n"
                f"Expected: {expected_hash}\n"
                f"Got: {actual_hash}"
            )

    logger.info("Model integrity verified")
```

#### **Isolate Model Cache**
```python
# Use dedicated directory with restricted permissions

# docker-compose.yml
volumes:
  - model_cache:/app/models:ro  # Read-only mount for API servers
  - model_cache:/app/models:rw  # Read-write for workers only

# Set permissions
RUN mkdir -p /app/models && \
    chmod 755 /app/models && \
    chown celery:celery /app/models
```

### 9.5 Data Privacy

#### **Embedding Data Sensitivity**
```python
# Embeddings are derived from document content → Sensitive data

# 1. Encrypt database connections
DATABASE_URL = "postgresql://user:pass@host:5432/db?sslmode=require"

# 2. Enable PostgreSQL encryption at rest
# ALTER DATABASE querybox SET ...

# 3. Log sanitization (don't log chunk text)
logger.info(
    "Embedding generated",
    chunk_id=str(chunk.id),
    # chunk_text=chunk.chunk_text,  # ❌ DON'T LOG SENSITIVE TEXT
    chunk_length=len(chunk.chunk_text),  # ✅ Log metadata only
    vector_norm=np.linalg.norm(vector)
)

# 4. Secure deletion
def secure_delete_embeddings(document_id: UUID, db: Session):
    """Permanently delete embeddings (GDPR right to erasure)"""

    # Delete from database (CASCADE handles this)
    db.query(Document).filter(Document.id == document_id).delete()

    # Overwrite in PostgreSQL (vacuum reclaims space)
    db.execute(text("VACUUM FULL embeddings"))

    db.commit()
    logger.info(f"Securely deleted embeddings for document {document_id}")
```

---

## 10. CODE PATTERNS & CONVENTIONS

### 10.1 Design Patterns Used

#### **Singleton Pattern** (Model Manager)
```python
# Ensure only one model instance loaded per worker

class ModelManager:
    """Singleton model manager"""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_model(self):
        """Lazy load model on first access"""
        if self._model is None:
            logger.info("Loading BGE-M3 model (first time)")
            self._model = SentenceTransformer("BAAI/bge-m3")
        return self._model

# Usage
model_manager = ModelManager()
model = model_manager.get_model()  # Loads once, reuses thereafter
```

#### **Strategy Pattern** (Device Selection)
```python
# Choose embedding device based on availability

class DeviceStrategy:
    """Abstract device strategy"""

    def get_device(self) -> str:
        raise NotImplementedError

class CUDAStrategy(DeviceStrategy):
    def get_device(self) -> str:
        import torch
        if torch.cuda.is_available():
            return 'cuda'
        raise RuntimeError("CUDA not available")

class CPUStrategy(DeviceStrategy):
    def get_device(self) -> str:
        return 'cpu'

class AutoStrategy(DeviceStrategy):
    def get_device(self) -> str:
        """Auto-detect best available device"""
        try:
            return CUDAStrategy().get_device()
        except RuntimeError:
            logger.info("CUDA not available, using CPU")
            return CPUStrategy().get_device()

# Usage
device_config = os.getenv("EMBEDDING_DEVICE", "auto")
strategies = {
    "cuda": CUDAStrategy(),
    "cpu": CPUStrategy(),
    "auto": AutoStrategy()
}
device = strategies[device_config].get_device()
```

#### **Repository Pattern** (Database Access)
```python
# Separate data access logic from business logic

class EmbeddingRepository:
    """Data access layer for embeddings"""

    def __init__(self, db: Session):
        self.db = db

    def get_unprocessed_chunks(
        self,
        document_id: UUID,
        limit: int = 100
    ) -> List[Embedding]:
        """Fetch chunks without embeddings"""
        return self.db.query(Embedding).filter(
            Embedding.document_id == document_id,
            Embedding.embedding.is_(None)
        ).order_by(Embedding.chunk_index).limit(limit).all()

    def update_chunk_embedding(
        self,
        chunk_id: UUID,
        vector: List[float],
        model: str
    ):
        """Update single chunk with embedding"""
        self.db.query(Embedding).filter(Embedding.id == chunk_id).update({
            'embedding': vector,
            'embedding_model': model,
            'updated_at': datetime.now(timezone.utc)
        })

    def bulk_update_embeddings(
        self,
        updates: List[Tuple[UUID, List[float]]]
    ):
        """Bulk update multiple chunks"""
        for chunk_id, vector in updates:
            self.update_chunk_embedding(chunk_id, vector, "BAAI/bge-m3")
        self.db.commit()

# Usage in service layer
repo = EmbeddingRepository(db)
chunks = repo.get_unprocessed_chunks(document_id, limit=100)
```

#### **Factory Pattern** (Service Creation)
```python
# Factory for creating embedding services with different configs

class EmbeddingServiceFactory:
    """Factory for embedding services"""

    @staticmethod
    def create_service(model_name: str = "BAAI/bge-m3") -> EmbeddingService:
        """Create embedding service with model"""

        if model_name == "BAAI/bge-m3":
            return BGE_M3EmbeddingService()
        elif model_name == "text-embedding-ada-002":
            return OpenAIEmbeddingService()
        else:
            raise ValueError(f"Unknown model: {model_name}")

class BGE_M3EmbeddingService(EmbeddingService):
    def __init__(self):
        super().__init__(
            model_name="BAAI/bge-m3",
            dimension=1024,
            max_tokens=8192
        )

# Usage
service = EmbeddingServiceFactory.create_service("BAAI/bge-m3")
```

### 10.2 Naming Conventions

#### **Variables**
```python
# snake_case for variables and functions
document_id = UUID("...")
embedding_service = get_embedding_service()
chunks_to_process = []

# UPPER_CASE for constants
MAX_BATCH_SIZE = 100
DEFAULT_MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DIMENSION = 1024
```

#### **Classes**
```python
# PascalCase for classes
class EmbeddingService:
    pass

class ModelManager:
    pass

class BatchProcessor:
    pass
```

#### **Functions**
```python
# Verb-noun format for clarity
def generate_embedding(text: str) -> List[float]:
    pass

def load_model(model_name: str) -> SentenceTransformer:
    pass

def update_chunk_embeddings(chunks: List[Embedding]):
    pass

# Boolean functions start with is_, has_, should_
def is_model_cached() -> bool:
    pass

def has_embeddings(document_id: UUID) -> bool:
    pass
```

### 10.3 Async/Await Patterns

#### **Pattern 1: Sync Celery Tasks**
```python
# Celery tasks are synchronous (not async def)

@celery_app.task
def generate_embeddings(self, document_id: str):  # NOT async def
    """Sync task for Celery"""

    db = SessionLocal()

    try:
        # Sync database operations
        chunks = db.query(Embedding).filter(...).all()

        # Sync embedding generation
        vectors = embedding_service.generate_embeddings_batch(texts)

        db.commit()

    finally:
        db.close()
```

#### **Pattern 2: Async API Endpoints**
```python
# API endpoints can be async

@router.post("/documents/{id}/embeddings/generate")
async def trigger_embedding(
    id: UUID,
    db: AsyncSession = Depends(get_async_db)  # Async DB session
):
    """Async endpoint"""

    # Async database query
    document = await db.execute(
        select(Document).where(Document.id == id)
    )

    # Queue Celery task (sync operation, but fast)
    task = generate_embeddings.apply_async(args=[str(id)])

    return {"task_id": task.id}
```

#### **Pattern 3: Running Async Code in Sync Context**
```python
# When Celery task needs to call async function

def run_async(coro):
    """Helper to run async coroutines in sync context"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)

# Usage in Celery task
@celery_app.task
def generate_embeddings(self, document_id: str):
    # Call async status tracker
    run_async(tracker.update_status(
        document_id=doc_uuid,
        stage='EMBEDDING',
        status='IN_PROGRESS'
    ))
```

### 10.4 Transaction Boundaries

#### **Pattern 1: Single Transaction per Batch**
```python
def process_batch(chunks: List[Embedding], vectors: List[List[float]]):
    """Update batch in single transaction"""

    db = SessionLocal()

    try:
        db.begin()  # Explicit transaction start

        for chunk, vector in zip(chunks, vectors):
            chunk.embedding = vector
            chunk.embedding_model = "BAAI/bge-m3"

        db.commit()  # Commit all or nothing

    except Exception as e:
        db.rollback()  # Rollback entire batch
        raise

    finally:
        db.close()
```

#### **Pattern 2: Nested Transactions (Savepoints)**
```python
def process_document_with_recovery(document_id: UUID):
    """Process with savepoints for partial recovery"""

    db = SessionLocal()

    try:
        # Outer transaction
        db.begin()

        batches = fetch_all_batches(document_id)
        successful_batches = 0

        for batch in batches:
            try:
                # Inner savepoint
                savepoint = db.begin_nested()

                process_batch(batch)

                savepoint.commit()  # Commit savepoint
                successful_batches += 1

            except Exception as e:
                savepoint.rollback()  # Rollback this batch only
                logger.error(f"Batch failed: {e}")

        # Commit outer transaction (all successful batches)
        db.commit()

        return successful_batches

    except Exception as e:
        db.rollback()  # Rollback everything
        raise

    finally:
        db.close()
```

### 10.5 Error Propagation Strategy

#### **Pattern 1: Let Errors Bubble Up**
```python
# Low-level functions raise specific exceptions

def generate_embedding(text: str) -> List[float]:
    """Generate embedding (can raise ValueError, RuntimeError)"""

    if not text or len(text.strip()) == 0:
        raise ValueError("Text cannot be empty")

    try:
        vector = model.encode(text)
        return vector.tolist()
    except RuntimeError as e:
        raise RuntimeError(f"Model encoding failed: {e}")
```

#### **Pattern 2: Catch and Handle at Service Layer**
```python
# Service layer catches and converts to result objects

class ProcessingResult:
    def __init__(self, success: bool, error: str = None):
        self.success = success
        self.error_message = error

def process_chunk_safe(chunk: Embedding) -> ProcessingResult:
    """Process chunk with error handling"""

    try:
        vector = generate_embedding(chunk.chunk_text)
        chunk.embedding = vector
        return ProcessingResult(success=True)

    except ValueError as e:
        logger.warning(f"Validation error for chunk {chunk.id}: {e}")
        return ProcessingResult(success=False, error=str(e))

    except RuntimeError as e:
        logger.error(f"Processing error for chunk {chunk.id}: {e}")
        return ProcessingResult(success=False, error=str(e))
```

#### **Pattern 3: Celery Task Re-raises for Retry**
```python
# Task layer re-raises retryable errors

@celery_app.task(bind=True, max_retries=3)
def generate_embeddings(self, document_id: str):
    """Task with retry logic"""

    try:
        result = embedding_service.process_document(document_id)

        if not result.success:
            # Non-retryable error
            logger.error(f"Processing failed: {result.error_message}")
            return {"success": False, "error": result.error_message}

        return {"success": True}

    except (OperationalError, ConnectionError) as e:
        # Retryable error
        logger.warning(f"Transient error, retrying: {e}")
        raise self.retry(exc=e, countdown=60)

    except Exception as e:
        # Unexpected error, retry anyway
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise self.retry(exc=e)
```

---

## 11. INTEGRATION POINTS

### 11.1 Component Connections

```
┌─────────────────┐
│   FastAPI       │
│   Endpoint      │
└────────┬────────┘
         │
         │ 1. POST /documents/{id}/embeddings/generate
         ▼
┌─────────────────┐
│   Celery        │
│   Queue         │◄──── Redis (broker)
└────────┬────────┘
         │
         │ 2. generate_embeddings.apply_async()
         ▼
┌─────────────────┐
│   Embedding     │
│   Worker        │
└────────┬────────┘
         │
         │ 3. Load BGE-M3 model
         ▼
┌─────────────────┐
│   Model         │
│   Manager       │
└────────┬────────┘
         │
         │ 4. model.encode(texts)
         ▼
┌─────────────────┐
│   Embedding     │
│   Service       │
└────────┬────────┘
         │
         │ 5. Fetch chunks
         ▼
┌─────────────────┐
│   PostgreSQL    │
│   + pgvector    │
└────────┬────────┘
         │
         │ 6. UPDATE embeddings SET embedding = vector
         │
         └──────► Store vectors
```

### 11.2 Database Queries

#### **Query 1: Fetch Unprocessed Chunks**
```sql
SELECT
    id,
    document_id,
    chunk_index,
    chunk_text,
    chunk_tokens
FROM embeddings
WHERE document_id = :document_id
  AND embedding IS NULL
ORDER BY chunk_index
LIMIT 100;

-- Execution plan should use index:
-- Index: idx_embeddings_no_vector (document_id) WHERE embedding IS NULL
```

#### **Query 2: Bulk Update Embeddings**
```sql
UPDATE embeddings
SET
    embedding = :vector_data::vector,
    embedding_model = 'BAAI/bge-m3',
    updated_at = NOW()
WHERE id = ANY(:chunk_ids);

-- For 100 chunks:
-- :chunk_ids = ARRAY['uuid1', 'uuid2', ..., 'uuid100']
```

#### **Query 3: Check Index Exists**
```sql
SELECT COUNT(*)
FROM pg_indexes
WHERE tablename = 'embeddings'
  AND indexname = 'idx_embeddings_vector_hnsw';

-- Result: 0 = index missing, 1 = index exists
```

#### **Query 4: Create HNSW Index**
```sql
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw
ON embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Takes ~10-30 seconds for 10,000 vectors
-- Blocks table (use CREATE INDEX CONCURRENTLY in production)
```

#### **Query 5: Get Document Embedding Status**
```sql
SELECT
    COUNT(*) as total_chunks,
    COUNT(embedding) as chunks_with_embeddings,
    ROUND(100.0 * COUNT(embedding) / NULLIF(COUNT(*), 0), 2) as completion_percentage,
    MAX(embedding_model) as embedding_model
FROM embeddings
WHERE document_id = :document_id;
```

### 11.3 External Services Called

#### **HuggingFace Model Hub**
```python
# Download model on first run

from sentence_transformers import SentenceTransformer

# HTTP request to:
# https://huggingface.co/BAAI/bge-m3/resolve/main/pytorch_model.bin
# https://huggingface.co/BAAI/bge-m3/resolve/main/config.json
# ...

model = SentenceTransformer("BAAI/bge-m3")

# Downloads to:
# ~/.cache/huggingface/hub/models--BAAI--bge-m3/
```

**Network Requirements:**
- Outbound HTTPS (port 443) to `huggingface.co`
- ~1.7GB download on first run
- No ongoing network required after download (model cached locally)

**Offline Support:**
```python
# Pre-download model, then run offline

# Step 1: Download model (online)
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-m3")
model.save("/app/models/bge-m3")

# Step 2: Load from local cache (offline)
model = SentenceTransformer("/app/models/bge-m3", local_files_only=True)
```

### 11.4 Events Published/Consumed

#### **Event 1: Chunking Completed → Trigger Embedding**
```python
# In chunking_tasks.py (publisher)

from app.tasks.embedding_tasks import generate_embeddings

# After chunking completes
if chunking_successful:
    # Chain next task
    generate_embeddings.apply_async(
        args=[str(document_id)],
        countdown=5  # Wait 5 seconds
    )
```

#### **Event 2: Embedding Completed → Trigger Indexing**
```python
# In embedding_tasks.py (publisher)

from app.tasks.indexing_tasks import index_document

# After embedding completes
if embedding_successful:
    # Trigger next stage (future: Step 9.3)
    index_document.apply_async(
        args=[str(document_id)]
    )
```

#### **Event 3: Processing Status Updates**
```python
# Publish status updates for monitoring

from app.services.processing.status_tracker import ProcessingStatusTracker

tracker = ProcessingStatusTracker(db)

# Event: Stage started
await tracker.update_status(
    document_id=doc_uuid,
    stage='EMBEDDING',
    status='IN_PROGRESS'
)

# Event: Stage completed
await tracker.mark_stage_completed(
    document_id=doc_uuid,
    stage='EMBEDDING',
    result_data={
        "chunks_processed": 150,
        "processing_time_ms": 45000
    }
)
```

---

## 12. TROUBLESHOOTING GUIDE

### 12.1 Common Issues and Solutions

#### **Issue 1: Model Download Fails**

**Symptoms:**
```
OSError: Can't load the model for 'BAAI/bge-m3'
ConnectionError: HTTPSConnectionPool(host='huggingface.co', port=443)
```

**Diagnosis:**
```bash
# Check internet connectivity
curl -I https://huggingface.co

# Check firewall rules
telnet huggingface.co 443

# Check proxy settings
echo $HTTP_PROXY
echo $HTTPS_PROXY
```

**Solutions:**

1. **Retry Download:**
```python
# Retry with exponential backoff
for attempt in range(3):
    try:
        model = SentenceTransformer("BAAI/bge-m3")
        break
    except (OSError, ConnectionError) as e:
        if attempt < 2:
            time.sleep(2 ** attempt * 10)
        else:
            raise
```

2. **Manual Download:**
```bash
# Download model files manually
mkdir -p /app/models/bge-m3
cd /app/models/bge-m3

wget https://huggingface.co/BAAI/bge-m3/resolve/main/pytorch_model.bin
wget https://huggingface.co/BAAI/bge-m3/resolve/main/config.json
wget https://huggingface.co/BAAI/bge-m3/resolve/main/tokenizer.json
wget https://huggingface.co/BAAI/bge-m3/resolve/main/tokenizer_config.json

# Load from local path
model = SentenceTransformer("/app/models/bge-m3")
```

3. **Use Different Mirror:**
```python
# Set HuggingFace mirror (for China/blocked regions)
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

---

#### **Issue 2: GPU Out of Memory**

**Symptoms:**
```
RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB
torch.cuda.OutOfMemoryError
```

**Diagnosis:**
```bash
# Check GPU memory usage
nvidia-smi

# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"
```

**Solutions:**

1. **Reduce Batch Size:**
```python
# Reduce internal batch size
vectors = model.encode(
    texts,
    device='cuda',
    batch_size=16  # Reduce from 32 to 16
)
```

2. **Clear GPU Cache:**
```python
import torch

# Clear cache before processing
torch.cuda.empty_cache()

# Process batch
vectors = model.encode(texts, device='cuda')

# Clear cache after
torch.cuda.empty_cache()
```

3. **Fallback to CPU:**
```python
try:
    vectors = model.encode(texts, device='cuda')
except RuntimeError as e:
    if "out of memory" in str(e):
        logger.warning("GPU OOM, falling back to CPU")
        torch.cuda.empty_cache()
        vectors = model.encode(texts, device='cpu')
    else:
        raise
```

4. **Use Mixed Precision:**
```python
# Enable FP16 for smaller memory footprint
model.half()  # Convert to FP16
vectors = model.encode(texts, device='cuda')
```

---

#### **Issue 3: Embeddings Not Appearing in Database**

**Symptoms:**
- Task completes successfully
- No errors in logs
- `SELECT COUNT(*) FROM embeddings WHERE embedding IS NOT NULL` returns 0

**Diagnosis:**
```sql
-- Check if chunks exist
SELECT COUNT(*) FROM embeddings WHERE document_id = :doc_id;

-- Check processing status
SELECT stage, status, error_message
FROM processing_status
WHERE document_id = :doc_id
ORDER BY created_at DESC;

-- Check Celery task result
SELECT * FROM celery_taskmeta WHERE task_id = :task_id;
```

**Solutions:**

1. **Check Transaction Commit:**
```python
# Ensure db.commit() is called
try:
    for chunk, vector in zip(chunks, vectors):
        chunk.embedding = vector

    db.commit()  # ← Don't forget this!

except Exception as e:
    db.rollback()
    raise
```

2. **Check Vector Dimension:**
```python
# Verify vector dimension matches column
assert len(vector) == 1024, f"Invalid dimension: {len(vector)}"

# Check database column
# ALTER TABLE embeddings ALTER COLUMN embedding TYPE vector(1024);
```

3. **Check pgvector Extension:**
```sql
-- Verify pgvector is installed
SELECT * FROM pg_extension WHERE extname = 'vector';

-- If missing:
CREATE EXTENSION vector;
```

---

#### **Issue 4: Slow Embedding Generation**

**Symptoms:**
- Processing 100 chunks takes >2 minutes (expected: <1 min with GPU, <2 min with CPU)
- Worker CPU usage is low (<50%)

**Diagnosis:**
```bash
# Monitor worker performance
celery -A app.celery_app inspect active

# Check worker resource usage
docker stats celery-embedding-worker

# Profile embedding generation
python -m cProfile -o embedding.prof scripts/benchmark_embeddings.py
```

**Solutions:**

1. **Enable GPU Acceleration:**
```bash
# Check GPU available
nvidia-smi

# Update docker-compose.yml
services:
  celery-embedding-worker:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

2. **Optimize Batch Size:**
```python
# Increase internal batch size (if memory allows)
EMBEDDING_INTERNAL_BATCH_SIZE = 64  # Increase from 32
```

3. **Use Faster Model (Trade-off Accuracy):**
```python
# Switch to smaller/faster model
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# Dimension: 384 (vs 1024), Speed: ~2x faster, Accuracy: ~5% lower
```

4. **Add More Workers:**
```bash
# Scale up workers
docker-compose up -d --scale celery-embedding-worker=4
```

---

#### **Issue 5: Vector Index Not Used (Slow Search)**

**Symptoms:**
- Vector similarity queries take >1 second
- EXPLAIN shows sequential scan instead of index scan

**Diagnosis:**
```sql
-- Check if index exists
SELECT * FROM pg_indexes WHERE tablename = 'embeddings';

-- Explain query plan
EXPLAIN ANALYZE
SELECT * FROM embeddings
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 10;

-- Expected: "Index Scan using idx_embeddings_vector_hnsw"
-- Bad: "Seq Scan on embeddings"
```

**Solutions:**

1. **Create Index (If Missing):**
```sql
CREATE INDEX idx_embeddings_vector_hnsw
ON embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

2. **Rebuild Index (If Corrupted):**
```sql
REINDEX INDEX idx_embeddings_vector_hnsw;
```

3. **Increase `probes` for Better Recall:**
```sql
-- Increase search width (at cost of speed)
SET hnsw.ef_search = 100;  -- Default: 40

-- Then run query
SELECT * FROM embeddings
ORDER BY embedding <=> :query_vector
LIMIT 10;
```

4. **Check Index Statistics:**
```sql
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexname = 'idx_embeddings_vector_hnsw';

-- If idx_scan = 0, index is not being used
```

### 12.2 Debug Commands

#### **Check Celery Worker Status**
```bash
# List active workers
celery -A app.celery_app inspect active

# Check worker stats
celery -A app.celery_app inspect stats

# Check registered tasks
celery -A app.celery_app inspect registered

# Monitor tasks in real-time
celery -A app.celery_app events
```

#### **Test Embedding Generation**
```python
# Python shell test
from app.services.embeddings import EmbeddingService

service = EmbeddingService()

# Test single embedding
vector = service.generate_embedding("This is a test")
print(f"Dimension: {len(vector)}, First 5 values: {vector[:5]}")

# Test batch
texts = ["Test 1", "Test 2", "Test 3"]
vectors = service.generate_embeddings_batch(texts)
print(f"Generated {len(vectors)} vectors")
```

#### **Check Database State**
```sql
-- Count embeddings by status
SELECT
    embedding IS NULL as missing_embedding,
    COUNT(*) as chunk_count
FROM embeddings
GROUP BY (embedding IS NULL);

-- List documents by embedding progress
SELECT
    d.id,
    d.original_name,
    COUNT(e.id) as total_chunks,
    COUNT(e.embedding) as embedded_chunks,
    ROUND(100.0 * COUNT(e.embedding) / NULLIF(COUNT(e.id), 0), 2) as percent_complete
FROM documents d
LEFT JOIN embeddings e ON d.id = e.document_id
GROUP BY d.id, d.original_name
ORDER BY percent_complete ASC;
```

#### **Test Vector Search**
```sql
-- Test similarity search with dummy vector
WITH test_query AS (
    SELECT ARRAY(
        SELECT random() FROM generate_series(1, 1024)
    )::vector as query_vector
)
SELECT
    e.id,
    LEFT(e.chunk_text, 50),
    1 - (e.embedding <=> t.query_vector) as similarity
FROM embeddings e, test_query t
WHERE e.embedding IS NOT NULL
ORDER BY e.embedding <=> t.query_vector
LIMIT 5;
```

### 12.3 Log Locations

```
/app/logs/
├── app.log              # General application logs
├── embeddings.log       # Embedding-specific logs
├── celery.log           # Celery worker logs
├── celery-beat.log      # Celery scheduler logs (if used)
└── error.log            # Error-only logs

# Docker logs
docker logs querybox-celery-embedding-worker

# Follow logs in real-time
tail -f /app/logs/embeddings.log

# Filter for specific document
grep "550e8400-e29b-41d4-a716-446655440000" /app/logs/embeddings.log

# Search for errors
grep -i "error\|exception\|failed" /app/logs/embeddings.log
```

---

## APPENDIX

### A. Quick Reference

**Key Files:**
- `app/services/embeddings/embedding_service.py` - Core embedding logic
- `app/tasks/embedding_tasks.py` - Celery async tasks
- `app/models/embedding.py` - Database model
- `app/core/config.py` - Configuration settings

**Key Commands:**
```bash
# Start embedding worker
celery -A app.celery_app worker --queues=embeddings

# Trigger embedding
curl -X POST http://localhost:8000/api/v1/documents/{id}/embeddings/generate

# Check status
curl http://localhost:8000/api/v1/documents/{id}/embeddings/status

# Monitor logs
tail -f /app/logs/embeddings.log
```

**Performance Targets:**
- CPU: >1.0 embeddings/second
- GPU: >3.0 embeddings/second
- Batch (100 chunks, CPU): <100 seconds
- Vector search (p99): <200ms

### B. Related Documentation

- [Step 9.0: pgvector Setup](./step9.0_pgvector_setup.md)
- [Step 9.1: Chunking Improvements](./step9.1_chunking_improvements.md)
- [Step 9.3: Vector Similarity Search](./step9.3_vector_similarity_search.md)
- [Celery Setup Guide](../celery/CELERY_SETUP_COMPLETE.md)

### C. External Resources

- [BGE-M3 Model Card](https://huggingface.co/BAAI/bge-m3)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [sentence-transformers Library](https://www.sbert.net/)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html)

---

**Last Updated:** October 25, 2024
**Version:** 1.0
**Status:** Ready for Implementation
