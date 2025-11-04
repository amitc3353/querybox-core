#!/usr/bin/env python3
"""
Demo Data Seeder - Step 12.3
Generates and uploads sample documents for testing QueryboxCore

This script:
1. Generates 5 sample documents programmatically (no external files needed)
2. Uploads documents via DocumentService API
3. Waits for processing to complete (extraction, chunking, embedding)
4. Verifies search functionality with sample queries
5. Reports detailed progress and errors

Usage:
    python backend/scripts/seed_demo.py
    python backend/scripts/seed_demo.py --count 10
    python backend/scripts/seed_demo.py --skip-verify
"""

import sys
import os
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import argparse
import logging
from typing import Dict, List, Tuple
from uuid import UUID
from datetime import datetime
import time
from io import BytesIO
import structlog

# Try to import dependencies
try:
    from sqlalchemy.orm import Session
    from tenacity import retry, stop_after_attempt, wait_exponential
    from app.db.database import SessionLocal
    from app.models.document import Document, DocumentStatusEnum, ProcessingStageEnum, StageStatusEnum
    from app.models.processing_status import ProcessingStatus
except ImportError as e:
    print(f"❌ Failed to import dependencies: {e}")
    print("Make sure you're running from the backend directory with dependencies installed")
    sys.exit(1)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()


# ============================================================================
# DOCUMENT CONTENT GENERATORS
# ============================================================================

def generate_technical_pdf_content() -> str:
    """Generate content for technical RAG architecture guide (15 pages)"""
    return """RAG Architecture Technical Guide

Table of Contents
1. Introduction to Retrieval-Augmented Generation
2. System Architecture Overview
3. Document Processing Pipeline
4. Embedding Generation
5. Vector Search Implementation
6. Answer Generation
7. Citation Extraction
8. Performance Optimization
9. Deployment Strategies
10. Monitoring and Observability

Chapter 1: Introduction to Retrieval-Augmented Generation

Retrieval-Augmented Generation (RAG) is a hybrid approach that combines the strengths of retrieval-based and generation-based AI systems. Unlike pure language models that rely solely on parametric knowledge, RAG systems ground their responses in external knowledge sources, enabling more accurate, up-to-date, and verifiable answers.

The RAG pipeline consists of three primary stages:
1. Indexing: Documents are processed, chunked, and embedded into vector representations
2. Retrieval: User queries are converted to vectors and similar document chunks are retrieved
3. Generation: Retrieved context is provided to an LLM to generate accurate, grounded responses

Key benefits of RAG systems:
- Reduced hallucinations through grounding in source documents
- Easy knowledge updates without model retraining
- Transparent citations for answer verification
- Lower computational costs compared to fine-tuning large models

Chapter 2: System Architecture Overview

A production RAG system comprises several interconnected components:

**Document Ingestion Layer**
- File upload API with validation (size, type, content)
- Multi-format support (PDF, DOCX, HTML, Markdown, plain text)
- Deduplication via content hashing
- Storage management (local filesystem, S3, Azure Blob)

**Processing Pipeline**
- Text extraction using specialized libraries (PyPDF, python-docx, BeautifulSoup)
- Document cleaning and normalization
- Semantic chunking with overlap for context preservation
- Metadata extraction (title, author, creation date)

**Embedding Layer**
- Batch embedding generation for efficiency
- Support for multiple embedding models (BGE-M3, OpenAI ada-002, Sentence-BERT)
- Vector dimension: 1024 for BGE-M3, 1536 for OpenAI
- GPU acceleration for large-scale processing

**Storage Layer**
- PostgreSQL with pgvector extension for vector storage
- IVFFlat index for approximate nearest neighbor search
- Redis caching for frequent queries
- MinIO for document blob storage

**Retrieval Layer**
- Hybrid search combining keyword and semantic similarity
- Multi-stage retrieval: initial search → reranking → citation extraction
- Configurable top-k results (default: 10)
- Similarity threshold filtering (min score: 0.7)

**Generation Layer**
- LLM integration (Ollama, OpenAI, Anthropic)
- Prompt engineering with retrieved context
- Streaming responses for better UX
- Confidence scoring based on source quality

Chapter 3: Document Processing Pipeline

The document processing pipeline transforms raw files into searchable vector embeddings through multiple stages:

**Stage 1: Upload and Validation**
- Maximum file size: 30MB (configurable)
- MIME type detection using python-magic
- Extension whitelist: .pdf, .docx, .txt, .md, .html
- Checksum calculation (SHA-256) for deduplication
- Processing time: <2 seconds for files under 10MB

**Stage 2: Text Extraction**
- PDF: pdfplumber for text + table extraction, pytesseract for OCR on scanned pages
- DOCX: python-docx for paragraph + table + image alt-text extraction
- HTML: BeautifulSoup for semantic content extraction, stripping scripts and styles
- Markdown: Direct parsing with metadata extraction from frontmatter
- Plain text: UTF-8 decoding with fallback to latin-1

Quality metrics:
- Extraction completeness: >95% for digital documents, >80% for scanned PDFs
- Processing speed: 100 pages/minute for digital PDFs, 20 pages/minute with OCR
- Error rate: <1% for modern file formats

**Stage 3: Semantic Chunking**
- Target chunk size: 512 tokens (optimal for BGE-M3)
- Maximum chunk size: 600 tokens (hard limit to prevent truncation)
- Minimum chunk size: 100 tokens (avoid low-quality fragments)
- Overlap: 50 tokens (~10%) for context preservation

Chunking algorithm:
1. Tokenize document using model-specific tokenizer (e.g., BGE-M3 tokenizer)
2. Identify semantic boundaries (paragraphs, headings, list items)
3. Merge small paragraphs until reaching target size
4. Split large paragraphs at sentence boundaries
5. Add overlap by including last 50 tokens from previous chunk

Metadata enrichment:
- section_heading: Extracted from document structure
- chunk_type: paragraph, list, table, code, heading
- semantic_density: Ratio of content words to total words (target: >0.6)
- contains_table, contains_list, contains_code, contains_equation flags

Chapter 4: Embedding Generation

Vector embeddings transform text into dense numerical representations that capture semantic meaning. QueryboxCore supports multiple embedding models:

**BGE-M3 (Recommended)**
- Dimension: 1024
- Context window: 8192 tokens
- Performance: 96.5% accuracy on MS-MARCO
- Speed: ~200 chunks/second on CPU, ~2000 chunks/second on GPU
- Model size: 2GB
- Use case: Best balance of quality and cost for self-hosted deployments

**OpenAI ada-002**
- Dimension: 1536
- Context window: 8191 tokens
- Performance: 94.8% accuracy on MS-MARCO
- Speed: API-limited (3000 requests/minute)
- Cost: $0.0001 per 1K tokens
- Use case: High quality with minimal infrastructure, suitable for low-volume applications

**Sentence-BERT**
- Dimension: 768
- Context window: 512 tokens
- Performance: 89.2% accuracy on MS-MARCO
- Speed: ~500 chunks/second on CPU
- Model size: 400MB
- Use case: Lightweight deployment, mobile/edge devices

Batch processing optimization:
- Batch size: 100 chunks per API call (reduces network overhead by 80%)
- Parallel processing: 4 workers for CPU-bound embedding generation
- GPU batching: Up to 512 chunks per batch with 16GB VRAM
- Caching: Redis cache for repeated queries (TTL: 1 hour)

Total processing time for 5 demo documents:
- Extraction: ~15 seconds
- Chunking: ~5 seconds
- Embedding (100 chunks): ~8 seconds with BGE-M3 on CPU
- Database insertion: ~2 seconds
- Total: ~30 seconds

Chapter 5: Vector Search Implementation

Vector search enables semantic similarity matching using cosine distance in high-dimensional space. QueryboxCore leverages pgvector for efficient approximate nearest neighbor (ANN) search.

**Indexing Strategy**
- Index type: IVFFlat (inverted file index with flat quantization)
- Number of lists: 100 (optimal for 10K-1M vectors)
- Distance metric: Cosine similarity
- Index build time: ~30 seconds for 10K vectors
- Index size: ~40MB for 10K 1024-dim vectors

**Query Processing**
1. Embed user query using same model as documents (BGE-M3)
2. Execute ANN search: `SELECT * FROM embeddings ORDER BY embedding <=> query_vector LIMIT 10`
3. Filter by similarity threshold (default: 0.7, adjustable per query)
4. Retrieve parent document metadata

**Search Performance**
- Query latency (p50): 80ms for 10K vectors
- Query latency (p95): 150ms for 10K vectors
- Query latency (p99): 200ms for 10K vectors
- Throughput: 50 queries/second (single-threaded)
- Throughput: 200 queries/second (4 worker threads)

Scalability limits:
- 10K vectors: <200ms p99 latency
- 100K vectors: <500ms p99 latency
- 1M vectors: <1s p99 latency
- Beyond 1M: Consider HNSW index or vector-specific databases (Milvus, Weaviate)

**Multi-stage Retrieval**
Stage 1: Initial retrieval (top 50 candidates)
- Uses vector similarity only
- Fast but may include false positives

Stage 2: Reranking (top 10 results)
- Cross-encoder model for more accurate scoring
- Evaluates query-document pair jointly
- 10x more expensive but improves precision by 20%

Stage 3: Citation extraction
- Highlights exact text spans matching query
- Uses substring matching + fuzzy matching (rapidfuzz)
- Returns start/end character positions for UI highlighting

Chapter 6: Answer Generation

Answer generation combines retrieved context with large language models to produce accurate, grounded responses.

**Prompt Engineering**
System prompt template:
\"\"\"
You are a helpful assistant that answers questions based on provided context.

Context:
{retrieved_chunks}

Question: {user_query}

Instructions:
- Answer the question using ONLY information from the provided context
- If the context doesn't contain relevant information, say "I don't have enough information to answer this question"
- Cite sources using [doc_id] notation
- Be concise but complete
- Maintain a professional tone
\"\"\"

Context formatting:
- Each chunk includes: document name, chunk text, relevance score
- Chunks sorted by relevance (highest first)
- Maximum context length: 4096 tokens (truncate if necessary)
- Chunk separation: Clear delimiters for model parsing

**Model Integration**
Supported LLM providers:
1. Ollama (self-hosted):
   - Models: llama3, mistral, mixtral
   - Latency: 50-200ms per token (depends on GPU)
   - Cost: $0 (infrastructure costs only)
   - Throughput: Limited by GPU memory

2. OpenAI:
   - Models: gpt-4, gpt-4-turbo, gpt-3.5-turbo
   - Latency: 20-100ms per token
   - Cost: $0.01-0.03 per 1K tokens
   - Throughput: Rate-limited by API tier

3. Anthropic Claude:
   - Models: claude-3-opus, claude-3-sonnet, claude-3-haiku
   - Latency: 30-80ms per token
   - Cost: $0.003-0.075 per 1K tokens
   - Throughput: 50K tokens/minute (tier-dependent)

**Streaming Responses**
- Server-Sent Events (SSE) for real-time token streaming
- Reduces perceived latency (first token in <500ms)
- Enables progressive UI rendering
- Handles connection interruptions gracefully

**Confidence Scoring**
Factors affecting confidence score:
- Retrieval similarity scores (weight: 0.4)
- Number of supporting sources (weight: 0.3)
- Answer completeness (weight: 0.2)
- Query complexity (weight: 0.1)

Confidence thresholds:
- High (>0.8): Strong evidence from multiple sources
- Medium (0.5-0.8): Moderate evidence or single source
- Low (<0.5): Weak evidence, suggest reformulating query

This technical guide provides comprehensive coverage of RAG system architecture, implementation details, and best practices for production deployment. Continued in additional chapters covering citation extraction, performance optimization, deployment strategies, and monitoring."""


