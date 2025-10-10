from fastapi import APIRouter, UploadFile, File
from app.schemas.upload import UploadResponse

router = APIRouter()

@router.post("/", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    return {"message": "Upload endpoint - to be implemented", "filename": file.filename}