from fastapi import APIRouter
from app.api.v1.endpoints import upload, documents, search, health, storage_admin, metadata, embeddings, answer

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(embeddings.router, prefix="/documents", tags=["embeddings"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(answer.router, prefix="/answer", tags=["answer"])
api_router.include_router(metadata.router, prefix="/metadata", tags=["metadata"])
api_router.include_router(storage_admin.router, prefix="/admin/storage", tags=["storage-admin"])