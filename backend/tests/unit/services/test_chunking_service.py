"""
Unit Tests for Chunking Service
Tests ChunkingService without external dependencies
"""
import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from app.services.chunking.chunking_service import (
    ChunkingService,
    ChunkData,
    ChunkingResult,
    get_chunking_service,
)
from app.models.embedding import Embedding


class TestChunkData:
    """Test ChunkData dataclass"""

    def test_chunk_data_creation(self):
        """Test creating a ChunkData instance"""
        chunk = ChunkData(
            text="This is a sample chunk of text.",
            chunk_index=0,
            start_position=0,
            end_position=32,
            token_estimate=8,
        )

        assert chunk.text == "This is a sample chunk of text."
        assert chunk.chunk_index == 0
        assert chunk.start_position == 0
        assert chunk.end_position == 32
        assert chunk.token_estimate == 8


class TestChunkingResult:
    """Test ChunkingResult dataclass"""

    def test_successful_result(self):
        """Test creating a successful chunking result"""
        result = ChunkingResult(
            success=True,
            chunk_count=47,
            total_chars=45230,
            avg_chunk_size=962,
            processing_time_ms=2345,
        )

        assert result.success is True
        assert result.chunk_count == 47
        assert result.total_chars == 45230
        assert result.avg_chunk_size == 962
        assert result.processing_time_ms == 2345
        assert result.error_message is None

    def test_failed_result(self):
        """Test creating a failed chunking result"""
        result = ChunkingResult(
            success=False,
            processing_time_ms=100,
            error_message="Text too short",
        )

        assert result.success is False
        assert result.error_message == "Text too short"
        assert result.chunk_count == 0
        assert result.total_chars == 0


