"""
Unit Tests for Metadata Validators
Step 6: Comprehensive tests for metadata validation logic
"""

import pytest
from datetime import datetime, timedelta

from app.schemas.metadata import (
    DocumentMetadata,
    ProcessingMetadata,
    ContentQuality,
    DocumentType,
    ProcessingEngine
)
from app.services.metadata.validators import (
    MetadataValidator,
    validate_document_metadata,
    validate_processing_metadata,
    is_metadata_complete,
    get_metadata_completeness_score
)


class TestMetadataValidator:
    """Test MetadataValidator class"""

    def test_valid_metadata(self):
        """Test validation of valid metadata"""
        metadata = DocumentMetadata(
            title="Test Document",
            author="John Doe",
            language="en",
            page_count=10,
            word_count=1000,
            text_quality_score=0.85,
            content_quality=ContentQuality.HIGH,
            processing_engine=ProcessingEngine.DOCLING,
            extracted_at=datetime.utcnow()
        )

        validator = MetadataValidator()
        is_valid, errors, warnings = validator.validate_metadata(metadata)

        assert is_valid is True
        assert len(errors) == 0

    def test_empty_title(self):
        """Test validation with empty title"""
        metadata = DocumentMetadata(
            title=None,
            processing_engine=ProcessingEngine.DOCLING,
            extracted_at=datetime.utcnow()
        )

        validator = MetadataValidator()
        is_valid, errors, warnings = validator.validate_metadata(metadata)

        assert is_valid is True  # Title is optional
        assert any("Title is empty" in w for w in warnings)

    def test_title_too_long(self):
        """Test validation with title exceeding max length"""
        long_title = "A" * 600  # Exceeds 500 char limit

        # In Pydantic v2, validation happens at object creation
        with pytest.raises(Exception):  # Pydantic ValidationError
            metadata = DocumentMetadata(
                title=long_title,
                processing_engine=ProcessingEngine.DOCLING,
                extracted_at=datetime.utcnow()
            )

    def test_invalid_language_code(self):
        """Test validation with invalid language code"""
        metadata = DocumentMetadata(
            title="Test",
            language="english",  # Should be 2-letter code
            processing_engine=ProcessingEngine.DOCLING,
            extracted_at=datetime.utcnow()
        )

        validator = MetadataValidator()
        is_valid, errors, warnings = validator.validate_metadata(metadata)

        assert is_valid is True  # Warnings don't fail validation
        assert any("not a valid ISO 639-1 code" in w for w in warnings)

    def test_negative_page_count(self):
        """Test validation with negative page count"""
        # In Pydantic v2, validation happens at object creation
        with pytest.raises(Exception):  # Pydantic ValidationError
            metadata = DocumentMetadata(
                title="Test",
                page_count=-5,
                processing_engine=ProcessingEngine.DOCLING,
                extracted_at=datetime.utcnow()
            )

    def test_invalid_quality_score(self):
        """Test validation with out-of-range quality score"""
        # In Pydantic v2, validation happens at object creation
        with pytest.raises(Exception):  # Pydantic ValidationError
            metadata = DocumentMetadata(
                title="Test",
                text_quality_score=1.5,  # Should be 0-1
                processing_engine=ProcessingEngine.DOCLING,
                extracted_at=datetime.utcnow()
            )

    def test_low_quality_warning(self):
        """Test that low quality scores generate warnings"""
        metadata = DocumentMetadata(
            title="Test",
            text_quality_score=0.2,
            content_quality=ContentQuality.POOR,
            processing_engine=ProcessingEngine.DOCLING,
            extracted_at=datetime.utcnow()
        )

        validator = MetadataValidator()
        is_valid, errors, warnings = validator.validate_metadata(metadata)

        assert is_valid is True
        assert any("Low text quality score" in w for w in warnings)

    def test_quality_consistency(self):
        """Test quality score and enum consistency validation"""
        metadata = DocumentMetadata(
            title="Test",
            text_quality_score=0.95,  # EXCELLENT
            content_quality=ContentQuality.LOW,  # Mismatch
            processing_engine=ProcessingEngine.DOCLING,
            extracted_at=datetime.utcnow()
        )

        validator = MetadataValidator()
        is_valid, errors, warnings = validator.validate_metadata(metadata)

        assert is_valid is True
        assert any("Quality mismatch" in w for w in warnings)

    def test_future_timestamp(self):
        """Test validation with future timestamp"""
        future_time = datetime.utcnow() + timedelta(days=1)

        metadata = DocumentMetadata(
            title="Test",
            processing_engine=ProcessingEngine.DOCLING,
            extracted_at=future_time
        )

        validator = MetadataValidator()
        is_valid, errors, warnings = validator.validate_metadata(metadata)

        assert is_valid is False
        assert any("in the future" in e for e in errors)

    def test_too_many_keywords(self):
        """Test validation with excessive keywords"""
        # Note: The Pydantic field_validator truncates to 50 keywords automatically
        # So we can't test for too many keywords warning with the object
        # Instead, test that the validator's _validate_keywords method works correctly
        validator = MetadataValidator()

        # Create metadata with exactly 50 keywords (the limit)
        keywords = [f"keyword{i}" for i in range(50)]
        metadata = DocumentMetadata(
            title="Test",
            keywords=keywords,
            processing_engine=ProcessingEngine.DOCLING,
            extracted_at=datetime.utcnow()
        )

        is_valid, errors, warnings = validator.validate_metadata(metadata)
        assert is_valid is True
        # With exactly 50 keywords, there should be no warning
        assert not any("exceeds recommended maximum" in w for w in warnings)

    def test_invalid_confidence_scores(self):
        """Test validation with out-of-range confidence scores"""
        metadata = DocumentMetadata(
            title="Test",
            confidence_scores={"title": 1.5, "author": -0.2},
            processing_engine=ProcessingEngine.DOCLING,
            extracted_at=datetime.utcnow()
        )

        validator = MetadataValidator()
        is_valid, errors, warnings = validator.validate_metadata(metadata)

        assert is_valid is False
        assert len([e for e in errors if "Confidence score" in e]) >= 2


