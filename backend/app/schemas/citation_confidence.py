"""
Citation & Confidence Schemas for Step 11.3

Pydantic models for citation enrichment and confidence scoring including:
- Abstention decisions
- Granular confidence scoring
- Enriched citations with quality indicators
- Enhanced metadata for production-ready responses
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Literal
from enum import Enum


class AbstentionReason(str, Enum):
    """Reason categories for abstention"""
    LOW_CONFIDENCE = "low_confidence"
    HIGH_HALLUCINATION = "high_hallucination"
    NO_EVIDENCE = "no_evidence"
    VERIFICATION_FAILED = "verification_failed"


class AbstentionDecision(BaseModel):
    """
    Decision from abstention service.

    Used in Stage 1 of citation & confidence pipeline.
    """
    should_abstain: bool = Field(
        ...,
        description="Whether to abstain from answering"
    )
    reason: Optional[AbstentionReason] = Field(
        None,
        description="Primary reason for abstention"
    )
    factors: List[str] = Field(
        default_factory=list,
        description="All factors that triggered abstention"
    )
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in abstention decision (how sure we can't answer)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "should_abstain": True,
                "reason": "low_confidence",
                "factors": ["low_confidence", "no_evidence"],
                "confidence": 0.8
            }
        }


class PropConfidence(BaseModel):
    """
    Per-proposition confidence score with factor breakdown.

    Used in Stage 2 of citation & confidence pipeline.
    """
    proposition_id: str = Field(..., description="Proposition identifier")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence score for this proposition"
    )
    breakdown: Dict[str, float] = Field(
        ...,
        description="Factor breakdown: passage_relevance, quote_quality, verification_agreement, citation_count"
    )
    is_fallback: bool = Field(
        False,
        description="Whether this used fallback confidence (error in calculation)"
    )

    @validator('breakdown')
    def validate_breakdown(cls, v):
        """Ensure all factor scores are in valid range"""
        required_factors = ["passage_relevance", "quote_quality", "verification_agreement", "citation_count"]
        for factor in required_factors:
            if factor in v:
                score = v[factor]
                if not (0.0 <= score <= 1.0):
                    raise ValueError(f"Factor {factor} score must be between 0.0 and 1.0, got {score}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "proposition_id": "p1",
                "confidence": 0.92,
                "breakdown": {
                    "passage_relevance": 0.95,
                    "quote_quality": 0.97,
                    "verification_agreement": 1.0,
                    "citation_count": 0.33
                },
                "is_fallback": False
            }
        }


class ConfidenceBreakdown(BaseModel):
    """
    Overall confidence breakdown across all propositions.
    """
    overall: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence (aggregated from all propositions)"
    )
    average_passage_relevance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average passage relevance score"
    )
    average_quote_quality: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average quote quality score"
    )
    average_verification_agreement: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average verification agreement score"
    )
    average_citation_count: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average citation count score"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "overall": 0.91,
                "average_passage_relevance": 0.38,
                "average_quote_quality": 0.34,
                "average_verification_agreement": 0.14,
                "average_citation_count": 0.05
            }
        }


class CitationQuality(str, Enum):
    """Citation quality levels based on quote match similarity"""
    STRONG = "STRONG"      # similarity >= 0.95 (exact/near-exact quote)
    MEDIUM = "MEDIUM"      # 0.85 <= similarity < 0.95 (paraphrased)
    WEAK = "WEAK"          # similarity < 0.85 or no quote match


class QuoteMatchInfo(BaseModel):
    """
    Simplified quote match info for API response.

    Subset of QuoteMatch from verification.py for enriched citations.
    """
    matched_text: str = Field(..., max_length=2000, description="The matched sentence")
    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity score of match"
    )
    sentence_index: int = Field(..., ge=0, description="Sentence index in passage")

    class Config:
        json_schema_extra = {
            "example": {
                "matched_text": "Paris is the capital of France",
                "similarity_score": 0.97,
                "sentence_index": 0
            }
        }


class EnrichedCitation(BaseModel):
    """
    Citation with quote match info and quality indicators.

    Extends Citation from answer.py with Step 11.3 enhancements.
    Used in Stage 3 of citation & confidence pipeline.
    """
    # Core citation fields (from Citation)
    document_id: str = Field(..., description="Source document UUID")
    document_name: str = Field(..., description="Document display name")
    passage_text: str = Field(..., max_length=1000, description="Cited passage text")
    page: Optional[int] = Field(None, ge=1, description="Page number in source")
    section: Optional[str] = Field(None, description="Section heading")
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score of this passage"
    )
    citation_number: int = Field(..., ge=1, description="Citation reference number [1], [2], etc.")

    # Enrichment fields (NEW in Step 11.3)
    quote_match: Optional[QuoteMatchInfo] = Field(
        None,
        description="Best quote match for this citation (if any)"
    )
    best_similarity: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Best similarity score from all quote matches"
    )
    is_exact_quote: bool = Field(
        False,
        description="Whether this citation has an exact/near-exact quote (similarity >= 0.95)"
    )
    quality: CitationQuality = Field(
        CitationQuality.WEAK,
        description="Quality level: STRONG, MEDIUM, or WEAK"
    )
    highlighted_passage_text: Optional[str] = Field(
        None,
        max_length=1200,  # Slightly larger to accommodate <mark> tags
        description="Passage text with matched portions highlighted using <mark> tags"
    )
    inline_citation: str = Field(
        ...,
        description="Inline formatted citation marker (e.g., '[1]' or '[1: doc_name, p.5]')"
    )
    proposition_ids: List[str] = Field(
        default_factory=list,
        description="IDs of propositions citing this source"
    )

    @validator('highlighted_passage_text')
    def validate_highlighted_text(cls, v):
        """Ensure highlighted text doesn't contain dangerous HTML"""
        if v:
            # Only allow <mark> tags (whitelist)
            import re
            # Remove all tags except <mark> and </mark>
            allowed_pattern = r'<(?!/?mark\b)[^>]*>'
            if re.search(allowed_pattern, v):
                raise ValueError("Highlighted text contains disallowed HTML tags")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_name": "France_Guide.pdf",
                "passage_text": "France's capital is Paris, located in the north.",
                "highlighted_passage_text": "France's capital is <mark>Paris</mark>, located in the <mark>north</mark>.",
                "page": 5,
                "section": "Geography",
                "relevance_score": 0.95,
                "citation_number": 1,
                "quote_match": {
                    "matched_text": "Paris",
                    "similarity_score": 0.97,
                    "sentence_index": 0
                },
                "best_similarity": 0.97,
                "is_exact_quote": True,
                "quality": "STRONG",
                "inline_citation": "[1]",
                "proposition_ids": ["p0", "p1"]
            }
        }


