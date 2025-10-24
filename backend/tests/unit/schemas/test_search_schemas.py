"""
Unit Tests for Search Schemas
Tests Pydantic validation for search request/response schemas
"""
import pytest
from pydantic import ValidationError
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.search import (
    SearchFilters,
    SearchQuery,
    SearchResultItem,
    SearchResponse,
)


class TestSearchFilters:
    """Test SearchFilters schema validation"""

    def test_filters_valid_document_types(self):
        """Test valid document types"""
        filters = SearchFilters(
            document_types=["application/pdf", "text/plain"]
        )

        assert filters.document_types == ["application/pdf", "text/plain"]

    def test_filters_invalid_document_type(self):
        """Test invalid document type raises error"""
        with pytest.raises(ValidationError) as exc_info:
            SearchFilters(document_types=["application/invalid"])

        assert "Invalid document types" in str(exc_info.value)

    def test_filters_quality_in_range(self):
        """Test min_quality within valid range"""
        filters = SearchFilters(min_quality=0.7)

        assert filters.min_quality == 0.7

    def test_filters_quality_too_high(self):
        """Test min_quality > 1.0 raises error"""
        with pytest.raises(ValidationError):
            SearchFilters(min_quality=1.5)

    def test_filters_quality_too_low(self):
        """Test min_quality < 0.0 raises error"""
        with pytest.raises(ValidationError):
            SearchFilters(min_quality=-0.1)

    def test_filters_date_range_valid(self):
        """Test valid date range"""
        filters = SearchFilters(
            date_from=datetime(2025, 1, 1),
            date_to=datetime(2025, 12, 31),
        )

        assert filters.date_from < filters.date_to

    def test_filters_date_to_before_from(self):
        """Test date_to before date_from raises error"""
        with pytest.raises(ValidationError) as exc_info:
            SearchFilters(
                date_from=datetime(2025, 12, 31),
                date_to=datetime(2025, 1, 1),
            )

        assert "date_to must be after date_from" in str(exc_info.value)

    def test_filters_tags_valid(self):
        """Test valid tags"""
        filters = SearchFilters(tags=["python", "fastapi", "api"])

        assert len(filters.tags) == 3

    def test_filters_too_many_tags(self):
        """Test tags exceeding max count raises error"""
        with pytest.raises(ValidationError):
            SearchFilters(tags=["tag"] * 21)  # Max is 20

    def test_filters_all_optional(self):
        """Test all filters are optional"""
        filters = SearchFilters()

        assert filters.document_types is None
        assert filters.date_from is None
        assert filters.date_to is None
        assert filters.min_quality is None
        assert filters.tags is None


class TestSearchQuery:
    """Test SearchQuery schema validation"""

    def test_query_valid(self):
        """Test valid search query"""
        query = SearchQuery(query="test query")

        assert query.query == "test query"
        assert query.limit == 10  # Default
        assert query.offset == 0  # Default

    def test_query_empty_raises_error(self):
        """Test empty query raises error"""
        with pytest.raises(ValidationError) as exc_info:
            SearchQuery(query="")

        # Pydantic validates min_length before custom validator
        error_str = str(exc_info.value).lower()
        assert ("string_too_short" in error_str) or ("at least 1 character" in error_str)

    def test_query_whitespace_only_raises_error(self):
        """Test whitespace-only query raises error"""
        with pytest.raises(ValidationError):
            SearchQuery(query="   ")

    def test_query_too_long_raises_error(self):
        """Test query exceeding max length raises error"""
        with pytest.raises(ValidationError):
            SearchQuery(query="A" * 501)  # Max is 500

    def test_query_strips_whitespace(self):
        """Test query strips leading/trailing whitespace"""
        query = SearchQuery(query="  test query  ")

        assert query.query == "test query"

    def test_query_sql_injection_detected(self):
        """Test SQL injection patterns are rejected"""
        # Only test patterns that are actually in the dangerous_patterns list
        dangerous_queries = [
            "test'; DROP TABLE documents;--",
            "test; DELETE FROM users",
        ]

        for dangerous in dangerous_queries:
            with pytest.raises(ValidationError) as exc_info:
                SearchQuery(query=dangerous)

            # Validator should reject with "forbidden pattern" message
            error_str = str(exc_info.value).lower()
            assert "forbidden pattern" in error_str

    def test_query_limit_valid_range(self):
        """Test limit within valid range"""
        query = SearchQuery(query="test", limit=50)

        assert query.limit == 50

    def test_query_limit_too_high(self):
        """Test limit > 100 raises error"""
        with pytest.raises(ValidationError):
            SearchQuery(query="test", limit=101)

    def test_query_limit_zero(self):
        """Test limit = 0 raises error"""
        with pytest.raises(ValidationError):
            SearchQuery(query="test", limit=0)

    def test_query_offset_valid(self):
        """Test valid offset"""
        query = SearchQuery(query="test", offset=10)

        assert query.offset == 10

    def test_query_offset_negative(self):
        """Test negative offset raises error"""
        with pytest.raises(ValidationError):
            SearchQuery(query="test", offset=-1)

    def test_query_with_filters(self):
        """Test query with filters"""
        filters = SearchFilters(
            document_types=["application/pdf"],
            min_quality=0.8,
        )
        query = SearchQuery(query="test", filters=filters)

        assert query.filters == filters

    def test_query_include_snippets(self):
        """Test include_snippets flag"""
        query = SearchQuery(query="test", include_snippets=False)

        assert query.include_snippets is False

    def test_query_include_metadata(self):
        """Test include_metadata flag"""
        query = SearchQuery(query="test", include_metadata=False)

        assert query.include_metadata is False