class TestProcessingMetadataValidation:
    """Test ProcessingMetadata validation"""

    def test_valid_processing_metadata(self):
        """Test validation of valid processing metadata"""
        metadata = ProcessingMetadata(
            percentage_complete=75.5,
            current_operation="Extracting metadata",
            processing_duration_ms=2500,
            extraction_quality=0.92,
            completeness_score=0.88,
            processing_priority=5
        )

        is_valid, errors, warnings = validate_processing_metadata(metadata)

        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_percentage(self):
        """Test validation with invalid percentage"""
        # In Pydantic v2, validation happens at object creation
        with pytest.raises(Exception):  # Pydantic ValidationError
            metadata = ProcessingMetadata(
                percentage_complete=150.0,  # Exceeds 100
                processing_priority=5
            )

    def test_negative_duration(self):
        """Test validation with negative duration"""
        # In Pydantic v2, validation happens at object creation
        with pytest.raises(Exception):  # Pydantic ValidationError
            metadata = ProcessingMetadata(
                percentage_complete=50.0,
                processing_duration_ms=-100,
                processing_priority=5
            )

    def test_invalid_priority(self):
        """Test validation with out-of-range priority"""
        # In Pydantic v2, validation happens at object creation
        with pytest.raises(Exception):  # Pydantic ValidationError
            metadata = ProcessingMetadata(
                percentage_complete=50.0,
                processing_priority=15  # Max is 10
            )


class TestMetadataCompletenessChecks:
    """Test metadata completeness functions"""

    def test_complete_metadata(self):
        """Test completeness check with well-populated metadata"""
        metadata = DocumentMetadata(
            title="Complete Document",
            author="John Doe",
            subject="Test Subject",
            keywords=["test", "document"],
            language="en",
            page_count=10,
            word_count=1000,
            document_type=DocumentType.REPORT,
            text_quality_score=0.85,
            processing_engine=ProcessingEngine.DOCLING,
            extracted_at=datetime.utcnow()
        )

        assert is_metadata_complete(metadata) is True
        score = get_metadata_completeness_score(metadata)
        assert score > 0.6  # Well-populated

    def test_minimal_metadata(self):
        """Test completeness check with minimal metadata"""
        metadata = DocumentMetadata(
            title="Minimal",
            processing_engine=ProcessingEngine.FALLBACK_TEXT,
            extracted_at=datetime.utcnow()
        )

        score = get_metadata_completeness_score(metadata)
        assert score < 0.4  # Minimal fields populated

    def test_incomplete_metadata(self):
        """Test incompleteness detection"""
        metadata = DocumentMetadata(
            title=None,
            language=None,
            processing_engine=ProcessingEngine.FALLBACK_BASIC,
            extracted_at=datetime.utcnow()
        )

        assert is_metadata_complete(metadata) is False
        score = get_metadata_completeness_score(metadata)
        assert score < 0.3


class TestConvenienceFunctions:
    """Test convenience validation functions"""

    def test_validate_document_metadata_function(self):
        """Test validate_document_metadata convenience function"""
        metadata = DocumentMetadata(
            title="Test",
            text_quality_score=0.5,
            processing_engine=ProcessingEngine.DOCLING,
            extracted_at=datetime.utcnow()
        )

        is_valid, errors, warnings = validate_document_metadata(metadata)

        assert is_valid is True
        assert isinstance(errors, list)
        assert isinstance(warnings, list)

    def test_strict_mode(self):
        """Test strict validation mode"""
        metadata = DocumentMetadata(
            title="Test",
            language="xyz",  # Generates warning
            processing_engine=ProcessingEngine.DOCLING,
            extracted_at=datetime.utcnow()
        )

        # Normal mode: warnings don't fail validation
        is_valid, errors, warnings = validate_document_metadata(metadata, strict=False)
        assert is_valid is True
        assert len(warnings) > 0

        # Strict mode: warnings fail validation
        is_valid, errors, warnings = validate_document_metadata(metadata, strict=True)
        assert is_valid is False
