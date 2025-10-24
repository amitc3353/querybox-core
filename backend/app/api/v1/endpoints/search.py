"""
Search API Endpoints for Step 8.3 - Simple Keyword Search

Provides keyword-based document search functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import structlog

from app.schemas.search import SearchQuery, SearchResponse
from app.services.search import get_search_service, KeywordSearchService
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
    Search documents using keyword-based full-text search

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

        # Count searchable documents
        searchable_count = db.query(DocumentText).filter(
            DocumentText.text_length > 0
        ).count()

        return {
            "status": "healthy",
            "service": "search",
            "searchable_documents": searchable_count,
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
