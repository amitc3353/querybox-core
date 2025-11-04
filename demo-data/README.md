# QueryboxCore Demo Data

This directory contains sample documents and queries for testing and demonstrating QueryboxCore's document processing and retrieval capabilities.

## Purpose

The demo data serves multiple purposes:

1. **Testing**: Verify that document upload, processing, and search functionality work correctly
2. **Development**: Quickly populate a development environment with realistic data
3. **Demonstrations**: Show potential users how QueryboxCore handles different document types
4. **Benchmarking**: Measure processing time and search accuracy with known content

## Directory Structure

```
demo-data/
├── README.md                  # This file
├── sample_queries.json        # Test queries for search verification
└── documents/                 # Generated sample documents (created by seed script)
    ├── technical_guide.txt    # RAG architecture guide (15 pages)
    ├── deployment_guide.md    # Deployment instructions (5 pages)
    ├── api_reference.html     # API documentation (10 pages)
    ├── user_manual.txt        # User guide (8 pages)
    └── research_paper.txt     # DPR research paper (20 pages)
```

## Document Types

### 1. Technical Guide (`technical_guide.txt`)
- **Content**: Comprehensive RAG (Retrieval-Augmented Generation) architecture guide
- **Pages**: 15 pages of technical content
- **Topics**: System architecture, document processing, embedding generation, vector search, answer generation, citations
- **Use Case**: Tests technical content processing and semantic search on architectural concepts

### 2. Deployment Guide (`deployment_guide.md`)
- **Content**: Step-by-step deployment instructions for QueryboxCore
- **Format**: Markdown with code blocks and structured sections
- **Pages**: 5 pages
- **Topics**: Prerequisites, installation, configuration, Docker deployment, troubleshooting
- **Use Case**: Tests Markdown parsing and structured documentation retrieval

### 3. API Reference (`api_reference.html`)
- **Content**: Complete API documentation with endpoints, parameters, and examples
- **Format**: HTML with styling and navigation
- **Pages**: 10 pages
- **Topics**: Authentication, document upload, management, search, chat interface, system health
- **Use Case**: Tests HTML parsing and API documentation search

### 4. User Manual (`user_manual.txt`)
- **Content**: Plain text user guide for QueryboxCore
- **Format**: Plain text with ASCII formatting
- **Pages**: 8 pages
- **Topics**: Getting started, uploading documents, searching, chat interface, troubleshooting, FAQ
- **Use Case**: Tests plain text processing and user-focused queries

### 5. Research Paper (`research_paper.txt`)
- **Content**: Dense Passage Retrieval (DPR) research paper excerpt
- **Format**: Academic paper with abstract, methodology, experiments
- **Pages**: 20 pages
- **Topics**: Neural retrieval, dual encoders, contrastive learning, MIPS, evaluation
- **Use Case**: Tests academic content processing and complex technical queries

## Sample Queries

The `sample_queries.json` file contains 10 test queries designed to retrieve relevant passages from the demo documents:

1. **RAG Configuration**: "How to configure the RAG pipeline?" → `technical_guide.txt`
2. **System Requirements**: "What are the system requirements for deployment?" → `deployment_guide.md`
3. **API Upload**: "How do I upload documents via API?" → `api_reference.html`
4. **File Types**: "What file types are supported?" → `user_manual.txt`
5. **DPR Concepts**: "How does Dense Passage Retrieval work?" → `research_paper.txt`
6. **Embeddings**: "What is the embedding generation process?" → `technical_guide.txt`
7. **Docker Deployment**: "How to deploy with Docker Compose?" → `deployment_guide.md`
8. **API Authentication**: "What are the API authentication methods?" → `api_reference.html`
9. **Troubleshooting**: "How to troubleshoot upload failures?" → `user_manual.txt`
10. **Architecture**: "What is the dual-encoder architecture?" → `research_paper.txt`

