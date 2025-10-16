from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from app.models.document import StorageProviderEnum
from app.models.types import GUID, JSON
import uuid


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    
    # Primary identifier
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Reference to parent document
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Version information
    version_number = Column(Integer, nullable=False)
    user_assigned_label = Column(String(100))
    version_note = Column(Text)
    
    # File metadata for this version
    file_size = Column(BigInteger, nullable=False)
    checksum = Column(String(64), nullable=False, unique=True)
    mime_type = Column(String(100), nullable=False)
    file_extension = Column(String(10), nullable=False)
    
    # Storage for this specific version
    storage_provider = Column(
        Enum(StorageProviderEnum, name="storage_provider_enum"),
        nullable=False
    )
    storage_path = Column(Text, nullable=False)
    storage_bucket = Column(String(100))
    storage_region = Column(String(50))
    
    # Version-specific metadata
    version_metadata = Column(JSON, default={})
    
    # Version lifecycle
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by_user_id = Column(GUID)
    is_latest_version = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    document = relationship("Document", back_populates="versions")