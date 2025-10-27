"""
Integration Tests for Hybrid Search
Tests complete hybrid search flow with all components
"""
import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.services.search.hybrid_search_service import HybridSearchService
from app.services.search.bm25_search_service import BM25SearchService
from app.services.search.vector_search_service import VectorSearchService
from app.services.search.rrf_ranker import RRFRanker
from app.schemas.search import (
    SearchFilters,
    SearchResultItem,
    SearchResponse,
)


class TestHybridSearchIntegration:
    """Integration tests for hybrid search with all components"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock()

    @pytest.fixture
    def real_rrf_ranker(self):
        """Create real RRF ranker (not mocked)"""
        return RRFRanker(k=60)

    @pytest.fixture
    def mock_bm25_service(self):
        """Create mock BM25 service"""
        return Mock(spec=BM25SearchService)

    @pytest.fixture
    def mock_vector_service(self):
        """Create mock vector service"""
        return Mock(spec=VectorSearchService)

    @pytest.fixture
    def full_hybrid_service(self, mock_db, mock_bm25_service, mock_vector_service, real_rrf_ranker):
        """Create full hybrid search stack with real RRF ranker"""
        return HybridSearchService(
            db=mock_db,
            bm25_service=mock_bm25_service,
            vector_service=mock_vector_service,
            rrf_ranker=real_rrf_ranker
        )

    def test_end_to_end_hybrid_search(self, full_hybrid_service, mock_bm25_service, mock_vector_service):
        """Test complete hybrid search flow end-to-end"""
        # Create realistic results from both searches
        doc_id = str(uuid4())
        keyword_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.95,
                document_name="test.pdf",
                snippet="machine learning algorithms",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                chunk_index=2,
                relevance_score=0.85,
                document_name="test.pdf",
                snippet="deep learning networks",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]
        vector_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=2,
                relevance_score=0.90,
                document_name="test.pdf",
                snippet="deep learning networks",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                chunk_index=3,
                relevance_score=0.80,
                document_name="test.pdf",
                snippet="neural network architecture",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        mock_bm25_service.search.return_value = keyword_results
        mock_vector_response = Mock()
        mock_vector_response.results = vector_results
        mock_vector_service.search.return_value = mock_vector_response

        response = full_hybrid_service.search("test query", None, 10, 0)

        # Verify complete flow
        assert response.success is True
        assert len(response.results) == 3  # 3 unique chunks (chunk 2 is deduplicated)

        # Verify RRF fusion happened (scores are RRF scores, normalized 0-1)
        for result in response.results:
            assert 0.0 <= result.relevance_score <= 1.0

        # Verify results are sorted by score
        scores = [r.relevance_score for r in response.results]
        assert scores == sorted(scores, reverse=True)

    def test_hybrid_search_with_overlap(self, full_hybrid_service, mock_bm25_service, mock_vector_service):
        """Test hybrid search with overlapping results from both searches"""
        doc_id = str(uuid4())

        # Same chunk appears in both with different scores
        keyword_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.95,
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
                chunk_index=1,  # Same chunk
                relevance_score=0.90,
                document_name="test.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        mock_bm25_service.search.return_value = keyword_results
        mock_vector_response = Mock()
        mock_vector_response.results = vector_results
        mock_vector_service.search.return_value = mock_vector_response

        response = full_hybrid_service.search("test", None, 10, 0)

        # Should return only 1 result (deduplicated)
        assert len(response.results) == 1

        # Score should be higher than if it only appeared in one list
        # (RRF combines both rankings)
        assert response.results[0].relevance_score > 0.0

    def test_hybrid_search_keyword_only(self, full_hybrid_service, mock_bm25_service, mock_vector_service):
        """Test hybrid search when only keyword search returns results"""
        doc_id = str(uuid4())
        keyword_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.95,
                document_name="test.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        mock_bm25_service.search.return_value = keyword_results
        mock_vector_response = Mock()
        mock_vector_response.results = []  # No vector results
        mock_vector_service.search.return_value = mock_vector_response

        response = full_hybrid_service.search("test", None, 10, 0)

        # Should still return keyword results
        assert len(response.results) == 1
        assert response.success is True

    def test_hybrid_search_vector_only(self, full_hybrid_service, mock_bm25_service, mock_vector_service):
        """Test hybrid search when only vector search returns results"""
        doc_id = str(uuid4())
        vector_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.90,
                document_name="test.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        mock_bm25_service.search.return_value = []  # No keyword results
        mock_vector_response = Mock()
        mock_vector_response.results = vector_results
        mock_vector_service.search.return_value = mock_vector_response

        response = full_hybrid_service.search("test", None, 10, 0)

        # Should still return vector results
        assert len(response.results) == 1
        assert response.success is True

    def test_hybrid_search_both_empty(self, full_hybrid_service, mock_bm25_service, mock_vector_service):
        """Test hybrid search when both searches return empty"""
        mock_bm25_service.search.return_value = []
        mock_vector_response = Mock()
        mock_vector_response.results = []
        mock_vector_service.search.return_value = mock_vector_response

        response = full_hybrid_service.search("test", None, 10, 0)

        # Should return success with empty results
        assert response.success is True
        assert len(response.results) == 0
        assert response.total_results == 0

    def test_hybrid_search_rrf_ranking(self, full_hybrid_service, mock_bm25_service, mock_vector_service):
        """Test RRF ranking boosts items that appear in both result sets"""
        doc_id = str(uuid4())

        # Chunk 1: High in keyword, not in vector
        # Chunk 2: Medium in keyword, high in vector (should boost to top)
        # Chunk 3: Not in keyword, medium in vector
        keyword_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.95,  # Rank 1 in keyword
                document_name="test.pdf",
                snippet="test1",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                chunk_index=2,
                relevance_score=0.85,  # Rank 2 in keyword
                document_name="test.pdf",
                snippet="test2",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]
        vector_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=2,
                relevance_score=0.90,  # Rank 1 in vector (appears in both!)
                document_name="test.pdf",
                snippet="test2",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                chunk_index=3,
                relevance_score=0.80,  # Rank 2 in vector
                document_name="test.pdf",
                snippet="test3",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        mock_bm25_service.search.return_value = keyword_results
        mock_vector_response = Mock()
        mock_vector_response.results = vector_results
        mock_vector_service.search.return_value = mock_vector_response

        response = full_hybrid_service.search("test", None, 10, 0)

        # Chunk 2 should be ranked highest (appears in both, high ranks in both)
        assert len(response.results) == 3
        assert response.results[0].chunk_index == 2  # Chunk 2 should be first

    def test_hybrid_search_with_filters(self, full_hybrid_service, mock_bm25_service, mock_vector_service):
        """Test hybrid search passes filters to both searches"""
        doc_id = str(uuid4())
        filters = SearchFilters(
            document_types=["application/pdf"],
            min_quality=0.8
        )

        keyword_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.95,
                document_name="test.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        mock_bm25_service.search.return_value = keyword_results
        mock_vector_response = Mock()
        mock_vector_response.results = []
        mock_vector_service.search.return_value = mock_vector_response

        response = full_hybrid_service.search("test", filters, 10, 0)

        # Verify both services were called with filters
        mock_bm25_service.search.assert_called_once()
        call_args = mock_bm25_service.search.call_args
        assert call_args.kwargs['filters'] == filters

        mock_vector_service.search.assert_called_once()
        call_args = mock_vector_service.search.call_args
        assert call_args.kwargs['filters'] == filters

    def test_hybrid_search_pagination(self, full_hybrid_service, mock_bm25_service, mock_vector_service):
        """Test hybrid search pagination works correctly"""
        doc_id = str(uuid4())

        # Create 10 results
        keyword_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=i,
                relevance_score=0.9 - i * 0.05,
                document_name="test.pdf",
                snippet=f"test{i}",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
            for i in range(5)
        ]
        vector_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=i + 5,
                relevance_score=0.9 - i * 0.05,
                document_name="test.pdf",
                snippet=f"test{i+5}",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
            for i in range(5)
        ]

        mock_bm25_service.search.return_value = keyword_results
        mock_vector_response = Mock()
        mock_vector_response.results = vector_results
        mock_vector_service.search.return_value = mock_vector_response

        # Request page 2 (offset=5, limit=5)
        response = full_hybrid_service.search("test", None, 5, 5)

        # Should return 5 results (second page)
        assert response.returned_results == 5
        assert len(response.results) == 5
        assert response.total_results == 10

    def test_hybrid_search_weighted_fusion(self, full_hybrid_service, mock_bm25_service, mock_vector_service):
        """Test hybrid search with custom keyword/vector weights"""
        doc_id = str(uuid4())

        keyword_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.95,
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
                chunk_index=2,
                relevance_score=0.90,
                document_name="test.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        mock_bm25_service.search.return_value = keyword_results
        mock_vector_response = Mock()
        mock_vector_response.results = vector_results
        mock_vector_service.search.return_value = mock_vector_response

        # Use keyword-heavy weighting
        response = full_hybrid_service.search(
            "test",
            None,
            10,
            0,
            keyword_weight=0.8,
            vector_weight=0.2
        )

        # Should complete successfully
        assert response.success is True
        assert len(response.results) == 2

    def test_hybrid_search_metadata_preserved(self, full_hybrid_service, mock_bm25_service, mock_vector_service):
        """Test hybrid search preserves all metadata fields"""
        doc_id = str(uuid4())
        created_at = datetime.now(timezone.utc)

        keyword_results = [
            SearchResultItem(
                document_id=doc_id,
                document_name="important_doc.pdf",
                chunk_index=5,
                relevance_score=0.95,
                snippet="...highlighted **text**...",
                chunk_position={'start': 1000, 'end': 2000},
                extraction_quality=0.93,
                document_type="application/pdf",
                created_at=created_at
            )
        ]

        mock_bm25_service.search.return_value = keyword_results
        mock_vector_response = Mock()
        mock_vector_response.results = []
        mock_vector_service.search.return_value = mock_vector_response

        response = full_hybrid_service.search("test", None, 10, 0)

        # Verify all metadata preserved
        result = response.results[0]
        assert result.document_id == doc_id
        assert result.document_name == "important_doc.pdf"
        assert result.chunk_index == 5
        assert result.snippet == "...highlighted **text**..."
        assert result.chunk_position == {'start': 1000, 'end': 2000}
        assert result.extraction_quality == 0.93
        assert result.document_type == "application/pdf"
        assert result.created_at == created_at

    def test_hybrid_search_error_resilience(self, full_hybrid_service, mock_bm25_service, mock_vector_service):
        """Test hybrid search is resilient to partial failures"""
        doc_id = str(uuid4())
        keyword_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.95,
                document_name="test.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        # Keyword succeeds, vector fails
        mock_bm25_service.search.return_value = keyword_results
        mock_vector_service.search.side_effect = Exception("Vector service error")

        response = full_hybrid_service.search("test", None, 10, 0)

        # Should still return results from keyword search
        assert response.success is True
        assert len(response.results) >= 1

    def test_hybrid_search_response_structure(self, full_hybrid_service, mock_bm25_service, mock_vector_service):
        """Test hybrid search returns properly structured SearchResponse"""
        doc_id = str(uuid4())
        keyword_results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.95,
                document_name="test.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        mock_bm25_service.search.return_value = keyword_results
        mock_vector_response = Mock()
        mock_vector_response.results = []
        mock_vector_service.search.return_value = mock_vector_response

        response = full_hybrid_service.search("test query", None, 10, 0)

        # Verify SearchResponse structure
        assert isinstance(response, SearchResponse)
        assert response.success is True
        assert response.query == "test query"
        assert isinstance(response.total_results, int)
        assert isinstance(response.returned_results, int)
        assert isinstance(response.results, list)
        assert isinstance(response.processing_time_ms, int)
        assert response.processing_time_ms >= 0
