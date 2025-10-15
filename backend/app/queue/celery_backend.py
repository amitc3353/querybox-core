"""
Celery Implementation of TaskQueue Abstraction
Provides Celery-specific task queue operations
"""

import logging
from typing import Any, Dict
from app.queue.base import TaskQueue, TaskResult, TaskStatus

logger = logging.getLogger(__name__)


class CeleryTaskQueue(TaskQueue):
    """Celery-based task queue implementation"""

    def __init__(self):
        # Lazy import to avoid circular dependencies
        from app.celery_app import celery_app
        from celery.result import AsyncResult

        self.app = celery_app
        self.AsyncResult = AsyncResult

    def enqueue_task(
        self,
        task_name: str,
        kwargs: dict = None,
        queue: str = "default",
        priority: int = 5,
        countdown: int = 0
    ) -> str:
        """Enqueue task using Celery"""
        kwargs = kwargs or {}

        try:
            # Send task to Celery
            task = self.app.send_task(
                f"app.tasks.metadata_tasks.{task_name}",  # Full task path
                kwargs=kwargs,
                queue=queue,
                priority=priority,
                countdown=countdown
            )

            logger.debug(
                f"Enqueued task {task_name} with ID {task.id} "
                f"to queue '{queue}' with priority {priority}"
            )

            return task.id

        except Exception as e:
            logger.error(f"Failed to enqueue task {task_name}: {e}")
            raise

    def get_task_status(self, task_id: str) -> TaskResult:
        """Get Celery task status"""
        try:
            result = self.AsyncResult(task_id, app=self.app)

            # Map Celery status to our TaskStatus
            status_map = {
                "PENDING": TaskStatus.PENDING,
                "STARTED": TaskStatus.RUNNING,
                "SUCCESS": TaskStatus.SUCCESS,
                "FAILURE": TaskStatus.FAILURE,
                "REVOKED": TaskStatus.CANCELLED,
                "RETRY": TaskStatus.RETRY,
            }

            status = status_map.get(result.state, TaskStatus.PENDING)

            # Extract progress if available
            progress = 0.0
            retry_count = 0
            if isinstance(result.info, dict):
                progress = result.info.get("progress", 0.0)
                retry_count = result.info.get("retry_count", 0)

            return TaskResult(
                task_id=task_id,
                status=status,
                result=result.result if status == TaskStatus.SUCCESS else None,
                error=str(result.info) if status == TaskStatus.FAILURE else None,
                progress=progress,
                retry_count=retry_count
            )

        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.PENDING,
                error=f"Failed to get status: {str(e)}"
            )

    def cancel_task(self, task_id: str, terminate: bool = False) -> bool:
        """Cancel Celery task"""
        try:
            self.app.control.revoke(task_id, terminate=terminate, signal='SIGTERM')
            logger.info(f"Cancelled task {task_id} (terminate={terminate})")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False

    def get_queue_info(self, queue: str = "default") -> Dict[str, Any]:
        """Get Celery queue info"""
        try:
            inspect = self.app.control.inspect()

            # Get active, scheduled, and reserved tasks
            active = inspect.active() or {}
            scheduled = inspect.scheduled() or {}
            reserved = inspect.reserved() or {}

            total_active = sum(len(tasks) for tasks in active.values())
            total_scheduled = sum(len(tasks) for tasks in scheduled.values())
            total_reserved = sum(len(tasks) for tasks in reserved.values())

            return {
                "queue": queue,
                "backend": "celery",
                "active_tasks": total_active,
                "scheduled_tasks": total_scheduled,
                "reserved_tasks": total_reserved,
                "total_pending": total_active + total_scheduled + total_reserved,
                "workers": len(active.keys()),
                "worker_names": list(active.keys())
            }

        except Exception as e:
            logger.error(f"Failed to get queue info for {queue}: {e}")
            return {
                "queue": queue,
                "backend": "celery",
                "error": str(e)
            }
