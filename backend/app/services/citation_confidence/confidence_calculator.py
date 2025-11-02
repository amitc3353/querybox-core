"""
Confidence Calculator for Step 11.3

Granular confidence calculator for propositions and overall answer using
weighted 4-factor algorithm:
1. Passage relevance (40%): Best rerank score from Step 10.2
2. Quote quality (35%): Best quote similarity score from quote matching
3. Verification agreement (15%): Independent verification confirms claim
4. Citation count (10%): Number of supporting sources (diversity)
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
import re
import structlog

from app.schemas.verification import VerifiedAnswerResponse, QuoteMatch, VerificationAnswer
from app.schemas.citation_confidence import PropConfidence, ConfidenceBreakdown
from app.core.config import settings
from app.core.verification_profiles import get_active_profile, VerificationProfile

logger = structlog.get_logger(__name__)


@dataclass
class ConfidenceWeights:
    """Weights for confidence calculation factors."""
    passage_relevance: float = 0.40
    quote_quality: float = 0.35
    verification_agreement: float = 0.15
    citation_count: float = 0.10

    def __post_init__(self):
        """Validate weights sum to 1.0."""
        total = (
            self.passage_relevance +
            self.quote_quality +
            self.verification_agreement +
            self.citation_count
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


class ConfidenceCalculator:
    """
    Granular confidence calculator for propositions and overall answer.

    Implements weighted 4-factor algorithm:
    1. Passage relevance (40%): Best rerank score from Step 10.2
    2. Quote quality (35%): Best quote similarity score from quote matching
    3. Verification agreement (15%): Independent verification confirms claim
    4. Citation count (10%): Number of supporting sources (diversity)
    """

    def __init__(self, weights: Optional[ConfidenceWeights] = None, profile: Optional[VerificationProfile] = None):
        """
        Initialize confidence calculator with weights.

        Args:
            weights: Custom weights (overrides profile weights if provided)
            profile: VerificationProfile to use (loads from settings if not provided)
        """
        # Load profile
        self.profile = profile or get_active_profile()

        # Use custom weights if provided, otherwise load from profile
        if weights:
            self.weights = weights
        else:
            self.weights = ConfidenceWeights(
                passage_relevance=self.profile.confidence_passage_relevance_weight,
                quote_quality=self.profile.confidence_quote_quality_weight,
                verification_agreement=self.profile.confidence_verification_agreement_weight,
                citation_count=self.profile.confidence_citation_count_weight,
            )

        logger.info(
            "ConfidenceCalculator initialized",
            verification_level=self.profile.level.value,
            weights=self.weights
        )

    async def calculate_all(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> Dict[str, PropConfidence]:
        """
        Calculate confidence for all propositions.

        Args:
            verified_response: VerifiedAnswerResponse from Step 11.2

        Returns:
            Dict mapping proposition_id → PropConfidence

        Complexity: O(P) where P = propositions (3-5 typically)
        Time: ~50-80ms for 3-5 propositions
        """
        logger.debug(
            "Calculating confidence for all propositions",
            propositions_count=len(verified_response.propositions)
        )

        prop_confidences = {}

        for proposition in verified_response.propositions:
            # Get proposition ID (handle dict format from VerifiedAnswerResponse)
            if isinstance(proposition, dict):
                prop_id = str(proposition.get('index', proposition.get('id', 'unknown')))
                prop_text = proposition.get('text', '')
            else:
                prop_id = str(getattr(proposition, 'index', getattr(proposition, 'id', 'unknown')))
                prop_text = getattr(proposition, 'text', '')

            # Get quote matches for this proposition
            quote_matches_data = verified_response.verification_metadata.quote_matches.get(
                prop_id, []
            )

            # Convert dict quote matches to QuoteMatch objects
            quote_matches = []
            for qm_data in quote_matches_data:
                if isinstance(qm_data, dict):
                    try:
                        quote_matches.append(QuoteMatch(**qm_data))
                    except Exception as e:
                        logger.warning(f"Failed to parse quote match: {e}")
                else:
                    quote_matches.append(qm_data)

            # Get verification answer for this proposition (if available)
            # Note: In current implementation, verification_answers may not be stored
            # We'll use a placeholder for now
            verification_answer = None  # TODO: Link to actual verification answers

            # Get citations for this proposition
            # For now, use all citations (would need proposition_ids mapping)
            citations = verified_response.citations

            # Calculate confidence
            try:
                prop_confidence = await self.calculate_proposition_confidence(
                    proposition_id=prop_id,
                    proposition_text=prop_text,
                    quote_matches=quote_matches,
                    verification_answer=verification_answer,
                    citations=citations,
                    hallucination_probability=verified_response.verification_metadata.hallucination_probability or 0.0
                )
                prop_confidences[prop_id] = prop_confidence
            except Exception as e:
                logger.error(
                    "Confidence calculation failed for proposition",
                    prop_id=prop_id,
                    error=str(e)
                )
                # Fallback: Use neutral confidence
                prop_confidences[prop_id] = PropConfidence(
                    proposition_id=prop_id,
                    confidence=0.5,
                    breakdown={
                        "passage_relevance": 0.0,
                        "quote_quality": 0.0,
                        "verification_agreement": 0.5,
                        "citation_count": 0.0
                    },
                    is_fallback=True
                )

        logger.debug(
            "Confidence calculation completed",
            avg_confidence=sum(pc.confidence for pc in prop_confidences.values()) / len(prop_confidences) if prop_confidences else 0
        )

        return prop_confidences

    async def calculate_proposition_confidence(
        self,
        proposition_id: str,
        proposition_text: str,
        quote_matches: List[QuoteMatch],
        verification_answer: Optional[VerificationAnswer],
        citations: List[Dict],
        hallucination_probability: float = 0.0
    ) -> PropConfidence:
        """
        Calculate confidence for a single proposition using 4-factor weighted algorithm.

        Algorithm:
        1. Passage Relevance (40%): Use best (max) relevance score from citations
        2. Quote Match Quality (35%): Use best (max) similarity score from quote matches
        3. Verification Agreement (15%): 1.0 if confirms, 0.5 if neutral, 0.0 if denies
        4. Citation Count (10%): Score = min(1.0, len(citations) / 3.0)

        Final confidence = weighted_sum(factors) * (1 - hallucination_probability)

        Args:
            proposition_id: Proposition identifier
            proposition_text: Proposition text for verification agreement check
            quote_matches: List of quote matches for this proposition
            verification_answer: Verification answer for this proposition (optional)
            citations: List of citations (as dicts)
            hallucination_probability: Overall hallucination probability from Step 11.2

        Returns:
            PropConfidence with score and factor breakdown

        Complexity: O(C + Q) where C = citations, Q = quote matches
        Time: ~5-10ms per proposition
        """
        # Factor 1: Passage Relevance (40%)
        passage_relevance = self._calculate_passage_relevance_score(citations)

        # Factor 2: Quote Match Quality (35%)
        quote_quality = self._calculate_quote_match_score(quote_matches)

        # Factor 3: Verification Agreement (15%)
        verif_agreement = self._calculate_verification_agreement_score(
            proposition_text,
            verification_answer
        )

        # Factor 4: Citation Count (10%)
        cite_count_score = self._calculate_citation_count_score(citations)

        # Weighted sum
        raw_confidence = (
            self.weights.passage_relevance * passage_relevance +
            self.weights.quote_quality * quote_quality +
            self.weights.verification_agreement * verif_agreement +
            self.weights.citation_count * cite_count_score
        )

        # Apply hallucination penalty
        final_confidence = raw_confidence * (1 - hallucination_probability)

        # Ensure confidence is in valid range [0, 1]
        final_confidence = max(0.0, min(1.0, final_confidence))

        # Build breakdown
        breakdown = {
            "passage_relevance": round(passage_relevance, 3),
            "quote_quality": round(quote_quality, 3),
            "verification_agreement": round(verif_agreement, 3),
            "citation_count": round(cite_count_score, 3),
        }

        logger.debug(
            "Proposition confidence calculated",
            proposition_id=proposition_id,
            confidence=round(final_confidence, 3),
            **breakdown
        )

        return PropConfidence(
            proposition_id=proposition_id,
            confidence=round(final_confidence, 3),
            breakdown=breakdown,
            is_fallback=False
        )

    def _calculate_passage_relevance_score(self, citations: List[Dict]) -> float:
        """
        Factor 1: Passage relevance score.

        Use maximum relevance score from all citations.

        Args:
            citations: List of citation dicts

        Returns:
            Max relevance score (0.0-1.0)
        """
        if not citations:
            return 0.0

        relevance_scores = []
        for citation in citations:
            if isinstance(citation, dict):
                score = citation.get('relevance_score', 0.0)
            else:
                score = getattr(citation, 'relevance_score', 0.0)

            if score is not None:
                relevance_scores.append(score)

        if not relevance_scores:
            return 0.0

        return max(relevance_scores)

    def _calculate_quote_match_score(self, quote_matches: List[QuoteMatch]) -> float:
        """
        Factor 2: Quote match quality score.

        Use maximum similarity score from all quote matches.

        Args:
            quote_matches: List of QuoteMatch objects

        Returns:
            Max similarity score (0.0-1.0)
        """
        if not quote_matches:
            return 0.0

        similarity_scores = [qm.similarity_score for qm in quote_matches]
        if not similarity_scores:
            return 0.0

        return max(similarity_scores)

    def _calculate_verification_agreement_score(
        self,
        proposition_text: str,
        verification_answer: Optional[VerificationAnswer]
    ) -> float:
        """
        Factor 3: Verification agreement score.

        Scoring:
        - 1.0: Verification confirms (contains "YES", "CORRECT", "TRUE")
        - 0.5: Neutral (contains "CANNOT DETERMINE", fallback answer, or no verification)
        - 0.0: Verification denies (contains "NO", "INCORRECT", "FALSE")

        Args:
            proposition_text: Proposition text
            verification_answer: Verification answer (optional)

        Returns:
            Agreement score (0.0-1.0)
        """
        if not verification_answer or not verification_answer.answer:
            return 0.5  # Neutral if no verification

        answer_lower = verification_answer.answer.lower()

        # Check for denial FIRST (to catch "incorrect" before "correct")
        if any(keyword in answer_lower for keyword in ["incorrect", "false", "not mentioned"]):
            return 0.0

        # Check for "no" as a word boundary (not substring)
        if re.search(r'\bno\b', answer_lower):
            return 0.0

        # Check for confirmation
        if any(keyword in answer_lower for keyword in ["yes", "correct", "true", "confirmed"]):
            return 1.0

        # Check for neutral/uncertain
        if any(keyword in answer_lower for keyword in ["cannot determine", "unsure", "unclear"]):
            return 0.5

        # Default: Use word overlap as proxy for agreement
        prop_words = set(proposition_text.lower().split())
        verif_words = set(answer_lower.split())

        if not prop_words:
            return 0.5

        overlap = len(prop_words & verif_words) / len(prop_words)

        # Scale overlap to [0, 1] with generous scaling
        return min(1.0, overlap * 2)

    def _calculate_citation_count_score(self, citations: List[Dict]) -> float:
        """
        Factor 4: Citation count score.

        Score = min(1.0, len(citations) / 3.0)

        Rationale:
        - 1 citation: 0.33
        - 2 citations: 0.67
        - 3+ citations: 1.0 (capped)

        Diminishing returns after 3 sources.

        Args:
            citations: List of citation dicts

        Returns:
            Citation count score (0.0-1.0)
        """
        return min(1.0, len(citations) / 3.0)

    def aggregate_to_overall_confidence(
        self,
        prop_confidences: Dict[str, PropConfidence]
    ) -> float:
        """
        Aggregate per-proposition confidences to overall verified confidence.

        Strategy: Weighted average (all props equal weight)

        Alternative strategies:
        - Minimum (conservative): Use lowest proposition confidence
        - Probabilistic: 1 - product(1 - conf_i) for all i

        Args:
            prop_confidences: Dict of proposition confidences

        Returns:
            Overall confidence score [0, 1]
        """
        if not prop_confidences:
            return 0.0

        # Weighted average (all props equal weight)
        avg_confidence = sum(pc.confidence for pc in prop_confidences.values()) / len(prop_confidences)

        return round(avg_confidence, 3)

    def build_confidence_breakdown(
        self,
        prop_confidences: Dict[str, PropConfidence]
    ) -> ConfidenceBreakdown:
        """
        Build overall confidence breakdown from per-proposition confidences.

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

        # Calculate averages
        num_props = len(prop_confidences)

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

        overall = self.aggregate_to_overall_confidence(prop_confidences)

        return ConfidenceBreakdown(
            overall=overall,
            average_passage_relevance=round(avg_passage_rel, 3),
            average_quote_quality=round(avg_quote_qual, 3),
            average_verification_agreement=round(avg_verif_agree, 3),
            average_citation_count=round(avg_cite_count, 3)
        )
