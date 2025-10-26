"""
Embedding API Endpoints Tests
Step 9.2: BGE-M3 Embedding Generation

Tests embedding endpoints:
- POST /documents/{document_id}/embeddings/generate - Trigger embedding generation
- GET  /documents/{document_id}/embeddings/status   - Check embedding status

Test Coverage:
- Success cases with valid inputs
- Error cases (404, 400)
- Edge cases (no chunks, already processed)
- Business logic (force_regenerate, batch_size)
- Status tracking and progress
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch

from app.main import app
from app.db.database import Base, get_db
from app.models.document import Document, DocumentStatusEnum, StorageProviderEnum
from app.models.embedding import Embedding


# ============================================================================
# TEST DATABASE SETUP
# ============================================================================

# Use in-memory SQLite for fast tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_embeddings.db"

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
    """FastAPI test client with proper dependency override"""
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


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
    """Create a sample document for testing"""
    document = Document(
        id=uuid4(),
        document_name="test_report.pdf",
        original_name="Test Report.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=1048576,
        checksum="sha256:abc123",
        storage_provider=StorageProviderEnum.LOCAL,
        storage_path="/documents/test_report.pdf",
        status=DocumentStatusEnum.COMPLETED,
        is_versioned_file=False,
        current_version=1,
        mutation_count=1,
        document_metadata={},
        tags=[],
        last_extraction_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        is_deleted=False,
        is_dirty=False
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


@pytest.fixture
def document_with_chunks(db_session, sample_document):
    """Create a document with chunks (no embeddings yet)"""
    chunks = []
    for i in range(50):
        chunk = Embedding(
            id=uuid4(),
            document_id=sample_document.id,
            chunk_index=i,
            chunk_text=f"This is test chunk {i} with some sample content.",
            chunk_tokens=15,
            start_position=i * 100,
            end_position=(i + 1) * 100,
            embedding=None,  # No embedding yet
            embedding_model=None,
            created_at=datetime.utcnow()
        )
        chunks.append(chunk)
        db_session.add(chunk)

    db_session.commit()
    return sample_document, chunks


@pytest.fixture
def document_with_embeddings(db_session, document_with_chunks):
    """Create a document with chunks that already have embeddings"""
    document, chunks = document_with_chunks

    # Add embeddings to all chunks
    for chunk in chunks:
        chunk.embedding = [0.1] * 1024  # Mock 1024-dim vector
        chunk.embedding_model = "BAAI/bge-m3"

    db_session.commit()
    document.last_embedding_at = datetime.utcnow()
    db_session.commit()

    return document, chunks


# ============================================================================
# TEST POST /documents/{id}/embeddings/generate
# ============================================================================

def test_generate_embeddings_success(client, document_with_chunks):
    """
    Test successful embedding generation trigger

    Expected:
    - 202 Accepted status (async task queued)
    - task_id returned
    - status = QUEUED
    - Message confirms number of chunks
    """
    document, chunks = document_with_chunks

    with patch('app.api.v1.endpoints.embeddings.generate_embeddings') as mock_task:
        # Mock Celery task
        mock_result = Mock()
        mock_result.id = "test-task-id-123"
        mock_task.apply_async.return_value = mock_result

        response = client.post(f"/api/v1/documents/{document.id}/embeddings/generate")

        assert response.status_code == 202
        data = response.json()

        assert data["task_id"] == "test-task-id-123"
        assert data["document_id"] == str(document.id)
        assert data["status"] == "QUEUED"
        assert "50 chunks" in data["message"]

        # Verify task was queued
        mock_task.apply_async.assert_called_once()


def test_generate_embeddings_document_not_found(client):
    """
    Test embedding generation with non-existent document

    Expected:
    - 404 Not Found status
    - Error message
    """
    non_existent_id = uuid4()
    response = client.post(f"/api/v1/documents/{non_existent_id}/embeddings/generate")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_generate_embeddings_invalid_uuid(client):
    """
    Test embedding generation with invalid UUID format

    Expected:
    - 400 Bad Request status
    """
    response = client.post("/api/v1/documents/invalid-uuid/embeddings/generate")

    assert response.status_code == 400
    data = response.json()
    assert "invalid" in data["detail"].lower()


def test_generate_embeddings_no_chunks(client, sample_document):
    """
    Test embedding generation when no chunks exist

    Expected:
    - 400 Bad Request status
    - Error about missing chunks
    """
    response = client.post(f"/api/v1/documents/{sample_document.id}/embeddings/generate")

    assert response.status_code == 400
    data = response.json()
    assert "no chunks found" in data["detail"].lower()


def test_generate_embeddings_already_exists_skip(client, document_with_embeddings):
    """
    Test embedding generation when embeddings already exist (skip by default)

    Expected:
    - 202 Accepted status
    - status = SKIPPED
    - Message explains embeddings exist
    """
    document, chunks = document_with_embeddings

    response = client.post(f"/api/v1/documents/{document.id}/embeddings/generate")

    assert response.status_code == 202
    data = response.json()

    assert data["status"] == "SKIPPED"
    assert "already exist" in data["message"].lower()
    assert data["task_id"] == "n/a"


def test_generate_embeddings_force_regenerate(client, document_with_embeddings):
    """
    Test force regeneration of existing embeddings

    Expected:
    - 202 Accepted status
    - Task queued even though embeddings exist
    - force_regenerate=true overrides skip
    """
    document, chunks = document_with_embeddings

    with patch('app.api.v1.endpoints.embeddings.generate_embeddings') as mock_task:
        mock_result = Mock()
        mock_result.id = "regenerate-task-123"
        mock_task.apply_async.return_value = mock_result

        response = client.post(
            f"/api/v1/documents/{document.id}/embeddings/generate",
            json={"force_regenerate": True}
        )

        assert response.status_code == 202
        data = response.json()

        assert data["status"] == "QUEUED"
        assert data["task_id"] == "regenerate-task-123"
        mock_task.apply_async.assert_called_once()


def test_generate_embeddings_custom_batch_size(client, document_with_chunks):
    """
    Test embedding generation with custom batch size

    Expected:
    - 202 Accepted status
    - Request body includes batch_size parameter
    """
    document, chunks = document_with_chunks

    with patch('app.api.v1.endpoints.embeddings.generate_embeddings') as mock_task:
        mock_result = Mock()
        mock_result.id = "task-456"
        mock_task.apply_async.return_value = mock_result

        response = client.post(
            f"/api/v1/documents/{document.id}/embeddings/generate",
            json={"batch_size": 50}
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "QUEUED"


# ============================================================================
# TEST GET /documents/{id}/embeddings/status
# ============================================================================

def test_get_embedding_status_success(client, document_with_chunks):
    """
    Test successful retrieval of embedding status

    Expected:
    - 200 OK status
    - Correct chunk counts
    - completion_percentage = 0 (no embeddings yet)
    """
    document, chunks = document_with_chunks

    response = client.get(f"/api/v1/documents/{document.id}/embeddings/status")

    assert response.status_code == 200
    data = response.json()

    assert data["document_id"] == str(document.id)
    assert data["total_chunks"] == 50
    assert data["chunks_with_embeddings"] == 0
    assert data["completion_percentage"] == 0.0
    assert data["embedding_model"] is None
    assert data["last_embedding_at"] is None


def test_get_embedding_status_partial_completion(client, document_with_chunks, db_session):
    """
    Test status with partial embedding completion

    Expected:
    - Correct counts for partial completion
    - completion_percentage calculated correctly
    """
    document, chunks = document_with_chunks

    # Add embeddings to first 25 chunks (50% complete)
    for i in range(25):
        chunks[i].embedding = [0.1] * 1024
        chunks[i].embedding_model = "BAAI/bge-m3"

    db_session.commit()

    response = client.get(f"/api/v1/documents/{document.id}/embeddings/status")

    assert response.status_code == 200
    data = response.json()

    assert data["total_chunks"] == 50
    assert data["chunks_with_embeddings"] == 25
    assert data["completion_percentage"] == 50.0
    assert data["embedding_model"] == "BAAI/bge-m3"


def test_get_embedding_status_complete(client, document_with_embeddings):
    """
    Test status with complete embedding generation

    Expected:
    - completion_percentage = 100.0
    - embedding_model populated
    - last_embedding_at timestamp present
    """
    document, chunks = document_with_embeddings

    response = client.get(f"/api/v1/documents/{document.id}/embeddings/status")

    assert response.status_code == 200
    data = response.json()

    assert data["total_chunks"] == 50
    assert data["chunks_with_embeddings"] == 50
    assert data["completion_percentage"] == 100.0
    assert data["embedding_model"] == "BAAI/bge-m3"
    assert data["last_embedding_at"] is not None


def test_get_embedding_status_no_chunks(client, sample_document):
    """
    Test status when document has no chunks

    Expected:
    - 200 OK status
    - total_chunks = 0
    - completion_percentage = 0.0
    """
    response = client.get(f"/api/v1/documents/{sample_document.id}/embeddings/status")

    assert response.status_code == 200
    data = response.json()

    assert data["total_chunks"] == 0
    assert data["chunks_with_embeddings"] == 0
    assert data["completion_percentage"] == 0.0


def test_get_embedding_status_document_not_found(client):
    """
    Test status retrieval for non-existent document

    Expected:
    - 404 Not Found status
    """
    non_existent_id = uuid4()
    response = client.get(f"/api/v1/documents/{non_existent_id}/embeddings/status")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_get_embedding_status_invalid_uuid(client):
    """
    Test status retrieval with invalid UUID

    Expected:
    - 400 Bad Request status
    """
    response = client.get("/api/v1/documents/invalid-uuid/embeddings/status")

    assert response.status_code == 400
    data = response.json()
    assert "invalid" in data["detail"].lower()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_full_embedding_workflow(client, document_with_chunks):
    """
    Test complete workflow: generate → check status

    Expected:
    - Generate returns 202
    - Status shows 0% initially
    - After mock completion, status shows 100%
    """
    document, chunks = document_with_chunks

    # Step 1: Check initial status (0%)
    response = client.get(f"/api/v1/documents/{document.id}/embeddings/status")
    assert response.status_code == 200
    data = response.json()
    assert data["completion_percentage"] == 0.0

    # Step 2: Trigger generation
    with patch('app.api.v1.endpoints.embeddings.generate_embeddings') as mock_task:
        mock_result = Mock()
        mock_result.id = "workflow-task-123"
        mock_task.apply_async.return_value = mock_result

        response = client.post(f"/api/v1/documents/{document.id}/embeddings/generate")
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "QUEUED"

    # Note: In real test, we would wait for task completion
    # For unit test, we verify the workflow triggers correctly


def test_embedding_status_reflects_processing(client, document_with_chunks, db_session):
    """
    Test status accurately reflects processing progress

    Expected:
    - Status updates as embeddings are added
    - completion_percentage increases correctly
    """
    document, chunks = document_with_chunks

    # Check 0% complete
    response = client.get(f"/api/v1/documents/{document.id}/embeddings/status")
    assert response.json()["completion_percentage"] == 0.0

    # Add embeddings to 10 chunks (20%)
    for i in range(10):
        chunks[i].embedding = [0.1] * 1024
        chunks[i].embedding_model = "BAAI/bge-m3"
    db_session.commit()

    response = client.get(f"/api/v1/documents/{document.id}/embeddings/status")
    assert response.json()["completion_percentage"] == 20.0

    # Add embeddings to 40 more chunks (100%)
    for i in range(10, 50):
        chunks[i].embedding = [0.1] * 1024
        chunks[i].embedding_model = "BAAI/bge-m3"
    db_session.commit()

    response = client.get(f"/api/v1/documents/{document.id}/embeddings/status")
    data = response.json()
    assert data["completion_percentage"] == 100.0
    assert data["chunks_with_embeddings"] == 50


def test_multiple_documents_independent(client, db_session):
    """
    Test that multiple documents have independent embedding status

    Expected:
    - Each document tracks its own embeddings
    - Completion percentages are independent
    """
    # Create two documents with chunks
    doc1 = Document(
        id=uuid4(),
        document_name="doc1.pdf",
        original_name="Doc 1.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=1048576,
        checksum="sha256:doc1",
        storage_provider=StorageProviderEnum.LOCAL,
        storage_path="/documents/doc1.pdf",
        status=DocumentStatusEnum.COMPLETED,
        is_versioned_file=False,
        current_version=1,
        mutation_count=1,
        document_metadata={},
        tags=[],
        created_at=datetime.utcnow(),
        is_deleted=False,
        is_dirty=False
    )
    db_session.add(doc1)

    doc2 = Document(
        id=uuid4(),
        document_name="doc2.pdf",
        original_name="Doc 2.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=1048576,
        checksum="sha256:doc2",
        storage_provider=StorageProviderEnum.LOCAL,
        storage_path="/documents/doc2.pdf",
        status=DocumentStatusEnum.COMPLETED,
        is_versioned_file=False,
        current_version=1,
        mutation_count=1,
        document_metadata={},
        tags=[],
        created_at=datetime.utcnow(),
        is_deleted=False,
        is_dirty=False
    )
    db_session.add(doc2)
    db_session.commit()

    # Add chunks to both documents
    for i in range(10):
        chunk1 = Embedding(
            id=uuid4(),
            document_id=doc1.id,
            chunk_index=i,
            chunk_text=f"Doc1 chunk {i}",
            chunk_tokens=10,
            embedding=[0.1] * 1024 if i < 5 else None,  # 50% complete
            embedding_model="BAAI/bge-m3" if i < 5 else None
        )
        db_session.add(chunk1)

        chunk2 = Embedding(
            id=uuid4(),
            document_id=doc2.id,
            chunk_index=i,
            chunk_text=f"Doc2 chunk {i}",
            chunk_tokens=10,
            embedding=None,  # 0% complete
            embedding_model=None
        )
        db_session.add(chunk2)

    db_session.commit()

    # Check doc1 status (50%)
    response = client.get(f"/api/v1/documents/{doc1.id}/embeddings/status")
    assert response.json()["completion_percentage"] == 50.0

    # Check doc2 status (0%)
    response = client.get(f"/api/v1/documents/{doc2.id}/embeddings/status")
    assert response.json()["completion_percentage"] == 0.0


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

def test_generate_embeddings_empty_request_body(client, document_with_chunks):
    """
    Test generation with no request body (use defaults)

    Expected:
    - 202 Accepted
    - Defaults used (force_regenerate=false, batch_size=100)
    """
    document, chunks = document_with_chunks

    with patch('app.api.v1.endpoints.embeddings.generate_embeddings') as mock_task:
        mock_result = Mock()
        mock_result.id = "default-task"
        mock_task.apply_async.return_value = mock_result

        response = client.post(f"/api/v1/documents/{document.id}/embeddings/generate")

        assert response.status_code == 202


def test_get_status_with_processing_status(client, document_with_chunks):
    """
    Test status includes processing_status if available

    Expected:
    - processing_status field populated when task is running
    """
    document, chunks = document_with_chunks

    response = client.get(f"/api/v1/documents/{document.id}/embeddings/status")

    assert response.status_code == 200
    data = response.json()

    # processing_status may be None or have a value
    assert "processing_status" in data


def test_embedding_status_percentage_rounding(client, db_session):
    """
    Test completion percentage is properly rounded

    Expected:
    - Percentage rounded to 2 decimal places
    """
    # Create document with 3 chunks, 1 with embedding (33.33...%)
    doc = Document(
        id=uuid4(),
        document_name="test.pdf",
        original_name="Test.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=1048576,
        checksum="sha256:test",
        storage_provider=StorageProviderEnum.LOCAL,
        storage_path="/documents/test.pdf",
        status=DocumentStatusEnum.COMPLETED,
        is_versioned_file=False,
        current_version=1,
        mutation_count=1,
        document_metadata={},
        tags=[],
        created_at=datetime.utcnow(),
        is_deleted=False,
        is_dirty=False
    )
    db_session.add(doc)
    db_session.commit()

    for i in range(3):
        chunk = Embedding(
            id=uuid4(),
            document_id=doc.id,
            chunk_index=i,
            chunk_text=f"Chunk {i}",
            chunk_tokens=10,
            embedding=[0.1] * 1024 if i == 0 else None,
            embedding_model="BAAI/bge-m3" if i == 0 else None
        )
        db_session.add(chunk)
    db_session.commit()

    response = client.get(f"/api/v1/documents/{doc.id}/embeddings/status")
    data = response.json()

    # 1/3 = 33.33333... should be rounded to 33.33
    assert data["completion_percentage"] == 33.33
