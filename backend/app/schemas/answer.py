"""
Answer Generation Schemas for Step 11.1 - Ollama LLM Integration

Pydantic models for answer generation requests and responses.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


class AnswerRequest(BaseModel):
    """Request schema for answer generation"""
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User question to answer"
    )
    document_ids: Optional[List[str]] = Field(
        None,
        max_items=50,
        description="Optional list of document IDs to search within"
    )
    workspace_id: Optional[str] = Field(
        None,
        description="Workspace ID for multi-tenant isolation"
    )
    top_k: int = Field(
        5,
        ge=1,
        le=20,
        description="Number of passages to retrieve for context"
    )
    temperature: Optional[float] = Field(
        0.2,
        ge=0.0,
        le=1.0,
        description="LLM temperature (0.0=deterministic, 1.0=creative)"
    )
    include_citations: bool = Field(
        True,
        description="Include source citations in answer"
    )

    @validator('query')
    def validate_query(cls, v):
        """Validate and sanitize query string"""
        # Remove leading/trailing whitespace
        v = v.strip()

        # Check not empty after stripping
        if not v:
            raise ValueError("Query cannot be empty")

        # Remove null bytes
        if '\x00' in v:
            raise ValueError("Query contains invalid null bytes")

        # Prompt injection detection patterns
        dangerous_patterns = [
            r"ignore\s+previous\s+instructions",
            r"disregard\s+(the\s+)?(system\s+prompt|passages?|documents?|context)",
            r"you\s+are\s+now",
            r"new\s+role:",
        ]

        import re
        query_lower = v.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, query_lower):
                raise ValueError("Query contains prohibited instructions")

        return v

    @validator('document_ids')
    def validate_document_ids(cls, v):
        """Validate document ID format"""
        if v:
            # Validate that IDs are non-empty strings
            for doc_id in v:
                if not doc_id or not isinstance(doc_id, str) or not doc_id.strip():
                    raise ValueError(f"Invalid document ID: {doc_id}")
                # Optionally validate UUID format if it looks like a UUID
                # This allows both UUIDs and test strings like "doc1"
                if '-' in doc_id:
                    import uuid
                    try:
                        uuid.UUID(doc_id)
                    except ValueError:
                        raise ValueError(f"Invalid UUID format: {doc_id}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is the return policy?",
                "document_ids": ["550e8400-e29b-41d4-a716-446655440000"],
                "workspace_id": "default",
                "top_k": 5,
                "temperature": 0.2,
                "include_citations": True
            }
        }


class Proposition(BaseModel):
    """Individual atomic claim from answer"""
    text: str = Field(..., description="Proposition text (atomic claim)")
    index: int = Field(..., ge=0, description="Position in answer (0-indexed)")
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score for this claim"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "The return policy allows returns within 30 days of purchase.",
                "index": 0,
                "confidence": 0.92
            }
        }


class Citation(BaseModel):
    """Source citation for answer claim"""
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

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_name": "Return_Policy.pdf",
                "passage_text": "Customers may return items within 30 days...",
                "page": 1,
                "section": "Return Policy",
                "relevance_score": 0.95,
                "citation_number": 1
            }
        }


class AnswerResponse(BaseModel):
    """Response schema for answer generation"""
    success: bool = Field(..., description="Whether answer generation succeeded")
    answer: str = Field(..., description="Generated answer with citations")
    propositions: List[Proposition] = Field(
        default_factory=list,
        description="Atomic claims (3-5 propositions)"
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Source citations"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall answer confidence"
    )
    can_answer: bool = Field(
        ...,
        description="Whether system could answer from provided documents"
    )
    abstention_reason: Optional[str] = Field(
        None,
        description="Reason if system abstained from answering"
    )
    processing_time_ms: int = Field(..., ge=0, description="Processing time in milliseconds")
    passages_used: int = Field(..., ge=0, description="Number of passages used for context")
    model_used: str = Field(..., description="LLM model used for generation")
    cache_hit: bool = Field(False, description="Whether answer was retrieved from cache")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "answer": "The return policy allows returns within 30 days of purchase [1]. Items must be in original condition with tags attached [2].",
                "propositions": [
                    {
                        "text": "The return policy allows returns within 30 days of purchase.",
                        "index": 0,
                        "confidence": 0.95
                    },
                    {
                        "text": "Items must be in original condition with tags attached.",
                        "index": 1,
                        "confidence": 0.90
                    }
                ],
                "citations": [
                    {
                        "document_id": "550e8400-e29b-41d4-a716-446655440000",
                        "document_name": "Return_Policy.pdf",
                        "passage_text": "Customers may return items within 30 days...",
                        "page": 1,
                        "section": "Return Policy",
                        "relevance_score": 0.95,
                        "citation_number": 1
                    }
                ],
                "confidence": 0.92,
                "can_answer": True,
                "abstention_reason": None,
                "processing_time_ms": 2456,
                "passages_used": 5,
                "model_used": "qwen2:7b",
                "cache_hit": False
            }
        }


class OllamaHealthResponse(BaseModel):
    """Health check response for Ollama service"""
    status: str = Field(..., description="Health status: 'healthy' or 'unhealthy'")
    model: Optional[str] = Field(None, description="Model name if healthy")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "model": "qwen2:7b",
                "error": None,
                "response_time_ms": 45
            }
        }
