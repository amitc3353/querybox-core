# PROJECT.md - QueryboxCore Technical Specification

## Executive Summary

QueryboxCore is a production-ready, developer-friendly RAG (Retrieval-Augmented Generation) engine that processes documents and provides AI-powered search with accurate citations. Built on pipeshub-ai's battle-tested architecture, it's designed for developers who need reliable document intelligence without enterprise complexity.

## 🎯 Product Vision & Goals

### Primary Goal
Build the simplest, most reliable document processing and retrieval system that any developer can deploy in under 30 minutes while maintaining enterprise-grade performance.

### Success Criteria
- **Developer Experience**: 30-minute deployment from zero
- **Performance**: Sub-200ms search latency at 1M+ documents
- **Accuracy**: >95% citation precision
- **Scale**: 1000+ concurrent users on single instance
- **Cost**: <$0.01 per document processed

## 🏗️ System Architecture

### High-Level Components

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web App]
        API_CLIENT[API Client]
        SDK[SDK/Library]
    end
    
    subgraph "API Gateway"
        AUTH[Auth Middleware]
        RATE[Rate Limiter]
        VAL[Validation Layer]
    end
    
    subgraph "Core Services"
        UPLOAD[Upload Service]
        PROC[Processing Service]
        SEARCH[Search Service]
        CHAT[Chat Service]
    end
    
    subgraph "Processing Pipeline"
        EXTRACT[Content Extractor]
        CHUNK[Semantic Chunker]
        EMBED[Embedding Generator]
        INDEX[Vector Indexer]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL)]
        VECTOR[(pgvector)]
        REDIS[(Redis)]
        S3[(S3/MinIO)]
    end
    
    WEB --> API_GATEWAY
    API_CLIENT --> API_GATEWAY
    SDK --> API_GATEWAY
    
    API_GATEWAY --> AUTH
    AUTH --> RATE
    RATE --> VAL
    VAL --> CORE_SERVICES
    
    UPLOAD --> S3
    UPLOAD --> PG
    PROC --> EXTRACT
    EXTRACT --> CHUNK
    CHUNK --> EMBED
    EMBED --> INDEX
    INDEX --> VECTOR
    
    SEARCH --> VECTOR
    SEARCH --> REDIS
    CHAT --> SEARCH
    CHAT --> PG
```

## 📡 API Specification

### API Design Principles
1. **RESTful**: Standard HTTP methods and status codes
2. **Versioned**: /api/v1/ prefix for all endpoints
3. **Consistent**: Unified error format and response structure
4. **Documented**: OpenAPI/Swagger auto-generated

### Core API Contracts

#### 1. Upload API
```python
# POST /api/v1/upload
class UploadRequest(BaseModel):
    file: UploadFile
    workspace_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None
    process_immediately: bool = True

class UploadResponse(BaseModel):
    document_id: UUID
    status: Literal["queued", "processing", "completed", "failed"]
    upload_url: Optional[str]  # For large files
    estimated_time_seconds: int
    
# POST /api/v1/upload/bulk
class BulkUploadRequest(BaseModel):
    files: List[UploadFile]  # Max 100 files
    workspace_id: Optional[UUID] = None
    
class BulkUploadResponse(BaseModel):
    batch_id: UUID
    documents: List[UploadResponse]
    total: int
    queued: int
    failed: List[Dict[str, str]]
```

#### 2. Document Management API
```python
# GET /api/v1/documents/{document_id}
class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    original_name: str
    mime_type: str
    size_bytes: int
    extraction_status: DocumentStatus
    embedding_status: DocumentStatus
    chunks_count: int
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    processing_errors: Optional[List[str]]
    
# GET /api/v1/documents/{document_id}/status
class DocumentStatusResponse(BaseModel):
    extraction: StatusDetail
    embedding: StatusDetail
    current_stage: str
    progress_percentage: int
    estimated_completion: Optional[datetime]
    
class StatusDetail(BaseModel):
    status: Literal["not_started", "in_progress", "completed", "failed"]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int
