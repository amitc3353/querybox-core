from fastapi import APIRouter
from app.schemas.document import DocumentResponse

router = APIRouter()

@router.get("/", response_model=list[DocumentResponse])
async def list_documents():
    return []

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    return {"id": document_id, "message": "Document endpoint - to be implemented"}