# QueryBox Core: Step 2 - Core API Structure
## Technical Implementation Documentation

---

## 1. FEATURE OVERVIEW

### What This Step Accomplishes
Step 2 establishes the core FastAPI application structure that serves as the foundation for all API endpoints and functionality:
- Complete FastAPI application initialization with lifecycle management
- CORS middleware configuration for cross-origin requests
- Modular route organization with API versioning
- Comprehensive health check endpoint with dependency monitoring
- Structured project layout following best practices
- Async request handling foundation

### Why This Step is Necessary
The Core API Structure is essential because it:
- Provides the HTTP interface for all client interactions
- Establishes middleware patterns for security and monitoring
- Creates a scalable routing structure for future endpoints
- Implements health monitoring for production readiness
- Sets up proper error handling and response formatting
- Enables async operations for high-performance handling

### Dependencies on Previous Steps
- **Step 1**: Requires database connection and Redis setup for health checks
- **Step 1**: Uses connection pooling configuration for dependency injection
- **Step 1**: Leverages storage directory structure for status reporting

### What Future Steps Depend on This
- **Step 3**: Upload endpoints will use the routing structure
- **Step 4**: Document management APIs build on this foundation
- **All Future Features**: Every API endpoint extends this structure
- **Monitoring**: Health checks enable production monitoring

---

## 2. TECHNICAL IMPLEMENTATION

### Files Created/Modified

#### Core Application Files
```
/backend/app/
├── main.py                        # Main FastAPI application
├── __init__.py                    # App module initialization

/backend/app/api/
├── __init__.py                    # API module initialization
└── v1/
    ├── __init__.py                # V1 API initialization
    ├── router.py                  # Main API router
    └── endpoints/
        ├── __init__.py            # Endpoints initialization
        ├── health.py              # Health check endpoint
        ├── upload.py              # Upload endpoints (stub)
        ├── documents.py           # Document endpoints (stub)
        └── search.py              # Search endpoints (stub)
```

#### Middleware and Dependencies
```
/backend/app/core/
├── config.py                      # Enhanced with API settings
├── deps.py                        # Dependency injection helpers
└── middleware.py                  # Custom middleware (future)
```

### Key Classes and Functions

#### Main Application (`/backend/app/main.py`)
```python
# Application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Redis, warm up connections
    await init_redis()
    yield
    # Shutdown: Cleanup connections
    await close_redis()

# FastAPI application instance
app = FastAPI(
    title="QueryBox Core API",
    description="High-performance document processing and retrieval system",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### API Router (`/backend/app/api/v1/router.py`)
```python
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
```

#### Health Check Endpoint (`/backend/app/api/v1/endpoints/health.py`)
```python
@router.get("/")
async def health_check():
    """Comprehensive health check with dependency status"""
    return {
        "status": "healthy",
        "service": "querybox-core-api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": check_database_health(),
            "redis": await check_redis_health(),
            "storage": check_storage_health()
        }
    }
```

### API Endpoints Created

#### Root Endpoints
- `GET /` - Welcome message and API information
- `GET /health` - Basic health check (main.py)

#### V1 API Endpoints
- `GET /api/v1/health/` - Comprehensive health check with dependency status
- `GET /api/v1/health/ready` - Readiness probe for Kubernetes
- `GET /api/v1/health/live` - Liveness probe for Kubernetes

#### OpenAPI Documentation
- `GET /api/v1/openapi.json` - OpenAPI 3.0 specification
- `GET /docs` - Swagger UI (automatic)
- `GET /redoc` - ReDoc UI (automatic)

### Configuration Updates

#### API-specific Settings (`/backend/app/core/config.py`)
```python
class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "QueryBox Core"
    VERSION: str = "1.0.0"
    
    # CORS Configuration  
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # API Limits
    MAX_REQUEST_SIZE: int = 100 * 1024 * 1024  # 100MB
    REQUEST_TIMEOUT: int = 300  # 5 minutes
