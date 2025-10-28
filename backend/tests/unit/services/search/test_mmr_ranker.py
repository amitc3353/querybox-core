"""
Unit Tests for MMR (Maximal Marginal Relevance) Ranker (Step 10.2)
Tests MMRRanker without external dependencies
"""
import pytest
from unittest.mock import Mock
from uuid import uuid4
from datetime import datetime, timezone
import numpy as np

from app.services.search.mmr_ranker import (
    MMRRanker,
    get_mmr_ranker
)
from app.schemas.search import SearchResultItem
from app.core.config import settings


class TestMMRRanker:
    """Test MMRRanker"""

    @pytest.fixture
    def ranker_default(self):
        """Create MMR ranker with default lambda=0.7"""
        return MMRRanker(lambda_param=0.7)

    @pytest.fixture
    def ranker_pure_relevance(self):
        """Create MMR ranker with lambda=1.0 (pure relevance, no diversity)"""
        return MMRRanker(lambda_param=1.0)

    @pytest.fixture
    def ranker_pure_diversity(self):
        """Create MMR ranker with lambda=0.0 (pure diversity, no relevance)"""
        return MMRRanker(lambda_param=0.0)

    @pytest.fixture
    def candidates_with_embeddings(self):
        """Create test candidates with embeddings"""
        doc_id = str(uuid4())

        # Create candidates with varied embeddings to test diversity
        candidates = []
        for i in range(10):
            # Create embeddings with different patterns
            if i < 3:
                # First 3: Similar embeddings (same topic A)
                base_emb = np.array([1.0, 0.0, 0.0, 0.0])
                embedding = base_emb + np.random.rand(4) * 0.1
            elif i < 6:
                # Next 3: Similar embeddings (same topic B)
                base_emb = np.array([0.0, 1.0, 0.0, 0.0])
                embedding = base_emb + np.random.rand(4) * 0.1
            else:
                # Last 4: Diverse embeddings (different topics)
                embedding = np.random.rand(4)

            # Normalize
            embedding = embedding / (np.linalg.norm(embedding) + 1e-10)

            # Create pydantic model with extra embedding field
            class SearchResultWithEmbedding(SearchResultItem):
                embedding: list = None

                class Config:
                    arbitrary_types_allowed = True

            candidate = SearchResultWithEmbedding(
                document_id=doc_id,
                document_name=f"doc{i}.pdf",
                relevance_score=0.9 - i * 0.05,  # Descending relevance
                snippet=f"Test snippet {i}",
                chunk_index=i,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc),
                embedding=embedding.tolist()
            )
            candidates.append(candidate)

        return candidates

    @pytest.fixture
    def candidates_without_embeddings(self):
        """Create test candidates without embeddings"""
        doc_id = str(uuid4())
        return [
            SearchResultItem(
                document_id=doc_id,
                document_name=f"doc{i}.pdf",
                relevance_score=0.9 - i * 0.1,
                snippet=f"Test snippet {i}",
                chunk_index=i,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
            for i in range(5)
        ]

    # Test 1: MMR with lambda=0.7 (balanced)
    def test_mmr_diversity_lambda_0_7(self, ranker_default, candidates_with_embeddings):
        """Test MMR with lambda=0.7 balances relevance and diversity"""
        top_k = 5

        reranked = ranker_default.rerank_with_mmr(candidates_with_embeddings, top_k)

        # Should return top_k results
        assert len(reranked) == top_k

        # First result should be highest relevance (regardless of lambda)
        assert reranked[0].relevance_score == max(c.relevance_score for c in candidates_with_embeddings)

        # Subsequent results should balance relevance and diversity
        # (cannot assert exact order, but verify we got diverse results)
        diversity_score = ranker_default.calculate_diversity_score(reranked)

        # With lambda=0.7, should have some diversity (not perfect, not zero)
        assert 0.2 < diversity_score < 0.9

    # Test 2: MMR with lambda=1.0 (pure relevance)
    def test_mmr_diversity_lambda_1_0(self, ranker_pure_relevance, candidates_with_embeddings):
        """Test MMR with lambda=1.0 produces pure relevance ranking"""
        top_k = 5

        reranked = ranker_pure_relevance.rerank_with_mmr(candidates_with_embeddings, top_k)

        # Should return top_k results
        assert len(reranked) == top_k

        # With lambda=1.0, should select by relevance only (top-5 by relevance score)
        expected_scores = sorted(
            [c.relevance_score for c in candidates_with_embeddings],
            reverse=True
        )[:top_k]

        actual_scores = [r.relevance_score for r in reranked]

        # Should match top-k relevance scores
        assert actual_scores == expected_scores

    # Test 3: MMR with lambda=0.0 (pure diversity)
    def test_mmr_diversity_lambda_0_0(self, ranker_pure_diversity, candidates_with_embeddings):
        """Test MMR with lambda=0.0 maximizes diversity"""
        top_k = 5

        reranked = ranker_pure_diversity.rerank_with_mmr(candidates_with_embeddings, top_k)

        # Should return top_k results
        assert len(reranked) == top_k

        # First result should still be highest relevance
        assert reranked[0].relevance_score == max(c.relevance_score for c in candidates_with_embeddings)

        # Calculate diversity of results
        diversity_score = ranker_pure_diversity.calculate_diversity_score(reranked)

        # With lambda=0.0, should maximize diversity
        # Diversity should be higher than with lambda=0.7
        assert diversity_score > 0.3  # Should have high diversity

    # Test 4: Diversity score calculation
    def test_mmr_diversity_score_calculation(self, ranker_default, candidates_with_embeddings):
        """Test diversity score calculation is accurate"""
        # Select 3 candidates manually
        selected = candidates_with_embeddings[:3]

        diversity_score = ranker_default.calculate_diversity_score(selected)

        # Diversity score should be in [0.0, 1.0]
        assert 0.0 <= diversity_score <= 1.0

        # Calculate expected diversity manually
        embeddings = [np.array(c.embedding) for c in selected]

        # Normalize embeddings
        normalized = []
        for emb in embeddings:
            norm = np.linalg.norm(emb) + 1e-10
            normalized.append(emb / norm)

        # Calculate pairwise similarities
        similarities = []
        for i in range(len(normalized)):
            for j in range(i + 1, len(normalized)):
                sim = np.dot(normalized[i], normalized[j])
                similarities.append(sim)

        expected_diversity = 1.0 - np.mean(similarities) if similarities else 1.0

        # Should match expected diversity
        assert abs(diversity_score - expected_diversity) < 0.01

    # Test 5: Missing embeddings fallback
    def test_mmr_missing_embeddings(self, ranker_default, candidates_without_embeddings):
        """Test MMR falls back to relevance ranking when embeddings missing"""
        top_k = 3

        reranked = ranker_default.rerank_with_mmr(candidates_without_embeddings, top_k)

        # Should return top_k results
        assert len(reranked) == top_k

        # Should fall back to relevance-only ranking
        expected_scores = sorted(
            [c.relevance_score for c in candidates_without_embeddings],
            reverse=True
        )[:top_k]

        actual_scores = [r.relevance_score for r in reranked]

        # Should match top-k relevance scores (fallback behavior)
        assert actual_scores == expected_scores

    # Test 6: Empty candidates
    def test_mmr_empty_candidates(self, ranker_default):
        """Test MMR with empty candidates returns empty list"""
        empty_candidates = []

        reranked = ranker_default.rerank_with_mmr(empty_candidates, top_k=10)

        assert reranked == []

    # Test 7: Single candidate
    def test_mmr_single_candidate(self, ranker_default, candidates_with_embeddings):
        """Test MMR with single candidate returns single result"""
        single_candidate = [candidates_with_embeddings[0]]

        reranked = ranker_default.rerank_with_mmr(single_candidate, top_k=10)

        assert len(reranked) == 1
        assert reranked[0] == single_candidate[0]

    # Test 8: top_k exceeds candidates
    def test_mmr_top_k_exceeds_candidates(self, ranker_default, candidates_with_embeddings):
        """Test MMR when top_k > number of candidates"""
        # Request 20, but only 10 candidates
        reranked = ranker_default.rerank_with_mmr(candidates_with_embeddings, top_k=20)

        # Should return all candidates
        assert len(reranked) == len(candidates_with_embeddings)

    # Test 9: Lambda parameter validation
    def test_mmr_lambda_validation(self):
        """Test lambda parameter validation"""
        # Valid lambda values
        MMRRanker(lambda_param=0.0)  # Min
        MMRRanker(lambda_param=0.5)  # Middle
        MMRRanker(lambda_param=1.0)  # Max

        # Invalid lambda values
        with pytest.raises(ValueError):
            MMRRanker(lambda_param=-0.1)  # Below min

        with pytest.raises(ValueError):
            MMRRanker(lambda_param=1.1)  # Above max

    # Test 10: Greedy selection algorithm correctness
    def test_mmr_greedy_selection(self, ranker_default, candidates_with_embeddings):
        """Test greedy MMR selection algorithm is correct"""
        top_k = 3

        reranked = ranker_default.rerank_with_mmr(candidates_with_embeddings, top_k)

        # First selection: highest relevance
        assert reranked[0].relevance_score == max(c.relevance_score for c in candidates_with_embeddings)

        # All results should be unique (no duplicates)
        chunk_ids = [f"{r.document_id}_{r.chunk_index}" for r in reranked]
        assert len(chunk_ids) == len(set(chunk_ids))

        # Results should be in the order they were selected
        # (not necessarily sorted by any single criterion)
        assert len(reranked) == top_k


class TestGetMMRRanker:
    """Test get_mmr_ranker factory function"""

    def test_get_mmr_ranker_returns_instance(self):
        """Test factory returns MMRRanker instance"""
        ranker = get_mmr_ranker()

        assert ranker is not None
        assert isinstance(ranker, MMRRanker)

    def test_get_mmr_ranker_with_custom_lambda(self):
        """Test factory with custom lambda parameter"""
        ranker = get_mmr_ranker(lambda_param=0.5)

        assert ranker.lambda_param == 0.5

    def test_get_mmr_ranker_uses_settings_default(self):
        """Test factory uses settings default lambda"""
        ranker = get_mmr_ranker(lambda_param=None)

        assert ranker.lambda_param == settings.MMR_LAMBDA
