# Phase 3: Experimental - Detailed Implementation Guide

## 🎯 Overview
**Timeline**: 3-4 weeks (after Phase 1 & 2 validation)
**Expected Accuracy Gain**: +20-30% on specific use cases
**Cost**: $100-500 for large corpus
**Effort**: High
**Risk**: Higher complexity, storage tradeoffs

---

## 🧩 Component 3.1: ColBERT v2 Multi-Vector Retrieval

### Background
**Problem**: Single-vector embeddings are coarse-grained
**Example**:
- Query: "machine learning optimization techniques"
- Chunk: Long paragraph about gradient descent, Adam optimizer, learning rates
- Single-vector: One 1024-dim vector for entire chunk (loses detail)
- ColBERT: One 128-dim vector PER TOKEN (~100 vectors per chunk)

**Solution**: Token-level embeddings with late interaction

### How It Works
```
Traditional Dense Retrieval:
  Query → Single vector (1024 dims)
  Chunk → Single vector (1024 dims)
  Similarity = cosine(query_vec, chunk_vec)

ColBERT:
  Query → Matrix of token vectors [N_query_tokens × 128]
  Chunk → Matrix of token vectors [N_chunk_tokens × 128]
  Similarity = MaxSim scoring (for each query token, find best matching chunk token)
```

### MaxSim Scoring
```python
def maxsim_score(query_matrix, doc_matrix):
    """
    For each query token, find max similarity with any document token
    Sum across all query tokens
    """
    scores = []
    for q_token_vec in query_matrix:
        # Find best matching doc token
        max_sim = max(
            cosine_similarity(q_token_vec, d_token_vec)
            for d_token_vec in doc_matrix
        )
        scores.append(max_sim)

    return sum(scores)
```

### Implementation Options

#### Option 1: Jina ColBERT v2 (Recommended)
**Model**: `jinaai/jina-colbert-v2`
**Features**:
- 89 languages (multilingual)
- 512 max tokens per chunk
- 128-dim token embeddings
- Residual compression (6-10x reduction)

```python
from transformers import AutoModel, AutoTokenizer

class ColBERTEmbedder:
    def __init__(self):
        self.model = AutoModel.from_pretrained("jinaai/jina-colbert-v2")
        self.tokenizer = AutoTokenizer.from_pretrained("jinaai/jina-colbert-v2")

    def embed_chunk(self, text: str):
        """
        Embed chunk to token-level embeddings

        Returns:
            Tensor of shape [num_tokens, 128]
        """
        tokens = self.tokenizer(text, return_tensors="pt", max_length=512)

        with torch.no_grad():
            outputs = self.model(**tokens)
            token_embeddings = outputs.last_hidden_state  # [1, seq_len, 128]

        return token_embeddings.squeeze(0)  # [seq_len, 128]

    def embed_query(self, query: str):
        """Embed query to token-level embeddings"""
        return self.embed_chunk(query)

    def maxsim_score(self, query_embeddings, doc_embeddings):
        """Calculate MaxSim score between query and document"""
        # query_embeddings: [N_query, 128]
        # doc_embeddings: [N_doc, 128]

        # Compute all pairwise similarities
        similarities = torch.mm(
            query_embeddings,
            doc_embeddings.transpose(0, 1)
        )  # [N_query, N_doc]

        # For each query token, take max similarity
        max_sims = similarities.max(dim=1).values  # [N_query]

        # Sum across query tokens
        return max_sims.sum().item()
```

#### Option 2: RAGatouille (Easier Wrapper)
**Library**: `ragatouille`
**Features**:
- Simplified ColBERT interface
- Built-in indexing and search
- Supports ColBERTv2

```python
from ragatouille import RAGPretrainedModel

class RAGatouilleRetriever:
    def __init__(self):
        self.model = RAGPretrainedModel.from_pretrained("colbert-ir/colbertv2.0")

    def index_chunks(self, chunks: List[str], chunk_ids: List[int]):
        """Index chunks with ColBERT"""
        self.model.index(
            collection=chunks,
            document_ids=chunk_ids,
            index_name="querybox-colbert",
            max_document_length=512
        )

    def search(self, query: str, top_k: int = 10):
        """Search with ColBERT"""
        results = self.model.search(
            query=query,
            k=top_k
        )
        return results
```

