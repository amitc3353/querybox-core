"""
Logging configuration for QueryBox Core (Step 13.5)

Integrates structlog with Better Stack (Logtail) for centralized logging.
Supports structured JSON logs with context propagation for multi-tenant filtering.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.types import EventDict, Processor

from app.core.config import settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add application-level context to all log messages.

    This processor adds:
    - service: "backend" (identifies logs from backend vs frontend)
    - environment: from ENV variable (dev/staging/prod)
    """
    event_dict["service"] = "backend"
    event_dict["environment"] = getattr(settings, "ENVIRONMENT", "development")
    return event_dict


def configure_logging() -> None:
    """
    Configure logging with structlog and Better Stack (Logtail) integration.

    Sets up:
    1. structlog with JSON formatting
    2. Better Stack handler (if enabled and token provided)
    3. Console handler for local development
    4. Context propagation for multi-tenant labels
    """
    # Determine log level from settings
    log_level_str = settings.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Create handlers list
    handlers: list = []

    # Console handler (always enabled for development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    handlers.append(console_handler)

    # Better Stack (Logtail) handler (if enabled)
    if settings.LOGTAIL_ENABLED and settings.LOGTAIL_SOURCE_TOKEN:
        try:
            from logtail import LogtailHandler

            logtail_handler = LogtailHandler(source_token=settings.LOGTAIL_SOURCE_TOKEN)
            logtail_handler.setLevel(log_level)
            handlers.append(logtail_handler)

            # Log successful initialization to console
            print(f"✅ Better Stack logging enabled (log level: {log_level_str})")
        except ImportError:
            print("⚠️  logtail-python not installed. Run: pip install logtail-python")
        except Exception as e:
            print(f"⚠️  Failed to initialize Better Stack logging: {e}")
    else:
        if not settings.LOGTAIL_SOURCE_TOKEN:
            print("ℹ️  Better Stack logging disabled (no LOGTAIL_SOURCE_TOKEN)")
        else:
            print("ℹ️  Better Stack logging disabled (LOGTAIL_ENABLED=False)")

    # Configure standard logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s",  # structlog handles formatting
        handlers=handlers,
        force=True,  # Override any existing configuration
    )

    # Configure structlog processors
    shared_processors: list[Processor] = [
        # Add contextvar-bound variables (client_id, service, module)
        structlog.contextvars.merge_contextvars,
        # Add log level
        structlog.processors.add_log_level,
        # Add timestamp in ISO format
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add application context (service, environment)
        add_app_context,
        # Add stack info for exceptions
        structlog.processors.StackInfoRenderer(),
        # Format exceptions nicely
        structlog.processors.format_exc_info,
    ]

    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            # Render to JSON for Better Stack
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Log initial message
    logger = structlog.get_logger()
    logger.info(
        "QueryBox logging initialized",
        log_level=log_level_str,
        logtail_enabled=settings.LOGTAIL_ENABLED,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structlog logger instance.

    Args:
        name: Optional logger name (usually __name__)

    Returns:
        Configured structlog logger

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing document", document_id=doc_id, client_id=client_id)
    """
    return structlog.get_logger(name)
