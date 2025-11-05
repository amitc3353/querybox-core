# CLAUDE.md - QueryboxCore Project Context

## 💡 Project Differentiator
**QueryboxCore is the simplest, developer-friendly RAG engine that can be self-hosted or embedded in SaaS products.**
Built on pipeshub-ai's proven architecture, it delivers unmatched speed, citation transparency, and developer control.

## 🎯 Project Overview
**QueryboxCore** is a high-performance document processing and retrieval system that makes AI-powered document search accessible to every developer. Unlike complex enterprise solutions, QueryboxCore can be deployed in minutes while maintaining production-grade performance.

## 🚀 Current Phase: MVP Development
**Sprint**: Document Upload & Processing (Week 1-2)
**Focus**: Core Pipeline Implementation
**Status**: Active Development

## 📋 Core Pipeline Components (From Pipeshub-AI)

### 1. **Upload & Validation** 
- **185+ File Formats**: PDF, DOCX, XLSX, PPTX, TXT, MD, HTML, CSV, JSON, XML
- **Two-tier Validation**: Frontend (30MB limit) + Backend (MIME verification)
- **Smart Routing**: >10MB via presigned URLs, ≤10MB through server

### 2. **Storage Architecture**
- **Multi-vendor Support**: S3/Azure/Local
- **Organization**: `{workspace_id}/documents/{document_id}/current/`
- **Versioning**: Built-in version control with history

### 3. **Processing Pipeline**
- **Queue System**: Kafka/Celery for async processing
- **Status Tracking**: extraction_status + embedding_status
- **Error Recovery**: Retry with exponential backoff (3 attempts)

### 4. **Chunking Strategy**
- **Semantic Chunking**: 1000 tokens with 200 overlap
- **Boundary Detection**: Preserve sentences/paragraphs
- **Metadata Preservation**: Track chunk origins

### 5. **Embedding Generation**
- **Batch Processing**: Up to 100 chunks at once
- **Model Agnostic**: OpenAI/Claude/Local models
- **Caching**: Redis for frequent queries

### 6. **Retrieval System**
- **Vector Search**: pgvector with IVFFlat indexing
- **Multi-stage**: Search → Rerank → Citation extraction
- **Performance**: <200ms p99 latency

### 7. **Chat Interface**
- **Citation Accuracy**: >95% with source tracking
- **Context Management**: Conversation history
- **Real-time Updates**: WebSocket/polling fallback

## 🎯 MVP Scope (Based on Pipeshub)

### ✅ Phase 1: Core Features (Weeks 1-4)
- [x] Document upload (PDF, DOCX, XLSX, PPTX, TXT, MD, HTML)
- [ ] API contracts with Pydantic validation
- [ ] File validation (30MB limit, MIME checking)
- [ ] S3/MinIO storage with presigned URLs
- [ ] Async processing queue (Celery + Redis)
- [ ] Document extraction (PyPDF, python-docx, etc.)
- [ ] Status tracking system
- [ ] Error handling with structured logging
- [ ] Database migrations with Alembic
- [ ] Health check endpoints

### 🔄 Phase 2: Intelligence Layer (Weeks 5-6)
- [ ] Semantic chunking (1000 tokens/200 overlap)
- [ ] Embedding generation (OpenAI ada-002)
- [ ] Vector storage (pgvector)
- [ ] Basic retrieval (<200ms)
- [ ] Search evaluation metrics

### 🎨 Phase 3: User Interface (Weeks 7-8)
- [ ] Upload interface with drag-drop
- [ ] Search bar with results display
- [ ] Chat interface with streaming
- [ ] Citation links and highlighting
- [ ] Processing status indicators

### ❌ Post-MVP
- Google Drive/Slack integration
- Advanced authentication (OAuth, SSO)
- Multi-tenant workspaces
- Analytics dashboard
- Audio/Video processing

## 🏗️ Technology Stack (Proven by Pipeshub)

**Backend:**
- FastAPI (async, 1000+ concurrent users)
- PostgreSQL + pgvector (million+ documents)
- Redis (caching, queue management)
- Celery (distributed task processing)
- MinIO/S3 (scalable file storage)

**Frontend:**
- Next.js 14 (server components)
- TypeScript (type safety)
- Tailwind CSS (rapid styling)
- React Query (data fetching)
- WebSockets (real-time updates)

**Processing Libraries:**
- pdfplumber (PDF extraction)
- pytesseract (OCR for scanned docs)
- python-docx (Word documents)
- openpyxl (Excel files)
- beautifulsoup4 (HTML parsing)

## 📊 Performance Targets (From Pipeshub)

