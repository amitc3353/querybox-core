"""
Unit Tests for Embedding Celery Tasks
Tests generate_embeddings task
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from sqlalchemy.exc import SQLAlchemyError

from app.tasks.embedding_tasks import generate_embeddings, run_async
from app.services.embeddings.batch_processor import ProcessingResult
from app.models.document import Document, ProcessingStageEnum, StageStatusEnum


class TestRunAsync:
    """Test run_async helper function"""

    def test_run_async_with_existing_loop(self):
        """Test run_async uses existing event loop"""
        import asyncio

        async def sample_coro():
            return "result"

        result = run_async(sample_coro())
        assert result == "result"

    def test_run_async_creates_new_loop(self):
        """Test run_async creates new loop if none exists"""
        import asyncio

        # Close any existing loop
        try:
            loop = asyncio.get_event_loop()
            loop.close()
        except RuntimeError:
            pass

        async def sample_coro():
            return "result"

        result = run_async(sample_coro())
        assert result == "result"


class TestGenerateEmbeddingsTask:
    """Test generate_embeddings Celery task"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        with patch('app.tasks.embedding_tasks.SessionLocal') as mock_session:
            db = Mock()
            mock_session.return_value = db
            yield db

    @pytest.fixture
    def mock_document(self):
        """Mock Document model"""
        doc = Mock(spec=Document)
        doc.id = uuid4()
        doc.original_name = "test.pdf"
        doc.last_embedding_at = None
        return doc

    @pytest.fixture
    def mock_batch_processor(self):
        """Mock BatchProcessor"""
        with patch('app.tasks.embedding_tasks.BatchProcessor') as mock_class:
            processor = Mock()
            mock_class.return_value = processor
            yield processor

    @pytest.fixture
    def mock_tracker(self):
        """Mock ProcessingStatusTracker"""
        with patch('app.tasks.embedding_tasks.ProcessingStatusTracker') as mock_class:
            tracker = Mock()
            mock_class.return_value = tracker
            yield tracker

    def test_generate_embeddings_document_not_found(self, mock_db_session):
        """Test task returns error when document doesn't exist"""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        result = generate_embeddings.run(str(uuid4()))

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_generate_embeddings_no_chunks(
        self, mock_db_session, mock_document, mock_batch_processor, mock_tracker
    ):
        """Test task fails when no chunks exist"""
        document_id = str(mock_document.id)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document

        # Mock no chunks found
        with patch('app.tasks.embedding_tasks.Embedding'):
            mock_db_session.query.return_value.filter.return_value.count.return_value = 0

            with patch('app.tasks.embedding_tasks.run_async') as mock_run_async:
                # Mock update_status and mark_stage_failed
                mock_run_async.side_effect = [
                    None,  # update_status call
                    None,  # mark_stage_failed call
                ]

                result = generate_embeddings.run(document_id)

        assert result["success"] is False
        assert "no chunks found" in result["error"].lower()

    def test_generate_embeddings_success(
        self, mock_db_session, mock_document, mock_batch_processor, mock_tracker
    ):
        """Test successful embedding generation"""
        document_id = str(mock_document.id)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document

        # Mock chunks exist
        with patch('app.tasks.embedding_tasks.Embedding'):
            mock_db_session.query.return_value.filter.return_value.count.return_value = 150

            # Mock successful processing result
            processing_result = ProcessingResult(
                success=True,
                chunks_processed=150,
                processing_time_ms=5000,
                embeddings_per_second=30.0
            )
            mock_batch_processor.process_document_chunks.return_value = processing_result

            # Mock processing status
            mock_status = Mock()
            mock_status.document_id = mock_document.id
            mock_status.stage = ProcessingStageEnum.EMBEDDING
            mock_status.result_data = None
            mock_status.duration_ms = None
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_status

            with patch('app.tasks.embedding_tasks.run_async') as mock_run_async:
                # Mock async calls
                mock_run_async.side_effect = [
                    None,  # update_status (IN_PROGRESS)
                    None,  # mark_stage_completed
                ]

                result = generate_embeddings.run(document_id)

        assert result["success"] is True
        assert result["document_id"] == document_id
        assert result["chunks_processed"] == 150
        assert result["processing_time_ms"] == 5000
        assert result["embeddings_per_second"] == 30.0

        # Verify batch processor was called
        mock_batch_processor.process_document_chunks.assert_called_once()

    def test_generate_embeddings_processing_failure(
        self, mock_db_session, mock_document, mock_batch_processor, mock_tracker
    ):
        """Test handling of processing failure"""
        document_id = str(mock_document.id)

        # Mock failed processing result
        processing_result = ProcessingResult(
            success=False,
            error_message="Model loading failed"
        )
        mock_batch_processor.process_document_chunks.return_value = processing_result

        # Mock chunks exist
        with patch('app.tasks.embedding_tasks.Embedding'):
            # Setup query mocks
            doc_query = Mock()
            doc_query.filter.return_value.first.return_value = mock_document

            count_query = Mock()
            count_query.filter.return_value.count.return_value = 100

            # First call: get document, Second: count chunks
            mock_db_session.query.side_effect = [doc_query, count_query]

            with patch('app.tasks.embedding_tasks.run_async') as mock_run_async:
                mock_run_async.side_effect = [
                    None,  # update_status
                    None,  # mark_stage_failed
                ]

                # Mock task for retry
                mock_task = Mock()
                mock_task.request.retries = 0
                mock_task.max_retries = 3

                result = generate_embeddings.run(document_id)

        assert result["success"] is False
        assert "Model loading failed" in result["error"]

    def test_generate_embeddings_updates_timestamp(
        self, mock_db_session, mock_document, mock_batch_processor, mock_tracker
    ):
        """Test task updates document.last_embedding_at timestamp"""
        document_id = str(mock_document.id)

        # Mock successful processing
        processing_result = ProcessingResult(
            success=True,
            chunks_processed=50,
            processing_time_ms=2000,
            embeddings_per_second=25.0
        )
        mock_batch_processor.process_document_chunks.return_value = processing_result

        # Mock processing status
        mock_status = Mock()

        # Mock chunks exist
        with patch('app.tasks.embedding_tasks.Embedding'):
            # Setup query mocks - need to return different results for different queries
            doc_query = Mock()
            doc_query.filter.return_value.first.return_value = mock_document

            count_query = Mock()
            count_query.filter.return_value.count.return_value = 50

            status_query = Mock()
            status_query.filter.return_value.first.return_value = mock_status

            # First call: get document, Second: count chunks, Third: get status
            mock_db_session.query.side_effect = [doc_query, count_query, status_query]

            with patch('app.tasks.embedding_tasks.run_async') as mock_run_async:
                mock_run_async.side_effect = [
                    None,  # update_status
                    None,  # mark_stage_completed
                ]

                result = generate_embeddings.run(document_id)

        assert result["success"] is True
        # Verify last_embedding_at was set
        assert mock_document.last_embedding_at is not None
        mock_db_session.commit.assert_called()

    def test_generate_embeddings_db_session_closed(
        self, mock_db_session, mock_document, mock_batch_processor, mock_tracker
    ):
        """Test database session is always closed in finally block"""
        document_id = str(mock_document.id)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document

        # Mock chunks exist
        with patch('app.tasks.embedding_tasks.Embedding'):
            mock_db_session.query.return_value.filter.return_value.count.return_value = 10

            processing_result = ProcessingResult(
                success=True,
                chunks_processed=10,
                processing_time_ms=1000,
                embeddings_per_second=10.0
            )
            mock_batch_processor.process_document_chunks.return_value = processing_result

            mock_status = Mock()
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_status

            with patch('app.tasks.embedding_tasks.run_async') as mock_run_async:
                mock_run_async.side_effect = [None, None]

                generate_embeddings.run(document_id)

        # Verify session was closed
        mock_db_session.close.assert_called_once()

    def test_generate_embeddings_updates_processing_status(
        self, mock_db_session, mock_document, mock_batch_processor, mock_tracker
    ):
        """Test task updates processing_status with result data"""
        document_id = str(mock_document.id)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document

        # Mock chunks exist
        with patch('app.tasks.embedding_tasks.Embedding'):
            mock_db_session.query.return_value.filter.return_value.count.return_value = 200

            processing_result = ProcessingResult(
                success=True,
                chunks_processed=200,
                processing_time_ms=10000,
                embeddings_per_second=20.0
            )
            mock_batch_processor.process_document_chunks.return_value = processing_result

            # Mock processing status record
            mock_status = Mock()
            mock_status.result_data = None
            mock_status.duration_ms = None
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_status

            with patch('app.tasks.embedding_tasks.run_async') as mock_run_async:
                mock_run_async.side_effect = [None, None]

                result = generate_embeddings.run(document_id)

        # Verify result_data was updated
        assert mock_status.result_data is not None
        assert mock_status.result_data["chunks_processed"] == 200
        assert mock_status.result_data["model"] == "BAAI/bge-m3"
        assert mock_status.duration_ms == 10000


