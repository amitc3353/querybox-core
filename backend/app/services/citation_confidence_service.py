"""
Citation & Confidence Service for Step 11.3

Main orchestration service that coordinates all citation & confidence enhancement stages:
1. Abstention decision (should we answer or abstain?)
2. Granular confidence calculation (per-proposition scores)
3. Citation enrichment (quote matches, quality indicators)
4. Enhanced metadata assembly (comprehensive response)

Transforms VerifiedAnswerResponse (Step 11.2) → EnhancedAnswerResponse (Step 11.3).
"""
from typing import Dict, List, Optional
import time
import structlog

from app.schemas.verification import VerifiedAnswerResponse
from app.schemas.citation_confidence import (
    EnhancedAnswerResponse,
    EnrichedCitation,
    PropConfidence,
    AbstentionDecision,
    EnhancedMetadata,
    AbstentionConfig,
    CitationConfig
)
from app.services.citation_confidence.abstention_service import AbstentionService
from app.services.citation_confidence.confidence_calculator import ConfidenceCalculator
from app.services.citation_confidence.citation_enricher import CitationEnricher
from app.services.citation_confidence.metadata_assembler import MetadataAssembler

logger = structlog.get_logger(__name__)


class CitationConfidenceService:
    """
    Main orchestration service for citation & confidence enhancement.

    Coordinates 4-stage enhancement pipeline:
    1. Abstention Decision: Determine if we should answer or abstain
    2. Confidence Calculation: Calculate per-proposition confidence scores
    3. Citation Enrichment: Add quote matches and quality indicators
    4. Metadata Assembly: Build comprehensive enhanced metadata

    Transforms VerifiedAnswerResponse → EnhancedAnswerResponse.
    """

    def __init__(
        self,
        abstention_service: Optional[AbstentionService] = None,
        confidence_calculator: Optional[ConfidenceCalculator] = None,
        citation_enricher: Optional[CitationEnricher] = None,
        metadata_assembler: Optional[MetadataAssembler] = None
    ):
        """
        Initialize citation & confidence service.

        Args:
            abstention_service: Abstention decision service (creates default if None)
            confidence_calculator: Confidence calculation service (creates default if None)
            citation_enricher: Citation enrichment service (creates default if None)
            metadata_assembler: Metadata assembly service (creates default if None)
        """
        self.abstention_service = abstention_service or AbstentionService()
        self.confidence_calculator = confidence_calculator or ConfidenceCalculator()
        self.citation_enricher = citation_enricher or CitationEnricher()
        self.metadata_assembler = metadata_assembler or MetadataAssembler()

        logger.info("CitationConfidenceService initialized")

    async def enhance(
        self,
        verified_response: VerifiedAnswerResponse,
        abstention_config: Optional[AbstentionConfig] = None,
        citation_config: Optional[CitationConfig] = None
    ) -> EnhancedAnswerResponse:
        """
        Execute full citation & confidence enhancement pipeline.

        Pipeline Stages:
        1. Abstention Decision: Check if should abstain (low confidence, high hallucination, etc.)
        2. Confidence Calculation: Calculate per-proposition confidence with factor breakdown
        3. Citation Enrichment: Add quote matches, quality indicators, highlighting
        4. Metadata Assembly: Build comprehensive enhanced metadata

        Args:
            verified_response: VerifiedAnswerResponse from Step 11.2
            abstention_config: Optional abstention configuration
            citation_config: Optional citation formatting configuration

        Returns:
            EnhancedAnswerResponse with granular confidence and enriched citations

        Complexity: O(P * C * Q) where P=propositions, C=citations, Q=quote matches
        Time: ~100-200ms additional latency on top of Step 11.2
        """
        start_time = time.time()

        logger.info(
            "Starting citation & confidence enhancement",
            propositions_count=len(verified_response.propositions),
            citations_count=len(verified_response.citations)
        )

        # Stage 1: Abstention Decision
        abstention_decision = await self._process_abstention(verified_response)

        if abstention_decision.should_abstain:
            # Return abstention response
            logger.info(
                "Abstention triggered",
                reason=abstention_decision.reason,
                confidence=abstention_decision.confidence
            )
            return self._build_abstention_response(
                verified_response,
                abstention_decision
            )

        # Stage 2: Calculate Confidences
        prop_confidences = await self._calculate_confidences(verified_response)

        # Stage 3: Enrich Citations
        citation_format = citation_config.inline_format if citation_config else "simple"
        enriched_citations = await self._enrich_citations(
            verified_response,
            citation_format
        )

        # Stage 4: Build Enhanced Metadata
        enhanced_metadata = await self._build_enhanced_metadata(
            verified_response,
            prop_confidences,
            enriched_citations,
            abstention_decision
        )

        # Calculate overall confidence
        overall_confidence = self.confidence_calculator.aggregate_to_overall_confidence(
            prop_confidences
        )

        # Build enhanced answer response
        enhanced_response = EnhancedAnswerResponse(
            # Core answer fields
            success=verified_response.success,
            answer=verified_response.answer,
            verified_answer=verified_response.verified_answer,
            propositions=verified_response.propositions,
            citations=verified_response.citations,  # Legacy field
            confidence=verified_response.confidence,
            verified_confidence=overall_confidence,
            can_answer=verified_response.can_answer,
            abstention_reason=verified_response.abstention_reason,
            processing_time_ms=verified_response.processing_time_ms,
            passages_used=verified_response.passages_used,
            model_used=verified_response.model_used,
            cache_hit=verified_response.cache_hit,
            # Step 11.3 enhancement fields
            abstained=False,
            abstention_message=None,
            enriched_citations=enriched_citations,
            enhanced_metadata=enhanced_metadata
        )

        elapsed_time = int((time.time() - start_time) * 1000)
        logger.info(
            "Citation & confidence enhancement completed",
            elapsed_ms=elapsed_time,
            overall_confidence=overall_confidence,
            strong_citations=enhanced_metadata.strong_citations
        )

        return enhanced_response

    async def _process_abstention(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> AbstentionDecision:
        """
        Stage 1: Check if should abstain from answering.

        Args:
            verified_response: VerifiedAnswerResponse from Step 11.2

        Returns:
            AbstentionDecision with should_abstain flag and reason
        """
        logger.debug("Stage 1: Processing abstention decision")

        try:
            decision = await self.abstention_service.should_abstain(verified_response)
            return decision
        except Exception as e:
            logger.error(f"Abstention decision failed: {e}", exc_info=True)
            # Conservative fallback: Don't abstain on error
            return AbstentionDecision(should_abstain=False)

    async def _calculate_confidences(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> Dict[str, PropConfidence]:
        """
        Stage 2: Calculate per-proposition confidence scores.

        Args:
            verified_response: VerifiedAnswerResponse from Step 11.2

        Returns:
            Dict mapping proposition_id → PropConfidence
        """
        logger.debug("Stage 2: Calculating confidence scores")

        try:
            prop_confidences = await self.confidence_calculator.calculate_all(
                verified_response
            )
            return prop_confidences
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}", exc_info=True)
            # Fallback: Return neutral confidences
            return {}

    async def _enrich_citations(
        self,
        verified_response: VerifiedAnswerResponse,
        inline_format: str = "simple"
    ) -> List[EnrichedCitation]:
        """
        Stage 3: Enrich citations with quote matches and quality indicators.

        Args:
            verified_response: VerifiedAnswerResponse from Step 11.2
            inline_format: Citation format ("simple" or "detailed")

        Returns:
            List of EnrichedCitation objects
        """
        logger.debug("Stage 3: Enriching citations")

        try:
            enriched = await self.citation_enricher.enrich_citations(
                citations=verified_response.citations,
                quote_matches=verified_response.verification_metadata.quote_matches,
                propositions=verified_response.propositions,
                inline_format=inline_format
            )
            return enriched
        except Exception as e:
            logger.error(f"Citation enrichment failed: {e}", exc_info=True)
            # Fallback: Return empty enriched citations list
            return []

    async def _build_enhanced_metadata(
        self,
        verified_response: VerifiedAnswerResponse,
        prop_confidences: Dict[str, PropConfidence],
        enriched_citations: List[EnrichedCitation],
        abstention_decision: AbstentionDecision
    ) -> EnhancedMetadata:
        """
        Stage 4: Assemble comprehensive enhanced metadata.

        Args:
            verified_response: VerifiedAnswerResponse from Step 11.2
            prop_confidences: Per-proposition confidences
            enriched_citations: Enriched citations
            abstention_decision: Abstention decision

        Returns:
            EnhancedMetadata with all enhancement details
        """
        logger.debug("Stage 4: Building enhanced metadata")

        try:
            metadata = await self.metadata_assembler.build(
                verified_response,
                prop_confidences,
                enriched_citations,
                abstention_decision
            )
            return metadata
        except Exception as e:
            logger.error(f"Metadata assembly failed: {e}", exc_info=True)
            # Fallback: Return minimal enhanced metadata
            from app.schemas.citation_confidence import ConfidenceBreakdown
            return EnhancedMetadata(
                # Core verification fields
                status=verified_response.verification_metadata.status,
                hallucination_probability=verified_response.verification_metadata.hallucination_probability,
                propositions_checked=verified_response.verification_metadata.propositions_checked,
                propositions_verified=verified_response.verification_metadata.propositions_verified,
                propositions_removed=verified_response.verification_metadata.propositions_removed,
                quote_matches=verified_response.verification_metadata.quote_matches,
                verification_latency_ms=verified_response.verification_metadata.verification_latency_ms,
                fallback_to_baseline=verified_response.verification_metadata.fallback_to_baseline,
                failure_reason=verified_response.verification_metadata.failure_reason,
                # Enhanced fields (defaults)
                confidence_breakdown=ConfidenceBreakdown(
                    overall=0.5,
                    average_passage_relevance=0.0,
                    average_quote_quality=0.0,
                    average_verification_agreement=0.5,
                    average_citation_count=0.0
                ),
                proposition_details=[],
                abstention_factors={},
                citation_validation_errors=[],
                total_citations=0,
                strong_citations=0,
                medium_citations=0,
                weak_citations=0
            )

    def _build_abstention_response(
        self,
        verified_response: VerifiedAnswerResponse,
        abstention_decision: AbstentionDecision
    ) -> EnhancedAnswerResponse:
        """
        Build abstention response when system decides not to answer.

        Args:
            verified_response: VerifiedAnswerResponse from Step 11.2
            abstention_decision: Abstention decision

        Returns:
            EnhancedAnswerResponse with abstained=True
        """
        # Generate user-facing abstention message
        abstention_message = self._generate_abstention_message(abstention_decision)

        # Build minimal enhanced metadata
        from app.schemas.citation_confidence import ConfidenceBreakdown
        enhanced_metadata = EnhancedMetadata(
            # Core verification fields
            status=verified_response.verification_metadata.status,
            hallucination_probability=verified_response.verification_metadata.hallucination_probability,
            propositions_checked=verified_response.verification_metadata.propositions_checked,
            propositions_verified=verified_response.verification_metadata.propositions_verified,
            propositions_removed=verified_response.verification_metadata.propositions_removed,
            quote_matches=verified_response.verification_metadata.quote_matches,
            verification_latency_ms=verified_response.verification_metadata.verification_latency_ms,
            fallback_to_baseline=verified_response.verification_metadata.fallback_to_baseline,
            failure_reason=verified_response.verification_metadata.failure_reason,
            # Enhanced fields
            confidence_breakdown=ConfidenceBreakdown(
                overall=0.0,
                average_passage_relevance=0.0,
                average_quote_quality=0.0,
                average_verification_agreement=0.0,
                average_citation_count=0.0
            ),
            proposition_details=[],
            abstention_factors={
                "low_confidence": "low_confidence" in abstention_decision.factors,
                "high_hallucination": "high_hallucination" in abstention_decision.factors,
                "no_evidence": "no_evidence" in abstention_decision.factors,
                "verification_failed": "verification_failed" in abstention_decision.factors,
            },
            citation_validation_errors=[],
            total_citations=0,
            strong_citations=0,
            medium_citations=0,
            weak_citations=0
        )

        return EnhancedAnswerResponse(
            # Core answer fields
            success=True,  # Abstention is a successful response
            answer="",
            verified_answer="",
            propositions=[],
            citations=[],
            confidence=0.0,
            verified_confidence=0.0,
            can_answer=False,
            abstention_reason=str(abstention_decision.reason.value),
            processing_time_ms=verified_response.processing_time_ms,
            passages_used=verified_response.passages_used,
            model_used=verified_response.model_used,
            cache_hit=False,
            # Step 11.3 enhancement fields
            abstained=True,
            abstention_message=abstention_message,
            enriched_citations=[],
            enhanced_metadata=enhanced_metadata
        )

    def _generate_abstention_message(
        self,
        abstention_decision: AbstentionDecision
    ) -> str:
        """
        Generate user-facing abstention message.

        Args:
            abstention_decision: Abstention decision with reason

        Returns:
            User-friendly abstention message
        """
        reason = abstention_decision.reason

        messages = {
            "low_confidence": (
                "I don't have enough confidence to answer this question accurately based on the available documents. "
                "Please try rephrasing your question or providing more specific documents."
            ),
            "high_hallucination": (
                "I cannot provide a reliable answer because the information I generated doesn't have strong support "
                "in the source documents. Please try asking a more specific question."
            ),
            "no_evidence": (
                "I couldn't find sufficient evidence in the documents to answer this question. "
                "The available documents may not contain the information you're looking for."
            ),
            "verification_failed": (
                "I encountered an error while verifying the answer against the source documents. "
                "Please try again or contact support if the issue persists."
            )
        }

        return messages.get(
            reason.value,
            "I cannot provide a reliable answer for this question at this time."
        )

    async def health_check(self) -> dict:
        """
        Health check for citation & confidence service.

        Returns:
            Health status dict with component checks
        """
        health_status = {
            "status": "healthy",
            "components": {}
        }

        # Check all sub-services
        try:
            abstention_health = await self.abstention_service.health_check()
            health_status["components"]["abstention_service"] = abstention_health.get("status", "healthy")
        except Exception as e:
            logger.error(f"Abstention service health check failed: {e}")
            health_status["components"]["abstention_service"] = "unhealthy"
            health_status["status"] = "degraded"

        # Confidence calculator (always healthy - pure logic)
        health_status["components"]["confidence_calculator"] = "healthy"

        # Citation enricher (always healthy - pure logic)
        health_status["components"]["citation_enricher"] = "healthy"

        # Metadata assembler (always healthy - pure logic)
        health_status["components"]["metadata_assembler"] = "healthy"

        return health_status


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

_citation_confidence_service: Optional[CitationConfidenceService] = None


def get_citation_confidence_service() -> CitationConfidenceService:
    """
    Get singleton CitationConfidenceService instance.

    Returns:
        CitationConfidenceService instance
    """
    global _citation_confidence_service

    if _citation_confidence_service is None:
        _citation_confidence_service = CitationConfidenceService()

    return _citation_confidence_service
