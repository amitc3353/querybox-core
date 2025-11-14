"""
Multi-Query RAG Schemas - Phase 5: Advanced Retrieval

Extended schemas for Multi-Query RAG responses with cost tracking and metadata.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.search import SearchResponse, SearchResultItem, SearchFilters


class MultiQueryMetadata(BaseModel):
    """
    Multi-Query RAG execution metadata.

    Tracks query variations, LLM costs, caching performance, and fusion statistics.
    """
    query_variations: List[str] = Field(
        default_factory=list,
        description="Generated query variations used for parallel search"
    )
    cost_usd: float = Field(
        0.0,
        ge=0.0,
        description="Total LLM cost in USD for query generation"
    )
    cache_hit: bool = Field(
        False,
        description="Whether query variations were retrieved from cache"
    )
    num_queries_searched: int = Field(
        0,
        ge=0,
        description="Total queries searched (original + variations)"
    )
    total_chunks_before_fusion: int = Field(
        0,
        ge=0,
        description="Total chunks collected before fusion"
    )
    fusion_algorithm: str = Field(
        "frequency_rrf",
        description="Fusion algorithm used (frequency_rrf)"
    )
    freq_weight: float = Field(
        2.0,
        ge=0.0,
        description="Frequency weight in fusion scoring"
    )
    rrf_weight: float = Field(
        1.0,
        ge=0.0,
        description="RRF weight in fusion scoring"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query_variations": [
                    "What are different machine learning techniques?",
                    "Explain various ML algorithms and their applications"
                ],
                "cost_usd": 0.00018,
                "cache_hit": False,
                "num_queries_searched": 3,
                "total_chunks_before_fusion": 27,
                "fusion_algorithm": "frequency_rrf",
                "freq_weight": 2.0,
                "rrf_weight": 1.0
            }
        }


class MultiQueryResponse(SearchResponse):
    """
    Extended search response for Multi-Query RAG.

    Inherits all SearchResponse fields and adds Multi-Query specific metadata.
    """
    multi_query_metadata: Optional[MultiQueryMetadata] = Field(
        None,
        description="Multi-Query RAG execution metadata (only present when Multi-Query is used)"
    )

    class Config:
        extra = "allow"  # Allow additional dynamic fields
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
                        "snippet": "...machine learning algorithms...",
                        "chunk_index": 5,
                        "extraction_quality": 0.95
                    }
                ],
                "processing_time_ms": 245,
                "filters_applied": {
                    "document_types": ["application/pdf"],
                    "min_quality": 0.7
                },
                "multi_query_metadata": {
                    "query_variations": [
                        "What are different machine learning techniques?",
                        "Explain various ML algorithms and their applications"
                    ],
                    "cost_usd": 0.00018,
                    "cache_hit": False,
                    "num_queries_searched": 3,
                    "total_chunks_before_fusion": 27,
                    "fusion_algorithm": "frequency_rrf",
                    "freq_weight": 2.0,
                    "rrf_weight": 1.0
                }
            }
        }


class MultiQueryCostSummary(BaseModel):
    """
    Cost summary for Multi-Query RAG operations.

    Useful for admin dashboards and cost monitoring.
    """
    total_queries_processed: int = Field(..., ge=0, description="Total queries processed")
    total_cost_usd: float = Field(..., ge=0.0, description="Total LLM cost in USD")
    cache_hit_rate: float = Field(..., ge=0.0, le=1.0, description="Cache hit rate (0.0-1.0)")
    avg_cost_per_query: float = Field(..., ge=0.0, description="Average cost per query in USD")
    total_variations_generated: int = Field(..., ge=0, description="Total query variations generated")

    class Config:
        json_schema_extra = {
            "example": {
                "total_queries_processed": 1000,
                "total_cost_usd": 0.13,
                "cache_hit_rate": 0.3,
                "avg_cost_per_query": 0.00013,
                "total_variations_generated": 2000
            }
        }
