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
from app.services.search.cross_encoder_service import (
    CrossEncoderService
)
from app.services.search.mmr_ranker import (
    MMRRanker,
    get_mmr_ranker
)
from app.services.search.deduplication_service import (
    DeduplicationService,
    get_deduplication_service
)
from app.services.search.reranking_pipeline import (
    RerankingPipeline,
    get_reranking_pipeline
)
from app.services.search.multi_query_retriever import (
    MultiQueryRetriever,
    get_multi_query_retriever
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
    # Cross-Encoder Reranking (Step 10.2)
    "CrossEncoderService",
    # MMR Ranker (Step 10.2)
    "MMRRanker",
    "get_mmr_ranker",
    # Deduplication (Step 10.2)
    "DeduplicationService",
    "get_deduplication_service",
    # Reranking Pipeline (Step 10.2)
    "RerankingPipeline",
    "get_reranking_pipeline",
    # Multi-Query RAG (Phase 5)
    "MultiQueryRetriever",
    "get_multi_query_retriever",
]
