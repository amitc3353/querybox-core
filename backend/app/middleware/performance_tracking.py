"""
Performance Tracking Middleware

Automatically tracks performance metrics for all API requests:
- Request/response latency
- HTTP status codes
- Error rates
- Request paths and methods
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable
import time
import logging
from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# ============================================================================
# HTTP REQUEST METRICS
# ============================================================================

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "status_code"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30]
)

http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "path"],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000, 31457280]
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "path", "status_code"],
    buckets=[100, 1000, 10000, 100000, 1000000]
)

http_errors_total = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "path", "status_code", "error_type"]
)


class PerformanceTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track performance metrics for all API requests.

    Tracks:
    - Request latency
    - Request/response sizes
    - Status codes
    - Error rates
    """

    def __init__(self, app: ASGIApp, track_request_body: bool = True, track_response_body: bool = True):
        """
        Initialize performance tracking middleware.

        Args:
            app: ASGI application
            track_request_body: Whether to track request body size (may impact performance)
            track_response_body: Whether to track response body size (may impact performance)
        """
        super().__init__(app)
        self.track_request_body = track_request_body
        self.track_response_body = track_response_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and track performance metrics.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response object
        """
        start_time = time.time()

        # Extract request info
        method = request.method
        path = self._normalize_path(request.url.path)

        # Track request size (if enabled)
        if self.track_request_body:
            request_size = int(request.headers.get("content-length", 0))
            if request_size > 0:
                http_request_size_bytes.labels(method=method, path=path).observe(request_size)

        # Process request
        response = None
        status_code = 500  # Default to server error
        error_type = None

        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception as e:
            error_type = type(e).__name__
            status_code = 500

            # Log error
            logger.error(
                f"Request failed: {method} {path}",
                extra={
                    "method": method,
                    "path": path,
                    "error_type": error_type,
                    "error_message": str(e)
                },
                exc_info=True
            )

            # Record error metric
            http_errors_total.labels(
                method=method,
                path=path,
                status_code=status_code,
                error_type=error_type
            ).inc()

            # Re-raise to let error handlers deal with it
            raise

        finally:
            # Calculate latency
            duration = time.time() - start_time

            # Record metrics
            http_requests_total.labels(
                method=method,
                path=path,
                status_code=status_code
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                path=path,
                status_code=status_code
            ).observe(duration)

            # Track response size (if enabled and response exists)
            if self.track_response_body and response is not None:
                response_size = int(response.headers.get("content-length", 0))
                if response_size > 0:
                    http_response_size_bytes.labels(
                        method=method,
                        path=path,
                        status_code=status_code
                    ).observe(response_size)

            # Log request details
            log_level = logging.INFO if status_code < 400 else logging.WARNING
            logger.log(
                log_level,
                f"{method} {path} - {status_code} ({duration*1000:.1f}ms)",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "latency_ms": int(duration * 1000),
                    "error_type": error_type
                }
            )

        return response

    def _normalize_path(self, path: str) -> str:
        """
        Normalize path for metric labels to avoid cardinality explosion.

        Replaces document IDs and other variable parts with placeholders.

        Args:
            path: Original request path

        Returns:
            Normalized path
        """
        # Skip normalization for static paths
        if path in ["/", "/health", "/metrics", "/docs", "/openapi.json"]:
            return path

        # Replace UUIDs and numeric IDs
        import re

        # Replace UUIDs (e.g., /documents/123e4567-e89b-12d3-a456-426614174000)
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path,
            flags=re.IGNORECASE
        )

        # Replace numeric IDs (e.g., /documents/123)
        path = re.sub(r'/\d+', '/{id}', path)

        return path


# ============================================================================
# REQUEST CONTEXT TRACKING
# ============================================================================

class RequestContext:
    """
    Context manager for tracking multi-stage request performance.

    Useful for tracking sub-operations within a single request.

    Example:
        with RequestContext("document_processing") as ctx:
            # Stage 1: Upload
            ctx.start_stage("upload")
            upload_file()
            ctx.end_stage("upload")

            # Stage 2: Extract
            ctx.start_stage("extract")
            extract_text()
            ctx.end_stage("extract")

            ctx.complete()
    """

    def __init__(self, operation_name: str):
        """
        Initialize request context.

        Args:
            operation_name: Name of the operation being tracked
        """
        self.operation_name = operation_name
        self.start_time = None
        self.stages = {}
        self.current_stage = None

    def __enter__(self):
        """Start tracking."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End tracking."""
        if exc_type is not None:
            logger.error(
                f"Operation '{self.operation_name}' failed",
                extra={
                    "operation": self.operation_name,
                    "error_type": exc_type.__name__,
                    "error_message": str(exc_val)
                },
                exc_info=True
            )
        return False

    def start_stage(self, stage_name: str):
        """Start tracking a stage."""
        self.current_stage = stage_name
        self.stages[stage_name] = {"start": time.time()}

    def end_stage(self, stage_name: str):
        """End tracking a stage."""
        if stage_name in self.stages and "start" in self.stages[stage_name]:
            duration = time.time() - self.stages[stage_name]["start"]
            self.stages[stage_name]["duration"] = duration
            self.stages[stage_name]["duration_ms"] = int(duration * 1000)

    def complete(self):
        """Mark operation as complete and log summary."""
        total_duration = time.time() - self.start_time

        logger.info(
            f"Operation '{self.operation_name}' completed",
            extra={
                "operation": self.operation_name,
                "total_duration_ms": int(total_duration * 1000),
                "stages": {
                    name: stage.get("duration_ms", 0)
                    for name, stage in self.stages.items()
                }
            }
        )

    def get_summary(self) -> dict:
        """Get operation summary."""
        total_duration = time.time() - self.start_time if self.start_time else 0

        return {
            "operation": self.operation_name,
            "total_duration_ms": int(total_duration * 1000),
            "stages": {
                name: {
                    "duration_ms": stage.get("duration_ms", 0),
                    "duration_seconds": stage.get("duration", 0)
                }
                for name, stage in self.stages.items()
            }
        }
