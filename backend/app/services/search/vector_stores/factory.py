"""
Vector store factory for config-driven vector store selection.

Enables swapping vector stores via configuration without code changes.
"""

import logging
from typing import Optional, Any

from app.services.search.vector_stores.base import VectorStore
from app.services.search.vector_stores.pgvector_store import PgVectorStore

logger = logging.getLogger(__name__)


def get_vector_store(
    store_name: Optional[str] = None,
    **kwargs: Any
) -> VectorStore:
    """
    Get vector store based on configuration.

    This factory function returns the appropriate vector store implementation
    based on the VECTOR_STORE config setting (or override parameter).

    Args:
        store_name: Optional store name to override config
                   Options: "pgvector", "qdrant", "lancedb", "weaviate"
                   If None, uses settings.VECTOR_STORE
        **kwargs: Additional arguments passed to store constructor
                 For pgvector: db (SQLAlchemy session) required
                 For qdrant: url, api_key optional
                 For lancedb: uri optional

    Returns:
        VectorStore instance

    Raises:
        ValueError: If store_name is unknown or required kwargs missing

    Example:
        # Use default from config (pgvector requires db session)
        from app.db.session import get_db
        db = next(get_db())
        vector_store = get_vector_store(db=db)

        # Override for specific use case
        qdrant_store = get_vector_store("qdrant", url="http://localhost:6333")
    """
    # Import settings here to avoid circular imports
    from app.core.config import settings

    # Use provided name or fall back to config
    name = store_name or settings.VECTOR_STORE

    logger.debug(f"Creating vector store: {name}")

    if name == "pgvector":
        # pgvector requires database session
        if "db" not in kwargs:
            raise ValueError("pgvector store requires 'db' parameter (SQLAlchemy session)")

        db = kwargs.pop("db")
        dimension = kwargs.pop("dimension", 1024)  # Default for BGE-M3
        return PgVectorStore(db=db, dimension=dimension)

    # Future stores (uncomment when implemented):
    # elif name == "qdrant":
    #     from app.services.search.vector_stores.qdrant_store import QdrantStore
    #     url = kwargs.pop("url", settings.QDRANT_URL)
    #     api_key = kwargs.pop("api_key", settings.QDRANT_API_KEY)
    #     dimension = kwargs.pop("dimension", 1024)
    #     return QdrantStore(url=url, api_key=api_key, dimension=dimension)
    #
    # elif name == "lancedb":
    #     from app.services.search.vector_stores.lancedb_store import LanceDBStore
    #     uri = kwargs.pop("uri", settings.LANCEDB_URI)
    #     dimension = kwargs.pop("dimension", 1024)
    #     return LanceDBStore(uri=uri, dimension=dimension)
    #
    # elif name == "weaviate":
    #     from app.services.search.vector_stores.weaviate_store import WeaviateStore
    #     url = kwargs.pop("url", settings.WEAVIATE_URL)
    #     api_key = kwargs.pop("api_key", settings.WEAVIATE_API_KEY)
    #     dimension = kwargs.pop("dimension", 1024)
    #     return WeaviateStore(url=url, api_key=api_key, dimension=dimension)

    else:
        available = ["pgvector"]  # Add others as implemented
        raise ValueError(
            f"Unknown vector store: '{name}'. "
            f"Available options: {', '.join(available)}"
        )


def get_available_vector_stores() -> list[str]:
    """
    Get list of available vector store names.

    Returns:
        List of store names that can be used with get_vector_store()
    """
    return ["pgvector"]  # Add others as implemented
