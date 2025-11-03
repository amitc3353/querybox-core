from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from app.models.types import GUID, JSON, StringArray
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
    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    
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
        Enum(StorageProviderEnum, name="storage_provider_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=StorageProviderEnum.LOCAL
    )
    storage_path = Column(Text, nullable=False)
    storage_bucket = Column(String(100))
    storage_region = Column(String(50))
    
    # Document status
    status = Column(
        Enum(DocumentStatusEnum, name="document_status_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DocumentStatusEnum.PENDING
    )
    
    # Versioning
    is_versioned_file = Column(Boolean, nullable=False, default=False)
    current_version = Column(Integer, nullable=False, default=1)
    mutation_count = Column(Integer, nullable=False, default=1)
    
    # Document metadata (Python attribute is 'document_metadata', DB column is 'metadata')
    document_metadata = Column('metadata', JSON, default={})
    tags = Column(StringArray)
    
    # Processing timestamps
    last_extraction_at = Column(DateTime(timezone=True))
    last_embedding_at = Column(DateTime(timezone=True))
    last_indexed_at = Column(DateTime(timezone=True))

    # Access tracking
    access_count = Column(Integer, nullable=False, default=0)
    last_accessed_at = Column(DateTime(timezone=True))

    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Soft delete
    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True))
    deleted_by_user_id = Column(GUID)
    
    # Processing flags
    is_dirty = Column(Boolean, nullable=False, default=False)
    processing_reason = Column(Text)
    
    # Relationships
    # Note: lazy="select" prevents automatic loading during delete operations
    # This avoids schema mismatch errors when document_versions table schema is out of sync
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan", lazy="select")
    document_text = relationship("DocumentText", back_populates="document", uselist=False, cascade="all, delete-orphan")
    processing_status = relationship("ProcessingStatus", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("Embedding", back_populates="document", cascade="all, delete-orphan")
    queue_items = relationship("ProcessingQueue", back_populates="document", cascade="all, delete-orphan")

    # ========================================================================
    # HELPER PROPERTIES (Step 7 Section 2)
    # ========================================================================

    @property
    def is_processing(self) -> bool:
        """
        Check if document is currently being processed

        Returns:
            True if status is PROCESSING, False otherwise

        Usage:
            if document.is_processing:
                raise HTTPException(409, "Cannot delete while processing")
        """
        return self.status == DocumentStatusEnum.PROCESSING

    @property
    def file_size_mb(self) -> float:
        """
        Get file size in megabytes

        Returns:
            File size in MB, rounded to 2 decimal places

        Usage:
            response_data["file_size_mb"] = document.file_size_mb
        """
        return round(self.file_size / (1024 * 1024), 2)

    # ========================================================================
    # SERIALIZATION METHODS
    # ========================================================================

    def to_dict(self) -> dict:
        """
        Serialize document to dictionary for API responses

        Returns a complete dictionary with all document fields including:
        - Core identification (id, names)
        - File metadata (mime_type, file_size, file_size_mb)
        - Storage information (provider, path, bucket, region)
        - Status and versioning
        - Document metadata (JSONB)
        - Tags (array)
        - Processing timestamps
        - Access tracking
        - Audit trail
        - Soft delete flags

        Returns:
            Dictionary with all document fields serialized

        Usage:
            document_dict = document.to_dict()
            return DocumentResponse(**document_dict)

        Note:
            - UUID fields are converted to strings
            - Enum values are converted to their string values
            - Datetime objects are converted to ISO 8601 strings
            - None values are preserved (not filtered out)
        """
        return {
            # Core identification
            "id": str(self.id),
            "document_name": self.document_name,
            "original_name": self.original_name,
            "alternate_name": self.alternate_name,

            # File metadata
            "mime_type": self.mime_type,
            "file_extension": self.file_extension,
            "file_size": self.file_size,
            "file_size_mb": self.file_size_mb,  # Computed property
            "checksum": self.checksum,

            # Storage information
            "storage_provider": self.storage_provider.value,
            "storage_path": self.storage_path,
            "storage_bucket": self.storage_bucket,
            "storage_region": self.storage_region,

            # Status and versioning
            "status": self.status.value,
            "is_versioned_file": self.is_versioned_file,
            "current_version": self.current_version,
            "mutation_count": self.mutation_count,

            # Metadata
            "metadata": self.document_metadata or {},
            "tags": self.tags or [],

            # Processing timestamps
            "last_extraction_at": self.last_extraction_at.isoformat() if self.last_extraction_at else None,
            "last_embedding_at": self.last_embedding_at.isoformat() if self.last_embedding_at else None,
            "last_indexed_at": self.last_indexed_at.isoformat() if self.last_indexed_at else None,

            # Audit trail
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,

            # Soft delete
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "deleted_by_user_id": str(self.deleted_by_user_id) if self.deleted_by_user_id else None,

            # Processing flags
            "is_dirty": self.is_dirty,
            "processing_reason": self.processing_reason
        }

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"<Document(id={self.id}, "
            f"name='{self.document_name}', "
            f"status={self.status.value}, "
            f"size={self.file_size_mb}MB)>"
        )