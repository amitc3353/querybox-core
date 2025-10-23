"""
Chunking Service for QueryBox Core
Splits extracted text into overlapping chunks for embedding generation
"""
import logging
import os
import re
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.embedding import Embedding

logger = logging.getLogger(__name__)


class ChunkData:
    """Data structure for a single text chunk"""

    def __init__(
        self,
        text: str,
        chunk_index: int,
        start_position: int,
        end_position: int,
        token_estimate: int,
    ):
        self.text = text
        self.chunk_index = chunk_index
        self.start_position = start_position
        self.end_position = end_position
        self.token_estimate = token_estimate


class ChunkingResult:
    """Result of text chunking operation"""

    def __init__(
        self,
        success: bool,
        chunk_count: int = 0,
        total_chars: int = 0,
        avg_chunk_size: int = 0,
        processing_time_ms: int = 0,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.chunk_count = chunk_count
        self.total_chars = total_chars
        self.avg_chunk_size = avg_chunk_size
        self.processing_time_ms = processing_time_ms
        self.error_message = error_message


class ChunkingService:
    """
    Text chunking service with sentence boundary preservation

    Features:
    - Fixed 1000-char chunks with 200-char overlap
    - Sentence boundary detection
    - Position tracking for citation mapping
    - Token estimation for downstream embedding
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        min_chunk_size: Optional[int] = None,
    ):
        """
        Initialize chunking service with configuration

        Args:
            chunk_size: Target characters per chunk (default: 1000)
            chunk_overlap: Overlap between chunks (default: 200)
            min_chunk_size: Minimum viable chunk size (default: 100)
        """
        # Get configuration from environment or use defaults
        self.chunk_size = chunk_size or int(os.getenv("CHUNK_SIZE", "1000"))
        self.chunk_overlap = chunk_overlap or int(os.getenv("CHUNK_OVERLAP", "200"))
        self.min_chunk_size = min_chunk_size or int(os.getenv("MIN_CHUNK_SIZE", "100"))

        # Sentence boundary pattern: split on . ! ? followed by space and capital letter
        self.sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'

        logger.info(
            f"ChunkingService initialized: chunk_size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}, min_size={self.min_chunk_size}"
        )

    def chunk_text(
        self,
        text: str,
        document_id: UUID,
        db: Session,
    ) -> ChunkingResult:
        """
        Split text into overlapping chunks with sentence boundaries

        Args:
            text: Full document text to chunk
            document_id: Document UUID for database linking
            db: Database session for persistence

        Returns:
            ChunkingResult with chunk count and metadata

        Raises:
            ValueError: If text is too short or invalid
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Validate input
            if not isinstance(text, str):
                raise ValueError("Text must be a string")

            if len(text) < self.min_chunk_size:
                raise ValueError(
                    f"Text too short: {len(text)} chars (minimum: {self.min_chunk_size})"
                )

            logger.info(
                f"Starting chunking for document {document_id}: {len(text)} chars"
            )

            # Step 1: Split into sentences
            sentences = self._split_into_sentences(text)
            logger.debug(f"Detected {len(sentences)} sentences")

            # Step 2: Create chunks from sentences
            chunks = self._create_chunks(sentences)
            logger.info(
                f"Created {len(chunks)} chunks (avg size: {sum(len(c.text) for c in chunks) // len(chunks) if chunks else 0} chars)"
            )

            # Step 3: Save chunks to database
            saved_count = self.save_chunks(chunks, document_id, db)

            # Calculate metrics
            end_time = datetime.now(timezone.utc)
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            total_chars = sum(len(chunk.text) for chunk in chunks)
            avg_chunk_size = total_chars // len(chunks) if chunks else 0

            logger.info(
                f"Chunking completed for document {document_id}: "
                f"{saved_count} chunks saved in {processing_time_ms}ms"
            )

            return ChunkingResult(
                success=True,
                chunk_count=saved_count,
                total_chars=total_chars,
                avg_chunk_size=avg_chunk_size,
                processing_time_ms=processing_time_ms,
            )

        except ValueError as e:
            # Validation errors - don't log as errors
            logger.warning(f"Chunking validation failed for document {document_id}: {e}")
            end_time = datetime.now(timezone.utc)
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return ChunkingResult(
                success=False,
                processing_time_ms=processing_time_ms,
                error_message=str(e),
            )

        except Exception as e:
            # Unexpected errors
            logger.error(
                f"Chunking failed for document {document_id}: {e}", exc_info=True
            )
            end_time = datetime.now(timezone.utc)
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return ChunkingResult(
                success=False,
                processing_time_ms=processing_time_ms,
                error_message=str(e),
            )

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using regex pattern

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Split on sentence boundaries
        sentences = re.split(self.sentence_pattern, text)

        # Filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        # If no sentences detected (no sentence boundaries), return text as single item
        if not sentences:
            sentences = [text]

        return sentences

    def _create_chunks(self, sentences: List[str]) -> List[ChunkData]:
        """
        Group sentences into chunks respecting size and overlap

        Args:
            sentences: List of sentences

        Returns:
            List of ChunkData objects
        """
        chunks = []
        current_chunk_text = ""
        current_position = 0
        chunk_index = 0

        for sentence in sentences:
            # Check if adding this sentence would exceed chunk size
            if current_chunk_text and len(current_chunk_text) + len(sentence) > self.chunk_size:
                # Save current chunk
                chunk_start = current_position
                chunk_end = current_position + len(current_chunk_text)
                token_estimate = self._estimate_tokens(current_chunk_text)

                chunks.append(
                    ChunkData(
                        text=current_chunk_text,
                        chunk_index=chunk_index,
                        start_position=chunk_start,
                        end_position=chunk_end,
                        token_estimate=token_estimate,
                    )
                )

                chunk_index += 1

                # Start new chunk with overlap from previous chunk
                overlap_text = current_chunk_text[-self.chunk_overlap:] if len(current_chunk_text) > self.chunk_overlap else current_chunk_text

                # Update position to account for overlap
                current_position = chunk_end - len(overlap_text)
                current_chunk_text = overlap_text + " " + sentence
            else:
                # Add sentence to current chunk
                if current_chunk_text:
                    current_chunk_text += " " + sentence
                else:
                    current_chunk_text = sentence

        # Don't forget the last chunk
        if current_chunk_text:
            chunk_start = current_position
            chunk_end = current_position + len(current_chunk_text)
            token_estimate = self._estimate_tokens(current_chunk_text)

            chunks.append(
                ChunkData(
                    text=current_chunk_text,
                    chunk_index=chunk_index,
                    start_position=chunk_start,
                    end_position=chunk_end,
                    token_estimate=token_estimate,
                )
            )

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count (rough approximation: chars / 4)

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def save_chunks(
        self,
        chunks: List[ChunkData],
        document_id: UUID,
        db: Session,
    ) -> int:
        """
        Save chunks to embeddings table

        Args:
            chunks: List of ChunkData objects
            document_id: Document UUID
            db: Database session

        Returns:
            Number of chunks saved

        Raises:
            Exception: If database operation fails
        """
        try:
            # Start transaction
            db.begin_nested()

            # Delete old chunks first (cleanup)
            deleted_count = db.query(Embedding).filter(
                Embedding.document_id == document_id
            ).delete()

            if deleted_count > 0:
                logger.debug(f"Deleted {deleted_count} old chunks for document {document_id}")

            # Prepare chunk records for bulk insert
            chunk_records = []
            for chunk in chunks:
                chunk_records.append({
                    "document_id": document_id,
                    "chunk_index": chunk.chunk_index,
                    "chunk_text": chunk.text,
                    "chunk_tokens": chunk.token_estimate,
                    "start_position": chunk.start_position,
                    "end_position": chunk.end_position,
                    "embedding_model": "pending",  # No embedding yet
                })

            # Bulk insert chunks
            if chunk_records:
                db.bulk_insert_mappings(Embedding, chunk_records)

            # Commit transaction
            db.commit()

            logger.info(f"Saved {len(chunks)} chunks for document {document_id}")
            return len(chunks)

        except SQLAlchemyError as e:
            # Rollback on database error
            db.rollback()
            logger.error(f"Database error saving chunks for document {document_id}: {e}")
            raise Exception(f"Failed to save chunks to database: {e}") from e

        except Exception as e:
            # Rollback on any other error
            db.rollback()
            logger.error(f"Unexpected error saving chunks for document {document_id}: {e}")
            raise


# Global service instance
_chunking_service: Optional[ChunkingService] = None


def get_chunking_service() -> ChunkingService:
    """
    Get or create global chunking service instance

    Returns:
        ChunkingService singleton instance
    """
    global _chunking_service
    if _chunking_service is None:
        _chunking_service = ChunkingService()
    return _chunking_service
