"""
Pipeline Performance Metrics - E2E Testing & Monitoring

Comprehensive metrics tracking for all pipeline stages:
- Upload & Validation
- Text Extraction
- Chunking
- Embedding Generation
- Search (Vector, BM25, Hybrid, Reranking)
- Answer Generation & Verification

Usage:
    from app.monitoring.pipeline_metrics import track_pipeline_stage

    @track_pipeline_stage("upload")
    async def upload_document(...):
        ...
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
from typing import Dict, Any, Optional, List
import time
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ============================================================================
# PIPELINE STAGE METRICS
# ============================================================================

# Request counters by stage
pipeline_requests_total = Counter(
    "pipeline_requests_total",
    "Total requests by pipeline stage",
    ["stage", "status"]  # stage: upload, extraction, chunking, etc. status: success, error
)

# Latency histograms by stage
pipeline_stage_latency_seconds = Histogram(
    "pipeline_stage_latency_seconds",
    "Latency per pipeline stage in seconds",
    ["stage"],  # upload, extraction, chunking, embedding, search, answer
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60, 120]
)

# Error counters by stage and type
pipeline_errors_total = Counter(
    "pipeline_errors_total",
    "Total errors by pipeline stage and type",
    ["stage", "error_type"]
)

# Active/concurrent operations by stage
pipeline_active_operations = Gauge(
    "pipeline_active_operations",
    "Number of currently active operations by stage",
    ["stage"]
)

# ============================================================================
# UPLOAD STAGE METRICS
# ============================================================================

upload_file_size_bytes = Histogram(
    "upload_file_size_bytes",
    "Uploaded file size distribution in bytes",
    buckets=[1024, 10240, 102400, 1048576, 10485760, 31457280]  # 1KB to 30MB
)

upload_file_type_total = Counter(
    "upload_file_type_total",
    "Total uploads by file type",
    ["file_type"]  # pdf, docx, txt, etc.
)

upload_validation_failures_total = Counter(
    "upload_validation_failures_total",
    "Upload validation failures by reason",
    ["reason"]  # size_exceeded, invalid_type, corrupted, etc.
)

# ============================================================================
# EXTRACTION STAGE METRICS
# ============================================================================

extraction_pages_processed = Histogram(
    "extraction_pages_processed",
    "Number of pages processed per document",
    buckets=[1, 5, 10, 25, 50, 100, 200, 500]
)

extraction_text_length_chars = Histogram(
    "extraction_text_length_chars",
    "Extracted text length distribution in characters",
    buckets=[100, 1000, 10000, 50000, 100000, 500000, 1000000]
)

extraction_method_total = Counter(
    "extraction_method_total",
    "Extraction method used",
    ["method"]  # pdfplumber, pytesseract, docx, etc.
)

# ============================================================================
# CHUNKING STAGE METRICS
# ============================================================================

chunking_chunks_created = Histogram(
    "chunking_chunks_created",
    "Number of chunks created per document",
    buckets=[1, 5, 10, 25, 50, 100, 200, 500, 1000]
)

chunking_chunk_size_tokens = Histogram(
    "chunking_chunk_size_tokens",
    "Chunk size distribution in tokens",
    buckets=[50, 100, 200, 500, 800, 1000, 1200, 1500]
)

chunking_method_total = Counter(
    "chunking_method_total",
    "Chunking method used",
    ["method"]  # semantic, fixed_size, sentence_based
)

# ============================================================================
# EMBEDDING STAGE METRICS
# ============================================================================

embedding_generation_latency_seconds = Histogram(
    "embedding_generation_latency_seconds",
    "Embedding generation latency per batch",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 20, 30]
)

embedding_batch_size = Histogram(
    "embedding_batch_size",
    "Number of chunks per embedding batch",
    buckets=[1, 10, 25, 50, 100, 200]
)

embedding_model_calls_total = Counter(
    "embedding_model_calls_total",
    "Total embedding model calls",
    ["model_name"]
)

# ============================================================================
# SEARCH STAGE METRICS
# ============================================================================

search_query_latency_seconds = Histogram(
    "search_query_latency_seconds",
    "Search query total latency",
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1, 2, 5]
)

search_results_returned = Histogram(
    "search_results_returned",
    "Number of results returned per search",
    buckets=[0, 1, 5, 10, 20, 50, 100]
)

search_method_total = Counter(
    "search_method_total",
    "Search method used",
    ["method"]  # vector, keyword, hybrid, reranked
)

search_cache_hits_total = Counter(
    "search_cache_hits_total",
    "Search cache hits vs misses",
    ["hit"]  # true, false
)

# ============================================================================
# ANSWER GENERATION STAGE METRICS
# ============================================================================

answer_generation_latency_seconds = Histogram(
    "answer_generation_latency_seconds",
    "Answer generation latency",
    buckets=[0.5, 1, 2, 5, 10, 20, 30, 60]
)

answer_llm_calls_total = Counter(
    "answer_llm_calls_total",
    "LLM calls for answer generation",
    ["llm_provider"]  # openai, claude, ollama
)

answer_token_usage = Histogram(
    "answer_token_usage",
    "Token usage per answer generation",
    ["token_type"],  # input, output
    buckets=[100, 500, 1000, 2000, 4000, 8000, 16000]
)

# ============================================================================
# PERFORMANCE TRACKING DECORATOR
# ============================================================================

def track_pipeline_stage(stage_name: str):
    """
    Decorator to automatically track performance metrics for pipeline stages.

    Args:
        stage_name: Name of the pipeline stage (upload, extraction, chunking, etc.)

    Example:
        @track_pipeline_stage("upload")
        async def upload_document(file):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Increment active operations
            pipeline_active_operations.labels(stage=stage_name).inc()
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # Record success
                elapsed = time.time() - start_time
                pipeline_stage_latency_seconds.labels(stage=stage_name).observe(elapsed)
                pipeline_requests_total.labels(stage=stage_name, status="success").inc()

                logger.info(
                    f"Pipeline stage '{stage_name}' completed successfully",
                    extra={
                        "stage": stage_name,
                        "latency_ms": int(elapsed * 1000),
                        "status": "success"
                    }
                )

                return result

            except Exception as e:
                # Record error
                elapsed = time.time() - start_time
                error_type = type(e).__name__

                pipeline_requests_total.labels(stage=stage_name, status="error").inc()
                pipeline_errors_total.labels(stage=stage_name, error_type=error_type).inc()

                logger.error(
                    f"Pipeline stage '{stage_name}' failed",
                    extra={
                        "stage": stage_name,
                        "latency_ms": int(elapsed * 1000),
                        "status": "error",
                        "error_type": error_type,
                        "error_message": str(e)
                    },
                    exc_info=True
                )

                raise

            finally:
                # Decrement active operations
                pipeline_active_operations.labels(stage=stage_name).dec()

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Increment active operations
            pipeline_active_operations.labels(stage=stage_name).inc()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # Record success
                elapsed = time.time() - start_time
                pipeline_stage_latency_seconds.labels(stage=stage_name).observe(elapsed)
                pipeline_requests_total.labels(stage=stage_name, status="success").inc()

                logger.info(
                    f"Pipeline stage '{stage_name}' completed successfully",
                    extra={
                        "stage": stage_name,
                        "latency_ms": int(elapsed * 1000),
                        "status": "success"
                    }
                )

                return result

            except Exception as e:
                # Record error
                elapsed = time.time() - start_time
                error_type = type(e).__name__

                pipeline_requests_total.labels(stage=stage_name, status="error").inc()
                pipeline_errors_total.labels(stage=stage_name, error_type=error_type).inc()

                logger.error(
                    f"Pipeline stage '{stage_name}' failed",
                    extra={
                        "stage": stage_name,
                        "latency_ms": int(elapsed * 1000),
                        "status": "error",
                        "error_type": error_type,
                        "error_message": str(e)
                    },
                    exc_info=True
                )

                raise

            finally:
                # Decrement active operations
                pipeline_active_operations.labels(stage=stage_name).dec()

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================================
# MANUAL METRIC RECORDING FUNCTIONS
# ============================================================================

