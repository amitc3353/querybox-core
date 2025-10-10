"""
Upload endpoint - Week 1, Day 2
Basic file upload with validation and database integration
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
import shutil
import hashlib
import magic
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict

from app.core.config import settings
from app.db.database import get_db
from app.models.document import Document, DocumentStatusEnum, StorageProviderEnum

logger = logging.getLogger(__name__)

router = APIRouter()

# MIME type mapping for allowed extensions
ALLOWED_MIME_TYPES = {
    'application/pdf': ['.pdf'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
    'text/plain': ['.txt'],
    'text/markdown': ['.md'],
    'text/html': ['.html'],
    'text/csv': ['.csv'],
    'application/json': ['.json'],
    'application/xml': ['.xml'],
    'text/xml': ['.xml']
}


@router.post("/")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a single document
    Day 2, Step 3: Basic Upload Handler with database
    Day 2, Step 4: File Validation with MIME type
    
    - Validates file size (30MB limit)
    - Checks allowed file extensions
    - Verifies MIME type
    - Saves to local storage/uploads/
    - Creates database record
    - Returns document ID and status
    """
    try:
        # Step 4: File Validation - Size check
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE / (1024 * 1024)}MB"
            )
        
        # Step 4: File Validation - Extension check
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_extension} not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        # Create uploads directory if it doesn't exist
        upload_dir = Path(settings.STORAGE_PATH) / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = upload_dir / safe_filename
        
        # Step 3: Save file to local storage temporarily
        file_content = await file.read()
        with file_path.open("wb") as buffer:
            buffer.write(file_content)
        
        # Step 4: MIME type verification
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_file(str(file_path))
        
        # Verify MIME type matches expected
        valid_mime = False
        for allowed_mime, extensions in ALLOWED_MIME_TYPES.items():
            if detected_mime == allowed_mime and file_extension in extensions:
                valid_mime = True
                break
        
        if not valid_mime:
            # Remove the file if MIME type doesn't match
            file_path.unlink()
            raise HTTPException(
                status_code=400,
                detail=f"File content does not match extension. Detected: {detected_mime}"
            )
        
        # Calculate file checksum
        sha256_hash = hashlib.sha256()
        sha256_hash.update(file_content)
        checksum = sha256_hash.hexdigest()
        
        # Check for duplicate files
        existing_doc = db.query(Document).filter_by(checksum=checksum).first()
        if existing_doc:
            # Remove the duplicate file
            file_path.unlink()
            raise HTTPException(
                status_code=409,
                detail=f"This file already exists with ID: {existing_doc.id}"
            )
        
        # Create document record in database
        doc = Document(
            document_name=safe_filename,
            original_name=file.filename,
            mime_type=detected_mime,
            file_extension=file_extension,
            file_size=file.size,
            checksum=checksum,
            storage_provider=StorageProviderEnum.LOCAL,
            storage_path=str(file_path.relative_to(settings.STORAGE_PATH)),
            status=DocumentStatusEnum.COMPLETED,  # Since we're not processing yet
            metadata={
                "upload_timestamp": timestamp,
                "uploaded_via": "api"
            }
        )
        
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        logger.info(f"Document uploaded successfully: {doc.id} - {safe_filename}")
        
        # Return response with document ID
        return JSONResponse(
            status_code=200,
            content={
                "message": "File uploaded successfully",
                "document_id": str(doc.id),
                "filename": safe_filename,
                "size": file.size,
                "mime_type": detected_mime,
                "status": doc.status.value,
                "created_at": doc.created_at.isoformat()
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        # Try to clean up file if it exists
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=500,
            detail=f"File upload failed: {str(e)}"
        )
    finally:
        # Ensure file is closed
        await file.close()


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