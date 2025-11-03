"""
Search Schemas for Step 8.3 & 9.3 - Keyword and Vector Search

Pydantic models for search requests and responses.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class SearchFilters(BaseModel):
    """Optional filters for search queries"""
    document_types: Optional[List[str]] = Field(None, max_items=10, description="Filter by document MIME types")
    date_from: Optional[datetime] = Field(None, description="Filter documents created after this date")
    date_to: Optional[datetime] = Field(None, description="Filter documents created before this date")
    min_quality: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum extraction quality score")
    tags: Optional[List[str]] = Field(None, max_items=20, description="Filter by document tags")

    @validator('date_to')
    def validate_date_range(cls, v, values):
        """Ensure date_to is after date_from"""
        if v and values.get('date_from'):
            if v < values['date_from']:
                raise ValueError("date_to must be after date_from")
        return v

    @validator('document_types')
    def validate_document_types(cls, v):
        """Validate document types against allowed list"""
        if v:
            allowed_types = [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # docx
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # xlsx
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # pptx
                'text/plain',
                'text/markdown',
                'text/html'
            ]
            invalid = [t for t in v if t not in allowed_types]
            if invalid:
                raise ValueError(f"Invalid document types: {invalid}. Allowed: {allowed_types}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "document_types": ["application/pdf"],
                "date_from": "2025-01-01T00:00:00Z",
                "min_quality": 0.7
            }
        }


class SearchQuery(BaseModel):
    """Search request schema"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query string")
    filters: Optional[SearchFilters] = Field(None, description="Optional search filters")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")
    include_snippets: bool = Field(True, description="Include text snippets with highlighted keywords")
    include_metadata: bool = Field(True, description="Include document metadata in results")

    @validator('query')
    def validate_query(cls, v):
        """Sanitize and validate query string"""
        # Remove leading/trailing whitespace
        v = v.strip()

        # Check not empty after stripping
        if not v:
            raise ValueError("Query cannot be empty")

        # Basic SQL injection prevention (paranoid check - SQLAlchemy handles this)
        dangerous_patterns = [';--', 'DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'UPDATE ', 'EXEC(']
        v_upper = v.upper()
        for pattern in dangerous_patterns:
            if pattern in v_upper:
                raise ValueError(f"Query contains forbidden pattern: {pattern}")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "machine learning algorithms",
                "filters": {
                    "document_types": ["application/pdf"],
                    "min_quality": 0.7
                },
                "limit": 10,
                "offset": 0
            }
        }


class SearchResultItem(BaseModel):
    """Individual search result"""
    chunk_id: Optional[str] = Field(None, description="Chunk/Embedding UUID (for citation extraction)")
    document_id: str = Field(..., description="Document UUID")
    document_name: str = Field(..., description="Document display name")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")
    snippet: Optional[str] = Field(None, description="Text excerpt with highlighted keywords")
    chunk_index: Optional[int] = Field(None, description="Chunk index if result is from a chunk")
    chunk_position: Optional[dict] = Field(None, description="Chunk position in document {start: int, end: int}")
    extraction_quality: Optional[float] = Field(None, ge=0.0, le=1.0, description="Extraction quality score")
    document_type: Optional[str] = Field(None, description="Document MIME type")
    created_at: Optional[datetime] = Field(None, description="Document creation timestamp")
    embedding: Optional[List[float]] = Field(None, description="Embedding vector for MMR diversity and semantic deduplication")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_name": "ML_Research_Paper.pdf",
                "relevance_score": 0.92,
                "snippet": "...various **machine learning algorithms** including neural networks...",
                "chunk_index": 5,
                "chunk_position": {"start": 4200, "end": 5150},
                "extraction_quality": 0.95,
                "document_type": "application/pdf",
                "created_at": "2025-10-23T14:30:00Z"
            }
        }