```

#### 3. Search API
```python
# POST /api/v1/search
class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    filters: Optional[SearchFilters] = None
    include_citations: bool = True
    similarity_threshold: float = 0.7
    search_type: Literal["semantic", "keyword", "hybrid"] = "hybrid"
    
class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    citations: List[Citation]
    total_found: int
    search_time_ms: float
    confidence_score: float
    
class SearchResult(BaseModel):
    document_id: UUID
    chunk_id: UUID
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    highlights: List[TextSpan]
    
class Citation(BaseModel):
    document_id: UUID
    document_name: str
    page_number: Optional[int]
    paragraph_index: Optional[int]
    confidence: float
    text_snippet: str
```

#### 4. Chat API
```python
# POST /api/v1/chat
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID] = None
    context_documents: Optional[List[UUID]] = None
    model: str = "gpt-4"
    temperature: float = 0.7
    stream: bool = False
    
class ChatResponse(BaseModel):
    response: str
    conversation_id: UUID
    citations: List[Citation]
    sources: List[DocumentReference]
    tokens_used: int
    cost_usd: float
    confidence: float
    
# GET /api/v1/chat/{conversation_id}/history
class ConversationHistory(BaseModel):
    conversation_id: UUID
    messages: List[Message]
    total_tokens: int
    total_cost: float
```

### Error Handling

```python
class APIError(BaseModel):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: str
    timestamp: datetime
    
# Standard error responses
400: ValidationError
401: AuthenticationError
403: AuthorizationError
404: NotFoundError
409: ConflictError
429: RateLimitError
500: InternalServerError
503: ServiceUnavailableError
```

## 🗄️ Database Schema

### Core Tables

```sql
-- Workspaces (for multi-tenant future)
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100),
    file_size BIGINT,
    storage_path TEXT NOT NULL,
    storage_url TEXT,
    checksum VARCHAR(64),  -- SHA256
    version INTEGER DEFAULT 1,
    
    -- Status tracking
    extraction_status VARCHAR(50) DEFAULT 'not_started',
    extraction_started_at TIMESTAMP,
    extraction_completed_at TIMESTAMP,
    extraction_error TEXT,
    
    embedding_status VARCHAR(50) DEFAULT 'not_started',
    embedding_started_at TIMESTAMP,
    embedding_completed_at TIMESTAMP,
    embedding_error TEXT,
    
    -- Metadata
    page_count INTEGER,
    word_count INTEGER,
    language VARCHAR(10),
    author VARCHAR(255),
    title VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    deleted_at TIMESTAMP,  -- Soft delete
    
    -- Indexes
    INDEX idx_workspace_docs (workspace_id, created_at DESC),
    INDEX idx_status (extraction_status, embedding_status),
    INDEX idx_checksum (checksum),
    INDEX idx_deleted (deleted_at)
);

-- Document chunks
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    tokens INTEGER,
    
    -- Position tracking
    page_number INTEGER,
    paragraph_index INTEGER,
    char_start INTEGER,
    char_end INTEGER,
    
    -- Embeddings
    embedding vector(1536),  -- OpenAI dimension
    embedding_model VARCHAR(50),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    UNIQUE(document_id, chunk_index),
    INDEX idx_document_chunks (document_id, chunk_index)
);

-- Vector index for similarity search
CREATE INDEX chunks_embedding_idx ON chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Processing queue
CREATE TABLE processing_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL,  -- 'extraction', 'embedding', 'indexing'
    status VARCHAR(50) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Execution tracking
    worker_id VARCHAR(255),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    failed_at TIMESTAMP,
    
    -- Error tracking
    error_message TEXT,
    error_stack TEXT,
    
    -- Scheduling
    scheduled_for TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_queue_status (status, priority DESC, scheduled_for),
    INDEX idx_queue_document (document_id),
    INDEX idx_queue_worker (worker_id)
);

-- Search logs for analytics
CREATE TABLE search_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id),
    query TEXT NOT NULL,
    query_hash VARCHAR(64),  -- For caching
    query_embedding vector(1536),
    
    -- Results
    results_count INTEGER,
    top_score FLOAT,
    clicked_result UUID,
    
    -- Performance
    search_time_ms FLOAT,
    total_time_ms FLOAT,
    
    -- Feedback
    helpful BOOLEAN,
    feedback TEXT,
    
    -- Metadata
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_search_workspace (workspace_id, created_at DESC),
    INDEX idx_search_query_hash (query_hash)
);

