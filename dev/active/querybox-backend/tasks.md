# QueryBox Backend RAG Optimization - Task Checklist

## Overview

This is your step-by-step checklist for the 2-day RAG optimization sprint. Work through phases sequentially, checking off tasks as you complete them.

**Total Estimated Time**: 16-20 hours over 2 days
**Goal**: 99% accuracy, <2s latency, modular architecture

---

## Phase 1: Foundation - Modular Architecture

**Goal**: Create abstract base classes and factory pattern for all components
**Time**: 3-4 hours
**Why First**: Enables all subsequent work, future-proofs codebase

### 1.1 Create Abstract Base Classes

- [x] **Create parser base class** (15 min)
  - File: `backend/app/services/parsers/base.py`
  - Methods: `parse()`, `get_confidence()`, `supports_format()`
  - Add type hints and docstrings

- [x] **Create embedding provider base class** (15 min)
  - File: `backend/app/services/embeddings/base.py`
  - Methods: `embed()`, `embed_query()`, `get_dimension()`
  - Support both batch and single embedding

- [x] **Create vector store base class** (15 min)
  - File: `backend/app/services/search/vector_stores/base.py`
  - Methods: `index()`, `search()`, `delete()`
  - Add filter support for metadata

- [x] **Create LLM provider base class** (15 min)
  - File: `backend/app/services/llm/base.py`
  - Methods: `generate()`, `generate_with_messages()`, `get_model_name()`
  - Support both completion and chat formats

**Success Criteria**: ✅ 4 abstract base classes with clear interfaces

---

### 1.2 Extract Existing Implementations

- [x] **Extract Docling parser** (30 min)
  - File: `backend/app/services/parsers/docling_parser.py`
  - Move logic from `text_extraction_service.py`
  - Implement `DocumentParser` interface
  - Test on sample PDF

- [x] **Extract BGE-M3 embedding provider** (30 min)
  - File: `backend/app/services/embeddings/bge_provider.py`
  - Move logic from `embedding_service.py` and `model_manager.py`
  - Implement `EmbeddingProvider` interface
  - Test embeddings generation

- [x] **Extract pgvector store** (30 min)
  - File: `backend/app/services/search/vector_stores/pgvector_store.py`
  - Move logic from `hybrid_search_service.py`
  - Implement `VectorStore` interface
  - Test search functionality

- [x] **Extract Ollama provider** (30 min)
  - File: `backend/app/services/llm/ollama_provider.py`
  - Move logic from `ollama_client.py`
  - Implement `LLMProvider` interface
  - Test generation with tinyllama

**Success Criteria**: ✅ 4 concrete implementations, all tests passing

---

### 1.3 Create Factory Pattern

- [x] **Create parser factory** (20 min)
  - File: `backend/app/services/parsers/factory.py`
  - Function: `get_parser(parser_name: str) -> DocumentParser`
  - Support: docling, mineru (placeholder for now)
  - Config-driven selection

- [x] **Create embedding factory** (20 min)
  - File: `backend/app/services/embeddings/factory.py`
  - Function: `get_embedding_provider(name: str) -> EmbeddingProvider`
  - Support: bge, openai (placeholder for now)
  - Config-driven selection

- [x] **Create vector store factory** (20 min)
  - File: `backend/app/services/search/vector_stores/factory.py`
  - Function: `get_vector_store(name: str) -> VectorStore`
  - Support: pgvector, qdrant (placeholder for now)
  - Config-driven selection

- [x] **Create LLM factory** (20 min)
  - File: `backend/app/services/llm/factory.py`
  - Function: `get_llm_provider(name: str) -> LLMProvider`
  - Support: ollama, openrouter (placeholder for now)
  - Config-driven selection

**Success Criteria**: ✅ 4 factories, config-driven component selection working

---

### 1.4 Update Configuration

- [x] **Add provider selection configs** (20 min)
  - File: `backend/app/core/config.py`
  - Add: `PARSER_PRIMARY` ✅
  - Add: `EMBEDDING_PROVIDER`, `VECTOR_STORE`, `LLM_PROVIDER` ✅
  - Note: `PARSER_FALLBACK` and `RETRIEVAL_MODE` will be added in later phases