Each query targets a specific document and tests semantic search accuracy with a minimum similarity score of 0.7.

## How to Use

### Seed Demo Data

Run the seeding script to generate documents and upload them to QueryboxCore:

```bash
# From project root
python backend/scripts/seed_demo.py

# Seed with only 3 documents
python backend/scripts/seed_demo.py --count 3

# Skip search verification
python backend/scripts/seed_demo.py --skip-verify
```

**Using Makefile targets:**

```bash
# Seed demo data only
make seed-demo

# Full demo setup (Docker + migrations + seed)
make demo-setup
```

### What the Script Does

1. **Generates 5 Documents**: Creates sample files in `demo-data/documents/` with realistic technical content
2. **Uploads to QueryboxCore**: Posts files to `/api/v1/upload` endpoint with `force_new=true`
3. **Monitors Processing**: Polls `processing_status` table until extraction, chunking, and embedding complete (max 120s)
4. **Verifies Search**: Runs test queries from `sample_queries.json` to confirm search functionality
5. **Reports Results**: Displays document IDs, processing status, and search verification results

### Prerequisites

Before seeding demo data, ensure:

1. **Backend is running**:
   ```bash
   # Development mode
   docker-compose -f docker-compose.dev.yml up -d

   # Or production mode
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Database is migrated**:
   ```bash
   python backend/scripts/migrate.py upgrade head
   ```

3. **Backend is healthy**:
   ```bash
   curl http://localhost:8000/health
   ```

### Expected Processing Time

- **Document generation**: <1 second (in-memory string operations)
- **File upload (5 docs)**: ~5-10 seconds (includes network overhead)
- **Text extraction**: ~10-15 seconds (plain text is fast)
- **Chunking**: ~5 seconds (semantic chunking for ~100 chunks)
- **Embedding generation**: ~15-30 seconds (BGE-M3 on CPU, faster with GPU)
- **Total time**: ~40-60 seconds

### Verify Demo Data

After seeding, verify the documents are searchable:

```bash
# List all documents
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/documents

# Search for specific content
curl -X POST http://localhost:8000/api/v1/search \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to configure RAG pipeline?",
    "top_k": 5,
    "min_score": 0.7
  }'

# Expected: Results from technical_guide.txt with similarity > 0.7
```

### Query Database Directly

Check documents in the database:

```sql
-- List demo documents
SELECT id, document_name, file_size, status, created_at
FROM documents
WHERE document_metadata->>'demo' = 'true'
ORDER BY created_at DESC;

-- Check processing status
SELECT d.document_name,
       ps.extraction_status,
       ps.chunking_status,
       ps.embedding_status
FROM documents d
JOIN processing_status ps ON d.id = ps.document_id
WHERE d.document_metadata->>'demo' = 'true';

-- Count embeddings generated
SELECT d.document_name, COUNT(e.id) as embedding_count
FROM documents d
LEFT JOIN embeddings e ON d.id = e.document_id
WHERE d.document_metadata->>'demo' = 'true'
GROUP BY d.document_name;
```

## Regenerating Demo Data

To regenerate demo data from scratch:

```bash
# 1. Delete existing demo documents (optional)
# Via API
curl -X DELETE -H "X-API-Key: your-key" \
  http://localhost:8000/api/v1/documents/{document-id}

# Or via database
psql -U querybox -d querybox_core -c \
  "DELETE FROM documents WHERE document_metadata->>'demo' = 'true';"