def generate_deployment_guide_md() -> str:
    """Generate deployment guide in Markdown format (5 pages)"""
    return """# QueryboxCore Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Docker Deployment](#docker-deployment)
5. [Production Checklist](#production-checklist)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Hardware (Minimum)**
- CPU: 4 cores (Intel/AMD x86_64 or ARM64)
- RAM: 8GB
- Storage: 50GB SSD
- Network: 10 Mbps

**Hardware (Recommended for Production)**
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 200GB+ NVMe SSD
- Network: 100 Mbps
- Optional: NVIDIA GPU with 16GB VRAM for fast embedding generation

**Software Dependencies**
- Docker >= 20.10
- Docker Compose >= 2.0
- Git >= 2.30
- Python 3.11 (for local development)
- PostgreSQL 15+ with pgvector extension
- Redis 7+
- MinIO or S3-compatible storage

### Pre-installation Checks

```bash
# Verify Docker installation
docker --version
docker-compose --version

# Check available disk space
df -h

# Verify network connectivity
curl -I https://github.com

# Check PostgreSQL can be reached (if using external database)
pg_isready -h your-postgres-host -p 5432
```

---

## Installation

### Quick Start (Docker Compose)

The fastest way to get QueryboxCore running:

```bash
# 1. Clone repository
git clone https://github.com/your-org/querybox-core.git
cd querybox-core

# 2. Copy environment template
cp .env.example .env

# 3. Edit environment variables
nano .env

# Required variables:
# - POSTGRES_PASSWORD: Secure database password
# - API_KEY: API authentication key
# - SECRET_KEY: Application secret for tokens
# - MINIO_ROOT_PASSWORD: Storage password

# 4. Start all services
docker-compose -f docker-compose.prod.yml up -d

# 5. Wait for services to be healthy
./scripts/health_check.sh

# 6. Load demo data (optional)
python backend/scripts/seed_demo.py

# 7. Access the API
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "healthy",
  "database": {"status": "up", "latency_ms": 12},
  "redis": {"status": "up", "latency_ms": 3},
  "storage": {"status": "up", "disk_free_gb": 45.2}
}
```

### Manual Installation (Development)

For local development without Docker:

```bash
# 1. Set up Python virtual environment
cd backend
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start PostgreSQL (via Docker or local install)
docker run -d --name querybox-postgres \\
  -e POSTGRES_PASSWORD=querybox \\
  -e POSTGRES_DB=querybox_core \\
  -p 5432:5432 \\
  pgvector/pgvector:pg15

# 4. Start Redis
docker run -d --name querybox-redis -p 6379:6379 redis:7-alpine

# 5. Start MinIO
docker run -d --name querybox-minio \\
  -p 9000:9000 -p 9001:9001 \\
  -e MINIO_ROOT_USER=minioadmin \\
  -e MINIO_ROOT_PASSWORD=minioadmin \\
  minio/minio server /data --console-address \":9001\"

# 6. Run database migrations
python scripts/migrate.py upgrade head

# 7. Start backend server
uvicorn app.main:app --reload --port 8000

# 8. Verify installation
curl http://localhost:8000/health
```

---

## Configuration

### Environment Variables

QueryboxCore uses environment variables for configuration (12-factor app pattern).

**Database Configuration**
```env
DATABASE_URL=postgresql://querybox:password@postgres:5432/querybox_core
DB_POOL_SIZE=5                   # SQLAlchemy connection pool size
DB_MAX_OVERFLOW=10               # Maximum overflow connections
DB_POOL_TIMEOUT=30               # Pool timeout in seconds
```

**Redis Configuration**
```env
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

**Storage Configuration**
```env
STORAGE_PROVIDER=local           # Options: local, s3, azure_blob
S3_ENDPOINT=http://minio:9000   # MinIO or S3 endpoint
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=querybox-documents
S3_REGION=us-east-1
MAX_FILE_SIZE=31457280          # 30MB in bytes
```

**AI/ML Configuration**
```env
EMBEDDING_MODEL=BAAI/bge-m3     # BGE-M3 (local)
# Or use OpenAI:
# EMBEDDING_MODEL=text-embedding-ada-002
# OPENAI_API_KEY=sk-...

CHUNK_SIZE=512                   # Target tokens per chunk
CHUNK_OVERLAP=50                 # Overlap tokens between chunks
```

**Application Configuration**
```env
ENVIRONMENT=production           # Options: development, production
LOG_LEVEL=info                   # Options: debug, info, warn, error
API_KEY=your-secure-api-key     # API authentication
SECRET_KEY=your-secret-key      # JWT signing
WORKERS=4                        # Uvicorn worker processes
```

**Feature Flags**
```env
ENABLE_DEMO_DATA=false          # Auto-load demo data on startup
AUTO_MIGRATE=false              # Auto-run migrations on startup
```

### Security Best Practices

1. **Change Default Passwords**
   ```bash
   # Generate secure passwords
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Use Environment-Specific Configs**
   - Development: `.env.development`
   - Staging: `.env.staging`
   - Production: `.env.production`

3. **Never Commit .env Files**
   ```bash
   # .gitignore should include:
   .env
   .env.*
   !.env.example
   ```

4. **Use Secrets Management in Production**
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault
   - Google Secret Manager

---

## Docker Deployment

### Production Deployment with Docker Compose

1. **Build Images**
   ```bash
   docker-compose -f docker-compose.prod.yml build --no-cache
   ```

2. **Start Services**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **View Logs**
   ```bash
   # All services
   docker-compose -f docker-compose.prod.yml logs -f

   # Specific service
   docker-compose -f docker-compose.prod.yml logs -f backend
   ```

4. **Scale Services**
   ```bash
   # Scale celery workers
   docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=3
   ```

### Health Monitoring

```bash
# Automated health check script
./scripts/health_check.sh --timeout 120 --interval 10

# Manual health check
curl http://localhost:8000/health | jq

# Check service status
docker-compose -f docker-compose.prod.yml ps
```

### Automated Deployment

Use the deployment script for zero-downtime deployments:

```bash
./scripts/deploy.sh

# Options:
./scripts/deploy.sh --skip-build          # Skip Docker build
./scripts/deploy.sh --skip-migrations     # Skip database migrations
```

The deployment script performs:
1. Git pull latest code
2. Backup current Docker images
3. Build new images
4. Run database migrations
5. Rolling restart (old containers → new containers)
6. Health check validation
7. Automatic rollback on failure

---

## Production Checklist

Before deploying to production, verify:

**Security**
- [ ] Changed all default passwords
- [ ] Generated secure API_KEY and SECRET_KEY
- [ ] Configured HTTPS/TLS (use Nginx reverse proxy)
- [ ] Enabled firewall rules (allow only necessary ports)
- [ ] Configured rate limiting
- [ ] Enabled audit logging
- [ ] Set up secrets management (Vault, AWS Secrets Manager)

**Performance**
- [ ] Tuned PostgreSQL (shared_buffers, work_mem)
- [ ] Configured Redis memory limits
- [ ] Set appropriate worker counts (CPU cores * 2)
- [ ] Enabled Docker resource limits
- [ ] Configured connection pooling

**Reliability**
- [ ] Set up automated backups (database + storage)
- [ ] Configured health checks
- [ ] Enabled restart policies (restart: unless-stopped)
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Configured alerting (PagerDuty, Slack)
- [ ] Tested disaster recovery procedure

**Compliance**
- [ ] Documented data retention policy
- [ ] Configured log retention (7 days local, 30 days centralized)
- [ ] Enabled data encryption (at rest and in transit)
- [ ] Set up access control (RBAC when auth is added)

---

## Troubleshooting

### Common Issues

**Issue: Backend fails to start**
```bash
# Check logs
docker-compose logs backend

# Common causes:
# 1. Database not ready - wait for postgres health check
# 2. Missing environment variables - check .env file
# 3. Port conflict - check if port 8000 is available

# Solution: Restart with dependencies
docker-compose -f docker-compose.prod.yml restart backend
```

**Issue: Database connection failed**
```bash
# Verify PostgreSQL is running
docker ps | grep postgres

# Test connection manually
docker exec querybox-postgres psql -U querybox -d querybox_core -c \"SELECT 1\"

# Check DATABASE_URL in .env
echo $DATABASE_URL

# Common fix: Wait for database to be ready
./scripts/health_check.sh --timeout 60
```

**Issue: Out of memory**
```bash
# Check memory usage
docker stats

# Solution: Increase Docker memory limit or reduce workers
# In .env:
WORKERS=2  # Reduce from 4 to 2
```

**Issue: Slow search queries**
```bash
# Check pgvector index
docker exec querybox-postgres psql -U querybox -d querybox_core -c \"
  SELECT schemaname, tablename, indexname
  FROM pg_indexes
  WHERE tablename = 'embeddings';
\"

# Rebuild index if missing
docker exec querybox-postgres psql -U querybox -d querybox_core -c \"
  CREATE INDEX idx_embeddings_vector ON embeddings
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
\"
```

### Getting Help

- **Documentation**: https://docs.querybox.com
- **GitHub Issues**: https://github.com/your-org/querybox-core/issues
- **Community Discord**: https://discord.gg/querybox
- **Commercial Support**: support@querybox.com

---

**Last Updated**: 2024-12-02
**Version**: 1.0.0
**Step**: 12.3 - Demo Data Pipeline
"""