- [ ] **Add API key configs** (10 min)
  - Add: `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `QDRANT_API_KEY`
  - Add: `OPENROUTER_MODEL`, `OPENAI_EMBEDDING_MODEL`
  - Add validation for required keys based on provider selection

- [ ] **Add feature flag configs** (10 min)
  - Add: `ENABLE_MULTI_QUERY`, `ENABLE_HYDE`, `ENABLE_QDRANT`
  - Add: `ENABLE_VISION_PARSING`, `PARSER_TABLE_ROUTER`
  - Add: `ENABLE_PARALLEL_VECTOR_STORES`

- [x] **Update .env.example** (10 min)
  - Document all new configs ✅
  - Provide sensible defaults ✅
  - Add comments explaining each option ✅

**Success Criteria**: ✅ Config system supports all provider options (core providers complete)

---

### 1.5 Integration & Testing ✅ COMPLETE

- [x] **Update existing services to use factories** (30 min)
  - Update: `text_extraction_service.py` → use `get_parser()` ✅
  - Update: `embedding_service.py` → use `get_embedding_provider()` ✅
  - Update: `hybrid_search_service.py` → use `get_vector_store()` ✅ (uses dependency injection)
  - Update: `answer_service.py` → use `get_llm_provider()` ✅

- [x] **Write unit tests for factories** (30 min)
  - Test each factory returns correct implementation ✅
  - Test invalid provider names raise errors ✅ (built into factories)
  - Test config overrides work correctly ✅

- [x] **Test end-to-end with current setup** (20 min)
  - Run full RAG pipeline with refactored code ✅
  - Verify: docling, bge, pgvector, ollama still working ✅
  - Check: No regression in functionality ✅
  - Measure: Baseline latency and accuracy ✅

**Success Criteria**: ✅ Modular architecture complete, no regressions, all factories working

---

## ✅ PHASE 1 COMPLETE (Jan 11, 2025)

**Total Time**: ~3.5 hours
**Achievement**: Complete modular architecture with factory pattern
**Files Created**: 14 files, ~2,800 lines of code
**Integration**: All existing services using factories
**Result**: Zero-code component swapping via .env configuration

**What This Enables**:
```bash
# Before: Hard-coded implementations
# After: Swap via config
LLM_PROVIDER=openrouter        # Switch to GPT-4o-mini (once implemented)
EMBEDDING_PROVIDER=openai      # Switch to OpenAI embeddings
VECTOR_STORE=qdrant           # Switch to Qdrant
PARSER_PRIMARY=mineru         # Switch to MinerU
```

**Remaining from Phase 1.4**: Add API keys and feature flags (30 min)
- Add: `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `QDRANT_API_KEY`
- Add: `ENABLE_MULTI_QUERY`, `ENABLE_HYDE`, `ENABLE_QDRANT`

---

## Phase 2: Parsing Optimization

**Goal**: Add MinerU, GPT-4o-mini vision, optimize Docling
**Time**: 2-3 hours
**Dependencies**: Phase 1 complete

### 2.1 Optimize Docling

- [ ] **Tune Docling parameters** (20 min)
  - File: `backend/app/services/parsers/docling_parser.py`
  - Enable: `DOCLING_PARALLEL_PAGES=True`
  - Enable: `DOCLING_PRELOAD_MODELS=True` (avoid lazy loading)
  - Increase: OCR batch size from 4 → 8
  - Test on sample documents, measure speed improvement

- [ ] **Add GPU support for Docling** (15 min)
  - Check CUDA availability
  - Enable GPU for OCR if available
  - Add fallback to CPU if GPU unavailable
  - Test with/without GPU, measure difference

**Success Criteria**: Docling 30-40% faster, no accuracy loss

---

### 2.2 Add MinerU Integration

- [ ] **Install MinerU** (10 min)
  - Add to `requirements.txt`: `mineru>=2.5.0`
  - Run: `pip install mineru`
  - Test import: `import mineru`

- [ ] **Create MinerU parser** (40 min)
  - File: `backend/app/services/parsers/mineru_parser.py`
  - Implement `DocumentParser` interface
  - Add table extraction logic
  - Handle errors gracefully (fallback to Docling)

- [ ] **Test MinerU on sample documents** (20 min)
  - Test on: financial report with complex tables
  - Test on: simple text document
  - Compare: MinerU vs Docling accuracy
  - Measure: parsing time for each

**Success Criteria**: MinerU working, excellent on table-heavy docs

---

### 2.3 Implement Document Type Router

