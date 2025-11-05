# Logging & Monitoring - Implementation Context

**Last Updated**: 2025-11-05
**Current Phase**: Phase 1 - COMPLETE
**Status**: ✅ All logging infrastructure implemented and ready for testing
**Next Session**: Testing will be done as part of querybox-frontend E2E testing

---

## 1. Quick Resume

To continue this work in a new session:
```
Continue from dev/active/logging-monitoring/
```

---

## 2. Current State (Updated: 2025-11-05)

### 📊 Progress Summary

**Overall Progress**: ✅ Phase 1 is 100% COMPLETE

**Implementation Status**:
- ✅ Backend logging: COMPLETE (100%)
- ✅ Celery logging: COMPLETE (100%)
- ✅ Frontend logging: COMPLETE (100%)
- ⏳ End-to-end testing: Deferred to querybox-frontend phase

**What's Implemented**:
- ✅ Backend structured logging with context propagation
- ✅ Better Stack integration (ready, needs token for testing)
- ✅ Celery task logging with automatic context management
- ✅ Frontend logger with API error tracking
- ✅ Multi-tenant labels (client_id, request_id, module)
- ✅ Graceful fallback if Better Stack disabled

**Deferred to Testing Phase**:
- Better Stack account setup and token configuration
- End-to-end logging verification
- Live-tail and search functionality testing
- Error boundary component (frontend)

---

### ✅ Phase 1: Backend Logging - COMPLETED

**Implementation Status**: Backend Better Stack integration is complete and ready for testing.

**Backend Logging** (`backend/app/`):
- **Status**: ✅ COMPLETED - Centralized logging configuration implemented
- **Library**: `structlog==23.2.0` + `logtail-python==0.3.4` installed
- **Configuration File**: `backend/app/core/logging.py` (134 lines) - NEW
- **Integration Point**: `backend/app/main.py:6,10-12` - configure_logging() called at startup
- **Features Implemented**:
  - JSON-formatted structured logs via structlog
  - Better Stack (Logtail) handler integration
  - Console handler for development
  - Context propagation (client_id, request_id, module, method, path)
  - Automatic service and environment labels
  - Configurable via LOGTAIL_ENABLED and LOG_LEVEL settings

**Celery Logging** (`backend/app/celery_app.py`):
- **Status**: ✅ COMPLETED - Celery signal handlers updated with structured logging
- **Logger**: structlog (integrated with Better Stack)
- **Location**: `backend/app/celery_app.py:105-153` - signal handlers (task_prerun, task_postrun, task_failure)
- **Context Binding**:
  - service="celery"
  - task_id, task_name, module
  - Automatic context clearing after task completion
- **Features**:
  - Task start/completion/failure logging
  - Automatic context propagation through task lifecycle
  - Context cleanup to prevent leaks between tasks

**Frontend Logging**:
- **Status**: ✅ COMPLETED - Full logger implementation with API integration
- **Dependencies**: `@logtail/browser@^0.4.22` in `frontend/package.json`
- **Logger File**: `frontend/lib/logger.ts` (147 lines)
- **Features**:
  - Browser-only initialization check (typeof window !== 'undefined')
  - info(), error(), warn(), debug() methods
  - apiCall() helper for request/response logging
  - Automatic page context (window.location.pathname)
  - Auto-flush on beforeunload event
  - Graceful fallback to console if Better Stack disabled
- **API Integration**: `frontend/lib/api/client.ts` (lines 3, 62-67, 82-89)
  - Network error logging
  - API error logging with full context

**Metrics** (Already Implemented):
- **Location**: `backend/app/main.py:210-222`
- **Library**: `prometheus-client==0.19.0`
- **Endpoint**: `/metrics` (Prometheus format)
- **Tracked**:
  - HTTP requests/responses
  - Upload pipeline metrics
  - Extraction, chunking, embedding metrics
  - Search and answer metrics
- **Note**: Can integrate with Grafana in Phase 2

