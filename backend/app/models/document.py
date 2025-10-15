from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, Text, Enum, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum
import uuid


class StorageProviderEnum(str, enum.Enum):
    LOCAL = "local"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"


class DocumentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStageEnum(str, enum.Enum):
    UPLOAD = "upload"
    VALIDATION = "validation"
    EXTRACTION = "extraction"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETION = "completion"


class StageStatusEnum(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Document(Base):
    __tablename__ = "documents"
    
    # Primary identifier
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Document naming
    document_name = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    alternate_name = Column(String(255))
    
    # File metadata
    mime_type = Column(String(100), nullable=False)
    file_extension = Column(String(10), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    checksum = Column(String(64), nullable=False, unique=True)
    
    # Storage configuration
    storage_provider = Column(
        Enum(StorageProviderEnum, name="storage_provider_enum"),
        nullable=False,
        default=StorageProviderEnum.LOCAL
    )
    storage_path = Column(Text, nullable=False)
    storage_bucket = Column(String(100))
    storage_region = Column(String(50))
    
    # Document status
    status = Column(
        Enum(DocumentStatusEnum, name="document_status_enum"),
        nullable=False,
        default=DocumentStatusEnum.PENDING
    )
    
    # Versioning
    is_versioned_file = Column(Boolean, nullable=False, default=False)
    current_version = Column(Integer, nullable=False, default=1)
    mutation_count = Column(Integer, nullable=False, default=1)
    
    # Document metadata
    document_metadata = Column(JSONB, default={})
    tags = Column(ARRAY(Text))
    
    # Processing timestamps
    last_extraction_at = Column(DateTime(timezone=True))
    last_embedding_at = Column(DateTime(timezone=True))
    last_indexed_at = Column(DateTime(timezone=True))
    
    # Storage access tracking
    last_accessed_at = Column(DateTime(timezone=True))
    access_count = Column(Integer, nullable=False, default=0)
    
    # Storage optimization
    storage_size = Column(BigInteger)  # Actual size on disk (may differ from file_size due to compression)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Soft delete
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True))
    deleted_by_user_id = Column(UUID(as_uuid=True))
    
    # Processing flags
    is_dirty = Column(Boolean, nullable=False, default=False)
    processing_reason = Column(Text)
    
    # Relationships
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    processing_status = relationship("ProcessingStatus", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("Embedding", back_populates="document", cascade="all, delete-orphan")
    queue_items = relationship("ProcessingQueue", back_populates="document", cascade="all, delete-orphan")