- [ ] **Create document classifier** (30 min)
  - File: `backend/app/services/parsers/router.py`
  - Function: `classify_document(file_path) -> str`
  - Detect: table_heavy (>5 tables or >30% coverage)
  - Detect: scanned (low OCR confidence)
  - Detect: standard (everything else)

- [ ] **Create smart parsing service** (30 min)
  - File: `backend/app/services/parsers/router.py`
  - Class: `SmartParsingService`
  - Logic: Route to MinerU if table_heavy, else Docling
  - Add: Confidence-based fallback (if <0.7, try alternative)
  - Test: Routing works correctly for different doc types

- [ ] **Update parser factory** (15 min)
  - Add "smart" option to factory
  - Use `SmartParsingService` when `PARSER_PRIMARY=smart`
  - Test: Config-driven smart routing

**Success Criteria**: Smart routing 10-15% accuracy gain on mixed documents

---

### 2.4 Add GPT-4o-mini Vision for Charts

- [ ] **Create vision parser** (40 min)
  - File: `backend/app/services/parsers/vision_parser.py`
  - Class: `VisionContentParser`
  - Method: `interpret_image(image_path, context) -> str`
  - Use: GPT-4o-mini with vision capability
  - Return: Text description of chart/graph data

- [ ] **Integrate vision into parsing pipeline** (30 min)
  - Update: `SmartParsingService` to detect images
  - For each image: Call vision parser
  - Append: Image descriptions to document text
  - Preserve: Image positions for citations

- [ ] **Test vision parsing** (20 min)
  - Test on: Document with bar charts
  - Test on: Document with line graphs
  - Test on: Document with infographics
  - Verify: Vision descriptions are accurate and useful

- [ ] **Add vision API config** (10 min)
  - Add: `ENABLE_VISION_PARSING` flag
  - Add: `VISION_API_PROVIDER` (openai default)
  - Add: Cost tracking for vision API calls
  - Update: .env.example with vision settings

**Success Criteria**: Charts/graphs now interpretable, 99% parsing coverage

---

### 2.5 Testing & Validation

- [ ] **Create parsing comparison script** (30 min)
  - File: `backend/scripts/test_parsers.py`
  - Compare: Docling vs MinerU vs Smart on 10 documents
  - Measure: accuracy, speed, confidence scores
  - Output: Comparison table

- [ ] **Run parsing benchmarks** (20 min)
  - Test on diverse document set (PDFs, PPTX, scanned)
  - Measure: parsing time, accuracy, OCR quality
  - Record: Baseline vs optimized performance
  - Target: 99% accuracy across document types

**Success Criteria**: Parsing 99% accurate, smart routing working, benchmarks documented

---

## Phase 3: LLM & Embeddings Upgrade

**Goal**: Add OpenRouter LLM and OpenAI embeddings
**Time**: 3-4 hours
**Dependencies**: Phase 1 complete

### 3.1 Implement OpenRouter Provider

- [ ] **Create OpenRouter provider** (40 min)
  - File: `backend/app/services/llm/openrouter_provider.py`
  - Class: `OpenRouterProvider(LLMProvider)`
  - Use: OpenAI SDK with custom base_url
  - Implement: `generate()`, `generate_with_messages()`
  - Add: Retry logic with exponential backoff

- [ ] **Add model selection logic** (20 min)
  - Support: Primary model (GPT-4o-mini default)
  - Support: Fallback models (Claude, Gemini)
  - Implement: Auto-fallback on rate limits or errors
  - Add: Model-specific prompt optimizations

- [ ] **Test OpenRouter integration** (30 min)
  - Test: Basic generation with GPT-4o-mini
  - Test: Fallback to Claude-3-Haiku
  - Test: Rate limit handling
  - Compare: Quality vs tinyllama (should be much better)

- [ ] **Update LLM factory** (10 min)
  - Add: `openrouter` option
  - Set: Default to `openrouter` in config
  - Test: Factory returns OpenRouter when configured

**Success Criteria**: OpenRouter working, 10x better quality than tinyllama

---

### 3.2 Implement OpenAI Embeddings

- [ ] **Create OpenAI embedding provider** (30 min)
  - File: `backend/app/services/embeddings/openai_provider.py`
  - Class: `OpenAIEmbeddingProvider(EmbeddingProvider)`
  - Use: `text-embedding-3-large` (3072-dim)
  - Implement: `embed()` (batch), `embed_query()` (single)
  - Add: Batch size optimization (100-500 texts/batch)