### Current Stack
- **Backend**: FastAPI 0.109.0, Python 3.11
- **Frontend**: Next.js 15.5.6, React 19
- **Task Queue**: Celery 5.3.4
- **Broker**: Redis 7-alpine
- **Database**: PostgreSQL 15-alpine
- **Storage**: MinIO latest
- **LLM**: Ollama latest

### Services Currently Running
- Backend API: http://localhost:8000
- Frontend: http://localhost:3001
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- MinIO: localhost:9000-9001
- Ollama: localhost:11434

---

## 3. Current Progress - Files Modified/Created

### ✅ Completed Files

#### Backend Files (COMPLETED)

**New Files Created**:
- ✅ `backend/app/core/logging.py` (134 lines)
  - configure_logging() function with Better Stack integration
  - get_logger() helper function
  - add_app_context() processor for service/environment labels
  - Handles LOGTAIL_ENABLED flag and graceful fallback

**Modified Files**:
- ✅ `backend/requirements.txt`
  - Added: `logtail-python==0.3.4`
  - Already had: `structlog==23.2.0`

- ✅ `backend/.env.example`
  - Added LOGTAIL_SOURCE_TOKEN configuration
  - Added LOGTAIL_ENABLED flag
  - Includes setup instructions

- ✅ `backend/app/core/config.py:163-166`
  - Added LOGTAIL_SOURCE_TOKEN: Optional[str] = None
  - Added LOGTAIL_ENABLED: bool = True
  - Added LOG_LEVEL: str = "INFO"

- ✅ `backend/app/main.py`
  - Line 6: Import configure_logging, get_logger
  - Line 10-12: Call configure_logging() at startup
  - Line 64-114: Added logging context middleware
    - Extracts client_id, request_id, module from requests
    - Binds to structlog context
    - Logs request completion with status/duration

- ✅ `backend/app/celery_app.py:105-153`
  - Updated task_prerun_handler with structlog context binding
  - Updated task_postrun_handler with context clearing
  - Updated task_failure_handler with error logging
  - Context includes: service="celery", task_id, task_name, module

#### Frontend Files (IN PROGRESS)

**Modified Files**:
- ✅ `frontend/package.json`
  - Added: `"@logtail/browser": "^0.4.22"`

**Completed Files**:
- ✅ `frontend/lib/logger.ts` (NEW: 147 lines)
  - Full logger implementation with Better Stack integration
  - Browser-safe initialization
  - Auto-context enrichment
  - Auto-flush on page unload

- ✅ `frontend/lib/api/client.ts` (modified: lines 3, 62-67, 82-89)
  - Logger import
  - Network error logging
  - API error logging with context

**Deferred to Testing Phase**:
- `frontend/.env.local` - Add NEXT_PUBLIC_LOGTAIL_SOURCE_TOKEN when ready to test
- `frontend/components/ErrorBoundary.tsx` - Deferred to querybox-frontend implementation

---

### Phase 2: SigNoz + OTEL-Collector

#### New Files

**Infrastructure**:
- `otel-collector-config.yaml` - OTEL Collector configuration
  - Receivers: OTLP (gRPC 4317, HTTP 4318), Prometheus (8888)
  - Processors: Resource, Batch, Attributes
  - Exporters: OTLP to SigNoz, optional S3
  - Service pipelines for logs, traces, metrics

**Backend**:
- `backend/app/core/telemetry.py` - OpenTelemetry configuration
  - TracerProvider setup
  - OTLP exporter to collector
  - Resource attributes (service.name, deployment.environment)
  - Auto-instrumentation setup

- `backend/app/middleware/telemetry.py` - Telemetry middleware
  - Extract client_id from headers/JWT
  - Add span attributes (client_id, service, module)
  - Bind to structlog context

**Frontend**:
- `frontend/lib/telemetry.ts` - OpenTelemetry Web setup
  - WebTracerProvider configuration
  - OTLP HTTP exporter to collector
  - FetchInstrumentation, DocumentLoadInstrumentation
  - Custom span creation helpers