| Metric | Target | Pipeshub Achieved |
|--------|--------|-------------------|
| File Upload (<10MB) | <2s | ✅ 1.8s |
| File Upload (>10MB) | Presigned URL | ✅ Direct |
| PDF Processing (100 pages) | <30s | ✅ 25s |
| Chunk Generation | 100 chunks/5s | ✅ 4.2s |
| Embedding Generation | 100 embeddings/5s | ✅ 4.5s |
| Search Latency (p99) | <200ms | ✅ 180ms |
| Citation Accuracy | >95% | ✅ 96.5% |
| Concurrent Users | 1000+ | ✅ 1200 |
| Document Capacity | 1M+ pages | ✅ 2M+ |

## 🚨 Critical Implementation Patterns

### File Validation (Pipeshub Pattern)
```python
# Two-tier validation
Frontend: Size + Extension checking
Backend: MIME type + Content verification
```

### Storage Strategy (Pipeshub Pattern)
```python
# Smart routing based on file size
if file_size > 10MB:
    return presigned_url_upload()
else:
    return direct_server_upload()
```

### Error Handling (Pipeshub Pattern)
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=4, max=15)
)
async def process_with_retry():
    # Exponential backoff: 4s, 8s, 15s
```

### Status Tracking (Pipeshub Pattern)
```python
class DocumentStatus:
    extraction_status: Enum[
        NOT_STARTED,
        IN_PROGRESS,
        COMPLETED,
        FAILED
    ]
    embedding_status: Enum[
        NOT_STARTED,
        IN_PROGRESS,
        COMPLETED,
        FAILED
    ]
```

## 🔒 Security & Monitoring

### API Security (MVP)
```python
# API key validation middleware
API_KEY_HEADER = "X-API-Key"
CORS_ORIGINS = ["http://localhost:3000"]
RATE_LIMIT = "100/minute"
```

### Observability Stack
```python
# Structured logging
import structlog
logger = structlog.get_logger()

# Health checks
GET /health → DB, Redis, S3 status
GET /metrics → processed_docs, avg_latency

# Error tracking
Sentry DSN or self-hosted alternative
Failed tasks → processing_errors table
```

### Monitoring Metrics
- Documents processed/hour
- Average processing time
- Search latency p50/p95/p99
- Embedding generation cost
- Storage usage trends

## 🧪 Testing & Validation

### Search Evaluation
```bash
# backend/scripts/eval_search.py
python eval_search.py \
  --queries sample_queries.json \
  --ground_truth expected_results.json \
  --output metrics.json

# Metrics tracked:
- Recall@10: >80%
- Precision@10: >70%
- MRR (Mean Reciprocal Rank): >0.7
- Latency: <200ms p99
```

### Demo Dataset
```bash
# Sample documents included
/demo-data/
  ├── sample.pdf (10 pages, technical)
  ├── report.docx (financial data)
  ├── data.xlsx (tabular data)
  ├── guide.md (markdown docs)
  └── webpage.html (scraped content)

# Auto-ingest for testing
make seed-demo
```

## 🛠️ Local Development Setup

### Quick Start
```bash
# Clone and setup
git clone https://github.com/[your-org]/querybox-core
cd querybox-core
cp .env.example .env.local

# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Initialize database
python scripts/init_local.py

# Seed demo data
python scripts/seed_demo.py

# Access
Frontend: http://localhost:3000
API: http://localhost:8000/docs
MinIO: http://localhost:9001
```

### Environment Configuration
```env
# .env.local template
DATABASE_URL=postgresql://user:pass@localhost:5432/querybox
REDIS_URL=redis://localhost:6379
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
OPENAI_API_KEY=sk-...
API_KEY=dev-key-12345
SENTRY_DSN=optional
```

## 📡 API Design Specifications

### RESTful Endpoints (v1)
```yaml
# Upload endpoints
POST   /api/v1/upload
POST   /api/v1/upload/bulk
GET    /api/v1/upload/presigned
POST   /api/v1/upload/complete/{upload_id}

# Document management
GET    /api/v1/documents
GET    /api/v1/documents/{id}
GET    /api/v1/documents/{id}/status
DELETE /api/v1/documents/{id}

# Search & retrieval
POST   /api/v1/search
POST   /api/v1/chat
GET    /api/v1/chat/{conversation_id}/history

# System
GET    /health
GET    /metrics
GET    /api/v1/info
```

### Pydantic Models
```python
# Request/Response contracts
class DocumentUpload(BaseModel):
    filename: str
    mime_type: str
    size: int
    metadata: Optional[Dict]

class SearchQuery(BaseModel):
    query: str
    top_k: int = 10
    filters: Optional[Dict]
    include_citations: bool = True

class SearchResult(BaseModel):
    documents: List[DocumentMatch]
    citations: List[Citation]
    confidence: float
    processing_time_ms: float
```

## 🗄️ Database Management

### Schema Migrations
```bash
# Using Alembic
alembic init migrations
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head

# Schema versioning
/db/
  ├── schema.sql (current)
  ├── migrations/
  │   ├── v001_initial.sql
  │   ├── v002_add_embeddings.sql
  │   └── v003_add_indexes.sql
  └── seeds/
      └── demo_data.sql
