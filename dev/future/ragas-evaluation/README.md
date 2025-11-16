# RAGAs Evaluation Framework

**Priority**: Medium (do after RAG Accuracy Improvement Phase 1)
**Time Estimate**: 4-5 hours
**Impact**: Measurable metrics, data-driven optimization

---

## 🎯 Goal

Implement RAGAs (Retrieval Augmented Generation Assessment) framework to:
1. Measure baseline system performance
2. Identify weak points in RAG pipeline
3. Tune hyperparameters based on data
4. Validate improvements from Phase 1

---

## 📊 RAGAs Metrics

### Core Metrics
1. **Faithfulness** (>0.90 target)
   - Are answers grounded in retrieved context?
   - No hallucinations

2. **Answer Relevancy** (>0.90 target)
   - Does answer address the question?
   - No off-topic responses

3. **Context Precision** (>0.80 target)
   - Are retrieved chunks relevant?
   - Measure of retrieval quality

4. **Context Recall** (>0.85 target)
   - Did we retrieve all necessary info?
   - Measure of retrieval completeness

5. **Citation Accuracy** (>95% target)
   - Are citations verifiable?
   - Custom metric for QueryBox

---

## 📋 Implementation Plan

### Phase 6.1: Install & Setup (30 min)

**Tasks**:
- [ ] Install RAGAs
  ```bash
  pip install ragas>=0.1.0 datasets>=2.14.0
  ```

- [ ] Test import
  ```python
  from ragas import evaluate
  from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
  ```

- [ ] Create evaluation directory
  ```bash
  mkdir -p backend/tests/evaluation
  ```

---

### Phase 6.2: Create Evaluation Dataset (60 min)

**Tasks**:
- [ ] Create dataset file: `backend/tests/evaluation/ragas_dataset.json`

**Format**:
```json
[
  {
    "question": "What is the revenue for Q3 2024?",
    "contexts": ["Tesla Q3 2024 revenue was $25.2 billion..."],
    "answer": "The revenue for Q3 2024 was $25.2 billion.",
    "ground_truth": "$25.2 billion"
  },
  ...
]
```

**Requirements**:
- 20 high-quality Q&A pairs
- Diverse query types (simple, complex, multi-hop)
- Ground truth manually verified
- Covers main document types

---

### Phase 6.3: Create Evaluation Script (50 min)

**File**: `backend/tests/evaluation/ragas_eval.py`

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from datasets import Dataset
import json

def run_ragas_evaluation():
    # Load test dataset
    with open('ragas_dataset.json', 'r') as f:
        data = json.load(f)

    # Run RAG pipeline for each query
    results = []
    for item in data:
        # Get RAG response
        response = run_rag_pipeline(item['question'])

        results.append({
            'question': item['question'],
            'answer': response['answer'],
            'contexts': response['contexts'],
            'ground_truth': item['ground_truth']
        })

    # Convert to Dataset
    dataset = Dataset.from_list(results)

    # Evaluate
    scores = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall
        ]
    )

    # Print results
    print("RAGAs Evaluation Results:")
    print(f"Faithfulness: {scores['faithfulness']:.3f}")
    print(f"Answer Relevancy: {scores['answer_relevancy']:.3f}")
    print(f"Context Precision: {scores['context_precision']:.3f}")
    print(f"Context Recall: {scores['context_recall']:.3f}")

    return scores

if __name__ == '__main__':
    run_ragas_evaluation()
```

---

### Phase 6.4: Run Baseline Evaluation (20 min)

**Tasks**:
- [ ] Configure system with current settings
- [ ] Run evaluation script
  ```bash
  python backend/tests/evaluation/ragas_eval.py
  ```

- [ ] Record baseline scores
- [ ] Identify weakest metric

**Expected Baseline** (before RAG Accuracy Improvement):
- Faithfulness: ~0.85
- Answer Relevancy: ~0.88
- Context Precision: ~0.75
- Context Recall: ~0.80

---

### Phase 6.5: Hyperparameter Tuning (90 min)

**File**: `backend/scripts/tune_hyperparameters.py`

**Parameters to Tune**:
1. **RRF_K**: [40, 60, 80] (Reciprocal Rank Fusion constant)
2. **RRF_KEYWORD_WEIGHT**: [0.3, 0.4, 0.5, 0.6, 0.7] (BM25 vs Vector balance)
3. **RERANK_TOP_K**: [30, 50, 70, 100] (How many to rerank)
4. **MMR_LAMBDA**: [0.5, 0.6, 0.7, 0.8] (Diversity vs Relevance)

**Process**:
```python
def tune_hyperparameters():
    best_score = 0
    best_params = {}

    # Grid search
    for rrf_k in [40, 60, 80]:
        for keyword_weight in [0.3, 0.5, 0.7]:
            for rerank_k in [30, 50, 70]:
                for mmr_lambda in [0.5, 0.7]:
                    # Update config
                    update_config(rrf_k, keyword_weight, rerank_k, mmr_lambda)

                    # Run evaluation
                    scores = run_ragas_evaluation()

                    # Calculate combined score
                    combined = (
                        scores['faithfulness'] * 0.3 +
                        scores['answer_relevancy'] * 0.3 +
                        scores['context_precision'] * 0.2 +
                        scores['context_recall'] * 0.2
                    )

                    if combined > best_score:
                        best_score = combined
                        best_params = {
                            'RRF_K': rrf_k,
                            'KEYWORD_WEIGHT': keyword_weight,
                            'RERANK_TOP_K': rerank_k,
                            'MMR_LAMBDA': mmr_lambda
                        }

    print(f"Best parameters: {best_params}")
    print(f"Best score: {best_score:.3f}")
    return best_params
