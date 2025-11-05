"""
Verification Service for Step 11.2 - Chain-of-Verification

Orchestrates the 6-stage verification pipeline to reduce LLM hallucinations.
Based on Meta AI research: Chain-of-Verification (arXiv 2309.11495).

Implements:
- Baseline answer generation (reuses Step 11.1)
- Verification question planning
- Independent verification execution
- Exact quote matching against source passages
- Hallucination detection
- Final verified response construction
"""
import asyncio
import hashlib
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
from uuid import uuid4

from redis import Redis

from app.services.ollama_client import OllamaClient, OllamaError, get_ollama_client
from app.services.answer_service import AnswerService
from app.services.verification.quote_matching_service import QuoteMatchingService
from app.services.verification.verification_question_generator import VerificationQuestionGenerator
from app.services.verification.hallucination_detector import HallucinationDetector
from app.schemas.answer import AnswerRequest, AnswerResponse, Proposition
from app.schemas.verification import (
    VerifiedAnswerResponse,
    VerificationMetadata,
    VerificationQuestion,
    VerificationAnswer,
    QuoteMatch,
    HallucinationReport,
    Passage
)
from app.core.config import settings
from app.core.logging import get_logger
from app.core.metrics import VerificationMetricsRecorder
from app.core.verification_profiles import get_active_profile, VerificationProfile

logger = get_logger(__name__)


