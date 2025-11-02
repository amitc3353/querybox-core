"""
Unit Tests for Verification Profiles - Step 11.4

Comprehensive tests for the verification profile system including:
- Profile validation
- Profile loading and caching
- All 5 preset levels (VERY_HIGH, HIGH, MEDIUM, LOW, VERY_LOW)
- Parameter ranges and consistency
- Integration with services

Based on technical documentation Section 11.4.
"""
import pytest
from unittest.mock import patch
import os

import sys
sys.path.insert(0, 'backend')

from app.core.verification_profiles import (
    VerificationProfile,
    VerificationLevel,
    get_active_profile,
    reload_profile,
    get_profile_summary,
    VERIFICATION_PROFILES,
    VERY_HIGH_PROFILE,
    HIGH_PROFILE,
    MEDIUM_PROFILE,
    LOW_PROFILE,
    VERY_LOW_PROFILE,
)


class TestVerificationProfileDataclass:
    """Test VerificationProfile dataclass validation."""

    def test_profile_creation_valid(self):
        """Test creating a valid profile."""
        profile = VerificationProfile(
            level=VerificationLevel.HIGH,
            description="Test profile",
            quote_similarity_threshold=0.85,
            quote_max_matches_per_proposition=5,
            hallucination_quote_coverage_weight=0.5,
            hallucination_verification_agreement_weight=0.3,
            hallucination_semantic_contradiction_weight=0.2,
            hallucination_flag_threshold=0.30,
            hallucination_auto_remove_threshold=0.70,
            confidence_passage_relevance_weight=0.40,
            confidence_quote_quality_weight=0.35,
            confidence_verification_agreement_weight=0.15,
            confidence_citation_count_weight=0.10,
            low_confidence_threshold=0.30,
            high_hallucination_threshold=0.70,
            verification_temperature=0.10,
            enable_contradiction_check=True,
            strict_mode=True
        )

        assert profile.level == VerificationLevel.HIGH
        assert profile.quote_similarity_threshold == 0.85
        assert profile.strict_mode is True

    def test_profile_validation_quote_threshold_out_of_range(self):
        """Test validation fails for quote threshold out of [0, 1]."""
        with pytest.raises(ValueError, match="quote_similarity_threshold must be in"):
            VerificationProfile(
                level=VerificationLevel.HIGH,
                description="Invalid",
                quote_similarity_threshold=1.5,  # Invalid
                quote_max_matches_per_proposition=5,
                hallucination_quote_coverage_weight=0.5,
                hallucination_verification_agreement_weight=0.3,
                hallucination_semantic_contradiction_weight=0.2,
                hallucination_flag_threshold=0.30,
                hallucination_auto_remove_threshold=0.70,
                confidence_passage_relevance_weight=0.40,
                confidence_quote_quality_weight=0.35,
                confidence_verification_agreement_weight=0.15,
                confidence_citation_count_weight=0.10,
                low_confidence_threshold=0.30,
                high_hallucination_threshold=0.70,
                verification_temperature=0.10,
                enable_contradiction_check=True,
                strict_mode=True
            )

    def test_profile_validation_hallucination_weights_must_sum_to_one(self):
        """Test validation fails when hallucination weights don't sum to 1.0."""
        with pytest.raises(ValueError, match="Hallucination weights must sum to 1.0"):
            VerificationProfile(
                level=VerificationLevel.HIGH,
                description="Invalid",
                quote_similarity_threshold=0.85,
                quote_max_matches_per_proposition=5,
                hallucination_quote_coverage_weight=0.6,  # Sum = 1.1 (invalid)
                hallucination_verification_agreement_weight=0.3,
                hallucination_semantic_contradiction_weight=0.2,
                hallucination_flag_threshold=0.30,
                hallucination_auto_remove_threshold=0.70,
                confidence_passage_relevance_weight=0.40,
                confidence_quote_quality_weight=0.35,
                confidence_verification_agreement_weight=0.15,
                confidence_citation_count_weight=0.10,
                low_confidence_threshold=0.30,
                high_hallucination_threshold=0.70,
                verification_temperature=0.10,
                enable_contradiction_check=True,
                strict_mode=True
            )

    def test_profile_validation_confidence_weights_must_sum_to_one(self):
        """Test validation fails when confidence weights don't sum to 1.0."""
        with pytest.raises(ValueError, match="Confidence weights must sum to 1.0"):
            VerificationProfile(
                level=VerificationLevel.HIGH,
                description="Invalid",
                quote_similarity_threshold=0.85,
                quote_max_matches_per_proposition=5,
                hallucination_quote_coverage_weight=0.5,
                hallucination_verification_agreement_weight=0.3,
                hallucination_semantic_contradiction_weight=0.2,
                hallucination_flag_threshold=0.30,
                hallucination_auto_remove_threshold=0.70,
                confidence_passage_relevance_weight=0.50,  # Sum = 1.10 (invalid)
                confidence_quote_quality_weight=0.35,
                confidence_verification_agreement_weight=0.15,
                confidence_citation_count_weight=0.10,
                low_confidence_threshold=0.30,
                high_hallucination_threshold=0.70,
                verification_temperature=0.10,
                enable_contradiction_check=True,
                strict_mode=True
            )


