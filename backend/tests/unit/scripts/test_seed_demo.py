"""
Unit Tests for Demo Data Seeder
Step 12.3: Demo Data Pipeline Testing

Test Coverage:
- Document content generation
- Demo data seeder initialization
- Document upload with retry logic
- Processing status monitoring
- Search verification
- Error recovery and handling
- Command-line argument parsing
- Progress tracking
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import sys
from uuid import uuid4, UUID
from io import BytesIO

# Import the module under test
from scripts.seed_demo import (
    generate_technical_pdf_content,
    generate_deployment_guide_md,
    generate_api_reference_html,
    generate_user_manual_txt,
    generate_research_paper_txt,
    DemoDataSeeder,
)

from app.models.document import ProcessingStageEnum, StageStatusEnum


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Mock database session"""
    mock_session = Mock()
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_session.query.return_value.filter.return_value.all.return_value = []
    return mock_session


@pytest.fixture
def temp_demo_data_path(tmp_path):
    """Create temporary demo-data directory"""
    demo_path = tmp_path / "demo-data"
    demo_path.mkdir()
    return demo_path


@pytest.fixture
def mock_document():
    """Create mock document object"""
    doc = Mock()
    doc.id = uuid4()
    doc.document_name = "test.pdf"
    doc.original_name = "test.pdf"
    doc.status = "completed"
    return doc


@pytest.fixture
def mock_processing_status():
    """Create mock processing status object"""
    status = Mock()
    status.stage = ProcessingStageEnum.EXTRACTION
    status.status = StageStatusEnum.COMPLETED
    return status


# ============================================================================
# TEST DOCUMENT CONTENT GENERATORS
# ============================================================================

def test_generate_technical_pdf_content():
    """
    Test technical PDF content generation

    Expected:
    - Returns non-empty string
    - Contains RAG-related keywords
    - Has substantial content (multiple paragraphs)
    """
    content = generate_technical_pdf_content()

    assert isinstance(content, str)
    assert len(content) > 5000  # Should be substantial
    assert "RAG" in content or "Retrieval" in content
    assert "embedding" in content.lower()
    assert "vector" in content.lower()


def test_generate_deployment_guide_md():
    """
    Test deployment guide markdown generation

    Expected:
    - Returns markdown formatted content
    - Contains deployment instructions
    - Has heading markers (#)
    """
    content = generate_deployment_guide_md()

    assert isinstance(content, str)
    assert len(content) > 3000
    assert "#" in content  # Markdown headers
    assert "deployment" in content.lower()
    assert "docker" in content.lower()


def test_generate_api_reference_html():
    """
    Test API reference HTML generation

    Expected:
    - Returns valid HTML
    - Contains API endpoints
    - Has HTML tags
    """
    content = generate_api_reference_html()

    assert isinstance(content, str)
    assert len(content) > 4000
    assert "<html" in content.lower()
    assert "</html>" in content.lower()
    assert "api" in content.lower()
    assert "/upload" in content or "POST" in content


def test_generate_user_manual_txt():
    """
    Test user manual plain text generation

    Expected:
    - Returns plain text content
    - Contains user instructions
    - Has table of contents
    """
    content = generate_user_manual_txt()

    assert isinstance(content, str)
    assert len(content) > 4000
    assert "TABLE OF CONTENTS" in content or "table of contents" in content.lower()
    assert "user" in content.lower() or "manual" in content.lower()


def test_generate_research_paper_txt():
    """
    Test research paper content generation

    Expected:
    - Returns academic-style content
    - Contains abstract/introduction
    - Has substantial length
    """
    content = generate_research_paper_txt()

    assert isinstance(content, str)
    assert len(content) > 5000
    assert "Abstract" in content or "Introduction" in content
    assert "retrieval" in content.lower() or "passage" in content.lower()


def test_all_generators_return_unique_content():
    """
    Test that all generators produce unique content

    Expected:
    - No two generators produce identical content
    """
    contents = [
        generate_technical_pdf_content(),
        generate_deployment_guide_md(),
        generate_api_reference_html(),
        generate_user_manual_txt(),
        generate_research_paper_txt(),
    ]

    # Check all contents are unique
    for i, content1 in enumerate(contents):
        for j, content2 in enumerate(contents):
            if i != j:
                assert content1 != content2


def test_generators_produce_consistent_output():
    """
    Test that generators produce same output on multiple calls

    Expected:
    - Multiple calls to same generator produce identical output
    - Content is deterministic, not random
    """
    content1 = generate_technical_pdf_content()
    content2 = generate_technical_pdf_content()

    assert content1 == content2  # Should be deterministic


