"""
Unit Tests for AbstentionService - Step 11.3

Tests abstention decision logic, multi-factor triggering, and edge cases.
"""
import pytest
from unittest.mock import Mock

import sys
sys.path.insert(0, 'backend')

from app.services.citation_confidence.abstention_service import AbstentionService
from app.schemas.verification import VerifiedAnswerResponse, VerificationMetadata
from app.schemas.citation_confidence import AbstentionReason


class TestAbstentionService:
    """Test suite for abstention service."""

    @pytest.fixture
    def service(self):
        """Create abstention service with default thresholds."""
        return AbstentionService(
            low_confidence_threshold=0.3,
            high_hallucination_threshold=0.7
        )

    @pytest.fixture
    def mock_verified_response(self):
        """Create mock VerifiedAnswerResponse for testing."""
        return VerifiedAnswerResponse(
            success=True,
            answer="Test answer",
            verified_answer="Test answer",
            propositions=[
                {"index": 0, "text": "Test proposition"}
            ],
            citations=[],
            confidence=0.85,
            verified_confidence=0.85,
            can_answer=True,
            abstention_reason=None,
            processing_time_ms=1000,
            passages_used=5,
            model_used="qwen2:7b",
            cache_hit=False,
            verification_metadata=VerificationMetadata(
                status="verified",
                hallucination_probability=0.1,
                propositions_checked=1,
                propositions_verified=1,
                propositions_removed=0,
                quote_matches={"0": [{"matched_text": "test", "similarity_score": 0.95}]},
                verification_latency_ms=1000,
                fallback_to_baseline=False,
                failure_reason=None
            )
        )

    # ========================================================================
    # Test Factor 1: Low Confidence
    # ========================================================================

    @pytest.mark.asyncio
    async def test_abstention_low_confidence(self, service, mock_verified_response):
        """Test abstention triggered by low confidence."""
        # Set very low confidence
        mock_verified_response.verified_confidence = 0.1

        decision = await service.should_abstain(mock_verified_response)

        assert decision.should_abstain is True, "Should abstain on low confidence"
        assert decision.reason == AbstentionReason.LOW_CONFIDENCE
        assert "low_confidence" in decision.factors
        assert decision.confidence > 0, "Should have abstention confidence"

    @pytest.mark.asyncio
    async def test_no_abstention_good_confidence(self, service, mock_verified_response):
        """Test no abstention when confidence is good."""
        # Set good confidence (above threshold)
        mock_verified_response.verified_confidence = 0.85

        decision = await service.should_abstain(mock_verified_response)

        assert decision.should_abstain is False, "Should not abstain on good confidence"
        assert len(decision.factors) == 0, "No factors should trigger"

    @pytest.mark.asyncio
    async def test_abstention_threshold_boundary(self, service, mock_verified_response):
        """Test abstention at exact threshold boundary."""
        # Set confidence exactly at threshold (0.3)
        mock_verified_response.verified_confidence = 0.3

        decision = await service.should_abstain(mock_verified_response)

        # At boundary, should NOT abstain (< is the condition, not <=)
        assert decision.should_abstain is False, "Should not abstain at exact threshold"

    # ========================================================================
    # Test Factor 2: High Hallucination
    # ========================================================================

    @pytest.mark.asyncio
    async def test_abstention_high_hallucination(self, service, mock_verified_response):
        """Test abstention triggered by high hallucination probability."""
        # Set high hallucination probability
        mock_verified_response.verification_metadata.hallucination_probability = 0.85

        decision = await service.should_abstain(mock_verified_response)

        assert decision.should_abstain is True, "Should abstain on high hallucination"
        assert decision.reason == AbstentionReason.HIGH_HALLUCINATION
        assert "high_hallucination" in decision.factors

    @pytest.mark.asyncio
    async def test_no_abstention_low_hallucination(self, service, mock_verified_response):
        """Test no abstention when hallucination is low."""
        # Set low hallucination probability
        mock_verified_response.verification_metadata.hallucination_probability = 0.1

        decision = await service.should_abstain(mock_verified_response)

        assert decision.should_abstain is False, "Should not abstain on low hallucination"

    # ========================================================================
    # Test Factor 3: No Evidence (Quote Matches)
    # ========================================================================

    @pytest.mark.asyncio
    async def test_abstention_no_quotes(self, service, mock_verified_response):
        """Test abstention triggered by absence of quote matches."""
        # Remove all quote matches
        mock_verified_response.verification_metadata.quote_matches = {}

        decision = await service.should_abstain(mock_verified_response)

        assert decision.should_abstain is True, "Should abstain when no quotes"
        assert decision.reason == AbstentionReason.NO_EVIDENCE
        assert "no_evidence" in decision.factors

    @pytest.mark.asyncio
    async def test_abstention_empty_quote_lists(self, service, mock_verified_response):
        """Test abstention when quote match dict exists but all lists are empty."""
        # Set empty quote match lists
        mock_verified_response.verification_metadata.quote_matches = {
            "0": [],
            "1": []
        }

        decision = await service.should_abstain(mock_verified_response)

        assert decision.should_abstain is True, "Should abstain when all quote lists empty"
        assert "no_evidence" in decision.factors

    @pytest.mark.asyncio
    async def test_no_abstention_with_quotes(self, service, mock_verified_response):
        """Test no abstention when quote matches exist."""
        # Ensure quote matches exist
        mock_verified_response.verification_metadata.quote_matches = {
            "0": [{"matched_text": "test", "similarity_score": 0.95}]
        }

        decision = await service.should_abstain(mock_verified_response)

        assert decision.should_abstain is False, "Should not abstain with valid quotes"

    # ========================================================================
    # Test Factor 4: Verification Failed
    # ========================================================================

    @pytest.mark.asyncio
    async def test_abstention_verification_failed(self, service, mock_verified_response):
        """Test abstention triggered by verification failure."""
        # Set verification status to failed
        mock_verified_response.verification_metadata.status = "failed"

        decision = await service.should_abstain(mock_verified_response)

        assert decision.should_abstain is True, "Should abstain on verification failure"
        assert decision.reason == AbstentionReason.VERIFICATION_FAILED
        assert "verification_failed" in decision.factors

    @pytest.mark.asyncio
    async def test_no_abstention_verification_success(self, service, mock_verified_response):
        """Test no abstention when verification succeeds."""
        # Set verification status to verified
        mock_verified_response.verification_metadata.status = "verified"

        decision = await service.should_abstain(mock_verified_response)

        assert decision.should_abstain is False, "Should not abstain on verification success"

    # ========================================================================
    # Test Multi-Factor Combinations
    # ========================================================================

    @pytest.mark.asyncio
    async def test_abstention_multiple_factors(self, service, mock_verified_response):
        """Test abstention with multiple factors triggered."""
        # Trigger multiple factors
        mock_verified_response.verified_confidence = 0.1  # Low confidence
        mock_verified_response.verification_metadata.hallucination_probability = 0.85  # High hallucination
        mock_verified_response.verification_metadata.quote_matches = {}  # No evidence

        decision = await service.should_abstain(mock_verified_response)

        assert decision.should_abstain is True, "Should abstain with multiple factors"
        assert len(decision.factors) >= 3, "Should report all triggered factors"
        assert "low_confidence" in decision.factors
        assert "high_hallucination" in decision.factors
        assert "no_evidence" in decision.factors

        # Confidence in abstention should be high (multiple factors)
        assert decision.confidence >= 0.8, "High abstention confidence with multiple factors"

    @pytest.mark.asyncio
    async def test_abstention_reason_prioritization(self, service, mock_verified_response):
        """Test that abstention reason follows priority order."""
        # Trigger verification_failed (highest priority) plus other factors
        mock_verified_response.verification_metadata.status = "failed"
        mock_verified_response.verified_confidence = 0.1
        mock_verified_response.verification_metadata.hallucination_probability = 0.85

        decision = await service.should_abstain(mock_verified_response)

        # Primary reason should be verification_failed (highest priority)
        assert decision.reason == AbstentionReason.VERIFICATION_FAILED

    # ========================================================================
    # Test Abstention Confidence Calculation
    # ========================================================================

    @pytest.mark.asyncio
    async def test_abstention_confidence_single_factor(self, service, mock_verified_response):
        """Test abstention confidence with single factor."""
        mock_verified_response.verified_confidence = 0.1

        decision = await service.should_abstain(mock_verified_response)

        # Single factor: confidence = 0.6
        assert decision.confidence == 0.6, "Single factor should have 0.6 confidence"

    @pytest.mark.asyncio
    async def test_abstention_confidence_two_factors(self, service, mock_verified_response):
        """Test abstention confidence with two factors."""
        mock_verified_response.verified_confidence = 0.1
        mock_verified_response.verification_metadata.hallucination_probability = 0.85

        decision = await service.should_abstain(mock_verified_response)

        # Two factors: confidence = 0.8
        assert decision.confidence == 0.8, "Two factors should have 0.8 confidence"

    @pytest.mark.asyncio
    async def test_abstention_confidence_three_plus_factors(self, service, mock_verified_response):
        """Test abstention confidence with three or more factors."""
        mock_verified_response.verified_confidence = 0.1
        mock_verified_response.verification_metadata.hallucination_probability = 0.85
        mock_verified_response.verification_metadata.quote_matches = {}

        decision = await service.should_abstain(mock_verified_response)

        # Three+ factors: confidence = 1.0
        assert decision.confidence == 1.0, "Three+ factors should have 1.0 confidence"

    # ========================================================================
    # Test Edge Cases
    # ========================================================================

    @pytest.mark.asyncio
    async def test_abstention_none_confidence(self, service, mock_verified_response):
        """Test handling when verified_confidence is None."""
        mock_verified_response.verified_confidence = None

        decision = await service.should_abstain(mock_verified_response)

        # Should not trigger low_confidence factor (None is not < 0.3)
        assert "low_confidence" not in decision.factors

    @pytest.mark.asyncio
    async def test_abstention_none_hallucination(self, service, mock_verified_response):
        """Test handling when hallucination_probability is None."""
        mock_verified_response.verification_metadata.hallucination_probability = None

        decision = await service.should_abstain(mock_verified_response)

        # Should not trigger high_hallucination factor
        assert "high_hallucination" not in decision.factors

    @pytest.mark.asyncio
    async def test_abstention_custom_thresholds(self):
        """Test abstention with custom thresholds."""
        # Create service with stricter thresholds
        strict_service = AbstentionService(
            low_confidence_threshold=0.5,  # Higher threshold
            high_hallucination_threshold=0.4  # Lower threshold
        )

        response = VerifiedAnswerResponse(
            success=True,
            answer="Test",
            verified_answer="Test",
            propositions=[],
            citations=[],
            confidence=0.45,
            verified_confidence=0.45,  # Would not trigger default (0.3) but triggers 0.5
            can_answer=True,
            abstention_reason=None,
            processing_time_ms=1000,
            passages_used=5,
            model_used="qwen2:7b",
            cache_hit=False,
            verification_metadata=VerificationMetadata(
                status="verified",
                hallucination_probability=0.45,  # Would not trigger default (0.7) but triggers 0.4
                propositions_checked=0,
                propositions_verified=0,
                propositions_removed=0,
                quote_matches={},
                verification_latency_ms=1000,
                fallback_to_baseline=False,
                failure_reason=None
            )
        )

        decision = await strict_service.should_abstain(response)

        # Both factors should trigger with stricter thresholds
        assert decision.should_abstain is True
        assert "low_confidence" in decision.factors
        assert "high_hallucination" in decision.factors

    # ========================================================================
    # Test Health Check
    # ========================================================================

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test health check functionality."""
        health = await service.health_check()

        assert health["status"] == "healthy"
        assert health["low_confidence_threshold"] == 0.3
        assert health["high_hallucination_threshold"] == 0.7


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
