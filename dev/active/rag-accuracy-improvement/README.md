# RAG Accuracy Improvement Project

**Goal**: Improve QueryBox retrieval accuracy by **50-80%** using cutting-edge 2024-2025 RAG techniques.

**Status**: Phase 1 Ready to Implement
**Last Updated**: Nov 15, 2025

---

## 📁 Documentation Structure

```
dev/active/rag-accuracy-improvement/
├── README.md              ← You are here (project overview)
├── plan.md                ← Strategic plan (all 3 phases)
├── context.md             ← Architecture, key files, decisions
├── tasks.md               ← Implementation checklist
├── phase1-details.md      ← Phase 1 implementation guide
├── phase2-details.md      ← Phase 2 implementation guide
└── phase3-details.md      ← Phase 3 implementation guide
```

---

## 🎯 Quick Summary

### Current Baseline
- **Retrieval Method**: Hybrid (BM25 + Vector with RRF fusion)
- **Reranking**: Cross-encoder (ms-marco-MiniLM-L6-v2)
- **Embeddings**: BGE-M3 (1024 dims, 8192 context)
- **Estimated Accuracy**: ~75% top-10 precision

### Target After Phase 1
- **New Techniques**: Contextual retrieval, Late chunking, HyDE
- **Expected Accuracy**: ~98% top-10 precision (+30%)
- **Cost**: $0 (using Ollama for local LLM)
- **Timeline**: 1-2 weeks

---

## 🚀 Three-Phase Roadmap

### **Phase 1: Quick Wins** (Week 1-2) - **IMPLEMENT THIS FIRST**
**Target**: +35-50% accuracy improvement

1. **Contextual Retrieval** (Anthropic 2024)
   - Add LLM-generated context to chunks
   - Expected: +15-25% accuracy

2. **Late Chunking** (Jina AI 2024)
   - Embed full doc first, then chunk
   - Expected: +12-15% accuracy

3. **HyDE** (Hypothetical Document Embeddings)
   - Generate hypothetical answer, search with it
   - Expected: +18-25% on ambiguous queries

**See**: `phase1-details.md` for implementation guide

---

### **Phase 2: Advanced Techniques** (Week 3-4) - **OPTIONAL**
**Target**: +20-30% additional accuracy

1. **Matryoshka Embeddings** (Nomic v1.5)
   - Adaptive dimensions (64-768)
   - 14x storage reduction

2. **Sentence Window Retrieval**
   - Search sentences, expand context
   - +5-10% accuracy

3. **Enhanced Query Preprocessing**
   - Entity extraction, acronym expansion
   - +5-10% accuracy

4. **Upgrade Cross-Encoder**
   - bge-reranker-v2-m3 (2024)
   - +3-5% accuracy

**See**: `phase2-details.md` for implementation guide

---

### **Phase 3: Experimental** (Week 5-8) - **ADVANCED USE CASES**
**Target**: +20-30% on specific documents

1. **ColBERT v2** (Token-level embeddings)
   - +25-35% on complex queries
   - Tradeoff: 6-10x storage

2. **RAPTOR** (Hierarchical retrieval)
   - +15-20% on long documents
   - Cost: $0.01-0.05 per document

3. **Optional Model Upgrade**
   - bge-multilingual-gemma2
   - +5% accuracy (skip - Phase 1 provides more)

**See**: `phase3-details.md` for implementation guide

---

## 📊 Expected Results

| Phase | Timeline | Cost | Accuracy Gain | Storage Impact | Speed Impact |
|-------|----------|------|---------------|----------------|--------------|
| **Phase 1** | 1-2 weeks | **$0** | **+35-50%** | Neutral | +10% latency |
| **Phase 2** | 2-3 weeks | $0 | +20-30% | **-14x** (savings!) | **14x faster** |
| **Phase 3** | 3-4 weeks | $100-500 | +20-30% | +3-10x | Neutral |

**Cumulative**: +60-80% accuracy improvement (after all 3 phases)

---

## 🔑 Key Decisions Made

### Embedding Model
- **Decision**: Keep BGE-M3 (not upgrading)
- **Rationale**:
  - BGE-M3 already strong (70-72% MTEB, better than E5-Mistral-7B)
  - Newer bge-multilingual-gemma2 only +5% improvement
  - Phase 1 techniques provide +35-50% without model change
  - Can revisit in Phase 3 if needed

