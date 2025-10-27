"""
Search Schemas for Step 8.3 & 9.3 - Keyword and Vector Search

Pydantic models for search requests and responses.
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class SearchFilters(BaseModel):
    """Optional filters for search queries"""
    document_types: Optional[List[str]] = Field(None, max_items=10, description="Filter by document MIME types")
    date_from: Optional[datetime] = Field(None, description="Filter documents created after this date")
    date_to: Optional[datetime] = Field(None, description="Filter documents created before this date")
    min_quality: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum extraction quality score")
    tags: Optional[List[str]] = Field(None, max_items=20, description="Filter by document tags")

    @validator('date_to')
    def validate_date_range(cls, v, values):
        """Ensure date_to is after date_from"""
        if v and values.get('date_from'):
            if v < values['date_from']:
                raise ValueError("date_to must be after date_from")
        return v

    @validator('document_types')
    def validate_document_types(cls, v):
        """Validate document types against allowed list"""
        if v:
            allowed_types = [
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # docx
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # xlsx
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # pptx
                'text/plain',
                'text/markdown',
                'text/html'
            ]
            invalid = [t for t in v if t not in allowed_types]
            if invalid:
                raise ValueError(f"Invalid document types: {invalid}. Allowed: {allowed_types}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "document_types": ["application/pdf"],
                "date_from": "2025-01-01T00:00:00Z",
                "min_quality": 0.7
            }
        }


class SearchQuery(BaseModel):
    """Search request schema"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query string")
    filters: Optional[SearchFilters] = Field(None, description="Optional search filters")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")
    include_snippets: bool = Field(True, description="Include text snippets with highlighted keywords")
    include_metadata: bool = Field(True, description="Include document metadata in results")

    @validator('query')
    def validate_query(cls, v):
        """Sanitize and validate query string"""
        # Remove leading/trailing whitespace
        v = v.strip()

        # Check not empty after stripping
        if not v:
            raise ValueError("Query cannot be empty")

        # Basic SQL injection prevention (paranoid check - SQLAlchemy handles this)
        dangerous_patterns = [';--', 'DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'UPDATE ', 'EXEC(']
        v_upper = v.upper()
        for pattern in dangerous_patterns:
            if pattern in v_upper:
                raise ValueError(f"Query contains forbidden pattern: {pattern}")

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "machine learning algorithms",
                "filters": {
                    "document_types": ["application/pdf"],
                    "min_quality": 0.7
                },
                "limit": 10,
                "offset": 0
            }
        }


class SearchResultItem(BaseModel):
    """Individual search result"""
    document_id: str = Field(..., description="Document UUID")
    document_name: str = Field(..., description="Document display name")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")
    snippet: Optional[str] = Field(None, description="Text excerpt with highlighted keywords")
    chunk_index: Optional[int] = Field(None, description="Chunk index if result is from a chunk")
    chunk_position: Optional[dict] = Field(None, description="Chunk position in document {start: int, end: int}")
    extraction_quality: Optional[float] = Field(None, ge=0.0, le=1.0, description="Extraction quality score")
    document_type: Optional[str] = Field(None, description="Document MIME type")
    created_at: Optional[datetime] = Field(None, description="Document creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_name": "ML_Research_Paper.pdf",
                "relevance_score": 0.92,
                "snippet": "...various **machine learning algorithms** including neural networks...",
                "chunk_index": 5,
                "chunk_position": {"start": 4200, "end": 5150},
                "extraction_quality": 0.95,
                "document_type": "application/pdf",
                "created_at": "2025-10-23T14:30:00Z"
            }
        }


