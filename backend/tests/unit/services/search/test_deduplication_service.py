"""
Unit Tests for Deduplication Service (Step 10.2)
Tests DeduplicationService without external dependencies
"""
import pytest
from unittest.mock import Mock
from uuid import uuid4
from datetime import datetime, timezone
import hashlib

from app.services.search.deduplication_service import (
    DeduplicationService,
    get_deduplication_service
)
from app.schemas.search import SearchResultItem
from app.core.config import settings


class TestDeduplicationService:
    """Test DeduplicationService"""

    @pytest.fixture
    def service_default(self):
        """Create deduplication service with default settings"""
        return DeduplicationService()

    @pytest.fixture
    def service_no_semantic(self):
        """Create deduplication service with semantic dedup disabled"""
        return DeduplicationService(enable_semantic_dedup=False)

    @pytest.fixture
    def candidates_with_exact_duplicates(self):
        """Create candidates with exact duplicates (same chunk_id)"""
        doc_id = str(uuid4())
        return [
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.9,
                snippet="Test snippet 1",
                chunk_index=1,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.95,  # Higher score for same chunk
                snippet="Test snippet 1",
                chunk_index=1,  # Same chunk index -> duplicate
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.8,
                snippet="Test snippet 2",
                chunk_index=2,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

    @pytest.fixture
    def candidates_with_content_duplicates(self):
        """Create candidates with content duplicates (same text, different formatting)"""
        doc_id = str(uuid4())
        return [
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.9,
                snippet="Machine learning is a subset of AI",
                chunk_index=1,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.85,
                snippet="Machine   learning   is   a   subset   of   AI",  # Extra whitespace
                chunk_index=2,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.8,
                snippet="Deep learning uses neural networks",  # Different content
                chunk_index=3,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

    # Test 1: Deduplicate by chunk_id
    def test_deduplicate_by_chunk_id(self, service_default, candidates_with_exact_duplicates):
        """Test exact deduplication by chunk_id"""
        original_count = len(candidates_with_exact_duplicates)

        deduplicated = service_default.deduplicate(candidates_with_exact_duplicates)

        # Should remove 1 duplicate (2 items with chunk_index=1)
        assert len(deduplicated) == original_count - 1

        # Should keep higher-scored version
        chunk_1_results = [r for r in deduplicated if r.chunk_index == 1]
        assert len(chunk_1_results) == 1
        assert chunk_1_results[0].relevance_score == 0.95  # Higher score kept

        # Should keep unique chunk
        chunk_2_results = [r for r in deduplicated if r.chunk_index == 2]
        assert len(chunk_2_results) == 1

    # Test 2: Deduplicate by content hash
    def test_deduplicate_by_content_hash(self, service_default, candidates_with_content_duplicates):
        """Test content-based deduplication using SHA-256 hash"""
        original_count = len(candidates_with_content_duplicates)

        deduplicated = service_default.deduplicate(candidates_with_content_duplicates)

        # Should remove 1 duplicate (same content with different whitespace)
        assert len(deduplicated) == original_count - 1

        # Verify only unique content remains
        snippets = [r.snippet for r in deduplicated]
        # Normalize and check uniqueness
        normalized_snippets = [
            ' '.join(s.lower().split()) for s in snippets
        ]
        assert len(normalized_snippets) == len(set(normalized_snippets))

    # Test 3: Deduplicate by embedding similarity (semantic)
    def test_deduplicate_by_embedding_similarity(self, service_default):
        """Test semantic deduplication with embeddings"""
        # Note: Currently semantic dedup is stubbed (returns as-is)
        # This test verifies the stub behavior

        doc_id = str(uuid4())
        candidates = [
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.9,
                snippet="Test snippet 1",
                chunk_index=1,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.8,
                snippet="Test snippet 2",
                chunk_index=2,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        deduplicated = service_default.deduplicate(candidates)

        # With current implementation (stubbed), should return as-is
        # In Phase 3 integration with DB, this would actually deduplicate
        assert len(deduplicated) == len(candidates)

    # Test 4: Deduplication statistics
    def test_deduplication_stats(self, service_default, candidates_with_exact_duplicates):
        """Test deduplication statistics calculation"""
        original = candidates_with_exact_duplicates
        deduplicated = service_default.deduplicate(original)

        stats = service_default.calculate_deduplication_stats(original, deduplicated)

        # Verify stats
        assert stats["original_count"] == len(original)
        assert stats["deduplicated_count"] == len(deduplicated)
        assert stats["duplicates_removed"] == len(original) - len(deduplicated)

        expected_rate = (len(original) - len(deduplicated)) / len(original)
        assert abs(stats["deduplication_rate"] - expected_rate) < 0.0001

    # Test 5: Deduplication keeps highest score
    def test_deduplication_keeps_highest_score(self, service_default):
        """Test deduplication always keeps highest-scored duplicate"""
        doc_id = str(uuid4())

        # Same chunk with different scores
        candidates = [
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.7,  # Lower score
                snippet="Duplicate content",
                chunk_index=1,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.95,  # Highest score
                snippet="Duplicate content",
                chunk_index=1,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.85,  # Middle score
                snippet="Duplicate content",
                chunk_index=1,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        deduplicated = service_default.deduplicate(candidates)

        # Should keep only highest scored version
        assert len(deduplicated) == 1
        assert deduplicated[0].relevance_score == 0.95

    # Test 6: Empty candidates
    def test_deduplication_empty_candidates(self, service_default):
        """Test deduplication with empty candidates returns empty list"""
        empty_candidates = []

        deduplicated = service_default.deduplicate(empty_candidates)

        assert deduplicated == []

    # Test 7: No duplicates
    def test_deduplication_no_duplicates(self, service_default):
        """Test deduplication with no duplicates returns all candidates"""
        doc_id = str(uuid4())
        candidates = [
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.9,
                snippet=f"Unique snippet {i}",
                chunk_index=i,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
            for i in range(5)
        ]

        deduplicated = service_default.deduplicate(candidates)

        # No duplicates, should return all
        assert len(deduplicated) == len(candidates)

    # Test 8: Content hash calculation
    def test_content_hash_calculation(self, service_default):
        """Test content hash calculation is deterministic and correct"""
        text1 = "Machine learning is AI"
        text2 = "Machine   learning   is   AI"  # Extra whitespace
        text3 = "MACHINE LEARNING IS AI"  # Different case
        text4 = "Deep learning is AI"  # Different content

        hash1 = service_default._calculate_content_hash(text1)
        hash2 = service_default._calculate_content_hash(text2)
        hash3 = service_default._calculate_content_hash(text3)
        hash4 = service_default._calculate_content_hash(text4)

        # Same normalized content should have same hash
        assert hash1 == hash2  # Whitespace normalized
        assert hash1 == hash3  # Case normalized

        # Different content should have different hash
        assert hash1 != hash4

        # Hash should be SHA-256 (64 hex characters)
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)

    # Test 9: Chunk ID generation
    def test_chunk_id_generation(self, service_default):
        """Test chunk ID generation is correct"""
        doc_id = str(uuid4())

        item = SearchResultItem(
            document_id=doc_id,
            document_name="test.pdf",
            relevance_score=0.9,
            snippet="test",
            chunk_index=42,
            chunk_position=None,
            extraction_quality=0.95,
            document_type="application/pdf",
            created_at=datetime.now(timezone.utc)
        )

        chunk_id = service_default._get_chunk_id(item)

        assert chunk_id == f"{doc_id}_42"

    # Test 10: Three-stage deduplication order
    def test_three_stage_deduplication_order(self, service_default):
        """Test deduplication runs in correct order: chunk_id -> content -> semantic"""
        doc_id = str(uuid4())

        # Create candidates with both exact and content duplicates
        candidates = [
            # Exact duplicate (same chunk_id)
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.9,
                snippet="Test",
                chunk_index=1,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.8,  # Lower score, should be removed
                snippet="Test",
                chunk_index=1,  # Same chunk -> exact duplicate
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            # Content duplicate (same text, different whitespace)
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.85,
                snippet="Machine learning",
                chunk_index=2,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.75,  # Lower score, should be removed
                snippet="Machine   learning",  # Same content, extra whitespace
                chunk_index=3,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            ),
            # Unique
            SearchResultItem(
                document_id=doc_id,
                document_name="doc1.pdf",
                relevance_score=0.7,
                snippet="Deep learning",
                chunk_index=4,
                chunk_position=None,
                extraction_quality=0.95,
                document_type="application/pdf",
                created_at=datetime.now(timezone.utc)
            )
        ]

        deduplicated = service_default.deduplicate(candidates)

        # Should remove 2 duplicates (1 exact, 1 content)
        assert len(deduplicated) == 3

        # Verify correct items kept
        chunk_indices = [r.chunk_index for r in deduplicated]
        assert 1 in chunk_indices  # Exact duplicate kept (higher score)
        assert 2 in chunk_indices  # Content duplicate kept (higher score)
        assert 4 in chunk_indices  # Unique kept


class TestGetDeduplicationService:
    """Test get_deduplication_service factory function"""

    def test_get_deduplication_service_returns_instance(self):
        """Test factory returns DeduplicationService instance"""
        service = get_deduplication_service()

        assert service is not None
        assert isinstance(service, DeduplicationService)

    def test_get_deduplication_service_with_custom_threshold(self):
        """Test factory with custom semantic threshold"""
        service = get_deduplication_service(
            semantic_threshold=0.90,
            enable_semantic_dedup=False
        )

        assert service.semantic_threshold == 0.90
        assert service.enable_semantic_dedup is False
