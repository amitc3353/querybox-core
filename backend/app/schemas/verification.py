"""
Verification Schemas for Step 11.2 - Chain-of-Verification

Pydantic models for verification pipeline including:
- Quote matching
- Verification questions
- Hallucination detection
- Verified answer responses
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Literal
from uuid import UUID


class QuoteMatch(BaseModel):
    """
    Represents a quote match found in a passage.

    Used in Stage 4 of verification pipeline to track supporting quotes.
    """
    passage_id: str = Field(..., description="ID of passage containing the match")
    passage_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Rerank score of passage (from Step 10.2)"
    )
    matched_text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The matched sentence from passage"
    )
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fuzzy match similarity score (RapidFuzz)"
    )
    start_pos: int = Field(..., ge=0, description="Character start position in passage")
    end_pos: int = Field(..., ge=0, description="Character end position in passage")
    sentence_index: int = Field(..., ge=0, description="Sentence index in passage")

    @validator('end_pos')
    def validate_positions(cls, v, values):
        """Ensure end_pos > start_pos"""
        if 'start_pos' in values and v <= values['start_pos']:
            raise ValueError("end_pos must be greater than start_pos")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "passage_id": "p1",
                "passage_score": 0.95,
                "matched_text": "France's capital city is Paris, located in the north.",
                "similarity_score": 0.92,
                "start_pos": 0,
                "end_pos": 54,
                "sentence_index": 0
            }
        }


class VerificationQuestion(BaseModel):
    """
    Verification question generated for a proposition.

    Used in Stage 2 of verification pipeline.
    """
    id: str = Field(..., description="Unique question ID")
    question_text: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="The verification question"
    )
    target_proposition_index: int = Field(
        ...,
        ge=0,
        description="Index of proposition being verified"
    )
    question_type: Literal["binary", "factual", "existence"] = Field(
        "binary",
        description="Type of verification question"
    )

    @validator('question_text')
    def validate_question_text(cls, v):
        """Validate question text doesn't contain injection patterns"""
        v = v.strip()
        if not v:
            raise ValueError("Question text cannot be empty")

        # Check for prompt injection patterns
        import re
        dangerous_patterns = [
            r"ignore\s+previous",
            r"disregard\s+the",
            r"new\s+role",
        ]
        question_lower = v.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, question_lower):
                raise ValueError("Question contains prohibited patterns")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "vq_1",
                "question_text": "According to the documents, is Paris the capital of France?",
                "target_proposition_index": 0,
                "question_type": "binary"
            }
        }


class VerificationAnswer(BaseModel):
    """
    Answer to a verification question.

    Used in Stage 3 of verification pipeline.
    """
    question_id: str = Field(..., description="ID of verification question")
    answer: str = Field(..., max_length=1000, description="Verification answer")
    is_fallback: bool = Field(
        False,
        description="Whether this is a fallback answer (LLM failed)"
    )
    fallback_reason: Optional[str] = Field(
        None,
        description="Reason for fallback (timeout, error, etc.)"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in this verification answer"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "question_id": "vq_1",
                "answer": "YES - The document states Paris is the capital. [1]",
                "is_fallback": False,
                "fallback_reason": None,
                "confidence": 0.8
            }
        }


class HallucinationReport(BaseModel):
    """
    Report from hallucination detection stage.

    Used in Stage 5 of verification pipeline.
    """
    hallucination_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall hallucination probability (0-1)"
    )
    flagged_proposition_indices: List[int] = Field(
        default_factory=list,
        description="Indices of propositions flagged as potentially hallucinated"
    )
    confidence_adjustment: float = Field(
        0.0,
        ge=-1.0,
        le=1.0,
        description="Adjustment to baseline confidence (-1 to +1)"
    )
    contradiction_details: Optional[Dict[str, str]] = Field(
        None,
        description="Details of contradictions found"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "hallucination_probability": 0.15,
                "flagged_proposition_indices": [],
                "confidence_adjustment": 0.0,
                "contradiction_details": None
            }
        }