```

---

## 3. DATA FLOW

### Application Startup Flow
1. **FastAPI Initialization** → Application instance created with metadata
2. **Lifespan Context** → Startup event triggers initialization
3. **Redis Connection** → Async Redis client initialized and tested
4. **Database Pool** → Connection pool warmed up with test query
5. **Storage Check** → Verify storage directories are accessible
6. **Router Registration** → All endpoint routers included
7. **Middleware Setup** → CORS and other middleware configured
8. **Ready to Serve** → Application starts accepting requests

### Request Processing Flow
1. **Client Request** → HTTP request hits the application
2. **CORS Validation** → Middleware checks origin permissions
3. **Route Matching** → FastAPI matches URL to endpoint
4. **Dependency Injection** → Database sessions, Redis clients injected
5. **Handler Execution** → Async endpoint function runs
6. **Response Serialization** → Pydantic models serialize response
7. **Middleware Processing** → Response passes through middleware
8. **Client Response** → JSON response sent to client

### Health Check Flow
```
GET /api/v1/health/
├── Database Check
│   ├── Get connection from pool
│   ├── Execute "SELECT 1"
│   └── Return status
├── Redis Check
│   ├── Get Redis client
│   ├── Execute PING
│   └── Return status
├── Storage Check
│   ├── Check directory exists
│   ├── Verify write permissions
│   └── Return status
└── Aggregate Results → Return combined health status
```

### Error Flow
1. **Exception Raised** → Handler or dependency throws exception
2. **Exception Handler** → FastAPI catches and processes
3. **Error Response** → Formatted error with status code
4. **Logging** → Error logged with context and traceback
5. **Metrics** → Error counter incremented (future)

---

## 4. VALIDATIONS & CONSTRAINTS

### Request Validations
- **Content-Type**: Must be application/json for JSON endpoints
- **Request Size**: Maximum 100MB (configurable)
- **URL Length**: Maximum 2048 characters
- **Header Size**: Maximum 8KB per header

### CORS Validations
```python
# Allowed origins (configurable)
BACKEND_CORS_ORIGINS = [
    "http://localhost:3000",    # Frontend dev server
    "http://localhost:8080",    # Alternative port
    "https://app.querybox.dev", # Production frontend
]

# Allowed methods
allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]

# Allowed headers
allow_headers=["*"]  # All headers allowed in development
```

### Health Check Constraints
- **Response Time**: Must complete within 5 seconds
- **Database Check**: Connection and query must succeed
- **Redis Check**: Optional - failure doesn't fail health check
- **Storage Check**: Directories must exist and be writable

### Rate Limiting (Prepared for Future)
```python
# Future implementation
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_PERIOD = 60  # seconds
RATE_LIMIT_BURST = 20
```

---

## 5. CONFIGURATION

### Environment Variables
```bash
# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME="QueryBox Core"
VERSION=1.0.0

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4
RELOAD=true  # Development only

# CORS Configuration
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]

# Request Limits
MAX_REQUEST_SIZE=104857600  # 100MB
REQUEST_TIMEOUT=300          # 5 minutes

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
ACCESS_LOG=true

# Documentation
DOCS_URL=/docs
REDOC_URL=/redoc
OPENAPI_URL=/api/v1/openapi.json
```

### Default Values
- **Host**: 0.0.0.0 (all interfaces)
- **Port**: 8000
- **Workers**: 4 (production), 1 (development)
- **Request Timeout**: 300 seconds
- **Max Request Size**: 100MB
- **CORS**: Localhost origins allowed

### API Versioning Structure
```
/api/
└── v1/                    # Version 1 API
    ├── health/            # Health endpoints
    ├── upload/            # Upload endpoints
    ├── documents/         # Document management
    └── search/            # Search functionality
```

### Docker Service Dependencies
- **Backend Service**: Runs the FastAPI application
- **PostgreSQL**: Required for database health checks
- **Redis**: Required for Redis health checks
- **Storage Volume**: Required for storage health checks

---

## 6. ERROR HANDLING

### Global Exception Handlers
```python
# Validation errors (422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": exc.body
        }
    )