- [ ] **Add caching for query embeddings** (20 min)
  - Use: Existing Redis cache
  - Key: SHA-256 hash of query text + model name
  - TTL: 30 minutes (same as current BGE-M3 cache)
  - Test: Cache hit/miss working correctly

- [ ] **Test OpenAI embeddings** (30 min)
  - Test: Batch embedding (100 chunks)
  - Test: Single query embedding
  - Test: Cache hit on repeated query
  - Measure: Latency vs BGE-M3 (should be faster)

- [ ] **Update embedding factory** (10 min)
  - Add: `openai` option
  - Set: Default to `openai` in config
  - Test: Factory returns OpenAI provider when configured

**Success Criteria**: OpenAI embeddings working, <200ms per query, cached

---

### 3.3 Update Answer Service

- [ ] **Update prompt templates** (30 min)
  - File: `backend/app/services/answer_service.py`
  - Optimize: Prompts for GPT-4o-mini (more capable than tinyllama)
  - Add: Model-specific variations (GPT vs Claude vs Gemini)
  - Test: Answer quality improvement

- [ ] **Add model metadata to responses** (15 min)
  - Include: Which LLM model used
  - Include: Which embedding provider used
  - Include: Provider-specific metadata (tokens, latency)
  - Update: API response schema

- [ ] **Test end-to-end with new providers** (30 min)
  - Test: Full RAG pipeline (OpenRouter + OpenAI embeddings)
  - Compare: Answer quality vs baseline (tinyllama + BGE-M3)
  - Measure: Latency improvement
  - Record: Accuracy improvement (qualitative)

**Success Criteria**: 60-70% answer quality improvement (biggest single win)

---

### 3.4 Cost Tracking & Monitoring

- [ ] **Implement cost tracking** (30 min)
  - File: `backend/app/services/monitoring/cost_tracker.py`
  - Track: LLM tokens (input/output)
  - Track: Embedding tokens
  - Track: Vision API calls
  - Calculate: Cost per query

- [ ] **Add cost logging** (20 min)
  - Log: Cost per query (structlog)
  - Log: Cost per component (LLM, embeddings, vision)
  - Log: Daily/monthly totals
  - Alert: If costs exceed threshold

- [ ] **Create cost dashboard script** (20 min)
  - File: `backend/scripts/cost_dashboard.py`
  - Show: Costs last 24h, 7d, 30d
  - Show: Cost breakdown by component
  - Show: Most expensive queries
  - Project: Monthly costs at current rate

**Success Criteria**: Full cost visibility, spending under control

---

### 3.5 A/B Testing Framework

- [ ] **Create provider comparison script** (40 min)
  - File: `backend/scripts/compare_providers.py`
  - Test: Same queries with different providers
  - Measure: Quality (qualitative), latency, cost
  - Output: Comparison table (GPT vs Claude vs Gemini)

- [ ] **Run provider comparisons** (30 min)
  - Test: 20 sample queries with 3 models
  - Models: GPT-4o-mini, Claude-3-Haiku, Gemini-2.0-Flash
  - Record: Which performs best (quality, speed, cost)
  - Decision: Pick best model as default

**Success Criteria**: Data-driven model selection, best provider chosen

---

## Phase 4: Vector Store Optimization

**Goal**: Add Qdrant for 10x faster vector search
**Time**: 3-4 hours
**Dependencies**: Phase 1 complete

### 4.1 Setup Qdrant

- [ ] **Choose Qdrant deployment** (10 min)
  - Option A: Qdrant Cloud (free 1GB tier, easiest)
  - Option B: Local Docker (self-hosted, more control)
  - Decision: Cloud for demo, local for production
  - Sign up: cloud.qdrant.io OR run Docker

- [ ] **Start Qdrant** (15 min)
  - Cloud: Get API key and cluster URL
  - Local: `docker run -p 6333:6333 qdrant/qdrant`
  - Test: `curl http://localhost:6333` (should return version)
  - Add: Credentials to .env

- [ ] **Install Qdrant client** (5 min)
  - Add to `requirements.txt`: `qdrant-client>=1.7.0`
  - Run: `pip install qdrant-client`
  - Test import: `from qdrant_client import QdrantClient`

**Success Criteria**: Qdrant running and accessible

---

### 4.2 Implement Qdrant Store

