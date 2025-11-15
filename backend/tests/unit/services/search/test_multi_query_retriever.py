"""
Unit Tests for Multi-Query RAG Retriever - Phase 5: Advanced Retrieval

Tests MultiQueryRetriever with mocked dependencies:
- LLM provider for query generation
- HybridSearchService for parallel searches
- Redis client for caching
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.services.search.multi_query_retriever import (
    MultiQueryRetriever,
    get_multi_query_retriever,
)
from app.services.search.hybrid_search_service import HybridSearchService
from app.schemas.search import SearchResultItem, SearchFilters
from app.schemas.multi_query import MultiQueryResponse, MultiQueryMetadata
from app.core.config import Settings


class TestMultiQueryRetriever:
    """Test MultiQueryRetriever"""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with Multi-Query configuration"""
        settings = Mock(spec=Settings)
        settings.MULTI_QUERY_ENABLED = True
        settings.MULTI_QUERY_NUM_VARIATIONS = 2
        settings.MULTI_QUERY_LLM_PROVIDER = "openrouter"
        settings.MULTI_QUERY_MODEL = "openai/gpt-4o-mini"
        settings.MULTI_QUERY_TEMPERATURE = 0.7
        settings.MULTI_QUERY_MAX_TOKENS = 200
        settings.MULTI_QUERY_CACHE_ENABLED = True
        settings.MULTI_QUERY_CACHE_TTL = 3600
        settings.MULTI_QUERY_FREQ_WEIGHT = 2.0
        settings.MULTI_QUERY_RRF_WEIGHT = 1.0
        settings.MULTI_QUERY_FALLBACK_ON_ERROR = True
        settings.MULTI_QUERY_TRACK_COST = True
        return settings

    @pytest.fixture
    def mock_hybrid_search(self):
        """Create mock HybridSearchService"""
        service = Mock(spec=HybridSearchService)
        service.search = Mock()  # HybridSearchService.search() is NOT async
        return service

    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider"""
        provider = Mock()
        provider.generate = AsyncMock()
        return provider

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client"""
        redis = Mock()
        redis.get = Mock(return_value=None)  # Cache miss by default
        redis.setex = Mock()
        return redis

    @pytest.fixture
    def retriever(self, mock_hybrid_search, mock_settings, mock_redis):
        """Create MultiQueryRetriever instance with mocked dependencies"""
        with patch('app.services.search.multi_query_retriever.get_llm_provider') as mock_factory:
            # Mock LLM provider
            mock_provider = Mock()
            mock_provider.generate = Mock()  # Not async
            mock_factory.return_value = mock_provider

            retriever = MultiQueryRetriever(
                hybrid_search_service=mock_hybrid_search,
                settings=mock_settings,
                redis_client=mock_redis,
            )

            return retriever

    @pytest.fixture
    def sample_search_results(self):
        """Sample search results from hybrid search"""
        doc_id = str(uuid4())
        return [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.95,
                document_name="doc1.pdf",
                snippet="machine learning algorithms",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                chunk_index=2,
                relevance_score=0.85,
                document_name="doc1.pdf",
                snippet="deep learning techniques",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
        ]

    # ========================================
    # Test: Query Variation Generation
    # ========================================

    @pytest.mark.asyncio
    async def test_generate_variations_success(self, retriever, mock_redis):
        """Test successful query variation generation"""
        # Mock LLM response
        llm_response = """1. What are different machine learning techniques?
2. Explain various ML algorithms and their applications"""

        from app.services.llm.base import LLMResponse
        mock_response = LLMResponse(
            text=llm_response,
            tokens_input=50,
            tokens_output=30,
            model="openai/gpt-4o-mini",
            latency_ms=100
        )
        retriever.llm_provider.generate = Mock(return_value=mock_response)

        # Execute
        variations, cost_usd, cache_hit = await retriever._generate_variations_with_cost(
            "machine learning algorithms"
        )

        # Assert
        assert len(variations) == 2
        assert variations[0] == "What are different machine learning techniques?"
        assert variations[1] == "Explain various ML algorithms and their applications"
        assert cost_usd > 0  # Cost tracking enabled
        assert cache_hit is False

    @pytest.mark.asyncio
    async def test_generate_variations_cache_hit(self, retriever, mock_redis):
        """Test cache hit for query variations"""
        import json

        # Mock Redis cache hit
        cached_variations = ["variation 1", "variation 2"]
        mock_redis.get.return_value = json.dumps(cached_variations)

        # Execute
        variations, cost_usd, cache_hit = await retriever._generate_variations_with_cost(
            "test query"
        )

        # Assert
        assert variations == cached_variations
        assert cost_usd == 0.0  # No LLM call, so no cost
        assert cache_hit is True
        retriever.llm_provider.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_variations_llm_error(self, retriever):
        """Test LLM error during variation generation"""
        # Mock LLM error
        retriever.llm_provider.generate.side_effect = Exception("LLM API error")

        # Execute
        variations, cost_usd, cache_hit = await retriever._generate_variations_with_cost(
            "test query"
        )

        # Assert - should return empty variations on error
        assert variations == []
        assert cost_usd == 0.0
        assert cache_hit is False

    @pytest.mark.asyncio
    async def test_cache_write_after_generation(self, retriever, mock_redis):
        """Test Redis cache write after successful generation"""
        # Mock LLM response
        llm_response = "1. First variation\n2. Second variation"
        from app.services.llm.base import LLMResponse
        mock_response = LLMResponse(
            text=llm_response,
            tokens_input=50,
            tokens_output=30,
            model="openai/gpt-4o-mini",
            latency_ms=100
        )
        retriever.llm_provider.generate = Mock(return_value=mock_response)

        # Execute
        await retriever._generate_variations_with_cost("test query")

        # Assert cache write was called
        assert mock_redis.setex.called

    # ========================================
    # Test: Parallel Search Execution
    # ========================================

    @pytest.mark.asyncio
    async def test_parallel_search_success(self, retriever, mock_hybrid_search, sample_search_results):
        """Test successful parallel search execution"""
        # Mock search responses
        from app.schemas.search import SearchResponse

        mock_response = SearchResponse(
            success=True,
            query="test",
            total_results=2,
            returned_results=2,
            results=sample_search_results,
            processing_time_ms=100,
            filters_applied={}
        )

        mock_hybrid_search.search.return_value = mock_response

        # Execute
        queries = ["query 1", "query 2", "query 3"]
        results = await retriever._parallel_search(
            queries=queries,
            top_k=10,
            filters=None,
            enable_reranking=False,
        )

        # Assert
        assert len(results) == 3  # All queries returned results
        assert mock_hybrid_search.search.call_count == 3

    @pytest.mark.asyncio
    async def test_parallel_search_partial_failure(self, retriever, mock_hybrid_search, sample_search_results):
        """Test parallel search with partial failures"""
        from app.schemas.search import SearchResponse

        call_count = {'count': 0}

        # First search succeeds, second fails, third succeeds
        def search_side_effect(*args, **kwargs):
            call_count['count'] += 1
            if call_count['count'] == 2:
                raise Exception("Search error")
            return SearchResponse(
                success=True,
                query="test",
                total_results=2,
                returned_results=2,
                results=sample_search_results,
                processing_time_ms=100,
                filters_applied={}
            )

        mock_hybrid_search.search = Mock(side_effect=search_side_effect)

        # Execute
        queries = ["query 1", "query 2", "query 3"]
        results = await retriever._parallel_search(
            queries=queries,
            top_k=10,
            filters=None,
            enable_reranking=False,
        )

        # Assert - The search_single function catches exceptions and returns []
        # So we get 3 results: [results, [], results]
        # The implementation filters out exceptions, not empty lists
        assert len(results) == 3
        assert len(results[1]) == 0  # Middle result should be empty due to error

    # ========================================
    # Test: Result Fusion
    # ========================================

    def test_fuse_results_frequency_ranking(self, retriever):
        """Test frequency-based fusion ranking"""
        doc_id = str(uuid4())

        # Create results where chunk 1 appears in 2 queries, chunk 2 in 1 query
        results_query1 = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.8,
                document_name="doc1.pdf",
                snippet="test 1",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
        ]

        results_query2 = [
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,  # Same chunk appears again
                relevance_score=0.7,
                document_name="doc1.pdf",
                snippet="test 1",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                chunk_index=2,
                relevance_score=0.9,
                document_name="doc1.pdf",
                snippet="test 2",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
        ]

        # Execute fusion
        fused = retriever._fuse_results([results_query1, results_query2], top_k=10)

        # Assert
        assert len(fused) == 2
        # Chunk 1 should rank higher due to frequency (appears in 2 queries)
        assert fused[0].chunk_index == 1
        assert fused[0].relevance_score > fused[1].relevance_score

    def test_fuse_results_empty_input(self, retriever):
        """Test fusion with empty results"""
        fused = retriever._fuse_results([], top_k=10)
        assert fused == []

    def test_fuse_results_top_k_limit(self, retriever):
        """Test fusion respects top_k limit"""
        doc_id = str(uuid4())

        # Create 5 unique chunks
        results = []
        for i in range(5):
            results.append([
                SearchResultItem(
                    document_id=doc_id,
                    chunk_index=i,
                    relevance_score=0.8,
                    document_name="doc1.pdf",
                    snippet=f"test {i}",
                    chunk_position=None,
                    extraction_quality=0.9,
                    document_type="application/pdf",
                    created_at=datetime.now(timezone.utc)
                )
            ])

        # Execute with top_k=3
        fused = retriever._fuse_results(results, top_k=3)

        # Assert
        assert len(fused) == 3

    # ========================================
    # Test: End-to-End Retrieval
    # ========================================

    @pytest.mark.asyncio
    async def test_retrieve_success(self, retriever, mock_hybrid_search, sample_search_results):
        """Test successful end-to-end retrieval with Multi-Query RAG"""
        from app.schemas.search import SearchResponse
        from app.services.llm.base import LLMResponse

        # Mock LLM response for variations
        mock_llm_response = LLMResponse(
            text="1. First variation\n2. Second variation",
            tokens_input=50,
            tokens_output=30,
            model="openai/gpt-4o-mini",
            latency_ms=100
        )
        retriever.llm_provider.generate = Mock(return_value=mock_llm_response)

        # Mock search responses
        mock_response = SearchResponse(
            success=True,
            query="test",
            total_results=2,
            returned_results=2,
            results=sample_search_results,
            processing_time_ms=100,
            filters_applied={}
        )
        mock_hybrid_search.search.return_value = mock_response

        # Execute
        response = await retriever.retrieve(
            query="machine learning algorithms",
            client_id=1,
            top_k=10,
            filters=None,
            enable_reranking=False,
        )

        # Assert
        assert isinstance(response, MultiQueryResponse)
        assert response.success is True
        assert response.multi_query_metadata is not None
        assert len(response.multi_query_metadata.query_variations) == 2
        assert response.multi_query_metadata.cost_usd > 0
        assert response.multi_query_metadata.num_queries_searched == 3  # Original + 2 variations

    @pytest.mark.asyncio
    async def test_retrieve_fallback_on_error(self, retriever, mock_hybrid_search, sample_search_results):
        """Test graceful fallback to standard search on error"""
        from app.schemas.search import SearchResponse

        # Mock LLM error
        retriever.llm_provider.generate.side_effect = Exception("LLM error")

        # Mock fallback search response
        mock_response = SearchResponse(
            success=True,
            query="test",
            total_results=2,
            returned_results=2,
            results=sample_search_results,
            processing_time_ms=100,
            filters_applied={}
        )
        mock_hybrid_search.search.return_value = mock_response

        # Execute
        response = await retriever.retrieve(
            query="test query",
            client_id=1,
            top_k=10,
            filters=None,
            enable_reranking=False,
        )

        # Assert - should fallback to standard search
        assert response.success is True
        assert mock_hybrid_search.search.called

    @pytest.mark.asyncio
    async def test_retrieve_disabled_fallback(self, retriever, mock_hybrid_search, mock_settings):
        """Test retrieval when Multi-Query is disabled"""
        from app.schemas.search import SearchResponse

        # Disable Multi-Query
        mock_settings.MULTI_QUERY_ENABLED = False
        retriever.settings = mock_settings

        # Mock fallback search
        mock_response = SearchResponse(
            success=True,
            query="test",
            total_results=0,
            returned_results=0,
            results=[],
            processing_time_ms=50,
            filters_applied={}
        )
        mock_hybrid_search.search.return_value = mock_response

        # Execute
        response = await retriever.retrieve(
            query="test query",
            client_id=1,
            top_k=10,
            filters=None,
            enable_reranking=False,
        )

        # Assert - should use fallback
        assert response.success is True
        mock_hybrid_search.search.assert_called_once()

    # ========================================
    # Test: Prompt Building
    # ========================================

    def test_build_variation_prompt(self, retriever):
        """Test prompt building for LLM"""
        prompt = retriever._build_variation_prompt("machine learning algorithms")

        assert "machine learning algorithms" in prompt
        assert "2" in prompt  # num_variations
        assert "alternative" in prompt.lower()

    # ========================================
    # Test: Variation Parsing
    # ========================================

    def test_parse_variations_numbered_list(self, retriever):
        """Test parsing numbered list variations"""
        llm_response = """1. First variation here
2. Second variation here"""

        variations = retriever._parse_variations(llm_response)

        assert len(variations) == 2
        assert variations[0] == "First variation here"
        assert variations[1] == "Second variation here"

    def test_parse_variations_with_extra_text(self, retriever):
        """Test parsing with extra explanatory text"""
        llm_response = """Here are the variations:
1. First variation
2. Second variation
These are semantically similar."""

        variations = retriever._parse_variations(llm_response)

        assert len(variations) == 2
        assert "First variation" in variations[0]
        assert "Second variation" in variations[1]

    def test_parse_variations_limit(self, retriever):
        """Test parsing respects NUM_VARIATIONS limit"""
        llm_response = """1. First
2. Second
3. Third
4. Fourth"""

        retriever.settings.MULTI_QUERY_NUM_VARIATIONS = 2
        variations = retriever._parse_variations(llm_response)

        assert len(variations) == 2  # Only first 2

    # ========================================
    # Test: Factory Function
    # ========================================

    def test_factory_function(self, mock_hybrid_search):
        """Test get_multi_query_retriever factory function"""
        with patch('app.services.search.multi_query_retriever.get_llm_provider'):
            retriever = get_multi_query_retriever(
                hybrid_search_service=mock_hybrid_search,
                redis_client=None,
            )

            assert isinstance(retriever, MultiQueryRetriever)
            assert retriever.hybrid_search == mock_hybrid_search

    # ========================================
    # Test: Edge Cases
    # ========================================

    @pytest.mark.asyncio
    async def test_retrieve_with_empty_query(self, retriever, mock_hybrid_search):
        """Test retrieval with empty query string"""
        from app.schemas.search import SearchResponse

        mock_response = SearchResponse(
            success=True,
            query="",
            total_results=0,
            returned_results=0,
            results=[],
            processing_time_ms=10,
            filters_applied={}
        )
        mock_hybrid_search.search.return_value = mock_response

        response = await retriever.retrieve(
            query="",
            client_id=1,
            top_k=10,
            filters=None,
            enable_reranking=False,
        )

        assert response.success is True
        assert len(response.results) == 0

    @pytest.mark.asyncio
    async def test_retrieve_with_very_long_query(self, retriever, mock_hybrid_search):
        """Test retrieval with very long query (> 1000 chars)"""
        from app.schemas.search import SearchResponse
        from app.services.llm.base import LLMResponse

        long_query = "machine learning " * 100  # ~1700 chars

        # Mock LLM response
        mock_llm_response = LLMResponse(
            text="1. ML algorithms\n2. Machine learning techniques",
            tokens_input=200,
            tokens_output=20,
            model="openai/gpt-4o-mini",
            latency_ms=150
        )
        retriever.llm_provider.generate = Mock(return_value=mock_llm_response)

        mock_response = SearchResponse(
            success=True,
            query=long_query,
            total_results=0,
            returned_results=0,
            results=[],
            processing_time_ms=50,
            filters_applied={}
        )
        mock_hybrid_search.search.return_value = mock_response

        response = await retriever.retrieve(
            query=long_query,
            client_id=1,
            top_k=10,
            filters=None,
            enable_reranking=False,
        )

        assert response.success is True

    def test_parse_variations_with_no_numbered_list(self, retriever):
        """Test parsing when LLM returns non-numbered format"""
        llm_response = """Here are some variations:
        - What is machine learning?
        - How does ML work?"""

        variations = retriever._parse_variations(llm_response)

        # Should extract what it can or return empty
        assert isinstance(variations, list)

    def test_parse_variations_with_empty_response(self, retriever):
        """Test parsing when LLM returns empty string"""
        variations = retriever._parse_variations("")

        assert variations == []

    def test_fuse_results_all_zero_scores(self, retriever):
        """Test fusion when all results have zero relevance scores"""
        doc_id = str(uuid4())

        results = [[
            SearchResultItem(
                document_id=doc_id,
                chunk_index=1,
                relevance_score=0.0,
                document_name="doc1.pdf",
                snippet="test",
                chunk_position=None,
                extraction_quality=0.9,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]]

        fused = retriever._fuse_results(results, top_k=10)

        assert len(fused) == 1
        assert fused[0].relevance_score >= 0.0

    def test_fuse_results_with_identical_chunks(self, retriever):
        """Test fusion when multiple queries return identical chunks"""
        doc_id = str(uuid4())

        # Same chunk appears in all 3 queries with different scores
        chunk = SearchResultItem(
            document_id=doc_id,
            chunk_index=1,
            relevance_score=0.8,
            document_name="doc1.pdf",
            snippet="identical content",
            chunk_position=None,
            extraction_quality=0.9,
            document_type="application/pdf",
            created_at=datetime.now(timezone.utc)
        )

        results = [[chunk], [chunk], [chunk]]

        fused = retriever._fuse_results(results, top_k=10)

        # Should deduplicate and boost score due to frequency
        assert len(fused) == 1
        assert fused[0].relevance_score > 0.8  # Boosted by frequency

    @pytest.mark.asyncio
    async def test_retrieve_with_unicode_query(self, retriever, mock_hybrid_search):
        """Test retrieval with Unicode characters in query"""
        from app.schemas.search import SearchResponse
        from app.services.llm.base import LLMResponse

        unicode_query = "¿Qué es machine learning? 机器学习"

        mock_llm_response = LLMResponse(
            text="1. What is ML?\n2. Machine learning explanation",
            tokens_input=30,
            tokens_output=15,
            model="openai/gpt-4o-mini",
            latency_ms=100
        )
        retriever.llm_provider.generate = Mock(return_value=mock_llm_response)

        mock_response = SearchResponse(
            success=True,
            query=unicode_query,
            total_results=0,
            returned_results=0,
            results=[],
            processing_time_ms=50,
            filters_applied={}
        )
        mock_hybrid_search.search.return_value = mock_response

        response = await retriever.retrieve(
            query=unicode_query,
            client_id=1,
            top_k=10,
            filters=None,
            enable_reranking=False,
        )

        assert response.success is True
