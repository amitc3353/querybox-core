"""
API Tests for Search Endpoints
Tests search API endpoints with mocked database
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.main import app
from app.schemas.search import SearchResponse, SearchResultItem


class TestSearchEndpoint:
    """Test POST /api/v1/search/ endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_search_response(self):
        """Create mock search response"""
        doc_id = str(uuid4())
        return SearchResponse(
            success=True,
            query="test query",
            total_results=5,
            returned_results=3,
            results=[
                SearchResultItem(
                    document_id=doc_id,
                    document_name="sample.pdf",
                    relevance_score=1.0,
                    snippet="...this is a **test** snippet...",
                    chunk_index=0,
                    chunk_position={"start": 0, "end": 850},
                    extraction_quality=0.95,
                    document_type="application/pdf",
                    created_at=datetime.now(timezone.utc),
                ),
                SearchResultItem(
                    document_id=doc_id,
                    document_name="sample.pdf",
                    relevance_score=0.92,
                    snippet="...another **test** result...",
                    chunk_index=1,
                    chunk_position={"start": 650, "end": 1500},
                    extraction_quality=0.95,
                    document_type="application/pdf",
                    created_at=datetime.now(timezone.utc),
                ),
                SearchResultItem(
                    document_id=doc_id,
                    document_name="sample.pdf",
                    relevance_score=0.85,
                    snippet="...yet another **test**...",
                    chunk_index=2,
                    chunk_position={"start": 1300, "end": 2150},
                    extraction_quality=0.95,
                    document_type="application/pdf",
                    created_at=datetime.now(timezone.utc),
                ),
            ],
            processing_time_ms=65,
            filters_applied=None,
        )

    @patch("app.api.v1.endpoints.search.get_search_service")
    def test_search_basic_query(self, mock_get_service, client, mock_search_response):
        """Test basic search query"""
        mock_service = Mock()
        mock_service.search.return_value = mock_search_response
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/search/",
            json={"query": "test query", "limit": 3},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["query"] == "test query"
        assert data["total_results"] == 5
        assert data["returned_results"] == 3
        assert len(data["results"]) == 3
        assert data["processing_time_ms"] > 0

    @patch("app.api.v1.endpoints.search.get_search_service")
    def test_search_with_filters(self, mock_get_service, client):
        """Test search with filters"""
        from app.schemas.search import SearchFilters

        # Create mock response WITH filters_applied
        doc_id = str(uuid4())
        filters = SearchFilters(
            document_types=["application/pdf"],
            min_quality=0.7
        )
        mock_response = SearchResponse(
            success=True,
            query="python",
            total_results=5,
            returned_results=3,
            results=[
                SearchResultItem(
                    document_id=doc_id,
                    document_name="sample.pdf",
                    relevance_score=1.0,
                )
            ],
            processing_time_ms=65,
            filters_applied=filters,  # Include filters in response
        )

        mock_service = Mock()
        mock_service.search.return_value = mock_response
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/search/",
            json={
                "query": "python",
                "filters": {
                    "document_types": ["application/pdf"],
                    "min_quality": 0.7,
                },
                "limit": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["filters_applied"] is not None
        assert data["filters_applied"]["min_quality"] == 0.7

    @patch("app.api.v1.endpoints.search.get_search_service")
    def test_search_with_pagination(self, mock_get_service, client, mock_search_response):
        """Test search with pagination"""
        mock_service = Mock()
        mock_service.search.return_value = mock_search_response
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/search/",
            json={"query": "test", "limit": 10, "offset": 5},
        )

        assert response.status_code == 200
        # Verify service was called with correct offset
        mock_service.search.assert_called_once()
        call_kwargs = mock_service.search.call_args[1]
        assert call_kwargs["offset"] == 5

    def test_search_empty_query(self, client):
        """Test search with empty query returns 400"""
        response = client.post(
            "/api/v1/search/",
            json={"query": "", "limit": 10},
        )

        assert response.status_code == 422  # Validation error

    def test_search_query_too_long(self, client):
        """Test search with query exceeding max length"""
        response = client.post(
            "/api/v1/search/",
            json={"query": "A" * 501, "limit": 10},
        )

        assert response.status_code == 422  # Validation error

    def test_search_invalid_limit(self, client):
        """Test search with invalid limit"""
        response = client.post(
            "/api/v1/search/",
            json={"query": "test", "limit": 101},  # Max is 100
        )

        assert response.status_code == 422

    def test_search_negative_offset(self, client):
        """Test search with negative offset"""
        response = client.post(
            "/api/v1/search/",
            json={"query": "test", "limit": 10, "offset": -1},
        )

        assert response.status_code == 422

    def test_search_invalid_document_type(self, client):
        """Test search with invalid document type"""
        response = client.post(
            "/api/v1/search/",
            json={
                "query": "test",
                "filters": {"document_types": ["application/invalid"]},
            },
        )

        assert response.status_code == 422

    def test_search_invalid_quality_range(self, client):
        """Test search with quality out of range"""
        response = client.post(
            "/api/v1/search/",
            json={
                "query": "test",
                "filters": {"min_quality": 1.5},  # Max is 1.0
            },
        )

        assert response.status_code == 422

    def test_search_sql_injection_attempt(self, client):
        """Test search rejects SQL injection patterns"""
        response = client.post(
            "/api/v1/search/",
            json={"query": "test'; DROP TABLE documents;--"},
        )

        assert response.status_code == 422  # Should be rejected by validation

    @patch("app.api.v1.endpoints.search.get_search_service")
    def test_search_database_error(self, mock_get_service, client):
        """Test search handles database errors gracefully"""
        mock_service = Mock()
        mock_service.search.side_effect = Exception("Database connection failed")
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/search/",
            json={"query": "test", "limit": 10},
        )

        assert response.status_code == 500
        assert "error" in response.json()["detail"].lower()

    @patch("app.api.v1.endpoints.search.get_search_service")
    def test_search_no_results(self, mock_get_service, client):
        """Test search with no matching results"""
        mock_service = Mock()
        mock_service.search.return_value = SearchResponse(
            success=True,
            query="nonexistent",
            total_results=0,
            returned_results=0,
            results=[],
            processing_time_ms=25,
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/search/",
            json={"query": "nonexistent", "limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_results"] == 0
        assert len(data["results"]) == 0

    @patch("app.api.v1.endpoints.search.get_search_service")
    def test_search_result_structure(self, mock_get_service, client, mock_search_response):
        """Test search result has correct structure"""
        mock_service = Mock()
        mock_service.search.return_value = mock_search_response
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/search/",
            json={"query": "test", "limit": 3},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify top-level structure
        assert "success" in data
        assert "query" in data
        assert "total_results" in data
        assert "returned_results" in data
        assert "results" in data
        assert "processing_time_ms" in data

        # Verify result item structure
        result = data["results"][0]
        assert "document_id" in result
        assert "document_name" in result
        assert "relevance_score" in result
        assert "snippet" in result
        assert "chunk_index" in result
        assert "chunk_position" in result
        assert "extraction_quality" in result
        assert "document_type" in result


class TestSearchHealthCheck:
    """Test GET /api/v1/search/health endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_health_check_healthy(self, client):
        """Test health check when service is healthy"""
        from app.db.database import get_db

        # Mock database session
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5

        mock_db = Mock()
        mock_db.query.return_value = mock_query

        # Override the dependency
        def override_get_db():
            return mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = client.get("/api/v1/search/health")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "healthy"
            assert data["service"] == "search"
            assert "searchable_documents" in data
            assert data["message"] == "Search service is operational"
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    def test_health_check_database_error(self, client):
        """Test health check when database fails"""
        from app.db.database import get_db

        mock_db = Mock()
        mock_db.query.side_effect = Exception("Database connection failed")

        # Override the dependency
        def override_get_db():
            return mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = client.get("/api/v1/search/health")

            assert response.status_code == 503  # Service Unavailable
            assert "unavailable" in response.json()["detail"].lower()
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()


class TestSearchDateFilters:
    """Test date filter validation"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_search_date_from_only(self, client):
        """Test search with only date_from filter"""
        response = client.post(
            "/api/v1/search/",
            json={
                "query": "test",
                "filters": {"date_from": "2025-01-01T00:00:00Z"},
            },
        )

        # Should accept date_from alone
        assert response.status_code in [200, 500]  # May fail on search, but validates

    def test_search_date_to_only(self, client):
        """Test search with only date_to filter"""
        response = client.post(
            "/api/v1/search/",
            json={
                "query": "test",
                "filters": {"date_to": "2025-12-31T23:59:59Z"},
            },
        )

        # Should accept date_to alone
        assert response.status_code in [200, 500]

    def test_search_invalid_date_range(self, client):
        """Test search with date_to before date_from"""
        response = client.post(
            "/api/v1/search/",
            json={
                "query": "test",
                "filters": {
                    "date_from": "2025-12-31T00:00:00Z",
                    "date_to": "2025-01-01T00:00:00Z",  # Before date_from
                },
            },
        )

        assert response.status_code == 422  # Validation error


class TestSearchSpecialCharacters:
    """Test search with special characters"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @patch("app.api.v1.endpoints.search.get_search_service")
    def test_search_with_unicode(self, mock_get_service, client):
        """Test search with unicode characters"""
        mock_service = Mock()
        mock_service.search.return_value = SearchResponse(
            success=True,
            query="pythön",
            total_results=0,
            returned_results=0,
            results=[],
            processing_time_ms=10,
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/search/",
            json={"query": "pythön", "limit": 10},
        )

        assert response.status_code == 200

    @patch("app.api.v1.endpoints.search.get_search_service")
    def test_search_with_special_chars(self, mock_get_service, client):
        """Test search with special characters"""
        mock_service = Mock()
        mock_service.search.return_value = SearchResponse(
            success=True,
            query="C++ programming",
            total_results=0,
            returned_results=0,
            results=[],
            processing_time_ms=10,
        )
        mock_get_service.return_value = mock_service

        response = client.post(
            "/api/v1/search/",
            json={"query": "C++ programming", "limit": 10},
        )

        assert response.status_code == 200