class PipelineMetricsRecorder:
    """Helper class to manually record specific pipeline metrics."""

    @staticmethod
    def record_upload(file_size: int, file_type: str, success: bool = True):
        """Record file upload metrics."""
        upload_file_size_bytes.observe(file_size)
        upload_file_type_total.labels(file_type=file_type).inc()
        if success:
            pipeline_requests_total.labels(stage="upload", status="success").inc()

    @staticmethod
    def record_upload_failure(reason: str):
        """Record upload validation failure."""
        upload_validation_failures_total.labels(reason=reason).inc()
        pipeline_requests_total.labels(stage="upload", status="error").inc()

    @staticmethod
    def record_extraction(pages: int, text_length: int, method: str):
        """Record text extraction metrics."""
        extraction_pages_processed.observe(pages)
        extraction_text_length_chars.observe(text_length)
        extraction_method_total.labels(method=method).inc()

    @staticmethod
    def record_chunking(chunk_count: int, avg_chunk_size_tokens: int, method: str):
        """Record chunking metrics."""
        chunking_chunks_created.observe(chunk_count)
        chunking_chunk_size_tokens.observe(avg_chunk_size_tokens)
        chunking_method_total.labels(method=method).inc()

    @staticmethod
    def record_embedding(batch_size: int, latency_seconds: float, model_name: str):
        """Record embedding generation metrics."""
        embedding_batch_size.observe(batch_size)
        embedding_generation_latency_seconds.observe(latency_seconds)
        embedding_model_calls_total.labels(model_name=model_name).inc()

    @staticmethod
    def record_search(latency_seconds: float, results_count: int, method: str, cache_hit: bool = False):
        """Record search metrics."""
        search_query_latency_seconds.observe(latency_seconds)
        search_results_returned.observe(results_count)
        search_method_total.labels(method=method).inc()
        search_cache_hits_total.labels(hit=str(cache_hit).lower()).inc()

    @staticmethod
    def record_answer(latency_seconds: float, llm_provider: str, input_tokens: int, output_tokens: int):
        """Record answer generation metrics."""
        answer_generation_latency_seconds.observe(latency_seconds)
        answer_llm_calls_total.labels(llm_provider=llm_provider).inc()
        answer_token_usage.labels(token_type="input").observe(input_tokens)
        answer_token_usage.labels(token_type="output").observe(output_tokens)


