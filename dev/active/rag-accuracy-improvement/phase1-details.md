# Phase 1: Quick Wins - Detailed Implementation Guide

## 🎯 Overview
**Timeline**: 1-2 weeks
**Expected Accuracy Gain**: +35-50%
**Cost**: $0 (using Ollama)
**Effort**: Medium

---

## 🧩 Component 1: Contextual Retrieval

### Background
**Problem**: Chunks lose document/section context when embedded independently
**Example**:
- Chunk: "Revenue grew 3% year-over-year"
- Missing context: Which company? Which year? Which section?

**Solution**: Prepend LLM-generated context before embedding
- Contextual chunk: "Document: Tesla 2024 Q3 Earnings\nSection: Financial Results\n\nRevenue grew 3% year-over-year"

### How It Works
```
Original Pipeline:
  Document → Chunk → Embed → Store

New Pipeline:
  Document → Chunk → Generate Context → Prepend Context → Embed → Store
                            ↓
                      [LLM: Ollama]
```

### Implementation Details

#### File: `backend/app/services/chunking/contextual_enrichment.py`

```python
from typing import Optional
import httpx
from app.core.config import settings

class ContextualEnricher:
    """Generate contextual prefixes for chunks using LLM"""

    def __init__(self):
        self.provider = settings.CONTEXTUAL_LLM_PROVIDER  # "ollama" or "haiku"
        self.model = settings.CONTEXTUAL_LLM_MODEL
        self.max_tokens = settings.CONTEXTUAL_MAX_TOKENS

    async def enrich_chunk(
        self,
        chunk_text: str,
        document_title: str,
        section_heading: Optional[str] = None,
        chunk_type: str = "paragraph"
    ) -> str:
        """
        Generate contextual prefix for a chunk

        Args:
            chunk_text: Original chunk text
            document_title: Document title or filename
            section_heading: Current section heading (if any)
            chunk_type: Type of chunk (paragraph, table, code, etc.)

        Returns:
            Contextual prefix to prepend to chunk
        """
        # Build context prompt
        prompt = self._build_context_prompt(
            chunk_text, document_title, section_heading, chunk_type
        )

        # Generate context using LLM
        if self.provider == "ollama":
            context = await self._generate_with_ollama(prompt)
        elif self.provider == "haiku":
            context = await self._generate_with_haiku(prompt)
        else:
            # Fallback: simple template-based context
            context = self._generate_template_context(
                document_title, section_heading, chunk_type
            )

        return context

    def _build_context_prompt(
        self,
        chunk_text: str,
        document_title: str,
        section_heading: Optional[str],
        chunk_type: str
    ) -> str:
        """Build prompt for context generation"""
        prompt = f"""You are helping to generate contextual information for document chunks to improve search retrieval.

Document: {document_title}
Section: {section_heading or "N/A"}
Chunk Type: {chunk_type}

Chunk Content:
{chunk_text[:500]}  # Truncate to 500 chars

Generate a concise 1-2 sentence context that:
1. Situates this chunk within the document structure
2. Helps someone searching for this information
3. Is under 50 words

Context:"""
        return prompt

    async def _generate_with_ollama(self, prompt: str) -> str:
        """Generate context using Ollama"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "max_tokens": self.max_tokens,
                    "temperature": 0.3,  # Low temperature for consistency
                }
            )
            result = response.json()
            return result["response"].strip()

    async def _generate_with_haiku(self, prompt: str) -> str:
        """Generate context using Anthropic Haiku"""
        # Use existing OpenRouter integration
        from app.services.llm.openrouter_client import OpenRouterClient

        client = OpenRouterClient()
        response = await client.generate(
            model="anthropic/claude-3-haiku",
            prompt=prompt,
            max_tokens=self.max_tokens,
            temperature=0.3
        )
        return response.strip()

    def _generate_template_context(
        self,
        document_title: str,
        section_heading: Optional[str],
        chunk_type: str
    ) -> str:
        """Fallback: template-based context (no LLM)"""
        parts = [f"Document: {document_title}"]

        if section_heading:
            parts.append(f"Section: {section_heading}")

        if chunk_type != "paragraph":
            parts.append(f"Type: {chunk_type}")

        return "\n".join(parts)
```