### Storage Considerations

**Storage Impact**:
```
Traditional:
  - 1 chunk = 1 vector (1024 floats) = 4KB

ColBERT (uncompressed):
  - 1 chunk = 512 tokens × 128 dims = 65,536 floats = 256KB
  - 64x larger!

ColBERT (compressed):
  - Residual compression: 6-10x reduction
  - 1 chunk ≈ 25-40KB
  - 6-10x larger than traditional
```

**Mitigation**:
1. **Quantization**: 32-bit → 8-bit floats (4x reduction)
2. **Residual Compression**: Built into ColBERTv2
3. **Selective Indexing**: Only use ColBERT for complex documents (legal, technical)

### Vector Store Integration

**Qdrant Native Support**:
```python
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

client = QdrantClient(url="http://localhost:6333")

# Create collection for ColBERT
client.create_collection(
    collection_name="colbert_chunks",
    vectors_config={
        "token_embeddings": VectorParams(
            size=128,
            distance=Distance.COSINE,
            multivector_config={
                "comparator": "max_sim"
            }
        )
    }
)

# Index chunk
client.upsert(
    collection_name="colbert_chunks",
    points=[
        PointStruct(
            id=chunk_id,
            vector={
                "token_embeddings": token_embeddings.tolist()  # List of 128-dim vectors
            },
            payload={"text": chunk.text}
        )
    ]
)
```

### Expected Results
- **Accuracy**: +25-35% on complex queries (phrase matching, technical terms)
- **Storage**: **6-10x increase**
- **Speed**: Comparable to dense retrieval (with optimized indexes)
- **Best For**: Legal documents, technical documentation, code search

### Cost-Benefit Decision
```python
# When to use ColBERT:
use_colbert = (
    document.type in ["legal", "technical", "code"] and
    query.complexity > 0.7 and
    storage_budget_available
)

if use_colbert:
    results = colbert_search(query)
else:
    results = standard_dense_search(query)
```

---

## 🧩 Component 3.2: RAPTOR Hierarchical Retrieval

### Background
**Problem**: Flat chunk structure can't answer multi-level questions
**Example**:
- High-level: "What is the main argument of this paper?"
- Mid-level: "What evidence supports the main argument?"
- Low-level: "What specific statistics are mentioned in the methodology section?"

**Solution**: Build tree of summaries at different abstraction levels

### Tree Structure
```
Level 3 (Document Summary):
  "This paper proposes a new RAG architecture using hierarchical retrieval..."

Level 2 (Section Summaries):
  - Introduction: "The paper motivates the need for better RAG..."
  - Methodology: "The proposed approach uses RAPTOR..."
  - Results: "Experiments show 20% improvement..."

Level 1 (Subsection Summaries):
  - 2.1 Dataset: "The authors use BEIR benchmark..."
  - 2.2 Baseline: "Comparison against standard RAG..."
  - 2.3 Metrics: "Evaluation using MRR and precision@10..."

Level 0 (Base Chunks):
  - Individual 100-token chunks (original content)
```

### How It Works
1. **Build Tree** (one-time, during indexing):
   - Start with base chunks (100 tokens)
   - Embed all chunks
   - Cluster using GMM (Gaussian Mixture Models)
   - For each cluster, generate summary using LLM
   - Repeat recursively until single root node

2. **Retrieve** (at query time):
   - Search ALL levels simultaneously
   - Base chunks: For specific details
   - Mid-level summaries: For section-level info
   - Top-level summary: For high-level overview
   - Combine results with weighted scoring

### Implementation

