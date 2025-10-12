# QueryBox Core: Step 1 - Database & Storage Foundation
## Technical Implementation Documentation

---

## 1. FEATURE OVERVIEW

### What This Step Accomplishes
Step 1 establishes the foundational data persistence layer for QueryBox Core, implementing:
- PostgreSQL database with pgvector extension for future semantic search capabilities
- Complete document metadata schema supporting versioning and processing stages
- Redis configuration for caching and future queue management
- Local file storage with organized directory structure
- Database connection pooling for optimal performance
- Basic health checking and monitoring setup

### Why This Step is Necessary
The Database & Storage Foundation is critical because it:
- Provides persistent storage for all document metadata and relationships
- Enables tracking of document processing stages and status
- Establishes the groundwork for vector embeddings and semantic search
- Creates a scalable storage architecture supporting multiple providers
- Implements audit trails and versioning from the beginning

### Dependencies
- Docker and Docker Compose for containerized services
- PostgreSQL 15+ with pgvector extension
- Redis 7+ for caching
- Python 3.11+ with FastAPI framework

### What Future Steps Depend on This
- **Step 2**: Upload service requires document table and storage paths
- **Step 3**: Storage service pattern builds on local storage structure
- **Step 4**: Processing pipeline needs status tracking tables
- **Week 2-4**: All features depend on this persistence layer

---

## 2. TECHNICAL IMPLEMENTATION

### Files Created/Modified

#### Database Layer
```
/backend/app/db/
├── database.py                    # Database engine, session management
└── __init__.py                    # Database module initialization

/backend/db/
└── schema.sql                     # Complete PostgreSQL schema

/backend/app/models/
├── __init__.py                    # Models module initialization
├── document.py                    # Document model with metadata
├── document_version.py            # Version tracking model
├── processing_status.py           # Processing stage tracking
├── processing_queue.py            # Queue management model
└── embedding.py                   # Vector embeddings model
```

#### Configuration
```
/backend/app/core/
├── config.py                      # Application settings
├── redis.py                       # Redis connection management
└── __init__.py                    # Core module initialization
```

#### Storage Structure
```
/storage/
├── uploads/                       # Temporary upload directory
├── processing/                    # Files being processed
├── completed/                     # Successfully processed files
├── failed/                        # Failed processing attempts
└── storage.md                     # Storage documentation
```

#### Docker Configuration
```
/docker/
├── docker-compose.yml             # Service orchestration
├── postgres-init/
│   └── 01_install_pgvector.sql   # pgvector extension setup
└── pgadmin/
    ├── pgadmin-servers.json       # pgAdmin configuration
    └── pgpassfile                 # pgAdmin password file
```

### Key Classes and Functions

#### Database Connection (`/backend/app/db/database.py`)
```python
class DatabaseManager:
    engine: Engine                 # SQLAlchemy engine with connection pooling
    SessionLocal: sessionmaker     # Session factory
    
def get_db():                     # Dependency injection for FastAPI
def test_connection():            # Health check function
```

#### Document Model (`/backend/app/models/document.py`)
```python
class Document(Base):
    id: UUID                      # Primary key
    document_name: str            # User-facing name
    original_name: str            # Original filename
    mime_type: str                # File MIME type
    file_size: int                # Size in bytes
    checksum: str                 # SHA-256 hash
    storage_path: str             # Storage location
    status: DocumentStatusEnum    # Current status
    # ... additional fields for versioning, metadata, timestamps
```

#### Redis Connection (`/backend/app/core/redis.py`)
```python
async def init_redis():           # Initialize Redis connection
async def get_redis():            # Get Redis client
async def close_redis():          # Cleanup connection
```

### Database Tables

#### documents
- **id** (UUID): Primary identifier
- **document_name** (VARCHAR): Display name
- **original_name** (VARCHAR): Original filename
- **mime_type** (VARCHAR): File type
- **file_size** (BIGINT): Size in bytes
- **checksum** (VARCHAR): SHA-256 hash
- **storage_provider** (ENUM): local/s3/azure_blob
- **storage_path** (TEXT): File location
- **status** (ENUM): pending/processing/completed/failed
- **created_at** (TIMESTAMP): Creation time
- **updated_at** (TIMESTAMP): Last modification
- **deleted_at** (TIMESTAMP): Soft delete timestamp

#### document_versions
- **id** (UUID): Version identifier
- **document_id** (UUID): Parent document reference
- **version_number** (INT): Sequential version
- **is_latest** (BOOLEAN): Current version flag
- **created_at** (TIMESTAMP): Version creation time

