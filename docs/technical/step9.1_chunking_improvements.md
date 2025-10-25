# Step 9.1: Chunking Improvements - Technical Documentation

**Version:** 1.0
**Last Updated:** October 24, 2024
**Status:** Planning Phase
**Timeline:** 2-3 days
**Dependencies:** Step 8.2 (Basic Chunking Implementation)

---

## 1. FEATURE OVERVIEW

### 1.1 What This Step Accomplishes

Step 9.1 enhances the text chunking pipeline to produce high-quality, semantically meaningful chunks optimized for embedding generation. This improvement moves from basic character-based chunking to intelligent, context-aware chunking that:

1. **Preserves Semantic Boundaries**: Uses advanced NLP libraries (spaCy/NLTK) for accurate sentence detection
2. **Maintains Document Structure**: Retains paragraph boundaries, headings, and document hierarchy
3. **Enriches Chunk Metadata**: Adds contextual information (headings, tables, page numbers, section info)
4. **Optimizes for BGE-M3**: Targets 512 tokens per chunk (vs current 1000 characters ≈ 250 tokens)
5. **Improves Retrieval Quality**: Better chunks → better embeddings → more accurate search results

### 1.2 Why This Step is Necessary

**Current Limitations (Step 8.2):**
- Simple regex-based sentence splitting: `r'(?<=[.!?])\s+(?=[A-Z])'`
  - Fails on abbreviations (Dr. Smith, U.S.A., etc.)
  - Misses sentence boundaries in lists, tables, or dialogue
  - Cannot handle complex punctuation patterns
- Character-based chunking (1000 chars) doesn't align with token limits
  - BGE-M3 model expects ~512 tokens (≈2048 characters for English)
  - Current chunks are too small, losing context
- No structural awareness
  - Chunks can split mid-paragraph or mid-section
  - Headers separated from their content
  - Tables and code blocks split awkwardly
- Minimal metadata
  - Only tracks: `start_position`, `end_position`, `page_number`
  - Missing: section headings, chunk type, semantic context
- Crude token estimation (`chars // 4`)
  - Inaccurate for non-English text
  - Doesn't account for special characters, code, or formatting

