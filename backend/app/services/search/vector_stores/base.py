"""
Abstract base class for vector stores.

This module defines the interface that all vector store implementations must implement,
enabling swappable vector storage strategies (Qdrant, pgvector, LanceDB, Weaviate, etc.)
without changing the core application logic.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np
from dataclasses import dataclass


@dataclass
class SearchResult:
    """
    Standardized search result returned by vector stores.

    Attributes:
        id: Unique identifier for the vector/document
        score: Similarity/relevance score
        vector: The embedding vector (optional, can be omitted to save bandwidth)
        metadata: Associated metadata (chunk text, document info, etc.)
    """
    id: str
    score: float
    metadata: Dict[str, Any]
    vector: Optional[np.ndarray] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "id": self.id,
            "score": self.score,
            "metadata": self.metadata
        }
        if self.vector is not None:
            result["vector"] = self.vector.tolist()
        return result


class VectorStore(ABC):
    """
    Abstract base class for vector stores.

    All vector store implementations (Qdrant, pgvector, LanceDB, etc.) must
    inherit from this class and implement its abstract methods.

    Example:
        class QdrantStore(VectorStore):
            def index(self, vectors, metadata, ids):
                # Implementation here
                pass
    """

    def __init__(self, name: str, dimension: int):
        """
        Initialize vector store.

        Args:
            name: Human-readable name for this store (e.g., "qdrant", "pgvector")
            dimension: Embedding vector dimension this store handles
        """
        self.name = name
        self.dimension = dimension

    @abstractmethod
    def index(
        self,
        vectors: List[np.ndarray],
        metadata: List[Dict[str, Any]],
        ids: List[str],
        **kwargs
    ) -> None:
        """
        Index (upsert) vectors with associated metadata.

        Args:
            vectors: List of embedding vectors to index
            metadata: List of metadata dicts (one per vector)
            ids: List of unique identifiers (one per vector)
            **kwargs: Store-specific options (e.g., batch_size, collection_name)

        Raises:
            ValueError: If vectors, metadata, and ids have different lengths
            Exception: For indexing errors
        """
        pass

    @abstractmethod
    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Metadata filters (e.g., {"document_id": "abc123"})
            **kwargs: Store-specific options (e.g., ef_search for HNSW)

        Returns:
            List of SearchResult objects, sorted by score (descending)

        Raises:
            ValueError: If query_vector has wrong dimension
            Exception: For search errors
        """
        pass

    @abstractmethod
    def delete(self, ids: List[str], **kwargs) -> None:
        """
        Delete vectors by their IDs.

        Args:
            ids: List of vector IDs to delete
            **kwargs: Store-specific options

        Raises:
            Exception: For deletion errors
        """
        pass

    def get_dimension(self) -> int:
        """
        Get the vector dimension for this store.

        Returns:
            Embedding vector dimension
        """
        return self.dimension

    def validate_vectors(
        self,
        vectors: List[np.ndarray],
        metadata: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Validate that vectors, metadata, and ids have consistent lengths and valid content.

        Args:
            vectors: List of embedding vectors
            metadata: List of metadata dicts
            ids: List of IDs

        Raises:
            ValueError: If validation fails
        """
        if len(vectors) != len(metadata):
            raise ValueError(
                f"Vectors and metadata length mismatch: "
                f"{len(vectors)} vs {len(metadata)}"
            )

        if len(vectors) != len(ids):
            raise ValueError(
                f"Vectors and ids length mismatch: "
                f"{len(vectors)} vs {len(ids)}"
            )

        if not vectors:
            raise ValueError("Vectors list cannot be empty")

        # Validate each vector dimension
        for i, vector in enumerate(vectors):
            if vector.shape[0] != self.dimension:
                raise ValueError(
                    f"Vector {i} has wrong dimension: "
                    f"expected {self.dimension}, got {vector.shape[0]}"
                )

            if np.isnan(vector).any():
                raise ValueError(f"Vector {i} contains NaN values")

            if np.isinf(vector).any():
                raise ValueError(f"Vector {i} contains infinite values")

    def validate_query_vector(self, query_vector: np.ndarray) -> None:
        """
        Validate that query vector has correct dimension and valid values.

        Args:
            query_vector: Query embedding vector

        Raises:
            ValueError: If validation fails
        """
        if query_vector.shape[0] != self.dimension:
            raise ValueError(
                f"Query vector has wrong dimension: "
                f"expected {self.dimension}, got {query_vector.shape[0]}"
            )

        if np.isnan(query_vector).any():
            raise ValueError("Query vector contains NaN values")

        if np.isinf(query_vector).any():
            raise ValueError("Query vector contains infinite values")

    def count(self, filters: Optional[Dict[str, Any]] = None, **kwargs) -> int:
        """
        Count vectors in the store (optionally with filters).

        This is an optional method that subclasses can override.
        Default implementation raises NotImplementedError.

        Args:
            filters: Metadata filters
            **kwargs: Store-specific options

        Returns:
            Number of vectors matching the filters

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement count()"
        )

    def get_by_id(self, id: str, **kwargs) -> Optional[SearchResult]:
        """
        Retrieve a vector by its ID.

        This is an optional method that subclasses can override.
        Default implementation raises NotImplementedError.

        Args:
            id: Vector ID
            **kwargs: Store-specific options

        Returns:
            SearchResult if found, None otherwise

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement get_by_id()"
        )

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this vector store.

        Returns:
            Dictionary containing store name, dimension, and other info
        """
        return {
            "name": self.name,
            "dimension": self.dimension,
            "store_type": self.__class__.__name__
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', dimension={self.dimension})"