class PropositionDetail(BaseModel):
    """
    Comprehensive per-proposition metadata.

    Used in Stage 4 of citation & confidence pipeline.
    """
    proposition_id: str = Field(..., description="Proposition identifier")
    text: str = Field(..., description="Proposition text")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this proposition"
    )
    confidence_breakdown: Dict[str, float] = Field(
        ...,
        description="Factor breakdown for this proposition"
    )
    has_quote: bool = Field(
        ...,
        description="Whether this proposition has supporting quote matches"
    )
    quote_similarity: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Best quote similarity score (if has_quote)"
    )
    verified: bool = Field(
        ...,
        description="Whether this proposition passed verification"
    )
    citations: List[int] = Field(
        default_factory=list,
        description="Citation numbers supporting this proposition [1, 2, ...]"
    )
    quality_indicator: Optional[CitationQuality] = Field(
        None,
        description="Best citation quality for this proposition"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "proposition_id": "p0",
                "text": "Paris is the capital of France",
                "confidence": 0.95,
                "confidence_breakdown": {
                    "passage_relevance": 0.95,
                    "quote_quality": 0.97,
                    "verification_agreement": 1.0,
                    "citation_count": 0.33
                },
                "has_quote": True,
                "quote_similarity": 0.97,
                "verified": True,
                "citations": [1],
                "quality_indicator": "STRONG"
            }
        }


