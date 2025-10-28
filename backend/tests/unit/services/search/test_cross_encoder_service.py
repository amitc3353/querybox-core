"""
Unit Tests for Cross-Encoder Reranking Service (Step 10.2)
Tests CrossEncoderService without external dependencies
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
import numpy as np

from app.services.search.cross_encoder_service import (
    CrossEncoderService,
    get_cross_encoder_service
)
from app.schemas.search import SearchResultItem
from app.core.config import settings


class TestCrossEncoderService:
    """Test CrossEncoderService"""

    @pytest.fixture
    def mock_cross_encoder_model(self):
        """Create mock cross-encoder model"""
        mock_model = MagicMock()
        # Return valid scores that will be normalized
        mock_model.predict.return_value = np.array([0.5, 0.3, 0.1, -0.2, -0.5])
        return mock_model

    @pytest.fixture
    def service_with_mock_model(self, mock_cross_encoder_model):
        """Create CrossEncoderService with mocked model"""
        with patch('app.services.search.cross_encoder_service.CrossEncoder') as mock_cross_encoder:
            mock_cross_encoder.return_value = mock_cross_encoder_model
            service = CrossEncoderService(
                model_name="cross-encoder/ms-marco-MiniLM-L6-v2",
                device="cpu",
                batch_size=32,
                max_length=512
            )
            return service

    @pytest.fixture
    def test_candidates(self):
        """Create test search result candidates"""
        doc_id = str(uuid4())
        return [
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.9,
                snippet="Machine learning is a subset of artificial intelligence",
                chunk_index=1,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.8,
                snippet="Deep learning uses neural networks for pattern recognition",
                chunk_index=2,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.7,
                snippet="Natural language processing enables computers to understand text",
                chunk_index=3,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.6,
                snippet="Computer vision allows machines to interpret visual information",
                chunk_index=4,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.5,
                snippet="Reinforcement learning trains agents through rewards and penalties",
                chunk_index=5,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

    # Test 1: Basic reranking functionality
    def test_cross_encoder_reranking_basic(self, service_with_mock_model, test_candidates):
        """Test cross-encoder reranking returns reordered results"""
        query = "What is machine learning?"
        top_k = 3

        reranked = service_with_mock_model.rerank(query, test_candidates, top_k)

        # Should return top_k results
        assert len(reranked) == top_k

        # Results should be SearchResultItem instances
        for result in reranked:
            assert isinstance(result, SearchResultItem)

        # Scores should be normalized (0.0-1.0)
        for result in reranked:
            assert 0.0 <= result.relevance_score <= 1.0

        # Results should be sorted by relevance score (descending)
        scores = [r.relevance_score for r in reranked]
        assert scores == sorted(scores, reverse=True)

    # Test 2: Score normalization using sigmoid
    def test_cross_encoder_score_normalization(self, service_with_mock_model, test_candidates):
        """Test sigmoid normalization converts raw scores to 0.0-1.0"""
        query = "test query"

        # Mock returns specific scores including negative values
        service_with_mock_model.model.predict.return_value = np.array([2.0, 0.0, -2.0])

        reranked = service_with_mock_model.rerank(query, test_candidates[:3], top_k=3)

        # All scores should be in [0.0, 1.0] after sigmoid normalization
        for result in reranked:
            assert 0.0 <= result.relevance_score <= 1.0

        # Positive logit (2.0) -> sigmoid > 0.5
        assert reranked[0].relevance_score > 0.5

        # Zero logit (0.0) -> sigmoid = 0.5
        assert 0.45 < reranked[1].relevance_score < 0.55

        # Negative logit (-2.0) -> sigmoid < 0.5
        assert reranked[2].relevance_score < 0.5

    # Test 3: Empty candidates
    def test_cross_encoder_empty_candidates(self, service_with_mock_model):
        """Test reranking with empty candidates returns empty list"""
        query = "test query"
        empty_candidates = []

        reranked = service_with_mock_model.rerank(query, empty_candidates, top_k=10)

        assert reranked == []

    # Test 4: Single candidate
    def test_cross_encoder_single_candidate(self, service_with_mock_model, test_candidates):
        """Test reranking with single candidate returns single result"""
        query = "test query"
        single_candidate = [test_candidates[0]]

        service_with_mock_model.model.predict.return_value = np.array([0.8])

        reranked = service_with_mock_model.rerank(query, single_candidate, top_k=10)

        assert len(reranked) == 1
        assert isinstance(reranked[0], SearchResultItem)
        assert 0.0 <= reranked[0].relevance_score <= 1.0

    # Test 5: Device fallback (CPU/GPU)
    def test_cross_encoder_device_fallback(self, service_with_mock_model, test_candidates):
        """Test fallback from GPU to CPU on OOM error"""
        query = "test query"

        # Mock GPU OOM error on first call, success on second
        service_with_mock_model.model.predict.side_effect = [
            RuntimeError("CUDA out of memory"),
            np.array([0.5, 0.3, 0.1, -0.2, -0.5])  # Success after fallback
        ]
        service_with_mock_model.model.to = MagicMock()  # Mock device switching

        reranked = service_with_mock_model.rerank(query, test_candidates, top_k=3)

        # Should succeed after fallback
        assert len(reranked) == 3

        # Should have switched to CPU
        service_with_mock_model.model.to.assert_called_once_with("cpu")
        assert service_with_mock_model.device == "cpu"

    # Test 6: NaN/Inf score handling
    def test_cross_encoder_nan_inf_handling(self, service_with_mock_model, test_candidates):
        """Test NaN and Inf scores are replaced with neutral 0.5"""
        query = "test query"

        # Return NaN and Inf values
        service_with_mock_model.model.predict.return_value = np.array([
            np.nan, np.inf, -np.inf, 1.0, 0.5
        ])

        reranked = service_with_mock_model.rerank(query, test_candidates, top_k=5)

        # All scores should be valid (no NaN/Inf)
        for result in reranked:
            assert not np.isnan(result.relevance_score)
            assert not np.isinf(result.relevance_score)
            assert 0.0 <= result.relevance_score <= 1.0

    # Test 7: Model not loaded
    def test_cross_encoder_model_not_loaded(self, test_candidates):
        """Test graceful fallback when model not loaded"""
        # Create service with model=None (simulating loading failure)
        with patch('app.services.search.cross_encoder_service.CrossEncoder') as mock_cross_encoder:
            mock_cross_encoder.side_effect = Exception("Model loading failed")

            service = CrossEncoderService()

            # Model should be None
            assert service.model is None

            # Reranking should fall back to original scores
            query = "test query"
            reranked = service.rerank(query, test_candidates, top_k=3)

            # Should return top-k sorted by original scores
            assert len(reranked) == 3
            scores = [r.relevance_score for r in reranked]
            assert scores == sorted(scores, reverse=True)

    # Test 8: Metadata preservation
    def test_cross_encoder_preserves_metadata(self, service_with_mock_model):
        """Test reranking preserves all candidate metadata"""
        doc_id = str(uuid4())
        created_at = datetime.now(timezone.utc)

        candidate = SearchResultItem(
            document_id=doc_id,
            document_name="test.pdf",
            relevance_score=0.9,
            snippet="original snippet",
            chunk_index=42,
            chunk_position={'start': 100, 'end': 200},
            extraction_quality=0.88,
            document_type="application/pdf",
            created_at=created_at
        )

        service_with_mock_model.model.predict.return_value = np.array([0.75])

        reranked = service_with_mock_model.rerank("test", [candidate], top_k=1)

        # Verify all metadata preserved (except relevance_score which is updated)
        result = reranked[0]
        assert result.document_id == doc_id
        assert result.document_name == "test.pdf"
        assert result.snippet == "original snippet"
        assert result.chunk_index == 42
        assert result.chunk_position == {'start': 100, 'end': 200}
        assert result.extraction_quality == 0.88
        assert result.document_type == "application/pdf"
        assert result.created_at == created_at


class TestGetCrossEncoderService:
    """Test get_cross_encoder_service factory function"""

    def test_get_cross_encoder_service_returns_instance(self):
        """Test factory returns CrossEncoderService instance"""
        with patch('app.services.search.cross_encoder_service.CrossEncoder'):
            service = get_cross_encoder_service()

            assert service is not None
            assert isinstance(service, CrossEncoderService)

    def test_get_cross_encoder_service_with_custom_params(self):
        """Test factory with custom parameters"""
        with patch('app.services.search.cross_encoder_service.CrossEncoder'):
            service = get_cross_encoder_service(
                model_name="custom-model",
                device="cuda",
                batch_size=16
            )

            assert service.model_name == "custom-model"
            assert service.device == "cuda"
            assert service.batch_size == 16
