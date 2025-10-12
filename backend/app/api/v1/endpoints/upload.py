"""
Upload endpoint - Week 1, Day 2 + Day 3, Step 5
Enhanced file upload with StorageManager integration
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import magic
from datetime import datetime, timezone
from pathlib import Path
import logging
from typing import Optional
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.storage_config import storage_settings
from app.db.database import get_db
from app.models.document import Document, DocumentStatusEnum, StorageProviderEnum
from app.services.storage import StorageManager
from app.services.storage.exceptions import StorageException, StorageQuotaExceeded
from app.schemas.storage import StorageResult

logger = logging.getLogger(__name__)

router = APIRouter()

def get_storage_manager(db: Session = Depends(get_db)) -> StorageManager:
    """Dependency to provide StorageManager instance"""
    return StorageManager(db)


@router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: Optional[str] = None,  # For future multi-tenant support
    db: Session = Depends(get_db),
    storage: StorageManager = Depends(get_storage_manager)
):
    """
    Upload a single document with enhanced storage management
    Day 3, Step 5: StorageManager integration with atomic operations
    
    Features:
    - Advanced file validation (size, extension, MIME type)
    - Organized storage with conflict resolution
    - Atomic operations with rollback on failure
    - Comprehensive error handling and logging
    - Database integration with audit trail
    """
    document_id = uuid4()
    temp_storage_result = None
    
    try:
        # Convert workspace_id to UUID (use default for MVP)
        if workspace_id:
            workspace_uuid = UUID(workspace_id)
        else:
            # Default workspace for MVP (single-tenant)
            workspace_uuid = UUID("00000000-0000-0000-0000-000000000000")
        
        # Step 1: Basic validation
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE / (1024 * 1024):.1f}MB"
            )
        
        # Step 2: Extension validation
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_extension}' not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        # Step 3: MIME type validation
        file_content = await file.read()
        mime = magic.Magic(mime=True)
        
        # Create temporary file for MIME detection
        temp_path = f"/tmp/upload_validation_{document_id}"
        with open(temp_path, "wb") as temp_file:
            temp_file.write(file_content)
        
        try:
            detected_mime = mime.from_file(temp_path)
        finally:
            # Clean up temp validation file
            Path(temp_path).unlink(missing_ok=True)
        
        # Verify MIME type is in allowed list
        if detected_mime not in storage_settings.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"MIME type '{detected_mime}' not allowed"
            )
        
        # Reset file for StorageManager
        await file.seek(0)
        
        # Step 4: Store document using StorageManager
        # This handles: conflict resolution, organized paths, checksums, duplicates
        temp_storage_result = await storage.store_document(
            file=file,
            workspace_id=workspace_uuid,
            document_id=document_id
        )
        
        # Step 5: Create database record with transaction
        db.begin()
        try:
            doc = Document(
                id=temp_storage_result.document_id,
                document_name=Path(temp_storage_result.path).name,
                original_name=file.filename,
                mime_type=temp_storage_result.mime_type,
                file_extension=file_extension,
                file_size=temp_storage_result.size,
                checksum=temp_storage_result.checksum,
                storage_provider=StorageProviderEnum.LOCAL,
                storage_path=temp_storage_result.path,
                status=DocumentStatusEnum.COMPLETED,
                metadata={
                    "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                    "uploaded_via": "api",
                    "workspace_id": str(workspace_uuid),
                    "conflict_strategy": storage_settings.CONFLICT_STRATEGY.value,
                    "operation_time_ms": temp_storage_result.operation_time_ms
                }
            )
            
            db.add(doc)
            db.commit()
            
            logger.info(
                f"Document uploaded successfully: {doc.id}",
                extra={
                    "document_id": str(doc.id),
                    "filename": file.filename,
                    "size": temp_storage_result.size,
                    "storage_path": temp_storage_result.path,
                    "operation_time_ms": temp_storage_result.operation_time_ms
                }
            )
            
            # Return enhanced response with storage details
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "File uploaded successfully",
                    "document": {
                        "id": str(doc.id),
                        "filename": doc.original_name,
                        "storage_filename": doc.document_name,
                        "size": temp_storage_result.size,
                        "mime_type": temp_storage_result.mime_type,
                        "checksum": temp_storage_result.checksum,
                        "status": doc.status.value,
                        "created_at": doc.created_at.isoformat()
                    },
                    "storage": {
                        "provider": temp_storage_result.provider.value,
                        "path": temp_storage_result.path,
                        "operation_time_ms": temp_storage_result.operation_time_ms
                    }
                }
            )
            
        except SQLAlchemyError as db_error:
            # Rollback database transaction
            db.rollback()
            
            # Clean up storage on database failure
            if temp_storage_result:
                try:
                    await storage.provider.delete_file(temp_storage_result.path)
                    logger.info(f"Cleaned up storage file after DB error: {temp_storage_result.path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup storage after DB error: {cleanup_error}")
            
            logger.error(f"Database error during upload: {db_error}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save document information"
            )
            
    except StorageQuotaExceeded as quota_error:
        logger.warning(f"Storage quota exceeded: {quota_error}")
        raise HTTPException(
            status_code=413,
            detail=f"Storage quota exceeded. Used: {quota_error.used_bytes / (1024*1024):.1f}MB, Limit: {quota_error.quota_bytes / (1024*1024):.1f}MB"
        )
        
    except StorageException as storage_error:
        logger.error(f"Storage error: {storage_error}")
        raise HTTPException(
            status_code=500,
            detail=f"Storage operation failed: {storage_error.message}"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
        
    except Exception as e:
        logger.error(f"Unexpected upload error: {str(e)}", exc_info=True)
        
        # Emergency cleanup
        if temp_storage_result:
            try:
                await storage.provider.delete_file(temp_storage_result.path)
            except:
                pass  # Don't fail the error response due to cleanup issues
        
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during upload"
        )


@router.get("/allowed-types")
async def get_allowed_file_types():
    """
    Get list of allowed file types
    Helper endpoint for frontend validation
    """
    return {
        "allowed_extensions": settings.ALLOWED_EXTENSIONS,
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024)
    }