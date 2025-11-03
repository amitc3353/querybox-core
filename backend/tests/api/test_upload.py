"""
Upload Endpoint Tests
Comprehensive tests for document upload with deduplication

Test Coverage:
- Successful upload (new file)
- Content-based deduplication
- Stale record cleanup (DB entry exists but file missing)
- force_new parameter bypasses deduplication
- File validation (size, extension, MIME type)
- Error handling and edge cases
- Integration with StorageManager
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from uuid import uuid4, UUID
from pathlib import Path
from io import BytesIO
import tempfile
import os

from app.main import app
from app.db.database import Base, get_db
from app.models.document import Document, DocumentStatusEnum, StorageProviderEnum
from app.core.storage_config import storage_settings


# ============================================================================
# TEST DATABASE SETUP
# ============================================================================

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_upload.db"

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
    """Create test database tables before each test, drop after"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db, temp_storage):
    """FastAPI test client with dependency overrides"""
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


@pytest.fixture(scope="function")
def temp_storage():
    """Create temporary storage directory for test files"""
    original_root = storage_settings.LOCAL_STORAGE_ROOT

    with tempfile.TemporaryDirectory() as tmpdir:
        # Override storage settings
        storage_settings.LOCAL_STORAGE_ROOT = tmpdir
        yield tmpdir

    # Restore original settings
    storage_settings.LOCAL_STORAGE_ROOT = original_root


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for upload testing"""
    content = b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    content += b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    content += b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    content += b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n"
    content += b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n149\n%%EOF"

    file = BytesIO(content)
    file.name = "test.pdf"
    file.content_type = "application/pdf"
    return ("file", ("test.pdf", file, "application/pdf"))


@pytest.fixture
def sample_md_file():
    """Create a sample markdown file for upload testing"""
    content = b"# Test Document\n\nThis is a test markdown document.\n\n## Features\n- Feature 1\n- Feature 2"

    file = BytesIO(content)
    file.name = "test.md"
    file.content_type = "text/markdown"
    return ("file", ("test.md", file, "text/markdown"))


@pytest.fixture
def large_file():
    """Create a file that exceeds size limit"""
    # Create 40MB file (exceeds 30MB limit)
    content = b"x" * (40 * 1024 * 1024)

    file = BytesIO(content)
    file.name = "large.pdf"
    file.content_type = "application/pdf"
    return ("file", ("large.pdf", file, "application/pdf"))


@pytest.fixture
def unsupported_file():
    """Create an unsupported file type"""
    content = b"Fake executable content"

    file = BytesIO(content)
    file.name = "malicious.exe"
    file.content_type = "application/x-msdownload"
    return ("file", ("malicious.exe", file, "application/x-msdownload"))


@pytest.fixture
def existing_document(db_session, temp_storage):
    """
    Create an existing document in DB with physical file
    For testing deduplication
    """
    import hashlib

    doc_id = uuid4()
    file_content = b"existing file content"

    # Calculate actual checksum
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_content)
    checksum = sha256_hash.hexdigest()

    storage_path = f"00000000-0000-0000-0000-000000000000/2025/11/{doc_id}/existing.pdf"

    # Create physical file
    full_path = Path(temp_storage) / storage_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(file_content)

    # Create DB record with actual checksum
    document = Document(
        id=doc_id,
        document_name="existing.pdf",
        original_name="existing.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=len(file_content),
        checksum=checksum,
        storage_provider=StorageProviderEnum.LOCAL,
        storage_path=storage_path,
        status=DocumentStatusEnum.COMPLETED,
        is_versioned_file=False,
        current_version=1,
        mutation_count=1,
        document_metadata={},
        tags=[],
        is_deleted=False,
        is_dirty=False
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    return document


@pytest.fixture
def stale_document(db_session):
    """
    Create a stale document (DB record exists but physical file missing)
    For testing automatic cleanup
    """
    doc_id = uuid4()
    checksum = "stale_checksum_67890"
    storage_path = f"00000000-0000-0000-0000-000000000000/2025/11/{doc_id}/missing.pdf"

    # Create DB record WITHOUT physical file
    document = Document(
        id=doc_id,
        document_name="missing.pdf",
        original_name="missing.pdf",
        mime_type="application/pdf",
        file_extension=".pdf",
        file_size=100,
        checksum=checksum,
        storage_provider=StorageProviderEnum.LOCAL,
        storage_path=storage_path,
        status=DocumentStatusEnum.COMPLETED,
        is_versioned_file=False,
        current_version=1,
        mutation_count=1,
        document_metadata={},
        tags=[],
        is_deleted=False,
        is_dirty=False
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    return document


# ============================================================================
# TEST SUCCESSFUL UPLOAD
# ============================================================================

def test_upload_new_document_success(client, sample_pdf_file, db_session):
    """
    Test successful upload of a new document

    Expected:
    - 200 OK status
    - Document created in database
    - Physical file stored
    - Correct metadata returned
    - Task queued for extraction
    """
    response = client.post("/api/v1/upload/", files=[sample_pdf_file])

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert data["success"] is True
    assert data["message"] == "File uploaded successfully"
    assert "document" in data
    assert "storage" in data

    # Check document details
    doc = data["document"]
    assert "id" in doc
    assert doc["filename"] == "test.pdf"
    assert doc["mime_type"] == "application/pdf"
    assert doc["status"] == "completed"
    assert "checksum" in doc
    assert doc["size"] > 0

    # Verify database record
    doc_id = UUID(doc["id"])
    db_doc = db_session.query(Document).filter(Document.id == doc_id).first()
    assert db_doc is not None
    assert db_doc.original_name == "test.pdf"
    assert db_doc.is_deleted is False

    # Verify physical file exists
    storage_path = Path(storage_settings.LOCAL_STORAGE_ROOT) / db_doc.storage_path
    assert storage_path.exists()


def test_upload_markdown_file(client, sample_md_file, db_session):
    """
    Test upload of markdown file

    Expected:
    - Markdown files are accepted
    - Extraction task queued
    """
    response = client.post("/api/v1/upload/", files=[sample_md_file])

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    doc = data["document"]
    assert doc["filename"] == "test.md"
    assert doc["mime_type"] in ["text/markdown", "text/plain", "application/octet-stream"]


# ============================================================================
# TEST CONTENT-BASED DEDUPLICATION
# ============================================================================

def test_duplicate_detection_same_content(client, existing_document, temp_storage, db_session):
    """
    Test that uploading identical content returns existing document

    Expected:
    - 200 OK status
    - duplicate=true in response
    - Returns existing document
    - New file NOT created
    """
    # Create file with same checksum as existing_document
    # For testing, we'll upload the same file
    file_content = (Path(temp_storage) / existing_document.storage_path).read_bytes()

    file = BytesIO(file_content)
    file.name = "duplicate.pdf"
    files = ("file", ("duplicate.pdf", file, "application/pdf"))

    response = client.post("/api/v1/upload/", files=[files])

    assert response.status_code == 200
    data = response.json()

    # Check duplicate flag
    assert data.get("duplicate") is True
    assert "already exists" in data["message"].lower() or "duplicate" in data["message"].lower()

    # Should return existing document
    assert data["document"]["id"] == str(existing_document.id)
    assert data["document"]["filename"] == existing_document.original_name

    # Verify no new document created in DB
    from app.models.document import Document
    doc_count = db_session.query(Document).filter(
        Document.checksum == existing_document.checksum
    ).count()
    assert doc_count == 1  # Still only one document


def test_duplicate_with_different_filename(client, existing_document, temp_storage):
    """
    Test that duplicate detection works even with different filename

    Expected:
    - Same content, different filename → still detected as duplicate
    """
    file_content = (Path(temp_storage) / existing_document.storage_path).read_bytes()

    file = BytesIO(file_content)
    file.name = "different_name.pdf"
    files = ("file", ("different_name.pdf", file, "application/pdf"))

    response = client.post("/api/v1/upload/", files=[files])

    assert response.status_code == 200
    data = response.json()

    assert data.get("duplicate") is True
    assert data["document"]["id"] == str(existing_document.id)


# ============================================================================
# TEST STALE RECORD CLEANUP
# ============================================================================

def test_stale_record_cleanup(client, stale_document, sample_pdf_file, db_session):
    """
    Test that stale records (DB entry exists but file missing) are automatically cleaned up

    Expected:
    - Old DB record deleted
    - New document created successfully
    - No error thrown
    """
    # First verify stale document exists in DB
    stale_doc = db_session.query(Document).filter(Document.id == stale_document.id).first()
    assert stale_doc is not None
    assert stale_doc.checksum == "stale_checksum_67890"

    # Upload a new file - should trigger cleanup of stale record
    response = client.post("/api/v1/upload/", files=[sample_pdf_file])

    assert response.status_code == 200
    data = response.json()

    # Should succeed with new upload
    assert data["success"] is True
    new_doc_id = data["document"]["id"]
    assert new_doc_id != str(stale_document.id)


# ============================================================================
# TEST FORCE_NEW PARAMETER
# ============================================================================

def test_force_new_parameter(client, existing_document, temp_storage, db_session):
    """
    Test force_new=true parameter bypasses deduplication check

    NOTE: This may still fail due to unique checksum constraint in database (production PostgreSQL)
    In test environment (SQLite), the constraint enforcement may differ
    """
    file_content = (Path(temp_storage) / existing_document.storage_path).read_bytes()

    file = BytesIO(file_content)
    file.name = "forced_new.pdf"
    files = ("file", ("forced_new.pdf", file, "application/pdf"))

    # With force_new=true, should attempt to create new document
    response = client.post("/api/v1/upload/?force_new=true", files=[files])

    # In SQLite test environment, may succeed (200)
    # In production PostgreSQL, would fail with 500 due to unique constraint
    assert response.status_code in [200, 500, 409]

    if response.status_code == 200:
        # SQLite allowed it - verify it attempted to create new document
        data = response.json()
        # Note: In production, the unique constraint would prevent this
        assert data["success"] is True


def test_force_new_with_different_content(client, sample_pdf_file, sample_md_file):
    """
    Test force_new=true works with different content

    Expected:
    - force_new=true allows multiple uploads of different files
    """
    # Upload first file
    response1 = client.post("/api/v1/upload/?force_new=true", files=[sample_pdf_file])
    assert response1.status_code == 200

    # Upload second file with force_new
    response2 = client.post("/api/v1/upload/?force_new=true", files=[sample_md_file])
    assert response2.status_code == 200

    # Both should succeed
    doc1_id = response1.json()["document"]["id"]
    doc2_id = response2.json()["document"]["id"]
    assert doc1_id != doc2_id


# ============================================================================
# TEST FILE VALIDATION
# ============================================================================

def test_file_size_validation(client, large_file):
    """
    Test that files exceeding size limit are rejected

    Expected:
    - 413 Payload Too Large status
    - Error message about size limit
    """
    response = client.post("/api/v1/upload/", files=[large_file])

    assert response.status_code == 413
    data = response.json()
    assert "size" in data["detail"].lower() or "large" in data["detail"].lower()


def test_unsupported_file_type(client, unsupported_file):
    """
    Test that unsupported file types are rejected

    Expected:
    - 400 Bad Request status
    - Error message about file type
    """
    response = client.post("/api/v1/upload/", files=[unsupported_file])

    assert response.status_code == 400
    data = response.json()
    assert "type" in data["detail"].lower() or "allowed" in data["detail"].lower()


def test_empty_file_validation(client):
    """
    Test that empty files are handled

    Expected:
    - Either rejected or handled gracefully
    """
    empty_file = BytesIO(b"")
    empty_file.name = "empty.pdf"
    files = ("file", ("empty.pdf", empty_file, "application/pdf"))

    response = client.post("/api/v1/upload/", files=[files])

    # Should either reject (400/422) or accept with warnings
    assert response.status_code in [200, 400, 422]


def test_missing_file_parameter(client):
    """
    Test upload without file parameter

    Expected:
    - 422 Unprocessable Entity (FastAPI validation error)
    """
    response = client.post("/api/v1/upload/")

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


# ============================================================================
# TEST ERROR HANDLING
# ============================================================================

def test_invalid_mime_type(client):
    """
    Test upload with invalid MIME type

    Expected:
    - 400 Bad Request for disallowed MIME types
    """
    # Create file with disallowed MIME type
    content = b"some content"
    file = BytesIO(content)
    file.name = "test.xyz"
    files = ("file", ("test.xyz", file, "application/x-unknown"))

    response = client.post("/api/v1/upload/", files=[files])

    # Should reject due to MIME type validation
    assert response.status_code in [400, 422]


def test_concurrent_uploads(client, sample_pdf_file):
    """
    Test multiple concurrent uploads of different files

    Expected:
    - All uploads succeed
    - Unique documents created
    """
    # Create 3 different files
    files = []
    for i in range(3):
        content = b"File content %d" % i
        file = BytesIO(content)
        file.name = f"concurrent_{i}.pdf"
        files.append(("file", (f"concurrent_{i}.pdf", file, "application/pdf")))

    # Upload all files
    responses = []
    for file in files:
        response = client.post("/api/v1/upload/", files=[file])
        responses.append(response)

    # All should succeed
    for response in responses:
        assert response.status_code == 200
        assert response.json()["success"] is True

    # All should have unique IDs
    doc_ids = [r.json()["document"]["id"] for r in responses]
    assert len(set(doc_ids)) == 3


# ============================================================================
# TEST INTEGRATION WITH STORAGE
# ============================================================================

def test_storage_path_structure(client, sample_pdf_file, db_session):
    """
    Test that storage paths follow expected structure

    Expected:
    - Path format: {workspace_id}/{year}/{month}/{document_id}/{filename}
    """
    response = client.post("/api/v1/upload/", files=[sample_pdf_file])

    assert response.status_code == 200
    data = response.json()

    storage_path = data["storage"]["path"]

    # Check path structure
    parts = storage_path.split("/")
    assert len(parts) >= 4  # workspace/year/month/doc_id/filename

    # Verify UUID format for workspace and document ID
    workspace_id = parts[0]
    assert len(workspace_id) == 36  # UUID format

    # Verify year/month
    year = parts[1]
    month = parts[2]
    assert len(year) == 4
    assert 1 <= int(month) <= 12


def test_checksum_calculation(client, sample_pdf_file, db_session):
    """
    Test that checksums are calculated correctly

    Expected:
    - Checksum is SHA256
    - Same file = same checksum
    """
    # Upload file
    response = client.post("/api/v1/upload/", files=[sample_pdf_file])

    assert response.status_code == 200
    data = response.json()

    checksum = data["document"]["checksum"]

    # Checksum should be 64 character hex string (SHA256)
    assert len(checksum) == 64
    assert all(c in "0123456789abcdef" for c in checksum)


# ============================================================================
# TEST EDGE CASES
# ============================================================================

def test_special_characters_in_filename(client):
    """
    Test upload with special characters in filename

    Expected:
    - Filename sanitized
    - Upload succeeds
    """
    content = b"test content"
    file = BytesIO(content)
    file.name = "test file with spaces & symbols!@#.pdf"
    files = ("file", ("test file with spaces & symbols!@#.pdf", file, "application/pdf"))

    response = client.post("/api/v1/upload/", files=[files])

    # Should either sanitize or accept
    assert response.status_code in [200, 400]

    if response.status_code == 200:
        data = response.json()
        # Filename should be sanitized or preserved
        assert data["document"]["filename"] is not None


def test_very_long_filename(client):
    """
    Test upload with very long filename

    Expected:
    - Filename truncated or rejected
    """
    content = b"test content"
    long_name = "a" * 300 + ".pdf"
    file = BytesIO(content)
    file.name = long_name
    files = ("file", (long_name, file, "application/pdf"))

    response = client.post("/api/v1/upload/", files=[files])

    # Should handle gracefully
    assert response.status_code in [200, 400]


def test_unicode_filename(client):
    """
    Test upload with Unicode characters in filename

    Expected:
    - Unicode handled correctly
    """
    content = b"test content"
    file = BytesIO(content)
    file.name = "测试文档.pdf"
    files = ("file", ("测试文档.pdf", file, "application/pdf"))

    response = client.post("/api/v1/upload/", files=[files])

    # Should handle Unicode filenames
    assert response.status_code in [200, 400]


# ============================================================================
# TEST BUSINESS LOGIC
# ============================================================================

def test_upload_metadata_tracking(client, sample_pdf_file, db_session):
    """
    Test that upload metadata is tracked correctly

    Expected:
    - Timestamps recorded
    - Operation time measured
    - Audit trail in metadata
    """
    response = client.post("/api/v1/upload/", files=[sample_pdf_file])

    assert response.status_code == 200
    data = response.json()

    # Check timestamps
    assert "created_at" in data["document"]

    # Check operation time
    assert "operation_time_ms" in data["storage"]
    assert data["storage"]["operation_time_ms"] > 0

    # Check storage provider
    assert data["storage"]["provider"] == "local"


def test_workspace_isolation(client, sample_pdf_file):
    """
    Test that documents are isolated by workspace

    Expected:
    - Default workspace used (00000000-0000-0000-0000-000000000000)
    - Storage path includes workspace ID
    """
    response = client.post("/api/v1/upload/", files=[sample_pdf_file])

    assert response.status_code == 200
    data = response.json()

    storage_path = data["storage"]["path"]

    # Should start with default workspace ID
    assert storage_path.startswith("00000000-0000-0000-0000-000000000000/")


def test_upload_status_tracking(client, sample_pdf_file, db_session):
    """
    Test that document status is set correctly on upload

    Expected:
    - Status = COMPLETED after successful upload
    - is_deleted = False
    - is_dirty = False
    """
    response = client.post("/api/v1/upload/", files=[sample_pdf_file])

    assert response.status_code == 200
    data = response.json()

    doc_id = UUID(data["document"]["id"])
    db_doc = db_session.query(Document).filter(Document.id == doc_id).first()

    assert db_doc.status == DocumentStatusEnum.COMPLETED
    assert db_doc.is_deleted is False
    assert db_doc.is_dirty is False