- [ ] **Create Qdrant store class** (50 min)
  - File: `backend/app/services/search/vector_stores/qdrant_store.py`
  - Class: `QdrantStore(VectorStore)`
  - Implement: `index()` - upsert vectors with metadata
  - Implement: `search()` - HNSW search with filters
  - Implement: `delete()` - delete vectors by ID
  - Add: Batch upsert optimization

- [ ] **Create collection schema** (20 min)
  - Collection name: `querybox_embeddings`
  - Vector size: 3072 (for text-embedding-3-large) or 1024 (for BGE-M3)
  - Distance metric: Cosine similarity
  - Payload schema: chunk_id, document_id, text, metadata
  - Create collection on first use

- [ ] **Add metadata filtering** (20 min)
  - Support: Filter by document_id
  - Support: Filter by chunk_type (table, paragraph, etc.)
  - Support: Filter by section_heading
  - Test: Filters work correctly

- [ ] **Test Qdrant search** (20 min)
  - Index: 100 test vectors
  - Search: Query vector, top_k=10
  - Measure: Search latency (should be <50ms)
  - Compare: vs pgvector (should be 10x faster)

**Success Criteria**: Qdrant store working, 10x faster than pgvector

---

### 4.3 Migration from PostgreSQL

- [ ] **Create migration script** (60 min)
  - File: `backend/scripts/migrate_to_qdrant.py`
  - Read: All embeddings from PostgreSQL
  - Transform: To Qdrant format (vector + payload)
  - Batch upload: 100-500 vectors at a time
  - Progress tracking: Log every 1000 vectors
  - Idempotent: Can re-run safely (upsert, not insert)

- [ ] **Test migration on subset** (20 min)
  - Migrate: First 1000 embeddings
  - Verify: Vectors in Qdrant match Postgres
  - Test: Search returns same results
  - Measure: Migration speed (vectors/sec)

- [ ] **Run full migration** (30 min)
  - Migrate: All embeddings from Postgres → Qdrant
  - Monitor: Progress and errors
  - Verify: Count matches between stores
  - Test: Random sample queries work correctly

**Success Criteria**: All embeddings in Qdrant, search results match Postgres

---

### 4.4 Parallel Operation

- [ ] **Implement parallel indexing** (30 min)
  - Update: Embedding task to index in both stores
  - Logic: Always write to Postgres (source of truth)
  - Logic: Also write to Qdrant if `ENABLE_QDRANT=true`
  - Test: New documents indexed in both places

- [ ] **Implement search routing** (30 min)
  - Update: `hybrid_search_service.py`
  - Logic: Use Qdrant for vector search if enabled
  - Logic: Fallback to pgvector if Qdrant unavailable
  - Test: Search uses correct store based on config

- [ ] **Add performance comparison** (20 min)
  - Run: Same queries on both stores
  - Measure: Latency (Qdrant vs pgvector)
  - Measure: Result quality (should be identical)
  - Record: Speed improvement (expect 5-10x)

**Success Criteria**: Parallel operation working, no data loss, faster search

---

### 4.5 Testing & Validation

- [ ] **Test search correctness** (30 min)
  - Run: 50 test queries on both stores
  - Compare: Top-10 results from each
  - Verify: Results are identical (same relevance)
  - Check: No missing documents

- [ ] **Test error handling** (20 min)
  - Simulate: Qdrant down (stop Docker)
  - Verify: System falls back to pgvector
  - Verify: No errors or crashes
  - Restart: Qdrant, verify system recovers

- [ ] **Benchmark performance** (20 min)
  - Measure: Search latency (p50, p95, p99)
  - Before: pgvector only
  - After: Qdrant
  - Record: Speed improvement (target: 10x)

**Success Criteria**: Qdrant 10x faster, correctness verified, fallback working

---

## Phase 5: Advanced Retrieval

**Goal**: Implement Multi-Query RAG for 15-25% accuracy boost
**Time**: 2-3 hours
**Dependencies**: Phases 1, 3 complete (need LLM provider)

### 5.1 Implement Multi-Query RAG

- [ ] **Create query variation generator** (40 min)
  - File: `backend/app/services/search/multi_query_retriever.py`
  - Class: `MultiQueryRetriever`
  - Method: `generate_variations(query) -> List[str]`
  - Logic: Use LLM to generate 2 variations
  - Prompt: "Rephrase this query in 2 different ways"
  - Test: Variations are distinct and meaningful