# 2. Delete generated files
rm -rf demo-data/documents/*.txt demo-data/documents/*.md demo-data/documents/*.html

# 3. Run seed script again
python backend/scripts/seed_demo.py
```

## Customization

### Adding New Documents

1. Create a new generator function in `backend/scripts/seed_demo.py`:

```python
def generate_custom_content() -> str:
    """Generate your custom document content"""
    return """Your content here..."""
```

2. Add it to `_create_sample_documents()`:

```python
custom_path = docs_dir / "custom_doc.txt"
custom_path.write_text(generate_custom_content())
files.append(custom_path)
```

3. Run the seed script:

```bash
python backend/scripts/seed_demo.py
```

### Adding New Test Queries

Edit `sample_queries.json` and add new entries:

```json
{
  "query": "Your test question?",
  "expected_doc": "custom_doc.txt",
  "description": "What this query tests",
  "min_score": 0.7
}
```

## File Size Summary

| Document | Size | Chunks (est.) | Embeddings |
|----------|------|---------------|------------|
| technical_guide.txt | ~85 KB | ~25 | 25 × 1024-dim |
| deployment_guide.md | ~32 KB | ~10 | 10 × 1024-dim |
| api_reference.html | ~48 KB | ~15 | 15 × 1024-dim |
| user_manual.txt | ~56 KB | ~18 | 18 × 1024-dim |
| research_paper.txt | ~68 KB | ~22 | 22 × 1024-dim |
| **Total** | **~289 KB** | **~90** | **~90 embeddings** |

## Troubleshooting

### Issue: Script fails with "Connection refused"
**Solution**: Backend is not running. Start it with `docker-compose up`.

### Issue: Documents stuck in "processing" status
**Solution**:
1. Check Celery worker is running: `docker-compose logs celery-worker`
2. Increase timeout: `python backend/scripts/seed_demo.py` (default 120s)
3. Check logs for extraction/embedding errors

### Issue: Search returns no results
**Solution**:
1. Verify embeddings were generated: Check `embeddings` table
2. Lower min_score threshold: Try 0.5 instead of 0.7
3. Check that processing completed successfully

### Issue: "Module not found" error
**Solution**: Install dependencies:
```bash
cd backend
pip install -r requirements.txt
# Or
pip install -r requirements-prod.txt
```

## Technical Details

### Document Generation

- **Method**: Programmatic content generation (no external files required)
- **Content**: Realistic technical documentation with proper structure
- **Metadata**: Each document tagged with `{"demo": true, "source": "seed_script"}`
- **Deduplication**: Bypassed with `force_new=true` parameter

### Upload Process

- **Method**: HTTP multipart/form-data POST to `/api/v1/upload`
- **Retry Logic**: Exponential backoff with 3 attempts (4s, 8s, 10s intervals)
- **Concurrency**: Sequential uploads (parallel upload can be added if needed)
- **Timeout**: 30s per upload request

### Processing Pipeline

1. **Text Extraction**: Handled by DocumentService
   - `.txt` → Direct UTF-8 read
   - `.md` → Markdown parsing with metadata extraction
   - `.html` → BeautifulSoup content extraction

2. **Semantic Chunking**: Handled by ChunkingService
   - Target size: 512 tokens (configurable)
   - Overlap: 50 tokens
   - Boundary detection: Paragraph/sentence breaks

3. **Embedding Generation**: Handled by EmbeddingService
   - Model: BGE-M3 (1024-dimensional vectors)
   - Batch size: 100 chunks
   - Storage: PostgreSQL with pgvector

### Search Verification

- **Queries**: 3 representative test queries
- **Endpoint**: POST `/api/v1/search`
- **Parameters**: `top_k=5`, `min_score=0.5`
- **Success Criteria**: At least one query returns results

## Related Documentation

- **Technical Spec**: `docs/technical/step-12-quick-wins-demo-foundation.md`
- **Deployment Guide**: `DEPLOYMENT.md`
- **API Documentation**: See `api_reference.html` (generated by seed script)
- **Main README**: `../README.md`

## Support

For issues with demo data:

1. Check logs: `docker-compose logs backend celery-worker`
2. Verify health: `curl http://localhost:8000/health`
3. Review processing status in database
4. Open issue on GitHub with error details

---

**Last Updated**: 2024-12-03
**Step**: 12.3 - Demo Data Pipeline
**Status**: ✅ Complete