class TestChunkingService:
    """Test ChunkingService"""

    @pytest.fixture
    def service(self):
        """Create chunking service instance"""
        return ChunkingService(
            chunk_size=1000,
            chunk_overlap=200,
            min_chunk_size=100,
        )

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.delete.return_value = 0
        mock_db.bulk_insert_mappings = Mock()
        mock_db.commit = Mock()
        mock_db.rollback = Mock()
        mock_db.begin_nested = Mock()
        return mock_db

    def test_split_into_sentences_basic(self, service):
        """Test basic sentence splitting"""
        text = "This is sentence one. This is sentence two! Is this sentence three?"
        sentences = service._split_into_sentences(text)

        assert len(sentences) == 3
        assert "This is sentence one." in sentences[0]
        assert "This is sentence two!" in sentences[1]
        assert "Is this sentence three?" in sentences[2]

    def test_split_into_sentences_multiple_spaces(self, service):
        """Test sentence splitting with multiple spaces"""
        text = "First sentence.  Second sentence.   Third sentence."
        sentences = service._split_into_sentences(text)

        assert len(sentences) == 3
        assert all(s.strip() for s in sentences)  # No empty strings

    def test_split_into_sentences_no_boundaries(self, service):
        """Test text with no sentence boundaries returns single item"""
        text = "this is all lowercase with no periods or capitals"
        sentences = service._split_into_sentences(text)

        assert len(sentences) == 1
        assert sentences[0] == text

    def test_split_into_sentences_mixed_terminators(self, service):
        """Test sentence splitting with different terminators"""
        text = "Statement. Question? Exclamation! Another statement."
        sentences = service._split_into_sentences(text)

        assert len(sentences) == 4

    def test_create_chunks_basic(self, service):
        """Test basic chunk creation from sentences"""
        sentences = [
            "This is the first sentence.",
            "This is the second sentence.",
            "This is the third sentence.",
        ]

        chunks = service._create_chunks(sentences)

        assert len(chunks) > 0
        assert all(isinstance(chunk, ChunkData) for chunk in chunks)
        assert chunks[0].chunk_index == 0
        assert chunks[0].start_position == 0

    def test_create_chunks_respects_chunk_size(self, service):
        """Test chunks don't exceed target chunk size"""
        # Create sentences that would exceed chunk size
        sentences = ["A" * 600 + ".", "B" * 600 + ".", "C" * 600 + "."]

        chunks = service._create_chunks(sentences)

        # Should create multiple chunks
        assert len(chunks) > 1
        # Each chunk should not significantly exceed chunk_size
        for chunk in chunks[:-1]:  # Last chunk can be smaller
            assert len(chunk.text) <= service.chunk_size + 200  # Allow some overlap

    def test_chunk_overlap_exists(self, service):
        """Test that chunks have overlap"""
        # Create text that will generate multiple chunks
        sentences = [f"Sentence {i}. " for i in range(50)]

        chunks = service._create_chunks(sentences)

        if len(chunks) >= 2:
            # Check overlap between first two chunks
            chunk1_end = chunks[0].text[-service.chunk_overlap:]
            chunk2_start = chunks[1].text[:service.chunk_overlap]

            # There should be some text similarity (overlap)
            assert chunks[1].start_position < chunks[0].end_position

    def test_chunk_position_tracking(self, service):
        """Test start/end positions are correct"""
        sentences = ["First. ", "Second. ", "Third. "]

        chunks = service._create_chunks(sentences)

        # Verify positions are sequential
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.start_position >= 0
            assert chunk.end_position > chunk.start_position
            assert chunk.end_position - chunk.start_position == len(chunk.text)

    def test_sentence_boundary_preservation(self, service):
        """Test chunks end with sentence terminators when possible"""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        sentences = service._split_into_sentences(text)
        chunks = service._create_chunks(sentences)

        # Most chunks should end with punctuation
        for chunk in chunks[:-1]:  # Skip last chunk
            last_char = chunk.text.strip()[-1] if chunk.text.strip() else ''
            # Should end with sentence terminator or be at word boundary
            assert last_char in '.!?' or last_char.isalnum()

    def test_estimate_tokens(self, service):
        """Test token estimation (roughly chars / 4)"""
        text = "This is a sample text for token estimation."
        estimated = service._estimate_tokens(text)

        # Should be roughly chars / 4
        expected = len(text) // 4
        assert abs(estimated - expected) <= 1  # Allow 1 token difference

    def test_estimate_tokens_empty(self, service):
        """Test token estimation for empty text"""
        estimated = service._estimate_tokens("")
        assert estimated == 0

    def test_chunk_text_success(self, service, mock_db):
        """Test successful chunking of text"""
        document_id = uuid4()
        text = "This is a test. " * 100  # ~1600 chars

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is True
        assert result.chunk_count > 0
        assert result.total_chars > 0
        assert result.avg_chunk_size > 0
        assert result.processing_time_ms >= 0
        assert result.error_message is None

    def test_chunk_text_too_short(self, service, mock_db):
        """Test chunking fails with text too short"""
        document_id = uuid4()
        text = "Short"  # < 100 chars

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is False
        assert "too short" in result.error_message.lower()

    def test_chunk_text_not_string(self, service, mock_db):
        """Test chunking fails with non-string input"""
        document_id = uuid4()

        result = service.chunk_text(
            text=12345,  # Not a string
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is False
        assert "must be a string" in result.error_message.lower()

    def test_chunk_text_at_minimum_length(self, service, mock_db):
        """Test chunking with text at minimum length"""
        document_id = uuid4()
        text = "A" * 100  # Exactly at minimum

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is True
        assert result.chunk_count >= 1

    def test_save_chunks_deletes_old_chunks(self, service, mock_db):
        """Test save_chunks deletes old chunks first"""
        document_id = uuid4()
        chunks = [
            ChunkData(
                text="Sample chunk",
                chunk_index=0,
                start_position=0,
                end_position=12,
                token_estimate=3,
            )
        ]

        service.save_chunks(chunks, document_id, mock_db)

        # Verify delete was called
        mock_db.query.assert_called()
        mock_db.commit.assert_called()

    def test_save_chunks_bulk_insert(self, service, mock_db):
        """Test save_chunks uses bulk insert"""
        document_id = uuid4()
        chunks = [
            ChunkData(
                text=f"Chunk {i}",
                chunk_index=i,
                start_position=i * 10,
                end_position=(i + 1) * 10,
                token_estimate=2,
            )
            for i in range(5)
        ]

        count = service.save_chunks(chunks, document_id, mock_db)

        assert count == 5
        mock_db.bulk_insert_mappings.assert_called_once()
        # Verify Embedding model was used
        call_args = mock_db.bulk_insert_mappings.call_args
        assert call_args[0][0] == Embedding

    def test_save_chunks_handles_db_error(self, service, mock_db):
        """Test save_chunks handles database errors"""
        document_id = uuid4()
        chunks = [ChunkData("Test", 0, 0, 4, 1)]

        # Make commit raise an exception
        mock_db.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            service.save_chunks(chunks, document_id, mock_db)

        assert "Database error" in str(exc_info.value)
        mock_db.rollback.assert_called()

    def test_save_chunks_empty_list(self, service, mock_db):
        """Test save_chunks with empty chunk list"""
        document_id = uuid4()
        chunks = []

        count = service.save_chunks(chunks, document_id, mock_db)

        assert count == 0
        # Should still delete old chunks even if no new ones
        mock_db.commit.assert_called()

    def test_configuration_from_env(self):
        """Test service reads configuration from environment"""
        service = ChunkingService(
            chunk_size=500,
            chunk_overlap=100,
            min_chunk_size=50,
        )

        assert service.chunk_size == 500
        assert service.chunk_overlap == 100
        assert service.min_chunk_size == 50

    def test_default_configuration(self):
        """Test service uses default configuration"""
        service = ChunkingService()

        # Should use defaults
        assert service.chunk_size == 1000
        assert service.chunk_overlap == 200
        assert service.min_chunk_size == 100

    def test_chunk_text_large_document(self, service, mock_db):
        """Test chunking a large document"""
        document_id = uuid4()
        # Create large text (10k chars)
        text = "This is a sentence. " * 500

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is True
        assert result.chunk_count > 5  # Should create multiple chunks
        assert result.avg_chunk_size > 0

    def test_sequential_chunk_indices(self, service):
        """Test chunk indices are sequential (0, 1, 2, ...)"""
        sentences = [f"Sentence {i}. " for i in range(20)]
        chunks = service._create_chunks(sentences)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_no_negative_positions(self, service):
        """Test chunks never have negative positions"""
        sentences = ["First sentence.", "Second sentence.", "Third sentence."]
        chunks = service._create_chunks(sentences)

        for chunk in chunks:
            assert chunk.start_position >= 0
            assert chunk.end_position >= 0
            assert chunk.end_position >= chunk.start_position


class TestGetChunkingService:
    """Test get_chunking_service singleton"""

    def test_get_chunking_service_returns_instance(self):
        """Test get_chunking_service returns ChunkingService instance"""
        # Reset global instance
        import app.services.chunking.chunking_service as service
        service._chunking_service = None

        chunking_service = get_chunking_service()
        assert chunking_service is not None
        assert isinstance(chunking_service, ChunkingService)

    def test_get_chunking_service_singleton(self):
        """Test get_chunking_service returns same instance"""
        # Reset global instance
        import app.services.chunking.chunking_service as service
        service._chunking_service = None

        service1 = get_chunking_service()
        service2 = get_chunking_service()

        # Should return the same instance
        assert service1 is service2

    def test_singleton_preserves_state(self):
        """Test singleton preserves configuration"""
        import app.services.chunking.chunking_service as service
        service._chunking_service = None

        # Get service and check config
        service1 = get_chunking_service()
        original_chunk_size = service1.chunk_size

        # Get again - should have same config
        service2 = get_chunking_service()
        assert service2.chunk_size == original_chunk_size
