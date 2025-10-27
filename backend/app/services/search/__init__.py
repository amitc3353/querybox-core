"""
Search Services Package

Provides keyword, vector, hybrid, and unified search functionality for documents and chunks.
"""
from app.services.search.keyword_search_service import (
    KeywordSearchService,
    get_search_service
)
from app.services.search.vector_search_service import (
    VectorSearchService,
    get_vector_search_service
)
from app.services.search.bm25_search_service import (
    BM25SearchService,
    get_bm25_search_service
)
from app.services.search.rrf_ranker import (
    RRFRanker,
    get_rrf_ranker
)
from app.services.search.hybrid_search_service import (
    HybridSearchService,
    get_hybrid_search_service
)
from app.services.search.search_service import (
    SearchService,
    get_unified_search_service
)
from app.services.search.quality_validator import (
    QualityValidator,
    get_quality_validator
)
from app.services.search.validators import (
    VectorSearchValidator,
    get_vector_search_validator
)

__all__ = [
    # Keyword Search
    "KeywordSearchService",
    "get_search_service",
    # Vector Search
    "VectorSearchService",
    "get_vector_search_service",
    # BM25 Search
    "BM25SearchService",
    "get_bm25_search_service",
    # RRF Ranker
    "RRFRanker",
    "get_rrf_ranker",
    # Hybrid Search
    "HybridSearchService",
    "get_hybrid_search_service",
    # Unified Search
    "SearchService",
    "get_unified_search_service",
    # Quality Validation
    "QualityValidator",
    "get_quality_validator",
    # Vector Search Validation
    "VectorSearchValidator",
    "get_vector_search_validator",
]