```

### Critical Indexes
```sql
-- Performance indexes
CREATE INDEX idx_documents_status ON documents(extraction_status, embedding_status);
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (vector vector_cosine_ops);
CREATE INDEX idx_documents_created ON documents(created_at DESC);
CREATE INDEX idx_search_queries ON search_logs(query_hash, created_at);
```

## ⏰ Realistic Timeline for Solopreneur

### MVP Complete: 8-10 Weeks

#### **Weeks 1-2: Foundation & Upload**
- **Hours/week**: 30-40 hours
- Set up infrastructure (Docker, PostgreSQL, Redis)
- Implement file upload with validation
- Storage service with S3/MinIO
- Basic API structure
- **Learning curve**: FastAPI, async Python, S3 APIs

#### **Weeks 3-4: Processing Pipeline**
- **Hours/week**: 35-40 hours
- Document extraction for all formats
- Queue system with Celery
- Status tracking implementation
- Error handling and retries
- **Learning curve**: Celery, document parsing libraries

#### **Weeks 5-6: Intelligence Layer**
- **Hours/week**: 40-45 hours
- Semantic chunking algorithm
- Embedding generation with OpenAI
- Vector storage with pgvector
- Retrieval system with reranking
- **Learning curve**: Vector databases, embeddings, LangChain

#### **Weeks 7-8: Frontend & Integration**
- **Hours/week**: 35-40 hours
- Upload interface with drag-drop
- Search and results display
- Chat interface with citations
- Real-time status updates
- **Learning curve**: Next.js 14, WebSockets, React Query

#### **Weeks 9-10: Testing & Polish**
- **Hours/week**: 25-30 hours
- End-to-end testing
- Performance optimization
- Bug fixes and edge cases
- Documentation
- Deployment setup

### 📚 Daily Schedule Recommendation

**Optimal Schedule (6 days/week):**
- **Morning (3-4 hours)**: Core development
- **Afternoon (2-3 hours)**: Testing & debugging
- **Evening (1-2 hours)**: Learning & research

**Weekly Breakdown:**
- **Mon-Thu**: Feature development (8 hrs/day)
- **Fri**: Testing & refactoring (6 hrs)
- **Sat**: Learning & planning (4 hrs)
- **Sun**: Rest or light documentation

### 🎯 Efficiency Tips

1. **Use Pipeshub Patterns**: Don't reinvent - adapt their proven solutions
2. **AI Assistance**: Use Claude/GPT for boilerplate and debugging
3. **Component Libraries**: Use shadcn/ui, don't build UI from scratch
4. **Docker Compose**: Set up once, develop faster
5. **Focus on Core**: Skip nice-to-haves until post-MVP

### ⚡ Accelerated Path (6 Weeks)

If working full-time (50-60 hours/week):
- **Week 1**: Infrastructure + Upload
- **Week 2**: Processing + Storage
- **Week 3**: Chunking + Embeddings
- **Week 4**: Retrieval + Search
- **Week 5**: Frontend + Chat
- **Week 6**: Testing + Deployment

### 🚩 Red Flags to Avoid

1. **Over-engineering**: Stick to pipeshub patterns
2. **Feature creep**: MVP only needs core features
3. **Perfect chunking**: 80% accuracy is good enough for MVP
4. **Custom UI**: Use component libraries
5. **Premature optimization**: Get it working first

## 📝 Development Workflow

### Three-Step Pattern for Each Feature
```bash
# Step 1: Analyze pipeshub implementation
claude "Analyze pipeshub-ai's [FEATURE] implementation..."

# Step 2: Generate context command
claude "Create QueryboxCore context command for [FEATURE]..."

# Step 3: Implement in QueryboxCore
claude --project querybox-core "[Generated context command]..."
```

## 📚 Learning Resources Priority

### Week 1-2 Focus:
- FastAPI documentation (async basics)
- S3/MinIO presigned URLs
- Python async/await patterns
- Docker Compose basics

### Week 3-4 Focus:
- Celery task queues
- PDF/Document parsing libraries
- PostgreSQL + SQLAlchemy

### Week 5-6 Focus:
- Vector databases (pgvector)
- Embeddings concepts
- LangChain basics
- Semantic search

### Week 7-8 Focus:
- Next.js 14 App Router
- React Server Components
- WebSocket basics
- Tailwind CSS

## 🔗 Important Links
- Pipeshub-AI: https://github.com/pipeshub-ai/pipeshub-ai
- QueryboxCore: [Your GitHub URL]
- FastAPI Docs: https://fastapi.tiangolo.com
- pgvector: https://github.com/pgvector/pgvector
- LangChain: https://docs.langchain.com
- Docker Compose: https://docs.docker.com/compose/

---
*Last Updated: [Current Date]*
*Phase: MVP Development - Week 1*
*Target Completion: 8-10 weeks*
*Daily Commitment: 6-8 hours*