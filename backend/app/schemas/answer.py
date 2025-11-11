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
    # Core fields (new schema)
    chunk_id: Optional[str] = Field(None, description="Unique chunk identifier")
    document_id: str = Field(..., description="Source document UUID")
    document_filename: Optional[str] = Field(None, description="Document display name")
    content: Optional[str] = Field(None, max_length=1000, description="Cited passage text")
    page_number: Optional[int] = Field(None, ge=1, description="Page number in source")
    chunk_index: Optional[int] = Field(None, ge=0, description="Chunk index in document")
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score of this passage"
    )
    quality: Optional[str] = Field(None, description="Citation quality: STRONG, MEDIUM, or WEAK")
    metadata: dict = Field(default_factory=dict, description="Additional metadata (file_type, upload_date, etc.)")

    # Backward compatibility fields (for legacy tests and verification service)
    document_name: Optional[str] = Field(None, description="Alias for document_filename (deprecated)")
    passage_text: Optional[str] = Field(None, max_length=1000, description="Alias for content (deprecated)")
    page: Optional[int] = Field(None, ge=1, description="Alias for page_number (deprecated)")
    section: Optional[str] = Field(None, description="Section/heading in document (deprecated)")
    citation_number: Optional[int] = Field(None, ge=1, description="Citation number in answer text (deprecated)")

    def __init__(self, **data):
        """Initialize with automatic field aliasing for backward compatibility"""
        # If old fields are provided but not new ones, copy them over
        if 'document_name' in data and 'document_filename' not in data:
            data['document_filename'] = data['document_name']
        if 'passage_text' in data and 'content' not in data:
            data['content'] = data['passage_text']
        if 'page' in data and 'page_number' not in data:
            data['page_number'] = data['page']

        # If new fields are provided but not old ones, copy them for backward compat
        if 'document_filename' in data and 'document_name' not in data:
            data['document_name'] = data['document_filename']
        if 'content' in data and 'passage_text' not in data:
            data['passage_text'] = data['content']
        if 'page_number' in data and 'page' not in data:
            data['page'] = data['page_number']

        # Generate chunk_id if not provided
        if 'chunk_id' not in data and 'document_id' in data:
            chunk_idx = data.get('chunk_index', 0)
            data['chunk_id'] = f"chunk_{data['document_id']}_{chunk_idx}"

        # Set default chunk_index if not provided
        if 'chunk_index' not in data:
            data['chunk_index'] = 0

        # Set default quality based on relevance_score if not provided
        if 'quality' not in data and 'relevance_score' in data:
            score = data['relevance_score']
            if score >= 0.8:
                data['quality'] = "STRONG"
            elif score >= 0.6:
                data['quality'] = "MEDIUM"
            else:
                data['quality'] = "WEAK"

        super().__init__(**data)

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "chunk_550e8400_0",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_filename": "Return_Policy.pdf",
                "content": "Customers may return items within 30 days...",
                "page_number": 1,
                "chunk_index": 0,
                "relevance_score": 0.95,
                "quality": "STRONG",
                "metadata": {
                    "file_type": "pdf",
                    "upload_date": "2025-11-10T12:00:00Z"
                }
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
