"""
Unit Tests for MetadataAssembler - Step 11.3

Tests metadata assembly, proposition details building, and abstention factors.
"""
import pytest
from unittest.mock import Mock

import sys
sys.path.insert(0, 'backend')

from app.services.citation_confidence.metadata_assembler import MetadataAssembler
from app.schemas.verification import VerifiedAnswerResponse, VerificationMetadata
from app.schemas.citation_confidence import (
    EnhancedMetadata,
    PropConfidence,
    EnrichedCitation,
    AbstentionDecision,
    AbstentionReason,
    CitationQuality,
    PropositionDetail
)


class TestMetadataAssembler:
    """Test suite for metadata assembler."""

    @pytest.fixture
    def assembler(self):
        """Create metadata assembler."""
        return MetadataAssembler()

    @pytest.fixture
    def mock_verified_response(self):
        """Create mock VerifiedAnswerResponse."""
        return VerifiedAnswerResponse(
            success=True,
            answer="Paris is the capital of France. [1]",
            verified_answer="Paris is the capital of France. [1]",
            propositions=[
                {"index": 0, "text": "Paris is the capital of France"}
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

    @pytest.fixture
    def mock_prop_confidences(self):
        """Create mock proposition confidences."""
        return {
            "0": PropConfidence(
                proposition_id="0",
                confidence=0.92,
                breakdown={
                    "passage_relevance": 0.95,
                    "quote_quality": 0.97,
                    "verification_agreement": 1.0,
                    "citation_count": 0.33
                },
                is_fallback=False
            )
        }

    @pytest.fixture
    def mock_enriched_citations(self):
        """Create mock enriched citations."""
        return [
            EnrichedCitation(
                document_id="doc1",
                document_name="France.pdf",
                passage_text="France's capital is Paris.",
                page=5,
                section="Geography",
                relevance_score=0.95,
                citation_number=1,
                quote_match=None,
                best_similarity=0.97,
                is_exact_quote=True,
                quality=CitationQuality.STRONG,
                highlighted_passage_text=None,
                inline_citation="[1]",
                proposition_ids=["0"]
            )
        ]

    @pytest.fixture
    def mock_abstention_decision(self):
        """Create mock abstention decision."""
        return AbstentionDecision(
            should_abstain=False,
            reason=None,
            factors=[],
            confidence=0.0
        )

    # ========================================================================
    # Test Complete Metadata Building
    # ========================================================================

    @pytest.mark.asyncio
    async def test_build_enhanced_metadata(
        self,
        assembler,
        mock_verified_response,
        mock_prop_confidences,
        mock_enriched_citations,
        mock_abstention_decision
    ):
        """Test complete enhanced metadata building."""
        metadata = await assembler.build(
            mock_verified_response,
            mock_prop_confidences,
            mock_enriched_citations,
            mock_abstention_decision
        )

        assert isinstance(metadata, EnhancedMetadata)

        # Core verification fields
        assert metadata.status == "verified"
        assert metadata.hallucination_probability == 0.1
        assert metadata.propositions_checked == 1

        # Enhanced fields
        assert metadata.confidence_breakdown.overall > 0
        assert len(metadata.proposition_details) == 1
        assert metadata.total_citations == 1
        assert metadata.strong_citations == 1

    # ========================================================================
    # Test Proposition Details Building
    # ========================================================================

    @pytest.mark.asyncio
    async def test_build_proposition_details(
        self,
        assembler,
        mock_verified_response,
        mock_prop_confidences,
        mock_enriched_citations
    ):
        """Test building proposition details array."""
        prop_details = assembler._build_proposition_details(
            mock_verified_response.propositions,
            mock_prop_confidences,
            mock_verified_response.verification_metadata.quote_matches,
            mock_enriched_citations
        )

        assert len(prop_details) == 1

        detail = prop_details[0]
        assert isinstance(detail, PropositionDetail)
        assert detail.proposition_id == "0"
        assert detail.text == "Paris is the capital of France"
        assert 0.0 <= detail.confidence <= 1.0
        assert detail.has_quote is True
        assert detail.quote_similarity is not None
        assert isinstance(detail.citations, list)

    def test_build_proposition_details_no_quotes(
        self,
        assembler,
        mock_prop_confidences
    ):
        """Test proposition details when no quotes exist."""
        propositions = [{"index": 0, "text": "Test claim"}]
        quote_matches = {}  # No quotes
        citations = []

        prop_details = assembler._build_proposition_details(
            propositions,
            mock_prop_confidences,
            quote_matches,
            citations
        )

        detail = prop_details[0]
        assert detail.has_quote is False
        assert detail.quote_similarity is None

    def test_build_proposition_details_no_confidence(self, assembler):
        """Test proposition details when confidence is missing (fallback)."""
        propositions = [{"index": 0, "text": "Test claim"}]
        prop_confidences = {}  # No confidence for prop 0
        quote_matches = {}
        citations = []

        prop_details = assembler._build_proposition_details(
            propositions,
            prop_confidences,
            quote_matches,
            citations
        )

        detail = prop_details[0]
        # Should use fallback confidence
        assert detail.confidence == 0.5
        assert detail.confidence_breakdown["verification_agreement"] == 0.5

    def test_build_proposition_details_multiple_quotes(
        self,
        assembler,
        mock_prop_confidences
    ):
        """Test proposition details with multiple quote matches (should use max similarity)."""
        propositions = [{"index": 0, "text": "Test claim"}]
        quote_matches = {
            "0": [
                {"similarity_score": 0.85},
                {"similarity_score": 0.97},  # Highest
                {"similarity_score": 0.90}
            ]
        }
        citations = []

        prop_details = assembler._build_proposition_details(
            propositions,
            mock_prop_confidences,
            quote_matches,
            citations
        )

        detail = prop_details[0]
        assert detail.quote_similarity == 0.97  # Maximum

    # ========================================================================
    # Test Confidence Breakdown Building
    # ========================================================================

    def test_build_confidence_breakdown(self, assembler, mock_prop_confidences):
        """Test building confidence breakdown from prop confidences."""
        breakdown = assembler._build_confidence_breakdown(mock_prop_confidences)

        assert breakdown.overall == 0.92
        assert breakdown.average_passage_relevance == 0.95
        assert breakdown.average_quote_quality == 0.97
        assert breakdown.average_verification_agreement == 1.0
        assert breakdown.average_citation_count == 0.33

    def test_build_confidence_breakdown_multiple_props(self, assembler):
        """Test confidence breakdown averaging across multiple propositions."""
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

        breakdown = assembler._build_confidence_breakdown(prop_confidences)

        # Averages
        assert breakdown.overall == 0.85  # (0.9 + 0.8) / 2
        assert breakdown.average_passage_relevance == 0.9  # (0.95 + 0.85) / 2
        assert breakdown.average_quote_quality == 0.85  # (0.90 + 0.80) / 2

    def test_build_confidence_breakdown_empty(self, assembler):
        """Test confidence breakdown with no propositions."""
        prop_confidences = {}

        breakdown = assembler._build_confidence_breakdown(prop_confidences)

        assert breakdown.overall == 0.0
        assert breakdown.average_passage_relevance == 0.0

    # ========================================================================
    # Test Abstention Factors Building
    # ========================================================================

    def test_build_abstention_factors_no_abstention(self, assembler):
        """Test abstention factors when no abstention."""
        decision = AbstentionDecision(
            should_abstain=False,
            reason=None,
            factors=[],
            confidence=0.0
        )

        factors = assembler._build_abstention_factors(decision)

        assert factors["low_confidence"] is False
        assert factors["high_hallucination"] is False
        assert factors["no_evidence"] is False
        assert factors["verification_failed"] is False

    def test_build_abstention_factors_low_confidence(self, assembler):
        """Test abstention factors with low confidence trigger."""
        decision = AbstentionDecision(
            should_abstain=True,
            reason=AbstentionReason.LOW_CONFIDENCE,
            factors=["low_confidence"],
            confidence=0.6
        )

        factors = assembler._build_abstention_factors(decision)

        assert factors["low_confidence"] is True
        assert factors["high_hallucination"] is False

    def test_build_abstention_factors_multiple_triggers(self, assembler):
        """Test abstention factors with multiple triggers."""
        decision = AbstentionDecision(
            should_abstain=True,
            reason=AbstentionReason.HIGH_HALLUCINATION,
            factors=["low_confidence", "high_hallucination", "no_evidence"],
            confidence=1.0
        )

        factors = assembler._build_abstention_factors(decision)

        assert factors["low_confidence"] is True
        assert factors["high_hallucination"] is True
        assert factors["no_evidence"] is True
        assert factors["verification_failed"] is False

    # ========================================================================
    # Test Citation Quality Counts
    # ========================================================================

    @pytest.mark.asyncio
    async def test_citation_quality_counts(
        self,
        assembler,
        mock_verified_response,
        mock_prop_confidences,
        mock_abstention_decision
    ):
        """Test that citation quality counts are calculated correctly."""
        enriched_citations = [
            EnrichedCitation(
                document_id="doc1",
                document_name="Test1.pdf",
                passage_text="Test",
                relevance_score=0.95,
                citation_number=1,
                quality=CitationQuality.STRONG,
                inline_citation="[1]",
                proposition_ids=[]
            ),
            EnrichedCitation(
                document_id="doc2",
                document_name="Test2.pdf",
                passage_text="Test",
                relevance_score=0.90,
                citation_number=2,
                quality=CitationQuality.STRONG,
                inline_citation="[2]",
                proposition_ids=[]
            ),
            EnrichedCitation(
                document_id="doc3",
                document_name="Test3.pdf",
                passage_text="Test",
                relevance_score=0.85,
                citation_number=3,
                quality=CitationQuality.MEDIUM,
                inline_citation="[3]",
                proposition_ids=[]
            ),
            EnrichedCitation(
                document_id="doc4",
                document_name="Test4.pdf",
                passage_text="Test",
                relevance_score=0.75,
                citation_number=4,
                quality=CitationQuality.WEAK,
                inline_citation="[4]",
                proposition_ids=[]
            )
        ]

        metadata = await assembler.build(
            mock_verified_response,
            mock_prop_confidences,
            enriched_citations,
            mock_abstention_decision
        )

        assert metadata.total_citations == 4
        assert metadata.strong_citations == 2
        assert metadata.medium_citations == 1
        assert metadata.weak_citations == 1

    @pytest.mark.asyncio
    async def test_empty_citations(
        self,
        assembler,
        mock_verified_response,
        mock_prop_confidences,
        mock_abstention_decision
    ):
        """Test metadata with no citations."""
        metadata = await assembler.build(
            mock_verified_response,
            mock_prop_confidences,
            [],  # Empty citations
            mock_abstention_decision
        )

        assert metadata.total_citations == 0
        assert metadata.strong_citations == 0
        assert metadata.medium_citations == 0
        assert metadata.weak_citations == 0

    # ========================================================================
    # Test Edge Cases
    # ========================================================================

    @pytest.mark.asyncio
    async def test_build_with_empty_propositions(
        self,
        assembler,
        mock_abstention_decision
    ):
        """Test building metadata with no propositions."""
        verified_response = VerifiedAnswerResponse(
            success=True,
            answer="",
            verified_answer="",
            propositions=[],  # Empty
            citations=[],
            confidence=0.0,
            verified_confidence=0.0,
            can_answer=False,
            abstention_reason=None,
            processing_time_ms=1000,
            passages_used=0,
            model_used="qwen2:7b",
            cache_hit=False,
            verification_metadata=VerificationMetadata(
                status="skipped",
                hallucination_probability=0.0,
                propositions_checked=0,
                propositions_verified=0,
                propositions_removed=0,
                quote_matches={},
                verification_latency_ms=0,
                fallback_to_baseline=False,
                failure_reason=None
            )
        )

        metadata = await assembler.build(
            verified_response,
            {},  # No confidences
            [],  # No citations
            mock_abstention_decision
        )

        assert len(metadata.proposition_details) == 0
        assert metadata.confidence_breakdown.overall == 0.0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
