"""
Prometheus Metrics for QueryBox Core - Step 11.2

Tracks verification pipeline metrics for monitoring and alerting.
Based on technical documentation Section 9 (Monitoring).
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Dict, Optional
import time


# ============================================================================
# VERIFICATION METRICS (Step 11.2)
# ============================================================================

# Request counters
verification_requests_total = Counter(
    "verification_requests_total",
    "Total verification requests processed",
    ["status"]  # verified, partial, failed, skipped
)

verification_errors_total = Counter(
    "verification_errors_total",
    "Total verification errors by stage",
    ["stage", "error_type"]  # stage: quote_matching, question_gen, etc.
)

# Latency histograms
verification_latency_seconds = Histogram(
    "verification_latency_seconds",
    "Verification pipeline end-to-end latency in seconds",
    buckets=[1, 2, 3, 5, 7, 10, 15, 20, 30]
)

verification_stage_latency_seconds = Histogram(
    "verification_stage_latency_seconds",
    "Latency per verification stage in seconds",
    ["stage"],  # question_gen, verification_exec, quote_matching, hallucination_detection
    buckets=[0.1, 0.25, 0.5, 1, 2, 3, 5, 10]
)

# Hallucination detection metrics
hallucination_probability = Histogram(
    "hallucination_probability",
    "Distribution of hallucination probability scores",
    buckets=[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

propositions_checked_total = Counter(
    "propositions_checked_total",
    "Total number of propositions checked"
)

propositions_verified_total = Counter(
    "propositions_verified_total",
    "Total number of propositions verified (with supporting quotes)"
)

propositions_removed_total = Counter(
    "propositions_removed_total",
    "Total number of propositions removed due to high hallucination probability"
)

propositions_verified_ratio = Histogram(
    "propositions_verified_ratio",
    "Ratio of verified propositions per answer",
    buckets=[0, 0.2, 0.4, 0.6, 0.8, 1.0]
)

# Quote matching metrics
quote_matches_found_total = Counter(
    "quote_matches_found_total",
    "Total number of quote matches found"
)

quote_match_similarity_score = Histogram(
    "quote_match_similarity_score",
    "Distribution of quote match similarity scores",
    buckets=[0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.0]
)

quote_matching_latency_seconds = Histogram(
    "quote_matching_latency_seconds",
    "Quote matching latency per proposition in seconds",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5]
)

# Cache metrics
verification_cache_hits_total = Counter(
    "verification_cache_hits_total",
    "Cache hits by level",
    ["level"]  # l1_verification, l2_quotes, l3_questions
)

verification_cache_misses_total = Counter(
    "verification_cache_misses_total",
    "Cache misses by level",
    ["level"]  # l1_verification, l2_quotes, l3_questions
)

verification_cache_hit_rate = Gauge(
    "verification_cache_hit_rate",
    "Current cache hit rate by level",
    ["level"]  # l1_verification, l2_quotes, l3_questions
)

# Verification questions metrics
verification_questions_generated_total = Counter(
    "verification_questions_generated_total",
    "Total verification questions generated",
    ["type"]  # binary, existence, attribute
)

verification_questions_fallback_total = Counter(
    "verification_questions_fallback_total",
    "Total fallback questions used (template-based)"
)

verification_answers_fallback_total = Counter(
    "verification_answers_fallback_total",
    "Total fallback answers used (LLM unavailable)"
)

# Confidence adjustment metrics
confidence_adjustment = Histogram(
    "confidence_adjustment",
    "Distribution of confidence adjustments after verification",
    buckets=[-0.5, -0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3, 0.5]
)

# Resource utilization
verification_concurrent_requests = Gauge(
    "verification_concurrent_requests",
    "Number of verification requests currently in progress"
)

verification_timeout_total = Counter(
    "verification_timeout_total",
    "Total verification timeouts",
    ["stage"]  # overall, question_gen, verification_exec
)


# ============================================================================
# ANSWER GENERATION METRICS (Step 11.1)
# ============================================================================

answer_requests_total = Counter(
    "answer_requests_total",
    "Total answer generation requests",
    ["source"]  # baseline, verified
)

answer_latency_seconds = Histogram(
    "answer_latency_seconds",
    "Answer generation latency in seconds",
    buckets=[0.5, 1, 2, 3, 5, 7, 10, 15, 20]
)

answer_abstentions_total = Counter(
    "answer_abstentions_total",
    "Total answers where system abstained",
    ["reason"]  # no_documents, low_confidence, verification_failed
)

answer_cache_hits_total = Counter(
    "answer_cache_hits_total",
    "Answer cache hits"
)


# ============================================================================
# METRIC RECORDING FUNCTIONS
# ============================================================================

class VerificationMetricsRecorder:
    """Helper class to record verification metrics."""

    @staticmethod
    def record_verification_request(status: str, latency_ms: int):
        """
        Record verification request completion.

        Args:
            status: "verified", "partial", "failed", or "skipped"
            latency_ms: Total latency in milliseconds
        """
        verification_requests_total.labels(status=status).inc()
        verification_latency_seconds.observe(latency_ms / 1000.0)

    @staticmethod
    def record_stage_latency(stage: str, latency_ms: int):
        """
        Record latency for individual verification stage.

        Args:
            stage: Stage name (question_gen, verification_exec, quote_matching, hallucination_detection)
            latency_ms: Stage latency in milliseconds
        """
        verification_stage_latency_seconds.labels(stage=stage).observe(latency_ms / 1000.0)

    @staticmethod
    def record_hallucination_detection(
        probability: float,
        propositions_checked: int,
        propositions_verified: int,
        propositions_removed: int
    ):
        """
        Record hallucination detection results.

        Args:
            probability: Hallucination probability (0-1)
            propositions_checked: Number of propositions checked
            propositions_verified: Number of propositions with supporting quotes
            propositions_removed: Number of propositions removed
        """
        hallucination_probability.observe(probability)

        propositions_checked_total.inc(propositions_checked)
        propositions_verified_total.inc(propositions_verified)
        propositions_removed_total.inc(propositions_removed)

        # Calculate ratio
        if propositions_checked > 0:
            ratio = propositions_verified / propositions_checked
            propositions_verified_ratio.observe(ratio)

    @staticmethod
    def record_quote_matches(
        matches_found: int,
        average_similarity: Optional[float] = None,
        latency_ms: Optional[int] = None
    ):
        """
        Record quote matching results.

        Args:
            matches_found: Number of quote matches found
            average_similarity: Average similarity score (optional)
            latency_ms: Quote matching latency in milliseconds (optional)
        """
        quote_matches_found_total.inc(matches_found)

        if average_similarity is not None:
            quote_match_similarity_score.observe(average_similarity)

        if latency_ms is not None:
            quote_matching_latency_seconds.observe(latency_ms / 1000.0)

    @staticmethod
    def record_cache_hit(level: str):
        """
        Record cache hit.

        Args:
            level: Cache level (l1_verification, l2_quotes, l3_questions)
        """
        verification_cache_hits_total.labels(level=level).inc()

        # Update hit rate gauge
        hits = verification_cache_hits_total.labels(level=level)._value._value
        misses = verification_cache_misses_total.labels(level=level)._value._value
        total = hits + misses
        if total > 0:
            verification_cache_hit_rate.labels(level=level).set(hits / total)

    @staticmethod
    def record_cache_miss(level: str):
        """
        Record cache miss.

        Args:
            level: Cache level (l1_verification, l2_quotes, l3_questions)
        """
        verification_cache_misses_total.labels(level=level).inc()

        # Update hit rate gauge
        hits = verification_cache_hits_total.labels(level=level)._value._value
        misses = verification_cache_misses_total.labels(level=level)._value._value
        total = hits + misses
        if total > 0:
            verification_cache_hit_rate.labels(level=level).set(hits / total)

    @staticmethod
    def record_verification_error(stage: str, error_type: str):
        """
        Record verification error.

        Args:
            stage: Stage where error occurred (quote_matching, question_gen, etc.)
            error_type: Error type (timeout, connection_error, etc.)
        """
        verification_errors_total.labels(stage=stage, error_type=error_type).inc()

    @staticmethod
    def record_confidence_adjustment(adjustment: float):
        """
        Record confidence adjustment after verification.

        Args:
            adjustment: Confidence change (negative = reduced, positive = increased)
        """
        confidence_adjustment.observe(adjustment)

    @staticmethod
    def record_timeout(stage: str):
        """
        Record verification timeout.

        Args:
            stage: Stage that timed out (overall, question_gen, verification_exec)
        """
        verification_timeout_total.labels(stage=stage).inc()

    @staticmethod
    def increment_concurrent_requests():
        """Increment concurrent verification requests counter."""
        verification_concurrent_requests.inc()

    @staticmethod
    def decrement_concurrent_requests():
        """Decrement concurrent verification requests counter."""
        verification_concurrent_requests.dec()


class AnswerMetricsRecorder:
    """Helper class to record answer generation metrics."""

    @staticmethod
    def record_answer_request(source: str, latency_ms: int, cache_hit: bool = False):
        """
        Record answer generation request.

        Args:
            source: "baseline" or "verified"
            latency_ms: Answer generation latency in milliseconds
            cache_hit: Whether result was from cache
        """
        answer_requests_total.labels(source=source).inc()
        answer_latency_seconds.observe(latency_ms / 1000.0)

        if cache_hit:
            answer_cache_hits_total.inc()

    @staticmethod
    def record_abstention(reason: str):
        """
        Record answer abstention.

        Args:
            reason: Abstention reason (no_documents, low_confidence, verification_failed)
        """
        answer_abstentions_total.labels(reason=reason).inc()


# ============================================================================
# CONTEXT MANAGER FOR LATENCY TRACKING
# ============================================================================

class LatencyTracker:
    """Context manager for tracking operation latency."""

    def __init__(self, metric_name: str, labels: Optional[Dict[str, str]] = None):
        """
        Initialize latency tracker.

        Args:
            metric_name: Name of the metric to record to
            labels: Optional labels for the metric
        """
        self.metric_name = metric_name
        self.labels = labels or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_ms = int((time.time() - self.start_time) * 1000)

        # Record based on metric name
        if self.metric_name == "verification":
            verification_latency_seconds.observe(elapsed_ms / 1000.0)
        elif self.metric_name == "verification_stage":
            stage = self.labels.get("stage", "unknown")
            verification_stage_latency_seconds.labels(stage=stage).observe(elapsed_ms / 1000.0)
        elif self.metric_name == "answer":
            answer_latency_seconds.observe(elapsed_ms / 1000.0)

    def get_elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        if self.start_time is None:
            return 0
        return int((time.time() - self.start_time) * 1000)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
Example usage in verification_service.py:

from app.core.metrics import VerificationMetricsRecorder, LatencyTracker

class VerificationService:
    async def verify_answer(self, request):
        # Track concurrent requests
        VerificationMetricsRecorder.increment_concurrent_requests()

        try:
            # Track overall latency
            with LatencyTracker("verification") as tracker:
                # ... verification pipeline ...

                # Record hallucination detection
                VerificationMetricsRecorder.record_hallucination_detection(
                    probability=hallucination_report.hallucination_probability,
                    propositions_checked=len(propositions),
                    propositions_verified=verified_count,
                    propositions_removed=removed_count
                )

                # Record final status
                VerificationMetricsRecorder.record_verification_request(
                    status=result.verification_metadata.status,
                    latency_ms=tracker.get_elapsed_ms()
                )

        finally:
            VerificationMetricsRecorder.decrement_concurrent_requests()
"""
