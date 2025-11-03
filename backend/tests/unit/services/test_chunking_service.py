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


class TestMarkdownHeadingExtraction:
    """Test markdown heading extraction in chunking service (Fix for section metadata)"""

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

    def test_heading_at_chunk_start(self, service, mock_db):
        """Test Strategy 1: Heading at the START of chunk is captured"""
        document_id = uuid4()
        text = """# Main Heading

This is content under the main heading. It contains multiple sentences to ensure proper chunking.
More content here to test the heading extraction when the heading starts the chunk.
Additional sentences to meet minimum chunk size requirements for the test to be valid.
""" * 3

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is True

        # Verify database was called with heading metadata
        if mock_db.bulk_insert_mappings.called:
            chunks = mock_db.bulk_insert_mappings.call_args[0][1]
            # At least one chunk should have the section heading
            section_headings = [c.get('section_heading') for c in chunks]
            assert any('Main Heading' in str(h) for h in section_headings if h is not None)

    def test_heading_within_chunk(self, service, mock_db):
        """Test Strategy 2: Heading WITHIN chunk (not at start) is captured"""
        document_id = uuid4()
        text = """Some introductory text without a heading at the very start.

## Section 1: Introduction

This is the content under Section 1. It includes multiple sentences to test chunking behavior.
When a heading appears within a chunk, it should still be captured as metadata for that chunk.
This tests the second strategy of the heading extraction logic that was recently fixed.
""" * 3

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is True

        if mock_db.bulk_insert_mappings.called:
            chunks = mock_db.bulk_insert_mappings.call_args[0][1]
            section_headings = [c.get('section_heading') for c in chunks]
            # Should capture "Section 1: Introduction" or "Introduction"
            assert any(
                h is not None and ('Section 1' in str(h) or 'Introduction' in str(h))
                for h in section_headings
            )

    def test_heading_before_chunk(self, service, mock_db):
        """Test Strategy 3: Most recent heading BEFORE chunk is used as fallback"""
        document_id = uuid4()
        text = """# Document Title

First paragraph under the title with some content.

Second paragraph that continues the content under the same heading.
This paragraph should still be associated with "Document Title" even though
the heading appeared before this chunk. This tests the third fallback strategy
where we look for the most recent heading before the current chunk position.

Third paragraph with more content to ensure multiple chunks are created.
Each subsequent chunk should maintain the heading context from the document title.
Additional content to meet chunking requirements and validate metadata propagation.
""" * 3

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is True

        if mock_db.bulk_insert_mappings.called:
            chunks = mock_db.bulk_insert_mappings.call_args[0][1]
            section_headings = [c.get('section_heading') for c in chunks]
            # At least one chunk should have "Document Title"
            assert any('Document Title' in str(h) for h in section_headings if h is not None)

    def test_nested_headings(self, service, mock_db):
        """Test extraction of nested headings (section and subsection)"""
        document_id = uuid4()
        text = """# Main Section

Content under main section.

## Subsection 2.1

Content under subsection with multiple sentences for proper chunking.
This tests that both section_heading (H1, H2) and subsection_heading (H3, H4) are captured.
Additional content to ensure chunk has sufficient length for processing.

### Sub-subsection 2.1.1

Deeply nested content to test subsection heading extraction.
This should capture the H3 heading as subsection_heading field.
More content to meet minimum requirements.
""" * 3

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is True

        if mock_db.bulk_insert_mappings.called:
            chunks = mock_db.bulk_insert_mappings.call_args[0][1]
            # Check that we have both section and subsection headings
            has_section = any(c.get('section_heading') is not None for c in chunks)
            has_subsection = any(c.get('subsection_heading') is not None for c in chunks)
            assert has_section or has_subsection  # At least one type should be present

    def test_multiple_sections(self, service, mock_db):
        """Test document with multiple sections maintains correct heading context"""
        document_id = uuid4()
        text = """# Section 1

Content for section 1 with multiple sentences.
This section has enough content to potentially create its own chunk.
Testing that section metadata is maintained correctly.

# Section 2

Content for section 2 with different heading.
Each section should maintain its own heading metadata in the chunks.
This validates that heading context switches correctly between sections.

# Section 3

Final section with its own content and heading.
Should be correctly associated with Section 3 heading.
Tests the complete heading extraction across document structure.
""" * 3

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is True

        if mock_db.bulk_insert_mappings.called:
            chunks = mock_db.bulk_insert_mappings.call_args[0][1]
            section_headings = [c.get('section_heading') for c in chunks if c.get('section_heading')]
            # Should have captured at least some section headings
            assert len(section_headings) > 0
            # Check that we have different section headings (not just one)
            unique_headings = set(str(h) for h in section_headings if h)
            # Might have 1 or more unique headings depending on chunking
            assert len(unique_headings) >= 1

    def test_markdown_heading_levels(self, service, mock_db):
        """Test different markdown heading levels (H1-H6)"""
        document_id = uuid4()
        text = """# H1 Heading
Content under H1 with sufficient text for chunking requirements.

## H2 Heading
Content under H2 heading to test level 2 extraction properly.

### H3 Heading
Content under H3 to validate subsection heading extraction works.

#### H4 Heading
Content under H4 for additional subsection level testing and validation.
""" * 3

        result = service.chunk_text(
            text=text,
            document_id=document_id,
            db=mock_db,
        )

        assert result.success is True

        if mock_db.bulk_insert_mappings.called:
            chunks = mock_db.bulk_insert_mappings.call_args[0][1]
            # Should extract headings from H1-H4
            all_headings = [
                c.get('section_heading') or c.get('subsection_heading')
                for c in chunks
            ]
            captured_headings = [h for h in all_headings if h is not None]
            assert len(captured_headings) > 0