#### Files to Modify

**Backend**:
- `backend/requirements.txt`
  - Add OpenTelemetry packages:
    ```
    opentelemetry-distro==0.45b0
    opentelemetry-exporter-otlp==1.24.0
    opentelemetry-instrumentation-fastapi==0.45b0
    opentelemetry-instrumentation-celery==0.45b0
    opentelemetry-instrumentation-sqlalchemy==0.45b0
    opentelemetry-instrumentation-redis==0.45b0
    ```

- `backend/app/main.py`
  - Import: `from app.core.telemetry import configure_telemetry, instrument_app`
  - Add: `configure_telemetry()` early in startup
  - Add: `instrument_app(app)` after app creation

- `backend/app/core/config.py`
  - Add: `OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"`
  - Add: `OTEL_SERVICE_NAME: str = "querybox-backend"`
  - Add: `DEPLOYMENT_ENVIRONMENT: str = "development"`

**Frontend**:
- `frontend/package.json`
  - Add OpenTelemetry packages:
    ```json
    "@opentelemetry/api": "^1.7.0",
    "@opentelemetry/sdk-trace-web": "^1.19.0",
    "@opentelemetry/exporter-trace-otlp-http": "^0.45.1",
    "@opentelemetry/instrumentation-fetch": "^0.45.1",
    "@opentelemetry/instrumentation-document-load": "^0.33.4"
    ```

- `frontend/app/layout.tsx`
  - Import: `import { initTelemetry } from '@/lib/telemetry'`
  - Add: `useEffect(() => { initTelemetry() }, [])`

**Docker**:
- `docker-compose.yml`
  - Add otel-collector service:
    ```yaml
    otel-collector:
      image: otel/opentelemetry-collector-contrib:latest
      command: ["--config=/etc/otel-collector-config.yaml"]
      volumes:
        - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml
      ports:
        - "4317:4317"  # OTLP gRPC
        - "4318:4318"  # OTLP HTTP
        - "8888:8888"  # Prometheus
      networks:
        - querybox-network
    ```

  - Update backend/celery services to use OTEL endpoint:
    ```yaml
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    ```

---

## 4. Integration Points

### Backend → Better Stack (Phase 1)

**Structlog Configuration** (`backend/app/core/logging.py`):
```python
import structlog
from logtail import LogtailHandler
import logging

def configure_logging():
    # Logtail handler
    logtail_handler = LogtailHandler(
        source_token=settings.LOGTAIL_SOURCE_TOKEN
    )

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logtail_handler],
        format="%(message)s"
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

**Usage in Code**:
```python
import structlog

logger = structlog.get_logger()
logger.info(
    "Document uploaded",
    document_id=doc.id,
    client_id=client_id,
    file_type=doc.file_type,
    file_size=doc.file_size
)
```

### Frontend → Better Stack (Phase 1)

**Logger Wrapper** (`frontend/lib/logger.ts`):
```typescript
import { Logtail } from '@logtail/browser';

const logtail = new Logtail(
  process.env.NEXT_PUBLIC_LOGTAIL_SOURCE_TOKEN || ''
);

export const logger = {
  info: (message: string, context?: Record<string, any>) => {
    logtail.info(message, context);
  },

  error: (message: string, error?: Error, context?: Record<string, any>) => {
    logtail.error(message, {
      ...context,
      error: error?.message,
      stack: error?.stack,
    });
  },

  warn: (message: string, context?: Record<string, any>) => {
    logtail.warn(message, context);
  },
};
```

**API Error Logging** (`frontend/lib/api/client.ts`):
```typescript
import { logger } from '@/lib/logger';

apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message;

    // Log to Logtail
    logger.error('API Error', error, {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      service: 'frontend',
    });

    console.error('API Error:', message);
    return Promise.reject(error);
  }
);
```

### Backend → OTEL-Collector → SigNoz (Phase 2)

**Telemetry Setup** (`backend/app/core/telemetry.py`):
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor

def configure_telemetry():
    resource = Resource.create({
        "service.name": "querybox-backend",
        "deployment.environment": settings.DEPLOYMENT_ENVIRONMENT,
    })

    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
    )
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

def instrument_app(app):
    FastAPIInstrumentor.instrument_app(app)
    CeleryInstrumentor().instrument()
```