- [ ] **Implement multi-query search** (50 min)
  - Method: `retrieve(query, top_k) -> List[Result]`
  - Step 1: Generate query variations (original + 2 variations)
  - Step 2: Search with each variation (top_k=20 each)
  - Step 3: Deduplicate results by chunk_id
  - Step 4: Re-rank by occurrence frequency (chunks in multiple results rank higher)
  - Step 5: Return top_k final results

- [ ] **Add caching for variations** (20 min)
  - Cache: Query variations (Redis, 1hr TTL)
  - Key: SHA-256 hash of original query
  - Benefit: Don't regenerate for repeated queries
  - Test: Cache working correctly

- [ ] **Test Multi-Query RAG** (30 min)
  - Test: 10 sample queries
  - Compare: Multi-Query vs standard search
  - Measure: Retrieval quality (precision, recall)
  - Record: Improvement (expect 15-25%)

**Success Criteria**: Multi-Query RAG 15-25% better retrieval

---

### 5.2 Implement HyDE (Optional)

- [ ] **Create HyDE retriever** (40 min)
  - File: `backend/app/services/search/hyde_retriever.py`
  - Class: `HyDERetriever`
  - Method: `generate_hypothetical_answer(query) -> str`
  - Logic: Use LLM to generate hypothetical answer
  - Prompt: "Generate a detailed answer to this query as if from a document"

- [ ] **Implement HyDE search** (30 min)
  - Method: `retrieve(query, top_k) -> List[Result]`
  - Step 1: Generate hypothetical answer
  - Step 2: Embed hypothetical answer (not query!)
  - Step 3: Search with hypothetical embedding
  - Step 4: Return top_k results
  - Rationale: Hypothesis matches document text better than query

- [ ] **Test HyDE** (30 min)
  - Test: 10 sample queries
  - Compare: HyDE vs standard vs Multi-Query
  - Measure: Retrieval quality
  - Decision: Which strategy performs best?

**Success Criteria**: HyDE implemented, compared with Multi-Query

---

### 5.3 Integration with Hybrid Search

- [ ] **Add retrieval mode selector** (30 min)
  - File: `backend/app/services/search/hybrid_search_service.py`
  - Config: `RETRIEVAL_MODE` (standard, multi_query, hyde)
  - Logic: Route to appropriate retriever based on config
  - Support: Per-query override (API parameter)

- [ ] **Update search endpoint** (20 min)
  - File: `backend/app/api/v1/endpoints/search.py`
  - Add: Optional `retrieval_mode` query parameter
  - Allow: Client to specify which strategy to use
  - Return: Which mode was used in response metadata

- [ ] **Test integration** (20 min)
  - Test: All three modes (standard, multi_query, hyde)
  - Verify: Correct retriever used based on config
  - Verify: Per-query override works
  - Measure: Latency for each mode

**Success Criteria**: Retrieval mode configurable, all modes working

---

### 5.4 Performance Optimization

- [ ] **Parallelize Multi-Query searches** (30 min)
  - Current: Sequential (search 3 queries one by one)
  - Optimization: Parallel (search 3 queries simultaneously)
  - Implementation: asyncio or ThreadPoolExecutor
  - Benefit: 3x faster (200ms overhead instead of 600ms)

- [ ] **Optimize deduplication** (20 min)
  - Current: O(n²) comparison
  - Optimization: Use set for O(n) deduplication
  - Key: chunk_id for exact dedup
  - Test: Same results, faster execution

- [ ] **Benchmark retrieval modes** (20 min)
  - Measure: Latency for each mode
  - Standard: ~200ms
  - Multi-Query (parallel): ~400ms (expect this)
  - HyDE: ~300ms
  - Target: All under 500ms

**Success Criteria**: Multi-Query adds <300ms latency, retrieval quality improved

---

### 5.5 Testing & Validation

- [ ] **Create retrieval evaluation dataset** (30 min)
  - File: `backend/tests/evaluation/retrieval_test_set.json`
  - Format: [{query, relevant_doc_ids}]
  - Create: 20 query-document pairs
  - Coverage: Easy, medium, hard queries

- [ ] **Run retrieval benchmarks** (30 min)
  - Metrics: Precision@K, Recall@K, MRR
  - Compare: Standard vs Multi-Query vs HyDE
  - Record: Which performs best
  - Decision: Set default retrieval mode

**Success Criteria**: Data-driven retrieval mode selection, best mode chosen

---

## Phase 6: Chunking & Testing

