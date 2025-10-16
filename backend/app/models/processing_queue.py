from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, CheckConstraint, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from app.models.types import GUID, JSON
import uuid


class ProcessingQueue(Base):
    __tablename__ = "processing_queue"
    
    # Primary identifier
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Reference to document
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Queue management
    priority = Column(Integer, default=5, nullable=False)
    status = Column(String(50), default='pending', nullable=False)
    
    # Worker tracking
    processor_id = Column(String(255))  # Celery worker ID
    locked_at = Column(DateTime(timezone=True))
    
    # Retry management
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    next_retry_at = Column(DateTime(timezone=True))
    
    # Timing
    scheduled_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    
    # Error tracking
    error_message = Column(Text)
    error_details = Column(JSON, default={})
    error_code = Column(String(50))

    # Metadata
    task_params = Column(JSON, default={})
    result_data = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="queue_items")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('priority >= 1 AND priority <= 10'),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')"
        ),
    )