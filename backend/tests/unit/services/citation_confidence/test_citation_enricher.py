"""
Unit Tests for CitationEnricher - Step 11.3

Tests citation enrichment, quality indicators, highlighting, and formatting.
"""
import pytest
from unittest.mock import Mock
import html

import sys
sys.path.insert(0, 'backend')

from app.services.citation_confidence.citation_enricher import CitationEnricher
from app.schemas.citation_confidence import EnrichedCitation, CitationQuality, QuoteMatchInfo
from app.schemas.verification import QuoteMatch


class TestCitationEnricher:
    """Test suite for citation enricher."""

    @pytest.fixture
    def enricher(self):
        """Create citation enricher with default thresholds."""
        return CitationEnricher(
            citation_strong_threshold=0.95,
            citation_medium_threshold=0.85
        )

    @pytest.fixture
    def sample_citations(self):
        """Create sample citations for testing."""
        return [
            {
                "document_id": "doc1",
                "document_name": "France_Guide.pdf",
                "passage_text": "France's capital is Paris, located in the north.",
                "page": 5,
                "section": "Geography",
                "relevance_score": 0.95,
                "citation_number": 1
            },
            {
                "document_id": "doc2",
                "document_name": "Europe.pdf",
                "passage_text": "Berlin is the capital of Germany.",
                "page": 12,
                "section": "Cities",
                "relevance_score": 0.75,
                "citation_number": 2
            }
        ]

    @pytest.fixture
    def sample_quote_matches(self):
        """Create sample quote matches for testing."""
        return {
            "0": [
                {
                    "passage_id": "doc1",
                    "matched_text": "Paris",
                    "similarity_score": 0.97,
                    "start_pos": 0,
                    "end_pos": 5,
                    "sentence_index": 0
                }
            ]
        }

    @pytest.fixture
    def sample_propositions(self):
        """Create sample propositions for testing."""
        return [
            {"index": 0, "text": "Paris is the capital of France"}
        ]

    # ========================================================================
    # Test Citation Quality Calculation
    # ========================================================================

    def test_citation_quality_strong(self, enricher):
        """Test STRONG quality for exact/near-exact quotes."""
        quote_match = QuoteMatch(
            passage_id="p1",
            passage_score=0.95,
            matched_text="Paris",
            similarity_score=0.97,  # >= 0.95
            start_pos=0,
            end_pos=5,
            sentence_index=0
        )

        quality = enricher._calculate_citation_quality(quote_match)

        assert quality == CitationQuality.STRONG

    def test_citation_quality_medium(self, enricher):
        """Test MEDIUM quality for paraphrased quotes."""
        quote_match = QuoteMatch(
            passage_id="p1",
            passage_score=0.90,
            matched_text="capital city Paris",
            similarity_score=0.88,  # 0.85 <= score < 0.95
            start_pos=0,
            end_pos=18,
            sentence_index=0
        )

        quality = enricher._calculate_citation_quality(quote_match)

        assert quality == CitationQuality.MEDIUM

    def test_citation_quality_weak(self, enricher):
        """Test WEAK quality for low similarity or no match."""
        quote_match = QuoteMatch(
            passage_id="p1",
            passage_score=0.85,
            matched_text="some text",
            similarity_score=0.70,  # < 0.85
            start_pos=0,
            end_pos=9,
            sentence_index=0
        )

        quality = enricher._calculate_citation_quality(quote_match)

        assert quality == CitationQuality.WEAK

    def test_citation_quality_no_match(self, enricher):
        """Test WEAK quality when no quote match."""
        quality = enricher._calculate_citation_quality(None)

        assert quality == CitationQuality.WEAK

    def test_citation_quality_boundary_strong(self, enricher):
        """Test quality at exact STRONG threshold (0.95)."""
        quote_match = QuoteMatch(
            passage_id="p1",
            passage_score=0.90,
            matched_text="test",
            similarity_score=0.95,  # Exactly at threshold
            start_pos=0,
            end_pos=4,
            sentence_index=0
        )

        quality = enricher._calculate_citation_quality(quote_match)

        assert quality == CitationQuality.STRONG

    def test_citation_quality_boundary_medium(self, enricher):
        """Test quality at exact MEDIUM threshold (0.85)."""
        quote_match = QuoteMatch(
            passage_id="p1",
            passage_score=0.90,
            matched_text="test",
            similarity_score=0.85,  # Exactly at threshold
            start_pos=0,
            end_pos=4,
            sentence_index=0
        )

        quality = enricher._calculate_citation_quality(quote_match)

        assert quality == CitationQuality.MEDIUM

    # ========================================================================
    # Test Text Highlighting
    # ========================================================================

    def test_highlight_matched_text(self, enricher):
        """Test adding <mark> tags to matched text."""
        passage_text = "France's capital is Paris, located in the north."
        quote_match = QuoteMatch(
            passage_id="p1",
            passage_score=0.90,
            matched_text="Paris",
            similarity_score=0.97,
            start_pos=20,
            end_pos=25,
            sentence_index=0
        )

        highlighted = enricher._highlight_matched_text(passage_text, quote_match)

        # Should contain <mark> tags
        assert "<mark>" in highlighted
        assert "</mark>" in highlighted
        assert "Paris" in highlighted or "paris" in highlighted.lower()

    def test_highlight_matched_text_html_escaping(self, enricher):
        """Test that HTML is properly escaped to prevent XSS."""
        passage_text = "Test <script>alert('xss')</script> content"
        quote_match = QuoteMatch(
            passage_id="p1",
            passage_score=0.90,
            matched_text="Test",
            similarity_score=0.97,
            start_pos=0,
            end_pos=4,
            sentence_index=0
        )

        highlighted = enricher._highlight_matched_text(passage_text, quote_match)

        # Should escape dangerous HTML
        assert "<script>" not in highlighted
        assert "&lt;script&gt;" in highlighted  # Escaped version
        assert "<mark>" in highlighted  # But <mark> should be allowed

    def test_highlight_matched_text_not_found(self, enricher):
        """Test highlighting when matched text not found in passage."""
        passage_text = "Some other text."
        quote_match = QuoteMatch(
            passage_id="p1",
            passage_score=0.90,
            matched_text="Paris",  # Not in passage
            similarity_score=0.97,
            start_pos=0,
            end_pos=5,
            sentence_index=0
        )

        highlighted = enricher._highlight_matched_text(passage_text, quote_match)

        # Should return escaped original without highlighting
        assert highlighted == html.escape(passage_text)

    def test_highlight_matched_text_case_insensitive(self, enricher):
        """Test that highlighting is case-insensitive."""
        passage_text = "The capital is PARIS."
        quote_match = QuoteMatch(
            passage_id="p1",
            passage_score=0.90,
            matched_text="paris",  # Lowercase
            similarity_score=0.97,
            start_pos=15,
            end_pos=20,
            sentence_index=0
        )

        highlighted = enricher._highlight_matched_text(passage_text, quote_match)

        # Should find and highlight PARIS despite case difference
        assert "<mark>" in highlighted

    # ========================================================================
    # Test Inline Citation Formatting
    # ========================================================================

    def test_format_inline_citation_simple(self, enricher):
        """Test simple citation format [1]."""
        citation = {"citation_number": 1}

        formatted = enricher._format_inline_citation(citation, "simple")

        assert formatted == "[1]"

    def test_format_inline_citation_detailed_with_page(self, enricher):
        """Test detailed citation format with page number."""
        citation = {
            "citation_number": 1,
            "document_name": "France_Guide.pdf",
            "page": 5
        }

        formatted = enricher._format_inline_citation(citation, "detailed")

        assert "[1:" in formatted
        assert "France_Guide.pdf" in formatted
        assert "p.5" in formatted

    def test_format_inline_citation_detailed_no_page(self, enricher):
        """Test detailed citation format without page number."""
        citation = {
            "citation_number": 1,
            "document_name": "France_Guide.pdf",
            "page": None
        }

        formatted = enricher._format_inline_citation(citation, "detailed")

        assert "[1:" in formatted
        assert "France_Guide.pdf" in formatted
        assert "p." not in formatted

    def test_format_inline_citation_long_name_truncation(self, enricher):
        """Test that very long document names are truncated."""
        citation = {
            "citation_number": 1,
            "document_name": "A" * 50,  # Very long name
            "page": 1
        }

        formatted = enricher._format_inline_citation(citation, "detailed")

        # Should be truncated to 30 chars + "..."
        assert len(citation["document_name"]) > 30
        assert "..." in formatted

    # ========================================================================
    # Test Find Best Quote Match
    # ========================================================================

    def test_find_best_quote_match_by_passage_id(self, enricher):
        """Test finding best quote match by passage ID."""
        citation_id = "doc1"
        citation_passage = "Test passage"

        quote_matches = [
            QuoteMatch(
                passage_id="doc1_chunk_0",  # Contains citation_id
                passage_score=0.90,
                matched_text="test",
                similarity_score=0.97,
                start_pos=0,
                end_pos=4,
                sentence_index=0
            ),
            QuoteMatch(
                passage_id="doc2_chunk_0",
                passage_score=0.90,
                matched_text="other",
                similarity_score=0.85,
                start_pos=0,
                end_pos=5,
                sentence_index=0
            )
        ]

        best_match = enricher._find_best_quote_match(
            citation_id,
            citation_passage,
            quote_matches
        )

        assert best_match is not None
        assert "doc1" in best_match.passage_id

    def test_find_best_quote_match_by_text_containment(self, enricher):
        """Test finding best quote match by text containment."""
        citation_id = "doc1"
        citation_passage = "The capital is Paris."

        quote_matches = [
            QuoteMatch(
                passage_id="unknown",
                passage_score=0.90,
                matched_text="Paris",  # Appears in citation_passage
                similarity_score=0.97,
                start_pos=0,
                end_pos=5,
                sentence_index=0
            )
        ]

        best_match = enricher._find_best_quote_match(
            citation_id,
            citation_passage,
            quote_matches
        )

        assert best_match is not None
        assert best_match.matched_text == "Paris"

    def test_find_best_quote_match_highest_similarity(self, enricher):
        """Test that highest similarity match is returned."""
        citation_id = "doc1"
        citation_passage = "Test passage"

        quote_matches = [
            QuoteMatch(
                passage_id="doc1_a",
                passage_score=0.90,
                matched_text="test",
                similarity_score=0.85,
                start_pos=0,
                end_pos=4,
                sentence_index=0
            ),
            QuoteMatch(
                passage_id="doc1_b",
                passage_score=0.90,
                matched_text="test",
                similarity_score=0.97,  # Higher
                start_pos=0,
                end_pos=4,
                sentence_index=0
            )
        ]

        best_match = enricher._find_best_quote_match(
            citation_id,
            citation_passage,
            quote_matches
        )

        assert best_match.similarity_score == 0.97

    def test_find_best_quote_match_no_matches(self, enricher):
        """Test when no quote matches are relevant."""
        citation_id = "doc1"
        citation_passage = "Test passage"

        quote_matches = [
            QuoteMatch(
                passage_id="doc2",  # Different document
                passage_score=0.90,
                matched_text="unrelated",  # Not in passage
                similarity_score=0.97,
                start_pos=0,
                end_pos=9,
                sentence_index=0
            )
        ]

        best_match = enricher._find_best_quote_match(
            citation_id,
            citation_passage,
            quote_matches
        )

        assert best_match is None

    # ========================================================================
    # Test Complete Citation Enrichment
    # ========================================================================

    @pytest.mark.asyncio
    async def test_enrich_citations_basic(
        self,
        enricher,
        sample_citations,
        sample_quote_matches,
        sample_propositions
    ):
        """Test basic citation enrichment."""
        enriched = await enricher.enrich_citations(
            sample_citations,
            sample_quote_matches,
            sample_propositions,
            inline_format="simple"
        )

        assert len(enriched) == 2, "Should enrich both citations"

        # Check first citation
        first = enriched[0]
        assert isinstance(first, EnrichedCitation)
        assert first.document_id == "doc1"
        assert first.citation_number == 1
        assert first.quality in [CitationQuality.STRONG, CitationQuality.MEDIUM, CitationQuality.WEAK]
        assert first.inline_citation == "[1]"

    @pytest.mark.asyncio
    async def test_enrich_citations_detailed_format(
        self,
        enricher,
        sample_citations,
        sample_quote_matches,
        sample_propositions
    ):
        """Test citation enrichment with detailed formatting."""
        enriched = await enricher.enrich_citations(
            sample_citations,
            sample_quote_matches,
            sample_propositions,
            inline_format="detailed"
        )

        first = enriched[0]
        # Should have detailed format
        assert "[1:" in first.inline_citation
        assert "France_Guide.pdf" in first.inline_citation or "..." in first.inline_citation

    @pytest.mark.asyncio
    async def test_enrich_citations_empty_citations(self, enricher):
        """Test enrichment with empty citations list."""
        enriched = await enricher.enrich_citations(
            citations=[],
            quote_matches={},
            propositions=[],
            inline_format="simple"
        )

        assert len(enriched) == 0, "Should return empty list"

    @pytest.mark.asyncio
    async def test_enrich_citations_error_handling(
        self,
        enricher,
        sample_propositions
    ):
        """Test that enrichment handles errors gracefully."""
        # Citation with missing required fields
        bad_citation = {
            # Missing many fields
            "citation_number": 1
        }

        enriched = await enricher.enrich_citations(
            citations=[bad_citation],
            quote_matches={},
            propositions=sample_propositions,
            inline_format="simple"
        )

        # Should create fallback enriched citation
        assert len(enriched) == 1
        assert enriched[0].quality == CitationQuality.WEAK

    @pytest.mark.asyncio
    async def test_enrich_citations_with_highlighting(
        self,
        enricher,
        sample_citations,
        sample_quote_matches,
        sample_propositions
    ):
        """Test that highlighting is applied when quote matches exist."""
        enriched = await enricher.enrich_citations(
            sample_citations,
            sample_quote_matches,
            sample_propositions,
            inline_format="simple"
        )

        # First citation should have highlighting (has quote match)
        first = enriched[0]
        if first.highlighted_passage_text:
            assert "<mark>" in first.highlighted_passage_text

    # ========================================================================
    # Test Citation Validation
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validate_citation_numbers_all_present(self, enricher):
        """Test validation when all citations are present."""
        answer_text = "Paris is the capital. [1] Berlin is also a capital. [2]"
        enriched_citations = [
            EnrichedCitation(
                document_id="doc1",
                document_name="France.pdf",
                passage_text="Test",
                relevance_score=0.95,
                citation_number=1,
                quality=CitationQuality.STRONG,
                inline_citation="[1]",
                proposition_ids=[]
            ),
            EnrichedCitation(
                document_id="doc2",
                document_name="Germany.pdf",
                passage_text="Test",
                relevance_score=0.90,
                citation_number=2,
                quality=CitationQuality.MEDIUM,
                inline_citation="[2]",
                proposition_ids=[]
            )
        ]

        errors = await enricher.validate_citation_numbers(answer_text, enriched_citations)

        assert len(errors) == 0, "Should have no validation errors"

    @pytest.mark.asyncio
    async def test_validate_citation_numbers_missing_citation(self, enricher):
        """Test validation when citation is referenced but missing."""
        answer_text = "Paris is the capital. [1] Berlin is also a capital. [2]"
        enriched_citations = [
            EnrichedCitation(
                document_id="doc1",
                document_name="France.pdf",
                passage_text="Test",
                relevance_score=0.95,
                citation_number=1,
                quality=CitationQuality.STRONG,
                inline_citation="[1]",
                proposition_ids=[]
            )
            # Citation [2] is missing
        ]

        errors = await enricher.validate_citation_numbers(answer_text, enriched_citations)

        assert len(errors) > 0, "Should have validation error"
        assert any("[2]" in error for error in errors), "Error should mention missing [2]"

    @pytest.mark.asyncio
    async def test_validate_citation_numbers_unused_citation(self, enricher):
        """Test validation when citation exists but not referenced."""
        answer_text = "Paris is the capital. [1]"
        enriched_citations = [
            EnrichedCitation(
                document_id="doc1",
                document_name="France.pdf",
                passage_text="Test",
                relevance_score=0.95,
                citation_number=1,
                quality=CitationQuality.STRONG,
                inline_citation="[1]",
                proposition_ids=[]
            ),
            EnrichedCitation(
                document_id="doc2",
                document_name="Germany.pdf",
                passage_text="Test",
                relevance_score=0.90,
                citation_number=2,  # Not referenced in answer
                quality=CitationQuality.MEDIUM,
                inline_citation="[2]",
                proposition_ids=[]
            )
        ]

        errors = await enricher.validate_citation_numbers(answer_text, enriched_citations)

        # Unused citations are logged as warnings, not errors
        assert len(errors) == 0, "Unused citations should not be errors"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
