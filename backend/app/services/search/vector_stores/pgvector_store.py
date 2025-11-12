"""
PostgreSQL + pgvector store implementation.

Wraps the existing pgvector search logic in the VectorStore interface.
"""

import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.search.vector_stores.base import VectorStore, SearchResult
from app.models.document import Document
from app.models.document_text import DocumentText
from app.models.embedding import Embedding

logger = logging.getLogger(__name__)


class PgVectorStore(VectorStore):
    """
    PostgreSQL + pgvector vector store implementation.

    Features:
    - Cosine similarity search with pgvector extension
    - HNSW index support for fast approximate search
    - Metadata filtering (document types, quality, dates)
    - Handles embeddings table with PostgreSQL ORM
    """

    def __init__(self, db: Session, dimension: int = 1024):
        """
        Initialize pgvector store.

        Args:
            db: SQLAlchemy database session
            dimension: Embedding vector dimension (default: 1024 for BGE-M3)
        """
        super().__init__(name="pgvector", dimension=dimension)
        self.db = db

    def index(
        self,
        vectors: List[np.ndarray],
        metadata: List[Dict[str, Any]],
        ids: List[str],
        **kwargs
    ) -> None:
        """
        Index (upsert) vectors into PostgreSQL embeddings table.

        Args:
            vectors: List of embedding vectors
            metadata: List of metadata dicts (must include document_id, chunk_text, etc.)
            ids: List of embedding IDs (chunk IDs)
            **kwargs: Optional parameters (currently unused)

        Raises:
            ValueError: If validation fails
        """
        # Validate inputs
        self.validate_vectors(vectors, metadata, ids)

        try:
            # For each vector, update or insert embedding
            for i, (vector, meta, embedding_id) in enumerate(zip(vectors, metadata, ids)):
                # Check if embedding exists
                existing = self.db.query(Embedding).filter(
                    Embedding.id == embedding_id
                ).first()

                if existing:
                    # Update existing embedding
                    existing.embedding = vector.tolist()
                    logger.debug(f"Updated embedding {embedding_id}")
                else:
                    # Create new embedding
                    # Note: This requires all necessary fields in metadata
                    embedding = Embedding(
                        id=embedding_id,
                        document_id=meta.get("document_id"),
                        chunk_text=meta.get("chunk_text", ""),
                        chunk_index=meta.get("chunk_index", i),
                        start_position=meta.get("start_position"),
                        end_position=meta.get("end_position"),
                        embedding=vector.tolist(),
                        section_heading=meta.get("section_heading"),
                        subsection_heading=meta.get("subsection_heading"),
                        chunk_type=meta.get("chunk_type"),
                        semantic_density=meta.get("semantic_density"),
                        contains_table=meta.get("contains_table", False),
                        contains_list=meta.get("contains_list", False),
                        contains_code=meta.get("contains_code", False),
                        contains_equation=meta.get("contains_equation", False),
                        contains_figure=meta.get("contains_figure", False),
                        language=meta.get("language"),
                        chunk_metadata=meta.get("chunk_metadata", {})
                    )
                    self.db.add(embedding)
                    logger.debug(f"Inserted embedding {embedding_id}")

            # Commit changes
            self.db.commit()
            logger.info(f"Indexed {len(vectors)} vectors in pgvector")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to index vectors: {e}", exc_info=True)
            raise RuntimeError(f"pgvector indexing failed: {e}")

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        Search for similar vectors using pgvector cosine similarity.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters:
                - document_types: List of MIME types
                - min_quality: Minimum extraction quality
                - date_from: Start date
                - date_to: End date
                - tags: List of tags
                - similarity_threshold: Minimum similarity score (0.0-1.0)
            **kwargs: Additional parameters:
                - offset: Pagination offset (default: 0)

        Returns:
            List of SearchResult objects sorted by similarity (descending)
        """
        # Validate query vector
        self.validate_query_vector(query_vector)

        try:
            offset = kwargs.get("offset", 0)
            similarity_threshold = (filters or {}).get("similarity_threshold", 0.0)

            # Calculate similarity score: 1 - cosine_distance
            similarity_expr = (
                1 - Embedding.embedding.cosine_distance(query_vector.tolist())
            ).label('similarity_score')

            # Build base query
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
            if similarity_threshold > 0.0:
                query = query.filter(similarity_expr > similarity_threshold)

            # Apply metadata filters
            query = self._apply_filters(query, filters)

            # Order by cosine distance (lower distance = higher similarity)
            query = query.order_by(
                Embedding.embedding.cosine_distance(query_vector.tolist())
            ).limit(top_k).offset(offset)

            # Execute query
            results = query.all()

            # Convert to SearchResult objects
            search_results = []
            for row in results:
                # Convert embedding to numpy array
                embedding_array = None
                if row.embedding is not None:
                    try:
                        embedding_array = np.array(list(row.embedding), dtype=np.float32)
                    except Exception as e:
                        logger.debug(f"Embedding conversion failed for {row.id}: {e}")

                # Build metadata dict
                metadata = {
                    "document_id": str(row.document_id),
                    "document_name": row.document_name,
                    "document_type": row.mime_type,
                    "chunk_text": row.chunk_text,
                    "chunk_index": row.chunk_index,
                    "section_heading": row.section_heading,
                    "chunk_type": row.chunk_type,
                    "extraction_quality": row.extraction_quality,
                    "created_at": row.created_at,
                    "chunk_position": {
                        "start": row.start_position,
                        "end": row.end_position
                    } if row.start_position is not None else None
                }

                search_results.append(
                    SearchResult(
                        id=str(row.id),
                        score=float(row.similarity_score),
                        metadata=metadata,
                        vector=embedding_array
                    )
                )

            logger.debug(f"pgvector search returned {len(search_results)} results")

            return search_results

        except Exception as e:
            logger.error(f"pgvector search failed: {e}", exc_info=True)
            raise RuntimeError(f"pgvector search failed: {e}")

    def delete(self, ids: List[str], **kwargs) -> None:
        """
        Delete vectors by their IDs.

        Args:
            ids: List of embedding IDs to delete
            **kwargs: Optional parameters (currently unused)
        """
        try:
            # Delete embeddings
            deleted_count = self.db.query(Embedding).filter(
                Embedding.id.in_(ids)
            ).delete(synchronize_session=False)

            self.db.commit()

            logger.info(f"Deleted {deleted_count} vectors from pgvector")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete vectors: {e}", exc_info=True)
            raise RuntimeError(f"pgvector deletion failed: {e}")

    def count(self, filters: Optional[Dict[str, Any]] = None, **kwargs) -> int:
        """
        Count vectors in the store (optionally with filters).

        Args:
            filters: Optional metadata filters (same as search)
            **kwargs: Optional parameters (currently unused)

        Returns:
            Number of vectors matching the filters
        """
        try:
            query = self.db.query(func.count(Embedding.id)).join(
                Document, Embedding.document_id == Document.id
            ).outerjoin(
                DocumentText, Embedding.document_id == DocumentText.document_id
            ).filter(
                Embedding.embedding.isnot(None),
                Document.status == 'completed',
                Document.is_deleted == False
            )

            # Apply filters
            query = self._apply_filters(query, filters)

            return query.scalar() or 0

        except Exception as e:
            logger.error(f"Failed to count vectors: {e}", exc_info=True)
            return 0

    def _apply_filters(self, query, filters: Optional[Dict[str, Any]]):
        """
        Apply metadata filters to query.

        Args:
            query: SQLAlchemy query object
            filters: Optional metadata filters

        Returns:
            Modified query with filters applied
        """
        if not filters:
            return query

        # Filter by document types (MIME types)
        if "document_types" in filters and filters["document_types"]:
            query = query.filter(Document.mime_type.in_(filters["document_types"]))

        # Filter by extraction quality
        if "min_quality" in filters and filters["min_quality"] is not None:
            query = query.filter(DocumentText.extraction_quality >= filters["min_quality"])

        # Filter by date range
        if "date_from" in filters and filters["date_from"]:
            query = query.filter(Document.created_at >= filters["date_from"])

        if "date_to" in filters and filters["date_to"]:
            query = query.filter(Document.created_at <= filters["date_to"])

        # Filter by tags
        if "tags" in filters and filters["tags"]:
            query = query.filter(Document.tags.overlap(filters["tags"]))

        return query

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about this vector store."""
        metadata = super().get_metadata()

        try:
            # Count total vectors
            total_vectors = self.count()
            metadata["total_vectors"] = total_vectors

            # Check if HNSW index exists
            # This is a simplified check - real implementation would query pg_indexes
            metadata["index_type"] = "hnsw"  # Assumption based on setup

        except Exception as e:
            logger.warning(f"Failed to get extended metadata: {e}")

        return metadata