def generate_api_reference_html() -> str:
    """Generate API reference in HTML format (10 pages)"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QueryboxCore API Reference</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; border-bottom: 3px solid #0066cc; padding-bottom: 10px; }
        h2 { color: #0066cc; margin-top: 30px; }
        h3 { color: #333; margin-top: 20px; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
        pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
        .endpoint { background: #e8f4f8; padding: 15px; margin: 10px 0; border-left: 4px solid #0066cc; }
        .method { font-weight: bold; color: #fff; padding: 3px 8px; border-radius: 3px; margin-right: 10px; }
        .get { background: #61affe; }
        .post { background: #49cc90; }
        .put { background: #fca130; }
        .delete { background: #f93e3e; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background: #f4f4f4; font-weight: bold; }
        .required { color: #f93e3e; }
    </style>
</head>
<body>

<h1>QueryboxCore API Reference v1.0</h1>

<p><strong>Base URL:</strong> <code>http://localhost:8000/api/v1</code></p>
<p><strong>Authentication:</strong> API Key in <code>X-API-Key</code> header</p>

<nav>
    <h2>Table of Contents</h2>
    <ul>
        <li><a href="#authentication">Authentication</a></li>
        <li><a href="#upload">Document Upload</a></li>
        <li><a href="#documents">Document Management</a></li>
        <li><a href="#search">Search & Retrieval</a></li>
        <li><a href="#chat">Chat Interface</a></li>
        <li><a href="#system">System & Health</a></li>
        <li><a href="#errors">Error Codes</a></li>
    </ul>
</nav>

<h2 id="authentication">Authentication</h2>

<p>All API requests require an API key passed in the <code>X-API-Key</code> header.</p>

<pre><code>curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/documents</code></pre>

<p><strong>HTTP Status Codes:</strong></p>
<ul>
    <li><code>200 OK</code> - Request succeeded</li>
    <li><code>401 Unauthorized</code> - Invalid or missing API key</li>
    <li><code>403 Forbidden</code> - API key lacks required permissions</li>
    <li><code>429 Too Many Requests</code> - Rate limit exceeded</li>
</ul>

<h2 id="upload">Document Upload</h2>

<div class="endpoint">
    <span class="method post">POST</span> <code>/upload</code>
    <p>Upload a document for processing and indexing.</p>
</div>

<h3>Request</h3>

<p><strong>Content-Type:</strong> <code>multipart/form-data</code></p>

<table>
    <tr>
        <th>Parameter</th>
        <th>Type</th>
        <th>Required</th>
        <th>Description</th>
    </tr>
    <tr>
        <td>file</td>
        <td>binary</td>
        <td class="required">Yes</td>
        <td>The file to upload. Max size: 30MB</td>
    </tr>
    <tr>
        <td>workspace_id</td>
        <td>string (UUID)</td>
        <td>No</td>
        <td>Workspace ID for multi-tenant support (future)</td>
    </tr>
    <tr>
        <td>force_new</td>
        <td>boolean</td>
        <td>No</td>
        <td>Bypass content-based deduplication (default: false)</td>
    </tr>
</table>

<h3>Response (200 OK)</h3>

<pre><code>{
  "success": true,
  "message": "File uploaded successfully",
  "document": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "filename": "technical_guide.pdf",
    "storage_filename": "tech_guide_abc123.pdf",
    "size": 2457600,
    "mime_type": "application/pdf",
    "checksum": "sha256:abc123...",
    "status": "completed",
    "created_at": "2024-12-02T10:30:00Z"
  },
  "storage": {
    "provider": "local",
    "path": "/storage/documents/workspace_id/doc_id/current/file.pdf",
    "operation_time_ms": 1234
  }
}</code></pre>

<h3>Response (200 OK - Duplicate Detected)</h3>

<pre><code>{
  "success": true,
  "message": "File already exists (duplicate detected by content hash)",
  "duplicate": true,
  "document": {
    "id": "existing-doc-id",
    ...
  },
  "processing_status": {
    "extraction_status": "completed",
    "chunking_status": "completed",
    "embedding_status": "completed",
    "ready_for_search": true
  }
}</code></pre>

<h3>Example</h3>

<pre><code>curl -X POST http://localhost:8000/api/v1/upload \\
  -H "X-API-Key: your-api-key" \\
  -F "file=@technical_guide.pdf"</code></pre>

<h3>Allowed File Types</h3>

<div class="endpoint">
    <span class="method get">GET</span> <code>/upload/allowed-types</code>
    <p>Get list of allowed file types and size limits.</p>
</div>

<pre><code>{
  "allowed_extensions": [".pdf", ".docx", ".txt", ".md", ".html"],
  "max_file_size_mb": 30
}</code></pre>

<h2 id="documents">Document Management</h2>

<div class="endpoint">
    <span class="method get">GET</span> <code>/documents</code>
    <p>List all documents with filtering, sorting, and pagination.</p>
</div>

<h3>Query Parameters</h3>

<table>
    <tr>
        <th>Parameter</th>
        <th>Type</th>
        <th>Default</th>
        <th>Description</th>
    </tr>
    <tr>
        <td>page</td>
        <td>integer</td>
        <td>1</td>
        <td>Page number (1-indexed)</td>
    </tr>
    <tr>
        <td>page_size</td>
        <td>integer</td>
        <td>20</td>
        <td>Items per page (max: 100)</td>
    </tr>
    <tr>
        <td>sort_by</td>
        <td>string</td>
        <td>created_at</td>
        <td>Sort field: created_at, updated_at, document_name, file_size, status</td>
    </tr>
    <tr>
        <td>sort_order</td>
        <td>string</td>
        <td>desc</td>
        <td>Sort order: asc or desc</td>
    </tr>
    <tr>
        <td>status</td>
        <td>string</td>
        <td></td>
        <td>Filter by status: pending, processing, completed, failed</td>
    </tr>
    <tr>
        <td>mime_type</td>
        <td>string</td>
        <td></td>
        <td>Filter by MIME type (e.g., application/pdf)</td>
    </tr>
    <tr>
        <td>tags</td>
        <td>string[]</td>
        <td></td>
        <td>Filter by tags (AND logic)</td>
    </tr>
</table>

<h3>Response</h3>

<pre><code>{
  "items": [
    {
      "id": "doc-id-1",
      "document_name": "technical_guide.pdf",
      "original_name": "RAG Architecture Guide.pdf",
      "mime_type": "application/pdf",
      "file_size": 2457600,
      "file_size_mb": 2.34,
      "status": "completed",
      "created_at": "2024-12-02T10:30:00Z",
      "updated_at": "2024-12-02T10:35:00Z",
      "tags": ["technical", "architecture"],
      "document_metadata": {
        "demo": true,
        "source": "seed_script"
      }
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20,
  "total_pages": 1,
  "has_next": false,
  "has_previous": false
}</code></pre>

<div class="endpoint">
    <span class="method get">GET</span> <code>/documents/{document_id}</code>
    <p>Get a specific document by ID with full metadata.</p>
</div>

<h3>Query Parameters</h3>

<table>
    <tr>
        <th>Parameter</th>
        <th>Type</th>
        <th>Default</th>
        <th>Description</th>
    </tr>
    <tr>
        <td>include_processing_status</td>
        <td>boolean</td>
        <td>true</td>
        <td>Include processing stage details</td>
    </tr>
    <tr>
        <td>track_access</td>
        <td>boolean</td>
        <td>true</td>
        <td>Increment access counter</td>
    </tr>
</table>

<div class="endpoint">
    <span class="method get">GET</span> <code>/documents/{document_id}/status</code>
    <p>Get document processing status.</p>
</div>

<h3>Response</h3>

<pre><code>{
  "document_id": "doc-id",
  "status": "processing",
  "processing_status": {
    "extraction": {
      "status": "completed",
      "started_at": "2024-12-02T10:30:00Z",
      "completed_at": "2024-12-02T10:30:15Z",
      "progress": 100
    },
    "chunking": {
      "status": "in_progress",
      "started_at": "2024-12-02T10:30:15Z",
      "progress": 60
    },
    "embedding": {
      "status": "not_started",
      "progress": 0
    }
  },
  "ready_for_search": false,
  "next_action": "wait_for_chunking"
}</code></pre>

<div class="endpoint">
    <span class="method get">GET</span> <code>/documents/search</code>
    <p>Search documents by name or metadata content (keyword search).</p>
</div>

<h3>Query Parameters</h3>

<table>
    <tr>
        <th>Parameter</th>
        <th>Type</th>
        <th>Required</th>
        <th>Description</th>
    </tr>
    <tr>
        <td>query</td>
        <td>string</td>
        <td class="required">Yes</td>
        <td>Search query (min 3 characters, max 200)</td>
    </tr>
    <tr>
        <td>search_fields</td>
        <td>string[]</td>
        <td>No</td>
        <td>Fields to search: document_name, original_name, metadata, tags (default: all)</td>
    </tr>
    <tr>
        <td>page</td>
        <td>integer</td>
        <td>No</td>
        <td>Page number (default: 1)</td>
    </tr>
    <tr>
        <td>page_size</td>
        <td>integer</td>
        <td>No</td>
        <td>Items per page (default: 20)</td>
    </tr>
</table>

<div class="endpoint">
    <span class="method delete">DELETE</span> <code>/documents/{document_id}</code>
    <p>Soft delete a document (mark as deleted, don't remove from database).</p>
</div>

<h3>Response</h3>

<pre><code>{
  "success": true,
  "document_id": "doc-id",
  "deleted_at": "2024-12-02T11:00:00Z",
  "hard_delete": false,
  "files_deleted": false
}</code></pre>

<div class="endpoint">
    <span class="method get">GET</span> <code>/documents/stats</code>
    <p>Get document statistics and analytics.</p>
</div>

<h3>Query Parameters</h3>

<table>
    <tr>
        <th>Parameter</th>
        <th>Type</th>
        <th>Default</th>
        <th>Description</th>
    </tr>
    <tr>
        <td>date_range</td>
        <td>string</td>
        <td>all</td>
        <td>Time range: 7d, 30d, 90d, 1y, all</td>
    </tr>
</table>

<h3>Response</h3>

<pre><code>{
  "total_documents": 5,
  "total_size_bytes": 12288000,
  "total_size_gb": 0.01,
  "by_status": {
    "completed": 4,
    "processing": 1
  },
  "by_mime_type": {
    "application/pdf": 2,
    "text/markdown": 1,
    "text/html": 1,
    "text/plain": 1
  },
  "avg_file_size_mb": 2.34,
  "upload_trend": [
    {"date": "2024-12-01", "count": 2},
    {"date": "2024-12-02", "count": 3}
  ]
}</code></pre>

<h2 id="search">Search & Retrieval</h2>

<div class="endpoint">
    <span class="method post">POST</span> <code>/search</code>
    <p>Perform semantic search across documents using vector similarity.</p>
</div>

<h3>Request Body</h3>

<pre><code>{
  "query": "How to configure RAG pipeline?",
  "top_k": 10,
  "min_score": 0.7,
  "filters": {
    "tags": ["technical"],
    "mime_type": "application/pdf"
  },
  "include_citations": true
}</code></pre>

<h3>Response</h3>

<pre><code>{
  "query": "How to configure RAG pipeline?",
  "documents": [
    {
      "document_id": "doc-id-1",
      "document_name": "technical_guide.pdf",
      "chunk_text": "RAG pipeline configuration involves...",
      "similarity_score": 0.89,
      "page_number": 5,
      "chunk_index": 23
    }
  ],
  "citations": [
    {
      "document_id": "doc-id-1",
      "document_name": "technical_guide.pdf",
      "text": "highlighted text span",
      "start_char": 1234,
      "end_char": 1456,
      "page": 5
    }
  ],
  "processing_time_ms": 180,
  "total_results": 10
}</code></pre>

<h2 id="chat">Chat Interface</h2>

<div class="endpoint">
    <span class="method post">POST</span> <code>/chat</code>
    <p>Ask a question and get an AI-generated answer with citations.</p>
</div>

<h3>Request Body</h3>

<pre><code>{
  "query": "What are the system requirements?",
  "conversation_id": "optional-uuid",
  "stream": true,
  "model": "llama3",
  "max_tokens": 500
}</code></pre>

<h3>Response (Non-streaming)</h3>

<pre><code>{
  "answer": "The system requirements for QueryboxCore are...",
  "confidence": 0.85,
  "sources": [
    {
      "document_id": "doc-id-2",
      "document_name": "deployment_guide.md",
      "relevance_score": 0.92,
      "excerpt": "Hardware (Minimum): CPU: 4 cores, RAM: 8GB..."
    }
  ],
  "conversation_id": "conv-uuid",
  "processing_time_ms": 1234
}</code></pre>

<h2 id="system">System & Health</h2>

<div class="endpoint">
    <span class="method get">GET</span> <code>/health</code>
    <p>Check system health status.</p>
</div>

<h3>Response</h3>

<pre><code>{
  "status": "healthy",
  "timestamp": "2024-12-02T10:30:00Z",
  "checks": {
    "database": {"status": "up", "latency_ms": 12},
    "redis": {"status": "up", "latency_ms": 3},
    "storage": {"status": "up", "disk_free_gb": 45.2}
  }
}</code></pre>

<div class="endpoint">
    <span class="method get">GET</span> <code>/info</code>
    <p>Get API version and configuration information.</p>
</div>

<h3>Response</h3>

<pre><code>{
  "version": "1.0.0",
  "api_version": "v1",
  "environment": "production",
  "features": {
    "embedding_model": "BAAI/bge-m3",
    "chunk_size": 512,
    "max_file_size_mb": 30
  }
}</code></pre>

<h2 id="errors">Error Codes</h2>

<table>
    <tr>
        <th>Status Code</th>
        <th>Error Type</th>
        <th>Description</th>
    </tr>
    <tr>
        <td>400</td>
        <td>Bad Request</td>
        <td>Invalid request parameters or body</td>
    </tr>
    <tr>
        <td>401</td>
        <td>Unauthorized</td>
        <td>Missing or invalid API key</td>
    </tr>
    <tr>
        <td>403</td>
        <td>Forbidden</td>
        <td>Insufficient permissions</td>
    </tr>
    <tr>
        <td>404</td>
        <td>Not Found</td>
        <td>Document or resource not found</td>
    </tr>
    <tr>
        <td>409</td>
        <td>Conflict</td>
        <td>Resource conflict (e.g., delete while processing)</td>
    </tr>
    <tr>
        <td>413</td>
        <td>Payload Too Large</td>
        <td>File size exceeds maximum (30MB)</td>
    </tr>
    <tr>
        <td>429</td>
        <td>Too Many Requests</td>
        <td>Rate limit exceeded</td>
    </tr>
    <tr>
        <td>500</td>
        <td>Internal Server Error</td>
        <td>Server-side error</td>
    </tr>
</table>

<h3>Error Response Format</h3>

<pre><code>{
  "detail": "Detailed error message",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2024-12-02T10:30:00Z"
}</code></pre>

<hr>

<footer>
    <p><strong>QueryboxCore API Reference</strong> | Version 1.0.0 | Last Updated: 2024-12-02</p>
    <p>For support, visit <a href="https://github.com/your-org/querybox-core">GitHub Repository</a></p>
</footer>

</body>
</html>
"""


