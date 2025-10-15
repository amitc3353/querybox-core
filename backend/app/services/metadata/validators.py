"""
Metadata Validators
Step 6: Validation utilities for metadata fields and quality checks

Provides comprehensive validation for extracted metadata to ensure
data integrity and quality standards.
"""

import re
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.schemas.metadata import (
    DocumentMetadata,
    ProcessingMetadata,
    ContentQuality,
    DocumentType,
    ProcessingEngine
)


logger = logging.getLogger(__name__)


class MetadataValidationError(Exception):
    """Raised when metadata validation fails"""
    pass


class MetadataValidator:
    """
    Validates metadata fields and enforces quality standards.

    Performs validation on extracted metadata to ensure consistency,
    completeness, and compliance with schema requirements.
    """

    # Valid language codes (ISO 639-1)
    VALID_LANGUAGE_CODES = {
        'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'zh', 'ko',
        'ar', 'hi', 'nl', 'sv', 'pl', 'tr', 'vi', 'th', 'id', 'cs'
    }

    # Minimum quality scores
    MIN_TEXT_QUALITY_SCORE = 0.0
    MAX_TEXT_QUALITY_SCORE = 1.0

    # Field length limits
    MAX_TITLE_LENGTH = 500
    MAX_AUTHOR_LENGTH = 200
    MAX_SUBJECT_LENGTH = 500
    MAX_KEYWORD_LENGTH = 100
    MAX_KEYWORDS_COUNT = 50

    def __init__(self):
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []

    def validate_metadata(
        self,
        metadata: DocumentMetadata,
        strict: bool = False
    ) -> tuple[bool, List[str], List[str]]:
        """
        Validate DocumentMetadata instance.

        Args:
            metadata: DocumentMetadata to validate
            strict: If True, warnings are treated as errors

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.validation_errors = []
        self.validation_warnings = []

        # Validate individual fields
        self._validate_title(metadata.title)
        self._validate_author(metadata.author)
        self._validate_subject(metadata.subject)
        self._validate_keywords(metadata.keywords)
        self._validate_language(metadata.language)
        self._validate_page_count(metadata.page_count)
        self._validate_word_count(metadata.word_count)
        self._validate_quality_score(metadata.text_quality_score)
        self._validate_confidence_scores(metadata.confidence_scores)
        self._validate_timestamps(metadata.extracted_at)

        # Validate consistency
        self._validate_quality_consistency(metadata)

        is_valid = len(self.validation_errors) == 0
        if strict:
            is_valid = is_valid and len(self.validation_warnings) == 0

        return is_valid, self.validation_errors, self.validation_warnings

    def validate_processing_metadata(
        self,
        metadata: ProcessingMetadata
    ) -> tuple[bool, List[str], List[str]]:
        """
        Validate ProcessingMetadata instance.

        Args:
            metadata: ProcessingMetadata to validate

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        self.validation_errors = []
        self.validation_warnings = []

        # Validate percentage
        if metadata.percentage_complete < 0.0 or metadata.percentage_complete > 100.0:
            self.validation_errors.append(
                f"Invalid percentage_complete: {metadata.percentage_complete}. Must be 0-100."
            )

        # Validate duration
        if metadata.processing_duration_ms is not None and metadata.processing_duration_ms < 0:
            self.validation_errors.append(
                f"Invalid processing_duration_ms: {metadata.processing_duration_ms}. Must be >= 0."
            )

        # Validate quality scores
        if metadata.extraction_quality is not None:
            if metadata.extraction_quality < 0.0 or metadata.extraction_quality > 1.0:
                self.validation_errors.append(
                    f"Invalid extraction_quality: {metadata.extraction_quality}. Must be 0-1."
                )

        if metadata.completeness_score is not None:
            if metadata.completeness_score < 0.0 or metadata.completeness_score > 1.0:
                self.validation_errors.append(
                    f"Invalid completeness_score: {metadata.completeness_score}. Must be 0-1."
                )

        # Validate priority
        if metadata.processing_priority < 1 or metadata.processing_priority > 10:
            self.validation_errors.append(
                f"Invalid processing_priority: {metadata.processing_priority}. Must be 1-10."
            )

        is_valid = len(self.validation_errors) == 0
        return is_valid, self.validation_errors, self.validation_warnings

    def _validate_title(self, title: Optional[str]) -> None:
        """Validate title field"""
        if not title:
            self.validation_warnings.append("Title is empty or missing")
            return

        if len(title) > self.MAX_TITLE_LENGTH:
            self.validation_errors.append(
                f"Title exceeds maximum length of {self.MAX_TITLE_LENGTH} characters"
            )

        # Check for suspicious patterns
        if title.strip() == "":
            self.validation_warnings.append("Title contains only whitespace")

        if re.match(r'^[0-9\-_]+$', title):
            self.validation_warnings.append("Title appears to be a filename or ID")

    def _validate_author(self, author: Optional[str]) -> None:
        """Validate author field"""
        if not author:
            return  # Author is optional

        if len(author) > self.MAX_AUTHOR_LENGTH:
            self.validation_errors.append(
                f"Author exceeds maximum length of {self.MAX_AUTHOR_LENGTH} characters"
            )

    def _validate_subject(self, subject: Optional[str]) -> None:
        """Validate subject field"""
        if not subject:
            return  # Subject is optional

        if len(subject) > self.MAX_SUBJECT_LENGTH:
            self.validation_errors.append(
                f"Subject exceeds maximum length of {self.MAX_SUBJECT_LENGTH} characters"
            )

    def _validate_keywords(self, keywords: List[str]) -> None:
        """Validate keywords list"""
        if not keywords:
            self.validation_warnings.append("No keywords extracted")
            return

        if len(keywords) > self.MAX_KEYWORDS_COUNT:
            self.validation_warnings.append(
                f"Keyword count ({len(keywords)}) exceeds recommended maximum of {self.MAX_KEYWORDS_COUNT}"
            )

        # Validate individual keywords
        for keyword in keywords:
            if not keyword or not keyword.strip():
                self.validation_errors.append("Empty keyword found in list")
                continue

            if len(keyword) > self.MAX_KEYWORD_LENGTH:
                self.validation_errors.append(
                    f"Keyword '{keyword[:50]}...' exceeds maximum length of {self.MAX_KEYWORD_LENGTH}"
                )

    def _validate_language(self, language: Optional[str]) -> None:
        """Validate language code"""
        if not language:
            self.validation_warnings.append("Language not detected")
            return

        # Check if it's a valid ISO 639-1 code
        if len(language) != 2:
            self.validation_warnings.append(
                f"Language code '{language}' is not a valid ISO 639-1 code (should be 2 characters)"
            )
        elif language.lower() not in self.VALID_LANGUAGE_CODES:
            self.validation_warnings.append(
                f"Language code '{language}' is not in common language set"
            )

    def _validate_page_count(self, page_count: Optional[int]) -> None:
        """Validate page count"""
        if page_count is None:
            return  # Optional field

        if page_count < 0:
            self.validation_errors.append(
                f"Invalid page_count: {page_count}. Must be >= 0."
            )

        if page_count == 0:
            self.validation_warnings.append("Page count is zero")

        if page_count > 10000:
            self.validation_warnings.append(
                f"Unusually high page count: {page_count}"
            )

    def _validate_word_count(self, word_count: Optional[int]) -> None:
        """Validate word count"""
        if word_count is None:
            return  # Optional field

        if word_count < 0:
            self.validation_errors.append(
                f"Invalid word_count: {word_count}. Must be >= 0."
            )

        if word_count == 0:
            self.validation_warnings.append("Word count is zero - possible empty document")

    def _validate_quality_score(self, score: Optional[float]) -> None:
        """Validate text quality score"""
        if score is None:
            return  # Optional field

        if score < self.MIN_TEXT_QUALITY_SCORE or score > self.MAX_TEXT_QUALITY_SCORE:
            self.validation_errors.append(
                f"Invalid text_quality_score: {score}. Must be between 0.0 and 1.0."
            )

        if score < 0.3:
            self.validation_warnings.append(
                f"Low text quality score: {score:.2f}"
            )

    def _validate_confidence_scores(self, scores: Dict[str, float]) -> None:
        """Validate confidence scores dictionary"""
        if not scores:
            self.validation_warnings.append("No confidence scores provided")
            return

        for field, score in scores.items():
            if not isinstance(score, (int, float)):
                self.validation_errors.append(
                    f"Confidence score for '{field}' is not numeric: {type(score)}"
                )
                continue

            if score < 0.0 or score > 1.0:
                self.validation_errors.append(
                    f"Confidence score for '{field}' out of range: {score}"
                )

            if score < 0.3:
                self.validation_warnings.append(
                    f"Low confidence score for '{field}': {score:.2f}"
                )

    def _validate_timestamps(self, extracted_at: datetime) -> None:
        """Validate timestamp fields"""
        if not extracted_at:
            self.validation_errors.append("Missing extracted_at timestamp")
            return

        # Check if timestamp is in the future
        now = datetime.utcnow()
        if extracted_at > now:
            self.validation_errors.append(
                f"Extracted timestamp is in the future: {extracted_at.isoformat()}"
            )

    def _validate_quality_consistency(self, metadata: DocumentMetadata) -> None:
        """Validate consistency between quality score and quality enum"""
        if metadata.text_quality_score is None:
            return

        score = metadata.text_quality_score
        quality = metadata.content_quality

        # Check if enum matches score
        expected_quality = None
        if score >= 0.9:
            expected_quality = ContentQuality.EXCELLENT
        elif score >= 0.7:
            expected_quality = ContentQuality.HIGH
        elif score >= 0.5:
            expected_quality = ContentQuality.MEDIUM
        elif score >= 0.3:
            expected_quality = ContentQuality.LOW
        else:
            expected_quality = ContentQuality.POOR

        if quality != expected_quality:
            # Note: In Pydantic v2 with use_enum_values=True, enums are already strings
            expected_str = expected_quality.value if hasattr(expected_quality, 'value') else str(expected_quality)
            quality_str = quality.value if hasattr(quality, 'value') else str(quality)
            self.validation_warnings.append(
                f"Quality mismatch: score {score:.2f} suggests '{expected_str}' "
                f"but set to '{quality_str}'"
            )


