# Phase 4: Vector Store Optimization - Qdrant Integration

**Author**: QueryBox Backend Team
**Date**: January 2025
**Status**: Implementation Guide
**Related**: Step 13.7, dev/active/querybox-backend/plan.md

---

## 1. GOAL & ARCHITECTURE

### Objective
Achieve 10x performance improvement in vector similarity search (500ms → 50ms p95 latency) by adding Qdrant as a specialized vector search layer alongside PostgreSQL pgvector, while maintaining zero risk through an "augment, don't replace" architecture strategy.

### Why This Approach
Current pgvector implementation (~500ms latency) becomes a bottleneck at scale and will be exacerbated by Phase 5 Multi-Query RAG (3x search calls). PostgreSQL is optimized for relational operations, not pure vector similarity search. Qdrant provides:
- Rust-based HNSW implementation (10x faster than pgvector)
- Optimized memory layout for vector operations
- Sub-50ms search at million-vector scale
- Free tier (300K vectors) + affordable self-hosting

### System Design Patterns

**Primary Pattern: Repository Pattern with Strategy**
- `VectorStore` abstract base class defines interface
- `PgVectorStore` and `QdrantStore` implement concrete strategies
- Factory pattern (`get_vector_store()`) selects provider based on configuration
- Allows runtime switching without code changes

**Secondary Pattern: Circuit Breaker**
- Health checks before Qdrant operations
- Automatic fallback to pgvector if Qdrant unavailable
- Prevents cascading failures

### Component Boundaries

```
┌─────────────────────────────────────────┐
│       VectorSearchService               │
│  (Consumer - business logic layer)      │
└─────────────┬───────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────┐
│     get_vector_store() Factory          │
│  (Configuration-based routing)          │
└─────┬───────────────────────────────────┘
      │
      ├──────────────┬────────────────────┐
      ↓              ↓                    ↓
┌─────────────┐ ┌──────────────┐ ┌──────────────┐
│ PgVector    │ │ QdrantStore  │ │ Future:      │
│ Store       │ │ (Rust HNSW)  │ │ LanceDB,     │
│ (Postgres)  │ │              │ │ Weaviate...  │
└─────────────┘ └──────────────┘ └──────────────┘
```

### Data Flow Architecture

**Indexing Flow (Write Path)**:
```
Document Upload → Extraction → Chunking → Embedding Generation
                                               ↓
                              ┌────────────────┴────────────────┐
                              ↓                                 ↓
                    PostgreSQL (Always)              Qdrant (If enabled)
                    - Full metadata                  - Vector + minimal payload
                    - Relations                      - chunk_id, document_id
                    - ACID guarantees                - text snippet (200 chars)
                    - Source of truth                - Fast HNSW index
```

**Search Flow (Read Path)**:
```
User Query → Embedding Generation → Search Routing
                                         ↓
                            ┌────────────┴────────────┐
                            ↓                         ↓
                    Qdrant Search              Fallback: pgvector
                    (if available)             (if Qdrant down)
                            ↓                         ↓
                    Chunk IDs (ranked) ───────────────┘
                            ↓
                    Enrich from PostgreSQL
                    (full metadata, relations)
                            ↓
                    Return to user
```

---

## 2. IMPLEMENTATION

### Files to Create

**1. `backend/app/services/search/vector_stores/qdrant_store.py`** (300 lines)
- Purpose: Qdrant implementation of VectorStore interface
- Implements: index(), search(), delete(), health_check(), get_stats()
- Manages: Qdrant client lifecycle, collection schema, batch operations

**2. `backend/scripts/migrate_to_qdrant.py`** (200 lines)
- Purpose: One-time migration of existing embeddings from PostgreSQL to Qdrant
- Features: Batch processing, progress tracking, idempotency, validation

**3. `backend/app/core/config.py`** (additions)
- Purpose: Qdrant configuration settings
- Adds: QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION, ENABLE_QDRANT, VECTOR_STORE

**4. `backend/tests/integration/test_qdrant_integration.py`** (250 lines)
- Purpose: Integration tests for Qdrant operations
- Coverage: Indexing, search, fallback, performance benchmarks

### Core Classes and Signatures

