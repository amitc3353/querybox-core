# QueryBox Future Work

This directory contains documentation for **deferred but planned** features and enhancements.

## 📁 Structure

```
dev/future/
├── README.md                   ← You are here
├── ragas-evaluation/          ← RAGAs framework for testing & tuning
└── remaining-backend-tasks/   ← Remaining items from querybox-backend
```

---

## 🎯 Priority Levels

### **High Priority** (Do Next)
- **RAG Accuracy Improvement** (in `dev/active/`) - Already planned, Phase 1 ready
  - Contextual Retrieval: +15-25% accuracy
  - Late Chunking: +12-15% accuracy
  - HyDE: +18-25% on ambiguous queries

### **Medium Priority** (Do After)
- **RAGAs Evaluation** (in `dev/future/ragas-evaluation/`)
  - Establish baseline metrics
  - Hyperparameter tuning
  - Performance validation

### **Low Priority** (Optional)
- **Multi-Query RAG Testing** (in `dev/future/remaining-backend-tasks/`)
  - Integration testing with real API
  - Performance benchmarking
  - Cost validation

---

## 🚀 Recommended Sequence

1. **Complete RAG Accuracy Improvement Phase 1** (1-2 weeks)
   - See: `dev/active/rag-accuracy-improvement/`
   - Impact: +35-50% accuracy improvement
   - Cost: $0 (using Ollama)

2. **Add RAGAs Evaluation** (4-5 hours)
   - See: `dev/future/ragas-evaluation/`
   - Impact: Measurable metrics, data-driven tuning
   - Cost: $0 (evaluation only)

3. **Optional: Complete Multi-Query Testing** (1.5 hours)
   - See: `dev/future/remaining-backend-tasks/`
   - Impact: Validate 15-25% accuracy claim
   - Cost: <$5 (testing with OpenRouter)

---

## 📊 Current System State

### Completed (Ready for Use)
✅ Modular architecture (swap components via config)
✅ Smart document routing (99% parsing)
✅ Vision API integration (charts/graphs)
✅ OpenRouter LLM provider (GPT, Claude, Gemini)
✅ OpenAI embeddings (better retrieval)
✅ Qdrant infrastructure (ready, disabled)
✅ Multi-Query RAG (implemented, needs testing)

### In Progress
🔄 RAG Accuracy Improvement (Phase 1 planning complete)

### Deferred (This Folder)
⏭️ RAGAs Evaluation Framework
⏭️ Multi-Query RAG validation testing
⏭️ Hyperparameter tuning

---

## 🔗 Related Documentation

- **Active Work**: `dev/active/` - What you should work on now
- **Completed Work**: `dev/completed/` - What's already done
- **Project Docs**: `/CLAUDE.md`, `/PROJECT.md`, `/ARCHITECTURE.md`

---

Last Updated: November 15, 2025
Status: Future work documented, prioritized