### Cost Strategy
- **Decision**: Use local LLM (Ollama) for context generation
- **Rationale**:
  - Near-zero cost vs $0.001/chunk for GPT-4o-mini
  - Fast inference (~100ms with llama3.2:3b)
  - Can upgrade to Haiku if quality insufficient

### Implementation Priority
- **Decision**: Phase 1 → Measure → Decide on Phase 2/3
- **Rationale**:
  - Phase 1 provides highest ROI (+35-50%)
  - Validate approach before investing in Phase 2/3
  - Some techniques (ColBERT, RAPTOR) only needed for specific use cases

---

## 🛠️ Implementation Checklist

### Prerequisites
- [ ] Set up Ollama (`curl -fsSL https://ollama.com/install.sh | sh`)
- [ ] Pull llama3.2:3b model (`ollama pull llama3.2:3b`)
- [ ] Create benchmark query set (50-100 queries)
- [ ] Establish baseline metrics

### Phase 1 Tasks (See `tasks.md` for details)
- [ ] **Task 1.1**: Implement Contextual Retrieval (2-3 days)
- [ ] **Task 1.2**: Implement Late Chunking (2-3 days)
- [ ] **Task 1.3**: Implement HyDE (1-2 days)
- [ ] **Task 1.4**: Testing & Validation (2-3 days)

### Success Criteria
- [ ] Top-10 Precision: 75% → **≥95%**
- [ ] Answer Accuracy: 95% → **≥97%**
- [ ] Indexing latency: <2x slowdown
- [ ] Search latency: <500ms increase

---

## 📖 How to Use This Documentation

### 1. **Read the Plan First**
Start with `plan.md` to understand:
- Overall strategy
- Why these techniques?
- Expected outcomes

### 2. **Understand the Context**
Read `context.md` to learn:
- Current architecture
- Key files to modify
- Integration points
- Risks and mitigations

### 3. **Follow the Tasks**
Use `tasks.md` as your implementation checklist:
- Step-by-step subtasks
- Dependencies
- Testing requirements

### 4. **Deep Dive into Phase Details**
When implementing:
- `phase1-details.md`: Full code examples, config, testing
- `phase2-details.md`: Advanced techniques (future)
- `phase3-details.md`: Experimental approaches (future)

---

## 🔬 Research Sources

### Techniques
1. **Contextual Retrieval**: [Anthropic Blog (Sep 2024)](https://www.anthropic.com/news/contextual-retrieval)
2. **Late Chunking**: [Jina AI arXiv:2409.04701 (Sep 2024)](https://arxiv.org/abs/2409.04701)
3. **RAPTOR**: [Stanford ICLR 2024](https://arxiv.org/abs/2401.18059)
4. **ColBERT v2**: [Stanford NLP](https://github.com/stanford-futuredata/ColBERT)
5. **HyDE**: [Original Paper](https://arxiv.org/abs/2212.10496)

### Models
1. **BGE-M3**: [BAAI GitHub](https://github.com/FlagOpen/FlagEmbedding)
2. **Nomic Embed v1.5**: [Nomic AI](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5)
3. **bge-reranker-v2-m3**: [Hugging Face](https://huggingface.co/BAAI/bge-reranker-v2-m3)
4. **Jina ColBERT v2**: [Jina AI](https://huggingface.co/jinaai/jina-colbert-v2)

### Benchmarks
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [BEIR Benchmark](https://github.com/beir-cellar/beir)

---

## 🤝 Contributing

When implementing these techniques:

1. **Update tasks.md** as you complete items
2. **Document decisions** in this README
3. **Add test results** to `phase*-details.md`
4. **Share learnings** in `context.md` (Architecture Decisions section)

---

## 📞 Questions?

- **Architecture questions**: See `context.md`
- **Implementation details**: See `phase*-details.md`
- **Progress tracking**: See `tasks.md`
- **Overall strategy**: See `plan.md`

---

## 🎯 Next Steps

**To start implementation:**

1. Read `plan.md` (10 min)
2. Read `context.md` (15 min)
3. Set up Ollama (5 min)
4. Create benchmark query set (30 min)
5. Open `tasks.md` and start Phase 1, Task 1.1

**Good luck! 🚀**

---

Last Updated: Nov 15, 2025
Maintained By: QueryBox Core Team