class TestPresetProfiles:
    """Test all 5 preset verification profiles."""

    def test_very_high_profile_parameters(self):
        """Test VERY_HIGH profile has strictest parameters."""
        profile = VERY_HIGH_PROFILE

        assert profile.level == VerificationLevel.VERY_HIGH
        assert profile.quote_similarity_threshold == 0.92  # Near-exact matches
        assert profile.hallucination_auto_remove_threshold == 0.50  # Remove early
        assert profile.low_confidence_threshold == 0.40  # High bar
        assert profile.high_hallucination_threshold == 0.60  # Low tolerance
        assert profile.verification_temperature == 0.05  # Very deterministic
        assert profile.enable_contradiction_check is True
        assert profile.strict_mode is True

    def test_high_profile_parameters(self):
        """Test HIGH profile (production default)."""
        profile = HIGH_PROFILE

        assert profile.level == VerificationLevel.HIGH
        assert profile.quote_similarity_threshold == 0.85  # Current production
        assert profile.hallucination_auto_remove_threshold == 0.70
        assert profile.low_confidence_threshold == 0.30
        assert profile.high_hallucination_threshold == 0.70
        assert profile.verification_temperature == 0.10
        assert profile.enable_contradiction_check is True
        assert profile.strict_mode is True

    def test_medium_profile_parameters(self):
        """Test MEDIUM profile (balanced)."""
        profile = MEDIUM_PROFILE

        assert profile.level == VerificationLevel.MEDIUM
        assert profile.quote_similarity_threshold == 0.75  # Allow paraphrasing
        assert profile.hallucination_auto_remove_threshold == 0.80  # More conservative
        assert profile.low_confidence_threshold == 0.25  # More lenient
        assert profile.high_hallucination_threshold == 0.75
        assert profile.verification_temperature == 0.15  # More creative
        assert profile.enable_contradiction_check is True
        assert profile.strict_mode is False  # Flag only, don't auto-remove

    def test_low_profile_parameters(self):
        """Test LOW profile (lenient)."""
        profile = LOW_PROFILE

        assert profile.level == VerificationLevel.LOW
        assert profile.quote_similarity_threshold == 0.65  # Loose matches
        assert profile.hallucination_auto_remove_threshold == 0.90  # Rarely remove
        assert profile.low_confidence_threshold == 0.20  # Answer more often
        assert profile.high_hallucination_threshold == 0.85
        assert profile.verification_temperature == 0.20
        assert profile.enable_contradiction_check is False  # Disabled for speed
        assert profile.strict_mode is False

    def test_very_low_profile_parameters(self):
        """Test VERY_LOW profile (minimal verification)."""
        profile = VERY_LOW_PROFILE

        assert profile.level == VerificationLevel.VERY_LOW
        assert profile.quote_similarity_threshold == 0.55  # Very loose
        assert profile.hallucination_auto_remove_threshold == 1.00  # Never remove
        assert profile.low_confidence_threshold == 0.15  # Almost always answer
        assert profile.high_hallucination_threshold == 0.95
        assert profile.verification_temperature == 0.30  # Most creative
        assert profile.enable_contradiction_check is False
        assert profile.strict_mode is False

    def test_all_profiles_have_valid_weights(self):
        """Test all preset profiles have valid weight sums."""
        for level, profile in VERIFICATION_PROFILES.items():
            # Check hallucination weights sum to 1.0
            hall_sum = (
                profile.hallucination_quote_coverage_weight +
                profile.hallucination_verification_agreement_weight +
                profile.hallucination_semantic_contradiction_weight
            )
            assert abs(hall_sum - 1.0) < 0.01, \
                f"{level} hallucination weights sum to {hall_sum}"

            # Check confidence weights sum to 1.0
            conf_sum = (
                profile.confidence_passage_relevance_weight +
                profile.confidence_quote_quality_weight +
                profile.confidence_verification_agreement_weight +
                profile.confidence_citation_count_weight
            )
            assert abs(conf_sum - 1.0) < 0.01, \
                f"{level} confidence weights sum to {conf_sum}"

    def test_strictness_ordering(self):
        """Test that profiles are ordered by strictness."""
        # Quote similarity thresholds should decrease from VERY_HIGH to VERY_LOW
        assert VERY_HIGH_PROFILE.quote_similarity_threshold > HIGH_PROFILE.quote_similarity_threshold
        assert HIGH_PROFILE.quote_similarity_threshold > MEDIUM_PROFILE.quote_similarity_threshold
        assert MEDIUM_PROFILE.quote_similarity_threshold > LOW_PROFILE.quote_similarity_threshold
        assert LOW_PROFILE.quote_similarity_threshold > VERY_LOW_PROFILE.quote_similarity_threshold

        # Auto-remove thresholds should increase (more lenient)
        assert VERY_HIGH_PROFILE.hallucination_auto_remove_threshold < HIGH_PROFILE.hallucination_auto_remove_threshold
        assert HIGH_PROFILE.hallucination_auto_remove_threshold < MEDIUM_PROFILE.hallucination_auto_remove_threshold
        assert MEDIUM_PROFILE.hallucination_auto_remove_threshold < LOW_PROFILE.hallucination_auto_remove_threshold
        assert LOW_PROFILE.hallucination_auto_remove_threshold < VERY_LOW_PROFILE.hallucination_auto_remove_threshold


