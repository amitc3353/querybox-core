"""
Document Service - Business logic for document operations
Step 7: Document Query Endpoints
Implements: get_by_id, list, search, stats, soft_delete
"""
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc, asc, cast, String
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from fastapi import status as http_status
import logging
import time

from app.models.document import (
    Document,
    DocumentStatusEnum,
    StorageProviderEnum,
    ProcessingStageEnum,
    StageStatusEnum
)
from app.models.processing_status import ProcessingStatus

logger = logging.getLogger(__name__)


# ============================================================================
# REPOSITORY PATTERN - Data Access Layer
# ============================================================================

class DocumentRepository:
    """
    Data access layer for documents
    Handles all direct database operations
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        document_id: UUID,
        include_deleted: bool = False
    ) -> Optional[Document]:
        """
        Get document by ID

        Args:
            document_id: Document UUID
            include_deleted: Whether to include soft-deleted documents

        Returns:
            Document or None if not found
        """
        query = self.db.query(Document).filter(Document.id == document_id)

        if not include_deleted:
            query = query.filter(Document.is_deleted == False)

        return query.first()

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        status: Optional[DocumentStatusEnum] = None,
        mime_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        storage_provider: Optional[StorageProviderEnum] = None,
        include_deleted: bool = False
    ) -> Tuple[List[Document], int]:
        """
        List documents with filtering, sorting, and pagination

        Returns:
            Tuple of (documents, total_count)
        """
        # Base query - exclude deleted by default
        query = self.db.query(Document)

        if not include_deleted:
            query = query.filter(Document.is_deleted == False)

        # Apply filters
        if status is not None:
            query = query.filter(Document.status == status)

        if mime_type is not None:
            query = query.filter(Document.mime_type == mime_type)

        if file_extension is not None:
            query = query.filter(Document.file_extension == file_extension)

        if storage_provider is not None:
            query = query.filter(Document.storage_provider == storage_provider)

        if tags is not None and len(tags) > 0:
            # AND logic: document must have ALL specified tags
            # For PostgreSQL: use contains operator
            # For SQLite: convert tags to text and use LIKE
            for tag in tags:
                if self.db.bind.dialect.name == 'postgresql':
                    query = query.filter(Document.tags.contains([tag]))
                else:
                    # SQLite: tags stored as JSON string, search within it
                    query = query.filter(cast(Document.tags, String).like(f'%"{tag}"%'))

        if created_after is not None:
            query = query.filter(Document.created_at >= created_after)

        if created_before is not None:
            query = query.filter(Document.created_at <= created_before)

        if min_size is not None:
            query = query.filter(Document.file_size >= min_size)

        if max_size is not None:
            query = query.filter(Document.file_size <= max_size)

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(Document, sort_by, Document.created_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        documents = query.all()

        return documents, total_count

    def search(
        self,
        search_query: str,
        search_fields: List[str],
        page: int = 1,
        page_size: int = 20,
        status: Optional[DocumentStatusEnum] = None
    ) -> Tuple[List[Document], int]:
        """
        Search documents by name or metadata content

        Args:
            search_query: Search string
            search_fields: Fields to search in (document_name, original_name, metadata, tags)
            page: Page number
            page_size: Items per page
            status: Optional status filter

        Returns:
            Tuple of (documents, total_count)
        """
        # Build search pattern for ILIKE
        # Escape special characters for LIKE queries
        escaped_query = search_query.replace("%", "\\%").replace("_", "\\_")
        search_pattern = f"%{escaped_query}%"

        # Base query
        query = self.db.query(Document).filter(Document.is_deleted == False)

        # Apply status filter if provided
        if status is not None:
            query = query.filter(Document.status == status)

        # Build search conditions based on search_fields
        search_conditions = []

        if "document_name" in search_fields:
            search_conditions.append(Document.document_name.ilike(search_pattern))

        if "original_name" in search_fields:
            search_conditions.append(Document.original_name.ilike(search_pattern))

        if "metadata" in search_fields:
            # Search in JSONB metadata (convert to text for ILIKE)
            search_conditions.append(
                cast(Document.document_metadata, String).ilike(search_pattern)
            )

        if "tags" in search_fields and Document.tags is not None:
            # Search in tags array (convert to text for ILIKE)
            search_conditions.append(
                cast(Document.tags, String).ilike(search_pattern)
            )

        # Apply OR logic for search conditions
        if search_conditions:
            query = query.filter(or_(*search_conditions))

        # Get total count
        total_count = query.count()

        # Order by updated_at (most recently updated first)
        query = query.order_by(desc(Document.updated_at))

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        documents = query.all()

        return documents, total_count

    def get_statistics(
        self,
        date_range_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get document statistics and aggregations

        Args:
            date_range_days: Limit to documents created in last N days (None = all time)

        Returns:
            Dictionary with statistics
        """
        # Base query for non-deleted documents
        base_query = self.db.query(Document).filter(Document.is_deleted == False)

        # Apply date range filter if specified
        if date_range_days is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=date_range_days)
            base_query = base_query.filter(Document.created_at >= cutoff_date)

        # Total count and size
        total_stats = base_query.with_entities(
            func.count(Document.id).label("total_documents"),
            func.sum(Document.file_size).label("total_size")
        ).first()

        total_documents = total_stats.total_documents or 0
        total_size_bytes = total_stats.total_size or 0

        # By status
        by_status = {}
        status_counts = base_query.with_entities(
            Document.status,
            func.count(Document.id).label("count")
        ).group_by(Document.status).all()

        for status, count in status_counts:
            by_status[status.value] = count

        # By MIME type (top 10)
        by_mime_type = {}
        mime_counts = base_query.with_entities(
            Document.mime_type,
            func.count(Document.id).label("count")
        ).group_by(Document.mime_type).order_by(desc("count")).limit(10).all()

        for mime_type, count in mime_counts:
            by_mime_type[mime_type] = count

        # Upload trend (last 30 days)
        upload_trend = []
        if date_range_days is None or date_range_days >= 30:
            trend_cutoff = datetime.utcnow() - timedelta(days=30)
            trend_data = self.db.query(
                func.date(Document.created_at).label("date"),
                func.count(Document.id).label("count")
            ).filter(
                Document.is_deleted == False,
                Document.created_at >= trend_cutoff
            ).group_by(
                func.date(Document.created_at)
            ).order_by("date").all()

            upload_trend = [
                {"date": str(date), "count": count}
                for date, count in trend_data
            ]

        # Average file size
        avg_file_size_mb = 0.0
        if total_documents > 0:
            avg_file_size_mb = (total_size_bytes / total_documents) / (1024 * 1024)

        # Most used tags
        most_used_tags = []

        # PostgreSQL: use unnest() for array unnesting
        # SQLite: manually parse JSON arrays
        if self.db.bind.dialect.name == 'postgresql':
            # PostgreSQL-specific array aggregation
            tag_query = self.db.query(
                func.unnest(Document.tags).label("tag"),
            ).filter(
                Document.is_deleted == False,
                Document.tags.isnot(None)
            ).subquery()

            tag_counts = self.db.query(
                tag_query.c.tag,
                func.count(tag_query.c.tag).label("count")
            ).group_by(tag_query.c.tag).order_by(desc("count")).limit(10).all()

            most_used_tags = [
                {"tag": tag, "count": count}
                for tag, count in tag_counts
            ]
        else:
            # SQLite: fetch all tags and count manually
            import json
            from collections import Counter

            documents_with_tags = base_query.filter(Document.tags.isnot(None)).all()
            tag_counter = Counter()

            for doc in documents_with_tags:
                if doc.tags:
                    # tags are already deserialized by StringArray type
                    for tag in doc.tags:
                        tag_counter[tag] += 1

            # Get top 10 most common tags
            most_used_tags = [
                {"tag": tag, "count": count}
                for tag, count in tag_counter.most_common(10)
            ]

        # By storage provider
        by_storage_provider = {}
        provider_counts = base_query.with_entities(
            Document.storage_provider,
            func.count(Document.id).label("count")
        ).group_by(Document.storage_provider).all()

        for provider, count in provider_counts:
            by_storage_provider[provider.value] = count

        return {
            "total_documents": total_documents,
            "total_size_bytes": total_size_bytes,
            "total_size_gb": round(total_size_bytes / (1024**3), 2),
            "by_status": by_status,
            "by_mime_type": by_mime_type,
            "by_storage_provider": by_storage_provider,
            "upload_trend": upload_trend,
            "avg_file_size_mb": round(avg_file_size_mb, 2),
            "most_used_tags": most_used_tags
        }

    def increment_access_count(self, document_id: UUID) -> None:
        """
        Increment access counter for a document

        Args:
            document_id: Document UUID
        """
        self.db.query(Document).filter(
            Document.id == document_id
        ).update({
            "access_count": Document.access_count + 1,
            "last_accessed_at": datetime.utcnow()
        })
        self.db.commit()

    def soft_delete(
        self,
        document_id: UUID,
        deleted_by_user_id: Optional[UUID] = None
    ) -> bool:
        """
        Soft delete a document

        Args:
            document_id: Document UUID
            deleted_by_user_id: User who deleted the document (if auth enabled)

        Returns:
            True if deleted, False if document not found
        """
        document = self.get_by_id(document_id, include_deleted=False)

        if not document:
            return False

        document.is_deleted = True
        document.deleted_at = datetime.utcnow()
        if deleted_by_user_id:
            document.deleted_by_user_id = deleted_by_user_id

        self.db.commit()
        return True

    def get_processing_status(self, document_id: UUID) -> List[ProcessingStatus]:
        """
        Get processing status records for a document

        Args:
            document_id: Document UUID

        Returns:
            List of ProcessingStatus records
        """
        return self.db.query(ProcessingStatus).filter(
            ProcessingStatus.document_id == document_id
        ).order_by(ProcessingStatus.stage).all()


