"""
Abstract base class for document parsers.

This module defines the interface that all document parsers must implement,
enabling swappable parsing strategies (Docling, MinerU, Unstructured, etc.)
without changing the core application logic.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path


class ParseResult:
    """
    Standardized result object returned by all parsers.

    Attributes:
        text: Extracted text content
        metadata: Parser-specific metadata (method, engine, quality, etc.)
        confidence: Confidence score for parsing quality (0.0-1.0)
        images: List of extracted images with metadata
        tables: List of extracted tables
        error: Error message if parsing partially failed
    """

    def __init__(
        self,
        text: str,
        metadata: Dict[str, Any],
        confidence: float = 1.0,
        images: Optional[List[Dict[str, Any]]] = None,
        tables: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None
    ):
        self.text = text
        self.metadata = metadata
        self.confidence = confidence
        self.images = images or []
        self.tables = tables or []
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "text": self.text,
            "metadata": self.metadata,
            "confidence": self.confidence,
            "images": self.images,
            "tables": self.tables,
            "error": self.error
        }


class DocumentParser(ABC):
    """
    Abstract base class for document parsers.

    All parser implementations (Docling, MinerU, Unstructured, etc.) must
    inherit from this class and implement its abstract methods.

    Example:
        class DoclingParser(DocumentParser):
            def parse(self, file_path: str, **kwargs) -> ParseResult:
                # Implementation here
                pass
    """

    def __init__(self, name: str):
        """
        Initialize parser.

        Args:
            name: Human-readable name for this parser (e.g., "docling", "mineru")
        """
        self.name = name

    @abstractmethod
    def parse(self, file_path: str, **kwargs) -> ParseResult:
        """
        Parse a document and extract text, metadata, and structured content.

        Args:
            file_path: Path to the document file
            **kwargs: Parser-specific options (e.g., enable_ocr, extract_tables)

        Returns:
            ParseResult object containing extracted content and metadata

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
            Exception: For other parsing errors
        """
        pass

    @abstractmethod
    def supports_format(self, file_extension: str) -> bool:
        """
        Check if this parser supports the given file format.

        Args:
            file_extension: File extension (e.g., "pdf", "docx", "pptx")

        Returns:
            True if format is supported, False otherwise
        """
        pass

    def get_confidence(self, result: ParseResult) -> float:
        """
        Get confidence score for a parsing result.

        This is a default implementation that can be overridden by subclasses
        for more sophisticated confidence calculation.

        Args:
            result: ParseResult object from parse()

        Returns:
            Confidence score between 0.0 (low confidence) and 1.0 (high confidence)
        """
        return result.confidence

    def validate_file(self, file_path: str) -> None:
        """
        Validate that the file exists and is readable.

        Args:
            file_path: Path to the file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is empty or not readable
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        if path.stat().st_size == 0:
            raise ValueError(f"File is empty: {file_path}")

    def get_file_extension(self, file_path: str) -> str:
        """
        Extract file extension from path.

        Args:
            file_path: Path to the file

        Returns:
            File extension without dot (e.g., "pdf", "docx")
        """
        return Path(file_path).suffix.lstrip('.').lower()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