#### processing_status
- **id** (UUID): Status record identifier
- **document_id** (UUID): Document reference
- **stage** (ENUM): Current processing stage
- **status** (ENUM): Stage status
- **started_at** (TIMESTAMP): Stage start time
- **completed_at** (TIMESTAMP): Stage completion time
- **error_message** (TEXT): Failure details

#### embeddings
- **id** (UUID): Embedding identifier
- **document_id** (UUID): Document reference
- **chunk_index** (INT): Position in document
- **embedding** (VECTOR(1536)): Vector representation
- **created_at** (TIMESTAMP): Generation time

### API Endpoints
No API endpoints are created in Step 1. This step focuses purely on the data layer foundation.

### Background Tasks
No background tasks are implemented in Step 1. Celery configuration is prepared for future steps.

---

## 3. DATA FLOW

### Database Initialization Flow
1. **Docker Compose Start** → PostgreSQL container launches
2. **Extension Installation** → pgvector extension installed via init script
3. **Schema Creation** → Tables created from schema.sql
4. **Connection Pool Setup** → SQLAlchemy creates connection pool
5. **Health Check** → Verify database connectivity

### Redis Initialization Flow
1. **Docker Compose Start** → Redis container launches
2. **Connection Creation** → AsyncRedis client initialized
3. **Health Check** → Verify Redis connectivity
4. **Ready for Use** → Available for caching operations

### Storage Directory Creation
1. **Directory Creation** → Four directories created under `/storage`
2. **Permission Setting** → 755 permissions for read/write access
3. **Documentation** → storage.md explains directory purposes
4. **Volume Mounting** → Docker maps to container paths

### Connection Pooling Flow
```python
Engine Configuration:
- pool_size: 5 connections
- max_overflow: 10 connections
- pool_timeout: 30 seconds
- pool_pre_ping: True (verify connections)
```

---

## 4. VALIDATIONS & CONSTRAINTS

### Database Constraints
- **Primary Keys**: UUID for all tables
- **Foreign Keys**: Cascade delete for related records
- **Unique Constraints**: 
  - documents.checksum (prevent duplicates)
  - processing_status.(document_id, stage) (one status per stage)
- **Not Null**: Critical fields like document_name, mime_type, file_size
- **Check Constraints**:
  - file_size > 0
  - version_number > 0

### Storage Constraints
- **Directory Structure**: Fixed four-directory pattern
- **Permissions**: 755 for directories, 644 for files
- **Path Length**: Maximum 255 characters
- **Reserved Names**: System directories protected

### Connection Limits
- **PostgreSQL**: Maximum 100 connections
- **Redis**: Maximum 10,000 connections
- **Connection Pool**: 15 total connections (5 + 10 overflow)

---

## 5. CONFIGURATION

### Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://querybox:querybox_dev_2024@localhost:5432/querybox_core
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_DECODE_RESPONSES=True
REDIS_MAX_CONNECTIONS=50

# Storage Configuration
STORAGE_PATH=storage
STORAGE_PERMISSIONS=755

# PostgreSQL Docker
POSTGRES_USER=querybox
POSTGRES_PASSWORD=querybox_dev_2024
POSTGRES_DB=querybox_core

# pgAdmin Configuration
PGADMIN_DEFAULT_EMAIL=admin@querybox.dev
PGADMIN_DEFAULT_PASSWORD=admin123
```

### Default Values
- **Database Pool**: 5 connections, 10 overflow
- **Redis Pool**: 50 connections maximum
- **Storage Path**: `./storage` relative to project root
- **File Permissions**: 755 for directories

### Directory Structure
```
/storage/
├── uploads/         # Temporary files during upload
├── processing/      # Files being processed
├── completed/       # Successfully processed files
└── failed/          # Failed processing attempts
```

### Docker Services
```yaml
services:
  postgres:         # PostgreSQL 15 with pgvector
  pgadmin:          # Database administration UI
  redis:            # Redis 7 for caching
  minio:            # S3-compatible storage (future)
```

---

## 6. ERROR HANDLING

### Database Connection Failures
```python
# Connection retry with exponential backoff
try:
    engine.connect()
except OperationalError:
    # Log error
    # Retry with delays: 1s, 2s, 4s, 8s
    # Maximum 5 attempts
    # Raise if all attempts fail
```

### Redis Connection Failures
```python
# Graceful degradation without Redis
try:
    redis_client = await get_redis()
except RedisConnectionError:
    # Log warning
    # Continue without caching
    # Features degrade gracefully
