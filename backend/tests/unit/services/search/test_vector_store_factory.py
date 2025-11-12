"""
Unit tests for vector store factory pattern

Tests:
- Factory returns correct store based on config
- Invalid store names raise errors
- Store override works
- Available stores list is correct
- Required parameters validation
"""
import pytest
from unittest.mock import Mock, patch

from app.services.search.vector_stores.factory import (
    get_vector_store,
    get_available_vector_stores
)
from app.services.search.vector_stores.base import VectorStore
from app.services.search.vector_stores.pgvector_store import PgVectorStore


class TestVectorStoreFactory:
    """Test vector store factory function"""

    def test_get_store_default_requires_db(self):
        """Test factory requires db parameter for pgvector"""
        with pytest.raises(ValueError, match="pgvector store requires 'db' parameter"):
            get_vector_store()

    def test_get_store_pgvector_with_db(self):
        """Test factory returns PgVectorStore when db provided"""
        mock_db = Mock()
        store = get_vector_store(db=mock_db)

        assert isinstance(store, VectorStore)
        assert isinstance(store, PgVectorStore)
        assert store.db is mock_db

    def test_get_store_pgvector_explicit(self):
        """Test factory returns pgvector when explicitly requested"""
        mock_db = Mock()
        store = get_vector_store("pgvector", db=mock_db)

        assert isinstance(store, PgVectorStore)

    def test_get_store_invalid_name(self):
        """Test factory raises error for invalid store name"""
        mock_db = Mock()
        with pytest.raises(ValueError, match="Unknown vector store"):
            get_vector_store("invalid_store", db=mock_db)

    @patch('app.core.config.settings')
    def test_get_store_from_config(self, mock_settings):
        """Test factory uses config setting"""
        mock_settings.VECTOR_STORE = "pgvector"
        mock_db = Mock()
        store = get_vector_store(db=mock_db)

        assert isinstance(store, PgVectorStore)

    def test_get_store_override_config(self):
        """Test explicit store name overrides config"""
        mock_db = Mock()
        store = get_vector_store("pgvector", db=mock_db)

        assert isinstance(store, PgVectorStore)

    def test_get_store_with_dimension(self):
        """Test factory accepts dimension parameter"""
        mock_db = Mock()
        store = get_vector_store("pgvector", db=mock_db, dimension=1536)

        assert isinstance(store, PgVectorStore)
        assert store.dimension == 1536

    def test_get_available_stores(self):
        """Test available stores list"""
        stores = get_available_vector_stores()

        assert isinstance(stores, list)
        assert "pgvector" in stores
        assert len(stores) >= 1

    def test_store_is_new_instance(self):
        """Test each factory call creates a new instance"""
        mock_db = Mock()
        store1 = get_vector_store(db=mock_db)
        store2 = get_vector_store(db=mock_db)

        # Should be different instances
        assert store1 is not store2


class TestVectorStoreInterface:
    """Test that all stores implement the base interface correctly"""

    def test_pgvector_store_has_required_methods(self):
        """Test PgVectorStore implements all abstract methods"""
        mock_db = Mock()
        store = PgVectorStore(db=mock_db, dimension=1024)

        # Check required methods exist
        assert hasattr(store, 'index')
        assert callable(store.index)
        assert hasattr(store, 'search')
        assert callable(store.search)
        assert hasattr(store, 'delete')
        assert callable(store.delete)

    def test_pgvector_store_metadata(self):
        """Test PgVectorStore has correct metadata"""
        mock_db = Mock()
        store = PgVectorStore(db=mock_db, dimension=1024)

        assert store.name == "pgvector"
        assert store.dimension == 1024

    def test_pgvector_store_dimension_configurable(self):
        """Test PgVectorStore dimension can be configured"""
        mock_db = Mock()

        store_1024 = PgVectorStore(db=mock_db, dimension=1024)
        assert store_1024.dimension == 1024

        store_3072 = PgVectorStore(db=mock_db, dimension=3072)
        assert store_3072.dimension == 3072