```python
class QdrantStore(VectorStore):
    """Qdrant vector store implementation with HNSW indexing"""

    def __init__(
        self,
        url: str,
        api_key: Optional[str],
        collection_name: str,
        dimension: int,
        distance: str = "Cosine"
    ):
        """Initialize Qdrant client and ensure collection exists"""

    def index(
        self,
        vectors: List[List[float]],
        metadata: List[Dict[str, Any]],
        ids: List[str]
    ) -> IndexResult:
        """
        Batch index vectors with metadata
        Time Complexity: O(n * log(m)) where n=batch_size, m=total_vectors
        Space Complexity: O(n) for batch buffer
        """

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Fast HNSW search with optional metadata filtering
        Time Complexity: O(log(n)) average case with HNSW
        Space Complexity: O(k) for results
        """

    def delete(self, ids: List[str]) -> bool:
        """Delete vectors by IDs (soft delete support)"""

    def health_check(self) -> HealthStatus:
        """Check Qdrant availability with timeout"""
```

### Database Schema Changes

**No schema changes required** - Qdrant operates independently. PostgreSQL schema remains unchanged, maintaining backward compatibility.

### Critical Algorithms

**1. Batch Indexing with Backpressure**
```python
def _batch_index(self, vectors, metadata, ids, batch_size=500):
    """
    Index vectors in batches with exponential backoff retry
    Complexity: O(n) where n = total vectors
    Memory: O(batch_size) - constant memory usage
    """
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i+batch_size]
        retry_count = 0
        while retry_count < 3:
            try:
                self.client.upsert(collection_name, batch)
                break
            except Exception:
                wait = 2 ** retry_count  # Exponential backoff
                time.sleep(wait)
                retry_count += 1
```

**2. Search with Circuit Breaker**
```python
def search_with_fallback(self, query_vector, top_k):
    """
    Try Qdrant first, fallback to pgvector if unavailable
    Complexity: O(log(n)) with HNSW, O(n) fallback with pgvector
    """
    if self._circuit_breaker.is_open():
        return self.pgvector_store.search(query_vector, top_k)

    try:
        results = self.qdrant_store.search(query_vector, top_k)
        self._circuit_breaker.record_success()
        return results
    except Exception as e:
        self._circuit_breaker.record_failure()
        logger.warning(f"Qdrant search failed, falling back: {e}")
        return self.pgvector_store.search(query_vector, top_k)
```

---

## 3. SECURITY & VALIDATION

### Input Sanitization
- **Vector dimension validation**: Reject vectors not matching collection dimension (1024 for BGE-M3, 3072 for OpenAI)
- **Metadata sanitization**: Escape special characters in text snippets before indexing
- **ID validation**: UUID format validation, prevent injection via chunk IDs
- **Query limits**: Cap `top_k` parameter (max 100) to prevent DoS via expensive queries