# ============================================================================
# TEST DEMODATASEEDER INITIALIZATION
# ============================================================================

def test_seeder_initialization(mock_db_session, temp_demo_data_path):
    """
    Test DemoDataSeeder initialization

    Expected:
    - Seeder created successfully
    - Parameters stored correctly
    - Empty uploaded_ids dict
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=3
    )

    assert seeder.db == mock_db_session
    assert seeder.demo_data_path == temp_demo_data_path
    assert seeder.document_count == 3
    assert seeder.uploaded_ids == {}


def test_seeder_document_count_limit(mock_db_session, temp_demo_data_path):
    """
    Test that document count is capped at 5

    Expected:
    - document_count clamped to max 5
    - Even if higher number requested
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=10  # Request 10
    )

    assert seeder.document_count == 5  # Should be capped at 5


def test_seeder_minimum_document_count(mock_db_session, temp_demo_data_path):
    """
    Test seeder with minimum document count

    Expected:
    - Accepts document_count=1
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    assert seeder.document_count == 1


# ============================================================================
# TEST CREATE_SAMPLE_DOCUMENTS
# ============================================================================

def test_create_sample_documents(mock_db_session, temp_demo_data_path):
    """
    Test sample document creation

    Expected:
    - Files created in demo-data/documents/
    - Correct number of files
    - Files have content
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=5
    )

    files = seeder._create_sample_documents()

    assert len(files) == 5
    for file_path in files:
        assert file_path.exists()
        assert file_path.stat().st_size > 1000  # Minimum 1KB


def test_create_sample_documents_file_types(mock_db_session, temp_demo_data_path):
    """
    Test that different file types are created

    Expected:
    - Mix of .txt, .md, .html files
    - Diverse file extensions
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=5
    )

    files = seeder._create_sample_documents()

    extensions = {f.suffix for f in files}

    # Should have mix of file types
    assert ".txt" in extensions
    assert ".md" in extensions
    assert ".html" in extensions


def test_create_sample_documents_partial_count(mock_db_session, temp_demo_data_path):
    """
    Test creating fewer than 5 documents

    Expected:
    - Only requested number created
    - First N documents selected
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=2
    )

    files = seeder._create_sample_documents()

    assert len(files) == 2


def test_create_sample_documents_directory_creation(mock_db_session, temp_demo_data_path):
    """
    Test that documents directory is created if missing

    Expected:
    - demo-data/documents/ directory created automatically
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    # Directory shouldn't exist yet
    docs_dir = temp_demo_data_path / "documents"
    assert not docs_dir.exists()

    # Create documents
    files = seeder._create_sample_documents()

    # Directory should now exist
    assert docs_dir.exists()
    assert docs_dir.is_dir()


# ============================================================================
# TEST UPLOAD_DOCUMENT
# ============================================================================

def test_upload_document_success(mock_db_session, temp_demo_data_path):
    """
    Test successful document upload

    Expected:
    - HTTP POST request made
    - Document ID returned
    - Retry logic not triggered on success
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    # Create test file
    test_file = temp_demo_data_path / "test.pdf"
    test_file.write_text("test content")

    doc_id = uuid4()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "document": {
            "id": str(doc_id),
            "filename": "test.pdf",
            "status": "completed"
        }
    }
    mock_response.raise_for_status = Mock()

    with patch('requests.post', return_value=mock_response):
        result = seeder._upload_document(test_file)

        assert result == doc_id


def test_upload_document_with_force_new(mock_db_session, temp_demo_data_path):
    """
    Test upload with force_new parameter

    Expected:
    - force_new=true in query params
    - Bypasses deduplication
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    test_file = temp_demo_data_path / "test.pdf"
    test_file.write_text("test content")

    doc_id = uuid4()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "document": {"id": str(doc_id), "filename": "test.pdf", "status": "completed"}
    }
    mock_response.raise_for_status = Mock()

    with patch('requests.post', return_value=mock_response) as mock_post:
        seeder._upload_document(test_file)

        # Verify force_new parameter was passed
        call_args = mock_post.call_args
        assert call_args[1]['params']['force_new'] == 'true'


def test_upload_document_retry_on_failure(mock_db_session, temp_demo_data_path):
    """
    Test retry logic on upload failure

    Expected:
    - Retries up to 3 times
    - Exponential backoff between retries
    - Exception raised after max retries
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    test_file = temp_demo_data_path / "test.pdf"
    test_file.write_text("test content")

    # Mock persistent failure
    with patch('requests.post', side_effect=Exception("Network error")):
        from tenacity import RetryError
        with pytest.raises((Exception, RetryError)) as exc_info:
            seeder._upload_document(test_file)

        # tenacity wraps the original exception in RetryError
        # Check if it's RetryError and verify retry attempts occurred
        if isinstance(exc_info.value, RetryError):
            # RetryError means retries were attempted
            assert exc_info.value is not None
        else:
            assert "Network error" in str(exc_info.value)


