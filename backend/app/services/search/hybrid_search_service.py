"""
Hybrid Search Service for Step 10.1 - Hybrid Retrieval + RRF

Combines BM25 keyword search and vector semantic search using RRF fusion.
"""
import time
import asyncio
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
import structlog

from app.services.search.bm25_search_service import BM25SearchService
from app.services.search.vector_search_service import VectorSearchService
from app.services.search.rrf_ranker import RRFRanker
from app.schemas.search import (
    SearchFilters,
    SearchResultItem,
    SearchResponse
)
from app.core.config import settings

logger = structlog.get_logger()


class HybridSearchService:
    """
    Hybrid search combining BM25 keyword and vector semantic search

    Implements 4-stage retrieval pipeline:
    1. Parallel Retrieval: Execute keyword and vector search concurrently
    2. Result Fusion: Combine using RRF (Reciprocal Rank Fusion)
    3. Deduplication: Remove duplicate chunks (same chunk from both searches)
    4. Re-ranking: Sort by fused RRF score
    """

    def __init__(
        self,
        db: Session,
        bm25_service: BM25SearchService,
        vector_service: VectorSearchService,
        rrf_ranker: RRFRanker
    ):
        """
        Initialize hybrid search with component services

        Args:
            db: Database session
            bm25_service: BM25 keyword search service
            vector_service: Vector semantic search service
            rrf_ranker: RRF ranker for fusion
        """
        self.db = db
        self.bm25 = bm25_service
        self.vector = vector_service
        self.rrf = rrf_ranker

        logger.info("hybrid_search_service_initialized")

    def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 10,
        offset: int = 0,
        keyword_weight: float = None,
        vector_weight: float = None,
        keyword_top_k: int = None,
        vector_top_k: int = None
    ) -> SearchResponse:
        """
        Execute hybrid search with RRF fusion

        4-Stage Pipeline:

        Stage 1: Parallel Retrieval
        - Execute BM25 keyword search (top_k=100)
        - Execute vector semantic search (top_k=100)
        - Both use same filters

        Stage 2: RRF Fusion
        - Combine results using Reciprocal Rank Fusion
        - Apply keyword/vector weights
        - Calculate fused scores

        Stage 3: Deduplication
        - Remove duplicate chunks (by chunk_id)
        - Keep highest-scored occurrence

        Stage 4: Final Ranking
        - Sort by RRF score (descending)
        - Apply pagination (limit, offset)
        - Return top-k results

        Args:
            query: Search query
            filters: Metadata filters
            limit: Final results to return
            offset: Pagination offset
            keyword_weight: Weight for BM25 results (0-1)
            vector_weight: Weight for vector results (0-1)
            keyword_top_k: Candidates from keyword search (default 100)
            vector_top_k: Candidates from vector search (default 100)

        Returns:
            SearchResponse with hybrid-ranked results
        """
        start_time = time.time()

        # Use default values from settings if not provided
        keyword_weight = keyword_weight if keyword_weight is not None else settings.RRF_KEYWORD_WEIGHT
        vector_weight = vector_weight if vector_weight is not None else settings.RRF_VECTOR_WEIGHT
        keyword_top_k = keyword_top_k if keyword_top_k is not None else settings.HYBRID_KEYWORD_TOP_K
        vector_top_k = vector_top_k if vector_top_k is not None else settings.HYBRID_VECTOR_TOP_K

        logger.info(
            "hybrid_search_started",
            query=query[:100],
            keyword_weight=keyword_weight,
            vector_weight=vector_weight,
            keyword_top_k=keyword_top_k,
            vector_top_k=vector_top_k,
            limit=limit,
            offset=offset
        )

        # Stage 1: Parallel Retrieval
        stage1_start = time.time()
        try:
            keyword_results, vector_results = self._parallel_search(
                query=query,
                filters=filters,
                keyword_top_k=keyword_top_k,
                vector_top_k=vector_top_k
            )
        except Exception as e:
            logger.error(
                "parallel_search_failed",
                query=query[:100],
                error=str(e),
                exc_info=True
            )
            # Fallback: Try searches sequentially
            keyword_results = self._safe_keyword_search(query, filters, keyword_top_k)
            vector_results = self._safe_vector_search(query, filters, vector_top_k)

        stage1_time_ms = int((time.time() - stage1_start) * 1000)

        logger.debug(
            "parallel_retrieval_completed",
            keyword_results=len(keyword_results),
            vector_results=len(vector_results),
            stage1_time_ms=stage1_time_ms
        )

        # Stage 2: RRF Fusion
        stage2_start = time.time()
        fused_results = self.rrf.fuse(
            keyword_results=keyword_results,
            vector_results=vector_results,
            keyword_weight=keyword_weight,
            vector_weight=vector_weight
        )
        stage2_time_ms = int((time.time() - stage2_start) * 1000)

        logger.debug(
            "rrf_fusion_completed",
            fused_results=len(fused_results),
            stage2_time_ms=stage2_time_ms
        )

        # Stage 3: Deduplication (already handled by RRF ranker)
        # Stage 4: Final Ranking and Pagination
        stage4_start = time.time()

        # Total count before pagination
        total_count = len(fused_results)

        # Apply pagination
        paginated_results = fused_results[offset:offset + limit]

        stage4_time_ms = int((time.time() - stage4_start) * 1000)

        # Calculate total processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "hybrid_search_completed",
            query=query[:100],
            keyword_candidates=len(keyword_results),
            vector_candidates=len(vector_results),
            fused_count=total_count,
            returned_results=len(paginated_results),
            processing_time_ms=processing_time_ms,
            stage1_ms=stage1_time_ms,
            stage2_ms=stage2_time_ms,
            stage4_ms=stage4_time_ms
        )

        # Build response
        return SearchResponse(
            success=True,
            query=query,
            total_results=total_count,
            returned_results=len(paginated_results),
            results=paginated_results,
            processing_time_ms=processing_time_ms,
            filters_applied=filters
        )

    def _parallel_search(
        self,
        query: str,
        filters: Optional[SearchFilters],
        keyword_top_k: int,
        vector_top_k: int
    ) -> Tuple[List[SearchResultItem], List[SearchResultItem]]:
        """
        Execute keyword and vector search in parallel (synchronous version)

        Note: Using synchronous execution instead of asyncio for simplicity
        since the search services are not async.

        Args:
            query: Search query
            filters: Search filters
            keyword_top_k: Candidates from keyword search
            vector_top_k: Candidates from vector search

        Returns:
            Tuple of (keyword_results, vector_results)
        """
        # Execute both searches (they're fast enough to run sequentially for MVP)
        # For production, consider using threading or true async

        keyword_results = self._safe_keyword_search(query, filters, keyword_top_k)
        vector_results = self._safe_vector_search(query, filters, vector_top_k)

        return keyword_results, vector_results

    def _safe_keyword_search(
        self,
        query: str,
        filters: Optional[SearchFilters],
        top_k: int
    ) -> List[SearchResultItem]:
        """
        Execute keyword search with error handling

        Args:
            query: Search query
            filters: Search filters
            top_k: Number of results to retrieve

        Returns:
            List of SearchResultItem (empty list if error)
        """
        try:
            results = self.bm25.search(
                query=query,
                filters=filters,
                limit=top_k,
                offset=0
            )
            return results
        except Exception as e:
            logger.error(
                "keyword_search_failed_in_hybrid",
                query=query[:100],
                error=str(e),
                exc_info=True
            )
            return []

    def _safe_vector_search(
        self,
        query: str,
        filters: Optional[SearchFilters],
        top_k: int
    ) -> List[SearchResultItem]:
        """
        Execute vector search with error handling

        Args:
            query: Search query
            filters: Search filters
            top_k: Number of results to retrieve

        Returns:
            List of SearchResultItem (empty list if error)
        """
        try:
            response = self.vector.search(
                query=query,
                filters=filters,
                limit=top_k,
                offset=0,
                similarity_threshold=0.0
            )
            return response.results
        except Exception as e:
            logger.error(
                "vector_search_failed_in_hybrid",
                query=query[:100],
                error=str(e),
                exc_info=True
            )
            return []

    def _deduplicate_results(
        self,
        results: List[SearchResultItem]
    ) -> List[SearchResultItem]:
        """
        Remove duplicate chunks, keeping highest-scored

        Args:
            results: List of SearchResultItem

        Returns:
            Deduplicated list
        """
        seen_chunks = {}

        for item in results:
            chunk_id = f"{item.document_id}_{item.chunk_index}"

            if chunk_id not in seen_chunks:
                seen_chunks[chunk_id] = item
            else:
                # Keep item with higher relevance score
                if item.relevance_score > seen_chunks[chunk_id].relevance_score:
                    seen_chunks[chunk_id] = item

        return list(seen_chunks.values())


def get_hybrid_search_service(
    db: Session,
    bm25_service: BM25SearchService,
    vector_service: VectorSearchService,
    rrf_ranker: RRFRanker
) -> HybridSearchService:
    """
    Factory function to create HybridSearchService instance

    Args:
        db: Database session
        bm25_service: BM25 keyword search service
        vector_service: Vector semantic search service
        rrf_ranker: RRF ranker for fusion

    Returns:
        HybridSearchService instance
    """
    return HybridSearchService(
        db=db,
        bm25_service=bm25_service,
        vector_service=vector_service,
        rrf_ranker=rrf_ranker
    )
