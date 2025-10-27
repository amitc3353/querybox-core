"""
Unit Tests for Hybrid Search Service
Tests HybridSearchService without external dependencies
"""
import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from app.services.search.hybrid_search_service import (
    HybridSearchService,
    get_hybrid_search_service,
)
from app.services.search.bm25_search_service import BM25SearchService
from app.services.search.vector_search_service import VectorSearchService
from app.services.search.rrf_ranker import RRFRanker
from app.schemas.search import (
    SearchFilters,
    SearchResultItem,
    SearchResponse,
)
from app.core.config import settings


class TestHybridSearchService:
    """Test HybridSearchService"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return Mock()

    @pytest.fixture
    def mock_bm25_service(self):
        """Create mock BM25 service"""
        return Mock(spec=BM25SearchService)

    @pytest.fixture
    def mock_vector_service(self):
        """Create mock vector service"""
        return Mock(spec=VectorSearchService)

    @pytest.fixture
    def mock_rrf_ranker(self):
        """Create mock RRF ranker"""
        return Mock(spec=RRFRanker)

    @pytest.fixture
    def service(self, mock_db, mock_bm25_service, mock_vector_service, mock_rrf_ranker):
        """Create hybrid search service instance"""
        return HybridSearchService(
            db=mock_db,
            bm25_service=mock_bm25_service,
            vector_service=mock_vector_service,
            rrf_ranker=mock_rrf_ranker
        )

    @pytest.fixture
    def sample_bm25_results(self):
        """Sample BM25 search results"""
        doc_id = str(uuid4())
        return [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.95,
                document_name="doc1.pdf",
                snippet="machine learning test1",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                chunk_index=2,
                relevance_score=0.85,
                document_name="doc1.pdf",
                snippet="deep learning test2",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

    @pytest.fixture
    def sample_vector_results(self):
        """Sample vector search results"""
        doc_id = str(uuid4())
        return [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=2,
                relevance_score=0.90,
                document_name="doc1.pdf",
                snippet="deep learning test2",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                chunk_index=3,
                relevance_score=0.80,
                document_name="doc1.pdf",
                snippet="neural networks test3",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

    # Tests for _deduplicate_results
    def test_deduplicate_results_removes_duplicates(self, service):
        """Test deduplication removes duplicate chunks"""
        doc_id = str(uuid4())
        results = [
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
            ),
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,  # Duplicate
                relevance_score=0.8,  # Lower score
                document_name="test.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        deduplicated = service._deduplicate_results(results)

        # Should keep only one (highest score)
        assert len(deduplicated) == 1
        assert deduplicated[0].relevance_score == 0.9

    def test_deduplicate_results_keeps_highest_score(self, service):
        """Test deduplication keeps result with highest RRF score"""
        doc_id = str(uuid4())
        results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.75,
                document_name="test.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,  # Duplicate
                relevance_score=0.95,  # Higher score
                document_name="test.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        deduplicated = service._deduplicate_results(results)

        # Should keep the one with higher score
        assert len(deduplicated) == 1
        assert deduplicated[0].relevance_score == 0.95

    def test_deduplicate_results_preserves_unique_chunks(self, service):
        """Test deduplication preserves unique chunks"""
        doc_id = str(uuid4())
        results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.9,
                document_name="test.pdf",
                snippet="test1",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                chunk_index=2,  # Different chunk
                relevance_score=0.8,
                document_name="test.pdf",
                snippet="test2",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        deduplicated = service._deduplicate_results(results)

        # Should keep both unique chunks
        assert len(deduplicated) == 2

    def test_deduplicate_results_empty_list(self, service):
        """Test deduplication with empty list"""
        deduplicated = service._deduplicate_results([])
        assert deduplicated == []

    # Tests for _safe_keyword_search
    def test_safe_keyword_search_success(self, service, mock_bm25_service, sample_bm25_results):
        """Test successful keyword search"""
        mock_bm25_service.search.return_value = sample_bm25_results

        results = service._safe_keyword_search("test query", None, 100)

        assert results == sample_bm25_results
        mock_bm25_service.search.assert_called_once_with(
            query="test query",
            filters=None,
            limit=100,
            offset=0
        )

    def test_safe_keyword_search_error_returns_empty(self, service, mock_bm25_service):
        """Test keyword search error returns empty list"""
        mock_bm25_service.search.side_effect = Exception("Search error")

        results = service._safe_keyword_search("test query", None, 100)

        assert results == []

    def test_safe_keyword_search_with_filters(self, service, mock_bm25_service, sample_bm25_results):
        """Test keyword search with filters"""
        filters = SearchFilters(document_types=["application/pdf"])
        mock_bm25_service.search.return_value = sample_bm25_results

        results = service._safe_keyword_search("test query", filters, 100)

        mock_bm25_service.search.assert_called_once_with(
            query="test query",
            filters=filters,
            limit=100,
            offset=0
        )

    # Tests for _safe_vector_search
    def test_safe_vector_search_success(self, service, mock_vector_service, sample_vector_results):
        """Test successful vector search"""
        mock_response = Mock()
        mock_response.results = sample_vector_results
        mock_vector_service.search.return_value = mock_response

        results = service._safe_vector_search("test query", None, 100)

        assert results == sample_vector_results
        mock_vector_service.search.assert_called_once_with(
            query="test query",
            filters=None,
            limit=100,
            offset=0,
            similarity_threshold=0.0
        )

    def test_safe_vector_search_error_returns_empty(self, service, mock_vector_service):
        """Test vector search error returns empty list"""
        mock_vector_service.search.side_effect = Exception("Search error")

        results = service._safe_vector_search("test query", None, 100)

        assert results == []

    def test_safe_vector_search_with_filters(self, service, mock_vector_service, sample_vector_results):
        """Test vector search with filters"""
        filters = SearchFilters(min_quality=0.8)
        mock_response = Mock()
        mock_response.results = sample_vector_results
        mock_vector_service.search.return_value = mock_response

        results = service._safe_vector_search("test query", filters, 100)

        mock_vector_service.search.assert_called_once_with(
            query="test query",
            filters=filters,
            limit=100,
            offset=0,
            similarity_threshold=0.0
        )

    # Tests for _parallel_search
    def test_parallel_search_returns_tuple(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        sample_bm25_results,
        sample_vector_results
    ):
        """Test parallel search returns tuple of results"""
        mock_bm25_service.search.return_value = sample_bm25_results
        mock_response = Mock()
        mock_response.results = sample_vector_results
        mock_vector_service.search.return_value = mock_response

        keyword_results, vector_results = service._parallel_search(
            query="test",
            filters=None,
            keyword_top_k=100,
            vector_top_k=100
        )

        assert keyword_results == sample_bm25_results
        assert vector_results == sample_vector_results

    def test_parallel_search_handles_keyword_error(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        sample_vector_results
    ):
        """Test parallel search handles keyword search error"""
        mock_bm25_service.search.side_effect = Exception("BM25 error")
        mock_response = Mock()
        mock_response.results = sample_vector_results
        mock_vector_service.search.return_value = mock_response

        keyword_results, vector_results = service._parallel_search(
            query="test",
            filters=None,
            keyword_top_k=100,
            vector_top_k=100
        )

        assert keyword_results == []
        assert vector_results == sample_vector_results

    def test_parallel_search_handles_vector_error(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        sample_bm25_results
    ):
        """Test parallel search handles vector search error"""
        mock_bm25_service.search.return_value = sample_bm25_results
        mock_vector_service.search.side_effect = Exception("Vector error")

        keyword_results, vector_results = service._parallel_search(
            query="test",
            filters=None,
            keyword_top_k=100,
            vector_top_k=100
        )

        assert keyword_results == sample_bm25_results
        assert vector_results == []

    # Tests for search (4-stage pipeline)
    def test_search_calls_both_services(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker,
        sample_bm25_results,
        sample_vector_results
    ):
        """Test search calls both BM25 and vector services"""
        # Mock service responses
        mock_bm25_service.search.return_value = sample_bm25_results
        mock_response = Mock()
        mock_response.results = sample_vector_results
        mock_vector_service.search.return_value = mock_response
        mock_rrf_ranker.fuse.return_value = sample_bm25_results + sample_vector_results

        response = service.search("test query", None, 10, 0)

        # Should call both services
        mock_bm25_service.search.assert_called_once()
        mock_vector_service.search.assert_called_once()
        mock_rrf_ranker.fuse.assert_called_once()

    def test_search_passes_correct_top_k(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker,
        sample_bm25_results
    ):
        """Test search passes correct top_k to services"""
        mock_bm25_service.search.return_value = sample_bm25_results
        mock_response = Mock()
        mock_response.results = sample_bm25_results
        mock_vector_service.search.return_value = mock_response
        mock_rrf_ranker.fuse.return_value = sample_bm25_results

        service.search("test", None, 10, 0, keyword_top_k=50, vector_top_k=75)

        # Check keyword_top_k
        call_args = mock_bm25_service.search.call_args
        assert call_args.kwargs['limit'] == 50

        # Check vector_top_k
        call_args = mock_vector_service.search.call_args
        assert call_args.kwargs['limit'] == 75

    def test_search_uses_default_top_k(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker,
        sample_bm25_results
    ):
        """Test search uses default top_k if not specified"""
        mock_bm25_service.search.return_value = sample_bm25_results
        mock_response = Mock()
        mock_response.results = sample_bm25_results
        mock_vector_service.search.return_value = mock_response
        mock_rrf_ranker.fuse.return_value = sample_bm25_results

        service.search("test", None, 10, 0)

        # Should use settings defaults
        call_args = mock_bm25_service.search.call_args
        assert call_args.kwargs['limit'] == settings.HYBRID_KEYWORD_TOP_K

        call_args = mock_vector_service.search.call_args
        assert call_args.kwargs['limit'] == settings.HYBRID_VECTOR_TOP_K

    def test_search_uses_default_weights(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker,
        sample_bm25_results
    ):
        """Test search uses default weights if not specified"""
        mock_bm25_service.search.return_value = sample_bm25_results
        mock_response = Mock()
        mock_response.results = sample_bm25_results
        mock_vector_service.search.return_value = mock_response
        mock_rrf_ranker.fuse.return_value = sample_bm25_results

        service.search("test", None, 10, 0)

        # Check RRF ranker was called with default weights
        call_args = mock_rrf_ranker.fuse.call_args
        assert call_args.kwargs['keyword_weight'] == settings.RRF_KEYWORD_WEIGHT
        assert call_args.kwargs['vector_weight'] == settings.RRF_VECTOR_WEIGHT

    def test_search_passes_custom_weights(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker,
        sample_bm25_results
    ):
        """Test search passes custom weights to RRF ranker"""
        mock_bm25_service.search.return_value = sample_bm25_results
        mock_response = Mock()
        mock_response.results = sample_bm25_results
        mock_vector_service.search.return_value = mock_response
        mock_rrf_ranker.fuse.return_value = sample_bm25_results

        service.search("test", None, 10, 0, keyword_weight=0.7, vector_weight=0.3)

        # Check custom weights
        call_args = mock_rrf_ranker.fuse.call_args
        assert call_args.kwargs['keyword_weight'] == 0.7
        assert call_args.kwargs['vector_weight'] == 0.3

    def test_search_returns_search_response(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker,
        sample_bm25_results,
        sample_vector_results
    ):
        """Test search returns SearchResponse object"""
        mock_bm25_service.search.return_value = sample_bm25_results
        mock_response = Mock()
        mock_response.results = sample_vector_results
        mock_vector_service.search.return_value = mock_response
        mock_rrf_ranker.fuse.return_value = sample_bm25_results

        response = service.search("test", None, 10, 0)

        assert isinstance(response, SearchResponse)
        assert response.success is True
        assert response.query == "test"
        assert response.total_results >= 0
        assert response.processing_time_ms >= 0

    def test_search_applies_pagination(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker
    ):
        """Test search applies limit and offset to final results"""
        # Create 20 results
        doc_id = str(uuid4())
        results = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=i,
                relevance_score=0.9 - i * 0.01,
                document_name="test.pdf",
                snippet=f"test{i}",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
            for i in range(20)
        ]

        mock_bm25_service.search.return_value = results[:10]
        mock_response = Mock()
        mock_response.results = results[10:]
        mock_vector_service.search.return_value = mock_response
        mock_rrf_ranker.fuse.return_value = results

        response = service.search("test", None, 5, 10)  # limit=5, offset=10

        # Should return 5 results starting from index 10
        assert response.returned_results == 5
        assert len(response.results) == 5

    def test_search_pagination_offset_beyond_results(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker,
        sample_bm25_results
    ):
        """Test search with offset beyond result count"""
        mock_bm25_service.search.return_value = sample_bm25_results
        mock_response = Mock()
        mock_response.results = []
        mock_vector_service.search.return_value = mock_response
        mock_rrf_ranker.fuse.return_value = sample_bm25_results

        response = service.search("test", None, 10, 100)  # offset=100

        # Should return empty (offset beyond results)
        assert response.returned_results == 0
        assert len(response.results) == 0

    def test_search_fallback_bm25_fails(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker,
        sample_vector_results
    ):
        """Test search falls back to vector-only if BM25 fails"""
        # Mock BM25 to raise error
        mock_bm25_service.search.side_effect = Exception("BM25 error")
        mock_response = Mock()
        mock_response.results = sample_vector_results
        mock_vector_service.search.return_value = mock_response
        mock_rrf_ranker.fuse.return_value = sample_vector_results

        response = service.search("test", None, 10, 0)

        # Should still return results (vector-only)
        assert response.success is True
        assert len(response.results) > 0

    def test_search_fallback_vector_fails(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker,
        sample_bm25_results
    ):
        """Test search falls back to BM25-only if vector fails"""
        mock_bm25_service.search.return_value = sample_bm25_results
        mock_vector_service.search.side_effect = Exception("Vector error")
        mock_rrf_ranker.fuse.return_value = sample_bm25_results

        response = service.search("test", None, 10, 0)

        # Should still return results (BM25-only)
        assert response.success is True
        assert len(response.results) > 0

    def test_search_both_fail_returns_empty(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker
    ):
        """Test search returns empty results if both services fail"""
        mock_bm25_service.search.side_effect = Exception("BM25 error")
        mock_vector_service.search.side_effect = Exception("Vector error")
        mock_rrf_ranker.fuse.return_value = []

        response = service.search("test", None, 10, 0)

        # Should return success with empty results
        assert response.success is True
        assert len(response.results) == 0

    def test_search_includes_filters_in_response(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker,
        sample_bm25_results
    ):
        """Test search includes filters in response"""
        filters = SearchFilters(document_types=["application/pdf"])
        mock_bm25_service.search.return_value = sample_bm25_results
        mock_response = Mock()
        mock_response.results = sample_bm25_results
        mock_vector_service.search.return_value = mock_response
        mock_rrf_ranker.fuse.return_value = sample_bm25_results

        response = service.search("test", filters, 10, 0)

        assert response.filters_applied == filters

    def test_search_processing_time_measured(
        self,
        service,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker,
        sample_bm25_results
    ):
        """Test search measures processing time"""
        mock_bm25_service.search.return_value = sample_bm25_results
        mock_response = Mock()
        mock_response.results = sample_bm25_results
        mock_vector_service.search.return_value = mock_response
        mock_rrf_ranker.fuse.return_value = sample_bm25_results

        response = service.search("test", None, 10, 0)

        # Processing time should be measured
        assert response.processing_time_ms >= 0
        assert isinstance(response.processing_time_ms, int)

    # Tests for initialization
    def test_init_stores_dependencies(
        self,
        mock_db,
        mock_bm25_service,
        mock_vector_service,
        mock_rrf_ranker
    ):
        """Test initialization stores all dependencies"""
        service = HybridSearchService(
            db=mock_db,
            bm25_service=mock_bm25_service,
            vector_service=mock_vector_service,
            rrf_ranker=mock_rrf_ranker
        )

        assert service.db == mock_db
        assert service.bm25 == mock_bm25_service
        assert service.vector == mock_vector_service
        assert service.rrf == mock_rrf_ranker


class TestGetHybridSearchService:
    """Test get_hybrid_search_service factory function"""

    def test_get_hybrid_search_service_returns_instance(self):
        """Test factory returns HybridSearchService instance"""
        mock_db = Mock()
        mock_bm25 = Mock()
        mock_vector = Mock()
        mock_rrf = Mock()

        service = get_hybrid_search_service(
            db=mock_db,
            bm25_service=mock_bm25,
            vector_service=mock_vector,
            rrf_ranker=mock_rrf
        )

        assert service is not None
        assert isinstance(service, HybridSearchService)
        assert service.db == mock_db
        assert service.bm25 == mock_bm25
        assert service.vector == mock_vector
        assert service.rrf == mock_rrf

    def test_get_hybrid_search_service_creates_new_instance(self):
        """Test factory creates new instance each time"""
        mock_db1 = Mock()
        mock_db2 = Mock()
        mock_bm25 = Mock()
        mock_vector = Mock()
        mock_rrf = Mock()

        service1 = get_hybrid_search_service(mock_db1, mock_bm25, mock_vector, mock_rrf)
        service2 = get_hybrid_search_service(mock_db2, mock_bm25, mock_vector, mock_rrf)

        # Should be different instances
        assert service1 is not service2
        assert service1.db == mock_db1
        assert service2.db == mock_db2
