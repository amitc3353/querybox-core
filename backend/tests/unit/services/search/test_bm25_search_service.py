"""
Unit Tests for BM25 Search Service
Tests BM25SearchService without external dependencies
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from app.services.search.bm25_search_service import (
    BM25SearchService,
    get_bm25_search_service,
)
from app.schemas.search import (
    SearchFilters,
    SearchResultItem,
)
from app.core.config import settings


class TestBM25SearchService:
    """Test BM25SearchService"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        mock_db = Mock()
        mock_db.query = Mock()
        mock_db.commit = Mock()
        mock_db.rollback = Mock()
        return mock_db

    @pytest.fixture
    def service(self, mock_db):
        """Create BM25 search service instance"""
        return BM25SearchService(db=mock_db)

    @pytest.fixture
    def sample_corpus_stats(self):
        """Sample corpus statistics"""
        return {
            'total_chunks': 1000,
            'avg_chunk_length': 200.0
        }

    @pytest.fixture
    def sample_chunks(self):
        """Sample chunk data from database"""
        doc_id = uuid4()
        return [
            Mock(
                id=uuid4(),
                document_id=doc_id,
                chunk_text="Machine learning is a subset of artificial intelligence",
                chunk_index=0,
                start_position=0,
                end_position=100,
                document_name="test.pdf",
                mime_type="application/pdf",
                created_at=datetime.now(timezone.utc),
                extraction_quality=0.9
            ),
            Mock(
                id=uuid4(),
                document_id=doc_id,
                chunk_text="Deep learning uses neural networks for pattern recognition",
                chunk_index=1,
                start_position=100,
                end_position=200,
                document_name="test.pdf",
                mime_type="application/pdf",
                created_at=datetime.now(timezone.utc),
                extraction_quality=0.9
            ),
            Mock(
                id=uuid4(),
                document_id=doc_id,
                chunk_text="Natural language processing enables machines to understand text",
                chunk_index=2,
                start_position=200,
                end_position=300,
                document_name="test.pdf",
                mime_type="application/pdf",
                created_at=datetime.now(timezone.utc),
                extraction_quality=0.9
            )
        ]

    # Tests for _parse_query
    def test_parse_query_lowercase(self, service):
        """Test query is lowercased"""
        terms = service._parse_query("Machine Learning")
        assert terms == ["machine", "learning"]

    def test_parse_query_removes_special_chars(self, service):
        """Test special characters are removed"""
        terms = service._parse_query("test@email.com & data-science!")
        assert all(term.isalnum() for term in terms)
        assert "test" in terms
        assert "email" in terms
        assert "com" in terms

    def test_parse_query_removes_duplicates(self, service):
        """Test duplicate terms are removed"""
        terms = service._parse_query("test test data test")
        assert terms.count("test") == 1
        assert terms.count("data") == 1

    def test_parse_query_skips_single_char(self, service):
        """Test single-character terms are skipped"""
        terms = service._parse_query("a b test i o data")
        assert "a" not in terms
        assert "b" not in terms
        assert "i" not in terms
        assert "test" in terms
        assert "data" in terms

    def test_parse_query_empty_string(self, service):
        """Test empty query returns empty list"""
        terms = service._parse_query("")
        assert terms == []

    def test_parse_query_whitespace_only(self, service):
        """Test whitespace-only query returns empty list"""
        terms = service._parse_query("   ")
        assert terms == []

    def test_parse_query_special_chars_only(self, service):
        """Test special characters only query returns empty list"""
        terms = service._parse_query("!@#$%^&*()")
        assert terms == []

    # Tests for _get_corpus_stats
    def test_get_corpus_stats_queries_database(self, service, mock_db):
        """Test corpus stats queries database correctly"""
        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = Mock(total_chunks=1000, avg_chunk_length=5000)
        mock_db.query.return_value = mock_query

        stats = service._get_corpus_stats()

        assert stats['total_chunks'] == 1000
        assert stats['avg_chunk_length'] == 1000.0  # 5000 chars / 5 chars per word

    def test_get_corpus_stats_caches_result(self, service, mock_db):
        """Test corpus stats are cached"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = Mock(total_chunks=1000, avg_chunk_length=5000)
        mock_db.query.return_value = mock_query

        # Call twice
        stats1 = service._get_corpus_stats()
        stats2 = service._get_corpus_stats()

        # Should only query DB once (cached)
        assert mock_db.query.call_count == 1
        assert stats1 == stats2

    def test_get_corpus_stats_handles_none_values(self, service, mock_db):
        """Test corpus stats handles None values from database"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = Mock(total_chunks=None, avg_chunk_length=None)
        mock_db.query.return_value = mock_query

        stats = service._get_corpus_stats()

        # Should use defaults to avoid division by zero
        assert stats['total_chunks'] == 1
        assert stats['avg_chunk_length'] == 200.0  # 1000 chars / 5

    # Tests for _calculate_bm25_score
    def test_calculate_bm25_score_simple(self, service):
        """Test BM25 score calculation for simple case"""
        # Cache corpus stats to avoid DB query
        service._corpus_stats_cache = {'total_chunks': 1000, 'avg_chunk_length': 200}

        query_terms = ["machine", "learning"]
        chunk_text = "machine learning is awesome"
        chunk_length = 4
        avg_chunk_length = 10.0

        score = service._calculate_bm25_score(query_terms, chunk_text, chunk_length, avg_chunk_length)

        # Score should be positive for matching terms
        assert score > 0

    def test_calculate_bm25_score_no_match(self, service):
        """Test BM25 score is 0 for no matching terms"""
        # Cache corpus stats to avoid DB query
        service._corpus_stats_cache = {'total_chunks': 1000, 'avg_chunk_length': 200}

        query_terms = ["database", "sql"]
        chunk_text = "machine learning is awesome"
        chunk_length = 4
        avg_chunk_length = 10.0

        score = service._calculate_bm25_score(query_terms, chunk_text, chunk_length, avg_chunk_length)

        assert score == 0.0

    def test_calculate_bm25_score_multiple_occurrences(self, service):
        """Test BM25 score increases with term frequency"""
        # Cache corpus stats to avoid DB query
        service._corpus_stats_cache = {'total_chunks': 1000, 'avg_chunk_length': 200}

        query_terms = ["test"]
        chunk_text1 = "test data"
        chunk_text2 = "test test test data"  # More occurrences

        score1 = service._calculate_bm25_score(query_terms, chunk_text1, 2, 10.0)
        score2 = service._calculate_bm25_score(query_terms, chunk_text2, 4, 10.0)

        # More term occurrences should increase score
        assert score2 > score1

    def test_calculate_bm25_score_length_normalization(self, service):
        """Test BM25 scoring applies length normalization"""
        # Cache corpus stats to avoid DB query
        service._corpus_stats_cache = {'total_chunks': 1000, 'avg_chunk_length': 200}

        query_terms = ["test"]
        short_text = "test data"  # Short doc with 1 occurrence
        long_text = "test " * 10 + "data"  # Longer doc with more test occurrences

        score_short = service._calculate_bm25_score(query_terms, short_text, 2, 10.0)
        score_long = service._calculate_bm25_score(query_terms, long_text, 11, 10.0)

        # Both should have positive scores (length normalization applied)
        assert score_short > 0
        assert score_long > 0

    def test_calculate_bm25_score_case_insensitive(self, service):
        """Test BM25 scoring is case-insensitive"""
        # Cache corpus stats to avoid DB query
        service._corpus_stats_cache = {'total_chunks': 1000, 'avg_chunk_length': 200}

        query_terms = ["machine", "learning"]
        chunk_text1 = "machine learning"
        chunk_text2 = "MACHINE LEARNING"
        chunk_text3 = "Machine Learning"

        score1 = service._calculate_bm25_score(query_terms, chunk_text1, 2, 10.0)
        score2 = service._calculate_bm25_score(query_terms, chunk_text2, 2, 10.0)
        score3 = service._calculate_bm25_score(query_terms, chunk_text3, 2, 10.0)

        # All should have same score
        assert score1 == score2 == score3

    # Tests for _fetch_candidate_chunks
    def test_fetch_candidate_chunks_returns_list(self, service, mock_db):
        """Test fetching candidates returns list of dicts"""
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        candidates = service._fetch_candidate_chunks(["test"], None, 100)

        assert isinstance(candidates, list)

    def test_fetch_candidate_chunks_builds_tsquery(self, service, mock_db, sample_chunks):
        """Test candidate chunks builds correct tsquery"""
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_chunks
        mock_db.query.return_value = mock_query

        candidates = service._fetch_candidate_chunks(["machine", "learning"], None, 100)

        # Should call query methods
        mock_db.query.assert_called_once()
        mock_query.join.assert_called()
        mock_query.filter.assert_called()
        mock_query.limit.assert_called_with(100)

    def test_fetch_candidate_chunks_escapes_special_chars(self, service, mock_db):
        """Test candidate chunks escapes single quotes in terms"""
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        # Terms with single quotes should be escaped
        candidates = service._fetch_candidate_chunks(["test's"], None, 100)

        assert isinstance(candidates, list)

    # Tests for _generate_snippet
    def test_generate_snippet_highlights_terms(self, service):
        """Test snippet highlights query terms"""
        chunk_text = "This is a test document about machine learning"
        query_terms = ["machine", "learning"]

        snippet = service._generate_snippet(chunk_text, query_terms)

        # Should highlight terms with **
        assert "**machine**" in snippet or "**learning**" in snippet

    def test_generate_snippet_adds_ellipsis(self, service):
        """Test snippet adds ellipsis"""
        chunk_text = "This is a test"
        query_terms = ["test"]

        snippet = service._generate_snippet(chunk_text, query_terms)

        assert snippet.startswith("...")
        assert snippet.endswith("...")

    def test_generate_snippet_empty_text(self, service):
        """Test snippet handles empty text"""
        chunk_text = ""
        query_terms = ["test"]

        snippet = service._generate_snippet(chunk_text, query_terms)

        assert snippet == ""

    def test_generate_snippet_no_terms_found(self, service):
        """Test snippet when no query terms found in text"""
        chunk_text = "This is a document about data science"
        query_terms = ["machine", "learning"]

        snippet = service._generate_snippet(chunk_text, query_terms)

        # Should still return snippet (from beginning)
        assert len(snippet) > 0
        assert snippet.startswith("...")

    def test_generate_snippet_limits_length(self, service):
        """Test snippet respects max length"""
        chunk_text = "A" * 500
        query_terms = ["test"]

        snippet = service._generate_snippet(chunk_text, query_terms, max_length=100)

        # Should be limited to max_length
        assert len(snippet) <= 110  # max_length + "..." + margin

    def test_generate_snippet_normalizes_whitespace(self, service):
        """Test snippet normalizes whitespace"""
        chunk_text = "This  is    a    test    document"
        query_terms = ["test"]

        snippet = service._generate_snippet(chunk_text, query_terms)

        # Should not have multiple consecutive spaces
        assert "  " not in snippet.replace("...", "")

    # Tests for _normalize_scores
    def test_normalize_scores_to_0_1_range(self, service):
        """Test scores are normalized to 0.0-1.0 range"""
        results = [
            {'relevance_score': 10.0},
            {'relevance_score': 5.0},
            {'relevance_score': 2.0}
        ]

        normalized = service._normalize_scores(results)

        # Max score should be 1.0
        assert normalized[0]['relevance_score'] == 1.0
        # Others should be proportional
        assert 0.0 < normalized[1]['relevance_score'] < 1.0
        assert 0.0 < normalized[2]['relevance_score'] < normalized[1]['relevance_score']

    def test_normalize_scores_empty_list(self, service):
        """Test normalizing empty list returns empty list"""
        results = []
        normalized = service._normalize_scores(results)
        assert normalized == []

    def test_normalize_scores_single_result(self, service):
        """Test normalizing single result"""
        results = [{'relevance_score': 5.0}]
        normalized = service._normalize_scores(results)

        # Single result should be normalized to 1.0
        assert normalized[0]['relevance_score'] == 1.0

    def test_normalize_scores_zero_max(self, service):
        """Test normalizing when max score is zero"""
        results = [
            {'relevance_score': 0.0},
            {'relevance_score': 0.0}
        ]
        normalized = service._normalize_scores(results)

        # Should return unchanged
        assert all(r['relevance_score'] == 0.0 for r in normalized)

    # Tests for _convert_to_result_items
    def test_convert_to_result_items(self, service):
        """Test converting dicts to SearchResultItem objects"""
        results = [
            {
                'document_id': str(uuid4()),
                'document_name': "test.pdf",
                'relevance_score': 0.85,
                'snippet': "...test snippet...",
                'chunk_index': 0,
                'chunk_position': {'start': 0, 'end': 100},
                'extraction_quality': 0.9,
                'document_type': "application/pdf",
                'created_at': datetime.now(timezone.utc)
            }
        ]

        items = service._convert_to_result_items(results)

        assert len(items) == 1
        assert isinstance(items[0], SearchResultItem)
        assert items[0].document_name == "test.pdf"
        assert items[0].relevance_score == 0.85

    def test_convert_to_result_items_empty(self, service):
        """Test converting empty list"""
        results = []
        items = service._convert_to_result_items(results)

        assert items == []

    # Tests for search (integration)
    def test_search_returns_results(self, service, mock_db, sample_chunks):
        """Test search returns SearchResultItem list"""
        # Mock corpus stats
        service._corpus_stats_cache = {'total_chunks': 1000, 'avg_chunk_length': 200}

        # Mock candidate chunks query
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_chunks
        mock_db.query.return_value = mock_query

        results = service.search("machine learning", None, 10, 0)

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, SearchResultItem) for r in results)

    def test_search_empty_query_returns_empty(self, service, mock_db):
        """Test empty query returns empty results"""
        results = service.search("", None, 10, 0)
        assert results == []

    def test_search_whitespace_query_returns_empty(self, service, mock_db):
        """Test whitespace-only query returns empty results"""
        results = service.search("   ", None, 10, 0)
        assert results == []

    def test_search_special_chars_only_returns_empty(self, service, mock_db):
        """Test special characters only query returns empty results"""
        results = service.search("!@#$%", None, 10, 0)
        assert results == []

    def test_search_no_candidates_returns_empty(self, service, mock_db):
        """Test search with no candidates returns empty"""
        service._corpus_stats_cache = {'total_chunks': 1000, 'avg_chunk_length': 200}

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        results = service.search("nonexistent", None, 10, 0)
        assert results == []

    def test_search_scores_are_sorted_descending(self, service, mock_db, sample_chunks):
        """Test search results are sorted by score descending"""
        service._corpus_stats_cache = {'total_chunks': 1000, 'avg_chunk_length': 200}

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_chunks
        mock_db.query.return_value = mock_query

        results = service.search("machine learning", None, 10, 0)

        # Scores should be descending
        scores = [r.relevance_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_pagination(self, service, mock_db, sample_chunks):
        """Test search applies pagination correctly"""
        service._corpus_stats_cache = {'total_chunks': 1000, 'avg_chunk_length': 200}

        # Return 3 chunks
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_chunks
        mock_db.query.return_value = mock_query

        # Request limit=2, offset=1
        results = service.search("machine learning", None, 2, 1)

        # Should return 2 results (skipping first)
        assert len(results) == 2

    def test_search_with_filters(self, service, mock_db, sample_chunks):
        """Test search with filters"""
        service._corpus_stats_cache = {'total_chunks': 1000, 'avg_chunk_length': 200}

        filters = SearchFilters(
            document_types=["application/pdf"],
            min_quality=0.8
        )

        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = sample_chunks
        mock_db.query.return_value = mock_query

        results = service.search("machine learning", filters, 10, 0)

        # Should call filter multiple times (for filters)
        assert mock_query.filter.call_count >= 2

    # Tests for _apply_filters
    def test_apply_filters_document_types(self, service):
        """Test applying document type filter"""
        mock_query = Mock()

        filters = SearchFilters(document_types=["application/pdf"])
        filtered = service._apply_filters(mock_query, filters)

        # Should call filter
        mock_query.filter.assert_called_once()

    def test_apply_filters_min_quality(self, service):
        """Test applying minimum quality filter"""
        mock_query = Mock()

        filters = SearchFilters(min_quality=0.8)
        filtered = service._apply_filters(mock_query, filters)

        # Should call filter
        mock_query.filter.assert_called_once()

    def test_apply_filters_date_range(self, service):
        """Test applying date range filters"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query

        filters = SearchFilters(
            date_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
            date_to=datetime(2025, 12, 31, tzinfo=timezone.utc)
        )
        filtered = service._apply_filters(mock_query, filters)

        # Should call filter at least once for date filters
        assert mock_query.filter.call_count >= 1

    def test_apply_filters_none(self, service):
        """Test applying no filters returns query unchanged"""
        mock_query = Mock()

        filtered = service._apply_filters(mock_query, None)

        # Should not call filter
        mock_query.filter.assert_not_called()
        assert filtered == mock_query

    # Tests for initialization
    def test_init_with_custom_k1_b(self):
        """Test initialization with custom BM25 parameters"""
        mock_db = Mock()
        service = BM25SearchService(db=mock_db, k1=2.0, b=0.5)

        assert service.k1 == 2.0
        assert service.b == 0.5

    def test_init_with_default_k1_b(self, service):
        """Test initialization uses settings defaults"""
        # Should use settings.BM25_K1 and settings.BM25_B
        assert service.k1 == settings.BM25_K1
        assert service.b == settings.BM25_B

    def test_init_corpus_cache_empty(self, service):
        """Test initialization sets empty corpus cache"""
        assert service._corpus_stats_cache is None

    def test_decimal_to_float_conversion_in_corpus_stats(self, service, mock_db):
        """Test Decimal values from database are converted to float"""
        from decimal import Decimal

        # Mock database query to return Decimal (as PostgreSQL does)
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = Mock(
            total_chunks=1000,
            avg_chunk_length=Decimal('5000.50')  # Decimal from database
        )
        mock_db.query.return_value = mock_query

        stats = service._get_corpus_stats()

        # Should convert Decimal to float
        assert isinstance(stats['avg_chunk_length'], float)
        assert stats['avg_chunk_length'] == 1000.1  # 5000.50 / 5.0
        # Verify it's not a Decimal
        assert not isinstance(stats['avg_chunk_length'], Decimal)

    def test_left_join_for_document_text(self, service, mock_db):
        """Test query uses LEFT JOIN (outerjoin) for DocumentText table"""
        # Mock query chain
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query  # LEFT JOIN
        mock_query.filter.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        # Execute fetch candidates
        service._fetch_candidate_chunks(["test"], None, 100)

        # Verify outerjoin was called (for LEFT JOIN with DocumentText)
        mock_query.outerjoin.assert_called()

    def test_avg_chunk_length_character_to_word_conversion(self, service, mock_db):
        """Test average chunk length is correctly converted from characters to words"""
        # Mock database query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = Mock(
            total_chunks=500,
            avg_chunk_length=2500  # 2500 characters
        )
        mock_db.query.return_value = mock_query

        stats = service._get_corpus_stats()

        # Should divide by 5.0 to convert chars to words
        assert stats['avg_chunk_length'] == 500.0  # 2500 / 5.0 = 500 words
        assert stats['total_chunks'] == 500


class TestGetBM25SearchService:
    """Test get_bm25_search_service factory function"""

    def test_get_bm25_search_service_returns_instance(self):
        """Test factory returns BM25SearchService instance"""
        mock_db = Mock()
        service = get_bm25_search_service(db=mock_db)

        assert service is not None
        assert isinstance(service, BM25SearchService)
        assert service.db == mock_db

    def test_get_bm25_search_service_creates_new_instance(self):
        """Test factory creates new instance each time"""
        mock_db1 = Mock()
        mock_db2 = Mock()

        service1 = get_bm25_search_service(db=mock_db1)
        service2 = get_bm25_search_service(db=mock_db2)

        # Should be different instances
        assert service1 is not service2
        assert service1.db == mock_db1
        assert service2.db == mock_db2