**Impact on System Performance:**
- Lower retrieval accuracy (estimated <70% recall@10)
- Poor citation quality (chunks don't align with natural text units)
- Embedding inefficiency (suboptimal chunk sizes for model)

### 1.3 Dependencies on Previous Steps

| Step | Dependency | Required Data/Functionality |
|------|-----------|----------------------------|
| **Step 8.1** | Text Extraction | `document_texts.full_text` contains extracted PDF text |
| **Step 8.2** | Basic Chunking | Database schema (`embeddings` table), chunking service framework |
| **Step 8.3** | Keyword Search | Search functionality to validate chunking quality improvements |
| **Step 9.0** | pgvector Setup | `embeddings.embedding` column exists for vector storage |

**Required Database Tables:**
- `documents` - Document metadata
- `document_texts` - Extracted text storage
- `embeddings` - Chunk storage with vector support
- `processing_status` - Pipeline tracking

### 1.4 What Future Steps Depend on This

| Step | Dependency Reason |
|------|------------------|
| **Step 9.2** | Embedding generation expects 512-token chunks optimized for BGE-M3 |
| **Step 9.3** | Vector search quality depends on chunk quality (garbage in, garbage out) |
| **Step 10** | Hybrid retrieval combines BM25 (keyword) + vector; both need good chunks |
| **Step 11** | LLM answer generation relies on retrieving coherent, complete chunks with proper context |

**Key Deliverable:** High-quality chunks that preserve semantic meaning and document structure, ready for accurate embedding generation.

---

## 2. TECHNICAL IMPLEMENTATION

### 2.1 Files to Create

```
backend/
├── app/
│   ├── services/
│   │   └── chunking/
│   │       ├── __init__.py (updated)
│   │       ├── chunking_service.py (MODIFY - enhance existing)
│   │       ├── sentence_splitter.py (NEW - spaCy/NLTK integration)
│   │       ├── metadata_extractor.py (NEW - extract headings, structure)
│   │       └── token_counter.py (NEW - accurate token counting)
│   └── schemas/
│       └── chunking.py (NEW - enhanced chunk schemas)
└── tests/
    └── unit/
        └── services/
            └── chunking/
                ├── test_sentence_splitter.py (NEW)
                ├── test_metadata_extractor.py (NEW)
                └── test_enhanced_chunking_service.py (MODIFY)
```

### 2.2 Files to Modify

| File Path | Modifications Required |
|-----------|----------------------|
| `app/services/chunking/chunking_service.py` | Add spaCy integration, token-based chunking, metadata extraction |
| `app/models/embedding.py` | Add new columns: `section_heading`, `chunk_type`, `semantic_density` |
| `app/tasks/chunking_tasks.py` | Update to handle enhanced metadata, add quality validation |
| `requirements.txt` | Add: `spacy>=3.7.0`, `nltk>=3.8.1`, `tiktoken>=0.5.0` |
| `db/migrations/` | Create migration: `v004_add_chunk_metadata.sql` |

### 2.3 Key Classes and Functions

#### 2.3.1 Enhanced ChunkingService

```python
# app/services/chunking/chunking_service.py

class EnhancedChunkingConfig:
    """Configuration for enhanced chunking"""
    target_tokens: int = 512  # BGE-M3 optimized
    max_tokens: int = 600      # Hard limit (model max = 8192, but smaller is better)
    min_tokens: int = 100      # Minimum viable chunk
    overlap_tokens: int = 50   # Token-based overlap (vs char-based)
    preserve_paragraphs: bool = True
    extract_metadata: bool = True
    use_spacy: bool = True     # Fallback to NLTK if False


class ChunkMetadata:
    """Rich metadata for each chunk"""
    section_heading: Optional[str]      # Nearest H1/H2/H3 heading
    subsection_heading: Optional[str]   # Nearest H4/H5/H6 heading
    chunk_type: str                     # "paragraph", "list", "table", "code", "heading"
    paragraph_index: int                # Which paragraph in section
    semantic_density: float             # Ratio of content words to total words
    contains_table: bool
    contains_list: bool
    language: str = "en"                # Detected language



class EnhancedChunkingService:
    """Improved chunking service with NLP-based sentence detection"""

    def __init__(self, config: EnhancedChunkingConfig = None):
        self.config = config or EnhancedChunkingConfig()
        self.sentence_splitter = SentenceSplitter(use_spacy=self.config.use_spacy)
        self.token_counter = TokenCounter(model="gpt-3.5-turbo")  # Compatible with BGE-M3
        self.metadata_extractor = MetadataExtractor()

    def chunk_text_enhanced(
        self,
        text: str,
        document_id: UUID,
        db: Session,
        document_metadata: Optional[Dict] = None
    ) -> ChunkingResult:
        """
        Enhanced chunking with semantic boundaries and metadata

        Steps:
        1. Extract document structure (headings, paragraphs, tables)
        2. Split into sentences using spaCy
        3. Group sentences into token-based chunks
        4. Preserve paragraph/section boundaries
        5. Add rich metadata to each chunk
        6. Save to database with metadata
        """
        pass

    def _extract_structure(self, text: str) -> DocumentStructure:
        """Extract headings, paragraphs, lists, tables from text"""
        pass

    def _create_semantic_chunks(
        self,
        sentences: List[Sentence],
        structure: DocumentStructure
    ) -> List[EnhancedChunk]:
        """Create chunks respecting semantic boundaries"""
        pass
```

#### 2.3.2 SentenceSplitter (NEW)

```python
# app/services/chunking/sentence_splitter.py

import spacy
import nltk
from typing import List, Optional

class Sentence:
    """Represents a sentence with metadata"""
    text: str
    start_char: int
    end_char: int
    tokens: List[str]
    token_count: int
    is_heading: bool
    part_of_list: bool


class SentenceSplitter:
    """Intelligent sentence splitting with spaCy/NLTK"""

    def __init__(self, use_spacy: bool = True):
        self.use_spacy = use_spacy

        if use_spacy:
            try:
                # Load spaCy model (en_core_web_sm)
                self.nlp = spacy.load("en_core_web_sm", disable=["ner", "parser"])
                self.nlp.add_pipe("sentencizer")
            except OSError:
                # Fallback to NLTK if spaCy model not found
                logger.warning("spaCy model not found, falling back to NLTK")
                self.use_spacy = False

        if not self.use_spacy:
            # Download NLTK punkt tokenizer if needed
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)

    def split_sentences(self, text: str) -> List[Sentence]:
        """Split text into sentences with metadata"""
        if self.use_spacy:
            return self._split_with_spacy(text)
        else:
            return self._split_with_nltk(text)

    def _split_with_spacy(self, text: str) -> List[Sentence]:
        """Use spaCy for sentence splitting (more accurate)"""
        doc = self.nlp(text)
        sentences = []

        for sent in doc.sents:
            sentences.append(Sentence(
                text=sent.text.strip(),
                start_char=sent.start_char,
                end_char=sent.end_char,
                tokens=[token.text for token in sent],
                token_count=len(sent),
                is_heading=self._is_heading(sent.text),
                part_of_list=self._is_list_item(sent.text)
            ))

        return sentences

    def _split_with_nltk(self, text: str) -> List[Sentence]:
        """Fallback to NLTK sentence tokenizer"""
        from nltk.tokenize import sent_tokenize, word_tokenize

        sentences = []
        offset = 0

        for sent_text in sent_tokenize(text):
            start_char = text.find(sent_text, offset)
            end_char = start_char + len(sent_text)
            tokens = word_tokenize(sent_text)

            sentences.append(Sentence(
                text=sent_text.strip(),
                start_char=start_char,
                end_char=end_char,
                tokens=tokens,
                token_count=len(tokens),
                is_heading=self._is_heading(sent_text),
                part_of_list=self._is_list_item(sent_text)
            ))

            offset = end_char

        return sentences

    @staticmethod
    def _is_heading(text: str) -> bool:
        """Detect if sentence is likely a heading"""
        # Heuristics: short, titlecase, ends without punctuation
        return (
            len(text) < 100 and
            text[0].isupper() and
            not text.endswith(('.', '!', '?', ',')) and
            sum(1 for c in text if c.isupper()) / len(text) > 0.3
        )

    @staticmethod
    def _is_list_item(text: str) -> bool:
        """Detect if sentence is part of a list"""
        import re
        # Check for list markers: bullets, numbers, dashes
        return bool(re.match(r'^\s*[-•*◦▪▫\d+\.)\]]\s+', text))
```

#### 2.3.3 TokenCounter (NEW)

```python
# app/services/chunking/token_counter.py

import tiktoken
from typing import Optional

class TokenCounter:
    """Accurate token counting using tiktoken (OpenAI's tokenizer)"""

    def __init__(self, model: str = "gpt-3.5-turbo"):
        """
        Initialize token counter

        Args:
            model: Model name for tokenizer (gpt-3.5-turbo compatible with BGE-M3)
        """
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base (used by gpt-3.5-turbo, gpt-4)
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count exact tokens in text"""
        return len(self.encoding.encode(text))

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to specified token count"""
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text

        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens)
```

#### 2.3.4 MetadataExtractor (NEW)

```python
# app/services/chunking/metadata_extractor.py

import re
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class DocumentStructure:
    """Represents document structure"""
    headings: List[Heading]
    paragraphs: List[Paragraph]
    tables: List[Table]
    lists: List[ListBlock]

@dataclass
class Heading:
    text: str
    level: int  # 1-6 for H1-H6
    start_char: int
    end_char: int

@dataclass
class Paragraph:
    text: str
    start_char: int
    end_char: int
    parent_heading: Optional[str]

class MetadataExtractor:
    """Extract structural metadata from document text"""

    def extract_structure(self, text: str) -> DocumentStructure:
        """
        Extract document structure

        Detects:
        - Headings (Markdown-style # or underlined)
        - Paragraphs (double newline separated)
        - Tables (grid patterns)
        - Lists (bullets, numbers)
        """
        return DocumentStructure(
            headings=self._extract_headings(text),
            paragraphs=self._extract_paragraphs(text),
            tables=self._extract_tables(text),
            lists=self._extract_lists(text)
        )

    def _extract_headings(self, text: str) -> List[Heading]:
        """
        Extract headings using multiple heuristics:
        1. Markdown-style (# Heading)
        2. Underlined (Heading\\n====)
        3. ALL CAPS short lines
        4. Title case at paragraph start
        """
        headings = []

        # Markdown-style headings
        for match in re.finditer(r'^(#{1,6})\s+(.+)$', text, re.MULTILINE):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            headings.append(Heading(
                text=heading_text,
                level=level,
                start_char=match.start(),
                end_char=match.end()
            ))

        # TODO: Add underlined headings, ALL CAPS detection

        return headings

    def _extract_paragraphs(self, text: str) -> List[Paragraph]:
        """Extract paragraphs (double newline separated)"""
        paragraphs = []
        current_heading = None

        # Split on double newlines
        blocks = re.split(r'\n\s*\n', text)
        offset = 0

        for block in blocks:
            block_stripped = block.strip()
            if not block_stripped:
                offset += len(block) + 2  # Account for newlines
                continue

            start_char = text.find(block_stripped, offset)
            end_char = start_char + len(block_stripped)

            paragraphs.append(Paragraph(
                text=block_stripped,
                start_char=start_char,
                end_char=end_char,
                parent_heading=current_heading
            ))

            offset = end_char

        return paragraphs

    def _extract_tables(self, text: str) -> List:
        """Detect table patterns (simple heuristic)"""
        # TODO: Implement table detection (look for grid patterns, |---|---|)
        return []

    def _extract_lists(self, text: str) -> List:
        """Detect list blocks"""
        # TODO: Implement list detection (consecutive lines starting with bullets/numbers)
        return []
```

### 2.4 Database Schema Changes

#### New Migration: `v004_add_chunk_metadata.sql`

```sql
-- Migration: Add enhanced metadata columns to embeddings table
-- Version: v004
-- Created: 2024-10-24

BEGIN;

-- Add new metadata columns
ALTER TABLE embeddings
ADD COLUMN IF NOT EXISTS section_heading VARCHAR(500),
ADD COLUMN IF NOT EXISTS subsection_heading VARCHAR(500),
ADD COLUMN IF NOT EXISTS chunk_type VARCHAR(50) DEFAULT 'paragraph',
ADD COLUMN IF NOT EXISTS paragraph_index INTEGER,
ADD COLUMN IF NOT EXISTS semantic_density FLOAT,
ADD COLUMN IF NOT EXISTS contains_table BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS contains_list BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en';

-- Add index on section_heading for filtering
CREATE INDEX IF NOT EXISTS idx_embeddings_section_heading
ON embeddings(section_heading)
WHERE section_heading IS NOT NULL;

-- Add index on chunk_type for categorization
CREATE INDEX IF NOT EXISTS idx_embeddings_chunk_type
ON embeddings(chunk_type);

-- Update existing rows with defaults
UPDATE embeddings
SET chunk_type = 'paragraph',
    semantic_density = 0.5,
    contains_table = FALSE,
    contains_list = FALSE,
    language = 'en'
WHERE chunk_type IS NULL;

COMMIT;

-- Rollback script (save separately as v004_rollback.sql)
-- BEGIN;
-- ALTER TABLE embeddings
-- DROP COLUMN IF EXISTS section_heading,
-- DROP COLUMN IF EXISTS subsection_heading,
-- DROP COLUMN IF EXISTS chunk_type,
-- DROP COLUMN IF EXISTS paragraph_index,
-- DROP COLUMN IF EXISTS semantic_density,
-- DROP COLUMN IF EXISTS contains_table,
-- DROP COLUMN IF EXISTS contains_list,
-- DROP COLUMN IF EXISTS language;
-- COMMIT;
```

### 2.5 API Endpoints

**No new API endpoints** - This step enhances internal processing. Existing endpoints remain:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/upload` | Trigger processing pipeline (includes enhanced chunking) |
| GET | `/api/v1/documents/{id}` | Retrieve document with chunk statistics |
| POST | `/api/v1/search` | Search chunks (benefits from improved chunking quality) |

**Response Schema Enhancement:**

```python
# app/schemas/document.py

class DocumentResponse(BaseModel):
    # ... existing fields ...

    chunking_metadata: Optional[Dict] = None  # NEW

    class Config:
        schema_extra = {
            "example": {
                # ... existing example ...
                "chunking_metadata": {
                    "chunk_count": 45,
                    "avg_tokens": 487,
                    "chunk_types": {
                        "paragraph": 38,
                        "heading": 5,
                        "list": 2
                    },
                    "has_structure": True
                }
            }
        }
```

### 2.6 Background Tasks

**Modified Task:** `app.tasks.chunking_tasks.chunk_document_text`

```python
# Key changes:
# 1. Use EnhancedChunkingService instead of ChunkingService
# 2. Pass document metadata to chunking service
# 3. Validate chunk quality before marking complete

@celery_app.task(name="app.tasks.chunking_tasks.chunk_document_text")
def chunk_document_text(document_id: str):
    # ... existing setup ...

    # NEW: Get document metadata for structure detection
    document_metadata = {
        "mime_type": document.mime_type,
        "original_name": document.original_name,
        "file_size": document.file_size
    }

    # Use enhanced chunking service
    chunking_service = get_enhanced_chunking_service()

    result = chunking_service.chunk_text_enhanced(
        text=document_text.full_text,
        document_id=doc_uuid,
        db=db,
        document_metadata=document_metadata  # NEW
    )

    # NEW: Validate chunk quality
    if result.success:
        quality_score = validate_chunk_quality(result)
        if quality_score < 0.7:  # Quality threshold
            logger.warning(
                f"Low chunk quality for document {document_id}: {quality_score}"
            )

    # ... rest of task ...
```

---

## 3. DATA FLOW

### 3.1 Step-by-Step Data Journey

```
┌─────────────────────────────────────────────────────────────┐
│                    ENHANCED CHUNKING PIPELINE                │
└─────────────────────────────────────────────────────────────┘

1. TRIGGER
   ├─ Celery Task: chunk_document_text(document_id)
   ├─ Source: Extraction task completion
   └─ Input: document_id (UUID)

2. FETCH DOCUMENT DATA
   ├─ Query: documents table → get metadata
   ├─ Query: document_texts table → get full_text
   └─ Output: (text: str, metadata: Dict)

3. EXTRACT STRUCTURE (NEW)
   ├─ Input: full_text (10,000 chars example)
   ├─ MetadataExtractor.extract_structure()
   │   ├─ Detect headings (Markdown # or patterns)
   │   ├─ Split into paragraphs (double newline)
   │   ├─ Find tables (grid patterns)
   │   └─ Identify lists (bullets, numbers)
   └─ Output: DocumentStructure
       ├─ headings: 5 headings detected
       ├─ paragraphs: 23 paragraphs
       ├─ tables: 1 table
       └─ lists: 3 list blocks

4. SENTENCE SPLITTING (ENHANCED)
   ├─ Input: full_text + DocumentStructure
   ├─ SentenceSplitter.split_sentences() [spaCy/NLTK]
   │   ├─ Load spaCy model (en_core_web_sm)
   │   ├─ Apply sentencizer pipeline
   │   ├─ Extract sentence boundaries
   │   └─ Add metadata (is_heading, part_of_list)
   └─ Output: List[Sentence]
       └─ 87 sentences with metadata

5. TOKEN COUNTING (NEW)
   ├─ Input: List[Sentence]
   ├─ TokenCounter.count_tokens() [tiktoken]
   │   ├─ Use cl100k_base encoding (GPT-3.5/4 compatible)
   │   └─ Count exact tokens per sentence
   └─ Output: Sentences with token_count
       └─ Total: 2,456 tokens

6. SEMANTIC CHUNKING (ENHANCED)
   ├─ Input: List[Sentence] + DocumentStructure
   ├─ EnhancedChunkingService._create_semantic_chunks()
   │   ├─ Target: 512 tokens per chunk
   │   ├─ Preserve paragraph boundaries
   │   ├─ Keep headings with content
   │   ├─ Add 50-token overlap
   │   └─ Attach metadata from structure
   └─ Output: List[EnhancedChunk] (5 chunks)
       ├─ Chunk 0: 487 tokens, type=paragraph, heading="Introduction"
       ├─ Chunk 1: 523 tokens, type=paragraph, heading="Methods"
       ├─ Chunk 2: 456 tokens, type=list, contains_list=True
       ├─ Chunk 3: 501 tokens, type=paragraph, heading="Results"
       └─ Chunk 4: 489 tokens, type=paragraph, heading="Conclusion"

7. METADATA ENRICHMENT
   ├─ Input: List[EnhancedChunk]
   ├─ For each chunk:
   │   ├─ Find nearest heading → section_heading
   │   ├─ Calculate semantic_density (content words / total)
   │   ├─ Detect chunk_type (paragraph/list/table/heading)
   │   └─ Add language detection
   └─ Output: Chunks with rich metadata

8. DATABASE PERSISTENCE
   ├─ Transaction START
   ├─ DELETE old chunks (document_id = uuid)
   ├─ Bulk INSERT new chunks to embeddings table
   │   ├─ Columns: id, document_id, chunk_index, chunk_text
   │   ├─ Columns: chunk_tokens, start_position, end_position
   │   ├─ Columns: section_heading, chunk_type, semantic_density
   │   ├─ Columns: contains_table, contains_list, language
   │   └─ embedding = NULL (filled in Step 9.2)
   ├─ UPDATE processing_status → CHUNKING = COMPLETED
   └─ COMMIT

9. QUALITY VALIDATION (NEW)
   ├─ Check avg chunk size (target: 400-600 tokens)
   ├─ Verify metadata coverage (>80% have headings)
   ├─ Calculate semantic_density distribution
   └─ Log quality metrics

10. RESULT
    └─ Return ChunkingResult
        ├─ success: True
        ├─ chunk_count: 5
        ├─ avg_chunk_size: 491 tokens
        ├─ quality_score: 0.87
        └─ processing_time_ms: 1,234
```

### 3.2 Input → Processing → Output Detail

| Stage | Input | Processing | Output |
|-------|-------|-----------|--------|
| **Fetch** | `document_id` | Query DB | `(full_text, metadata)` |
| **Structure** | `full_text: str` | Regex + Heuristics | `DocumentStructure` |
| **Sentences** | `full_text: str` | spaCy NLP pipeline | `List[Sentence]` (87 items) |
| **Tokens** | `List[Sentence]` | tiktoken encoding | Token counts (2,456 total) |
| **Chunking** | `List[Sentence]` | Group by 512 tokens | `List[EnhancedChunk]` (5 items) |
| **Metadata** | `EnhancedChunk` | Structure mapping | Chunks + metadata |
| **Persist** | `List[EnhancedChunk]` | SQL bulk insert | Database rows |

### 3.3 Database Transactions

```sql
-- Transaction sequence:

BEGIN;

-- 1. Delete old chunks (if re-processing)
DELETE FROM embeddings WHERE document_id = 'abc-123...';
-- Result: 3 rows deleted (old chunks)

-- 2. Insert new chunks
INSERT INTO embeddings (
    id, document_id, chunk_index, chunk_text, chunk_tokens,
    embedding, start_position, end_position, page_number,
    section_heading, chunk_type, semantic_density,
    contains_table, contains_list, language,
    embedding_model, created_at
) VALUES
    (uuid_generate_v4(), 'abc-123...', 0, 'Introduction text...', 487, NULL, 0, 1234, 1,
     'Introduction', 'paragraph', 0.72, FALSE, FALSE, 'en', 'pending', NOW()),
    (uuid_generate_v4(), 'abc-123...', 1, 'Methods section...', 523, NULL, 1184, 2567, 1,
     'Methods', 'paragraph', 0.68, FALSE, FALSE, 'en', 'pending', NOW()),
    -- ... 3 more chunks
;
-- Result: 5 rows inserted

-- 3. Update processing status
UPDATE processing_status
SET status = 'COMPLETED',
    completed_at = NOW(),
    duration_ms = 1234,
    result_data = '{"chunk_count": 5, "avg_tokens": 491}'::jsonb
WHERE document_id = 'abc-123...' AND stage = 'CHUNKING';

-- 4. Update document timestamp
UPDATE documents
SET last_indexed_at = NOW()
WHERE id = 'abc-123...';

COMMIT;
```

### 3.4 File System Operations

**None** - This step operates purely on database text. No file I/O except:
- Loading spaCy model (cached in memory after first load)
- NLTK data (downloaded once to `~/nltk_data/`)

---

## 4. VALIDATIONS & CONSTRAINTS

### 4.1 Input Validations

| Validation | Check | Error Response |
|------------|-------|----------------|
| **Text existence** | `document_text IS NOT NULL` | `"No extracted text found"` |
| **Text length** | `len(text) >= 100 chars` | `"Text too short for chunking"` |
| **Document exists** | `document_id IN documents` | `"Document not found"` |
| **Extraction complete** | `processing_status.EXTRACTION = COMPLETED` | `"Text extraction must complete first"` |
| **Token count** | `total_tokens >= 50` | `"Insufficient content for meaningful chunks"` |

### 4.2 Business Rules Enforced

1. **Chunk Size Constraints:**
   ```python
   MIN_TOKENS = 100  # Chunks smaller than this are merged
   TARGET_TOKENS = 512  # Optimal for BGE-M3
   MAX_TOKENS = 600  # Hard limit to prevent truncation
   ```

2. **Overlap Rules:**
   ```python
   OVERLAP_TOKENS = 50  # 10% overlap for context continuity
   # Overlap text comes from end of previous chunk
   # Ensures no information loss at boundaries
   ```

3. **Structure Preservation:**
   - Never split mid-sentence
   - Prefer paragraph boundaries for chunk breaks
   - Keep headings with at least one paragraph of content
   - Tables and code blocks stay together (if possible)

4. **Metadata Requirements:**
   - Every chunk must have `chunk_type` (paragraph/list/table/heading/code)
   - `semantic_density` calculated for all text chunks
   - `section_heading` populated if heading found within 500 chars

5. **Quality Thresholds:**
   ```python
   MIN_QUALITY_SCORE = 0.6  # Warn if below
   TARGET_QUALITY_SCORE = 0.8  # Ideal

   # Quality factors:
   # - Avg chunk size 400-600 tokens: +0.3
   # - >80% chunks have headings: +0.3
   # - Semantic density 0.5-0.8: +0.2
   # - No chunks < 100 tokens: +0.2
   ```

### 4.3 Security Checks

| Check | Implementation | Purpose |
|-------|----------------|---------|
| **Input sanitization** | Strip null bytes, control characters | Prevent injection |
| **Token limit** | Enforce `MAX_TOKENS = 600` | Prevent memory overflow |
| **Text length limit** | Max 10 million chars | Prevent DoS via huge docs |
| **Regex timeout** | `re.match(..., timeout=5s)` (Python 3.11+) | Prevent ReDoS attacks |
| **spaCy pipeline limit** | Disable unused pipes (ner, parser) | Reduce attack surface |

### 4.4 Error Conditions Handled

```python
# Error hierarchy:

1. ValidationError (don't retry)
   ├─ Text too short
   ├─ Document not found
   └─ Invalid UTF-8 encoding

2. ProcessingError (retry up to 3 times)
   ├─ spaCy model loading failure
   ├─ Token counting error
   └─ Sentence splitting timeout

3. DatabaseError (retry with backoff)
   ├─ Connection timeout
   ├─ Unique constraint violation
   └─ Transaction deadlock

4. SystemError (alert, don't retry)
   ├─ Out of memory
   ├─ Disk full
   └─ spaCy model corrupted
```

### 4.5 Rate Limits & Quotas

**No direct rate limits** (internal processing task), but:

```python
# Celery task configuration
@celery_app.task(
    time_limit=300,        # 5 minutes max per document
    soft_time_limit=240,   # Warn at 4 minutes
    max_retries=3,
    default_retry_delay=60  # 1 minute between retries
)
```

**Resource quotas:**
- spaCy max text length: 1 million characters per call
- Token counter batch size: 100 sentences at once
- Database bulk insert: 1000 chunks max per transaction

---

## 5. CONFIGURATION

### 5.1 Environment Variables

```bash
# .env configuration

# Chunking Parameters
CHUNK_TARGET_TOKENS=512        # Optimal for BGE-M3 (default: 512)
CHUNK_MAX_TOKENS=600          # Hard limit (default: 600)
CHUNK_MIN_TOKENS=100          # Minimum viable chunk (default: 100)
CHUNK_OVERLAP_TOKENS=50       # Overlap between chunks (default: 50)

# NLP Settings
USE_SPACY=true                # Use spaCy vs NLTK (default: true)
SPACY_MODEL=en_core_web_sm    # spaCy model name (default: en_core_web_sm)
NLTK_DATA_PATH=~/nltk_data    # NLTK data directory (default: ~/nltk_data)

# Token Counter
TOKENIZER_MODEL=gpt-3.5-turbo # tiktoken model (default: gpt-3.5-turbo)

# Quality Thresholds
MIN_QUALITY_SCORE=0.6         # Warn below this (default: 0.6)
TARGET_QUALITY_SCORE=0.8      # Target quality (default: 0.8)

# Processing Limits
MAX_TEXT_LENGTH=10000000      # 10M chars max (default: 10M)
SENTENCE_SPLIT_TIMEOUT=30     # Timeout in seconds (default: 30)

# Feature Flags
PRESERVE_PARAGRAPHS=true      # Respect paragraph boundaries (default: true)
EXTRACT_METADATA=true         # Add rich metadata (default: true)
DETECT_STRUCTURE=true         # Extract headings/lists/tables (default: true)
```

### 5.2 Default Values & Limits

| Parameter | Default | Min | Max | Notes |
|-----------|---------|-----|-----|-------|
| `target_tokens` | 512 | 100 | 8192 | BGE-M3 supports up to 8192, but smaller is better |
| `overlap_tokens` | 50 | 0 | 200 | ~10% overlap recommended |
| `min_chunk_size` | 100 | 50 | 500 | Too small = poor embeddings |
| `max_chunk_size` | 600 | 512 | 1000 | Stay under model limits |
| `semantic_density_threshold` | 0.3 | 0.1 | 1.0 | Below 0.3 = likely noise |
| `quality_score_warn` | 0.6 | 0.0 | 1.0 | Log warning if below |

### 5.3 File Paths & Directory Structure

```
backend/
├── .env                              # Environment configuration
├── .env.example                      # Template with defaults
├── requirements.txt                  # Python dependencies
│   ├── spacy>=3.7.0                 # Sentence splitting
│   ├── en-core-web-sm>=3.7.0        # spaCy English model
│   ├── nltk>=3.8.1                  # Fallback sentence splitting
│   └── tiktoken>=0.5.0              # Token counting
│
├── app/
│   ├── services/
│   │   └── chunking/
│   │       ├── __init__.py
│   │       ├── chunking_service.py   # Main service (MODIFIED)
│   │       ├── sentence_splitter.py  # NEW
│   │       ├── metadata_extractor.py # NEW
│   │       └── token_counter.py      # NEW
│   │
│   └── models/
│       └── embedding.py              # MODIFIED (add metadata columns)
│
├── db/
│   └── migrations/
│       └── v004_add_chunk_metadata.sql  # NEW migration
│
└── tests/
    └── unit/
        └── services/
            └── chunking/
                ├── test_sentence_splitter.py
                ├── test_metadata_extractor.py
                └── test_token_counter.py
```

### 5.4 Docker Services Required

**No new Docker services** - Uses existing:

```yaml
# docker/docker-compose.yml (existing services)

services:
  postgres:
    image: pgvector/pgvector:pg15  # ✅ Already configured

  redis:
    image: redis:7-alpine          # ✅ Celery broker

  celery-worker:
    # ✅ Runs chunking tasks
    command: celery -A app.celery_app worker --loglevel=info
```

**Setup Requirements:**

```bash
# 1. Install spaCy model (run once)
python -m spacy download en_core_web_sm

# 2. Download NLTK data (fallback, run once)
python -c "import nltk; nltk.download('punkt')"

# 3. Run database migration
docker exec querybox-postgres psql -U querybox -d querybox_core -f /migrations/v004_add_chunk_metadata.sql
```

---

## 6. ERROR HANDLING

### 6.1 Failure Scenarios

#### Scenario 1: spaCy Model Not Found

```python
# Error:
OSError: [E050] Can't find model 'en_core_web_sm'

# Recovery:
1. Detect error in SentenceSplitter.__init__
2. Log warning: "spaCy model not found, falling back to NLTK"
3. Set self.use_spacy = False
4. Continue with NLTK tokenizer
5. Task completes successfully (degraded mode)

# Prevention:
- Add spaCy model to Dockerfile: RUN python -m spacy download en_core_web_sm
- Check model existence at startup
```

#### Scenario 2: Text Contains Invalid UTF-8

```python
# Error:
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff

# Recovery:
1. Catch in chunk_text_enhanced()
2. Try encoding detection: chardet.detect(raw_bytes)
3. Convert to UTF-8: text.encode('utf-8', errors='replace').decode('utf-8')
4. Log warning with document_id
5. Continue processing (some chars become �)

# Prevention:
- Validate encoding during text extraction (Step 8.1)
- Store detected encoding in document_texts table
```

#### Scenario 3: Document Text Too Short

```python
# Error:
ValidationError: "Text too short: 45 chars (minimum: 100)"

# Recovery:
1. Don't retry (validation error)
2. Mark processing_status.CHUNKING = FAILED
3. Set error_message in status
4. Return error to caller
5. Document stays in EXTRACTION_COMPLETED state

# User action required:
- Re-upload document with more content
- Or skip chunking for this document
```

#### Scenario 4: Database Connection Lost During Bulk Insert

```python
# Error:
OperationalError: connection to server lost

# Recovery:
1. Catch SQLAlchemyError in save_chunks()
2. Rollback transaction
3. Retry task (Celery auto-retry with backoff)
4. Exponential backoff: 60s → 120s → 240s
5. After 3 failures: mark FAILED, alert admin

# Rollback:
- No chunks saved (transaction atomicity)
- Old chunks remain if they existed
```

#### Scenario 5: Chunk Quality Below Threshold

```python
# Scenario:
quality_score = 0.52  # Below MIN_QUALITY_SCORE (0.6)

# Recovery:
1. Log warning (not error): "Low chunk quality for document_id: 0.52"
2. Add to result_data: {"quality_score": 0.52, "quality_warning": true}
3. Continue (don't fail task)
4. Mark CHUNKING = COMPLETED (with warning flag)
5. Admin can review low-quality chunks later

# Not a failure:
- Chunks are still usable
- Search may be less accurate, but functional
```

### 6.2 Error Messages & Codes

```python
# Standardized error codes

class ChunkingErrorCode(Enum):
    # Validation errors (4xx equivalent)
    TEXT_TOO_SHORT = "CHUNK_E001"
    DOCUMENT_NOT_FOUND = "CHUNK_E002"
    NO_EXTRACTED_TEXT = "CHUNK_E003"
    INVALID_ENCODING = "CHUNK_E004"

    # Processing errors (5xx equivalent)
    SENTENCE_SPLIT_FAILED = "CHUNK_E101"
    TOKEN_COUNT_FAILED = "CHUNK_E102"
    METADATA_EXTRACTION_FAILED = "CHUNK_E103"

    # System errors (5xx critical)
    SPACY_MODEL_ERROR = "CHUNK_E201"
    DATABASE_ERROR = "CHUNK_E202"
    OUT_OF_MEMORY = "CHUNK_E203"

# Error response format
{
    "success": false,
    "error_code": "CHUNK_E001",
    "error_message": "Text too short: 45 chars (minimum: 100)",
    "document_id": "abc-123-...",
    "retry_after": null,  # Don't retry validation errors
    "details": {
        "text_length": 45,
        "min_required": 100
    }
}
```

### 6.3 Recovery Mechanisms

| Error Type | Recovery Strategy | Max Retries | Backoff |
|------------|------------------|-------------|---------|
| **Validation** | Fail immediately, log | 0 | N/A |
| **Processing** | Retry with fallback | 3 | Exponential (60s, 120s, 240s) |
| **Database** | Retry with reconnect | 3 | Exponential |
| **System** | Alert admin, fail | 0 | N/A |

**Retry Logic:**

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(SQLAlchemyError, ConnectionError),
    retry_backoff=True,          # Exponential backoff
    retry_backoff_max=600,       # Cap at 10 minutes
    retry_jitter=True            # Add randomness to prevent thundering herd
)
def chunk_document_text(self, document_id):
    try:
        # ... chunking logic ...
    except ValidationError as e:
        # Don't retry validation errors
        raise Ignore()
    except (SQLAlchemyError, ConnectionError) as e:
        # Auto-retry with backoff (handled by decorator)
        raise
    except Exception as e:
        # Unexpected error - retry once, then fail
        if self.request.retries < 1:
            raise self.retry(exc=e, countdown=60)
        else:
            # Give up, mark failed
            raise
```

### 6.4 Rollback Procedures

#### Database Rollback

```python
# Automatic transaction rollback on error

try:
    db.begin_nested()

    # Delete old chunks
    db.query(Embedding).filter(Embedding.document_id == doc_id).delete()

    # Insert new chunks
    db.bulk_insert_mappings(Embedding, chunk_records)

    # Commit
    db.commit()

except Exception as e:
    # ROLLBACK - restores old chunks, discards new ones
    db.rollback()
    logger.error(f"Rollback: {e}")
    raise
```

#### Manual Rollback (if needed)

```sql
-- Restore previous chunking state for a document

BEGIN;

-- 1. Find document's last successful chunking timestamp
SELECT created_at
FROM processing_status
WHERE document_id = 'abc-123...'
  AND stage = 'CHUNKING'
  AND status = 'COMPLETED'
ORDER BY created_at DESC
LIMIT 1 OFFSET 1;  -- Get second-to-last (before failed attempt)
-- Result: 2024-10-24 10:00:00

-- 2. Delete chunks created after that timestamp
DELETE FROM embeddings
WHERE document_id = 'abc-123...'
  AND created_at > '2024-10-24 10:00:00';

-- 3. Restore old processing status
UPDATE processing_status
SET status = 'COMPLETED',
    error_message = NULL,
    updated_at = NOW()
WHERE document_id = 'abc-123...'
  AND stage = 'CHUNKING';

COMMIT;
```

### 6.5 Logging Points

```python
# Structured logging with levels

import structlog
logger = structlog.get_logger()

# 1. Task start (INFO)
logger.info(
    "chunking_started",
    document_id=str(document_id),
    text_length=len(text),
    mime_type=document.mime_type
)

# 2. Structure extraction (DEBUG)
logger.debug(
    "structure_extracted",
    document_id=str(document_id),
    heading_count=len(structure.headings),
    paragraph_count=len(structure.paragraphs)
)

# 3. Sentence splitting (DEBUG)
logger.debug(
    "sentences_split",
    document_id=str(document_id),
    sentence_count=len(sentences),
    method="spacy"  # or "nltk"
)

# 4. Chunking complete (INFO)
logger.info(
    "chunks_created",
    document_id=str(document_id),
    chunk_count=len(chunks),
    avg_tokens=sum(c.token_count for c in chunks) // len(chunks),
    processing_time_ms=processing_time
)

# 5. Quality check (WARNING if low)
if quality_score < MIN_QUALITY_SCORE:
    logger.warning(
        "low_chunk_quality",
        document_id=str(document_id),
        quality_score=quality_score,
        threshold=MIN_QUALITY_SCORE
    )

# 6. Database save (INFO)
logger.info(
    "chunks_saved",
    document_id=str(document_id),
    chunks_inserted=len(chunks),
    chunks_deleted=deleted_count
)

# 7. Errors (ERROR)
logger.error(
    "chunking_failed",
    document_id=str(document_id),
    error_code="CHUNK_E101",
    error_message=str(e),
    exc_info=True  # Include stack trace
)
```

**Log Output Format (JSON):**

```json
{
  "event": "chunks_created",
  "level": "info",
  "timestamp": "2024-10-24T12:34:56.789Z",
  "document_id": "abc-123-def-456",
  "chunk_count": 5,
  "avg_tokens": 487,
  "processing_time_ms": 1234,
  "logger": "app.tasks.chunking_tasks",
  "thread": "MainThread"
}
```

---

## 7. TESTING CHECKLIST

### 7.1 Manual Testing

#### Test 1: Basic Chunking with spaCy

```bash
# 1. Upload a PDF document
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@tests/fixtures/sample_10pages.pdf" \
  -H "X-API-Key: dev-key-12345"

# Expected response:
{
  "document_id": "abc-123...",
  "status": "processing",
  "message": "Document uploaded successfully"
}

# 2. Wait for chunking to complete (monitor logs)
docker logs -f querybox-celery-worker | grep "chunks_created"

# 3. Verify chunks in database
docker exec querybox-postgres psql -U querybox -d querybox_core -c "
SELECT
  chunk_index,
  chunk_tokens,
  chunk_type,
  section_heading,
  LENGTH(chunk_text) as text_length
FROM embeddings
WHERE document_id = 'abc-123...'
ORDER BY chunk_index;
"

# Expected output:
 chunk_index | chunk_tokens | chunk_type |  section_heading  | text_length
-------------+--------------+------------+-------------------+-------------
           0 |          487 | paragraph  | Introduction      |        1954
           1 |          523 | paragraph  | Methods           |        2103
           2 |          456 | list       | Results           |        1834
           3 |          501 | paragraph  | Discussion        |        2015
           4 |          489 | paragraph  | Conclusion        |        1967
```

#### Test 2: Fallback to NLTK (spaCy Disabled)

```bash
# 1. Set environment variable
export USE_SPACY=false

# 2. Restart Celery worker
docker restart querybox-celery-worker

# 3. Upload document and verify chunking still works
# (same as Test 1)

# 4. Check logs for fallback message
docker logs querybox-celery-worker | grep "falling back to NLTK"
# Expected: "spaCy model not found, falling back to NLTK"
```

#### Test 3: Short Document (Edge Case)

```bash
# 1. Create a short text file (<100 chars)
echo "This is too short." > /tmp/short.txt

# 2. Upload
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@/tmp/short.txt" \
  -H "X-API-Key: dev-key-12345"

# 3. Check processing status
curl http://localhost:8000/api/v1/documents/{document_id} \
  -H "X-API-Key: dev-key-12345"

# Expected response:
{
  "chunking_status": "failed",
  "chunking_error": "Text too short: 19 chars (minimum: 100)"
}
```

#### Test 4: Metadata Extraction

```bash
# 1. Upload a structured document (with headings)
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@tests/fixtures/structured_doc.pdf" \
  -H "X-API-Key: dev-key-12345"

# 2. Verify metadata in chunks
docker exec querybox-postgres psql -U querybox -d querybox_core -c "
SELECT
  chunk_index,
  section_heading,
  subsection_heading,
  chunk_type,
  contains_list,
  contains_table
FROM embeddings
WHERE document_id = '{document_id}'
ORDER BY chunk_index;
"

# Expected: Most chunks should have section_heading populated
```

### 7.2 Expected Successful Behavior

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| **Normal PDF (10 pages)** | 10-page PDF, ~2500 tokens | 5 chunks, avg 500 tokens each |
| **Structured document** | PDF with H1/H2 headings | >80% chunks have `section_heading` |
| **List-heavy document** | Document with bullet lists | Some chunks have `chunk_type=list`, `contains_list=true` |
| **Table in document** | PDF with table | Chunk containing table has `contains_table=true` |
| **Long paragraph** | 3000-token paragraph | Split into 6 chunks with 50-token overlap |
| **Short sentences** | Many 5-10 word sentences | Grouped into 512-token chunks |

### 7.3 Edge Cases to Verify

#### Edge Case 1: Document with Only Headings

```python
# Input:
text = """
# Heading 1
## Heading 2
### Heading 3
"""

# Expected behavior:
- 1-2 chunks (very short)
- chunk_type = "heading"
- section_heading populated
- No error (min_chunk_size relaxed for headings)
```

#### Edge Case 2: Very Long Sentence (>600 tokens)

```python
# Input:
text = "This is a single sentence that somehow goes on for over 600 tokens and never ends with proper punctuation and keeps rambling and..."  # (600+ tokens)

# Expected behavior:
- Split at token limit (600 tokens)
- Add marker: "... (truncated)"
- Log warning: "Sentence exceeds max_tokens, truncating"
- chunk_type = "paragraph" (best guess)
```

#### Edge Case 3: Mixed Languages

```python
# Input:
text = "English paragraph here. 这是中文段落。Back to English."

# Expected behavior:
- Language detection per chunk
- Tokenizer handles multi-language correctly
- Some chunks may have language="zh"
- Sentence splitting may be less accurate for Chinese (no spaces)
```

#### Edge Case 4: Code Block in Document

```python
# Input:
text = """
Here is some code:

def hello_world():
    print("Hello, world!")
    return True

And back to normal text.
"""

# Expected behavior:
- Code block detected (indentation pattern)
- chunk_type = "code"
- Preserve code block intact (don't split mid-function)
- Token count accurate (including whitespace)
```

#### Edge Case 5: Empty Paragraphs / Whitespace

```python
# Input:
text = "Paragraph 1.\n\n\n\n\n\n\nParagraph 2."

# Expected behavior:
- Whitespace normalized
- Only 2 chunks created (for 2 paragraphs)
- Empty lines ignored
```

### 7.4 Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Chunking speed** | <2s for 10-page PDF (~2500 tokens) | `processing_time_ms` in result |
| **spaCy load time** | <3s (one-time at startup) | Log timestamp between start and first use |
| **Token counting** | <100ms for 1000 tokens | Benchmark `TokenCounter.count_tokens()` |
| **Database insert** | <500ms for 100 chunks | Log time between INSERT start and COMMIT |
| **Memory usage** | <500MB per task | Monitor Celery worker memory |
| **Quality score** | >0.8 for well-structured docs | Calculate from metadata coverage |

**Benchmark Script:**

```python
# tests/performance/test_chunking_performance.py

import time
from app.services.chunking import EnhancedChunkingService

def test_chunking_speed():
    # Load sample text (2500 tokens)
    with open("tests/fixtures/sample_2500tokens.txt") as f:
        text = f.read()

    service = EnhancedChunkingService()

    start = time.time()
    result = service.chunk_text_enhanced(text, document_id, db)
    elapsed = time.time() - start

    assert elapsed < 2.0, f"Chunking took {elapsed}s (target: <2s)"
    assert result.success
    assert result.chunk_count >= 4  # ~2500 tokens / 512 = ~5 chunks
```

---

## 8. MONITORING & METRICS

### 8.1 Metrics Collected

#### Application Metrics (Prometheus format)

```python
# app/services/chunking/chunking_service.py

from prometheus_client import Counter, Histogram, Gauge

# Counters
chunking_total = Counter(
    'querybox_chunking_total',
    'Total documents chunked',
    ['status']  # labels: success, failed
)

chunking_errors = Counter(
    'querybox_chunking_errors',
    'Chunking errors by type',
    ['error_type']  # labels: validation, processing, database, system
)

# Histograms
chunking_duration = Histogram(
    'querybox_chunking_duration_seconds',
    'Time spent chunking documents',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

chunk_count = Histogram(
    'querybox_chunk_count',
    'Number of chunks per document',
    buckets=[1, 5, 10, 20, 50, 100]
)

chunk_tokens = Histogram(
    'querybox_chunk_tokens',
    'Token count per chunk',
    buckets=[100, 200, 300, 400, 500, 600, 800, 1000]
)

# Gauges
chunks_in_database = Gauge(
    'querybox_chunks_total',
    'Total chunks in database'
)

quality_score = Histogram(
    'querybox_chunk_quality_score',
    'Chunk quality scores',
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
)

# Usage in code:
with chunking_duration.time():
    result = self.chunk_text_enhanced(...)

chunking_total.labels(status='success').inc()
chunk_count.observe(result.chunk_count)
quality_score.observe(result.quality_score)
```

#### Business Metrics

| Metric | Description | Query |
|--------|-------------|-------|
| **Avg chunks per document** | Mean chunk count | `SELECT AVG(chunk_count) FROM (SELECT COUNT(*) as chunk_count FROM embeddings GROUP BY document_id)` |
| **Avg tokens per chunk** | Mean token count | `SELECT AVG(chunk_tokens) FROM embeddings WHERE chunk_tokens IS NOT NULL` |
| **Metadata coverage** | % chunks with section_heading | `SELECT COUNT(*) FILTER (WHERE section_heading IS NOT NULL) * 100.0 / COUNT(*) FROM embeddings` |
| **Chunk type distribution** | Breakdown by type | `SELECT chunk_type, COUNT(*) FROM embeddings GROUP BY chunk_type` |
| **Quality score distribution** | P50, P90, P99 | From `processing_status.result_data->'quality_score'` |

### 8.2 Log Entries Generated

**Standard log format (JSON structured logs):**

```json
// 1. Task started
{
  "event": "chunking_started",
  "level": "info",
  "timestamp": "2024-10-24T12:00:00.000Z",
  "document_id": "abc-123",
  "text_length": 10247,
  "mime_type": "application/pdf"
}

// 2. Structure extracted
{
  "event": "structure_extracted",
  "level": "debug",
  "timestamp": "2024-10-24T12:00:00.123Z",
  "document_id": "abc-123",
  "headings": 5,
  "paragraphs": 23,
  "tables": 1,
  "lists": 3
}

// 3. Sentences split
{
  "event": "sentences_split",
  "level": "debug",
  "timestamp": "2024-10-24T12:00:00.456Z",
  "document_id": "abc-123",
  "sentence_count": 87,
  "method": "spacy",
  "split_duration_ms": 234
}

// 4. Chunks created
{
  "event": "chunks_created",
  "level": "info",
  "timestamp": "2024-10-24T12:00:01.789Z",
  "document_id": "abc-123",
  "chunk_count": 5,
  "avg_tokens": 487,
  "min_tokens": 456,
  "max_tokens": 523,
  "quality_score": 0.87
}

// 5. Quality warning (if applicable)
{
  "event": "low_chunk_quality",
  "level": "warning",
  "timestamp": "2024-10-24T12:00:01.800Z",
  "document_id": "abc-123",
  "quality_score": 0.52,
  "threshold": 0.6,
  "issues": ["avg_tokens_too_low", "missing_headings"]
}

// 6. Chunks saved to database
{
  "event": "chunks_saved",
  "level": "info",
  "timestamp": "2024-10-24T12:00:02.000Z",
  "document_id": "abc-123",
  "chunks_inserted": 5,
  "chunks_deleted": 3,
  "db_duration_ms": 211
}

// 7. Task completed
{
  "event": "chunking_completed",
  "level": "info",
  "timestamp": "2024-10-24T12:00:02.100Z",
  "document_id": "abc-123",
  "total_duration_ms": 2100,
  "success": true
}

// 8. Error (if failed)
{
  "event": "chunking_failed",
  "level": "error",
  "timestamp": "2024-10-24T12:00:02.100Z",
  "document_id": "abc-123",
  "error_code": "CHUNK_E101",
  "error_message": "Sentence splitting timeout",
  "total_duration_ms": 31000,
  "retry_count": 2,
  "stack_trace": "..."
}
```

### 8.3 Health Check Indicators

```python
# GET /health endpoint enhancement

{
  "status": "healthy",
  "services": {
    "database": "up",
    "redis": "up",
    "celery": "up",
    "chunking": {
      "status": "up",
      "checks": {
        "spacy_model_loaded": true,
        "nltk_data_available": true,
        "token_counter_functional": true
      },
      "last_successful_chunk": "2024-10-24T12:00:02Z",
      "avg_processing_time_ms": 1850,
      "error_rate_1h": 0.02  # 2% error rate in last hour
    }
  }
}
```

**Unhealthy States:**

- `spacy_model_loaded: false` → Critical (fallback to NLTK)
- `error_rate_1h > 0.1` → Warning (>10% failures)
- `avg_processing_time_ms > 5000` → Warning (slower than expected)
- Last successful chunk >1 hour ago → Warning (no recent activity)

### 8.4 Performance Measurements

#### Real-time Metrics Dashboard (Grafana)

**Panel 1: Chunking Throughput**
```promql
# Documents chunked per minute
rate(querybox_chunking_total{status="success"}[1m]) * 60
```

**Panel 2: Processing Time (P50, P90, P99)**
```promql
# P90 chunking duration
histogram_quantile(0.9, querybox_chunking_duration_seconds_bucket)
```

**Panel 3: Chunk Quality Distribution**
```promql
# Avg quality score (last 5 min)
avg_over_time(querybox_chunk_quality_score_sum[5m]) /
avg_over_time(querybox_chunk_quality_score_count[5m])
```

**Panel 4: Error Rate**
```promql
# Error rate % (last 1h)
sum(rate(querybox_chunking_errors[1h])) /
sum(rate(querybox_chunking_total[1h])) * 100
```

**Panel 5: Chunk Size Distribution**
```promql
# Histogram of chunk sizes
rate(querybox_chunk_tokens_bucket[5m])
```

#### Database Queries for Analysis

```sql
-- 1. Average chunk statistics by document type
SELECT
  d.mime_type,
  COUNT(DISTINCT e.document_id) as document_count,
  AVG(chunk_count) as avg_chunks,
  AVG(avg_tokens) as avg_tokens_per_chunk,
  AVG(quality_score) as avg_quality
FROM documents d
JOIN (
  SELECT
    document_id,
    COUNT(*) as chunk_count,
    AVG(chunk_tokens) as avg_tokens
  FROM embeddings
  GROUP BY document_id
) e ON d.id = e.document_id
JOIN (
  SELECT
    document_id,
    (result_data->>'quality_score')::float as quality_score
  FROM processing_status
  WHERE stage = 'CHUNKING'
) ps ON d.id = ps.document_id
GROUP BY d.mime_type;

-- 2. Find low-quality chunks
SELECT
  d.original_name,
  e.chunk_index,
  e.chunk_tokens,
  e.semantic_density,
  e.chunk_type,
  e.section_heading
FROM embeddings e
JOIN documents d ON e.document_id = d.id
WHERE e.semantic_density < 0.3 OR e.chunk_tokens < 100
ORDER BY e.semantic_density ASC
LIMIT 20;

-- 3. Metadata coverage report
SELECT
  COUNT(*) as total_chunks,
  COUNT(section_heading) as chunks_with_heading,
  COUNT(section_heading) * 100.0 / COUNT(*) as heading_coverage_pct,
  COUNT(*) FILTER (WHERE contains_table) as chunks_with_table,
  COUNT(*) FILTER (WHERE contains_list) as chunks_with_list
FROM embeddings;
```

---

## 9. SECURITY CONSIDERATIONS

### 9.1 Authentication/Authorization Checks

**Not directly applicable** (internal Celery task, no external API), but:

```python
# Celery task only processes documents already uploaded
# Upload endpoint handles auth:

@router.post("/upload")
async def upload_document(
    file: UploadFile,
    api_key: str = Depends(verify_api_key),  # ✅ Auth check
    db: Session = Depends(get_db)
):
    # Upload → triggers chunking task
    # Chunking task inherits permission context
```

**Task security:**
- Only processes `document_id` from trusted source (upload endpoint)
- No user input in task parameters (UUID only)
- Database queries use parameterized queries (SQLAlchemy ORM)

### 9.2 Input Sanitization

```python
# 1. Text normalization (remove control characters)
def sanitize_text(text: str) -> str:
    """Remove potentially harmful characters"""
    # Remove null bytes
    text = text.replace('\x00', '')

    # Remove other control chars (except newline, tab)
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')

    # Normalize Unicode
    import unicodedata
    text = unicodedata.normalize('NFKC', text)

    return text

# 2. Length validation
MAX_TEXT_LENGTH = 10_000_000  # 10M chars
if len(text) > MAX_TEXT_LENGTH:
    raise ValidationError(f"Text too long: {len(text)} chars (max: {MAX_TEXT_LENGTH})")

# 3. Encoding validation
try:
    text.encode('utf-8')
except UnicodeEncodeError:
    # Convert to UTF-8, replacing invalid chars
    text = text.encode('utf-8', errors='replace').decode('utf-8')
```

### 9.3 Path Traversal Prevention

**Not applicable** - No file paths in user input. All file operations use:
- Database blobs (`document_texts.full_text`)
- UUIDs for identifiers (not filenames)

### 9.4 SQL Injection Prevention

**Protected by SQLAlchemy ORM:**

```python
# ✅ SAFE - Parameterized query
db.query(Embedding).filter(Embedding.document_id == doc_uuid).delete()

# ✅ SAFE - Bulk insert with ORM
db.bulk_insert_mappings(Embedding, chunk_records)

# ❌ UNSAFE (we don't do this)
# db.execute(f"DELETE FROM embeddings WHERE document_id = '{doc_uuid}'")
```

**Additional protection:**
- All DB queries use ORM (no raw SQL)
- UUIDs validated before use
- No string concatenation in queries

### 9.5 File Type Restrictions

**Enforced at upload** (Step 4), but validated again:

```python
# Chunking only processes text extracted from allowed types
ALLOWED_MIME_TYPES = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'text/markdown'
]

# Document must pass upload validation before reaching chunking
# If mime_type not in ALLOWED, extraction fails, chunking never runs
```

### 9.6 Additional Security Measures

#### 1. ReDoS (Regular Expression Denial of Service) Prevention

```python
# Problematic regex (can hang on malicious input):
# r'(a+)+b'  # Catastrophic backtracking

# Our regex (safe):
SENTENCE_PATTERN = r'(?<=[.!?])\s+(?=[A-Z])'  # Linear time complexity

# Python 3.11+ timeout (additional safety):
import re
re.match(SENTENCE_PATTERN, text, timeout=5)  # Timeout after 5 seconds
```

#### 2. Resource Limits

```python
# Celery task limits (prevent resource exhaustion)
@celery_app.task(
    time_limit=300,        # Kill task after 5 minutes
    soft_time_limit=240,   # Warn at 4 minutes
    max_retries=3
)

# spaCy limits (prevent memory overflow)
nlp.max_length = 1_000_000  # Max 1M chars per spaCy call

# Token counter limits
MAX_TOKENS_PER_CHUNK = 600  # Hard cap
```

#### 3. Sensitive Data Detection

```python
# Optional: Detect PII/secrets in chunks (for future implementation)

def detect_sensitive_data(chunk_text: str) -> Dict[str, bool]:
    """Detect potential sensitive information"""
    return {
        "contains_email": bool(re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', chunk_text)),
        "contains_phone": bool(re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', chunk_text)),
        "contains_ssn": bool(re.search(r'\b\d{3}-\d{2}-\d{4}\b', chunk_text)),
        "contains_credit_card": bool(re.search(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', chunk_text))
    }

# Can be used to flag/redact sensitive chunks
```

#### 4. Audit Logging

```python
# Log all chunking operations for audit trail
audit_logger.info(
    "document_chunked",
    document_id=document_id,
    user_id=document.uploaded_by,  # Track who uploaded
    chunk_count=result.chunk_count,
    timestamp=datetime.utcnow(),
    ip_address=request.client.host  # From upload context
)
```

---

## 10. CODE PATTERNS & CONVENTIONS

### 10.1 Design Patterns Used

#### 1. **Service Layer Pattern**
```python
# Separate business logic from API/task layers

# app/services/chunking/chunking_service.py
class EnhancedChunkingService:
    """Business logic for chunking"""
    def chunk_text_enhanced(self, ...): pass

# app/tasks/chunking_tasks.py
@celery_app.task
def chunk_document_text(document_id):
    """Task orchestration only"""
    service = get_chunking_service()
    result = service.chunk_text_enhanced(...)
```

**Benefits:**
- Testable (mock service in tests)
- Reusable (service used in tasks, API, CLI)
- Single Responsibility (service = chunking, task = orchestration)

#### 2. **Strategy Pattern** (Sentence Splitting)
```python
# Abstract interface for multiple strategies

class SentenceSplitterStrategy(ABC):
    @abstractmethod
    def split(self, text: str) -> List[Sentence]: pass

class SpacySplitter(SentenceSplitterStrategy):
    def split(self, text): # spaCy implementation

class NLTKSplitter(SentenceSplitterStrategy):
    def split(self, text): # NLTK implementation

# Context class
class SentenceSplitter:
    def __init__(self, use_spacy: bool):
        self.strategy = SpacySplitter() if use_spacy else NLTKSplitter()

    def split_sentences(self, text):
        return self.strategy.split(text)
```

**Benefits:**
- Easy to swap algorithms
- Testable (test each strategy independently)
- Extensible (add new splitters without changing existing code)

#### 3. **Factory Pattern** (Service Creation)
```python
# app/services/chunking/__init__.py

_chunking_service: Optional[EnhancedChunkingService] = None

def get_chunking_service(
    config: Optional[EnhancedChunkingConfig] = None
) -> EnhancedChunkingService:
    """Factory function for chunking service (singleton)"""
    global _chunking_service

    if _chunking_service is None:
        _chunking_service = EnhancedChunkingService(config)

    return _chunking_service

# Usage:
service = get_chunking_service()  # Returns singleton
```

**Benefits:**
- Centralized creation logic
- Singleton pattern (reuse loaded models)
- Testable (inject mock config)

#### 4. **Data Transfer Object (DTO) Pattern**
```python
# app/schemas/chunking.py

from pydantic import BaseModel

class ChunkData(BaseModel):
    """DTO for chunk data"""
    text: str
    chunk_index: int
    start_position: int
    end_position: int
    token_estimate: int
    metadata: Optional[ChunkMetadata]

    class Config:
        orm_mode = True  # Can create from SQLAlchemy models

class ChunkingResult(BaseModel):
    """DTO for chunking operation result"""
    success: bool
    chunk_count: int
    avg_chunk_size: int
    processing_time_ms: int
    error_message: Optional[str] = None
```

**Benefits:**
- Type safety (Pydantic validation)
- Decouples service layer from database models
- Easy serialization (for API responses, Celery results)

### 10.2 Naming Conventions

#### File & Directory Names
```
snake_case for files:       chunking_service.py
snake_case for dirs:        app/services/chunking/
```

#### Python Code
```python
# Classes: PascalCase
class EnhancedChunkingService: pass
class ChunkMetadata: pass

# Functions/methods: snake_case
def chunk_text_enhanced(): pass
def _extract_structure(): pass  # Private (starts with _)

# Constants: UPPER_SNAKE_CASE
MAX_TOKENS = 600
MIN_CHUNK_SIZE = 100

# Variables: snake_case
chunk_count = 5
document_id = uuid.uuid4()

# Type hints: everywhere
def count_tokens(self, text: str) -> int: pass
```

#### Database
```sql
-- Tables: lowercase plural
embeddings, documents, processing_status

-- Columns: snake_case
chunk_text, section_heading, created_at

-- Indexes: idx_<table>_<column(s)>
idx_embeddings_vector
idx_embeddings_chunk_index
```

### 10.3 Async/Await Patterns

**Note:** Chunking service is **synchronous** (spaCy/NLTK are sync libraries), but integrates with async FastAPI:

```python
# Celery task: Synchronous (no async/await needed)
@celery_app.task
def chunk_document_text(document_id):
    # Sync code
    result = chunking_service.chunk_text_enhanced(...)
    return result

# FastAPI endpoint: Async (wraps sync Celery call)
@router.post("/upload")
async def upload_document(file: UploadFile, db: Session = Depends(get_db)):
    # Save document (sync DB operation)
    document = create_document(db, ...)

    # Queue chunking task (async - non-blocking)
    chunk_document_text.delay(str(document.id))

    # Return immediately (don't wait for chunking)
    return {"document_id": document.id, "status": "processing"}
```

**Async database with SQLAlchemy:**
```python
# If needed in future (currently using sync SessionLocal)
from sqlalchemy.ext.asyncio import AsyncSession

async def get_document_async(db: AsyncSession, document_id: UUID):
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    return result.scalar_one_or_none()
```

### 10.4 Transaction Boundaries

```python
# Pattern: Transaction per operation (short-lived)

def save_chunks(self, chunks, document_id, db):
    """
    Transaction boundary: This entire method

    ✅ DO: Keep transaction short
    ✅ DO: Commit at end
    ✅ DO: Rollback on error
    ❌ DON'T: Hold transaction across external calls
    """

    try:
        db.begin_nested()  # Start savepoint

        # 1. Delete old chunks
        db.query(Embedding).filter(
            Embedding.document_id == document_id
        ).delete()

        # 2. Insert new chunks
        db.bulk_insert_mappings(Embedding, chunk_records)

        # 3. Commit (releases locks)
        db.commit()

    except Exception as e:
        # Rollback savepoint
        db.rollback()
        logger.error(f"Transaction rollback: {e}")
        raise

# ❌ BAD: Transaction across service calls
# db.begin()
# chunking_service.chunk_text(...)  # Long-running operation
# embedding_service.generate_embeddings(...)  # External API call
# db.commit()  # Transaction held for too long!

# ✅ GOOD: Separate transactions
db.begin()
chunks = chunking_service.chunk_text(...)
db.commit()

db.begin()
embeddings = embedding_service.generate_embeddings(chunks)
db.commit()
```

### 10.5 Error Propagation Strategy

```python
# Error hierarchy:

# 1. Domain exceptions (custom, catchable)
class ChunkingError(Exception):
    """Base class for chunking errors"""
    pass

class ValidationError(ChunkingError):
    """Input validation failed"""
    pass

class ProcessingError(ChunkingError):
    """Chunking process failed"""
    pass

# 2. Service layer: Raise domain exceptions
def chunk_text_enhanced(self, text, ...):
    if len(text) < MIN_CHUNK_SIZE:
        raise ValidationError(f"Text too short: {len(text)}")

    try:
        chunks = self._create_chunks(...)
    except Exception as e:
        raise ProcessingError(f"Chunking failed: {e}") from e

# 3. Task layer: Catch and handle
@celery_app.task
def chunk_document_text(document_id):
    try:
        result = service.chunk_text_enhanced(...)
        return {"success": True, ...}

    except ValidationError as e:
        # Don't retry validation errors
        logger.warning(f"Validation failed: {e}")
        return {"success": False, "error": str(e)}

    except ProcessingError as e:
        # Retry processing errors
        logger.error(f"Processing failed: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"success": False, "error": str(e)}

# 4. API layer: Convert to HTTP responses
@router.get("/documents/{document_id}")
async def get_document(document_id: UUID):
    try:
        document = get_document_service(document_id)
        return document
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail="Processing failed")
```

**Error logging levels:**
- `ValidationError` → `logger.warning()` (expected errors)
- `ProcessingError` → `logger.error()` (unexpected but retryable)
- `SystemError` → `logger.critical()` (requires immediate attention)

---

## 11. INTEGRATION POINTS

### 11.1 How This Connects to Other Components

```
┌───────────────────────────────────────────────────────────┐
│              CHUNKING SERVICE INTEGRATION MAP              │
└───────────────────────────────────────────────────────────┘

┌─────────────────┐         ┌──────────────────┐
│ Upload Endpoint │────────>│ Extraction Task  │
│  (Step 3)       │         │   (Step 8.1)     │
└─────────────────┘         └──────────────────┘
                                      │
                                      │ Extracts text
                                      ▼
                            ┌──────────────────┐
                            │  document_texts  │
                            │      table       │
                            └──────────────────┘
                                      │
                                      │ Triggers
                                      ▼
                            ┌──────────────────┐
                            │ CHUNKING TASK    │◄────── You are here (Step 9.1)
                            │   (Enhanced)     │
                            └──────────────────┘
                                      │
                   ┌──────────────────┼──────────────────┐
                   ▼                  ▼                  ▼
         ┌─────────────────┐ ┌──────────────┐ ┌──────────────────┐
         │ Sentence        │ │ Token        │ │ Metadata         │
         │ Splitter        │ │ Counter      │ │ Extractor        │
         │ (spaCy/NLTK)    │ │ (tiktoken)   │ │ (Regex/Pattern)  │
         └─────────────────┘ └──────────────┘ └──────────────────┘
                   │                  │                  │
                   └──────────────────┼──────────────────┘
                                      ▼
                            ┌──────────────────┐
                            │   embeddings     │
                            │      table       │
                            │ (chunks stored)  │
                            └──────────────────┘
                                      │
                                      │ Triggers
                                      ▼
                            ┌──────────────────┐
                            │ Embedding Task   │
                            │   (Step 9.2)     │
                            └──────────────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │ Vector Search    │
                            │   (Step 9.3)     │
                            └──────────────────┘

DEPENDENCIES:
┌────────────────┬────────────────────────────────────────┐
│ Upstream       │ document_texts.full_text (Step 8.1)    │
│ (requires)     │ processing_status.EXTRACTION=COMPLETED │
├────────────────┼────────────────────────────────────────┤
│ Downstream     │ embeddings.chunk_text → Step 9.2       │
│ (provides for) │ embeddings.metadata → Step 10, 11      │
└────────────────┴────────────────────────────────────────┘
```

### 11.2 Database Queries Executed

#### Query 1: Fetch Document & Text
```sql
-- Executed by: chunk_document_text task

-- Get document metadata
SELECT id, original_name, mime_type, file_size
FROM documents
WHERE id = 'abc-123...'
LIMIT 1;

-- Get extracted text
SELECT full_text, text_length, page_count
FROM document_texts
WHERE document_id = 'abc-123...'
LIMIT 1;
```

#### Query 2: Check Processing Status
```sql
-- Verify extraction completed before chunking
SELECT stage, status, completed_at
FROM processing_status
WHERE document_id = 'abc-123...'
  AND stage = 'EXTRACTION'
LIMIT 1;

-- Expected: status = 'COMPLETED'
```

#### Query 3: Delete Old Chunks (If Re-processing)
```sql
-- Cleanup before inserting new chunks
DELETE FROM embeddings
WHERE document_id = 'abc-123...';

-- Returns: number of rows deleted (0 if first time)
```

#### Query 4: Bulk Insert Chunks
```sql
-- Insert all chunks in one transaction
INSERT INTO embeddings (
    id, document_id, chunk_index, chunk_text, chunk_tokens,
    embedding, start_position, end_position, page_number,
    section_heading, subsection_heading, chunk_type,
    paragraph_index, semantic_density, contains_table, contains_list,
    language, embedding_model, created_at
) VALUES
    ('uuid1', 'abc-123...', 0, 'text1', 487, NULL, 0, 1234, 1, 'Intro', NULL, 'paragraph', 0, 0.72, FALSE, FALSE, 'en', 'pending', NOW()),
    ('uuid2', 'abc-123...', 1, 'text2', 523, NULL, 1184, 2567, 1, 'Methods', NULL, 'paragraph', 1, 0.68, FALSE, FALSE, 'en', 'pending', NOW()),
    ('uuid3', 'abc-123...', 2, 'text3', 456, NULL, 2517, 3950, 2, 'Results', NULL, 'list', 0, 0.65, FALSE, TRUE, 'en', 'pending', NOW()),
    ('uuid4', 'abc-123...', 3, 'text4', 501, NULL, 3900, 5420, 2, 'Discussion', NULL, 'paragraph', 0, 0.71, FALSE, FALSE, 'en', 'pending', NOW()),
    ('uuid5', 'abc-123...', 4, 'text5', 489, NULL, 5370, 6830, 3, 'Conclusion', NULL, 'paragraph', 0, 0.69, FALSE, FALSE, 'en', 'pending', NOW())
ON CONFLICT (document_id, chunk_index) DO UPDATE SET
    chunk_text = EXCLUDED.chunk_text,
    chunk_tokens = EXCLUDED.chunk_tokens,
    -- ... update all columns
;

-- Returns: 5 rows inserted (or updated)
```

#### Query 5: Update Processing Status
```sql
-- Mark chunking as completed
UPDATE processing_status
SET
    status = 'COMPLETED',
    completed_at = NOW(),
    duration_ms = 1234,
    result_data = '{"chunk_count": 5, "avg_tokens": 491, "quality_score": 0.87}'::jsonb
WHERE document_id = 'abc-123...'
  AND stage = 'CHUNKING';

-- If status doesn't exist, insert it (handled by StatusTracker)
INSERT INTO processing_status (
    document_id, stage, status, started_at, completed_at, duration_ms, result_data
) VALUES (
    'abc-123...', 'CHUNKING', 'COMPLETED', NOW(), NOW(), 1234, '{"chunk_count": 5}'::jsonb
)
ON CONFLICT (document_id, stage) DO UPDATE SET ...;
```

#### Query 6: Update Document Timestamp
```sql
-- Track when document was last indexed
UPDATE documents
SET last_indexed_at = NOW()
WHERE id = 'abc-123...';
```

### 11.3 External Services Called

| Service | Purpose | How Called | Fallback |
|---------|---------|------------|----------|
| **spaCy** | Sentence splitting | `nlp(text)` → spaCy pipeline | NLTK if model not found |
| **NLTK** | Fallback sentence splitting | `sent_tokenize(text)` | N/A (basic regex if NLTK fails) |
| **tiktoken** | Token counting | `encoding.encode(text)` | Simple `len(text) // 4` estimate |

**None of these are network calls** - all run locally:
- spaCy model loaded into memory (1.5GB for en_core_web_sm)
- NLTK data in `~/nltk_data/` directory
- tiktoken uses local tokenizer file

### 11.4 Events Published/Consumed

#### Events Consumed (Celery Queue)

```python
# Event: document.extraction.completed
# Published by: extraction_tasks.py (Step 8.1)
# Consumed by: chunking_tasks.py (this step)

# Celery routing:
celery_app.conf.task_routes = {
    'app.tasks.extraction_tasks.extract_text': {'queue': 'extraction'},
    'app.tasks.chunking_tasks.chunk_document_text': {'queue': 'chunking'},
}

# Task chain:
extraction_task.delay(document_id)  # Step 8.1
  ↓ (on success)
chunking_task.delay(document_id)    # Step 9.1 ← This task
```

#### Events Published

```python
# Event: document.chunking.completed
# Published by: chunking_tasks.py (this step)
# Will be consumed by: embedding_tasks.py (Step 9.2)

# Example:
@celery_app.task
def chunk_document_text(document_id):
    # ... chunking logic ...

    if result.success:
        # Trigger next step in pipeline
        from app.tasks.embedding_tasks import generate_embeddings
        generate_embeddings.delay(document_id)  # Step 9.2

    return result
```

**Event Flow:**
```
Upload → Extraction → Chunking → Embedding → Indexing
         (Step 8.1)   (Step 9.1)  (Step 9.2)  (Step 9.3)
```

---

## 12. TROUBLESHOOTING GUIDE

### 12.1 Common Issues & Solutions

#### Issue 1: "spaCy model not found" Error

**Symptoms:**
```
OSError: [E050] Can't find model 'en_core_web_sm'.
It doesn't seem to be a Python package or a valid path to a data directory.
```

**Diagnosis:**
```bash
# Check if spaCy model is installed
python -m spacy info en_core_web_sm

# Expected output:
# ============================== Info about model ==============================
# lang         en
# ...

# If error: Model not found
```

**Solution:**
```bash
# 1. Install spaCy model
python -m spacy download en_core_web_sm

# 2. Verify installation
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('✅ Model loaded')"

# 3. Restart Celery worker
docker restart querybox-celery-worker

# 4. Check logs for fallback message
docker logs querybox-celery-worker | grep "falling back to NLTK"
# Should NOT appear if model loaded successfully
```

#### Issue 2: Chunks Have Wrong Token Counts

**Symptoms:**
- `chunk_tokens` values seem off (e.g., 1000 tokens for 200-char text)
- Chunks too large/small for embedding model

**Diagnosis:**
```sql
-- Check token counts
SELECT
    chunk_index,
    LENGTH(chunk_text) as char_count,
    chunk_tokens,
    chunk_tokens / LENGTH(chunk_text)::float as tokens_per_char
FROM embeddings
WHERE document_id = 'abc-123...'
ORDER BY chunk_index;

-- Expected: tokens_per_char ≈ 0.25 (4 chars per token)
-- If much higher/lower, token counting is wrong
```

**Solution:**
```python
# 1. Verify tiktoken is installed
pip install tiktoken==0.5.0

# 2. Test token counter directly
python -c "
from app.services.chunking.token_counter import TokenCounter
counter = TokenCounter()
text = 'This is a test sentence with approximately ten tokens.'
print(f'Tokens: {counter.count_tokens(text)}')
# Expected: ~12 tokens
"

# 3. If error, check encoding
python -c "
import tiktoken
encoding = tiktoken.get_encoding('cl100k_base')
print(encoding)
# Should print: <Encoding 'cl100k_base'>
"
```

#### Issue 3: Low Chunk Quality Scores (<0.6)

**Symptoms:**
- Warning logs: `"low_chunk_quality"`
- Most chunks missing `section_heading`
- Many chunks < 100 tokens

**Diagnosis:**
```sql
-- Analyze chunk quality
SELECT
    COUNT(*) as total_chunks,
    AVG(chunk_tokens) as avg_tokens,
    COUNT(section_heading) as chunks_with_heading,
    COUNT(section_heading) * 100.0 / COUNT(*) as heading_coverage,
    AVG(semantic_density) as avg_density
FROM embeddings
WHERE document_id = 'abc-123...';

-- Expected:
-- avg_tokens: 400-600
-- heading_coverage: >80%
-- avg_density: 0.5-0.8
```

**Solutions:**

1. **If avg_tokens too low (<300):**
```python
# Increase target chunk size
export CHUNK_TARGET_TOKENS=600  # (was 512)

# Restart Celery, re-process document
```

2. **If heading_coverage low (<50%):**
```python
# Document may not have structured headings
# Check original document format
# Possible causes:
# - Plain text file (no Markdown headers)
# - Scanned PDF (OCR text has no structure)
# - Academic paper (custom formatting)

# Solution: Improve heading detection heuristics in metadata_extractor.py
```

3. **If avg_density low (<0.3):**
```python
# Text contains too many stop words / filler
# May be expected for certain document types
# Not necessarily a problem if chunks are still semantically meaningful
```

#### Issue 4: Chunking Task Timeout (>5 minutes)

**Symptoms:**
```
celery.exceptions.SoftTimeLimitExceeded:
Task exceeded soft time limit (240s)
```

**Diagnosis:**
```bash
# Check document size
docker exec querybox-postgres psql -U querybox -d querybox_core -c "
SELECT
    d.original_name,
    dt.text_length,
    dt.text_length / 1000000.0 as size_mb,
    COUNT(e.id) as chunk_count
FROM documents d
JOIN document_texts dt ON d.id = dt.document_id
LEFT JOIN embeddings e ON d.id = e.document_id
WHERE d.id = 'abc-123...'
GROUP BY d.id, d.original_name, dt.text_length;
"

# If text_length > 1M chars → very large document
```

**Solution:**
```python
# 1. Increase task timeout
# In app/tasks/chunking_tasks.py:
@celery_app.task(
    time_limit=600,      # 10 minutes (was 300)
    soft_time_limit=540  # 9 minutes (was 240)
)

# 2. Or chunk in batches (for very large documents)
def chunk_large_document(text, document_id, db):
    BATCH_SIZE = 100_000  # Process 100k chars at a time

    for i in range(0, len(text), BATCH_SIZE):
        batch_text = text[i:i+BATCH_SIZE]
        chunks = chunk_text_enhanced(batch_text, ...)
        save_chunks(chunks, db)
```

#### Issue 5: Database "Unique Constraint Violation"

**Symptoms:**
```
IntegrityError: duplicate key value violates unique constraint
"embeddings_unique_chunk"
DETAIL: Key (document_id, chunk_index)=(abc-123..., 0) already exists.
```

**Diagnosis:**
```sql
-- Check for duplicate chunks
SELECT document_id, chunk_index, COUNT(*)
FROM embeddings
GROUP BY document_id, chunk_index
HAVING COUNT(*) > 1;

-- If rows returned → duplicates exist (should be impossible)
```

**Solution:**
```python
# This should never happen (DELETE before INSERT)
# But if it does:

# 1. Delete all chunks for document
DELETE FROM embeddings WHERE document_id = 'abc-123...';

# 2. Retry chunking task
from app.tasks.chunking_tasks import chunk_document_text
chunk_document_text.apply_async(args=['abc-123...'])

# 3. If recurring, check for race condition:
# - Multiple workers processing same document?
# - Task queued multiple times?

# Fix: Add task deduplication
@celery_app.task(bind=True)
def chunk_document_text(self, document_id):
    # Check if already processing
    if redis_client.exists(f"chunking:{document_id}"):
        logger.warning(f"Chunking already in progress for {document_id}")
        return

    # Set lock (expire after 10 minutes)
    redis_client.setex(f"chunking:{document_id}", 600, "1")

    try:
        # ... chunking logic ...
    finally:
        # Release lock
        redis_client.delete(f"chunking:{document_id}")
```

### 12.2 Debug Commands

```bash
# 1. Check Celery worker status
docker exec querybox-celery-worker celery -A app.celery_app inspect active
# Shows currently running tasks

# 2. Inspect task result
python -c "
from app.celery_app import celery_app
from celery.result import AsyncResult
result = AsyncResult('task-id-here', app=celery_app)
print(f'State: {result.state}')
print(f'Result: {result.result}')
"

# 3. Test sentence splitter directly
python -c "
from app.services.chunking.sentence_splitter import SentenceSplitter
splitter = SentenceSplitter(use_spacy=True)
text = 'First sentence. Second sentence! Third sentence?'
sentences = splitter.split_sentences(text)
for s in sentences:
    print(f'{s.text} ({s.token_count} tokens)')
"

# 4. Test token counter
python -c "
from app.services.chunking.token_counter import TokenCounter
counter = TokenCounter()
text = 'This is a test with multiple words to count tokens.'
print(f'Token count: {counter.count_tokens(text)}')
"

# 5. Validate chunk quality for a document
python -c "
from app.db.database import SessionLocal
from uuid import UUID
db = SessionLocal()
doc_id = UUID('abc-123...')

from sqlalchemy import func
stats = db.query(
    func.count().label('total'),
    func.avg(Embedding.chunk_tokens).label('avg_tokens'),
    func.count(Embedding.section_heading).label('with_heading')
).filter(Embedding.document_id == doc_id).first()

print(f'Total chunks: {stats.total}')
print(f'Avg tokens: {stats.avg_tokens:.1f}')
print(f'Heading coverage: {stats.with_heading / stats.total * 100:.1f}%')
"

# 6. Re-process a failed document
docker exec -it querybox-celery-worker python -c "
from app.tasks.chunking_tasks import chunk_document_text
result = chunk_document_text.delay('abc-123...')
print(f'Task ID: {result.id}')
"
```

### 12.3 Log Locations

```bash
# Celery worker logs (all chunking activity)
docker logs querybox-celery-worker

# Filter for specific document
docker logs querybox-celery-worker | grep "abc-123..."

# Filter for errors only
docker logs querybox-celery-worker | grep "ERROR"

# Real-time log streaming
docker logs -f querybox-celery-worker

# PostgreSQL logs (database errors)
docker logs querybox-postgres | grep "ERROR"

# Application logs (if using file logging)
# backend/logs/chunking.log (if configured)
tail -f backend/logs/chunking.log
```

### 12.4 Database Queries for Verification

#### Verify Chunking Completed
```sql
SELECT
    d.id,
    d.original_name,
    ps.status as chunking_status,
    ps.completed_at,
    ps.duration_ms,
    ps.result_data->>'chunk_count' as chunks,
    ps.error_message
FROM documents d
JOIN processing_status ps ON d.id = ps.document_id
WHERE ps.stage = 'CHUNKING'
  AND d.id = 'abc-123...'::uuid;
```

#### Inspect Chunk Details
```sql
SELECT
    chunk_index,
    LENGTH(chunk_text) as text_length,
    chunk_tokens,
    section_heading,
    chunk_type,
    semantic_density,
    contains_table,
    contains_list
FROM embeddings
WHERE document_id = 'abc-123...'::uuid
ORDER BY chunk_index;
```

#### Find Problematic Chunks
```sql
-- Chunks that might cause issues
SELECT
    document_id,
    chunk_index,
    chunk_tokens,
    semantic_density,
    chunk_type,
    'Too short' as issue
FROM embeddings
WHERE chunk_tokens < 100

UNION ALL

SELECT
    document_id,
    chunk_index,
    chunk_tokens,
    semantic_density,
    chunk_type,
    'Too long'
FROM embeddings
WHERE chunk_tokens > 600

UNION ALL

SELECT
    document_id,
    chunk_index,
    chunk_tokens,
    semantic_density,
    chunk_type,
    'Low density'
FROM embeddings
WHERE semantic_density < 0.3;
```

#### Count Chunks by Type
```sql
SELECT
    chunk_type,
    COUNT(*) as count,
    AVG(chunk_tokens) as avg_tokens,
    AVG(semantic_density) as avg_density
FROM embeddings
WHERE document_id = 'abc-123...'::uuid
GROUP BY chunk_type
ORDER BY count DESC;
```

---

## SUMMARY & NEXT STEPS

### Key Deliverables of Step 9.1

✅ **Enhanced chunking service** with spaCy/NLTK sentence detection
✅ **Token-based chunking** optimized for BGE-M3 (512 tokens target)
✅ **Rich metadata extraction** (headings, types, semantic density)
✅ **Database schema updates** to store enhanced metadata
✅ **Quality validation** to ensure chunk quality >80%
✅ **Comprehensive testing** with 10+ sample documents

### Validation Criteria

- [ ] All chunks between 100-600 tokens
- [ ] Average chunk size: 400-550 tokens
- [ ] >80% chunks have `section_heading` (for structured docs)
- [ ] spaCy sentence splitting works (with NLTK fallback)
- [ ] Token counting accurate (within 5% of actual)
- [ ] Chunking completes in <2s for 10-page PDF
- [ ] Quality score >0.7 for most documents

### Transition to Step 9.2

**Prerequisites before Step 9.2:**
1. Step 9.1 complete (this document)
2. All chunks have `chunk_tokens` populated
3. `embeddings.embedding` column exists (Step 9.0 ✅)
4. BGE-M3 model downloaded and ready

**Step 9.2 will:**
- Generate embeddings for each chunk using BGE-M3
- Store vectors in `embeddings.embedding` column
- Batch process 100 chunks at a time
- Track embedding generation status

---

## APPENDIX

### A. Dependencies to Install

```bash
# requirements.txt additions

# NLP libraries
spacy>=3.7.0
en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0-py3-none-any.whl
nltk>=3.8.1

# Token counting
tiktoken>=0.5.0

# Already installed (verify):
# - sqlalchemy>=2.0.23
# - pgvector>=0.2.4
# - pydantic>=2.0.0
```

### B. Environment Variables Reference

```bash
# Complete .env for Step 9.1

# Chunking Configuration
CHUNK_TARGET_TOKENS=512
CHUNK_MAX_TOKENS=600
CHUNK_MIN_TOKENS=100
CHUNK_OVERLAP_TOKENS=50

# NLP Settings
USE_SPACY=true
SPACY_MODEL=en_core_web_sm
NLTK_DATA_PATH=~/nltk_data

# Token Counting
TOKENIZER_MODEL=gpt-3.5-turbo

# Quality Thresholds
MIN_QUALITY_SCORE=0.6
TARGET_QUALITY_SCORE=0.8

# Processing Limits
MAX_TEXT_LENGTH=10000000
SENTENCE_SPLIT_TIMEOUT=30

# Feature Flags
PRESERVE_PARAGRAPHS=true
EXTRACT_METADATA=true
DETECT_STRUCTURE=true

# Database (existing)
DATABASE_URL=postgresql://querybox:querybox_dev_2024@localhost:5432/querybox_core

# Celery (existing)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### C. Migration Scripts

See section 2.4 for complete migration script (`v004_add_chunk_metadata.sql`)

### D. Testing Fixtures

```python
# tests/fixtures/sample_texts.py

SAMPLE_SHORT_TEXT = """
This is a short document with only two sentences.
It should create just one chunk.
"""

SAMPLE_STRUCTURED_TEXT = """
# Introduction

This is the introduction paragraph with some context.
It explains what the document is about.

## Background

The background section provides historical context.
Multiple sentences describe the problem space.

### Technical Details

This subsection dives into specifics.

# Methods

Our methodology consists of three steps.
Each step is described in detail below.

1. First step description
2. Second step description
3. Third step description

# Results

The results show significant improvements.
See Table 1 for detailed metrics.

# Conclusion

In conclusion, we have demonstrated the effectiveness.
"""

SAMPLE_TABLE_TEXT = """
Performance Metrics:

| Metric   | Before | After |
|----------|--------|-------|
| Speed    | 100ms  | 50ms  |
| Accuracy | 85%    | 95%   |

The table above shows our improvements.
"""
```

---

**End of Technical Documentation for Step 9.1: Chunking Improvements**

*This document should be ingested into NotebookLLM or similar tools for reference during implementation.*

*Version: 1.0 | Last Updated: October 24, 2024 | Author: QueryBox Core Team*