# Global validator instance
_metadata_validator: Optional[MetadataValidator] = None


def get_metadata_validator() -> MetadataValidator:
    """Get or create global metadata validator instance"""
    global _metadata_validator
    if _metadata_validator is None:
        _metadata_validator = MetadataValidator()
    return _metadata_validator


def validate_document_metadata(
    metadata: DocumentMetadata,
    strict: bool = False
) -> tuple[bool, List[str], List[str]]:
    """
    Convenience function to validate DocumentMetadata.

    Args:
        metadata: DocumentMetadata to validate
        strict: If True, warnings are treated as errors

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    validator = get_metadata_validator()
    return validator.validate_metadata(metadata, strict=strict)


def validate_processing_metadata(
    metadata: ProcessingMetadata
) -> tuple[bool, List[str], List[str]]:
    """
    Convenience function to validate ProcessingMetadata.

    Args:
        metadata: ProcessingMetadata to validate

    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    validator = get_metadata_validator()
    return validator.validate_processing_metadata(metadata)


def is_metadata_complete(metadata: DocumentMetadata) -> bool:
    """
    Check if metadata is reasonably complete.

    Args:
        metadata: DocumentMetadata to check

    Returns:
        True if metadata has essential fields populated
    """
    required_fields = [
        metadata.title is not None,
        metadata.language is not None,
        metadata.page_count is not None or metadata.word_count is not None
    ]

    return sum(required_fields) >= 2  # At least 2 of 3 required fields


def get_metadata_completeness_score(metadata: DocumentMetadata) -> float:
    """
    Calculate completeness score for metadata (0.0-1.0).

    Args:
        metadata: DocumentMetadata to score

    Returns:
        Completeness score between 0.0 and 1.0
    """
    total_fields = 15  # Total number of important fields
    populated_fields = 0

    # Check each field
    if metadata.title:
        populated_fields += 1
    if metadata.author:
        populated_fields += 1
    if metadata.subject:
        populated_fields += 1
    if metadata.keywords:
        populated_fields += 1
    if metadata.creator_application:
        populated_fields += 1
    if metadata.page_count is not None:
        populated_fields += 1
    if metadata.word_count is not None:
        populated_fields += 1
    if metadata.character_count is not None:
        populated_fields += 1
    if metadata.language:
        populated_fields += 1
    if metadata.document_type:
        populated_fields += 1
    if metadata.text_quality_score is not None:
        populated_fields += 1
    if metadata.has_images is not None:
        populated_fields += 1
    if metadata.has_tables is not None:
        populated_fields += 1
    if metadata.confidence_scores:
        populated_fields += 1
    if metadata.extracted_at:
        populated_fields += 1

    return populated_fields / total_fields
