"""
Document Query Endpoints
Step 7: Document Query and Retrieval API
Step 8.3: Search Quality Validation

Endpoints:
- GET  /documents                            - List documents with pagination/filtering
- GET  /documents/search                     - Search documents
- GET  /documents/stats                      - Document statistics
- GET  /documents/{document_id}/search-quality  - Validate search readiness (Step 8.3)
- GET  /documents/{document_id}              - Get single document by ID
- DELETE /documents/{document_id}            - Soft delete document

IMPORTANT: Endpoint order matters in FastAPI!
Specific paths (/search, /stats, /{id}/search-quality) MUST come before generic paths (/{document_id})
"""
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import logging

from app.db.database import get_db
from app.services.document_service import DocumentService
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentSearchResponse,
    DocumentStatsResponse,
    DocumentDeleteResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    """
    Get DocumentService instance with database session
    Used for dependency injection in endpoints
    """
    return DocumentService(db)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_uuid(document_id: str) -> UUID:
    """
    Validate and convert document ID string to UUID

    Args:
        document_id: Document ID string

    Returns:
        UUID object

    Raises:
        HTTPException: 400 if invalid UUID format
    """
    try:
        return UUID(document_id)
    except ValueError:
        logger.warning(f"Invalid UUID format: {document_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )


# ============================================================================
# ENDPOINTS (Order matters! Specific paths before generic paths)
# ============================================================================

# 1. List documents (/) - catch-all for root
@router.get(
    "/",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List documents",
    description="List documents with pagination, filtering, and sorting"
)
async def list_documents(
    # Pagination
    page: int = Query(default=1, ge=1, le=10000, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),

    # Sorting
    sort_by: str = Query(
        default="created_at",
        description="Field to sort by",
        pattern="^(created_at|updated_at|document_name|file_size|status)$"
    ),
    sort_order: str = Query(default="desc", description="Sort order", pattern="^(asc|desc)$"),

    # Filters
    status: Optional[str] = Query(default=None, description="Filter by document status"),
    mime_type: Optional[str] = Query(default=None, max_length=100, description="Filter by MIME type"),
    file_extension: Optional[str] = Query(default=None, pattern=r"^\.[a-z0-9]+$", description="Filter by file extension"),
    tags: Optional[List[str]] = Query(default=None, max_length=10, description="Filter by tags (AND logic)"),
    created_after: Optional[datetime] = Query(default=None, description="Filter documents created after this date"),
    created_before: Optional[datetime] = Query(default=None, description="Filter documents created before this date"),
    min_size: Optional[int] = Query(default=None, ge=0, description="Minimum file size in bytes"),
    max_size: Optional[int] = Query(default=None, le=10*1024*1024*1024, description="Maximum file size in bytes"),
    storage_provider: Optional[str] = Query(default=None, description="Filter by storage provider"),
    include_deleted: bool = Query(default=False, description="Include soft-deleted documents"),

    service: DocumentService = Depends(get_document_service)
):
    """List documents with pagination and filters - see Step 7 spec for details"""
    logger.info(f"GET /documents - page={page}, page_size={page_size}, sort_by={sort_by}, status={status}")

    result = service.list_documents(
        page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order,
        status=status, mime_type=mime_type, file_extension=file_extension, tags=tags,
        created_after=created_after, created_before=created_before,
        min_size=min_size, max_size=max_size, storage_provider=storage_provider,
        include_deleted=include_deleted
    )

    logger.info(f"Listed {len(result['items'])} documents (total={result['total']}, page={page})")
    return result


# 2. Search documents (/search) - specific path, must come before /{document_id}
@router.get(
    "/search",
    response_model=DocumentSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search documents",
    description="Search documents by name or metadata content"
)
async def search_documents(
    q: str = Query(..., max_length=200, description="Search query (minimum 3 characters)"),
    search_fields: Optional[List[str]] = Query(default=["document_name", "metadata"], description="Fields to search in"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    service: DocumentService = Depends(get_document_service)
):
    """Search documents using ILIKE - see Step 7 spec for details"""
    logger.info(f"GET /documents/search - q='{q}', fields={search_fields}")

    result = service.search_documents(
        query=q,
        search_fields=search_fields,
        page=page,
        page_size=page_size,
        status=status
    )

    logger.info(f"Search returned {result['total']} results for query '{q}'")
    return result


# 3. Get statistics (/stats) - specific path, must come before /{document_id}
@router.get(
    "/stats",
    response_model=DocumentStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document statistics",
    description="Get document statistics and analytics"
)
async def get_document_stats(
    date_range: str = Query(
        default="all",
        pattern="^(7d|30d|90d|1y|all)$",
        description="Date range for statistics (7d, 30d, 90d, 1y, all)"
    ),
    service: DocumentService = Depends(get_document_service)
):
    """Get statistics and analytics - see Step 7 spec for details"""
    logger.info(f"GET /documents/stats - date_range={date_range}")

    stats = service.get_document_stats(date_range=date_range)

    logger.info(f"Stats retrieved: {stats['total_documents']} documents, {stats['total_size_gb']} GB")
    return stats


# 4. Get document search quality (/{document_id}/search-quality) - specific path with parameter
@router.get(
    "/{document_id}/search-quality",
    status_code=status.HTTP_200_OK,
    summary="Validate document search quality",
    description="Check if document is ready for search with extraction and chunking quality metrics"
)
async def get_document_search_quality(
    document_id: str = Path(..., description="Document UUID", example="550e8400-e29b-41d4-a716-446655440000"),
    db: Session = Depends(get_db)
):
    """
    Validate document search readiness for Step 8.3

    **Validates:**
    - Text extraction quality (Step 8.1)
    - Chunking quality (Step 8.2)
    - Overall search readiness

    **Checks:**
    - Extraction: text length, quality score, OCR usage
    - Chunking: chunk count, sizes, overlap, index gaps
    - Readiness: combined quality score

    **Example Response:**
    ```json
    {
      "document_id": "550e8400-...",
      "document_name": "sample.pdf",
      "is_search_ready": true,
      "extraction_passed": true,
      "chunking_passed": true,
      "overall_quality_score": 0.88,
      "extraction_details": {
        "text_length": 45230,
        "extraction_quality": 0.92,
        "extraction_method": "docling",
        "pages_with_ocr": 2,
        "total_pages": 10
      },
      "chunking_details": {
        "chunk_count": 47,
        "avg_chunk_size": 982,
        "chunks_in_range": 46,
        "has_proper_overlap": true
      },
      "issues": [],
      "recommendations": ["Quality is good for search"]
    }
    ```

    Args:
        document_id: Document UUID to validate
        db: Database session (injected)

    Returns:
        Search readiness report with quality metrics

    Raises:
        HTTPException 400: Invalid UUID format
        HTTPException 404: Document not found
        HTTPException 500: Validation error
    """
    logger.info(f"GET /documents/{document_id}/search-quality")

    # Validate UUID format
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        logger.warning(f"Invalid UUID format: {document_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )

    # Get quality validator
    from app.services.search import get_quality_validator
    validator = get_quality_validator(db)

    try:
        # Validate search readiness
        result = validator.validate_search_readiness(doc_uuid)

        # Check if document exists
        if result["document_name"] is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document not found: {document_id}"
            )

        logger.info(
            f"Document {document_id} quality check: "
            f"ready={result['is_search_ready']}, quality={result['overall_quality_score']}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating document quality: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate document quality: {str(e)}"
        )


# 5. Get document by ID (/{document_id}) - generic path, must come after specific paths
@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get document by ID",
    description="Retrieve a single document with full metadata by UUID",
    responses={
        200: {"description": "Document found", "model": DocumentResponse},
        400: {"description": "Invalid UUID", "model": ErrorResponse},
        404: {"description": "Not found", "model": ErrorResponse},
        500: {"description": "Server error", "model": ErrorResponse}
    }
)
async def get_document(
    document_id: str = Path(..., description="Document UUID", example="550e8400-e29b-41d4-a716-446655440000"),
    include_processing_status: bool = Query(default=True, description="Include processing status details"),
    include_versions: bool = Query(default=False, description="Include version history (future)"),
    include_embeddings: bool = Query(default=False, description="Include embedding status (future)"),
    service: DocumentService = Depends(get_document_service)
):
    """
    Get document by ID with full metadata

    **Per Step 7 Section 2.2 specification:**
    - Retrieves complete document information
    - **Automatically increments access_count**
    - **Automatically updates last_accessed_at timestamp**
    - Optionally includes processing status

    **Query Parameters:**
    - `include_processing_status`: Include detailed processing stage info (default: true)
    - `include_versions`: Include version history (placeholder, not yet implemented)
    - `include_embeddings`: Include embedding status (placeholder, not yet implemented)

    **Returns:**
    - Full document metadata (all 32 fields from DocumentResponse schema)
    - Processing status by stage (if requested)

    **Errors:**
    - 400: Invalid UUID format
    - 404: Document not found or soft-deleted
    - 500: Database or server error
    """
    logger.info(f"GET /documents/{document_id} - include_processing_status={include_processing_status}")

    # Validate UUID format (raises 400 HTTPException if invalid)
    doc_uuid = validate_uuid(document_id)

    # Get document from service
    # Service automatically increments access_count and updates last_accessed_at
    document_data = service.get_document_by_id(
        document_id=doc_uuid,
        include_processing_status=include_processing_status,
        track_access=True  # This triggers access counter increment
    )

    # Note: include_versions and include_embeddings are in the spec but not implemented in Step 7
    # They are placeholders for future functionality

    logger.info(f"Document {document_id} retrieved successfully")
    return document_data


# 5. Delete document (/{document_id}) - DELETE method, order doesn't matter for different HTTP methods
@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete document",
    description="Soft delete a document",
    responses={
        200: {"description": "Deleted", "model": DocumentDeleteResponse},
        400: {"description": "Invalid UUID", "model": ErrorResponse},
        404: {"description": "Not found", "model": ErrorResponse},
        409: {"description": "Cannot delete while processing", "model": ErrorResponse},
        500: {"description": "Deletion failed", "model": ErrorResponse}
    }
)
async def delete_document(
    document_id: str = Path(..., description="Document UUID to delete", example="550e8400-e29b-41d4-a716-446655440000"),
    hard_delete: bool = Query(default=False, description="Actually delete vs soft delete (not implemented)"),
    delete_files: bool = Query(default=True, description="Delete physical files (queued for async deletion)"),
    service: DocumentService = Depends(get_document_service)
):
    """
    Soft delete a document

    **Features:**
    - Marks document as deleted (is_deleted=TRUE)
    - Sets deleted_at timestamp
    - Prevents deletion of documents being processed (409 error)
    - Queues physical file cleanup (placeholder for future Celery task)

    **Query Parameters:**
    - `hard_delete`: Actually delete from database (not implemented, always soft delete)
    - `delete_files`: Queue physical file deletion (placeholder)

    **Returns:**
    - Deletion confirmation with timestamp

    **Errors:**
    - 400: Invalid UUID format
    - 404: Document not found or already deleted
    - 409: Document is being processed
    - 500: Deletion failed
    """
    logger.info(f"DELETE /documents/{document_id} - delete_files={delete_files}")

    # Validate UUID format
    doc_uuid = validate_uuid(document_id)

    # Call service layer (always soft delete in Step 7)
    result = service.soft_delete_document(
        document_id=doc_uuid,
        deleted_by_user_id=None,  # Future: get from auth context
        delete_files=delete_files
    )

    logger.info(f"Document {document_id} soft deleted successfully")
    return result