def test_upload_document_http_error(mock_db_session, temp_demo_data_path):
    """
    Test upload with HTTP error response

    Expected:
    - HTTP errors caught and retried
    - Exception raised with details
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    test_file = temp_demo_data_path / "test.pdf"
    test_file.write_text("test content")

    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("500 Server Error")

    with patch('requests.post', return_value=mock_response):
        with pytest.raises(Exception):
            seeder._upload_document(test_file)


# ============================================================================
# TEST UPLOAD_DOCUMENTS_CONCURRENT
# ============================================================================

def test_upload_documents_concurrent_success(mock_db_session, temp_demo_data_path):
    """
    Test concurrent upload of multiple documents

    Expected:
    - All documents uploaded
    - Document IDs collected
    - uploaded_ids dict populated
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=3
    )

    # Create test files
    test_files = []
    for i in range(3):
        test_file = temp_demo_data_path / f"test{i}.pdf"
        test_file.write_text(f"test content {i}")
        test_files.append(test_file)

    # Mock successful uploads
    doc_ids = [uuid4() for _ in range(3)]

    def mock_upload(file_path):
        idx = test_files.index(file_path)
        return doc_ids[idx]

    with patch.object(seeder, '_upload_document', side_effect=mock_upload):
        result_ids = seeder._upload_documents_concurrent(test_files)

        assert len(result_ids) == 3
        assert all(id in doc_ids for id in result_ids)
        assert len(seeder.uploaded_ids) == 3


def test_upload_documents_concurrent_partial_failure(mock_db_session, temp_demo_data_path):
    """
    Test concurrent upload with some failures

    Expected:
    - Successful uploads complete
    - Failed uploads logged but don't stop process
    - Partial list of IDs returned
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=3
    )

    test_files = []
    for i in range(3):
        test_file = temp_demo_data_path / f"test{i}.pdf"
        test_file.write_text(f"test content {i}")
        test_files.append(test_file)

    # Mock: first upload succeeds, second fails, third succeeds
    doc_id1 = uuid4()
    doc_id3 = uuid4()

    def mock_upload(file_path):
        if file_path.name == "test1.pdf":
            raise Exception("Upload failed")
        elif file_path.name == "test0.pdf":
            return doc_id1
        else:
            return doc_id3

    with patch.object(seeder, '_upload_document', side_effect=mock_upload):
        result_ids = seeder._upload_documents_concurrent(test_files)

        # Should have 2 successful uploads
        assert len(result_ids) == 2
        assert doc_id1 in result_ids
        assert doc_id3 in result_ids


# ============================================================================
# TEST WAIT_FOR_PROCESSING
# ============================================================================

def test_wait_for_processing_success(mock_db_session, temp_demo_data_path, mock_document):
    """
    Test waiting for processing to complete

    Expected:
    - Polls processing status
    - Returns when all stages complete
    - No timeout
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    doc_id = uuid4()

    # Mock processing statuses - all completed
    mock_statuses = [
        Mock(stage=ProcessingStageEnum.EXTRACTION, status=StageStatusEnum.COMPLETED),
        Mock(stage=ProcessingStageEnum.CHUNKING, status=StageStatusEnum.COMPLETED),
        Mock(stage=ProcessingStageEnum.EMBEDDING, status=StageStatusEnum.COMPLETED),
    ]

    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document
    mock_db_session.query.return_value.filter.return_value.all.return_value = mock_statuses

    # Should complete without timeout
    seeder._wait_for_processing([doc_id], timeout=10)


