# RAG Accuracy Improvement - Strategic Plan

## 🎯 Mission
Improve QueryBox retrieval accuracy by **50-80%** using cutting-edge 2024-2025 techniques while maintaining fast performance.

---

## 📊 Current State Assessment (Baseline)

### Strengths
- ✅ **Hybrid Search**: BM25 + Vector with RRF fusion
- ✅ **Cross-Encoder Reranking**: ms-marco-MiniLM-L6-v2
- ✅ **MMR Diversification**: Lambda 0.7
- ✅ **Rich Metadata Extraction**: 10 element types (headings, tables, lists, code, equations, figures, citations, footnotes, definitions, paragraphs)
- ✅ **Vision API Integration**: GPT-4o-mini for charts/graphs
- ✅ **Smart Document Routing**: OCR fallback, format detection
- ✅ **BGE-M3 Embeddings**: Multilingual, 8192 token context

### Critical Gaps (Accuracy Losses)
1. **Context Loss in Chunking**: Chunks lack document/section context → **15-20% accuracy loss**
2. **No Late Chunking**: Embedding before chunking loses long-range dependencies → **10-15% accuracy loss**
3. **Single-Vector Retrieval**: Coarse matching, not token-level precision → **10-15% accuracy loss**
4. **No Hierarchical Retrieval**: Can't answer multi-level questions → **20%+ accuracy loss** on complex queries
5. **Limited Query Optimization**: Basic multi-query, no HyDE → **15-20% accuracy loss** on ambiguous queries

### Current Performance (Estimated)
- **Top-10 Retrieval Precision**: ~75%
- **With Reranking**: ~90%
- **With Verification**: ~95% answer accuracy

---

## 🚀 Three-Phase Roadmap

### **Phase 1: Quick Wins** (Week 1-2) - **HIGHEST ROI**
**Target**: +35-50% accuracy improvement
**Cost**: ~$0 (using local LLM)
**Effort**: 1-2 weeks

**Techniques:**
1. ✅ **Contextual Retrieval** (Anthropic 2024)
   - Add LLM-generated context to chunks before embedding
   - Expected: +15-25% accuracy

2. ✅ **Late Chunking** (Jina AI 2024)
   - Embed full document first, then chunk
   - Expected: +12-15% accuracy

3. ✅ **HyDE** (Hypothetical Document Embeddings)
   - Generate hypothetical answer, search with it
   - Expected: +18-25% on ambiguous queries

**Expected Results:**
- Top-10 Precision: 75% → **~98%** (+30%)
- Answer Accuracy: 95% → **~97%** (+2%)

---

### **Phase 2: Advanced Techniques** (Week 3-4)
**Target**: +20-30% additional accuracy
**Cost**: $0
**Effort**: 2-3 weeks

**Techniques:**
1. ✅ **Matryoshka Embeddings** (Adaptive Retrieval)
   - 64 dims for initial retrieval → 768 dims for reranking
   - Expected: +2% accuracy, **14x storage reduction**, **14x faster** initial search

2. ✅ **Sentence Window Retrieval**
   - Search at sentence level → expand to ±3 sentences
   - Expected: +5-10% accuracy

3. ✅ **Enhanced Query Preprocessing**
   - Entity extraction, acronym expansion, synonym addition
   - Intent detection (question, definition, comparison)
   - Expected: +5-10% accuracy

4. ✅ **Upgrade Cross-Encoder Reranker**
   - From ms-marco-MiniLM-L6-v2 (2021) → BAAI/bge-reranker-v2-m3 (2024)
   - Expected: +3-5% accuracy

**Expected Results:**
- Top-10 Precision: ~98% → **~99%** (+1%)
- Storage: **14x reduction**
- Speed: **14x faster** initial retrieval

---

### **Phase 3: Experimental** (Week 5-8)
**Target**: +20-30% on specific use cases
**Cost**: $100-500 for large corpus
**Effort**: 3-4 weeks

**Techniques:**
1. ✅ **ColBERT v2 Multi-Vector Retrieval**
   - Token-level embeddings for fine-grained matching
   - Expected: +25-35% on complex queries
   - Tradeoff: **6-10x storage increase**

