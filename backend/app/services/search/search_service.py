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
from app.services.embeddings.embedding_service import EmbeddingService
from app.schemas.search import SearchFilters, SearchResponse

logger = structlog.get_logger()


class SearchService:
    """
    Unified search interface supporting multiple search strategies

    Strategies:
    - keyword: Full-text search (fast, exact matches)
    - vector: Semantic search (slower, conceptual matches)
    - hybrid: Combined BM25 + vector search with RRF fusion
    """

    def __init__(self, db: Session, embedding_service: Optional[EmbeddingService] = None):
        """
        Initialize unified search service

        Args:
            db: Database session
            embedding_service: Optional embedding service for vector search
        """
        self.db = db
        self.keyword = KeywordSearchService(db)
        self.bm25 = BM25SearchService(db)
        self.vector = VectorSearchService(db, embedding_service) if embedding_service else None

        # Initialize hybrid search if vector search is available
        self.hybrid = None
        if self.vector is not None:
            self.hybrid = HybridSearchService(
                db=db,
                bm25_service=self.bm25,
                vector_service=self.vector,
                rrf_ranker=RRFRanker()
            )

        logger.info(
            "search_service_initialized",
            keyword_available=True,
            vector_available=self.vector is not None,
            hybrid_available=self.hybrid is not None
        )

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
                **kwargs  # Pass through similarity_threshold, etc.
            )

        elif strategy == "hybrid":
            if self.hybrid is None:
                raise ValueError(
                    "Hybrid search not available. Embedding service not initialized."
                )
            return self.hybrid.search(
                query=query,
                filters=filters,
                limit=limit,
                offset=offset,
                keyword_weight=kwargs.get('keyword_weight'),
                vector_weight=kwargs.get('vector_weight'),
                keyword_top_k=kwargs.get('keyword_top_k'),
                vector_top_k=kwargs.get('vector_top_k')
            )

        else:
            # Should never reach here due to validation above
            raise ValueError(f"Unknown search strategy: {strategy}")


def get_unified_search_service(
    db: Session,
    embedding_service: Optional[EmbeddingService] = None
) -> SearchService:
    """
    Factory function to create unified SearchService instance

    Args:
        db: Database session
        embedding_service: Optional embedding service for vector search

    Returns:
        SearchService instance
    """
    return SearchService(db=db, embedding_service=embedding_service)