```python
from sklearn.mixture import GaussianMixture
import numpy as np

class RAPTORIndexer:
    def __init__(self, embedding_model, llm):
        self.embedding_model = embedding_model
        self.llm = llm
        self.max_chunk_size = 100  # tokens
        self.cluster_size = 5  # number of clusters per level

    def build_raptor_tree(self, document: str) -> Dict[int, List[Node]]:
        """
        Build RAPTOR tree structure

        Returns:
            Dict mapping level → list of nodes at that level
        """
        # Level 0: Base chunks
        base_chunks = self.chunk_document(document, self.max_chunk_size)
        embeddings = self.embedding_model.embed_batch(base_chunks)

        tree = {0: [Node(text=chunk, embedding=emb) for chunk, emb in zip(base_chunks, embeddings)]}
        current_level = 0
        current_nodes = tree[0]

        # Build levels recursively
        while len(current_nodes) > 1:
            current_level += 1
            next_level_nodes = self.build_next_level(current_nodes)
            tree[current_level] = next_level_nodes
            current_nodes = next_level_nodes

        return tree

    def build_next_level(self, nodes: List[Node]) -> List[Node]:
        """Build next level of tree by clustering and summarizing"""
        # 1. Extract embeddings
        embeddings = np.array([node.embedding for node in nodes])

        # 2. Cluster using GMM
        n_clusters = min(self.cluster_size, len(nodes))
        gmm = GaussianMixture(n_components=n_clusters, random_state=42)
        cluster_labels = gmm.fit_predict(embeddings)

        # 3. For each cluster, create summary
        next_level_nodes = []
        for cluster_id in range(n_clusters):
            cluster_nodes = [node for i, node in enumerate(nodes) if cluster_labels[i] == cluster_id]

            # Generate summary for cluster
            cluster_text = "\n\n".join([node.text for node in cluster_nodes])
            summary = self.llm.summarize(cluster_text, max_tokens=200)

            # Embed summary
            summary_embedding = self.embedding_model.embed(summary)

            # Create node
            summary_node = Node(
                text=summary,
                embedding=summary_embedding,
                children=cluster_nodes
            )
            next_level_nodes.append(summary_node)

        return next_level_nodes

    async def retrieve_from_tree(
        self,
        query: str,
        tree: Dict[int, List[Node]],
        top_k: int = 10
    ) -> List[Node]:
        """Retrieve from all levels of tree"""
        query_embedding = self.embedding_model.embed_query(query)

        # Retrieve from ALL levels
        all_results = []
        for level, nodes in tree.items():
            # Search this level
            level_results = self.vector_search(query_embedding, nodes, top_k=5)

            # Weight by level (higher levels get lower weight)
            level_weight = 1.0 / (level + 1)
            for node in level_results:
                node.score *= level_weight

            all_results.extend(level_results)

        # Sort by weighted score
        all_results.sort(key=lambda x: x.score, reverse=True)

        return all_results[:top_k]

class Node:
    def __init__(self, text: str, embedding: np.ndarray, children: List['Node'] = None):
        self.text = text
        self.embedding = embedding
        self.children = children or []
        self.score = 0.0
```

### LLM Summarization (Cost Optimization)

```python
async def summarize_cluster(self, cluster_text: str) -> str:
    """Generate concise summary for cluster"""

    # Use cheapest LLM for summarization
    # Option 1: Ollama (free)
    # Option 2: Haiku (~$0.01 per document)
    # Option 3: GPT-4o-mini (~$0.05 per document)

    prompt = f"""Summarize the following text cluster concisely in 2-3 sentences:

{cluster_text[:2000]}  # Truncate to avoid token limits

Summary:"""

    if self.llm_provider == "ollama":
        summary = await self.ollama_generate(prompt, max_tokens=200)
    elif self.llm_provider == "haiku":
        summary = await self.haiku_generate(prompt, max_tokens=200)
    else:
        summary = await self.gpt_generate(prompt, max_tokens=200)

    return summary

# Cost calculation
# Ollama: $0
# Haiku: $0.01-0.02 per document (100-200 tokens output × $0.25 per 1M tokens)
# GPT-4o-mini: $0.03-0.05 per document
```

### Database Schema

```sql
-- RAPTOR tree structure
CREATE TABLE raptor_nodes (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    level INTEGER NOT NULL,  -- 0 = base chunks, 1+ = summaries
    node_index INTEGER NOT NULL,  -- Position within level
    text TEXT NOT NULL,
    embedding vector(1024),
    parent_id INTEGER REFERENCES raptor_nodes(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_raptor_document_level ON raptor_nodes(document_id, level);
CREATE INDEX idx_raptor_embedding ON raptor_nodes USING ivfflat (embedding vector_cosine_ops);

-- Store parent-child relationships
CREATE TABLE raptor_edges (
    parent_id INTEGER REFERENCES raptor_nodes(id),
    child_id INTEGER REFERENCES raptor_nodes(id),
    PRIMARY KEY (parent_id, child_id)
);
```

