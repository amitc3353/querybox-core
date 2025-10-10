from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class DocumentResponse(BaseModel):
    id: str
    filename: Optional[str] = None
    size: Optional[int] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    message: Optional[str] = None