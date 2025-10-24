"""
Tasks Package

Celery tasks for async document processing.
Tasks must be imported here for Celery autodiscovery to work.
"""

# Import all task modules so Celery can discover them
from app.tasks import extraction_tasks  # noqa: F401
from app.tasks import chunking_tasks  # noqa: F401
from app.tasks import metadata_tasks  # noqa: F401

__all__ = [
    "extraction_tasks",
    "chunking_tasks",
    "metadata_tasks",
]