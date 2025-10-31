"""
Metadata Assembler for Step 11.3

Builds comprehensive EnhancedMetadata from:
- Verification metadata (Step 11.2)
- Per-proposition confidence scores
- Enriched citations
- Abstention decision

Assembles proposition details array, confidence breakdown, and abstention factors.
"""
from typing import Dict, List
import structlog

from app.schemas.verification import VerifiedAnswerResponse
from app.schemas.citation_confidence import (
    EnhancedMetadata,
    PropConfidence,
    EnrichedCitation,
    AbstentionDecision,
    PropositionDetail,
    ConfidenceBreakdown,
    CitationQuality
)

logger = structlog.get_logger(__name__)


class MetadataAssembler:
    """
    Metadata assembly service.

    Builds EnhancedMetadata by consolidating:
    1. Proposition details array (per-prop confidence, citations, verification status)
    2. Confidence breakdown (overall + per-factor averages)
    3. Abstention factors analysis
    4. Citation quality counts (strong/medium/weak)
    """

    def __init__(self):
        """Initialize metadata assembler."""
        logger.info("MetadataAssembler initialized")

    async def build(
        self,
        verified_response: VerifiedAnswerResponse,
        prop_confidences: Dict[str, PropConfidence],
        enriched_citations: List[EnrichedCitation],
        abstention_decision: AbstentionDecision
    ) -> EnhancedMetadata:
        """
        Build comprehensive enhanced metadata.

        Args:
            verified_response: VerifiedAnswerResponse from Step 11.2
            prop_confidences: Dict of proposition confidences
            enriched_citations: List of enriched citations
            abstention_decision: Abstention decision

        Returns:
            EnhancedMetadata with all enhancement details
        """
        logger.debug(
            "Building enhanced metadata",
            propositions_count=len(verified_response.propositions),
            citations_count=len(enriched_citations)
        )

        # Build proposition details array
        proposition_details = self._build_proposition_details(
            verified_response.propositions,
            prop_confidences,
            verified_response.verification_metadata.quote_matches,
            enriched_citations
        )

        # Build confidence breakdown
        confidence_breakdown = self._build_confidence_breakdown(prop_confidences)

        # Build abstention factors
        abstention_factors = self._build_abstention_factors(abstention_decision)

        # Count citation quality distribution
        total_citations = len(enriched_citations)
        strong_citations = sum(1 for c in enriched_citations if c.quality == CitationQuality.STRONG)
        medium_citations = sum(1 for c in enriched_citations if c.quality == CitationQuality.MEDIUM)
        weak_citations = sum(1 for c in enriched_citations if c.quality == CitationQuality.WEAK)

        # Validate citations (future enhancement)
        citation_validation_errors = []

        # Build enhanced metadata
        enhanced_metadata = EnhancedMetadata(
            # Core verification fields (from Step 11.2)
            status=verified_response.verification_metadata.status,
            hallucination_probability=verified_response.verification_metadata.hallucination_probability,
            propositions_checked=verified_response.verification_metadata.propositions_checked,
            propositions_verified=verified_response.verification_metadata.propositions_verified,
            propositions_removed=verified_response.verification_metadata.propositions_removed,
            quote_matches=verified_response.verification_metadata.quote_matches,
            verification_latency_ms=verified_response.verification_metadata.verification_latency_ms,
            fallback_to_baseline=verified_response.verification_metadata.fallback_to_baseline,
            failure_reason=verified_response.verification_metadata.failure_reason,
            # Enhanced fields (NEW in Step 11.3)
            confidence_breakdown=confidence_breakdown,
            proposition_details=proposition_details,
            abstention_factors=abstention_factors,
            citation_validation_errors=citation_validation_errors,
            total_citations=total_citations,
            strong_citations=strong_citations,
            medium_citations=medium_citations,
            weak_citations=weak_citations
        )

        logger.debug(
            "Enhanced metadata built successfully",
            total_citations=total_citations,
            strong_citations=strong_citations,
            overall_confidence=confidence_breakdown.overall
        )

        return enhanced_metadata

    def _build_proposition_details(
        self,
        propositions: List[Dict],
        prop_confidences: Dict[str, PropConfidence],
        quote_matches: Dict[str, List[Dict]],
        enriched_citations: List[EnrichedCitation]
    ) -> List[PropositionDetail]:
        """
        Build per-proposition details array.

        Args:
            propositions: List of proposition dicts
            prop_confidences: Dict of proposition confidences
            quote_matches: Quote matches dict from verification metadata
            enriched_citations: List of enriched citations

        Returns:
            List of PropositionDetail objects
        """
        proposition_details = []

        for proposition in propositions:
            # Get proposition ID
            if isinstance(proposition, dict):
                prop_id = str(proposition.get('index', proposition.get('id', 'unknown')))
                prop_text = proposition.get('text', '')
            else:
                prop_id = str(getattr(proposition, 'index', getattr(proposition, 'id', 'unknown')))
                prop_text = getattr(proposition, 'text', '')

            # Get confidence for this proposition
            prop_confidence = prop_confidences.get(prop_id)
            if not prop_confidence:
                # Fallback
                logger.warning(f"No confidence found for proposition {prop_id}, using defaults")
                confidence = 0.5
                confidence_breakdown = {
                    "passage_relevance": 0.0,
                    "quote_quality": 0.0,
                    "verification_agreement": 0.5,
                    "citation_count": 0.0
                }
            else:
                confidence = prop_confidence.confidence
                confidence_breakdown = prop_confidence.breakdown

            # Check if has quote matches
            prop_quotes = quote_matches.get(prop_id, [])
            has_quote = len(prop_quotes) > 0

            # Get best quote similarity
            quote_similarity = None
            if has_quote:
                similarities = []
                for qm_data in prop_quotes:
                    if isinstance(qm_data, dict):
                        sim = qm_data.get('similarity_score', 0.0)
                    else:
                        sim = getattr(qm_data, 'similarity_score', 0.0)
                    similarities.append(sim)

                quote_similarity = max(similarities) if similarities else None

            # Determine if verified (simple heuristic: has_quote and confidence > 0.5)
            verified = has_quote and confidence > 0.5

            # Find which citations support this proposition
            # For now, we'll use all citations (would need better mapping)
            citation_numbers = [c.citation_number for c in enriched_citations]

            # Determine best quality indicator
            quality_indicator = None
            if has_quote and enriched_citations:
                # Find best quality among citations
                qualities = [c.quality for c in enriched_citations]
                if CitationQuality.STRONG in qualities:
                    quality_indicator = CitationQuality.STRONG
                elif CitationQuality.MEDIUM in qualities:
                    quality_indicator = CitationQuality.MEDIUM
                elif CitationQuality.WEAK in qualities:
                    quality_indicator = CitationQuality.WEAK

            # Build proposition detail
            prop_detail = PropositionDetail(
                proposition_id=prop_id,
                text=prop_text,
                confidence=confidence,
                confidence_breakdown=confidence_breakdown,
                has_quote=has_quote,
                quote_similarity=quote_similarity,
                verified=verified,
                citations=citation_numbers,
                quality_indicator=quality_indicator
            )

            proposition_details.append(prop_detail)

        return proposition_details

    def _build_confidence_breakdown(
        self,
        prop_confidences: Dict[str, PropConfidence]
    ) -> ConfidenceBreakdown:
        """
        Build overall confidence breakdown.

        Args:
            prop_confidences: Dict of proposition confidences

        Returns:
            ConfidenceBreakdown with aggregated factors
        """
        if not prop_confidences:
            return ConfidenceBreakdown(
                overall=0.0,
                average_passage_relevance=0.0,
                average_quote_quality=0.0,
                average_verification_agreement=0.0,
                average_citation_count=0.0
            )

        num_props = len(prop_confidences)

        # Calculate averages
        avg_passage_rel = sum(
            pc.breakdown.get("passage_relevance", 0.0) for pc in prop_confidences.values()
        ) / num_props

        avg_quote_qual = sum(
            pc.breakdown.get("quote_quality", 0.0) for pc in prop_confidences.values()
        ) / num_props

        avg_verif_agree = sum(
            pc.breakdown.get("verification_agreement", 0.0) for pc in prop_confidences.values()
        ) / num_props

        avg_cite_count = sum(
            pc.breakdown.get("citation_count", 0.0) for pc in prop_confidences.values()
        ) / num_props

        # Calculate overall (weighted average of proposition confidences)
        overall = sum(pc.confidence for pc in prop_confidences.values()) / num_props

        return ConfidenceBreakdown(
            overall=round(overall, 3),
            average_passage_relevance=round(avg_passage_rel, 3),
            average_quote_quality=round(avg_quote_qual, 3),
            average_verification_agreement=round(avg_verif_agree, 3),
            average_citation_count=round(avg_cite_count, 3)
        )

    def _build_abstention_factors(
        self,
        abstention_decision: AbstentionDecision
    ) -> Dict[str, bool]:
        """
        Build abstention factors dict.

        Args:
            abstention_decision: Abstention decision

        Returns:
            Dict with factor names → boolean (triggered or not)
        """
        return {
            "low_confidence": "low_confidence" in abstention_decision.factors,
            "high_hallucination": "high_hallucination" in abstention_decision.factors,
            "no_evidence": "no_evidence" in abstention_decision.factors,
            "verification_failed": "verification_failed" in abstention_decision.factors,
        }