#### Integration into Chunking Service

Update `backend/app/services/chunking/chunking_service.py`:

```python
from app.services.chunking.contextual_enrichment import ContextualEnricher

class ChunkingService:
    def __init__(self):
        # Existing initialization...
        self.contextual_enricher = ContextualEnricher() if settings.ENABLE_CONTEXTUAL_RETRIEVAL else None

    async def chunk_document(self, document: Document) -> List[Chunk]:
        # Existing chunking logic...
        chunks = self._create_chunks(document)

        # NEW: Add contextual enrichment
        if self.contextual_enricher:
            chunks = await self._enrich_chunks_with_context(chunks, document)

        return chunks

    async def _enrich_chunks_with_context(
        self,
        chunks: List[Chunk],
        document: Document
    ) -> List[Chunk]:
        """Add contextual prefixes to all chunks"""
        enriched_chunks = []

        for chunk in chunks:
            # Generate contextual prefix
            context = await self.contextual_enricher.enrich_chunk(
                chunk_text=chunk.text,
                document_title=document.title or document.filename,
                section_heading=chunk.metadata.section_heading,
                chunk_type=chunk.metadata.chunk_type
            )

            # Create contextual text
            contextual_text = f"{context}\n\n{chunk.text}"

            # Update chunk
            chunk.contextual_text = contextual_text
            chunk.metadata.contextual_prefix = context
            enriched_chunks.append(chunk)

        return enriched_chunks
```

#### Update Embedding Pipeline

Update `backend/app/services/embeddings.py`:

```python
async def embed_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
    """Embed chunks (use contextual text if available)"""
    texts_to_embed = []

    for chunk in chunks:
        # Use contextual text if available, otherwise original
        text = chunk.contextual_text if chunk.contextual_text else chunk.text
        texts_to_embed.append(text)

    # Generate embeddings
    embeddings = await self.model.embed_batch(texts_to_embed)

    # Attach embeddings to chunks
    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding

    return chunks
```

### Configuration

Add to `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    # Contextual Retrieval Settings
    ENABLE_CONTEXTUAL_RETRIEVAL: bool = True
    CONTEXTUAL_LLM_PROVIDER: str = "ollama"  # "ollama", "haiku", "template"
    CONTEXTUAL_LLM_MODEL: str = "llama3.2:3b"
    CONTEXTUAL_MAX_TOKENS: int = 100

    # Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
```

Add to `backend/.env.example`:

```bash
# Contextual Retrieval
ENABLE_CONTEXTUAL_RETRIEVAL=true
CONTEXTUAL_LLM_PROVIDER=ollama  # ollama, haiku, template
CONTEXTUAL_LLM_MODEL=llama3.2:3b
CONTEXTUAL_MAX_TOKENS=100
OLLAMA_BASE_URL=http://localhost:11434
```

### Testing

Create `tests/services/test_contextual_enrichment.py`:

```python
import pytest
from app.services.chunking.contextual_enrichment import ContextualEnricher

@pytest.mark.asyncio
async def test_enrich_chunk_with_ollama():
    enricher = ContextualEnricher()

    chunk_text = "Revenue grew 3% year-over-year to $25.2 billion."
    document_title = "Tesla Q3 2024 Earnings Report"
    section_heading = "Financial Results"

    context = await enricher.enrich_chunk(
        chunk_text=chunk_text,
        document_title=document_title,
        section_heading=section_heading,
        chunk_type="paragraph"
    )

    # Verify context contains key information
    assert "Tesla" in context or "Financial" in context
    assert len(context) < 200  # Should be concise

@pytest.mark.asyncio
async def test_template_fallback():
    enricher = ContextualEnricher()
    enricher.provider = "template"  # Force template mode

    context = enricher._generate_template_context(
        document_title="Test Document",
        section_heading="Introduction",
        chunk_type="table"
    )

    assert "Document: Test Document" in context
    assert "Section: Introduction" in context
    assert "Type: table" in context
```

### Expected Results
- **Accuracy**: +15-25% on retrieval precision
- **Latency**: +100-200ms per document (one-time, during indexing)
- **Cost**: $0 with Ollama, ~$50 for 10K docs with Haiku
- **Storage**: +10-20% (contextual text stored in metadata)

