"""
Docling API Client
Step 6: HTTP client wrapper for Docling service integration

Provides async HTTP client for communicating with Docling service,
following PipesHub architecture patterns for document processing.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config.docling_config import docling_settings, is_docling_supported, get_format_config


logger = logging.getLogger(__name__)


class DoclingServiceError(Exception):
    """Base exception for Docling service errors"""
    pass


class DoclingTimeoutError(DoclingServiceError):
    """Raised when Docling service request times out"""
    pass


class DoclingUnsupportedFormatError(DoclingServiceError):
    """Raised when document format is not supported by Docling"""
    pass


class DoclingAPIError(DoclingServiceError):
    """Raised for API-level errors from Docling service"""
    def __init__(self, message: str, status_code: int = None, response_data: Dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


@dataclass
class DoclingAnalysisResult:
    """Result from Docling document analysis"""
    
    # Document properties
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: List[str] = None
    creator_application: Optional[str] = None
    
    # Technical specifications
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    character_count: Optional[int] = None
    language: Optional[str] = None
    
    # Content analysis
    text_content: Optional[str] = None
    has_images: bool = False
    has_tables: bool = False
    is_scanned: bool = False
    
    # Quality assessment
    text_quality_score: Optional[float] = None
    confidence_scores: Dict[str, float] = None
    
    # Processing metadata
    processing_time_ms: float = 0.0
    docling_version: Optional[str] = None
    extraction_warnings: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.confidence_scores is None:
            self.confidence_scores = {}
        if self.extraction_warnings is None:
            self.extraction_warnings = []


class DoclingClient:
    """
    Async HTTP client for Docling service.
    
    Handles document analysis requests with proper error handling,
    retries, and timeout management.
    """
    
    def __init__(self):
        self.base_url = docling_settings.DOCLING_SERVICE_URL.rstrip('/')
        self.api_key = docling_settings.DOCLING_API_KEY
        self.timeout = docling_settings.DOCLING_REQUEST_TIMEOUT
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is created"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                'User-Agent': 'QueryboxCore/1.0',
                'Accept': 'application/json'
            }
            
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def health_check(self) -> bool:
        """
        Check if Docling service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            await self._ensure_session()
            
            async with self.session.get(f'{self.base_url}/health') as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('status') == 'healthy'
                return False
                
        except Exception as e:
            logger.warning(f"Docling health check failed: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, DoclingTimeoutError))
    )
    async def analyze_document(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        options: Optional[Dict[str, Any]] = None
    ) -> DoclingAnalysisResult:
        """
        Analyze a document using Docling service.
        
        Args:
            file_content: Document content as bytes
            filename: Original filename
            mime_type: Document MIME type
            options: Additional processing options
            
        Returns:
            DoclingAnalysisResult with extracted metadata
            
        Raises:
            DoclingUnsupportedFormatError: If format not supported
            DoclingAPIError: For API-level errors
            DoclingTimeoutError: If request times out
        """
        if not is_docling_supported(mime_type):
            raise DoclingUnsupportedFormatError(f"Format {mime_type} not supported by Docling")
        
        await self._ensure_session()
        
        # Prepare request data
        format_config = get_format_config(mime_type)
        processing_options = {
            'quality_level': docling_settings.DOCLING_QUALITY_LEVEL.value,
            'extract_images': docling_settings.DOCLING_EXTRACT_IMAGES,
            'extract_tables': docling_settings.DOCLING_EXTRACT_TABLES,
            'ocr_enabled': docling_settings.DOCLING_OCR_ENABLED,
            'language_detection': docling_settings.DOCLING_LANGUAGE_DETECTION,
            **format_config,
            **(options or {})
        }
        
        # Create multipart form data
        data = aiohttp.FormData()
        data.add_field('file', file_content, filename=filename, content_type=mime_type)
        data.add_field('options', json.dumps(processing_options), content_type='application/json')
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with self.session.post(f'{self.base_url}/analyze', data=data) as response:
                processing_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                
                if response.status == 413:
                    raise DoclingAPIError("File too large for processing", response.status)
                
                if response.status == 415:
                    raise DoclingUnsupportedFormatError(f"Unsupported media type: {mime_type}")
                
                if response.status >= 400:
                    error_data = {}
                    try:
                        error_data = await response.json()
                    except:
                        pass
                    
                    error_msg = error_data.get('message', f'HTTP {response.status}')
                    raise DoclingAPIError(error_msg, response.status, error_data)
                
                result_data = await response.json()
                return self._parse_docling_response(result_data, processing_time_ms)
                
        except asyncio.TimeoutError:
            raise DoclingTimeoutError(f"Request timed out after {self.timeout}s")
        except aiohttp.ClientError as e:
            raise DoclingServiceError(f"HTTP client error: {e}")
    
    def _parse_docling_response(self, data: Dict[str, Any], processing_time_ms: float) -> DoclingAnalysisResult:
        """Parse Docling API response into DoclingAnalysisResult"""
        
        # Extract document properties
        document = data.get('document', {})
        metadata = document.get('metadata', {})
        content = data.get('content', {})
        analysis = data.get('analysis', {})
        
        # Parse keywords (can be string or list)
        keywords_raw = metadata.get('keywords', [])
        if isinstance(keywords_raw, str):
            keywords = [kw.strip() for kw in keywords_raw.split(',') if kw.strip()]
        else:
            keywords = keywords_raw or []
        
        # Extract confidence scores
        confidence_scores = analysis.get('confidence', {})
        if isinstance(confidence_scores, (int, float)):
            confidence_scores = {'overall': float(confidence_scores)}
        
        return DoclingAnalysisResult(
            # Document properties
            title=metadata.get('title'),
            author=metadata.get('author'),
            subject=metadata.get('subject'),
            keywords=keywords,
            creator_application=metadata.get('creator'),
            
            # Technical specifications
            page_count=metadata.get('page_count'),
            word_count=content.get('word_count'),
            character_count=content.get('character_count'),
            language=analysis.get('language'),
            
            # Content analysis
            text_content=content.get('text'),
            has_images=content.get('has_images', False),
            has_tables=content.get('has_tables', False),
            is_scanned=analysis.get('is_scanned', False),
            
            # Quality assessment
            text_quality_score=analysis.get('text_quality_score'),
            confidence_scores=confidence_scores,
            
            # Processing metadata
            processing_time_ms=processing_time_ms,
            docling_version=data.get('version'),
            extraction_warnings=data.get('warnings', [])
        )
    
    async def get_supported_formats(self) -> List[str]:
        """
        Get list of formats supported by Docling service.
        
        Returns:
            List of supported MIME types
        """
        try:
            await self._ensure_session()
            
            async with self.session.get(f'{self.base_url}/formats') as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('supported_formats', [])
                return []
                
        except Exception as e:
            logger.warning(f"Failed to get supported formats: {e}")
            return []
    
    async def get_service_info(self) -> Dict[str, Any]:
        """
        Get Docling service information.
        
        Returns:
            Service information dictionary
        """
        try:
            await self._ensure_session()
            
            async with self.session.get(f'{self.base_url}/info') as response:
                if response.status == 200:
                    return await response.json()
                return {}
                
        except Exception as e:
            logger.warning(f"Failed to get service info: {e}")
            return {}


# Global client instance
_docling_client: Optional[DoclingClient] = None


async def get_docling_client() -> DoclingClient:
    """Get or create global Docling client instance"""
    global _docling_client
    if _docling_client is None:
        _docling_client = DoclingClient()
    await _docling_client._ensure_session()
    return _docling_client


async def close_docling_client():
    """Close global Docling client"""
    global _docling_client
    if _docling_client:
        await _docling_client.close()
        _docling_client = None