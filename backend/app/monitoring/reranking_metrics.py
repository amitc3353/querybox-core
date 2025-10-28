"""
Reranking Metrics for Prometheus (Step 10.2 - Phase 5)

This module provides Prometheus metrics for monitoring reranking operations:
- Cross-encoder reranking
- MMR diversity ranking
- Deduplication
- Full pipeline execution

Follows the same pattern as storage_metrics.py for consistency.
"""
import time
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

# Try importing prometheus_client, provide fallback if not available
try:
    from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Fallback mock classes when prometheus_client not available
    class Counter:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            pass

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
        def observe(self, *args, **kwargs):
            pass

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
        def set(self, *args, **kwargs):
            pass

    class Info:
        def __init__(self, *args, **kwargs):
            pass
        def info(self, *args, **kwargs):
            pass

    def generate_latest():
        return b""

    CONTENT_TYPE_LATEST = "text/plain"


# ============================================================================
# Metric Definitions
# ============================================================================

# Total reranking requests
reranking_requests_total = Counter(
    'reranking_requests_total',
    'Total number of reranking requests',
    ['strategy', 'status']  # strategy: cross_encoder, mmr, dedup, full_pipeline; status: success, failure
)

# Reranking latency per stage
reranking_latency_seconds = Histogram(
    'reranking_latency_seconds',
    'Reranking latency in seconds by stage',
    ['stage'],  # stage: cross_encoder, mmr, deduplication, full_pipeline
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# MMR diversity score (gauge for current value)
mmr_diversity_score = Gauge(
    'mmr_diversity_score',
    'Current MMR diversity score (0.0-1.0)'
)

# Deduplication metrics
deduplication_removed_total = Counter(
    'deduplication_removed_total',
    'Total number of duplicates removed',
    ['dedup_type']  # dedup_type: exact_chunk_id, content_hash, semantic_embedding
)

deduplication_rate = Gauge(
    'deduplication_rate',
    'Current deduplication rate (duplicates removed / total candidates)'
)

# Full pipeline latency
pipeline_latency_seconds = Histogram(
    'pipeline_latency_seconds',
    'Full reranking pipeline latency in seconds',
    buckets=[0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Reranking failures
reranking_failures_total = Counter(
    'reranking_failures_total',
    'Total number of reranking failures',
    ['stage', 'error_type']  # stage: cross_encoder, mmr, dedup, pipeline; error_type: model_error, oom_error, etc.
)

# Candidate count metrics
reranking_candidates_total = Counter(
    'reranking_candidates_total',
    'Total number of candidates processed',
    ['stage']  # stage: input, cross_encoder_output, dedup_output, mmr_output
)

# Model loading status
reranking_model_info = Info(
    'reranking_model_info',
    'Reranking model information'
)

# GPU usage metrics
reranking_gpu_available = Gauge(
    'reranking_gpu_available',
    'Whether GPU is available for reranking (1=yes, 0=no)'
)


# ============================================================================
# Metrics Collector Class
# ============================================================================

class RerankingMetricsCollector:
    """
    Collector class for reranking metrics.

    Provides methods to record various reranking operations and automatically
    track metrics like latency, success/failure rates, and diversity scores.
    """

    def __init__(self):
        """Initialize the metrics collector"""
        self.prometheus_available = PROMETHEUS_AVAILABLE

    # ------------------------------------------------------------------------
    # General Reranking Metrics
    # ------------------------------------------------------------------------

    def record_reranking_request(
        self,
        strategy: str,
        status: str,
        duration: float,
        candidate_count: int
    ):
        """
        Record a reranking request.

        Args:
            strategy: Reranking strategy (cross_encoder, mmr, dedup, full_pipeline)
            status: Request status (success, failure)
            duration: Duration in seconds
            candidate_count: Number of candidates processed
        """
        reranking_requests_total.labels(strategy=strategy, status=status).inc()
        reranking_latency_seconds.labels(stage=strategy).observe(duration)
        reranking_candidates_total.labels(stage=strategy).inc(candidate_count)

    # ------------------------------------------------------------------------
    # Cross-Encoder Metrics
    # ------------------------------------------------------------------------

    def record_cross_encoder_reranking(
        self,
        status: str,
        duration: float,
        input_count: int,
        output_count: int,
        error_type: Optional[str] = None
    ):
        """
        Record cross-encoder reranking operation.

        Args:
            status: Operation status (success, failure)
            duration: Duration in seconds
            input_count: Number of input candidates
            output_count: Number of output candidates
            error_type: Error type if failed (e.g., model_error, oom_error)
        """
        reranking_requests_total.labels(strategy='cross_encoder', status=status).inc()
        reranking_latency_seconds.labels(stage='cross_encoder').observe(duration)
        reranking_candidates_total.labels(stage='cross_encoder_input').inc(input_count)
        reranking_candidates_total.labels(stage='cross_encoder_output').inc(output_count)

        if status == 'failure' and error_type:
            reranking_failures_total.labels(stage='cross_encoder', error_type=error_type).inc()

    # ------------------------------------------------------------------------
    # MMR Metrics
    # ------------------------------------------------------------------------

    def record_mmr_reranking(
        self,
        status: str,
        duration: float,
        diversity_score: float,
        input_count: int,
        output_count: int,
        lambda_param: float,
        error_type: Optional[str] = None
    ):
        """
        Record MMR reranking operation.

        Args:
            status: Operation status (success, failure)
            duration: Duration in seconds
            diversity_score: Calculated diversity score (0.0-1.0)
            input_count: Number of input candidates
            output_count: Number of output candidates
            lambda_param: Lambda parameter used (0.0-1.0)
            error_type: Error type if failed
        """
        reranking_requests_total.labels(strategy='mmr', status=status).inc()
        reranking_latency_seconds.labels(stage='mmr').observe(duration)
        mmr_diversity_score.set(diversity_score)
        reranking_candidates_total.labels(stage='mmr_input').inc(input_count)
        reranking_candidates_total.labels(stage='mmr_output').inc(output_count)

        if status == 'failure' and error_type:
            reranking_failures_total.labels(stage='mmr', error_type=error_type).inc()

    # ------------------------------------------------------------------------
    # Deduplication Metrics
    # ------------------------------------------------------------------------

    def record_deduplication(
        self,
        status: str,
        duration: float,
        original_count: int,
        deduplicated_count: int,
        duplicates_by_type: Dict[str, int],
        error_type: Optional[str] = None
    ):
        """
        Record deduplication operation.

        Args:
            status: Operation status (success, failure)
            duration: Duration in seconds
            original_count: Number of original candidates
            deduplicated_count: Number after deduplication
            duplicates_by_type: Dict mapping dedup_type to count removed
                               (e.g., {'exact_chunk_id': 5, 'content_hash': 2})
            error_type: Error type if failed
        """
        reranking_requests_total.labels(strategy='dedup', status=status).inc()
        reranking_latency_seconds.labels(stage='deduplication').observe(duration)
        reranking_candidates_total.labels(stage='dedup_input').inc(original_count)
        reranking_candidates_total.labels(stage='dedup_output').inc(deduplicated_count)

        # Record duplicates removed by type
        for dedup_type, count in duplicates_by_type.items():
            deduplication_removed_total.labels(dedup_type=dedup_type).inc(count)

        # Calculate and record deduplication rate
        if original_count > 0:
            rate = (original_count - deduplicated_count) / original_count
            deduplication_rate.set(rate)

        if status == 'failure' and error_type:
            reranking_failures_total.labels(stage='deduplication', error_type=error_type).inc()

    # ------------------------------------------------------------------------
    # Full Pipeline Metrics
    # ------------------------------------------------------------------------

    def record_pipeline_execution(
        self,
        status: str,
        duration: float,
        input_count: int,
        output_count: int,
        pipeline_stats: Optional[Dict[str, Any]] = None,
        error_type: Optional[str] = None
    ):
        """
        Record full reranking pipeline execution.

        Args:
            status: Operation status (success, failure)
            duration: Total duration in seconds
            input_count: Number of input candidates
            output_count: Number of final output candidates
            pipeline_stats: Optional dict with detailed pipeline stats
            error_type: Error type if failed
        """
        reranking_requests_total.labels(strategy='full_pipeline', status=status).inc()
        pipeline_latency_seconds.observe(duration)
        reranking_candidates_total.labels(stage='pipeline_input').inc(input_count)
        reranking_candidates_total.labels(stage='pipeline_output').inc(output_count)

        # Record individual stage metrics from pipeline stats
        if pipeline_stats:
            # Stage 1: Reranking
            if 'stage1_reranking' in pipeline_stats:
                stage1 = pipeline_stats['stage1_reranking']
                if stage1.get('enabled'):
                    reranking_latency_seconds.labels(stage='cross_encoder').observe(
                        stage1.get('processing_time_ms', 0) / 1000.0
                    )

            # Stage 2: Deduplication
            if 'stage2_deduplication' in pipeline_stats:
                stage2 = pipeline_stats['stage2_deduplication']
                if stage2.get('enabled'):
                    reranking_latency_seconds.labels(stage='deduplication').observe(
                        stage2.get('processing_time_ms', 0) / 1000.0
                    )
                    if 'duplicates_removed' in stage2:
                        deduplication_removed_total.labels(dedup_type='pipeline').inc(
                            stage2['duplicates_removed']
                        )

            # Stage 3: MMR
            if 'stage3_mmr' in pipeline_stats:
                stage3 = pipeline_stats['stage3_mmr']
                if stage3.get('enabled'):
                    reranking_latency_seconds.labels(stage='mmr').observe(
                        stage3.get('processing_time_ms', 0) / 1000.0
                    )
                    if 'diversity_score' in stage3:
                        mmr_diversity_score.set(stage3['diversity_score'])

        if status == 'failure' and error_type:
            reranking_failures_total.labels(stage='pipeline', error_type=error_type).inc()

    # ------------------------------------------------------------------------
    # Model & System Metrics
    # ------------------------------------------------------------------------

    def set_model_info(
        self,
        model_name: str,
        device: str,
        batch_size: int,
        max_length: int
    ):
        """
        Set reranking model information.

        Args:
            model_name: Name of the cross-encoder model
            device: Device (cpu, cuda)
            batch_size: Batch size for inference
            max_length: Max sequence length
        """
        reranking_model_info.info({
            'model_name': model_name,
            'device': device,
            'batch_size': str(batch_size),
            'max_length': str(max_length)
        })

    def set_gpu_availability(self, available: bool):
        """
        Set GPU availability status.

        Args:
            available: Whether GPU is available (True/False)
        """
        reranking_gpu_available.set(1 if available else 0)

    # ------------------------------------------------------------------------
    # Context Managers for Timing
    # ------------------------------------------------------------------------

    @asynccontextmanager
    async def time_cross_encoder_reranking(self, input_count: int):
        """
        Context manager to time cross-encoder reranking.

        Usage:
            async with metrics_collector.time_cross_encoder_reranking(100):
                results = await cross_encoder.rerank(query, candidates, top_k)
        """
        start_time = time.time()
        error_type = None
        status = 'success'
        output_count = 0

        try:
            yield
        except RuntimeError as e:
            status = 'failure'
            if 'CUDA out of memory' in str(e):
                error_type = 'oom_error'
            else:
                error_type = 'model_error'
            raise
        except Exception as e:
            status = 'failure'
            error_type = 'unknown_error'
            raise
        finally:
            duration = time.time() - start_time
            self.record_cross_encoder_reranking(
                status=status,
                duration=duration,
                input_count=input_count,
                output_count=output_count,
                error_type=error_type
            )

    @asynccontextmanager
    async def time_pipeline_execution(self, input_count: int):
        """
        Context manager to time full pipeline execution.

        Usage:
            async with metrics_collector.time_pipeline_execution(100):
                result = pipeline.process(query, candidates, final_top_k, rerank_top_k)
        """
        start_time = time.time()
        error_type = None
        status = 'success'
        output_count = 0

        try:
            yield
        except Exception as e:
            status = 'failure'
            error_type = type(e).__name__
            raise
        finally:
            duration = time.time() - start_time
            self.record_pipeline_execution(
                status=status,
                duration=duration,
                input_count=input_count,
                output_count=output_count,
                error_type=error_type
            )


# ============================================================================
# Global Metrics Collector Instance
# ============================================================================

metrics_collector = RerankingMetricsCollector()


# ============================================================================
# Convenience Functions
# ============================================================================

def get_metrics():
    """
    Get current metrics in Prometheus format.

    Returns:
        bytes: Metrics in Prometheus text format
    """
    if PROMETHEUS_AVAILABLE:
        return generate_latest()
    return b""


def get_metrics_content_type():
    """
    Get the content type for Prometheus metrics.

    Returns:
        str: Content type header value
    """
    return CONTENT_TYPE_LATEST


def is_prometheus_available():
    """
    Check if Prometheus client is available.

    Returns:
        bool: True if prometheus_client is installed
    """
    return PROMETHEUS_AVAILABLE
