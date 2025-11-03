"""
Metrics Dashboard Endpoint

Provides human-readable performance metrics for manual testing and monitoring.
"""

from fastapi import APIRouter, Response
from typing import Dict, Any
from datetime import datetime, timezone
import logging

from app.monitoring.pipeline_metrics import (
    get_pipeline_metrics_summary,
    get_prometheus_metrics,
    get_prometheus_content_type
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/summary", response_model=Dict[str, Any])
async def get_metrics_summary():
    """
    Get human-readable pipeline metrics summary.

    Returns metrics for:
    - Each pipeline stage (upload, extraction, chunking, embedding, search, answer)
    - Average latencies
    - Request counts
    - Error counts by stage
    - Currently active operations

    Useful for quick performance checks during manual testing.

    Example Response:
    ```json
    {
        "timestamp": "2024-01-15T10:30:00Z",
        "stages": {
            "upload": {
                "total_time_seconds": 45.5,
                "request_count": 10,
                "avg_latency_seconds": 4.55,
                "avg_latency_ms": 4550.0
            },
            "extraction": { ... },
            ...
        },
        "errors": {
            "upload": {
                "ValueError": 2,
                "FileNotFoundError": 1
            }
        },
        "active_operations": {
            "embedding": 2,
            "search": 1
        }
    }
    ```
    """
    try:
        summary = get_pipeline_metrics_summary()
        return summary
    except Exception as e:
        logger.error(f"Failed to generate metrics summary: {e}", exc_info=True)
        return {
            "error": "Failed to generate metrics summary",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/prometheus")
async def get_prometheus_metrics_endpoint():
    """
    Get metrics in Prometheus format.

    Returns all metrics in Prometheus exposition format for scraping
    by Prometheus or viewing raw metrics.

    Content-Type: text/plain; version=0.0.4
    """
    try:
        metrics_data = get_prometheus_metrics()
        return Response(
            content=metrics_data,
            media_type=get_prometheus_content_type()
        )
    except Exception as e:
        logger.error(f"Failed to generate Prometheus metrics: {e}", exc_info=True)
        return Response(
            content=f"# Error generating metrics: {str(e)}",
            media_type="text/plain"
        )


@router.get("/health-detailed")
async def get_detailed_health():
    """
    Get detailed health status including performance metrics.

    Combines health checks with key performance indicators.

    Returns:
    - System health status
    - Recent error rates
    - Average latencies per stage
    - Active operations
    - Resource utilization indicators
    """
    from app.db.database import test_connection
    from app.core.redis import get_redis

    health_status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "healthy",
        "checks": {},
        "performance": {}
    }

    # Database check
    try:
        db_healthy = test_connection()
        health_status["checks"]["database"] = "healthy" if db_healthy else "unhealthy"
        if not db_healthy:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Redis check
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
        # Don't degrade status for Redis

    # Get performance summary
    try:
        perf_summary = get_pipeline_metrics_summary()

        # Extract key performance indicators
        health_status["performance"]["stages"] = {}
        for stage, data in perf_summary.get("stages", {}).items():
            health_status["performance"]["stages"][stage] = {
                "avg_latency_ms": data.get("avg_latency_ms", 0),
                "request_count": data.get("request_count", 0)
            }

        health_status["performance"]["active_operations"] = perf_summary.get("active_operations", {})

        # Check for high error rates
        errors = perf_summary.get("errors", {})
        total_errors = sum(sum(stage_errors.values()) for stage_errors in errors.values())

        if total_errors > 0:
            health_status["performance"]["total_errors"] = total_errors
            health_status["performance"]["errors_by_stage"] = {
                stage: sum(stage_errors.values())
                for stage, stage_errors in errors.items()
            }

            # Degrade status if error rate is high
            if total_errors > 10:
                health_status["status"] = "degraded"

    except Exception as e:
        health_status["performance"]["error"] = f"Failed to get performance metrics: {str(e)}"

    return health_status


@router.get("/bottlenecks")
async def identify_bottlenecks():
    """
    Identify performance bottlenecks in the pipeline.

    Analyzes metrics to find:
    - Slowest pipeline stages
    - Stages with high error rates
    - Stages with high active operations (potential queue buildup)

    Returns recommendations for optimization.
    """
    summary = get_pipeline_metrics_summary()

    bottlenecks = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "analysis": {
            "slow_stages": [],
            "high_error_stages": [],
            "congested_stages": [],
            "recommendations": []
        }
    }

    stages_data = summary.get("stages", {})
    errors_data = summary.get("errors", {})
    active_ops = summary.get("active_operations", {})

    # Identify slow stages (> 1 second average)
    for stage, data in stages_data.items():
        avg_latency = data.get("avg_latency_seconds", 0)
        if avg_latency > 1.0:
            bottlenecks["analysis"]["slow_stages"].append({
                "stage": stage,
                "avg_latency_seconds": avg_latency,
                "avg_latency_ms": data.get("avg_latency_ms", 0),
                "request_count": data.get("request_count", 0)
            })

    # Identify stages with high error rates
    for stage, stage_errors in errors_data.items():
        total_errors = sum(stage_errors.values())
        if total_errors > 5:
            bottlenecks["analysis"]["high_error_stages"].append({
                "stage": stage,
                "error_count": total_errors,
                "errors_by_type": stage_errors
            })

    # Identify congested stages (high active operations)
    for stage, active_count in active_ops.items():
        if active_count > 5:
            bottlenecks["analysis"]["congested_stages"].append({
                "stage": stage,
                "active_operations": active_count
            })

    # Generate recommendations
    if bottlenecks["analysis"]["slow_stages"]:
        slowest = max(bottlenecks["analysis"]["slow_stages"], key=lambda x: x["avg_latency_seconds"])
        bottlenecks["analysis"]["recommendations"].append({
            "priority": "high",
            "issue": f"Slow {slowest['stage']} stage ({slowest['avg_latency_ms']}ms average)",
            "recommendation": f"Optimize {slowest['stage']} processing or add caching"
        })

    if bottlenecks["analysis"]["high_error_stages"]:
        highest_error = max(bottlenecks["analysis"]["high_error_stages"], key=lambda x: x["error_count"])
        bottlenecks["analysis"]["recommendations"].append({
            "priority": "high",
            "issue": f"High error rate in {highest_error['stage']} ({highest_error['error_count']} errors)",
            "recommendation": f"Investigate {highest_error['stage']} errors and add error handling"
        })

    if bottlenecks["analysis"]["congested_stages"]:
        most_congested = max(bottlenecks["analysis"]["congested_stages"], key=lambda x: x["active_operations"])
        bottlenecks["analysis"]["recommendations"].append({
            "priority": "medium",
            "issue": f"{most_congested['stage']} has {most_congested['active_operations']} active operations",
            "recommendation": f"Consider scaling {most_congested['stage']} workers or adding queue limits"
        })

    if not any([
        bottlenecks["analysis"]["slow_stages"],
        bottlenecks["analysis"]["high_error_stages"],
        bottlenecks["analysis"]["congested_stages"]
    ]):
        bottlenecks["analysis"]["recommendations"].append({
            "priority": "info",
            "issue": "No significant bottlenecks detected",
            "recommendation": "Pipeline is performing well"
        })

    return bottlenecks


