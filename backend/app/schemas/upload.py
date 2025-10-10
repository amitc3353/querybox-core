from pydantic import BaseModel
from typing import Optional, Dict

class UploadResponse(BaseModel):
    message: str
    filename: Optional[str] = None
    document_id: Optional[str] = None
    upload_url: Optional[str] = None