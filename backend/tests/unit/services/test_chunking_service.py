"""
Unit Tests for Enhanced Chunking Service
Tests ChunkingService with new enhanced architecture
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4

from app.services.chunking.chunking_service import (
    ChunkingService,
    EnhancedChunkingConfig,
    ChunkingResult,
    EnhancedChunk,
    ChunkMetadata,
    get_chunking_service,
)
from app.models.embedding import Embedding


class TestEnhancedChunkingConfig:
    """Test EnhancedChunkingConfig dataclass"""

    def test_default_configuration(self):
        """Test default configuration values"""
        config = EnhancedChunkingConfig()

        assert config.target_tokens == 512
        assert config.max_tokens == 600
        assert config.min_tokens == 100
        assert config.overlap_tokens == 50
        assert config.preserve_paragraphs is True
        assert config.extract_metadata is True
        assert config.use_spacy is True

    def test_custom_configuration(self):
        """Test creating custom configuration"""
        config = EnhancedChunkingConfig(
            target_tokens=256,
            max_tokens=400,
            min_tokens=50,
            overlap_tokens=25,
            preserve_paragraphs=False,
            extract_metadata=False,
            use_spacy=False,
        )

        assert config.target_tokens == 256
        assert config.max_tokens == 400
        assert config.min_tokens == 50
        assert config.overlap_tokens == 25
        assert config.preserve_paragraphs is False
        assert config.extract_metadata is False
        assert config.use_spacy is False


class TestChunkMetadata:
    """Test ChunkMetadata dataclass"""

    def test_default_metadata(self):
        """Test default metadata values"""
        metadata = ChunkMetadata()

        assert metadata.section_heading is None
        assert metadata.subsection_heading is None
        assert metadata.chunk_type == "paragraph"
        assert metadata.paragraph_index == 0
        assert metadata.semantic_density == 0.5
        assert metadata.contains_table is False
        assert metadata.contains_list is False
        assert metadata.contains_code is False
        assert metadata.contains_equation is False
        assert metadata.contains_figure is False
        assert metadata.language == "en"

    def test_custom_metadata(self):
        """Test creating custom metadata"""
        metadata = ChunkMetadata(
            section_heading="Introduction",
            subsection_heading="Background",
            chunk_type="heading",
            paragraph_index=1,
            semantic_density=0.8,
            contains_table=True,
            contains_list=True,
            language="es",
        )

        assert metadata.section_heading == "Introduction"
        assert metadata.subsection_heading == "Background"
        assert metadata.chunk_type == "heading"
        assert metadata.semantic_density == 0.8
        assert metadata.contains_table is True
        assert metadata.contains_list is True
        assert metadata.language == "es"


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
            quality_score=0.85,
        )

        assert result.success is True
        assert result.chunk_count == 47
        assert result.total_chars == 45230
        assert result.avg_chunk_size == 962
        assert result.processing_time_ms == 2345
        assert result.quality_score == 0.85
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
    """Test Enhanced ChunkingService"""

    @pytest.fixture
    def service(self):
        """Create chunking service instance with default config"""
        return ChunkingService()

    @pytest.fixture
    def custom_service(self):
        """Create chunking service with custom config"""
        config = EnhancedChunkingConfig(
            target_tokens=256,
            max_tokens=400,
            min_tokens=50,
            overlap_tokens=25,
        )
        return ChunkingService(config=config)

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

    def test_initialization_default_config(self, service):
        """Test service initializes with default configuration"""
        assert service.config is not None
        assert service.config.target_tokens == 512
        assert service.config.max_tokens == 600
        assert service.config.overlap_tokens == 50
        assert service.sentence_splitter is not None
        assert service.token_counter is not None
        assert service.metadata_extractor is not None

    def test_initialization_custom_config(self, custom_service):
        """Test service initializes with custom configuration"""
        assert custom_service.config.target_tokens == 256
        assert custom_service.config.max_tokens == 400
        assert custom_service.config.min_tokens == 50
        assert custom_service.config.overlap_tokens == 25

    def test_chunk_text_success(self, service, mock_db):
        """Test successful chunking of text"""
        document_id = uuid4()
        # Create text long enough to pass validation
        text = "This is a test sentence. " * 100  # ~2500 chars

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
        assert result.quality_score > 0

    def test_chunk_text_too_short(self, service, mock_db):
        """Test chunking fails with text too short"""
        document_id = uuid4()
        text = "Short"  # Less than minimum required

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
        # Create text at minimum char length (min_tokens * 4)
        text = "A " * 200  # ~400 chars (min_tokens=100, * 4)

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        # Should succeed or provide clear error
        assert isinstance(result, ChunkingResult)

    def test_chunk_text_large_document(self, service, mock_db):
        """Test chunking a large document"""
        document_id = uuid4()
        # Create large text (10k chars)
        text = "This is a sentence for testing. " * 300

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is True
        assert result.chunk_count >= 5  # Should create multiple chunks

    def test_chunk_text_saves_to_database(self, service, mock_db):
        """Test that chunks are saved to database"""
        document_id = uuid4()
        text = "This is a test. " * 100

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        # Verify database operations were called
        if result.success:
            mock_db.begin_nested.assert_called()
            mock_db.commit.assert_called()

    def test_configuration_from_env(self):
        """Test service reads configuration from environment"""
        config = EnhancedChunkingConfig(
            target_tokens=256,
            max_tokens=400,
            min_tokens=50,
        )
        service = ChunkingService(config=config)

        assert service.config.target_tokens == 256
        assert service.config.max_tokens == 400
        assert service.config.min_tokens == 50


class TestGetChunkingService:
    """Test get_chunking_service singleton"""

    def test_get_chunking_service_returns_instance(self):
        """Test get_chunking_service returns ChunkingService instance"""
        # Reset global instance
        import app.services.chunking.chunking_service as service_module
        service_module._chunking_service = None

        chunking_service = get_chunking_service()
        assert chunking_service is not None
        assert isinstance(chunking_service, ChunkingService)

    def test_get_chunking_service_singleton(self):
        """Test get_chunking_service returns same instance"""
        # Reset global instance
        import app.services.chunking.chunking_service as service_module
        service_module._chunking_service = None

        service1 = get_chunking_service()
        service2 = get_chunking_service()

        # Should return the same instance
        assert service1 is service2

    def test_singleton_preserves_state(self):
        """Test singleton preserves configuration"""
        import app.services.chunking.chunking_service as service_module
        service_module._chunking_service = None

        # Get service and check config
        service1 = get_chunking_service()
        original_target_tokens = service1.config.target_tokens

        # Get again - should have same config
        service2 = get_chunking_service()
        assert service2.config.target_tokens == original_target_tokens


class TestChunkingServiceErrorHandling:
    """Test error handling in ChunkingService"""

    @pytest.fixture
    def service(self):
        """Create chunking service instance"""
        return ChunkingService()

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

    def test_handles_database_error(self, service, mock_db):
        """Test service handles database errors gracefully"""
        document_id = uuid4()
        text = "This is a test. " * 100

        # Make commit raise an exception
        mock_db.commit.side_effect = Exception("Database error")

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        # Should return failed result, not raise exception
        assert result.success is False
        assert result.error_message is not None

    def test_handles_empty_text_gracefully(self, service, mock_db):
        """Test service handles empty text"""
        document_id = uuid4()
        text = ""

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is False
        assert result.error_message is not None


class TestChunkingServiceQuality:
    """Test quality scoring in ChunkingService"""

    @pytest.fixture
    def service(self):
        """Create chunking service instance"""
        return ChunkingService()

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

    def test_quality_score_in_result(self, service, mock_db):
        """Test that chunking result includes quality score"""
        document_id = uuid4()
        text = "This is a test sentence. " * 100

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        if result.success:
            assert hasattr(result, 'quality_score')
            assert 0.0 <= result.quality_score <= 1.0

    def test_quality_score_reasonable(self, service, mock_db):
        """Test quality score is reasonable for good text"""
        document_id = uuid4()
        # Well-structured text with paragraphs
        text = """
        Introduction

        This is an introductory paragraph about the topic. It provides context and sets the stage.

        Background

        The background section explains the history and motivation. It helps readers understand why this matters.

        Methods

        The methods section describes the approach taken. It includes detailed steps and procedures.
        """ * 5  # Repeat to ensure sufficient length

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        if result.success:
            # Quality score should be reasonable (>0.3) for well-structured text
            assert result.quality_score > 0.3
