# QueryBox Backend RAG Optimization - Implementation Context

## Current State Analysis

### What's Working Well ✅

1. **Solid Foundation Architecture**
   - PostgreSQL + pgvector for vector storage
   - Hybrid search (BM25 + vector + RRF fusion)
   - Advanced reranking with cross-encoder
   - Chain-of-Verification for hallucination reduction
   - Comprehensive metadata extraction

2. **Excellent Parsing**
   - Docling: 97.9% table accuracy
   - OCR fallback with EasyOCR
   - Rich metadata (10+ element types)
   - Quality assessment scoring

3. **Sophisticated Chunking**
   - Token-aware (BGE-M3 tokenizer)
   - Semantic boundary preservation
   - Rich metadata (section headings, chunk types)
   - Overlap for context continuity

4. **Production-Ready Features**
   - Citation extraction with confidence scores
   - Redis caching for embeddings
   - Celery for async processing
   - Structured logging
   - Docker containerization

### What Needs Improvement ⚠️

1. **LLM Quality**: tinyllama (637MB) insufficient for production
2. **Speed**: CPU-only processing, slow embeddings (100-500ms/batch)
3. **Scalability**: pgvector slower at scale, HNSW index requires 1000+ vectors
4. **Visual Content**: No chart/graph interpretation (images extracted but not understood)
5. **Modularity**: Components tightly coupled, hard to swap alternatives
6. **Cost Optimization**: No clear path from prototype to production-scale

---

## Key Files to Modify

### Core Services (Existing)

#### 1. **Text Extraction Service**
**Path**: `backend/app/services/extraction/text_extraction_service.py`

**Current**: Docling + PyPDF2 fallback, OCR with EasyOCR

**Changes Needed**:
- Add MinerU as alternative parser
- Implement document type classifier (route to appropriate parser)
- Add GPT-4o-mini vision integration for charts/graphs
- Optimize Docling parameters (GPU, batch size, preload)

**Key Functions**:
- `extract_text()` - Main extraction entry point
- `_extract_with_docling()` - Docling extraction logic
- Need to add: `_extract_with_mineru()`, `_extract_visual_content()`

---

#### 2. **Chunking Service**
**Path**: `backend/app/services/chunking/chunking_service.py`

**Current**: 512 target tokens, 50 overlap, paragraph boundaries

**Changes Needed**:
- Increase target: 512 → 700 tokens
- Increase overlap: 50 → 150 tokens (20%)
- Add semantic boundary detection (topic shifts)
- Adjust for OpenAI embeddings (3072-dim, 8K max)

**Key Functions**:
- `chunk_document()` - Main chunking entry point
- `_group_sentences_into_chunks()` - Chunking logic
- Need to enhance: Semantic splitting, better overlap strategy

---

#### 3. **Embedding Service**
**Path**: `backend/app/services/embeddings/embedding_service.py`

**Current**: BGE-M3 local model (1024-dim, CPU)

**Changes Needed**:
- Add OpenAI embeddings provider
- Implement abstract `EmbeddingProvider` interface
- Config-driven provider selection
- Keep BGE-M3 as fallback option

**Key Functions**:
- `generate_embeddings()` - Main embedding entry point
- `embed_query()` - Query embedding (cached)
- Need to add: Provider abstraction, OpenAI implementation

---

#### 4. **Model Manager**
**Path**: `backend/app/services/embeddings/model_manager.py`

**Current**: Singleton for BGE-M3 model management

**Changes Needed**:
- Extract into provider pattern
- Support multiple embedding providers
- Lazy loading per provider
- Device management (CPU, CUDA, MPS)

**Key Functions**:
- `get_model()` - Returns BGE-M3 model
- Need to refactor: Multi-provider support

---

#### 5. **Hybrid Search Service**
**Path**: `backend/app/services/search/hybrid_search_service.py`

**Current**: BM25 + vector + RRF + reranking + MMR