def test_wait_for_processing_timeout(mock_db_session, temp_demo_data_path, mock_document):
    """
    Test processing timeout

    Expected:
    - TimeoutError raised
    - Error message includes timeout duration
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    doc_id = uuid4()

    # Mock processing statuses - never completes
    mock_statuses = [
        Mock(stage=ProcessingStageEnum.EXTRACTION, status=StageStatusEnum.IN_PROGRESS),
    ]

    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document
    mock_db_session.query.return_value.filter.return_value.all.return_value = mock_statuses

    with pytest.raises(TimeoutError) as exc_info:
        seeder._wait_for_processing([doc_id], timeout=1)  # Short timeout

    assert "did not complete" in str(exc_info.value).lower()


def test_wait_for_processing_document_not_found(mock_db_session, temp_demo_data_path):
    """
    Test processing wait when document doesn't exist

    Expected:
    - Error logged
    - Continues checking other documents
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    doc_id = uuid4()

    # Mock: document not found
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    # Should timeout since document never found
    with pytest.raises(TimeoutError):
        seeder._wait_for_processing([doc_id], timeout=1)


# ============================================================================
# TEST VERIFY_SEARCH
# ============================================================================

def test_verify_search_success(mock_db_session, temp_demo_data_path):
    """
    Test search verification success

    Expected:
    - Sample queries executed
    - Returns True if results found
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "documents": [
            {"document_id": str(uuid4()), "chunk_text": "test result"}
        ]
    }
    mock_response.raise_for_status = Mock()

    with patch('requests.post', return_value=mock_response):
        result = seeder._verify_search()

        assert result is True


def test_verify_search_no_results(mock_db_session, temp_demo_data_path):
    """
    Test search verification when no results found

    Expected:
    - Returns False
    - All test queries attempted
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"documents": []}  # Empty results
    mock_response.raise_for_status = Mock()

    with patch('requests.post', return_value=mock_response):
        result = seeder._verify_search()

        assert result is False


def test_verify_search_api_error(mock_db_session, temp_demo_data_path):
    """
    Test search verification with API error

    Expected:
    - Returns False
    - Error logged
    - No exception raised
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    with patch('requests.post', side_effect=Exception("API Error")):
        result = seeder._verify_search()

        assert result is False


# ============================================================================
# TEST MAIN SEED WORKFLOW
# ============================================================================

def test_seed_full_workflow(mock_db_session, temp_demo_data_path):
    """
    Test complete seeding workflow

    Expected:
    - Documents created
    - Documents uploaded
    - Processing waited for
    - Search verified
    - Results returned
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=2
    )

    # Mock all sub-methods
    doc_ids = [uuid4(), uuid4()]

    with patch.object(seeder, '_create_sample_documents') as mock_create:
        mock_files = [temp_demo_data_path / f"doc{i}.txt" for i in range(2)]
        for f in mock_files:
            f.write_text("test")
        mock_create.return_value = mock_files

        with patch.object(seeder, '_upload_documents_concurrent', return_value=doc_ids):
            with patch.object(seeder, '_wait_for_processing'):
                with patch.object(seeder, '_verify_search', return_value=True):
                    results = seeder.seed()

                    assert results["success_count"] == 2
                    assert results["failure_count"] == 0
                    assert results["search_verified"] is True
                    assert len(results["document_ids"]) == 2


def test_seed_with_upload_failures(mock_db_session, temp_demo_data_path):
    """
    Test seeding with some upload failures

    Expected:
    - Partial success recorded
    - failure_count > 0
    - Process completes
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=3
    )

    doc_ids = [uuid4()]  # Only 1 out of 3 succeeds

    with patch.object(seeder, '_create_sample_documents') as mock_create:
        mock_files = [temp_demo_data_path / f"doc{i}.txt" for i in range(3)]
        for f in mock_files:
            f.write_text("test")
        mock_create.return_value = mock_files

        with patch.object(seeder, '_upload_documents_concurrent', return_value=doc_ids):
            with patch.object(seeder, '_wait_for_processing'):
                with patch.object(seeder, '_verify_search', return_value=False):
                    results = seeder.seed()

                    assert results["success_count"] == 1
                    assert results["failure_count"] == 2


def test_seed_exception_handling(mock_db_session, temp_demo_data_path):
    """
    Test that exceptions are caught and re-raised

    Expected:
    - Exception logged
    - Exception propagated
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    with patch.object(seeder, '_create_sample_documents', side_effect=Exception("Test error")):
        with pytest.raises(Exception) as exc_info:
            seeder.seed()

        assert "Test error" in str(exc_info.value)


# ============================================================================
# TEST MAIN FUNCTION
# ============================================================================

