# RAG Accuracy Improvement - Implementation Tasks

## ✅ Phase 0: Setup & Documentation
- [x] Research cutting-edge RAG techniques (2024-2025)
- [x] Compare embedding models (BGE-M3 vs E5-Mistral vs Nomic)
- [x] Create dev-docs structure
- [x] Document all 3 phases (plan.md, context.md, phase*-details.md)
- [ ] Set up Ollama for local LLM
- [ ] Create benchmark test query set (50-100 queries)
- [ ] Establish baseline metrics (current accuracy, latency)

---

## 🚀 Phase 1: Quick Wins (Week 1-2)

### Task 1.1: Contextual Retrieval Implementation
**Goal**: Add LLM-generated context to chunks before embedding
**Expected Gain**: +15-25% accuracy
**Effort**: 2-3 days

#### Subtasks:
- [ ] 1.1.1: Create `backend/app/services/chunking/contextual_enrichment.py`
  - [ ] Implement `ContextualEnricher` class
  - [ ] Add Ollama integration (llama3.2:3b)
  - [ ] Add Haiku fallback option
  - [ ] Create prompt template for context generation
  - [ ] Add caching for generated contexts (Redis)

- [ ] 1.1.2: Update `backend/app/services/chunking/chunking_service.py`
  - [ ] Add `_enrich_chunk_with_context()` method
  - [ ] Call contextual enrichment after chunk creation
  - [ ] Store both original + contextual text

- [ ] 1.1.3: Update `backend/app/schemas/chunk.py`
  - [ ] Add `contextual_prefix` field to ChunkMetadata
  - [ ] Add `contextual_text` field to Chunk model

- [ ] 1.1.4: Update embedding pipeline
  - [ ] Modify `backend/app/services/embeddings.py`
  - [ ] Embed contextual text instead of original
  - [ ] Maintain original text for display

- [ ] 1.1.5: Add configuration
  - [ ] Add config variables to `backend/app/core/config.py`
  - [ ] Add environment variables to `.env.example`

- [ ] 1.1.6: Testing
  - [ ] Unit tests for contextual enrichment
  - [ ] Integration tests for full pipeline
  - [ ] Benchmark accuracy improvement

---

### Task 1.2: Late Chunking Implementation
**Goal**: Embed full documents first, then chunk
**Expected Gain**: +12-15% accuracy
**Effort**: 2-3 days

#### Subtasks:
- [ ] 1.2.1: Create `backend/app/services/embeddings/late_chunking.py`
  - [ ] Implement `LateChunkingEmbedder` class
  - [ ] Tokenize full document (up to 8192 tokens)
  - [ ] Run through transformer (full context)
  - [ ] Apply mean pooling per chunk boundary
  - [ ] Return chunk embeddings with metadata

- [ ] 1.2.2: Update `backend/app/services/embeddings.py`
  - [ ] Add `embed_with_late_chunking()` method
  - [ ] Add mode selection (standard vs late chunking)
  - [ ] Handle documents > 8192 tokens (batching)

- [ ] 1.2.3: Update document processing pipeline
  - [ ] Modify `backend/app/services/document_processing/processor.py`
  - [ ] Add late chunking mode option
  - [ ] Pass chunk boundaries to embedding service

- [ ] 1.2.4: Add configuration
  - [ ] Add `ENABLE_LATE_CHUNKING` flag
  - [ ] Add `LATE_CHUNKING_MAX_DOC_TOKENS` setting
  - [ ] Add `LATE_CHUNKING_BATCH_SIZE` setting

- [ ] 1.2.5: Testing
  - [ ] Unit tests for late chunking logic
  - [ ] Test pronoun resolution (e.g., "it" → "Berlin")
  - [ ] Test cross-reference preservation
  - [ ] Benchmark accuracy on entity-heavy documents
  - [ ] Monitor memory usage

---

### Task 1.3: HyDE Implementation
**Goal**: Generate hypothetical answers for better retrieval
**Expected Gain**: +18-25% on ambiguous queries
**Effort**: 1-2 days

#### Subtasks:
- [ ] 1.3.1: Create `backend/app/services/search/hyde.py`
  - [ ] Implement `HyDESearcher` class
  - [ ] Add query complexity detector (heuristics)
  - [ ] Add hypothetical answer generator (Ollama/Haiku)
  - [ ] Implement HyDE search logic

- [ ] 1.3.2: Create query complexity detector
  - [ ] Detect ambiguous queries (multi-hop, comparison)
  - [ ] Use heuristics (question words, sentence structure)
  - [ ] Optional: Use LLM for complexity scoring

- [ ] 1.3.3: Update `backend/app/services/search/search_service.py`
  - [ ] Add HyDE routing logic
  - [ ] Add `enable_hyde` parameter
  - [ ] Fall back to standard search if HyDE fails

- [ ] 1.3.4: Update API endpoints
  - [ ] Add `enable_hyde` to UnifiedSearchQuery schema
  - [ ] Add HyDE metadata to response
  - [ ] Document new parameter in OpenAPI