class TestSearchResultItem:
    """Test SearchResultItem schema validation"""

    def test_result_item_valid(self):
        """Test valid search result item"""
        result = SearchResultItem(
            document_id=str(uuid4()),
            document_name="test.pdf",
            relevance_score=0.95,
            snippet="...test **snippet**...",
            chunk_index=5,
            chunk_position={"start": 1000, "end": 1850},
            extraction_quality=0.92,
            document_type="application/pdf",
            created_at=datetime.now(timezone.utc),
        )

        assert result.document_name == "test.pdf"
        assert result.relevance_score == 0.95
        assert result.chunk_index == 5

    def test_result_item_relevance_score_in_range(self):
        """Test relevance_score within 0.0-1.0 range"""
        result = SearchResultItem(
            document_id=str(uuid4()),
            document_name="test.pdf",
            relevance_score=0.5,
        )

        assert 0.0 <= result.relevance_score <= 1.0

    def test_result_item_relevance_score_too_high(self):
        """Test relevance_score > 1.0 raises error"""
        with pytest.raises(ValidationError):
            SearchResultItem(
                document_id=str(uuid4()),
                document_name="test.pdf",
                relevance_score=1.5,
            )

    def test_result_item_relevance_score_negative(self):
        """Test negative relevance_score raises error"""
        with pytest.raises(ValidationError):
            SearchResultItem(
                document_id=str(uuid4()),
                document_name="test.pdf",
                relevance_score=-0.1,
            )

    def test_result_item_optional_fields(self):
        """Test result item with minimal required fields"""
        result = SearchResultItem(
            document_id=str(uuid4()),
            document_name="test.pdf",
            relevance_score=0.95,
        )

        assert result.snippet is None
        assert result.chunk_index is None
        assert result.extraction_quality is None

    def test_result_item_chunk_position_structure(self):
        """Test chunk_position has correct structure"""
        result = SearchResultItem(
            document_id=str(uuid4()),
            document_name="test.pdf",
            relevance_score=0.95,
            chunk_position={"start": 100, "end": 950},
        )

        assert "start" in result.chunk_position
        assert "end" in result.chunk_position
        assert result.chunk_position["end"] > result.chunk_position["start"]


class TestSearchResponse:
    """Test SearchResponse schema validation"""

    def test_response_valid(self):
        """Test valid search response"""
        result = SearchResultItem(
            document_id=str(uuid4()),
            document_name="test.pdf",
            relevance_score=0.95,
        )

        response = SearchResponse(
            success=True,
            query="test query",
            total_results=10,
            returned_results=3,
            results=[result],
            processing_time_ms=45,
        )

        assert response.success is True
        assert response.query == "test query"
        assert response.total_results == 10
        assert response.returned_results == 3
        assert len(response.results) == 1

    def test_response_empty_results(self):
        """Test response with no results"""
        response = SearchResponse(
            success=True,
            query="nonexistent",
            total_results=0,
            returned_results=0,
            results=[],
            processing_time_ms=25,
        )

        assert response.total_results == 0
        assert len(response.results) == 0

    def test_response_processing_time_non_negative(self):
        """Test processing_time_ms cannot be negative"""
        with pytest.raises(ValidationError):
            SearchResponse(
                success=True,
                query="test",
                total_results=0,
                returned_results=0,
                results=[],
                processing_time_ms=-10,
            )

    def test_response_total_results_non_negative(self):
        """Test total_results cannot be negative"""
        with pytest.raises(ValidationError):
            SearchResponse(
                success=True,
                query="test",
                total_results=-1,
                returned_results=0,
                results=[],
                processing_time_ms=10,
            )

    def test_response_returned_results_non_negative(self):
        """Test returned_results cannot be negative"""
        with pytest.raises(ValidationError):
            SearchResponse(
                success=True,
                query="test",
                total_results=0,
                returned_results=-1,
                results=[],
                processing_time_ms=10,
            )

    def test_response_with_filters(self):
        """Test response includes filters_applied"""
        filters = SearchFilters(min_quality=0.7)

        response = SearchResponse(
            success=True,
            query="test",
            total_results=5,
            returned_results=5,
            results=[],
            processing_time_ms=30,
            filters_applied=filters,
        )

        assert response.filters_applied == filters

    def test_response_with_suggestions(self):
        """Test response includes query suggestions"""
        response = SearchResponse(
            success=True,
            query="pythn",
            total_results=0,
            returned_results=0,
            results=[],
            processing_time_ms=15,
            suggestions=["python", "pythonic"],
        )

        assert response.suggestions is not None
        assert len(response.suggestions) == 2


class TestSearchSchemaIntegration:
    """Test schema integration"""

    def test_full_search_flow(self):
        """Test complete search request/response flow"""
        # Create search query with filters
        filters = SearchFilters(
            document_types=["application/pdf"],
            min_quality=0.8,
        )
        query = SearchQuery(
            query="machine learning",
            filters=filters,
            limit=5,
            offset=0,
        )

        # Create search results
        results = [
            SearchResultItem(
                document_id=str(uuid4()),
                document_name=f"doc{i}.pdf",
                relevance_score=1.0 - (i * 0.1),
                snippet=f"...result {i}...",
                chunk_index=i,
                chunk_position={"start": i * 1000, "end": (i + 1) * 1000},
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc),
            )
            for i in range(5)
        ]

        # Create response
        response = SearchResponse(
            success=True,
            query=query.query,
            total_results=25,
            returned_results=5,
            results=results,
            processing_time_ms=67,
            filters_applied=filters,
        )

        # Verify all fields
        assert response.success is True
        assert response.total_results == 25
        assert len(response.results) == 5
        assert response.results[0].relevance_score > response.results[-1].relevance_score
        assert response.filters_applied.min_quality == 0.8
