from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from app.models.document import ProcessingStageEnum, StageStatusEnum
from app.models.types import GUID, JSON
import uuid


class ProcessingStatus(Base):
    __tablename__ = "processing_status"
    
    # Primary identifier
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Reference to document being processed
    document_id = Column(GUID, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    # Processing stage information
    stage = Column(
        Enum(ProcessingStageEnum, name="processing_stage_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    status = Column(
        Enum(StageStatusEnum, name="stage_status_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=StageStatusEnum.NOT_STARTED
    )
    
    # Timing information
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    
    # Progress tracking
    progress_percentage = Column(Integer, default=0)
    
    # Results and error handling
    result_data = Column(JSON, default={})
    error_message = Column(Text)
    error_code = Column(String(50))

    # Retry tracking
    attempt_number = Column(Integer, nullable=False, default=1)
    max_attempts = Column(Integer, nullable=False, default=3)

    # Processing metadata (Python attribute is 'status_metadata', DB column is 'metadata')
    status_metadata = Column('metadata', JSON, default={})
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="processing_status")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('progress_percentage >= 0 AND progress_percentage <= 100'),
        CheckConstraint(
            "(completed_at IS NULL AND duration_ms IS NULL) OR "
            "(completed_at IS NOT NULL AND duration_ms IS NOT NULL)"
        ),
    )