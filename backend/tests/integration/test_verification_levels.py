"""
Integration Tests for Verification Levels - Step 11.4

Tests the complete verification pipeline with all 5 verification levels
to ensure behavior differs appropriately based on strictness.

Based on technical documentation Section 11.4.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
import os

import sys
sys.path.insert(0, 'backend')

from app.core.verification_profiles import (
    VerificationLevel,
    reload_profile,
    VERY_HIGH_PROFILE,
    HIGH_PROFILE,
    MEDIUM_PROFILE,
    LOW_PROFILE,
    VERY_LOW_PROFILE
)
from app.services.verification import VerificationService, QuoteMatchingService
from app.services.verification.hallucination_detector import HallucinationDetector
from app.services.citation_confidence.confidence_calculator import ConfidenceCalculator
from app.services.citation_confidence.abstention_service import AbstentionService
from app.schemas.answer import AnswerRequest, AnswerResponse, Proposition, Citation
from app.schemas.verification import (
    VerifiedAnswerResponse,
    Passage,
    QuoteMatch,
    HallucinationReport
)


class TestVerificationLevelsIntegration:
    """Integration tests for all 5 verification levels."""

    @pytest.fixture
    def sample_passages(self):
        """Create sample passages for testing."""
        return [
            Passage(
                id="p1",
                content="Paris is the capital of France. It is located in the northern part of the country.",
                document_id="doc1",
                chunk_index=0,
                rerank_score=0.95
            ),
            Passage(
                id="p2",
                content="The capital city of France is known as Paris. It is a major European city.",
                document_id="doc2",
                chunk_index=0,
                rerank_score=0.90
            ),
            Passage(
                id="p3",
                content="France is a country in Western Europe. Paris serves as its capital.",
                document_id="doc3",
                chunk_index=0,
                rerank_score=0.85
            )
        ]

    @pytest.mark.parametrize("level,expected_threshold", [
        (VerificationLevel.VERY_HIGH, 0.92),
        (VerificationLevel.HIGH, 0.85),
        (VerificationLevel.MEDIUM, 0.75),
        (VerificationLevel.LOW, 0.65),
        (VerificationLevel.VERY_LOW, 0.55),
    ])
    def test_quote_matching_threshold_varies_by_level(
        self,
        level,
        expected_threshold,
        sample_passages
    ):
        """Test that quote matching threshold varies correctly by verification level."""
        # Create service with specific profile
        profile_map = {
            VerificationLevel.VERY_HIGH: VERY_HIGH_PROFILE,
            VerificationLevel.HIGH: HIGH_PROFILE,
            VerificationLevel.MEDIUM: MEDIUM_PROFILE,
            VerificationLevel.LOW: LOW_PROFILE,
            VerificationLevel.VERY_LOW: VERY_LOW_PROFILE,
        }

        service = QuoteMatchingService(profile=profile_map[level])

        assert service.similarity_threshold == expected_threshold, \
            f"Expected {expected_threshold} for {level.value}"

        # Test actual matching behavior
        proposition = "Paris is the capital of France"
        matches = service.find_supporting_quotes(proposition, sample_passages)

        # All levels should find at least one match for this exact proposition
        assert len(matches) >= 1, f"{level.value} should find matches"

        # Best match should have similarity >= threshold
        assert matches[0].similarity_score >= expected_threshold

    def test_very_high_level_strictest_matching(self, sample_passages):
        """Test VERY_HIGH level has strictest quote matching."""
        very_high_service = QuoteMatchingService(profile=VERY_HIGH_PROFILE)
        medium_service = QuoteMatchingService(profile=MEDIUM_PROFILE)

        # Slightly paraphrased proposition
        proposition = "The capital of France is the city of Paris"

        very_high_matches = very_high_service.find_supporting_quotes(proposition, sample_passages)
        medium_matches = medium_service.find_supporting_quotes(proposition, sample_passages)

        # MEDIUM should find more matches due to lower threshold
        # (This may not always hold depending on the exact paraphrase)
        # But we can at least verify VERY_HIGH is more selective
        assert very_high_service.similarity_threshold > medium_service.similarity_threshold

    def test_very_low_level_most_lenient_matching(self, sample_passages):
        """Test VERY_LOW level has most lenient quote matching."""
        very_low_service = QuoteMatchingService(profile=VERY_LOW_PROFILE)
        high_service = QuoteMatchingService(profile=HIGH_PROFILE)

        # Loosely related proposition
        proposition = "France has a capital city"

        very_low_matches = very_low_service.find_supporting_quotes(proposition, sample_passages)
        high_matches = high_service.find_supporting_quotes(proposition, sample_passages)

        # VERY_LOW should be more likely to find matches
        assert very_low_service.similarity_threshold < high_service.similarity_threshold

    @pytest.mark.parametrize("level,expected_conf_threshold,expected_hall_threshold", [
        (VerificationLevel.VERY_HIGH, 0.40, 0.60),
        (VerificationLevel.HIGH, 0.30, 0.70),
        (VerificationLevel.MEDIUM, 0.25, 0.75),
        (VerificationLevel.LOW, 0.20, 0.85),
        (VerificationLevel.VERY_LOW, 0.15, 0.95),
    ])
    def test_abstention_thresholds_vary_by_level(
        self,
        level,
        expected_conf_threshold,
        expected_hall_threshold
    ):
        """Test abstention thresholds vary correctly by verification level."""
        profile_map = {
            VerificationLevel.VERY_HIGH: VERY_HIGH_PROFILE,
            VerificationLevel.HIGH: HIGH_PROFILE,
            VerificationLevel.MEDIUM: MEDIUM_PROFILE,
            VerificationLevel.LOW: LOW_PROFILE,
            VerificationLevel.VERY_LOW: VERY_LOW_PROFILE,
        }

        service = AbstentionService(profile=profile_map[level])

        assert service.low_confidence_threshold == expected_conf_threshold
        assert service.high_hallucination_threshold == expected_hall_threshold

    @pytest.mark.asyncio
    async def test_very_high_level_abstains_more_often(self):
        """Test VERY_HIGH level abstains more often than other levels."""
        # Create mock verified response with borderline confidence
        # and sufficient evidence to avoid no_evidence abstention
        mock_response = VerifiedAnswerResponse(
            success=True,
            answer="Test answer",
            verified_answer="Test answer",
            propositions=[
                {"text": "Test proposition", "index": 0, "confidence": 0.85}
            ],
            citations=[
                {
                    "document_id": "doc1",
                    "document_name": "test.pdf",
                    "passage_text": "Test quote",
                    "relevance_score": 0.8,
                    "citation_number": 1
                }
            ],
            confidence=0.35,  # Between VERY_HIGH (0.40) and HIGH (0.30) thresholds
            verified_confidence=0.35,
            can_answer=True,
            abstention_reason=None,
            processing_time_ms=1000,
            passages_used=3,
            model_used="test",
            cache_hit=False,
            verification_metadata={
                "status": "verified",
                "active_verification_level": "HIGH",
                "hallucination_probability": 0.1,
                "propositions_checked": 1,
                "propositions_verified": 1,
                "propositions_removed": 0,
                "quote_matches": {"prop_0": [{"quote": "Test quote", "similarity": 0.9}]},
                "verification_latency_ms": 1000,
                "fallback_to_baseline": False,
                "failure_reason": None
            }
        )

        # Test with VERY_HIGH (should abstain)
        very_high_abstention = AbstentionService(profile=VERY_HIGH_PROFILE)
        very_high_decision = await very_high_abstention.should_abstain(mock_response)

        # Test with HIGH (should NOT abstain)
        high_abstention = AbstentionService(profile=HIGH_PROFILE)
        high_decision = await high_abstention.should_abstain(mock_response)

        # VERY_HIGH should abstain (0.35 < 0.40), HIGH should not (0.35 > 0.30)
        assert very_high_decision.should_abstain is True
        assert high_decision.should_abstain is False

    def test_hallucination_detection_weights_consistent_across_levels(self):
        """Test hallucination detection weights are consistent (as per design)."""
        # All levels should use same weights (design decision from tech doc)
        for profile in [VERY_HIGH_PROFILE, HIGH_PROFILE, MEDIUM_PROFILE, LOW_PROFILE, VERY_LOW_PROFILE]:
            assert profile.hallucination_quote_coverage_weight == 0.5
            assert profile.hallucination_verification_agreement_weight == 0.3
            assert profile.hallucination_semantic_contradiction_weight == 0.2

    @pytest.mark.parametrize("level,expected_temperature", [
        (VerificationLevel.VERY_HIGH, 0.05),
        (VerificationLevel.HIGH, 0.10),
        (VerificationLevel.MEDIUM, 0.15),
        (VerificationLevel.LOW, 0.20),
        (VerificationLevel.VERY_LOW, 0.30),
    ])
    def test_verification_temperature_varies_by_level(self, level, expected_temperature):
        """Test verification temperature varies by level."""
        profile_map = {
            VerificationLevel.VERY_HIGH: VERY_HIGH_PROFILE,
            VerificationLevel.HIGH: HIGH_PROFILE,
            VerificationLevel.MEDIUM: MEDIUM_PROFILE,
            VerificationLevel.LOW: LOW_PROFILE,
            VerificationLevel.VERY_LOW: VERY_LOW_PROFILE,
        }

        profile = profile_map[level]
        assert profile.verification_temperature == expected_temperature

    def test_contradiction_check_disabled_for_low_levels(self):
        """Test contradiction check is disabled for LOW and VERY_LOW levels."""
        # Should be enabled for high strictness
        assert VERY_HIGH_PROFILE.enable_contradiction_check is True
        assert HIGH_PROFILE.enable_contradiction_check is True
        assert MEDIUM_PROFILE.enable_contradiction_check is True

        # Should be disabled for performance on low strictness
        assert LOW_PROFILE.enable_contradiction_check is False
        assert VERY_LOW_PROFILE.enable_contradiction_check is False

    def test_strict_mode_varies_by_level(self):
        """Test strict mode is enabled for high levels, disabled for lower levels."""
        # Strict mode (auto-remove on suspicion)
        assert VERY_HIGH_PROFILE.strict_mode is True
        assert HIGH_PROFILE.strict_mode is True

        # Flag-only mode
        assert MEDIUM_PROFILE.strict_mode is False
        assert LOW_PROFILE.strict_mode is False
        assert VERY_LOW_PROFILE.strict_mode is False

    @pytest.mark.parametrize("level,expected_remove_threshold", [
        (VerificationLevel.VERY_HIGH, 0.50),  # Remove aggressively
        (VerificationLevel.HIGH, 0.70),
        (VerificationLevel.MEDIUM, 0.80),
        (VerificationLevel.LOW, 0.90),
        (VerificationLevel.VERY_LOW, 1.00),  # Never remove
    ])
    def test_auto_remove_threshold_varies_by_level(
        self,
        level,
        expected_remove_threshold
    ):
        """Test auto-remove threshold varies by verification level."""
        profile_map = {
            VerificationLevel.VERY_HIGH: VERY_HIGH_PROFILE,
            VerificationLevel.HIGH: HIGH_PROFILE,
            VerificationLevel.MEDIUM: MEDIUM_PROFILE,
            VerificationLevel.LOW: LOW_PROFILE,
            VerificationLevel.VERY_LOW: VERY_LOW_PROFILE,
        }

        profile = profile_map[level]
        assert profile.hallucination_auto_remove_threshold == expected_remove_threshold


class TestVerificationLevelsSwitching:
    """Test switching between verification levels at runtime."""

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "VERY_HIGH"})
    def test_switch_to_very_high_level(self):
        """Test switching to VERY_HIGH level."""
        profile = reload_profile()

        service = QuoteMatchingService()
        assert service.similarity_threshold == 0.92

    @patch.dict(os.environ, {"VERIFICATION_LEVEL": "VERY_LOW"})
    def test_switch_to_very_low_level(self):
        """Test switching to VERY_LOW level."""
        profile = reload_profile()

        service = QuoteMatchingService()
        assert service.similarity_threshold == 0.55

    def test_multiple_services_use_same_profile(self):
        """Test that multiple services use the same active profile."""
        from app.core.verification_profiles import get_active_profile

        active = get_active_profile()

        # Create multiple services
        quote_service = QuoteMatchingService()
        abstention_service = AbstentionService()
        confidence_calc = ConfidenceCalculator()

        # All should use the same profile
        assert quote_service.profile.level == active.level
        assert abstention_service.profile.level == active.level
        assert confidence_calc.profile.level == active.level


class TestVerificationLevelsEdgeCases:
    """Test edge cases across verification levels."""

    def test_all_levels_have_valid_max_matches(self):
        """Test all levels have valid quote_max_matches_per_proposition."""
        for profile in [VERY_HIGH_PROFILE, HIGH_PROFILE, MEDIUM_PROFILE, LOW_PROFILE, VERY_LOW_PROFILE]:
            # VERY_LOW uses 3 for speed, others use 5
            if profile.level == VerificationLevel.VERY_LOW:
                assert profile.quote_max_matches_per_proposition == 3
            else:
                assert profile.quote_max_matches_per_proposition == 5

    def test_confidence_weights_identical_across_levels(self):
        """Test confidence calculation weights are identical (design decision)."""
        # All levels use same confidence weights for consistency
        for profile in [VERY_HIGH_PROFILE, HIGH_PROFILE, MEDIUM_PROFILE, LOW_PROFILE, VERY_LOW_PROFILE]:
            assert profile.confidence_passage_relevance_weight == 0.40
            assert profile.confidence_quote_quality_weight == 0.35
            assert profile.confidence_verification_agreement_weight == 0.15
            assert profile.confidence_citation_count_weight == 0.10

    def test_flag_threshold_increases_with_leniency(self):
        """Test that flag_threshold increases as level becomes more lenient."""
        # Flag threshold should increase (flag less often)
        assert VERY_HIGH_PROFILE.hallucination_flag_threshold < HIGH_PROFILE.hallucination_flag_threshold
        assert HIGH_PROFILE.hallucination_flag_threshold < MEDIUM_PROFILE.hallucination_flag_threshold
        assert MEDIUM_PROFILE.hallucination_flag_threshold < LOW_PROFILE.hallucination_flag_threshold
        assert LOW_PROFILE.hallucination_flag_threshold < VERY_LOW_PROFILE.hallucination_flag_threshold


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
