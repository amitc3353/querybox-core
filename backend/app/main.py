from fastapi import FastAPI, Response
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
    Health check endpoint - Day 3, Step 5
    Enhanced with database, Redis, and storage checks
    """
    from datetime import datetime, timezone
    import os
    from pathlib import Path
    
    health_status = {
        "status": "healthy",
        "service": "querybox-core-api",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage_path": settings.STORAGE_PATH,
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
        "checks": {}
    }
    
    # Check database
    try:
        from app.db.database import test_connection
        db_healthy = test_connection()
        health_status["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "connection": db_healthy
        }
        if not db_healthy:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        from app.core.redis import get_redis
        redis_client = await get_redis()
        await redis_client.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "connection": True
        }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e),
            "connection": False
        }
        # Don't degrade status for Redis as it's optional for now
    
    # Check storage system
    try:
        from app.services.storage.local import LocalStorageProvider
        storage_provider = LocalStorageProvider()
        
        # Check storage directory exists and is writable
        storage_path = Path(settings.STORAGE_PATH)
        storage_exists = storage_path.exists()
        storage_writable = os.access(storage_path, os.W_OK) if storage_exists else False
        
        # Get disk space
        stat = os.statvfs(storage_path) if storage_exists else None
        if stat:
            total_bytes = stat.f_blocks * stat.f_frsize
            # Use f_bavail for cross-platform compatibility (macOS uses f_bavail, Linux has both)
            available_bytes = stat.f_bavail * stat.f_frsize
            used_bytes = total_bytes - available_bytes
            usage_percentage = (used_bytes / total_bytes) * 100 if total_bytes > 0 else 0
            
            health_status["checks"]["storage"] = {
                "status": "healthy",
                "path_exists": storage_exists,
                "path_writable": storage_writable,
                "disk_space": {
                    "total_gb": round(total_bytes / (1024**3), 2),
                    "used_gb": round(used_bytes / (1024**3), 2),
                    "available_gb": round(available_bytes / (1024**3), 2),
                    "usage_percentage": round(usage_percentage, 2)
                }
            }
            
            # Check if disk space is low
            if usage_percentage > 90:
                health_status["checks"]["storage"]["status"] = "critical"
                health_status["status"] = "critical"
            elif usage_percentage > 80:
                health_status["checks"]["storage"]["status"] = "warning"
                if health_status["status"] == "healthy":
                    health_status["status"] = "warning"
        else:
            health_status["checks"]["storage"] = {
                "status": "unhealthy",
                "path_exists": storage_exists,
                "path_writable": storage_writable,
                "error": "Storage path not accessible"
            }
            health_status["status"] = "degraded"
        
        # Test basic storage operations
        try:
            test_path = "_health_check_test.txt"
            test_content = b"health check test"
            
            await storage_provider.save_file(test_content, test_path)
            retrieved_content = await storage_provider.get_file(test_path)
            await storage_provider.delete_file(test_path)
            
            operation_success = retrieved_content == test_content
            health_status["checks"]["storage"]["operations"] = {
                "save": True,
                "retrieve": True,
                "delete": True,
                "test_successful": operation_success
            }
            
            if not operation_success:
                health_status["checks"]["storage"]["status"] = "degraded"
                if health_status["status"] == "healthy":
                    health_status["status"] = "degraded"
                    
        except Exception as e:
            health_status["checks"]["storage"]["operations"] = {
                "error": str(e),
                "test_successful": False
            }
            health_status["checks"]["storage"]["status"] = "unhealthy"
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["checks"]["storage"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint - Day 3, Step 5
    Returns metrics in Prometheus format for monitoring
    """
    from app.monitoring.storage_metrics import get_metrics, get_metrics_content_type
    
    metrics_data = get_metrics()
    return Response(
        content=metrics_data,
        media_type=get_metrics_content_type()
    )