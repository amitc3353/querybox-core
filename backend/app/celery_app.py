"""
Celery Application Configuration
Provides Celery app instance for async task processing

This file is ONLY imported by celery_backend.py - application code should
use the task queue abstraction instead.
"""

from celery import Celery
from app.core.config import settings

# Create Celery application
celery_app = Celery(
    "querybox_core",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Task execution
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    task_acks_late=True,  # Acknowledge after task completes
    worker_prefetch_multiplier=1,  # One task at a time per worker

    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results to backend

    # Task routing
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',

    # Retry policy
    task_publish_retry=True,
    task_publish_retry_policy={
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.2,
    },

    # Worker
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    worker_disable_rate_limits=True,  # We don't need rate limiting for MVP
)

# Task routing configuration
celery_app.conf.task_routes = {
    "app.tasks.metadata_tasks.*": {
        "queue": "metadata",
        "routing_key": "metadata"
    },
    # Future: Add more queues for embeddings, chunking, etc.
    # "app.tasks.embedding_tasks.*": {"queue": "embeddings"},
    # "app.tasks.chunking_tasks.*": {"queue": "chunking"},
}

# Auto-discover tasks in app.tasks package
celery_app.autodiscover_tasks(['app.tasks'])

# Celery beat schedule (for periodic tasks - future use)
celery_app.conf.beat_schedule = {
    # Example: Clean up old results every hour
    # 'cleanup-old-results': {
    #     'task': 'app.tasks.maintenance.cleanup_old_results',
    #     'schedule': 3600.0,  # Every hour
    # },
}


# Signal handlers for monitoring (optional)
from celery.signals import task_prerun, task_postrun, task_failure
import logging

logger = logging.getLogger(__name__)


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, **kwargs):
    """Log when task starts"""
    logger.info(f"Task {task.name} [{task_id}] started")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, retval=None, **kwargs):
    """Log when task completes"""
    logger.info(f"Task {task.name} [{task_id}] completed")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    """Log when task fails"""
    logger.error(f"Task {sender.name} [{task_id}] failed: {exception}")