---

## 🧩 Component 2: Late Chunking

### Background
**Problem**: Traditional chunking loses document-level context
**Example**:
- Document: "The capital of Germany is Berlin. It has 3.7 million residents."
- Chunk 1: "The capital of Germany is Berlin."
- Chunk 2: "It has 3.7 million residents." ← "It" loses reference to "Berlin"

**Solution**: Embed full document first, then chunk
- Embedding knows "It" refers to "Berlin" due to full document context

### How It Works
```
Traditional Pipeline:
  Document → Chunk → Tokenize → Transformer → Pool → Embedding

Late Chunking Pipeline:
  Document → Tokenize (full doc) → Transformer (full context) → Chunk → Pool → Embedding
                                          ↑
                                  Full 8192 tokens
```

### Implementation Details

#### File: `backend/app/services/embeddings/late_chunking.py`

```python
import torch
from transformers import AutoModel, AutoTokenizer
from typing import List, Tuple

class LateChunkingEmbedder:
    """Embed documents with late chunking (embed full doc, then chunk)"""

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        self.model = AutoModel.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.max_length = 8192  # BGE-M3 max context

        # Move to GPU if available
        if torch.cuda.is_available():
            self.model = self.model.cuda()

        self.model.eval()

    def late_chunk_embed(
        self,
        document_text: str,
        chunk_boundaries: List[Tuple[int, int]]  # List of (start_token, end_token)
    ) -> List[torch.Tensor]:
        """
        Embed document with late chunking

        Args:
            document_text: Full document text
            chunk_boundaries: List of (start_token_idx, end_token_idx) for each chunk

        Returns:
            List of embeddings (one per chunk)
        """
        # 1. Tokenize full document
        tokens = self.tokenizer(
            document_text,
            return_tensors="pt",
            max_length=self.max_length,
            truncation=True,
            padding=False
        )

        if torch.cuda.is_available():
            tokens = {k: v.cuda() for k, v in tokens.items()}

        # 2. Run through transformer (full document context)
        with torch.no_grad():
            outputs = self.model(**tokens)
            token_embeddings = outputs.last_hidden_state  # [1, seq_len, hidden_dim]

        # 3. Apply mean pooling per chunk (late chunking)
        chunk_embeddings = []

        for start_idx, end_idx in chunk_boundaries:
            # Extract token embeddings for this chunk
            chunk_token_embeds = token_embeddings[:, start_idx:end_idx, :]

            # Mean pooling
            chunk_embedding = chunk_token_embeds.mean(dim=1)  # [1, hidden_dim]

            # Normalize (important for cosine similarity)
            chunk_embedding = torch.nn.functional.normalize(chunk_embedding, p=2, dim=1)

            chunk_embeddings.append(chunk_embedding.squeeze(0).cpu())

        return chunk_embeddings

    def get_chunk_boundaries(
        self,
        document_text: str,
        chunk_texts: List[str]
    ) -> List[Tuple[int, int]]:
        """
        Calculate token boundaries for each chunk within the full document

        Args:
            document_text: Full document text
            chunk_texts: List of chunk texts (in order)

        Returns:
            List of (start_token_idx, end_token_idx) for each chunk
        """
        # Tokenize full document
        full_tokens = self.tokenizer(
            document_text,
            max_length=self.max_length,
            truncation=True
        )
        full_text = self.tokenizer.decode(full_tokens['input_ids'], skip_special_tokens=True)

        boundaries = []
        current_char_pos = 0

        for chunk_text in chunk_texts:
            # Find chunk position in full document
            chunk_start_char = full_text.find(chunk_text, current_char_pos)
            chunk_end_char = chunk_start_char + len(chunk_text)

            # Convert character positions to token positions
            start_token_idx = len(self.tokenizer(
                full_text[:chunk_start_char],
                add_special_tokens=False
            )['input_ids'])

            end_token_idx = len(self.tokenizer(
                full_text[:chunk_end_char],
                add_special_tokens=False
            )['input_ids'])

            boundaries.append((start_token_idx, end_token_idx))
            current_char_pos = chunk_end_char

        return boundaries
```