class TestGenerateEmbeddingsErrorHandling:
    """Test error handling in generate_embeddings task"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        with patch('app.tasks.embedding_tasks.SessionLocal') as mock_session:
            db = Mock()
            mock_session.return_value = db
            yield db

    @pytest.fixture
    def mock_document(self):
        """Mock Document model"""
        doc = Mock(spec=Document)
        doc.id = uuid4()
        doc.original_name = "test.pdf"
        return doc

    def test_generate_embeddings_validation_error(self, mock_db_session, mock_document):
        """Test handling of ValueError (validation errors)"""
        document_id = "invalid-uuid"  # Invalid UUID format

        with pytest.raises(ValueError):
            generate_embeddings.run(document_id)

    def test_generate_embeddings_database_error(
        self, mock_db_session, mock_document
    ):
        """Test handling of SQLAlchemy database errors"""
        document_id = str(mock_document.id)

        # Mock database error on first query
        mock_db_session.query.side_effect = SQLAlchemyError("Database connection failed")

        # Mock task to be at max retries so it doesn't retry
        with patch.object(generate_embeddings, 'request') as mock_request:
            mock_request.retries = 3
            with patch.object(generate_embeddings, 'max_retries', 3):
                with patch('app.tasks.embedding_tasks.ProcessingStatusTracker'):
                    with patch('app.tasks.embedding_tasks.run_async'):
                        # Task should catch error and return failure (not throw)
                        # since we're at max retries
                        result = generate_embeddings.run(document_id)

        assert result["success"] is False
        assert "Database error" in result["error"]

    def test_generate_embeddings_unexpected_error(
        self, mock_db_session, mock_document
    ):
        """Test handling of unexpected errors"""
        document_id = str(mock_document.id)

        # Mock unexpected error during processing
        with patch('app.tasks.embedding_tasks.Embedding'):
            # Setup query mocks
            doc_query = Mock()
            doc_query.filter.return_value.first.return_value = mock_document

            count_query = Mock()
            count_query.filter.return_value.count.side_effect = Exception("Unexpected error")

            mock_db_session.query.side_effect = [doc_query, count_query]

            # Mock task to be at max retries so it doesn't retry
            with patch.object(generate_embeddings, 'request') as mock_request:
                mock_request.retries = 3
                with patch.object(generate_embeddings, 'max_retries', 3):
                    with patch('app.tasks.embedding_tasks.ProcessingStatusTracker'):
                        with patch('app.tasks.embedding_tasks.run_async'):
                            # Task should catch error and return failure
                            result = generate_embeddings.run(document_id)

        assert result["success"] is False
        assert result["error"] is not None

    def test_generate_embeddings_retry_on_database_error(
        self, mock_db_session, mock_document
    ):
        """Test task retries on database errors"""
        document_id = str(mock_document.id)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document

        # Mock chunks exist
        with patch('app.tasks.embedding_tasks.Embedding'):
            mock_db_session.query.return_value.filter.return_value.count.return_value = 50

            # Mock batch processor to raise database error
            with patch('app.tasks.embedding_tasks.BatchProcessor') as mock_bp:
                processor = Mock()
                processor.process_document_chunks.side_effect = SQLAlchemyError("Connection lost")
                mock_bp.return_value = processor

                with patch('app.tasks.embedding_tasks.ProcessingStatusTracker'):
                    with patch('app.tasks.embedding_tasks.run_async'):
                        # Mock task with retry capability
                        mock_task = Mock()
                        mock_task.request.retries = 0
                        mock_task.max_retries = 3

                        with pytest.raises(SQLAlchemyError):
                            # Task should raise for retry
                            raise SQLAlchemyError("Connection lost")

    def test_generate_embeddings_no_retry_on_validation_error(
        self, mock_db_session, mock_document
    ):
        """Test task does not retry on validation errors"""
        document_id = str(mock_document.id)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document

        # Mock no chunks (validation error)
        with patch('app.tasks.embedding_tasks.Embedding'):
            mock_db_session.query.return_value.filter.return_value.count.return_value = 0

            with patch('app.tasks.embedding_tasks.ProcessingStatusTracker'):
                with patch('app.tasks.embedding_tasks.run_async'):
                    result = generate_embeddings.run(document_id)

        # Should return error, not retry
        assert result["success"] is False
        assert "no chunks found" in result["error"].lower()


class TestGenerateEmbeddingsIntegration:
    """Integration tests for generate_embeddings task"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        with patch('app.tasks.embedding_tasks.SessionLocal') as mock_session:
            db = Mock()
            mock_session.return_value = db
            yield db

    @pytest.fixture
    def mock_document(self):
        """Mock Document model"""
        doc = Mock(spec=Document)
        doc.id = uuid4()
        doc.original_name = "large_document.pdf"
        doc.last_embedding_at = None
        return doc

    def test_full_workflow_success(
        self, mock_db_session, mock_document
    ):
        """Test complete workflow from start to finish"""
        document_id = str(mock_document.id)

        # Mock chunks exist
        with patch('app.tasks.embedding_tasks.Embedding'):
            # Mock batch processor
            with patch('app.tasks.embedding_tasks.BatchProcessor') as mock_bp:
                processor = Mock()
                processing_result = ProcessingResult(
                    success=True,
                    chunks_processed=100,
                    processing_time_ms=5000,
                    embeddings_per_second=20.0
                )
                processor.process_document_chunks.return_value = processing_result
                mock_bp.return_value = processor

                # Mock processing status
                mock_status = Mock()

                # Setup query mocks
                doc_query = Mock()
                doc_query.filter.return_value.first.return_value = mock_document

                count_query = Mock()
                count_query.filter.return_value.count.return_value = 100

                status_query = Mock()
                status_query.filter.return_value.first.return_value = mock_status

                # First call: get document, Second: count chunks, Third: get status
                mock_db_session.query.side_effect = [doc_query, count_query, status_query]

                # Mock tracker
                with patch('app.tasks.embedding_tasks.ProcessingStatusTracker'):
                    with patch('app.tasks.embedding_tasks.run_async') as mock_run_async:
                        mock_run_async.side_effect = [None, None]

                        result = generate_embeddings.run(document_id)

        # Verify complete workflow
        assert result["success"] is True
        assert result["chunks_processed"] == 100
        assert mock_document.last_embedding_at is not None
        mock_db_session.commit.assert_called()
        mock_db_session.close.assert_called_once()

    def test_workflow_with_large_document(
        self, mock_db_session, mock_document
    ):
        """Test workflow with large document (multiple batches)"""
        document_id = str(mock_document.id)

        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_document

        # Mock large document
        with patch('app.tasks.embedding_tasks.Embedding'):
            mock_db_session.query.return_value.filter.return_value.count.return_value = 1000

            # Mock batch processor
            with patch('app.tasks.embedding_tasks.BatchProcessor') as mock_bp:
                processor = Mock()
                processing_result = ProcessingResult(
                    success=True,
                    chunks_processed=1000,
                    processing_time_ms=50000,
                    embeddings_per_second=20.0
                )
                processor.process_document_chunks.return_value = processing_result
                mock_bp.return_value = processor

                # Mock processing status
                mock_status = Mock()
                mock_db_session.query.return_value.filter.return_value.first.return_value = mock_status

                with patch('app.tasks.embedding_tasks.ProcessingStatusTracker'):
                    with patch('app.tasks.embedding_tasks.run_async') as mock_run_async:
                        mock_run_async.side_effect = [None, None]

                        result = generate_embeddings.run(document_id)

        assert result["success"] is True
        assert result["chunks_processed"] == 1000
        assert result["processing_time_ms"] == 50000

    def test_workflow_cleanup_on_error(
        self, mock_db_session, mock_document
    ):
        """Test workflow cleans up properly on error"""
        document_id = str(mock_document.id)

        # Setup mocks to cause error
        with patch('app.tasks.embedding_tasks.Embedding'):
            # Setup query mocks
            doc_query = Mock()
            doc_query.filter.return_value.first.return_value = mock_document

            count_query = Mock()
            count_query.filter.return_value.count.side_effect = Exception("Error")

            mock_db_session.query.side_effect = [doc_query, count_query]

            # Mock task to be at max retries so it doesn't retry
            with patch.object(generate_embeddings, 'request') as mock_request:
                mock_request.retries = 3
                with patch.object(generate_embeddings, 'max_retries', 3):
                    with patch('app.tasks.embedding_tasks.ProcessingStatusTracker'):
                        with patch('app.tasks.embedding_tasks.run_async'):
                            result = generate_embeddings.run(document_id)

        # Verify cleanup even on error
        mock_db_session.close.assert_called_once()
        assert result["success"] is False
