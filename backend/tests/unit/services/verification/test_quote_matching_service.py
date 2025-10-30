"""
Unit Tests for QuoteMatchingService - Step 11.2

Tests quote matching accuracy, performance, and edge cases.

Based on technical documentation Section 8 (Testing Approach).
"""
import pytest
from unittest.mock import Mock

import sys
sys.path.insert(0, 'backend')

from app.services.verification import QuoteMatchingService
from app.schemas.verification import Passage, QuoteMatch


class TestQuoteMatchingService:
    """Test suite for quote matching service."""

    @pytest.fixture
    def service(self):
        """Create quote matching service with default threshold."""
        return QuoteMatchingService(similarity_threshold=0.85)

    @pytest.fixture
    def service_low_threshold(self):
        """Create quote matching service with lower threshold for paraphrased testing."""
        return QuoteMatchingService(similarity_threshold=0.66)

    def test_quote_matching_exact_match(self, service_low_threshold):
        """Test exact quote matching with high similarity."""
        proposition = "The capital of France is Paris."

        passages = [
            Passage(
                id="p1",
                content="France's capital city is Paris, located in the north.",
                document_id="doc1",
                chunk_index=0,
                rerank_score=0.95
            ),
            Passage(
                id="p2",
                content="Berlin is the capital of Germany.",
                document_id="doc2",
                chunk_index=0,
                rerank_score=0.60
            )
        ]

        matches = service_low_threshold.find_supporting_quotes(proposition, passages)

        # Should find at least one match
        assert len(matches) >= 1, "Should find at least one matching quote"

        # Best match should be from passage 1
        assert matches[0].passage_id == "p1", "Best match should be from passage 1"

        # Similarity score should be above threshold (0.66 for paraphrased content)
        assert matches[0].similarity_score >= 0.66, f"Score {matches[0].similarity_score} < 0.66"

        # Should contain "Paris"
        assert "Paris" in matches[0].matched_text or "paris" in matches[0].matched_text.lower()

        # Should NOT match passage 2 (Berlin)
        assert all(m.passage_id != "p2" for m in matches), "Should not match Berlin passage"

    def test_quote_matching_paraphrase(self, service_low_threshold):
        """Test fuzzy matching for paraphrased content."""
        proposition = "Paris is the capital of France."

        passages = [
            Passage(
                id="p1",
                content="The capital city of France is known as Paris.",
                document_id="doc1",
                chunk_index=0,
                rerank_score=0.95
            )
        ]

        matches = service_low_threshold.find_supporting_quotes(proposition, passages)

        # Should find match despite paraphrase
        assert len(matches) >= 1, "Should match paraphrased content"
        assert matches[0].similarity_score >= 0.66, "Should have good similarity for paraphrased content"

    def test_quote_matching_no_matches(self, service):
        """Test when no quotes match above threshold."""
        proposition = "Tokyo is the capital of Japan."

        passages = [
            Passage(
                id="p1",
                content="Paris is the capital of France.",
                document_id="doc1",
                chunk_index=0,
                rerank_score=0.95
            )
        ]

        matches = service.find_supporting_quotes(proposition, passages)

        # Should return empty list (no matches)
        assert len(matches) == 0, "Should not find matches for unrelated content"

    def test_quote_matching_multiple_passages(self, service_low_threshold):
        """Test matching across multiple passages."""
        proposition = "Paris is the capital"

        passages = [
            Passage(
                id="p1",
                content="Paris is the capital of France.",
                document_id="doc1",
                chunk_index=0,
                rerank_score=0.95
            ),
            Passage(
                id="p2",
                content="The capital city Paris has many museums.",
                document_id="doc2",
                chunk_index=0,
                rerank_score=0.90
            ),
            Passage(
                id="p3",
                content="London is the capital of the UK.",
                document_id="doc3",
                chunk_index=0,
                rerank_score=0.85
            )
        ]

        matches = service_low_threshold.find_supporting_quotes(proposition, passages, top_k=5)

        # Should find matches from first two passages
        assert len(matches) >= 2, "Should find matches from multiple passages"

        # Matches should be sorted by similarity score (descending)
        scores = [m.similarity_score for m in matches]
        assert scores == sorted(scores, reverse=True), "Matches should be sorted by score"

    def test_quote_matching_top_k_limiting(self, service_low_threshold):
        """Test that top_k parameter limits results correctly."""
        proposition = "The city is beautiful"

        passages = [
            Passage(
                id=f"p{i}",
                content=f"The city is beautiful and historic. Sentence {i}.",
                document_id=f"doc{i}",
                chunk_index=0,
                rerank_score=0.90
            )
            for i in range(5)
        ]

        # Request only top 2 matches
        matches = service_low_threshold.find_supporting_quotes(proposition, passages, top_k=2)

        # Should return exactly 2 matches
        assert len(matches) == 2, f"Should return exactly 2 matches, got {len(matches)}"

    def test_quote_matching_positions(self, service_low_threshold):
        """Test that character positions are calculated correctly."""
        proposition = "Paris is the capital"

        passage_content = "Introduction. Paris is the capital of France. Conclusion."
        passages = [
            Passage(
                id="p1",
                content=passage_content,
                document_id="doc1",
                chunk_index=0,
                rerank_score=0.95
            )
        ]

        matches = service_low_threshold.find_supporting_quotes(proposition, passages)

        assert len(matches) >= 1, "Should find match"

        match = matches[0]

        # Verify positions
        assert match.start_pos >= 0, "Start position should be non-negative"
        assert match.end_pos > match.start_pos, "End position should be after start"

        # Extract matched text using positions
        extracted = passage_content[match.start_pos:match.end_pos]
        assert extracted == match.matched_text, "Positions should extract correct text"

    def test_quote_matching_empty_proposition(self, service):
        """Test handling of empty proposition."""
        proposition = ""

        passages = [
            Passage(
                id="p1",
                content="Some content here.",
                document_id="doc1",
                chunk_index=0,
                rerank_score=0.95
            )
        ]

        matches = service.find_supporting_quotes(proposition, passages)

        # Should handle gracefully and return empty
        assert len(matches) == 0, "Empty proposition should return no matches"

    def test_quote_matching_empty_passages(self, service):
        """Test handling of empty passage list."""
        proposition = "Paris is the capital of France"
        passages = []

        matches = service.find_supporting_quotes(proposition, passages)

        # Should return empty list
        assert len(matches) == 0, "Empty passages should return no matches"

    def test_quote_matching_sentence_filtering(self, service):
        """Test that very short sentences are filtered out."""
        proposition = "Important claim"

        passages = [
            Passage(
                id="p1",
                content="Yes. No. Important claim is true. OK.",
                document_id="doc1",
                chunk_index=0,
                rerank_score=0.95
            )
        ]

        matches = service.find_supporting_quotes(proposition, passages)

        # Should match the longer sentence, not "Yes", "No", "OK"
        if matches:
            assert len(matches[0].matched_text.split()) >= 3, \
                "Matched text should have at least 3 words"

    def test_health_check(self, service):
        """Test health check functionality."""
        health = service.health_check()

        assert health["status"] == "healthy", "Service should be healthy"
        assert "threshold" in health, "Health check should report threshold"
        assert health["threshold"] == 0.85, "Threshold should match initialization"

    def test_quote_matching_case_insensitivity(self, service_low_threshold):
        """Test that matching is case-insensitive."""
        proposition = "PARIS IS THE CAPITAL"

        passages = [
            Passage(
                id="p1",
                content="paris is the capital of france.",
                document_id="doc1",
                chunk_index=0,
                rerank_score=0.95
            )
        ]

        matches = service_low_threshold.find_supporting_quotes(proposition, passages)

        # Should match despite case differences
        assert len(matches) >= 1, "Should match regardless of case"
        assert matches[0].similarity_score >= 0.66, "Case differences and paraphrasing should still match"


# Performance test (optional, can be slow)
@pytest.mark.slow
class TestQuoteMatchingPerformance:
    """Performance tests for quote matching."""

    def test_quote_matching_performance_target(self):
        """Test that quote matching meets <100ms target."""
        import time

        # Use lower threshold for paraphrased content
        service = QuoteMatchingService(similarity_threshold=0.66)
        proposition = "The capital of France is Paris."

        # Create 10 passages with varying content
        passages = [
            Passage(
                id=f"p{i}",
                content=f"Sentence {i}. France's capital is Paris. More text here. " * 5,
                document_id=f"doc{i}",
                chunk_index=0,
                rerank_score=0.90
            )
            for i in range(10)
        ]

        # Measure time
        start_time = time.time()
        matches = service.find_supporting_quotes(proposition, passages)
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"\nQuote matching took {elapsed_ms:.1f}ms for 10 passages")

        # Should complete in <100ms (target from documentation)
        # Note: May vary by machine, so we use 200ms as upper bound for CI
        assert elapsed_ms < 200, f"Quote matching took {elapsed_ms:.1f}ms, target <100ms"
        assert len(matches) > 0, "Should find matches"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
