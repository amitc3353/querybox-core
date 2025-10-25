"""
Chunking Service for QueryBox Core
Splits extracted text into overlapping chunks for embedding generation
"""
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.embedding import Embedding
from app.services.chunking.token_counter import TokenCounter
from app.services.chunking.sentence_splitter import SentenceSplitter, Sentence
from app.services.chunking.metadata_extractor import MetadataExtractor, DocumentStructure

logger = logging.getLogger(__name__)


@dataclass
class EnhancedChunkingConfig:
    """Configuration for enhanced chunking with token-based optimization

    Optimized for BGE-M3 embedding model (8192 token max, but smaller chunks
    are better for retrieval accuracy).
    """
    target_tokens: int = 512        # BGE-M3 optimized target
    max_tokens: int = 600            # Hard limit (model max = 8192, but smaller is better)
    min_tokens: int = 100            # Minimum viable chunk
    overlap_tokens: int = 50         # Token-based overlap (vs char-based)
    preserve_paragraphs: bool = True # Respect paragraph boundaries
    extract_metadata: bool = True    # Extract document structure metadata
    use_spacy: bool = True           # Use spaCy (fallback to NLTK if False)


@dataclass
class ChunkMetadata:
    """Rich metadata for each chunk

    Stores document structure information to improve retrieval context
    and enable advanced filtering/ranking.
    """
    section_heading: Optional[str] = None       # Nearest H1/H2/H3 heading
    subsection_heading: Optional[str] = None    # Nearest H4/H5/H6 heading
    chunk_type: str = "paragraph"               # "paragraph", "list", "table", "code", "heading"
    paragraph_index: int = 0                    # Which paragraph in section
    semantic_density: float = 0.5               # Ratio of content words to total words
    contains_table: bool = False                # Contains table data
    contains_list: bool = False                 # Contains list items
    contains_code: bool = False                 # Contains code blocks
    contains_equation: bool = False             # Contains equations
    contains_figure: bool = False               # Contains figure references
    language: str = "en"                        # Detected language


class ChunkData:
    """Data structure for a single text chunk (legacy)"""

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


class EnhancedChunk:
    """Enhanced chunk data with rich metadata"""

    def __init__(
        self,
        text: str,
        chunk_index: int,
        start_position: int,
        end_position: int,
        token_count: int,
        metadata: "ChunkMetadata",
        jsonb_metadata: Dict[str, Any],
    ):
        self.text = text
        self.chunk_index = chunk_index
        self.start_position = start_position
        self.end_position = end_position
        self.token_count = token_count
        self.metadata = metadata
        self.jsonb_metadata = jsonb_metadata