-- Conversations for chat
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id),
    title VARCHAR(500),
    model VARCHAR(50),
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_conv_workspace (workspace_id, updated_at DESC)
);

-- Chat messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    
    -- Token tracking
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost DECIMAL(10, 6),
    
    -- Citations
    citations JSONB DEFAULT '[]',
    sources JSONB DEFAULT '[]',
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_msg_conversation (conversation_id, created_at)
);

-- Processing errors for debugging
CREATE TABLE processing_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id),
    task_type VARCHAR(50),
    error_type VARCHAR(100),
    error_message TEXT,
    error_stack TEXT,
    context JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_errors_document (document_id),
    INDEX idx_errors_unresolved (resolved, created_at DESC)
);
```

### Migration Strategy

```bash
# Alembic setup
alembic init migrations
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head

# Version control
/db/migrations/
  ├── versions/
  │   ├── 001_initial_schema.py
  │   ├── 002_add_vectors.py
  │   ├── 003_add_search_logs.py
  │   └── 004_add_conversations.py
  ├── alembic.ini
  └── env.py
```

## 🔄 Processing Pipeline

### Document Processing Flow

```python
class DocumentProcessor:
    """
    Main processing pipeline orchestrator
    Based on pipeshub-ai patterns
    """
    
    async def process_document(self, document_id: UUID):
        """
        Complete processing pipeline for a document
        """
        try:
            # Stage 1: Load document
            document = await self.load_document(document_id)
            await self.update_status(document_id, "extraction", "in_progress")
            
            # Stage 2: Extract content based on type
            extractor = self.get_extractor(document.mime_type)
            content = await extractor.extract(document.storage_path)
            
            # Stage 3: Clean and normalize
            cleaned_content = await self.clean_content(content)
            
            # Stage 4: Chunk semantically
            chunks = await self.chunk_content(
                cleaned_content,
                chunk_size=1000,
                overlap=200
            )
            
            # Stage 5: Store chunks
            await self.store_chunks(document_id, chunks)
            await self.update_status(document_id, "extraction", "completed")
            
            # Stage 6: Generate embeddings
            await self.update_status(document_id, "embedding", "in_progress")
            embeddings = await self.generate_embeddings(chunks)
            
            # Stage 7: Store embeddings
            await self.store_embeddings(document_id, embeddings)
            await self.update_status(document_id, "embedding", "completed")
            
            # Stage 8: Update search index
            await self.update_search_index(document_id)
            
            return ProcessingResult(
                document_id=document_id,
                chunks_count=len(chunks),
                success=True
            )
            
        except Exception as e:
            await self.handle_error(document_id, e)
            raise
```

### Content Extraction

```python
class ExtractorFactory:
    """
    Factory for document extractors
    """
    
    extractors = {
        'application/pdf': PDFExtractor,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DocxExtractor,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ExcelExtractor,
        'text/plain': TextExtractor,
        'text/markdown': MarkdownExtractor,
        'text/html': HTMLExtractor,
    }
    
    def get_extractor(self, mime_type: str) -> BaseExtractor:
        extractor_class = self.extractors.get(mime_type, GenericExtractor)
        return extractor_class()

