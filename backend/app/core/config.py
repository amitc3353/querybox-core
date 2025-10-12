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
    
    # Processing
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()