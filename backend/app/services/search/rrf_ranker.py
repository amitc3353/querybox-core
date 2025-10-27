"""
RRF Ranker for Step 10.1 - Hybrid Retrieval

Reciprocal Rank Fusion (RRF) algorithm for combining multiple search result lists.
"""
from typing import List, Optional, Dict
import structlog

from app.schemas.search import SearchResultItem
from app.core.config import settings

logger = structlog.get_logger()


class RRFRanker:
    """
    Reciprocal Rank Fusion (RRF) Algorithm

    RRF combines multiple ranked lists into a single ranked list.

    RRF Formula:
    RRFscore(d) = Σ (weight_i / (k + rank_i(d)))

    Where:
    - d = document/chunk
    - rank_i(d) = rank of d in list i (1-indexed)
    - weight_i = weight for list i (default 0.5 for each)
    - k = constant (default 60, prevents division by zero, reduces ranking volatility)

    Advantages over linear combination:
    - No need to normalize scores from different systems
    - Robust to score distribution differences
    - Simple and effective
    - Used in production by major search systems (Elasticsearch, Vespa, etc.)
    """

    def __init__(self, k: int = None):
        """
        Initialize RRF ranker

        Args:
            k: RRF constant (40-100, default 60)
                - Lower k: More weight to top-ranked items
                - Higher k: More equal weighting across ranks
        """
        self.k = k if k is not None else settings.RRF_K

        logger.info("rrf_ranker_initialized", k=self.k)

    def fuse(
        self,
        keyword_results: List[SearchResultItem],
        vector_results: List[SearchResultItem],
        keyword_weight: float = None,
        vector_weight: float = None
    ) -> List[SearchResultItem]:
        """
        Fuse keyword and vector search results using RRF

        Steps:
        1. Create rank maps for both result lists
        2. Calculate RRF score for each unique chunk
        3. Apply optional weighting (keyword_weight, vector_weight)
        4. Sort by RRF score (descending)
        5. Deduplicate by chunk_id
        6. Return fused results

        Args:
            keyword_results: Results from BM25/keyword search (ranked)
            vector_results: Results from vector search (ranked)
            keyword_weight: Weight for keyword results (0-1)
            vector_weight: Weight for vector results (0-1)

        Returns:
            Fused and ranked results with updated relevance_score (RRF score)
        """
        # Use default weights if not provided
        keyword_weight = keyword_weight if keyword_weight is not None else settings.RRF_KEYWORD_WEIGHT
        vector_weight = vector_weight if vector_weight is not None else settings.RRF_VECTOR_WEIGHT

        logger.debug(
            "rrf_fusion_started",
            keyword_results_count=len(keyword_results),
            vector_results_count=len(vector_results),
            keyword_weight=keyword_weight,
            vector_weight=vector_weight,
            k=self.k
        )

        # Build rank maps (chunk_id -> rank)
        keyword_rank_map = self._build_rank_map(keyword_results)
        vector_rank_map = self._build_rank_map(vector_results)

        # Get all unique chunk IDs
        all_chunk_ids = set(keyword_rank_map.keys()) | set(vector_rank_map.keys())

        # Build chunk_id -> SearchResultItem map for lookup
        chunk_item_map = {}
        for item in keyword_results:
            chunk_id = self._get_chunk_id(item)
            chunk_item_map[chunk_id] = item
        for item in vector_results:
            chunk_id = self._get_chunk_id(item)
            if chunk_id not in chunk_item_map:  # Prefer keyword item if both exist
                chunk_item_map[chunk_id] = item

        # Calculate RRF scores for all chunks
        fused_results = []
        for chunk_id in all_chunk_ids:
            keyword_rank = keyword_rank_map.get(chunk_id)
            vector_rank = vector_rank_map.get(chunk_id)

            # Calculate RRF score
            rrf_score = self._calculate_rrf_score(
                keyword_rank=keyword_rank,
                vector_rank=vector_rank,
                keyword_weight=keyword_weight,
                vector_weight=vector_weight
            )

            # Get the SearchResultItem
            item = chunk_item_map[chunk_id]

            # Create new item with updated RRF score
            fused_item = SearchResultItem(
                document_id=item.document_id,
                document_name=item.document_name,
                relevance_score=rrf_score,
                snippet=item.snippet,
                chunk_index=item.chunk_index,
                chunk_position=item.chunk_position,
                extraction_quality=item.extraction_quality,
                document_type=item.document_type,
                created_at=item.created_at
            )

            fused_results.append(fused_item)

        # Sort by RRF score (descending)
        fused_results.sort(key=lambda x: x.relevance_score, reverse=True)

        # Normalize RRF scores to 0.0-1.0 range
        fused_results = self._normalize_scores(fused_results)

        logger.info(
            "rrf_fusion_completed",
            keyword_results=len(keyword_results),
            vector_results=len(vector_results),
            fused_results=len(fused_results),
            avg_rrf_score=round(sum(r.relevance_score for r in fused_results) / len(fused_results), 4) if fused_results else 0.0
        )

        return fused_results

    def _build_rank_map(self, results: List[SearchResultItem]) -> Dict[str, int]:
        """
        Build chunk_id -> rank mapping

        Args:
            results: Ranked list of SearchResultItem (already sorted by relevance)

        Returns:
            Dict mapping chunk_id to rank (1-indexed)
        """
        rank_map = {}
        for rank, item in enumerate(results, start=1):
            chunk_id = self._get_chunk_id(item)
            rank_map[chunk_id] = rank

        return rank_map

    def _get_chunk_id(self, item: SearchResultItem) -> str:
        """
        Generate unique chunk identifier

        Args:
            item: SearchResultItem

        Returns:
            Unique chunk ID (e.g., "doc-id_chunk-index")
        """
        chunk_index = item.chunk_index if item.chunk_index is not None else 0
        return f"{item.document_id}_{chunk_index}"

    def _calculate_rrf_score(
        self,
        keyword_rank: Optional[int],
        vector_rank: Optional[int],
        keyword_weight: float,
        vector_weight: float
    ) -> float:
        """
        Calculate RRF score for a single item

        RRF_weighted = (keyword_weight / (k + keyword_rank)) +
                       (vector_weight / (k + vector_rank))

        If item doesn't appear in a list, rank = infinity (contributes 0)

        Args:
            keyword_rank: Rank in keyword results (1-indexed, None if not present)
            vector_rank: Rank in vector results (1-indexed, None if not present)
            keyword_weight: Weight for keyword results
            vector_weight: Weight for vector results

        Returns:
            RRF score (higher = more relevant)
        """
        score = 0.0

        # Add keyword contribution
        if keyword_rank is not None:
            score += keyword_weight / (self.k + keyword_rank)

        # Add vector contribution
        if vector_rank is not None:
            score += vector_weight / (self.k + vector_rank)

        return score

    def _normalize_scores(self, results: List[SearchResultItem]) -> List[SearchResultItem]:
        """
        Normalize RRF scores to 0.0-1.0 range

        Args:
            results: List of SearchResultItem with RRF scores

        Returns:
            Results with normalized scores (0.0-1.0)
        """
        if not results:
            return results

        # Find max RRF score
        max_score = max(r.relevance_score for r in results)

        if max_score == 0:
            return results

        # Normalize to 0.0-1.0
        normalized_results = []
        for item in results:
            normalized_score = item.relevance_score / max_score

            normalized_item = SearchResultItem(
                document_id=item.document_id,
                document_name=item.document_name,
                relevance_score=round(normalized_score, 4),
                snippet=item.snippet,
                chunk_index=item.chunk_index,
                chunk_position=item.chunk_position,
                extraction_quality=item.extraction_quality,
                document_type=item.document_type,
                created_at=item.created_at
            )

            normalized_results.append(normalized_item)

        return normalized_results


def get_rrf_ranker(k: int = None) -> RRFRanker:
    """
    Factory function to create RRFRanker instance

    Args:
        k: RRF constant (default from settings)

    Returns:
        RRFRanker instance
    """
    return RRFRanker(k=k)
