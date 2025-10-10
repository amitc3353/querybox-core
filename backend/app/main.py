from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.core.config import settings
from app.api.v1.router import api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for the application
    """
    logger.info("Starting QueryboxCore API...")
    
    # Initialize Redis connection
    try:
        from app.core.redis import init_redis
        await init_redis()
    except Exception as e:
        logger.warning(f"Redis initialization failed: {e}. Continuing without Redis.")
    
    yield
    
    # Cleanup
    logger.info("Shutting down QueryboxCore API...")
    try:
        from app.core.redis import close_redis
        await close_redis()
    except Exception:
        pass


app = FastAPI(
    title="QueryBox Core API",
    description="High-performance document processing and retrieval system",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": "QueryBox Core API", "status": "running"}

@app.get("/health")
async def health():
    """
    Health check endpoint - Day 1, Step 2
    Enhanced with database and Redis checks
    """
    health_status = {
        "status": "healthy",
        "service": "querybox-core-api",
        "version": "1.0.0",
        "storage_path": settings.STORAGE_PATH,
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
        "checks": {}
    }
    
    # Check database
    try:
        from app.db.database import test_connection
        db_healthy = test_connection()
        health_status["checks"]["database"] = "healthy" if db_healthy else "unhealthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        from app.core.redis import get_redis
        redis_client = await get_redis()
        await redis_client.ping()
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
        # Don't degrade status for Redis as it's optional for now
    
    return health_status