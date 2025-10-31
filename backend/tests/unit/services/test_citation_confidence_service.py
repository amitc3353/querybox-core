"""
Unit Tests for CitationConfidenceService - Step 11.3

Tests orchestration of 4-stage enhancement pipeline and integration.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

import sys
sys.path.insert(0, 'backend')

from app.services.citation_confidence_service import CitationConfidenceService
from app.schemas.verification import VerifiedAnswerResponse, VerificationMetadata
from app.schemas.citation_confidence import EnhancedAnswerResponse, AbstentionReason


class TestCitationConfidenceService:
    """Test suite for citation confidence service orchestration."""

    @pytest.fixture
    def service(self):
        """Create citation confidence service with default configuration."""
        return CitationConfidenceService()

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
    # Test Complete Enhancement Pipeline
    # ========================================================================

    @pytest.mark.asyncio
    async def test_enhance_complete_pipeline(self, service, mock_verified_response):
        """Test complete 4-stage enhancement pipeline."""
        result = await service.enhance(mock_verified_response)

        assert isinstance(result, EnhancedAnswerResponse)
        assert result.success is True
        assert result.abstained is False
        assert result.verified_answer == "Paris is the capital of France. [1]"
        assert len(result.enriched_citations) > 0
        assert result.enhanced_metadata is not None
        assert result.enhanced_metadata.confidence_breakdown is not None

    @pytest.mark.asyncio
    async def test_enhance_with_good_confidence(self, service, mock_verified_response):
        """Test enhancement when all signals are good (should not abstain)."""
        # Good confidence, low hallucination, has quotes
        mock_verified_response.verified_confidence = 0.85
        mock_verified_response.verification_metadata.hallucination_probability = 0.1

        result = await service.enhance(mock_verified_response)

        assert result.abstained is False
        assert result.verified_answer != ""
        assert result.enhanced_metadata.confidence_breakdown.overall > 0

    # ========================================================================
    # Test Abstention Scenarios
    # ========================================================================

    @pytest.mark.asyncio
    async def test_enhance_abstention_low_confidence(self, service, mock_verified_response):
        """Test abstention triggered by low confidence."""
        # Set very low confidence
        mock_verified_response.verified_confidence = 0.1

        result = await service.enhance(mock_verified_response)

        assert result.abstained is True
        assert result.abstention_message is not None
        assert "confidence" in result.abstention_message.lower()
        assert result.verified_answer == ""
        assert len(result.enriched_citations) == 0

    @pytest.mark.asyncio
    async def test_enhance_abstention_high_hallucination(self, service, mock_verified_response):
        """Test abstention triggered by high hallucination."""
        # Set high hallucination probability
        mock_verified_response.verification_metadata.hallucination_probability = 0.85

        result = await service.enhance(mock_verified_response)

        assert result.abstained is True
        assert result.abstention_message is not None
        assert len(result.enriched_citations) == 0

    @pytest.mark.asyncio
    async def test_enhance_abstention_no_evidence(self, service, mock_verified_response):
        """Test abstention triggered by no supporting evidence."""
        # Remove all quote matches
        mock_verified_response.verification_metadata.quote_matches = {}

        result = await service.enhance(mock_verified_response)

        assert result.abstained is True
        assert result.abstention_message is not None
        assert "evidence" in result.abstention_message.lower() or "documents" in result.abstention_message.lower()

    @pytest.mark.asyncio
    async def test_enhance_abstention_verification_failed(self, service, mock_verified_response):
        """Test abstention triggered by verification failure."""
        # Set verification status to failed
        mock_verified_response.verification_metadata.status = "failed"

        result = await service.enhance(mock_verified_response)

        assert result.abstained is True
        assert result.abstention_message is not None

    @pytest.mark.asyncio
    async def test_abstention_response_structure(self, service, mock_verified_response):
        """Test that abstention response has correct structure."""
        mock_verified_response.verified_confidence = 0.1

        result = await service.enhance(mock_verified_response)

        # Check abstention response structure
        assert result.abstained is True
        assert result.success is True  # Abstention is a successful response
        assert result.can_answer is False
        assert result.abstention_message is not None
        assert result.abstention_reason is not None
        assert result.enhanced_metadata.abstention_factors["low_confidence"] is True

    # ========================================================================
    # Test Enriched Citations
    # ========================================================================

    @pytest.mark.asyncio
    async def test_enriched_citations_structure(self, service, mock_verified_response):
        """Test that enriched citations have correct structure."""
        result = await service.enhance(mock_verified_response)

        assert len(result.enriched_citations) > 0

        citation = result.enriched_citations[0]
        assert hasattr(citation, 'document_id')
        assert hasattr(citation, 'quality')
        assert hasattr(citation, 'is_exact_quote')
        assert hasattr(citation, 'inline_citation')

    @pytest.mark.asyncio
    async def test_enriched_citations_quality_indicators(self, service, mock_verified_response):
        """Test that quality indicators are assigned."""
        result = await service.enhance(mock_verified_response)

        citation = result.enriched_citations[0]
        # Quality should be STRONG, MEDIUM, or WEAK
        assert citation.quality in ["STRONG", "MEDIUM", "WEAK"]

    # ========================================================================
    # Test Enhanced Metadata
    # ========================================================================

    @pytest.mark.asyncio
    async def test_enhanced_metadata_structure(self, service, mock_verified_response):
        """Test that enhanced metadata has correct structure."""
        result = await service.enhance(mock_verified_response)

        metadata = result.enhanced_metadata
        assert metadata.confidence_breakdown is not None
        assert len(metadata.proposition_details) > 0
        assert isinstance(metadata.abstention_factors, dict)
        assert metadata.total_citations >= 0
        assert metadata.strong_citations >= 0

    @pytest.mark.asyncio
    async def test_enhanced_metadata_confidence_breakdown(self, service, mock_verified_response):
        """Test confidence breakdown is calculated."""
        result = await service.enhance(mock_verified_response)

        breakdown = result.enhanced_metadata.confidence_breakdown
        assert 0.0 <= breakdown.overall <= 1.0
        assert 0.0 <= breakdown.average_passage_relevance <= 1.0
        assert 0.0 <= breakdown.average_quote_quality <= 1.0

    @pytest.mark.asyncio
    async def test_enhanced_metadata_proposition_details(self, service, mock_verified_response):
        """Test proposition details are included."""
        result = await service.enhance(mock_verified_response)

        prop_details = result.enhanced_metadata.proposition_details
        assert len(prop_details) == 1  # One proposition

        detail = prop_details[0]
        assert detail.proposition_id == "0"
        assert detail.text == "Paris is the capital of France"
        assert 0.0 <= detail.confidence <= 1.0
        assert isinstance(detail.has_quote, bool)

    # ========================================================================
    # Test Error Handling
    # ========================================================================

    @pytest.mark.asyncio
    async def test_enhance_error_handling_abstention_failure(self, service, mock_verified_response):
        """Test that abstention errors are handled gracefully."""
        # Mock abstention service to raise error
        service.abstention_service.should_abstain = AsyncMock(side_effect=Exception("Abstention error"))

        # Should not raise exception, should continue with default (no abstention)
        result = await service.enhance(mock_verified_response)

        # Should still return valid response
        assert isinstance(result, EnhancedAnswerResponse)

    @pytest.mark.asyncio
    async def test_enhance_error_handling_confidence_failure(self, service, mock_verified_response):
        """Test that confidence calculation errors are handled gracefully."""
        # Mock confidence calculator to raise error
        service.confidence_calculator.calculate_all = AsyncMock(side_effect=Exception("Confidence error"))

        # Should not raise exception, should use fallback
        result = await service.enhance(mock_verified_response)

        # Should still return valid response
        assert isinstance(result, EnhancedAnswerResponse)

    @pytest.mark.asyncio
    async def test_enhance_error_handling_enrichment_failure(self, service, mock_verified_response):
        """Test that citation enrichment errors are handled gracefully."""
        # Mock citation enricher to raise error
        service.citation_enricher.enrich_citations = AsyncMock(side_effect=Exception("Enrichment error"))

        # Should not raise exception, should use fallback
        result = await service.enhance(mock_verified_response)

        # Should still return valid response
        assert isinstance(result, EnhancedAnswerResponse)

    # ========================================================================
    # Test Configuration Options
    # ========================================================================

    @pytest.mark.asyncio
    async def test_enhance_with_simple_citation_format(self, service, mock_verified_response):
        """Test enhancement with simple citation format [1]."""
        from app.schemas.citation_confidence import CitationConfig

        config = CitationConfig(inline_format="simple")

        result = await service.enhance(mock_verified_response, citation_config=config)

        if len(result.enriched_citations) > 0:
            # Simple format should be [N]
            assert result.enriched_citations[0].inline_citation.startswith("[")
            assert result.enriched_citations[0].inline_citation.endswith("]")

    @pytest.mark.asyncio
    async def test_enhance_with_detailed_citation_format(self, service, mock_verified_response):
        """Test enhancement with detailed citation format [1: doc, p.5]."""
        from app.schemas.citation_confidence import CitationConfig

        config = CitationConfig(inline_format="detailed")

        result = await service.enhance(mock_verified_response, citation_config=config)

        if len(result.enriched_citations) > 0:
            # Detailed format should include document name
            assert ":" in result.enriched_citations[0].inline_citation

    # ========================================================================
    # Test Health Check
    # ========================================================================

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test health check functionality."""
        health = await service.health_check()

        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "components" in health
        assert "abstention_service" in health["components"]
        assert "confidence_calculator" in health["components"]
        assert "citation_enricher" in health["components"]
        assert "metadata_assembler" in health["components"]

    # ========================================================================
    # Test Dependency Injection
    # ========================================================================

    def test_service_initialization_with_defaults(self):
        """Test that service initializes with default dependencies."""
        service = CitationConfidenceService()

        assert service.abstention_service is not None
        assert service.confidence_calculator is not None
        assert service.citation_enricher is not None
        assert service.metadata_assembler is not None

    def test_service_initialization_with_custom_dependencies(self):
        """Test that service accepts custom dependencies."""
        from app.services.citation_confidence.abstention_service import AbstentionService
        from app.services.citation_confidence.confidence_calculator import ConfidenceCalculator

        custom_abstention = AbstentionService(
            low_confidence_threshold=0.5,
            high_hallucination_threshold=0.5
        )
        custom_calculator = ConfidenceCalculator()

        service = CitationConfidenceService(
            abstention_service=custom_abstention,
            confidence_calculator=custom_calculator
        )

        assert service.abstention_service is custom_abstention
        assert service.confidence_calculator is custom_calculator

    # ========================================================================
    # Test Abstention Message Generation
    # ========================================================================

    def test_generate_abstention_message_low_confidence(self, service):
        """Test abstention message for low confidence."""
        from app.schemas.citation_confidence import AbstentionDecision

        decision = AbstentionDecision(
            should_abstain=True,
            reason=AbstentionReason.LOW_CONFIDENCE,
            factors=["low_confidence"],
            confidence=0.6
        )

        message = service._generate_abstention_message(decision)

        assert "confidence" in message.lower()
        assert len(message) > 0

    def test_generate_abstention_message_high_hallucination(self, service):
        """Test abstention message for high hallucination."""
        from app.schemas.citation_confidence import AbstentionDecision

        decision = AbstentionDecision(
            should_abstain=True,
            reason=AbstentionReason.HIGH_HALLUCINATION,
            factors=["high_hallucination"],
            confidence=0.8
        )

        message = service._generate_abstention_message(decision)

        assert "reliable" in message.lower() or "support" in message.lower()
        assert len(message) > 0

    def test_generate_abstention_message_no_evidence(self, service):
        """Test abstention message for no evidence."""
        from app.schemas.citation_confidence import AbstentionDecision

        decision = AbstentionDecision(
            should_abstain=True,
            reason=AbstentionReason.NO_EVIDENCE,
            factors=["no_evidence"],
            confidence=0.6
        )

        message = service._generate_abstention_message(decision)

        assert "evidence" in message.lower() or "documents" in message.lower()
        assert len(message) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