### Authentication/Authorization
- **API key protection**: Qdrant API keys stored in environment variables, never in code
- **TLS enforcement**: Use HTTPS for Qdrant Cloud connections (wss:// for gRPC)
- **Network isolation**: Self-hosted Qdrant runs in Docker network, not exposed to public internet
- **Client-level auth**: Each VectorSearchService instance validates client_id before queries

### Rate Limiting
- **Not applicable at this layer** - Rate limiting handled by API gateway (FastAPI middleware)
- **Circuit breaker serves as throttle**: Automatically disables Qdrant after 5 consecutive failures (30s cooldown)

### Data Protection
- **Minimal payload strategy**: Only store chunk_id, document_id, and 200-char text snippet in Qdrant
- **Full data in PostgreSQL**: Sensitive metadata remains in PostgreSQL (GDPR/compliance boundary)
- **No PII in vectors**: Embeddings are numerical representations, not raw text
- **Deletion propagation**: When document deleted from PostgreSQL, also deleted from Qdrant (GDPR right to deletion)

---

## 4. PERFORMANCE DECISIONS

### Caching Strategy
- **No vector caching**: Vectors are already pre-computed and stored (caching would be redundant)
- **Connection pooling**: Single long-lived Qdrant client per application instance (connection reuse)
- **Collection schema caching**: Schema fetched once at startup, cached in memory
- **Query result caching disabled initially**: Adds complexity, premature optimization (revisit in Phase 6)

### Query Optimization
- **HNSW index parameters**:
  - `m=16`: Connections per layer (balance between speed and accuracy)
  - `ef_construct=100`: Construction-time search depth (high quality index)
  - `ef_search=64`: Runtime search depth (configurable per query)
  - Rationale: Standard Qdrant recommendations for 1M+ vectors
- **Metadata filtering**: Use Qdrant's payload filtering (pushed to index level, not post-filter)
- **Batch operations**: Index in batches of 500 (optimal for network latency vs memory)

### Async vs Sync Trade-offs
- **Sync indexing initially**: Simpler implementation, writes are already async (Celery tasks)
- **Async search considered**: Would require FastAPI async routes - deferred to avoid complexity
- **Background sync option**: Flag-controlled (QDRANT_ASYNC_SYNC=true) for production tuning

### Resource Limits
- **Max batch size**: 500 vectors (prevent OOM in Qdrant)
- **Connection timeout**: 5s (fail fast if Qdrant unresponsive)
- **Search timeout**: 2s (prevent slow queries blocking API)
- **Circuit breaker**: Open after 5 failures, 30s cooldown (prevent thundering herd)
- **Max top_k**: 100 results (prevent expensive ranking operations)

---

## 5. ERROR HANDLING

### Failure Scenarios Covered

**1. Qdrant Unavailable (503)**
- Trigger: Service down, network partition, DNS failure
- Handling: Circuit breaker opens → automatic fallback to pgvector
- User impact: Transparent (search continues, slightly slower)
- Logging: `ERROR: Qdrant unreachable, fallback to pgvector (search_id={id})`

**2. Collection Missing (404)**
- Trigger: Collection deleted, wrong collection name
- Handling: Auto-create collection with correct schema → retry operation
- User impact: First query delayed ~200ms (one-time), then normal
- Logging: `WARNING: Collection not found, creating: {collection_name}`

**3. Dimension Mismatch (400)**
- Trigger: Embedding model changed (e.g., BGE-M3 → OpenAI), config drift
- Handling: Reject indexing request, log error, alert admin
- User impact: Document processing fails (visible in processing_status table)
- Logging: `ERROR: Vector dimension mismatch: expected {expected}, got {actual}`

**4. Quota Exceeded (429)**
- Trigger: Qdrant Cloud free tier limit (300K vectors) reached
- Handling: Disable Qdrant writes, continue using existing data, alert admin
- User impact: New documents not searchable via Qdrant (pgvector fallback works)
- Logging: `CRITICAL: Qdrant quota exceeded, disabling writes`

### Retry Logic

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    reraise=True
)
def _index_with_retry(self, batch):
    """Exponential backoff: 2s → 4s → 8s"""
    return self.client.upsert(self.collection_name, batch)
```

### Rollback Procedures

**Scenario: Migration fails halfway**
1. Migration script tracks last successfully indexed batch (checkpoint file)
2. Re-run script → resumes from checkpoint (idempotent upsert)
3. Validate: `COUNT(*) FROM embeddings` == Qdrant collection size

**Scenario: Performance regression after Qdrant deployment**
1. Set `VECTOR_STORE=pgvector` in .env (instant rollback)
2. Restart application (picks up new config)
3. All searches route to pgvector (Qdrant untouched)
4. Investigate Qdrant issue offline, re-enable when fixed

### Logging Strategy

**Log Levels**:
- `DEBUG`: Individual vector operations (disabled in production)
- `INFO`: Batch indexing progress, search routing decisions
- `WARNING`: Fallback triggered, degraded performance
- `ERROR`: Operation failures, invalid input
- `CRITICAL`: Service unavailable, quota exceeded, data corruption

**Structured Logging** (JSON format):
```json
{
  "timestamp": "2025-01-13T10:30:45Z",
  "level": "WARNING",
  "service": "qdrant_store",
  "event": "fallback_triggered",
  "qdrant_error": "ConnectionTimeout",
  "fallback_latency_ms": 487,
  "search_id": "abc-123-def"
}
```

---

## 6. CONFIGURATION

### Environment Variables

```bash
# Qdrant Connection
QDRANT_URL=http://localhost:6333          # Or https://xyz.cloud.qdrant.io
QDRANT_API_KEY=                           # Optional for local, required for cloud
QDRANT_COLLECTION=querybox_embeddings     # Collection name