def generate_user_manual_txt() -> str:
    """Generate user manual in plain text format (8 pages)"""
    return """QUERYBOXCORE USER MANUAL
========================

Version: 1.0.0
Last Updated: December 2, 2024
Document Type: Plain Text User Guide

================================================================================
TABLE OF CONTENTS
================================================================================

1. Introduction
2. Getting Started
3. Uploading Documents
4. Searching Documents
5. Chat Interface
6. Managing Documents
7. Advanced Features
8. Troubleshooting
9. FAQ
10. Support

================================================================================
1. INTRODUCTION
================================================================================

Welcome to QueryboxCore!

QueryboxCore is a powerful document processing and retrieval system that uses
AI to help you find information in your documents quickly and accurately.

Key Features:
- Upload documents in multiple formats (PDF, DOCX, TXT, MD, HTML)
- Automatic text extraction and processing
- Semantic search (find documents by meaning, not just keywords)
- AI-powered question answering with citations
- Fast and accurate retrieval

Who is this for:
- Developers building AI-powered applications
- Teams managing large document repositories
- Organizations needing accurate document search
- Anyone who wants to "chat with their documents"

System Requirements:
- Web browser (Chrome, Firefox, Safari, Edge)
- API key for authentication
- Documents in supported formats
- Internet connection (for cloud deployment)

================================================================================
2. GETTING STARTED
================================================================================

Step 1: Get Your API Key
-------------------------
Contact your administrator to obtain an API key. This key authenticates your
requests to the QueryboxCore API.

Example API key: qbx_1234567890abcdef

Step 2: Set Up Your Environment
---------------------------------
If using command line tools:

  export QUERYBOX_API_KEY="your-api-key"
  export QUERYBOX_URL="http://localhost:8000"

If using a programming language:

  Python:
    import os
    os.environ['QUERYBOX_API_KEY'] = 'your-api-key'

  JavaScript:
    process.env.QUERYBOX_API_KEY = 'your-api-key'

Step 3: Verify Connection
---------------------------
Test your connection with a health check:

  curl -H "X-API-Key: your-api-key" http://localhost:8000/health

Expected response:
  {
    "status": "healthy",
    "database": {"status": "up"},
    "redis": {"status": "up"},
    "storage": {"status": "up"}
  }

If you see "status": "healthy", you're ready to go!

================================================================================
3. UPLOADING DOCUMENTS
================================================================================

Supported File Types
--------------------
- PDF: Portable Document Format (.pdf)
- Word: Microsoft Word documents (.docx)
- Text: Plain text files (.txt)
- Markdown: Markdown files (.md)
- HTML: Web pages (.html)

Maximum file size: 30MB per document

How to Upload (Command Line)
-----------------------------
Using curl:

  curl -X POST http://localhost:8000/api/v1/upload \\
    -H "X-API-Key: your-api-key" \\
    -F "file=@/path/to/your/document.pdf"

How to Upload (Python)
-----------------------
Using requests library:

  import requests

  url = "http://localhost:8000/api/v1/upload"
  headers = {"X-API-Key": "your-api-key"}
  files = {"file": open("document.pdf", "rb")}

  response = requests.post(url, headers=headers, files=files)
  print(response.json())

Upload Response
---------------
After uploading, you'll receive a response like:

  {
    "success": true,
    "message": "File uploaded successfully",
    "document": {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "filename": "document.pdf",
      "size": 2457600,
      "status": "completed",
      "created_at": "2024-12-02T10:30:00Z"
    }
  }

Important: Save the "id" field - you'll need it to reference this document later.

Processing Status
-----------------
After upload, documents go through these stages:
1. Extraction: Text is extracted from the file
2. Chunking: Document is split into searchable chunks
3. Embedding: AI creates vector representations for search

Check processing status:

  curl -H "X-API-Key: your-api-key" \\
    http://localhost:8000/api/v1/documents/{document-id}/status

The document is ready for search when all stages show "completed".
Typical processing time: 15-60 seconds depending on document size.

================================================================================
4. SEARCHING DOCUMENTS
================================================================================

Two Types of Search
-------------------

1. Keyword Search (Metadata)
   - Searches document names, tags, metadata
   - Fast but literal matching
   - Good for finding specific documents by name

2. Semantic Search (Content)
   - Searches document content using AI
   - Finds documents by meaning, not just keywords
   - More accurate for complex queries

Keyword Search Example
----------------------
Find documents with "deployment" in the name:

  curl -H "X-API-Key: your-api-key" \\
    "http://localhost:8000/api/v1/documents/search?query=deployment"

Semantic Search Example
-----------------------
Find documents about a specific topic:

  curl -X POST http://localhost:8000/api/v1/search \\
    -H "X-API-Key: your-api-key" \\
    -H "Content-Type: application/json" \\
    -d '{
      "query": "How do I configure the RAG pipeline?",
      "top_k": 5,
      "min_score": 0.7
    }'

Search Parameters
-----------------
- query: Your search question or keywords (required)
- top_k: Number of results to return (default: 10, max: 50)
- min_score: Minimum similarity score (default: 0.7, range: 0.0-1.0)
- filters: Additional filters (tags, file type, date range)

Understanding Search Results
-----------------------------
Each result includes:
- document_id: Unique identifier
- document_name: File name
- similarity_score: How relevant (0.0 to 1.0, higher is better)
- chunk_text: Relevant excerpt from the document
- page_number: Where the information was found
- chunk_index: Position in document

Tip: Results with score > 0.8 are highly relevant
     Results with score 0.6-0.8 are moderately relevant
     Results with score < 0.6 may not be useful

================================================================================
5. CHAT INTERFACE
================================================================================

Ask Questions About Your Documents
-----------------------------------
The chat interface lets you ask questions in natural language and get
AI-generated answers based on your documents.

Basic Chat Request
------------------
  curl -X POST http://localhost:8000/api/v1/chat \\
    -H "X-API-Key: your-api-key" \\
    -H "Content-Type: application/json" \\
    -d '{
      "query": "What are the system requirements?",
      "stream": false
    }'

Chat Response
-------------
  {
    "answer": "The system requirements are: CPU: 4 cores, RAM: 8GB...",
    "confidence": 0.85,
    "sources": [
      {
        "document_id": "doc-id",
        "document_name": "deployment_guide.md",
        "relevance_score": 0.92,
        "excerpt": "Hardware (Minimum): CPU: 4 cores..."
      }
    ],
    "conversation_id": "conv-uuid"
  }

Understanding Confidence Scores
--------------------------------
- High (> 0.8): Strong evidence from multiple sources, trust the answer
- Medium (0.5-0.8): Moderate evidence, answer likely correct
- Low (< 0.5): Weak evidence, consider rephrasing your question

Conversation History
--------------------
To maintain context across multiple questions, use the conversation_id:

  First question:
    {"query": "What are the system requirements?"}
    Response includes: "conversation_id": "abc-123"

  Follow-up question:
    {"query": "What about storage requirements?", "conversation_id": "abc-123"}

The system remembers previous questions in the conversation.

Streaming Responses
-------------------
For real-time answers (words appear as they're generated):

  {"query": "...", "stream": true}

This uses Server-Sent Events (SSE) for progressive rendering.
First token appears in < 500ms, full answer in 2-5 seconds.

================================================================================
6. MANAGING DOCUMENTS
================================================================================

List All Documents
------------------
  curl -H "X-API-Key: your-api-key" \\
    "http://localhost:8000/api/v1/documents?page=1&page_size=20"

Filter and Sort
---------------
  # Filter by status
  ?status=completed

  # Filter by file type
  ?mime_type=application/pdf

  # Filter by tags
  ?tags=technical&tags=architecture

  # Sort by creation date (newest first)
  ?sort_by=created_at&sort_order=desc

  # Sort by file size
  ?sort_by=file_size&sort_order=asc

Get Document Details
--------------------
  curl -H "X-API-Key: your-api-key" \\
    http://localhost:8000/api/v1/documents/{document-id}

Delete a Document
-----------------
  curl -X DELETE -H "X-API-Key: your-api-key" \\
    http://localhost:8000/api/v1/documents/{document-id}

Note: This is a "soft delete" - the document is marked as deleted but not
physically removed. This allows for recovery if deleted by mistake.

Get Statistics
--------------
  curl -H "X-API-Key: your-api-key" \\
    "http://localhost:8000/api/v1/documents/stats?date_range=30d"

Shows:
- Total documents and storage used
- Breakdown by file type
- Upload trends over time
- Processing statistics

================================================================================
7. ADVANCED FEATURES
================================================================================

Content-Based Deduplication
----------------------------
QueryboxCore automatically detects duplicate uploads:
- Files are fingerprinted using SHA-256 checksums
- If you upload the same file twice, the second upload is rejected
- You get the ID of the existing document instead
- This saves storage space and processing time

To override (for testing):
  ?force_new=true

Batch Upload
------------
Upload multiple files at once (Python example):

  import requests
  from pathlib import Path

  url = "http://localhost:8000/api/v1/upload"
  headers = {"X-API-Key": "your-api-key"}

  files_to_upload = Path("documents/").glob("*.pdf")

  for file_path in files_to_upload:
      with open(file_path, "rb") as f:
          files = {"file": f}
          response = requests.post(url, headers=headers, files=files)
          print(f"Uploaded: {file_path.name}, ID: {response.json()['document']['id']}")

Custom Metadata
---------------
Add custom metadata during upload (future feature):

  {
    "file": file_binary,
    "metadata": {
      "department": "Engineering",
      "project": "RAG System",
      "confidential": false,
      "expiry_date": "2025-12-31"
    }
  }

Tags for Organization
---------------------
Assign tags to documents for easier filtering:

  {
    "file": file_binary,
    "tags": ["technical", "architecture", "deployment"]
  }

Then filter by tag:
  ?tags=technical

================================================================================
8. TROUBLESHOOTING
================================================================================

Problem: Upload fails with "413 Payload Too Large"
Solution: Your file exceeds 30MB. Try:
  - Compressing the PDF
  - Splitting into multiple documents
  - Removing embedded images if not needed

Problem: Upload fails with "400 File type not allowed"
Solution: Ensure your file has a supported extension:
  - .pdf, .docx, .txt, .md, .html
  - Check the actual file type (some .pdf files are actually images)

Problem: Document stuck in "processing" status
Solution:
  1. Wait at least 2 minutes (large PDFs take time)
  2. Check processing status for error messages
  3. If failed, try re-uploading with force_new=true

Problem: Search returns no results
Solution:
  1. Verify documents are fully processed (check status)
  2. Try simpler search queries
  3. Lower min_score threshold (try 0.5 instead of 0.7)
  4. Check that documents actually contain relevant content

Problem: "401 Unauthorized" error
Solution:
  - Verify your API key is correct
  - Check that X-API-Key header is included in request
  - Ensure API key hasn't expired (contact admin)

Problem: Slow search queries (> 5 seconds)
Solution:
  - This is normal for large document collections (> 10,000 docs)
  - Contact admin to rebuild vector indexes
  - Consider using keyword search for simple queries

================================================================================
9. FAQ
================================================================================

Q: How accurate is the semantic search?
A: 90-95% accuracy for well-written technical documents. Accuracy depends on:
   - Document quality (OCR documents are less accurate)
   - Query specificity (specific questions work better than vague ones)
   - Available context (more documents = better results)

Q: Can I upload scanned PDFs?
A: Yes! OCR (Optical Character Recognition) is automatic. However:
   - Processing takes 3-5x longer
   - Accuracy depends on scan quality
   - Handwritten text may not be recognized

Q: How long are documents stored?
A: Indefinitely unless you delete them. Contact admin for retention policies.

Q: Can I edit documents after upload?
A: No. To update a document:
   1. Delete the old version
   2. Upload the new version
   Future: Version control will be supported

Q: Is my data secure?
A: Yes. QueryboxCore implements:
   - API key authentication
   - Encrypted storage (in production)
   - Audit logging
   - Soft deletes for recovery

Q: How many documents can I upload?
A: No hard limit. Performance remains good up to 100,000 documents.
   Contact admin if you need more capacity.

Q: Can I use QueryboxCore offline?
A: Yes, if self-hosted. Cloud deployments require internet access.

================================================================================
10. SUPPORT
================================================================================

Getting Help
------------
- Documentation: https://docs.querybox.com
- GitHub Issues: https://github.com/your-org/querybox-core/issues
- Community Discord: https://discord.gg/querybox
- Email Support: support@querybox.com (commercial licenses)

Before Contacting Support
--------------------------
Please gather:
1. Your API request (curl command or code snippet)
2. Full error message
3. Document ID (if applicable)
4. Steps to reproduce the issue

Feature Requests
----------------
Submit feature requests on GitHub:
https://github.com/your-org/querybox-core/issues/new

Include:
- Use case description
- Expected behavior
- Why existing features don't solve your need

Contributing
------------
QueryboxCore is open source! Contributions welcome:
- Report bugs
- Improve documentation
- Submit pull requests
- Share use cases

See CONTRIBUTING.md for guidelines.

================================================================================

Thank you for using QueryboxCore!

For the latest updates, visit: https://github.com/your-org/querybox-core

================================================================================
"""