# ============================================================================
# METRICS SUMMARY FOR DASHBOARD
# ============================================================================

def get_pipeline_metrics_summary() -> Dict[str, Any]:
    """
    Get a human-readable summary of pipeline metrics.

    Returns:
        Dictionary with metrics summary for each pipeline stage
    """
    from prometheus_client import REGISTRY

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stages": {},
        "errors": {},
        "active_operations": {}
    }

    # Collect metrics from registry
    for metric in REGISTRY.collect():
        metric_name = metric.name

        # Pipeline stage latencies
        if metric_name == "pipeline_stage_latency_seconds":
            for sample in metric.samples:
                if sample.name.endswith("_sum"):
                    stage = sample.labels.get("stage", "unknown")
                    if stage not in summary["stages"]:
                        summary["stages"][stage] = {"total_time_seconds": 0, "request_count": 0}
                    summary["stages"][stage]["total_time_seconds"] = sample.value
                elif sample.name.endswith("_count"):
                    stage = sample.labels.get("stage", "unknown")
                    if stage not in summary["stages"]:
                        summary["stages"][stage] = {"total_time_seconds": 0, "request_count": 0}
                    summary["stages"][stage]["request_count"] = int(sample.value)

        # Errors by stage
        elif metric_name == "pipeline_errors_total":
            for sample in metric.samples:
                stage = sample.labels.get("stage", "unknown")
                error_type = sample.labels.get("error_type", "unknown")
                if stage not in summary["errors"]:
                    summary["errors"][stage] = {}
                summary["errors"][stage][error_type] = int(sample.value)

        # Active operations
        elif metric_name == "pipeline_active_operations":
            for sample in metric.samples:
                stage = sample.labels.get("stage", "unknown")
                summary["active_operations"][stage] = int(sample.value)

    # Calculate average latencies
    for stage, data in summary["stages"].items():
        if data["request_count"] > 0:
            data["avg_latency_seconds"] = round(data["total_time_seconds"] / data["request_count"], 3)
            data["avg_latency_ms"] = round(data["avg_latency_seconds"] * 1000, 1)
        else:
            data["avg_latency_seconds"] = 0
            data["avg_latency_ms"] = 0

    return summary


def get_prometheus_metrics() -> str:
    """Get metrics in Prometheus format."""
    return generate_latest().decode('utf-8')


def get_prometheus_content_type() -> str:
    """Get Prometheus metrics content type."""
    return CONTENT_TYPE_LATEST