class SearchResponse(BaseModel):
    """Search response with results and metadata"""
    success: bool = Field(..., description="Whether the search was successful")
    query: str = Field(..., description="The search query that was executed")
    total_results: int = Field(..., ge=0, description="Total number of matching documents")
    returned_results: int = Field(..., ge=0, description="Number of results returned in this response")
    results: List[SearchResultItem] = Field(default_factory=list, description="Search results")
    processing_time_ms: int = Field(..., ge=0, description="Search processing time in milliseconds")
    filters_applied: Optional[SearchFilters] = Field(None, description="Filters that were applied to the search")
    suggestions: Optional[List[str]] = Field(None, description="Query suggestions or corrections")
    reranking_metadata: Optional[dict] = Field(None, description="Step 10.2 reranking pipeline metadata (if enabled)")

    class Config:
        extra = "allow"  # Allow extra fields like reranking_metadata
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "machine learning algorithms",
                "total_results": 47,
                "returned_results": 10,
                "results": [
                    {
                        "document_id": "550e8400-e29b-41d4-a716-446655440000",
                        "document_name": "ML_Research.pdf",
                        "relevance_score": 0.92,
                        "snippet": "...various **machine learning algorithms**...",
                        "extraction_quality": 0.95
                    }
                ],
                "processing_time_ms": 45,
                "filters_applied": {
                    "document_types": ["application/pdf"],
                    "min_quality": 0.7
                }
            }
        }


# Quality validation schemas (for quality endpoint)
class ExtractionQualityReport(BaseModel):
    """Extraction quality validation report"""
    document_id: str
    document_name: str
    extraction_status: str  # 'passed', 'failed', 'warning'
    text_length: int
    extraction_quality: Optional[float]
    extraction_method: Optional[str]
    pages_with_ocr: Optional[int]
    total_pages: Optional[int]
    detected_language: Optional[str]
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ChunkingQualityReport(BaseModel):
    """Chunking quality validation report"""
    document_id: str
    chunking_status: str  # 'passed', 'failed', 'warning'
    chunk_count: int
    avg_chunk_size: Optional[int]
    chunks_in_range: Optional[int]
    has_proper_overlap: Optional[bool]
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class SearchReadinessReport(BaseModel):
    """Overall search readiness status"""
    document_id: str
    document_name: str
    is_search_ready: bool
    extraction_passed: bool
    chunking_passed: bool
    overall_quality_score: float
    extraction_details: Optional[dict]
    chunking_details: Optional[dict]
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# ========================================
# Step 9.3: Vector Search Schemas
# ========================================

class VectorSearchQuery(BaseModel):
    """Vector similarity search request schema"""
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language search query")
    filters: Optional[SearchFilters] = Field(None, description="Optional search filters")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")
    similarity_threshold: float = Field(0.0, ge=0.0, le=1.0, description="Minimum cosine similarity (0.0-1.0)")
    include_embeddings: bool = Field(False, description="Include embedding vectors in response (debug only)")

    @validator('query')
    def validate_query(cls, v):
        """Sanitize and validate query string"""
        # Remove leading/trailing whitespace
        v = v.strip()

        # Check not empty after stripping
        if not v:
            raise ValueError("Query cannot be empty")

        # Remove null bytes
        if '\x00' in v:
            raise ValueError("Query contains invalid null bytes")

        return v

    @validator('similarity_threshold')
    def validate_threshold(cls, v):
        """Validate similarity threshold"""
        if v < 0.0 or v > 1.0:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "How do I reset my password?",
                "filters": {
                    "document_types": ["application/pdf"],
                    "min_quality": 0.7
                },
                "limit": 10,
                "offset": 0,
                "similarity_threshold": 0.5
            }
        }


class SearchStrategyEnum(str, Enum):
    """Available search strategies"""
    KEYWORD = "keyword"
    VECTOR = "vector"
    HYBRID = "hybrid"


