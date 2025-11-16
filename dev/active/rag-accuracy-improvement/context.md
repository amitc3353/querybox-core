# RAG Accuracy Improvement - Context & Architecture

## 🏗️ System Architecture Overview

### Current RAG Pipeline
```
Document Upload
    ↓
[Document Processing]
    ├── Docling Parser (primary)
    ├── OCR Fallback (scanned PDFs)
    └── Vision API (charts/graphs)
    ↓
[Chunking Service]
    ├── Token-based chunking (512 tokens, 50 overlap)
    ├── Metadata extraction (10 types)
    └── Quality scoring
    ↓
[Embedding Service]
    ├── BGE-M3 (1024 dims, 8192 context)
    ├── Redis caching (30min TTL)
    └── Batch processing
    ↓
[Vector Store]
    ├── pgvector (primary)
    └── Qdrant (optional, circuit breaker)
    ↓
[Search Service]
    ├── Hybrid Search (BM25 + Vector)
    ├── Multi-Query RAG (LLM expansion)
    ├── RRF Fusion
    ├── Cross-Encoder Reranking
    ├── MMR Diversification
    └── Semantic Deduplication
    ↓
[LLM Generation]
    ├── OpenRouter (GPT-4o-mini default)
    └── Citation extraction
    ↓
[Verification]
    ├── Chain-of-Verification
    ├── Quote matching
    ├── Hallucination detection
    └── Confidence scoring
```

---

## 📁 Key Files & Components

### Document Processing
- **`backend/app/services/document_processing/processor.py`**
  - Main document processing orchestrator
  - Smart router for format detection
  - Vision API integration

- **`backend/app/services/parsing/docling_parser.py`**
  - Docling-based parsing with OCR fallback
  - Multi-format support (PDF, DOCX, PPTX, HTML, MD)

- **`backend/app/services/vision/vision_service.py`**
  - GPT-4o-mini for chart/graph interpretation
  - Cost-aware processing ($0.10 max per document)

### Chunking
- **`backend/app/services/chunking/chunking_service.py`**
  - Token-based semantic chunking
  - Sentence boundary preservation (spaCy/NLTK)
  - Metadata extraction (10 element types)
  - Quality scoring (token distribution, semantic density)

- **`backend/app/schemas/chunk.py`**
  - Chunk data models
  - ChunkMetadata schema (rich metadata)

### Embeddings
- **`backend/app/services/embeddings.py`**
  - BGE-M3 embedding provider
  - Batch processing (100 chunks at a time)
  - Redis caching
  - Provider abstraction (BGE-M3, OpenAI, HuggingFace)

- **`backend/app/core/config.py`**
  - Embedding configuration
  - Model settings (BGE_M3_MODEL_NAME, dimensions, max_length)

### Search & Retrieval
- **`backend/app/services/search/search_service.py`**
  - Unified search orchestrator
  - Multi-strategy support (hybrid, vector, keyword)
  - 3-stage reranking pipeline

- **`backend/app/services/search/hybrid_search.py`**
  - BM25 + Vector fusion
  - RRF scoring

- **`backend/app/services/search/multi_query_rag.py`**
  - LLM-based query expansion
  - Frequency-based result fusion

- **`backend/app/services/search/reranking/`**
  - Cross-encoder reranking (ms-marco-MiniLM-L6-v2)
  - MMR diversification
  - Semantic deduplication

### Vector Stores
- **`backend/app/db/repositories/chunk_repository.py`**
  - pgvector operations
  - Cosine similarity search

- **`backend/app/services/vector_stores/qdrant_store.py`**
  - Qdrant integration (optional)
  - Circuit breaker fallback

### Verification & Quality
- **`backend/app/services/citation_confidence/confidence_calculator.py`**
  - Chain-of-Verification implementation
  - 4-factor confidence scoring

- **`backend/app/services/verification/quality_validator.py`**
  - Document-level quality assessment

---

## 🎯 Phase 1 Architecture Changes