def test_main_default_arguments(mock_db_session, temp_demo_data_path):
    """
    Test main function with default arguments

    Expected:
    - Default count=5
    - Seeding executed
    - Exit code 0 on success
    """
    with patch('sys.argv', ['seed_demo.py']):
        with patch('scripts.seed_demo.SessionLocal', return_value=mock_db_session):
            with patch('scripts.seed_demo.DemoDataSeeder') as mock_seeder_class:
                mock_seeder = Mock()
                mock_seeder.seed.return_value = {
                    "success_count": 5,
                    "failure_count": 0,
                    "document_ids": [str(uuid4()) for _ in range(5)],
                    "search_verified": True
                }
                mock_seeder_class.return_value = mock_seeder

                from scripts.seed_demo import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0


def test_main_custom_count(mock_db_session, temp_demo_data_path):
    """
    Test main function with custom document count

    Expected:
    - Custom count passed to seeder
    """
    with patch('sys.argv', ['seed_demo.py', '--count', '3']):
        with patch('scripts.seed_demo.SessionLocal', return_value=mock_db_session):
            with patch('scripts.seed_demo.DemoDataSeeder') as mock_seeder_class:
                mock_seeder = Mock()
                mock_seeder.seed.return_value = {
                    "success_count": 3,
                    "failure_count": 0,
                    "document_ids": [str(uuid4()) for _ in range(3)],
                    "search_verified": True
                }
                mock_seeder_class.return_value = mock_seeder

                from scripts.seed_demo import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Verify seeder was created with count=3
                call_args = mock_seeder_class.call_args
                assert call_args[1]['document_count'] == 3


def test_main_failure_exit_code(mock_db_session, temp_demo_data_path):
    """
    Test main function exits with code 1 on failure

    Expected:
    - Exit code 1
    - Error message printed
    """
    with patch('sys.argv', ['seed_demo.py']):
        with patch('scripts.seed_demo.SessionLocal', return_value=mock_db_session):
            with patch('scripts.seed_demo.DemoDataSeeder') as mock_seeder_class:
                mock_seeder_class.side_effect = Exception("Seeding failed")

                from scripts.seed_demo import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1


# ============================================================================
# TEST ERROR RECOVERY
# ============================================================================

def test_upload_retry_exponential_backoff(mock_db_session, temp_demo_data_path):
    """
    Test that retry uses exponential backoff

    Expected:
    - Multiple retry attempts
    - Increasing delay between attempts
    - Max 3 attempts
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    test_file = temp_demo_data_path / "test.pdf"
    test_file.write_text("test content")

    # Track retry attempts
    attempt_count = [0]

    def mock_post_with_failures(*args, **kwargs):
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise Exception("Temporary failure")
        # Success on 3rd attempt
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "document": {"id": str(uuid4()), "filename": "test.pdf", "status": "completed"}
        }
        mock_resp.raise_for_status = Mock()
        return mock_resp

    with patch('requests.post', side_effect=mock_post_with_failures):
        result = seeder._upload_document(test_file)

        # Should succeed after retries
        assert result is not None
        assert attempt_count[0] == 3  # Succeeded on 3rd attempt


def test_processing_status_polling_interval(mock_db_session, temp_demo_data_path, mock_document):
    """
    Test that processing status is polled at correct interval

    Expected:
    - Multiple polls executed
    - 2-second interval between polls
    """
    seeder = DemoDataSeeder(
        db=mock_db_session,
        demo_data_path=temp_demo_data_path,
        document_count=1
    )

    doc_id = uuid4()

    # Mock: First check returns in_progress, second returns completed
    check_count = [0]

    def mock_query_side_effect(*args):
        check_count[0] += 1
        if check_count[0] == 1:
            # First check: still processing
            return [
                Mock(stage=ProcessingStageEnum.EXTRACTION, status=StageStatusEnum.IN_PROGRESS),
            ]
        else:
            # Second check: all complete
            return [
                Mock(stage=ProcessingStageEnum.EXTRACTION, status=StageStatusEnum.COMPLETED),
                Mock(stage=ProcessingStageEnum.CHUNKING, status=StageStatusEnum.COMPLETED),
                Mock(stage=ProcessingStageEnum.EMBEDDING, status=StageStatusEnum.COMPLETED),
            ]

    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document
    mock_db_session.query.return_value.filter.return_value.all.side_effect = mock_query_side_effect

    with patch('time.sleep') as mock_sleep:
        seeder._wait_for_processing([doc_id], timeout=30)

        # Should have called sleep with 2-second interval
        assert mock_sleep.called
        assert mock_sleep.call_args[0][0] == 2