# Generic HTTP exceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )

# Unhandled exceptions (500)
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__
        }
    )
```

### Error Response Format
```json
{
    "detail": "Error message",
    "status_code": 400,
    "type": "ValidationError",
    "timestamp": "2024-11-15T10:30:00Z",
    "path": "/api/v1/upload",
    "request_id": "uuid-string"
}
```

### Common Error Scenarios
1. **404 Not Found**: Invalid endpoint path
2. **405 Method Not Allowed**: Wrong HTTP method
3. **422 Unprocessable Entity**: Validation errors
4. **500 Internal Server Error**: Unhandled exceptions
5. **503 Service Unavailable**: Dependencies unavailable

### Logging Configuration
```python
# Structured logging
logger = logging.getLogger("querybox.api")
logger.setLevel(settings.LOG_LEVEL)

# Log format
{
    "timestamp": "2024-11-15T10:30:00Z",
    "level": "ERROR",
    "logger": "querybox.api",
    "message": "Request failed",
    "extra": {
        "path": "/api/v1/upload",
        "method": "POST",
        "status_code": 500,
        "duration_ms": 125
    }
}
```

---

## 7. TESTING CHECKLIST

### API Startup Testing
- [ ] Application starts without errors: `uvicorn app.main:app`
- [ ] Swagger UI accessible: http://localhost:8000/docs
- [ ] ReDoc accessible: http://localhost:8000/redoc
- [ ] OpenAPI JSON available: http://localhost:8000/api/v1/openapi.json

### Health Check Testing
```bash
# Basic health check
curl http://localhost:8000/health
# Expected: {"status": "healthy", "service": "querybox-core-api"}

# Comprehensive health check
curl http://localhost:8000/api/v1/health/
# Expected: Status of all dependencies

# Readiness probe
curl http://localhost:8000/api/v1/health/ready
# Expected: 200 OK when ready

# Liveness probe  
curl http://localhost:8000/api/v1/health/live
# Expected: 200 OK when alive
```

### CORS Testing
```javascript
// Browser console test
fetch('http://localhost:8000/api/v1/health/', {
    method: 'GET',
    headers: {
        'Origin': 'http://localhost:3000'
    }
})
.then(response => response.json())
.then(data => console.log(data))
// Should succeed without CORS errors
```

### Error Handling Testing
```bash
# 404 Not Found
curl http://localhost:8000/api/v1/nonexistent
# Expected: {"detail": "Not Found", "status_code": 404}

# 405 Method Not Allowed
curl -X DELETE http://localhost:8000/api/v1/health/
# Expected: {"detail": "Method Not Allowed", "status_code": 405}

# 422 Validation Error (future endpoints)
curl -X POST http://localhost:8000/api/v1/upload/ \
    -H "Content-Type: application/json" \
    -d '{"invalid": "data"}'
# Expected: Validation error details
```

### Performance Testing
```bash
# Load test with Apache Bench
ab -n 1000 -c 10 http://localhost:8000/api/v1/health/
# Expected: <100ms average response time

# Concurrent connection test
for i in {1..20}; do 
    curl http://localhost:8000/api/v1/health/ & 
done
# All requests should complete successfully
```

### Expected Behavior
- **Startup Time**: <2 seconds
- **Health Check Response**: <100ms
- **Memory Usage**: <200MB baseline
- **CPU Usage**: <5% idle
- **Concurrent Requests**: Handle 100+ simultaneously

---

## 8. MONITORING & METRICS

### Application Metrics (Prepared)
```python
# Request metrics
request_count = Counter('http_requests_total', 'Total HTTP requests')
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
request_size = Histogram('http_request_size_bytes', 'HTTP request size')
response_size = Histogram('http_response_size_bytes', 'HTTP response size')