# Feature Flags
ENABLE_QDRANT=true                        # Master switch (disable for instant rollback)
VECTOR_STORE=qdrant                       # Options: pgvector, qdrant (routing decision)

# Performance Tuning
QDRANT_BATCH_SIZE=500                     # Vectors per batch (100-1000)
QDRANT_TIMEOUT=5                          # Connection timeout (seconds)
QDRANT_SEARCH_TIMEOUT=2                   # Search operation timeout (seconds)
QDRANT_ASYNC_SYNC=false                   # Async indexing (future optimization)

# Circuit Breaker
QDRANT_CIRCUIT_FAILURE_THRESHOLD=5        # Consecutive failures before opening
QDRANT_CIRCUIT_COOLDOWN=30                # Seconds before retry after open
```

### Default Values and Rationale

- **QDRANT_BATCH_SIZE=500**: Balance between network round-trips (fewer batches) and memory usage (smaller batches). Empirically tested optimal value.
- **QDRANT_TIMEOUT=5s**: Fail fast if Qdrant down (prevents API blocking). Most operations complete <100ms.
- **VECTOR_STORE=qdrant**: Default to fast path when Qdrant enabled. Override to `pgvector` for debugging.
- **QDRANT_CIRCUIT_FAILURE_THRESHOLD=5**: Tolerate transient failures (network blips), but prevent sustained hammering.

### Feature Flags

**Gradual Rollout Pattern**:
```python
# Phase 1: Enable for internal testing only
ENABLE_QDRANT=true
QDRANT_ROLLOUT_PERCENTAGE=0  # 0% of prod traffic

# Phase 2: Canary deployment (10% traffic)
QDRANT_ROLLOUT_PERCENTAGE=10

# Phase 3: Full rollout
QDRANT_ROLLOUT_PERCENTAGE=100

# Emergency rollback
VECTOR_STORE=pgvector  # Instant switch, zero downtime
```

### Resource Limits

- **Qdrant Cloud Free Tier**: 1GB (~300K vectors with 1024-dim BGE-M3)
- **Self-hosted**: 4GB RAM recommended (handles 1M vectors comfortably)
- **Disk**: 2GB for 1M vectors (includes HNSW index overhead)

---

## 7. INTEGRATION DETAILS

### Connection to Existing Services

**VectorSearchService Integration**:
```python
# Before (pgvector only)
self.vector_store = PgVectorStore(db=db, dimension=1024)

# After (factory pattern with Qdrant support)
self.vector_store = get_vector_store(
    store_name=settings.VECTOR_STORE,  # "qdrant" or "pgvector"
    db=db,
    dimension=1024
)
```

**HybridSearchService** (no changes required):
- Uses `VectorSearchService` abstraction
- Unaware of underlying vector store implementation
- Calls remain identical: `vector_service.search(query_vector, top_k=10)`

### API Contracts

**VectorStore Interface** (already defined in Phase 1):
```python
class VectorStore(ABC):
    @abstractmethod
    def index(self, vectors, metadata, ids) -> IndexResult:
        """Index vectors with metadata"""

    @abstractmethod
    def search(self, query_vector, top_k, filters) -> List[SearchResult]:
        """Similarity search with optional filtering"""

    @abstractmethod
    def delete(self, ids) -> bool:
        """Delete vectors by IDs"""

    @abstractmethod
    def health_check(self) -> HealthStatus:
        """Check service availability"""
```

**QdrantStore** implements this contract exactly (no breaking changes to consumers).

### Event Publishing/Consuming

**Indexing Events** (future enhancement, not MVP):
```python
# When document embedded, publish event
event_bus.publish("document.embedded", {
    "document_id": doc_id,
    "chunk_count": len(chunks),
    "timestamp": datetime.utcnow()
})

# Qdrant sync service consumes event (async indexing)
@event_bus.subscribe("document.embedded")
async def sync_to_qdrant(event_data):
    # Fetch embeddings from PostgreSQL
    # Index in Qdrant
    pass