### New Components to Add

#### 1. Contextual Retrieval
**New File**: `backend/app/services/chunking/contextual_enrichment.py`
```
Purpose: Generate contextual prefixes for chunks before embedding
Dependencies:
  - LLM provider (Ollama/Haiku)
  - Chunking service
  - Document metadata

Integration Points:
  - Called by chunking_service.py after chunk creation
  - Before embedding generation
  - Store both original + contextual text
```

#### 2. Late Chunking
**New File**: `backend/app/services/embeddings/late_chunking.py`
```
Purpose: Embed full documents, then apply chunking
Dependencies:
  - BGE-M3 model
  - Transformer library
  - Chunk boundary information

Integration Points:
  - Alternative to standard embedding pipeline
  - Config flag: ENABLE_LATE_CHUNKING
  - Used in document_processing/processor.py
```

#### 3. HyDE (Hypothetical Document Embeddings)
**New File**: `backend/app/services/search/hyde.py`
```
Purpose: Generate hypothetical answers for ambiguous queries
Dependencies:
  - LLM provider (Ollama/Haiku)
  - Embedding service
  - Query complexity detector

Integration Points:
  - Called by search_service.py for complex queries
  - New parameter: enable_hyde (default: auto-detect)
  - Fallback to standard search if HyDE fails
```

---

## 🔧 Configuration Changes

### New Config Variables (backend/app/core/config.py)

```python
# Contextual Retrieval
ENABLE_CONTEXTUAL_RETRIEVAL: bool = True
CONTEXTUAL_LLM_PROVIDER: str = "ollama"  # ollama, haiku, openrouter
CONTEXTUAL_LLM_MODEL: str = "llama3.2:3b"
CONTEXTUAL_MAX_TOKENS: int = 100

# Late Chunking
ENABLE_LATE_CHUNKING: bool = True
LATE_CHUNKING_MAX_DOC_TOKENS: int = 8192
LATE_CHUNKING_BATCH_SIZE: int = 4  # docs per batch

# HyDE
ENABLE_HYDE: bool = True  # auto-detect or manual
HYDE_LLM_PROVIDER: str = "ollama"
HYDE_LLM_MODEL: str = "llama3.2:3b"
HYDE_MAX_TOKENS: int = 200
HYDE_QUERY_COMPLEXITY_THRESHOLD: float = 0.6
```

---

## 📊 Data Model Changes

### Chunks Table Updates (if needed)
```sql
-- Add column for contextual text (optional - can store in JSON)
ALTER TABLE chunks ADD COLUMN contextual_text TEXT;

-- Add column for late chunking metadata
ALTER TABLE chunks ADD COLUMN late_chunked BOOLEAN DEFAULT FALSE;
```

### Metadata Extensions
```python
class ChunkMetadata(BaseModel):
    # Existing fields...

    # New fields for Phase 1
    contextual_prefix: Optional[str] = None
    late_chunked: bool = False
    hyde_generated: bool = False
```

---

## 🧪 Testing Strategy

### Unit Tests
- `tests/services/test_contextual_enrichment.py`
- `tests/services/test_late_chunking.py`
- `tests/services/test_hyde.py`

### Integration Tests
- `tests/integration/test_contextual_retrieval_pipeline.py`
- `tests/integration/test_late_chunking_pipeline.py`
- `tests/integration/test_hyde_search.py`

### Benchmark Tests
- `tests/benchmarks/test_accuracy_improvement.py`
  - Compare before/after on test query set
  - Measure Top-10 precision, MRR
  - Latency impact

---

## 🚨 Risks & Mitigations

### Risk 1: Increased Latency
**Concern**: Contextual retrieval + HyDE add LLM calls
**Mitigation**:
- Use fast local LLM (Ollama llama3.2:3b ~100ms)
- Cache contextual prefixes (one-time cost)
- Make HyDE optional (only for complex queries)

