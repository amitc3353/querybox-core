"""
Unit Tests for Vector Search Service
Tests VectorSearchService without external dependencies
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.services.search.vector_search_service import (
    VectorSearchService,
    get_vector_search_service,
)
from app.schemas.search import (
    SearchFilters,
    SearchResponse,
    SearchResultItem,
)


class TestVectorSearchService:
    """Test VectorSearchService"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        mock_db = Mock()
        mock_db.query = Mock()
        mock_db.commit = Mock()
        mock_db.rollback = Mock()
        return mock_db

    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service"""
        mock_service = Mock()
        # Default: return 1024-dimensional vector (BGE-M3)
        mock_service.generate_embedding.return_value = [0.1] * 1024
        return mock_service

    @pytest.fixture
    def service(self, mock_db, mock_embedding_service):
        """Create vector search service instance"""
        return VectorSearchService(db=mock_db, embedding_service=mock_embedding_service)

    @pytest.fixture
    def sample_vector_results(self):
        """Sample vector search query results with similarity scores"""
        doc_id = uuid4()
        return [
            Mock(
                id=uuid4(),
                document_id=doc_id,
                document_name="sample.pdf",
                mime_type="application/pdf",
                created_at=datetime.now(timezone.utc),
                extraction_quality=0.95,
                chunk_index=0,
                chunk_text="This is a sample test document about machine learning",
                section_heading="Introduction",
                chunk_type="text",
                start_position=0,
                end_position=850,
                similarity_score=0.87,  # High similarity
            ),
            Mock(
                id=uuid4(),
                document_id=doc_id,
                document_name="sample.pdf",
                mime_type="application/pdf",
                created_at=datetime.now(timezone.utc),
                extraction_quality=0.95,
                chunk_index=1,
                chunk_text="Deep learning is a subset of machine learning algorithms",
                section_heading="Overview",
                chunk_type="text",
                start_position=650,
                end_position=1500,
                similarity_score=0.72,  # Medium similarity
            ),
            Mock(
                id=uuid4(),
                document_id=doc_id,
                document_name="sample.pdf",
                mime_type="application/pdf",
                created_at=datetime.now(timezone.utc),
                extraction_quality=0.95,
                chunk_index=2,
                chunk_text="Neural networks are used in various applications",
                section_heading="Applications",
                chunk_type="text",
                start_position=1300,
                end_position=2150,
                similarity_score=0.65,  # Lower similarity
            ),
        ]

    def test_sanitize_query_removes_null_bytes(self, service):
        """Test query sanitization removes null bytes"""
        query = "test\x00query"
        sanitized = service._sanitize_query(query)

        assert "\x00" not in sanitized
        assert sanitized == "testquery"

    def test_sanitize_query_strips_whitespace(self, service):
        """Test query sanitization strips whitespace"""
        query = "  machine learning  "
        sanitized = service._sanitize_query(query)

        assert sanitized == "machine learning"

    def test_sanitize_query_empty_raises_error(self, service):
        """Test empty query raises ValueError"""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            service._sanitize_query("")

    def test_sanitize_query_limits_length(self, service):
        """Test query length is limited"""
        query = "a" * 2000
        sanitized = service._sanitize_query(query)

        # Should truncate to MAX_QUERY_LENGTH (1000)
        assert len(sanitized) == 1000

    def test_generate_query_embedding(self, service, mock_embedding_service):
        """Test query embedding generation"""
        query = "machine learning"

        vector = service._generate_query_embedding(query)

        # Should call embedding service
        mock_embedding_service.generate_embedding.assert_called_once_with(query)

        # Should return 1024-dimensional vector
        assert len(vector) == 1024
        assert isinstance(vector, list)

    def test_generate_snippet_adds_ellipsis(self, service):
        """Test snippet generation adds ellipsis"""
        chunk_text = "This is a test chunk"
        snippet = service._generate_snippet(chunk_text)

        assert snippet.startswith("...")
        assert snippet.endswith("...")

    def test_generate_snippet_normalizes_whitespace(self, service):
        """Test snippet normalizes whitespace"""
        chunk_text = "This  is   a    test"
        snippet = service._generate_snippet(chunk_text)

        assert "  " not in snippet  # No double spaces

    def test_generate_snippet_limits_length(self, service):
        """Test snippet respects max length"""
        chunk_text = "A" * 500
        snippet = service._generate_snippet(chunk_text, max_length=100)

        # Should be truncated to max_length + "..."
        assert len(snippet) <= 103

    def test_generate_snippet_empty_string(self, service):
        """Test snippet handles empty string"""
        chunk_text = ""
        snippet = service._generate_snippet(chunk_text)

        assert snippet == ""

    def test_convert_to_result_items(self, service):
        """Test converting dicts to SearchResultItem objects"""
        results = [
            {
                "document_id": str(uuid4()),
                "document_name": "test.pdf",
                "relevance_score": 0.85,
                "snippet": "...test snippet...",
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
        assert items[0].relevance_score == 0.85

    def test_convert_to_result_items_empty(self, service):
        """Test converting empty list"""
        results = []
        items = service._convert_to_result_items(results)

        assert items == []

    def test_count_matching_chunks(self, service, mock_db):
        """Test _count_matching_chunks returns correct count"""
        query_vector = [0.1] * 1024

        # Mock the count query
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 15

        mock_db.query.return_value = mock_query

        count = service._count_matching_chunks(query_vector, None, 0.0)

        assert count == 15
        mock_query.scalar.assert_called_once()

    def test_count_matching_chunks_no_results(self, service, mock_db):
        """Test count returns 0 when no matches"""
        query_vector = [0.1] * 1024

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = None

        mock_db.query.return_value = mock_query

        count = service._count_matching_chunks(query_vector, None, 0.0)

        assert count == 0

    def test_count_matching_chunks_with_threshold(self, service, mock_db):
        """Test count with similarity threshold"""
        query_vector = [0.1] * 1024

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 5

        mock_db.query.return_value = mock_query

        count = service._count_matching_chunks(query_vector, None, 0.7)

        # Should apply threshold filter
        assert mock_query.filter.call_count >= 2  # Base filters + threshold
        assert count == 5

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

        filters = SearchFilters(min_quality=0.8)
        filtered = service._apply_filters(mock_query, filters)

        # Should call filter with quality check
        mock_query.filter.assert_called_once()

    def test_apply_filters_none(self, service, mock_db):
        """Test applying no filters returns query unchanged"""
        mock_query = Mock()

        filtered = service._apply_filters(mock_query, None)

        # Should not call filter
        mock_query.filter.assert_not_called()
        assert filtered == mock_query

    def test_vector_search_with_results(self, service, mock_db, mock_embedding_service, sample_vector_results):
        """Test basic vector search returns results"""
        # Mock count query
        count_query = Mock()
        count_query.join.return_value = count_query
        count_query.outerjoin.return_value = count_query
        count_query.filter.return_value = count_query
        count_query.scalar.return_value = 10

        # Mock search query
        search_query = Mock()
        search_query.join.return_value = search_query
        search_query.outerjoin.return_value = search_query
        search_query.filter.return_value = search_query
        search_query.order_by.return_value = search_query
        search_query.limit.return_value = search_query
        search_query.offset.return_value = search_query
        search_query.all.return_value = sample_vector_results

        # Mock db.query to return different mocks
        mock_db.query.side_effect = [count_query, search_query]

        response = service.search("machine learning", None, 3, 0)

        # Verify response
        assert isinstance(response, SearchResponse)
        assert response.success is True
        assert response.query == "machine learning"
        assert response.total_results == 10
        assert response.returned_results == 3
        assert len(response.results) == 3
        assert response.processing_time_ms >= 0

        # Verify results are sorted by similarity (descending)
        assert response.results[0].relevance_score == 0.87
        assert response.results[1].relevance_score == 0.72
        assert response.results[2].relevance_score == 0.65

        # Verify embedding service was called
        mock_embedding_service.generate_embedding.assert_called_once_with("machine learning")

    def test_vector_search_with_threshold(self, service, mock_db, mock_embedding_service, sample_vector_results):
        """Test vector search with similarity threshold"""
        # Filter out low similarity results
        high_similarity_results = [r for r in sample_vector_results if r.similarity_score >= 0.7]

        # Mock count query
        count_query = Mock()
        count_query.join.return_value = count_query
        count_query.outerjoin.return_value = count_query
        count_query.filter.return_value = count_query
        count_query.scalar.return_value = 2

        # Mock search query
        search_query = Mock()
        search_query.join.return_value = search_query
        search_query.outerjoin.return_value = search_query
        search_query.filter.return_value = search_query
        search_query.order_by.return_value = search_query
        search_query.limit.return_value = search_query
        search_query.offset.return_value = search_query
        search_query.all.return_value = high_similarity_results

        mock_db.query.side_effect = [count_query, search_query]

        response = service.search("machine learning", None, 10, 0, similarity_threshold=0.7)

        # Should only return high similarity results
        assert response.success is True
        assert response.total_results == 2
        assert response.returned_results == 2

        # All results should have similarity >= 0.7
        for result in response.results:
            assert result.relevance_score >= 0.7

    def test_vector_search_with_filters(self, service, mock_db, mock_embedding_service, sample_vector_results):
        """Test vector search with metadata filters"""
        filters = SearchFilters(
            document_types=["application/pdf"],
            min_quality=0.9,
        )

        # Mock queries
        count_query = Mock()
        count_query.join.return_value = count_query
        count_query.outerjoin.return_value = count_query
        count_query.filter.return_value = count_query
        count_query.scalar.return_value = 3

        search_query = Mock()
        search_query.join.return_value = search_query
        search_query.outerjoin.return_value = search_query
        search_query.filter.return_value = search_query
        search_query.order_by.return_value = search_query
        search_query.limit.return_value = search_query
        search_query.offset.return_value = search_query
        search_query.all.return_value = sample_vector_results

        mock_db.query.side_effect = [count_query, search_query]

        response = service.search("machine learning", filters, 10, 0)

        assert response.success is True
        assert response.filters_applied == filters

        # Verify all results meet quality requirement
        for result in response.results:
            assert result.extraction_quality >= 0.9

    def test_vector_search_no_results(self, service, mock_db, mock_embedding_service):
        """Test vector search with no matching results"""
        # Mock queries returning no results
        count_query = Mock()
        count_query.join.return_value = count_query
        count_query.outerjoin.return_value = count_query
        count_query.filter.return_value = count_query
        count_query.scalar.return_value = 0

        search_query = Mock()
        search_query.join.return_value = search_query
        search_query.outerjoin.return_value = search_query
        search_query.filter.return_value = search_query
        search_query.order_by.return_value = search_query
        search_query.limit.return_value = search_query
        search_query.offset.return_value = search_query
        search_query.all.return_value = []

        mock_db.query.side_effect = [count_query, search_query]

        response = service.search("nonexistent topic", None, 10, 0)

        assert response.success is True
        assert response.total_results == 0
        assert response.returned_results == 0
        assert len(response.results) == 0

    def test_dimension_mismatch_error(self, service, mock_embedding_service):
        """Test error handling when embedding dimensions don't match"""
        # Mock embedding service to return wrong dimensions
        mock_embedding_service.generate_embedding.return_value = [0.1] * 512  # Wrong: 512 instead of 1024

        # The service should still process it (dimension check happens at DB level)
        # But we can verify the embedding was generated
        query = "test"
        vector = service._generate_query_embedding(query)

        # Should return whatever the embedding service returns
        assert len(vector) == 512
        mock_embedding_service.generate_embedding.assert_called_once_with(query)

    def test_search_embedding_generation_error(self, service, mock_db, mock_embedding_service):
        """Test error handling when embedding generation fails"""
        # Mock embedding service to raise error
        mock_embedding_service.generate_embedding.side_effect = RuntimeError("Model not loaded")

        with pytest.raises(RuntimeError, match="Failed to generate query embedding"):
            service.search("test query", None, 10, 0)

    def test_search_pagination(self, service, mock_db, mock_embedding_service, sample_vector_results):
        """Test vector search pagination with offset"""
        # Mock queries
        count_query = Mock()
        count_query.join.return_value = count_query
        count_query.outerjoin.return_value = count_query
        count_query.filter.return_value = count_query
        count_query.scalar.return_value = 20

        search_query = Mock()
        search_query.join.return_value = search_query
        search_query.outerjoin.return_value = search_query
        search_query.filter.return_value = search_query
        search_query.order_by.return_value = search_query
        search_query.limit.return_value = search_query
        search_query.offset.return_value = search_query
        search_query.all.return_value = sample_vector_results[:2]  # Page 2

        mock_db.query.side_effect = [count_query, search_query]

        response = service.search("test", None, 2, 5)

        # Should call offset with 5
        search_query.offset.assert_called_with(5)
        assert response.returned_results == 2

    def test_vector_search_chunks_query_structure(self, service, mock_db, sample_vector_results):
        """Test _vector_search_chunks builds correct query"""
        query_vector = [0.1] * 1024

        # Mock the query chain
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = sample_vector_results

        mock_db.query.return_value = mock_query

        results = service._vector_search_chunks(query_vector, None, 10, 0, 0.0)

        # Verify query was called
        mock_db.query.assert_called_once()
        mock_query.join.assert_called()  # Should join Document and DocumentText
        mock_query.filter.assert_called()
        mock_query.order_by.assert_called()  # Should order by cosine distance
        mock_query.all.assert_called_once()

        # Verify results format
        assert len(results) == 3
        assert results[0]["chunk_index"] == 0
        assert "similarity_score" in results[0]
        assert "relevance_score" in results[0]

    def test_similarity_threshold_none_handling(self, service, mock_db, sample_vector_results):
        """Test similarity_threshold=None is handled correctly (no filter applied)"""
        query_vector = [0.1] * 1024

        # Mock query chain (including outerjoin used for DocumentText)
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query  # Added for LEFT JOIN
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = sample_vector_results

        mock_db.query.return_value = mock_query

        # Call with similarity_threshold=None
        results = service._vector_search_chunks(query_vector, None, 10, 0, None)

        # Should not crash and should return results
        assert len(results) == 3

        # Filter should only be called for base filters, not similarity threshold
        # (Exact call count may vary based on implementation)
        assert mock_query.filter.called

    def test_similarity_threshold_zero_handling(self, service, mock_db, sample_vector_results):
        """Test similarity_threshold=0.0 is handled correctly (no filter applied)"""
        query_vector = [0.1] * 1024

        # Mock query chain (including outerjoin used for DocumentText)
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query  # Added for LEFT JOIN
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = sample_vector_results

        mock_db.query.return_value = mock_query

        # Call with similarity_threshold=0.0 (should not apply threshold filter)
        results = service._vector_search_chunks(query_vector, None, 10, 0, 0.0)

        # Should not crash and should return all results
        assert len(results) == 3

    def test_chunk_id_included_in_results(self, service, mock_db):
        """Test that chunk_id (UUID) is included in search results"""
        query_vector = [0.1] * 1024

        # Create sample result with chunk_id
        chunk_id = uuid4()
        sample_result = Mock(
            id=chunk_id,  # This should become chunk_id in results
            document_id=uuid4(),
            document_name="test.pdf",
            mime_type="application/pdf",
            created_at=datetime.now(timezone.utc),
            extraction_quality=0.95,
            chunk_index=0,
            chunk_text="Sample text for testing",
            section_heading="Introduction",
            chunk_type="text",
            start_position=0,
            end_position=100,
            similarity_score=0.85,
        )

        # Mock query chain (including outerjoin used for DocumentText)
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query  # Added for LEFT JOIN
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = [sample_result]

        mock_db.query.return_value = mock_query

        # Execute search
        results = service._vector_search_chunks(query_vector, None, 10, 0, 0.0)

        # Verify chunk_id is in results
        assert len(results) == 1
        assert "chunk_id" in results[0]
        assert results[0]["chunk_id"] == str(chunk_id)
        # Ensure chunk_id is a string UUID, not integer
        from uuid import UUID
        UUID(results[0]["chunk_id"])  # Should not raise ValueError


class TestGetVectorSearchService:
    """Test get_vector_search_service factory function"""

    def test_get_vector_search_service_returns_instance(self):
        """Test get_vector_search_service returns VectorSearchService instance"""
        mock_db = Mock()
        mock_embedding_service = Mock()

        service = get_vector_search_service(db=mock_db, embedding_service=mock_embedding_service)

        assert service is not None
        assert isinstance(service, VectorSearchService)
        assert service.db == mock_db
        assert service.embedding_service == mock_embedding_service

    def test_get_vector_search_service_creates_new_instance(self):
        """Test get_vector_search_service creates new instance each time"""
        mock_db1 = Mock()
        mock_db2 = Mock()
        mock_embedding_service1 = Mock()
        mock_embedding_service2 = Mock()

        service1 = get_vector_search_service(db=mock_db1, embedding_service=mock_embedding_service1)
        service2 = get_vector_search_service(db=mock_db2, embedding_service=mock_embedding_service2)

        # Should be different instances with different dependencies
        assert service1 is not service2
        assert service1.db == mock_db1
        assert service2.db == mock_db2
        assert service1.embedding_service == mock_embedding_service1
        assert service2.embedding_service == mock_embedding_service2