#### Integration into Embedding Service

Update `backend/app/services/embeddings.py`:

```python
from app.services.embeddings.late_chunking import LateChunkingEmbedder

class EmbeddingService:
    def __init__(self):
        # Existing initialization...
        if settings.ENABLE_LATE_CHUNKING:
            self.late_chunking_embedder = LateChunkingEmbedder()
        else:
            self.late_chunking_embedder = None

    async def embed_document_chunks(
        self,
        document_text: str,
        chunks: List[Chunk]
    ) -> List[Chunk]:
        """Embed chunks using late chunking if enabled"""

        if self.late_chunking_embedder and len(document_text) <= 8192:
            # Use late chunking
            chunk_texts = [chunk.text for chunk in chunks]
            chunk_boundaries = self.late_chunking_embedder.get_chunk_boundaries(
                document_text, chunk_texts
            )

            embeddings = self.late_chunking_embedder.late_chunk_embed(
                document_text, chunk_boundaries
            )

            # Attach embeddings
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding.numpy()
                chunk.metadata.late_chunked = True
        else:
            # Fall back to standard chunking
            embeddings = await self.embed_batch([chunk.text for chunk in chunks])
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
                chunk.metadata.late_chunked = False

        return chunks
```

### Configuration

Add to `backend/app/core/config.py`:

```python
# Late Chunking Settings
ENABLE_LATE_CHUNKING: bool = True
LATE_CHUNKING_MAX_DOC_TOKENS: int = 8192
LATE_CHUNKING_BATCH_SIZE: int = 4  # documents per batch
```

### Testing

Create `tests/services/test_late_chunking.py`:

```python
import pytest
from app.services.embeddings.late_chunking import LateChunkingEmbedder

def test_late_chunking_pronoun_resolution():
    embedder = LateChunkingEmbedder()

    # Document with pronoun reference
    document = "The capital of Germany is Berlin. It has 3.7 million residents."
    chunk_texts = [
        "The capital of Germany is Berlin.",
        "It has 3.7 million residents."
    ]

    # Get embeddings
    boundaries = embedder.get_chunk_boundaries(document, chunk_texts)
    embeddings = embedder.late_chunk_embed(document, boundaries)

    # Both chunks should have embeddings
    assert len(embeddings) == 2
    assert embeddings[0].shape[0] == 1024  # BGE-M3 dimension
    assert embeddings[1].shape[0] == 1024

    # Test: "It" in chunk 2 should be semantically close to "Berlin" in chunk 1
    # (This would require a semantic similarity test with reference embeddings)
```

### Expected Results
- **Accuracy**: +12-15% on entity resolution, cross-references
- **Latency**: +50-100ms per document (transformer overhead)
- **Memory**: +30% during embedding (full document in memory)
- **Quality**: Pronouns, cross-references properly resolved

---

## 🧩 Component 3: HyDE (Hypothetical Document Embeddings)

### Background
**Problem**: Queries are short and vague, documents are detailed
**Example**:
- Query: "How do I reset my password?"
- Document: "To reset your password, navigate to Settings > Account > Security > Reset Password. Click the button and follow the email instructions."

**Solution**: Generate a hypothetical answer, search with that
- Hypothetical answer: "To reset your password, go to settings and click reset password..."
- This matches document content better than the original query

### How It Works
```
Traditional Search:
  Query → Embed → Search

HyDE Search:
  Query → LLM Generate Answer → Embed Answer → Search
              ↓
        "To reset your password,
         go to settings..."
```

### Implementation Details

#### File: `backend/app/services/search/hyde.py`