class TestProfileLoading:
    """Test profile loading and caching."""

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "HIGH"})
    def test_get_active_profile_default(self):
        """Test loading default HIGH profile."""
        profile = reload_profile()  # Force reload to pick up env

        assert profile.level == VerificationLevel.HIGH
        assert profile == HIGH_PROFILE

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "VERY_HIGH"})
    def test_get_active_profile_very_high(self):
        """Test loading VERY_HIGH profile."""
        profile = reload_profile()

        assert profile.level == VerificationLevel.VERY_HIGH
        assert profile == VERY_HIGH_PROFILE

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "MEDIUM"})
    def test_get_active_profile_medium(self):
        """Test loading MEDIUM profile."""
        profile = reload_profile()

        assert profile.level == VerificationLevel.MEDIUM
        assert profile == MEDIUM_PROFILE

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "LOW"})
    def test_get_active_profile_low(self):
        """Test loading LOW profile."""
        profile = reload_profile()

        assert profile.level == VerificationLevel.LOW
        assert profile == LOW_PROFILE

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "VERY_LOW"})
    def test_get_active_profile_very_low(self):
        """Test loading VERY_LOW profile."""
        profile = reload_profile()

        assert profile.level == VerificationLevel.VERY_LOW
        assert profile == VERY_LOW_PROFILE

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "INVALID"})
    def test_get_active_profile_invalid_level_raises_error(self):
        """Test that invalid VERIFICATION_LEVEL raises ValueError."""
        with pytest.raises(ValueError, match="Invalid VERIFICATION_LEVEL"):
            reload_profile()

    def test_profile_caching(self):
        """Test that profile is cached after first load."""
        # First load
        profile1 = get_active_profile()

        # Second load (should be cached)
        profile2 = get_active_profile()

        # Should be the same instance
        assert profile1 is profile2

    def test_reload_profile_clears_cache(self):
        """Test that reload_profile clears cache."""
        # Load profile
        profile1 = get_active_profile()

        # Reload
        profile2 = reload_profile()

        # Should be same content but reload forces new load
        assert profile1.level == profile2.level


