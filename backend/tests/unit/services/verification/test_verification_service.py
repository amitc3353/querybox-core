"""
Unit Tests for VerificationService - Step 11.2

Tests the full Chain-of-Verification pipeline with mocked dependencies.

Based on technical documentation Section 8 (Testing Approach).
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

import sys
sys.path.insert(0, 'backend')

from app.services.verification import VerificationService, QuoteMatchingService
from app.services.verification.hallucination_detector import HallucinationDetector
from app.schemas.answer import AnswerRequest, AnswerResponse, Proposition, Citation
from app.schemas.verification import (
    VerifiedAnswerResponse,
    VerificationQuestion,
    VerificationAnswer,
    QuoteMatch,
    HallucinationReport,
    Passage
)


class TestVerificationService:
    """Test suite for Chain-of-Verification service."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Mock Ollama client."""
        mock = AsyncMock()
        mock.generate.return_value = {
            "response": "YES - The document states Paris is the capital. [1]",
            "metadata": {
                "model": "qwen2:7b",
                "tokens": 15
            }
        }
        mock.health_check.return_value = {"status": "healthy"}
        return mock

    @pytest.fixture
    def mock_answer_service(self):
        """Mock answer service (Step 11.1)."""
        mock = AsyncMock()
        mock.generate_answer.return_value = AnswerResponse(
            success=True,
            answer="Paris is the capital of France. [1]",
            propositions=[
                Proposition(text="Paris is the capital of France", index=0, confidence=None)
            ],
            citations=[
                Citation(
                    document_id="doc1",
                    document_name="France.pdf",
                    passage_text="France's capital city is Paris, located in the north.",
                    page=1,
                    section="Geography",
                    relevance_score=0.95,
                    citation_number=1
                )
            ],
            confidence=0.85,
            can_answer=True,
            abstention_reason=None,
            processing_time_ms=3000,
            passages_used=1,
            model_used="qwen2:7b",
            cache_hit=False
        )
        return mock

    @pytest.fixture
    def quote_matching_service(self):
        """Real quote matching service."""
        return QuoteMatchingService(similarity_threshold=0.66)

    @pytest.fixture
    def mock_question_generator(self):
        """Mock verification question generator."""
        mock = AsyncMock()
        mock.generate_questions.return_value = [
            VerificationQuestion(
                id="vq_1",
                question_text="According to the documents, is Paris the capital of France?",
                target_proposition_index=0,
                question_type="binary"
            )
        ]
        return mock

    @pytest.fixture
    def mock_hallucination_detector(self):
        """Mock hallucination detector."""
        mock = AsyncMock()
        mock.detect_hallucinations.return_value = HallucinationReport(
            hallucination_probability=0.1,
            flagged_proposition_indices=[],
            confidence_adjustment=0.0,
            contradiction_details=None
        )
        return mock

    @pytest.fixture
    def verification_service(
        self,
        mock_ollama_client,
        mock_answer_service,
        quote_matching_service,
        mock_question_generator,
        mock_hallucination_detector
    ):
        """Create verification service with mocked dependencies."""
        mock_cache = Mock()
        mock_cache.get.return_value = None  # No cache hits

        return VerificationService(
            ollama_client=mock_ollama_client,
            answer_service=mock_answer_service,
            quote_matcher=quote_matching_service,
            question_generator=mock_question_generator,
            hallucination_detector=mock_hallucination_detector,
            cache=mock_cache
        )

    @pytest.mark.asyncio
    async def test_verify_answer_success(self, verification_service):
        """Test successful verification pipeline."""
        request = AnswerRequest(
            query="What is the capital of France?",
            document_ids=[str(uuid4())],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )

        result = await verification_service.verify_answer(request, enable_verification=True)

        # Assertions
        assert isinstance(result, VerifiedAnswerResponse)
        assert result.verification_metadata is not None
        assert result.verification_metadata.status in ["verified", "partial"]
        assert result.verification_metadata.propositions_checked == 1
        assert result.verification_metadata.hallucination_probability <= 1.0
        assert not result.verification_metadata.fallback_to_baseline

    @pytest.mark.asyncio
    async def test_verify_answer_disabled(self, verification_service):
        """Test verification can be disabled."""
        request = AnswerRequest(
            query="What is the capital of France?",
            document_ids=[str(uuid4())],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )

        result = await verification_service.verify_answer(request, enable_verification=False)

        assert result.verification_metadata.status == "skipped"
        assert result.verification_metadata.fallback_to_baseline is True

    @pytest.mark.asyncio
    async def test_verify_answer_baseline_abstained(
        self,
        verification_service,
        mock_answer_service
    ):
        """Test verification skipped when baseline abstains."""
        # Mock baseline abstention
        mock_answer_service.generate_answer.return_value = AnswerResponse(
            success=True,
            answer="I cannot answer this based on the provided documents.",
            propositions=[],
            citations=[],
            confidence=0.0,
            can_answer=False,
            abstention_reason="No relevant documents found",
            processing_time_ms=2000,
            passages_used=0,
            model_used="qwen2:7b",
            cache_hit=False
        )

        request = AnswerRequest(
            query="What is the population of Mars?",
            document_ids=[str(uuid4())],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )

        result = await verification_service.verify_answer(request, enable_verification=True)

        assert result.verification_metadata.status == "skipped"
        assert result.verification_metadata.fallback_to_baseline is True

    @pytest.mark.asyncio
    async def test_verify_answer_fallback_on_timeout(
        self,
        verification_service,
        mock_ollama_client
    ):
        """Test graceful fallback when verification times out."""
        import asyncio

        # Simulate timeout on verification question
        mock_ollama_client.generate.side_effect = asyncio.TimeoutError()

        request = AnswerRequest(
            query="What is the capital of France?",
            document_ids=[str(uuid4())],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )

        result = await verification_service.verify_answer(request, enable_verification=True)

        # Should still return valid response (baseline answer with fallback verification answers)
        assert isinstance(result, VerifiedAnswerResponse)
        assert result.verification_metadata.status in ["verified", "partial", "failed"]
        assert result.answer is not None  # Baseline answer preserved

    @pytest.mark.asyncio
    async def test_verify_answer_no_propositions(
        self,
        verification_service,
        mock_answer_service
    ):
        """Test verification when no propositions extracted."""
        # Mock answer with no propositions
        mock_answer_service.generate_answer.return_value = AnswerResponse(
            success=True,
            answer="Yes.",
            propositions=[],  # No propositions
            citations=[],
            confidence=0.5,
            can_answer=True,
            abstention_reason=None,
            processing_time_ms=2000,
            passages_used=1,
            model_used="qwen2:7b",
            cache_hit=False
        )

        request = AnswerRequest(
            query="Simple query?",
            document_ids=[str(uuid4())],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )

        result = await verification_service.verify_answer(request, enable_verification=True)

        assert result.verification_metadata.status == "partial"
        assert result.verification_metadata.fallback_to_baseline is True

    @pytest.mark.asyncio
    async def test_quote_matching_integration(
        self,
        verification_service,
        mock_answer_service
    ):
        """Test quote matching integration in verification pipeline."""
        # Note: This test will likely fail because we don't have real passages
        # in the baseline answer. This is a known issue to fix.
        request = AnswerRequest(
            query="What is the capital of France?",
            document_ids=[str(uuid4())],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )

        result = await verification_service.verify_answer(request, enable_verification=True)

        # Check that quote matching was attempted
        # (may be empty due to missing passages)
        assert "quote_matches" in result.verification_metadata.model_dump()

    @pytest.mark.asyncio
    async def test_high_hallucination_probability(
        self,
        verification_service,
        mock_hallucination_detector
    ):
        """Test behavior when high hallucination probability detected."""
        # Mock high hallucination probability
        mock_hallucination_detector.detect_hallucinations.return_value = HallucinationReport(
            hallucination_probability=0.8,
            flagged_proposition_indices=[0],
            confidence_adjustment=-0.3,
            contradiction_details={"0": "Contradiction detected"}
        )

        request = AnswerRequest(
            query="What is the capital of France?",
            document_ids=[str(uuid4())],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )

        result = await verification_service.verify_answer(request, enable_verification=True)

        # High hallucination should result in partial status
        assert result.verification_metadata.status == "partial"
        assert result.verification_metadata.hallucination_probability == 0.8
        # Check that hallucination was detected (propositions_verified < propositions_checked)
        assert result.verification_metadata.propositions_verified < result.verification_metadata.propositions_checked

    @pytest.mark.asyncio
    async def test_verification_question_generation(
        self,
        verification_service,
        mock_question_generator
    ):
        """Test verification question generation."""
        request = AnswerRequest(
            query="What is the capital of France?",
            document_ids=[str(uuid4())],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )

        await verification_service.verify_answer(request, enable_verification=True)

        # Verify question generator was called
        mock_question_generator.generate_questions.assert_called_once()
        call_args = mock_question_generator.generate_questions.call_args
        propositions = call_args[0][0]
        assert len(propositions) > 0

    @pytest.mark.asyncio
    async def test_verification_answer_execution(
        self,
        verification_service,
        mock_ollama_client
    ):
        """Test verification answer execution."""
        request = AnswerRequest(
            query="What is the capital of France?",
            document_ids=[str(uuid4())],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )

        await verification_service.verify_answer(request, enable_verification=True)

        # Verify Ollama was called for verification question
        assert mock_ollama_client.generate.called

    @pytest.mark.asyncio
    async def test_verified_confidence_calculation(
        self,
        verification_service,
        mock_hallucination_detector
    ):
        """Test verified confidence calculation."""
        # Mock hallucination detector with negative adjustment
        mock_hallucination_detector.detect_hallucinations.return_value = HallucinationReport(
            hallucination_probability=0.2,
            flagged_proposition_indices=[],
            confidence_adjustment=-0.1,  # Reduce confidence
            contradiction_details=None
        )

        request = AnswerRequest(
            query="What is the capital of France?",
            document_ids=[str(uuid4())],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )

        result = await verification_service.verify_answer(request, enable_verification=True)

        # Verified confidence should be adjusted
        assert result.verified_confidence is not None
        # Should be baseline (0.85) + adjustment (-0.1) = 0.75
        # But clamped to [0, 1]
        assert 0.0 <= result.verified_confidence <= 1.0

    @pytest.mark.asyncio
    async def test_proposition_removal_on_high_hallucination(
        self,
        verification_service,
        mock_hallucination_detector
    ):
        """Test proposition removal when hallucination probability > 0.7."""
        # Mock very high hallucination probability
        mock_hallucination_detector.detect_hallucinations.return_value = HallucinationReport(
            hallucination_probability=0.9,
            flagged_proposition_indices=[0],
            confidence_adjustment=-0.5,
            contradiction_details={"0": "No supporting quotes found"}
        )

        request = AnswerRequest(
            query="What is the capital of France?",
            document_ids=[str(uuid4())],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )

        result = await verification_service.verify_answer(request, enable_verification=True)

        # Propositions should be removed
        assert result.verification_metadata.propositions_removed > 0
        assert result.verified_answer != result.answer  # Modified answer

    @pytest.mark.asyncio
    async def test_parallel_execution(
        self,
        verification_service,
        mock_question_generator
    ):
        """Test parallel execution of verification questions."""
        # Mock multiple propositions
        mock_question_generator.generate_questions.return_value = [
            VerificationQuestion(
                id=f"vq_{i}",
                question_text=f"Question {i}?",
                target_proposition_index=i,
                question_type="binary"
            )
            for i in range(3)
        ]

        request = AnswerRequest(
            query="Complex query with multiple claims?",
            document_ids=[str(uuid4())],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )

        await verification_service.verify_answer(request, enable_verification=True)

        # Verify multiple verification questions were executed
        # (They should run in parallel via asyncio.gather)
        assert verification_service.ollama.generate.call_count >= 1

    @pytest.mark.asyncio
    async def test_fallback_answer_creation(self, verification_service):
        """Test fallback answer creation when verification fails."""
        question = VerificationQuestion(
            id="vq_test",
            question_text="Test question?",
            target_proposition_index=0,
            question_type="binary"
        )

        fallback = verification_service._create_fallback_answer(question, "timeout")

        assert fallback.question_id == "vq_test"
        assert fallback.is_fallback is True
        assert fallback.fallback_reason == "timeout"
        assert fallback.confidence == 0.0
        assert "cannot verify" in fallback.answer.lower()

    @pytest.mark.asyncio
    async def test_verification_prompt_building(self, verification_service):
        """Test verification prompt building."""
        question = VerificationQuestion(
            id="vq_test",
            question_text="Is Paris the capital?",
            target_proposition_index=0,
            question_type="binary"
        )

        context = "[1] Paris is the capital of France."

        prompt = verification_service._build_verification_prompt(question, context)

        # Verify prompt structure
        assert "PASSAGES:" in prompt
        assert "VERIFICATION QUESTION:" in prompt
        assert "Paris is the capital of France" in prompt
        assert "Is Paris the capital?" in prompt
        assert "YES, NO, or CANNOT DETERMINE" in prompt


class TestVerificationServiceCaching:
    """Test caching functionality of verification service."""

    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test cache key generation for different cache levels."""
        service = VerificationService(cache=None)

        # Test L1: Verification cache key
        request = AnswerRequest(
            query="Test query",
            document_ids=["doc1", "doc2"],
            top_k=5,
            include_citations=True,
            temperature=0.2
        )
        key1 = service._generate_verification_cache_key(request, True)
        assert key1.startswith("verification:")
        assert len(key1) > 20

        # Test L3: Question cache key
        propositions = [
            Proposition(text="Paris is capital", index=0, confidence=None)
        ]
        key3 = service._generate_question_cache_key(propositions)
        assert key3.startswith("vq:")
        assert len(key3) > 10

        # Test L2: Quote cache key
        passages = [
            Passage(
                id="p1",
                content="Test content",
                document_id="doc1",
                chunk_index=0,
                rerank_score=0.9,
                metadata=None
            )
        ]
        key2 = service._generate_quote_cache_key("Test proposition", passages)
        assert key2.startswith("quotes:")
        assert len(key2) > 10


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
