"""
Docling Integration Service
Step 6: Main service for Docling-based metadata extraction

Coordinates Docling client calls, metadata mapping, and fallback handling
following PipesHub architecture patterns.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from app.config.docling_config import (
    docling_settings,
    is_docling_supported,
    requires_fallback,
    get_max_file_size
)
from app.schemas.metadata import (
    DocumentMetadata,
    ProcessingMetadata,
    MetadataExtractionResponse
)
from app.services.metadata.docling_client import (
    get_docling_client,
    DoclingClient,
    DoclingServiceError,
    DoclingTimeoutError,
    DoclingUnsupportedFormatError,
    DoclingAPIError
)
from app.services.metadata.metadata_mapper import (
    map_docling_to_metadata,
    create_docling_processing_metadata
)
from app.services.metadata.fallback_extractors.text_extractor import (
    extract_basic_metadata
)


logger = logging.getLogger(__name__)


class MetadataExtractionError(Exception):
    """Base exception for metadata extraction errors"""
    pass


class FileSizeExceededError(MetadataExtractionError):
    """Raised when file size exceeds limits"""
    pass


class DoclingMetadataService:
    """
    Main service for Docling-based metadata extraction.
    
    Handles the complete metadata extraction workflow:
    1. Check file compatibility and size limits
    2. Attempt extraction via Docling service
    3. Map results to our metadata schema
    4. Fall back to basic extraction if needed
    5. Return structured response
    """
    
    def __init__(self):
        self.client: Optional[DoclingClient] = None
        self._health_status = None
        self._last_health_check = None
    
    async def initialize(self):
        """Initialize the service and check Docling availability"""
        try:
            self.client = await get_docling_client()
            await self._check_service_health()
            logger.info("Docling metadata service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docling service: {e}")
            self.client = None
    
    async def extract_metadata(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        document_id: str,
        force_fallback: bool = False
    ) -> MetadataExtractionResponse:
        """
        Extract metadata from document using Docling or fallback.
        
        Args:
            file_content: Document content as bytes
            filename: Original filename
            mime_type: Document MIME type
            document_id: Document identifier for tracking
            force_fallback: Skip Docling and use fallback directly
            
        Returns:
            MetadataExtractionResponse with extraction results
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate file size
            self._validate_file_size(file_content, mime_type)
            
            # Determine extraction strategy
            if force_fallback or not await self._can_use_docling(mime_type):
                logger.info(f"Using fallback extraction for {filename} ({mime_type})")
                return await self._extract_with_fallback(
                    file_content, filename, mime_type, document_id, start_time
                )
            
            # Attempt Docling extraction
            try:
                logger.info(f"Attempting Docling extraction for {filename}")
                return await self._extract_with_docling(
                    file_content, filename, mime_type, document_id, start_time
                )
                
            except (DoclingServiceError, DoclingTimeoutError, DoclingAPIError) as e:
                logger.warning(f"Docling extraction failed for {filename}: {e}")
                
                # Fall back to basic extraction if enabled
                if docling_settings.DOCLING_FALLBACK_ENABLED:
                    logger.info(f"Falling back to basic extraction for {filename}")
                    return await self._extract_with_fallback(
                        file_content, filename, mime_type, document_id, start_time,
                        docling_error=str(e)
                    )
                else:
                    # Return error if fallback is disabled
                    raise MetadataExtractionError(f"Docling extraction failed and fallback disabled: {e}")
                    
        except Exception as e:
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"Metadata extraction failed for {filename}: {e}")
            
            return MetadataExtractionResponse(
                document_id=document_id,
                success=False,
                metadata=None,
                processing_metadata=None,
                error_message=str(e),
                extraction_time_ms=processing_time
            )
    
    async def _extract_with_docling(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        document_id: str,
        start_time: float
    ) -> MetadataExtractionResponse:
        """Extract metadata using Docling service"""
        
        # Ensure client is available
        if not self.client:
            await self.initialize()
        
        if not self.client:
            raise DoclingServiceError("Docling client not available")
        
        # Call Docling service
        docling_result = await self.client.analyze_document(
            file_content=file_content,
            filename=filename,
            mime_type=mime_type
        )
        
        # Map results to our schema
        metadata = map_docling_to_metadata(docling_result, mime_type, filename)
        processing_metadata = create_docling_processing_metadata(docling_result)
        
        processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        logger.info(
            f"Docling extraction successful for {filename}: "
            f"{processing_time:.1f}ms, quality={metadata.text_quality_score}"
        )
        
        return MetadataExtractionResponse(
            document_id=document_id,
            success=True,
            metadata=metadata,
            processing_metadata=processing_metadata,
            error_message=None,
            extraction_time_ms=processing_time
        )
    
    async def _extract_with_fallback(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        document_id: str,
        start_time: float,
        docling_error: Optional[str] = None
    ) -> MetadataExtractionResponse:
        """Extract metadata using fallback extractor"""
        
        try:
            # Use basic fallback extraction
            metadata = await extract_basic_metadata(
                file_content, filename, mime_type
            )
            
            # Add warning about fallback usage
            if docling_error:
                metadata.processing_warnings.append(f"Docling failed: {docling_error}")
            
            # Create processing metadata
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            processing_metadata = ProcessingMetadata(
                percentage_complete=100.0,
                current_operation="Completed metadata extraction via fallback",
                processing_duration_ms=int(processing_time),
                extraction_quality=0.5,  # Lower quality for fallback
                completeness_score=0.3,  # Limited completeness
                retry_count=1 if docling_error else 0
            )
            
            logger.info(
                f"Fallback extraction successful for {filename}: {processing_time:.1f}ms"
            )
            
            return MetadataExtractionResponse(
                document_id=document_id,
                success=True,
                metadata=metadata,
                processing_metadata=processing_metadata,
                error_message=None,
                extraction_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = (asyncio.get_event_loop().time() - start_time) * 1000
            raise MetadataExtractionError(f"Fallback extraction failed: {e}")
    
    async def _can_use_docling(self, mime_type: str) -> bool:
        """Check if Docling can be used for this MIME type"""
        
        # Check format support
        if not is_docling_supported(mime_type):
            return False
        
        # Check service health
        if not await self.is_healthy():
            logger.warning("Docling service unhealthy, cannot use for extraction")
            return False
        
        return True
    
    def _validate_file_size(self, file_content: bytes, mime_type: str):
        """Validate file size against limits"""
        file_size = len(file_content)
        max_size = get_max_file_size(mime_type)
        
        if file_size > max_size:
            raise FileSizeExceededError(
                f"File size {file_size} bytes exceeds limit {max_size} bytes for {mime_type}"
            )
    
    async def is_healthy(self) -> bool:
        """
        Check if Docling service is healthy.
        
        Caches health status for 30 seconds to avoid excessive checks.
        """
        import time
        
        current_time = time.time()
        
        # Return cached status if recent
        if (self._last_health_check and 
            current_time - self._last_health_check < 30 and
            self._health_status is not None):
            return self._health_status
        
        # Perform health check
        try:
            if not self.client:
                await self.initialize()
            
            if self.client:
                self._health_status = await self.client.health_check()
            else:
                self._health_status = False
                
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            self._health_status = False
        
        self._last_health_check = current_time
        return self._health_status
    
    async def _check_service_health(self):
        """Initial service health check during initialization"""
        if self.client:
            try:
                healthy = await self.client.health_check()
                if healthy:
                    logger.info("Docling service is healthy")
                else:
                    logger.warning("Docling service health check failed")
            except Exception as e:
                logger.error(f"Docling service health check error: {e}")
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get Docling service information"""
        if not self.client:
            return {"status": "client_not_initialized"}
        
        try:
            info = await self.client.get_service_info()
            info["healthy"] = await self.is_healthy()
            return info
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_supported_formats(self) -> list:
        """Get list of formats supported by Docling"""
        if not self.client:
            return []
        
        try:
            return await self.client.get_supported_formats()
        except Exception as e:
            logger.warning(f"Failed to get supported formats: {e}")
            return []
    
    async def refresh_metadata(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        document_id: str,
        force_docling: bool = False
    ) -> MetadataExtractionResponse:
        """
        Refresh metadata with option to force Docling usage.
        
        Args:
            file_content: Document content
            filename: Original filename
            mime_type: Document MIME type
            document_id: Document identifier
            force_docling: Force use of Docling even if service is unhealthy
            
        Returns:
            MetadataExtractionResponse
        """
        return await self.extract_metadata(
            file_content=file_content,
            filename=filename,
            mime_type=mime_type,
            document_id=document_id,
            force_fallback=not force_docling
        )


# Global service instance
_docling_metadata_service: Optional[DoclingMetadataService] = None


async def get_docling_metadata_service() -> DoclingMetadataService:
    """Get or create global Docling metadata service instance"""
    global _docling_metadata_service
    if _docling_metadata_service is None:
        _docling_metadata_service = DoclingMetadataService()
        await _docling_metadata_service.initialize()
    return _docling_metadata_service


async def extract_document_metadata(
    file_content: bytes,
    filename: str,
    mime_type: str,
    document_id: str
) -> MetadataExtractionResponse:
    """
    Convenience function for document metadata extraction.
    
    Args:
        file_content: Document content as bytes
        filename: Original filename
        mime_type: Document MIME type
        document_id: Document identifier
        
    Returns:
        MetadataExtractionResponse with extraction results
    """
    service = await get_docling_metadata_service()
    return await service.extract_metadata(
        file_content=file_content,
        filename=filename,
        mime_type=mime_type,
        document_id=document_id
    )