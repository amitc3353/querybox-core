"""
Unit Tests for Reranking Pipeline (Step 10.2)
Tests RerankingPipeline orchestration of cross-encoder, deduplication, and MMR
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
import numpy as np

from app.services.search.reranking_pipeline import (
    RerankingPipeline,
    get_reranking_pipeline
)
from app.services.search.cross_encoder_service import CrossEncoderService
from app.services.search.mmr_ranker import MMRRanker
from app.services.search.deduplication_service import DeduplicationService
from app.schemas.search import SearchResultItem


class TestRerankingPipeline:
    """Test RerankingPipeline"""

    @pytest.fixture
    def mock_cross_encoder(self):
        """Create mock cross-encoder service"""
        mock = Mock(spec=CrossEncoderService)
        # Simulate reranking by returning top-k candidates with updated scores
        def mock_rerank(query, candidates, top_k):
            return candidates[:top_k]
        mock.rerank.side_effect = mock_rerank
        return mock

    @pytest.fixture
    def mock_mmr_ranker(self):
        """Create mock MMR ranker"""
        mock = Mock(spec=MMRRanker)
        mock.lambda_param = 0.7
        # Simulate MMR by returning top-k candidates
        def mock_rerank_with_mmr(candidates, top_k):
            return candidates[:top_k]
        mock.rerank_with_mmr.side_effect = mock_rerank_with_mmr
        mock.calculate_diversity_score.return_value = 0.75
        return mock

    @pytest.fixture
    def mock_dedup_service(self):
        """Create mock deduplication service"""
        mock = Mock(spec=DeduplicationService)
        # Simulate deduplication by removing 1 duplicate
        def mock_deduplicate(candidates):
            # Simulate removing 1 duplicate
            return candidates if len(candidates) <= 1 else candidates[:-1]
        mock.deduplicate.side_effect = mock_deduplicate
        mock.calculate_deduplication_stats.return_value = {
            "original_count": 50,
            "deduplicated_count": 45,
            "duplicates_removed": 5,
            "deduplication_rate": 0.1
        }
        return mock

    @pytest.fixture
    def pipeline_all_enabled(self, mock_cross_encoder, mock_mmr_ranker, mock_dedup_service):
        """Create pipeline with all stages enabled"""
        return RerankingPipeline(
            cross_encoder=mock_cross_encoder,
            mmr_ranker=mock_mmr_ranker,
            dedup_service=mock_dedup_service,
            enable_reranking=True,
            enable_mmr=True,
            enable_dedup=True
        )

    @pytest.fixture
    def pipeline_reranking_disabled(self, mock_cross_encoder, mock_mmr_ranker, mock_dedup_service):
        """Create pipeline with reranking disabled"""
        return RerankingPipeline(
            cross_encoder=mock_cross_encoder,
            mmr_ranker=mock_mmr_ranker,
            dedup_service=mock_dedup_service,
            enable_reranking=False,  # Disabled
            enable_mmr=True,
            enable_dedup=True
        )

    @pytest.fixture
    def test_candidates(self):
        """Create test candidates"""
        doc_id = str(uuid4())
        return [
            SearchResultItem(
                document_id=doc_id,
                document_name=f"doc{i}.pdf",
                relevance_score=max(0.1, 0.9 - i * 0.008),  # Ensure score stays >= 0.1 for all 100 candidates
                snippet=f"Test snippet {i}",
                chunk_index=i,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
            for i in range(100)  # 100 candidates
        ]

    # Test 1: Full pipeline with all stages enabled
    def test_full_pipeline_all_stages_enabled(
        self,
        pipeline_all_enabled,
        test_candidates,
        mock_cross_encoder,
        mock_dedup_service,
        mock_mmr_ranker
    ):
        """Test full pipeline runs all 3 stages when enabled"""
        query = "test query"
        final_top_k = 10
        rerank_top_k = 50

        result = pipeline_all_enabled.process(
            query=query,
            candidates=test_candidates,
            final_top_k=final_top_k,
            rerank_top_k=rerank_top_k
        )

        # Verify all stages were called
        mock_cross_encoder.rerank.assert_called_once()
        mock_dedup_service.deduplicate.assert_called_once()
        mock_mmr_ranker.rerank_with_mmr.assert_called_once()

        # Verify final results
        assert "results" in result
        assert len(result["results"]) == final_top_k

        # Verify metadata
        assert "processing_time_ms" in result
        assert "pipeline_stats" in result

        # Verify all stages in stats
        stats = result["pipeline_stats"]
        assert "stage1_reranking" in stats
        assert "stage2_deduplication" in stats
        assert "stage3_mmr" in stats

        # Verify stage 1 stats
        assert stats["stage1_reranking"]["enabled"] is True
        assert "processing_time_ms" in stats["stage1_reranking"]

        # Verify stage 2 stats
        assert stats["stage2_deduplication"]["enabled"] is True
        assert "processing_time_ms" in stats["stage2_deduplication"]

        # Verify stage 3 stats
        assert stats["stage3_mmr"]["enabled"] is True
        assert "diversity_score" in stats["stage3_mmr"]
        assert "processing_time_ms" in stats["stage3_mmr"]

    # Test 2: Pipeline with reranking disabled
    def test_pipeline_reranking_disabled(
        self,
        pipeline_reranking_disabled,
        test_candidates,
        mock_cross_encoder,
        mock_dedup_service,
        mock_mmr_ranker
    ):
        """Test pipeline skips reranking when disabled"""
        query = "test query"
        final_top_k = 10
        rerank_top_k = 50

        result = pipeline_reranking_disabled.process(
            query=query,
            candidates=test_candidates,
            final_top_k=final_top_k,
            rerank_top_k=rerank_top_k
        )

        # Reranking should NOT be called
        mock_cross_encoder.rerank.assert_not_called()

        # Dedup and MMR should still be called
        mock_dedup_service.deduplicate.assert_called_once()
        mock_mmr_ranker.rerank_with_mmr.assert_called_once()

        # Verify stats show reranking disabled
        stats = result["pipeline_stats"]
        assert stats["stage1_reranking"]["enabled"] is False

    # Test 3: Pipeline with MMR disabled
    def test_pipeline_mmr_disabled(self, mock_cross_encoder, mock_mmr_ranker, mock_dedup_service, test_candidates):
        """Test pipeline skips MMR when disabled"""
        pipeline = RerankingPipeline(
            cross_encoder=mock_cross_encoder,
            mmr_ranker=mock_mmr_ranker,
            dedup_service=mock_dedup_service,
            enable_reranking=True,
            enable_mmr=False,  # Disabled
            enable_dedup=True
        )

        query = "test query"
        result = pipeline.process(
            query=query,
            candidates=test_candidates,
            final_top_k=10,
            rerank_top_k=50
        )

        # MMR should NOT be called
        mock_mmr_ranker.rerank_with_mmr.assert_not_called()

        # Reranking and dedup should still be called
        mock_cross_encoder.rerank.assert_called_once()
        mock_dedup_service.deduplicate.assert_called_once()

        # Verify stats show MMR disabled
        stats = result["pipeline_stats"]
        assert stats["stage3_mmr"]["enabled"] is False

    # Test 4: Pipeline with dedup disabled
    def test_pipeline_dedup_disabled(self, mock_cross_encoder, mock_mmr_ranker, mock_dedup_service, test_candidates):
        """Test pipeline skips deduplication when disabled"""
        pipeline = RerankingPipeline(
            cross_encoder=mock_cross_encoder,
            mmr_ranker=mock_mmr_ranker,
            dedup_service=mock_dedup_service,
            enable_reranking=True,
            enable_mmr=True,
            enable_dedup=False  # Disabled
        )

        query = "test query"
        result = pipeline.process(
            query=query,
            candidates=test_candidates,
            final_top_k=10,
            rerank_top_k=50
        )

        # Dedup should NOT be called
        mock_dedup_service.deduplicate.assert_not_called()

        # Reranking and MMR should still be called
        mock_cross_encoder.rerank.assert_called_once()
        mock_mmr_ranker.rerank_with_mmr.assert_called_once()

        # Verify stats show dedup disabled
        stats = result["pipeline_stats"]
        assert stats["stage2_deduplication"]["enabled"] is False

    # Test 5: Statistics collection
    def test_pipeline_statistics_collection(
        self,
        pipeline_all_enabled,
        test_candidates,
        mock_dedup_service
    ):
        """Test pipeline collects comprehensive statistics"""
        query = "test query"
        result = pipeline_all_enabled.process(
            query=query,
            candidates=test_candidates,
            final_top_k=10,
            rerank_top_k=50
        )

        stats = result["pipeline_stats"]

        # Verify stage 1 stats (reranking)
        assert stats["stage1_reranking"]["enabled"] is True
        assert stats["stage1_reranking"]["input_count"] == len(test_candidates)
        assert stats["stage1_reranking"]["output_count"] == 50  # rerank_top_k
        assert "processing_time_ms" in stats["stage1_reranking"]
        assert stats["stage1_reranking"]["processing_time_ms"] >= 0

        # Verify stage 2 stats (deduplication)
        assert stats["stage2_deduplication"]["enabled"] is True
        assert "original_count" in stats["stage2_deduplication"]
        assert "deduplicated_count" in stats["stage2_deduplication"]
        assert "duplicates_removed" in stats["stage2_deduplication"]
        assert "deduplication_rate" in stats["stage2_deduplication"]
        assert "processing_time_ms" in stats["stage2_deduplication"]

        # Verify stage 3 stats (MMR)
        assert stats["stage3_mmr"]["enabled"] is True
        assert "input_count" in stats["stage3_mmr"]
        assert "output_count" in stats["stage3_mmr"]
        assert "diversity_score" in stats["stage3_mmr"]
        assert stats["stage3_mmr"]["lambda"] == 0.7
        assert "processing_time_ms" in stats["stage3_mmr"]

        # Verify total processing time
        assert "processing_time_ms" in result
        assert result["processing_time_ms"] >= 0

    # Test 6: Empty candidates
    def test_pipeline_empty_candidates(self, pipeline_all_enabled):
        """Test pipeline handles empty candidates gracefully"""
        query = "test query"
        empty_candidates = []

        result = pipeline_all_enabled.process(
            query=query,
            candidates=empty_candidates,
            final_top_k=10,
            rerank_top_k=50
        )

        assert result["results"] == []

    # Test 7: Pipeline error handling
    def test_pipeline_error_handling(
        self,
        mock_cross_encoder,
        mock_mmr_ranker,
        mock_dedup_service,
        test_candidates
    ):
        """Test pipeline handles errors gracefully"""
        # Make cross-encoder raise exception
        mock_cross_encoder.rerank.side_effect = Exception("Model error")

        pipeline = RerankingPipeline(
            cross_encoder=mock_cross_encoder,
            mmr_ranker=mock_mmr_ranker,
            dedup_service=mock_dedup_service,
            enable_reranking=True,
            enable_mmr=True,
            enable_dedup=True
        )

        query = "test query"

        # Should not raise exception
        try:
            result = pipeline.process(
                query=query,
                candidates=test_candidates,
                final_top_k=10,
                rerank_top_k=50
            )
            # Should still return results (pipeline continues despite error)
            assert "results" in result
        except Exception:
            pytest.fail("Pipeline should handle errors gracefully")

    # Test 8: Stage execution order
    def test_pipeline_stage_execution_order(
        self,
        pipeline_all_enabled,
        test_candidates,
        mock_cross_encoder,
        mock_dedup_service,
        mock_mmr_ranker
    ):
        """Test stages execute in correct order: reranking -> dedup -> MMR"""
        call_order = []

        # Track call order
        mock_cross_encoder.rerank.side_effect = lambda *args, **kwargs: (
            call_order.append("reranking"),
            test_candidates[:50]
        )[1]

        mock_dedup_service.deduplicate.side_effect = lambda candidates: (
            call_order.append("dedup"),
            candidates[:-1]  # Remove 1
        )[1]

        mock_mmr_ranker.rerank_with_mmr.side_effect = lambda candidates, top_k: (
            call_order.append("mmr"),
            candidates[:top_k]
        )[1]

        query = "test query"
        pipeline_all_enabled.process(
            query=query,
            candidates=test_candidates,
            final_top_k=10,
            rerank_top_k=50
        )

        # Verify execution order
        assert call_order == ["reranking", "dedup", "mmr"]

    # Test 9: Pagination handling
    def test_pipeline_pagination_handling(
        self,
        pipeline_all_enabled,
        test_candidates
    ):
        """Test pipeline handles pagination correctly"""
        query = "test query"
        final_top_k = 10
        rerank_top_k = 50

        result = pipeline_all_enabled.process(
            query=query,
            candidates=test_candidates,
            final_top_k=final_top_k,
            rerank_top_k=rerank_top_k
        )

        # Should return exactly final_top_k results
        assert len(result["results"]) == final_top_k

    # Test 10: Uses settings defaults
    def test_pipeline_uses_settings_defaults(
        self,
        mock_cross_encoder,
        mock_mmr_ranker,
        mock_dedup_service
    ):
        """Test pipeline uses settings defaults when parameters not provided"""
        # Create pipeline without explicit enable flags
        pipeline = RerankingPipeline(
            cross_encoder=mock_cross_encoder,
            mmr_ranker=mock_mmr_ranker,
            dedup_service=mock_dedup_service
            # No enable_reranking, enable_mmr, enable_dedup -> use settings defaults
        )

        # Should have settings defaults
        from app.core.config import settings
        assert pipeline.enable_reranking == settings.ENABLE_RERANKING
        assert pipeline.enable_mmr == settings.ENABLE_MMR
        assert pipeline.enable_dedup == settings.ENABLE_ADVANCED_DEDUP


class TestGetRerankingPipeline:
    """Test get_reranking_pipeline factory function"""

    @patch('app.services.search.reranking_pipeline.CrossEncoderService')
    @patch('app.services.search.reranking_pipeline.MMRRanker')
    @patch('app.services.search.reranking_pipeline.DeduplicationService')
    def test_get_reranking_pipeline_returns_instance(
        self,
        mock_dedup_class,
        mock_mmr_class,
        mock_cross_encoder_class
    ):
        """Test factory returns RerankingPipeline instance"""
        pipeline = get_reranking_pipeline()

        assert pipeline is not None
        assert isinstance(pipeline, RerankingPipeline)

    @patch('app.services.search.reranking_pipeline.CrossEncoderService')
    @patch('app.services.search.reranking_pipeline.MMRRanker')
    @patch('app.services.search.reranking_pipeline.DeduplicationService')
    def test_get_reranking_pipeline_with_provided_services(
        self,
        mock_dedup_class,
        mock_mmr_class,
        mock_cross_encoder_class
    ):
        """Test factory accepts provided service instances"""
        cross_encoder = Mock(spec=CrossEncoderService)
        mmr_ranker = Mock(spec=MMRRanker)
        dedup_service = Mock(spec=DeduplicationService)

        pipeline = get_reranking_pipeline(
            cross_encoder=cross_encoder,
            mmr_ranker=mmr_ranker,
            dedup_service=dedup_service
        )

        # Should use provided instances (not create new ones)
        assert pipeline.cross_encoder is cross_encoder
        assert pipeline.mmr_ranker is mmr_ranker
        assert pipeline.dedup_service is dedup_service
