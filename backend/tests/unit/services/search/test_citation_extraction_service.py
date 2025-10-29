"""
Unit Tests for Citation Extraction Service (Step 10.3)

Tests cover:
- Citation extraction from search results
- Citation metadata retrieval
- Sentence boundary detection
- Citation scoring algorithm
- Citation highlighting
- Error handling and graceful degradation
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from app.services.search.citation_extraction_service import (
    CitationExtractionService,
    get_citation_service
)
from app.schemas.search import (
    SearchResultItem,
    SearchResultItemWithCitations,
    Citation,
    CitationPosition
)


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = Mock(spec=Session)
    return session


@pytest.fixture
def citation_service(mock_db_session):
    """Create CitationExtractionService instance with mock database"""
    return CitationExtractionService(mock_db_session)


@pytest.fixture
def sample_search_results():
    """Create sample search results for testing"""
    return [
        SearchResultItem(
            document_id="doc-123",
            document_name="Test Document.pdf",
            relevance_score=0.92,
            snippet="RAG systems improve accuracy by 40% according to studies.",
            chunk_index=5,
            chunk_position={"start": 1000, "end": 2000}
        ),
        SearchResultItem(
            document_id="doc-456",
            document_name="Research Paper.pdf",
            relevance_score=0.85,
            snippet="Machine learning models achieve 95% precision.",
            chunk_index=3
        )
    ]


class TestCitationExtractionServiceInit:
    """Test service initialization"""

    def test_service_initialization(self, mock_db_session):
        """Test service initializes correctly"""
        service = CitationExtractionService(mock_db_session)

        assert service.db is mock_db_session
        assert service.nlp is None  # Lazy loaded
        assert service.enable_cache is True
        assert service.cache_ttl == 900

    def test_get_citation_service_factory(self, mock_db_session):
        """Test factory function creates service"""
        service = get_citation_service(mock_db_session)

        assert isinstance(service, CitationExtractionService)
        assert service.db is mock_db_session


class TestExtractCitations:
    """Test main citation extraction method"""

    def test_extract_citations_empty_results(self, citation_service):
        """Test extraction with empty results returns empty list"""
        results = citation_service.extract_citations([])

        assert results == []

    @patch('app.services.search.citation_extraction_service.CitationExtractionService._fetch_citation_metadata')
    def test_extract_citations_no_chunk_ids(self, mock_fetch, citation_service):
        """Test extraction with results but no chunk IDs"""
        search_results = [
            SearchResultItem(
                document_id="doc-123",
                document_name="Test.pdf",
                relevance_score=0.9,
                chunk_index=None  # No chunk_index
            )
        ]

        results = citation_service.extract_citations(search_results)

        # Should return results without citations
        assert len(results) == 1
        assert isinstance(results[0], SearchResultItemWithCitations)
        assert len(results[0].citations) == 0

    @patch('app.services.search.citation_extraction_service.CitationExtractionService._extract_citations_from_chunk')
    @patch('app.services.search.citation_extraction_service.CitationExtractionService._fetch_citation_metadata')
    def test_extract_citations_basic(self, mock_fetch, mock_extract, citation_service, sample_search_results):
        """Test basic citation extraction"""
        # Mock metadata
        mock_fetch.return_value = {
            "doc-123": {
                "chunk_text": "RAG systems improve accuracy by 40%.",
                "page_number": 5,
                "section_heading": "Results",
                "start_position": 1000,
                "end_position": 2000
            }
        }

        # Mock extracted citations
        mock_extract.return_value = [
            Citation(
                text="RAG systems improve accuracy by 40%",
                page=5,
                section="Results",
                position=CitationPosition(start=1000, end=1036),
                confidence=0.9,
                source_context="Page 5, Results"
            )
        ]

        results = citation_service.extract_citations(sample_search_results, citation_limit=3)

        assert len(results) > 0
        assert isinstance(results[0], SearchResultItemWithCitations)

    def test_extract_citations_graceful_degradation(self, citation_service, sample_search_results):
        """Test graceful degradation on error"""
        # Force an error by not mocking dependencies
        results = citation_service.extract_citations(sample_search_results)

        # Should still return results, possibly without citations
        assert len(results) == len(sample_search_results)
        assert all(isinstance(r, SearchResultItemWithCitations) for r in results)


class TestFetchCitationMetadata:
    """Test citation metadata retrieval"""

    def test_fetch_empty_chunk_ids(self, citation_service):
        """Test fetching with empty chunk IDs returns empty dict"""
        result = citation_service._fetch_citation_metadata([])

        assert result == {}

    def test_fetch_metadata_database_query(self, citation_service, mock_db_session):
        """Test database query for citation metadata"""
        chunk_ids = ["chunk-1", "chunk-2"]

        # Mock database response
        mock_row = Mock()
        mock_row.id = "chunk-1"
        mock_row.chunk_text = "Test text"
        mock_row.page_number = 5
        mock_row.section_heading = "Section 1"
        mock_row.subsection_heading = None
        mock_row.start_position = 100
        mock_row.end_position = 200
        mock_row.chunk_index = 1
        mock_row.document_name = "test.pdf"
        mock_row.total_pages = 10

        mock_result = Mock()
        mock_result.fetchall.return_value = [mock_row]
        mock_db_session.execute.return_value = mock_result

        metadata = citation_service._fetch_citation_metadata(chunk_ids)

        assert "chunk-1" in metadata
        assert metadata["chunk-1"]["page_number"] == 5
        assert metadata["chunk-1"]["section_heading"] == "Section 1"
        assert metadata["chunk-1"]["chunk_text"] == "Test text"


class TestExtractCitationsFromChunk:
    """Test citation extraction from individual chunks"""

    def test_extract_from_empty_text(self, citation_service):
        """Test extraction from empty text returns empty list"""
        citations = citation_service._extract_citations_from_chunk(
            chunk_text="",
            chunk_metadata={},
            citation_limit=3
        )

        assert citations == []

    def test_extract_fallback_without_spacy(self, citation_service):
        """Test fallback extraction when spaCy not available"""
        chunk_text = "This is a test sentence. Another sentence here. Third sentence."
        chunk_metadata = {
            "page_number": 1,
            "section_heading": "Introduction",
            "start_position": 0
        }

        citations = citation_service._extract_citations_from_chunk(
            chunk_text=chunk_text,
            chunk_metadata=chunk_metadata,
            citation_limit=2
        )

        # Fallback should still extract something
        assert isinstance(citations, list)

    @patch('app.services.search.citation_extraction_service.CitationExtractionService._get_nlp_model')
    def test_extract_with_spacy_model(self, mock_nlp, citation_service):
        """Test extraction with spaCy model"""
        # Mock spaCy model and doc
        mock_sent = Mock()
        mock_sent.text = "RAG systems improve accuracy by 40%."
        mock_sent.start_char = 0
        mock_sent.__len__ = Mock(return_value=7)  # word count
        mock_sent.split.return_value = ["RAG", "systems", "improve", "accuracy", "by", "40%"]

        # Mock token for scoring
        mock_token = Mock()
        mock_token.like_num = True
        mock_token.pos_ = "VERB"
        # Return a fresh iterator each time __iter__ is called
        mock_sent.__iter__ = lambda: iter([mock_token])

        mock_doc = Mock()
        mock_doc.sents = [mock_sent]

        mock_nlp_instance = Mock()
        mock_nlp_instance.return_value = mock_doc
        mock_nlp.return_value = mock_nlp_instance

        chunk_text = "RAG systems improve accuracy by 40%."
        chunk_metadata = {
            "page_number": 5,
            "section_heading": "Results",
            "start_position": 1000
        }

        citations = citation_service._extract_citations_from_chunk(
            chunk_text=chunk_text,
            chunk_metadata=chunk_metadata,
            citation_limit=3
        )

        assert isinstance(citations, list)


class TestCitationScoring:
    """Test citation worthiness scoring"""

    def test_calculate_score_with_numbers(self, citation_service):
        """Test scoring gives higher score to sentences with numbers"""
        # Mock sentence with numbers
        mock_sent = Mock()
        mock_token_num = Mock()
        mock_token_num.like_num = True
        mock_token_num.pos_ = "NUM"
        # Return a fresh iterator each time __iter__ is called
        mock_sent.__iter__ = lambda: iter([mock_token_num])
        mock_sent.text = "Accuracy improved by 40%"
        mock_sent.split.return_value = ["Accuracy", "improved", "by", "40%"]

        score = citation_service._calculate_citation_score(mock_sent)

        assert score >= 0.3  # Should have number bonus

    def test_calculate_score_with_verb(self, citation_service):
        """Test scoring gives bonus for verbs"""
        mock_sent = Mock()
        mock_token_verb = Mock()
        mock_token_verb.like_num = False
        mock_token_verb.pos_ = "VERB"
        # Return a fresh iterator each time __iter__ is called
        mock_sent.__iter__ = lambda: iter([mock_token_verb])
        mock_sent.text = "The system improves performance"
        mock_sent.split.return_value = ["The", "system", "improves", "performance"]

        score = citation_service._calculate_citation_score(mock_sent)

        assert score >= 0.2  # Should have verb bonus


class TestSourceContextBuilding:
    """Test source context string building"""

    def test_build_context_with_page_and_section(self, citation_service):
        """Test building context with both page and section"""
        context = citation_service._build_source_context(
            page=5,
            section="Results"
        )

        assert "Page 5" in context
        assert "Results" in context

    def test_build_context_page_only(self, citation_service):
        """Test building context with page only"""
        context = citation_service._build_source_context(
            page=5,
            section=None
        )

        assert "Page 5" in context
        assert context == "Page 5"

    def test_build_context_section_only(self, citation_service):
        """Test building context with section only"""
        context = citation_service._build_source_context(
            page=None,
            section="Introduction"
        )

        assert "Introduction" in context
        assert "Page" not in context

    def test_build_context_neither(self, citation_service):
        """Test building context with neither page nor section"""
        context = citation_service._build_source_context(
            page=None,
            section=None
        )

        assert context == "Unknown source"

    def test_build_context_truncates_long_section(self, citation_service):
        """Test long section headings are truncated"""
        long_section = "A" * 100

        context = citation_service._build_source_context(
            page=1,
            section=long_section
        )

        # Should be truncated with ellipsis
        assert len(context) < len(long_section) + 20


class TestCitationHighlighting:
    """Test citation highlighting in snippets"""

    def test_highlight_single_citation(self, citation_service):
        """Test highlighting single citation"""
        snippet = "RAG systems improve accuracy by 40% according to studies."
        citations = [
            Citation(
                text="improve accuracy by 40%",
                page=5,
                section="Results",
                position=CitationPosition(start=100, end=123),
                confidence=0.9,
                source_context="Page 5, Results"
            )
        ]

        highlighted = citation_service._highlight_citations(snippet, citations)

        assert "<mark" in highlighted
        assert "data-page='5'" in highlighted
        assert "improve accuracy by 40%" in highlighted

    def test_highlight_empty_snippet(self, citation_service):
        """Test highlighting empty snippet returns empty"""
        highlighted = citation_service._highlight_citations("", [])

        assert highlighted == ""

    def test_highlight_citation_not_in_snippet(self, citation_service):
        """Test highlighting when citation text not in snippet"""
        snippet = "This is some text"
        citations = [
            Citation(
                text="Not in snippet",
                page=1,
                section="Test",
                position=CitationPosition(start=0, end=10),
                confidence=0.5,
                source_context="Page 1"
            )
        ]

        highlighted = citation_service._highlight_citations(snippet, citations)

        # Should return original snippet unchanged
        assert highlighted == snippet

    def test_highlight_multiple_citations(self, citation_service):
        """Test highlighting multiple citations"""
        snippet = "First citation here. Second citation there."
        citations = [
            Citation(
                text="First citation",
                page=1,
                section="S1",
                position=CitationPosition(start=0, end=14),
                confidence=0.9,
                source_context="Page 1"
            ),
            Citation(
                text="Second citation",
                page=2,
                section="S2",
                position=CitationPosition(start=21, end=36),
                confidence=0.8,
                source_context="Page 2"
            )
        ]

        highlighted = citation_service._highlight_citations(snippet, citations)

        # Should have two marks
        assert highlighted.count("<mark") == 2
        assert "data-page='1'" in highlighted
        assert "data-page='2'" in highlighted


class TestErrorHandling:
    """Test error handling and graceful degradation"""

    def test_metadata_fetch_error_returns_partial(self, citation_service, mock_db_session):
        """Test metadata fetch continues on error"""
        chunk_ids = ["chunk-1"]

        # Mock database to raise error
        mock_db_session.execute.side_effect = Exception("Database error")

        metadata = citation_service._fetch_citation_metadata(chunk_ids)

        # Should return empty dict instead of raising
        assert metadata == {}

    def test_extract_citations_handles_spacy_error(self, citation_service):
        """Test extraction handles spaCy errors gracefully"""
        chunk_text = "Test text"
        chunk_metadata = {"page_number": 1}

        # Should not raise, should use fallback
        citations = citation_service._extract_citations_from_chunk(
            chunk_text, chunk_metadata, 3
        )

        assert isinstance(citations, list)


class TestCachingBehavior:
    """Test caching behavior (currently disabled in sync mode)"""

    def test_fetch_from_cache_returns_empty(self, citation_service):
        """Test cache fetch returns empty in sync mode"""
        result = citation_service._fetch_from_cache(["chunk-1"])

        assert result == {}

    def test_cache_metadata_no_error(self, citation_service):
        """Test caching doesn't raise errors"""
        # Should complete without error
        citation_service._cache_metadata("chunk-1", {"test": "data"})


# Integration-style tests (require database setup)
@pytest.mark.integration
class TestCitationExtractionIntegration:
    """Integration tests (require database)"""

    @pytest.mark.skip(reason="Requires database setup")
    def test_end_to_end_citation_extraction(self):
        """Test complete citation extraction flow"""
        # This would require full database setup
        pass


# Performance tests
@pytest.mark.performance
class TestCitationExtractionPerformance:
    """Performance tests for citation extraction"""

    @pytest.mark.skip(reason="Performance test - run manually")
    def test_extraction_latency(self, citation_service):
        """Test citation extraction completes within target latency"""
        import time

        # Mock 10 search results
        results = [
            SearchResultItem(
                document_id=f"doc-{i}",
                document_name=f"Doc{i}.pdf",
                relevance_score=0.9,
                snippet="Test text" * 50,
                chunk_index=i
            )
            for i in range(10)
        ]

        start = time.time()
        citation_service.extract_citations(results, citation_limit=3)
        latency_ms = (time.time() - start) * 1000

        # Target: <100ms for 10 results
        assert latency_ms < 100, f"Latency {latency_ms}ms exceeds 100ms target"