@router.get("/stage/{stage_name}")
async def get_stage_metrics(stage_name: str):
    """
    Get detailed metrics for a specific pipeline stage.

    Args:
        stage_name: Name of the stage (upload, extraction, chunking, embedding, search, answer)

    Returns:
        Detailed metrics for the specified stage
    """
    summary = get_pipeline_metrics_summary()

    stage_data = summary.get("stages", {}).get(stage_name)
    if not stage_data:
        return {
            "error": f"No metrics found for stage '{stage_name}'",
            "available_stages": list(summary.get("stages", {}).keys())
        }

    stage_errors = summary.get("errors", {}).get(stage_name, {})
    active_ops = summary.get("active_operations", {}).get(stage_name, 0)

    return {
        "stage": stage_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "performance": stage_data,
        "errors": stage_errors,
        "active_operations": active_ops,
        "health": "healthy" if not stage_errors and stage_data.get("avg_latency_seconds", 0) < 5 else "degraded"
    }


@router.post("/reset")
async def reset_metrics():
    """
    Reset all metrics (for testing purposes only).

    WARNING: This will clear all collected metrics data.
    Use only in development/testing environments.
    """
    # Note: Prometheus metrics cannot be reset at runtime
    # This endpoint is a placeholder for future implementation
    return {
        "message": "Metrics reset not implemented",
        "reason": "Prometheus metrics are cumulative and cannot be reset at runtime",
        "recommendation": "Restart the application to reset metrics"
    }