- [ ] 1.3.5: Add configuration
  - [ ] Add `ENABLE_HYDE` flag
  - [ ] Add HyDE LLM settings
  - [ ] Add complexity threshold

- [ ] 1.3.6: Testing
  - [ ] Unit tests for HyDE logic
  - [ ] Test on ambiguous queries
  - [ ] Test on multi-hop questions
  - [ ] Benchmark accuracy improvement
  - [ ] Monitor latency impact (~200ms expected)

---

### Task 1.4: Testing & Validation
**Goal**: Measure accuracy improvements and validate performance
**Effort**: 2-3 days

#### Subtasks:
- [ ] 1.4.1: Create test query set
  - [ ] Collect 50-100 representative queries
  - [ ] Include: simple, complex, ambiguous, multi-hop
  - [ ] Create ground truth answers
  - [ ] Store in `tests/data/benchmark_queries.json`

- [ ] 1.4.2: Implement benchmark suite
  - [ ] Create `tests/benchmarks/test_accuracy.py`
  - [ ] Measure Top-10 precision
  - [ ] Measure Mean Reciprocal Rank (MRR)
  - [ ] Measure answer accuracy
  - [ ] Measure latency (p50, p95, p99)

- [ ] 1.4.3: Run A/B tests
  - [ ] Baseline (current system)
  - [ ] With contextual retrieval
  - [ ] With late chunking
  - [ ] With HyDE
  - [ ] All combined

- [ ] 1.4.4: Validate results
  - [ ] Compare metrics before/after
  - [ ] Analyze failure cases
  - [ ] Identify areas for improvement

- [ ] 1.4.5: Performance optimization
  - [ ] Profile slow operations
  - [ ] Optimize batch sizes
  - [ ] Tune LLM timeouts
  - [ ] Add caching where beneficial

- [ ] 1.4.6: Documentation
  - [ ] Update README with new features
  - [ ] Document configuration options
  - [ ] Create migration guide for existing users
  - [ ] Add examples to API documentation

---

## 📊 Phase 1 Success Criteria

### Accuracy Targets
- [ ] Top-10 Precision: 75% → **≥95%** (+27% minimum)
- [ ] Mean Reciprocal Rank: Current → **+20% improvement**
- [ ] Answer Accuracy: 95% → **≥97%**

### Performance Targets
- [ ] Indexing latency: **<2x slowdown** (acceptable for +35-50% accuracy)
- [ ] Search latency: **<500ms increase** for complex queries
- [ ] Memory usage: **<30% increase** during embedding

### Cost Targets
- [ ] Contextual retrieval: **$0 using Ollama** (or <$50 for 10K docs with Haiku)
- [ ] HyDE: **$0 using Ollama** (or <$0.005 per query with Haiku)

---

## 🎯 Phase 2: Advanced Techniques (Week 3-4)

### Task 2.1: Matryoshka Embeddings
**Goal**: Adaptive dimension retrieval (64-768 dims)
**Expected Gain**: +2% accuracy, 14x storage reduction
**Effort**: 2-3 days

#### Subtasks:
- [ ] 2.1.1: Evaluate Nomic Embed v1.5
  - [ ] Test on sample documents
  - [ ] Compare accuracy vs BGE-M3
  - [ ] Measure inference speed

- [ ] 2.1.2: Implement adaptive retrieval
  - [ ] Stage 1: 64-dim for initial retrieval (top-100)
  - [ ] Stage 2: 768-dim for reranking (top-10)

- [ ] 2.1.3: Migrate existing embeddings
  - [ ] Re-embed all chunks with Nomic v1.5
  - [ ] Store multiple dimension versions

- [ ] 2.1.4: Update vector store
  - [ ] Support multi-dimension storage
  - [ ] Optimize search for small dimensions

- [ ] 2.1.5: Testing & benchmarking
  - [ ] Measure accuracy at different dimensions
  - [ ] Measure storage reduction (expect 14x)
  - [ ] Measure search speed improvement (expect 14x)

---

### Task 2.2: Sentence Window Retrieval
**Goal**: Search sentences, expand to ±3 sentence context
**Expected Gain**: +5-10% accuracy
**Effort**: 2-3 days

#### Subtasks:
- [ ] 2.2.1: Implement sentence-level indexing
  - [ ] Split chunks into sentences
  - [ ] Embed each sentence
  - [ ] Store sentence-to-chunk mapping

- [ ] 2.2.2: Create sentence window expander
  - [ ] Retrieve top-k sentences
  - [ ] Expand to ±3 sentences
  - [ ] Merge overlapping windows

- [ ] 2.2.3: Update search pipeline
  - [ ] Add sentence window mode
  - [ ] Configure window size (default: ±3)

- [ ] 2.2.4: Testing
  - [ ] Test precision (small context)
  - [ ] Test recall (expanded context)
  - [ ] Compare vs standard chunk retrieval

---

### Task 2.3: Enhanced Query Preprocessing
**Goal**: Extract entities, expand acronyms, add synonyms
**Expected Gain**: +5-10% accuracy
**Effort**: 2-3 days