### Celery Context Propagation

**Task with Client ID**:
```python
@app.task(bind=True)
def process_document(self, document_id: str, client_id: str):
    logger = structlog.get_logger()
    logger = logger.bind(
        client_id=client_id,
        service="celery",
        module="upload",
        document_id=document_id,
        task_id=self.request.id
    )

    logger.info("Starting document processing")

    # Phase 2: Add to span
    span = trace.get_current_span()
    span.set_attribute("client_id", client_id)
    span.set_attribute("document_id", document_id)

    # Processing logic...
    logger.info("Document processing complete")
```

---

## 5. Environment Variables

### Development

**Backend** (`.env` or `.env.local`):
```bash
# Phase 1: Better Stack
LOGTAIL_SOURCE_TOKEN=your_better_stack_source_token_here

# Phase 2: OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=querybox-backend
DEPLOYMENT_ENVIRONMENT=development
```

**Frontend** (`.env.local`):
```bash
# Phase 1: Better Stack
NEXT_PUBLIC_LOGTAIL_SOURCE_TOKEN=your_better_stack_source_token_here

# Phase 2: OpenTelemetry
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces
NEXT_PUBLIC_SERVICE_NAME=querybox-frontend
```

### Production

**Backend**:
```bash
LOGTAIL_SOURCE_TOKEN=  # Remove in Phase 2
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_SERVICE_NAME=querybox-backend
DEPLOYMENT_ENVIRONMENT=production
```

**Frontend**:
```bash
NEXT_PUBLIC_LOGTAIL_SOURCE_TOKEN=  # Remove in Phase 2
NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
NEXT_PUBLIC_SERVICE_NAME=querybox-frontend
```

---

## 6. Testing Checklist

### Phase 1 Verification

**Backend Logs**:
- [ ] Start backend server
- [ ] Visit http://localhost:8000/docs
- [ ] Check Better Stack for startup logs
- [ ] Make API request (GET /api/v1/documents/)
- [ ] Verify request logged with method, path, status
- [ ] Check log includes service="backend"

**Frontend Logs**:
- [ ] Open http://localhost:3001
- [ ] Open DevTools Console
- [ ] Trigger an API error (invalid request)
- [ ] Check Better Stack for error log
- [ ] Verify log includes service="frontend", error details

**Celery Logs**:
- [ ] Upload a document
- [ ] Check Better Stack for task logs
- [ ] Verify logs include task_id, document_id
- [ ] Check task_prerun, task_success, task_failure events

**Live-Tail**:
- [ ] Open Better Stack UI
- [ ] Enable live-tail
- [ ] Make multiple API requests
- [ ] Verify logs appear in real-time (<5 seconds)

**Search & Filter**:
- [ ] Search for `service="backend"`
- [ ] Search for `level="error"`
- [ ] Search for `client_id="default"`
- [ ] Filter by time range (last 1 hour)

### Phase 2 Verification

**Distributed Tracing**:
- [ ] Upload document
- [ ] View trace in SigNoz
- [ ] Verify trace shows: Next.js → FastAPI → Celery → Ollama
- [ ] Check span duration for each component

**Custom Labels**:
- [ ] Query: `client_id="test-client"`
- [ ] Query: `service="celery" AND module="upload"`
- [ ] Query: `deployment.environment="development"`

**Dashboards**:
- [ ] View service overview dashboard
- [ ] Check request rate, error rate, latency
- [ ] View upload pipeline dashboard
- [ ] Check Celery task metrics

---

## 7. Common Queries

### Better Stack (Phase 1)

**All Backend Errors**:
```
service:"backend" AND level:"error"
```

**Slow Requests** (>1 second):
```
service:"backend" AND duration:>1000
```

