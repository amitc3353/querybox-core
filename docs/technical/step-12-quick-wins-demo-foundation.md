# Step 12: Quick Wins & Demo Foundation - Technical Documentation

**Version**: 1.0
**Date**: December 2024
**Status**: Implementation Ready
**Deliverable**: One-command deployment (`docker-compose up`) with demo data

---

## Table of Contents
1. [Goal & Architecture](#1-goal--architecture)
2. [Implementation](#2-implementation)
3. [Security & Validation](#3-security--validation)
4. [Performance Decisions](#4-performance-decisions)
5. [Error Handling](#5-error-handling)
6. [Configuration](#6-configuration)
7. [Integration Details](#7-integration-details)
8. [Testing Approach](#8-testing-approach)
9. [Monitoring](#9-monitoring)
10. [Code Snippets](#10-code-snippets)
11. [Important Decisions](#11-important-decisions)

---

## 1. GOAL & ARCHITECTURE

### Objective
Step 12 removes all deployment friction by creating a reproducible, automated development and production environment. The specific goal is to enable any developer to run `docker-compose up` and have a fully functional QueryboxCore system with demo data pre-loaded within 5 minutes. This addresses the current manual setup barriers: unmanaged database migrations, missing application containerization, and absence of demo data for testing.

### System Design Patterns

**Repository Pattern (Database Migrations)**
Alembic implements the Repository pattern for database version control, treating migrations as discrete changesets with bidirectional operations (upgrade/downgrade). The migration repository (`backend/alembic/versions/`) maintains chronological schema evolution, enabling rollback to any historical state. This pattern separates schema management from application code while maintaining SQLAlchemy ORM compatibility through automatic model inspection.

**Factory Pattern (Demo Data Generation)**
The demo data seeder (`seed_demo.py`) uses the Factory pattern to create realistic document fixtures with varied characteristics: technical PDFs with code snippets, markdown documentation with structured headings, HTML content with mixed formatting. Each factory method produces documents with deterministic properties (file size, content complexity, metadata richness) ensuring consistent test scenarios across environments.

**Observer Pattern (Health Monitoring)**
Health check infrastructure implements Observer pattern where container health checks continuously monitor service readiness. The FastAPI `/health` endpoint aggregates status from multiple observers (database connection, Redis ping, storage accessibility, Ollama availability) and publishes composite health state. Docker Compose orchestration subscribes to these health signals to manage service dependencies and restart policies.

**Layered Architecture**
The system maintains three distinct layers:
1. **Infrastructure Layer**: Docker containers, network configuration, volume management
2. **Persistence Layer**: PostgreSQL with pgvector, Redis cache, MinIO storage, managed through Alembic migrations
3. **Application Layer**: FastAPI backend with processing pipeline, accessing persistence through service interfaces

### Component Boundaries

**Database Migration Boundary**
Alembic operates independently of the running application, executing SQL transformations directly against PostgreSQL. The boundary interface is the SQLAlchemy `MetaData` object generated from model inspection. Migrations must be idempotent and transactional, never assuming application-level validation or business logic.

**Containerization Boundary**
The backend Dockerfile creates a hermetic environment containing only Python 3.11 runtime, application code, and production dependencies. Development tools, test fixtures, and documentation remain outside container boundary. Multi-stage builds enforce strict separation: build stage compiles dependencies, runtime stage contains only execution artifacts.

**Demo Data Boundary**
Seed script operates through public API contracts (DocumentService, EmbeddingService) rather than direct database access. This ensures demo data creation exercises the same validation, processing, and storage paths as production data. The boundary prevents test data contamination by using designated document IDs and metadata tags (`demo: true`).

### Data Flow Architecture

**Migration Flow**
```
schema.sql → Model Inspection → Alembic Revision → SQL Migration Script → PostgreSQL Execution → Version Table Update
```

**Deployment Flow**
```
docker-compose up → Pull Images → Network Creation → Volume Mounting → Health Check Loop → Service Readiness → Application Startup
```

**Demo Data Flow**
```
Sample Documents → Upload API → Validation → Storage (Local/MinIO) → Processing Queue → Text Extraction → Semantic Chunking → BGE-M3 Embedding → pgvector Storage → Search Index
```

The architecture prioritizes reproducibility (immutable containers), observability (comprehensive health checks), and developer experience (single-command setup).

---

## 2. IMPLEMENTATION

### Files to Create

**Database Migration Infrastructure**

1. **`backend/alembic.ini`** (Configuration)
   - Alembic configuration with database URL template
   - Logging setup for migration output
   - Script location (`backend/alembic/`)
   - Version table name (`alembic_version`)

2. **`backend/alembic/env.py`** (Migration Runtime)
   - SQLAlchemy engine configuration from environment variables
   - Model metadata import from `app.models`
   - Online (connected) vs offline (SQL generation) mode
   - Transaction management with rollback on failure
   - Purpose: Bridges Alembic framework to QueryboxCore models

3. **`backend/alembic/versions/001_initial_schema.py`** (Initial Migration)
   - Generated via `alembic revision --autogenerate`
   - Creates all tables: documents, embeddings, processing_status, document_versions
   - Installs pgvector extension if not present
   - Creates indexes: IVFFlat for vectors, GIN for JSONB, B-tree for timestamps
   - Sets up triggers for updated_at timestamps
   - Purpose: Establishes baseline schema matching current SQLAlchemy models

4. **`backend/scripts/init_db.py`** (Database Initialization Utility)
   - Validates database connectivity
   - Runs Alembic migrations programmatically
   - Creates initial admin user if specified
   - Verifies schema integrity post-migration
   - Purpose: Automated initialization for CI/CD pipelines

5. **`backend/scripts/migrate.py`** (Migration Wrapper)
   - CLI wrapper around Alembic commands
   - Supports: upgrade, downgrade, history, current
   - Adds safety checks: backup prompts, dry-run mode
   - Purpose: Developer-friendly migration interface

**Deployment Infrastructure**

6. **`backend/Dockerfile`** (Application Container)
   ```
   Stage 1 (builder):
     - Python 3.11-slim base
     - Install build dependencies (gcc, poetry)
     - Copy requirements.txt, install packages
     - Download BGE-M3 model (~2GB cache)

   Stage 2 (runtime):
     - Python 3.11-slim base
     - Copy only installed packages from builder
     - Copy application code
     - Non-root user (app:app, UID 1000)
     - Health check: curl localhost:8000/health
     - CMD: uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   Purpose: Creates 400MB production image (vs 1.2GB single-stage)

7. **`docker-compose.prod.yml`** (Production Orchestration)
   - Services: backend, postgres, redis, minio, ollama
   - Backend service:
     - Depends on: postgres, redis, minio
     - Health check with 30s interval
     - Restart policy: unless-stopped
     - Environment from .env.prod
   - Volumes: Named volumes for persistence
   - Networks: Internal network for service communication
   - Purpose: Production-ready multi-container deployment

8. **`scripts/deploy.sh`** (Deployment Automation)
   - Pull latest code from Git
   - Build Docker images with cache
   - Run database migrations
   - Perform rolling restart (zero-downtime)
   - Verify health checks pass
   - Rollback on failure
   - Purpose: One-command production deployment

9. **`scripts/health_check.sh`** (Health Monitoring)
   - Polls `/health` endpoint every 5 seconds
   - Checks all dependencies: DB, Redis, Storage, Ollama
   - Exits with error code if unhealthy after 60s
   - Purpose: CI/CD health validation, load balancer integration

10. **`.dockerignore`** (Build Optimization)
    - Excludes: `__pycache__`, `.pytest_cache`, `*.pyc`, `.git`
    - Excludes: `tests/`, `docs/`, `demo-data/`
    - Purpose: Reduces Docker context size by 70%

**Demo Data Pipeline**

11. **`backend/scripts/seed_demo.py`** (Demo Data Seeder)
    - Core Classes:
      - `DemoDocumentFactory`: Creates sample documents with metadata
      - `DemoDataSeeder`: Orchestrates upload and processing
      - `ProgressTracker`: Real-time progress display
    - Functions:
      - `create_sample_documents()`: Generates 5 document types
      - `upload_documents()`: Uploads via DocumentService API
      - `wait_for_processing()`: Polls until embeddings complete
      - `verify_search()`: Tests semantic search functionality
    - Purpose: Populates system with realistic demo data

12. **`demo-data/README.md`** (Demo Data Documentation)
    - Describes sample document types and purpose
    - Lists sample queries with expected results
    - Explains how to regenerate demo data
    - Purpose: Developer onboarding documentation

13. **`demo-data/sample_queries.json`** (Test Queries)
    ```json
    [
      {"query": "How to configure RAG pipeline?", "expected_doc": "technical_guide.pdf"},
      {"query": "What are the system requirements?", "expected_doc": "deployment_guide.md"},
      ...
    ]
    ```
    Purpose: Automated testing of search quality

14. **`demo-data/documents/`** (Sample Documents Directory)
    - `technical_guide.pdf` (15 pages): RAG architecture explanation
    - `deployment_guide.md` (5 pages): Step-by-step deployment
    - `api_reference.html` (10 pages): OpenAPI documentation export
    - `research_paper.pdf` (20 pages): Academic paper on embeddings
    - `user_manual.txt` (8 pages): Plain text usage instructions
    - Purpose: Diverse document types for testing all processing pipelines

### Database Schema Changes

**Critical Fix: Vector Dimension Mismatch**

Current state:
- `backend/db/schema.sql`: `vector(1024)` for BGE-M3
- `docker/postgres-init/01-schema.sql`: `vector(1536)` for OpenAI

Migration will:
1. Drop existing embeddings table if dimension mismatch
2. Recreate with `vector(1024)` matching BGE-M3
3. Rebuild IVFFlat index with correct dimension
4. Update any test data to correct dimension

**New Tables** (if not in schema.sql):
- `alembic_version`: Tracks current migration version
- `migration_history`: Audit log of all migration executions

### Core Algorithms

**Migration Generation** (O(n) where n = number of models)
```python
def generate_migration(models: List[Type[Base]]) -> str:
    """
    Complexity: O(n) model introspection + O(m) existing schema parsing
    where n = models count, m = database tables count

    Uses SQLAlchemy's model metadata to generate CREATE/ALTER statements
    by comparing model state to current database schema.
    """
```

**Demo Data Processing** (O(n*m) where n = documents, m = avg chunks/doc)
```python
async def process_demo_documents(docs: List[Path]) -> Dict[str, UUID]:
    """
    Complexity: O(n*m*k) where
    n = number of documents (5)
    m = average chunks per document (50-100)
    k = embedding dimension (1024)

    Parallelizes document processing using asyncio.gather()
    Bottleneck: Embedding generation (5s per 100 chunks with BGE-M3)
    Total time: ~30-60 seconds for 5 documents
    """
```

---

## 3. SECURITY & VALIDATION

### Input Sanitization

**Migration Safety**
- All migrations run within database transactions, rolling back on any error
- SQL injection prevention: Alembic uses parameterized queries exclusively
- Migration scripts undergo code review before execution; never auto-apply in production
- Dry-run mode (`alembic upgrade --sql head`) generates SQL for manual inspection
- Version locking: Production requires explicit version specification, no `head` upgrades

**Docker Image Security**
- Base image: Python 3.11-slim with weekly security patches applied
- Non-root user enforcement: Application runs as UID 1000 with minimal privileges
- Read-only root filesystem except explicit writable volumes (`/tmp`, `/storage`)
- No shell access: ENTRYPOINT uses exec form to prevent shell injection
- Secret management: Environment variables loaded from external sources, never baked into image
- Dependency pinning: `requirements.txt` with exact versions and SHA256 checksums

**Demo Data Sanitization**
- All demo documents contain synthetic data only, no real PII or sensitive information
- Document content reviewed for: personally identifiable information, credentials, internal URLs
- Metadata scrubbed: author names replaced with "Demo User", timestamps normalized
- File validation: MIME type checking, size limits (max 10MB per document), malware scanning hooks
- Database isolation: Demo data uses separate workspace/namespace, easily deletable

### Authentication & Authorization

**Migration Execution**
- Database credentials stored in environment variables only, never in code
- Minimum privilege principle: Migration user has DDL permissions only (CREATE, ALTER, DROP tables)
- No DML permissions on migration user, preventing data modification
- Audit logging: All migration executions logged with timestamp, user, and result

**Health Check Endpoints**
- Public health checks (`/health`) provide minimal info: UP/DOWN status only
- Detailed metrics (`/health/detailed`) require API key authentication
- Rate limiting: 10 requests/minute per IP to prevent abuse
- No sensitive data in health responses: Database credentials, internal IPs excluded

**Container Access**
- No SSH access to containers; use `docker exec` for debugging (requires host access)
- Secrets mounted as read-only volumes, not environment variables
- Inter-service communication uses internal Docker network, not exposed externally
- MinIO access keys rotated monthly, stored in vault

### Data Protection

**At Rest**
- PostgreSQL data volume encrypted with LUKS in production
- MinIO storage uses server-side encryption (SSE-S3)
- Redis persistence files encrypted at volume level
- Backup encryption: Weekly backups encrypted with GPG before S3 upload

**In Transit**
- Internal: Services communicate over Docker internal network (encrypted in swarm mode)
- External: Nginx reverse proxy terminates TLS 1.3, redirects HTTP → HTTPS
- Certificate management: Let's Encrypt with auto-renewal

---

## 4. PERFORMANCE DECISIONS

### Caching Strategy

**Docker Layer Caching**
- Dependencies layer (`RUN pip install -r requirements.txt`) cached until requirements change
- BGE-M3 model layer (2GB) cached across builds, downloaded once
- Application code layer rebuilt on every code change (placed after dependencies)
- Build time: 15 minutes first build, 30 seconds incremental builds (95% reduction)

**Migration Execution Caching**
- Alembic maintains version table, skipping already-applied migrations (O(1) version check)
- Migration scripts compiled to Python bytecode, cached in `__pycache__`
- Database connection pooling: Reuse connections across multiple migration operations

**Demo Data Caching**
- Processed documents cached in storage layer after first seeding
- Re-running `seed_demo.py` checks for existing documents by SHA256 hash
- Embeddings cached in Redis (TTL: 1 hour) to speed up repeated processing
- Search index warmed after seeding: Runs sample queries to populate PostgreSQL cache

### Query Optimization

**Migration Generation**
- Model introspection uses SQLAlchemy's metadata reflection (cached during runtime)
- Schema comparison algorithm: O(n log n) using sorted table/column lists
- Avoids full table scans: Uses information_schema queries with WHERE clauses

**Demo Data Upload**
- Batch processing: Upload 5 documents concurrently using asyncio.gather()
- Chunk generation: Parallelized using ProcessPoolExecutor (4 workers)
- Embedding generation: Batch size 100 chunks, leverages BGE-M3 batch inference
- Database inserts: Bulk insert for chunks (INSERT INTO ... VALUES (batch), not individual INSERTs)

### Async vs Sync Trade-offs

**Async (Used For)**
- Document upload: Non-blocking I/O during file storage and API calls
- Embedding generation: Can process multiple documents concurrently
- Health checks: Parallel checks to database, Redis, storage (total time = max(individual checks), not sum)

**Sync (Used For)**
- Database migrations: Sequential execution required for consistency
- Docker image builds: Layered approach requires sequential stages
- Demo data verification: Must wait for processing completion before validating search

**Rationale**: Async for I/O-bound operations (network, disk), sync for CPU-bound or order-dependent tasks.

### Resource Limits

**Docker Resource Allocation**
- Backend container: 2GB RAM limit, 1 CPU core, prevents memory leaks from crashing host
- PostgreSQL: 4GB RAM, 2 CPU cores, allows shared_buffers = 1GB for query cache
- Redis: 512MB RAM limit (sufficient for session cache, embedding cache disabled if full)
- Ollama: 8GB RAM (4GB model + 4GB context), 2 CPU cores, GPU passthrough if available

**Database Connection Pooling**
- SQLAlchemy pool: 5 min connections, 20 max connections, prevents connection exhaustion
- Pool timeout: 30 seconds, fails fast rather than queueing indefinitely
- Pool pre-ping: Validates connections before use, handles stale connections gracefully

**File Size Limits**
- Demo documents: Max 10MB each, prevents processing pipeline bottlenecks
- Chunk size: 512 tokens target, 600 max, optimizes embedding quality vs speed
- Upload buffer: 50MB in-memory buffer, streams larger files to disk

---

## 5. ERROR HANDLING

### Failure Scenarios

**Migration Failures**

1. **Schema Conflict (Table Already Exists)**
   - Detection: Alembic catches `ProgrammingError` on CREATE TABLE
   - Recovery: Check `alembic_version` table, mark migration as already applied
   - Logging: WARN level, includes conflicting table name and resolution
   - User Action: Manual verification that existing schema matches expected state

2. **Database Connection Loss During Migration**
   - Detection: PostgreSQL connection timeout or network error
   - Recovery: Transaction rollback automatic (uncommitted changes lost)
   - Retry Logic: 3 retries with exponential backoff (5s, 10s, 20s)
   - Failure Mode: Exit with error code 1, log full stack trace
   - User Action: Verify database availability, re-run migration

3. **Vector Extension Missing**
   - Detection: `CREATE EXTENSION IF NOT EXISTS vector` fails
   - Recovery: Pre-flight check in `env.py`, fails early with clear error message
   - Logging: ERROR level with installation instructions
   - User Action: Install pgvector extension manually or use pgvector Docker image

**Container Startup Failures**

4. **Port Already in Use**
   - Detection: Docker bind error on `docker-compose up`
   - Recovery: No automatic recovery, fail fast
   - Logging: Docker logs with conflicting port and process ID
   - User Action: Stop conflicting process or change port in docker-compose.yml

5. **Health Check Timeout**
   - Detection: Container fails health check after 30 seconds (3 retries * 10s)
   - Recovery: Docker restarts container, max 3 restarts
   - Logging: Container logs sent to stdout, visible in `docker-compose logs`
   - Failure Mode: Mark container as unhealthy, stop dependent containers
   - User Action: Check logs for root cause (database unavailable, missing env vars)

**Demo Data Seeding Failures**

6. **Document Processing Failure**
   - Detection: Exception during text extraction or embedding generation
   - Recovery: Skip failed document, continue processing remaining documents
   - Retry Logic: 2 retries per document with 5-second delay
   - Logging: ERROR level with document path and failure reason
   - Failure Mode: Partial seeding (some documents loaded), exit code 0 with warnings

7. **Insufficient Disk Space**
   - Detection: OS error during file write (errno 28: No space left)
   - Recovery: No automatic recovery, fail immediately
   - Logging: CRITICAL level with available disk space and required space
   - User Action: Free disk space, re-run seeding script

### Rollback Procedures

**Database Rollback**
```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade abc123

# Verify current version
alembic current
```

**Deployment Rollback**
```bash
# Stop current deployment
docker-compose down

# Checkout previous version
git checkout <previous-commit-sha>

# Rollback database
alembic downgrade -1

# Redeploy
docker-compose up -d
```

### Logging Strategy

**Structured Logging Format**
```python
{
  "timestamp": "2024-12-02T10:30:45.123Z",
  "level": "INFO",
  "service": "backend",
  "module": "alembic.env",
  "correlation_id": "abc-123-def",
  "message": "Running migration 001_initial_schema",
  "context": {
    "migration_version": "001",
    "duration_ms": 1234
  }
}
```

**Log Levels Usage**
- DEBUG: SQL statements, query parameters, timing details
- INFO: Migration start/complete, container startup, health check passes
- WARN: Retryable errors, deprecated features, performance degradation
- ERROR: Failed operations requiring user intervention, unhandled exceptions
- CRITICAL: Service unavailable, data corruption detected, security breaches

**Log Aggregation**
- Docker logs → stdout → Docker logging driver (json-file with rotation)
- Production: Forward to centralized logging (e.g., Loki, Elasticsearch)
- Retention: 7 days local, 30 days centralized

---

## 6. CONFIGURATION

### Environment Variables

**Database Configuration**
- `DATABASE_URL` (required): PostgreSQL connection string
  Format: `postgresql://user:pass@host:5432/dbname`
  Default: `postgresql://postgres:postgres@localhost:5432/querybox`

- `ALEMBIC_CONFIG` (optional): Path to alembic.ini
  Default: `backend/alembic.ini`

- `DB_POOL_SIZE` (optional): SQLAlchemy connection pool size
  Default: `5` (balance between connection overhead and concurrency)

**Demo Data Configuration**
- `DEMO_DATA_PATH` (optional): Path to demo documents directory
  Default: `demo-data/documents`
  Rationale: Allows custom demo content for specific use cases

- `DEMO_DOCUMENT_COUNT` (optional): Number of documents to seed
  Default: `5` (fast seeding, sufficient variety)
  Rationale: 5 documents take ~60s to process, good for CI pipelines

- `ENABLE_DEMO_DATA` (optional): Auto-load demo data on startup
  Default: `false` (explicit opt-in)
  Rationale: Production environments should not auto-seed data

**Application Configuration**
- `AUTO_MIGRATE` (optional): Run migrations on application startup
  Default: `false` (manual control in production)
  Rationale: Migrations should be deliberate, reviewed actions

- `DOCKER_BUILD_CACHE` (optional): Enable Docker layer caching
  Default: `true` (faster builds)

- `LOG_LEVEL` (optional): Logging verbosity
  Default: `INFO` (balance between noise and visibility)
  Options: DEBUG, INFO, WARN, ERROR, CRITICAL

### Feature Flags

**Migration Features**
- `MIGRATION_DRY_RUN`: Generate SQL without executing
  Use case: Review migration changes before applying

- `MIGRATION_BACKUP_BEFORE`: Create database backup before migration
  Use case: Production deployments, critical schema changes

**Demo Data Features**
- `DEMO_INCLUDE_EMBEDDINGS`: Pre-generate embeddings during seeding
  Default: `true` (enables immediate search testing)
  Rationale: Without embeddings, semantic search won't work on demo data

- `DEMO_WARM_CACHE`: Run sample queries after seeding to warm caches
  Default: `true` (improves first user experience)

### Resource Limits

**Container Limits** (docker-compose.yml)
```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '1.0'      # Rationale: FastAPI is async, single core sufficient for dev
        memory: 2G       # Rationale: BGE-M3 model + uvicorn workers + overhead
      reservations:
        cpus: '0.5'      # Guarantee half CPU core
        memory: 1G       # Minimum memory to function
```

**Database Limits**
- `max_connections`: 100 (PostgreSQL default, sufficient for 20 concurrent users)
- `shared_buffers`: 1GB (25% of available RAM, optimizes query cache)
- `work_mem`: 50MB (per connection sort/hash operations)

---

## 7. INTEGRATION DETAILS

### Alembic ↔ SQLAlchemy Integration

**Model Metadata Import**
Alembic's `env.py` imports application models to generate migrations:
```python
from app.models import Base  # Includes all models via __init__.py
target_metadata = Base.metadata
```

This enables automatic migration generation via model introspection. Changes to SQLAlchemy models are detected by comparing `Base.metadata` to database schema.

**Naming Conventions**
SQLAlchemy naming conventions ensure consistent constraint names:
```python
convention = {
    "ix": "ix_%(column_0_label)s",           # Index
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # Unique
    "ck": "ck_%(table_name)s_%(constraint_name)s", # Check
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s", # Foreign key
    "pk": "pk_%(table_name)s"                # Primary key
}
```
Rationale: Predictable names for DROP/ALTER operations in migrations.

### Docker Compose Service Dependencies

**Dependency Graph**
```
backend → postgres (required)
       → redis (required)
       → minio (optional, fallback to local storage)
       → ollama (required for answer generation)

postgres → (no dependencies)
redis → (no dependencies)
minio → (no dependencies)
ollama → (no dependencies)
```

**Health Check Integration**
```yaml
backend:
  depends_on:
    postgres:
      condition: service_healthy  # Waits for Postgres health check to pass
    redis:
      condition: service_started  # Redis starts quickly, no health check needed
```

Backend health check polls dependencies:
1. Database: Execute `SELECT 1` query (connection test)
2. Redis: Execute `PING` command
3. Storage: Check disk space, test write permissions
4. Ollama: HTTP request to `/api/tags`

If any dependency fails, backend reports unhealthy, triggering restart.

### Demo Seeding → Processing Pipeline Integration

**Service Layer Access**
Seed script uses existing service interfaces, not direct database access:

```python
# Upload through DocumentService (validates, stores, creates DB record)
document_id = await document_service.upload_document(file_path, metadata)

# Processing triggered automatically via Celery tasks
# seed_demo.py polls processing_status table until complete
await wait_for_processing(document_id, timeout=60)

# Verify via search API
results = await search_service.search(query="test", top_k=5)
```

**API Contracts**
- `POST /api/v1/upload`: Accepts multipart/form-data with file and metadata JSON
- `GET /api/v1/documents/{id}/status`: Returns processing stage (extraction, chunking, embedding)
- `POST /api/v1/search`: Accepts query string, returns ranked results with citations

**Event Flow**
1. Upload → Document created in `documents` table with status=PENDING
2. Celery task `extract_text_task` → Updates status=EXTRACTING → CHUNKING
3. Celery task `generate_embeddings_task` → Updates status=EMBEDDING → COMPLETED
4. Seed script polls status every 2 seconds until COMPLETED or FAILED

### Database Transactions

**Migration Transactions**
Each migration runs in a single transaction:
```python
with engine.begin() as connection:  # BEGIN
    context.configure(connection=connection)
    context.run_migrations()
    # Automatic COMMIT on success, ROLLBACK on exception
```

**Seed Data Transactions**
Document uploads use separate transactions per document:
```python
async with get_db() as db:
    document = await document_service.create(db, document_data)
    await db.commit()  # Commit after each document
```
Rationale: Partial seeding allowed. If document 3 of 5 fails, documents 1-2 remain saved.

---

## 8. TESTING APPROACH

### Unit Tests

**Migration Generation Test**
File: `backend/tests/unit/test_migrations.py`
```python
def test_initial_migration_creates_all_tables():
    """Verify migration creates documents, embeddings, processing_status tables"""
    from alembic import command
    from alembic.config import Config

    # Run migration on empty test database
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    # Verify tables exist
    inspector = inspect(test_engine)
    tables = inspector.get_table_names()
    assert "documents" in tables
    assert "embeddings" in tables
    assert "processing_status" in tables

    # Verify pgvector extension installed
    result = test_engine.execute("SELECT extname FROM pg_extension WHERE extname='vector'")
    assert result.scalar() == "vector"
```

**Demo Data Factory Test**
File: `backend/tests/unit/test_seed_demo.py`
```python
def test_create_sample_documents():
    """Verify factory creates documents with expected properties"""
    docs = create_sample_documents(count=3)

    assert len(docs) == 3
    assert all(doc.exists() for doc in docs)
    assert any(doc.suffix == ".pdf" for doc in docs)
    assert any(doc.suffix == ".md" for doc in docs)

    # Verify content not empty
    for doc in docs:
        assert doc.stat().st_size > 1000  # Minimum 1KB
```

### Integration Tests

**Full Stack Startup Test**
File: `backend/tests/integration/test_docker_compose.py`
```python
@pytest.mark.integration
def test_docker_compose_startup():
    """Verify all services start and health checks pass"""
    # Start services
    subprocess.run(["docker-compose", "up", "-d"], check=True)

    # Wait for health checks (max 60 seconds)
    for attempt in range(12):
        response = requests.get("http://localhost:8000/health")
        if response.json()["status"] == "healthy":
            break
        time.sleep(5)
    else:
        pytest.fail("Health check failed after 60 seconds")

    # Verify all dependencies healthy
    health = response.json()
    assert health["database"]["status"] == "up"
    assert health["redis"]["status"] == "up"
    assert health["storage"]["status"] == "up"

    # Cleanup
    subprocess.run(["docker-compose", "down", "-v"], check=True)
```

**End-to-End Seeding Test**
```python
@pytest.mark.integration
async def test_demo_data_seeding_and_search():
    """Verify demo data loads and search returns results"""
    # Run seeding
    result = subprocess.run(["python", "backend/scripts/seed_demo.py"],
                            capture_output=True, check=True)
    assert "5 documents seeded successfully" in result.stdout.decode()

    # Test search functionality
    response = requests.post("http://localhost:8000/api/v1/search",
                             json={"query": "deployment guide", "top_k": 5})
    results = response.json()

    assert len(results["documents"]) > 0
    assert any("deployment" in doc["metadata"]["title"].lower()
               for doc in results["documents"])
```

### Performance Benchmarks

**Migration Execution Time**
Target: Initial migration completes in <30 seconds on empty database
```bash
time alembic upgrade head
# Expected: real 0m25.432s
```

**Docker Build Time**
Target: Incremental builds <60 seconds (cached layers)
```bash
time docker build -t querybox-backend .
# First build: ~15 minutes (downloads models)
# Incremental: ~30 seconds (code changes only)
```

**Demo Data Processing Time**
Target: 5 documents fully processed (extracted, chunked, embedded) in <2 minutes
```bash
time python backend/scripts/seed_demo.py
# Expected: ~60-90 seconds (depends on document complexity)
```

### Manual Verification Steps

**Step 1: Clean Slate Test**
```bash
# Remove all containers and volumes
docker-compose down -v

# Verify no stale data
docker volume ls | grep querybox  # Should be empty

# Start fresh
docker-compose up -d

# Verify logs show migration execution
docker-compose logs backend | grep "Running migration"
```

**Step 2: Demo Data Verification**
```bash
# Seed demo data
python backend/scripts/seed_demo.py

# Verify document count in database
docker-compose exec postgres psql -U postgres -d querybox -c "SELECT COUNT(*) FROM documents WHERE metadata->>'demo'='true';"
# Expected: 5

# Test search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "deployment", "top_k": 3}'
# Should return 3 results with citations
```

**Step 3: Health Check Validation**
```bash
# Check health endpoint
curl http://localhost:8000/health | jq
# Expected: {"status": "healthy", "database": {"status": "up", ...}}

# Verify all services responding
docker-compose ps
# All services should show "healthy" or "Up"
```

---

## 9. MONITORING

### Metrics Collected

**Migration Metrics** (Prometheus format)
```
alembic_migration_duration_seconds{version="001"} 25.4
alembic_migration_success_total{version="001"} 1
alembic_migration_failure_total{version="001"} 0
alembic_current_version{version="001"} 1
```

**Container Health Metrics**
```
container_health_status{service="backend"} 1    # 1=healthy, 0=unhealthy
container_restart_count{service="backend"} 0
container_uptime_seconds{service="backend"} 3600
```

**Demo Data Metrics**
```
demo_documents_loaded_total 5
demo_documents_failed_total 0
demo_processing_duration_seconds 72.3
demo_embedding_count_total 487  # Total chunks embedded
```

**Resource Utilization**
```
container_memory_usage_bytes{service="backend"} 524288000  # 500MB
container_cpu_usage_percent{service="backend"} 12.5
postgres_connection_count 3
redis_memory_usage_bytes 10485760  # 10MB
```

### Log Entries Added

**Migration Logs**
```
INFO  - Starting migration to version 001_initial_schema [correlation_id=mig-abc123]
INFO  - Creating table: documents [duration_ms=234]
INFO  - Creating index: idx_documents_created_at [duration_ms=567]
INFO  - Migration 001_initial_schema completed successfully [total_duration_ms=25430]
```

**Container Startup Logs**
```
INFO  - Backend container starting [version=1.0.0, commit=abc123]
INFO  - Database connection established [host=postgres, database=querybox]
INFO  - Health check passed: All dependencies healthy
INFO  - Uvicorn started on http://0.0.0.0:8000
```

**Demo Seeding Logs**
```
INFO  - Starting demo data seeding [document_count=5]
INFO  - Uploaded document: technical_guide.pdf [id=uuid-123, size_mb=2.3]
INFO  - Processing document: technical_guide.pdf [chunks=67]
INFO  - Generated embeddings: technical_guide.pdf [vectors=67, duration_ms=5430]
INFO  - Demo data seeding complete [total_duration_s=72.3, success_count=5, failure_count=0]
```

### Health Check Endpoints

**Primary Health Check**
```
GET /health
Response:
{
  "status": "healthy",
  "timestamp": "2024-12-02T10:30:45Z",
  "checks": {
    "database": {"status": "up", "latency_ms": 12},
    "redis": {"status": "up", "latency_ms": 3},
    "storage": {"status": "up", "disk_free_gb": 45.2},
    "ollama": {"status": "up", "latency_ms": 234}
  }
}
```

**Detailed Health Check** (requires API key)
```
GET /health/detailed
Response:
{
  "status": "healthy",
  "migration_version": "001_initial_schema",
  "demo_data_loaded": true,
  "uptime_seconds": 3600,
  "memory_usage_mb": 512,
  "cpu_usage_percent": 12.5,
  "request_count_last_hour": 1234
}
```

### Alert Thresholds

**Critical Alerts** (PagerDuty/Slack)
- Container unhealthy for >2 minutes
- Migration failure
- Database connection loss
- Disk space <10GB free

**Warning Alerts** (Email)
- Container restarted >3 times in 10 minutes
- Health check latency >5 seconds
- Memory usage >90%
- CPU usage >80% for >5 minutes

**Info Alerts** (Monitoring dashboard)
- Demo data seeded (new environment detected)
- Migration executed (schema version changed)
- Container updated (new image deployed)

---

## 10. CODE SNIPPETS

### Main Class Structure: DemoDataSeeder

```python
from pathlib import Path
from typing import Dict, List
from uuid import UUID
import asyncio
from app.services.document_service import DocumentService
from app.services.search_service import SearchService

class DemoDataSeeder:
    """
    Orchestrates demo data loading with progress tracking and error recovery.

    Responsibilities:
    - Generate sample documents with diverse characteristics
    - Upload documents through DocumentService (exercises validation)
    - Wait for async processing to complete
    - Verify search functionality with sample queries
    - Report detailed progress and errors
    """

    def __init__(
        self,
        demo_data_path: Path,
        document_service: DocumentService,
        search_service: SearchService,
        document_count: int = 5
    ):
        self.demo_data_path = demo_data_path
        self.document_service = document_service
        self.search_service = search_service
        self.document_count = document_count
        self.uploaded_ids: Dict[str, UUID] = {}

    async def seed(self) -> Dict[str, any]:
        """
        Main seeding workflow with error recovery.

        Returns:
            Dict with success_count, failure_count, and uploaded document IDs
        """
        results = {
            "success_count": 0,
            "failure_count": 0,
            "uploaded_ids": {},
            "errors": []
        }

        # Step 1: Create sample documents
        documents = self._create_sample_documents()

        # Step 2: Upload documents concurrently
        upload_tasks = [
            self._upload_document(doc)
            for doc in documents
        ]
        upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)

        # Step 3: Process results and track errors
        for doc, result in zip(documents, upload_results):
            if isinstance(result, Exception):
                results["failure_count"] += 1
                results["errors"].append({"document": doc.name, "error": str(result)})
            else:
                results["success_count"] += 1
                results["uploaded_ids"][doc.name] = result
                self.uploaded_ids[doc.name] = result

        # Step 4: Wait for processing to complete
        await self._wait_for_processing(list(self.uploaded_ids.values()))

        # Step 5: Verify search functionality
        search_verified = await self._verify_search()
        results["search_verified"] = search_verified

        return results

    def _create_sample_documents(self) -> List[Path]:
        """Generate 5 diverse sample documents in demo-data directory"""
        # Implementation omitted for brevity
        pass

    async def _upload_document(self, doc_path: Path) -> UUID:
        """Upload single document through DocumentService"""
        # Implementation omitted for brevity
        pass

    async def _wait_for_processing(self, document_ids: List[UUID], timeout: int = 120):
        """Poll processing status until all documents complete or timeout"""
        # Implementation omitted for brevity
        pass

    async def _verify_search(self) -> bool:
        """Run sample queries and verify results match expected documents"""
        # Implementation omitted for brevity
        pass
```

### Critical Function: Alembic env.py run_migrations_online

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os

# Import application models for metadata
from app.models import Base
target_metadata = Base.metadata

def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (connected to database).

    Critical features:
    - Transaction wrapping for atomic migrations
    - Automatic rollback on failure
    - Connection pooling disabled (migration is one-time operation)
    - Environment variable configuration (12-factor app)
    """

    # Override database URL from environment (supports multiple environments)
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/querybox"
    )

    # Create engine with no pooling (migrations don't need connection reuse)
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Critical: Avoid connection pool exhaustion
    )

    with connectable.connect() as connection:
        # Configure migration context
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Detect column type changes
            compare_server_default=True,  # Detect default value changes
            include_schemas=False,  # Single schema (public)
            version_table="alembic_version",  # Track current migration version
        )

        # Run migration within transaction
        with context.begin_transaction():
            try:
                context.run_migrations()
                # Automatic COMMIT if successful
            except Exception as e:
                # Automatic ROLLBACK on any exception
                # Re-raise to propagate error to caller
                raise
```

### Error Handling Pattern: Upload with Retry

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger()

class DemoDataSeeder:
    @retry(
        stop=stop_after_attempt(3),  # Max 3 attempts
        wait=wait_exponential(multiplier=1, min=4, max=10),  # 4s, 8s, 10s delays
        reraise=True  # Propagate exception after final retry
    )
    async def _upload_document(self, doc_path: Path) -> UUID:
        """
        Upload document with exponential backoff retry.

        Retryable errors:
        - Network timeouts
        - Database connection errors
        - Temporary storage unavailability

        Non-retryable errors (fail immediately):
        - File not found
        - Invalid file type
        - File too large
        """
        try:
            logger.info("uploading_document",
                       document=doc_path.name,
                       size_mb=doc_path.stat().st_size / 1_000_000)

            with open(doc_path, "rb") as f:
                document_id = await self.document_service.upload(
                    file=f,
                    filename=doc_path.name,
                    metadata={"demo": True, "source": "seed_script"}
                )

            logger.info("document_uploaded",
                       document=doc_path.name,
                       document_id=str(document_id))

            return document_id

        except FileNotFoundError as e:
            # Non-retryable: File doesn't exist
            logger.error("document_not_found", document=doc_path.name, error=str(e))
            raise  # Don't retry

        except ValueError as e:
            # Non-retryable: Invalid file type or size
            logger.error("invalid_document", document=doc_path.name, error=str(e))
            raise  # Don't retry

        except Exception as e:
            # Retryable: Network/database/storage errors
            logger.warning("upload_failed_retrying",
                          document=doc_path.name,
                          error=str(e),
                          exc_info=True)
            raise  # Retry via tenacity decorator
```

### Test Example: Migration Rollback

```python
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

@pytest.fixture
def alembic_config():
    """Create Alembic configuration for test database"""
    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url",
        "postgresql://postgres:postgres@localhost:5432/querybox_test"
    )
    return config

def test_migration_rollback(alembic_config, test_engine):
    """
    Verify migration can rollback cleanly without leaving orphaned objects.

    Test steps:
    1. Upgrade to head (apply all migrations)
    2. Verify tables exist
    3. Downgrade to base (rollback all migrations)
    4. Verify tables removed
    5. Upgrade again (re-apply migrations)
    6. Verify idempotency (same result as first upgrade)
    """

    # Step 1: Apply migrations
    command.upgrade(alembic_config, "head")

    # Step 2: Verify tables created
    inspector = inspect(test_engine)
    tables_after_upgrade = inspector.get_table_names()
    assert "documents" in tables_after_upgrade
    assert "embeddings" in tables_after_upgrade

    # Verify pgvector extension installed
    with test_engine.connect() as conn:
        result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname='vector'"))
        assert result.scalar() == "vector"

    # Step 3: Rollback migrations
    command.downgrade(alembic_config, "base")

    # Step 4: Verify tables removed
    inspector = inspect(test_engine)
    tables_after_downgrade = inspector.get_table_names()
    assert "documents" not in tables_after_downgrade
    assert "embeddings" not in tables_after_downgrade

    # Verify version table still exists (tracks migration state)
    assert "alembic_version" in tables_after_downgrade

    # Step 5: Re-apply migrations (test idempotency)
    command.upgrade(alembic_config, "head")

    # Step 6: Verify identical result
    inspector = inspect(test_engine)
    tables_after_reupgrade = inspector.get_table_names()
    assert set(tables_after_reupgrade) == set(tables_after_upgrade)
```

---

## 11. IMPORTANT DECISIONS

### Why Alembic Over Manual SQL Scripts

**Decision**: Use Alembic for database migrations instead of maintaining schema.sql manually.

**Rationale**:
- **Version Control**: Git tracks migration history, enabling blame, rollback, and branching
- **Team Collaboration**: Multiple developers can create migrations independently, Alembic resolves conflicts
- **Automatic Generation**: Alembic detects model changes and generates migrations (90% accuracy, manual review required)
- **Rollback Safety**: Down migrations allow reverting changes without data loss
- **CI/CD Integration**: `alembic upgrade head` runs in deployment pipeline, no manual SQL execution

**Alternatives Considered**:
1. **Manual schema.sql** - Rejected: No version history, no rollback, merge conflicts on schema changes
2. **Django ORM migrations** - Rejected: Requires Django framework, overkill for FastAPI project
3. **Flyway/Liquibase** - Rejected: Java-based, additional runtime dependency

**Trade-offs Accepted**:
- Initial setup complexity (alembic init, env.py configuration)
- Learning curve for team (Alembic-specific commands)
- Autogenerate not 100% accurate (manual review required for complex changes like enum modifications)

### Why Multi-Stage Docker Build

**Decision**: Use multi-stage Dockerfile (builder + runtime) instead of single-stage build.

**Rationale**:
- **Image Size**: Single-stage = 1.2GB, multi-stage = 400MB (66% reduction)
- **Security**: Runtime image excludes build tools (gcc, make), reducing attack surface
- **Build Speed**: Cached builder stage reused across builds, only runtime layer rebuilt on code changes
- **Production Safety**: Build dependencies (dev tools, test libraries) never reach production

**Implementation**:
```dockerfile
# Stage 1: Builder (1GB)
FROM python:3.11-slim as builder
RUN apt-get update && apt-get install -y gcc
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage 2: Runtime (400MB)
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY ./app /app
ENV PATH=/root/.local/bin:$PATH
```

**Trade-offs Accepted**:
- Slightly more complex Dockerfile (2 stages vs 1)
- Must manually track which files go in each stage
- Debugging harder (can't install tools in runtime stage without rebuilding)

### Why 5 Sample Documents for Demo Data

**Decision**: Seed 5 documents instead of 10 or 20.

**Rationale**:
- **Processing Time**: 5 docs = 60-90 seconds, 10 docs = 120+ seconds (CI timeout threshold)
- **Variety**: 5 allows one of each type (PDF, MD, HTML, TXT, JSON), demonstrating all processing pipelines
- **Storage Cost**: 5 docs = ~20MB, manageable in CI environments with limited disk
- **Search Relevance**: 5 docs sufficient to demonstrate hybrid search, reranking, and citation extraction

**Alternatives Considered**:
1. **1-2 documents** - Rejected: Insufficient to test search ranking (need multiple results)
2. **10+ documents** - Rejected: Too slow for CI pipelines, excessive storage in demo environments
3. **Dynamic count via env var** - Accepted: `DEMO_DOCUMENT_COUNT` allows customization

**Trade-offs Accepted**:
- Limited diversity (can't demonstrate all document edge cases with only 5 samples)
- Search results may lack depth (few documents to rank)
- May need to add more documents later for specific feature demos

### Technical Debt Incurred

**1. Manual Schema Sync Required**
**Debt**: `docker/postgres-init/01-schema.sql` must be manually synced with `backend/db/schema.sql` initially.

**Rationale**: Docker init scripts run before Alembic, so initial container creation uses old schema.sql.

**Payoff Plan**: After Alembic adoption, deprecate docker init scripts. Migrations become single source of truth.

**2. Demo Data Not Versioned**
**Debt**: Sample documents stored in Git (binary files), no version control for content changes.

**Rationale**: Simplest approach for MVP, avoids dependency on external storage or asset management system.

**Payoff Plan**: Move to Git LFS or external storage (S3) if demo data grows beyond 50MB.

**3. No Automated Migration Testing in CI**
**Debt**: Migrations tested manually, not run in CI pipeline.

**Rationale**: Requires PostgreSQL in CI environment, adds 30+ seconds to pipeline.

**Payoff Plan**: Add GitHub Actions workflow with postgres service container, run migrations on every PR.

**4. Health Check Credentials in Code**
**Debt**: Health check API key validated in code, not externalized to secrets management.

**Rationale**: Simplifies deployment, avoids dependency on Vault/AWS Secrets Manager for MVP.

**Payoff Plan**: Integrate secrets manager when deploying to production (AWS Secrets Manager, HashiCorp Vault).

### Future Improvements

**1. Auto-Migration on Startup** (v2.0)
Run `alembic upgrade head` automatically when backend container starts, no manual migration command needed.

**Benefits**: Eliminates deployment step, reduces human error.
**Risks**: Failed migration crashes container startup, harder to troubleshoot.
**Implementation**: Add pre-start script in Docker CMD.

**2. Dynamic Demo Data Generation** (v2.1)
Generate demo documents programmatically using templates + random data, rather than storing static files.

**Benefits**: Reduces repo size, allows customizable demo scenarios (e.g., finance vs healthcare docs).
**Risks**: Generated content may lack realism, harder to debug search issues.
**Implementation**: Create document templates with Jinja2, populate with faker library.

**3. Migration Dry-Run in CI** (v2.2)
Add GitHub Actions job that generates migration from model changes, posts SQL diff as PR comment.

**Benefits**: Reviewers see schema changes without running locally, catches migration errors early.
**Risks**: Adds 30s to CI time, requires PostgreSQL service in GitHub Actions.
**Implementation**: GitHub Actions workflow with `services: postgres` and `alembic upgrade --sql head`.

**4. Rollback Testing** (v2.3)
Automated tests that apply migrations, rollback, re-apply, and verify idempotency.

**Benefits**: Ensures down migrations work correctly (often forgotten), prevents production incidents.
**Risks**: Doubles migration test time.
**Implementation**: Pytest fixture that runs upgrade → downgrade → upgrade cycle.

**5. Multi-Database Support** (v3.0)
Support PostgreSQL, MySQL, SQLite via Alembic dialect switching.

**Benefits**: Widens deployment options (SQLite for local dev, MySQL for legacy systems).
**Risks**: Each database has quirks (pgvector only works with Postgres), increases testing matrix.
**Implementation**: Conditional Alembic templates based on database type, separate CI jobs per database.

---

## Summary

Step 12 delivers **one-command deployment** by automating three critical gaps:
1. **Database Migrations** via Alembic: Reproducible schema evolution with rollback safety
2. **Deployment Infrastructure** via Docker: Hermetic containers with multi-stage builds (66% size reduction)
3. **Demo Data Pipeline** via seed script: Realistic test data generated in 60 seconds

These improvements reduce setup time from **30+ minutes** (manual database creation, environment configuration, test data creation) to **<5 minutes** (`docker-compose up && python scripts/seed_demo.py`). This unlocks rapid iteration for developers and enables CI/CD automation for production deployments.

**Key Metrics**:
- Initial migration: <30 seconds
- Docker build: 15 minutes first time, 30 seconds incremental
- Demo data seeding: 60-90 seconds for 5 documents
- Total setup: <5 minutes from clone to working system

**Next Steps** (Step 13):
With deployment automated, focus shifts to frontend development. The backend API is now containerized and demo-ready, enabling parallel frontend development without backend setup friction.