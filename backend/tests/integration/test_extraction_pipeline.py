"""
Integration Tests for Text Extraction Pipeline
Tests end-to-end flow: upload → extraction → database
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from pathlib import Path
import tempfile
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.models.document import Document, DocumentStatusEnum
from app.models.document_text import DocumentText


# Check if Docling is available
try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False

# Skip tests if Docling dependencies not installed
requires_docling = pytest.mark.skipif(
    not DOCLING_AVAILABLE,
    reason="Docling dependencies not installed"
)


# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """Create test client with proper dependency override"""
    # Set up dependency override for this test
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    # Clean up dependency override after test
    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing"""
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
        # Write minimal PDF content
        pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
190
%%EOF"""
        f.write(pdf_content)
        filepath = f.name

    yield filepath

    # Cleanup
    Path(filepath).unlink(missing_ok=True)


class TestUploadAndExtractionPipeline:
    """Test complete upload → extraction flow"""

    def test_upload_triggers_extraction_task(self, client, sample_pdf):
        """Test uploading PDF triggers extraction task"""
        with open(sample_pdf, 'rb') as f:
            # Mock Celery delay to prevent actual task execution
            with patch('app.api.v1.endpoints.upload.extract_document_text.delay') as mock_delay:
                mock_delay.return_value = Mock(id="task-123")

                # Mock storage operations with AsyncMock
                from uuid import uuid4
                from datetime import datetime
                from app.schemas.storage import StorageResult, StorageProviderType

                test_doc_id = uuid4()
                mock_storage = AsyncMock()

                # Return proper StorageResult instead of Mock
                mock_storage.store_document.return_value = StorageResult(
                    document_id=test_doc_id,
                    path="/storage/test.pdf",
                    size=1024,
                    checksum="abc123",
                    mime_type="application/pdf",
                    provider=StorageProviderType.LOCAL,
                    operation_time_ms=100.0,
                    created_at=datetime.utcnow()
                )

                with patch('app.api.v1.endpoints.upload.StorageManager', return_value=mock_storage):
                    response = client.post(
                        "/api/v1/upload",
                        files={"file": ("test.pdf", f, "application/pdf")}
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "document" in data

        # Verify extraction task was queued
        mock_delay.assert_called_once()

    def test_upload_non_pdf_no_extraction(self, client):
        """Test uploading non-PDF file doesn't trigger extraction"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Sample text file")
            filepath = f.name

        try:
            with open(filepath, 'rb') as f:
                with patch('app.api.v1.endpoints.upload.extract_document_text.delay') as mock_delay:
                    with patch('app.api.v1.endpoints.upload.StorageManager'):
                        response = client.post(
                            "/api/v1/upload",
                            files={"file": ("test.txt", f, "text/plain")}
                        )

            # Extraction should NOT be triggered for TXT files
            mock_delay.assert_not_called()
        finally:
            Path(filepath).unlink(missing_ok=True)


class TestExtractionServiceIntegration:
    """Test extraction service with mocked Docling"""

    @requires_docling
    @pytest.mark.asyncio
    async def test_extract_and_save_to_database(self, test_db):
        """Test extraction saves to database correctly"""
        from app.services.extraction import get_text_extractor
        from app.services.extraction.text_extraction_service import TextExtractionResult

        document_id = uuid4()
        db = TestingSessionLocal()

        try:
            # Create test document
            document = Document(
                id=document_id,
                document_name="test.pdf",
                original_name="test.pdf",
                mime_type="application/pdf",
                file_extension=".pdf",
                file_size=1024,
                checksum=f"checksum-{uuid4()}",  # Unique checksum for each test
                storage_path="/tmp/test.pdf",
                storage_provider="local",
                status=DocumentStatusEnum.PENDING,
            )
            db.add(document)
            db.commit()

            # Mock successful extraction
            extractor = get_text_extractor()

            result = TextExtractionResult(
                success=True,
                full_text="Extracted text from test PDF",
                text_length=29,
                extraction_method="docling",
                extraction_engine="native",
                extraction_quality=0.9,
                pages_with_ocr=0,
                total_pages=1,
                extraction_duration_ms=1000,
                detected_language="en",
            )

            # Save to database
            document_text = await extractor.save_extracted_text(
                db=db,
                document_id=document_id,
                result=result,
            )

            assert document_text is not None
            assert document_text.document_id == document_id
            assert document_text.text_length == 29
            assert document_text.extraction_method == "docling"

            # Verify database record
            saved_text = db.query(DocumentText).filter(
                DocumentText.document_id == document_id
            ).first()

            assert saved_text is not None
            assert saved_text.full_text == "Extracted text from test PDF"
            assert saved_text.extraction_quality == 0.9

        finally:
            db.close()

    @requires_docling
    @pytest.mark.asyncio
    async def test_extract_updates_existing_record(self, test_db):
        """Test re-extraction updates existing DocumentText"""
        from app.services.extraction.text_extraction_service import TextExtractionResult

        document_id = uuid4()
        db = TestingSessionLocal()

        try:
            # Create document and initial text
            document = Document(
                id=document_id,
                document_name="test.pdf",
                original_name="test.pdf",
                mime_type="application/pdf",
                file_extension=".pdf",
                file_size=1024,
                checksum=f"checksum-{uuid4()}",  # Unique checksum for each test
                storage_path="/tmp/test.pdf",
                storage_provider="local",
                status=DocumentStatusEnum.PENDING,
            )
            db.add(document)

            initial_text = DocumentText(
                document_id=document_id,
                full_text="Old text",
                text_length=8,
                extraction_method="fallback",
                extraction_engine="basic",
                extracted_at=datetime.now(timezone.utc),
            )
            db.add(initial_text)
            db.commit()

            # Mock Docling to avoid dependency issues
            with patch('docling.document_converter.DocumentConverter'):
                from app.services.extraction import get_text_extractor

                # Re-extract with better quality
                extractor = get_text_extractor()

                new_result = TextExtractionResult(
                    success=True,
                    full_text="New extracted text with better quality",
                    text_length=39,
                    extraction_method="docling",
                    extraction_engine="native",
                    extraction_quality=0.95,
                    pages_with_ocr=0,
                    total_pages=1,
                    extraction_duration_ms=1500,
                    detected_language="en",
                )

                # Update in database
                document_text = await extractor.save_extracted_text(
                    db=db,
                    document_id=document_id,
                    result=new_result,
                )

            # Verify it updated (not created new)
            all_texts = db.query(DocumentText).filter(
                DocumentText.document_id == document_id
            ).all()

            assert len(all_texts) == 1  # Should have only ONE record
            assert all_texts[0].full_text == "New extracted text with better quality"
            assert all_texts[0].extraction_method == "docling"
            assert all_texts[0].text_length == 39

        finally:
            db.close()