**Celery Task Failures**:
```
service:"celery" AND status:"failure"
```

**Frontend API Errors**:
```
service:"frontend" AND message:*"API Error"*
```

**Logs for Specific Client**:
```
client_id:"client-123"
```

### SigNoz (Phase 2)

**All Services Error Rate**:
```
service IN ["backend", "frontend", "celery"]
AND span.status_code = "error"
```

**P95 Latency by Module**:
```
service="backend"
GROUP BY module
PERCENTILE(duration, 95)
```

**Client Activity**:
```
client_id="client-123"
ORDER BY timestamp DESC
LIMIT 100
```

---

## 8. Troubleshooting

### Issue: Logs not appearing in Better Stack

**Checks**:
1. Verify LOGTAIL_SOURCE_TOKEN is set correctly
2. Check network connectivity (curl https://in.logtail.com)
3. Verify logger is configured before logging statements
4. Check Better Stack dashboard for rate limit errors
5. Verify free tier limit not exceeded (3 GB/day)

**Solution**:
```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger.debug("Test log - should appear in Better Stack")
```

### Issue: Missing client_id in logs

**Checks**:
1. Verify middleware is registered
2. Check X-Client-ID header is sent from frontend
3. Verify structlog context is bound correctly

**Solution**:
```python
# In middleware
structlog.contextvars.bind_contextvars(client_id=client_id)

# Verify in logs
logger.info("Test", extra={"client_id": client_id})
```

### Issue: High resource usage (Phase 2)

**Checks**:
1. Check Docker stats (docker stats)
2. Verify SigNoz services are running
3. Check ClickHouse memory usage

**Solutions**:
- Reduce retention period (7 days → 3 days)
- Add resource limits to docker-compose.yml
- Enable log sampling (log 1 in 10 requests)
- Use Docker volume for ClickHouse data

---

## 9. Next Steps

### ✅ Phase 1 Implementation - COMPLETE

**All Implementation Tasks Completed**:
1. ✅ Backend logging - complete and ready
2. ✅ Celery logging - complete and ready
3. ✅ Frontend logger wrapper - complete and ready
4. ✅ API error logging - complete and ready
5. ✅ Context propagation - complete and ready

**Deferred to Testing Phase** (querybox-frontend E2E):
1. Better Stack account setup and token configuration
2. Dependency installation (pip install logtail-python, npm install)
3. End-to-end testing: Upload → Search → Chat → Check logs
4. Live-tail verification
5. Search/filter verification (service, level, client_id)
6. Error boundary implementation and testing

### Future - Phase 2 (6-8 hours, Step 16)
1. Install SigNoz via install script
2. Add OTEL-Collector to docker-compose.yml
3. Install OpenTelemetry SDKs
4. Create telemetry configuration
5. Instrument all services
6. Create dashboards
7. Set up alerts
8. Document production deployment

---

## 10. Resources

### Better Stack
- Dashboard: https://betterstack.com/logtail
- Docs: https://betterstack.com/docs/logs/
- Python SDK: https://pypi.org/project/logtail-python/
- JavaScript SDK: https://www.npmjs.com/package/@logtail/browser

### SigNoz
- Website: https://signoz.io/
- Docs: https://signoz.io/docs/
- GitHub: https://github.com/SigNoz/signoz
- Installation: https://signoz.io/docs/install/docker/

### OpenTelemetry
- Website: https://opentelemetry.io/
- Python Docs: https://opentelemetry.io/docs/instrumentation/python/
- JavaScript Docs: https://opentelemetry.io/docs/instrumentation/js/
- Collector: https://opentelemetry.io/docs/collector/

### Structlog
- Docs: https://www.structlog.org/
- Best Practices: https://www.structlog.org/en/stable/standard-library.html
- Processors: https://www.structlog.org/en/stable/processors.html

---

**Last Updated**: 2025-01-05
**Status**: Ready for Phase 1 implementation
**Next**: Sign up for Better Stack and get source token
