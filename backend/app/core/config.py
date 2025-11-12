from pydantic_settings import BaseSettings
from pydantic import ConfigDict
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

    # ========================================
    # OpenAI Embedding Configuration (Phase 3)
    # ========================================
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"  # or text-embedding-3-large
    OPENAI_EMBEDDING_DIMENSION: int = 1536  # 1536 for small, 3072 for large
    OPENAI_EMBEDDING_BATCH_SIZE: int = 100  # Number of texts per API call

    # ========================================
    # BGE-M3 Embedding Configuration (Local)
    # ========================================
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_MAX_TOKENS: int = 8192
    EMBEDDING_DEVICE: str = "auto"  # "cuda", "cpu", or "auto"
    EMBEDDING_BATCH_SIZE: int = 100
    TRANSFORMERS_CACHE: str = os.path.expanduser("~/.cache/huggingface")
    HF_HOME: str = os.path.expanduser("~/.cache/huggingface")

    # Query Embedding Caching (Performance Optimization)
    EMBEDDING_CACHE_ENABLED: bool = True  # Enable Redis caching for query embeddings
    EMBEDDING_CACHE_TTL_SECONDS: int = 1800  # 30 minutes TTL for cached embeddings

    # ========================================
    # Modular Provider Configuration (Enables swapping components via config)
    # ========================================

    # Parser Selection (Options: "docling", "mineru", "unstructured", "smart")
    PARSER_PRIMARY: str = "docling"  # Primary parser for document extraction

    # Embedding Provider Selection (Options: "bge", "bge-m3", "openai", "cohere", "voyage")
    EMBEDDING_PROVIDER: str = "bge-m3"  # Embedding provider for vector generation

    # Vector Store Selection (Options: "pgvector", "qdrant", "lancedb", "weaviate")
    VECTOR_STORE: str = "pgvector"  # Vector database for similarity search

    # LLM Provider Selection (Options: "ollama", "openrouter", "openai", "claude")
    LLM_PROVIDER: str = "ollama"  # LLM provider for answer generation

    # pgvector Configuration
    PGVECTOR_INDEX_TYPE: str = "hnsw"
    PGVECTOR_HNSW_M: int = 16
    PGVECTOR_HNSW_EF_CONSTRUCTION: int = 64
    PGVECTOR_MIN_VECTORS_FOR_INDEX: int = 1000

    # ========================================
    # Qdrant Vector Store Configuration (Phase 4)
    # ========================================

    # Qdrant Feature Flag
    # Set to True: Enables parallel indexing (writes to both pgvector + Qdrant) and smart fallback
    # Set to False ONLY when:
    #   - Initial development/testing before Qdrant is ready
    #   - Troubleshooting Qdrant connection issues
    #   - Temporarily disabling Qdrant during infrastructure changes
    #   - Running on resource-constrained environments (save memory/CPU)
    ENABLE_QDRANT: bool = True  # Enable Qdrant parallel indexing and smart fallback

    # Qdrant Connection Settings
    QDRANT_URL: str = "http://localhost:6333"  # Local Docker or Cloud URL
    QDRANT_API_KEY: Optional[str] = None  # Required for Cloud, empty for local Docker
    QDRANT_COLLECTION: str = "querybox_embeddings"  # Collection name
    QDRANT_PREFER_GRPC: bool = False  # Use gRPC instead of HTTP (faster, requires port 6334)

    # Qdrant Performance Tuning
    QDRANT_BATCH_SIZE: int = 500  # Vectors per batch insert (100-1000)
    QDRANT_TIMEOUT: int = 5  # Connection timeout in seconds
    QDRANT_SEARCH_TIMEOUT: int = 2  # Search operation timeout in seconds
    QDRANT_PARALLEL_UPLOAD: bool = True  # Enable parallel batch uploads

    # Circuit Breaker Configuration (Automatic fallback to pgvector if Qdrant unavailable)
    QDRANT_CIRCUIT_FAILURE_THRESHOLD: int = 5  # Failures before opening circuit
    QDRANT_CIRCUIT_COOLDOWN: int = 30  # Seconds before retry after circuit opens
    QDRANT_CIRCUIT_HALF_OPEN_REQUESTS: int = 3  # Test requests in half-open state

    # HNSW Index Configuration (Advanced - affects search quality vs speed)
    QDRANT_HNSW_M: int = 16  # Connections per layer (8-64, higher = better recall, more memory)
    QDRANT_HNSW_EF_CONSTRUCT: int = 100  # Construction-time search depth (64-256)
    QDRANT_HNSW_EF_SEARCH: int = 64  # Runtime search depth (16-512, higher = better recall, slower)
    QDRANT_ON_DISK: bool = False  # Store vectors on disk (for >1M vectors, saves RAM)

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

    # ========================================
    # Ollama LLM Configuration (Step 11.1)
    # ========================================
    # Available Models: tinyllama:latest (637MB, active), qwen2:7b (4.4GB, requires more RAM)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "tinyllama"  # Active model (optimized for limited memory)
    OLLAMA_TIMEOUT: int = 60  # Timeout in seconds
    OLLAMA_TEMPERATURE: float = 0.2  # Default temperature for answer generation
    OLLAMA_MAX_TOKENS: int = 2000  # Maximum tokens for completion
    OLLAMA_CONTEXT_TOKENS: int = 6000  # Maximum tokens for context passages

    # ========================================
    # OpenRouter LLM Configuration (Phase 3)
    # ========================================
    # OpenRouter provides access to multiple LLMs (GPT, Claude, Gemini, Llama)
    # Sign up at: https://openrouter.ai/
    OPENROUTER_API_KEY: Optional[str] = None  # Required for OpenRouter (sk-or-v1-...)
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"  # Default model (fast + affordable)
    OPENROUTER_APP_NAME: str = "QueryBox Core"  # App name (for OpenRouter rankings)
    OPENROUTER_SITE_URL: Optional[str] = None  # Optional site URL (for rankings)

    # Available OpenRouter Models:
    # - openai/gpt-4o-mini (recommended: $0.15/$0.60 per 1M tokens, 128k context)
    # - openai/gpt-4o ($2.50/$10.00 per 1M tokens, 128k context, highest quality)
    # - anthropic/claude-3.5-sonnet ($3/$15 per 1M tokens, 200k context)
    # - anthropic/claude-3-haiku ($0.25/$1.25 per 1M tokens, 200k context, fastest)
    # - google/gemini-2.0-flash-exp (FREE during preview, 1M context)
    # - meta-llama/llama-3.1-405b ($2.70 per 1M tokens, 128k context)

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

    # ========================================
    # Chain-of-Verification Configuration (Step 11.2)
    # ========================================

    # Verification Level (Controls all verification parameters)
    # Options: VERY_HIGH, HIGH, MEDIUM, LOW, VERY_LOW
    # - VERY_HIGH: Maximum strictness for legal/medical (>98% accuracy)
    # - HIGH: Production default (>95% accuracy) - RECOMMENDED
    # - MEDIUM: Balanced for internal tools (>90% accuracy)
    # - LOW: Lenient for exploratory queries (>85% accuracy)
    # - VERY_LOW: Minimal verification, speed-focused (>80% accuracy)
    VERIFICATION_LEVEL: str = "HIGH"

    # Verification Feature Flags
    VERIFICATION_ENABLED: bool = True  # Global enable/disable
    VERIFICATION_DEFAULT_ON: bool = False  # Default for API requests (opt-in)

    # Feature-specific flags
    ENABLE_QUOTE_MATCHING: bool = True
    ENABLE_VERIFICATION_QUESTIONS: bool = True
    ENABLE_HALLUCINATION_DETECTION: bool = True
    ENABLE_CONTRADICTION_CHECK: bool = True  # LLM-based, can disable for speed

    # Performance Tuning
    VERIFICATION_TIMEOUT_SECONDS: int = 120  # Total verification timeout
    VERIFICATION_QUESTION_TIMEOUT: int = 60  # Per-question timeout
    VERIFICATION_MAX_QUESTIONS: int = 10  # Prevent DOS
    VERIFICATION_MAX_PROPOSITIONS: int = 10  # Limit proposition count

    # Quote Matching Configuration
    QUOTE_SIMILARITY_THRESHOLD: float = 0.85  # Fuzzy match threshold (0-1)
    QUOTE_MAX_MATCHES_PER_PROPOSITION: int = 5  # Top-k matches to store
    QUOTE_MATCHING_TIMEOUT_MS: int = 100  # Per-proposition timeout

    # Hallucination Detection
    HALLUCINATION_PROBABILITY_THRESHOLD: float = 0.3  # Flag answers above this
    HALLUCINATION_AUTO_REMOVE_THRESHOLD: float = 0.7  # Auto-remove claims above this
    HALLUCINATION_CONTRADICTION_CHECK: bool = True  # Enable LLM contradiction check

    # Caching (3-level strategy)
    VERIFICATION_CACHE_TTL_SECONDS: int = 3600  # L1: 1 hour
    QUOTE_MATCH_CACHE_TTL_SECONDS: int = 86400  # L2: 24 hours
    VERIFICATION_QUESTION_CACHE_TTL_SECONDS: int = 604800  # L3: 1 week

    # Rate Limiting - Verification
    VERIFICATION_RATE_LIMIT_PER_MINUTE: int = 5  # Verified answers per minute
    VERIFICATION_RATE_LIMIT_PER_HOUR: int = 50  # Hourly limit

    # Resource Limits
    MAX_CONCURRENT_VERIFICATIONS: int = 10  # Redis-based semaphore
    MAX_CONCURRENT_QUOTE_MATCHES: int = 20  # Per verification
    MAX_CONCURRENT_LLM_CALLS: int = 5  # Per verification
    MAX_VERIFICATION_MEMORY_MB: int = 100  # Per request

    # Monitoring - Verification
    ENABLE_VERIFICATION_METRICS: bool = True
    LOG_VERIFICATION_RESULTS: bool = True
    TRACK_HALLUCINATION_TRENDS: bool = True

    # ========================================
    # Better Stack (Logtail) Logging Configuration (Step 13.5)
    # ========================================
    LOGTAIL_SOURCE_TOKEN: Optional[str] = None
    LOGTAIL_HOST: str = "in.logs.betterstack.com"  # US endpoint (default) or EU: s{source_id}.eu-nbg-2.betterstackdata.com
    LOGTAIL_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # ========================================
    # Docling Parser Optimization (Phase 2.1)
    # ========================================

    # Device Selection
    DOCLING_DEVICE: str = "auto"  # Options: auto, cpu, cuda, mps
    DOCLING_ENABLE_MPS: bool = False  # Apple Silicon GPU (experimental, disabled due to EasyOCR compatibility)
    DOCLING_NUM_THREADS: int = 8  # CPU threads for parallel processing

    # Parallel Processing (ThreadedPdfPipeline)
    DOCLING_USE_THREADED_PIPELINE: bool = True  # Use ThreadedPdfPipeline (5-stage parallel processing)
    DOCLING_OCR_BATCH_SIZE: int = 4  # EasyOCR batch size: 4 for CPU, 64 for GPU
    DOCLING_LAYOUT_BATCH_SIZE: int = 4  # Layout model batch size: 4 for CPU, 64 for GPU
    DOCLING_TABLE_BATCH_SIZE: int = 4  # Table extraction batch size: 4 for CPU, 64 for GPU

    # Model Loading Strategy
    DOCLING_EAGER_INIT: bool = True  # Initialize models on service startup (avoid first-request latency)
    DOCLING_WARMUP_ON_STARTUP: bool = True  # Warm up models with dummy PDF on startup

    # Large PDF Handling (100+ pages)
    DOCLING_PAGE_BATCH_SIZE: int = 50  # Pages per batch for memory-efficient processing
    DOCLING_MAX_PAGES_MEMORY_THRESHOLD: int = 100  # Switch to batch mode above this page count

    # Performance Tuning
    DOCLING_ENABLE_PERFORMANCE_LOGGING: bool = True  # Log detailed performance metrics
    DOCLING_LOG_GPU_MEMORY: bool = True  # Log GPU memory usage (if GPU available)

    # ========================================
    # Vision API Configuration (Phase 2.4)
    # ========================================
    # GPT-4o-mini Vision API for chart/graph interpretation

    # Enable/Disable Vision Processing
    ENABLE_VISION_PARSING: bool = True  # Master switch for vision API
    VISION_PARSE_IMAGES_IN_DOCS: bool = True  # Extract and interpret images from documents

    # Vision API Model Selection
    VISION_API_MODEL: str = "gpt-4o-mini"  # OpenAI vision model (gpt-4o-mini, gpt-4o, gpt-4-vision-preview)
    VISION_API_MAX_TOKENS: int = 500  # Max tokens for vision API response
    VISION_API_TEMPERATURE: float = 0.2  # Lower = more deterministic

    # Image Processing
    VISION_API_MAX_IMAGES_PER_DOC: int = 20  # Max images to process per document (cost control)
    VISION_IMAGE_MAX_SIZE: int = 2048  # Max image dimension (pixels) for Vision API
    VISION_IMAGE_QUALITY: str = "auto"  # Options: "auto", "low", "high"

    # Cost Tracking
    VISION_ENABLE_COST_TRACKING: bool = True  # Track API usage and costs
    VISION_COST_PER_IMAGE: float = 0.0005  # Est. cost per image with gpt-4o-mini
    VISION_MAX_COST_PER_DOC: float = 0.10  # Max spend per document ($0.10 = 200 images)
    VISION_WARN_COST_THRESHOLD: float = 0.05  # Warn if cost exceeds this per doc

    # Performance
    VISION_API_TIMEOUT_SECONDS: int = 30  # Timeout for vision API calls
    VISION_API_MAX_RETRIES: int = 2  # Number of retries on failure
    VISION_ENABLE_CACHING: bool = True  # Cache vision results (avoid reprocessing)
    VISION_CACHE_TTL_SECONDS: int = 86400  # 24 hours cache

    # ========================================
    # Smart Router Configuration (Phase 2.3)
    # ========================================
    # Intelligent document routing that automatically selects optimal parser(s)
    # based on document characteristics (images, tables, complexity)

    # Enable/Disable Smart Router
    SMART_ROUTER_ENABLED: bool = True  # Master switch for smart routing

    # Document Analysis Thresholds
    SMART_ROUTER_IMAGE_THRESHOLD: int = 3  # Min images to trigger Vision API
    SMART_ROUTER_MIN_IMAGE_SIZE_BYTES: int = 10000  # Ignore images smaller than this (10KB)
    SMART_ROUTER_DETECT_SCANNED_PDF: bool = True  # Auto-detect scanned/image-only PDFs
    SMART_ROUTER_SCANNED_TEXT_THRESHOLD: int = 100  # Chars per page to consider "scanned" (<100)

    # Routing Strategy
    SMART_ROUTER_PREFER_VISION_FOR_CHARTS: bool = True  # Use Vision when images detected
    SMART_ROUTER_ALWAYS_USE_DOCLING: bool = True  # Always extract text with Docling
    SMART_ROUTER_ENABLE_PARALLEL_PARSING: bool = False  # Parse Docling + Vision concurrently (experimental)

    # Cost Controls for Vision in Smart Router
    SMART_ROUTER_MAX_IMAGES_FOR_VISION: int = 10  # Override Vision's default per-doc limit
    SMART_ROUTER_SKIP_VISION_IF_EXPENSIVE: bool = True  # Skip Vision if >max images
    SMART_ROUTER_SKIP_VISION_IF_NO_TEXT: bool = False  # Process image-only docs with Vision

    # Result Merging Strategy
    SMART_ROUTER_CONFIDENCE_WEIGHT_TEXT: float = 0.7  # Weight for Docling confidence
    SMART_ROUTER_CONFIDENCE_WEIGHT_VISION: float = 0.3  # Weight for Vision confidence
    SMART_ROUTER_INTERLEAVE_VISION_TEXT: bool = False  # Inject descriptions at positions vs append
    SMART_ROUTER_VISION_TEXT_SEPARATOR: str = "\n\n---\n\n## Chart Interpretations\n\n"  # Separator for Vision text

    # Fallback Behavior
    SMART_ROUTER_FALLBACK_TO_DOCLING: bool = True  # Use Docling if Vision fails/disabled
    SMART_ROUTER_FAIL_IF_ALL_PARSERS_FAIL: bool = True  # Return error if all parsers fail

    # Performance & Logging
    SMART_ROUTER_LOG_ROUTING_DECISIONS: bool = True  # Log which parser(s) selected
    SMART_ROUTER_LOG_ANALYSIS_RESULTS: bool = True  # Log document analysis details
    SMART_ROUTER_ENABLE_METRICS: bool = True  # Track routing statistics

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra environment variables not defined in Settings
    )

settings = Settings()