# Error metrics
error_count = Counter('http_errors_total', 'Total HTTP errors', ['status_code'])
```

### Health Check Metrics
```json
{
    "timestamp": "2024-11-15T10:30:00Z",
    "status": "healthy",
    "uptime_seconds": 3600,
    "checks": {
        "database": {
            "status": "healthy",
            "response_time_ms": 15,
            "connection_pool_size": 5,
            "active_connections": 2
        },
        "redis": {
            "status": "healthy",
            "response_time_ms": 5,
            "memory_used_mb": 25.5
        },
        "storage": {
            "status": "healthy",
            "writable": true,
            "available_space_gb": 45.2
        }
    }
}
```

### Logging Output
```
# Application startup
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000

# Request logging
INFO:     127.0.0.1:58432 - "GET /api/v1/health/ HTTP/1.1" 200 OK
INFO:     Request completed: method=GET path=/api/v1/health/ status=200 duration=15ms

# Error logging
ERROR:    Exception in ASGI application
ERROR:    Database connection failed: Connection refused
WARNING:  Redis connection failed, continuing without cache
```

### Performance Indicators
- **Request Latency**: p50 < 50ms, p95 < 200ms, p99 < 500ms
- **Throughput**: >1000 requests/second for health checks
- **Error Rate**: <0.1% for client errors, <0.01% for server errors
- **Uptime**: >99.9% availability target

---

## 9. SECURITY CONSIDERATIONS

### CORS Security
```python
# Production CORS configuration
BACKEND_CORS_ORIGINS = [
    "https://app.querybox.dev",      # Production frontend
    "https://staging.querybox.dev",   # Staging frontend
]

# Strict CORS in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=3600,
)
```

### Security Headers
```python
# Security middleware (future)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response
```

### Input Validation
- **URL Parameters**: Validated by FastAPI path parameters
- **Query Parameters**: Type checking and constraints
- **Request Bodies**: Pydantic model validation
- **Headers**: Size and character validation

### API Security Preparation
```python
# API key authentication (prepared for future)
async def verify_api_key(api_key: str = Header(...)):
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Rate limiting preparation
async def check_rate_limit(request: Request):
    # Future: Implement rate limiting logic
    pass
```

---

## 10. CODE PATTERNS & CONVENTIONS

### Project Structure Pattern
```
/backend/
├── app/
│   ├── api/              # API layer
│   │   └── v1/           # Versioned API
│   │       ├── endpoints/# Individual endpoints
│   │       └── router.py # Route aggregation
│   ├── core/             # Core functionality
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   └── main.py          # Application entry
├── tests/                # Test files
└── scripts/              # Utility scripts
```

### Async Pattern
```python
# Async endpoint pattern
@router.get("/example")
async def async_endpoint(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    # Async operations
    cache_value = await redis.get("key")
    
    # Sync database operations (current)
    result = db.query(Model).all()
    
    return {"data": result}
```

### Dependency Injection Pattern
```python
# Dependencies defined in core/deps.py
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_redis():
    return await get_redis_client()

# Used in endpoints
@router.get("/")
async def endpoint(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    pass
```

### Error Handling Pattern
```python
# Consistent error responses
def create_error_response(
    status_code: int,
    detail: str,
    error_type: str = None
) -> JSONResponse:
    content = {
        "detail": detail,
        "status_code": status_code,
        "timestamp": datetime.utcnow().isoformat()
    }
    if error_type:
        content["type"] = error_type
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )
```

### Naming Conventions
- **Endpoints**: Lowercase with hyphens (`/health-check`)
- **Functions**: Snake_case (`get_health_status`)
- **Classes**: PascalCase (`HealthCheckResponse`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_REQUEST_SIZE`)
- **Files**: Snake_case (`health_check.py`)

---

## 11. INTEGRATION POINTS

### FastAPI Integration
```python
# Main application integration
app = FastAPI()
app.include_router(api_router, prefix=settings.API_V1_STR)

# Router integration
api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
```