def generate_research_paper_txt() -> str:
    """Generate research paper content in plain text (20 pages worth of content)"""
    return """Dense Passage Retrieval for Open-Domain Question Answering

Abstract

We present Dense Passage Retrieval (DPR), a simple yet effective approach for
passage retrieval in open-domain question answering. Unlike traditional sparse
retrieval methods that rely on exact keyword matching (e.g., BM25), DPR uses
dense representations learned by neural networks to encode questions and passages
into a shared embedding space. This enables semantic matching that goes beyond
lexical overlap. Our experiments on Natural Questions, TriviaQA, WebQuestions,
and CuratedTREC benchmarks demonstrate that DPR significantly outperforms
traditional retrieval methods, achieving 78.4% accuracy on Natural Questions and
79.4% on TriviaQA when combined with a state-of-the-art reader model.

1. Introduction

Open-domain question answering (QA) is the task of answering factual questions
using a large collection of documents. The traditional pipeline consists of two
main components: (1) a retriever that selects a small subset of potentially
relevant passages from the collection, and (2) a reader that extracts the answer
from the retrieved passages.

For decades, retrieval has been dominated by sparse vector space models, most
notably TF-IDF and BM25, which represent queries and documents as high-dimensional
sparse vectors based on term frequencies and inverse document frequencies. While
these methods have proven effective for keyword-based search, they struggle with
semantic matching when the question and relevant passage use different vocabulary
(the vocabulary mismatch problem).

Recent advances in pre-trained language models such as BERT have enabled dense
representations that capture semantic similarity beyond surface-level lexical
overlap. However, applying dense encodings to retrieval at scale presents unique
challenges:

1. Computational efficiency: With millions of passages, we need sub-linear time
   retrieval methods rather than exhaustive comparison.

2. Training signal: Effective dense representations require large amounts of
   question-passage pairs with relevance labels.

3. Domain generalization: The retriever must work well across different question
   types and domains without task-specific tuning.

This paper addresses these challenges and makes the following contributions:

- We propose Dense Passage Retrieval (DPR), a dense encoder framework that uses
  dual encoders for questions and passages, trained with a simple contrastive
  learning objective.

- We demonstrate that in-batch negatives and hard negative mining are crucial
  for training effective dense retrievers.

- We show that DPR achieves state-of-the-art retrieval accuracy on multiple
  open-domain QA benchmarks, outperforming BM25 by 9-19 points in top-20 recall.

- We provide analysis on the types of questions where dense retrieval excels
  and where it still struggles compared to sparse methods.

2. Background and Related Work

2.1 Open-Domain Question Answering

Open-domain QA has a long history in NLP, dating back to systems like BASEBALL
(Green et al., 1961) and LUNAR (Woods, 1973). Modern approaches typically follow
a two-stage retrieve-then-read pipeline:

Retrieval Stage: Given a question, select a small set of potentially relevant
passages from a large corpus (e.g., Wikipedia with 21 million passages). The goal
is to achieve high recall while maintaining computational efficiency.

Reading Stage: Given the retrieved passages, extract or generate the answer. Early
approaches used rule-based extraction (Moldovan et al., 2003; Parikh et al., 2015),
while recent methods leverage neural reading comprehension models (Chen et al.,
2017; Wang et al., 2018; Yang et al., 2019).

2.2 Sparse Retrieval Methods

The dominant retrieval paradigm for decades has been sparse vector representations:

TF-IDF (Term Frequency-Inverse Document Frequency): Represents documents as
sparse vectors where each dimension corresponds to a term, weighted by its
frequency in the document and its inverse frequency across the corpus.

BM25 (Robertson & Zaragoza, 2009): An improved probabilistic variant of TF-IDF
that incorporates document length normalization and term saturation. BM25 remains
the de facto standard baseline for information retrieval.

These methods are:
- Computationally efficient: Inverted indexes enable sub-linear retrieval.
- Interpretable: The matching signal comes from explicit term overlap.
- Domain-robust: No training required, works out-of-the-box on new domains.

However, they suffer from the vocabulary mismatch problem. For example, the
question "Who invented the telephone?" and a passage containing "Alexander Graham
Bell developed the device for transmitting speech electrically" share no content
words despite being semantically related.

2.3 Dense Retrieval Methods

Dense retrieval represents queries and passages as low-dimensional dense vectors
(typically 128-768 dimensions) learned by neural networks. Similarity is measured
by vector dot product or cosine similarity in the embedding space.

Early work on neural retrieval focused on learning to rank (Huang et al., 2013;
Shen et al., 2014), but these methods were not competitive with BM25 for first-stage
retrieval. Recent advances in pre-trained language models have renewed interest:

- Lee et al. (2019) used BERT independently on questions and passages but found
  it underperformed BM25 without careful tuning.

- Guu et al. (2020) proposed REALM, which jointly trains the retriever and reader
  end-to-end using masked language modeling as the pre-training task.

- Chang et al. (2020) used a hard negative mining approach to improve dense
  retrieval for passage re-ranking.

Our work differs in that we focus on simple, effective training objectives for
dense retrieval that work well with relatively small amounts of supervision
(question-answer pairs) without requiring end-to-end training or additional
pre-training tasks.

3. Methodology

3.1 Problem Formulation

Given a factoid question q, our goal is to retrieve a small set of passages P =
{p1, p2, ..., pk} from a large corpus C such that at least one passage contains
the answer to q. We assume access to training examples of the form (qi, pi+, ai)
where pi+ is a passage containing the answer ai to question qi.

3.2 Dense Passage Retrieval (DPR)

We use a bi-encoder architecture with separate encoders for questions and passages:

Question Encoder: EQ(q) → dq ∈ ℝ^d
Passage Encoder: EP(p) → dp ∈ ℝ^d

where d is the embedding dimension (typically 768 for BERT-base). The similarity
score between a question q and passage p is computed as:

sim(q, p) = EQ(q)^T × EP(p)

At inference time, we encode all passages in the corpus offline and index them
using Maximum Inner Product Search (MIPS) libraries like FAISS (Johnson et al.,
2019). For a new question q, we encode it and retrieve the top-k passages with
highest similarity scores in sub-linear time.

3.3 Encoder Architecture

We instantiate both EQ and EP using BERT-base (Devlin et al., 2019):
- Input: Tokenized text with [CLS] token
- Output: [CLS] token representation from the final layer
- Parameters: ~110M parameters per encoder

While the encoders share the same architecture, they do not share parameters.
This allows the model to learn question-specific and passage-specific features
while maintaining the simplicity of dot-product similarity.

Alternative architectures we considered:
- Single encoder with [CLS] for both questions and passages: This tied-encoder
  approach reduces parameters but we found it slightly less effective.
- Cross-encoder (BERT on concatenated question + passage): More expressive but
  prohibitively slow for large-scale retrieval (requires encoding every
  question-passage pair at inference time).

3.4 Training Objective

We train the encoders using contrastive learning with in-batch negatives. For
each training example (q, p+, a), we treat p+ as the positive passage and all
other passages in the batch as negatives.

The loss function is negative log-likelihood:

L(q, p+, p1-, p2-, ..., pn-) = -log(exp(sim(q, p+)) / (exp(sim(q, p+)) + Σi exp(sim(q, pi-))))

where p1-, p2-, ..., pn- are negative passages.

This formulation is similar to the noise contrastive estimation (NCE) objective
and has several advantages:
1. Computationally efficient: No need to sample negatives; we use other positives
   in the batch.
2. Batch size acts as the number of negatives, providing strong training signal
   with large batches.
3. The gradient naturally pushes the model to separate positive from negative
   passages in embedding space.

3.5 Negative Sampling Strategies

The choice of negative passages significantly impacts retrieval quality. We compare
three strategies:

Random: Sample passages uniformly from the corpus.
- Pros: Easy to implement, provides diversity
- Cons: Too easy (most random passages are clearly irrelevant)

BM25: Use BM25 to retrieve top-1000 passages, sample negatives from those that
don't contain the answer.
- Pros: Hard negatives (lexically similar but semantically different)
- Cons: Biased toward improving on BM25's failure cases

In-batch negatives: Use positive passages for other questions in the batch.
- Pros: No additional sampling required, automatically hard (each positive is
  relevant to its own question)
- Cons: Less diverse than explicit negative sampling

Gold passages for other questions: For each question, use the gold passages of
other questions in the batch as hard negatives.
- Pros: Guaranteed to be real passages containing answers to different questions
- Cons: May be too hard if questions are unrelated

Our experiments (Section 5.2) show that in-batch negatives combined with one
BM25 hard negative per question provides the best balance of efficiency and
effectiveness.

3.6 Efficient MIPS for Large-Scale Retrieval

Encoding millions of passages and performing exact nearest neighbor search at
query time is computationally expensive. We address this using:

Offline Passage Encoding: We encode all 21 million Wikipedia passages once and
store the embeddings. This one-time cost takes ~8 hours on 8 V100 GPUs.

FAISS Indexing: We use the Facebook AI Similarity Search (FAISS) library to build
an IVFFlat index with 4096 clusters. At query time, we:
1. Encode the question (10ms on GPU)
2. Search the index for top-k passages (50ms for k=100, CPU-only)
3. Total retrieval time: <100ms per question

This provides 100x speedup over brute-force comparison while maintaining >99%
recall@100 compared to exact search.

For deployment at even larger scale (100M+ passages), we can use approximate
methods like product quantization (PQ) which trades a small amount of accuracy
for 4-8x reduction in memory and search time.

4. Experimental Setup

4.1 Datasets

We evaluate DPR on five open-domain QA datasets:

Natural Questions (NQ): 79k training questions sampled from real Google search
queries, with answers from Wikipedia passages. We use the open-domain version
where the model doesn't know which passage contains the answer.

TriviaQA: 79k training questions from trivia enthusiasts, with Wikipedia passages
as evidence. We use the unfiltered version which includes questions without
supporting evidence.

WebQuestions (WebQ): 3.8k training questions compiled from Google Suggest API,
with answers from Freebase but evidencepassages from Wikipedia.

CuratedTREC (TREC): 1.4k training questions from TREC QA tracks, manually curated
with high-quality answer annotations.

SQuAD v1.1: 87k training questions created by crowdworkers reading Wikipedia
passages. We use this dataset only for ablation studies, not as a primary
evaluation benchmark, since the questions are passage-dependent.

Statistics:
Dataset         Train    Dev     Test    Avg Q Length    Avg P Length
NQ              79k      9k      3.6k    9.1 tokens      157 tokens
TriviaQA        79k      9k      11.3k   14.2 tokens     246 tokens
WebQuestions    3.8k     361     2.0k    8.9 tokens      138 tokens
CuratedTREC     1.4k     133     694     10.3 tokens     172 tokens
SQuAD           87k      10k     10k     11.7 tokens     142 tokens

4.2 Evaluation Metrics

We evaluate retrieval using:

Top-k Retrieval Accuracy: Percentage of questions where at least one of the top-k
retrieved passages contains the answer (exact string match). We report k=20 and
k=100.

End-to-end QA Accuracy: Percentage of questions answered correctly by the full
retrieve-then-read pipeline (using a BERT-based extractive reader).

We also analyze:
- Retrieval latency (ms per question)
- Memory footprint (GB for passage index)
- Passage rank distribution (where do correct passages rank?)

4.3 Implementation Details

Question Encoder: BERT-base (110M parameters)
Passage Encoder: BERT-base (110M parameters, separate from question encoder)
Embedding dimension: 768
Maximum question length: 256 tokens
Maximum passage length: 256 tokens
Passages: 100-word splits from Wikipedia (21 million passages total)

Training:
- Batch size: 128 (16 per GPU × 8 GPUs)
- Learning rate: 2e-5 with linear warmup (1000 steps)
- Training steps: 40,000
- Optimizer: AdamW with 0.1 weight decay
- Hard negatives: 1 BM25 negative + in-batch negatives
- Training time: ~9 hours on 8 V100 GPUs

Retrieval:
- Index: FAISS IVFFlat with 4096 clusters
- Search probes: 64 clusters
- Top-k candidates: 100
- Total index size: ~65GB (21M passages × 768 dims × 4 bytes)
- Query latency: ~100ms (50ms FAISS search + 50ms overhead)

5. Results

5.1 Main Results

Table 1: Top-k retrieval accuracy (%) on development sets

Method           NQ       TriviaQA    WebQ     TREC
                @20 @100 @20   @100  @20 @100 @20 @100
BM25            59.1 73.7 66.9  76.7  55.0 71.1 70.9 84.1
DPR (Ours)      78.4 85.4 79.4  85.0  73.2 81.4 79.8 89.1
Improvement     +19.3+11.7+12.5 +8.3  +18.2+10.3 +8.9 +5.0

DPR significantly outperforms BM25 across all datasets:
- NQ: +19.3 points at top-20 (largest gain, questions use diverse vocabulary)
- TriviaQA: +12.5 points (trivia questions often require inference)
- WebQ: +18.2 points (short questions with implicit context)
- TREC: +8.9 points (more specific questions, lexical overlap helps)

The smaller gain on TREC suggests that dense retrieval benefits more from semantic
understanding than keyword matching, which aligns with our hypothesis that dense
models excel at handling vocabulary mismatch.

5.2 Ablation Studies

We analyze the impact of various design choices on Natural Questions dev set:

Effect of Training Data Size:
Training Examples    Top-20 Accuracy
1,000               61.2%
5,000               69.8%
10,000              73.5%
20,000              76.1%
40,000              77.9%
79,000 (full)       78.4%

Dense retrieval benefits significantly from more training data, with diminishing
returns after ~40k examples. Even with only 10k examples, DPR outperforms BM25
(59.1%), suggesting that dense representations can be learned from moderate
amounts of supervision.

Effect of Negative Sampling Strategy:
Strategy                        Top-20 Accuracy
Random negatives               68.7%
BM25 negatives only            74.2%
In-batch negatives only        76.8%
In-batch + 1 BM25 negative     78.4%
In-batch + 2 BM25 negatives    78.3%

In-batch negatives are highly effective, likely because they provide a good
balance of difficulty (each positive is relevant to a different question). Adding
one BM25 hard negative provides a small additional gain (+1.6 points), but adding
more hurts performance (possibly due to noise from BM25's false negatives).

Effect of Batch Size:
Batch Size    Top-20 Accuracy
16            72.1%
32            74.9%
64            76.7%
128           78.4%
256           78.2%

Larger batches improve performance up to 128, likely because they provide more
in-batch negatives. Beyond 128, we see diminishing returns or slight degradation,
possibly due to optimization difficulties with very large batches.

This section is continued with more detailed analysis on page 16..."""


