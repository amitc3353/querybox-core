"""
Quality Validator for Step 8.3 - Simple Keyword Search

Validates extraction and chunking quality to ensure documents are search-ready.
"""
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.document import Document
from app.models.document_text import DocumentText
from app.models.embedding import Embedding


class QualityValidator:
    """
    Validates extraction and processing quality for search readiness

    Used for testing and quality assurance of Steps 8.1 and 8.2
    """

    # Quality thresholds
    MIN_EXTRACTION_QUALITY = 0.5
    MIN_TEXT_LENGTH = 100
    MIN_CHUNK_SIZE = 100
    MAX_CHUNK_SIZE = 1500
    EXPECTED_CHUNK_OVERLAP = 200
    OVERLAP_TOLERANCE = 50  # ±50 chars

    def __init__(self, db: Session):
        """Initialize validator with database session"""
        self.db = db

    def validate_document_extraction(self, document_id: UUID) -> Dict:
        """
        Validate extraction quality for a document

        Checks:
        - Text extracted successfully
        - Extraction quality score > threshold
        - Text length reasonable (not empty, not too short)
        - OCR usage tracked correctly
        - Language detected

        Args:
            document_id: Document UUID to validate

        Returns:
            Dict with extraction validation results
        """
        # Get document
        document = self.db.query(Document).filter(
            Document.id == document_id
        ).first()

        if not document:
            return {
                "document_id": str(document_id),
                "document_name": None,
                "extraction_status": "failed",
                "text_length": 0,
                "extraction_quality": None,
                "extraction_method": None,
                "pages_with_ocr": None,
                "total_pages": None,
                "detected_language": None,
                "issues": ["Document not found"],
                "recommendations": ["Check if document ID is correct"]
            }

        # Get document text
        document_text = self.db.query(DocumentText).filter(
            DocumentText.document_id == document_id
        ).first()

        if not document_text:
            return {
                "document_id": str(document_id),
                "document_name": document.document_name,
                "extraction_status": "failed",
                "text_length": 0,
                "extraction_quality": None,
                "extraction_method": None,
                "pages_with_ocr": None,
                "total_pages": None,
                "detected_language": None,
                "issues": ["No extracted text found - extraction may have failed"],
                "recommendations": [
                    "Check processing_status table for extraction errors",
                    "Re-run text extraction task",
                    "Verify document is not corrupted"
                ]
            }

        # Validate extraction quality
        issues = []
        recommendations = []
        status = "passed"

        # Check text length
        if document_text.text_length == 0:
            issues.append("Text extraction produced 0 characters")
            recommendations.append("Check if document is text-based or scanned")
            status = "failed"
        elif document_text.text_length < self.MIN_TEXT_LENGTH:
            issues.append(f"Text is too short ({document_text.text_length} chars)")
            recommendations.append("Document may be mostly images or empty pages")
            status = "warning"

        # Check extraction quality score
        if document_text.extraction_quality is not None:
            if document_text.extraction_quality < self.MIN_EXTRACTION_QUALITY:
                issues.append(
                    f"Extraction quality too low ({document_text.extraction_quality:.2f} < {self.MIN_EXTRACTION_QUALITY})"
                )
                recommendations.append("Consider using OCR for scanned documents")
                status = "failed"
        else:
            issues.append("Extraction quality score not available")
            status = "warning"

        # Check OCR usage
        if document_text.pages_with_ocr and document_text.total_pages:
            ocr_percentage = (document_text.pages_with_ocr / document_text.total_pages) * 100
            if ocr_percentage > 50:
                issues.append(f"High OCR usage: {ocr_percentage:.1f}% of pages")
                recommendations.append("OCR quality may be lower - verify search results")

        # Check language detection
        if not document_text.detected_language:
            issues.append("Language not detected")
            recommendations.append("May affect search accuracy for non-English documents")

        # Success case
        if not issues:
            status = "passed"
            recommendations.append("Extraction quality is good for search")

        return {
            "document_id": str(document_id),
            "document_name": document.document_name,
            "extraction_status": status,
            "text_length": document_text.text_length,
            "extraction_quality": document_text.extraction_quality,
            "extraction_method": document_text.extraction_method,
            "pages_with_ocr": document_text.pages_with_ocr,
            "total_pages": document_text.total_pages,
            "detected_language": document_text.detected_language,
            "issues": issues,
            "recommendations": recommendations
        }

    def validate_document_chunking(self, document_id: UUID) -> Dict:
        """
        Validate chunking quality

        Checks:
        - Chunks created successfully
        - Chunk count matches expected
        - Chunk sizes within acceptable range
        - No gaps in chunk_index
        - Overlap exists between chunks

        Args:
            document_id: Document UUID to validate

        Returns:
            Dict with chunking validation results
        """
        # Get document
        document = self.db.query(Document).filter(
            Document.id == document_id
        ).first()

        if not document:
            return {
                "document_id": str(document_id),
                "chunking_status": "failed",
                "chunk_count": 0,
                "avg_chunk_size": None,
                "chunks_in_range": None,
                "has_proper_overlap": None,
                "issues": ["Document not found"],
                "recommendations": ["Check if document ID is correct"]
            }

        # Get chunks
        chunks = self.db.query(Embedding).filter(
            Embedding.document_id == document_id
        ).order_by(Embedding.chunk_index).all()

        if not chunks:
            return {
                "document_id": str(document_id),
                "chunking_status": "failed",
                "chunk_count": 0,
                "avg_chunk_size": None,
                "chunks_in_range": None,
                "has_proper_overlap": None,
                "issues": ["No chunks found - chunking may have failed"],
                "recommendations": [
                    "Check processing_status table for chunking errors",
                    "Re-run chunking task",
                    "Verify text extraction completed successfully"
                ]
            }

        # Validate chunking quality
        issues = []
        recommendations = []
        status = "passed"

        # Calculate chunk statistics
        chunk_count = len(chunks)
        chunk_sizes = [len(chunk.chunk_text) for chunk in chunks]
        avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0

        # Check chunk sizes
        chunks_in_range = sum(
            1 for size in chunk_sizes
            if self.MIN_CHUNK_SIZE <= size <= self.MAX_CHUNK_SIZE
        )

        if chunks_in_range < len(chunk_sizes):
            out_of_range = len(chunk_sizes) - chunks_in_range
            issues.append(f"{out_of_range} chunks out of size range ({self.MIN_CHUNK_SIZE}-{self.MAX_CHUNK_SIZE} chars)")
            recommendations.append("Review chunking configuration")
            status = "warning"

        # Check for chunk index gaps
        expected_indexes = set(range(len(chunks)))
        actual_indexes = set(chunk.chunk_index for chunk in chunks)
        if expected_indexes != actual_indexes:
            missing = expected_indexes - actual_indexes
            issues.append(f"Missing chunk indexes: {sorted(missing)}")
            recommendations.append("Re-run chunking to fix gaps")
            status = "failed"

        # Check overlap between consecutive chunks
        has_proper_overlap = True
        overlap_checks = 0
        proper_overlaps = 0

        for i in range(len(chunks) - 1):
            if chunks[i].end_position and chunks[i+1].start_position:
                overlap = chunks[i].end_position - chunks[i+1].start_position
                overlap_checks += 1

                # Check if overlap is within tolerance
                if abs(overlap - self.EXPECTED_CHUNK_OVERLAP) <= self.OVERLAP_TOLERANCE:
                    proper_overlaps += 1

        if overlap_checks > 0:
            overlap_percentage = (proper_overlaps / overlap_checks) * 100
            has_proper_overlap = overlap_percentage >= 80

            if not has_proper_overlap:
                issues.append(f"Only {overlap_percentage:.1f}% of chunks have proper overlap")
                recommendations.append("Verify chunking overlap configuration")
                status = "warning"

        # Check chunk count reasonableness
        # Get text length to estimate expected chunks
        document_text = self.db.query(DocumentText).filter(
            DocumentText.document_id == document_id
        ).first()

        if document_text and document_text.text_length > 0:
            # Rough estimate: 1 chunk per 800 chars (1000 - 200 overlap)
            expected_chunks = document_text.text_length / 800
            if chunk_count < expected_chunks * 0.5:
                issues.append(f"Chunk count seems low ({chunk_count} vs expected ~{int(expected_chunks)})")
                recommendations.append("Check if all text was chunked")
                status = "warning"

        # Success case
        if not issues:
            status = "passed"
            recommendations.append("Chunking quality is good for search")

        return {
            "document_id": str(document_id),
            "chunking_status": status,
            "chunk_count": chunk_count,
            "avg_chunk_size": int(avg_chunk_size) if avg_chunk_size else None,
            "chunks_in_range": chunks_in_range,
            "has_proper_overlap": has_proper_overlap if overlap_checks > 0 else None,
            "issues": issues,
            "recommendations": recommendations
        }

    def validate_search_readiness(self, document_id: UUID) -> Dict:
        """
        Check if document is ready for search

        Validates entire pipeline: upload → extract → chunk → search-ready

        Args:
            document_id: Document UUID to validate

        Returns:
            Dict with overall search readiness status
        """
        # Get document
        document = self.db.query(Document).filter(
            Document.id == document_id
        ).first()

        if not document:
            return {
                "document_id": str(document_id),
                "document_name": None,
                "is_search_ready": False,
                "extraction_passed": False,
                "chunking_passed": False,
                "overall_quality_score": 0.0,
                "extraction_details": None,
                "chunking_details": None,
                "issues": ["Document not found"],
                "recommendations": ["Check if document ID is correct"]
            }

        # Validate extraction
        extraction_result = self.validate_document_extraction(document_id)
        extraction_passed = extraction_result["extraction_status"] == "passed"

        # Validate chunking
        chunking_result = self.validate_document_chunking(document_id)
        chunking_passed = chunking_result["chunking_status"] == "passed"

        # Calculate overall quality score (0.0 - 1.0)
        quality_components = []

        if extraction_result["extraction_quality"]:
            quality_components.append(extraction_result["extraction_quality"])

        if extraction_result["text_length"] > 0:
            # Normalize text length score (1000+ chars = 1.0)
            length_score = min(extraction_result["text_length"] / 1000, 1.0)
            quality_components.append(length_score)

        if chunking_result["chunk_count"] > 0:
            # Normalize chunk count (10+ chunks = 1.0)
            chunk_score = min(chunking_result["chunk_count"] / 10, 1.0)
            quality_components.append(chunk_score)

        overall_quality_score = sum(quality_components) / len(quality_components) if quality_components else 0.0

        # Determine if search-ready
        is_search_ready = extraction_passed and chunking_passed and overall_quality_score >= 0.5

        # Combine issues and recommendations
        all_issues = extraction_result["issues"] + chunking_result["issues"]
        all_recommendations = extraction_result["recommendations"] + chunking_result["recommendations"]

        return {
            "document_id": str(document_id),
            "document_name": document.document_name,
            "is_search_ready": is_search_ready,
            "extraction_passed": extraction_passed,
            "chunking_passed": chunking_passed,
            "overall_quality_score": round(overall_quality_score, 2),
            "extraction_details": {
                "text_length": extraction_result["text_length"],
                "extraction_quality": extraction_result["extraction_quality"],
                "extraction_method": extraction_result["extraction_method"],
                "pages_with_ocr": extraction_result["pages_with_ocr"],
                "total_pages": extraction_result["total_pages"],
                "detected_language": extraction_result["detected_language"]
            },
            "chunking_details": {
                "chunk_count": chunking_result["chunk_count"],
                "avg_chunk_size": chunking_result["avg_chunk_size"],
                "chunks_in_range": chunking_result["chunks_in_range"],
                "has_proper_overlap": chunking_result["has_proper_overlap"]
            },
            "issues": all_issues,
            "recommendations": all_recommendations
        }

    def batch_validate_documents(self, document_ids: List[UUID]) -> Dict:
        """
        Validate multiple documents (for 10+ sample doc test)

        Args:
            document_ids: List of document UUIDs to validate

        Returns:
            Dict with aggregate metrics and per-document results
        """
        results = []
        passed_count = 0
        failed_count = 0
        total_quality = 0.0

        for doc_id in document_ids:
            result = self.validate_search_readiness(doc_id)
            results.append(result)

            if result["is_search_ready"]:
                passed_count += 1
            else:
                failed_count += 1

            total_quality += result["overall_quality_score"]

        avg_quality = total_quality / len(document_ids) if document_ids else 0.0

        return {
            "total_documents": len(document_ids),
            "passed": passed_count,
            "failed": failed_count,
            "avg_quality_score": round(avg_quality, 2),
            "results": results
        }


def get_quality_validator(db: Session) -> QualityValidator:
    """
    Factory function to create QualityValidator instance

    Args:
        db: Database session

    Returns:
        QualityValidator instance
    """
    return QualityValidator(db=db)