class VerificationService:
    """
    Chain-of-Verification service for reducing LLM hallucinations.

    Implements a 6-stage pipeline:
    1. Baseline answer generation (from Step 11.1)
    2. Verification question planning
    3. Independent verification execution (parallel)
    4. Exact quote matching against source passages (parallel)
    5. Hallucination detection
    6. Final verified response construction

    Performance targets:
    - Latency: <7s p95 (vs 3s baseline)
    - Cache hit rate: 60-70% for quote matches
    - Hallucination detection accuracy: >85%
    """

    # Configuration
    VERIFICATION_TIMEOUT_SECONDS = getattr(settings, 'VERIFICATION_TIMEOUT_SECONDS', 120)
    VERIFICATION_QUESTION_TIMEOUT = getattr(settings, 'VERIFICATION_QUESTION_TIMEOUT', 60)
    MAX_VERIFICATION_QUESTIONS = getattr(settings, 'VERIFICATION_MAX_QUESTIONS', 10)

    # Cache TTLs
    VERIFICATION_CACHE_TTL = getattr(settings, 'VERIFICATION_CACHE_TTL_SECONDS', 3600)  # 1 hour
    QUOTE_MATCH_CACHE_TTL = getattr(settings, 'QUOTE_MATCH_CACHE_TTL_SECONDS', 86400)  # 24 hours
    VERIFICATION_QUESTION_CACHE_TTL = getattr(settings, 'VERIFICATION_QUESTION_CACHE_TTL_SECONDS', 604800)  # 1 week

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        answer_service: Optional[AnswerService] = None,
        quote_matcher: Optional[QuoteMatchingService] = None,
        question_generator: Optional[VerificationQuestionGenerator] = None,
        hallucination_detector: Optional[HallucinationDetector] = None,
        cache: Optional[Redis] = None,
        profile: Optional[VerificationProfile] = None
    ):
        """
        Initialize verification service with dependencies.

        Args:
            ollama_client: OllamaClient for LLM calls
            answer_service: AnswerService from Step 11.1
            quote_matcher: QuoteMatchingService for exact quote matching
            question_generator: VerificationQuestionGenerator
            hallucination_detector: HallucinationDetector
            cache: Redis client for caching
            profile: VerificationProfile (loads from settings if not provided)
        """
        self.ollama = ollama_client or get_ollama_client()
        self.answer_service = answer_service or AnswerService(cache)
        self.quote_matcher = quote_matcher or QuoteMatchingService()
        self.question_generator = question_generator or VerificationQuestionGenerator(self.ollama)
        self.hallucination_detector = hallucination_detector or HallucinationDetector(self.ollama)
        self.cache = cache

        # Load active verification profile
        self.profile = profile or get_active_profile()

        logger.info(
            "VerificationService initialized",
            cache='enabled' if cache else 'disabled',
            verification_level=self.profile.level.value,
            auto_remove_threshold=self.profile.hallucination_auto_remove_threshold
        )

    async def verify_answer(
        self,
        request: AnswerRequest,
        enable_verification: bool = True
    ) -> VerifiedAnswerResponse:
        """
        Execute full Chain-of-Verification pipeline.

        Complexity: O(N*M) where N=propositions (3-5), M=passages (5-10)
        Time: ~2-4s additional latency (Step 11.1 baseline ~3s → ~5-7s total)

        Args:
            request: Answer request with query and document IDs
            enable_verification: If False, returns baseline answer only

        Returns:
            VerifiedAnswerResponse with verification metadata

        Raises:
            HTTPException: On validation or generation errors
        """
        start_time = time.time()
        request_id = str(uuid4())

        # Track concurrent requests
        VerificationMetricsRecorder.increment_concurrent_requests()

        logger.info(
            "Starting verification pipeline",
            request_id=request_id,
            query_length=len(request.query),
            enable_verification=enable_verification
        )

        # Check cache (L1: Verification results)
        if self.cache and enable_verification:
            cache_key = self._generate_verification_cache_key(request, enable_verification)
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                logger.info("Verification cache hit", request_id=request_id)
                VerificationMetricsRecorder.record_cache_hit("l1_verification")
                cached_result.cache_hit = True
                VerificationMetricsRecorder.decrement_concurrent_requests()
                return cached_result
            else:
                VerificationMetricsRecorder.record_cache_miss("l1_verification")

        # Initialize baseline_answer to None for exception handling
        baseline_answer = None

        try:
            # Stage 1: Generate baseline answer (Step 11.1)
            baseline_answer = await self.answer_service.generate_answer(request)

            if not enable_verification:
                # Return baseline without verification
                return self._wrap_baseline_as_verified(
                    baseline_answer,
                    status="skipped",
                    fallback_to_baseline=True
                )

            # Check if baseline abstained
            if not baseline_answer.can_answer:
                logger.info("Baseline abstained, skipping verification")
                return self._wrap_baseline_as_verified(
                    baseline_answer,
                    status="skipped",
                    fallback_to_baseline=True
                )

            # Check if we have propositions to verify
            if not baseline_answer.propositions:
                logger.warning("No propositions to verify, returning baseline")
                return self._wrap_baseline_as_verified(
                    baseline_answer,
                    status="partial",
                    fallback_to_baseline=True
                )

            # Stages 2-6: Run verification pipeline with timeout
            try:
                verified_response = await asyncio.wait_for(
                    self._run_verification_pipeline(baseline_answer, request_id),
                    timeout=self.VERIFICATION_TIMEOUT_SECONDS
                )

                # Calculate total latency
                elapsed_ms = int((time.time() - start_time) * 1000)
                verified_response.verification_metadata.verification_latency_ms = elapsed_ms
                verified_response.processing_time_ms = elapsed_ms

                # Cache result (L1)
                if self.cache:
                    await self._save_to_cache(cache_key, verified_response)

                # Record metrics
                VerificationMetricsRecorder.record_verification_request(
                    status=verified_response.verification_metadata.status,
                    latency_ms=elapsed_ms
                )

                VerificationMetricsRecorder.record_hallucination_detection(
                    probability=verified_response.verification_metadata.hallucination_probability,
                    propositions_checked=verified_response.verification_metadata.propositions_checked,
                    propositions_verified=verified_response.verification_metadata.propositions_verified,
                    propositions_removed=verified_response.verification_metadata.propositions_removed
                )

                logger.info(
                    "Verification completed",
                    request_id=request_id,
                    status=verified_response.verification_metadata.status,
                    hallucination_probability=verified_response.verification_metadata.hallucination_probability,
                    latency_ms=elapsed_ms
                )

                return verified_response

            except asyncio.TimeoutError:
                logger.error(
                    "Verification timeout",
                    request_id=request_id,
                    timeout=self.VERIFICATION_TIMEOUT_SECONDS
                )
                VerificationMetricsRecorder.record_timeout("overall")
                return self._fallback_to_baseline(baseline_answer, "timeout")

        except Exception as e:
            logger.error(
                "Verification failed",
                request_id=request_id,
                error=str(e),
                exc_info=True
            )
            VerificationMetricsRecorder.record_verification_error("pipeline", type(e).__name__)
            # If we have baseline answer, return it with error status
            if baseline_answer is not None:
                return self._fallback_to_baseline(baseline_answer, f"error: {str(e)}")
            # Otherwise, return error fallback without baseline
            return self._create_error_fallback(request, str(e))

        finally:
            # Always decrement concurrent requests
            VerificationMetricsRecorder.decrement_concurrent_requests()

    async def _run_verification_pipeline(
        self,
        baseline: AnswerResponse,
        request_id: str
    ) -> VerifiedAnswerResponse:
        """
        Execute stages 2-6 of verification pipeline.

        Args:
            baseline: Baseline answer from Step 11.1
            request_id: Request ID for logging

        Returns:
            VerifiedAnswerResponse with verification metadata
        """
        # Convert answer_service.Passage to verification.Passage
        passages = self._convert_passages(baseline)

        # Stage 2: Generate verification questions
        verification_questions = await self._generate_verification_questions(
            baseline.propositions,
            request_id
        )

        logger.info(
            "Generated verification questions",
            request_id=request_id,
            question_count=len(verification_questions)
        )

        # Stage 3 & 4: Execute in parallel
        # - Stage 3: Answer verification questions independently
        # - Stage 4: Find supporting quotes
        verification_task = self._execute_verifications(
            verification_questions,
            passages,
            request_id
        )
        quote_matching_task = self._match_quotes(
            baseline.propositions,
            passages,
            request_id
        )

        verification_answers, quote_matches = await asyncio.gather(
            verification_task,
            quote_matching_task
        )

        logger.info(
            "Quote matching completed",
            request_id=request_id,
            propositions_with_quotes=sum(1 for matches in quote_matches.values() if matches)
        )

        # Stage 5: Detect hallucinations
        hallucination_report = await self._detect_hallucinations(
            baseline.answer,
            baseline.propositions,
            verification_answers,
            quote_matches
        )

        if hallucination_report.hallucination_probability > 0.3:
            logger.warning(
                "High hallucination probability detected",
                request_id=request_id,
                probability=hallucination_report.hallucination_probability,
                flagged_count=len(hallucination_report.flagged_proposition_indices)
            )

        # Stage 6: Build verified response
        verified_response = self._build_verified_response(
            baseline,
            hallucination_report,
            quote_matches
        )

        return verified_response

    async def _generate_verification_questions(
        self,
        propositions: List[Proposition],
        request_id: str
    ) -> List[VerificationQuestion]:
        """
        Stage 2: Generate focused verification questions.

        Uses L3 cache (1-week TTL) for generated questions.

        Args:
            propositions: List of propositions to verify
            request_id: Request ID for logging

        Returns:
            List of VerificationQuestion objects
        """
        # Limit propositions to prevent DOS
        if len(propositions) > self.MAX_VERIFICATION_QUESTIONS:
            logger.warning(
                f"Too many propositions ({len(propositions)}), limiting to {self.MAX_VERIFICATION_QUESTIONS}"
            )
            propositions = propositions[:self.MAX_VERIFICATION_QUESTIONS]

        # Check L3 cache for verification questions
        if self.cache:
            cache_key = self._generate_question_cache_key(propositions)
            cached_questions = await self._get_questions_from_cache(cache_key)
            if cached_questions:
                logger.info("Verification questions cache hit", request_id=request_id)
                VerificationMetricsRecorder.record_cache_hit("l3_questions")
                return cached_questions
            else:
                VerificationMetricsRecorder.record_cache_miss("l3_questions")

        # Generate questions using VerificationQuestionGenerator
        try:
            questions = await self.question_generator.generate_questions(propositions)

            # Cache questions (L3)
            if self.cache:
                await self._save_questions_to_cache(cache_key, questions)

            return questions

        except Exception as e:
            logger.error(
                f"Question generation failed: {e}",
                request_id=request_id,
                exc_info=True
            )
            # Fallback to template-based questions
            return self._generate_template_questions(propositions)

    async def _execute_verifications(
        self,
        questions: List[VerificationQuestion],
        passages: List[Passage],
        request_id: str
    ) -> List[VerificationAnswer]:
        """
        Stage 3: Answer verification questions independently.

        Critical: Do NOT include baseline answer to prevent confirmation bias.
        Executes questions in parallel for 2-3x speedup.

        Args:
            questions: Verification questions to answer
            passages: Retrieved passages (reused from baseline)
            request_id: Request ID for logging

        Returns:
            List of VerificationAnswer objects (may include fallbacks)
        """
        logger.info(
            f"Executing {len(questions)} verification questions in parallel",
            request_id=request_id
        )

        # Build context from passages (WITHOUT baseline answer - critical!)
        context = self._build_passage_context(passages)

        # Execute questions in parallel
        tasks = [
            self._answer_verification_question_with_fallback(q, context, request_id)
            for q in questions
        ]

        verification_answers = await asyncio.gather(*tasks)

        # Count fallback usage
        fallback_count = sum(1 for ans in verification_answers if ans.is_fallback)
        if fallback_count > 0:
            logger.warning(
                f"{fallback_count}/{len(questions)} verification questions used fallback",
                request_id=request_id
            )

        return verification_answers

    async def _answer_verification_question_with_fallback(
        self,
        question: VerificationQuestion,
        context: str,
        request_id: str
    ) -> VerificationAnswer:
        """
        Answer a single verification question with graceful fallback.

        Fallback strategy:
        1. Try LLM-based answer (with timeout)
        2. If fails, use conservative fallback: "Cannot verify from documents"
        3. Mark as fallback for downstream handling

        Args:
            question: VerificationQuestion to answer
            context: Passage context (without baseline answer)
            request_id: Request ID for logging

        Returns:
            VerificationAnswer (may be fallback)
        """
        try:
            # Build verification prompt
            prompt = self._build_verification_prompt(question, context)

            # Call Ollama with timeout
            response = await asyncio.wait_for(
                self.ollama.generate(
                    prompt=prompt,
                    temperature=self.profile.verification_temperature,  # From active profile
                    max_tokens=500    # Shorter than baseline (2000)
                ),
                timeout=self.VERIFICATION_QUESTION_TIMEOUT
            )

            return VerificationAnswer(
                question_id=question.id,
                answer=response["response"].strip(),
                is_fallback=False,
                fallback_reason=None,
                confidence=0.8  # LLM-based answer has decent confidence
            )

        except asyncio.TimeoutError:
            logger.error(
                f"Verification question timeout: {question.id}",
                request_id=request_id,
                question_preview=question.question_text[:50]
            )
            return self._create_fallback_answer(question, "timeout")

        except Exception as e:
            logger.error(
                f"Verification question failed: {e}",
                request_id=request_id,
                question_id=question.id
            )
            return self._create_fallback_answer(question, f"error: {str(e)}")

    def _build_verification_prompt(
        self,
        question: VerificationQuestion,
        context: str
    ) -> str:
        """
        Build prompt for verification question.

        Critical: Do NOT include baseline answer to prevent confirmation bias.

        Args:
            question: VerificationQuestion
            context: Passage context

        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a precise fact-checking assistant. Answer the verification question using ONLY the provided passages.

PASSAGES:
{context}

VERIFICATION QUESTION: {question.question_text}

INSTRUCTIONS:
1. Answer with YES, NO, or CANNOT DETERMINE
2. Provide a brief explanation (1-2 sentences)
3. Cite the passage number if you find supporting evidence [1], [2], etc.
4. If the answer is not in the passages, respond: "CANNOT DETERMINE - not mentioned in documents"

ANSWER:"""

        return prompt

    def _create_fallback_answer(
        self,
        question: VerificationQuestion,
        reason: str
    ) -> VerificationAnswer:
        """
        Create fallback answer when LLM verification fails.

        Strategy: Conservative fallback that doesn't affirm or deny the claim.
        This allows hallucination detection to flag based on quote matching alone.

        Args:
            question: VerificationQuestion
            reason: Reason for fallback

        Returns:
            VerificationAnswer with is_fallback=True
        """
        return VerificationAnswer(
            question_id=question.id,
            answer="I cannot verify this claim from the provided documents.",
            is_fallback=True,
            fallback_reason=reason,
            confidence=0.0  # No confidence in fallback answer
        )

    async def _match_quotes(
        self,
        propositions: List[Proposition],
        passages: List[Passage],
        request_id: str
    ) -> Dict[int, List[QuoteMatch]]:
        """
        Stage 4: Find supporting quotes for each proposition.

        Runs quote matching in parallel for all propositions.
        Uses L2 cache (24-hour TTL) for quote matches.

        Args:
            propositions: List of propositions to find quotes for
            passages: Retrieved passages
            request_id: Request ID for logging

        Returns:
            Dict mapping proposition index to list of QuoteMatch objects
        """
        logger.info(
            f"Starting quote matching for {len(propositions)} propositions",
            request_id=request_id
        )

        # Run quote matching in parallel
        tasks = []
        cache_hits = 0
        for prop in propositions:
            # Check L2 cache for quote matches
            if self.cache:
                cache_key = self._generate_quote_cache_key(prop.text, passages)
                cached_matches = await self._get_quotes_from_cache(cache_key)
                if cached_matches:
                    VerificationMetricsRecorder.record_cache_hit("l2_quotes")
                    cache_hits += 1
                    tasks.append(asyncio.create_task(asyncio.sleep(0, result=cached_matches)))
                    continue
                else:
                    VerificationMetricsRecorder.record_cache_miss("l2_quotes")

            # Run quote matching
            task = asyncio.create_task(
                asyncio.to_thread(
                    self.quote_matcher.find_supporting_quotes,
                    prop.text,
                    passages
                )
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build quote matches dict
        quote_matches = {}
        total_matches = 0
        similarity_scores = []

        for prop, result in zip(propositions, results):
            if isinstance(result, Exception):
                logger.warning(
                    f"Quote matching failed for proposition {prop.index}: {result}",
                    request_id=request_id
                )
                VerificationMetricsRecorder.record_verification_error("quote_matching", type(result).__name__)
                quote_matches[prop.index] = []
            else:
                quote_matches[prop.index] = result
                total_matches += len(result)

                # Collect similarity scores for metrics
                for match in result:
                    similarity_scores.append(match.similarity_score)

                # Cache successful matches (L2)
                if self.cache and result:
                    cache_key = self._generate_quote_cache_key(prop.text, passages)
                    await self._save_quotes_to_cache(cache_key, result)

        # Record quote matching metrics
        if similarity_scores:
            avg_similarity = sum(similarity_scores) / len(similarity_scores)
            VerificationMetricsRecorder.record_quote_matches(
                matches_found=total_matches,
                average_similarity=avg_similarity
            )
        else:
            VerificationMetricsRecorder.record_quote_matches(matches_found=0)

        return quote_matches

    async def _detect_hallucinations(
        self,
        baseline_answer: str,
        baseline_propositions: List[Proposition],
        verification_answers: List[VerificationAnswer],
        quote_matches: Dict[int, List[QuoteMatch]]
    ) -> HallucinationReport:
        """
        Stage 5: Detect unsupported or contradictory claims.

        Uses HallucinationDetector with three-factor scoring:
        1. Quote coverage (weight: 0.5)
        2. Verification agreement (weight: 0.3)
        3. Semantic contradiction (weight: 0.2)

        Args:
            baseline_answer: Original generated answer
            baseline_propositions: Propositions extracted from baseline
            verification_answers: Independent verification answers
            quote_matches: Quote matches per proposition index

        Returns:
            HallucinationReport with probability and flagged propositions
        """
        return await self.hallucination_detector.detect_hallucinations(
            baseline_answer,
            baseline_propositions,
            verification_answers,
            quote_matches
        )

    def _build_verified_response(
        self,
        baseline: AnswerResponse,
        hallucination_report: HallucinationReport,
        quote_matches: Dict[int, List[QuoteMatch]]
    ) -> VerifiedAnswerResponse:
        """
        Stage 6: Construct final verified answer.

        Removes flagged propositions if hallucination probability > threshold.
        Adds abstention notice if needed.
        Updates citations and confidence.

        Args:
            baseline: Baseline answer response
            hallucination_report: Hallucination detection report
            quote_matches: Quote matches per proposition

        Returns:
            VerifiedAnswerResponse with verification metadata
        """
        # Determine verified answer
        if hallucination_report.hallucination_probability > self.profile.hallucination_auto_remove_threshold:
            # High hallucination probability - remove flagged propositions
            verified_answer = self._remove_flagged_propositions(
                baseline.answer,
                baseline.propositions,
                hallucination_report.flagged_proposition_indices
            )
            propositions_removed = len(hallucination_report.flagged_proposition_indices)

            logger.info(
                f"Removed {propositions_removed} flagged propositions due to high hallucination probability"
            )
        else:
            # Keep original answer
            verified_answer = baseline.answer
            propositions_removed = 0

        # Calculate verified confidence
        verified_confidence = baseline.confidence + hallucination_report.confidence_adjustment
        verified_confidence = max(0.0, min(1.0, verified_confidence))  # Clamp to [0,1]

        # Determine status
        if hallucination_report.hallucination_probability < 0.3:
            status = "verified"
        elif hallucination_report.hallucination_probability >= 0.7:
            status = "partial"
        else:
            status = "partial"

        # Build metadata
        verification_metadata = VerificationMetadata(
            status=status,
            active_verification_level=self.profile.level.value,
            hallucination_probability=hallucination_report.hallucination_probability,
            propositions_checked=len(baseline.propositions),
            propositions_verified=len(baseline.propositions) - len(hallucination_report.flagged_proposition_indices),
            propositions_removed=propositions_removed,
            quote_matches={
                str(k): [qm.model_dump() for qm in v]
                for k, v in quote_matches.items()
            },
            verification_latency_ms=0,  # Set by caller
            fallback_to_baseline=False,
            failure_reason=None
        )

        # Build verified response
        return VerifiedAnswerResponse(
            **baseline.model_dump(exclude={"answer"}),
            answer=baseline.answer,  # Original answer
            verified_answer=verified_answer,  # Potentially modified
            verified_confidence=verified_confidence,
            verification_metadata=verification_metadata
        )

    def _remove_flagged_propositions(
        self,
        answer: str,
        propositions: List[Proposition],
        flagged_indices: List[int]
    ) -> str:
        """
        Remove flagged propositions from answer.

        Simple implementation: Remove sentences containing flagged propositions.

        Args:
            answer: Original answer text
            propositions: List of all propositions
            flagged_indices: Indices of flagged propositions

        Returns:
            Modified answer with flagged propositions removed
        """
        if not flagged_indices:
            return answer

        # Get flagged proposition texts
        flagged_texts = [prop.text for prop in propositions if prop.index in flagged_indices]

        # Split answer into sentences
        import re
        sentences = re.split(r'(?<=[.!?])\s+', answer)

        # Keep sentences that don't match flagged propositions
        kept_sentences = []
        for sent in sentences:
            # Check if sentence matches any flagged proposition
            is_flagged = any(
                self._text_similarity(sent, flagged_text) > 0.7
                for flagged_text in flagged_texts
            )
            if not is_flagged:
                kept_sentences.append(sent)

        # Join kept sentences
        if kept_sentences:
            return " ".join(kept_sentences)
        else:
            return "I cannot provide a verified answer based on the available documents."

    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple text similarity for proposition matching.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        from rapidfuzz import fuzz
        return fuzz.token_set_ratio(text1.lower(), text2.lower()) / 100.0

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _convert_passages(self, baseline: AnswerResponse) -> List[Passage]:
        """
        Convert answer_service.Passage to verification.Passage.

        Args:
            baseline: Baseline answer response

        Returns:
            List of verification.Passage objects
        """
        # For now, return empty list as we don't have passages in AnswerResponse
        # TODO: Modify AnswerResponse schema to include passages
        # This is a temporary workaround
        return []

    def _build_passage_context(self, passages: List[Passage]) -> str:
        """
        Build context string from passages for verification prompt.

        Args:
            passages: List of passages

        Returns:
            Formatted context string
        """
        if not passages:
            return "No passages available."

        context_parts = []
        for i, passage in enumerate(passages, start=1):
            context_parts.append(f"[{i}] {passage.content}")

        return "\n\n".join(context_parts)

    def _generate_template_questions(
        self,
        propositions: List[Proposition]
    ) -> List[VerificationQuestion]:
        """
        Generate template-based questions as fallback.

        Args:
            propositions: List of propositions

        Returns:
            List of VerificationQuestion objects
        """
        questions = []
        for prop in propositions:
            question = VerificationQuestion(
                id=f"vq_{uuid4().hex[:8]}",
                question_text=f"According to the documents, is the following statement correct: {prop.text}?",
                target_proposition_index=prop.index,
                question_type="binary"
            )
            questions.append(question)

        return questions

    def _fallback_to_baseline(
        self,
        baseline: AnswerResponse,
        reason: str
    ) -> VerifiedAnswerResponse:
        """
        Return baseline answer when verification fails.

        Args:
            baseline: Baseline answer response
            reason: Reason for fallback

        Returns:
            VerifiedAnswerResponse with failed status
        """
        return VerifiedAnswerResponse(
            **baseline.model_dump(),
            verified_answer=baseline.answer,
            verified_confidence=baseline.confidence,
            verification_metadata=VerificationMetadata(
                status="failed",
                active_verification_level=self.profile.level.value,
                hallucination_probability=0.0,
                propositions_checked=0,
                propositions_verified=0,
                propositions_removed=0,
                quote_matches={},
                verification_latency_ms=0,
                fallback_to_baseline=True,
                failure_reason=reason
            )
        )

    def _create_error_fallback(
        self,
        request: AnswerRequest,
        error_message: str
    ) -> VerifiedAnswerResponse:
        """
        Create error fallback response when baseline answer generation fails.

        Args:
            request: Original answer request
            error_message: Error message

        Returns:
            VerifiedAnswerResponse with failed status and abstention
        """
        # Create a minimal baseline answer for abstention
        baseline = AnswerResponse(
            success=False,
            answer="I cannot answer this question at the moment due to a service error.",
            propositions=[],
            citations=[],
            confidence=0.0,
            can_answer=False,
            abstention_reason=f"Service unavailable: {error_message}",
            processing_time_ms=0,
            passages_used=0,
            model_used="unknown",
            cache_hit=False
        )

        return VerifiedAnswerResponse(
            **baseline.model_dump(),
            verified_answer=baseline.answer,
            verified_confidence=0.0,
            verification_metadata=VerificationMetadata(
                status="failed",
                active_verification_level=self.profile.level.value,
                hallucination_probability=0.0,
                propositions_checked=0,
                propositions_verified=0,
                propositions_removed=0,
                quote_matches={},
                verification_latency_ms=0,
                fallback_to_baseline=True,
                failure_reason=error_message
            )
        )

    def _wrap_baseline_as_verified(
        self,
        baseline: AnswerResponse,
        status: str,
        fallback_to_baseline: bool
    ) -> VerifiedAnswerResponse:
        """
        Wrap baseline answer as VerifiedAnswerResponse.

        Args:
            baseline: Baseline answer response
            status: Verification status
            fallback_to_baseline: Whether this is a fallback

        Returns:
            VerifiedAnswerResponse
        """
        return VerifiedAnswerResponse(
            **baseline.model_dump(),
            verified_answer=baseline.answer,
            verified_confidence=baseline.confidence,
            verification_metadata=VerificationMetadata(
                status=status,
                hallucination_probability=0.0,
                propositions_checked=len(baseline.propositions),
                propositions_verified=len(baseline.propositions),
                propositions_removed=0,
                quote_matches={},
                verification_latency_ms=0,
                fallback_to_baseline=fallback_to_baseline,
                failure_reason=None
            )
        )

    # ========================================================================
    # CACHING
    # ========================================================================

    def _generate_verification_cache_key(
        self,
        request: AnswerRequest,
        enable_verification: bool
    ) -> str:
        """
        Generate L1 cache key for verification results.

        Args:
            request: Answer request
            enable_verification: Verification enabled flag

        Returns:
            Cache key string
        """
        doc_ids = sorted(request.document_ids or [])
        cache_input = f"{request.query}:{':'.join(doc_ids)}:{request.top_k}:{enable_verification}"
        return f"verification:{hashlib.sha256(cache_input.encode()).hexdigest()}"

    def _generate_question_cache_key(self, propositions: List[Proposition]) -> str:
        """
        Generate L3 cache key for verification questions.

        Args:
            propositions: List of propositions

        Returns:
            Cache key string
        """
        prop_texts = "|".join(sorted(prop.text for prop in propositions))
        return f"vq:{hashlib.sha256(prop_texts.encode()).hexdigest()}"

    def _generate_quote_cache_key(
        self,
        proposition_text: str,
        passages: List[Passage]
    ) -> str:
        """
        Generate L2 cache key for quote matches.

        Args:
            proposition_text: Proposition text
            passages: List of passages

        Returns:
            Cache key string
        """
        passage_ids = "|".join(sorted(p.id for p in passages))
        cache_input = f"{proposition_text}:{passage_ids}"
        return f"quotes:{hashlib.sha256(cache_input.encode()).hexdigest()}"

    async def _get_from_cache(self, cache_key: str) -> Optional[VerifiedAnswerResponse]:
        """Get verification result from L1 cache."""
        if not self.cache:
            return None

        try:
            cached_json = self.cache.get(cache_key)
            if cached_json:
                data = json.loads(cached_json)
                return VerifiedAnswerResponse(**data)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")

        return None

    async def _save_to_cache(self, cache_key: str, response: VerifiedAnswerResponse):
        """Save verification result to L1 cache."""
        if not self.cache:
            return

        try:
            cache_data = response.model_dump()
            self.cache.setex(
                cache_key,
                self.VERIFICATION_CACHE_TTL,
                json.dumps(cache_data)
            )
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    async def _get_questions_from_cache(self, cache_key: str) -> Optional[List[VerificationQuestion]]:
        """Get verification questions from L3 cache."""
        if not self.cache:
            return None

        try:
            cached_json = self.cache.get(cache_key)
            if cached_json:
                data = json.loads(cached_json)
                return [VerificationQuestion(**q) for q in data]
        except Exception as e:
            logger.warning(f"Question cache get error: {e}")

        return None

    async def _save_questions_to_cache(
        self,
        cache_key: str,
        questions: List[VerificationQuestion]
    ):
        """Save verification questions to L3 cache."""
        if not self.cache:
            return

        try:
            cache_data = [q.model_dump() for q in questions]
            self.cache.setex(
                cache_key,
                self.VERIFICATION_QUESTION_CACHE_TTL,
                json.dumps(cache_data)
            )
        except Exception as e:
            logger.warning(f"Question cache set error: {e}")

    async def _get_quotes_from_cache(self, cache_key: str) -> Optional[List[QuoteMatch]]:
        """Get quote matches from L2 cache."""
        if not self.cache:
            return None

        try:
            cached_json = self.cache.get(cache_key)
            if cached_json:
                data = json.loads(cached_json)
                return [QuoteMatch(**q) for q in data]
        except Exception as e:
            logger.warning(f"Quote cache get error: {e}")

        return None

    async def _save_quotes_to_cache(
        self,
        cache_key: str,
        quotes: List[QuoteMatch]
    ):
        """Save quote matches to L2 cache."""
        if not self.cache:
            return

        try:
            cache_data = [q.model_dump() for q in quotes]
            self.cache.setex(
                cache_key,
                self.QUOTE_MATCH_CACHE_TTL,
                json.dumps(cache_data)
            )
        except Exception as e:
            logger.warning(f"Quote cache set error: {e}")


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_verification_service() -> VerificationService:
    """
    Get VerificationService instance for dependency injection.

    Returns:
        VerificationService instance with all dependencies
    """
    redis_client = None
    try:
        from app.core.redis import get_redis
        redis_client = await get_redis()
    except Exception as e:
        logger.warning(f"Redis client not available for VerificationService: {e}")

    return VerificationService(cache=redis_client)
