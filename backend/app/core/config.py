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

    # ========================================
    # Cross-Encoder Reranking Configuration (Step 10.2)
    # ========================================
    CROSS_ENCODER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L6-v2"
    CROSS_ENCODER_DEVICE: str = "cpu"  # "cpu" or "cuda" for GPU
    CROSS_ENCODER_BATCH_SIZE: int = 32
    CROSS_ENCODER_MAX_LENGTH: int = 512
    CROSS_ENCODER_NUM_THREADS: int = 4
    CROSS_ENCODER_CACHE_SIZE: int = 1000

    ENABLE_RERANKING: bool = True
    RERANK_TOP_K: int = 50
    RERANK_MIN_TOP_K: int = 10
    RERANK_MAX_TOP_K: int = 200
    RERANK_MIN_CANDIDATES: int = 20

    # ========================================
    # MMR (Maximal Marginal Relevance) Configuration (Step 10.2)
    # ========================================
    ENABLE_MMR: bool = True
    MMR_LAMBDA: float = 0.7  # 0.0 = max diversity, 1.0 = max relevance
    MMR_MIN_LAMBDA: float = 0.0
    MMR_MAX_LAMBDA: float = 1.0
    MMR_MIN_CANDIDATES: int = 10

    # ========================================
    # Advanced Deduplication Configuration (Step 10.2)
    # ========================================
    ENABLE_ADVANCED_DEDUP: bool = True
    ENABLE_SEMANTIC_DEDUP: bool = True
    SEMANTIC_DEDUP_THRESHOLD: float = 0.95
    SEMANTIC_DEDUP_MIN_THRESHOLD: float = 0.80
    SEMANTIC_DEDUP_MAX_THRESHOLD: float = 0.99
    CONTENT_HASH_ALGORITHM: str = "sha256"

    # ========================================
    # Reranking Pipeline Configuration (Step 10.2)
    # ========================================
    RERANKING_STAGE_1_ENABLED: bool = True  # Cross-encoder
    RERANKING_STAGE_2_ENABLED: bool = True  # Deduplication
    RERANKING_STAGE_3_ENABLED: bool = True  # MMR
    RERANKING_TIMEOUT_MS: int = 3000
    RERANKING_MAX_RETRIES: int = 1

    # ========================================
    # Model Caching & Loading (Step 10.2)
    # ========================================
    MODEL_CACHE_DIR: str = "./models/cross_encoder"
    MODEL_DOWNLOAD_ON_STARTUP: bool = True
    MODEL_LAZY_LOADING: bool = False
    MODEL_WARMUP_ON_STARTUP: bool = True

    # ========================================
    # Rate Limiting - Reranking (Step 10.2)
    # ========================================
    RATE_LIMIT_RERANKING: str = "10/minute"
    MAX_CONCURRENT_RERANKING: int = 5

    # ========================================
    # Monitoring - Reranking (Step 10.2)
    # ========================================
    RERANKING_LOG_LEVEL: str = "INFO"
    LOG_SLOW_RERANKING: bool = True
    SLOW_RERANKING_THRESHOLD_MS: int = 300
    ENABLE_RERANKING_METRICS: bool = True
    TRACK_MMR_DIVERSITY: bool = True
    TRACK_DEDUP_STATS: bool = True

    # ========================================
    # A/B Testing - Reranking (Step 10.2)
    # ========================================
    RERANKING_AB_TEST_ENABLED: bool = False
    RERANKING_AB_TEST_RATIO: float = 0.5

    # ========================================
    # Citation Extraction Configuration (Step 10.3)
    # ========================================
    ENABLE_CITATIONS: bool = True
    CITATION_LIMIT_DEFAULT: int = 3
    CITATION_LIMIT_MAX: int = 5
    EXPOSE_ABSOLUTE_POSITIONS: bool = False  # Security: use relative positions in production

    # SpaCy NLP Configuration
    SPACY_MODEL_NAME: str = "en_core_web_sm"
    SPACY_DISABLE_PIPES: List[str] = ["ner", "parser"]  # Disable for performance

    # Citation Cache Configuration
    CITATION_CACHE_ENABLED: bool = True
    CITATION_CACHE_TTL_SECONDS: int = 900  # 15 minutes

    # Citation Extraction Performance
    CITATION_TIMEOUT_MS: int = 200
    CITATION_BATCH_SIZE: int = 10

    # Citation Scoring Thresholds
    CITATION_MIN_CONFIDENCE: float = 0.3
    CITATION_MIN_WORD_COUNT: int = 10
    CITATION_MAX_WORD_COUNT: int = 50

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