```

### Storage Access Failures
- **Directory Not Found**: Create missing directories automatically
- **Permission Denied**: Log error, return 500 to client
- **Disk Full**: Check space before operations, fail fast
- **Path Too Long**: Validate before attempting creation

### Error Messages
```python
# Database errors
"Database connection failed: Connection refused"
"Connection pool exhausted: Timeout after 30s"
"Database migration failed: Schema version mismatch"

# Redis errors
"Redis connection failed: Connection refused"
"Redis operation failed: Memory limit exceeded"

# Storage errors
"Storage directory creation failed: Permission denied"
"Storage path invalid: Path too long (>255 chars)"
```

### Recovery Mechanisms
- **Database**: Automatic reconnection with connection pool
- **Redis**: Bypass cache on failure, direct to database
- **Storage**: Fallback to alternate directories if configured

---

## 7. TESTING CHECKLIST

### Database Setup Verification
- [ ] PostgreSQL container running: `docker-compose ps postgres`
- [ ] pgvector extension installed: `SELECT * FROM pg_extension WHERE extname = 'vector';`
- [ ] All tables created: `\dt` in psql should show 6 tables
- [ ] Indexes created: `\di` should show primary and unique indexes

### Redis Verification
- [ ] Redis container running: `docker-compose ps redis`
- [ ] Connection test: `docker-compose exec redis redis-cli ping`
- [ ] Memory configured: `docker-compose exec redis redis-cli INFO memory`

### Storage Verification
- [ ] Directories exist: `ls -la storage/`
- [ ] Correct permissions: Should show `drwxr-xr-x` (755)
- [ ] Write test: `echo "test" > storage/uploads/test.txt`
- [ ] Docker volume mount: Verify files appear in container

### Connection Pool Testing
```python
# Test concurrent connections
import asyncio
from app.db.database import get_db

async def test_connection():
    db = next(get_db())
    result = db.execute("SELECT 1")
    return result.scalar()

# Run 20 concurrent queries
tasks = [test_connection() for _ in range(20)]
results = await asyncio.gather(*tasks)
assert all(r == 1 for r in results)
```

### Expected Behavior
- Database queries complete in <100ms
- Redis operations complete in <10ms
- Storage operations complete in <50ms
- Health checks return within 1 second

### Performance Benchmarks
- **Connection Pool**: Handle 100+ requests/second
- **Database Queries**: <10ms for simple queries
- **Redis Operations**: <1ms for get/set operations
- **Storage I/O**: >100MB/s read/write speed

---

## 8. MONITORING & METRICS

### Health Check Indicators
```python
GET /health → {
    "status": "healthy",
    "database": {
        "connected": true,
        "pool_size": 5,
        "active_connections": 2
    },
    "redis": {
        "connected": true,
        "memory_used_mb": 12.5
    },
    "storage": {
        "writable": true,
        "space_available_gb": 45.2
    }
}
```

### Database Metrics
- **Connection Pool**: Size, active, idle, overflow
- **Query Performance**: Execution time per query type
- **Transaction Rate**: Commits/rollbacks per minute
- **Lock Contention**: Waiting queries count

### Redis Metrics
- **Memory Usage**: Current usage, peak usage
- **Connection Count**: Active connections
- **Operation Latency**: GET/SET operation times
- **Hit Rate**: Cache hits vs misses

### Storage Metrics
- **Disk Usage**: Space used per directory
- **I/O Operations**: Read/write operations per second
- **File Count**: Files per directory
- **Operation Latency**: File operation durations

### Log Entries
```
# Database logs
INFO: Database connection established
INFO: Connection pool created: size=5, overflow=10
WARNING: Connection pool near capacity: 13/15 connections
ERROR: Database connection failed: timeout after 30s

# Redis logs
INFO: Redis connection established
WARNING: Redis memory usage high: 90% of limit
ERROR: Redis connection lost: Connection refused

# Storage logs
INFO: Storage directories created successfully
INFO: Storage health check passed
ERROR: Storage write failed: No space left on device
```

---

## 9. SECURITY CONSIDERATIONS

### Database Security
- **Credentials**: Stored in environment variables, not in code
- **Connection Encryption**: SSL/TLS ready for production
- **User Permissions**: Least privilege principle applied
- **SQL Injection**: Parameterized queries via SQLAlchemy

### Redis Security
- **Authentication**: Password protection ready
- **Network Isolation**: Docker network isolation
- **Command Restrictions**: Dangerous commands disabled
- **Memory Limits**: Prevent memory exhaustion

### Storage Security
- **Directory Permissions**: 755 prevents unauthorized access
- **Path Validation**: No directory traversal allowed
- **File Permissions**: 644 for uploaded files
- **Quota Management**: Prepared for user quotas

### Network Security
- **Docker Networks**: Isolated bridge network
- **Port Exposure**: Only necessary ports exposed
- **Service Communication**: Internal DNS names used
- **Firewall Ready**: Compatible with host firewall rules

---

## 10. CODE PATTERNS & CONVENTIONS

### Design Patterns

#### Singleton Pattern (Database/Redis)
```python
# Single database engine instance
_engine = None
def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine
```

#### Factory Pattern (Session Creation)
```python
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
```

#### Repository Pattern (Prepared)
```python
# Ready for repository layer
class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, document: Document) -> Document:
        self.db.add(document)
        self.db.commit()
        return document