#### Subtasks:
- [ ] 2.3.1: Implement entity extraction
  - [ ] Use spaCy NER
  - [ ] Boost chunks with matching entities

- [ ] 2.3.2: Add acronym expansion
  - [ ] Build acronym dictionary
  - [ ] Expand in queries (ML → Machine Learning)

- [ ] 2.3.3: Add synonym generation
  - [ ] Use WordNet or LLM
  - [ ] Expand query with synonyms

- [ ] 2.3.4: Implement intent detection
  - [ ] Classify query type (question, definition, comparison, how-to)
  - [ ] Route to optimized retrieval strategy per intent

- [ ] 2.3.5: Testing
  - [ ] Test entity matching accuracy
  - [ ] Test acronym expansion
  - [ ] Test synonym recall

---

### Task 2.4: Upgrade Cross-Encoder Reranker
**Goal**: Upgrade from ms-marco-MiniLM to bge-reranker-v2-m3
**Expected Gain**: +3-5% accuracy
**Effort**: 1 day

#### Subtasks:
- [ ] 2.4.1: Install BAAI/bge-reranker-v2-m3
- [ ] 2.4.2: Update config (model name, max_length=8192)
- [ ] 2.4.3: Test on sample queries
- [ ] 2.4.4: Benchmark accuracy improvement
- [ ] 2.4.5: Deploy to production

---

## 🔬 Phase 3: Experimental (Week 5-8)

### Task 3.1: ColBERT v2 Multi-Vector Retrieval
**Goal**: Token-level embeddings for fine-grained matching
**Expected Gain**: +25-35% on complex queries
**Effort**: 1-2 weeks
**Tradeoff**: 6-10x storage increase

#### Subtasks:
- [ ] 3.1.1: Evaluate ColBERT models
  - [ ] Test jinaai/jina-colbert-v2
  - [ ] Test RAGatouille wrapper

- [ ] 3.1.2: Implement ColBERT embedding
  - [ ] Generate token-level embeddings
  - [ ] Apply residual compression

- [ ] 3.1.3: Implement MaxSim scoring
  - [ ] Late interaction between query & document tokens

- [ ] 3.1.4: Update vector store
  - [ ] Support multi-vector storage (Qdrant native support)
  - [ ] Optimize for token-level search

- [ ] 3.1.5: Testing & benchmarking
  - [ ] Test on technical/legal documents
  - [ ] Measure accuracy improvement
  - [ ] Measure storage cost (expect 6-10x)

- [ ] 3.1.6: Cost-benefit analysis
  - [ ] Decide if accuracy gain justifies storage cost
  - [ ] Consider hybrid: ColBERT for specific document types only

---

### Task 3.2: RAPTOR Hierarchical Retrieval
**Goal**: Build tree of summaries, search all levels
**Expected Gain**: +15-20% on long documents
**Effort**: 1-2 weeks
**Cost**: $0.01-0.05 per document

#### Subtasks:
- [ ] 3.2.1: Implement tree builder
  - [ ] Layer 0: Base chunks (100 tokens)
  - [ ] Layer 1+: GMM clustering + summarization
  - [ ] Store tree structure in database

- [ ] 3.2.2: Implement multi-level retrieval
  - [ ] Search all layers simultaneously
  - [ ] Combine results with weighted scoring

- [ ] 3.2.3: Add LLM summarization
  - [ ] Generate cluster summaries (Ollama/Haiku)
  - [ ] Optimize for cost (~$0.01-0.05/doc)

- [ ] 3.2.4: Update database schema
  - [ ] Add tree structure tables
  - [ ] Store layer relationships

- [ ] 3.2.5: Testing & benchmarking
  - [ ] Test on long research papers
  - [ ] Test multi-hop questions
  - [ ] Measure accuracy improvement

- [ ] 3.2.6: Cost analysis
  - [ ] Calculate LLM cost for corpus
  - [ ] Decide if worth it for your use case

---

### Task 3.3: Optional Embedding Model Upgrade
**Goal**: Upgrade from BGE-M3 to bge-multilingual-gemma2
**Expected Gain**: +5% accuracy
**Effort**: 1-2 days
**Tradeoff**: 9GB model vs 2.2GB

#### Subtasks:
- [ ] 3.3.1: Install bge-multilingual-gemma2
- [ ] 3.3.2: Test on sample documents
- [ ] 3.3.3: Benchmark accuracy vs BGE-M3
- [ ] 3.3.4: Measure inference speed
- [ ] 3.3.5: Re-embed all documents (if upgrading)
- [ ] 3.3.6: Cost-benefit decision

---

## 📈 Progress Tracking

### Current Status
- **Phase**: 0 (Setup & Documentation)
- **Completion**: 60% (documentation complete, setup pending)
- **Next Task**: Set up Ollama + create benchmark query set

### Timeline
- **Week 1-2**: Phase 1 implementation
- **Week 3**: Phase 1 testing & validation
- **Week 4+**: Evaluate Phase 2-3 based on Phase 1 results

---

Last Updated: Nov 15, 2025
Status: Ready to Begin Implementation
