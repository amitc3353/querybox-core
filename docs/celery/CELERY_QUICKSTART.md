# Celery Quick Start Guide

## Prerequisites

- Python 3.11+ with all requirements installed
- Redis server (or Docker)

---

## Step 1: Start Redis

### Option A: Using Docker (Recommended)
```bash
docker run -d --name querybox-redis -p 6379:6379 redis:7-alpine
```

### Option B: Local Redis Installation
```bash
# macOS
brew install redis
redis-server

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Verify Redis is running
redis-cli ping
# Should output: PONG
```

---

## Step 2: Verify Configuration

```bash
cd backend

# Check config file
cat app/core/config.py | grep CELERY

# Expected output:
# CELERY_BROKER_URL: str = "redis://localhost:6379/1"
# CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
# TASK_QUEUE_BACKEND: str = "celery"
```

---

## Step 3: Test Celery App Initialization

```bash
python -c "
from app.celery_app import celery_app
print('✅ Celery app initialized')
print(f'Broker: {celery_app.conf.broker_url}')
print(f'Backend: {celery_app.conf.result_backend}')
print(f'Queues: {list(celery_app.conf.task_routes.keys())}')
"
```

**Expected output:**
```
✅ Celery app initialized
Broker: redis://localhost:6379/1
Backend: redis://localhost:6379/2
Queues: ['app.tasks.metadata_tasks.*']
```

---

## Step 4: Create a Test Task (Optional)

Create `/app/tasks/metadata_tasks.py` if it doesn't exist:

```python
"""
Metadata Processing Tasks
Celery tasks for async metadata extraction
"""

import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.metadata_tasks.test_task",
    bind=True,
    max_retries=3
)
def test_task(self, message: str = "Hello from Celery!"):
    """Test task to verify Celery is working"""
    logger.info(f"Test task executing with message: {message}")

    try:
        # Simulate some work
        import time
        time.sleep(2)

        result = {
            "status": "success",
            "message": message,
            "task_id": self.request.id
        }

        logger.info(f"Test task completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Test task failed: {e}")
        raise self.retry(exc=e, countdown=5)


@celery_app.task(
    name="app.tasks.metadata_tasks.extract_metadata_task",
    bind=True,
    max_retries=3
)
def extract_metadata_task(self, document_id: str, file_path: str, **kwargs):
    """Placeholder for actual metadata extraction"""
    logger.info(f"Extracting metadata for document {document_id}")

    # TODO: Implement actual extraction using docling service
    return {
        "document_id": document_id,
        "status": "placeholder",
        "message": "Actual implementation pending"
    }
```

---

## Step 5: Start Celery Worker

### Terminal 1: Start Worker
```bash
cd backend

celery -A app.celery_app worker \
    --loglevel=info \
    --queues=metadata,default \
    --concurrency=2 \
    --hostname=worker1@%h

# Press Ctrl+C to stop
```

**Expected output:**
```
 -------------- celery@worker1 v5.x.x
---- **** -----
--- * ***  * -- Darwin-...
-- * - **** ---
- ** ---------- [config]
- ** ---------- .> app:         querybox_core:...
- ** ---------- .> transport:   redis://localhost:6379/1
- ** ---------- .> results:     redis://localhost:6379/2
- *** --- * --- .> concurrency: 2 (prefork)
-- ******* ---- .> task events: OFF
--- ***** -----
 -------------- [queues]
                .> metadata      exchange=metadata(direct) key=metadata
                .> default       exchange=default(direct) key=default

[tasks]
  . app.tasks.metadata_tasks.extract_metadata_task
  . app.tasks.metadata_tasks.test_task

[YYYY-MM-DD HH:MM:SS,SSS: INFO/MainProcess] Connected to redis://localhost:6379/1
[YYYY-MM-DD HH:MM:SS,SSS: INFO/MainProcess] mingle: searching for neighbors
[YYYY-MM-DD HH:MM:SS,SSS: INFO/MainProcess] mingle: all alone
[YYYY-MM-DD HH:MM:SS,SSS: INFO/MainProcess] celery@worker1 ready.
```

---

## Step 6: Test Task Execution

### Terminal 2: Send Test Task
```bash
cd backend

python -c "
from app.queue import get_task_queue
import time

queue = get_task_queue()
print('✅ Queue abstraction loaded')

# Enqueue test task
task_id = queue.enqueue_task(
    task_name='test_task',
    kwargs={'message': 'Testing Celery!'},
    queue='metadata',
    priority=5
)

print(f'✅ Task queued with ID: {task_id}')

# Wait for completion
time.sleep(3)

# Check status
status = queue.get_task_status(task_id)
print(f'Task Status: {status.status}')
print(f'Task Result: {status.result}')
print(f'Progress: {status.progress}%')
"
```

**Expected output:**
```
✅ Queue abstraction loaded
✅ Task queued with ID: abc-123-def-456
Task Status: SUCCESS
Task Result: {'status': 'success', 'message': 'Testing Celery!', 'task_id': 'abc-123-def-456'}
Progress: 0.0%
```

