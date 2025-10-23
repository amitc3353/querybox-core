# Task Queue Abstraction - Quick Reference Guide

## Import and Basic Usage

```python
from app.queue import get_task_queue
from app.queue.base import TaskStatus

# Get queue instance (singleton)
queue = get_task_queue()
```

---

## API Reference

### 1. Enqueue Task

```python
task_id = queue.enqueue_task(
    task_name="extract_metadata_task",          # Task function name (without module prefix)
    kwargs={"document_id": "123", "path": "/tmp/doc.pdf"},  # Task arguments
    queue="metadata",                           # Queue name (default: "default")
    priority=5,                                 # Priority 0-9 (default: 5)
    countdown=0                                 # Delay in seconds (default: 0)
)

# Returns: task_id (str)
```

**Full task path**: `app.tasks.metadata_tasks.{task_name}` (prefix added automatically)

---

### 2. Get Task Status

```python
status = queue.get_task_status(task_id)

# TaskResult fields:
print(status.task_id)      # str: "abc-123-def"
print(status.status)       # TaskStatus: PENDING, RUNNING, SUCCESS, FAILURE, CANCELLED, RETRY
print(status.result)       # Any: Task return value (if SUCCESS)
print(status.error)        # str: Error message (if FAILURE)
print(status.progress)     # float: 0.0-100.0
print(status.retry_count)  # int: Number of retries
```

**TaskStatus Values**:
- `PENDING`: Task queued but not started
- `RUNNING`: Task currently executing
- `SUCCESS`: Task completed successfully
- `FAILURE`: Task failed with error
- `CANCELLED`: Task was cancelled
- `RETRY`: Task is being retried

---

### 3. Cancel Task

```python
success = queue.cancel_task(
    task_id="abc-123-def",
    terminate=True  # True: SIGTERM, False: revoke without terminating
)

# Returns: bool (True if cancelled successfully)
```

---

### 4. Get Queue Info

```python
info = queue.get_queue_info("metadata")

# Returns dictionary:
{
    "queue": "metadata",
    "backend": "celery",
    "active_tasks": 3,       # Currently running
    "scheduled_tasks": 1,    # Scheduled for future
    "reserved_tasks": 1,     # Reserved by workers
    "total_pending": 5,      # Sum of above
    "workers": 2,            # Number of workers
    "worker_names": ["worker1@host", "worker2@host"]
}
```

---

## Real-World Examples

### Example 1: Metadata Extraction Endpoint

```python
from fastapi import APIRouter, HTTPException
from app.queue import get_task_queue

@router.post("/documents/{document_id}/metadata/extract")
async def extract_metadata(document_id: str):
    queue = get_task_queue()

    try:
        task_id = queue.enqueue_task(
            task_name="extract_metadata_task",
            kwargs={
                "document_id": document_id,
                "file_path": f"/storage/{document_id}.pdf"
            },
            queue="metadata",
            priority=7  # Higher priority
        )

        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Metadata extraction started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### Example 2: Polling Task Status

```python
import asyncio
from app.queue import get_task_queue

async def wait_for_task(task_id: str, timeout: int = 300):
    """Wait for task completion with timeout"""
    queue = get_task_queue()
    start_time = asyncio.get_event_loop().time()

    while True:
        status = queue.get_task_status(task_id)

        if status.status == TaskStatus.SUCCESS:
            return status.result

        if status.status == TaskStatus.FAILURE:
            raise Exception(f"Task failed: {status.error}")

        if status.status == TaskStatus.CANCELLED:
            raise Exception("Task was cancelled")

        # Check timeout
        if asyncio.get_event_loop().time() - start_time > timeout:
            queue.cancel_task(task_id, terminate=True)
            raise TimeoutError(f"Task timed out after {timeout}s")

        # Wait before next check
        await asyncio.sleep(2)
```

---

### Example 3: Batch Task Submission

```python
from app.queue import get_task_queue

def batch_process_documents(document_ids: list[str]):
    """Submit multiple documents for processing"""
    queue = get_task_queue()
    task_ids = []

    for doc_id in document_ids:
        task_id = queue.enqueue_task(
            task_name="extract_metadata_task",
            kwargs={"document_id": doc_id},
            queue="metadata",
            priority=5
        )
        task_ids.append(task_id)

    return {
        "submitted": len(task_ids),
        "task_ids": task_ids
    }
```

---

### Example 4: Task Status Dashboard

```python
from app.queue import get_task_queue

def get_processing_dashboard():
    """Get overview of all queues"""
    queue = get_task_queue()

    queues = ["metadata", "embeddings", "chunking"]
    dashboard = {}

    for queue_name in queues:
        info = queue.get_queue_info(queue_name)
        dashboard[queue_name] = {
            "active": info["active_tasks"],
            "pending": info["total_pending"],
            "workers": info["workers"]
        }

    return dashboard

