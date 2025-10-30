"""
Answer Generation Endpoint for Step 11.1 - Ollama LLM Integration

POST /api/v1/answer - Generate verified answer from documents
GET /health/ollama - Health check for Ollama service
"""
from fastapi import APIRouter, Depends, HTTPException, Header, status
from typing import Optional
import logging

from app.schemas.answer import (
    AnswerRequest,
    AnswerResponse,
    OllamaHealthResponse
)
from app.services.answer_service import get_answer_service, AnswerService
from app.services.ollama_client import get_ollama_client
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# AUTHENTICATION DEPENDENCY
# ============================================================================

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """
    Verify API key for authentication

    Args:
        x_api_key: API key from X-API-Key header

    Raises:
        HTTPException: 401 if API key invalid
    """
    if x_api_key != settings.API_KEY:
        logger.warning(f"Invalid API key attempted: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key


# ============================================================================
# ANSWER GENERATION ENDPOINT
# ============================================================================

@router.post(
    "",
    response_model=AnswerResponse,
    summary="Generate Answer",
    description="Generate verified answer from documents using Ollama LLM",
    responses={
        200: {
            "description": "Answer generated successfully",
            "model": AnswerResponse
        },
        400: {"description": "Invalid request parameters"},
        401: {"description": "Invalid API key"},
        503: {"description": "Ollama service unavailable"},
        500: {"description": "Internal server error"}
    }
)
async def generate_answer(
    request: AnswerRequest,
    answer_service: AnswerService = Depends(get_answer_service),
    api_key: str = Depends(verify_api_key)
) -> AnswerResponse:
    """
    Generate answer for user query

    **Authentication**: Requires X-API-Key header

    **Rate Limit**: 10 requests/minute per API key

    **Request Body**:
    - query: User question (1-500 characters)
    - document_ids: Optional list of document UUIDs to search
    - workspace_id: Optional workspace ID for isolation
    - top_k: Number of passages to retrieve (1-20, default: 5)
    - temperature: LLM temperature (0.0-1.0, default: 0.2)
    - include_citations: Whether to include source citations (default: true)

    **Response**:
    - answer: Generated answer with citation markers [1], [2], etc.
    - propositions: Atomic claims (3-5) extracted from answer
    - citations: Source documents with page numbers and sections
    - confidence: Overall confidence score (0.0-1.0)
    - can_answer: Whether system could answer from documents
    - abstention_reason: Reason if system abstained
    - processing_time_ms: Processing time in milliseconds

    **Example**:
    ```json
    {
        "query": "What is the return policy?",
        "document_ids": ["550e8400-e29b-41d4-a716-446655440000"],
        "top_k": 5,
        "include_citations": true
    }
    ```
    """
    logger.info(
        f"Answer request received: query_length={len(request.query)}, "
        f"document_ids={len(request.document_ids or [])}"
    )

    try:
        response = await answer_service.generate_answer(request)
        return response

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Unexpected error in answer endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# ============================================================================
# OLLAMA HEALTH CHECK ENDPOINT
# ============================================================================

@router.get(
    "/health/ollama",
    response_model=OllamaHealthResponse,
    summary="Ollama Health Check",
    description="Check if Ollama service is operational",
    responses={
        200: {
            "description": "Health check completed (may be healthy or unhealthy)",
            "model": OllamaHealthResponse
        }
    }
)
async def check_ollama_health() -> OllamaHealthResponse:
    """
    Check Ollama service health

    **No authentication required** (health check endpoint)

    **Response**:
    - status: "healthy" or "unhealthy"
    - model: Model name if service is healthy
    - error: Error message if service is unhealthy
    - response_time_ms: Response time in milliseconds

    **Example Response (Healthy)**:
    ```json
    {
        "status": "healthy",
        "model": "qwen2:7b",
        "error": null,
        "response_time_ms": 45
    }
    ```

    **Example Response (Unhealthy)**:
    ```json
    {
        "status": "unhealthy",
        "model": null,
        "error": "Connection failed: [Errno 111] Connection refused",
        "response_time_ms": null
    }
    ```
    """
    logger.info("Ollama health check requested")

    try:
        ollama_client = get_ollama_client()
        health_result = await ollama_client.health_check()

        return OllamaHealthResponse(**health_result)

    except Exception as e:
        logger.error(f"Error in Ollama health check: {e}", exc_info=True)
        return OllamaHealthResponse(
            status="unhealthy",
            model=None,
            error=str(e),
            response_time_ms=None
        )