# ============================================================================
# DEMO DATA SEEDER CLASS
# ============================================================================

class DemoDataSeeder:
    """Orchestrates demo data loading with progress tracking"""

    def __init__(self, db: Session, demo_data_path: Path, document_count: int = 5):
        """
        Initialize the seeder

        Args:
            db: Database session
            demo_data_path: Path to demo-data/ directory
            document_count: Number of documents to create (default: 5)
        """
        self.db = db
        self.demo_data_path = demo_data_path
        self.document_count = min(document_count, 5)  # Max 5 for our generators
        self.uploaded_ids: Dict[str, UUID] = {}
        self.logger = logger.bind(seeder="DemoDataSeeder")

    def seed(self) -> Dict[str, any]:
        """
        Main seeding workflow

        Returns:
            Dict with success_count, failure_count, and uploaded document IDs
        """
        self.logger.info("Starting demo data seeding", document_count=self.document_count)

        try:
            # Step 1: Create sample documents
            self.logger.info("Creating sample documents...")
            doc_paths = self._create_sample_documents()
            self.logger.info(f"Created {len(doc_paths)} documents", paths=[str(p) for p in doc_paths])

            # Step 2: Upload documents concurrently
            self.logger.info("Uploading documents...")
            document_ids = self._upload_documents_concurrent(doc_paths)
            self.logger.info(f"Uploaded {len(document_ids)} documents", ids=[str(id) for id in document_ids])

            # Step 3: Wait for processing
            self.logger.info("Waiting for processing to complete...")
            self._wait_for_processing(document_ids, timeout=120)
            self.logger.info("All documents processed successfully")

            # Step 4: Verify search
            self.logger.info("Verifying search functionality...")
            search_works = self._verify_search()

            results = {
                "success_count": len(document_ids),
                "failure_count": len(doc_paths) - len(document_ids),
                "document_ids": [str(id) for id in document_ids],
                "search_verified": search_works
            }

            self.logger.info("Demo data seeding completed", **results)
            return results

        except Exception as e:
            self.logger.error("Demo data seeding failed", error=str(e), exc_info=True)
            raise

    def _create_sample_documents(self) -> List[Path]:
        """
        Generate sample documents and save to demo-data/documents/

        Returns:
            List of paths to created files
        """
        docs_dir = self.demo_data_path / "documents"
        docs_dir.mkdir(parents=True, exist_ok=True)

        files = []

        # Document 1: Technical guide (save as .txt for simplicity)
        tech_path = docs_dir / "technical_guide.txt"
        tech_path.write_text(generate_technical_pdf_content())
        files.append(tech_path)
        self.logger.info("Created technical guide", path=str(tech_path), size_kb=tech_path.stat().st_size // 1024)

        # Document 2: Deployment guide (markdown)
        deploy_path = docs_dir / "deployment_guide.md"
        deploy_path.write_text(generate_deployment_guide_md())
        files.append(deploy_path)
        self.logger.info("Created deployment guide", path=str(deploy_path), size_kb=deploy_path.stat().st_size // 1024)

        # Document 3: API reference (HTML)
        api_path = docs_dir / "api_reference.html"
        api_path.write_text(generate_api_reference_html())
        files.append(api_path)
        self.logger.info("Created API reference", path=str(api_path), size_kb=api_path.stat().st_size // 1024)

        # Document 4: User manual (plain text)
        manual_path = docs_dir / "user_manual.txt"
        manual_path.write_text(generate_user_manual_txt())
        files.append(manual_path)
        self.logger.info("Created user manual", path=str(manual_path), size_kb=manual_path.stat().st_size // 1024)

        # Document 5: Research paper (plain text)
        research_path = docs_dir / "research_paper.txt"
        research_path.write_text(generate_research_paper_txt())
        files.append(research_path)
        self.logger.info("Created research paper", path=str(research_path), size_kb=research_path.stat().st_size // 1024)

        return files[:self.document_count]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=10))
    def _upload_document(self, doc_path: Path) -> UUID:
        """
        Upload a single document via HTTP API with retry logic

        Args:
            doc_path: Path to document file

        Returns:
            UUID of uploaded document

        Raises:
            Exception if upload fails after retries
        """
        import requests

        url = "http://localhost:8000/api/v1/upload/"

        with open(doc_path, 'rb') as f:
            files = {'file': (doc_path.name, f, 'application/octet-stream')}

            # For demo data, bypass deduplication
            params = {'force_new': 'true'}

            try:
                response = requests.post(url, files=files, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                doc_id = UUID(data['document']['id'])

                self.logger.info(
                    "Uploaded document",
                    filename=doc_path.name,
                    document_id=str(doc_id),
                    status=data['document'].get('status', 'unknown')
                )

                return doc_id

            except requests.exceptions.RequestException as e:
                self.logger.error(
                    "Upload failed",
                    filename=doc_path.name,
                    error=str(e),
                    exc_info=True
                )
                raise

    def _upload_documents_concurrent(self, doc_paths: List[Path]) -> List[UUID]:
        """
        Upload documents concurrently for speed

        Args:
            doc_paths: List of document paths to upload

        Returns:
            List of uploaded document IDs
        """
        document_ids = []

        for doc_path in doc_paths:
            try:
                doc_id = self._upload_document(doc_path)
                document_ids.append(doc_id)
                self.uploaded_ids[doc_path.name] = doc_id
            except Exception as e:
                self.logger.error(
                    "Failed to upload document after retries",
                    filename=doc_path.name,
                    error=str(e)
                )
                # Continue with other documents

        return document_ids

    def _wait_for_processing(self, document_ids: List[UUID], timeout: int = 120):
        """
        Poll processing_status until all documents are COMPLETED

        Args:
            document_ids: List of document IDs to monitor
            timeout: Maximum wait time in seconds

        Raises:
            TimeoutError if processing doesn't complete in time
        """
        start_time = time.time()
        check_interval = 2  # seconds

        while True:
            elapsed = time.time() - start_time

            if elapsed > timeout:
                raise TimeoutError(
                    f"Processing did not complete within {timeout}s. "
                    f"Check backend logs for errors."
                )

            # Check processing status for all documents
            all_complete = True
            statuses = {}

            for doc_id in document_ids:
                doc = self.db.query(Document).filter(Document.id == doc_id).first()

                if not doc:
                    self.logger.error("Document not found", document_id=str(doc_id))
                    all_complete = False  # Document not found means processing incomplete
                    continue

                # Query all processing status rows for this document
                processing_statuses = self.db.query(ProcessingStatus).filter(
                    ProcessingStatus.document_id == doc_id
                ).all()

                # Build status map for each stage
                stage_status_map = {}
                for ps in processing_statuses:
                    stage_status_map[ps.stage] = ps.status

                # Check if all required stages are completed
                extraction_done = stage_status_map.get(ProcessingStageEnum.EXTRACTION) == StageStatusEnum.COMPLETED
                chunking_done = stage_status_map.get(ProcessingStageEnum.CHUNKING) == StageStatusEnum.COMPLETED
                embedding_done = stage_status_map.get(ProcessingStageEnum.EMBEDDING) == StageStatusEnum.COMPLETED

                statuses[str(doc_id)] = {
                    "extraction": stage_status_map.get(ProcessingStageEnum.EXTRACTION, StageStatusEnum.NOT_STARTED).value,
                    "chunking": stage_status_map.get(ProcessingStageEnum.CHUNKING, StageStatusEnum.NOT_STARTED).value,
                    "embedding": stage_status_map.get(ProcessingStageEnum.EMBEDDING, StageStatusEnum.NOT_STARTED).value
                }

                if not (extraction_done and chunking_done and embedding_done):
                    all_complete = False

            self.logger.info(
                "Processing status check",
                elapsed_s=int(elapsed),
                timeout_s=timeout,
                statuses=statuses
            )

            if all_complete:
                self.logger.info("All documents processed successfully")
                return

            # Wait before next check
            time.sleep(check_interval)

    def _verify_search(self) -> bool:
        """
        Run sample queries to verify search works

        Returns:
            True if search returns results, False otherwise
        """
        import requests

        test_queries = [
            "How to configure RAG pipeline?",
            "What are the system requirements?",
            "How to deploy QueryboxCore?"
        ]

        url = "http://localhost:8000/api/v1/search"

        for query in test_queries:
            try:
                response = requests.post(
                    url,
                    json={"query": query, "top_k": 5, "min_score": 0.5},
                    timeout=10
                )
                response.raise_for_status()

                data = response.json()
                result_count = len(data.get('documents', []))

                self.logger.info(
                    "Search query succeeded",
                    query=query,
                    result_count=result_count
                )

                if result_count > 0:
                    return True

            except Exception as e:
                self.logger.error(
                    "Search query failed",
                    query=query,
                    error=str(e)
                )

        return False


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main entry point for demo data seeding"""
    parser = argparse.ArgumentParser(
        description="Seed QueryboxCore with demo documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Seed with default 5 documents
  python backend/scripts/seed_demo.py

  # Seed with only 3 documents
  python backend/scripts/seed_demo.py --count 3

  # Skip search verification
  python backend/scripts/seed_demo.py --skip-verify
        """
    )

    parser.add_argument(
        '--count',
        type=int,
        default=5,
        help='Number of documents to create (max: 5, default: 5)'
    )

    parser.add_argument(
        '--skip-verify',
        action='store_true',
        help='Skip search verification after seeding'
    )

    parser.add_argument(
        '--demo-data-path',
        type=Path,
        default=Path(__file__).parent.parent.parent / "demo-data",
        help='Path to demo-data directory (default: ../../demo-data)'
    )

    args = parser.parse_args()

    # Print banner
    print("\n" + "="*70)
    print("QueryboxCore Demo Data Seeder - Step 12.3")
    print("="*70 + "\n")

    # Initialize database session
    logger.info("Initializing database session...")
    db = SessionLocal()

    try:
        # Create seeder
        seeder = DemoDataSeeder(
            db=db,
            demo_data_path=args.demo_data_path,
            document_count=args.count
        )

        # Run seeding
        results = seeder.seed()

        # Report results
        print("\n" + "="*70)
        print("✅ Demo Data Seeding Completed Successfully!")
        print("="*70)
        print(f"Documents uploaded: {results['success_count']}")
        print(f"Documents failed: {results['failure_count']}")
        print(f"Search verified: {'✅' if results['search_verified'] else '❌'}")
        print("\nDocument IDs:")
        for doc_id in results['document_ids']:
            print(f"  - {doc_id}")
        print("\n" + "="*70 + "\n")

        # Exit with success code
        sys.exit(0)

    except Exception as e:
        print("\n" + "="*70)
        print("❌ Demo Data Seeding Failed!")
        print("="*70)
        print(f"Error: {str(e)}")
        print("\nCheck logs for details.")
        print("="*70 + "\n")

        # Exit with error code
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
