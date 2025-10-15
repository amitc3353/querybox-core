"""
Text Fallback Extractor
Step 6: Simple metadata extraction for unsupported file types

Provides basic metadata extraction when Docling service cannot process
a document format. Handles plain text, CSV, JSON, and other simple formats.
"""

import json
import csv
import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from app.schemas.metadata import (
    DocumentMetadata,
    ContentQuality,
    DocumentType,
    ProcessingEngine
)


logger = logging.getLogger(__name__)


class TextMetadataExtractor:
    """
    Simple metadata extractor for text-based formats.
    
    Provides basic analysis when Docling service is unavailable
    or for unsupported formats.
    """
    
    def __init__(self):
        self.extraction_version = "1.0.0"
        self.processing_engine = ProcessingEngine.FALLBACK_TEXT
    
    async def extract_metadata(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str
    ) -> DocumentMetadata:
        """
        Extract basic metadata from file content.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            mime_type: File MIME type
            
        Returns:
            DocumentMetadata with basic information
        """
        try:
            # Decode content to text
            text_content = self._decode_content(file_content, mime_type)
            
            # Extract basic properties
            metadata = DocumentMetadata(
                title=self._extract_title(text_content, filename),
                author=None,  # Cannot reliably extract from plain text
                subject=None,
                keywords=self._extract_keywords(text_content),
                creator_application=None,
                
                # Technical specifications
                page_count=self._estimate_page_count(text_content),
                word_count=self._count_words(text_content),
                character_count=len(text_content) if text_content else 0,
                language=self._detect_language_basic(text_content),
                
                # Content analysis
                document_type=self._classify_document_type(filename, mime_type, text_content),
                content_quality=self._assess_content_quality(text_content),
                text_quality_score=self._calculate_quality_score(text_content),
                has_images=False,  # Text formats don't have images
                has_tables=self._detect_tables(text_content, mime_type),
                is_scanned=False,  # Text formats are not scanned
                requires_ocr=False,
                
                # Processing metadata
                extraction_version=self.extraction_version,
                processing_engine=self.processing_engine,
                confidence_scores={"overall": 0.6},  # Lower confidence for fallback
                processing_warnings=["Used fallback extractor - limited metadata available"],
                
                # Timestamp
                extracted_at=datetime.utcnow()
            )
            
            logger.info(f"Fallback extraction completed for {filename}")
            return metadata
            
        except Exception as e:
            logger.error(f"Fallback extraction failed for {filename}: {e}")
            return self._create_minimal_metadata(filename, mime_type)
    
    def _decode_content(self, content: bytes, mime_type: str) -> Optional[str]:
        """Decode bytes content to text with encoding detection"""
        if not content:
            return None
        
        # Try common encodings
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252', 'ascii']
        
        for encoding in encodings:
            try:
                return content.decode(encoding)
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        # If all encodings fail, use utf-8 with error handling
        try:
            return content.decode('utf-8', errors='replace')
        except Exception:
            return None
    
    def _extract_title(self, text: Optional[str], filename: str) -> Optional[str]:
        """Extract title from text content or filename"""
        if text:
            # Look for title patterns at the beginning
            lines = text.strip().split('\n')[:10]  # Check first 10 lines
            
            for line in lines:
                line = line.strip()
                if line and len(line) > 5 and len(line) < 200:
                    # Skip lines that look like metadata or code
                    if not any(pattern in line.lower() for pattern in 
                              ['import ', 'from ', '<?xml', '<!doctype', 'function ', 'class ']):
                        return line[:500]  # Limit title length
        
        # Fall back to filename
        title = Path(filename).stem
        return title.replace('_', ' ').replace('-', ' ').strip() if title else None
    
    def _extract_keywords(self, text: Optional[str]) -> List[str]:
        """Extract simple keywords from text"""
        if not text or len(text) < 100:
            return []
        
        # Simple keyword extraction based on word frequency
        # Remove common words and short words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
            'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        # Filter and count
        word_freq = {}
        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        return [word for word, freq in keywords if freq > 1]
    
    def _estimate_page_count(self, text: Optional[str]) -> Optional[int]:
        """Estimate page count based on character count"""
        if not text:
            return None
        
        # Rough estimate: 2000 characters per page
        char_count = len(text)
        if char_count > 2000:
            return max(1, char_count // 2000)
        else:
            return 1
    
    def _count_words(self, text: Optional[str]) -> Optional[int]:
        """Count words in text"""
        if not text:
            return None
        
        # Simple word count
        words = re.findall(r'\b\w+\b', text)
        return len(words)
    
    def _detect_language_basic(self, text: Optional[str]) -> Optional[str]:
        """Basic language detection based on common words"""
        if not text or len(text) < 100:
            return None
        
        # Very basic detection based on common words
        text_lower = text.lower()
        
        # English indicators
        english_words = ['the', 'and', 'is', 'to', 'a', 'in', 'that', 'have', 'i', 'it']
        english_score = sum(1 for word in english_words if word in text_lower)
        
        # Spanish indicators
        spanish_words = ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se']
        spanish_score = sum(1 for word in spanish_words if word in text_lower)
        
        # French indicators
        french_words = ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir']
        french_score = sum(1 for word in french_words if word in text_lower)
        
        scores = {'en': english_score, 'es': spanish_score, 'fr': french_score}
        max_lang = max(scores, key=scores.get)
        
        # Only return if confident
        if scores[max_lang] >= 3:
            return max_lang
        
        return 'en'  # Default to English
    
    def _classify_document_type(self, filename: str, mime_type: str, text: Optional[str]) -> DocumentType:
        """Classify document type based on filename and content"""
        filename_lower = filename.lower()
        
        # Check filename patterns
        if any(pattern in filename_lower for pattern in ['readme', 'manual', 'guide', 'doc']):
            return DocumentType.MANUAL
        
        if any(pattern in filename_lower for pattern in ['report', 'summary']):
            return DocumentType.REPORT
        
        if any(pattern in filename_lower for pattern in ['invoice', 'bill', 'receipt']):
            return DocumentType.INVOICE
        
        if any(pattern in filename_lower for pattern in ['contract', 'agreement', 'terms']):
            return DocumentType.CONTRACT
        
        # Check MIME type
        if mime_type == 'text/csv':
            return DocumentType.SPREADSHEET
        
        if mime_type == 'application/json':
            return DocumentType.OTHER
        
        # Check content patterns
        if text:
            text_lower = text.lower()
            
            if any(pattern in text_lower for pattern in ['dear sir', 'dear madam', 'sincerely', 'regards']):
                return DocumentType.EMAIL
            
            if 'table of contents' in text_lower or text.count('\n#') > 3:
                return DocumentType.MANUAL
        
        return DocumentType.OTHER
    
    def _assess_content_quality(self, text: Optional[str]) -> ContentQuality:
        """Assess content quality based on text characteristics"""
        if not text:
            return ContentQuality.POOR
        
        quality_score = self._calculate_quality_score(text)
        
        if quality_score >= 0.8:
            return ContentQuality.HIGH
        elif quality_score >= 0.6:
            return ContentQuality.MEDIUM
        elif quality_score >= 0.4:
            return ContentQuality.LOW
        else:
            return ContentQuality.POOR
    
    def _calculate_quality_score(self, text: Optional[str]) -> Optional[float]:
        """Calculate text quality score"""
        if not text:
            return 0.0
        
        score = 0.0
        factors = 0
        
        # Length factor
        if len(text) > 100:
            score += 0.2
        factors += 1
        
        # Word diversity
        words = re.findall(r'\b\w+\b', text.lower())
        if words:
            unique_words = len(set(words))
            total_words = len(words)
            if total_words > 0:
                diversity = unique_words / total_words
                score += min(diversity * 2, 0.3)  # Cap at 0.3
        factors += 1
        
        # Sentence structure
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) > 2:
            score += 0.2
        factors += 1
        
        # Proper capitalization
        caps_count = sum(1 for c in text if c.isupper())
        if caps_count > 0 and caps_count < len(text) * 0.1:  # Not all caps
            score += 0.2
        factors += 1
        
        # Punctuation presence
        punct_count = sum(1 for c in text if c in '.,!?;:')
        if punct_count > len(text) * 0.01:  # At least 1% punctuation
            score += 0.1
        factors += 1
        
        return min(score / factors, 1.0)  # Normalize to 0-1
    
    def _detect_tables(self, text: Optional[str], mime_type: str) -> bool:
        """Detect if text contains table-like data"""
        if mime_type == 'text/csv':
            return True
        
        if not text:
            return False
        
        # Look for table patterns
        lines = text.split('\n')
        
        # Check for consistent delimiters
        delimiter_counts = {}
        for line in lines[:20]:  # Check first 20 lines
            for delimiter in ['\t', ',', '|', ';']:
                count = line.count(delimiter)
                if count > 1:
                    if delimiter not in delimiter_counts:
                        delimiter_counts[delimiter] = []
                    delimiter_counts[delimiter].append(count)
        
        # If we find consistent delimiter usage, likely a table
        for delimiter, counts in delimiter_counts.items():
            if len(counts) > 3 and len(set(counts)) <= 2:  # Consistent column count
                return True
        
        return False
    
    def _create_minimal_metadata(self, filename: str, mime_type: str) -> DocumentMetadata:
        """Create minimal metadata when extraction fails"""
        return DocumentMetadata(
            title=Path(filename).stem.replace('_', ' ').replace('-', ' '),
            extraction_version=self.extraction_version,
            processing_engine=ProcessingEngine.FALLBACK_BASIC,
            content_quality=ContentQuality.LOW,
            processing_warnings=["Extraction failed, using minimal metadata"],
            extracted_at=datetime.utcnow()
        )


# Global extractor instance
_text_extractor: Optional[TextMetadataExtractor] = None


def get_text_extractor() -> TextMetadataExtractor:
    """Get or create global text extractor instance"""
    global _text_extractor
    if _text_extractor is None:
        _text_extractor = TextMetadataExtractor()
    return _text_extractor


async def extract_basic_metadata(
    file_content: bytes,
    filename: str,
    mime_type: str
) -> DocumentMetadata:
    """
    Convenience function for basic metadata extraction.
    
    Args:
        file_content: File content as bytes
        filename: Original filename
        mime_type: File MIME type
        
    Returns:
        DocumentMetadata with basic information
    """
    extractor = get_text_extractor()
    return await extractor.extract_metadata(file_content, filename, mime_type)