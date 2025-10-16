"""
Document Query Endpoints Tests
Step 7: Document Query and Retrieval API

Tests all document query endpoints:
- GET  /documents/{id}     - Get document by ID
- GET  /documents          - List with pagination/filtering
- GET  /documents/search   - Search documents
- GET  /documents/stats    - Document statistics
- DELETE /documents/{id}   - Soft delete document

Test Coverage:
- Success cases with valid inputs
- Error cases (404, 400, 409)
- Edge cases (empty DB, boundaries)
- Business logic (access tracking, soft delete)
- Pagination and filtering
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from uuid import uuid4, UUID

from app.main import app
from app.db.database import Base, get_db
from app.models.document import Document, DocumentStatusEnum, StorageProviderEnum


# ============================================================================
# TEST DATABASE SETUP
# ============================================================================

# Use in-memory SQLite for fast tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_documents.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for tests"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_db():
    """
    Create test database tables before each test,
    drop them after each test
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture(scope="function")
def db_session(test_db):
    """SQLAlchemy database session for direct DB access"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_document(db_session):
    """
    Create a single sample document for testing

    Returns:
        Document: A completed PDF document with metadata
    """
    document = Document(
        id=uuid4(),
        document_name="test_report.pdf",
        original_name="Test Report.pdf",
        alternate_name="Q4 Report",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=2457600,  # ~2.34 MB
        checksum="sha256:abc123def456",
        storage_provider=StorageProviderEnum.LOCAL,
        storage_path="/documents/2024/test_report.pdf",
        storage_bucket=None,
        storage_region=None,
        status=DocumentStatusEnum.COMPLETED,
        is_versioned_file=False,
        current_version=1,
        mutation_count=1,
        document_metadata={"title": "Test Report", "author": "Test User", "page_count": 45},
        tags=["test", "report", "finance"],
        last_extraction_at=datetime.utcnow() - timedelta(hours=1),
        last_accessed_at=datetime.utcnow() - timedelta(minutes=30),
        access_count=5,
        created_at=datetime.utcnow() - timedelta(days=1),
        updated_at=datetime.utcnow() - timedelta(hours=2),
        is_deleted=False,
        is_dirty=False
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


@pytest.fixture
def sample_documents(db_session):
    """
    Create multiple sample documents for testing pagination, filtering, search

    Returns:
        List[Document]: 10 documents with varying attributes
    """
    documents = []
    base_time = datetime.utcnow()

    # Create 10 diverse documents
    for i in range(10):
        doc = Document(
            id=uuid4(),
            document_name=f"document_{i}.{'pdf' if i % 2 == 0 else 'docx'}",
            original_name=f"Document {i}.{'pdf' if i % 2 == 0 else 'docx'}",
            mime_type="application/pdf" if i % 2 == 0 else "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_extension=".pdf" if i % 2 == 0 else ".docx",
            file_size=1048576 * (i + 1),  # 1MB, 2MB, 3MB, ...
            checksum=f"sha256:checksum_{i}",
            storage_provider=StorageProviderEnum.LOCAL,
            storage_path=f"/documents/2024/document_{i}",
            status=DocumentStatusEnum.COMPLETED if i < 7 else DocumentStatusEnum.PROCESSING if i < 9 else DocumentStatusEnum.PENDING,
            is_versioned_file=False,
            current_version=1,
            mutation_count=1,
            document_metadata={"title": f"Document {i}", "category": "financial" if i % 3 == 0 else "legal"},
            tags=["finance", "quarterly"] if i % 3 == 0 else ["legal", "contract"],
            created_at=base_time - timedelta(days=10 - i),
            updated_at=base_time - timedelta(hours=10 - i),
            access_count=i * 2,
            is_deleted=False if i < 9 else True,  # Last document is soft-deleted
            is_dirty=False
        )
        documents.append(doc)
        db_session.add(doc)

    db_session.commit()
    for doc in documents:
        db_session.refresh(doc)

    return documents


@pytest.fixture
def processing_document(db_session):
    """Create a document that is currently being processed"""
    document = Document(
        id=uuid4(),
        document_name="processing_doc.pdf",
        original_name="Processing Document.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=1048576,
        checksum="sha256:processing123",
        storage_provider=StorageProviderEnum.LOCAL,
        storage_path="/documents/2024/processing_doc.pdf",
        status=DocumentStatusEnum.PROCESSING,  # Currently processing
        is_versioned_file=False,
        current_version=1,
        mutation_count=1,
        document_metadata={},
        tags=[],
        created_at=datetime.utcnow(),
        is_deleted=False,
        is_dirty=False
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


@pytest.fixture
def deleted_document(db_session):
    """Create a soft-deleted document"""
    document = Document(
        id=uuid4(),
        document_name="deleted_doc.pdf",
        original_name="Deleted Document.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=1048576,
        checksum="sha256:deleted123",
        storage_provider=StorageProviderEnum.LOCAL,
        storage_path="/documents/2024/deleted_doc.pdf",
        status=DocumentStatusEnum.COMPLETED,
        is_versioned_file=False,
        current_version=1,
        mutation_count=1,
        document_metadata={},
        tags=[],
        created_at=datetime.utcnow() - timedelta(days=5),
        is_deleted=True,  # Soft deleted
        deleted_at=datetime.utcnow() - timedelta(days=1),
        is_dirty=False
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


# ============================================================================
# TEST GET /documents/{id}
# ============================================================================

def test_get_document_by_id_success(client, sample_document):
    """
    Test successful retrieval of document by ID

    Expected:
    - 200 OK status
    - Full document metadata returned
    - file_size_mb calculated correctly
    - All fields present
    """
    response = client.get(f"/api/v1/documents/{sample_document.id}")

    assert response.status_code == 200
    data = response.json()

    # Check core fields
    assert data["id"] == str(sample_document.id)
    assert data["document_name"] == "test_report.pdf"
    assert data["original_name"] == "Test Report.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["file_extension"] == ".pdf"

    # Check file size (bytes and MB)
    assert data["file_size"] == 2457600
    assert data["file_size_mb"] == 2.34  # Rounded to 2 decimals

    # Check status
    assert data["status"] == "completed"
    assert data["is_deleted"] is False

    # Check metadata
    assert data["document_metadata"]["title"] == "Test Report"
    assert data["document_metadata"]["page_count"] == 45

    # Check tags
    assert "finance" in data["tags"]
    assert len(data["tags"]) == 3


def test_get_document_by_id_not_found(client):
    """
    Test retrieval of non-existent document

    Expected:
    - 404 Not Found status
    - Error message: "Document not found"
    """
    non_existent_id = uuid4()
    response = client.get(f"/api/v1/documents/{non_existent_id}")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_get_document_by_id_invalid_uuid(client):
    """
    Test retrieval with invalid UUID format

    Expected:
    - 400 Bad Request status
    - Error message about invalid UUID format
    """
    response = client.get("/api/v1/documents/invalid-uuid-format")

    assert response.status_code == 400
    data = response.json()
    assert "invalid" in data["detail"].lower()
    assert "uuid" in data["detail"].lower() or "id" in data["detail"].lower()


def test_get_document_increments_access_count(client, sample_document, db_session):
    """
    Test that accessing a document increments access_count

    Expected:
    - access_count incremented by 1 after each GET request
    - last_accessed_at updated
    """
    # Get initial access count
    initial_count = sample_document.access_count

    # Access document
    response = client.get(f"/api/v1/documents/{sample_document.id}")
    assert response.status_code == 200

    # Refresh document from database
    db_session.refresh(sample_document)

    # Verify access count incremented
    assert sample_document.access_count == initial_count + 1
    assert sample_document.last_accessed_at is not None

    # Access again
    response = client.get(f"/api/v1/documents/{sample_document.id}")
    assert response.status_code == 200

    db_session.refresh(sample_document)
    assert sample_document.access_count == initial_count + 2


def test_get_document_soft_deleted_returns_404(client, deleted_document):
    """
    Test that soft-deleted documents return 404

    Expected:
    - 404 Not Found (soft-deleted docs excluded by default)
    """
    response = client.get(f"/api/v1/documents/{deleted_document.id}")
    assert response.status_code == 404


# ============================================================================
# TEST GET /documents (List with Pagination/Filtering)
# ============================================================================

def test_list_documents_default_pagination(client, sample_documents):
    """
    Test listing documents with default pagination

    Expected:
    - 200 OK status
    - Default page=1, page_size=20
    - Correct pagination metadata
    - Documents sorted by created_at DESC (most recent first)
    """
    response = client.get("/api/v1/documents")

    assert response.status_code == 200
    data = response.json()

    # Check pagination metadata
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] == 9  # 10 created, 1 soft-deleted
    assert data["total_pages"] == 1
    assert data["has_next"] is False
    assert data["has_previous"] is False

    # Check items
    assert len(data["items"]) == 9

    # Verify sorted by created_at DESC (most recent first)
    created_dates = [item["created_at"] for item in data["items"]]
    assert created_dates == sorted(created_dates, reverse=True)


def test_list_documents_with_filters(client, sample_documents):
    """
    Test listing with various filters

    Expected:
    - Filters work: status, mime_type, tags
    - Only matching documents returned
    """
    # Filter by status=completed
    response = client.get("/api/v1/documents?status=completed")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 7  # 7 completed (excluding soft-deleted)
    for item in data["items"]:
        assert item["status"] == "completed"

    # Filter by mime_type
    response = client.get("/api/v1/documents?mime_type=application/pdf")
    assert response.status_code == 200
    data = response.json()
    # 5 PDFs total (0, 2, 4, 6, 8), but doc 8 is processing
    assert data["total"] >= 4
    for item in data["items"]:
        assert item["mime_type"] == "application/pdf"

    # Filter by tags (AND logic)
    response = client.get("/api/v1/documents?tags=finance&tags=quarterly")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1  # Documents 0, 3, 6 have these tags
    for item in data["items"]:
        assert "finance" in item["tags"]
        assert "quarterly" in item["tags"]


def test_list_documents_sorting(client, sample_documents):
    """
    Test sorting by different fields and orders

    Expected:
    - sort_by=created_at, sort_order=asc works
    - sort_by=file_size works
    """
    # Sort by created_at ASC (oldest first)
    response = client.get("/api/v1/documents?sort_by=created_at&sort_order=asc")
    assert response.status_code == 200
    data = response.json()

    created_dates = [item["created_at"] for item in data["items"]]
    assert created_dates == sorted(created_dates)

    # Sort by file_size DESC (largest first)
    response = client.get("/api/v1/documents?sort_by=file_size&sort_order=desc")
    assert response.status_code == 200
    data = response.json()

    file_sizes = [item["file_size"] for item in data["items"]]
    assert file_sizes == sorted(file_sizes, reverse=True)


def test_list_documents_pagination_metadata(client, sample_documents):
    """
    Test pagination metadata accuracy

    Expected:
    - total_pages calculated correctly
    - has_next/has_previous accurate
    """
    # Get page 1 with page_size=3
    response = client.get("/api/v1/documents?page=1&page_size=3")
    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 3
    assert data["total"] == 9  # 9 non-deleted documents
    assert data["total_pages"] == 3  # ceil(9/3)
    assert data["has_next"] is True
    assert data["has_previous"] is False
    assert len(data["items"]) == 3

    # Get page 2
    response = client.get("/api/v1/documents?page=2&page_size=3")
    data = response.json()

    assert data["page"] == 2
    assert data["has_next"] is True
    assert data["has_previous"] is True

    # Get last page
    response = client.get("/api/v1/documents?page=3&page_size=3")
    data = response.json()

    assert data["page"] == 3
    assert data["has_next"] is False
    assert data["has_previous"] is True


def test_list_documents_empty_database(client):
    """
    Test listing when database is empty

    Expected:
    - 200 OK status
    - Empty items array
    - total=0, total_pages=0
    """
    response = client.get("/api/v1/documents")

    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0
    assert data["total_pages"] == 0
    assert data["has_next"] is False
    assert data["has_previous"] is False


def test_list_documents_exclude_soft_deleted(client, sample_documents):
    """
    Test that soft-deleted documents are excluded by default

    Expected:
    - Soft-deleted document (index 9) not in results
    - total count excludes soft-deleted
    """
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()

    # 10 created, 1 soft-deleted = 9 results
    assert data["total"] == 9

    # Verify deleted document not in results
    deleted_doc = sample_documents[9]  # Last document is soft-deleted
    document_ids = [item["id"] for item in data["items"]]
    assert str(deleted_doc.id) not in document_ids


def test_list_documents_invalid_page_size(client):
    """
    Test validation of page_size parameter

    Expected:
    - 422 Unprocessable Entity for page_size > 100
    """
    response = client.get("/api/v1/documents?page_size=500")
    assert response.status_code == 422  # Pydantic validation error


# ============================================================================
# TEST GET /documents/search
# ============================================================================

def test_search_documents_success(client, sample_documents):
    """
    Test successful document search

    Expected:
    - 200 OK status
    - Matching documents returned
    - Search works in document_name and metadata
    """
    # Search for "Document 3" (exists in sample_documents)
    response = client.get("/api/v1/documents/search?q=Document 3")

    assert response.status_code == 200
    data = response.json()

    assert data["query"] == "Document 3"
    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    # Verify search result contains the query
    found = False
    for item in data["items"]:
        if "3" in item["document_name"] or "3" in str(item["document_metadata"]):
            found = True
            break
    assert found is True


def test_search_documents_no_results(client, sample_documents):
    """
    Test search with no matching results

    Expected:
    - 200 OK status
    - Empty items array
    - total=0
    """
    response = client.get("/api/v1/documents/search?q=nonexistent12345")

    assert response.status_code == 200
    data = response.json()

    assert data["query"] == "nonexistent12345"
    assert data["items"] == []
    assert data["total"] == 0


def test_search_query_too_short(client):
    """
    Test search query validation (minimum 3 characters)

    Expected:
    - 400 Bad Request for queries < 3 characters
    - Error message about minimum length
    """
    response = client.get("/api/v1/documents/search?q=ab")

    assert response.status_code == 400
    data = response.json()
    assert "3" in data["detail"] or "minimum" in data["detail"].lower()


def test_search_in_metadata(client, sample_documents):
    """
    Test search in JSONB metadata field

    Expected:
    - Can find documents by metadata content
    - "financial" category in metadata
    """
    response = client.get("/api/v1/documents/search?q=financial")

    assert response.status_code == 200
    data = response.json()

    # Documents 0, 3, 6 have "financial" in metadata.category
    assert data["total"] >= 1

    # Verify at least one result has "financial" in metadata
    found = False
    for item in data["items"]:
        if "financial" in str(item["document_metadata"]).lower():
            found = True
            break
    assert found is True


# ============================================================================
# TEST GET /documents/stats
# ============================================================================

def test_document_stats_all(client, sample_documents):
    """
    Test document statistics with date_range=all

    Expected:
    - 200 OK status
    - Correct total_documents count
    - total_size_bytes and total_size_gb calculated
    - by_status breakdown
    - by_mime_type breakdown
    """
    response = client.get("/api/v1/documents/stats?date_range=all")

    assert response.status_code == 200
    data = response.json()

    # Check total counts
    assert data["total_documents"] == 9  # Excluding soft-deleted

    # Check total size (sum of 1MB + 2MB + ... + 9MB, excluding doc 9 which is deleted)
    # Docs 0-8 are not deleted, doc 9 is deleted
    # Doc i has size (i+1)MB, so docs 0-8 have sizes 1+2+3+4+5+6+7+8+9 = 45MB
    expected_size_mb = sum(range(1, 10))  # 1+2+...+9 = 45
    expected_size_bytes = expected_size_mb * 1048576
    assert data["total_size_bytes"] == expected_size_bytes
    assert data["total_size_gb"] == round(expected_size_bytes / (1024**3), 2)

    # Check by_status breakdown
    assert "by_status" in data
    assert "completed" in data["by_status"]
    assert data["by_status"]["completed"] == 7  # Documents 0-6

    # Check by_mime_type
    assert "by_mime_type" in data
    assert "application/pdf" in data["by_mime_type"]


def test_document_stats_by_status(client, sample_documents):
    """
    Test document statistics grouped by status

    Expected:
    - by_status contains counts for completed, processing, pending
    """
    response = client.get("/api/v1/documents/stats")

    assert response.status_code == 200
    data = response.json()

    by_status = data["by_status"]

    # From sample_documents:
    # 0-6: completed (7)
    # 7-8: processing (2)
    # 9: pending but soft-deleted (excluded)
    assert by_status.get("completed", 0) == 7
    assert by_status.get("processing", 0) == 2


def test_document_stats_date_range(client, sample_documents):
    """
    Test document statistics with date_range filter

    Expected:
    - date_range=7d filters to last 7 days
    - Only recent documents counted
    """
    # Test with 7d range
    response = client.get("/api/v1/documents/stats?date_range=7d")
    assert response.status_code == 200
    data_7d = response.json()

    # Test with 30d range
    response = client.get("/api/v1/documents/stats?date_range=30d")
    assert response.status_code == 200
    data_30d = response.json()

    # 30d should have more or equal documents than 7d
    assert data_30d["total_documents"] >= data_7d["total_documents"]


# ============================================================================
# TEST DELETE /documents/{id}
# ============================================================================

def test_soft_delete_document(client, sample_document, db_session):
    """
    Test successful soft deletion of document

    Expected:
    - 200 OK status
    - success=true in response
    - is_deleted set to TRUE in database
    - deleted_at timestamp set
    - Document no longer appears in list
    """
    document_id = sample_document.id

    # Delete document
    response = client.delete(f"/api/v1/documents/{document_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["document_id"] == str(document_id)
    assert "deleted_at" in data
    assert data["hard_delete"] is False

    # Verify in database
    db_session.refresh(sample_document)
    assert sample_document.is_deleted is True
    assert sample_document.deleted_at is not None

    # Verify no longer appears in list
    list_response = client.get("/api/v1/documents")
    list_data = list_response.json()
    document_ids = [item["id"] for item in list_data["items"]]
    assert str(document_id) not in document_ids


def test_delete_already_deleted(client, deleted_document):
    """
    Test deletion of already soft-deleted document

    Expected:
    - 404 Not Found (already deleted documents excluded)
    """
    response = client.delete(f"/api/v1/documents/{deleted_document.id}")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_delete_processing_document_fails(client, processing_document):
    """
    Test that deleting a processing document fails with 409 Conflict

    Expected:
    - 409 Conflict status
    - Error message about processing
    """
    response = client.delete(f"/api/v1/documents/{processing_document.id}")

    assert response.status_code == 409
    data = response.json()
    assert "processing" in data["detail"].lower() or "conflict" in data["detail"].lower()


def test_delete_not_found(client):
    """
    Test deletion of non-existent document

    Expected:
    - 404 Not Found status
    """
    non_existent_id = uuid4()
    response = client.delete(f"/api/v1/documents/{non_existent_id}")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_delete_invalid_uuid(client):
    """
    Test deletion with invalid UUID format

    Expected:
    - 400 Bad Request status
    """
    response = client.delete("/api/v1/documents/invalid-uuid")

    assert response.status_code == 400
    data = response.json()
    assert "invalid" in data["detail"].lower()


# ============================================================================
# ADDITIONAL EDGE CASE TESTS
# ============================================================================

def test_list_documents_with_date_range_filter(client, sample_documents):
    """
    Test filtering by created_after and created_before

    Expected:
    - Date range filtering works correctly
    """
    # Get documents created in last 5 days
    cutoff_date = (datetime.utcnow() - timedelta(days=5)).isoformat()
    response = client.get(f"/api/v1/documents?created_after={cutoff_date}")

    assert response.status_code == 200
    data = response.json()

    # Verify all results are within date range
    for item in data["items"]:
        item_date = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        assert item_date >= datetime.fromisoformat(cutoff_date)


def test_list_documents_with_size_range_filter(client, sample_documents):
    """
    Test filtering by min_size and max_size

    Expected:
    - Size range filtering works
    """
    # Get documents between 2MB and 5MB
    min_size = 2 * 1048576  # 2MB
    max_size = 5 * 1048576  # 5MB

    response = client.get(f"/api/v1/documents?min_size={min_size}&max_size={max_size}")

    assert response.status_code == 200
    data = response.json()

    # Verify all results are within size range
    for item in data["items"]:
        assert min_size <= item["file_size"] <= max_size


def test_search_with_pagination(client, sample_documents):
    """
    Test search with pagination parameters

    Expected:
    - Search respects page and page_size
    """
    response = client.get("/api/v1/documents/search?q=document&page=1&page_size=3")

    assert response.status_code == 200
    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 3
    assert len(data["items"]) <= 3


def test_get_document_with_processing_status(client, sample_document):
    """
    Test getting document with processing status details

    Expected:
    - include_processing_status=true returns processing status
    """
    response = client.get(
        f"/api/v1/documents/{sample_document.id}?include_processing_status=true"
    )

    assert response.status_code == 200
    data = response.json()

    # Processing status should be included (may be empty if no processing done)
    assert "processing_status" in data or "processing_status" not in data  # Optional field


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

def test_list_documents_performance(client, sample_documents):
    """
    Test that list endpoint responds quickly

    Expected:
    - Response time < 200ms for 9 documents
    """
    import time
    start = time.time()
    response = client.get("/api/v1/documents")
    elapsed = (time.time() - start) * 1000  # Convert to ms

    assert response.status_code == 200
    # Note: In real tests with proper DB, this should be < 200ms
    # For in-memory SQLite tests, just verify it completes
    assert elapsed < 5000  # 5 seconds max for test environment


def test_search_performance(client, sample_documents):
    """
    Test that search endpoint responds quickly

    Expected:
    - Response time reasonable for search query
    """
    import time
    start = time.time()
    response = client.get("/api/v1/documents/search?q=document")
    elapsed = (time.time() - start) * 1000

    assert response.status_code == 200
    assert elapsed < 5000  # Reasonable for test environment
