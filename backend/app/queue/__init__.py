"""
Task Queue Package
Provides backend-agnostic task queue abstraction

Usage:
    from app.queue import get_task_queue
    queue = get_task_queue()
    task_id = queue.enqueue_task("extract_metadata_task", kwargs={...})
"""

import logging
from app.queue.base import TaskQueue, TaskResult, TaskStatus

logger = logging.getLogger(__name__)

# Global instance (lazy loaded)
_task_queue: TaskQueue = None


def get_task_queue() -> TaskQueue:
    """
    Factory function to get task queue implementation.

    Controlled by environment variable TASK_QUEUE_BACKEND:
    - "celery" (default) - Use Celery with Redis
    - "kafka" (future) - Use Kafka event streaming

    Returns:
        TaskQueue implementation
    """
    global _task_queue

    if _task_queue is not None:
        return _task_queue

    from app.core.config import settings

    backend = getattr(settings, "TASK_QUEUE_BACKEND", "celery")

    if backend == "celery":
        from app.queue.celery_backend import CeleryTaskQueue
        _task_queue = CeleryTaskQueue()
        logger.info("Initialized Celery task queue backend")

    elif backend == "kafka":
        # Future implementation
        raise NotImplementedError(
            "Kafka backend not yet implemented. "
            "Set TASK_QUEUE_BACKEND=celery to use Celery."
        )

    else:
        raise ValueError(
            f"Unknown task queue backend: {backend}. "
            f"Supported backends: celery, kafka"
        )

    return _task_queue


def reset_task_queue():
    """Reset global task queue instance (useful for testing)"""
    global _task_queue
    _task_queue = None


__all__ = [
    "TaskQueue",
    "TaskResult",
    "TaskStatus",
    "get_task_queue",
    "reset_task_queue"
]
