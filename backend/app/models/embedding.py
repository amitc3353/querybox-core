from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Float, Boolean, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.db.database import Base
from app.models.types import GUID
import uuid


# Use JSONB for PostgreSQL, JSON for other databases (including SQLite for tests)
def get_json_type():
    """Return appropriate JSON type based on database dialect"""
    from sqlalchemy import inspect
    from app.db.database import engine

    try:
        dialect_name = engine.dialect.name
        if dialect_name == 'postgresql':
            return JSONB
        else:
            return JSON
    except:
        # Default to JSON for safety (works with SQLite)
        return JSON


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

    # Embedding vector (1536 dimensions for OpenAI ada-002 / BGE-M3)
    embedding = Column(Vector(1536))

    # Chunk metadata
    start_position = Column(Integer)
    end_position = Column(Integer)
    page_number = Column(Integer)

    # Enhanced metadata (Step 9.1)
    section_heading = Column(String(500))
    subsection_heading = Column(String(500))
    chunk_type = Column(String(50), default='paragraph')  # paragraph, list, table, code, heading, etc.
    paragraph_index = Column(Integer)
    semantic_density = Column(Float)  # Ratio of content words to total words
    contains_table = Column(Boolean, default=False)
    contains_list = Column(Boolean, default=False)
    contains_code = Column(Boolean, default=False)
    contains_equation = Column(Boolean, default=False)
    contains_figure = Column(Boolean, default=False)
    language = Column(String(10), default='en')

    # JSON/JSONB column for comprehensive document structure metadata
    # Uses JSONB for PostgreSQL, JSON for SQLite (tests)
    chunk_metadata = Column(JSON)

    # Processing metadata
    embedding_model = Column(String(100), nullable=False, default='text-embedding-ada-002')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="embeddings")