class EnhancedMetadata(BaseModel):
    """
    Enhanced metadata extending VerificationMetadata from Step 11.2.

    Includes confidence breakdown, proposition details, and abstention factors.
    Used in Stage 4 of citation & confidence pipeline.
    """
    # Core verification fields (from VerificationMetadata)
    status: Literal["verified", "partial", "failed", "skipped"] = Field(
        ...,
        description="Verification status"
    )
    hallucination_probability: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Hallucination probability score"
    )
    propositions_checked: int = Field(0, ge=0, description="Number of propositions checked")
    propositions_verified: int = Field(0, ge=0, description="Number successfully verified")
    propositions_removed: int = Field(0, ge=0, description="Number removed due to hallucination")
    quote_matches: Dict[str, List[Dict]] = Field(
        default_factory=dict,
        description="Quote matches per proposition"
    )
    verification_latency_ms: int = Field(0, ge=0, description="Verification latency")
    fallback_to_baseline: bool = Field(False, description="Whether verification failed")
    failure_reason: Optional[str] = Field(None, description="Failure reason if applicable")

    # Enhanced fields (NEW in Step 11.3)
    confidence_breakdown: ConfidenceBreakdown = Field(
        ...,
        description="Overall confidence breakdown by factors"
    )
    proposition_details: List[PropositionDetail] = Field(
        default_factory=list,
        description="Detailed per-proposition metadata"
    )
    abstention_factors: Dict[str, bool] = Field(
        default_factory=dict,
        description="Abstention factors: {low_confidence: bool, high_hallucination: bool, ...}"
    )
    citation_validation_errors: List[str] = Field(
        default_factory=list,
        description="Citation validation errors (if any)"
    )
    total_citations: int = Field(0, ge=0, description="Total number of citations")
    strong_citations: int = Field(0, ge=0, description="Count of STRONG quality citations")
    medium_citations: int = Field(0, ge=0, description="Count of MEDIUM quality citations")
    weak_citations: int = Field(0, ge=0, description="Count of WEAK quality citations")

    @validator('strong_citations', 'medium_citations', 'weak_citations')
    def validate_citation_counts(cls, v, values):
        """Ensure citation quality counts don't exceed total"""
        if 'total_citations' in values:
            total = values['total_citations']
            # Sum of quality counts should equal total
            # (validated after all fields set)
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "status": "verified",
                "hallucination_probability": 0.05,
                "propositions_checked": 2,
                "propositions_verified": 2,
                "propositions_removed": 0,
                "quote_matches": {},
                "verification_latency_ms": 4500,
                "fallback_to_baseline": False,
                "failure_reason": None,
                "confidence_breakdown": {
                    "overall": 0.91,
                    "average_passage_relevance": 0.38,
                    "average_quote_quality": 0.34,
                    "average_verification_agreement": 0.14,
                    "average_citation_count": 0.05
                },
                "proposition_details": [],
                "abstention_factors": {
                    "low_confidence": False,
                    "high_hallucination": False,
                    "no_evidence": False,
                    "verification_failed": False
                },
                "citation_validation_errors": [],
                "total_citations": 1,
                "strong_citations": 1,
                "medium_citations": 0,
                "weak_citations": 0
            }
        }