class ChunkingResult:
    """Result of text chunking operation"""

    def __init__(
        self,
        success: bool,
        chunk_count: int = 0,
        total_chars: int = 0,
        avg_chunk_size: int = 0,
        processing_time_ms: int = 0,
        quality_score: float = 0.0,
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.chunk_count = chunk_count
        self.total_chars = total_chars
        self.avg_chunk_size = avg_chunk_size
        self.processing_time_ms = processing_time_ms
        self.quality_score = quality_score
        self.error_message = error_message


class ChunkingService:
    """
    Enhanced text chunking service with NLP-based processing and rich metadata

    Features:
    - Token-based chunking optimized for BGE-M3 (512 target, 600 max, 50 overlap tokens)
    - Sentence boundary preservation with spaCy/NLTK dual backend
    - Rich metadata extraction (headings, tables, lists, code, equations, figures, etc.)
    - Document structure analysis
    - Semantic density calculation
    - Position tracking for citation mapping
    """

    def __init__(self, config: Optional[EnhancedChunkingConfig] = None):
        """
        Initialize enhanced chunking service with configuration

        Args:
            config: EnhancedChunkingConfig instance (uses defaults if None)
        """
        # Use provided config or create default from environment variables
        self.config = config or EnhancedChunkingConfig(
            target_tokens=int(os.getenv("CHUNK_TARGET_TOKENS", "512")),
            max_tokens=int(os.getenv("CHUNK_MAX_TOKENS", "600")),
            min_tokens=int(os.getenv("CHUNK_MIN_TOKENS", "100")),
            overlap_tokens=int(os.getenv("CHUNK_OVERLAP_TOKENS", "50")),
            preserve_paragraphs=os.getenv("PRESERVE_PARAGRAPHS", "true").lower() == "true",
            extract_metadata=os.getenv("EXTRACT_METADATA", "true").lower() == "true",
            use_spacy=os.getenv("USE_SPACY", "true").lower() == "true",
        )

        # Initialize NLP components
        self.sentence_splitter = SentenceSplitter(use_spacy=self.config.use_spacy)
        self.token_counter = TokenCounter(model="BAAI/bge-m3")
        self.metadata_extractor = MetadataExtractor() if self.config.extract_metadata else None

        logger.info(
            f"ChunkingService initialized (enhanced): target_tokens={self.config.target_tokens}, "
            f"max_tokens={self.config.max_tokens}, overlap={self.config.overlap_tokens}, "
            f"preserve_paragraphs={self.config.preserve_paragraphs}, "
            f"extract_metadata={self.config.extract_metadata}, use_spacy={self.config.use_spacy}"
        )

    def chunk_text(
        self,
        text: str,
        document_id: UUID,
        db: Session,
    ) -> ChunkingResult:
        """
        Split text into token-optimized chunks with rich metadata extraction

        Implements the complete enhanced chunking pipeline:
        1. Extract document structure using MetadataExtractor
        2. Split into sentences using SentenceSplitter (spaCy/NLTK)
        3. Count tokens for each sentence using TokenCounter (BGE-M3)
        4. Group sentences into chunks (target: 512 tokens, max: 600, min: 100)
        5. Add 50-token overlap between chunks
        6. Preserve paragraph boundaries (don't split mid-paragraph if possible)
        7. Attach metadata (section_heading, chunk_type, semantic_density, etc.)
        8. Save chunks to database with all enhanced metadata fields

        Args:
            text: Full document text to chunk
            document_id: Document UUID for database linking
            db: Database session for persistence

        Returns:
            ChunkingResult with chunk count and enhanced metrics

        Raises:
            ValueError: If text is too short or invalid
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Validate input
            if not isinstance(text, str):
                raise ValueError("Text must be a string")

            min_chars = self.config.min_tokens * 4  # Rough char estimate
            if len(text) < min_chars:
                raise ValueError(
                    f"Text too short: {len(text)} chars (minimum: {min_chars})"
                )

            logger.info(
                f"Starting enhanced chunking for document {document_id}: {len(text)} chars"
            )

            # Step 1: Extract document structure (if enabled)
            doc_structure = None
            if self.metadata_extractor:
                doc_structure = self.metadata_extractor.extract_structure(text)
                logger.debug(
                    f"Extracted structure: {len(doc_structure.headings)} headings, "
                    f"{len(doc_structure.tables)} tables, {len(doc_structure.lists)} lists, "
                    f"{len(doc_structure.code_blocks)} code blocks, "
                    f"{len(doc_structure.equations)} equations"
                )

            # Step 2: Split into sentences with metadata
            sentences = self.sentence_splitter.split_sentences(text)
            logger.debug(f"Split into {len(sentences)} sentences")

            # Step 3: Create token-based chunks with metadata
            chunks = self._create_token_based_chunks(sentences, doc_structure)
            logger.info(
                f"Created {len(chunks)} chunks (avg tokens: {sum(c.token_count for c in chunks) // len(chunks) if chunks else 0})"
            )

            # Step 4: Save chunks to database with enhanced metadata
            saved_count = self._save_enhanced_chunks(chunks, document_id, db)

            # Step 5: Calculate quality score
            quality_score = self._calculate_quality_score(chunks)

            # Calculate metrics
            end_time = datetime.now(timezone.utc)
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            total_chars = sum(len(chunk.text) for chunk in chunks)
            avg_chunk_size = total_chars // len(chunks) if chunks else 0

            logger.info(
                f"Enhanced chunking completed for document {document_id}: "
                f"{saved_count} chunks saved, quality_score={quality_score:.2f}, {processing_time_ms}ms"
            )

            return ChunkingResult(
                success=True,
                chunk_count=saved_count,
                total_chars=total_chars,
                avg_chunk_size=avg_chunk_size,
                processing_time_ms=processing_time_ms,
                quality_score=quality_score,
            )

        except ValueError as e:
            logger.warning(f"Chunking validation failed for document {document_id}: {e}")
            end_time = datetime.now(timezone.utc)
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return ChunkingResult(
                success=False,
                processing_time_ms=processing_time_ms,
                error_message=str(e),
            )

        except Exception as e:
            logger.error(
                f"Enhanced chunking failed for document {document_id}: {e}",
                exc_info=True,
            )
            end_time = datetime.now(timezone.utc)
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return ChunkingResult(
                success=False,
                processing_time_ms=processing_time_ms,
                error_message=str(e),
            )

    def _create_token_based_chunks(
        self,
        sentences: List[Sentence],
        doc_structure: Optional[DocumentStructure],
    ) -> List[EnhancedChunk]:
        """
        Group sentences into chunks based on token counts

        Args:
            sentences: List of sentences with metadata
            doc_structure: Document structure metadata

        Returns:
            List of EnhancedChunk objects
        """
        chunks = []
        current_sentences = []
        current_tokens = 0
        chunk_index = 0

        for sentence in sentences:
            # Get accurate token count
            sentence_tokens = self.token_counter.count_tokens(sentence.text)

            # Check if adding this sentence would exceed max tokens
            if current_sentences and current_tokens + sentence_tokens > self.config.max_tokens:
                # Save current chunk
                chunk = self._build_chunk(
                    current_sentences,
                    chunk_index,
                    doc_structure,
                )
                chunks.append(chunk)
                chunk_index += 1

                # Start new chunk with overlap
                overlap_sentences = self._get_overlap_sentences(
                    current_sentences,
                    self.config.overlap_tokens,
                )
                current_sentences = overlap_sentences + [sentence]
                current_tokens = sum(
                    self.token_counter.count_tokens(s.text) for s in current_sentences
                )
            else:
                # Add sentence to current chunk
                current_sentences.append(sentence)
                current_tokens += sentence_tokens

                # Check if we've reached target size and should split at paragraph boundary
                if (
                    self.config.preserve_paragraphs
                    and current_tokens >= self.config.target_tokens
                    and not sentence.part_of_list
                ):
                    # Save chunk at natural paragraph boundary
                    chunk = self._build_chunk(
                        current_sentences,
                        chunk_index,
                        doc_structure,
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                    # Start new chunk with overlap
                    overlap_sentences = self._get_overlap_sentences(
                        current_sentences,
                        self.config.overlap_tokens,
                    )
                    current_sentences = overlap_sentences
                    current_tokens = sum(
                        self.token_counter.count_tokens(s.text) for s in current_sentences
                    )

        # Don't forget the last chunk
        if current_sentences:
            chunk = self._build_chunk(
                current_sentences,
                chunk_index,
                doc_structure,
            )
            chunks.append(chunk)

        return chunks

    def _get_overlap_sentences(
        self,
        sentences: List[Sentence],
        overlap_tokens: int,
    ) -> List[Sentence]:
        """
        Get sentences from end of list that fit within overlap token budget

        Args:
            sentences: List of sentences
            overlap_tokens: Target overlap in tokens

        Returns:
            List of sentences for overlap
        """
        overlap = []
        token_count = 0

        # Work backwards from end
        for sentence in reversed(sentences):
            sentence_tokens = self.token_counter.count_tokens(sentence.text)
            if token_count + sentence_tokens <= overlap_tokens:
                overlap.insert(0, sentence)
                token_count += sentence_tokens
            else:
                break

        return overlap

    def _build_chunk(
        self,
        sentences: List[Sentence],
        chunk_index: int,
        doc_structure: Optional[DocumentStructure],
    ) -> EnhancedChunk:
        """
        Build enhanced chunk from sentences with metadata

        Args:
            sentences: Sentences to include in chunk
            chunk_index: Index of this chunk
            doc_structure: Document structure metadata

        Returns:
            EnhancedChunk with text and metadata
        """
        # Combine sentence texts
        chunk_text = " ".join(s.text for s in sentences)

        # Calculate positions
        start_position = sentences[0].start_char if sentences else 0
        end_position = sentences[-1].end_char if sentences else 0

        # Count tokens accurately
        token_count = self.token_counter.count_tokens(chunk_text)

        # Extract metadata for this chunk
        metadata = self._extract_chunk_metadata(sentences, doc_structure, chunk_text)

        # Build JSONB metadata
        jsonb_metadata = self._build_jsonb_metadata(sentences, doc_structure)

        return EnhancedChunk(
            text=chunk_text,
            chunk_index=chunk_index,
            start_position=start_position,
            end_position=end_position,
            token_count=token_count,
            metadata=metadata,
            jsonb_metadata=jsonb_metadata,
        )

    def _extract_chunk_metadata(
        self,
        sentences: List[Sentence],
        doc_structure: Optional[DocumentStructure],
        chunk_text: str,
    ) -> ChunkMetadata:
        """
        Extract metadata for a chunk with detection of all 10 element types

        Detects chunk type from:
        - paragraph, list, table, heading, code
        - figure, equation, citation, footnote, definition

        Priority: code > table > equation > figure > definition > list > heading > citation > footnote > paragraph

        Args:
            sentences: Sentences in this chunk
            doc_structure: Document structure
            chunk_text: Full chunk text

        Returns:
            ChunkMetadata object
        """
        # Initialize chunk type detection flags
        chunk_type = "paragraph"  # Default
        is_heading = any(s.is_heading for s in sentences)
        is_list = any(s.part_of_list for s in sentences)

        # Find section headings
        section_heading = None
        subsection_heading = None
        if doc_structure and doc_structure.headings:
            # Find most recent heading before this chunk
            chunk_start = sentences[0].start_char if sentences else 0
            for heading in reversed(doc_structure.headings):
                if heading.start_char < chunk_start:
                    if heading.level <= 2:
                        section_heading = heading.text
                    else:
                        subsection_heading = heading.text
                    break

        # Calculate semantic density (ratio of content words to total words)
        words = chunk_text.split()
        content_words = [w for w in words if len(w) > 3 and w.isalpha()]
        semantic_density = len(content_words) / len(words) if words else 0.5

        # Detect special content types
        contains_table = False
        contains_list = False
        contains_code = False
        contains_equation = False
        contains_figure = False

        # Additional type detection (not stored as boolean flags but used for chunk_type)
        contains_citation = False
        contains_footnote = False
        contains_definition = False

        if doc_structure:
            chunk_start = sentences[0].start_char if sentences else 0
            chunk_end = sentences[-1].end_char if sentences else 0

            # Check if chunk overlaps with any special elements
            # Two ranges overlap if: NOT (range1_end < range2_start OR range1_start > range2_end)
            contains_table = any(
                not (table.end_char < chunk_start or table.start_char > chunk_end)
                for table in doc_structure.tables
            )

            contains_list = any(
                not (lst.end_char < chunk_start or lst.start_char > chunk_end)
                for lst in doc_structure.lists
            )

            contains_code = any(
                not (code.end_char < chunk_start or code.start_char > chunk_end)
                for code in doc_structure.code_blocks
            )

            contains_equation = any(
                not (eq.end_char < chunk_start or eq.start_char > chunk_end)
                for eq in doc_structure.equations
            )

            contains_figure = any(
                not (fig.end_char < chunk_start or fig.start_char > chunk_end)
                for fig in doc_structure.figures
            )

            # Detect citations, footnotes, and definitions
            contains_citation = any(
                not (cite.end_char < chunk_start or cite.start_char > chunk_end)
                for cite in doc_structure.citations
            )

            contains_footnote = any(
                # Footnotes store reference_char (single point), check if within chunk
                chunk_start <= note.reference_char <= chunk_end
                for note in doc_structure.footnotes
            )

            contains_definition = any(
                # Definitions store start_char and end_char for the term
                not (defn.end_char < chunk_start or defn.start_char > chunk_end)
                for defn in doc_structure.definitions
            )

        # Determine chunk_type with priority-based logic
        # Priority: code > table > equation > figure > definition > list > heading > citation > footnote > paragraph
        if contains_code:
            chunk_type = "code"
        elif contains_table:
            chunk_type = "table"
        elif contains_equation:
            chunk_type = "equation"
        elif contains_figure:
            chunk_type = "figure"
        elif contains_definition:
            chunk_type = "definition"
        elif is_list or contains_list:
            chunk_type = "list"
        elif is_heading:
            chunk_type = "heading"
        elif contains_citation:
            chunk_type = "citation"
        elif contains_footnote:
            chunk_type = "footnote"
        else:
            chunk_type = "paragraph"

        return ChunkMetadata(
            section_heading=section_heading,
            subsection_heading=subsection_heading,
            chunk_type=chunk_type,
            paragraph_index=0,  # Could calculate based on doc structure
            semantic_density=semantic_density,
            contains_table=contains_table,
            contains_list=contains_list,
            contains_code=contains_code,
            contains_equation=contains_equation,
            contains_figure=contains_figure,
            language="en",  # Could add language detection
        )

    def _build_jsonb_metadata(
        self,
        sentences: List[Sentence],
        doc_structure: Optional[DocumentStructure],
    ) -> Dict[str, Any]:
        """
        Build comprehensive JSONB metadata for chunk

        Args:
            sentences: Sentences in chunk
            doc_structure: Document structure

        Returns:
            Dictionary for JSONB storage
        """
        metadata: Dict[str, Any] = {
            "sentence_count": len(sentences),
            "has_headings": any(s.is_heading for s in sentences),
            "has_lists": any(s.part_of_list for s in sentences),
        }

        if doc_structure:
            chunk_start = sentences[0].start_char if sentences else 0
            chunk_end = sentences[-1].end_char if sentences else 0

            # Add overlapping element counts
            # Two ranges overlap if: NOT (range1_end < range2_start OR range1_start > range2_end)
            metadata["table_count"] = sum(
                1 for t in doc_structure.tables
                if not (t.end_char < chunk_start or t.start_char > chunk_end)
            )

            metadata["code_block_count"] = sum(
                1 for c in doc_structure.code_blocks
                if not (c.end_char < chunk_start or c.start_char > chunk_end)
            )

            metadata["equation_count"] = sum(
                1 for e in doc_structure.equations
                if not (e.end_char < chunk_start or e.start_char > chunk_end)
            )

            metadata["citation_count"] = sum(
                1 for c in doc_structure.citations
                if not (c.end_char < chunk_start or c.start_char > chunk_end)
            )

        return metadata

    def _save_enhanced_chunks(
        self,
        chunks: List[EnhancedChunk],
        document_id: UUID,
        db: Session,
    ) -> int:
        """
        Save enhanced chunks to database with metadata

        Args:
            chunks: List of EnhancedChunk objects
            document_id: Document UUID
            db: Database session

        Returns:
            Number of chunks saved
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
                    "chunk_tokens": chunk.token_count,
                    "start_position": chunk.start_position,
                    "end_position": chunk.end_position,
                    "embedding_model": "pending",  # No embedding yet
                    # Enhanced metadata fields
                    "section_heading": chunk.metadata.section_heading,
                    "subsection_heading": chunk.metadata.subsection_heading,
                    "chunk_type": chunk.metadata.chunk_type,
                    "paragraph_index": chunk.metadata.paragraph_index,
                    "semantic_density": chunk.metadata.semantic_density,
                    "contains_table": chunk.metadata.contains_table,
                    "contains_list": chunk.metadata.contains_list,
                    "contains_code": chunk.metadata.contains_code,
                    "contains_equation": chunk.metadata.contains_equation,
                    "contains_figure": chunk.metadata.contains_figure,
                    "language": chunk.metadata.language,
                    "chunk_metadata": chunk.jsonb_metadata,
                })

            # Bulk insert chunks
            if chunk_records:
                db.bulk_insert_mappings(Embedding, chunk_records)

            # Commit transaction
            db.commit()

            logger.info(f"Saved {len(chunks)} enhanced chunks for document {document_id}")
            return len(chunks)

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error saving enhanced chunks for document {document_id}: {e}")
            raise Exception(f"Failed to save enhanced chunks to database: {e}") from e

        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error saving enhanced chunks for document {document_id}: {e}")
            raise

    def _calculate_quality_score(self, chunks: List[EnhancedChunk]) -> float:
        """
        Calculate quality score for chunked document

        Evaluates chunk quality based on:
        1. Token distribution (optimal: 400-600 tokens/chunk)
        2. Metadata coverage (>80% have section_heading)
        3. Semantic density (>0.3 is good content)

        Args:
            chunks: List of EnhancedChunk objects

        Returns:
            Quality score from 0.0 to 1.0
        """
        if not chunks:
            return 0.0

        scores = []

        # 1. Token distribution score (40% weight)
        # Optimal range: 400-600 tokens
        avg_tokens = sum(c.token_count for c in chunks) / len(chunks)
        if 400 <= avg_tokens <= 600:
            token_score = 1.0
        elif 300 <= avg_tokens < 400:
            token_score = 0.7 + (avg_tokens - 300) / 100 * 0.3
        elif 600 < avg_tokens <= 800:
            token_score = 0.7 + (800 - avg_tokens) / 200 * 0.3
        else:
            token_score = 0.5
        scores.append(('token_distribution', token_score, 0.4))

        # 2. Metadata coverage score (30% weight)
        # Chunks with section headings indicate good structure extraction
        chunks_with_headings = sum(
            1 for c in chunks
            if c.metadata.section_heading is not None
        )
        metadata_coverage = chunks_with_headings / len(chunks)
        if metadata_coverage >= 0.8:
            metadata_score = 1.0
        elif metadata_coverage >= 0.5:
            metadata_score = 0.6 + (metadata_coverage - 0.5) / 0.3 * 0.4
        else:
            metadata_score = metadata_coverage / 0.5 * 0.6
        scores.append(('metadata_coverage', metadata_score, 0.3))

        # 3. Semantic density score (30% weight)
        # Average semantic density should be >0.3 for good content
        avg_density = sum(c.metadata.semantic_density for c in chunks) / len(chunks)
        if avg_density >= 0.5:
            density_score = 1.0
        elif avg_density >= 0.3:
            density_score = 0.6 + (avg_density - 0.3) / 0.2 * 0.4
        else:
            density_score = avg_density / 0.3 * 0.6
        scores.append(('semantic_density', density_score, 0.3))

        # Calculate weighted average
        quality_score = sum(score * weight for _, score, weight in scores)

        logger.debug(
            f"Quality score breakdown: "
            f"token={token_score:.2f} (avg={avg_tokens:.0f}), "
            f"metadata={metadata_score:.2f} (coverage={metadata_coverage:.1%}), "
            f"density={density_score:.2f} (avg={avg_density:.2f}), "
            f"final={quality_score:.2f}"
        )

        return round(quality_score, 2)


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
