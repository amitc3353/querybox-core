"""
Parser factory for config-driven parser selection.

Enables swapping document parsers via configuration without code changes.
"""

import logging
from typing import Optional

from app.services.parsers.base import DocumentParser
from app.services.parsers.docling_parser import DoclingParser

logger = logging.getLogger(__name__)


def get_parser(parser_name: Optional[str] = None) -> DocumentParser:
    """
    Get document parser based on configuration.

    This factory function returns the appropriate parser implementation
    based on the PARSER_PRIMARY config setting (or override parameter).

    Args:
        parser_name: Optional parser name to override config
                    Options: "docling", "mineru", "unstructured"
                    If None, uses settings.PARSER_PRIMARY

    Returns:
        DocumentParser instance

    Raises:
        ValueError: If parser_name is unknown

    Example:
        # Use default from config
        parser = get_parser()
        result = parser.parse("document.pdf")

        # Override for specific use case
        mineru_parser = get_parser("mineru")
        result = mineru_parser.parse("table-heavy.pdf")
    """
    # Import settings here to avoid circular imports
    from app.core.config import settings

    # Use provided name or fall back to config
    name = parser_name or settings.PARSER_PRIMARY

    logger.debug(f"Creating parser: {name}")

    if name == "docling":
        return DoclingParser()

    # Future parsers (uncomment when implemented):
    # elif name == "mineru":
    #     from app.services.parsers.mineru_parser import MinerUParser
    #     return MinerUParser()
    #
    # elif name == "unstructured":
    #     from app.services.parsers.unstructured_parser import UnstructuredParser
    #     return UnstructuredParser()
    #
    # elif name == "smart":
    #     from app.services.parsers.router import SmartParsingService
    #     return SmartParsingService()

    else:
        available = ["docling"]  # Add others as implemented
        raise ValueError(
            f"Unknown parser: '{name}'. Available options: {', '.join(available)}"
        )


def get_available_parsers() -> list[str]:
    """
    Get list of available parser names.

    Returns:
        List of parser names that can be used with get_parser()
    """
    return ["docling"]  # Add others as implemented
