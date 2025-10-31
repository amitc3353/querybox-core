"""
Abstention Service for Step 11.3

Multi-factor abstention decision engine that determines whether to abstain
from answering based on confidence, hallucination, evidence, and verification status.

Philosophy: Better to say "I don't know" than provide wrong answer.
"""
from typing import List
import structlog

from app.schemas.verification import VerifiedAnswerResponse
from app.schemas.citation_confidence import AbstentionDecision, AbstentionReason
from app.core.config import settings

logger = structlog.get_logger(__name__)


class AbstentionService:
    """
    Multi-factor abstention decision engine.

    Decides whether to abstain from answering based on:
    1. Low confidence (<0.3 by default)
    2. High hallucination probability (>0.7 by default)
    3. No supporting evidence (no quote matches)
    4. Verification failed

    Abstention philosophy: Better to say "I don't know" than provide wrong answer.
    """

    def __init__(
        self,
        low_confidence_threshold: float = None,
        high_hallucination_threshold: float = None
    ):
        """
        Initialize abstention service with thresholds.

        Args:
            low_confidence_threshold: Threshold for low confidence abstention (default from settings)
            high_hallucination_threshold: Threshold for high hallucination abstention (default from settings)
        """
        self.low_confidence_threshold = low_confidence_threshold or getattr(
            settings, 'LOW_CONFIDENCE_THRESHOLD', 0.3
        )
        self.high_hallucination_threshold = high_hallucination_threshold or getattr(
            settings, 'HIGH_HALLUCINATION_THRESHOLD', 0.7
        )

        logger.info(
            "AbstentionService initialized",
            low_confidence_threshold=self.low_confidence_threshold,
            high_hallucination_threshold=self.high_hallucination_threshold,
        )

    async def should_abstain(
        self,
        verified_response: VerifiedAnswerResponse
    ) -> AbstentionDecision:
        """
        Multi-factor abstention decision.

        Decision Logic:
        - If ANY critical factor triggered → ABSTAIN
        - Categorize primary reason
        - Calculate abstention confidence (how sure we can't answer)

        Args:
            verified_response: VerifiedAnswerResponse from Step 11.2

        Returns:
            AbstentionDecision with should_abstain, reason, factors

        Complexity: O(P) where P = propositions
        Time: <10ms
        """
        factors_triggered = []

        # Factor 1: Low confidence check
        try:
            if self._check_low_confidence(verified_response):
                factors_triggered.append("low_confidence")
                logger.debug(
                    "Low confidence factor triggered",
                    verified_confidence=verified_response.verified_confidence
                )
        except Exception as e:
            logger.error("Low confidence check failed", error=str(e))
            # Conservative: Treat error as triggered
            factors_triggered.append("low_confidence")

        # Factor 2: High hallucination check
        try:
            if self._check_high_hallucination(verified_response):
                factors_triggered.append("high_hallucination")
                logger.debug(
                    "High hallucination factor triggered",
                    hallucination_probability=verified_response.verification_metadata.hallucination_probability
                )
        except Exception as e:
            logger.error("High hallucination check failed", error=str(e))
            factors_triggered.append("high_hallucination")

        # Factor 3: No evidence check
        try:
            if self._check_no_quotes(verified_response):
                factors_triggered.append("no_evidence")
                logger.debug("No evidence factor triggered")
        except Exception as e:
            logger.error("No evidence check failed", error=str(e))
            factors_triggered.append("no_evidence")

        # Factor 4: Verification failed check
        try:
            if self._check_verification_failed(verified_response):
                factors_triggered.append("verification_failed")
                logger.debug("Verification failed factor triggered")
        except Exception as e:
            logger.error("Verification failed check failed", error=str(e))
            factors_triggered.append("verification_failed")

        # Decision
        if factors_triggered:
            reason = self._categorize_reason(factors_triggered)
            confidence = self._calculate_abstention_confidence(factors_triggered)

            logger.info(
                "Abstention decision: ABSTAIN",
                reason=reason,
                factors=factors_triggered,
                confidence=confidence,
            )

            return AbstentionDecision(
                should_abstain=True,
                reason=reason,
                factors=factors_triggered,
                confidence=confidence
            )
        else:
            logger.debug("Abstention decision: ANSWER")
            return AbstentionDecision(should_abstain=False)

    def _check_low_confidence(self, verified_response: VerifiedAnswerResponse) -> bool:
        """
        Check if verified confidence below threshold.

        Returns:
            True if confidence is too low to answer reliably
        """
        return (
            verified_response.verified_confidence is not None and
            verified_response.verified_confidence < self.low_confidence_threshold
        )

    def _check_high_hallucination(self, verified_response: VerifiedAnswerResponse) -> bool:
        """
        Check if hallucination probability above threshold.

        Returns:
            True if hallucination risk is too high
        """
        return (
            verified_response.verification_metadata.hallucination_probability is not None and
            verified_response.verification_metadata.hallucination_probability > self.high_hallucination_threshold
        )

    def _check_no_quotes(self, verified_response: VerifiedAnswerResponse) -> bool:
        """
        Check if all propositions lack quote matches.

        Returns:
            True if no supporting evidence found
        """
        quote_matches = verified_response.verification_metadata.quote_matches
        if not quote_matches:
            return True

        # Check if all propositions have empty quote lists
        return all(len(matches) == 0 for matches in quote_matches.values())

    def _check_verification_failed(self, verified_response: VerifiedAnswerResponse) -> bool:
        """
        Check if verification process failed.

        Returns:
            True if verification encountered errors
        """
        return verified_response.verification_metadata.status == "failed"

    def _categorize_reason(self, factors_triggered: List[str]) -> AbstentionReason:
        """
        Categorize abstention reason from triggered factors.

        Priority order:
        1. verification_failed (most critical)
        2. high_hallucination
        3. low_confidence
        4. no_evidence

        Args:
            factors_triggered: List of factor names that triggered

        Returns:
            Primary AbstentionReason
        """
        if "verification_failed" in factors_triggered:
            return AbstentionReason.VERIFICATION_FAILED
        elif "high_hallucination" in factors_triggered:
            return AbstentionReason.HIGH_HALLUCINATION
        elif "low_confidence" in factors_triggered:
            return AbstentionReason.LOW_CONFIDENCE
        elif "no_evidence" in factors_triggered:
            return AbstentionReason.NO_EVIDENCE
        else:
            # Should not reach here
            return AbstentionReason.LOW_CONFIDENCE

    def _calculate_abstention_confidence(self, factors_triggered: List[str]) -> float:
        """
        Calculate confidence in abstention decision.

        More factors triggered = higher confidence in abstention.

        Score:
        - 1 factor: 0.6
        - 2 factors: 0.8
        - 3+ factors: 1.0

        Args:
            factors_triggered: List of factor names

        Returns:
            Confidence score (0.0-1.0) in abstention decision
        """
        count = len(factors_triggered)
        if count >= 3:
            return 1.0
        elif count == 2:
            return 0.8
        elif count == 1:
            return 0.6
        else:
            return 0.0  # No abstention

    async def health_check(self) -> dict:
        """
        Health check for abstention service.

        Returns:
            Health status dict
        """
        return {
            "status": "healthy",
            "low_confidence_threshold": self.low_confidence_threshold,
            "high_hallucination_threshold": self.high_hallucination_threshold,
        }
