from pydantic import BaseModel
from typing import List, Optional, Dict

class SearchQuery(BaseModel):
    query: str
    top_k: int = 10
    filters: Optional[Dict] = None
    include_citations: bool = True

class SearchResponse(BaseModel):
    message: str
    query: Optional[str] = None
    results: Optional[List[Dict]] = None
    citations: Optional[List[Dict]] = None