```

**Tasks**:
- [ ] Run grid search (~20-30 combinations, ~2 hours)
- [ ] Record best parameters
- [ ] Update `backend/app/core/config.py` with optimal values
- [ ] Re-run evaluation to validate

**Target**: RAGAs scores >0.90 on all metrics

---

### Phase 6.6: Performance Testing (90 min)

**File**: `backend/tests/performance/load_test.py`

**Tests**:
1. **Latency Test**
   - 100 concurrent queries
   - Measure: p50, p95, p99
   - Target: p95 <2s

2. **Throughput Test**
   - Gradually increase load
   - Measure: queries/second
   - Identify: Breaking point

3. **Cost Test**
   - Run 100 queries
   - Track: LLM costs, embedding costs, vision costs
   - Verify: <$0.05 per query

**Tasks**:
- [ ] Create load test script
- [ ] Run tests with all optimizations enabled
- [ ] Identify bottlenecks
- [ ] Record performance metrics

---

### Phase 6.7: Final Validation (60 min)

**Tasks**:
- [ ] Run comprehensive RAGAs evaluation (all metrics)
- [ ] Test all retrieval modes:
  - Standard
  - Multi-Query
  - (HyDE if implemented)

- [ ] Test all provider combinations:
  - Parser: Docling, Smart
  - LLM: Ollama, OpenRouter
  - Embeddings: BGE-M3, OpenAI
  - Vector: pgvector, Qdrant

- [ ] Document final configuration:
  - File: `FINAL_CONFIG.md`
  - Best settings for each component
  - RAGAs scores achieved
  - Latency and cost data

- [ ] Create demo script:
  - File: `backend/scripts/demo.py`
  - Show impressive results
  - Compare before/after

---

## 📊 Success Criteria

### Accuracy (RAGAs Metrics)
- [ ] Faithfulness: >0.90
- [ ] Answer Relevancy: >0.90
- [ ] Context Precision: >0.80
- [ ] Context Recall: >0.85
- [ ] Citation Accuracy: >0.95 (custom metric)

### Performance
- [ ] p50 Latency: <1.5s
- [ ] p95 Latency: <2s
- [ ] p99 Latency: <3s
- [ ] Throughput: >10 queries/sec

### Cost
- [ ] Per-query: <$0.05
- [ ] 100 queries: <$5

---

## 🔗 Dependencies

**Requires**:
- Completed: Modular architecture (Phase 1)
- Completed: OpenRouter LLM (Phase 3)
- Completed: OpenAI embeddings (Phase 3)
- Completed: Multi-Query RAG (Phase 5)

**Optional**:
- RAG Accuracy Improvement Phase 1 (for best results)
- Qdrant enabled (for speed testing)

---

## 📈 Expected Results

### Before RAGAs Tuning
- Faithfulness: ~0.85
- Answer Relevancy: ~0.88
- Context Precision: ~0.75
- Context Recall: ~0.80

### After RAGAs Tuning
- Faithfulness: >0.90 (+6%)
- Answer Relevancy: >0.90 (+2%)
- Context Precision: >0.85 (+13%)
- Context Recall: >0.88 (+10%)

### After RAG Accuracy Improvement (Phase 1)
- All metrics: >0.95 (+additional 5-10%)

---

## 🎯 When to Implement

**Do This When**:
- ✅ You have production or realistic test data
- ✅ You want to measure actual system performance
- ✅ You need to optimize for specific use cases
- ✅ You completed RAG Accuracy Improvement Phase 1

**Skip This If**:
- ❌ Still in early prototyping
- ❌ Don't have ground truth data
- ❌ System not stable yet

---

Last Updated: November 15, 2025
Status: Ready for implementation when needed
Priority: Medium (do after RAG Accuracy Improvement)