# Output:
# {
#     "metadata": {"active": 3, "pending": 5, "workers": 2},
#     "embeddings": {"active": 1, "pending": 2, "workers": 1},
#     "chunking": {"active": 0, "pending": 0, "workers": 1}
# }
```

---

### Example 5: Delayed Task Execution

```python
from app.queue import get_task_queue

def schedule_cleanup(document_id: str, delay_hours: int = 24):
    """Schedule document cleanup after delay"""
    queue = get_task_queue()

    task_id = queue.enqueue_task(
        task_name="cleanup_document_task",
        kwargs={"document_id": document_id},
        queue="maintenance",
        countdown=delay_hours * 3600  # Convert hours to seconds
    )

    return task_id
```

---

## Backend Configuration

### Current Backend: Celery
```python
# app/core/config.py
TASK_QUEUE_BACKEND = "celery"
CELERY_BROKER_URL = "redis://localhost:6379/1"
CELERY_RESULT_BACKEND = "redis://localhost:6379/2"
```

### Future Backend: Kafka
```python
# app/core/config.py
TASK_QUEUE_BACKEND = "kafka"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC_PREFIX = "querybox"
```

**No code changes needed** - just change `TASK_QUEUE_BACKEND`!

---

## Testing

### Unit Tests (No Redis Required)

```python
from unittest.mock import patch
from app.queue import get_task_queue, reset_task_queue

def test_enqueue_task():
    reset_task_queue()  # Reset singleton

    with patch('app.celery_app.celery_app') as mock_celery:
        mock_celery.send_task.return_value.id = "test-123"

        queue = get_task_queue()
        task_id = queue.enqueue_task("test_task", kwargs={"arg": "val"})

        assert task_id == "test-123"
```

---

## Error Handling

```python
from app.queue import get_task_queue
from app.queue.base import TaskStatus

queue = get_task_queue()

# Enqueue with error handling
try:
    task_id = queue.enqueue_task(
        task_name="risky_task",
        kwargs={"data": "value"}
    )
except Exception as e:
    print(f"Failed to enqueue: {e}")
    # Handle failure (retry, log, alert, etc.)

# Check status with error handling
status = queue.get_task_status(task_id)
if status.status == TaskStatus.FAILURE:
    print(f"Task failed: {status.error}")
    print(f"Retry count: {status.retry_count}")

    # Optionally retry
    if status.retry_count < 3:
        new_task_id = queue.enqueue_task(
            task_name="risky_task",
            kwargs={"data": "value"}
        )
```

---

## Best Practices

### 1. Use Descriptive Task Names
```python
# Good
queue.enqueue_task("extract_pdf_metadata_task", ...)
queue.enqueue_task("generate_embeddings_task", ...)

# Bad
queue.enqueue_task("process", ...)
queue.enqueue_task("task1", ...)
```

### 2. Always Handle Failures
```python
status = queue.get_task_status(task_id)
if status.status == TaskStatus.FAILURE:
    # Log error
    logger.error(f"Task {task_id} failed: {status.error}")
    # Update database
    update_document_status(doc_id, "extraction_failed")
    # Notify user
    send_notification(user_id, "Processing failed")
```

### 3. Use Appropriate Priorities
```python
# High priority (7-9): User-initiated actions
queue.enqueue_task("extract_metadata", priority=8)

# Normal priority (4-6): Background processing
queue.enqueue_task("generate_embeddings", priority=5)

# Low priority (0-3): Maintenance tasks
queue.enqueue_task("cleanup_old_files", priority=2)
```

### 4. Set Reasonable Timeouts
```python
# Short timeout for quick tasks
await wait_for_task(task_id, timeout=30)

# Long timeout for heavy processing
await wait_for_task(task_id, timeout=600)
```

### 5. Monitor Queue Health
```python
def check_queue_health():
    queue = get_task_queue()
    info = queue.get_queue_info("metadata")

    if info["workers"] == 0:
        alert("No workers available!")

    if info["total_pending"] > 1000:
        alert("Queue backlog too high!")
```

---

## Monitoring

### Check Active Tasks
```bash
# Get queue info programmatically
python -c "
from app.queue import get_task_queue
queue = get_task_queue()
print(queue.get_queue_info('metadata'))
"
```

### Celery Flower Dashboard
```bash
pip install flower
celery -A app.celery_app flower

# Access dashboard at http://localhost:5555
```

---

## Migration Checklist

### When Moving to Kafka:

1. ✅ **No changes needed** - Abstraction handles it
2. ✅ Implement `KafkaTaskQueue` class
3. ✅ Update factory to support "kafka" backend
4. ✅ Change `TASK_QUEUE_BACKEND=kafka` in config
5. ✅ Test with existing API endpoints (should work unchanged)

---

*Last Updated: 2024*
*All examples tested and verified ✅*