```

### Database Transactions

**Write Path** (dual indexing):
```python
with db.begin():  # PostgreSQL transaction
    # 1. Save embeddings to PostgreSQL (ACID guaranteed)
    db.add_all(embedding_records)
    db.commit()

    # 2. Sync to Qdrant (best-effort, no transaction)
    if settings.ENABLE_QDRANT:
        try:
            qdrant_store.index(vectors, metadata, ids)
        except Exception as e:
            logger.warning(f"Qdrant sync failed: {e}")
            # PostgreSQL commit still succeeds (eventual consistency)
```

**Read Path** (no transactions needed):
- Read-only operations
- No cross-store consistency requirements (Qdrant returns chunk IDs, PostgreSQL enriches)

---

## 8. TESTING APPROACH

### Unit Tests

**Example: Test QdrantStore Initialization**
```python
def test_qdrant_store_creates_collection_if_missing():
    """Verify collection auto-creation with correct schema"""
    mock_client = Mock()
    mock_client.get_collection.side_effect = NotFoundException()

    store = QdrantStore(
        url="http://localhost:6333",
        api_key=None,
        collection_name="test_collection",
        dimension=1024
    )

    # Assert create_collection called with correct params
    mock_client.create_collection.assert_called_once()
    call_args = mock_client.create_collection.call_args
    assert call_args.kwargs["vectors_config"].size == 1024
    assert call_args.kwargs["vectors_config"].distance == Distance.COSINE
```

### Integration Tests

**Setup**:
```python
@pytest.fixture(scope="module")
def qdrant_store():
    """Real Qdrant instance (Docker required)"""
    # Start Qdrant container
    subprocess.run(["docker", "run", "-d", "-p", "6333:6333", "qdrant/qdrant"])
    time.sleep(2)  # Wait for startup

    store = QdrantStore(
        url="http://localhost:6333",
        collection_name="test_collection",
        dimension=1024
    )

    yield store

    # Cleanup
    store.client.delete_collection("test_collection")
```

**Test: Full Index and Search Flow**
```python
def test_index_and_search_e2e(qdrant_store):
    """Verify vectors can be indexed and retrieved"""
    # Index 100 random vectors
    vectors = [np.random.rand(1024).tolist() for _ in range(100)]
    ids = [str(uuid4()) for _ in range(100)]
    metadata = [{"text": f"chunk_{i}"} for i in range(100)]

    result = qdrant_store.index(vectors, metadata, ids)
    assert result.success is True
    assert result.indexed_count == 100

    # Search with first vector (should return itself as top result)
    results = qdrant_store.search(vectors[0], top_k=5)
    assert len(results) == 5
    assert results[0].id == ids[0]  # Exact match
    assert results[0].score > 0.99  # Near-perfect similarity
```

### Performance Benchmarks

**Latency Test** (expect <50ms p95):
```python
def test_search_latency_under_50ms():
    """Verify search meets performance target"""
    latencies = []

    for _ in range(100):
        query_vector = np.random.rand(1024).tolist()
        start = time.perf_counter()
        results = qdrant_store.search(query_vector, top_k=10)
        latency_ms = (time.perf_counter() - start) * 1000
        latencies.append(latency_ms)

    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)

    assert p95 < 50, f"p95 latency {p95}ms exceeds 50ms target"
    print(f"Latency: p50={p50:.1f}ms, p95={p95:.1f}ms, p99={p99:.1f}ms")
```

### Manual Verification Steps

1. **Verify Qdrant Running**: `curl http://localhost:6333/health` → `{"status":"ok"}`
2. **Check Collection Exists**: `curl http://localhost:6333/collections` → See "querybox_embeddings"
3. **Run Migration Script**: `python backend/scripts/migrate_to_qdrant.py` → Progress bars, final validation
4. **Test Search via API**: `POST /api/v1/search/semantic` → Response <100ms
5. **Verify Fallback**: Stop Qdrant container → Search still works (slower, uses pgvector)

---

## 9. MONITORING

### Metrics Collected

