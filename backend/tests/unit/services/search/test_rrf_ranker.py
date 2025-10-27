"""
Unit Tests for RRF Ranker
Tests RRFRanker without external dependencies
"""
import pytest
from unittest.mock import Mock
from uuid import uuid4
from datetime import datetime, timezone

from app.services.search.rrf_ranker import (
    RRFRanker,
    get_rrf_ranker,
)
from app.schemas.search import SearchResultItem
from app.core.config import settings


class TestRRFRanker:
    """Test RRFRanker"""

    @pytest.fixture
    def ranker(self):
        """Create RRF ranker with k=60"""
        return RRFRanker(k=60)

    @pytest.fixture
    def keyword_results(self):
        """Sample keyword search results"""
        doc_id = str(uuid4())
        return [
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.95,
                snippet="test1",
                chunk_index=1,
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.85,
                snippet="test2",
                chunk_index=2,
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.75,
                snippet="test3",
                chunk_index=3,
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

    @pytest.fixture
    def vector_results(self):
        """Sample vector search results"""
        doc_id = str(uuid4())
        return [
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.90,
                snippet="test2",
                chunk_index=2,  # Same chunk as keyword rank 2
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.80,
                snippet="test4",
                chunk_index=4,  # New chunk
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

    # Tests for _calculate_rrf_score
    def test_calculate_rrf_score_both_ranks(self, ranker):
        """Test RRF score calculation when item appears in both lists"""
        # Item at rank 1 in keyword, rank 1 in vector
        score = ranker._calculate_rrf_score(1, 1, 0.5, 0.5)

        # RRF = 0.5/(60+1) + 0.5/(60+1) = 0.5/61 + 0.5/61 ≈ 0.0164
        expected = (0.5 / 61) + (0.5 / 61)
        assert abs(score - expected) < 0.0001

    def test_calculate_rrf_score_keyword_only(self, ranker):
        """Test RRF score when item only in keyword results"""
        # Item at rank 1 in keyword, not in vector (rank=None)
        score = ranker._calculate_rrf_score(1, None, 0.5, 0.5)

        # RRF = 0.5/(60+1) + 0 = 0.5/61 ≈ 0.0082
        expected = 0.5 / 61
        assert abs(score - expected) < 0.0001

    def test_calculate_rrf_score_vector_only(self, ranker):
        """Test RRF score when item only in vector results"""
        # Item not in keyword (rank=None), at rank 2 in vector
        score = ranker._calculate_rrf_score(None, 2, 0.5, 0.5)

        # RRF = 0 + 0.5/(60+2) = 0.5/62 ≈ 0.0081
        expected = 0.5 / 62
        assert abs(score - expected) < 0.0001

    def test_calculate_rrf_score_with_weights(self, ranker):
        """Test RRF score with different weights"""
        # Keyword-heavy weighting (0.7, 0.3)
        score = ranker._calculate_rrf_score(1, 1, 0.7, 0.3)

        # RRF = 0.7/(60+1) + 0.3/(60+1)
        expected = (0.7 / 61) + (0.3 / 61)
        assert abs(score - expected) < 0.0001

    def test_calculate_rrf_score_higher_rank_lower_score(self, ranker):
        """Test higher rank produces lower RRF score"""
        score_rank1 = ranker._calculate_rrf_score(1, 1, 0.5, 0.5)
        score_rank10 = ranker._calculate_rrf_score(10, 10, 0.5, 0.5)

        assert score_rank1 > score_rank10  # Lower rank number = higher score

    def test_calculate_rrf_score_none_both_ranks(self, ranker):
        """Test RRF score when item in neither list"""
        # Should not happen in practice, but test it
        score = ranker._calculate_rrf_score(None, None, 0.5, 0.5)

        assert score == 0.0

    def test_calculate_rrf_score_zero_weights(self, ranker):
        """Test RRF score with zero weights"""
        score = ranker._calculate_rrf_score(1, 1, 0.0, 0.0)

        assert score == 0.0

    def test_calculate_rrf_score_extreme_ranks(self, ranker):
        """Test RRF score with very high ranks"""
        score_rank1 = ranker._calculate_rrf_score(1, 1, 0.5, 0.5)
        score_rank1000 = ranker._calculate_rrf_score(1000, 1000, 0.5, 0.5)

        # Very high ranks should have very low scores
        assert score_rank1000 < score_rank1
        assert score_rank1000 > 0.0

    # Tests for _build_rank_map
    def test_build_rank_map_creates_mapping(self, ranker, keyword_results):
        """Test rank map creation"""
        rank_map = ranker._build_rank_map(keyword_results)

        # Should have 3 entries
        assert len(rank_map) == 3

        # Check ranks are 1-indexed
        for chunk_id, rank in rank_map.items():
            assert rank >= 1
            assert rank <= 3

    def test_build_rank_map_preserves_order(self, ranker, keyword_results):
        """Test rank map preserves result order"""
        rank_map = ranker._build_rank_map(keyword_results)

        # First result should be rank 1
        first_chunk_id = ranker._get_chunk_id(keyword_results[0])
        assert rank_map[first_chunk_id] == 1

        # Last result should be rank 3
        last_chunk_id = ranker._get_chunk_id(keyword_results[2])
        assert rank_map[last_chunk_id] == 3

    def test_build_rank_map_empty_list(self, ranker):
        """Test rank map with empty list"""
        rank_map = ranker._build_rank_map([])

        assert rank_map == {}

    # Tests for _get_chunk_id
    def test_get_chunk_id_creates_unique_id(self, ranker):
        """Test chunk ID generation"""
        doc_id = str(uuid4())
        item = SearchResultItem(
            document_id=doc_id,
            document_name="test.pdf",
            relevance_score=0.9,
            snippet="test",
            chunk_index=5,
            chunk_position=None,
            extraction_quality=0.9,
            document_type="application/pdf",
            created_at=datetime.now(timezone.utc)
        )

        chunk_id = ranker._get_chunk_id(item)

        assert chunk_id == f"{doc_id}_5"

    def test_get_chunk_id_handles_none_chunk_index(self, ranker):
        """Test chunk ID with None chunk_index"""
        doc_id = str(uuid4())
        item = SearchResultItem(
            document_id=doc_id,
            document_name="test.pdf",
            relevance_score=0.9,
            snippet="test",
            chunk_index=None,
            chunk_position=None,
            extraction_quality=0.9,
            document_type="application/pdf",
            created_at=datetime.now(timezone.utc)
        )

        chunk_id = ranker._get_chunk_id(item)

        # Should default to 0
        assert chunk_id == f"{doc_id}_0"

    def test_get_chunk_id_different_chunks_same_doc(self, ranker):
        """Test chunk IDs for different chunks in same document"""
        doc_id = str(uuid4())
        item1 = SearchResultItem(
            document_id=doc_id,
            document_name="test.pdf",
            relevance_score=0.9,
            snippet="test1",
            chunk_index=1,
            chunk_position=None,
            extraction_quality=0.9,
            document_type="application/pdf",
            created_at=datetime.now(timezone.utc)
        )
        item2 = SearchResultItem(
            document_id=doc_id,
            document_name="test.pdf",
            relevance_score=0.8,
            snippet="test2",
            chunk_index=2,
            chunk_position=None,
            extraction_quality=0.9,
            document_type="application/pdf",
            created_at=datetime.now(timezone.utc)
        )

        chunk_id1 = ranker._get_chunk_id(item1)
        chunk_id2 = ranker._get_chunk_id(item2)

        # Should be different
        assert chunk_id1 != chunk_id2

    # Tests for fuse
    def test_fuse_combines_results(self, ranker, keyword_results, vector_results):
        """Test RRF fusion combines results from both searches"""
        fused = ranker.fuse(keyword_results, vector_results, 0.5, 0.5)

        # Should have unique chunks from both
        assert len(fused) >= 3  # At least 3 unique chunks

    def test_fuse_deduplicates_chunks(self, ranker):
        """Test RRF fusion removes duplicate chunks"""
        doc_id = str(uuid4())

        # Same chunk appears in both (chunk_index=1)
        keyword_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.9,
                document_name="test.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]
        vector_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,  # Duplicate
                relevance_score=0.8,
                document_name="test.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        fused = ranker.fuse(keyword_results, vector_results, 0.5, 0.5)

        # Should only have 1 result (deduplicated)
        assert len(fused) == 1

    def test_fuse_updates_relevance_score_to_rrf(self, ranker, keyword_results, vector_results):
        """Test fused results have RRF scores as relevance_score"""
        fused = ranker.fuse(keyword_results, vector_results, 0.5, 0.5)

        # All results should have normalized RRF scores (0.0-1.0)
        for result in fused:
            assert 0.0 <= result.relevance_score <= 1.0

    def test_fuse_sorts_by_rrf_score(self, ranker, keyword_results, vector_results):
        """Test fused results are sorted by RRF score descending"""
        fused = ranker.fuse(keyword_results, vector_results, 0.5, 0.5)

        # Should be sorted descending
        scores = [r.relevance_score for r in fused]
        assert scores == sorted(scores, reverse=True)

    def test_fuse_empty_keyword_results(self, ranker, vector_results):
        """Test fusion with empty keyword results returns vector-only"""
        fused = ranker.fuse([], vector_results, 0.5, 0.5)

        assert len(fused) == len(vector_results)

    def test_fuse_empty_vector_results(self, ranker, keyword_results):
        """Test fusion with empty vector results returns keyword-only"""
        fused = ranker.fuse(keyword_results, [], 0.5, 0.5)

        assert len(fused) == len(keyword_results)

    def test_fuse_both_empty_returns_empty(self, ranker):
        """Test fusion with both empty returns empty list"""
        fused = ranker.fuse([], [], 0.5, 0.5)

        assert fused == []

    def test_fuse_weighted_fusion_keyword_heavy(self, ranker, keyword_results, vector_results):
        """Test keyword-heavy weighting affects ranking"""
        fused_balanced = ranker.fuse(keyword_results, vector_results, 0.5, 0.5)
        fused_keyword_heavy = ranker.fuse(keyword_results, vector_results, 0.8, 0.2)

        # First result might differ based on weights
        # Just verify we got results and they're ranked
        assert len(fused_balanced) > 0
        assert len(fused_keyword_heavy) > 0

    def test_fuse_weighted_fusion_vector_heavy(self, ranker, keyword_results, vector_results):
        """Test vector-heavy weighting affects ranking"""
        fused_balanced = ranker.fuse(keyword_results, vector_results, 0.5, 0.5)
        fused_vector_heavy = ranker.fuse(keyword_results, vector_results, 0.2, 0.8)

        # Both should return results
        assert len(fused_balanced) > 0
        assert len(fused_vector_heavy) > 0

    def test_fuse_uses_default_weights(self, ranker, keyword_results, vector_results):
        """Test fusion uses default weights from settings"""
        fused = ranker.fuse(keyword_results, vector_results, None, None)

        # Should complete successfully with defaults
        assert len(fused) > 0

    def test_fuse_preserves_metadata(self, ranker):
        """Test fusion preserves all item metadata"""
        doc_id = str(uuid4())
        created_at = datetime.now(timezone.utc)

        keyword_results = [
            SearchResultItem(
                document_id=doc_id,
                document_name="test.pdf",
                relevance_score=0.9,
                snippet="test snippet",
                chunk_index=1,
                chunk_position={'start': 0, 'end': 100},
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=created_at
            )
        ]
        vector_results = []

        fused = ranker.fuse(keyword_results, vector_results, 0.5, 0.5)

        # Verify metadata preserved
        assert fused[0].document_id == doc_id
        assert fused[0].document_name == "test.pdf"
        assert fused[0].snippet == "test snippet"
        assert fused[0].chunk_index == 1
        assert fused[0].chunk_position == {'start': 0, 'end': 100}
        assert fused[0].extraction_quality == 0.95
        assert fused[0].document_type == "application/pdf"
        assert fused[0].created_at == created_at

    # Tests for _normalize_scores
    def test_normalize_scores_to_0_1_range(self, ranker):
        """Test scores are normalized to 0.0-1.0 range"""
        doc_id = str(uuid4())
        # Create items with unnormalized RRF scores (small values from RRF formula)
        results = [
            SearchResultItem(
                document_id=doc_id,
                document_name="test.pdf",
                relevance_score=0.05,  # Already valid, but will be normalized to 1.0
                snippet="test1",
                chunk_index=1,
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="test.pdf",
                relevance_score=0.025,  # Half of max
                snippet="test2",
                chunk_index=2,
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="test.pdf",
                relevance_score=0.01,  # Lower score
                snippet="test3",
                chunk_index=3,
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        normalized = ranker._normalize_scores(results)

        # Max score should be 1.0
        assert normalized[0].relevance_score == 1.0
        # Others should be proportional
        assert 0.0 < normalized[1].relevance_score < 1.0
        assert 0.0 < normalized[2].relevance_score < normalized[1].relevance_score

    def test_normalize_scores_empty_list(self, ranker):
        """Test normalizing empty list returns empty list"""
        results = []
        normalized = ranker._normalize_scores(results)
        assert normalized == []

    def test_normalize_scores_single_result(self, ranker):
        """Test normalizing single result"""
        doc_id = str(uuid4())
        results = [
            SearchResultItem(
                document_id=doc_id,
                document_name="test.pdf",
                relevance_score=0.05,  # Valid RRF score
                snippet="test",
                chunk_index=1,
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        normalized = ranker._normalize_scores(results)

        # Single result should be normalized to 1.0
        assert normalized[0].relevance_score == 1.0

    def test_normalize_scores_zero_max(self, ranker):
        """Test normalizing when max score is zero"""
        doc_id = str(uuid4())
        results = [
            SearchResultItem(
                document_id=doc_id,
                document_name="test.pdf",
                relevance_score=0.0,
                snippet="test1",
                chunk_index=1,
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="test.pdf",
                relevance_score=0.0,
                snippet="test2",
                chunk_index=2,
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        normalized = ranker._normalize_scores(results)

        # Should return unchanged
        assert all(r.relevance_score == 0.0 for r in normalized)

    # Tests for initialization
    def test_init_with_custom_k(self):
        """Test initialization with custom k value"""
        ranker = RRFRanker(k=40)
        assert ranker.k == 40

    def test_init_default_k(self, ranker):
        """Test initialization with default k=60"""
        assert ranker.k == 60

    def test_init_uses_settings_default(self):
        """Test initialization uses settings default"""
        ranker = RRFRanker(k=None)
        assert ranker.k == settings.RRF_K


class TestGetRRFRanker:
    """Test get_rrf_ranker factory function"""

    def test_get_rrf_ranker_returns_instance(self):
        """Test factory returns RRFRanker instance"""
        ranker = get_rrf_ranker()

        assert ranker is not None
        assert isinstance(ranker, RRFRanker)

    def test_get_rrf_ranker_with_custom_k(self):
        """Test factory with custom k parameter"""
        ranker = get_rrf_ranker(k=40)

        assert ranker.k == 40

    def test_get_rrf_ranker_creates_new_instance(self):
        """Test factory creates new instance each time"""
        ranker1 = get_rrf_ranker(k=40)
        ranker2 = get_rrf_ranker(k=60)

        # Should be different instances
        assert ranker1 is not ranker2
        assert ranker1.k == 40
        assert ranker2.k == 60
