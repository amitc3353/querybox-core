"""
Citation Enricher for Step 11.3

Enriches citations with quote match info and quality indicators.
Links quote matches to specific citations, calculates quality levels,
and adds highlighted matched text.
"""
from typing import List, Dict, Optional
import html
import re
import structlog

from app.schemas.verification import QuoteMatch
from app.schemas.citation_confidence import (
    EnrichedCitation,
    CitationQuality,
    QuoteMatchInfo
)
from app.core.config import settings

logger = structlog.get_logger(__name__)


class CitationEnricher:
    """
    Citation enrichment service.

    Enriches citations with:
    1. Quote match info (link to supporting quotes)
    2. Citation quality indicators (STRONG/MEDIUM/WEAK)
    3. Highlighted matched text
    4. Inline citation formatting
    5. Proposition mappings (which claims cite which docs)
    """

    def __init__(
        self,
        citation_strong_threshold: float = None,
        citation_medium_threshold: float = None
    ):
        """
        Initialize citation enricher with quality thresholds.

        Args:
            citation_strong_threshold: Threshold for STRONG quality (default 0.95)
            citation_medium_threshold: Threshold for MEDIUM quality (default 0.85)
        """
        self.strong_threshold = citation_strong_threshold or getattr(
            settings, 'CITATION_STRONG_THRESHOLD', 0.95
        )
        self.medium_threshold = citation_medium_threshold or getattr(
            settings, 'CITATION_MEDIUM_THRESHOLD', 0.85
        )

        logger.info(
            "CitationEnricher initialized",
            strong_threshold=self.strong_threshold,
            medium_threshold=self.medium_threshold
        )

    async def enrich_citations(
        self,
        citations: List[Dict],
        quote_matches: Dict[str, List[Dict]],
        propositions: List[Dict],
        inline_format: str = "simple"
    ) -> List[EnrichedCitation]:
        """
        Enrich citations with quote match info and quality indicators.

        Enhancements:
        1. Link quote matches to specific citations
        2. Calculate citation quality (strong/medium/weak)
        3. Add highlighted matched text
        4. Map citations to propositions (which claims cite which docs)
        5. Validate citation numbers [1], [2], etc.

        Args:
            citations: List of citation dicts from VerifiedAnswerResponse
            quote_matches: Dict mapping proposition_id → list of quote match dicts
            propositions: List of proposition dicts
            inline_format: "simple" ([1]) or "detailed" ([1: doc, p.5])

        Returns:
            List of EnrichedCitation objects

        Complexity: O(C * Q) where C = citations, Q = quote matches
        Time: ~50-100ms
        """
        logger.debug(
            "Enriching citations",
            total_citations=len(citations),
            total_propositions=len(propositions)
        )

        enriched_citations = []

        for citation in citations:
            try:
                # Convert quote matches from dict to QuoteMatch objects if needed
                all_quote_matches = []
                for prop_id, matches in quote_matches.items():
                    for match_data in matches:
                        if isinstance(match_data, dict):
                            try:
                                all_quote_matches.append(QuoteMatch(**match_data))
                            except Exception as e:
                                logger.warning(f"Failed to parse quote match: {e}")
                        else:
                            all_quote_matches.append(match_data)

                # Find best quote match for this citation
                # Match by passage_id or document_id
                citation_id = citation.get('document_id', '')
                citation_passage_text = citation.get('passage_text', '')

                best_quote_match = self._find_best_quote_match(
                    citation_id,
                    citation_passage_text,
                    all_quote_matches
                )

                # Calculate citation quality
                quality = self._calculate_citation_quality(best_quote_match)

                # Highlight matched text if quote match exists
                highlighted_text = None
                if best_quote_match and citation_passage_text:
                    highlighted_text = self._highlight_matched_text(
                        citation_passage_text,
                        best_quote_match
                    )

                # Build QuoteMatchInfo
                quote_match_info = None
                best_similarity = None
                is_exact_quote = False

                if best_quote_match:
                    quote_match_info = QuoteMatchInfo(
                        matched_text=best_quote_match.matched_text,
                        similarity_score=best_quote_match.similarity_score,
                        sentence_index=best_quote_match.sentence_index
                    )
                    best_similarity = best_quote_match.similarity_score
                    is_exact_quote = best_similarity >= self.strong_threshold

                # Format inline citation
                inline_citation = self._format_inline_citation(
                    citation,
                    inline_format
                )

                # Find which propositions cite this citation
                # For now, we'll leave this empty (would need citation tracking in answer generation)
                proposition_ids = []

                # Build enriched citation
                enriched_citation = EnrichedCitation(
                    # Core fields
                    document_id=citation.get('document_id', ''),
                    document_name=citation.get('document_name', ''),
                    passage_text=citation.get('passage_text', ''),
                    page=citation.get('page'),
                    section=citation.get('section'),
                    relevance_score=citation.get('relevance_score', 0.0),
                    citation_number=citation.get('citation_number', 0),
                    # Enrichment fields
                    quote_match=quote_match_info,
                    best_similarity=best_similarity,
                    is_exact_quote=is_exact_quote,
                    quality=quality,
                    highlighted_passage_text=highlighted_text,
                    inline_citation=inline_citation,
                    proposition_ids=proposition_ids
                )

                enriched_citations.append(enriched_citation)

            except Exception as e:
                logger.error(
                    "Failed to enrich citation",
                    citation_number=citation.get('citation_number'),
                    error=str(e)
                )
                # Fallback: Create basic enriched citation
                enriched_citations.append(EnrichedCitation(
                    document_id=citation.get('document_id', ''),
                    document_name=citation.get('document_name', ''),
                    passage_text=citation.get('passage_text', ''),
                    page=citation.get('page'),
                    section=citation.get('section'),
                    relevance_score=citation.get('relevance_score', 0.0),
                    citation_number=citation.get('citation_number', 0),
                    quality=CitationQuality.WEAK,
                    inline_citation=f"[{citation.get('citation_number', 0)}]",
                    proposition_ids=[]
                ))

        # Count quality distribution
        quality_counts = {
            "STRONG": sum(1 for c in enriched_citations if c.quality == CitationQuality.STRONG),
            "MEDIUM": sum(1 for c in enriched_citations if c.quality == CitationQuality.MEDIUM),
            "WEAK": sum(1 for c in enriched_citations if c.quality == CitationQuality.WEAK),
        }

        logger.debug(
            "Citation enrichment completed",
            total_citations=len(enriched_citations),
            **quality_counts
        )

        return enriched_citations

    def _find_best_quote_match(
        self,
        citation_id: str,
        citation_passage_text: str,
        all_quote_matches: List[QuoteMatch]
    ) -> Optional[QuoteMatch]:
        """
        Find best quote match for this citation.

        Match by:
        1. passage_id matching citation document_id
        2. matched_text appearing in citation_passage_text

        Args:
            citation_id: Citation document ID
            citation_passage_text: Citation passage text
            all_quote_matches: All quote matches

        Returns:
            Best QuoteMatch or None
        """
        # Filter matches related to this citation
        relevant_matches = []

        for qm in all_quote_matches:
            # Try to match by passage_id (may contain document_id)
            if citation_id in qm.passage_id or qm.passage_id in citation_id:
                relevant_matches.append(qm)
                continue

            # Try to match by text containment
            if qm.matched_text and citation_passage_text:
                if qm.matched_text.lower() in citation_passage_text.lower():
                    relevant_matches.append(qm)

        if not relevant_matches:
            return None

        # Return match with highest similarity score
        return max(relevant_matches, key=lambda qm: qm.similarity_score)

    def _calculate_citation_quality(
        self,
        quote_match: Optional[QuoteMatch]
    ) -> CitationQuality:
        """
        Calculate citation quality indicator.

        Quality Levels:
        - STRONG: similarity >= 0.95 (exact/near-exact quote)
        - MEDIUM: 0.85 <= similarity < 0.95 (paraphrased)
        - WEAK: similarity < 0.85 or no quote match

        Args:
            quote_match: Best quote match for citation (or None)

        Returns:
            CitationQuality enum
        """
        if not quote_match:
            return CitationQuality.WEAK

        similarity = quote_match.similarity_score

        if similarity >= self.strong_threshold:
            return CitationQuality.STRONG
        elif similarity >= self.medium_threshold:
            return CitationQuality.MEDIUM
        else:
            return CitationQuality.WEAK

    def _highlight_matched_text(
        self,
        passage_text: str,
        quote_match: QuoteMatch
    ) -> str:
        """
        Add HTML highlighting to matched text in passage.

        Example:
        Input: "France's capital is Paris, located in the north."
        Quote match: "capital is Paris" (positions 10-26)
        Output: "France's <mark>capital is Paris</mark>, located in the north."

        Args:
            passage_text: Original passage text
            quote_match: Quote match with matched_text

        Returns:
            Passage text with <mark> tags around matched portion

        Security: HTML escapes passage text to prevent XSS
        """
        try:
            # HTML escape the entire passage text first
            safe_passage = html.escape(passage_text)

            # Find the matched text in the escaped passage
            # Need to escape the matched text too for comparison
            safe_matched_text = html.escape(quote_match.matched_text)

            # Find occurrence of matched text (case-insensitive)
            match_start = safe_passage.lower().find(safe_matched_text.lower())

            if match_start == -1:
                # Couldn't find exact match, return original
                return safe_passage

            match_end = match_start + len(safe_matched_text)

            # Insert <mark> tags
            highlighted = (
                safe_passage[:match_start] +
                f"<mark>{safe_passage[match_start:match_end]}</mark>" +
                safe_passage[match_end:]
            )

            return highlighted

        except Exception as e:
            logger.error(f"Failed to highlight text: {e}")
            # Fallback: Return escaped original
            return html.escape(passage_text)

    def _format_inline_citation(
        self,
        citation: Dict,
        format_style: str
    ) -> str:
        """
        Format inline citation marker.

        Styles:
        - simple: "[1]"
        - detailed: "[1: doc_name, p.5]"

        Args:
            citation: Citation dict
            format_style: "simple" or "detailed"

        Returns:
            Formatted citation marker string
        """
        citation_num = citation.get('citation_number', 0)

        if format_style == "detailed":
            doc_name = citation.get('document_name', 'Unknown')
            page = citation.get('page')

            # Truncate doc name if too long
            if len(doc_name) > 30:
                doc_name = doc_name[:27] + "..."

            if page:
                return f"[{citation_num}: {doc_name}, p.{page}]"
            else:
                return f"[{citation_num}: {doc_name}]"
        else:
            # Simple format
            return f"[{citation_num}]"

    async def validate_citation_numbers(
        self,
        answer_text: str,
        enriched_citations: List[EnrichedCitation]
    ) -> List[str]:
        """
        Validate all [N] markers in answer have corresponding citations.

        Args:
            answer_text: Answer text with citation markers
            enriched_citations: List of enriched citations

        Returns:
            List of validation errors (empty if valid)

        Example errors:
        - "Citation [3] referenced but not found in citations list"
        - "Citation [1] appears in list but not referenced in answer"
        """
        errors = []

        # Extract citation numbers from answer text
        citation_pattern = r'\[(\d+)\]'
        referenced_numbers = set(int(m) for m in re.findall(citation_pattern, answer_text))

        # Get available citation numbers
        available_numbers = set(c.citation_number for c in enriched_citations)

        # Check for referenced but missing citations
        missing = referenced_numbers - available_numbers
        for num in missing:
            errors.append(f"Citation [{num}] referenced but not found in citations list")

        # Check for unused citations (warning, not error)
        unused = available_numbers - referenced_numbers
        for num in unused:
            # This is just a warning, not added to errors
            logger.debug(f"Citation [{num}] appears in list but not referenced in answer")

        return errors
