"""
Unified Search Service

Provides a single interface for multiple search strategies:
- keyword: Full-text search using PostgreSQL ts_vector
- vector: Semantic search using pgvector cosine similarity
- hybrid: Combined keyword + vector search with RRF fusion
"""
from typing import Optional
from sqlalchemy.orm import Session
import structlog

from app.services.search.keyword_search_service import KeywordSearchService
from app.services.search.vector_search_service import VectorSearchService
from app.services.search.bm25_search_service import BM25SearchService
from app.services.search.hybrid_search_service import HybridSearchService
from app.services.search.rrf_ranker import RRFRanker
from app.services.search.cross_encoder_service import CrossEncoderService
from app.services.search.mmr_ranker import MMRRanker
from app.services.search.deduplication_service import DeduplicationService
from app.services.search.reranking_pipeline import RerankingPipeline
from app.services.embeddings.embedding_service import EmbeddingService
from app.schemas.search import SearchFilters, SearchResponse
from app.core.config import settings

logger = structlog.get_logger()


class SearchService:
    """
    Unified search interface supporting multiple search strategies

    Strategies:
    - keyword: Full-text search (fast, exact matches)
    - vector: Semantic search (slower, conceptual matches)
    - hybrid: Combined BM25 + vector search with RRF fusion
    """

    def __init__(
        self,
        db: Session,
        embedding_service: Optional[EmbeddingService] = None,
        enable_reranking: bool = None
    ):
        """
        Initialize unified search service

        Args:
            db: Database session
            embedding_service: Optional embedding service for vector search
            enable_reranking: Enable Step 10.2 reranking pipeline (default from settings)
        """
        self.db = db
        self.keyword = KeywordSearchService(db)
        self.bm25 = BM25SearchService(db)
        self.vector = VectorSearchService(db, embedding_service) if embedding_service else None

        # Store reranking settings for lazy initialization (Step 10.2)
        self._reranking_pipeline = None
        self._reranking_enabled = enable_reranking if enable_reranking is not None else settings.ENABLE_RERANKING
        self._reranking_init_attempted = False

        # Initialize hybrid search if vector search is available (reranking will be lazy-loaded)
        self.hybrid = None
        if self.vector is not None:
            self.hybrid = HybridSearchService(
                db=db,
                bm25_service=self.bm25,
                vector_service=self.vector,
                rrf_ranker=RRFRanker(),
                reranking_pipeline=None  # Will be lazy-loaded via property
            )

        logger.info(
            "search_service_initialized",
            keyword_available=True,
            vector_available=self.vector is not None,
            hybrid_available=self.hybrid is not None,
            reranking_lazy_load_enabled=self._reranking_enabled
        )

    @property
    def reranking_pipeline(self):
        """
        Lazy load reranking pipeline on first access

        This prevents loading heavy ML models (cross-encoder, MMR, deduplication)
        during SearchService initialization. Models are only loaded when reranking
        is actually requested via enable_reranking=True.

        Returns:
            RerankingPipeline instance or None if disabled/failed
        """
        if self._reranking_pipeline is None and self._reranking_enabled and not self._reranking_init_attempted:
            self._reranking_init_attempted = True
            try:
                logger.info("lazy_loading_reranking_pipeline")

                # Initialize component services
                cross_encoder = CrossEncoderService()
                mmr_ranker = MMRRanker()
                dedup_service = DeduplicationService()

                # Create reranking pipeline
                self._reranking_pipeline = RerankingPipeline(
                    cross_encoder=cross_encoder,
                    mmr_ranker=mmr_ranker,
                    dedup_service=dedup_service
                )

                # Update hybrid search service with initialized pipeline
                if self.hybrid is not None:
                    self.hybrid.reranking_pipeline = self._reranking_pipeline

                logger.info("reranking_pipeline_lazy_loaded_successfully")

            except Exception as e:
                logger.error(
                    "reranking_pipeline_lazy_loading_failed",
                    error=str(e),
                    exc_info=True,
                    note="Reranking will not be available. Hybrid search will work without reranking."
                )
                self._reranking_pipeline = None

        return self._reranking_pipeline

    def search(
        self,
        query: str,
        strategy: str = "hybrid",
        filters: Optional[SearchFilters] = None,
        limit: int = 10,
        offset: int = 0,
        **kwargs
    ) -> SearchResponse:
        """
        Execute search using specified strategy

        Args:
            query: Search query string
            strategy: Search strategy ("keyword", "vector", or "hybrid"). Default: "hybrid" (best)
            filters: Optional search filters
            limit: Maximum results to return
            offset: Pagination offset
            **kwargs: Additional strategy-specific parameters

        Returns:
            SearchResponse with results

        Raises:
            ValueError: If strategy is invalid or not available
        """
        # Validate strategy
        if strategy not in ["keyword", "vector", "hybrid"]:
            raise ValueError(f"Invalid search strategy: {strategy}. Must be 'keyword', 'vector', or 'hybrid'")

        # Log search request
        logger.info(
            "unified_search_request",
            query=query[:100],
            strategy=strategy,
            limit=limit,
            offset=offset
        )

        # Route to appropriate search service
        if strategy == "keyword":
            return self.keyword.search(
                query=query,
                filters=filters,
                limit=limit,
                offset=offset
            )

        elif strategy == "vector":
            if self.vector is None:
                raise ValueError(
                    "Vector search not available. Embedding service not initialized."
                )
            return self.vector.search(
                query=query,
                filters=filters,
                limit=limit,
                offset=offset,
                similarity_threshold=kwargs.get('similarity_threshold') or 0.0
            )

        elif strategy == "hybrid":
            if self.hybrid is None:
                raise ValueError(
                    "Hybrid search not available. Embedding service not initialized."
                )

            # Trigger lazy loading of reranking pipeline if reranking is requested
            enable_reranking = kwargs.get('enable_reranking', False)
            if enable_reranking:
                # Access the property to trigger lazy loading
                _ = self.reranking_pipeline

            return self.hybrid.search(
                query=query,
                filters=filters,
                limit=limit,
                offset=offset,
                keyword_weight=kwargs.get('keyword_weight'),
                vector_weight=kwargs.get('vector_weight'),
                keyword_top_k=kwargs.get('keyword_top_k'),
                vector_top_k=kwargs.get('vector_top_k'),
                # Step 10.2: Reranking parameters
                enable_reranking=enable_reranking,
                rerank_top_k=kwargs.get('rerank_top_k'),
                enable_mmr=kwargs.get('enable_mmr'),
                enable_dedup=kwargs.get('enable_dedup')
            )

        else:
            # Should never reach here due to validation above
            raise ValueError(f"Unknown search strategy: {strategy}")


def get_unified_search_service(
    db: Session,
    embedding_service: Optional[EmbeddingService] = None,
    enable_reranking: bool = None
) -> SearchService:
    """
    Factory function to create unified SearchService instance

    Args:
        db: Database session
        embedding_service: Optional embedding service for vector search
        enable_reranking: Enable Step 10.2 reranking pipeline (default from settings)

    Returns:
        SearchService instance
    """
    return SearchService(
        db=db,
        embedding_service=embedding_service,
        enable_reranking=enable_reranking
    )