**Vector Store Metrics** (Prometheus format):
```python
# Search performance
qdrant_search_latency_ms = Histogram("qdrant_search_latency_ms", buckets=[10, 25, 50, 100, 250, 500])
qdrant_search_total = Counter("qdrant_search_total", labels=["status"])  # success, fallback, error

# Indexing throughput
qdrant_index_batch_size = Histogram("qdrant_index_batch_size", buckets=[100, 250, 500, 1000])
qdrant_index_duration_ms = Histogram("qdrant_index_duration_ms", buckets=[100, 500, 1000, 5000])

# Health
qdrant_available = Gauge("qdrant_available")  # 1=up, 0=down
qdrant_circuit_breaker_state = Gauge("qdrant_circuit_breaker_state")  # 0=closed, 1=open
```

### Log Entries Added

**Search Routing Decision**:
```python
logger.info(
    "Vector search routed",
    extra={
        "provider": "qdrant",  # or "pgvector"
        "latency_ms": 42,
        "results_count": 10,
        "search_id": request_id
    }
)
```

**Fallback Triggered**:
```python
logger.warning(
    "Qdrant fallback triggered",
    extra={
        "reason": "ConnectionTimeout",
        "fallback_latency_ms": 487,
        "qdrant_failures_count": 3
    }
)
```

### Health Check Endpoints

**New Endpoint**: `GET /api/v1/vector-store/health`
```json
{
  "status": "healthy",
  "provider": "qdrant",
  "qdrant": {
    "available": true,
    "latency_ms": 12,
    "collection": "querybox_embeddings",
    "vector_count": 245678
  },
  "pgvector": {
    "available": true,
    "vector_count": 245678
  },
  "in_sync": true
}
```

### Alert Thresholds

**Critical Alerts**:
- Qdrant unavailable >5 minutes → Page on-call
- Sync lag >1000 vectors → Alert admin (data inconsistency)
- p95 latency >200ms for 10 minutes → Investigate performance

**Warning Alerts**:
- Circuit breaker opened → Monitor for recovery
- Fallback usage >50% of requests → Check Qdrant health
- Qdrant quota >80% → Plan migration to self-hosted

---

## 10. CODE SNIPPETS

### Main Class Structure

```python
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.services.search.vector_stores.base import VectorStore, SearchResult

class QdrantStore(VectorStore):
    """
    Qdrant vector store implementation with HNSW indexing

    Provides 10x faster vector similarity search compared to pgvector
    through Rust-based HNSW index and optimized memory layout.
    """

    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        collection_name: str = "querybox_embeddings",
        dimension: int = 1024,
        distance: str = "Cosine"
    ):
        self.client = QdrantClient(
            url=url,
            api_key=api_key,
            timeout=5
        )
        self.collection_name = collection_name
        self.dimension = dimension

        # Ensure collection exists with correct schema
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.dimension,
                    distance=Distance.COSINE
                )
            )
```

### Critical Function: Batch Indexing

```python
def index(
    self,
    vectors: List[List[float]],
    metadata: List[Dict[str, Any]],
    ids: List[str]
) -> IndexResult:
    """
    Index vectors in batches with retry logic

    Args:
        vectors: List of embedding vectors (dimension must match collection)
        metadata: List of metadata dicts (chunk_id, document_id, text snippet)
        ids: List of unique identifiers (UUIDs as strings)

    Returns:
        IndexResult with success status and count

    Raises:
        ValueError: If dimension mismatch or length mismatch
        QdrantException: If indexing fails after retries
    """
    # Validation
    if len(vectors) != len(metadata) != len(ids):
        raise ValueError("Vectors, metadata, and ids must have same length")

    if len(vectors[0]) != self.dimension:
        raise ValueError(f"Vector dimension {len(vectors[0])} != {self.dimension}")

    # Batch indexing with progress tracking
    batch_size = 500
    indexed_count = 0

    for i in range(0, len(vectors), batch_size):
        batch_vectors = vectors[i:i+batch_size]
        batch_metadata = metadata[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]

        # Prepare points for Qdrant
        points = [
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "chunk_id": meta["chunk_id"],
                    "document_id": meta["document_id"],
                    "text": meta.get("text", "")[:200],  # Limit to 200 chars
                    "chunk_index": meta.get("chunk_index", 0)
                }
            )
            for point_id, vector, meta in zip(batch_ids, batch_vectors, batch_metadata)
        ]

        # Upsert with retry
        self._upsert_with_retry(points)
        indexed_count += len(points)

        # Progress logging
        if indexed_count % 1000 == 0:
            logger.info(f"Indexed {indexed_count}/{len(vectors)} vectors")

    return IndexResult(success=True, indexed_count=indexed_count)
```

