from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "QueryBox Core"
    
    # Database
    DATABASE_URL: str = "postgresql://querybox:querybox_dev_2024@localhost:5432/querybox_core"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Storage
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "querybox-documents"
    
    # AI/Embeddings
    OPENAI_API_KEY: Optional[str] = None

    # BGE-M3 Embedding Configuration
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_MAX_TOKENS: int = 8192
    EMBEDDING_DEVICE: str = "auto"  # "cuda", "cpu", or "auto"
    EMBEDDING_BATCH_SIZE: int = 100
    TRANSFORMERS_CACHE: str = os.path.expanduser("~/.cache/huggingface")
    HF_HOME: str = os.path.expanduser("~/.cache/huggingface")

    # pgvector Configuration
    PGVECTOR_INDEX_TYPE: str = "hnsw"
    PGVECTOR_HNSW_M: int = 16
    PGVECTOR_HNSW_EF_CONSTRUCTION: int = 64
    PGVECTOR_MIN_VECTORS_FOR_INDEX: int = 1000

    # Vector Search Configuration (Step 9.3)
    VECTOR_SEARCH_TIMEOUT_MS: int = 500
    VECTOR_SEARCH_MAX_LIMIT: int = 100
    VECTOR_SEARCH_DEFAULT_LIMIT: int = 10
    VECTOR_SEARCH_MIN_SIMILARITY: float = 0.0

    # BM25 Search Configuration (Step 10.1)
    BM25_K1: float = 1.5  # Term frequency saturation parameter
    BM25_B: float = 0.75  # Length normalization parameter

    # RRF (Reciprocal Rank Fusion) Configuration (Step 10.1)
    RRF_K: int = 60  # RRF constant (40-100)
    RRF_KEYWORD_WEIGHT: float = 0.5  # Default weight for keyword results
    RRF_VECTOR_WEIGHT: float = 0.5  # Default weight for vector results

    # Hybrid Search Configuration (Step 10.1)
    HYBRID_KEYWORD_TOP_K: int = 100  # Candidates from keyword search
    HYBRID_VECTOR_TOP_K: int = 100  # Candidates from vector search
    HYBRID_ENABLE_PARALLEL: bool = True  # Enable parallel search execution

    # Security
    API_KEY: str = "dev-key-12345"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # File limits
    MAX_FILE_SIZE: int = 30 * 1024 * 1024  # 30MB
    LARGE_FILE_THRESHOLD: int = 10 * 1024 * 1024  # 10MB
    
    # Local storage (Week 1)
    STORAGE_PATH: str = "storage"
    
    # Allowed file extensions (from CLAUDE.md)
    ALLOWED_EXTENSIONS: List[str] = [
        ".pdf", ".docx", ".xlsx", ".pptx", 
        ".txt", ".md", ".html", ".csv", 
        ".json", ".xml"
    ]
    
    # Processing / Task Queue
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    TASK_QUEUE_BACKEND: str = "celery"  # "celery" or "kafka" (future)

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()