**Goal**: Optimize chunking, run RAGAs evaluation, tune hyperparameters
**Time**: 4-5 hours
**Dependencies**: All previous phases

### 6.1 Improve Chunking Strategy

- [ ] **Update chunking parameters** (20 min)
  - File: `backend/app/services/chunking/chunking_service.py`
  - Update: `CHUNKING_TARGET_TOKENS = 700` (from 512)
  - Update: `CHUNKING_MAX_TOKENS = 850` (from 600)
  - Update: `CHUNKING_MIN_TOKENS = 150` (from 100)
  - Update: `CHUNKING_OVERLAP_TOKENS = 150` (from 50)

- [ ] **Implement semantic boundary detection** (60 min)
  - Add: Topic shift detection between sentences
  - Logic: Don't split chunks mid-topic
  - Use: Sentence embeddings similarity
  - If: similarity < threshold, start new chunk
  - Test: Chunks are more coherent

- [ ] **Test new chunking** (30 min)
  - Re-chunk: 10 sample documents
  - Compare: Old vs new chunks
  - Verify: Better context preservation
  - Verify: Chunks don't split mid-topic
  - Measure: Average chunk length (should be ~700 tokens)

- [ ] **Re-process sample documents** (20 min)
  - Delete: Old embeddings for test documents
  - Re-chunk: With new parameters
  - Re-embed: With OpenAI embeddings
  - Re-index: In Qdrant
  - Test: Search quality improvement

**Success Criteria**: Chunks 700 tokens avg, better coherence, 5-10% citation accuracy gain

---

### 6.2 RAGAs Evaluation Framework

- [ ] **Install RAGAs** (5 min)
  - Add to `requirements.txt`: `ragas>=0.1.0`, `datasets>=2.14.0`
  - Run: `pip install ragas datasets`
  - Test import: `from ragas import evaluate`

- [ ] **Create evaluation dataset** (60 min)
  - File: `backend/tests/evaluation/ragas_dataset.json`
  - Format: [{question, contexts, answer, ground_truth}]
  - Create: 20 high-quality Q&A pairs
  - Sources: Actual documents in system
  - Ground truth: Manually verified answers

- [ ] **Create evaluation script** (50 min)
  - File: `backend/tests/evaluation/ragas_eval.py`
  - Load: Test dataset
  - For each query:
    - Run: Full RAG pipeline
    - Collect: contexts, answer, ground_truth
  - Run: RAGAs evaluation
  - Metrics: faithfulness, answer_relevancy, context_precision, context_recall

- [ ] **Run baseline evaluation** (20 min)
  - Config: Standard retrieval, current settings
  - Run: RAGAs on 20 test queries
  - Record: Baseline scores
  - Target: >0.85 on all metrics

**Success Criteria**: RAGAs evaluation working, baseline scores captured

---

### 6.3 Hyperparameter Tuning

- [ ] **Create tuning script** (40 min)
  - File: `backend/scripts/tune_hyperparameters.py`
  - Parameters to tune:
    - RRF_K: [40, 60, 80]
    - RRF_KEYWORD_WEIGHT: [0.3, 0.4, 0.5, 0.6, 0.7]
    - RERANK_TOP_K: [30, 50, 70, 100]
    - MMR_LAMBDA: [0.5, 0.6, 0.7, 0.8]
  - For each combination:
    - Run: RAGAs evaluation
    - Record: Scores
  - Output: Best hyperparameters

- [ ] **Run tuning experiments** (60 min)
  - Test: ~20-30 combinations (grid search)
  - Record: RAGAs scores for each
  - Identify: Best combination
  - Update: Config with optimal values

- [ ] **Validate tuned parameters** (30 min)
  - Run: Full evaluation with tuned parameters
  - Compare: vs baseline
  - Verify: Improvement in all metrics
  - Record: Final RAGAs scores

**Success Criteria**: Hyperparameters optimized, RAGAs scores >0.90

---

### 6.4 End-to-End Performance Testing

- [ ] **Create performance test script** (40 min)
  - File: `backend/tests/performance/load_test.py`
  - Simulate: 100 concurrent queries
  - Measure: Latency (p50, p95, p99)
  - Measure: Throughput (queries/sec)
  - Measure: Error rate

- [ ] **Run load tests** (30 min)
  - Test: With all optimizations enabled
  - Record: Performance metrics
  - Verify: p95 latency <3s
  - Verify: No errors or timeouts

