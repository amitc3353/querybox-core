from fastapi import APIRouter
from app.schemas.search import SearchQuery, SearchResponse

router = APIRouter()

@router.post("/", response_model=SearchResponse)
async def search_documents(query: SearchQuery):
    return {"message": "Search endpoint - to be implemented", "query": query.query}