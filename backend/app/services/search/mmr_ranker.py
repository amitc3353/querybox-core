"""
MMR (Maximal Marginal Relevance) Ranker for Step 10.2

Implements diversity-based result selection to reduce redundancy.
"""
from typing import List, Optional
import structlog
import numpy as np

from app.schemas.search import SearchResultItem
from app.core.config import settings

logger = structlog.get_logger()


class MMRRanker:
    """
    Maximal Marginal Relevance (MMR) Algorithm for Result Diversification

    MMR Formula:
    MMR = argmax[D_i ∈ R \ S] [λ * Relevance(D_i, Q) - (1-λ) * max[D_j ∈ S] Similarity(D_i, D_j)]

    Where:
    - R = candidate result set
    - S = already selected results
    - Q = query
    - λ = diversity factor (0 = max diversity, 1 = max relevance)
    - Relevance(D_i, Q) = relevance score from reranking
    - Similarity(D_i, D_j) = cosine similarity between embeddings

    Process:
    1. Start with empty selected set S
    2. Select document with highest relevance score
    3. For each remaining document:
       - Calculate MMR score = λ * relevance - (1-λ) * max_similarity_to_selected
       - Select document with highest MMR score
    4. Repeat until k documents selected

    Benefits:
    - Diversifies results across different topics
    - Reduces redundancy (same information repeated)
    - Balances relevance and novelty

    Typical λ values:
    - λ=1.0: No diversity (pure relevance ranking)
    - λ=0.7: Balanced (recommended default)
    - λ=0.5: Equal weight to relevance and diversity
    - λ=0.3: High diversity (may sacrifice relevance)
    """

    def __init__(self, lambda_param: float = None):
        """
        Initialize MMR ranker

        Args:
            lambda_param: Diversity factor (0-1, higher = more relevance, less diversity)
        """
        self.lambda_param = lambda_param if lambda_param is not None else settings.MMR_LAMBDA

        if not 0.0 <= self.lambda_param <= 1.0:
            raise ValueError(f"lambda_param must be 0.0-1.0, got {self.lambda_param}")

        logger.info("mmr_ranker_initialized", lambda_param=self.lambda_param)

    def rerank_with_mmr(
        self,
        candidates: List[SearchResultItem],
        top_k: int = 10
    ) -> List[SearchResultItem]:
        """
        Apply MMR to diversify results

        Greedy selection algorithm:
        1. Select document with highest relevance score first
        2. For each iteration:
           - For each remaining candidate, calculate MMR score
           - MMR = λ * relevance - (1-λ) * max_similarity_to_selected
           - Select candidate with highest MMR score
        3. Repeat until k documents selected

        Args:
            candidates: Results with relevance_score and embedding
            top_k: Number of results to return

        Returns:
            Diversified list of top-k results
        """
        if not candidates:
            logger.debug("mmr_rerank_skipped_empty_candidates")
            return []

        # Handle edge cases
        if len(candidates) <= top_k:
            logger.debug(
                "mmr_rerank_skipped_not_enough_candidates",
                candidates_count=len(candidates),
                top_k=top_k
            )
            return candidates

        if top_k <= 0:
            logger.warning("mmr_rerank_invalid_top_k", top_k=top_k)
            return []

        logger.info(
            "mmr_rerank_started",
            candidates_count=len(candidates),
            top_k=top_k,
            lambda_param=self.lambda_param
        )

        try:
            # Extract embeddings from candidates
            embeddings = []
            for candidate in candidates:
                embedding = self._get_embedding_vector(candidate)
                if embedding is None:
                    # Embeddings not available - fall back to relevance-only ranking
                    logger.warning(
                        "mmr_rerank_embeddings_not_available",
                        note="Falling back to relevance-only ranking. "
                             "For full MMR diversity, embeddings must be included in SearchResultItem. "
                             "Consider adding embedding field or fetching from DB in Phase 3."
                    )
                    return sorted(candidates, key=lambda x: x.relevance_score, reverse=True)[:top_k]
                embeddings.append(embedding)

            # Convert to numpy array for efficient computation
            embeddings_matrix = np.array(embeddings)

            # Normalize embeddings for cosine similarity
            # cosine_similarity = dot(A, B) / (||A|| * ||B||)
            # For normalized vectors: cosine_similarity = dot(A, B)
            norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
            normalized_embeddings = embeddings_matrix / (norms + 1e-10)  # Add epsilon to prevent division by zero

            logger.debug(
                "mmr_embeddings_prepared",
                embeddings_count=len(embeddings),
                embedding_dim=embeddings_matrix.shape[1]
            )

            # MMR greedy selection
            selected_indices = []
            remaining_indices = list(range(len(candidates)))

            # Step 1: Select document with highest relevance score
            max_relevance_idx = max(remaining_indices, key=lambda i: candidates[i].relevance_score)
            selected_indices.append(max_relevance_idx)
            remaining_indices.remove(max_relevance_idx)

            logger.debug(
                "mmr_first_selection",
                document_id=candidates[max_relevance_idx].document_id,
                relevance_score=candidates[max_relevance_idx].relevance_score
            )

            # Step 2: Iteratively select documents with highest MMR score
            while len(selected_indices) < top_k and remaining_indices:
                mmr_scores = []

                for candidate_idx in remaining_indices:
                    # Relevance term: λ * Relevance(D_i, Q)
                    relevance = candidates[candidate_idx].relevance_score

                    # Diversity term: (1-λ) * max[D_j ∈ S] Similarity(D_i, D_j)
                    # Calculate similarity to all selected documents
                    candidate_embedding = normalized_embeddings[candidate_idx]

                    max_similarity = 0.0
                    for selected_idx in selected_indices:
                        selected_embedding = normalized_embeddings[selected_idx]
                        # Cosine similarity for normalized vectors
                        similarity = np.dot(candidate_embedding, selected_embedding)
                        max_similarity = max(max_similarity, similarity)

                    # MMR score
                    mmr_score = (
                        self.lambda_param * relevance -
                        (1 - self.lambda_param) * max_similarity
                    )

                    mmr_scores.append((candidate_idx, mmr_score))

                # Select candidate with highest MMR score
                best_idx, best_mmr = max(mmr_scores, key=lambda x: x[1])
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)

                logger.debug(
                    "mmr_iteration",
                    iteration=len(selected_indices),
                    selected_document_id=candidates[best_idx].document_id,
                    mmr_score=round(best_mmr, 4),
                    relevance_score=candidates[best_idx].relevance_score
                )

            # Build result list preserving MMR order
            reranked_results = [candidates[idx] for idx in selected_indices]

            # Calculate diversity metrics
            diversity_score = self.calculate_diversity_score(reranked_results)

            logger.info(
                "mmr_rerank_completed",
                input_count=len(candidates),
                output_count=len(reranked_results),
                diversity_score=round(diversity_score, 4),
                lambda_param=self.lambda_param
            )

            return reranked_results

        except Exception as e:
            logger.error(
                "mmr_rerank_failed",
                candidates_count=len(candidates),
                top_k=top_k,
                error=str(e),
                exc_info=True
            )
            # Fallback: Return top-k by relevance
            return sorted(candidates, key=lambda x: x.relevance_score, reverse=True)[:top_k]

    def calculate_diversity_score(
        self,
        results: List[SearchResultItem]
    ) -> float:
        """
        Calculate average pairwise diversity (1 - similarity)

        Algorithm:
        1. Extract embeddings from results
        2. Calculate pairwise cosine similarities
        3. Diversity = 1 - average_similarity

        Higher score = more diverse results
        Range: 0.0 (all identical) to 1.0 (completely diverse)

        Args:
            results: List of search results with embeddings

        Returns:
            Diversity score (0.0-1.0)
        """
        if not results or len(results) <= 1:
            # No diversity to calculate with 0 or 1 result
            return 1.0

        try:
            # Extract embeddings
            embeddings = []
            for result in results:
                embedding = self._get_embedding_vector(result)
                if embedding is None:
                    logger.debug("diversity_score_embeddings_not_available")
                    return 0.5  # Neutral score when embeddings not available
                embeddings.append(embedding)

            # Convert to numpy array
            embeddings_matrix = np.array(embeddings)

            # Normalize for cosine similarity
            norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
            normalized_embeddings = embeddings_matrix / (norms + 1e-10)

            # Calculate pairwise similarities
            n = len(results)
            similarities = []

            for i in range(n):
                for j in range(i + 1, n):  # Only upper triangle (avoid duplicates)
                    similarity = np.dot(normalized_embeddings[i], normalized_embeddings[j])
                    similarities.append(similarity)

            if not similarities:
                return 1.0  # Single result

            # Average similarity
            avg_similarity = float(np.mean(similarities))

            # Diversity = 1 - similarity
            diversity = 1.0 - avg_similarity

            logger.debug(
                "diversity_score_calculated",
                results_count=len(results),
                avg_similarity=round(avg_similarity, 4),
                diversity_score=round(diversity, 4)
            )

            return diversity

        except Exception as e:
            logger.error(
                "diversity_score_calculation_failed",
                results_count=len(results),
                error=str(e),
                exc_info=True
            )
            return 0.5  # Neutral score on error

    def _get_embedding_vector(self, candidate: SearchResultItem) -> Optional[np.ndarray]:
        """
        Extract embedding vector from SearchResultItem

        Currently, SearchResultItem schema doesn't include embeddings.
        This method checks for optional embedding field that may be added
        in Phase 3 integration.

        Args:
            candidate: SearchResultItem (possibly with embedding field)

        Returns:
            Embedding vector as numpy array, or None if not available
        """
        # Check if candidate has embedding attribute (may be added as extra field)
        if hasattr(candidate, 'embedding') and candidate.embedding is not None:
            embedding = candidate.embedding

            # Convert to numpy array if needed
            if isinstance(embedding, list):
                return np.array(embedding)
            elif isinstance(embedding, np.ndarray):
                return embedding
            else:
                logger.warning(
                    "unexpected_embedding_type",
                    embedding_type=type(embedding).__name__
                )
                return None

        # Embeddings not available
        return None


def get_mmr_ranker(lambda_param: float = None) -> MMRRanker:
    """
    Factory function to create MMRRanker instance

    Args:
        lambda_param: Diversity factor (default from settings)

    Returns:
        MMRRanker instance
    """
    return MMRRanker(lambda_param=lambda_param)