# ============================================================================
# SERVICE LAYER - Business Logic
# ============================================================================

class DocumentService:
    """
    Business logic for document operations
    Uses DocumentRepository for data access
    """

    # Allowed sort fields
    ALLOWED_SORT_FIELDS = [
        "created_at", "updated_at", "document_name",
        "file_size", "status"
    ]

    # Default pagination
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # Search constraints
    MIN_SEARCH_QUERY_LENGTH = 3
    MAX_SEARCH_QUERY_LENGTH = 200

    def __init__(self, db: Session):
        self.db = db
        self.repository = DocumentRepository(db)

    def get_document_by_id(
        self,
        document_id: UUID,
        include_processing_status: bool = True,
        track_access: bool = True
    ) -> Dict[str, Any]:
        """
        Get document by ID with full metadata

        Args:
            document_id: Document UUID
            include_processing_status: Include processing details
            track_access: Increment access counter

        Returns:
            Document data dictionary

        Raises:
            HTTPException: 404 if document not found
        """
        start_time = time.time()

        logger.info(f"Getting document: {document_id}")

        try:
            # Get document from repository
            document = self.repository.get_by_id(document_id)

            if not document:
                logger.warning(f"Document {document_id} not found")
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )

            # Track access if requested
            if track_access:
                try:
                    self.repository.increment_access_count(document_id)
                    logger.debug(f"Access count incremented for document {document_id}")
                except Exception as e:
                    # Don't fail the request if access tracking fails
                    logger.error(f"Failed to increment access count: {e}")

            # Build response
            response_data = self._document_to_dict(document)

            # Add processing status if requested
            if include_processing_status:
                processing_status = self._get_processing_status_dict(document_id)
                response_data["processing_status"] = processing_status

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Document {document_id} retrieved in {elapsed_ms:.2f}ms"
            )

            return response_data

        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error getting document {document_id}: {e}")
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve document"
            )
        except Exception as e:
            logger.error(f"Unexpected error getting document {document_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    def list_documents(
        self,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        status: Optional[str] = None,
        mime_type: Optional[str] = None,
        file_extension: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        storage_provider: Optional[str] = None,
        include_deleted: bool = False
    ) -> Dict[str, Any]:
        """
        List documents with pagination, filtering, and sorting

        Returns:
            Dictionary with items, pagination metadata

        Raises:
            HTTPException: 400 for invalid parameters
        """
        start_time = time.time()

        # Validate pagination
        if page < 1:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="page must be >= 1"
            )

        if page_size < 1 or page_size > self.MAX_PAGE_SIZE:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"page_size must be between 1 and {self.MAX_PAGE_SIZE}"
            )

        # Validate sort field
        if sort_by not in self.ALLOWED_SORT_FIELDS:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_by field. Allowed: {self.ALLOWED_SORT_FIELDS}"
            )

        # Validate sort order
        if sort_order.lower() not in ["asc", "desc"]:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="sort_order must be 'asc' or 'desc'"
            )

        # Validate date range
        if created_after and created_before and created_before < created_after:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="created_before must be after created_after"
            )

        # Validate size range
        if min_size and max_size and max_size < min_size:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="max_size must be >= min_size"
            )

        # Convert status string to enum
        status_enum = None
        if status:
            try:
                status_enum = DocumentStatusEnum(status)
            except ValueError:
                valid_statuses = [s.value for s in DocumentStatusEnum]
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Allowed: {valid_statuses}"
                )

        # Convert storage_provider string to enum
        storage_provider_enum = None
        if storage_provider:
            try:
                storage_provider_enum = StorageProviderEnum(storage_provider)
            except ValueError:
                valid_providers = [p.value for p in StorageProviderEnum]
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid storage_provider. Allowed: {valid_providers}"
                )

        logger.info(
            f"Listing documents: page={page}, page_size={page_size}, "
            f"sort_by={sort_by}, status={status}, mime_type={mime_type}"
        )

        try:
            # Get documents from repository
            documents, total_count = self.repository.list(
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order,
                status=status_enum,
                mime_type=mime_type,
                file_extension=file_extension,
                tags=tags,
                created_after=created_after,
                created_before=created_before,
                min_size=min_size,
                max_size=max_size,
                storage_provider=storage_provider_enum,
                include_deleted=include_deleted
            )

            # Convert documents to dictionaries
            items = [self._document_to_dict(doc) for doc in documents]

            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
            has_next = page < total_pages
            has_previous = page > 1

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Listed {len(items)} documents (total={total_count}) "
                f"in {elapsed_ms:.2f}ms"
            )

            # Performance warning
            if elapsed_ms > 1000:
                logger.warning(f"Slow query detected: {elapsed_ms:.2f}ms")

            return {
                "items": items,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous
            }

        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error listing documents: {e}")
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve documents"
            )
        except Exception as e:
            logger.error(f"Unexpected error listing documents: {e}", exc_info=True)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    def search_documents(
        self,
        query: str,
        search_fields: List[str] = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search documents by name or metadata content

        Args:
            query: Search query string
            search_fields: Fields to search (default: document_name, metadata)
            page: Page number
            page_size: Items per page
            status: Optional status filter

        Returns:
            Search results with pagination

        Raises:
            HTTPException: 400 for invalid query
        """
        start_time = time.time()

        # Validate query length
        if len(query) < self.MIN_SEARCH_QUERY_LENGTH:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Search query must be at least {self.MIN_SEARCH_QUERY_LENGTH} characters"
            )

        if len(query) > self.MAX_SEARCH_QUERY_LENGTH:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Search query must be at most {self.MAX_SEARCH_QUERY_LENGTH} characters"
            )

        # Default search fields
        if search_fields is None:
            search_fields = ["document_name", "metadata"]

        # Validate search fields
        allowed_search_fields = ["document_name", "original_name", "metadata", "tags"]
        for field in search_fields:
            if field not in allowed_search_fields:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid search field '{field}'. Allowed: {allowed_search_fields}"
                )

        # Validate pagination
        if page < 1 or page_size < 1 or page_size > self.MAX_PAGE_SIZE:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid pagination: page must be >= 1, page_size between 1 and {self.MAX_PAGE_SIZE}"
            )

        # Convert status string to enum
        status_enum = None
        if status:
            try:
                status_enum = DocumentStatusEnum(status)
            except ValueError:
                valid_statuses = [s.value for s in DocumentStatusEnum]
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status. Allowed: {valid_statuses}"
                )

        logger.info(f"Searching documents: query='{query}', fields={search_fields}")

        try:
            # Search via repository
            documents, total_count = self.repository.search(
                search_query=query,
                search_fields=search_fields,
                page=page,
                page_size=page_size,
                status=status_enum
            )

            # Convert to dictionaries
            items = [self._document_to_dict(doc) for doc in documents]

            # Calculate pagination
            total_pages = (total_count + page_size - 1) // page_size

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Search query '{query}' returned {total_count} results "
                f"in {elapsed_ms:.2f}ms"
            )

            # Warning if no results
            if total_count == 0:
                logger.warning(f"Search query returned 0 results: '{query}'")

            return {
                "query": query,
                "items": items,
                "total": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error searching documents: {e}")
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Search failed"
            )
        except Exception as e:
            logger.error(f"Unexpected error searching documents: {e}", exc_info=True)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    def get_document_stats(
        self,
        date_range: str = "all"
    ) -> Dict[str, Any]:
        """
        Get document statistics and analytics

        Args:
            date_range: Date range for stats (7d, 30d, 90d, 1y, all)

        Returns:
            Statistics dictionary
        """
        start_time = time.time()

        # Map date range to days
        date_range_map = {
            "7d": 7,
            "30d": 30,
            "90d": 90,
            "1y": 365,
            "all": None
        }

        if date_range not in date_range_map:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date_range. Allowed: {list(date_range_map.keys())}"
            )

        days = date_range_map[date_range]

        logger.info(f"Getting document statistics for date_range={date_range}")

        try:
            stats = self.repository.get_statistics(date_range_days=days)

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"Statistics retrieved in {elapsed_ms:.2f}ms: "
                f"{stats['total_documents']} documents, "
                f"{stats['total_size_gb']} GB"
            )

            return stats

        except SQLAlchemyError as e:
            logger.error(f"Database error getting statistics: {e}")
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve statistics"
            )
        except Exception as e:
            logger.error(f"Unexpected error getting statistics: {e}", exc_info=True)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    def soft_delete_document(
        self,
        document_id: UUID,
        deleted_by_user_id: Optional[UUID] = None,
        delete_files: bool = True
    ) -> Dict[str, Any]:
        """
        Soft delete a document

        Args:
            document_id: Document UUID
            deleted_by_user_id: User who deleted (if auth enabled)
            delete_files: Whether to delete physical files (future: queue cleanup)

        Returns:
            Deletion confirmation

        Raises:
            HTTPException: 404 if not found, 409 if processing
        """
        logger.info(f"Soft deleting document: {document_id}")

        try:
            # Get document first to check status
            document = self.repository.get_by_id(document_id)

            if not document:
                logger.warning(f"Cannot delete - document {document_id} not found")
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )

            # Check if document is being processed
            if document.status == DocumentStatusEnum.PROCESSING:
                logger.warning(
                    f"Cannot delete - document {document_id} is being processed"
                )
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail="Cannot delete document while processing"
                )

            # Perform soft delete
            success = self.repository.soft_delete(
                document_id=document_id,
                deleted_by_user_id=deleted_by_user_id
            )

            if not success:
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete document"
                )

            logger.info(
                f"Document {document_id} soft deleted successfully "
                f"by user {deleted_by_user_id}"
            )

            # TODO: Queue async file cleanup task if delete_files=True
            # cleanup_document_files.delay(str(document_id))

            return {
                "success": True,
                "document_id": str(document_id),
                "deleted_at": datetime.utcnow().isoformat(),
                "hard_delete": False,
                "files_deleted": False  # Will be True when cleanup task implemented
            }

        except HTTPException:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error deleting document {document_id}: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Deletion failed"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error deleting document {document_id}: {e}",
                exc_info=True
            )
            self.db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _document_to_dict(self, document: Document) -> Dict[str, Any]:
        """
        Convert Document model to dictionary for API response

        Args:
            document: Document model instance

        Returns:
            Dictionary with document data
        """
        return {
            "id": str(document.id),
            "document_name": document.document_name,
            "original_name": document.original_name,
            "alternate_name": document.alternate_name,
            "mime_type": document.mime_type,
            "file_extension": document.file_extension,
            "file_size": document.file_size,
            "file_size_mb": round(document.file_size / (1024 * 1024), 2),
            "checksum": document.checksum,
            "storage_provider": document.storage_provider.value,
            "storage_path": document.storage_path,
            "storage_bucket": document.storage_bucket,
            "storage_region": document.storage_region,
            "status": document.status.value,
            "is_versioned_file": document.is_versioned_file,
            "current_version": document.current_version,
            "mutation_count": document.mutation_count,
            "document_metadata": document.document_metadata or {},
            "tags": document.tags or [],
            "last_extraction_at": document.last_extraction_at.isoformat() if document.last_extraction_at else None,
            "last_embedding_at": document.last_embedding_at.isoformat() if document.last_embedding_at else None,
            "last_indexed_at": document.last_indexed_at.isoformat() if document.last_indexed_at else None,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "is_deleted": document.is_deleted,
            "is_dirty": document.is_dirty,
            "processing_reason": document.processing_reason
        }

    def _get_processing_status_dict(self, document_id: UUID) -> Dict[str, Any]:
        """
        Get processing status information for a document

        Args:
            document_id: Document UUID

        Returns:
            Dictionary with processing status by stage
        """
        try:
            statuses = self.repository.get_processing_status(document_id)

            # Build status dict by stage
            status_dict = {}
            for ps in statuses:
                stage_name = ps.stage.value
                status_dict[stage_name] = {
                    "status": ps.status.value,
                    "started_at": ps.started_at.isoformat() if ps.started_at else None,
                    "completed_at": ps.completed_at.isoformat() if ps.completed_at else None,
                    "progress": ps.progress_percentage,
                    "error_message": ps.error_message
                }

            return status_dict

        except Exception as e:
            logger.error(f"Error getting processing status: {e}")
            return {}


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_document_service(db: Session) -> DocumentService:
    """
    Dependency injection for DocumentService
    Use this in FastAPI endpoints with Depends()

    Example:
        @router.get("/documents/{document_id}")
        async def get_document(
            document_id: UUID,
            service: DocumentService = Depends(get_document_service)
        ):
            return service.get_document_by_id(document_id)
    """
    return DocumentService(db)