**Check Worker Terminal (Terminal 1):**
```
[YYYY-MM-DD HH:MM:SS,SSS: INFO/MainProcess] Task app.tasks.metadata_tasks.test_task[abc-123-def-456] received
[YYYY-MM-DD HH:MM:SS,SSS: INFO/ForkPoolWorker-1] Test task executing with message: Testing Celery!
[YYYY-MM-DD HH:MM:SS,SSS: INFO/ForkPoolWorker-1] Test task completed: {'status': 'success', ...}
[YYYY-MM-DD HH:MM:SS,SSS: INFO/ForkPoolWorker-1] Task app.tasks.metadata_tasks.test_task[abc-123-def-456] succeeded in 2.003s: {...}
```

---

## Step 7: Test API Endpoint (Optional)

### Terminal 1: Keep Celery worker running

### Terminal 2: Start FastAPI server
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Terminal 3: Test metadata extraction endpoint
```bash
# Create a test document first (replace with actual document ID)
curl -X POST "http://localhost:8000/api/v1/metadata/documents/{document_id}/metadata/extract" \
  -H "X-API-Key: dev-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "force_reextraction": false
  }'
```

**Expected response:**
```json
{
  "document_id": "123e4567-e89b-12d3-a456-426614174000",
  "task_id": "abc-123-def-456",
  "status": "queued",
  "message": "Metadata extraction task queued successfully",
  "force_reextraction": false
}
```

---

## Monitoring Commands

### Check Queue Info
```bash
python -c "
from app.queue import get_task_queue
queue = get_task_queue()
info = queue.get_queue_info('metadata')
print(f'Active tasks: {info[\"active_tasks\"]}')
print(f'Pending tasks: {info[\"total_pending\"]}')
print(f'Workers: {info[\"workers\"]}')
"
```

### Check Task Status
```bash
python -c "
from app.queue import get_task_queue
queue = get_task_queue()
status = queue.get_task_status('TASK_ID_HERE')
print(f'Status: {status.status}')
print(f'Result: {status.result}')
"
```

### Install Flower (Web UI)
```bash
pip install flower

# Start Flower dashboard
celery -A app.celery_app flower

# Access at http://localhost:5555
```

---

## Troubleshooting

### Issue: "Connection refused to Redis"
**Solution:**
```bash
# Check if Redis is running
redis-cli ping

# If not, start Redis
docker start querybox-redis
# OR
redis-server
```

---

### Issue: "No module named 'app.tasks.metadata_tasks'"
**Solution:**
Create the task module:
```bash
touch app/tasks/__init__.py
touch app/tasks/metadata_tasks.py
```

Add a basic task to `metadata_tasks.py` (see Step 4).

---

### Issue: Worker not processing tasks
**Solution:**
1. Check worker is running: `ps aux | grep celery`
2. Check queues match: Worker should listen to same queue as task
3. Check Redis connectivity: `redis-cli -n 1 PING`
4. Restart worker with `--loglevel=debug` for more info

---

### Issue: Tasks stuck in PENDING
**Solution:**
1. Verify worker is connected to correct Redis database
2. Check task routing in `app/celery_app.py`
3. Ensure worker is listening to correct queue
4. Check task name matches exactly (including prefix)

---

## Running in Production

### Use Supervisor or systemd

**Example systemd service** (`/etc/systemd/system/querybox-celery.service`):
```ini
[Unit]
Description=QueryBox Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=querybox
Group=querybox
WorkingDirectory=/opt/querybox-core/backend
Environment="PATH=/opt/querybox-core/venv/bin"
ExecStart=/opt/querybox-core/venv/bin/celery -A app.celery_app worker \
    --loglevel=info \
    --queues=metadata,default \
    --concurrency=4 \
    --pidfile=/var/run/celery/worker.pid \
    --logfile=/var/log/celery/worker.log

[Install]
WantedBy=multi-user.target
```

**Commands:**
```bash
sudo systemctl enable querybox-celery
sudo systemctl start querybox-celery
sudo systemctl status querybox-celery
```

---

## Performance Tuning

### Adjust Concurrency
```bash
# More workers for CPU-bound tasks
celery -A app.celery_app worker --concurrency=8

# Fewer workers for I/O-bound tasks
celery -A app.celery_app worker --concurrency=2
```

### Use Autoscaling
```bash
celery -A app.celery_app worker --autoscale=10,3
# Min 3 workers, max 10 workers
```

### Multiple Workers by Queue
```bash
# Terminal 1: Metadata queue (high priority)
celery -A app.celery_app worker \
    --queues=metadata \
    --concurrency=4 \
    --hostname=metadata_worker@%h

# Terminal 2: Default queue (lower priority)
celery -A app.celery_app worker \
    --queues=default \
    --concurrency=2 \
    --hostname=default_worker@%h
```

---

## Clean Shutdown

### Stop Worker Gracefully
```bash
# Send TERM signal (completes current tasks)
celery -A app.celery_app control shutdown

# Or Ctrl+C in worker terminal (same effect)
```

### Purge All Tasks (Dangerous!)
```bash
celery -A app.celery_app purge
# Confirm: yes
```

---

## Next Steps

1. ✅ **Verify setup** - Run test task (Step 6)
2. ✅ **Implement tasks** - Add actual metadata extraction logic
3. ✅ **Test endpoints** - Try metadata extraction API (Step 7)
4. ✅ **Monitor** - Install Flower dashboard
5. ✅ **Production** - Set up systemd/supervisor service

---

*Last Updated: 2024*
*Celery Version: 5.x*
*Redis Version: 7.x*