class SearchResponse(BaseModel):
    """Search response with results and metadata"""
    success: bool = Field(..., description="Whether the search was successful")
    query: str = Field(..., description="The search query that was executed")
    total_results: int = Field(..., ge=0, description="Total number of matching documents")
    returned_results: int = Field(..., ge=0, description="Number of results returned in this response")
    results: List[SearchResultItem] = Field(default_factory=list, description="Search results")
    processing_time_ms: int = Field(..., ge=0, description="Search processing time in milliseconds")
    filters_applied: Optional[SearchFilters] = Field(None, description="Filters that were applied to the search")
    suggestions: Optional[List[str]] = Field(None, description="Query suggestions or corrections")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "query": "machine learning algorithms",
                "total_results": 47,
                "returned_results": 10,
                "results": [
                    {
                        "document_id": "550e8400-e29b-41d4-a716-446655440000",
                        "document_name": "ML_Research.pdf",
                        "relevance_score": 0.92,
                        "snippet": "...various **machine learning algorithms**...",
                        "extraction_quality": 0.95
                    }
                ],
                "processing_time_ms": 45,
                "filters_applied": {
                    "document_types": ["application/pdf"],
                    "min_quality": 0.7
                }
            }
        }


# Quality validation schemas (for quality endpoint)
class ExtractionQualityReport(BaseModel):
    """Extraction quality validation report"""
    document_id: str
    document_name: str
    extraction_status: str  # 'passed', 'failed', 'warning'
    text_length: int
    extraction_quality: Optional[float]
    extraction_method: Optional[str]
    pages_with_ocr: Optional[int]
    total_pages: Optional[int]
    detected_language: Optional[str]
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ChunkingQualityReport(BaseModel):
    """Chunking quality validation report"""
    document_id: str
    chunking_status: str  # 'passed', 'failed', 'warning'
    chunk_count: int
    avg_chunk_size: Optional[int]
    chunks_in_range: Optional[int]
    has_proper_overlap: Optional[bool]
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class SearchReadinessReport(BaseModel):
    """Overall search readiness status"""
    document_id: str
    document_name: str
    is_search_ready: bool
    extraction_passed: bool
    chunking_passed: bool
    overall_quality_score: float
    extraction_details: Optional[dict]
    chunking_details: Optional[dict]
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# ========================================
# Step 9.3: Vector Search Schemas
# ========================================

class VectorSearchQuery(BaseModel):
    """Vector similarity search request schema"""
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language search query")
    filters: Optional[SearchFilters] = Field(None, description="Optional search filters")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")
    similarity_threshold: float = Field(0.0, ge=0.0, le=1.0, description="Minimum cosine similarity (0.0-1.0)")
    include_embeddings: bool = Field(False, description="Include embedding vectors in response (debug only)")

    @validator('query')
    def validate_query(cls, v):
        """Sanitize and validate query string"""
        # Remove leading/trailing whitespace
        v = v.strip()

        # Check not empty after stripping
        if not v:
            raise ValueError("Query cannot be empty")

        # Remove null bytes
        if '\x00' in v:
            raise ValueError("Query contains invalid null bytes")

        return v

    @validator('similarity_threshold')
    def validate_threshold(cls, v):
        """Validate similarity threshold"""
        if v < 0.0 or v > 1.0:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "How do I reset my password?",
                "filters": {
                    "document_types": ["application/pdf"],
                    "min_quality": 0.7
                },
                "limit": 10,
                "offset": 0,
                "similarity_threshold": 0.5
            }
        }


class SearchStrategyEnum(str, Enum):
    """Available search strategies"""
    KEYWORD = "keyword"
    VECTOR = "vector"
    HYBRID = "hybrid"  # Future - Step 10.1


class UnifiedSearchQuery(BaseModel):
    """Unified search request supporting multiple strategies"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query string")
    strategy: SearchStrategyEnum = Field(
        SearchStrategyEnum.KEYWORD,
        description="Search strategy: 'keyword' (fast, exact), 'vector' (semantic), 'hybrid' (future)"
    )
    filters: Optional[SearchFilters] = Field(None, description="Optional search filters")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return")
    offset: int = Field(0, ge=0, description="Pagination offset")
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum similarity for vector search")

    @validator('query')
    def validate_query(cls, v):
        """Sanitize and validate query string"""
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        if '\x00' in v:
            raise ValueError("Query contains invalid null bytes")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "machine learning algorithms",
                "strategy": "vector",
                "filters": {
                    "document_types": ["application/pdf"],
                    "min_quality": 0.7
                },
                "limit": 10,
                "offset": 0,
                "similarity_threshold": 0.5
            }
        }