```

### Naming Conventions
- **Database**: Snake_case for tables and columns
- **Models**: PascalCase for class names
- **Functions**: snake_case for function names
- **Constants**: UPPER_SNAKE_CASE
- **Files**: snake_case.py

### Async Patterns
```python
# Async Redis operations
async def get_cached_value(key: str):
    redis = await get_redis()
    return await redis.get(key)

# Sync database operations (for now)
def get_document(db: Session, doc_id: UUID):
    return db.query(Document).filter(Document.id == doc_id).first()
```

### Transaction Boundaries
```python
# Explicit transaction management
with db.begin():
    document = Document(**data)
    db.add(document)
    # Automatic commit or rollback
```

---

## 11. INTEGRATION POINTS

### Database Integration
```python
# FastAPI dependency injection
@app.get("/documents/{id}")
def get_document(id: UUID, db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.id == id).first()
```

### Redis Integration
```python
# Caching layer (prepared for future)
async def get_cached_or_fetch(key: str, fetch_func):
    redis = await get_redis()
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    
    result = await fetch_func()
    await redis.set(key, json.dumps(result), ex=3600)
    return result
```

### Storage Integration
```python
# File operations
def save_uploaded_file(file: UploadFile) -> str:
    file_path = f"storage/uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    return file_path
```

### Docker Service Communication
```yaml
# Internal service names
DATABASE_URL=postgresql://querybox:password@postgres:5432/querybox_core
REDIS_URL=redis://redis:6379
```

---

## 12. TROUBLESHOOTING GUIDE

### Common Issues and Solutions

#### "Database connection refused"
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Verify credentials
docker-compose exec postgres psql -U querybox -d querybox_core

# Solution: Restart PostgreSQL
docker-compose restart postgres
```

#### "pgvector extension not found"
```bash
# Connect to database
docker-compose exec postgres psql -U querybox -d querybox_core

# Install extension manually
CREATE EXTENSION IF NOT EXISTS vector;

# Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

#### "Redis connection failed"
```bash
# Check Redis status
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping

# Check memory
docker-compose exec redis redis-cli INFO memory

# Solution: Restart Redis
docker-compose restart redis
```

#### "Storage permission denied"
```bash
# Check permissions
ls -la storage/

# Fix permissions
chmod -R 755 storage/
chown -R $USER:$USER storage/

# Verify Docker can access
docker-compose exec postgres ls -la /storage
```

### Debug Commands
```bash
# Database debugging
docker-compose exec postgres pg_stat_activity  # Active connections
docker-compose exec postgres pg_stat_database  # Database statistics

# Redis debugging
docker-compose exec redis redis-cli MONITOR    # Real-time commands
docker-compose exec redis redis-cli INFO       # Server information

# Container debugging
docker-compose logs -f postgres                 # Follow logs
docker-compose exec postgres bash              # Shell access
```

### Verification Queries
```sql
-- Check database tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';

-- Verify pgvector
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check constraints
SELECT conname, contype, conrelid::regclass 
FROM pg_constraint 
WHERE connamespace = 'public'::regnamespace;

-- Connection pool status
SELECT datname, numbackends, active_time 
FROM pg_stat_database 
WHERE datname = 'querybox_core';
```

### Log Locations
```bash
# PostgreSQL logs
docker-compose logs postgres > postgres.log

# Redis logs
docker-compose logs redis > redis.log

# Application logs (when running)
tail -f backend/logs/app.log

# Docker daemon logs
journalctl -u docker.service
```

---

## Summary

Step 1 successfully establishes a robust database and storage foundation for QueryBox Core, providing:

1. **Complete PostgreSQL schema** with pgvector support for future semantic search
2. **Redis caching layer** ready for session management and queuing
3. **Organized storage structure** with proper permissions and documentation
4. **Connection pooling** for optimal database performance
5. **Health monitoring** capabilities for all components
6. **Security measures** including credential management and network isolation
7. **Error handling** with graceful degradation and recovery mechanisms

This foundation enables all future development steps and provides the persistence layer required for document upload, processing, and retrieval operations.