```python
from typing import List, Optional
import httpx
from app.core.config import settings
from app.schemas.chunk import Chunk

class HyDESearcher:
    """Hypothetical Document Embeddings for better retrieval"""

    def __init__(self):
        self.provider = settings.HYDE_LLM_PROVIDER
        self.model = settings.HYDE_LLM_MODEL
        self.max_tokens = settings.HYDE_MAX_TOKENS

    async def search_with_hyde(
        self,
        query: str,
        top_k: int = 10,
        use_hyde: bool = True
    ) -> List[Chunk]:
        """
        Search using HyDE if query is complex enough

        Args:
            query: User query
            top_k: Number of results to return
            use_hyde: Force HyDE on/off (default: auto-detect)

        Returns:
            List of relevant chunks
        """
        # 1. Decide whether to use HyDE
        if use_hyde and await self._should_use_hyde(query):
            # Generate hypothetical answer
            hypothetical_answer = await self._generate_hypothetical_answer(query)

            # Search with hypothetical answer
            search_text = hypothetical_answer
        else:
            # Standard search
            search_text = query

        # 2. Embed search text
        from app.services.embeddings import embedding_service
        search_embedding = await embedding_service.embed_query(search_text)

        # 3. Vector search
        from app.db.repositories.chunk_repository import chunk_repository
        results = await chunk_repository.similarity_search(
            embedding=search_embedding,
            top_k=top_k * 2  # Get more candidates for reranking
        )

        # 4. Rerank with original query (not hypothetical answer)
        from app.services.search.reranking.cross_encoder import cross_encoder_reranker
        reranked_results = await cross_encoder_reranker.rerank(
            query=query,  # Use original query
            chunks=results,
            top_k=top_k
        )

        return reranked_results

    async def _should_use_hyde(self, query: str) -> bool:
        """Determine if query is complex enough to benefit from HyDE"""
        # Heuristics for complex queries
        complexity_score = 0

        # Multi-word queries
        word_count = len(query.split())
        if word_count >= 5:
            complexity_score += 0.3

        # Question queries
        question_words = ["how", "what", "why", "when", "where", "which", "who"]
        if any(query.lower().startswith(qw) for qw in question_words):
            complexity_score += 0.3

        # Comparison queries
        if "vs" in query.lower() or "compare" in query.lower() or "difference" in query.lower():
            complexity_score += 0.4

        # Multi-hop indicators
        if "and" in query.lower() or "then" in query.lower():
            complexity_score += 0.2

        return complexity_score >= settings.HYDE_QUERY_COMPLEXITY_THRESHOLD

    async def _generate_hypothetical_answer(self, query: str) -> str:
        """Generate hypothetical answer using LLM"""
        prompt = f"""Answer this question concisely and directly in 2-3 sentences:

Question: {query}

Answer:"""

        if self.provider == "ollama":
            return await self._generate_with_ollama(prompt)
        elif self.provider == "haiku":
            return await self._generate_with_haiku(prompt)
        else:
            # Fallback: return original query
            return query

    async def _generate_with_ollama(self, prompt: str) -> str:
        """Generate using Ollama"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "max_tokens": self.max_tokens,
                    "temperature": 0.5,
                }
            )
            result = response.json()
            return result["response"].strip()

    async def _generate_with_haiku(self, prompt: str) -> str:
        """Generate using Haiku"""
        from app.services.llm.openrouter_client import OpenRouterClient

        client = OpenRouterClient()
        response = await client.generate(
            model="anthropic/claude-3-haiku",
            prompt=prompt,
            max_tokens=self.max_tokens,
            temperature=0.5
        )
        return response.strip()
```

#### Integration into Search Service

Update `backend/app/services/search/search_service.py`:

```python
from app.services.search.hyde import HyDESearcher

class SearchService:
    def __init__(self):
        # Existing initialization...
        self.hyde_searcher = HyDESearcher() if settings.ENABLE_HYDE else None

    async def unified_search(
        self,
        query: str,
        strategy: str = "hybrid",
        enable_hyde: bool = True,
        **kwargs
    ) -> List[Chunk]:
        """Unified search with optional HyDE"""

        # Use HyDE if enabled and query is complex
        if self.hyde_searcher and enable_hyde:
            return await self.hyde_searcher.search_with_hyde(
                query=query,
                top_k=kwargs.get('top_k', 10)
            )
        else:
            # Standard search (existing logic)
            return await self._standard_search(query, strategy, **kwargs)
```

#### Update API Schema

Update `backend/app/schemas/search.py`:

```python
class UnifiedSearchQuery(BaseModel):
    query: str
    strategy: str = "hybrid"
    enable_reranking: bool = True
    enable_mmr: bool = True
    enable_dedup: bool = True
    enable_hyde: bool = True  # NEW
    top_k: int = 10
```

