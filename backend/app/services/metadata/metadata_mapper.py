"""
Docling Metadata Mapper
Step 6: Maps Docling analysis results to QueryBox metadata schema

Transforms Docling service responses into our standardized DocumentMetadata
format while preserving all relevant information.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.schemas.metadata import (
    DocumentMetadata,
    ContentQuality,
    DocumentType,
    ProcessingEngine,
    ProcessingMetadata
)
from app.services.metadata.docling_client import DoclingAnalysisResult


logger = logging.getLogger(__name__)


class DoclingMetadataMapper:
    """
    Maps Docling analysis results to QueryBox metadata schema.
    
    Handles data transformation, type conversion, and quality assessment
    based on Docling's analysis output.
    """
    
    # Document type mapping based on common patterns
    DOCUMENT_TYPE_PATTERNS = {
        'report': ['report', 'annual report', 'financial report', 'status report'],
        'article': ['article', 'paper', 'research', 'study', 'analysis'],
        'presentation': ['presentation', 'slides', 'deck', 'pptx'],
        'manual': ['manual', 'guide', 'documentation', 'handbook', 'tutorial'],
        'form': ['form', 'application', 'questionnaire', 'survey'],
        'invoice': ['invoice', 'bill', 'receipt', 'statement'],
        'contract': ['contract', 'agreement', 'terms', 'license'],
        'resume': ['resume', 'cv', 'curriculum vitae', 'biography'],
        'email': ['email', 'message', 're:', 'fwd:'],
        'web_page': ['web page', 'website', 'blog post', 'html']
    }
    
    def __init__(self):
        self.extraction_version = "1.0.0"
    
    def map_docling_result(
        self,
        docling_result: DoclingAnalysisResult,
        mime_type: str,
        original_filename: str
    ) -> DocumentMetadata:
        """
        Map Docling analysis result to DocumentMetadata schema.
        
        Args:
            docling_result: Result from Docling service
            mime_type: Original document MIME type
            original_filename: Original filename
            
        Returns:
            DocumentMetadata instance
        """
        try:
            # Map basic document properties
            metadata = DocumentMetadata(
                title=self._extract_title(docling_result, original_filename),
                author=self._clean_text(docling_result.author),
                subject=self._clean_text(docling_result.subject),
                keywords=self._process_keywords(docling_result.keywords),
                creator_application=self._clean_text(docling_result.creator_application),
                
                # Technical specifications
                page_count=docling_result.page_count,
                word_count=docling_result.word_count,
                character_count=docling_result.character_count,
                language=self._normalize_language(docling_result.language),
                
                # Content analysis
                document_type=self._classify_document_type(docling_result, original_filename),
                content_quality=self._assess_content_quality(docling_result),
                text_quality_score=docling_result.text_quality_score,
                has_images=docling_result.has_images,
                has_tables=docling_result.has_tables,
                is_scanned=docling_result.is_scanned,
                requires_ocr=docling_result.is_scanned,
                
                # Processing metadata
                extraction_version=self.extraction_version,
                processing_engine=ProcessingEngine.DOCLING,
                confidence_scores=self._normalize_confidence_scores(docling_result.confidence_scores),
                processing_warnings=docling_result.extraction_warnings or [],
                
                # Timestamp
                extracted_at=datetime.utcnow()
            )
            
            logger.info(f"Mapped Docling result for document: {original_filename}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error mapping Docling result: {e}")
            # Return minimal metadata on error
            return self._create_minimal_metadata(original_filename, mime_type)
    
    def create_processing_metadata(
        self,
        docling_result: DoclingAnalysisResult,
        processing_stage: str = "metadata_extraction"
    ) -> ProcessingMetadata:
        """
        Create ProcessingMetadata from Docling analysis.
        
        Args:
            docling_result: Result from Docling service
            processing_stage: Current processing stage
            
        Returns:
            ProcessingMetadata instance
        """
        # Calculate quality metrics
        extraction_quality = self._calculate_extraction_quality(docling_result)
        completeness_score = self._calculate_completeness_score(docling_result)
        
        return ProcessingMetadata(
            percentage_complete=100.0,  # Metadata extraction is complete
            current_operation=f"Completed {processing_stage} via Docling",
            estimated_completion=datetime.utcnow(),
            processing_duration_ms=int(docling_result.processing_time_ms),
            error_category=None,
            error_details=None,
            retry_count=0,
            extraction_quality=extraction_quality,
            completeness_score=completeness_score,
            processing_priority=5
        )
    
    def _extract_title(self, result: DoclingAnalysisResult, filename: str) -> Optional[str]:
        """Extract and clean document title"""
        title = result.title
        
        if not title or title.strip() == '':
            # Use filename as fallback, cleaned up
            title = filename
            if '.' in title:
                title = title.rsplit('.', 1)[0]  # Remove extension
            title = title.replace('_', ' ').replace('-', ' ').strip()
        
        # Clean and validate title
        if title:
            title = self._clean_text(title)
            if len(title) > 500:
                title = title[:497] + '...'
        
        return title if title else None
    
    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean and validate text fields"""
        if not text:
            return None
        
        # Remove extra whitespace and control characters
        cleaned = ' '.join(text.strip().split())
        
        # Remove null bytes and other problematic characters
        cleaned = cleaned.replace('\x00', '').replace('\r', ' ').replace('\n', ' ')
        
        return cleaned if cleaned else None
    
    def _process_keywords(self, keywords: Optional[List[str]]) -> List[str]:
        """Process and clean keywords list"""
        if not keywords:
            return []
        
        processed = []
        for keyword in keywords:
            if isinstance(keyword, str):
                cleaned = self._clean_text(keyword)
                if cleaned and len(cleaned) <= 100:
                    processed.append(cleaned)
        
        # Limit to 50 keywords
        return processed[:50]
    
    def _normalize_language(self, language: Optional[str]) -> Optional[str]:
        """Normalize language code to ISO 639-1 format"""
        if not language:
            return None
        
        # Convert to lowercase
        lang = language.lower().strip()
        
        # Handle common variations
        lang_map = {
            'english': 'en',
            'spanish': 'es',
            'french': 'fr',
            'german': 'de',
            'italian': 'it',
            'portuguese': 'pt',
            'chinese': 'zh',
            'japanese': 'ja',
            'korean': 'ko',
            'russian': 'ru',
            'arabic': 'ar'
        }
        
        if lang in lang_map:
            return lang_map[lang]
        
        # If already a 2-letter code, validate
        if len(lang) == 2 and lang.isalpha():
            return lang
        
        # Extract 2-letter code from longer codes (e.g., 'en-US' -> 'en')
        if '-' in lang:
            return lang.split('-')[0]
        
        return None
    
    def _classify_document_type(
        self,
        result: DoclingAnalysisResult,
        filename: str
    ) -> Optional[DocumentType]:
        """
        Classify document type based on content analysis.
        
        Uses title, filename, and content patterns to determine document type.
        """
        # Combine text sources for analysis
        text_sources = []
        if result.title:
            text_sources.append(result.title.lower())
        if filename:
            text_sources.append(filename.lower())
        if result.subject:
            text_sources.append(result.subject.lower())
        
        combined_text = ' '.join(text_sources)
        
        # Check for patterns
        for doc_type, patterns in self.DOCUMENT_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in combined_text:
                    return DocumentType(doc_type)
        
        # Special handling based on file characteristics
        if result.has_tables and not result.has_images:
            return DocumentType.SPREADSHEET
        
        if result.page_count and result.page_count > 20:
            return DocumentType.MANUAL
        
        if result.page_count and result.page_count == 1 and result.has_tables:
            return DocumentType.FORM
        
        # Default classification
        return DocumentType.OTHER
    
    def _assess_content_quality(self, result: DoclingAnalysisResult) -> ContentQuality:
        """
        Assess content quality based on Docling analysis.
        
        Uses text quality score and other indicators.
        """
        score = result.text_quality_score
        
        if score is None:
            # Estimate quality based on other factors
            if result.is_scanned:
                return ContentQuality.LOW
            elif result.has_tables or result.has_images:
                return ContentQuality.HIGH
            else:
                return ContentQuality.MEDIUM
        
        # Map score to quality level
        if score >= 0.9:
            return ContentQuality.EXCELLENT
        elif score >= 0.7:
            return ContentQuality.HIGH
        elif score >= 0.5:
            return ContentQuality.MEDIUM
        elif score >= 0.3:
            return ContentQuality.LOW
        else:
            return ContentQuality.POOR
    
    def _normalize_confidence_scores(self, scores: Optional[Dict[str, float]]) -> Dict[str, float]:
        """Normalize and validate confidence scores"""
        if not scores:
            return {}
        
        normalized = {}
        for key, value in scores.items():
            if isinstance(value, (int, float)):
                # Clamp to 0.0-1.0 range
                normalized[str(key)] = max(0.0, min(1.0, float(value)))
        
        return normalized
    
    def _calculate_extraction_quality(self, result: DoclingAnalysisResult) -> Optional[float]:
        """Calculate overall extraction quality score"""
        if not result.confidence_scores:
            return None
        
        # Average confidence scores
        scores = [score for score in result.confidence_scores.values() if isinstance(score, (int, float))]
        if not scores:
            return None
        
        return sum(scores) / len(scores)
    
    def _calculate_completeness_score(self, result: DoclingAnalysisResult) -> float:
        """Calculate metadata completeness score"""
        total_fields = 10  # Number of key fields we expect
        filled_fields = 0
        
        # Check key fields
        if result.title:
            filled_fields += 1
        if result.author:
            filled_fields += 1
        if result.language:
            filled_fields += 1
        if result.page_count:
            filled_fields += 1
        if result.word_count:
            filled_fields += 1
        if result.keywords:
            filled_fields += 1
        if result.subject:
            filled_fields += 1
        if result.text_quality_score is not None:
            filled_fields += 1
        if result.confidence_scores:
            filled_fields += 1
        if result.creator_application:
            filled_fields += 1
        
        return filled_fields / total_fields
    
    def _create_minimal_metadata(self, filename: str, mime_type: str) -> DocumentMetadata:
        """Create minimal metadata when mapping fails"""
        return DocumentMetadata(
            title=self._extract_title(DoclingAnalysisResult(), filename),
            extraction_version=self.extraction_version,
            processing_engine=ProcessingEngine.DOCLING,
            content_quality=ContentQuality.MEDIUM,
            processing_warnings=["Failed to map Docling result, using minimal metadata"],
            extracted_at=datetime.utcnow()
        )


# Global mapper instance
metadata_mapper = DoclingMetadataMapper()


def map_docling_to_metadata(
    docling_result: DoclingAnalysisResult,
    mime_type: str,
    filename: str
) -> DocumentMetadata:
    """
    Convenience function to map Docling result to metadata.
    
    Args:
        docling_result: Result from Docling analysis
        mime_type: Document MIME type
        filename: Original filename
        
    Returns:
        DocumentMetadata instance
    """
    return metadata_mapper.map_docling_result(docling_result, mime_type, filename)


def create_docling_processing_metadata(
    docling_result: DoclingAnalysisResult,
    stage: str = "metadata_extraction"
) -> ProcessingMetadata:
    """
    Convenience function to create processing metadata.
    
    Args:
        docling_result: Result from Docling analysis
        stage: Processing stage name
        
    Returns:
        ProcessingMetadata instance
    """
    return metadata_mapper.create_processing_metadata(docling_result, stage)