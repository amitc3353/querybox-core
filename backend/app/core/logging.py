"""
Logging configuration for QueryBox Core

Integrates structlog with Sentry for centralized logging and error tracking.
Supports structured JSON logs with context propagation for multi-tenant filtering.
"""

import logging
import sys
from typing import Any

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
    Configure logging with structlog and Sentry integration.

    Sets up:
    1. structlog with JSON formatting
    2. Sentry for error tracking and logging (if DSN provided)
    3. Console handler for local development
    4. Context propagation for multi-tenant labels
    """
    # Determine log level from settings
    log_level_str = settings.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Initialize Sentry (if enabled)
    if hasattr(settings, "SENTRY_DSN") and settings.SENTRY_DSN:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration

            # Configure Sentry logging integration
            sentry_logging = LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors and above as events
            )

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=getattr(settings, "SENTRY_ENVIRONMENT", "development"),
                traces_sample_rate=getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 1.0),
                integrations=[sentry_logging],
                # Send default PII (like user IDs) for better debugging
                send_default_pii=True,
                # Enable performance monitoring
                enable_tracing=True,
            )

            print(f"✅ Sentry logging enabled (environment: {getattr(settings, 'SENTRY_ENVIRONMENT', 'development')})")
        except ImportError:
            print("⚠️  sentry-sdk not installed. Run: pip install sentry-sdk")
        except Exception as e:
            print(f"⚠️  Failed to initialize Sentry: {e}")
    else:
        print("ℹ️  Sentry logging disabled (no SENTRY_DSN configured)")

    # Console handler (always enabled for development)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Configure standard logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s",  # structlog handles formatting
        handlers=[console_handler],
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
            # Render to JSON for structured logging
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
        sentry_enabled=bool(hasattr(settings, "SENTRY_DSN") and settings.SENTRY_DSN),
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
