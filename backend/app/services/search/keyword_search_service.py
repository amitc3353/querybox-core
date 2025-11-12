"""
Keyword Search Service for Step 8.3 - Simple Keyword Search

PostgreSQL full-text search implementation for documents and chunks.
"""
import time
import re
from typing import List, Optional, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_, or_
from datetime import datetime

from app.models.document import Document
from app.models.document_text import DocumentText
from app.models.embedding import Embedding
from app.schemas.search import (
    SearchFilters,
    SearchResultItem,
    SearchResponse
)


class KeywordSearchService:
    """
    Keyword-based document search using PostgreSQL full-text search

    Features:
    - Full-text search with ts_vector and ts_query
    - Searches both full documents and chunks
    - Relevance ranking with ts_rank
    - Context snippet generation with ts_headline
    - Metadata filtering (type, quality, dates)
    """

    def __init__(self, db: Session):
        """Initialize search service with database session"""
        self.db = db
        self.language = 'english'  # PostgreSQL text search language
        self._is_sqlite = self._detect_database_type()

    def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 10,
        offset: int = 0
    ) -> SearchResponse:
        """
        Execute keyword search at chunk-level for precise context

        Args:
            query: Search query string
            filters: Optional filters (document_types, quality, dates)
            limit: Maximum results to return (1-100)
            offset: Pagination offset

        Returns:
            SearchResponse with ranked chunk results and metadata
        """
        start_time = time.time()

        # Build PostgreSQL tsquery
        tsquery = self._build_tsquery(query)

        # Get total count of matching chunks (for pagination)
        total_count = self._count_matching_chunks(tsquery, filters)

        # Search chunks only (chunk-level results for better RAG context)
        chunk_results = self._search_chunks(tsquery, filters, limit, offset)

        # Normalize relevance scores to 0.0-1.0 range
        chunk_results = self._normalize_scores(chunk_results)

        # Convert to SearchResultItem objects
        result_items = self._convert_to_result_items(chunk_results)

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Build response
        return SearchResponse(
            success=True,
            query=query,
            total_results=total_count,
            returned_results=len(result_items),
            results=result_items,
            processing_time_ms=processing_time_ms,
            filters_applied=filters
        )

    def _detect_database_type(self) -> bool:
        """
        Detect if database is SQLite (for test compatibility)

        Returns:
            True if SQLite, False otherwise (PostgreSQL)
        """
        try:
            dialect_name = self.db.bind.dialect.name
            return dialect_name == 'sqlite'
        except Exception:
            return False

    def _build_tsquery(self, query: str) -> str:
        """
        Convert user query to PostgreSQL tsquery format

        Args:
            query: Raw user query string

        Returns:
            Sanitized tsquery string suitable for to_tsquery()
        """
        # Remove special characters that could break tsquery
        query = query.strip()

        # Remove null bytes
        query = query.replace('\x00', '')

        # Escape single quotes for SQL
        query = query.replace("'", "''")

        # Split into words
        words = query.split()

        # Build tsquery with AND operator (&)
        # Example: "machine learning" -> "machine & learning"
        if len(words) > 1:
            tsquery = ' & '.join(words)
        else:
            tsquery = query

        return tsquery

    def _search_full_documents(
        self,
        tsquery: str,
        filters: Optional[SearchFilters],
        limit: int
    ) -> List[Dict]:
        """
        Search full document texts using PostgreSQL full-text search

        Args:
            tsquery: PostgreSQL tsquery string
            filters: Optional search filters
            limit: Maximum results

        Returns:
            List of document matches with rank and snippet
        """
        # Build base query
        query = self.db.query(
            DocumentText.document_id,
            Document.document_name,
            Document.mime_type,
            Document.created_at,
            DocumentText.extraction_quality,
            # Calculate relevance rank
            func.ts_rank(
                func.to_tsvector(self.language, DocumentText.full_text),
                func.to_tsquery(self.language, tsquery)
            ).label('rank'),
            # Generate highlighted snippet
            func.ts_headline(
                self.language,
                DocumentText.full_text,
                func.to_tsquery(self.language, tsquery),
                'MaxWords=50, MinWords=30, MaxFragments=1'
            ).label('snippet')
        ).join(
            Document, DocumentText.document_id == Document.id
        ).filter(
            # Full-text search condition
            func.to_tsvector(self.language, DocumentText.full_text).op('@@')(
                func.to_tsquery(self.language, tsquery)
            ),
            # Only completed documents
            Document.status == 'completed',
            # Not deleted
            Document.is_deleted == False
        )

        # Apply filters
        query = self._apply_filters(query, filters)

        # Order by relevance and limit
        query = query.order_by(text('rank DESC')).limit(limit)

        # Execute query
        results = query.all()

        # Convert to dict
        doc_results = []
        for row in results:
            doc_results.append({
                'document_id': str(row.document_id),
                'document_name': row.document_name,
                'document_type': row.mime_type,
                'relevance_score': float(row.rank),
                'snippet': self._clean_snippet(row.snippet),
                'extraction_quality': row.extraction_quality,
                'created_at': row.created_at,
                'source': 'document',
                'chunk_index': None,
                'chunk_position': None
            })

        return doc_results

    def _count_matching_chunks(
        self,
        tsquery: str,
        filters: Optional[SearchFilters]
    ) -> int:
        """
        Count total matching chunks for pagination

        Args:
            tsquery: PostgreSQL tsquery string (or search term for SQLite)
            filters: Optional search filters

        Returns:
            Total count of matching chunks
        """
        query = self.db.query(func.count(Embedding.id)).join(
            Document, Embedding.document_id == Document.id
        ).join(
            DocumentText, Embedding.document_id == DocumentText.document_id
        )

        # Use different search depending on database
        if self._is_sqlite:
            # SQLite: Use LIKE for each search term (AND condition, case-insensitive)
            search_terms = tsquery.replace(' & ', ' ').replace('&', ' ').split()
            search_filters = [func.lower(Embedding.chunk_text).like(f"%{term.lower()}%") for term in search_terms if term.strip()]

            if search_filters:
                query = query.filter(
                    and_(*search_filters),
                    Document.status == 'completed',
                    Document.is_deleted == False
                )
            else:
                # If no valid search terms, return 0
                return 0
        else:
            # PostgreSQL: Use full-text search
            query = query.filter(
                # Full-text search condition
                func.to_tsvector(self.language, Embedding.chunk_text).op('@@')(
                    func.to_tsquery(self.language, tsquery)
                ),
                # Only completed documents
                Document.status == 'completed',
                # Not deleted
                Document.is_deleted == False
            )

        # Apply filters
        query = self._apply_filters(query, filters)

        return query.scalar() or 0

    def _search_chunks(
        self,
        tsquery: str,
        filters: Optional[SearchFilters],
        limit: int,
        offset: int = 0
    ) -> List[Dict]:
        """
        Search individual chunks using database-appropriate search method

        Args:
            tsquery: PostgreSQL tsquery string (or search term for SQLite)
            filters: Optional search filters
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of chunk matches with rank and snippet
        """
        if self._is_sqlite:
            # SQLite fallback: LIKE-based search with AND conditions for each word (case-insensitive)
            # Split query by ' & ' and search for each term
            search_terms = tsquery.replace(' & ', ' ').replace('&', ' ').split()

            query = self.db.query(
                Embedding.id.label('chunk_id'),
                Embedding.document_id,
                Document.document_name,
                Document.mime_type,
                Document.created_at,
                DocumentText.extraction_quality,
                Embedding.chunk_index,
                Embedding.start_position,
                Embedding.end_position,
                func.length(Embedding.chunk_text).label('rank'),  # Simple relevance by length
                func.substr(Embedding.chunk_text, 1, 200).label('snippet')  # Simple snippet
            ).join(
                Document, Embedding.document_id == Document.id
            ).join(
                DocumentText, Embedding.document_id == DocumentText.document_id
            )

            # Build filter for all search terms (AND condition, case-insensitive)
            search_filters = [func.lower(Embedding.chunk_text).like(f"%{term.lower()}%") for term in search_terms if term.strip()]
            if search_filters:
                query = query.filter(
                    and_(*search_filters),
                    Document.status == 'completed',
                    Document.is_deleted == False
                )
            else:
                # If no valid search terms, return empty
                query = query.filter(False)
        else:
            # PostgreSQL: Use full-text search
            query = self.db.query(
                Embedding.id.label('chunk_id'),
                Embedding.document_id,
                Document.document_name,
                Document.mime_type,
                Document.created_at,
                DocumentText.extraction_quality,
                Embedding.chunk_index,
                Embedding.start_position,
                Embedding.end_position,
                # Calculate relevance rank
                func.ts_rank(
                    func.to_tsvector(self.language, Embedding.chunk_text),
                    func.to_tsquery(self.language, tsquery)
                ).label('rank'),
                # Generate highlighted snippet
                func.ts_headline(
                    self.language,
                    Embedding.chunk_text,
                    func.to_tsquery(self.language, tsquery),
                    'MaxWords=50, MinWords=30, MaxFragments=1'
                ).label('snippet')
            ).join(
                Document, Embedding.document_id == Document.id
            ).join(
                DocumentText, Embedding.document_id == DocumentText.document_id
            ).filter(
                # Full-text search condition
                func.to_tsvector(self.language, Embedding.chunk_text).op('@@')(
                    func.to_tsquery(self.language, tsquery)
                ),
                # Only completed documents
                Document.status == 'completed',
                # Not deleted
                Document.is_deleted == False
            )

        # Apply filters
        query = self._apply_filters(query, filters)

        # Order by relevance, apply pagination
        query = query.order_by(text('rank DESC')).limit(limit).offset(offset)

        # Execute query
        results = query.all()

        # Convert to dict
        chunk_results = []
        for row in results:
            chunk_results.append({
                'chunk_id': str(row.chunk_id),
                'document_id': str(row.document_id),
                'document_name': row.document_name,
                'document_type': row.mime_type,
                'relevance_score': float(row.rank),
                'snippet': self._clean_snippet(row.snippet),
                'extraction_quality': row.extraction_quality,
                'created_at': row.created_at,
                'source': 'chunk',
                'chunk_index': row.chunk_index,
                'chunk_position': {
                    'start': row.start_position,
                    'end': row.end_position
                } if row.start_position is not None else None
            })

        return chunk_results

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
            # PostgreSQL array overlap operator
            query = query.filter(Document.tags.overlap(filters.tags))

        return query

    def _merge_results(
        self,
        doc_results: List[Dict],
        chunk_results: List[Dict],
        limit: int,
        offset: int
    ) -> List[SearchResultItem]:
        """
        Merge document and chunk results, deduplicate by document_id

        Args:
            doc_results: Results from full document search
            chunk_results: Results from chunk search
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of SearchResultItem objects
        """
        # Combine all results
        all_results = doc_results + chunk_results

        # Deduplicate by document_id, keeping highest rank
        seen_docs = {}
        for result in all_results:
            doc_id = result['document_id']

            if doc_id not in seen_docs:
                seen_docs[doc_id] = result
            else:
                # Keep result with higher relevance score
                if result['relevance_score'] > seen_docs[doc_id]['relevance_score']:
                    seen_docs[doc_id] = result

        # Convert to list and sort by relevance
        merged = list(seen_docs.values())
        merged.sort(key=lambda x: x['relevance_score'], reverse=True)

        # Apply pagination
        paginated = merged[offset:offset + limit]

        # Convert to SearchResultItem objects
        result_items = []
        for result in paginated:
            result_items.append(
                SearchResultItem(
                    document_id=result['document_id'],
                    document_name=result['document_name'],
                    relevance_score=result['relevance_score'],
                    snippet=result['snippet'],
                    chunk_index=result['chunk_index'],
                    chunk_position=result['chunk_position'],
                    extraction_quality=result['extraction_quality'],
                    document_type=result['document_type'],
                    created_at=result['created_at']
                )
            )

        return result_items

    def _clean_snippet(self, snippet: str) -> str:
        """
        Clean and format snippet text

        Args:
            snippet: Raw snippet from ts_headline

        Returns:
            Cleaned snippet with proper highlighting
        """
        if not snippet:
            return ""

        # ts_headline uses <b></b> tags for highlighting
        # Convert to ** markdown style
        snippet = snippet.replace('<b>', '**').replace('</b>', '**')

        # Add ellipsis if needed
        if not snippet.startswith('...'):
            snippet = '...' + snippet
        if not snippet.endswith('...'):
            snippet = snippet + '...'

        # Normalize whitespace
        snippet = re.sub(r'\s+', ' ', snippet)

        # Limit length
        max_length = 300
        if len(snippet) > max_length:
            snippet = snippet[:max_length] + '...'

        return snippet.strip()

    def _normalize_scores(self, results: List[Dict]) -> List[Dict]:
        """
        Normalize relevance scores to 0.0-1.0 range for better UX

        PostgreSQL ts_rank typically returns very low scores (0.01-0.15).
        We normalize to make scores more intuitive (0.7-1.0 for good matches).

        Args:
            results: List of search results with raw relevance_score

        Returns:
            Results with normalized relevance_score (0.0-1.0)
        """
        if not results:
            return results

        # Find max score for normalization
        max_score = max(r['relevance_score'] for r in results)

        # Avoid division by zero
        if max_score == 0:
            return results

        # Normalize scores to 0.0-1.0 range, then boost to 0.6-1.0 range
        # This makes top results appear more relevant (0.8-1.0)
        for result in results:
            # Normalize to 0.0-1.0
            normalized = result['relevance_score'] / max_score

            # Boost to 0.6-1.0 range (better UX for top matches)
            boosted = 0.6 + (normalized * 0.4)

            result['relevance_score'] = round(boosted, 4)

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
                    chunk_id=result.get('chunk_id'),
                    document_id=result['document_id'],
                    document_name=result['document_name'],
                    relevance_score=result['relevance_score'],
                    snippet=result['snippet'],
                    chunk_index=result['chunk_index'],
                    chunk_position=result['chunk_position'],
                    extraction_quality=result['extraction_quality'],
                    document_type=result['document_type'],
                    created_at=result['created_at']
                )
            )
        return result_items


def get_search_service(db: Session) -> KeywordSearchService:
    """
    Factory function to create KeywordSearchService instance

    Args:
        db: Database session

    Returns:
        KeywordSearchService instance
    """
    return KeywordSearchService(db=db)
