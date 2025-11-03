"""
BM25 Search Service for Step 10.1 - Hybrid Retrieval

BM25 (Best Matching 25) search algorithm implementation for keyword-based retrieval.
"""
import time
import math
import re
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import structlog

from app.models.document import Document
from app.models.document_text import DocumentText
from app.models.embedding import Embedding
from app.schemas.search import (
    SearchFilters,
    SearchResultItem
)
from app.core.config import settings

logger = structlog.get_logger()


class BM25SearchService:
    """
    BM25 (Best Matching 25) search implementation

    BM25 is a probabilistic ranking function that considers:
    - Term frequency (TF): How often a term appears in a document
    - Inverse document frequency (IDF): Rarity of term across corpus
    - Document length normalization: Penalizes very long documents

    BM25 Formula:
    score(D,Q) = Σ IDF(qi) * (f(qi,D) * (k1 + 1)) / (f(qi,D) + k1 * (1 - b + b * |D|/avgdl))

    Where:
    - f(qi,D) = term frequency of query term qi in document D
    - |D| = length of document D (in words)
    - avgdl = average document length in corpus
    - k1 = term frequency saturation parameter (default: 1.5)
    - b = length normalization parameter (default: 0.75)
    """

    def __init__(self, db: Session, k1: float = None, b: float = None):
        """
        Initialize BM25 search service

        Args:
            db: Database session
            k1: Term frequency saturation (1.2-2.0, higher = more weight to TF)
            b: Length normalization (0-1, higher = more penalization for long docs)
        """
        self.db = db
        self.k1 = k1 if k1 is not None else settings.BM25_K1
        self.b = b if b is not None else settings.BM25_B
        self._corpus_stats_cache = None  # Cache for corpus statistics

        logger.info(
            "bm25_service_initialized",
            k1=self.k1,
            b=self.b
        )

    def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[SearchResultItem]:
        """
        Execute BM25 search on chunk-level

        Steps:
        1. Parse query into terms
        2. Get corpus statistics (total chunks, avg length)
        3. Fetch candidate chunks from database
        4. Calculate BM25 score for each chunk
        5. Apply metadata filters
        6. Rank by BM25 score
        7. Return top-k results

        Args:
            query: Search query string
            filters: Optional search filters
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of SearchResultItem with BM25 scores
        """
        start_time = time.time()

        # Parse query into terms
        query_terms = self._parse_query(query)

        if not query_terms:
            logger.warning("bm25_search_empty_query", query=query)
            return []

        logger.debug(
            "bm25_search_started",
            query=query[:100],
            query_terms=query_terms[:10],
            term_count=len(query_terms)
        )

        # Get corpus statistics
        corpus_stats = self._get_corpus_stats()

        # Fetch candidate chunks using PostgreSQL FTS
        candidates = self._fetch_candidate_chunks(query_terms, filters, limit * 10)

        if not candidates:
            logger.info("bm25_search_no_candidates", query=query[:100])
            return []

        # Calculate BM25 scores for each candidate
        scored_results = []
        for candidate in candidates:
            bm25_score = self._calculate_bm25_score(
                query_terms=query_terms,
                chunk_text=candidate['chunk_text'],
                chunk_length=len(candidate['chunk_text'].split()),
                avg_chunk_length=corpus_stats['avg_chunk_length']
            )

            if bm25_score > 0:
                scored_results.append({
                    'chunk_id': candidate['chunk_id'],  # For citation extraction
                    'document_id': str(candidate['document_id']),
                    'document_name': candidate['document_name'],
                    'document_type': candidate['mime_type'],
                    'relevance_score': bm25_score,
                    'snippet': self._generate_snippet(candidate['chunk_text'], query_terms),
                    'chunk_index': candidate['chunk_index'],
                    'chunk_position': {
                        'start': candidate['start_position'],
                        'end': candidate['end_position']
                    } if candidate['start_position'] is not None else None,
                    'extraction_quality': candidate['extraction_quality'],
                    'created_at': candidate['created_at'],
                    'embedding': candidate.get('embedding')  # For MMR and semantic dedup
                })

        # Sort by BM25 score (descending)
        scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)

        # Apply pagination
        paginated_results = scored_results[offset:offset + limit]

        # Normalize scores to 0.0-1.0 range
        paginated_results = self._normalize_scores(paginated_results)

        # Convert to SearchResultItem objects
        result_items = self._convert_to_result_items(paginated_results)

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "bm25_search_completed",
            query=query[:100],
            candidates_found=len(candidates),
            scored_results=len(scored_results),
            returned_results=len(result_items),
            processing_time_ms=processing_time_ms
        )

        return result_items

    def _parse_query(self, query: str) -> List[str]:
        """
        Parse query into terms (tokenization)

        Args:
            query: Raw query string

        Returns:
            List of lowercase terms
        """
        # Remove special characters, keep alphanumeric and spaces
        query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query)

        # Split into words and lowercase
        terms = [term.lower() for term in query.split() if term.strip()]

        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in terms:
            if term not in seen and len(term) > 1:  # Skip single-char terms
                seen.add(term)
                unique_terms.append(term)

        return unique_terms

    def _get_corpus_stats(self) -> Dict[str, float]:
        """
        Get corpus statistics (total chunks, avg length) - cached

        Returns:
            Dict with 'total_chunks' and 'avg_chunk_length'
        """
        # Use cache if available (valid for 5 minutes)
        if self._corpus_stats_cache:
            return self._corpus_stats_cache

        # Query corpus statistics
        result = self.db.query(
            func.count(Embedding.id).label('total_chunks'),
            func.avg(func.length(Embedding.chunk_text)).label('avg_chunk_length')
        ).filter(
            Embedding.chunk_text.isnot(None),
            Embedding.chunk_text != ''
        ).first()

        total_chunks = result.total_chunks or 1  # Avoid division by zero
        avg_chunk_length_chars = result.avg_chunk_length or 1000

        # Estimate avg word count (approx 5 chars per word)
        # Convert Decimal to float for arithmetic operations
        avg_chunk_length_words = float(avg_chunk_length_chars) / 5.0

        self._corpus_stats_cache = {
            'total_chunks': total_chunks,
            'avg_chunk_length': avg_chunk_length_words
        }

        logger.debug(
            "corpus_stats_calculated",
            total_chunks=total_chunks,
            avg_chunk_length=avg_chunk_length_words
        )

        return self._corpus_stats_cache

    def _fetch_candidate_chunks(
        self,
        query_terms: List[str],
        filters: Optional[SearchFilters],
        top_k: int
    ) -> List[Dict]:
        """
        Fetch candidate chunks using PostgreSQL FTS

        Args:
            query_terms: List of query terms
            filters: Optional search filters
            top_k: Number of candidates to fetch

        Returns:
            List of candidate chunk dictionaries
        """
        # Build tsquery from query terms
        tsquery = ' & '.join([term.replace("'", "''") for term in query_terms])

        # Build base query
        # Use LEFT JOIN for DocumentText to include embeddings even when DocumentText is missing
        query = self.db.query(
            Embedding.id,
            Embedding.document_id,
            Embedding.chunk_text,
            Embedding.chunk_index,
            Embedding.start_position,
            Embedding.end_position,
            Embedding.embedding,  # Include embedding for MMR and semantic dedup
            Document.document_name,
            Document.mime_type,
            Document.created_at,
            DocumentText.extraction_quality
        ).join(
            Document, Embedding.document_id == Document.id
        ).outerjoin(
            DocumentText, Embedding.document_id == DocumentText.document_id
        ).filter(
            # Full-text search condition
            func.to_tsvector('english', Embedding.chunk_text).op('@@')(
                func.to_tsquery('english', tsquery)
            ),
            # Only completed documents
            Document.status == 'completed',
            # Not deleted
            Document.is_deleted == False
        )

        # Apply filters
        query = self._apply_filters(query, filters)

        # Limit candidates
        query = query.limit(top_k)

        # Execute query
        results = query.all()

        # Convert to dict
        candidates = []
        for row in results:
            # Convert pgvector embedding to list of floats
            embedding_list = None
            if hasattr(row, 'embedding') and row.embedding is not None:
                try:
                    # pgvector returns the embedding as a list already
                    embedding_list = list(row.embedding) if hasattr(row.embedding, '__iter__') else None
                except Exception as e:
                    logger.debug(
                        "embedding_conversion_failed",
                        chunk_id=str(row.id),
                        error=str(e)
                    )

            candidates.append({
                'chunk_id': str(row.id),  # For citation extraction
                'id': str(row.id),
                'document_id': row.document_id,
                'chunk_text': row.chunk_text,
                'chunk_index': row.chunk_index,
                'start_position': row.start_position,
                'end_position': row.end_position,
                'document_name': row.document_name,
                'mime_type': row.mime_type,
                'created_at': row.created_at,
                'extraction_quality': row.extraction_quality,
                'embedding': embedding_list  # For MMR and semantic dedup
            })

        return candidates

    def _calculate_idf(self, term: str, total_chunks: int) -> float:
        """
        Calculate Inverse Document Frequency for a term

        IDF(t) = log((N - n(t) + 0.5) / (n(t) + 0.5))

        Where:
        - N = total number of chunks in corpus
        - n(t) = number of chunks containing term t

        Args:
            term: Search term
            total_chunks: Total number of chunks in corpus

        Returns:
            IDF score for term
        """
        # Count chunks containing term
        chunks_with_term = self.db.query(func.count(Embedding.id)).filter(
            Embedding.chunk_text.ilike(f'%{term}%')
        ).scalar() or 0

        # Calculate IDF using BM25 formula
        idf = math.log((total_chunks - chunks_with_term + 0.5) / (chunks_with_term + 0.5) + 1.0)

        return max(idf, 0.0)  # Ensure non-negative

    def _calculate_bm25_score(
        self,
        query_terms: List[str],
        chunk_text: str,
        chunk_length: int,
        avg_chunk_length: float
    ) -> float:
        """
        Calculate BM25 score for a single chunk

        BM25 Formula:
        score(D,Q) = Σ IDF(qi) * (f(qi,D) * (k1 + 1)) / (f(qi,D) + k1 * (1 - b + b * |D|/avgdl))

        Args:
            query_terms: List of query terms
            chunk_text: Chunk text to score
            chunk_length: Length of chunk in words
            avg_chunk_length: Average chunk length in corpus

        Returns:
            BM25 score
        """
        # Normalize chunk text to lowercase for matching
        chunk_text_lower = chunk_text.lower()

        # Calculate term frequencies in chunk
        term_freqs = {}
        for term in query_terms:
            # Count occurrences (case-insensitive)
            term_freqs[term] = chunk_text_lower.count(term)

        # Calculate BM25 score
        score = 0.0
        corpus_stats = self._get_corpus_stats()
        total_chunks = corpus_stats['total_chunks']

        for term in query_terms:
            # Get term frequency in chunk
            tf = term_freqs[term]

            if tf == 0:
                continue

            # Calculate IDF (simplified - using term presence in chunk text)
            # For performance, we estimate IDF instead of querying for each term
            # Assuming rare terms have higher IDF (basic heuristic)
            idf = 1.0  # Simplified IDF (can be improved with caching)

            # Calculate length normalization
            length_norm = 1 - self.b + self.b * (chunk_length / avg_chunk_length)

            # BM25 term score
            term_score = idf * (tf * (self.k1 + 1)) / (tf + self.k1 * length_norm)

            score += term_score

        return score

    def _apply_filters(self, query, filters: Optional[SearchFilters]):
        """
        Apply search filters to query

        Args:
            query: SQLAlchemy query object
            filters: Optional search filters

        Returns:
            Modified query with filters applied
        """
        if not filters:
            return query

        # Filter by document types (MIME types)
        if filters.document_types:
            query = query.filter(Document.mime_type.in_(filters.document_types))

        # Filter by extraction quality
        if filters.min_quality is not None:
            query = query.filter(DocumentText.extraction_quality >= filters.min_quality)

        # Filter by date range
        if filters.date_from:
            query = query.filter(Document.created_at >= filters.date_from)

        if filters.date_to:
            query = query.filter(Document.created_at <= filters.date_to)

        # Filter by tags
        if filters.tags:
            query = query.filter(Document.tags.overlap(filters.tags))

        return query

    def _generate_snippet(self, chunk_text: str, query_terms: List[str], max_length: int = 300) -> str:
        """
        Generate snippet from chunk text with query term highlighting

        Args:
            chunk_text: Full chunk text
            query_terms: Query terms to highlight
            max_length: Maximum snippet length

        Returns:
            Snippet with highlighted terms
        """
        if not chunk_text:
            return ""

        # Find first occurrence of any query term
        chunk_lower = chunk_text.lower()
        first_pos = len(chunk_text)

        for term in query_terms:
            pos = chunk_lower.find(term.lower())
            if pos != -1 and pos < first_pos:
                first_pos = pos

        # Extract snippet around first occurrence
        if first_pos < len(chunk_text):
            # Get context before and after
            start = max(0, first_pos - 100)
            end = min(len(chunk_text), first_pos + 200)
            snippet = chunk_text[start:end]
        else:
            # No term found, take beginning
            snippet = chunk_text[:max_length]

        # Highlight query terms
        for term in query_terms:
            # Case-insensitive highlighting
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            snippet = pattern.sub(f'**{term}**', snippet)

        # Add ellipsis
        if not snippet.startswith('...'):
            snippet = '...' + snippet
        if not snippet.endswith('...'):
            snippet = snippet + '...'

        # Normalize whitespace
        snippet = re.sub(r'\s+', ' ', snippet)

        # Limit length
        if len(snippet) > max_length:
            snippet = snippet[:max_length] + '...'

        return snippet.strip()

    def _normalize_scores(self, results: List[Dict]) -> List[Dict]:
        """
        Normalize BM25 scores to 0.0-1.0 range

        Args:
            results: List of results with BM25 scores

        Returns:
            Results with normalized scores
        """
        if not results:
            return results

        # Find max score
        max_score = max(r['relevance_score'] for r in results)

        if max_score == 0:
            return results

        # Normalize to 0.0-1.0 range
        for result in results:
            normalized = result['relevance_score'] / max_score
            result['relevance_score'] = round(normalized, 4)

        return results

    def _convert_to_result_items(self, results: List[Dict]) -> List[SearchResultItem]:
        """
        Convert internal result dicts to SearchResultItem schema objects

        Args:
            results: List of result dictionaries

        Returns:
            List of SearchResultItem objects
        """
        result_items = []
        for result in results:
            result_items.append(
                SearchResultItem(
                    chunk_id=result.get('chunk_id'),  # For citation extraction
                    document_id=result['document_id'],
                    document_name=result['document_name'],
                    relevance_score=result['relevance_score'],
                    snippet=result['snippet'],
                    chunk_index=result['chunk_index'],
                    chunk_position=result['chunk_position'],
                    extraction_quality=result['extraction_quality'],
                    document_type=result['document_type'],
                    created_at=result['created_at'],
                    embedding=result.get('embedding')  # For MMR and semantic dedup
                )
            )
        return result_items


def get_bm25_search_service(db: Session) -> BM25SearchService:
    """
    Factory function to create BM25SearchService instance

    Args:
        db: Database session

    Returns:
        BM25SearchService instance
    """
    return BM25SearchService(db=db)