class EnhancedAnswerResponse(BaseModel):
    """
    Production-ready answer response with full citation & confidence enhancement.

    Extends VerifiedAnswerResponse from Step 11.2 with Step 11.3 enhancements.
    Final response model for POST /api/v1/answer endpoint.
    """
    # Core answer fields (from AnswerResponse and VerifiedAnswerResponse)
    success: bool = Field(..., description="Whether answer generation succeeded")
    answer: str = Field(..., description="Original generated answer")
    verified_answer: str = Field(..., description="Verified answer (may differ if claims removed)")
    propositions: List[Dict] = Field(default_factory=list, description="Atomic claims")
    citations: List[Dict] = Field(default_factory=list, description="Source citations (legacy)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Baseline confidence")
    verified_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Adjusted confidence after verification"
    )
    can_answer: bool = Field(..., description="Whether system could answer")
    abstention_reason: Optional[str] = Field(None, description="Abstention reason (legacy)")
    processing_time_ms: int = Field(..., ge=0, description="Total processing time")
    passages_used: int = Field(..., ge=0, description="Number of passages used")
    model_used: str = Field(..., description="LLM model used")
    cache_hit: bool = Field(False, description="Whether answer was cached")

    # Step 11.3 Enhancement fields (NEW)
    abstained: bool = Field(False, description="Whether system abstained from answering")
    abstention_message: Optional[str] = Field(
        None,
        description="User-facing abstention message"
    )
    enriched_citations: List[EnrichedCitation] = Field(
        default_factory=list,
        description="Enriched citations with quality indicators and quote matches"
    )
    enhanced_metadata: EnhancedMetadata = Field(
        ...,
        description="Enhanced metadata with confidence breakdown and proposition details"
    )

    class Config:
        protected_namespaces = ()  # Allow model_used field
        json_schema_extra = {
            "example": {
                "success": True,
                "abstained": False,
                "answer": "Paris is the capital of France. [1]",
                "verified_answer": "Paris is the capital of France. [1]",
                "propositions": [
                    {"text": "Paris is the capital of France", "index": 0, "confidence": 0.95}
                ],
                "citations": [],  # Legacy field (use enriched_citations instead)
                "enriched_citations": [
                    {
                        "document_id": "uuid-1",
                        "document_name": "France_Guide.pdf",
                        "passage_text": "France's capital is Paris.",
                        "citation_number": 1,
                        "relevance_score": 0.95,
                        "quality": "STRONG",
                        "is_exact_quote": True,
                        "best_similarity": 0.97
                    }
                ],
                "confidence": 0.85,
                "verified_confidence": 0.91,
                "can_answer": True,
                "abstention_reason": None,
                "abstention_message": None,
                "processing_time_ms": 4750,
                "passages_used": 5,
                "model_used": "qwen2:7b",
                "cache_hit": False,
                "enhanced_metadata": {
                    "status": "verified",
                    "hallucination_probability": 0.05,
                    "confidence_breakdown": {"overall": 0.91},
                    "proposition_details": [],
                    "abstention_factors": {},
                    "total_citations": 1,
                    "strong_citations": 1
                }
            }
        }


class CitationConfig(BaseModel):
    """Configuration for citation formatting"""
    inline_format: Literal["simple", "detailed"] = Field(
        "simple",
        description="Citation format: 'simple' ([1]) or 'detailed' ([1: doc_name, p.5])"
    )
    highlight_enabled: bool = Field(
        True,
        description="Enable matched text highlighting with <mark> tags"
    )
    quality_indicators: bool = Field(
        True,
        description="Include citation quality indicators (STRONG/MEDIUM/WEAK)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "inline_format": "simple",
                "highlight_enabled": True,
                "quality_indicators": True
            }
        }


class AbstentionConfig(BaseModel):
    """Configuration for abstention behavior"""
    strict_mode: bool = Field(
        False,
        description="Require all factors to trigger (AND) vs any one factor (OR)"
    )
    low_confidence_threshold: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="Threshold for low confidence abstention"
    )
    high_hallucination_threshold: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Threshold for high hallucination abstention"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "strict_mode": False,
                "low_confidence_threshold": 0.3,
                "high_hallucination_threshold": 0.7
            }
        }