### Risk 2: Storage Increase
**Concern**: Storing contextual text doubles chunk storage
**Mitigation**:
- Store in JSON metadata column (compressed)
- Optional: only store context hash, regenerate on-the-fly
- Phase 2 Matryoshka embeddings will reduce storage 14x

### Risk 3: Late Chunking Memory Usage
**Concern**: Embedding full 8192-token documents uses more memory
**Mitigation**:
- Batch documents (4 at a time)
- Fall back to standard chunking for very long documents (>8192 tokens)
- Monitor GPU/CPU memory usage

### Risk 4: Quality of Local LLM Context
**Concern**: Ollama context quality < GPT-4o-mini
**Mitigation**:
- Validate on test set
- If quality insufficient, use Haiku (~$0.0001/chunk)
- Provide config option to choose LLM provider

---

## 🔄 Rollback Plan

### If Phase 1 Causes Issues

1. **Config Flags**: All features have `ENABLE_*` flags
   - Set `ENABLE_CONTEXTUAL_RETRIEVAL = False`
   - Set `ENABLE_LATE_CHUNKING = False`
   - Set `ENABLE_HYDE = False`

2. **Database**: No breaking schema changes
   - New columns are optional
   - Can ignore contextual_text if not used

3. **Gradual Rollout**:
   - Test on subset of documents first
   - A/B test new vs old pipeline
   - Monitor accuracy metrics before full deployment

---

## 📈 Performance Monitoring

### Metrics to Track

**Accuracy Metrics**:
- Top-10 retrieval precision
- Mean Reciprocal Rank (MRR)
- Answer accuracy
- Citation relevance score

**Performance Metrics**:
- Indexing time (per document)
- Search latency (p50, p95, p99)
- Memory usage (embedding service)
- Storage size (per chunk)

**Cost Metrics**:
- LLM API calls (contextual retrieval, HyDE)
- Embedding compute time
- Storage costs

### Monitoring Tools
- Prometheus metrics (already configured)
- Grafana dashboards (create new for RAG accuracy)
- Celery task monitoring
- Database query performance

---

## 🔗 External Dependencies

### Required Services
1. **Ollama** (for local LLM)
   - Install: `curl -fsSL https://ollama.com/install.sh | sh`
   - Pull model: `ollama pull llama3.2:3b`
   - API endpoint: `http://localhost:11434`

2. **Alternative: Anthropic Haiku**
   - Already configured in OpenRouter
   - Model: `anthropic/claude-3-haiku`
   - Cost: ~$0.25 per 1M input tokens

### Optional Upgrades (Phase 2-3)
- Nomic Embed v1.5 (Matryoshka embeddings)
- Jina ColBERT v2 (multi-vector retrieval)
- RAPTOR clustering libraries (scikit-learn, UMAP)

---

## 📝 Architecture Decisions

### Decision 1: Keep BGE-M3
**Rationale**:
- Already performs well (70-72% MTEB)
- Proven in production
- Phase 1 techniques provide +35-50% improvement without model change
- Upgrading to bge-multilingual-gemma2 only adds +5% (diminishing returns)

### Decision 2: Local LLM for Context Generation
**Rationale**:
- Near-zero cost (vs $0.001/chunk for GPT-4o-mini)
- Fast inference (~100ms with llama3.2:3b)
- Good enough quality for contextual prefixes
- Can upgrade to Haiku if quality insufficient

### Decision 3: Late Chunking with BGE-M3
**Rationale**:
- BGE-M3 supports 8192 tokens (sufficient for most documents)
- No need to change embedding model
- Proven technique (Jina AI published results)
- Can be toggled via config flag

### Decision 4: Optional HyDE
**Rationale**:
- Only use for complex/ambiguous queries (auto-detect)
- Adds latency (~200ms), not suitable for all queries
- Fallback to standard search if HyDE fails
- Measurable impact on multi-hop questions

---

Last Updated: Nov 15, 2025
Status: Architecture Reviewed and Approved