class VerificationMetadata(BaseModel):
    """
    Metadata about verification process.

    Included in VerifiedAnswerResponse.
    """
    status: Literal["verified", "partial", "failed", "skipped"] = Field(
        ...,
        description="Verification status"
    )
    active_verification_level: Optional[str] = Field(
        None,
        description="Active verification level (VERY_HIGH, HIGH, MEDIUM, LOW, VERY_LOW)"
    )
    hallucination_probability: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Hallucination probability score"
    )
    propositions_checked: int = Field(
        0,
        ge=0,
        description="Number of propositions checked"
    )
    propositions_verified: int = Field(
        0,
        ge=0,
        description="Number of propositions successfully verified"
    )
    propositions_removed: int = Field(
        0,
        ge=0,
        description="Number of propositions removed due to high hallucination probability"
    )
    quote_matches: Dict[str, List[Dict]] = Field(
        default_factory=dict,
        description="Quote matches per proposition index (stringified)"
    )
    verification_latency_ms: int = Field(
        0,
        ge=0,
        description="Verification pipeline latency in milliseconds"
    )
    fallback_to_baseline: bool = Field(
        False,
        description="Whether verification failed and returned baseline answer"
    )
    failure_reason: Optional[str] = Field(
        None,
        description="Reason for failure if status=failed"
    )

    @validator('propositions_verified')
    def validate_verified_count(cls, v, values):
        """Ensure verified count doesn't exceed checked count"""
        if 'propositions_checked' in values and v > values['propositions_checked']:
            raise ValueError("propositions_verified cannot exceed propositions_checked")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "status": "verified",
                "active_verification_level": "HIGH",
                "hallucination_probability": 0.1,
                "propositions_checked": 2,
                "propositions_verified": 2,
                "propositions_removed": 0,
                "quote_matches": {
                    "0": [
                        {
                            "passage_id": "p1",
                            "similarity_score": 0.92,
                            "matched_text": "Paris is the capital..."
                        }
                    ]
                },
                "verification_latency_ms": 4500,
                "fallback_to_baseline": False,
                "failure_reason": None
            }
        }


class VerifiedAnswerResponse(BaseModel):
    """
    Response schema for verified answer generation.

    Extends AnswerResponse from Step 11.1 with verification metadata.
    """
    # Core answer fields (from AnswerResponse)
    success: bool = Field(..., description="Whether answer generation succeeded")
    answer: str = Field(..., description="Original generated answer with citations")
    verified_answer: str = Field(
        ...,
        description="Verified answer (may differ if claims removed)"
    )
    propositions: List[Dict] = Field(
        default_factory=list,
        description="Atomic claims from answer"
    )
    citations: List[Dict] = Field(
        default_factory=list,
        description="Source citations"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall answer confidence (baseline)"
    )
    verified_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Adjusted confidence after verification"
    )
    can_answer: bool = Field(
        ...,
        description="Whether system could answer from provided documents"
    )
    abstention_reason: Optional[str] = Field(
        None,
        description="Reason if system abstained from answering"
    )
    processing_time_ms: int = Field(..., ge=0, description="Total processing time")
    passages_used: int = Field(..., ge=0, description="Number of passages used")
    model_used: str = Field(..., description="LLM model used")
    cache_hit: bool = Field(False, description="Whether answer was cached")

    # Verification-specific fields
    verification_metadata: VerificationMetadata = Field(
        ...,
        description="Verification pipeline metadata"
    )

    class Config:
        protected_namespaces = ()  # Allow model_used field without warning
        json_schema_extra = {
            "example": {
                "success": True,
                "answer": "Paris is the capital of France. [1]",
                "verified_answer": "Paris is the capital of France. [1]",
                "propositions": [
                    {"text": "Paris is the capital of France", "index": 0, "confidence": 0.95}
                ],
                "citations": [
                    {
                        "document_id": "doc1",
                        "document_name": "France.pdf",
                        "passage_text": "Paris is the capital...",
                        "citation_number": 1,
                        "relevance_score": 0.95
                    }
                ],
                "confidence": 0.85,
                "verified_confidence": 0.90,
                "can_answer": True,
                "abstention_reason": None,
                "processing_time_ms": 6500,
                "passages_used": 5,
                "model_used": "qwen2:7b",
                "cache_hit": False,
                "verification_metadata": {
                    "status": "verified",
                    "hallucination_probability": 0.1,
                    "propositions_checked": 1,
                    "propositions_verified": 1,
                    "propositions_removed": 0,
                    "quote_matches": {},
                    "verification_latency_ms": 3000,
                    "fallback_to_baseline": False,
                    "failure_reason": None
                }
            }
        }


class Passage(BaseModel):
    """
    Passage model for quote matching.

    Represents a retrieved passage from search (Step 10).
    """
    id: str = Field(..., description="Passage ID")
    content: str = Field(..., min_length=1, description="Passage text content")
    document_id: str = Field(..., description="Source document ID")
    chunk_index: int = Field(..., ge=0, description="Chunk index in document")
    rerank_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Reranking score from Step 10.2"
    )
    metadata: Optional[Dict] = Field(
        None,
        description="Additional passage metadata"
    )

    @validator('content')
    def validate_content_length(cls, v):
        """Validate content isn't too long (prevent DOS)"""
        # Max 2000 tokens ≈ 8000 chars (from doc Section 3)
        if len(v) > 10000:
            raise ValueError("Passage content exceeds maximum length (10000 chars)")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "passage_1",
                "content": "France's capital city is Paris, located in the northern part of the country.",
                "document_id": "doc_123",
                "chunk_index": 0,
                "rerank_score": 0.95,
                "metadata": {"page": 1, "section": "Geography"}
            }
        }
