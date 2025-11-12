"""
Vector Search Service for Step 9.3 - Semantic Vector Similarity Search

PostgreSQL pgvector-based semantic search implementation for document chunks.
"""
import time
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, text, literal
import structlog

from app.models.document import Document
from app.models.document_text import DocumentText
from app.models.embedding import Embedding
from app.services.embeddings.embedding_service import EmbeddingService
from app.schemas.search import (
    SearchFilters,
    SearchResultItem,
    SearchResponse
)

logger = structlog.get_logger()


class VectorSearchService:
    """
    Semantic vector similarity search using pgvector and BGE-M3 embeddings

    Features:
    - Natural language query understanding
    - Cosine similarity search with pgvector
    - Multi-lingual support (100+ languages via BGE-M3)
    - Fast retrieval with HNSW/IVFFlat indexes
    - Metadata filtering (type, quality, dates)
    """

    def __init__(self, db: Session, embedding_service: EmbeddingService):
        """
        Initialize vector search service

        Args:
            db: Database session
            embedding_service: Service for generating query embeddings
        """
        self.db = db
        self.embedding_service = embedding_service
        self._is_sqlite = self._detect_database_type()

    def _detect_database_type(self) -> bool:
        """
        Detect if database is SQLite (for test compatibility)

        Returns:
            True if SQLite, False otherwise (PostgreSQL)
        """
        try:
            dialect_name = self.db.bind.dialect.name
            return dialect_name == 'sqlite'
        except Exception:
            return False

    def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 10,
        offset: int = 0,
        similarity_threshold: float = 0.0
    ) -> SearchResponse:
        """
        Execute semantic vector similarity search

        Args:
            query: Natural language search query
            filters: Optional filters (document_types, quality, dates)
            limit: Maximum results to return (1-100)
            offset: Pagination offset
            similarity_threshold: Minimum cosine similarity (0.0-1.0)

        Returns:
            SearchResponse with semantically ranked results

        Raises:
            ValueError: If query is invalid
            RuntimeError: If embedding generation or search fails
        """
        start_time = time.time()

        # Validate query
        query = self._sanitize_query(query)

        # Log search request
        logger.info(
            "vector_search_request",
            query=query[:100],
            query_length=len(query),
            has_filters=filters is not None,
            limit=limit,
            offset=offset,
            similarity_threshold=similarity_threshold
        )

        # Generate query embedding
        embedding_start = time.time()
        try:
            query_vector = self._generate_query_embedding(query)
        except Exception as e:
            logger.error(
                "query_embedding_failed",
                query=query[:100],
                error=str(e),
                exc_info=True
            )
            raise RuntimeError(f"Failed to generate query embedding: {e}")
        embedding_time_ms = int((time.time() - embedding_start) * 1000)

        # Get total count of matching chunks (for pagination)
        search_start = time.time()
        total_count = self._count_matching_chunks(
            query_vector, filters, similarity_threshold
        )

        # Search chunks using pgvector cosine similarity
        chunk_results = self._vector_search_chunks(
            query_vector, filters, limit, offset, similarity_threshold
        )

        search_time_ms = int((time.time() - search_start) * 1000)

        # Convert to SearchResultItem objects
        result_items = self._convert_to_result_items(chunk_results)

        # Calculate total processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log search results
        logger.info(
            "vector_search_completed",
            query=query[:100],
            total_results=total_count,
            returned_results=len(result_items),
            processing_time_ms=processing_time_ms,
            embedding_time_ms=embedding_time_ms,
            search_time_ms=search_time_ms,
            avg_similarity=round(sum(r.relevance_score for r in result_items) / len(result_items), 3) if result_items else 0.0
        )

        # Build response
        return SearchResponse(
            success=True,
            query=query,
            total_results=total_count,
            returned_results=len(result_items),
            results=result_items,
            processing_time_ms=processing_time_ms,
            filters_applied=filters
        )

    def _sanitize_query(self, query: str) -> str:
        """
        Sanitize and validate query string

        Args:
            query: Raw user query string

        Returns:
            Sanitized query string

        Raises:
            ValueError: If query is empty or invalid
        """
        # Remove null bytes
        query = query.replace('\x00', '')

        # Remove control characters except newlines/tabs
        query = ''.join(char for char in query if ord(char) >= 32 or char in '\n\t')

        # Strip whitespace
        query = query.strip()

        # Validate not empty
        if not query:
            raise ValueError("Query cannot be empty")

        # Limit length (BGE-M3 max: 8192 tokens ≈ 50,000 chars)
        MAX_QUERY_LENGTH = 1000  # Reasonable limit for queries
        if len(query) > MAX_QUERY_LENGTH:
            logger.warning(
                "query_truncated",
                original_length=len(query),
                max_length=MAX_QUERY_LENGTH
            )
            query = query[:MAX_QUERY_LENGTH]

        return query

    def _generate_query_embedding(self, query: str) -> List[float]:
        """
        Convert query text to embedding vector using BGE-M3

        Args:
            query: Query text

        Returns:
            1024-dimensional normalized vector

        Raises:
            RuntimeError: If embedding generation fails
        """
        logger.debug("generating_query_embedding", query_length=len(query))

        # Use embedding service to generate vector
        vector = self.embedding_service.generate_embedding(query)

        logger.debug(
            "query_embedding_generated",
            dimension=len(vector)
        )

        return vector

    def _count_matching_chunks(
        self,
        query_vector: List[float],
        filters: Optional[SearchFilters],
        similarity_threshold: float
    ) -> int:
        """
        Count total matching chunks for pagination

        Args:
            query_vector: Query embedding vector
            filters: Optional search filters
            similarity_threshold: Minimum similarity score

        Returns:
            Total count of matching chunks
        """
        # Build count query with proper joins
        # Use LEFT JOIN for DocumentText to include embeddings even when DocumentText is missing
        query = self.db.query(func.count(Embedding.id)).join(
            Document, Embedding.document_id == Document.id
        ).outerjoin(
            DocumentText, Embedding.document_id == DocumentText.document_id
        ).filter(
            # Only chunks with embeddings
            Embedding.embedding.isnot(None),
            # Only completed documents
            Document.status == 'completed',
            # Not deleted
            Document.is_deleted == False
        )

        # Apply similarity threshold if specified (PostgreSQL only, requires pgvector)
        if not self._is_sqlite and similarity_threshold is not None and similarity_threshold > 0.0:
            # 1 - cosine_distance = similarity score
            similarity_expr = 1 - Embedding.embedding.cosine_distance(query_vector)
            query = query.filter(similarity_expr > similarity_threshold)

        # Apply metadata filters
        query = self._apply_filters(query, filters)

        return query.scalar() or 0

    def _vector_search_chunks(
        self,
        query_vector: List[float],
        filters: Optional[SearchFilters],
        limit: int,
        offset: int,
        similarity_threshold: float
    ) -> List[Dict]:
        """
        Execute cosine similarity search using pgvector

        Uses pgvector operators:
        - cosine_distance (<=>): Returns distance (0 = identical, 2 = opposite)
        - Similarity score: 1 - cosine_distance (0.0-1.0, higher = more similar)

        Args:
            query_vector: Query embedding vector
            filters: Optional search filters
            limit: Maximum results
            offset: Pagination offset
            similarity_threshold: Minimum similarity score

        Returns:
            List of chunk matches with similarity scores
        """
        if self._is_sqlite:
            # SQLite fallback: Return results without similarity calculation
            # For testing purposes, we just return results ordered by chunk_index
            # NOTE: This is NOT a real semantic search, just a fallback for tests
            query = self.db.query(
                Embedding.id,
                Embedding.document_id,
                Embedding.chunk_text,
                Embedding.chunk_index,
                Embedding.section_heading,
                Embedding.chunk_type,
                Embedding.start_position,
                Embedding.end_position,
                Embedding.embedding,
                Document.document_name,
                Document.mime_type,
                Document.created_at,
                DocumentText.extraction_quality,
                literal(0.5).label('similarity_score')  # Dummy similarity score for SQLite
            ).join(
                Document, Embedding.document_id == Document.id
            ).outerjoin(
                DocumentText, Embedding.document_id == DocumentText.document_id
            ).filter(
                # Only chunks with embeddings
                Embedding.embedding.isnot(None),
                # Only completed documents
                Document.status == 'completed',
                # Not deleted
                Document.is_deleted == False
            )

            # Apply metadata filters
            query = self._apply_filters(query, filters)

            # Order by chunk_index (no real similarity for SQLite)
            query = query.order_by(Embedding.chunk_index).limit(limit).offset(offset)
        else:
            # PostgreSQL: Use pgvector for cosine similarity
            # Calculate similarity score: 1 - cosine_distance
            similarity_expr = (1 - Embedding.embedding.cosine_distance(query_vector)).label('similarity_score')

            # Build base query
            # Use LEFT JOIN for DocumentText to include embeddings even when DocumentText is missing
            query = self.db.query(
                Embedding.id,
                Embedding.document_id,
                Embedding.chunk_text,
                Embedding.chunk_index,
                Embedding.section_heading,
                Embedding.chunk_type,
                Embedding.start_position,
                Embedding.end_position,
                Embedding.embedding,  # Include embedding for MMR and semantic dedup
                Document.document_name,
                Document.mime_type,
                Document.created_at,
                DocumentText.extraction_quality,
                similarity_expr
            ).join(
                Document, Embedding.document_id == Document.id
            ).outerjoin(
                DocumentText, Embedding.document_id == DocumentText.document_id
            ).filter(
                # Only chunks with embeddings
                Embedding.embedding.isnot(None),
                # Only completed documents
                Document.status == 'completed',
                # Not deleted
                Document.is_deleted == False
            )

            # Apply similarity threshold
            if similarity_threshold is not None and similarity_threshold > 0.0:
                query = query.filter(similarity_expr > similarity_threshold)

            # Apply metadata filters
            query = self._apply_filters(query, filters)

            # Order by cosine distance (lower distance = higher similarity)
            # Using cosine_distance for ordering is more efficient with indexes
            query = query.order_by(
                Embedding.embedding.cosine_distance(query_vector)
            ).limit(limit).offset(offset)

        # Execute query
        results = query.all()

        # Convert to dict
        chunk_results = []
        for row in results:
            # Convert pgvector embedding to list of floats
            embedding_list = None
            if row.embedding is not None:
                try:
                    # pgvector returns the embedding as a list already
                    embedding_list = list(row.embedding) if hasattr(row.embedding, '__iter__') else None
                except Exception as e:
                    logger.debug(
                        "embedding_conversion_failed",
                        chunk_id=str(row.id),
                        error=str(e)
                    )

            chunk_results.append({
                'chunk_id': str(row.id),
                'document_id': str(row.document_id),
                'document_name': row.document_name,
                'document_type': row.mime_type,
                'chunk_text': row.chunk_text,
                'chunk_index': row.chunk_index,
                'section_heading': row.section_heading,
                'chunk_type': row.chunk_type,
                'relevance_score': float(row.similarity_score),
                'similarity_score': float(row.similarity_score),
                'snippet': self._generate_snippet(row.chunk_text),
                'extraction_quality': row.extraction_quality,
                'created_at': row.created_at,
                'chunk_position': {
                    'start': row.start_position,
                    'end': row.end_position
                } if row.start_position is not None else None,
                'embedding': embedding_list  # For MMR and semantic dedup
            })

        return chunk_results

    def _apply_filters(self, query, filters: Optional[SearchFilters]):
        """
        Apply search filters to query

        Args:
            query: SQLAlchemy query object
            filters: Optional search filters

        Returns:
            Modified query with filters applied
        """
        if not filters:
            return query

        # Filter by document types (MIME types)
        if filters.document_types:
            query = query.filter(Document.mime_type.in_(filters.document_types))

        # Filter by extraction quality
        if filters.min_quality is not None:
            query = query.filter(DocumentText.extraction_quality >= filters.min_quality)

        # Filter by date range
        if filters.date_from:
            query = query.filter(Document.created_at >= filters.date_from)

        if filters.date_to:
            query = query.filter(Document.created_at <= filters.date_to)

        # Filter by tags
        if filters.tags:
            # PostgreSQL array overlap operator
            query = query.filter(Document.tags.overlap(filters.tags))

        return query

    def _generate_snippet(self, chunk_text: str, max_length: int = 300) -> str:
        """
        Generate text snippet from chunk

        Args:
            chunk_text: Full chunk text
            max_length: Maximum snippet length

        Returns:
            Formatted snippet
        """
        if not chunk_text:
            return ""

        # Normalize whitespace
        import re
        snippet = re.sub(r'\s+', ' ', chunk_text)

        # Truncate if needed
        if len(snippet) > max_length:
            snippet = snippet[:max_length] + '...'
        else:
            # Add ellipsis for context
            snippet = '...' + snippet + '...'

        return snippet.strip()

    def _convert_to_result_items(self, results: List[Dict]) -> List[SearchResultItem]:
        """
        Convert internal result dicts to SearchResultItem schema objects

        Args:
            results: List of result dictionaries

        Returns:
            List of SearchResultItem objects
        """
        result_items = []
        for result in results:
            result_items.append(
                SearchResultItem(
                    chunk_id=result.get('chunk_id'),
                    document_id=result['document_id'],
                    document_name=result['document_name'],
                    relevance_score=result['relevance_score'],
                    snippet=result['snippet'],
                    chunk_index=result['chunk_index'],
                    chunk_position=result['chunk_position'],
                    extraction_quality=result['extraction_quality'],
                    document_type=result['document_type'],
                    created_at=result['created_at'],
                    embedding=result.get('embedding')  # For MMR and semantic dedup
                )
            )
        return result_items


def get_vector_search_service(
    db: Session,
    embedding_service: EmbeddingService
) -> VectorSearchService:
    """
    Factory function to create VectorSearchService instance

    Args:
        db: Database session
        embedding_service: Embedding service for query vectorization

    Returns:
        VectorSearchService instance
    """
    return VectorSearchService(db=db, embedding_service=embedding_service)