- [ ] **Identify bottlenecks** (30 min)
  - Profile: Each component (parsing, embedding, search, generation)
  - Measure: Time spent in each stage
  - Identify: Slowest component
  - Optimize: If any component >1s

- [ ] **Test cost at scale** (20 min)
  - Run: 100 queries
  - Calculate: Total cost (LLM + embeddings + vision)
  - Verify: Cost per query <$0.05
  - Project: Monthly costs at 10K queries

**Success Criteria**: p95 <3s, cost <$0.05/query, no bottlenecks >1s

---

### 6.5 Final Validation

- [ ] **Run comprehensive RAGAs evaluation** (30 min)
  - Test: Full 20-query dataset
  - Config: All optimizations enabled
  - Record: Final RAGAs scores
  - Target: All metrics >0.90

- [ ] **Test all retrieval modes** (30 min)
  - Standard: Baseline
  - Multi-Query: Should be +15-25%
  - HyDE: Compare with Multi-Query
  - Record: Which performs best

- [ ] **Test all provider combinations** (40 min)
  - Parser: Docling, MinerU, Smart
  - LLM: OpenRouter (GPT, Claude, Gemini)
  - Embeddings: OpenAI, BGE-M3
  - Vector: Qdrant, pgvector
  - Record: Best combination

- [ ] **Document final configuration** (30 min)
  - File: `dev/active/querybox-backend/FINAL_CONFIG.md`
  - Document: Optimal settings for each component
  - Include: RAGAs scores, latency, cost
  - Include: Recommendations for production

- [ ] **Create demo script** (30 min)
  - File: `backend/scripts/demo.py`
  - Show: Sample queries with impressive results
  - Highlight: Accurate citations, fast responses
  - Compare: Before/after metrics (old vs new system)

**Success Criteria**: 95-99% accuracy, <2s latency, comprehensive documentation

---

## Success Validation Checklist

### Accuracy (RAGAs Metrics)
- [ ] Faithfulness: >0.90 (no hallucinations)
- [ ] Answer Relevancy: >0.90 (answers the question)
- [ ] Context Precision: >0.80 (retrieved chunks relevant)
- [ ] Context Recall: >0.85 (all relevant info retrieved)
- [ ] Citation Accuracy: >95% (citations verifiable)

### Performance (Latency)
- [ ] p50 Latency: <1.5s
- [ ] p95 Latency: <3s
- [ ] p99 Latency: <5s
- [ ] Parsing: <2s per document
- [ ] Embedding: <200ms per query
- [ ] Vector Search: <100ms (Qdrant)

### Cost
- [ ] Demo total: <$20
- [ ] Per-query: <$0.05
- [ ] First month projection: <$50

### Architecture
- [ ] All components swappable via config
- [ ] No breaking changes to API
- [ ] Backward compatible (can revert to old setup)
- [ ] Clear documentation and demos

---

## Getting Started

**Recommended Path**:
1. Start with **Phase 1** (Modular Architecture) - Most important foundation
2. Do **Phase 3** (LLM & Embeddings) next - Biggest accuracy win
3. Then **Phase 4** (Qdrant) - Speed improvement
4. Then **Phase 2** (Parsing) - Final accuracy push
5. Then **Phase 5** (Advanced Retrieval) - Extra boost
6. Finally **Phase 6** (Testing & Tuning) - Validation

**Time Management**:
- Phases 1-3: Day 1 (8-10 hours)
- Phases 4-6: Day 2 (8-10 hours)
- Buffer: 2-4 hours for debugging and testing

**Priority if Time Short**:
1. ✅ Phase 1 (modular architecture) - Essential
2. ✅ Phase 3 (OpenRouter + OpenAI) - Biggest win
3. ✅ Phase 6.2-6.3 (RAGAs evaluation) - Measure success
4. ⚠️ Phase 4 (Qdrant) - Nice to have
5. ⚠️ Phase 5 (Multi-Query) - Nice to have
6. ⚠️ Phase 2 (MinerU + Vision) - Nice to have

**Minimum Viable Demo (6-8 hours)**:
- Phase 1: Modular architecture
- Phase 3: OpenRouter + OpenAI embeddings
- Phase 6.1: Better chunking
- Phase 6.2: RAGAs evaluation
- Result: 70% improvement, solid foundation

Ready to start! Begin with Phase 1.1 - Create Abstract Base Classes 🚀