**Changes Needed**:
- Add Multi-Query RAG layer
- Add HyDE (Hypothetical Document Embeddings) option
- Integrate with new vector store abstraction
- Make retrieval strategy configurable

**Key Functions**:
- `search()` - Main search entry point
- `_search_bm25()` - Keyword search
- `_search_vector()` - Vector search
- `_fuse_results()` - RRF fusion
- Need to add: `multi_query_search()`, `hyde_search()`

---

#### 6. **Ollama Client (LLM)**
**Path**: `backend/app/services/ollama_client.py`

**Current**: Direct Ollama integration (tinyllama)

**Changes Needed**:
- Extract into LLM provider abstraction
- Add OpenRouter provider
- Keep Ollama as fallback
- Config-driven LLM selection

**Key Functions**:
- `generate()` - Text generation
- `generate_with_retry()` - Retry logic
- Need to refactor: Provider pattern, multi-model support

---

#### 7. **Answer Service**
**Path**: `backend/app/services/answer_service.py`

**Current**: RAG pipeline (search → retrieve → generate → verify)

**Changes Needed**:
- Use new LLM provider abstraction
- Integrate Multi-Query RAG
- Update prompt templates for OpenRouter models
- Add model-specific optimizations (GPT-4o-mini, Claude, Gemini)

**Key Functions**:
- `generate_answer()` - Basic RAG
- `generate_verified_answer()` - With Chain-of-Verification
- `generate_enhanced_answer()` - With citation confidence

---

#### 8. **Configuration**
**Path**: `backend/app/core/config.py`

**Current**: Monolithic config with hardcoded choices

**Changes Needed**:
- Add provider selection configs:
  - `PARSER_PRIMARY`, `PARSER_FALLBACK`
  - `EMBEDDING_PROVIDER`, `VECTOR_STORE`
  - `LLM_PROVIDER`, `RETRIEVAL_MODE`
- Add API keys: `OPENAI_API_KEY`, `OPENROUTER_API_KEY`
- Add Qdrant settings: `QDRANT_URL`, `QDRANT_API_KEY`
- Add feature flags: `ENABLE_MULTI_QUERY`, `ENABLE_HYDE`

---

### New Files to Create

#### 9. **Abstract Base Classes (Modular Architecture)**

