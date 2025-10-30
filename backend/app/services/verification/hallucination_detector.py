"""
Hallucination Detector for Step 11.2 - Chain-of-Verification

Detects hallucinations by comparing baseline answers with verification results
and quote coverage.

Implements Stage 5 of verification pipeline.
"""
from typing import List, Dict
import logging

from app.schemas.verification import (
    HallucinationReport,
    VerificationAnswer,
    QuoteMatch
)
from app.schemas.answer import Proposition
from app.utils.text_matching import normalize_text, calculate_word_overlap

logger = logging.getLogger(__name__)


class HallucinationDetector:
    """
    Detect hallucinations in generated answers.

    Uses three-factor scoring:
    1. Quote coverage: Does proposition have supporting quote? (weight: 0.5)
    2. Verification agreement: Do independent answers match? (weight: 0.3)
    3. Semantic contradiction: Do answers contradict? (weight: 0.2)

    Based on technical documentation Section 2 (hallucination detection algorithm).
    """

    def __init__(self, ollama_client=None):
        """
        Initialize hallucination detector.

        Args:
            ollama_client: Optional OllamaClient for LLM-based contradiction detection.
                          If None, uses heuristic-based detection only.
        """
        self.ollama_client = ollama_client

        # Scoring weights
        self.quote_coverage_weight = 0.5
        self.verification_agreement_weight = 0.3
        self.semantic_contradiction_weight = 0.2

        logger.info(
            "HallucinationDetector initialized "
            f"(LLM-based contradiction: {ollama_client is not None})"
        )

    async def detect_hallucinations(
        self,
        baseline_answer: str,
        baseline_propositions: List[Proposition],
        verification_answers: List[VerificationAnswer],
        quote_matches: Dict[int, List[QuoteMatch]]
    ) -> HallucinationReport:
        """
        Detect hallucinations in baseline answer.

        Complexity: O(N) where N = number of propositions (typically 3-5)
        Time: ~100-200ms (includes optional LLM call for contradiction check)

        Args:
            baseline_answer: Original generated answer
            baseline_propositions: Propositions extracted from baseline
            verification_answers: Independent verification answers
            quote_matches: Quote matches per proposition index

        Returns:
            HallucinationReport with probability and flagged propositions

        Example:
            >>> report = await detector.detect_hallucinations(
            ...     "Paris is the capital of France.",
            ...     [Proposition(text="Paris is capital", index=0)],
            ...     [VerificationAnswer(question_id="vq1", answer="YES", ...)],
            ...     {0: [QuoteMatch(...)] }
            ... )
            >>> report.hallucination_probability < 0.3
            True
        """
        logger.info(
            f"Detecting hallucinations for {len(baseline_propositions)} propositions"
        )

        hallucination_score = 0.0
        flagged_proposition_indices = []
        contradiction_details = {}

        for prop in baseline_propositions:
            prop_index = prop.index

            # Factor 1: Quote coverage (weight: 0.5)
            quote_coverage_score = self._calculate_quote_coverage_score(
                prop_index,
                quote_matches
            )

            if quote_coverage_score == 0:
                # No quotes found - major hallucination indicator
                hallucination_score += self.quote_coverage_weight
                flagged_proposition_indices.append(prop_index)

                logger.warning(
                    f"Proposition {prop_index} has no supporting quotes",
                    extra={"proposition_text": prop.text[:50]}
                )
                continue  # Skip other checks if no quotes

            # Factor 2: Verification agreement (weight: 0.3)
            verification_agreement_score = self._calculate_verification_agreement_score(
                prop,
                verification_answers
            )

            if verification_agreement_score > 0:
                hallucination_score += verification_agreement_score
                logger.debug(
                    f"Proposition {prop_index} has verification disagreement",
                    extra={"score": verification_agreement_score}
                )

            # Factor 3: Semantic contradiction (weight: 0.2)
            if self.ollama_client:
                contradiction_score, contradiction_detail = await self._check_contradiction(
                    prop,
                    verification_answers
                )

                if contradiction_score > 0:
                    hallucination_score += contradiction_score
                    contradiction_details[str(prop_index)] = contradiction_detail

                    logger.warning(
                        f"Proposition {prop_index} has contradiction",
                        extra={"detail": contradiction_detail}
                    )

        # Normalize hallucination probability (max 1.0)
        hallucination_probability = min(1.0, hallucination_score)

        # Calculate confidence adjustment
        confidence_adjustment = self._calculate_confidence_adjustment(
            hallucination_probability
        )

        logger.info(
            f"Hallucination detection complete: probability={hallucination_probability:.2f}, "
            f"flagged={len(flagged_proposition_indices)}"
        )

        return HallucinationReport(
            hallucination_probability=hallucination_probability,
            flagged_proposition_indices=flagged_proposition_indices,
            confidence_adjustment=confidence_adjustment,
            contradiction_details=contradiction_details if contradiction_details else None
        )

    def _calculate_quote_coverage_score(
        self,
        prop_index: int,
        quote_matches: Dict[int, List[QuoteMatch]]
    ) -> float:
        """
        Calculate quote coverage score for proposition.

        Args:
            prop_index: Proposition index
            quote_matches: Quote matches per proposition index

        Returns:
            Score (0 = no quotes, 1 = has quotes)
        """
        if prop_index not in quote_matches or not quote_matches[prop_index]:
            return 0.0  # No quotes found

        # Has at least one quote match above threshold
        return 1.0

    def _calculate_verification_agreement_score(
        self,
        proposition: Proposition,
        verification_answers: List[VerificationAnswer]
    ) -> float:
        """
        Calculate verification agreement score.

        Checks if verification answers agree with the proposition.

        Args:
            proposition: Proposition to check
            verification_answers: List of verification answers

        Returns:
            Score (0 = agreement, 0.3 = disagreement)
        """
        # Find verification answer for this proposition
        target_verification = None
        for ver_answer in verification_answers:
            # Match by proposition index (encoded in question_id)
            if f"_{proposition.index}" in ver_answer.question_id or \
               len(verification_answers) == 1:  # Single proposition case
                target_verification = ver_answer
                break

        if not target_verification:
            # No verification found - neutral
            return 0.0

        # Check if verification answer indicates disagreement
        answer_lower = target_verification.answer.lower()

        # Negative indicators
        if any(indicator in answer_lower for indicator in [
            'no', 'not', 'cannot', 'unable', 'incorrect', 'false'
        ]):
            return self.verification_agreement_weight

        # Check for word overlap between proposition and verification answer
        overlap = calculate_word_overlap(
            proposition.text,
            target_verification.answer
        )

        # Low overlap indicates disagreement
        if overlap < 0.3:
            return self.verification_agreement_weight * 0.5

        return 0.0  # Agreement

    async def _check_contradiction(
        self,
        proposition: Proposition,
        verification_answers: List[VerificationAnswer]
    ) -> tuple[float, str]:
        """
        Check for semantic contradictions using LLM.

        Args:
            proposition: Proposition to check
            verification_answers: List of verification answers

        Returns:
            (contradiction_score, contradiction_detail) tuple
        """
        # Find relevant verification answer
        target_verification = None
        for ver_answer in verification_answers:
            if f"_{proposition.index}" in ver_answer.question_id or \
               len(verification_answers) == 1:
                target_verification = ver_answer
                break

        if not target_verification:
            return 0.0, ""

        try:
            prompt = self._build_contradiction_check_prompt(
                proposition.text,
                target_verification.answer
            )

            response = await self.ollama_client.generate(
                prompt=prompt,
                temperature=0.1,  # Very deterministic
                max_tokens=100,
            )

            result = response["response"].strip().lower()

            if "contradict" in result or "disagree" in result or "inconsistent" in result:
                return self.semantic_contradiction_weight, result
            else:
                return 0.0, ""

        except Exception as e:
            logger.error(f"Contradiction check failed: {e}")
            return 0.0, ""

    def _build_contradiction_check_prompt(
        self,
        proposition: str,
        verification_answer: str
    ) -> str:
        """
        Build prompt for LLM contradiction detection.

        Args:
            proposition: Original proposition
            verification_answer: Verification answer

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a fact-checking assistant. Determine if there is a contradiction between these two statements.

STATEMENT 1 (Claim): {proposition}

STATEMENT 2 (Verification): {verification_answer}

Do these statements contradict each other? Answer with one of:
- "AGREE" if they are consistent
- "CONTRADICT" if they disagree
- "UNCERTAIN" if unclear

Answer in one word only.

ANSWER:"""

        return prompt

    def _calculate_confidence_adjustment(
        self,
        hallucination_probability: float
    ) -> float:
        """
        Calculate confidence adjustment based on hallucination probability.

        Args:
            hallucination_probability: Hallucination probability (0-1)

        Returns:
            Confidence adjustment (-1 to 0)
        """
        # Linear scaling: higher hallucination = lower confidence
        # hallu_prob = 0 → adjustment = 0 (no change)
        # hallu_prob = 1 → adjustment = -0.5 (reduce confidence by 50%)

        adjustment = -hallucination_probability * 0.5

        return round(adjustment, 2)
