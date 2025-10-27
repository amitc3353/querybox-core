"""
Search API Endpoints for Step 8.3 & 9.3 - Keyword and Vector Search

Provides keyword-based and semantic vector search functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import structlog

from app.schemas.search import (
    SearchQuery,
    SearchResponse,
    VectorSearchQuery,
    UnifiedSearchQuery
)
from app.services.search import (
    get_search_service,
    get_vector_search_service,
    get_unified_search_service,
    KeywordSearchService
)
from app.services.embeddings import get_embedding_service
from app.db.database import get_db

# Initialize router
router = APIRouter()

# Initialize logger
logger = structlog.get_logger()


@router.post("/", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search_documents(
    query: SearchQuery,
    db: Session = Depends(get_db)
):
    """
    Search documents using keyword-based full-text search (default/legacy)

    **Note:** For semantic search, use POST /search/semantic
    **Note:** For unified search with strategy selection, use POST /search/unified

    **Search Strategy:**
    - Searches both full documents (`document_texts`) and chunks (`embeddings`)
    - Uses PostgreSQL full-text search (to_tsvector, to_tsquery)
    - Returns results ranked by relevance (ts_rank)
    - Generates highlighted snippets (ts_headline)

    **Filters Supported:**
    - Document types (MIME types)
    - Minimum extraction quality
    - Date range (created_at)
    - Tags

    **Example Request:**
    ```json
    {
      "query": "machine learning algorithms",
      "filters": {
        "document_types": ["application/pdf"],
        "min_quality": 0.7
      },
      "limit": 10,
      "offset": 0
    }
    ```

    **Example Response:**
    ```json
    {
      "success": true,
      "query": "machine learning algorithms",
      "total_results": 47,
      "returned_results": 10,
      "results": [
        {
          "document_id": "550e8400-...",
          "document_name": "ML_Research.pdf",
          "relevance_score": 0.92,
          "snippet": "...various **machine learning algorithms**...",
          "extraction_quality": 0.95
        }
      ],
      "processing_time_ms": 45
    }
    ```

    Args:
        query: SearchQuery with query string, filters, limit, offset
        db: Database session (injected)

    Returns:
        SearchResponse with search results and metadata

    Raises:
        HTTPException 400: Invalid query or filters
        HTTPException 500: Database or server error
    """
    try:
        # Log search request
        logger.info(
            "search_request",
            query=query.query,
            filters=query.filters.dict() if query.filters else None,
            limit=query.limit,
            offset=query.offset
        )

        # Get search service
        search_service = get_search_service(db)

        # Execute search
        response = search_service.search(
            query=query.query,
            filters=query.filters,
            limit=query.limit,
            offset=query.offset
        )

        # Log search results
        logger.info(
            "search_completed",
            query=query.query,
            total_results=response.total_results,
            returned_results=response.returned_results,
            processing_time_ms=response.processing_time_ms
        )

        return response

    except ValueError as e:
        # Validation errors (e.g., invalid query format)
        logger.warning(
            "search_validation_error",
            query=query.query,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search query: {str(e)}"
        )

    except SQLAlchemyError as e:
        # Database errors
        logger.error(
            "search_database_error",
            query=query.query,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during search. Please try again later."
        )

    except Exception as e:
        # Unexpected errors
        logger.error(
            "search_unexpected_error",
            query=query.query,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during search. Please try again later."
        )


@router.post("/semantic", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def semantic_search(
    query: VectorSearchQuery,
    db: Session = Depends(get_db)
):
    """
    Semantic vector similarity search using BGE-M3 embeddings

    **Search Strategy:**
    - Converts query to 1024-dimensional vector using BGE-M3
    - Performs cosine similarity search using pgvector
    - Returns results ranked by semantic relevance (0.0-1.0)
    - Supports 100+ languages through BGE-M3 model

    **Performance:**
    - Target latency: <200ms p99
    - Uses HNSW/IVFFlat indexes for fast retrieval

    **Filters Supported:**
    - Document types (MIME types)
    - Minimum extraction quality
    - Date range (created_at)
    - Tags
    - Similarity threshold

    **Example Request:**
    ```json
    {
      "query": "How do I reset my password?",
      "filters": {
        "document_types": ["application/pdf"],
        "min_quality": 0.7
      },
      "limit": 10,
      "similarity_threshold": 0.5
    }
    ```

    **Example Response:**
    ```json
    {
      "success": true,
      "query": "How do I reset my password?",
      "total_results": 23,
      "returned_results": 10,
      "results": [
        {
          "document_id": "550e8400-...",
          "document_name": "User_Guide.pdf",
          "relevance_score": 0.87,
          "snippet": "...Password Recovery Procedure...",
          "extraction_quality": 0.95
        }
      ],
      "processing_time_ms": 145
    }
    ```

    Args:
        query: VectorSearchQuery with query string, filters, limit, offset, similarity_threshold
        db: Database session (injected)

    Returns:
        SearchResponse with semantically ranked results

    Raises:
        HTTPException 400: Invalid query or filters
        HTTPException 500: Database, embedding, or server error
    """
    try:
        # Log search request
        logger.info(
            "semantic_search_request",
            query=query.query[:100],
            filters=query.filters.dict() if query.filters else None,
            limit=query.limit,
            offset=query.offset,
            similarity_threshold=query.similarity_threshold
        )

        # Get services
        embedding_service = get_embedding_service()
        vector_search_service = get_vector_search_service(db, embedding_service)

        # Execute vector search
        response = vector_search_service.search(
            query=query.query,
            filters=query.filters,
            limit=query.limit,
            offset=query.offset,
            similarity_threshold=query.similarity_threshold
        )

        # Log search results
        logger.info(
            "semantic_search_completed",
            query=query.query[:100],
            total_results=response.total_results,
            returned_results=response.returned_results,
            processing_time_ms=response.processing_time_ms
        )

        return response

    except ValueError as e:
        # Validation errors (e.g., invalid query format, empty embeddings)
        logger.warning(
            "semantic_search_validation_error",
            query=query.query[:100],
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search query: {str(e)}"
        )

    except RuntimeError as e:
        # Embedding generation or search execution errors
        logger.error(
            "semantic_search_runtime_error",
            query=query.query[:100],
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search execution failed: {str(e)}"
        )

    except SQLAlchemyError as e:
        # Database errors
        logger.error(
            "semantic_search_database_error",
            query=query.query[:100],
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during search. Please try again later."
        )

    except Exception as e:
        # Unexpected errors
        logger.error(
            "semantic_search_unexpected_error",
            query=query.query[:100],
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during search. Please try again later."
        )


@router.post("/unified", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def unified_search(
    query: UnifiedSearchQuery,
    db: Session = Depends(get_db)
):
    """
    Unified search endpoint supporting multiple strategies

    **Strategies:**
    - keyword: Full-text search (fast, exact matches)
    - vector: Semantic search (slower, conceptual matches)
    - hybrid: Combined BM25 + vector search with RRF fusion (best accuracy)

    **Hybrid Search Parameters:**
    - keyword_weight: Weight for keyword results (default: 0.5)
    - vector_weight: Weight for vector results (default: 0.5)
    - keyword_top_k: Candidates from keyword search (default: 100)
    - vector_top_k: Candidates from vector search (default: 100)

    **Example Request (Hybrid):**
    ```json
    {
      "query": "machine learning algorithms",
      "strategy": "hybrid",
      "filters": {
        "document_types": ["application/pdf"]
      },
      "limit": 10,
      "keyword_weight": 0.5,
      "vector_weight": 0.5,
      "keyword_top_k": 100,
      "vector_top_k": 100
    }
    ```

    **Example Request (Vector):**
    ```json
    {
      "query": "machine learning algorithms",
      "strategy": "vector",
      "filters": {
        "document_types": ["application/pdf"]
      },
      "limit": 10,
      "similarity_threshold": 0.5
    }
    ```

    Args:
        query: UnifiedSearchQuery with strategy, filters, etc.
        db: Database session (injected)

    Returns:
        SearchResponse with results from selected strategy

    Raises:
        HTTPException 400: Invalid query, strategy, or filters
        HTTPException 500: Database or server error
    """
    try:
        # Log search request
        logger.info(
            "unified_search_request",
            query=query.query[:100],
            strategy=query.strategy,
            limit=query.limit
        )

        # Get services
        embedding_service = get_embedding_service()
        unified_search_service = get_unified_search_service(db, embedding_service)

        # Execute search with selected strategy
        response = unified_search_service.search(
            query=query.query,
            strategy=query.strategy,
            filters=query.filters,
            limit=query.limit,
            offset=query.offset,
            similarity_threshold=query.similarity_threshold,
            keyword_weight=query.keyword_weight,
            vector_weight=query.vector_weight,
            keyword_top_k=query.keyword_top_k,
            vector_top_k=query.vector_top_k
        )

        # Log search results
        logger.info(
            "unified_search_completed",
            query=query.query[:100],
            strategy=query.strategy,
            total_results=response.total_results,
            returned_results=response.returned_results,
            processing_time_ms=response.processing_time_ms
        )

        return response

    except ValueError as e:
        # Validation errors (invalid strategy, query, etc.)
        logger.warning(
            "unified_search_validation_error",
            query=query.query[:100],
            strategy=query.strategy,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search request: {str(e)}"
        )

    except RuntimeError as e:
        # Runtime errors (e.g., embedding generation, search execution)
        logger.error(
            "unified_search_runtime_error",
            query=query.query[:100],
            strategy=query.strategy,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search execution failed: {str(e)}"
        )

    except Exception as e:
        # Unexpected errors
        logger.error(
            "unified_search_unexpected_error",
            query=query.query[:100],
            strategy=query.strategy,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during search. Please try again later."
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def search_health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint for search functionality

    Verifies:
    - Database connection is working
    - Search indexes exist
    - Search service is operational

    Returns:
        Health status with searchable document count
    """
    try:
        from app.models.document_text import DocumentText
        from app.models.embedding import Embedding

        # Count searchable documents
        searchable_count = db.query(DocumentText).filter(
            DocumentText.text_length > 0
        ).count()

        # Count embeddings for vector search
        embedding_count = db.query(Embedding).filter(
            Embedding.embedding.isnot(None)
        ).count()

        return {
            "status": "healthy",
            "service": "search",
            "searchable_documents": searchable_count,
            "embeddings_available": embedding_count,
            "vector_search_ready": embedding_count > 0,
            "message": "Search service is operational"
        }

    except Exception as e:
        logger.error(
            "search_health_check_failed",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search service is unavailable"
        )