### Expected Results
- **Accuracy**: +15-20% on long documents, multi-hop questions
- **Cost**: $0.01-0.05 per document (LLM summarization)
- **Storage**: 3-5x increase (tree structure)
- **Best For**: Research papers, technical documentation, long-form content

### Use Case Decision
```python
# When to use RAPTOR:
use_raptor = (
    document.page_count > 10 and  # Long documents
    document.type in ["research", "technical", "report"] and
    query.is_multi_level()  # Requires synthesis across sections
)
```

---

## 🧩 Component 3.3: Optional Embedding Model Upgrade

### Option: bge-multilingual-gemma2

**Model**: `BAAI/bge-multilingual-gemma2`
**Released**: July 2024
**Improvement**: +5% over BGE-M3

**Specs**:
- **Size**: 9GB (vs BGE-M3 2.2GB)
- **MTEB Score**: ~75% (vs BGE-M3 ~70%)
- **Languages**: 100+
- **Max Tokens**: 8192

**Implementation**:
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-multilingual-gemma2")

# Use same interface as BGE-M3
embeddings = model.encode(texts, normalize_embeddings=True)
```

**Tradeoff Analysis**:
```
Pros:
  + 5% accuracy improvement
  + Latest SOTA from BAAI
  + Drop-in replacement

Cons:
  - 9GB model (4x larger)
  - Slower inference (~2x)
  - Need to re-embed all documents

Decision:
  Skip this - Phase 1 techniques provide +35-50% improvement already
  5% gain not worth the effort/cost
```

---

## 📊 Phase 3 Success Metrics

### ColBERT Targets
- **Accuracy**: +25-35% on phrase matching queries
- **Storage**: Accept 6-10x increase for high-value documents
- **Use Cases**: Legal, technical, code search

### RAPTOR Targets
- **Accuracy**: +15-20% on multi-hop questions
- **Cost**: <$500 for 10K documents
- **Use Cases**: Research papers, long documents

---

## 🧪 Testing Plan

### ColBERT Evaluation
```python
# Test on technical queries
technical_queries = [
    "gradient descent optimization algorithm",
    "OAuth 2.0 authorization code flow",
    "React useEffect dependency array"
]

dense_results = test_dense_retrieval(technical_queries)
colbert_results = test_colbert_retrieval(technical_queries)

print(f"Dense: {dense_results.accuracy}%")
print(f"ColBERT: {colbert_results.accuracy}%")
# Expected: +25-35% improvement
```

### RAPTOR Evaluation
```python
# Test on multi-level questions
multi_level_queries = [
    "What is the main contribution of this paper?",  # High-level
    "What datasets were used in the evaluation?",    # Mid-level
    "What was the precision@10 on BEIR benchmark?"  # Low-level
]

flat_results = test_flat_retrieval(multi_level_queries)
raptor_results = test_raptor_retrieval(multi_level_queries)

print(f"Flat: {flat_results.accuracy}%")
print(f"RAPTOR: {raptor_results.accuracy}%")
# Expected: +15-20% improvement on long docs
```

---

## 🚀 Implementation Decision Matrix

| Technique | Accuracy Gain | Storage Cost | Complexity | When to Use |
|-----------|---------------|--------------|------------|-------------|
| **ColBERT** | +25-35% | **6-10x** | High | Legal, technical, code docs |
| **RAPTOR** | +15-20% | 3-5x | High | Long docs, research papers |
| **bge-gemma2** | +5% | Neutral | Low | Skip - Phase 1 provides more |

**Recommendation**: Implement ColBERT and/or RAPTOR **only if**:
1. Phase 1 + 2 results show need for further improvement
2. Have specific use cases (legal, research papers)
3. Storage budget allows 6-10x increase
4. Can justify LLM cost for RAPTOR summarization

---

Last Updated: Nov 15, 2025
Status: Documented for Future Consideration
