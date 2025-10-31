"""
Unit Tests for ConfidenceCalculator - Step 11.3

Tests 4-factor confidence calculation, aggregation strategies, and edge cases.
"""
import pytest
from unittest.mock import Mock

import sys
sys.path.insert(0, 'backend')

from app.services.citation_confidence.confidence_calculator import (
    ConfidenceCalculator,
    ConfidenceWeights
)
from app.schemas.verification import VerifiedAnswerResponse, VerificationMetadata, QuoteMatch
from app.schemas.citation_confidence import PropConfidence, ConfidenceBreakdown


class TestConfidenceCalculator:
    """Test suite for confidence calculator."""

    @pytest.fixture
    def calculator(self):
        """Create confidence calculator with default weights."""
        return ConfidenceCalculator()

    @pytest.fixture
    def mock_verified_response(self):
        """Create mock VerifiedAnswerResponse for testing."""
        return VerifiedAnswerResponse(
            success=True,
            answer="Paris is the capital of France. [1]",
            verified_answer="Paris is the capital of France. [1]",
            propositions=[
                {"index": 0, "text": "Paris is the capital of France"}
            ],
            citations=[
                {
                    "document_id": "doc1",
                    "document_name": "France.pdf",
                    "passage_text": "France's capital is Paris.",
                    "relevance_score": 0.95,
                    "citation_number": 1
                }
            ],
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
                quote_matches={
                    "0": [
                        {
                            "passage_id": "doc1",
                            "matched_text": "Paris",
                            "similarity_score": 0.97,
                            "start_pos": 0,
                            "end_pos": 5,
                            "sentence_index": 0
                        }
                    ]
                },
                verification_latency_ms=1000,
                fallback_to_baseline=False,
                failure_reason=None
            )
        )

    # ========================================================================
    # Test Confidence Weights
    # ========================================================================

    def test_default_weights_sum_to_one(self, calculator):
        """Test that default weights sum to 1.0."""
        weights = calculator.weights
        total = (
            weights.passage_relevance +
            weights.quote_quality +
            weights.verification_agreement +
            weights.citation_count
        )
        assert abs(total - 1.0) < 0.01, f"Weights should sum to 1.0, got {total}"

    def test_custom_weights_validation(self):
        """Test that invalid weights raise error."""
        # Weights that don't sum to 1.0
        with pytest.raises(ValueError, match="must sum to 1.0"):
            ConfidenceWeights(
                passage_relevance=0.5,
                quote_quality=0.3,
                verification_agreement=0.1,
                citation_count=0.05  # Total = 0.95, not 1.0
            )

    def test_custom_weights_accepted(self):
        """Test that valid custom weights are accepted."""
        weights = ConfidenceWeights(
            passage_relevance=0.5,
            quote_quality=0.3,
            verification_agreement=0.1,
            citation_count=0.1
        )
        calculator = ConfidenceCalculator(weights=weights)

        assert calculator.weights.passage_relevance == 0.5
        assert calculator.weights.quote_quality == 0.3

    # ========================================================================
    # Test Factor 1: Passage Relevance Score
    # ========================================================================

    def test_passage_relevance_single_citation(self, calculator):
        """Test passage relevance with single citation."""
        citations = [
            {"relevance_score": 0.95}
        ]

        score = calculator._calculate_passage_relevance_score(citations)

        assert score == 0.95, "Should return single relevance score"

    def test_passage_relevance_multiple_citations(self, calculator):
        """Test passage relevance with multiple citations (should use max)."""
        citations = [
            {"relevance_score": 0.95},
            {"relevance_score": 0.75},
            {"relevance_score": 0.88}
        ]

        score = calculator._calculate_passage_relevance_score(citations)

        assert score == 0.95, "Should return maximum relevance score"

    def test_passage_relevance_empty_citations(self, calculator):
        """Test passage relevance with no citations."""
        citations = []

        score = calculator._calculate_passage_relevance_score(citations)

        assert score == 0.0, "Should return 0.0 for empty citations"

    def test_passage_relevance_missing_scores(self, calculator):
        """Test passage relevance when some citations lack scores."""
        citations = [
            {"relevance_score": 0.95},
            {},  # No score
            {"relevance_score": 0.80}
        ]

        score = calculator._calculate_passage_relevance_score(citations)

        assert score == 0.95, "Should ignore citations without scores"

    # ========================================================================
    # Test Factor 2: Quote Match Quality Score
    # ========================================================================

    def test_quote_quality_single_match(self, calculator):
        """Test quote quality with single match."""
        matches = [
            QuoteMatch(
                passage_score=0.90,
                passage_id="p1",
                matched_text="test",
                similarity_score=0.97,
                start_pos=0,
                end_pos=4,
                sentence_index=0
            )
        ]

        score = calculator._calculate_quote_match_score(matches)

        assert score == 0.97, "Should return single similarity score"

    def test_quote_quality_multiple_matches(self, calculator):
        """Test quote quality with multiple matches (should use max)."""
        matches = [
            QuoteMatch(
                passage_score=0.90,
                passage_id="p1",
                matched_text="test1",
                similarity_score=0.97,
                start_pos=0,
                end_pos=5,
                sentence_index=0
            ),
            QuoteMatch(
                passage_score=0.90,
                passage_id="p2",
                matched_text="test2",
                similarity_score=0.85,
                start_pos=0,
                end_pos=5,
                sentence_index=0
            )
        ]

        score = calculator._calculate_quote_match_score(matches)

        assert score == 0.97, "Should return maximum similarity score"

    def test_quote_quality_no_matches(self, calculator):
        """Test quote quality with no matches."""
        matches = []

        score = calculator._calculate_quote_match_score(matches)

        assert score == 0.0, "Should return 0.0 for no matches"

    # ========================================================================
    # Test Factor 3: Verification Agreement Score
    # ========================================================================

    def test_verification_agreement_confirmed(self, calculator):
        """Test verification agreement when answer confirms."""
        from app.schemas.verification import VerificationAnswer

        prop_text = "Paris is the capital"
        verif_answer = VerificationAnswer(
            question_id="vq_1",
            answer="Yes, the document confirms Paris is the capital.",
            confidence=0.9
        )

        score = calculator._calculate_verification_agreement_score(prop_text, verif_answer)

        assert score == 1.0, "Should return 1.0 for confirmed answer"

    def test_verification_agreement_denied(self, calculator):
        """Test verification agreement when answer denies."""
        from app.schemas.verification import VerificationAnswer

        prop_text = "Paris is the capital"
        verif_answer = VerificationAnswer(
            question_id="vq_1",
            answer="No, this is incorrect.",
            confidence=0.9
        )

        score = calculator._calculate_verification_agreement_score(prop_text, verif_answer)

        assert score == 0.0, "Should return 0.0 for denied answer"

    def test_verification_agreement_neutral(self, calculator):
        """Test verification agreement when answer is neutral."""
        from app.schemas.verification import VerificationAnswer

        prop_text = "Paris is the capital"
        verif_answer = VerificationAnswer(
            question_id="vq_1",
            answer="Cannot determine from the documents.",
            confidence=0.5
        )

        score = calculator._calculate_verification_agreement_score(prop_text, verif_answer)

        assert score == 0.5, "Should return 0.5 for neutral answer"

    def test_verification_agreement_no_answer(self, calculator):
        """Test verification agreement when no verification answer."""
        prop_text = "Paris is the capital"
        verif_answer = None

        score = calculator._calculate_verification_agreement_score(prop_text, verif_answer)

        assert score == 0.5, "Should return 0.5 for no verification"

    # ========================================================================
    # Test Factor 4: Citation Count Score
    # ========================================================================

    def test_citation_count_single_citation(self, calculator):
        """Test citation count with single citation."""
        citations = [{"id": "c1"}]

        score = calculator._calculate_citation_count_score(citations)

        # 1 citation = 1/3 = 0.333...
        assert abs(score - 0.333) < 0.01, "1 citation should give ~0.33 score"

    def test_citation_count_two_citations(self, calculator):
        """Test citation count with two citations."""
        citations = [{"id": "c1"}, {"id": "c2"}]

        score = calculator._calculate_citation_count_score(citations)

        # 2 citations = 2/3 = 0.666...
        assert abs(score - 0.667) < 0.01, "2 citations should give ~0.67 score"

    def test_citation_count_three_plus_citations(self, calculator):
        """Test citation count with three or more citations (capped at 1.0)."""
        citations = [{"id": f"c{i}"} for i in range(5)]

        score = calculator._calculate_citation_count_score(citations)

        assert score == 1.0, "3+ citations should give max score of 1.0"

    def test_citation_count_no_citations(self, calculator):
        """Test citation count with no citations."""
        citations = []

        score = calculator._calculate_citation_count_score(citations)

        assert score == 0.0, "0 citations should give 0.0 score"

    # ========================================================================
    # Test Complete Confidence Calculation
    # ========================================================================

    @pytest.mark.asyncio
    async def test_calculate_proposition_confidence(self, calculator):
        """Test complete per-proposition confidence calculation."""
        prop_id = "0"
        prop_text = "Paris is the capital of France"

        quote_matches = [
            QuoteMatch(
                passage_score=0.90,
                passage_id="p1",
                matched_text="Paris",
                similarity_score=0.97,
                start_pos=0,
                end_pos=5,
                sentence_index=0
            )
        ]

        citations = [
            {"relevance_score": 0.95, "id": "c1"}
        ]

        result = await calculator.calculate_proposition_confidence(
            proposition_id=prop_id,
            proposition_text=prop_text,
            quote_matches=quote_matches,
            verification_answer=None,
            citations=citations,
            hallucination_probability=0.0
        )

        assert isinstance(result, PropConfidence)
        assert result.proposition_id == prop_id
        assert 0.0 <= result.confidence <= 1.0
        assert "passage_relevance" in result.breakdown
        assert "quote_quality" in result.breakdown
        assert "verification_agreement" in result.breakdown
        assert "citation_count" in result.breakdown
        assert result.is_fallback is False

    @pytest.mark.asyncio
    async def test_confidence_with_hallucination_penalty(self, calculator):
        """Test that hallucination probability reduces confidence."""
        prop_id = "0"
        prop_text = "Test proposition"

        # Calculate with no hallucination
        result_no_halluc = await calculator.calculate_proposition_confidence(
            proposition_id=prop_id,
            proposition_text=prop_text,
            quote_matches=[],
            verification_answer=None,
            citations=[{"relevance_score": 0.95}],
            hallucination_probability=0.0
        )

        # Calculate with high hallucination
        result_with_halluc = await calculator.calculate_proposition_confidence(
            proposition_id=prop_id,
            proposition_text=prop_text,
            quote_matches=[],
            verification_answer=None,
            citations=[{"relevance_score": 0.95}],
            hallucination_probability=0.5  # 50% hallucination
        )

        # Confidence should be reduced by hallucination
        assert result_with_halluc.confidence < result_no_halluc.confidence
        assert result_with_halluc.confidence == pytest.approx(result_no_halluc.confidence * 0.5, rel=0.01)

    @pytest.mark.asyncio
    async def test_calculate_all_propositions(self, calculator, mock_verified_response):
        """Test calculating confidence for all propositions."""
        prop_confidences = await calculator.calculate_all(mock_verified_response)

        assert len(prop_confidences) == 1, "Should calculate for 1 proposition"
        assert "0" in prop_confidences, "Should have confidence for proposition 0"

        prop_conf = prop_confidences["0"]
        assert isinstance(prop_conf, PropConfidence)
        assert 0.0 <= prop_conf.confidence <= 1.0

    # ========================================================================
    # Test Aggregation to Overall Confidence
    # ========================================================================

    def test_aggregate_single_proposition(self, calculator):
        """Test aggregation with single proposition."""
        prop_confidences = {
            "0": PropConfidence(
                proposition_id="0",
                confidence=0.85,
                breakdown={},
                is_fallback=False
            )
        }

        overall = calculator.aggregate_to_overall_confidence(prop_confidences)

        assert overall == 0.85, "Single proposition should return its confidence"

    def test_aggregate_multiple_propositions(self, calculator):
        """Test aggregation with multiple propositions (weighted average)."""
        prop_confidences = {
            "0": PropConfidence(
                proposition_id="0",
                confidence=0.9,
                breakdown={},
                is_fallback=False
            ),
            "1": PropConfidence(
                proposition_id="1",
                confidence=0.8,
                breakdown={},
                is_fallback=False
            )
        }

        overall = calculator.aggregate_to_overall_confidence(prop_confidences)

        # Average: (0.9 + 0.8) / 2 = 0.85
        assert overall == 0.85, "Should return average of confidences"

    def test_aggregate_empty_propositions(self, calculator):
        """Test aggregation with no propositions."""
        prop_confidences = {}

        overall = calculator.aggregate_to_overall_confidence(prop_confidences)

        assert overall == 0.0, "Empty propositions should return 0.0"

    # ========================================================================
    # Test Confidence Breakdown
    # ========================================================================

    def test_build_confidence_breakdown(self, calculator):
        """Test building overall confidence breakdown."""
        prop_confidences = {
            "0": PropConfidence(
                proposition_id="0",
                confidence=0.9,
                breakdown={
                    "passage_relevance": 0.95,
                    "quote_quality": 0.90,
                    "verification_agreement": 1.0,
                    "citation_count": 0.67
                },
                is_fallback=False
            ),
            "1": PropConfidence(
                proposition_id="1",
                confidence=0.8,
                breakdown={
                    "passage_relevance": 0.85,
                    "quote_quality": 0.80,
                    "verification_agreement": 0.5,
                    "citation_count": 0.33
                },
                is_fallback=False
            )
        }

        breakdown = calculator.build_confidence_breakdown(prop_confidences)

        assert isinstance(breakdown, ConfidenceBreakdown)
        assert breakdown.overall == 0.85  # (0.9 + 0.8) / 2
        assert breakdown.average_passage_relevance == 0.9  # (0.95 + 0.85) / 2
        assert breakdown.average_quote_quality == 0.85  # (0.90 + 0.80) / 2

    def test_build_confidence_breakdown_empty(self, calculator):
        """Test building confidence breakdown with no propositions."""
        prop_confidences = {}

        breakdown = calculator.build_confidence_breakdown(prop_confidences)

        assert breakdown.overall == 0.0
        assert breakdown.average_passage_relevance == 0.0

    # ========================================================================
    # Test Edge Cases
    # ========================================================================

    @pytest.mark.asyncio
    async def test_confidence_bounds_checking(self, calculator):
        """Test that confidence is always bounded between 0 and 1."""
        prop_id = "0"
        prop_text = "Test"

        # Even with perfect scores and no hallucination
        result = await calculator.calculate_proposition_confidence(
            proposition_id=prop_id,
            proposition_text=prop_text,
            quote_matches=[
                QuoteMatch(
                passage_score=0.90,
                passage_id="p1",
                    matched_text="test",
                    similarity_score=1.0,
                    start_pos=0,
                    end_pos=4,
                    sentence_index=0
                )
            ],
            verification_answer=None,
            citations=[
                {"relevance_score": 1.0},
                {"relevance_score": 1.0},
                {"relevance_score": 1.0},
            ],
            hallucination_probability=0.0
        )

        assert 0.0 <= result.confidence <= 1.0, "Confidence must be in [0, 1]"

    @pytest.mark.asyncio
    async def test_confidence_with_dict_proposition(self, calculator, mock_verified_response):
        """Test that confidence calculation works with dict propositions."""
        # Propositions are dicts in VerifiedAnswerResponse
        assert isinstance(mock_verified_response.propositions[0], dict)

        prop_confidences = await calculator.calculate_all(mock_verified_response)

        # Should successfully calculate despite dict format
        assert len(prop_confidences) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
