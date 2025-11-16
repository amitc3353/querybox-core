# Phase 2: Advanced Techniques - Detailed Implementation Guide

## 🎯 Overview
**Timeline**: 2-3 weeks (after Phase 1 validation)
**Expected Accuracy Gain**: +20-30% (on top of Phase 1)
**Cost**: $0
**Effort**: Medium-High

---

## 🧩 Component 2.1: Matryoshka Embeddings

### Background
**Problem**: Fixed 1024-dim embeddings are overkill for simple queries
**Example**:
- Simple query: "What is RAG?" → Doesn't need full 1024 dimensions
- Complex query: "Compare RAPTOR vs standard RAG for long-context retrieval" → Needs full precision

**Solution**: Use adaptive dimensions
- Stage 1: 64 dims for initial retrieval (14x faster, 14x smaller)
- Stage 2: 768 dims for reranking (high precision)

### Nomic Embed v1.5 Features
- **Matryoshka Representation Learning**: Single embedding, multiple dimensions
- **Dimensions**: 64, 128, 256, 512, 768
- **Accuracy**: Competitive with BGE-M3 at full 768 dims
- **Efficiency**: 14x storage reduction at 64 dims, minimal accuracy loss

### Implementation Plan

#### 1. Model Evaluation
```python
# Test Nomic Embed v1.5 accuracy vs BGE-M3
from sentence_transformers import SentenceTransformer

# Load model
model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)

# Test at different dimensions
for dim in [64, 128, 256, 512, 768]:
    embeddings = model.encode(
        texts,
        output_dim=dim,
        task_type="search_document"
    )
    # Benchmark accuracy
```

#### 2. Adaptive Retrieval Pipeline
```python
class AdaptiveRetriever:
    def __init__(self):
        self.model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5")

    async def adaptive_search(self, query: str, top_k: int = 10):
        # Stage 1: Fast initial retrieval (64 dims)
        query_embed_small = self.model.encode(
            query,
            output_dim=64,
            task_type="search_query"
        )

        # Search with small embeddings (fast!)
        candidates = await self.vector_search_64d(query_embed_small, top_k=100)

        # Stage 2: Precise reranking (768 dims)
        query_embed_large = self.model.encode(
            query,
            output_dim=768,
            task_type="search_query"
        )

        # Re-embed top-100 candidates at full precision
        candidate_embeds_large = [
            self.get_full_embedding(c.chunk_id) for c in candidates
        ]

        # Rerank with high precision
        final_results = self.rerank(query_embed_large, candidate_embeds_large, top_k)

        return final_results
```

#### 3. Storage Strategy
```python
# Store multiple dimension versions
class ChunkEmbedding(BaseModel):
    chunk_id: int
    embedding_64: List[float]   # For fast search
    embedding_768: List[float]  # For reranking

    # OR use Matryoshka property: embedding_768[:64] == embedding_64
    embedding: List[float]  # Store only 768, truncate for search
```

### Expected Results
- **Accuracy**: +2% (same or better at full 768 dims)
- **Storage**: 14x reduction (64 dims vs 1024 dims)
- **Speed**: 14x faster initial search
- **Cost**: $0 (open-source model)

---

## 🧩 Component 2.2: Sentence Window Retrieval

### Background
**Problem**: Chunks are too large (lose precision) or too small (lose context)
**Solution**: Retrieve at sentence level, expand to window context

### How It Works
```
Traditional:
  Search chunks (512 tokens) → Return chunks

Sentence Window:
  Search sentences (50 tokens) → Expand to ±3 sentences → Return context
```

### Implementation

```python
class SentenceWindowRetriever:
    def __init__(self, window_size: int = 3):
        self.window_size = window_size

    def index_sentences(self, document: str, chunk_id: int):
        """Split chunk into sentences and index each"""
        sentences = self.split_into_sentences(document)

        for idx, sentence in enumerate(sentences):
            # Embed sentence
            embedding = self.embed(sentence)

            # Store with metadata
            self.store_sentence(
                chunk_id=chunk_id,
                sentence_idx=idx,
                text=sentence,
                embedding=embedding
            )

    async def search_with_window(self, query: str, top_k: int = 10):
        # 1. Search at sentence level
        top_sentences = await self.sentence_search(query, top_k * 3)

        # 2. Expand to window context
        expanded_chunks = []
        for sentence in top_sentences:
            window = self.expand_to_window(
                chunk_id=sentence.chunk_id,
                sentence_idx=sentence.idx,
                window_size=self.window_size
            )
            expanded_chunks.append(window)

        # 3. Deduplicate overlapping windows
        unique_chunks = self.deduplicate_windows(expanded_chunks)

        return unique_chunks[:top_k]

    def expand_to_window(self, chunk_id: int, sentence_idx: int, window_size: int):
        """Get ±N sentences around target sentence"""
        start_idx = max(0, sentence_idx - window_size)
        end_idx = sentence_idx + window_size + 1

        sentences = self.get_sentences(chunk_id, start_idx, end_idx)
        return "\n".join(sentences)
```

### Expected Results
- **Accuracy**: +5-10% (better precision + context)
- **Storage**: 3-5x increase (sentence-level index)
- **Speed**: Neutral (more candidates, but faster search)

---

## 🧩 Component 2.3: Enhanced Query Preprocessing

### Techniques

#### 1. Entity Extraction
```python
import spacy

nlp = spacy.load("en_core_web_sm")

def extract_entities(query: str):
    doc = nlp(query)
    entities = {
        "persons": [ent.text for ent in doc.ents if ent.label_ == "PERSON"],
        "orgs": [ent.text for ent in doc.ents if ent.label_ == "ORG"],
        "dates": [ent.text for ent in doc.ents if ent.label_ == "DATE"],
        "locations": [ent.text for ent in doc.ents if ent.label_ == "GPE"]
    }
    return entities

# Boost chunks containing these entities
```

