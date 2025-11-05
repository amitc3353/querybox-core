"""
Quote Matching Service for Step 11.2 - Chain-of-Verification

Performs exact quote matching using fuzzy string matching (RapidFuzz).
Finds supporting quotes in passages for each proposition.

Based on technical documentation Section 10 (Code Snippets).
"""
from typing import List, Tuple
from rapidfuzz import fuzz
import tiktoken

from app.schemas.verification import QuoteMatch, Passage
from app.utils.text_matching import extract_sentences, normalize_text
from app.core.config import settings
from app.core.logging import get_logger
from app.core.verification_profiles import get_active_profile, VerificationProfile

logger = get_logger(__name__)


class QuoteMatchingService:
    """
    Exact quote matching service using fuzzy string matching.

    Finds supporting quotes in passages for each proposition using
    RapidFuzz for efficient similarity computation.

    Performance targets:
    - Complexity: O(P * S * T) where P=passages, S=sentences, T=tokens
    - Time: 50-100ms per proposition
    """

    def __init__(self, similarity_threshold: float = None, profile: VerificationProfile = None):
        """
        Initialize quote matching service.

        Args:
            similarity_threshold: Minimum similarity score (0-1) for matches.
                                 If not provided, uses active profile threshold.
            profile: VerificationProfile to use (loads from settings if not provided)
        """
        # Load profile if not provided
        self.profile = profile or get_active_profile()

        # Use explicit threshold or profile threshold
        self.similarity_threshold = similarity_threshold or self.profile.quote_similarity_threshold

        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        logger.info(
            f"QuoteMatchingService initialized with threshold={self.similarity_threshold} "
            f"(verification_level={self.profile.level.value})"
        )

    def find_supporting_quotes(
        self,
        proposition: str,
        passages: List[Passage],
        top_k: int = None
    ) -> List[QuoteMatch]:
        """
        Find exact quotes supporting the proposition.

        Algorithm:
        1. Extract all sentences from passages
        2. Normalize proposition and sentences (lowercase, strip)
        3. Compute fuzzy match score for each sentence
        4. Return top-k matches above similarity threshold

        Args:
            proposition: Atomic claim to verify (e.g., "Paris is the capital of France")
            passages: List of retrieved passages from search
            top_k: Number of matches to return (default from settings)

        Returns:
            List of QuoteMatch objects sorted by similarity score (descending)

        Complexity:
            O(P * S * T) where:
            - P = number of passages (typically 5-10)
            - S = sentences per passage (typically 10-20)
            - T = token-level comparison (typically ~100 tokens)

            Average case: ~5,000 operations
            Time: 50-100ms with RapidFuzz optimizations

        Example:
            >>> proposition = "Paris is the capital of France"
            >>> passages = [Passage(id="p1", content="Paris is France's capital.", ...)]
            >>> matches = service.find_supporting_quotes(proposition, passages)
            >>> matches[0].similarity_score >= 0.85
            True
        """
        top_k = top_k or self.profile.quote_max_matches_per_proposition

        logger.debug(
            f"Starting quote matching for proposition: {proposition[:50]}...",
            extra={
                "proposition_length": len(proposition),
                "passages_count": len(passages),
                "threshold": self.similarity_threshold,
            }
        )

        # Normalize proposition
        normalized_prop = normalize_text(proposition)

        # Collect all candidate sentences from passages
        all_matches = []

        for passage in passages:
            # Extract sentences with boundary detection
            sentences = extract_sentences(passage.content)

            for idx, sentence in enumerate(sentences):
                # Normalize sentence
                normalized_sentence = normalize_text(sentence)

                # Skip if too short (likely not a complete claim)
                if len(normalized_sentence.split()) < 3:
                    continue

                # Compute fuzzy match score (0-100)
                # Using token_sort_ratio: balances word-level matching with order sensitivity
                # Better than partial_ratio for paraphrasing while maintaining high precision
                similarity_score = fuzz.token_sort_ratio(
                    normalized_prop,
                    normalized_sentence
                ) / 100.0  # Normalize to 0-1

                # Only keep matches above threshold
                if similarity_score >= self.similarity_threshold:
                    # Calculate token positions for highlighting
                    start_pos, end_pos = self._find_sentence_positions(
                        passage.content,
                        sentence
                    )

                    quote_match = QuoteMatch(
                        passage_id=passage.id,
                        passage_score=passage.rerank_score,  # From Step 10.2
                        matched_text=sentence.strip(),
                        similarity_score=round(similarity_score, 3),
                        start_pos=start_pos,
                        end_pos=end_pos,
                        sentence_index=idx
                    )

                    all_matches.append(quote_match)

                    logger.debug(
                        "Quote match found",
                        extra={
                            "passage_id": passage.id,
                            "similarity": similarity_score,
                            "match_preview": sentence[:50] + "...",
                        }
                    )

        # Sort by similarity score (descending), then by passage score
        sorted_matches = sorted(
            all_matches,
            key=lambda x: (x.similarity_score, x.passage_score),
            reverse=True
        )

        # Return top-k matches
        top_matches = sorted_matches[:top_k]

        logger.debug(
            "Quote matching completed",
            extra={
                "total_candidates": len(all_matches),
                "top_k_returned": len(top_matches),
                "best_score": top_matches[0].similarity_score if top_matches else 0,
            }
        )

        return top_matches

    def _find_sentence_positions(
        self,
        passage_content: str,
        sentence: str
    ) -> Tuple[int, int]:
        """
        Find start and end character positions of sentence in passage.

        Args:
            passage_content: Full passage text
            sentence: Sentence to locate

        Returns:
            (start_pos, end_pos) tuple for highlighting

        Example:
            >>> positions = service._find_sentence_positions(
            ...     "Hello world. Goodbye world.",
            ...     "Hello world."
            ... )
            >>> positions
            (0, 12)
        """
        try:
            start_pos = passage_content.index(sentence)
            end_pos = start_pos + len(sentence)
            return start_pos, end_pos
        except ValueError:
            # Sentence not found exactly (shouldn't happen, but handle gracefully)
            logger.warning(
                "Could not find sentence position in passage",
                extra={"sentence_preview": sentence[:30]}
            )
            return 0, len(sentence)

    def health_check(self) -> dict:
        """
        Health check for quote matching service.

        Returns:
            dict: Health status with component info

        Example:
            >>> health = service.health_check()
            >>> health['status']
            'healthy'
        """
        try:
            # Test basic functionality
            test_proposition = "Test proposition"
            test_passage = Passage(
                id="test",
                content="Test proposition example",
                document_id="doc1",
                chunk_index=0,
                rerank_score=1.0
            )

            # Try to match
            matches = self.find_supporting_quotes(
                test_proposition,
                [test_passage],
                top_k=1
            )

            return {
                "status": "healthy",
                "threshold": self.similarity_threshold,
                "test_match_found": len(matches) > 0
            }

        except Exception as e:
            logger.error(f"Quote matching health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
