from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from app.models.types import GUID
import uuid
# Note: pgvector extension types will be added when we implement vector search


class Embedding(Base):
    __tablename__ = "embeddings"
    
    # Primary identifier
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Reference to source document
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Chunk information
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_tokens = Column(Integer)
    
    # Note: embedding vector column will be added when pgvector is configured
    # embedding = Column(Vector(1536))  # OpenAI ada-002 dimension
    
    # Chunk metadata
    start_position = Column(Integer)
    end_position = Column(Integer)
    page_number = Column(Integer)
    
    # Processing metadata
    embedding_model = Column(String(100), nullable=False, default='text-embedding-ada-002')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="embeddings")