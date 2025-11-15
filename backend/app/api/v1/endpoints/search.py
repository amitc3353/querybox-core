"""
Search API Endpoints for Step 8.3 & 9.3 - Keyword and Vector Search

Provides keyword-based and semantic vector search functionality.
Step 10.3: Added citation extraction support
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import structlog
import time

from app.schemas.search import (
    SearchQuery,
    SearchResponse,
    VectorSearchQuery,
    UnifiedSearchQuery,
    SearchResponseWithCitations
)
from app.schemas.multi_query import MultiQueryResponse
from app.services.search import (
    get_search_service,
    get_vector_search_service,
    get_unified_search_service,
    get_hybrid_search_service,
    get_multi_query_retriever,
    KeywordSearchService
)
from app.services.embeddings import get_embedding_service
from app.db.database import get_db
from app.core.config import settings

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


@router.post("/keyword", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def keyword_search(
    query: SearchQuery,
    db: Session = Depends(get_db)
):
    """
    Dedicated keyword search endpoint for better API consistency

    **Note:** This endpoint provides the same functionality as POST /search/
    but with a more explicit, RESTful naming convention.

    **Search Strategy:**
    - PostgreSQL full-text search with to_tsvector and to_tsquery
    - Returns results ranked by relevance (ts_rank)
    - Generates highlighted snippets (ts_headline)

    **Example Request:**
    ```json
    {
      "query": "machine learning",
      "filters": {
        "document_types": ["application/pdf"]
      },
      "limit": 10
    }
    ```

    Args:
        query: SearchQuery with query string, filters, limit, offset
        db: Database session (injected)

    Returns:
        SearchResponse with keyword search results

    Raises:
        HTTPException 400: Invalid query or filters
        HTTPException 500: Database or server error
    """
    try:
        # Log search request
        logger.info(
            "keyword_search_request",
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
            "keyword_search_completed",
            query=query.query,
            total_results=response.total_results,
            returned_results=response.returned_results,
            processing_time_ms=response.processing_time_ms
        )

        return response

    except ValueError as e:
        logger.warning(
            "keyword_search_validation_error",
            query=query.query,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search query: {str(e)}"
        )

    except SQLAlchemyError as e:
        logger.error(
            "keyword_search_database_error",
            query=query.query,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during search. Please try again later."
        )

    except Exception as e:
        logger.error(
            "keyword_search_unexpected_error",
            query=query.query,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during search. Please try again later."
        )


@router.post("/hybrid", response_model=SearchResponseWithCitations, status_code=status.HTTP_200_OK)
async def hybrid_search(
    query: UnifiedSearchQuery,
    citations: bool = Query(
        default=True,
        description="Enable citation extraction and source tracking"
    ),
    citation_limit: int = Query(
        default=3,
        ge=1,
        le=5,
        description="Maximum citations per result (1-5, default: 3)"
    ),
    db: Session = Depends(get_db)
):
    """
    Dedicated hybrid search endpoint combining BM25 + vector search with RRF fusion

    **Search Strategy:**
    - Combines keyword (BM25) and semantic (vector) search
    - Merges results using Reciprocal Rank Fusion (RRF)
    - Supports advanced reranking with cross-encoder + MMR + deduplication
    - Provides best accuracy for production RAG applications

    **Hybrid Search Parameters:**
    - keyword_weight: Weight for keyword results (default: 0.5)
    - vector_weight: Weight for vector results (default: 0.5)
    - keyword_top_k: Candidates from keyword search (default: 100)
    - vector_top_k: Candidates from vector search (default: 100)

    **Advanced Reranking Parameters:**
    - enable_reranking: Enable cross-encoder reranking (default: False)
    - rerank_top_k: Candidates to keep after reranking (default: 50)
    - enable_mmr: Enable MMR diversification (default: from settings)
    - mmr_lambda: Diversity parameter, 0.0=max diversity, 1.0=max relevance (default: 0.7)
    - enable_dedup: Enable advanced deduplication (default: from settings)

    **Citation Parameters:**
    - citations: Enable citation extraction (default: True)
    - citation_limit: Max citations per result (default: 3, max: 5)

    **Example Request:**
    ```json
    {
      "query": "machine learning algorithms",
      "filters": {
        "document_types": ["application/pdf"]
      },
      "limit": 10,
      "keyword_weight": 0.5,
      "vector_weight": 0.5,
      "enable_reranking": true,
      "rerank_top_k": 50,
      "enable_mmr": true,
      "mmr_lambda": 0.7
    }
    ```

    Args:
        query: UnifiedSearchQuery with hybrid search parameters
        citations: Enable citation extraction (default: True)
        citation_limit: Maximum citations per result (1-5, default: 3)
        db: Database session (injected)

    Returns:
        SearchResponseWithCitations with hybrid search results and citations

    Raises:
        HTTPException 400: Invalid query or parameters
        HTTPException 500: Database or server error
    """
    try:
        start_time = time.time()

        # Override strategy to hybrid
        query.strategy = "hybrid"

        # Log search request
        logger.info(
            "hybrid_search_request",
            query=query.query[:100],
            limit=query.limit,
            keyword_weight=query.keyword_weight,
            vector_weight=query.vector_weight,
            enable_reranking=query.enable_reranking,
            citations_enabled=citations,
            citation_limit=citation_limit,
            retrieval_mode=settings.RETRIEVAL_MODE
        )

        # Get services
        embedding_service = get_embedding_service()

        # Route based on RETRIEVAL_MODE configuration (Phase 5: Multi-Query RAG)
        if settings.RETRIEVAL_MODE == "multi_query" and settings.MULTI_QUERY_ENABLED:
            # Use Multi-Query RAG retriever
            logger.info("hybrid_search_using_multi_query", query=query.query[:100])

            # Get hybrid search service (required for Multi-Query RAG)
            # Import required services
            from app.services.search.bm25_search_service import get_bm25_search_service
            from app.services.search.vector_search_service import get_vector_search_service as get_vector_svc
            from app.services.search.rrf_ranker import get_rrf_ranker
            from app.services.search.reranking_pipeline import get_reranking_pipeline

            # Instantiate all required services
            bm25_service = get_bm25_search_service(db)
            vector_service = get_vector_svc(db, embedding_service)
            rrf_ranker = get_rrf_ranker()
            reranking_pipeline = get_reranking_pipeline()

            # Create hybrid search service with all dependencies
            hybrid_search_service = get_hybrid_search_service(
                db=db,
                bm25_service=bm25_service,
                vector_service=vector_service,
                rrf_ranker=rrf_ranker,
                reranking_pipeline=reranking_pipeline
            )

            # Initialize Redis client for caching (optional)
            redis_client = None
            if settings.MULTI_QUERY_CACHE_ENABLED:
                try:
                    from redis import Redis
                    redis_client = Redis(
                        host=settings.REDIS_HOST,
                        port=settings.REDIS_PORT,
                        db=settings.REDIS_DB,
                        decode_responses=True,
                    )
                except Exception as e:
                    logger.warning("multi_query_redis_init_failed", error=str(e))

            # Create multi-query retriever
            multi_query_retriever = get_multi_query_retriever(
                hybrid_search_service=hybrid_search_service,
                redis_client=redis_client,
            )

            # Execute multi-query retrieval
            response = await multi_query_retriever.retrieve(
                query=query.query,
                client_id=1,  # TODO: Get from auth context
                top_k=query.limit,
                filters=query.filters,
                enable_reranking=query.enable_reranking,
            )
        else:
            # Use standard unified search service
            logger.info("hybrid_search_using_standard", query=query.query[:100])
            unified_search_service = get_unified_search_service(db, embedding_service)

            # Execute hybrid search
            response = unified_search_service.search(
                query=query.query,
                strategy="hybrid",
                filters=query.filters,
                limit=query.limit,
                offset=query.offset,
                # Vector search parameters
                similarity_threshold=query.similarity_threshold,
                # Hybrid search parameters
                keyword_weight=query.keyword_weight,
                vector_weight=query.vector_weight,
                keyword_top_k=query.keyword_top_k,
                vector_top_k=query.vector_top_k,
                # Advanced reranking parameters
                enable_reranking=query.enable_reranking,
                rerank_top_k=query.rerank_top_k,
                enable_mmr=query.enable_mmr,
                enable_dedup=query.enable_dedup
            )

        # Extract citations if enabled
        if citations:
            try:
                from app.services.search.citation_extraction_service import get_citation_service

                citation_service = get_citation_service(db)
                enriched_results = citation_service.extract_citations(
                    search_results=response.results,
                    citation_limit=citation_limit
                )

                logger.info(
                    "hybrid_citation_extraction_completed",
                    num_results=len(enriched_results),
                    total_citations=sum(len(r.citations) for r in enriched_results)
                )

                total_time_ms = int((time.time() - start_time) * 1000)

                # Build response with citations, preserving multi_query_metadata if present
                response_data = {
                    "success": response.success,
                    "query": response.query,
                    "total_results": response.total_results,
                    "returned_results": len(enriched_results),
                    "results": enriched_results,
                    "processing_time_ms": total_time_ms,
                    "citations_enabled": True,
                    "filters_applied": response.filters_applied,
                    "reranking_metadata": response.reranking_metadata if hasattr(response, 'reranking_metadata') else None
                }

                # Include multi_query_metadata if present (Phase 5: Multi-Query RAG)
                if hasattr(response, 'multi_query_metadata') and response.multi_query_metadata:
                    response_data["multi_query_metadata"] = response.multi_query_metadata

                return SearchResponseWithCitations(**response_data)

            except Exception as e:
                logger.error(
                    "hybrid_citation_extraction_failed",
                    error=str(e),
                    exc_info=True
                )
                # Graceful degradation: return results without citations
                from app.schemas.search import SearchResultItemWithCitations

                enriched_results = [
                    SearchResultItemWithCitations(**r.dict())
                    for r in response.results
                ]

                total_time_ms = int((time.time() - start_time) * 1000)

                # Build response, preserving multi_query_metadata if present
                response_data = {
                    "success": response.success,
                    "query": response.query,
                    "total_results": response.total_results,
                    "returned_results": len(enriched_results),
                    "results": enriched_results,
                    "processing_time_ms": total_time_ms,
                    "citations_enabled": False,
                    "filters_applied": response.filters_applied,
                    "reranking_metadata": response.reranking_metadata if hasattr(response, 'reranking_metadata') else None
                }

                # Include multi_query_metadata if present (Phase 5: Multi-Query RAG)
                if hasattr(response, 'multi_query_metadata') and response.multi_query_metadata:
                    response_data["multi_query_metadata"] = response.multi_query_metadata

                return SearchResponseWithCitations(**response_data)

        # No citations requested
        from app.schemas.search import SearchResultItemWithCitations

        enriched_results = [
            SearchResultItemWithCitations(**r.dict())
            for r in response.results
        ]

        total_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "hybrid_search_completed",
            query=query.query[:100],
            total_results=response.total_results,
            returned_results=len(enriched_results),
            processing_time_ms=total_time_ms,
            citations_enabled=False
        )

        return SearchResponseWithCitations(
            success=response.success,
            query=response.query,
            total_results=response.total_results,
            returned_results=len(enriched_results),
            results=enriched_results,
            processing_time_ms=total_time_ms,
            citations_enabled=False,
            filters_applied=response.filters_applied,
            reranking_metadata=response.reranking_metadata if hasattr(response, 'reranking_metadata') else None
        )

    except ValueError as e:
        logger.warning(
            "hybrid_search_validation_error",
            query=query.query[:100],
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search request: {str(e)}"
        )

    except RuntimeError as e:
        logger.error(
            "hybrid_search_runtime_error",
            query=query.query[:100],
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search execution failed: {str(e)}"
        )

    except Exception as e:
        logger.error(
            "hybrid_search_unexpected_error",
            query=query.query[:100],
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during search. Please try again later."
        )


@router.post("/unified", response_model=SearchResponseWithCitations, status_code=status.HTTP_200_OK)
async def unified_search(
    query: UnifiedSearchQuery,
    citations: bool = Query(
        default=True,
        description="Enable citation extraction and source tracking (Step 10.3)"
    ),
    citation_limit: int = Query(
        default=3,
        ge=1,
        le=5,
        description="Maximum citations per result (1-5, default: 3)"
    ),
    db: Session = Depends(get_db)
):
    """
    Unified search endpoint supporting multiple strategies with citation extraction

    **Strategies:**
    - keyword: Full-text search (fast, exact matches)
    - vector: Semantic search (slower, conceptual matches)
    - hybrid: Combined BM25 + vector search with RRF fusion (best accuracy)

    **Hybrid Search Parameters (Step 10.1):**
    - keyword_weight: Weight for keyword results (default: 0.5)
    - vector_weight: Weight for vector results (default: 0.5)
    - keyword_top_k: Candidates from keyword search (default: 100)
    - vector_top_k: Candidates from vector search (default: 100)

    **Advanced Reranking Parameters (Step 10.2):**
    - enable_reranking: Enable cross-encoder reranking + MMR + deduplication (default: False)
    - rerank_top_k: Candidates to keep after cross-encoder reranking (default: 50)
    - enable_mmr: Enable MMR diversification (default: from settings)
    - mmr_lambda: MMR diversity parameter, 0.0=max diversity, 1.0=max relevance (default: 0.7)
    - enable_dedup: Enable advanced deduplication (default: from settings)
    - semantic_dedup_threshold: Semantic similarity threshold for deduplication (default: 0.95)

    **Citation Extraction Parameters (Step 10.3):**
    - citations: Enable citation extraction (default: True)
    - citation_limit: Max citations per result (default: 3, max: 5)

    **Example Request (Hybrid with Reranking):**
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
      "vector_top_k": 100,
      "enable_reranking": true,
      "rerank_top_k": 50,
      "enable_mmr": true,
      "mmr_lambda": 0.7,
      "enable_dedup": true
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
        query: UnifiedSearchQuery with strategy, filters, and reranking parameters
        db: Database session (injected)

    Returns:
        SearchResponse with results from selected strategy and optional reranking_metadata

    Raises:
        HTTPException 400: Invalid query, strategy, or filters
        HTTPException 500: Database or server error
    """
    try:
        start_time = time.time()

        # Log search request
        logger.info(
            "unified_search_request",
            query=query.query[:100],
            strategy=query.strategy,
            limit=query.limit,
            citations_enabled=citations,
            citation_limit=citation_limit
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
            # Vector search parameters
            similarity_threshold=query.similarity_threshold,
            # Hybrid search parameters (Step 10.1)
            keyword_weight=query.keyword_weight,
            vector_weight=query.vector_weight,
            keyword_top_k=query.keyword_top_k,
            vector_top_k=query.vector_top_k,
            # Advanced reranking parameters (Step 10.2)
            enable_reranking=query.enable_reranking,
            rerank_top_k=query.rerank_top_k,
            enable_mmr=query.enable_mmr,
            enable_dedup=query.enable_dedup
        )

        # Step 10.3: Extract citations if enabled
        if citations:
            try:
                from app.services.search.citation_extraction_service import get_citation_service

                citation_service = get_citation_service(db)
                enriched_results = citation_service.extract_citations(
                    search_results=response.results,
                    citation_limit=citation_limit
                )

                logger.info(
                    "citation_extraction_completed",
                    num_results=len(enriched_results),
                    total_citations=sum(len(r.citations) for r in enriched_results)
                )

                # Calculate total processing time
                total_time_ms = int((time.time() - start_time) * 1000)

                # Return response with citations
                return SearchResponseWithCitations(
                    success=response.success,
                    query=response.query,
                    total_results=response.total_results,
                    returned_results=len(enriched_results),
                    results=enriched_results,
                    processing_time_ms=total_time_ms,
                    citations_enabled=True,
                    filters_applied=response.filters_applied,
                    reranking_metadata=response.reranking_metadata if hasattr(response, 'reranking_metadata') else None
                )

            except Exception as e:
                logger.error(
                    "citation_extraction_failed",
                    error=str(e),
                    exc_info=True
                )
                # Graceful degradation: return results without citations
                from app.schemas.search import SearchResultItemWithCitations

                enriched_results = [
                    SearchResultItemWithCitations(**r.dict())
                    for r in response.results
                ]

                total_time_ms = int((time.time() - start_time) * 1000)

                # Build response, preserving multi_query_metadata if present
                response_data = {
                    "success": response.success,
                    "query": response.query,
                    "total_results": response.total_results,
                    "returned_results": len(enriched_results),
                    "results": enriched_results,
                    "processing_time_ms": total_time_ms,
                    "citations_enabled": False,
                    "filters_applied": response.filters_applied,
                    "reranking_metadata": response.reranking_metadata if hasattr(response, 'reranking_metadata') else None
                }

                # Include multi_query_metadata if present (Phase 5: Multi-Query RAG)
                if hasattr(response, 'multi_query_metadata') and response.multi_query_metadata:
                    response_data["multi_query_metadata"] = response.multi_query_metadata

                return SearchResponseWithCitations(**response_data)

        # No citations requested - convert to SearchResponseWithCitations format
        from app.schemas.search import SearchResultItemWithCitations

        enriched_results = [
            SearchResultItemWithCitations(**r.dict())
            for r in response.results
        ]

        total_time_ms = int((time.time() - start_time) * 1000)

        # Log search results
        logger.info(
            "unified_search_completed",
            query=query.query[:100],
            strategy=query.strategy,
            total_results=response.total_results,
            returned_results=response.returned_results,
            processing_time_ms=total_time_ms,
            citations_enabled=False
        )

        return SearchResponseWithCitations(
            success=response.success,
            query=response.query,
            total_results=response.total_results,
            returned_results=len(enriched_results),
            results=enriched_results,
            processing_time_ms=total_time_ms,
            citations_enabled=False,
            filters_applied=response.filters_applied,
            reranking_metadata=response.reranking_metadata if hasattr(response, 'reranking_metadata') else None
        )

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


@router.get("/reranking/health", status_code=status.HTTP_200_OK)
async def reranking_health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint for reranking functionality (Step 10.2 - Phase 5)

    Verifies:
    - Cross-encoder model is loaded
    - GPU availability (if configured)
    - Embeddings available for MMR diversity calculation
    - All reranking components operational

    Returns:
        Health status with reranking capability details

    Example Response:
    ```json
    {
        "status": "healthy",
        "service": "reranking",
        "cross_encoder_loaded": true,
        "cross_encoder_model": "cross-encoder/ms-marco-MiniLM-L6-v2",
        "device": "cuda",
        "gpu_available": true,
        "embeddings_available": 5420,
        "mmr_ready": true,
        "deduplication_ready": true,
        "message": "Reranking service is operational"
    }
    ```
    """
    try:
        from app.models.embedding import Embedding
        from app.core.config import settings
        import torch

        # Initialize health status
        health_status = {
            "status": "healthy",
            "service": "reranking",
            "cross_encoder_loaded": False,
            "cross_encoder_model": None,
            "device": None,
            "gpu_available": False,
            "embeddings_available": 0,
            "mmr_ready": False,
            "deduplication_ready": False,
            "message": "Reranking service is operational"
        }

        # Check GPU availability
        gpu_available = torch.cuda.is_available()
        health_status["gpu_available"] = gpu_available

        # Get configured device (reranking uses cross-encoder model)
        configured_device = settings.CROSS_ENCODER_DEVICE
        actual_device = "cuda" if gpu_available and configured_device == "cuda" else "cpu"
        health_status["device"] = actual_device

        # Check cross-encoder model loading
        try:
            from app.services.search.cross_encoder_service import get_cross_encoder_service
            cross_encoder = get_cross_encoder_service()

            if cross_encoder.model is not None:
                health_status["cross_encoder_loaded"] = True
                health_status["cross_encoder_model"] = cross_encoder.model_name
            else:
                health_status["status"] = "degraded"
                health_status["message"] = "Cross-encoder model not loaded"

        except Exception as e:
            logger.warning(
                "reranking_health_check_cross_encoder_error",
                error=str(e)
            )
            health_status["status"] = "degraded"
            health_status["message"] = f"Cross-encoder initialization error: {str(e)}"

        # Check embeddings availability for MMR
        try:
            embedding_count = db.query(Embedding).filter(
                Embedding.embedding.isnot(None)
            ).count()
            health_status["embeddings_available"] = embedding_count
            health_status["mmr_ready"] = embedding_count > 0

        except Exception as e:
            logger.warning(
                "reranking_health_check_embeddings_error",
                error=str(e)
            )
            health_status["mmr_ready"] = False

        # Deduplication is always ready (doesn't depend on external resources)
        health_status["deduplication_ready"] = True

        # Overall status check
        if not health_status["cross_encoder_loaded"]:
            health_status["status"] = "degraded"
            health_status["message"] = "Reranking available but cross-encoder not loaded"
        elif not health_status["mmr_ready"]:
            health_status["status"] = "degraded"
            health_status["message"] = "Reranking available but MMR requires embeddings"

        return health_status

    except Exception as e:
        logger.error(
            "reranking_health_check_failed",
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reranking service is unavailable"
        )
