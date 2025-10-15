"""
Task Queue Abstraction Layer
Allows switching between Celery, Kafka, or other queue systems without code changes

This abstraction makes switching from Celery to Kafka a configuration change
instead of a code rewrite.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from enum import Enum
from dataclasses import dataclass


class TaskStatus(str, Enum):
    """Task execution status - backend agnostic"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    RETRY = "retry"


@dataclass
class TaskResult:
    """Standardized task result across all backends"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    progress: float = 0.0
    retry_count: int = 0


class TaskQueue(ABC):
    """
    Abstract task queue interface.

    Implementations: CeleryTaskQueue, KafkaTaskQueue (future)
    """

    @abstractmethod
    def enqueue_task(
        self,
        task_name: str,
        kwargs: dict = None,
        queue: str = "default",
        priority: int = 5,
        countdown: int = 0
    ) -> str:
        """
        Enqueue a task for async execution.

        Args:
            task_name: Name of the task function (e.g., "extract_metadata_task")
            kwargs: Keyword arguments for the task
            queue: Queue name (e.g., "metadata", "embeddings")
            priority: Task priority (1=highest, 10=lowest)
            countdown: Delay in seconds before executing

        Returns:
            task_id: Unique task identifier
        """
        pass

    @abstractmethod
    def get_task_status(self, task_id: str) -> TaskResult:
        """
        Get status and result of a task.

        Args:
            task_id: Task identifier

        Returns:
            TaskResult with current status
        """
        pass

    @abstractmethod
    def cancel_task(self, task_id: str, terminate: bool = False) -> bool:
        """
        Cancel a pending or running task.

        Args:
            task_id: Task identifier
            terminate: If True, forcefully terminate running task

        Returns:
            True if cancelled, False otherwise
        """
        pass

    @abstractmethod
    def get_queue_info(self, queue: str = "default") -> Dict[str, Any]:
        """
        Get queue statistics.

        Args:
            queue: Queue name

        Returns:
            Dictionary with queue stats (depth, workers, etc.)
        """
        pass