### Database Integration
```python
# Health check database query
def check_database_health() -> dict:
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        return {"status": "healthy", "connected": True}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
    finally:
        db.close()
```

### Redis Integration
```python
# Health check Redis ping
async def check_redis_health() -> dict:
    try:
        redis = await get_redis()
        await redis.ping()
        return {"status": "healthy", "connected": True}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Middleware Pipeline
```
Request → CORS → Logging → Rate Limit → Auth → Handler → Response
```

### Future Event Integration
```python
# Event publishing preparation
async def publish_event(event_type: str, data: dict):
    # Future: Publish to message queue
    pass

# Event subscription preparation  
async def subscribe_events():
    # Future: Subscribe to message queue
    pass
```

---

## 12. TROUBLESHOOTING GUIDE

### Common Issues and Solutions

#### "Application won't start"
```bash
# Check Python version
python --version  # Should be 3.11+

# Check dependencies
pip install -r requirements.txt

# Check port availability
lsof -i :8000  # Should show nothing

# Start with debug logging
LOG_LEVEL=DEBUG uvicorn app.main:app --reload

# Check for syntax errors
python -m py_compile app/main.py
```

#### "CORS errors in browser"
```javascript
// Browser console shows CORS error
// Check allowed origins
console.log(response.headers.get('Access-Control-Allow-Origin'))

// Solution: Add origin to BACKEND_CORS_ORIGINS
BACKEND_CORS_ORIGINS='["http://localhost:3000","http://yourdomain.com"]'
```

#### "Health check failing"
```bash
# Check individual components
# Database
docker-compose exec postgres pg_isready

# Redis
docker-compose exec redis redis-cli ping

# Storage
ls -la storage/  # Check permissions

# Detailed health check
curl -v http://localhost:8000/api/v1/health/
```

#### "Slow response times"
```bash
# Check worker count
ps aux | grep uvicorn  # Should show multiple workers

# Monitor resource usage
htop  # Check CPU and memory

# Database connection pool
SELECT count(*) FROM pg_stat_activity WHERE datname = 'querybox_core';

# Enable profiling
pip install py-spy
py-spy top -- python -m uvicorn app.main:app
```

### Debug Commands
```bash
# Application logs
uvicorn app.main:app --log-level debug

# HTTP request/response debugging
curl -v http://localhost:8000/api/v1/health/

# FastAPI route inspection
python -c "from app.main import app; print(app.routes)"

# Dependency debugging
python -c "from app.core.deps import get_db; print(get_db)"
```

### Verification Commands
```bash
# Check all routes
curl http://localhost:8000/api/v1/openapi.json | jq '.paths'

# Verify middleware
curl -I http://localhost:8000/api/v1/health/ \
    -H "Origin: http://localhost:3000"
# Should include CORS headers

# Test error handling
curl http://localhost:8000/this/does/not/exist
# Should return proper 404 error

# Load test
wrk -t4 -c100 -d30s http://localhost:8000/api/v1/health/
# Should show stable performance
```

### Log Analysis
```bash
# Parse JSON logs
cat app.log | jq 'select(.level == "ERROR")'

# Count requests by status
cat access.log | awk '{print $9}' | sort | uniq -c

# Find slow requests
cat app.log | jq 'select(.duration_ms > 1000)'

# Monitor real-time
tail -f app.log | jq '.'
```

---

## Summary

Step 2 successfully establishes a production-ready API structure for QueryBox Core, providing:

1. **Complete FastAPI setup** with async support and lifecycle management
2. **Modular routing** with API versioning for future expansion
3. **Comprehensive health checks** monitoring all system dependencies
4. **CORS configuration** enabling secure cross-origin requests
5. **Error handling** with consistent response formats
6. **OpenAPI documentation** with automatic interactive UIs
7. **Foundation for security** with prepared authentication hooks
8. **Monitoring readiness** with health endpoints and logging

This API structure serves as the backbone for all future functionality, providing a solid foundation for document upload, processing, and retrieval endpoints while maintaining high performance and reliability standards.