class TestDatabaseConstraints:
    """Test database constraints for document_texts table"""

    def test_unique_document_id_constraint(self):
        """Test only one DocumentText per document"""
        document_id = uuid4()
        db = TestingSessionLocal()

        try:
            # Create document
            document = Document(
                id=document_id,
                document_name="test.pdf",
                original_name="test.pdf",
                mime_type="application/pdf",
                file_extension=".pdf",
                file_size=1024,
                checksum=f"checksum-{uuid4()}",
                storage_path="/tmp/test.pdf",
                storage_provider="local",
                status=DocumentStatusEnum.PENDING,
            )
            db.add(document)
            db.commit()

            # Add first DocumentText
            text1 = DocumentText(
                document_id=document_id,
                full_text="First text",
                text_length=10,
                extraction_method="docling",
                extraction_engine="native",
                extracted_at=datetime.now(timezone.utc),
            )
            db.add(text1)
            db.commit()

            # Try to add second DocumentText with same document_id
            text2 = DocumentText(
                document_id=document_id,
                full_text="Second text",
                text_length=11,
                extraction_method="docling",
                extraction_engine="native",
                extracted_at=datetime.now(timezone.utc),
            )
            db.add(text2)

            with pytest.raises(Exception):  # Should raise IntegrityError
                db.commit()

        finally:
            db.rollback()
            db.close()

    def test_cascade_delete(self):
        """Test DocumentText is deleted when Document is deleted"""
        document_id = uuid4()
        db = TestingSessionLocal()

        try:
            # Create document and text
            document = Document(
                id=document_id,
                document_name="test.pdf",
                original_name="test.pdf",
                mime_type="application/pdf",
                file_extension=".pdf",
                file_size=1024,
                checksum=f"checksum-{uuid4()}",
                storage_path="/tmp/test.pdf",
                storage_provider="local",
                status=DocumentStatusEnum.PENDING,
            )
            db.add(document)
            db.commit()

            text = DocumentText(
                document_id=document_id,
                full_text="Text to be deleted",
                text_length=18,
                extraction_method="docling",
                extraction_engine="native",
                extracted_at=datetime.now(timezone.utc),
            )
            db.add(text)
            db.commit()

            # Delete document
            db.delete(document)
            db.commit()

            # Verify DocumentText was also deleted (CASCADE)
            remaining_text = db.query(DocumentText).filter(
                DocumentText.document_id == document_id
            ).first()

            assert remaining_text is None

        finally:
            db.close()


class TestErrorHandling:
    """Test error handling in extraction pipeline"""

    @requires_docling
    @pytest.mark.asyncio
    async def test_extraction_handles_missing_file(self):
        """Test extraction handles missing file gracefully"""
        # Mock Docling to avoid dependency issues
        with patch('docling.document_converter.DocumentConverter'):
            from app.services.extraction import get_text_extractor

            document_id = uuid4()
            extractor = get_text_extractor()

            result = await extractor.extract_text(
                file_path="/nonexistent/file.pdf",
                document_id=document_id,
                mime_type="application/pdf",
            )

            assert result.success is False
            assert "not found" in result.error_message.lower() or "not available" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_save_handles_database_error(self):
        """Test save_extracted_text handles database errors"""
        from app.services.extraction import get_text_extractor
        from app.services.extraction.text_extraction_service import TextExtractionResult

        document_id = uuid4()
        extractor = get_text_extractor()

        result = TextExtractionResult(
            success=True,
            full_text="Test text",
            text_length=9,
            extraction_method="docling",
            extraction_engine="native",
        )

        # Mock database that raises error
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.commit.side_effect = Exception("Database error")

        document_text = await extractor.save_extracted_text(
            db=mock_db,
            document_id=document_id,
            result=result,
        )

        # Should return None on error
        assert document_text is None
        mock_db.rollback.assert_called_once()