class PDFExtractor(BaseExtractor):
    """
    PDF extraction with OCR support
    """
    
    async def extract(self, file_path: str) -> ExtractedContent:
        try:
            # Try text extraction first
            text = await self.extract_text_with_pdfplumber(file_path)
            
            if not text or len(text) < 100:
                # Fall back to OCR for scanned PDFs
                text = await self.extract_with_ocr(file_path)
                
            # Extract metadata
            metadata = await self.extract_metadata(file_path)
            
            return ExtractedContent(
                text=text,
                metadata=metadata,
                page_count=metadata.get('pages', 0)
            )
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise ExtractionError(f"Failed to extract PDF: {e}")
```

### Semantic Chunking

```python
class SemanticChunker:
    """
    Intelligent text chunking that preserves context
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n\n"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
        
    async def chunk_text(self, text: str) -> List[Chunk]:
        """
        Split text into semantic chunks
        """
        # Split by paragraphs first
        paragraphs = text.split(self.separator)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(self.tokenizer.encode(para))
            
            if current_size + para_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = self.separator.join(current_chunk)
                chunks.append(self.create_chunk(chunk_text, len(chunks)))
                
                # Start new chunk with overlap
                overlap_text = self.get_overlap(current_chunk)
                current_chunk = [overlap_text] if overlap_text else []
                current_size = len(self.tokenizer.encode(overlap_text)) if overlap_text else 0
                
            current_chunk.append(para)
            current_size += para_size
            
        # Add final chunk
        if current_chunk:
            chunk_text = self.separator.join(current_chunk)
            chunks.append(self.create_chunk(chunk_text, len(chunks)))
            
        return chunks
```

### Embedding Generation

```python
class EmbeddingService:
    """
    Optimized embedding generation with caching
    """
    
    def __init__(self):
        self.model = "text-embedding-ada-002"
        self.batch_size = 100
        self.cache = RedisCache()
        
    async def generate_embeddings(
        self,
        texts: List[str]
    ) -> List[np.ndarray]:
        """
        Generate embeddings with batching and caching
        """
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        # Check cache first
        for i, text in enumerate(texts):
            cache_key = self.get_cache_key(text)
            cached = await self.cache.get(cache_key)
            
            if cached:
                embeddings.append(np.array(cached))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
                embeddings.append(None)
                
        # Generate embeddings for uncached texts
        if uncached_texts:
            for batch_start in range(0, len(uncached_texts), self.batch_size):
                batch_end = min(batch_start + self.batch_size, len(uncached_texts))
                batch = uncached_texts[batch_start:batch_end]
                
                # Call OpenAI API
                response = await self.openai_client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                # Process responses
                for j, embedding_data in enumerate(response.data):
                    embedding = np.array(embedding_data.embedding)
                    original_index = uncached_indices[batch_start + j]
                    embeddings[original_index] = embedding
                    
                    # Cache for future use
                    cache_key = self.get_cache_key(batch[j])
                    await self.cache.set(
                        cache_key,
                        embedding.tolist(),
                        expire=3600
                    )
                    
        return embeddings
```

## 🔍 Search & Retrieval

### Multi-Stage Retrieval

```python
class SearchService:
    """
    Multi-stage search with reranking
    """
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> SearchResponse:
        """
        Perform semantic search with reranking
        """
        # Stage 1: Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query)
        
        # Stage 2: Vector similarity search
        vector_results = await self.vector_search(
            query_embedding,
            limit=top_k * 3,  # Over-fetch for reranking
            filters=filters
        )
        
        # Stage 3: Keyword search (BM25)
        keyword_results = await self.keyword_search(
            query,
            limit=top_k * 2,
            filters=filters
        )
        
        # Stage 4: Merge and deduplicate
        combined_results = self.merge_results(
            vector_results,
            keyword_results,
            weights={'vector': 0.7, 'keyword': 0.3}
        )
        
        # Stage 5: Rerank with cross-encoder
        reranked = await self.rerank_results(
            query,
            combined_results[:top_k * 2]
        )
        
        # Stage 6: Extract citations
        final_results = reranked[:top_k]
        citations = await self.extract_citations(query, final_results)
        
        return SearchResponse(
            query=query,
            results=final_results,
            citations=citations,
            total_found=len(combined_results),
            search_time_ms=self.timer.elapsed_ms(),
            confidence_score=self.calculate_confidence(final_results)
        )
```

## 🧪 Testing Strategy

### Test Coverage Requirements

```yaml
# Testing pyramid
Unit Tests: 80% coverage
  - Core functions
  - Utilities
  - Validators
  
Integration Tests: 70% coverage
  - API endpoints
  - Database operations
  - External services
  
E2E Tests: Critical paths
  - Upload → Process → Search
  - Chat conversation flow
  - Error recovery
  
Performance Tests:
  - Load testing: 1000 concurrent users
  - Stress testing: 10M documents
  - Benchmark suite
```

### Search Evaluation Framework

```python
# backend/scripts/eval_search.py
class SearchEvaluator:
    """
    Evaluate search quality metrics
    """
    
    def __init__(self, ground_truth_file: str):
        self.ground_truth = self.load_ground_truth(ground_truth_file)
        
    async def evaluate(self, queries: List[str]) -> EvaluationMetrics:
        results = {}
        
        for query in queries:
            # Get search results
            search_response = await self.search_service.search(query)
            
            # Get expected results
            expected = self.ground_truth.get(query, [])
            
            # Calculate metrics
            results[query] = {
                'precision_at_10': self.calculate_precision(
                    search_response.results[:10],
                    expected
                ),
                'recall_at_10': self.calculate_recall(
                    search_response.results[:10],
                    expected
                ),
                'mrr': self.calculate_mrr(
                    search_response.results,
                    expected
                ),
                'ndcg': self.calculate_ndcg(
                    search_response.results,
                    expected
                ),
                'latency_ms': search_response.search_time_ms
            }
            
        return self.aggregate_metrics(results)
```

## 🚀 Deployment Configuration

### Docker Compose Setup

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  postgres:
    image: ankane/pgvector:v0.5.1-pg15
    environment:
      POSTGRES_USER: querybox
      POSTGRES_PASSWORD: querybox123
      POSTGRES_DB: queryboxcore
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U querybox"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://querybox:querybox123@postgres:5432/queryboxcore
      REDIS_URL: redis://redis:6379
      S3_ENDPOINT_URL: http://minio:9000
      S3_ACCESS_KEY: minioadmin
      S3_SECRET_KEY: minioadmin
      S3_BUCKET: documents
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    volumes:
      - ./backend:/app
      - ./demo-data:/demo-data
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    environment:
      DATABASE_URL: postgresql://querybox:querybox123@postgres:5432/queryboxcore
      REDIS_URL: redis://redis:6379
      S3_ENDPOINT_URL: http://minio:9000
      S3_ACCESS_KEY: minioadmin
      S3_SECRET_KEY: minioadmin
    volumes:
      - ./backend:/app
    depends_on:
      - backend
    command: celery -A app.worker worker --loglevel=info

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

## 📊 Monitoring & Observability

### Metrics Collection

```python
# backend/app/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import structlog

logger = structlog.get_logger()

# Prometheus metrics
documents_processed = Counter(
    'documents_processed_total',
    'Total number of documents processed',
    ['status', 'file_type']
)

processing_duration = Histogram(
    'processing_duration_seconds',
    'Document processing duration',
    ['file_type', 'stage']
)

search_latency = Histogram(
    'search_latency_seconds',
    'Search request latency',
    ['search_type']
)

active_workers = Gauge(
    'active_workers',
    'Number of active processing workers'
)

# Structured logging
class StructuredLogger:
    def __init__(self):
        self.logger = structlog.get_logger()
        
    def log_upload(self, document_id: str, size: int, mime_type: str):
        self.logger.info(
            "document_uploaded",
            document_id=document_id,
            size_bytes=size,
            mime_type=mime_type,
            event_type="upload"
        )
        
    def log_processing_complete(
        self,
        document_id: str,
        duration_seconds: float,
        chunks_count: int
    ):
        self.logger.info(
            "processing_complete",
            document_id=document_id,
            duration_seconds=duration_seconds,
            chunks_count=chunks_count,
            event_type="processing"
        )
        
    def log_search(
        self,
        query: str,
        results_count: int,
        latency_ms: float
    ):
        self.logger.info(
            "search_performed",
            query_hash=hashlib.md5(query.encode()).hexdigest(),
            results_count=results_count,
            latency_ms=latency_ms,
            event_type="search"
        )
```

### Health Checks

```python
# backend/app/api/health.py
@router.get("/health")
async def health_check():
    """
    Comprehensive health check
    """
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Database check
    try:
        await db.execute("SELECT 1")
        checks["checks"]["database"] = "healthy"
    except Exception as e:
        checks["checks"]["database"] = f"unhealthy: {str(e)}"
        checks["status"] = "degraded"
        
    # Redis check
    try:
        await redis.ping()
        checks["checks"]["redis"] = "healthy"
    except Exception as e:
        checks["checks"]["redis"] = f"unhealthy: {str(e)}"
        checks["status"] = "degraded"
        
    # S3 check
    try:
        await s3.head_bucket(Bucket=settings.S3_BUCKET)
        checks["checks"]["storage"] = "healthy"
    except Exception as e:
        checks["checks"]["storage"] = f"unhealthy: {str(e)}"
        checks["status"] = "degraded"
        
    # Worker check
    active = celery_app.control.inspect().active()
    if active:
        checks["checks"]["workers"] = f"healthy: {len(active)} workers"
    else:
        checks["checks"]["workers"] = "unhealthy: no active workers"
        checks["status"] = "degraded"
        
    return checks
```

## 🔒 Security Implementation

### API Security

```python
# backend/app/middleware/security.py
class SecurityMiddleware:
    """
    Comprehensive security middleware
    """
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.api_key_validator = APIKeyValidator()
        
    async def __call__(self, request: Request, call_next):
        # API Key validation
        api_key = request.headers.get("X-API-Key")
        if not api_key or not await self.api_key_validator.validate(api_key):
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid API key"}
            )
            
        # Rate limiting
        client_id = self.get_client_id(request)
        if not await self.rate_limiter.check_rate_limit(client_id):
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded"}
            )
            
        # CORS headers
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        return response
```

## 📚 Demo Data & Quick Start

### Sample Dataset

```bash
/demo-data/
├── documents/
│   ├── technical_paper.pdf      # 15 pages, technical content
│   ├── financial_report.docx    # Tables and charts
│   ├── product_catalog.xlsx     # Product data
│   ├── user_guide.md            # Markdown documentation
│   ├── company_page.html        # Web content
│   └── meeting_notes.txt        # Plain text
├── queries.json                  # Sample search queries
├── expected_results.json         # Ground truth for evaluation
└── seed.py                       # Script to load demo data
```

### Quick Start Script

```python
# scripts/quickstart.py
#!/usr/bin/env python
"""
Quick start script for QueryboxCore
"""

import asyncio
import sys
from pathlib import Path

async def main():
    print("🚀 QueryboxCore Quick Start")
    print("-" * 40)
    
    # Check dependencies
    print("✓ Checking dependencies...")
    check_dependencies()
    
    # Start services
    print("✓ Starting services...")
    start_services()
    
    # Initialize database
    print("✓ Initializing database...")
    await initialize_database()
    
    # Create demo workspace
    print("✓ Creating demo workspace...")
    api_key = await create_demo_workspace()
    
    # Load demo data
    print("✓ Loading demo data...")
    await load_demo_data()
    
    print("-" * 40)
    print("✅ QueryboxCore is ready!")
    print(f"📡 API: http://localhost:8000/docs")
    print(f"🌐 Frontend: http://localhost:3000")
    print(f"🔑 API Key: {api_key}")
    print(f"📚 Demo data loaded: 6 documents")
    
if __name__ == "__main__":
    asyncio.run(main())
```

## 🎯 Success Metrics & KPIs

### Technical KPIs
- **Upload Success Rate**: >99.5%
- **Processing Time**: <30s for 100-page PDF
- **Search Latency p99**: <200ms
- **Citation Accuracy**: >95%
- **System Uptime**: >99.9%

### Business KPIs
- **Developer Adoption**: 100+ deployments in 3 months
- **Document Volume**: 1M+ documents processed
- **Query Volume**: 10K+ queries/day
- **Cost Efficiency**: <$0.01 per document

### Quality Metrics
- **Search Relevance (MRR)**: >0.7
- **User Satisfaction**: >4.5/5
- **Bug Rate**: <5 per 1000 documents
- **Documentation Coverage**: 100%

---
*Version: 1.0.0*
*Last Updated: [Current Date]*
*Status: Active Development*
*Target Release: MVP in 8 weeks*