class TestProfileSummary:
    """Test profile summary functionality."""

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "HIGH"})
    def test_get_profile_summary_structure(self):
        """Test profile summary has correct structure."""
        reload_profile()  # Force reload
        summary = get_profile_summary()

        # Check required keys
        required_keys = [
            "level",
            "description",
            "quote_similarity_threshold",
            "hallucination_auto_remove_threshold",
            "low_confidence_threshold",
            "high_hallucination_threshold",
            "verification_temperature",
            "enable_contradiction_check",
            "strict_mode"
        ]

        for key in required_keys:
            assert key in summary, f"Missing key: {key}"

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "VERY_HIGH"})
    def test_get_profile_summary_values(self):
        """Test profile summary returns correct values."""
        reload_profile()
        summary = get_profile_summary()

        assert summary["level"] == "VERY_HIGH"
        assert summary["quote_similarity_threshold"] == 0.92
        assert summary["hallucination_auto_remove_threshold"] == 0.50
        assert summary["strict_mode"] is True


class TestProfileIntegration:
    """Test profile integration with services."""

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "VERY_HIGH"})
    def test_profile_affects_quote_matching_threshold(self):
        """Test that profile affects QuoteMatchingService threshold."""
        from app.services.verification import QuoteMatchingService

        reload_profile()
        service = QuoteMatchingService()

        # Should use VERY_HIGH threshold (0.92)
        assert service.similarity_threshold == 0.92

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "LOW"})
    def test_profile_affects_quote_matching_threshold_low(self):
        """Test LOW profile threshold in QuoteMatchingService."""
        from app.services.verification import QuoteMatchingService

        reload_profile()
        service = QuoteMatchingService()

        # Should use LOW threshold (0.65)
        assert service.similarity_threshold == 0.65

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "MEDIUM"})
    def test_profile_affects_abstention_thresholds(self):
        """Test that profile affects AbstentionService thresholds."""
        from app.services.citation_confidence.abstention_service import AbstentionService

        reload_profile()
        service = AbstentionService()

        # Should use MEDIUM thresholds
        assert service.low_confidence_threshold == 0.25
        assert service.high_hallucination_threshold == 0.75

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "HIGH"})
    def test_profile_affects_confidence_calculator_weights(self):
        """Test that profile affects ConfidenceCalculator weights."""
        from app.services.citation_confidence.confidence_calculator import ConfidenceCalculator

        reload_profile()
        calc = ConfidenceCalculator()

        # Should use HIGH weights (same as default)
        assert calc.weights.passage_relevance == 0.40
        assert calc.weights.quote_quality == 0.35
        assert calc.weights.verification_agreement == 0.15
        assert calc.weights.citation_count == 0.10

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "VERY_LOW"})
    def test_profile_disables_contradiction_check(self):
        """Test that VERY_LOW profile disables contradiction check."""
        from app.services.verification.hallucination_detector import HallucinationDetector

        reload_profile()
        detector = HallucinationDetector(ollama_client=None)

        # Should have contradiction check disabled
        assert detector.profile.enable_contradiction_check is False

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "VERY_HIGH"})
    def test_profile_enables_strict_mode(self):
        """Test that VERY_HIGH profile enables strict mode."""
        reload_profile()
        profile = get_active_profile()

        assert profile.strict_mode is True


class TestProfileEdgeCases:
    """Test edge cases and error handling."""

    def test_all_profiles_in_registry(self):
        """Test that all 5 levels are in registry."""
        assert len(VERIFICATION_PROFILES) == 5

        for level in VerificationLevel:
            assert level in VERIFICATION_PROFILES

    def test_profile_immutability(self):
        """Test that profiles are frozen (immutable)."""
        profile = HIGH_PROFILE

        # Should raise error when trying to modify
        with pytest.raises(Exception):  # dataclass frozen=True raises FrozenInstanceError
            profile.quote_similarity_threshold = 0.99

    def test_verification_level_enum_values(self):
        """Test VerificationLevel enum has correct values."""
        assert VerificationLevel.VERY_HIGH.value == "VERY_HIGH"
        assert VerificationLevel.HIGH.value == "HIGH"
        assert VerificationLevel.MEDIUM.value == "MEDIUM"
        assert VerificationLevel.LOW.value == "LOW"
        assert VerificationLevel.VERY_LOW.value == "VERY_LOW"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
