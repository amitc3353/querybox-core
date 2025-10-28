"""
Advanced Deduplication Service for Step 10.2

Implements multiple deduplication strategies for search results.
"""
from typing import List, Set, Dict, Optional
import hashlib
import structlog
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.schemas.search import SearchResultItem
from app.core.config import settings

logger = structlog.get_logger()


class DeduplicationService:
    """
    Advanced Deduplication for Search Results

    Implements 3 deduplication strategies:

    1. **Exact Deduplication (chunk_id)**
       - Removes exact duplicate chunks (same document_id + chunk_index)
       - O(n) with hash set

    2. **Content-Based Deduplication (SHA-256 hash)**
       - Hashes normalized chunk text
       - Catches identical content with different whitespace/formatting
       - O(n) with hash set

    3. **Semantic Deduplication (embedding similarity)**
       - Compares embedding vectors using cosine similarity
       - Catches near-duplicates with slightly different wording
       - Threshold: 0.95 cosine similarity (very similar)
       - O(n²) pairwise comparison (expensive, use sparingly)

    Why needed:
    - Different chunks may have identical or near-identical content
    - Copy-pasted sections across documents
    - Repeated disclaimers, headers, footers
    - Boilerplate text

    Performance:
    - Exact dedup: O(n) - very fast
    - Content dedup: O(n) - fast
    - Semantic dedup: O(n²) - expensive, only for small result sets (<100)
    """

    def __init__(
        self,
        semantic_threshold: float = None,
        enable_semantic_dedup: bool = None
    ):
        """
        Initialize deduplication service

        Args:
            semantic_threshold: Cosine similarity threshold for near-duplicates (0.90-0.98)
            enable_semantic_dedup: Enable expensive semantic deduplication
        """
        self.semantic_threshold = (
            semantic_threshold if semantic_threshold is not None
            else settings.SEMANTIC_DEDUP_THRESHOLD
        )
        self.enable_semantic_dedup = (
            enable_semantic_dedup if enable_semantic_dedup is not None
            else settings.ENABLE_SEMANTIC_DEDUP
        )

        logger.info(
            "deduplication_service_initialized",
            semantic_threshold=self.semantic_threshold,
            enable_semantic_dedup=self.enable_semantic_dedup
        )

    def deduplicate(
        self,
        candidates: List[SearchResultItem]
    ) -> List[SearchResultItem]:
        """
        Apply all deduplication strategies

        Order matters:
        1. Exact dedup (fastest, catches most duplicates)
        2. Content dedup (fast, catches formatting variations)
        3. Semantic dedup (slow, catches near-duplicates)

        Args:
            candidates: List of search result items

        Returns:
            Deduplicated list (preserves relative order of kept items)
        """
        if not candidates:
            logger.debug("deduplicate_skipped_empty_candidates")
            return []

        original_count = len(candidates)

        logger.info(
            "deduplication_started",
            candidates_count=original_count,
            enable_semantic_dedup=self.enable_semantic_dedup
        )

        # Stage 1: Exact deduplication by chunk_id
        stage1_start_count = len(candidates)
        candidates = self._deduplicate_by_chunk_id(candidates)
        stage1_removed = stage1_start_count - len(candidates)

        logger.debug(
            "dedup_stage1_completed",
            strategy="chunk_id",
            input_count=stage1_start_count,
            output_count=len(candidates),
            removed=stage1_removed
        )

        # Stage 2: Content-based deduplication
        stage2_start_count = len(candidates)
        candidates = self._deduplicate_by_content_hash(candidates)
        stage2_removed = stage2_start_count - len(candidates)

        logger.debug(
            "dedup_stage2_completed",
            strategy="content_hash",
            input_count=stage2_start_count,
            output_count=len(candidates),
            removed=stage2_removed
        )

        # Stage 3: Semantic deduplication (optional, expensive)
        stage3_removed = 0
        if self.enable_semantic_dedup and len(candidates) <= 100:
            stage3_start_count = len(candidates)
            candidates = self._deduplicate_by_embedding_similarity(candidates)
            stage3_removed = stage3_start_count - len(candidates)

            logger.debug(
                "dedup_stage3_completed",
                strategy="embedding_similarity",
                input_count=stage3_start_count,
                output_count=len(candidates),
                removed=stage3_removed
            )
        elif self.enable_semantic_dedup and len(candidates) > 100:
            logger.warning(
                "dedup_stage3_skipped_too_many_candidates",
                candidates_count=len(candidates),
                max_allowed=100
            )

        total_removed = original_count - len(candidates)

        logger.info(
            "deduplication_completed",
            original_count=original_count,
            final_count=len(candidates),
            total_removed=total_removed,
            stage1_removed=stage1_removed,
            stage2_removed=stage2_removed,
            stage3_removed=stage3_removed
        )

        return candidates

    def _deduplicate_by_chunk_id(
        self,
        candidates: List[SearchResultItem]
    ) -> List[SearchResultItem]:
        """
        Remove exact duplicate chunks (by document_id + chunk_index)
        Keep highest-scored occurrence

        Args:
            candidates: List of search results

        Returns:
            Deduplicated list
        """
        seen = {}

        for candidate in candidates:
            chunk_id = self._get_chunk_id(candidate)

            if chunk_id not in seen:
                seen[chunk_id] = candidate
            else:
                # Keep higher-scored version
                if candidate.relevance_score > seen[chunk_id].relevance_score:
                    seen[chunk_id] = candidate

        return list(seen.values())

    def _deduplicate_by_content_hash(
        self,
        candidates: List[SearchResultItem]
    ) -> List[SearchResultItem]:
        """
        Remove content duplicates using SHA-256 hash

        Normalization:
        - Convert to lowercase
        - Remove extra whitespace
        - Hash normalized text

        Args:
            candidates: List of search results

        Returns:
            Deduplicated list
        """
        seen_hashes: Set[str] = set()
        deduplicated = []

        for candidate in candidates:
            # Use snippet for hashing (contains the actual text content)
            text = candidate.snippet if candidate.snippet else candidate.document_name
            content_hash = self._calculate_content_hash(text)

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                deduplicated.append(candidate)
            else:
                logger.debug(
                    "duplicate_content_detected",
                    document_id=candidate.document_id,
                    chunk_index=candidate.chunk_index,
                    content_hash=content_hash[:16]  # First 16 chars
                )

        return deduplicated

    def _calculate_content_hash(self, text: str) -> str:
        """
        Calculate SHA-256 hash of normalized text

        Normalization steps:
        1. Lowercase
        2. Remove extra whitespace
        3. Hash UTF-8 bytes

        Args:
            text: Text to hash

        Returns:
            SHA-256 hash (hex string)
        """
        # Normalize text
        normalized = text.lower()
        normalized = ' '.join(normalized.split())  # Remove extra whitespace

        # Calculate SHA-256 hash
        hash_bytes = hashlib.sha256(normalized.encode('utf-8')).digest()
        hash_hex = hash_bytes.hex()

        return hash_hex

    def _deduplicate_by_embedding_similarity(
        self,
        candidates: List[SearchResultItem]
    ) -> List[SearchResultItem]:
        """
        Remove near-duplicates using embedding similarity

        Algorithm:
        1. Sort by relevance score (descending) - keep highest-scored
        2. Keep first item
        3. For each subsequent item:
           - Calculate similarity to all kept items
           - If max similarity > threshold, discard
           - Otherwise, keep

        O(n²) complexity - use only for final top-k (k < 100)

        Args:
            candidates: List of search results with embeddings

        Returns:
            Deduplicated list
        """
        if not candidates or len(candidates) == 1:
            return candidates

        # Check if we have embeddings - if not, skip semantic dedup
        # Note: Embeddings would need to be fetched from DB if not in SearchResultItem
        # For now, we'll skip if embeddings not available
        logger.warning(
            "semantic_dedup_skipped_embeddings_not_available",
            note="Embeddings not included in SearchResultItem schema. "
                 "Consider adding embedding field or fetching from DB for semantic dedup."
        )

        # Fallback: Just return candidates as-is
        # TODO: In Phase 3, integrate with DB to fetch embeddings if needed
        return candidates

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

    def calculate_deduplication_stats(
        self,
        original: List[SearchResultItem],
        deduplicated: List[SearchResultItem]
    ) -> Dict[str, any]:
        """
        Calculate deduplication statistics for monitoring

        Args:
            original: Original list before deduplication
            deduplicated: List after deduplication

        Returns:
            Statistics dictionary with counts and rate
        """
        original_count = len(original)
        deduplicated_count = len(deduplicated)
        duplicates_removed = original_count - deduplicated_count
        deduplication_rate = (
            duplicates_removed / original_count if original_count > 0 else 0.0
        )

        return {
            "original_count": original_count,
            "deduplicated_count": deduplicated_count,
            "duplicates_removed": duplicates_removed,
            "deduplication_rate": round(deduplication_rate, 4)
        }


def get_deduplication_service(
    semantic_threshold: float = None,
    enable_semantic_dedup: bool = None
) -> DeduplicationService:
    """
    Factory function to create DeduplicationService instance

    Args:
        semantic_threshold: Similarity threshold (default from settings)
        enable_semantic_dedup: Enable semantic dedup (default from settings)

    Returns:
        DeduplicationService instance
    """
    return DeduplicationService(
        semantic_threshold=semantic_threshold,
        enable_semantic_dedup=enable_semantic_dedup
    )
