"""
Unit Tests for Keyword Search Service
Tests KeywordSearchService without external dependencies
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.services.search.keyword_search_service import (
    KeywordSearchService,
    get_search_service,
)
from app.schemas.search import (
    SearchFilters,
    SearchQuery,
    SearchResponse,
    SearchResultItem,
)


class TestKeywordSearchService:
    """Test KeywordSearchService"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        mock_db = Mock()
        mock_db.query = Mock()
        mock_db.commit = Mock()
        mock_db.rollback = Mock()
        return mock_db

    @pytest.fixture
    def service(self, mock_db):
        """Create search service instance"""
        return KeywordSearchService(db=mock_db)

    @pytest.fixture
    def sample_chunk_results(self):
        """Sample chunk query results"""
        doc_id = uuid4()
        return [
            Mock(
                document_id=doc_id,
                document_name="sample.pdf",
                mime_type="application/pdf",
                created_at=datetime.now(timezone.utc),
                extraction_quality=0.95,
                chunk_index=0,
                start_position=0,
                end_position=850,
                rank=0.0997573,
                snippet="This is a sample <b>test</b> snippet",
            ),
            Mock(
                document_id=doc_id,
                document_name="sample.pdf",
                mime_type="application/pdf",
                created_at=datetime.now(timezone.utc),
                extraction_quality=0.95,
                chunk_index=1,
                start_position=650,
                end_position=1500,
                rank=0.0865432,
                snippet="Another <b>test</b> snippet here",
            ),
            Mock(
                document_id=doc_id,
                document_name="sample.pdf",
                mime_type="application/pdf",
                created_at=datetime.now(timezone.utc),
                extraction_quality=0.95,
                chunk_index=2,
                start_position=1300,
                end_position=2150,
                rank=0.0723456,
                snippet="Yet another <b>test</b> result",
            ),
        ]

    def test_build_tsquery_single_word(self, service):
        """Test building tsquery for single word"""
        query = "fastapi"
        tsquery = service._build_tsquery(query)

        assert tsquery == "fastapi"

    def test_build_tsquery_multiple_words(self, service):
        """Test building tsquery for multiple words"""
        query = "machine learning algorithms"
        tsquery = service._build_tsquery(query)

        # Words should be joined with &
        assert tsquery == "machine & learning & algorithms"

    def test_build_tsquery_strips_whitespace(self, service):
        """Test tsquery strips leading/trailing whitespace"""
        query = "  fastapi  "
        tsquery = service._build_tsquery(query)

        assert tsquery == "fastapi"

    def test_build_tsquery_escapes_quotes(self, service):
        """Test tsquery escapes single quotes"""
        query = "it's working"
        tsquery = service._build_tsquery(query)

        # Single quotes should be escaped
        assert "''" in tsquery

    def test_build_tsquery_removes_null_bytes(self, service):
        """Test tsquery removes null bytes"""
        query = "test\x00query"
        tsquery = service._build_tsquery(query)

        assert "\x00" not in tsquery

    def test_clean_snippet_converts_tags(self, service):
        """Test snippet cleaning converts HTML tags to markdown"""
        snippet = "This is a <b>test</b> snippet"
        cleaned = service._clean_snippet(snippet)

        assert "<b>" not in cleaned
        assert "</b>" not in cleaned
        assert "**test**" in cleaned

    def test_clean_snippet_adds_ellipsis(self, service):
        """Test snippet cleaning adds ellipsis"""
        snippet = "This is a test snippet"
        cleaned = service._clean_snippet(snippet)

        assert cleaned.startswith("...")
        assert cleaned.endswith("...")

    def test_clean_snippet_normalizes_whitespace(self, service):
        """Test snippet normalizes multiple spaces"""
        snippet = "This  is    a  test"
        cleaned = service._clean_snippet(snippet)

        assert "  " not in cleaned  # No double spaces

    def test_clean_snippet_limits_length(self, service):
        """Test snippet respects max length"""
        snippet = "A" * 500
        cleaned = service._clean_snippet(snippet)

        assert len(cleaned) <= 305  # 300 + ellipsis

    def test_clean_snippet_empty_string(self, service):
        """Test snippet cleaning handles empty string"""
        snippet = ""
        cleaned = service._clean_snippet(snippet)

        assert cleaned == ""

    def test_normalize_scores_basic(self, service):
        """Test relevance score normalization"""
        results = [
            {"relevance_score": 0.0997573},
            {"relevance_score": 0.0865432},
            {"relevance_score": 0.0723456},
        ]

        normalized = service._normalize_scores(results)

        # Top result should be 1.0
        assert normalized[0]["relevance_score"] == 1.0

        # Second should be lower
        assert 0.6 <= normalized[1]["relevance_score"] < 1.0

        # Third should be lowest
        assert 0.6 <= normalized[2]["relevance_score"] < normalized[1]["relevance_score"]

    def test_normalize_scores_empty_list(self, service):
        """Test normalization with empty list"""
        results = []
        normalized = service._normalize_scores(results)

        assert normalized == []

    def test_normalize_scores_single_result(self, service):
        """Test normalization with single result"""
        results = [{"relevance_score": 0.05}]
        normalized = service._normalize_scores(results)

        # Single result should get max score
        assert normalized[0]["relevance_score"] == 1.0

    def test_normalize_scores_zero_scores(self, service):
        """Test normalization handles zero scores"""
        results = [
            {"relevance_score": 0.0},
            {"relevance_score": 0.0},
        ]

        normalized = service._normalize_scores(results)

        # Should not crash, scores unchanged
        assert normalized[0]["relevance_score"] == 0.0

    def test_convert_to_result_items(self, service):
        """Test converting dicts to SearchResultItem objects"""
        results = [
            {
                "document_id": str(uuid4()),
                "document_name": "test.pdf",
                "relevance_score": 0.95,
                "snippet": "test snippet",
                "chunk_index": 0,
                "chunk_position": {"start": 0, "end": 100},
                "extraction_quality": 0.9,
                "document_type": "application/pdf",
                "created_at": datetime.now(timezone.utc),
            }
        ]

        items = service._convert_to_result_items(results)

        assert len(items) == 1
        assert isinstance(items[0], SearchResultItem)
        assert items[0].document_name == "test.pdf"
        assert items[0].chunk_index == 0
        assert items[0].relevance_score == 0.95

    def test_convert_to_result_items_empty(self, service):
        """Test converting empty list"""
        results = []
        items = service._convert_to_result_items(results)

        assert items == []

    def test_search_chunks_query_structure(self, service, mock_db, sample_chunk_results):
        """Test _search_chunks builds correct query"""
        # Mock the query chain
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = sample_chunk_results

        mock_db.query.return_value = mock_query

        results = service._search_chunks("test", None, 10, 0)

        # Verify query was called
        mock_db.query.assert_called_once()
        mock_query.join.assert_called()  # Should join Document and DocumentText
        mock_query.filter.assert_called()
        mock_query.all.assert_called_once()

        # Verify results format
        assert len(results) == 3
        assert results[0]["chunk_index"] == 0
        assert results[0]["chunk_position"]["start"] == 0

    def test_count_matching_chunks(self, service, mock_db):
        """Test _count_matching_chunks returns correct count"""
        # Mock the count query
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 7

        mock_db.query.return_value = mock_query

        count = service._count_matching_chunks("test", None)

        assert count == 7
        mock_query.scalar.assert_called_once()

    def test_count_matching_chunks_no_results(self, service, mock_db):
        """Test count returns 0 when no matches"""
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = None

        mock_db.query.return_value = mock_query

        count = service._count_matching_chunks("nonexistent", None)

        assert count == 0

    def test_apply_filters_document_types(self, service, mock_db):
        """Test applying document type filter"""
        mock_query = Mock()

        filters = SearchFilters(document_types=["application/pdf"])
        filtered = service._apply_filters(mock_query, filters)

        # Should call filter with mime_type.in_
        mock_query.filter.assert_called_once()

    def test_apply_filters_min_quality(self, service, mock_db):
        """Test applying minimum quality filter"""
        mock_query = Mock()

        filters = SearchFilters(min_quality=0.7)
        filtered = service._apply_filters(mock_query, filters)

        # Should call filter with quality check
        mock_query.filter.assert_called_once()

    def test_apply_filters_date_range(self, service, mock_db):
        """Test applying date range filters"""
        # Mock query to return self for chaining
        mock_query = Mock()
        mock_query.filter.return_value = mock_query

        filters = SearchFilters(
            date_from=datetime(2025, 1, 1),
            date_to=datetime(2025, 12, 31),
        )
        filtered = service._apply_filters(mock_query, filters)

        # Should call filter twice (from and to)
        assert mock_query.filter.call_count == 2

    def test_apply_filters_none(self, service, mock_db):
        """Test applying no filters returns query unchanged"""
        mock_query = Mock()

        filtered = service._apply_filters(mock_query, None)

        # Should not call filter
        mock_query.filter.assert_not_called()
        assert filtered == mock_query

    def test_search_integration(self, service, mock_db, sample_chunk_results):
        """Test full search method integration"""
        # Mock count query
        count_query = Mock()
        count_query.join.return_value = count_query
        count_query.filter.return_value = count_query
        count_query.scalar.return_value = 7

        # Mock search query
        search_query = Mock()
        search_query.join.return_value = search_query
        search_query.filter.return_value = search_query
        search_query.order_by.return_value = search_query
        search_query.limit.return_value = search_query
        search_query.offset.return_value = search_query
        search_query.all.return_value = sample_chunk_results

        # Mock db.query to return different mocks
        mock_db.query.side_effect = [count_query, search_query]

        response = service.search("test query", None, 3, 0)

        assert isinstance(response, SearchResponse)
        assert response.success is True
        assert response.query == "test query"
        assert response.total_results == 7
        assert response.returned_results == 3
        assert len(response.results) == 3
        assert response.processing_time_ms >= 0

    def test_search_with_filters(self, service, mock_db, sample_chunk_results):
        """Test search with filters applied"""
        filters = SearchFilters(
            document_types=["application/pdf"],
            min_quality=0.7,
        )

        # Mock queries
        count_query = Mock()
        count_query.join.return_value = count_query
        count_query.filter.return_value = count_query
        count_query.scalar.return_value = 3

        search_query = Mock()
        search_query.join.return_value = search_query
        search_query.filter.return_value = search_query
        search_query.order_by.return_value = search_query
        search_query.limit.return_value = search_query
        search_query.offset.return_value = search_query
        search_query.all.return_value = sample_chunk_results

        mock_db.query.side_effect = [count_query, search_query]

        response = service.search("test", filters, 10, 0)

        assert response.success is True
        assert response.filters_applied == filters

    def test_search_pagination(self, service, mock_db, sample_chunk_results):
        """Test search pagination with offset"""
        # Mock queries
        count_query = Mock()
        count_query.join.return_value = count_query
        count_query.filter.return_value = count_query
        count_query.scalar.return_value = 10

        search_query = Mock()
        search_query.join.return_value = search_query
        search_query.filter.return_value = search_query
        search_query.order_by.return_value = search_query
        search_query.limit.return_value = search_query
        search_query.offset.return_value = search_query
        search_query.all.return_value = sample_chunk_results[:2]  # Page 2

        mock_db.query.side_effect = [count_query, search_query]

        response = service.search("test", None, 2, 3)

        # Should call offset with 3
        search_query.offset.assert_called_with(3)
        assert response.returned_results == 2

    def test_search_no_results(self, service, mock_db):
        """Test search with no matching results"""
        # Mock queries returning no results
        count_query = Mock()
        count_query.join.return_value = count_query
        count_query.filter.return_value = count_query
        count_query.scalar.return_value = 0

        search_query = Mock()
        search_query.join.return_value = search_query
        search_query.filter.return_value = search_query
        search_query.order_by.return_value = search_query
        search_query.limit.return_value = search_query
        search_query.offset.return_value = search_query
        search_query.all.return_value = []

        mock_db.query.side_effect = [count_query, search_query]

        response = service.search("nonexistent", None, 10, 0)

        assert response.success is True
        assert response.total_results == 0
        assert response.returned_results == 0
        assert len(response.results) == 0


class TestGetSearchService:
    """Test get_search_service factory function"""

    def test_get_search_service_returns_instance(self):
        """Test get_search_service returns KeywordSearchService instance"""
        mock_db = Mock()
        service = get_search_service(db=mock_db)

        assert service is not None
        assert isinstance(service, KeywordSearchService)
        assert service.db == mock_db

    def test_get_search_service_creates_new_instance(self):
        """Test get_search_service creates new instance each time"""
        mock_db1 = Mock()
        mock_db2 = Mock()

        service1 = get_search_service(db=mock_db1)
        service2 = get_search_service(db=mock_db2)

        # Should be different instances with different DB sessions
        assert service1 is not service2
        assert service1.db == mock_db1
        assert service2.db == mock_db2
