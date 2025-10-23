"""
DocumentText Model
Stores extracted text from documents for search and chunking
"""
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
from app.models.types import GUID
import uuid


class DocumentText(Base):
    __tablename__ = "document_texts"

    # Primary identifier
    id = Column(GUID, primary_key=True, default=uuid.uuid4)

    # Reference to parent document
    document_id = Column(
        GUID,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Extracted text content
    full_text = Column(Text, nullable=False)
    text_length = Column(Integer, nullable=False)

    # Extraction metadata
    extraction_method = Column(String(50), nullable=False)  # 'docling', 'docling_ocr', 'fallback'
    extraction_engine = Column(String(50))  # 'easyocr', 'tesseract', 'rapidocr', 'native'
    extraction_quality = Column(Float)  # 0.0-1.0 confidence score

    # OCR tracking
    pages_with_ocr = Column(Integer, default=0)
    total_pages = Column(Integer)
    extraction_duration_ms = Column(Integer)

    # Language detection
    detected_language = Column(String(10))

    # Timestamps
    extracted_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    document = relationship("Document", back_populates="document_text")

    # Constraints
    __table_args__ = (
        CheckConstraint('extraction_quality >= 0.0 AND extraction_quality <= 1.0', name='check_extraction_quality'),
        CheckConstraint('text_length >= 0', name='check_text_length_positive'),
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentText(document_id={self.document_id}, "
            f"text_length={self.text_length}, "
            f"method={self.extraction_method})>"
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary for API responses"""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "text_length": self.text_length,
            "extraction_method": self.extraction_method,
            "extraction_engine": self.extraction_engine,
            "extraction_quality": self.extraction_quality,
            "pages_with_ocr": self.pages_with_ocr,
            "total_pages": self.total_pages,
            "extraction_duration_ms": self.extraction_duration_ms,
            "detected_language": self.detected_language,
            "extracted_at": self.extracted_at.isoformat() if self.extracted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