**File**: `backend/app/services/parsers/base.py`
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class DocumentParser(ABC):
    """Abstract base class for document parsers"""

    @abstractmethod
    def parse(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Parse document and return text + metadata"""
        pass

    @abstractmethod
    def get_confidence(self, result: Dict[str, Any]) -> float:
        """Return confidence score for parsing result"""
        pass

    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        """Check if parser supports file format"""
        pass
```

**File**: `backend/app/services/embeddings/base.py`
```python
from abc import ABC, abstractmethod
from typing import List
import numpy as np

class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers"""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[np.ndarray]:
        """Embed multiple texts (batch)"""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> np.ndarray:
        """Embed single query (often cached)"""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return embedding dimension"""
        pass
```

**File**: `backend/app/services/search/vector_stores/base.py`
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class VectorStore(ABC):
    """Abstract base class for vector stores"""

    @abstractmethod
    def index(self, vectors: List[np.ndarray], metadata: List[Dict], ids: List[str]):
        """Index vectors with metadata"""
        pass

    @abstractmethod
    def search(self, query_vector: np.ndarray, filters: Dict, top_k: int) -> List[Dict]:
        """Search for similar vectors"""
        pass

    @abstractmethod
    def delete(self, ids: List[str]):
        """Delete vectors by ID"""
        pass
```

**File**: `backend/app/services/llm/base.py`
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def generate(self, prompt: str, context: str, **kwargs) -> str:
        """Generate text completion"""
        pass

    @abstractmethod
    def generate_with_messages(self, messages: List[Dict], **kwargs) -> str:
        """Generate with chat message format"""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return current model name"""
        pass
```

---

#### 10. **Concrete Implementations**

**Parser Implementations**:
- `backend/app/services/parsers/docling_parser.py` - Existing Docling logic extracted
- `backend/app/services/parsers/mineru_parser.py` - MinerU integration
- `backend/app/services/parsers/vision_parser.py` - GPT-4o-mini vision for charts
- `backend/app/services/parsers/router.py` - Smart routing logic

**Embedding Implementations**:
- `backend/app/services/embeddings/bge_provider.py` - Existing BGE-M3 extracted
- `backend/app/services/embeddings/openai_provider.py` - OpenAI embeddings API

**Vector Store Implementations**:
- `backend/app/services/search/vector_stores/pgvector_store.py` - Existing pgvector extracted
- `backend/app/services/search/vector_stores/qdrant_store.py` - Qdrant integration

**LLM Implementations**:
- `backend/app/services/llm/ollama_provider.py` - Existing Ollama extracted
- `backend/app/services/llm/openrouter_provider.py` - OpenRouter integration

**Advanced Retrieval**:
- `backend/app/services/search/multi_query_retriever.py` - Multi-Query RAG
- `backend/app/services/search/hyde_retriever.py` - HyDE (optional)

---

#### 11. **Utilities & Scripts**

**Migration Scripts**:
- `backend/scripts/migrate_to_qdrant.py` - Migrate embeddings from Postgres to Qdrant
- `backend/scripts/test_parsers.py` - Compare Docling vs MinerU on sample docs
- `backend/scripts/benchmark_retrievers.py` - Compare retrieval strategies

**Evaluation**:
- `backend/tests/evaluation/ragas_eval.py` - RAGAs evaluation framework
- `backend/tests/evaluation/create_test_dataset.py` - Generate ground truth Q&A pairs

**Factories**:
- `backend/app/services/parsers/factory.py` - Parser factory (config → implementation)
- `backend/app/services/embeddings/factory.py` - Embedding provider factory
- `backend/app/services/search/vector_stores/factory.py` - Vector store factory
- `backend/app/services/llm/factory.py` - LLM provider factory

---

## Architectural Decisions

### Decision 1: Abstract Base Classes + Factory Pattern

**Why**:
- Future-proof: Easy to add new providers (Cohere, Anthropic, Weaviate, etc.)
- Testable: Mock providers for unit tests
- Configurable: Swap implementations via .env without code changes
- Aligns with Step 15 vision: Modular, swappable components

**Implementation**:
```python
# Config (.env)
EMBEDDING_PROVIDER=openai

# Factory (factory.py)
def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.EMBEDDING_PROVIDER
    if provider == "openai":
        return OpenAIProvider()
    elif provider == "bge":
        return BGEProvider()
    else:
        raise ValueError(f"Unknown provider: {provider}")

# Usage (anywhere)
embedder = get_embedding_provider()
vectors = embedder.embed(texts)
```

**Benefit**: Change one line in .env, entire system switches providers

---

### Decision 2: PostgreSQL + Qdrant (Parallel, Not Replacement)

**Why**:
- **Risk mitigation**: Don't touch working Postgres setup
- **A/B testing**: Compare performance side-by-side
- **Rollback safety**: Can disable Qdrant anytime
- **Best of both**: Postgres for relations/metadata, Qdrant for fast vector search

**Architecture**:
```
┌─────────────────────────────────┐
│   PostgreSQL (Source of Truth) │
│   - Documents, chunks, metadata │
│   - Relational integrity        │
│   - ACID transactions           │
└─────────────────────────────────┘
          ↓ sync (one-way)
┌─────────────────────────────────┐
│   Qdrant (Fast Search Layer)   │
│   - Vectors + minimal metadata  │
│   - HNSW index (fast)           │
│   - <50ms search                │
└─────────────────────────────────┘
```

**Implementation**:
- Postgres writes continue as normal
- Async background job syncs to Qdrant
- Search checks config: use Qdrant if enabled, else pgvector
- Can compare both in parallel (feature flag)

---

### Decision 3: OpenRouter Over Direct OpenAI

**Why**:
- **Multi-model access**: GPT-4o-mini, Claude-3-Haiku, Gemini-2.0-Flash, Llama-3.1
- **Easy A/B testing**: Try different models without code changes
- **Fallback built-in**: If one model fails, auto-retry with alternative
- **Same interface**: Uses OpenAI SDK (minimal code changes)
- **No lock-in**: Can switch to direct API later (change base_url)

**Implementation**:
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"]
)

response = client.chat.completions.create(
    model="openai/gpt-4o-mini",  # Or anthropic/claude-3-haiku
    messages=[...]
)
```

**Benefit**: Try 5 models in 5 minutes, pick the best one

---

### Decision 4: Multi-Query RAG Over HyDE (Initially)

**Why**:
- **Simpler**: Generate query variations vs generate hypothetical documents
- **Proven**: 15-25% improvement in benchmarks
- **Non-invasive**: Wraps existing search, no changes to core logic
- **Faster**: Can parallelize query variations
- **Lower risk**: Easier to implement correctly in 2 hours

**Implementation**:
```python
class MultiQueryRetriever:
    def retrieve(self, query, top_k=5):
        # 1. Generate 2 variations
        variations = self.llm.generate_variations(query)
        # ["What is France's capital?",
        #  "Which city is France's capital?",
        #  "France capital city name"]

        # 2. Search with all 3
        all_results = []
        for q in variations:
            results = self.search(q, top_k=20)
            all_results.extend(results)

        # 3. Deduplicate & re-rank by frequency
        return self.rank_by_occurrence(all_results, top_k)
```

**Note**: HyDE still available as alternative (config flag)

---

### Decision 5: Keep Docling, Add MinerU + Vision

**Why**:
- **Docling is excellent**: 97.9% accuracy, no need to replace
- **MinerU for edge cases**: 10-15% of docs are table-heavy
- **Vision for charts**: Final 5% (images, graphs, infographics)
- **Incremental improvement**: Not risky replacement
- **Cost-effective**: MinerU free, vision API cheap ($0.001/image)

**Implementation**:
```python
class SmartParsingService:
    def parse(self, file_path):
        doc_type = self.classify(file_path)

        if doc_type == "table_heavy":
            result = self.mineru.parse(file_path)
        else:
            result = self.docling.parse(file_path)

        # Extract images/charts
        if result.has_images:
            for img in result.images:
                img_text = self.vision.interpret(img)
                result.add_text(img_text)

        return result
```

**Fallback**: If MinerU/vision fail, Docling handles everything

---

## Integration Points

### 1. **API Endpoints** (Minimal Changes)

**Path**: `backend/app/api/v1/endpoints/`

**Files**:
- `answer.py` - Answer generation endpoints
- `documents.py` - Document upload/management
- `search.py` - Search endpoints

**Changes**:
- Add query parameters for provider selection (optional, for A/B testing)
- Add response fields for provider metadata (which LLM/embedder used)
- No breaking changes to existing contracts

**Example**:
```python
# Optional: Allow client to specify provider
@router.post("/answer")
def generate_answer(
    query: str,
    llm_provider: Optional[str] = None,  # New, optional
    retrieval_mode: Optional[str] = None  # New, optional
):
    # Use specified provider or default from config
    llm = get_llm_provider(llm_provider or settings.LLM_PROVIDER)
    ...
```

---

### 2. **Database Schema** (No Changes!)

**Important**: No database schema changes required

**Why**:
- Qdrant stores vectors separately (not in Postgres)
- Modular providers use same data formats
- Metadata schema stays unchanged

**Only addition**: Optional tracking table for provider metrics
```sql
-- Optional, for monitoring only
CREATE TABLE provider_metrics (
    id SERIAL PRIMARY KEY,
    provider_type VARCHAR(50),  -- 'llm', 'embedding', 'vector_store'
    provider_name VARCHAR(100), -- 'openai', 'qdrant', 'bge'
    query_id UUID,
    latency_ms INT,
    tokens_used INT,
    cost_usd DECIMAL(10,6),
    created_at TIMESTAMP
);
```

---

### 3. **Celery Tasks** (Minor Updates)

**Path**: `backend/app/services/tasks/`

**Current**: Document processing tasks (upload → extract → chunk → embed → index)

**Changes**:
- Update embedding task to use new provider abstraction
- Add Qdrant sync task (Postgres → Qdrant)
- No changes to task signatures or API contracts

**Example**:
```python
@celery_app.task
def embed_and_index_document(document_id: str):
    # Use configured providers
    embedder = get_embedding_provider()
    vector_store = get_vector_store()

    chunks = get_chunks(document_id)
    vectors = embedder.embed([c.text for c in chunks])

    # Index in both stores (if Qdrant enabled)
    pgvector_store.index(vectors, chunks)
    if settings.ENABLE_QDRANT:
        qdrant_store.index(vectors, chunks)
```

---

### 4. **Caching** (Enhanced)

**Current**: Redis for query embeddings (30min TTL)

**Enhancements**:
- Cache LLM responses (verification results, 1hr TTL)
- Cache query variations (Multi-Query RAG, 1hr TTL)
- Cache parser results (document text, until doc updated)

**Benefits**:
- Reduce API costs (don't re-generate same queries)
- Faster response times for common queries
- Cost optimization for LLM calls

---

### 5. **Monitoring & Logging**

**Current**: Structlog for structured logging

**Additions**:
- Log provider selection (which LLM/embedder used)
- Log latency per component (parsing, embedding, search, generation)
- Log costs per query (track API spending)
- Log RAGAs metrics (track accuracy over time)

**Example**:
```python
logger.info("rag_query",
    query_id=query_id,
    llm_provider="openrouter",
    llm_model="openai/gpt-4o-mini",
    embedding_provider="openai",
    vector_store="qdrant",
    retrieval_mode="multi_query",
    latency_ms=1847,
    cost_usd=0.0043,
    ragas_faithfulness=0.92
)
```

**Benefit**: Data-driven optimization, cost tracking, quality monitoring

---

## Configuration Structure (.env)

### Parsing
```bash
# Primary parser: docling | mineru | unstructured
PARSER_PRIMARY=docling

# Fallback if primary fails
PARSER_FALLBACK=mineru

# Enable smart routing (table-heavy docs → MinerU)
PARSER_TABLE_ROUTER=true

# Docling optimizations
DOCLING_PARALLEL_PAGES=true
DOCLING_PRELOAD_MODELS=true
DOCLING_GPU_ENABLED=true

# MinerU settings
MINERU_GPU_ENABLED=true

# Vision API for charts (GPT-4o-mini)
ENABLE_VISION_PARSING=true
VISION_API_PROVIDER=openai
```

### Embeddings
```bash
# Provider: openai | bge | cohere | voyage
EMBEDDING_PROVIDER=openai

# OpenAI embeddings
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
OPENAI_EMBEDDING_DIMENSION=3072

# BGE (fallback)
BGE_MODEL_NAME=BAAI/bge-m3
BGE_DEVICE=auto
```

### Vector Store
```bash
# Store: qdrant | pgvector | lancedb | weaviate
VECTOR_STORE=qdrant

# Qdrant settings
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=querybox_embeddings

# Enable parallel operation (Qdrant + Postgres both active)
ENABLE_PARALLEL_VECTOR_STORES=true
```

### LLM
```bash
# Provider: openrouter | ollama | openai | anthropic
LLM_PROVIDER=openrouter

# OpenRouter settings
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_FALLBACK=anthropic/claude-3-haiku,google/gemini-2.0-flash

# Ollama (fallback)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=tinyllama
```

### Advanced Retrieval
```bash
# Retrieval mode: standard | multi_query | hyde
RETRIEVAL_MODE=multi_query

# Multi-Query RAG settings
ENABLE_MULTI_QUERY=true
MULTI_QUERY_VARIATIONS=2

# HyDE settings
ENABLE_HYDE=false
```

### Chunking
```bash
CHUNKING_TARGET_TOKENS=700
CHUNKING_MAX_TOKENS=850
CHUNKING_MIN_TOKENS=150
CHUNKING_OVERLAP_TOKENS=150
ENABLE_SEMANTIC_SPLITTING=true
```

---

## Key Metrics to Track

### Accuracy Metrics (RAGAs)
- **Faithfulness**: 0.0-1.0 (higher = fewer hallucinations)
- **Answer Relevancy**: 0.0-1.0 (higher = more relevant answers)
- **Context Precision**: 0.0-1.0 (higher = retrieved chunks are relevant)
- **Context Recall**: 0.0-1.0 (higher = all relevant info retrieved)

**Target**: All >0.85, ideally >0.90

### Performance Metrics
- **p50 Latency**: Median response time
- **p95 Latency**: 95th percentile response time
- **p99 Latency**: 99th percentile response time
- **Throughput**: Queries per second

**Target**: p50 <1.5s, p95 <3s, p99 <5s

### Cost Metrics
- **Cost per Query**: Total API costs / number of queries
- **Cost per Component**: Breakdown (LLM, embeddings, vision)
- **Monthly Burn**: Projected monthly cost at current usage

**Target**: <$0.05 per query, <$50/month for demo scale

### Component Performance
- **Parsing Time**: Time to extract text from documents
- **Embedding Time**: Time to generate embeddings
- **Search Time**: Time to retrieve relevant chunks
- **Generation Time**: Time for LLM to generate answer

**Target**: Parsing <2s, Embedding <200ms, Search <100ms, Generation <1s

---

## Testing Strategy

### Unit Tests
- Test each provider implementation independently
- Mock external APIs (OpenAI, OpenRouter, Qdrant)
- Test factory pattern (config → correct provider)
- Test error handling and fallbacks

### Integration Tests
- Test full RAG pipeline with different provider combinations
- Test Postgres → Qdrant synchronization
- Test Multi-Query RAG with actual LLM
- Test document type routing (Docling vs MinerU)

### Evaluation Tests (RAGAs)
- Create ground truth dataset (10-20 Q&A pairs)
- Run RAGAs evaluation before and after changes
- Measure improvement in each metric
- Ensure no regression in accuracy

### Performance Tests
- Benchmark latency for each provider combination
- Load test (100 concurrent queries)
- Measure p50/p95/p99 latencies
- Identify bottlenecks

### Cost Tests
- Track API costs for sample workload (100 queries)
- Compare costs across providers (OpenAI vs Anthropic vs local)
- Project monthly costs at different scales

---

## Dependencies to Add

```txt
# requirements.txt additions

# OpenAI (embeddings + vision)
openai>=1.0.0

# Qdrant (vector store)
qdrant-client>=1.7.0

# MinerU (parsing)
mineru>=2.5.0

# RAGAs (evaluation)
ragas>=0.1.0
datasets>=2.14.0

# OpenRouter (already uses OpenAI SDK)
# No additional dependency needed
```

---

## Next Steps

1. ✅ **Read plan.md** - Understand strategy and technology choices
2. ✅ **Read this file (context.md)** - Understand current state and files to modify
3. 🎯 **Read tasks.md** - Start implementation Phase 1 → Phase 6
4. 🚀 **Begin with Phase 1** - Modular architecture (most important foundation)

**Estimated Timeline**: 16-20 hours over 2 days
**Expected Outcome**: 95-99% accuracy, <2s latency, modular & sustainable architecture

Ready to start building! Let's begin with Phase 1 in tasks.md 🚀