class UnifiedSearchQuery(BaseModel):
    """Unified search request supporting multiple strategies"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query string")
    strategy: SearchStrategyEnum = Field(
        SearchStrategyEnum.HYBRID,
        description="Search strategy: 'keyword' (fast, exact), 'vector' (semantic), 'hybrid' (BEST - BM25 + vector with RRF fusion, default)"
    )
    filters: Optional[SearchFilters] = Field(None, description="Optional search filters")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum similarity for vector search")

    # Hybrid search parameters (Step 10.1)
    keyword_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Weight for keyword results in hybrid search (0.0-1.0)")
    vector_weight: Optional[float] = Field(None, ge=0.0, le=1.0, description="Weight for vector results in hybrid search (0.0-1.0)")
    keyword_top_k: Optional[int] = Field(None, ge=10, le=500, description="Number of candidates from keyword search in hybrid mode")
    vector_top_k: Optional[int] = Field(None, ge=10, le=500, description="Number of candidates from vector search in hybrid mode")

    # Advanced reranking parameters (Step 10.2)
    enable_reranking: bool = Field(False, description="Enable cross-encoder reranking + MMR + deduplication (Step 10.2)")
    rerank_top_k: Optional[int] = Field(None, ge=10, le=200, description="Number of candidates to keep after cross-encoder reranking")
    enable_mmr: Optional[bool] = Field(None, description="Enable MMR diversification in reranking pipeline")
    mmr_lambda: Optional[float] = Field(None, ge=0.0, le=1.0, description="MMR diversity parameter (0.0=max diversity, 1.0=max relevance)")
    enable_dedup: Optional[bool] = Field(None, description="Enable advanced deduplication in reranking pipeline")
    semantic_dedup_threshold: Optional[float] = Field(None, ge=0.8, le=0.99, description="Semantic deduplication similarity threshold")

    @validator('query')
    def validate_query(cls, v):
        """Sanitize and validate query string"""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        if '\x00' in v:
            raise ValueError("Query contains invalid null bytes")
        return v

    @validator('vector_weight')
    def validate_weights(cls, v, values):
        """Validate that weights are reasonable"""
        keyword_weight = values.get('keyword_weight')

        # If both weights are specified, ensure they're not both zero
        if keyword_weight is not None and v is not None:
            if keyword_weight == 0.0 and v == 0.0:
                raise ValueError("Both keyword_weight and vector_weight cannot be zero")

        return v

    @validator('rerank_top_k')
    def validate_rerank_top_k(cls, v, values):
        """Validate rerank_top_k parameter (Step 10.2 - Phase 5)"""
        if v is not None:
            # rerank_top_k should be greater than final limit
            limit = values.get('limit') or 10
            if v < limit:
                raise ValueError(f"rerank_top_k ({v}) should be >= limit ({limit}) to have enough candidates for final selection")

            # rerank_top_k should be reasonable relative to candidate pool
            # Handle None values explicitly (Optional fields default to None, not the .get() default)
            keyword_top_k = values.get('keyword_top_k') or 100
            vector_top_k = values.get('vector_top_k') or 100
            max_candidates = max(keyword_top_k, vector_top_k)

            if v > max_candidates:
                raise ValueError(f"rerank_top_k ({v}) should be <= max candidate pool size ({max_candidates})")

        return v

    @validator('mmr_lambda')
    def validate_mmr_lambda(cls, v, values):
        """Validate MMR lambda parameter (Step 10.2 - Phase 5)"""
        if v is not None:
            enable_mmr = values.get('enable_mmr')
            enable_reranking = values.get('enable_reranking', False)

            # If MMR is explicitly enabled but lambda not provided, use default
            if enable_mmr and v is None:
                return 0.7  # Default lambda

            # Warn about extreme values
            if v == 0.0:
                # Pure diversity, no relevance - rare use case
                pass
            elif v == 1.0:
                # Pure relevance, no diversity - defeats the purpose of MMR
                pass

        return v

    @validator('semantic_dedup_threshold')
    def validate_semantic_dedup_threshold(cls, v, values):
        """Validate semantic deduplication threshold (Step 10.2 - Phase 5)"""
        if v is not None:
            enable_dedup = values.get('enable_dedup')
            enable_reranking = values.get('enable_reranking', False)

            # If dedup enabled but threshold very low, might remove too many results
            if enable_dedup and v < 0.85:
                raise ValueError(f"semantic_dedup_threshold ({v}) is too low, may remove too many valid results. Minimum: 0.85")

            # If threshold very high (>0.98), might not catch near-duplicates
            if enable_dedup and v > 0.98:
                # This is a warning case but we'll allow it
                pass

        return v

    @validator('enable_reranking')
    def validate_reranking_configuration(cls, v, values):
        """Validate overall reranking configuration (Step 10.2 - Phase 5)"""
        if v:  # If reranking enabled
            strategy = values.get('strategy')

            # Reranking only makes sense for hybrid strategy
            if strategy and strategy != SearchStrategyEnum.HYBRID:
                raise ValueError(f"Reranking is only supported for 'hybrid' strategy, got '{strategy}'")

            # Check if we have enough candidates to make reranking worthwhile
            # Handle None values explicitly (Optional fields default to None, not the .get() default)
            keyword_top_k = values.get('keyword_top_k') or 100
            vector_top_k = values.get('vector_top_k') or 100
            limit = values.get('limit') or 10

            total_candidates = keyword_top_k + vector_top_k
            if total_candidates < 50:
                raise ValueError(f"Reranking requires at least 50 total candidates (keyword_top_k + vector_top_k), got {total_candidates}")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "machine learning algorithms",
                "strategy": "hybrid",
                "filters": {
                    "document_types": ["application/pdf"],
                    "min_quality": 0.7
                },
                "limit": 10,
                "offset": 0,
                "keyword_weight": 0.5,
                "vector_weight": 0.5,
                "keyword_top_k": 100,
                "vector_top_k": 100,
                "enable_reranking": True,
                "rerank_top_k": 50,
                "enable_mmr": True,
                "mmr_lambda": 0.7,
                "enable_dedup": True
            }
        }


# ========================================
# Step 10.3: Citation Extraction Schemas
# ========================================

class CitationPosition(BaseModel):
    """Position of citation in source document"""
    start: int = Field(..., description="Start character offset in document")
    end: int = Field(..., description="End character offset in document")

    class Config:
        json_schema_extra = {
            "example": {
                "start": 1234,
                "end": 1298
            }
        }


class Citation(BaseModel):
    """Single citation with source tracking"""
    text: str = Field(..., max_length=500, description="Citation text excerpt")
    page: Optional[int] = Field(None, ge=1, description="Page number in source document")
    section: Optional[str] = Field(None, max_length=500, description="Section heading in document")
    position: CitationPosition = Field(..., description="Character position in document")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Citation confidence score (0.0-1.0)")
    source_context: str = Field(..., description="Human-readable source context (e.g., 'Page 12, Section 3.2')")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "RAG systems improve accuracy by 40% compared to baseline LLMs",
                "page": 12,
                "section": "3.2 Performance Analysis",
                "position": {
                    "start": 1234,
                    "end": 1298
                },
                "confidence": 0.95,
                "source_context": "Page 12, 3.2 Performance Analysis"
            }
        }


class SearchResultItemWithCitations(SearchResultItem):
    """Search result with citation metadata"""
    citations: List[Citation] = Field(
        default_factory=list,
        description="Extracted citations from this chunk"
    )
    snippet_highlighted: Optional[str] = Field(
        None,
        description="Snippet with citation highlighting (HTML <mark> tags)"
    )
    source_page: Optional[int] = Field(
        None,
        ge=1,
        description="Primary source page number"
    )
    source_section: Optional[str] = Field(
        None,
        max_length=500,
        description="Primary source section heading"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_name": "RAG_Performance_Study.pdf",
                "relevance_score": 0.92,
                "snippet": "...RAG systems improve accuracy by 40%...",
                "chunk_index": 5,
                "citations": [
                    {
                        "text": "RAG systems improve accuracy by 40%",
                        "page": 12,
                        "section": "3.2 Performance Analysis",
                        "position": {"start": 1234, "end": 1298},
                        "confidence": 0.95,
                        "source_context": "Page 12, 3.2 Performance Analysis"
                    }
                ],
                "snippet_highlighted": "...RAG systems <mark data-page='12'>improve accuracy by 40%</mark>...",
                "source_page": 12,
                "source_section": "3.2 Performance Analysis"
            }
        }


class SearchResponseWithCitations(BaseModel):
    """Search response with citations"""
    success: bool = Field(..., description="Whether the search was successful")
    query: str = Field(..., description="The search query that was executed")
    total_results: int = Field(..., ge=0, description="Total number of matching documents")
    returned_results: int = Field(..., ge=0, description="Number of results returned in this response")
    results: List[SearchResultItemWithCitations] = Field(
        default_factory=list,
        description="Search results with citations"
    )
    processing_time_ms: int = Field(..., ge=0, description="Search processing time in milliseconds")
    citations_enabled: bool = Field(True, description="Whether citation extraction was enabled")
    filters_applied: Optional[SearchFilters] = Field(None, description="Filters that were applied to the search")
    reranking_metadata: Optional[dict] = Field(None, description="Reranking pipeline metadata (if enabled)")

    class Config:
        extra = "allow"
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "machine learning algorithms",
                "total_results": 47,
                "returned_results": 10,
                "results": [
                    {
                        "document_id": "550e8400-e29b-41d4-a716-446655440000",
                        "document_name": "ML_Research.pdf",
                        "relevance_score": 0.92,
                        "snippet": "...machine learning algorithms...",
                        "citations": [
                            {
                                "text": "ML algorithms improve performance by 40%",
                                "page": 5,
                                "section": "Results",
                                "position": {"start": 100, "end": 145},
                                "confidence": 0.9,
                                "source_context": "Page 5, Results"
                            }
                        ],
                        "source_page": 5
                    }
                ],
                "processing_time_ms": 450,
                "citations_enabled": True
            }
        }