### Configuration

Add to `backend/app/core/config.py`:

```python
# HyDE Settings
ENABLE_HYDE: bool = True
HYDE_LLM_PROVIDER: str = "ollama"  # "ollama", "haiku"
HYDE_LLM_MODEL: str = "llama3.2:3b"
HYDE_MAX_TOKENS: int = 200
HYDE_QUERY_COMPLEXITY_THRESHOLD: float = 0.6
```

### Testing

Create `tests/services/test_hyde.py`:

```python
import pytest
from app.services.search.hyde import HyDESearcher

@pytest.mark.asyncio
async def test_hyde_query_complexity():
    searcher = HyDESearcher()

    # Simple query - should NOT use HyDE
    simple = "password reset"
    assert not await searcher._should_use_hyde(simple)

    # Complex query - SHOULD use HyDE
    complex_query = "How do I reset my password if I forgot my email address?"
    assert await searcher._should_use_hyde(complex_query)

    # Comparison query - SHOULD use HyDE
    comparison = "What is the difference between OAuth and JWT?"
    assert await searcher._should_use_hyde(comparison)

@pytest.mark.asyncio
async def test_hypothetical_answer_generation():
    searcher = HyDESearcher()

    query = "How do I reset my password?"
    hypothetical = await searcher._generate_hypothetical_answer(query)

    # Hypothetical answer should be longer than query
    assert len(hypothetical) > len(query)

    # Should contain relevant keywords
    assert "password" in hypothetical.lower()
```

### Expected Results
- **Accuracy**: +18-25% on ambiguous/multi-hop queries
- **Latency**: +200ms per query (LLM generation)
- **Cost**: $0 with Ollama, ~$0.002/query with Haiku
- **Quality**: Better matching for question-style queries

---

## 📊 Phase 1 Success Metrics

### Accuracy Targets
- **Top-10 Precision**: 75% → **≥95%** (+27%)
- **Mean Reciprocal Rank**: Current → **+20%**
- **Answer Accuracy**: 95% → **≥97%**

### Performance Targets
- **Indexing Latency**: <2x slowdown (acceptable)
- **Search Latency**: <500ms increase
- **Memory Usage**: <30% increase

### Cost Targets
- **Total Cost**: ~$0 using Ollama
- **Alternative**: <$100 for 10K docs using Haiku

---

## 🧪 Testing Plan

### 1. Create Benchmark Query Set
```python
# tests/data/benchmark_queries.json
[
    {
        "id": 1,
        "query": "What is the revenue for Q3 2024?",
        "expected_chunks": ["chunk_123", "chunk_456"],
        "difficulty": "simple"
    },
    {
        "id": 2,
        "query": "How does the new algorithm compare to the previous version in terms of accuracy and speed?",
        "expected_chunks": ["chunk_789", "chunk_012"],
        "difficulty": "complex"
    }
    // ... 50-100 total queries
]
```

### 2. Run A/B Tests
```bash
# Baseline (current system)
pytest tests/benchmarks/test_accuracy.py --baseline

# With contextual retrieval only
pytest tests/benchmarks/test_accuracy.py --contextual-only

# With late chunking only
pytest tests/benchmarks/test_accuracy.py --late-chunking-only

# With HyDE only
pytest tests/benchmarks/test_accuracy.py --hyde-only

# All combined
pytest tests/benchmarks/test_accuracy.py --all-features
```

### 3. Measure Results
- Top-10 precision (% correct in top 10)
- Mean Reciprocal Rank (average position)
- Latency (p50, p95, p99)
- Memory usage (peak)

---

## 🚀 Deployment Checklist

- [ ] Set up Ollama (or configure Haiku)
- [ ] Pull llama3.2:3b model
- [ ] Update config with new settings
- [ ] Run tests to verify all components
- [ ] Create benchmark query set
- [ ] Run A/B tests
- [ ] Deploy to staging
- [ ] Monitor accuracy metrics
- [ ] Deploy to production
- [ ] Document new features

---

Last Updated: Nov 15, 2025
Status: Ready for Implementation