#### 2. Acronym Expansion
```python
ACRONYM_DICT = {
    "ML": "Machine Learning",
    "AI": "Artificial Intelligence",
    "RAG": "Retrieval Augmented Generation",
    "LLM": "Large Language Model",
    # ... build from domain knowledge
}

def expand_acronyms(query: str):
    expanded = query
    for acronym, full_form in ACRONYM_DICT.items():
        if acronym in query:
            expanded += f" {full_form}"
    return expanded
```

#### 3. Synonym Generation
```python
from nltk.corpus import wordnet

def add_synonyms(query: str):
    words = query.split()
    synonyms = []

    for word in words:
        synsets = wordnet.synsets(word)
        for synset in synsets[:2]:  # Top 2 synsets
            for lemma in synset.lemmas()[:2]:  # Top 2 synonyms
                if lemma.name() != word:
                    synonyms.append(lemma.name())

    return query + " " + " ".join(synonyms)
```

#### 4. Intent Detection
```python
class QueryIntentDetector:
    INTENTS = {
        "question": ["how", "what", "why", "when", "where", "who", "which"],
        "definition": ["what is", "define", "meaning of"],
        "comparison": ["compare", "difference", "vs", "versus"],
        "how_to": ["how to", "steps to", "guide to"],
        "list": ["list", "types of", "examples of"]
    }

    def detect_intent(self, query: str):
        query_lower = query.lower()

        for intent, keywords in self.INTENTS.items():
            if any(kw in query_lower for kw in keywords):
                return intent

        return "general"

# Route to optimized strategy per intent
```

### Expected Results
- **Accuracy**: +5-10%
- **Effort**: 2-3 days
- **Cost**: $0

---

## 🧩 Component 2.4: Upgrade Cross-Encoder Reranker

### Current vs New

| Feature | ms-marco-MiniLM-L6-v2 (current) | bge-reranker-v2-m3 (new) |
|---------|--------------------------------|--------------------------|
| **Released** | 2021 | 2024 |
| **Max Length** | 512 tokens | 8192 tokens |
| **Multilingual** | No | Yes (100+ languages) |
| **Accuracy** | Baseline | +3-5% better |
| **Speed** | Fast | Comparable |

### Implementation

```python
# backend/app/core/config.py
CROSS_ENCODER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
CROSS_ENCODER_MAX_LENGTH = 8192  # Can handle much longer contexts

# backend/app/services/search/reranking/cross_encoder.py
from sentence_transformers import CrossEncoder

class CrossEncoderReranker:
    def __init__(self):
        self.model = CrossEncoder(
            "BAAI/bge-reranker-v2-m3",
            max_length=8192,
            device="cuda" if torch.cuda.is_available() else "cpu"
        )

    async def rerank(self, query: str, chunks: List[Chunk], top_k: int):
        # Prepare pairs
        pairs = [[query, chunk.text] for chunk in chunks]

        # Score pairs
        scores = self.model.predict(pairs)

        # Sort by score
        ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)

        return [chunk for chunk, score in ranked[:top_k]]
```

### Expected Results
- **Accuracy**: +3-5%
- **Effort**: 1 day (drop-in replacement)
- **Cost**: $0

---

## 📊 Phase 2 Success Metrics

### Accuracy Targets
- **Top-10 Precision**: ~98% → **~99%**
- **Storage**: **14x reduction** with Matryoshka
- **Speed**: **14x faster** initial retrieval

### Performance Targets
- **Search Latency**: Improved (faster initial search)
- **Storage Cost**: **-85% reduction** (1024 dims → 64 dims)
- **Reranking Accuracy**: +3-5% with new cross-encoder

---

## 🧪 Testing Plan

### 1. Matryoshka Evaluation
```python
# Test accuracy at different dimensions
for dim in [64, 128, 256, 512, 768]:
    accuracy = test_retrieval_accuracy(dimension=dim)
    print(f"{dim} dims: {accuracy}%")

# Expected:
# 64 dims: ~92%   (14x faster, 14x smaller)
# 128 dims: ~95%  (7x faster, 7x smaller)
# 256 dims: ~97%  (4x faster, 4x smaller)
# 768 dims: ~99%  (full precision)
```

### 2. Sentence Window Benchmark
```python
# Compare chunk-level vs sentence-level retrieval
test_queries = load_benchmark_queries()

chunk_results = test_chunk_retrieval(test_queries)
sentence_results = test_sentence_window_retrieval(test_queries)

print(f"Chunk retrieval: {chunk_results.accuracy}%")
print(f"Sentence window: {sentence_results.accuracy}%")
# Expected: +5-10% improvement
```

### 3. Query Preprocessing Impact
```python
# A/B test query preprocessing
baseline = test_without_preprocessing()
with_preprocessing = test_with_preprocessing()

print(f"Baseline: {baseline.accuracy}%")
print(f"With preprocessing: {with_preprocessing.accuracy}%")
# Expected: +5-10% improvement
```

---

## 🚀 Implementation Priority

**Recommended Order:**
1. **Upgrade Cross-Encoder** (Day 1) - Easiest, immediate +3-5%
2. **Matryoshka Embeddings** (Day 2-5) - Biggest storage/speed gains
3. **Query Preprocessing** (Day 6-8) - Good accuracy boost
4. **Sentence Window** (Day 9-14) - More complex, optional

---

Last Updated: Nov 15, 2025
Status: Documented for Future Implementation
