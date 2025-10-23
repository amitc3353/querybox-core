"""
Chunking Service Package
Exports chunking functionality for text splitting
"""

from app.services.chunking.chunking_service import (
    ChunkingService,
    ChunkData,
    ChunkingResult,
    get_chunking_service,
)

__all__ = [
    "ChunkingService",
    "ChunkData",
    "ChunkingResult",
    "get_chunking_service",
]