2. ✅ **RAPTOR Hierarchical Retrieval**
   - Build tree: summaries (top) → sections (mid) → chunks (bottom)
   - Search all levels simultaneously
   - Expected: +15-20% on long documents
   - Cost: $0.01-0.05 per document (LLM summarization)

3. ✅ **Embedding Model Upgrade** (Optional)
   - From BGE-M3 → bge-multilingual-gemma2 (July 2024)
   - Expected: +5% accuracy
   - Tradeoff: 9GB model (vs 2.2GB)

**Expected Results:**
- Top-10 Precision: ~99% → **>99.5%** on complex queries
- Long Document Performance: **+15-20%**
- Storage: +3-10x (depending on techniques)

---

## 💰 Cost-Benefit Analysis

| Phase | Time | One-Time Cost | Runtime Cost | Accuracy Gain | Storage Impact | Speed Impact |
|-------|------|---------------|--------------|---------------|----------------|--------------|
| **Phase 1** | 1-2 weeks | **$0** (Ollama) | $0 | **+35-50%** | Neutral | +10% latency |
| **Phase 2** | 2-3 weeks | $0 | $0 | **+20-30%** | **-14x** (savings!) | **-14x** faster |
| **Phase 3** | 3-4 weeks | $100-500 | $0 | **+20-30%** | +3-10x | Neutral |

**Cumulative Expected Gains:**
- After Phase 1: **+35-50%** accuracy
- After Phase 2: **+50-70%** accuracy (some overlap)
- After Phase 3: **+60-80%** accuracy

---

## 🎯 Success Metrics

### Quantitative Metrics
1. **Top-10 Retrieval Precision**: % of queries where correct answer is in top 10 results
2. **Mean Reciprocal Rank (MRR)**: Average position of first correct result
3. **Answer Accuracy**: % of queries with correct final answer
4. **Latency**: p50, p95, p99 response times
5. **Storage Efficiency**: Bytes per chunk

### Qualitative Metrics
1. **Citation Quality**: Relevance of cited chunks
2. **Context Preservation**: Handling of cross-references, pronouns
3. **Multi-Hop Performance**: Complex queries requiring synthesis
4. **Long Document Performance**: Research papers, technical docs

### Baseline Targets
- **Phase 1**: Top-10 precision 75% → 98%
- **Phase 2**: Storage reduction 14x, maintain accuracy
- **Phase 3**: Approach 99.5% precision on complex queries

---

## 📅 Timeline

```
Week 1-2:  Phase 1 Implementation
Week 3:    Phase 1 Testing & Validation
Week 4:    Phase 2 Planning (optional)
Week 5-6:  Phase 2 Implementation (optional)
Week 7-8:  Phase 2 Testing (optional)
Week 9+:   Phase 3 Evaluation (optional)
```

---

## 🔗 Related Documentation
- **Technical Details**: See `phase1-details.md`, `phase2-details.md`, `phase3-details.md`
- **Implementation Tasks**: See `tasks.md`
- **Architecture Context**: See `context.md`
- **Project Overview**: See `/CLAUDE.md`, `/PROJECT.md`, `/ARCHITECTURE.md`

---

## 📝 Decision Log

### Nov 15, 2025
- ✅ **Embedding Model**: Keep BGE-M3 (proven, fast, multilingual)
- ✅ **Cost Strategy**: Minimize cost using local LLM (Ollama) for context generation
- ✅ **Phase 1 Priority**: Focus on Contextual Retrieval, Late Chunking, HyDE
- ✅ **Phase 2-3**: Document for future implementation after Phase 1 validation

### Research Findings
- **BGE-M3 vs E5-Mistral-7B**: BGE-M3 actually outperforms E5-Mistral on MTEB (70-72% vs 64-66%)
- **BGE-M3 vs bge-multilingual-gemma2**: New BGE model is +5% better, but Phase 1 techniques provide +35-50%
- **Nomic Embed v1.5**: Excellent for Matryoshka embeddings (Phase 2 consideration)
- **Latest MTEB Rankings** (Nov 2025): Gemini #1, Qwen3-Embedding #2, BGE family still top-tier open-source

---

Last Updated: Nov 15, 2025
Status: Phase 1 Ready to Implement