### Error Handling Pattern

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from qdrant_client.http.exceptions import UnexpectedResponse

class CircuitBreaker:
    """Simple circuit breaker for Qdrant operations"""

    def __init__(self, failure_threshold=5, cooldown_seconds=30):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self._state = "closed"  # closed, open, half_open

    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)"""
        if self._state == "closed":
            return False

        # Check if cooldown expired
        if time.time() - self.last_failure_time > self.cooldown_seconds:
            self._state = "half_open"  # Try one request
            return False

        return True

    def record_success(self):
        """Reset failure count on successful request"""
        self.failure_count = 0
        self._state = "closed"

    def record_failure(self):
        """Increment failure count, open circuit if threshold exceeded"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    reraise=True
)
def _upsert_with_retry(self, points):
    """Upsert points with exponential backoff retry"""
    try:
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    except UnexpectedResponse as e:
        logger.error(f"Qdrant upsert failed: {e}")
        raise
```

### Test Example

```python
import pytest
from unittest.mock import Mock, patch
from app.services.search.vector_stores.qdrant_store import QdrantStore

class TestQdrantStoreIntegration:
    """Integration tests for QdrantStore (requires running Qdrant)"""

    @pytest.fixture
    def qdrant_store(self):
        """Real Qdrant connection (Docker required)"""
        return QdrantStore(
            url="http://localhost:6333",
            collection_name="test_collection",
            dimension=1024
        )

    def test_index_and_search_correctness(self, qdrant_store):
        """
        Verify indexed vectors can be retrieved with correct ranking

        Test scenario:
        1. Index 10 vectors
        2. Search with query vector similar to vector #5
        3. Verify vector #5 is in top-3 results
        """
        # Generate test data
        base_vector = np.random.rand(1024)
        vectors = []
        for i in range(10):
            if i == 5:
                # Make vector #5 very similar to base
                vector = base_vector + np.random.rand(1024) * 0.01
            else:
                vector = np.random.rand(1024)
            vectors.append(vector.tolist())

        ids = [f"vec_{i}" for i in range(10)]
        metadata = [{"chunk_id": f"chunk_{i}", "document_id": "doc_1"} for i in range(10)]

        # Index
        result = qdrant_store.index(vectors, metadata, ids)
        assert result.success is True

        # Search with base vector (should find vector #5 in top results)
        results = qdrant_store.search(base_vector.tolist(), top_k=3)

        result_ids = [r.id for r in results]
        assert "vec_5" in result_ids, "Similar vector not found in top-3 results"

        # Verify similarity score is high
        vec_5_result = next(r for r in results if r.id == "vec_5")
        assert vec_5_result.score > 0.95, f"Similarity score {vec_5_result.score} too low"

    def test_fallback_on_connection_error(self):
        """Verify fallback to pgvector when Qdrant unavailable"""
        qdrant_store = QdrantStore(url="http://invalid:9999")  # Unreachable
        pgvector_store = Mock()
        pgvector_store.search.return_value = [Mock(id="fallback_result")]

        # Search with fallback logic
        with patch.object(qdrant_store, 'pgvector_fallback', pgvector_store):
            results = qdrant_store.search_with_fallback([0.1] * 1024, top_k=5)

        # Verify fallback was used
        pgvector_store.search.assert_called_once()
        assert results[0].id == "fallback_result"
```

---

## Summary

This implementation guide provides a complete blueprint for Phase 4 Vector Store Optimization. Key takeaways:

1. **Zero-risk architecture**: PostgreSQL remains unchanged, Qdrant is additive
2. **10x performance**: Rust-based HNSW delivers <50ms search vs 500ms pgvector
3. **Production-ready**: Circuit breaker, retry logic, comprehensive error handling
4. **Observable**: Metrics, structured logging, health checks at every layer
5. **Testable**: Unit tests, integration tests, performance benchmarks included

Implementation time: 6-7 hours. Expected results: Immediate 10x search speedup, foundation for Phase 5 Multi-Query RAG.
