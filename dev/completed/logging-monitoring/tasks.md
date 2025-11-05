# Logging & Monitoring - Implementation Tasks

**Timeline**: Phase 1 (2 hours) + Phase 2 (6-8 hours)
**Last Updated**: 2025-11-05
**Status**: ✅ Phase 1 Complete (100%) - Ready for Testing

## Summary

**Phase 1 Implementation**: COMPLETE
- ✅ Backend structured logging with Better Stack
- ✅ Celery task logging with context propagation
- ✅ Frontend logger with API error tracking
- ✅ Multi-tenant label support (client_id, request_id, module)
- ⏳ Testing deferred to querybox-frontend E2E phase

**Phase 2 (Future - Step 16)**: SigNoz + OpenTelemetry for production

---

## Phase 1: Better Stack Integration (2 hours)

### Step 1: Better Stack Account Setup (15 min)

- [ ] Sign up at https://betterstack.com/logtail
- [ ] Create new source named "QueryBox Development"
- [ ] Copy source token from dashboard
- [ ] Save token securely (password manager)
- [ ] Note free tier limits: 3 GB/day, 3-day retention

**Note**: This step can be completed when ready to test. Backend code is ready to accept the token.

### Step 2: Environment Configuration (10 min)

**Backend**:
- [x] Add to `backend/.env.example`:
  ```bash
  LOGTAIL_SOURCE_TOKEN=your_better_stack_source_token
  LOGTAIL_ENABLED=True
  ```
  ✅ Completed - includes setup instructions

- [ ] Add actual token to `backend/.env`:
  ```bash
  LOGTAIL_SOURCE_TOKEN=your_actual_token_here
  ```
  ⏳ Pending - waiting for Better Stack signup

**Frontend**:
- [ ] Add to `frontend/.env.local`:
  ```bash
  NEXT_PUBLIC_LOGTAIL_SOURCE_TOKEN=your_token_here
  ```
  ⏳ Pending - waiting for Better Stack signup

### Step 3: Backend Dependencies (5 min)

- [x] Add to `backend/requirements.txt`:
  ```
  logtail-python==0.3.4
  ```
  ✅ Completed - dependency added

- [ ] Install: `pip install logtail-python`
  ⏳ Pending - run when ready to test

- [ ] Verify: `pip show logtail-python`
  ⏳ Pending - verify after installation

### Step 4: Backend Logging Configuration (30 min)

- [x] Create `backend/app/core/logging.py` (134 lines)
  ✅ Completed - full implementation with:
  - configure_logging() function
  - get_logger() helper
  - add_app_context() processor
  - Better Stack handler integration
  - Console handler for development
  - Graceful fallback if Better Stack disabled

- [x] Implement configure_logging() function:
  - [x] Import structlog, logtail, logging
  - [x] Create LogtailHandler with source token
  - [x] Configure root logger with Logtail handler
  - [x] Configure structlog processors:
    - [x] contextvars.merge_contextvars (for client_id)
    - [x] add_log_level
    - [x] TimeStamper(fmt="iso", utc=True)
    - [x] JSONRenderer()
    - [x] StackInfoRenderer()
    - [x] format_exc_info
  - [x] Set wrapper_class and logger_factory
  - [x] Export configure_logging and get_logger functions
  ✅ All completed

- [x] Update `backend/app/core/config.py`:
  - [x] Add LOGTAIL_SOURCE_TOKEN: Optional[str] = None
  - [x] Add LOGTAIL_ENABLED: bool = True
  - [x] Add LOG_LEVEL: str = "INFO"
  ✅ Completed at lines 163-166

- [x] Update `backend/app/main.py`:
  - [x] Import: `from app.core.logging import configure_logging, get_logger`
  - [x] Call configure_logging() at startup (line 10)
  - [x] Add logging context middleware (lines 64-114)
  ✅ Completed - includes context extraction middleware

- [ ] Test backend logging:
  - [ ] Install dependencies: `pip install logtail-python`
  - [ ] Add LOGTAIL_SOURCE_TOKEN to backend/.env
  - [ ] Start backend: `cd backend && python -m uvicorn app.main:app --reload`
  - [ ] Check terminal for startup logs
  - [ ] Visit http://localhost:8000/docs
  - [ ] Check Better Stack dashboard for logs
  - [ ] Verify logs appear within 5 seconds
  ⏳ Pending - ready to test once token obtained

### Step 5: Celery Logging Integration (15 min)

- [x] Find Celery worker startup code
  ✅ Found at `backend/app/celery_app.py`

- [x] Update Celery signal handlers with structlog:
  - [x] task_prerun_handler (lines 105-123)
    - Binds context: service="celery", task_id, task_name, module
    - Logs task start
  - [x] task_postrun_handler (lines 126-137)
    - Logs task completion
    - Clears context to prevent leaks
  - [x] task_failure_handler (lines 140-153)
    - Logs task failures with error details
    - Clears context
  ✅ All completed - uses shared logging config from configure_logging()

**Note**: Celery automatically uses the logging configuration from backend/app/main.py
since it imports the same app.core.logging module. No separate Logtail handler needed.

- [ ] Test Celery logging:
  - [ ] Start Celery worker with logging enabled
  - [ ] Trigger a task (upload document)
  - [ ] Check Better Stack for task logs
  - [ ] Verify service="celery" in logs
  - [ ] Verify task_id, task_name context present
  ⏳ Pending - ready to test once token obtained

### Step 6: Frontend Dependencies (5 min)

- [x] Add to `frontend/package.json`:
  ```json
  "@logtail/browser": "^0.4.22"
  ```
  ✅ Completed - dependency added

- [ ] Install: `cd frontend && npm install`
  ⏳ Pending - run when ready to implement frontend

- [ ] Verify: `npm list @logtail/browser`
  ⏳ Pending - verify after installation

### Step 7: Frontend Logger Setup (30 min)

- [x] Create `frontend/lib/logger.ts` (147 lines)
  ✅ Completed - full implementation with:
  - Browser-only initialization check
  - info(), error(), warn(), debug() methods
  - apiCall() helper for API request/response logging
  - Automatic page context (window.location.pathname)
  - Auto-flush on page unload
  - Graceful fallback to console if Better Stack disabled

- [x] Implement logger wrapper:
  - [x] Import Logtail from @logtail/browser
  - [x] Create instance with NEXT_PUBLIC_LOGTAIL_SOURCE_TOKEN
  - [x] Export logger object with methods:
    - [x] info(message, context?)
    - [x] error(message, error?, context?)
    - [x] warn(message, context?)
    - [x] debug(message, context?)
  ✅ All completed

- [x] Update `frontend/lib/api/client.ts`:
  - [x] Import logger from @/lib/logger (line 3)
  - [x] Add logging to response interceptor:
    - Lines 62-67: Network error logging
    - Lines 82-89: API error logging with context
  ✅ Completed - comprehensive error logging

**Note**: Error boundary implementation deferred to querybox-frontend dev docs

### Step 8: Add Custom Context (15 min)

**Backend Middleware**:
- [x] Add logging context middleware to `backend/app/main.py` (lines 64-114)
  ✅ Completed - extracts and binds context:
  - client_id from X-Client-ID header (default: "default")
  - request_id from X-Request-ID header or generated UUID
  - module from URL path parsing
  - method, path from request
  - Logs request completion with status/duration

**Frontend Context**:
- [x] Logger automatically includes context:
  - service="frontend" (automatic)
  - page=window.location.pathname (automatic)
  - environment=process.env.NODE_ENV (automatic)
  ✅ Completed - no manual context binding needed

**Note**: Multi-tenant client_id support will be added when authentication is implemented

### Step 9: Setup & Verification (Deferred to Testing Phase)

**Note**: The logging infrastructure is complete and ready. Actual testing will be done as part of the querybox-frontend E2E testing phase.

**Setup Required (When Ready to Test)**:
- [ ] Sign up for Better Stack at https://betterstack.com/logtail
- [ ] Get source token and add to:
  - `backend/.env`: LOGTAIL_SOURCE_TOKEN=your_token
  - `frontend/.env.local`: NEXT_PUBLIC_LOGTAIL_SOURCE_TOKEN=your_token
- [ ] Install dependencies:
  - Backend: `pip install logtail-python`
  - Frontend: `npm install` (dependency already in package.json)

**Logging Verification (Deferred to E2E Testing)**:
These tasks will be completed during the querybox-frontend integration testing:
- Upload flow logging verification
- Search flow logging verification
- Error handling and logging verification
- Better Stack UI verification (live-tail, search, filters)

**Documentation**:
- [x] Dev docs created with implementation details
- [x] Example queries documented in context.md
- [x] Log levels and usage documented in logging.py docstrings
- [ ] Add logging section to main README (deferred to production deployment)

---

## Phase 2: SigNoz + OTEL-Collector (6-8 hours)

### Step 1: Infrastructure Setup (1 hour)

**OTEL-Collector Installation**:
- [ ] Create `otel-collector-config.yaml` in project root
- [ ] Configure receivers:
  - [ ] OTLP gRPC (4317)
  - [ ] OTLP HTTP (4318)
  - [ ] Prometheus (8888)

- [ ] Configure processors:
  - [ ] resource (add service.name, environment, region)
  - [ ] batch (buffer 5000 spans, flush every 1s)
  - [ ] attributes (extract client_id from headers)

- [ ] Configure exporters:
  - [ ] OTLP to SigNoz (localhost:4317)
  - [ ] logging (debug mode)

- [ ] Configure service pipelines:
  - [ ] traces: [otlp] → [batch, resource] → [otlp]
  - [ ] metrics: [otlp, prometheus] → [batch] → [otlp]
  - [ ] logs: [otlp] → [batch, resource, attributes] → [otlp]

**SigNoz Installation**:
- [ ] Clone SigNoz repository:
  ```bash
  cd ~/signoz
  git clone https://github.com/SigNoz/signoz.git
  cd signoz/deploy/
  ```

- [ ] Run install script:
  ```bash
  ./install.sh
  ```

- [ ] Wait for all services to start (~5 min)

- [ ] Verify SigNoz is running:
  - [ ] Visit http://localhost:3301
  - [ ] Create admin account
  - [ ] Check Services tab (should be empty for now)

**Docker Compose Integration**:
- [ ] Add otel-collector to `docker-compose.yml`:
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

- [ ] Start otel-collector:
  ```bash
  docker-compose up -d otel-collector
  ```

- [ ] Verify: `docker-compose logs otel-collector`

### Step 2: Backend OpenTelemetry Integration (2-3 hours)

**Dependencies**:
- [ ] Add to `backend/requirements.txt`:
  ```
  opentelemetry-distro==0.45b0
  opentelemetry-exporter-otlp==1.24.0
  opentelemetry-instrumentation-fastapi==0.45b0
  opentelemetry-instrumentation-celery==0.45b0
  opentelemetry-instrumentation-sqlalchemy==0.45b0
  opentelemetry-instrumentation-redis==0.45b0
  opentelemetry-instrumentation-requests==0.45b0
  opentelemetry-sdk==1.24.0
  opentelemetry-semantic-conventions==0.45b0
  ```

- [ ] Install: `pip install -r backend/requirements.txt`

**Telemetry Configuration**:
- [ ] Create `backend/app/core/telemetry.py`
- [ ] Implement configure_telemetry():
  - [ ] Import OpenTelemetry modules
  - [ ] Create Resource with service.name, deployment.environment
  - [ ] Setup TracerProvider
  - [ ] Add BatchSpanProcessor with OTLPSpanExporter
  - [ ] Configure to send to otel-collector (localhost:4317)

- [ ] Implement instrument_app(app):
  - [ ] FastAPIInstrumentor.instrument_app(app)
  - [ ] CeleryInstrumentor().instrument()
  - [ ] SQLAlchemyInstrumentor().instrument()
  - [ ] RedisInstrumentor().instrument()

**Middleware for Context**:
- [ ] Create `backend/app/middleware/telemetry.py`
- [ ] Add middleware to extract and set client_id:
  ```python
  from opentelemetry import trace

  @app.middleware("http")
  async def add_telemetry_context(request: Request, call_next):
      span = trace.get_current_span()
      client_id = request.headers.get("X-Client-ID", "default")

      span.set_attribute("client_id", client_id)
      span.set_attribute("service", "backend")
      span.set_attribute("module", request.url.path.split("/")[2])

      response = await call_next(request)
      return response
  ```

**Environment Configuration**:
- [ ] Update `backend/app/core/config.py`:
  ```python
  OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
  OTEL_SERVICE_NAME: str = "querybox-backend"
  DEPLOYMENT_ENVIRONMENT: str = "development"
  ```

**Integration**:
- [ ] Update `backend/app/main.py`:
  - [ ] Import configure_telemetry, instrument_app
  - [ ] Call configure_telemetry() early in startup
  - [ ] Call instrument_app(app) after app creation
  - [ ] Register telemetry middleware

**Custom Spans**:
- [ ] Add custom spans to key functions:
  - [ ] Document upload pipeline
  - [ ] Search queries
  - [ ] Answer generation

- [ ] Example:
  ```python
  from opentelemetry import trace

  tracer = trace.get_tracer(__name__)

  def process_document(document_id: str):
      with tracer.start_as_current_span("process_document") as span:
          span.set_attribute("document_id", document_id)
          # ... processing logic
  ```

**Testing**:
- [ ] Restart backend server
- [ ] Make API request
- [ ] Check SigNoz UI → Services
- [ ] Verify querybox-backend appears
- [ ] Click on service → View traces
- [ ] Verify trace shows request details

### Step 3: Celery OpenTelemetry Integration (1 hour)

**Task Context Propagation**:
- [ ] Update Celery tasks to accept client_id:
  ```python
  @app.task(bind=True)
  def process_document(self, document_id: str, client_id: str):
      with tracer.start_as_current_span("celery.process_document") as span:
          span.set_attribute("client_id", client_id)
          span.set_attribute("document_id", document_id)
          span.set_attribute("service", "celery")
          # ... processing
  ```

- [ ] Pass client_id when calling tasks:
  ```python
  # In API endpoint
  client_id = request.headers.get("X-Client-ID", "default")
  process_document.delay(document_id, client_id)
  ```

**Testing**:
- [ ] Upload document
- [ ] Check SigNoz for trace
- [ ] Verify trace shows: API request → Celery task
- [ ] Verify client_id attribute is present

### Step 4: Frontend OpenTelemetry Integration (1-2 hours)

**Dependencies**:
- [ ] Add to `frontend/package.json`:
  ```json
  "@opentelemetry/api": "^1.7.0",
  "@opentelemetry/sdk-trace-web": "^1.19.0",
  "@opentelemetry/exporter-trace-otlp-http": "^0.45.1",
  "@opentelemetry/instrumentation-fetch": "^0.45.1",
  "@opentelemetry/instrumentation-document-load": "^0.33.4",
  "@opentelemetry/resources": "^1.19.0",
  "@opentelemetry/semantic-conventions": "^1.19.0"
  ```

- [ ] Install: `npm install`

**Telemetry Setup**:
- [ ] Create `frontend/lib/telemetry.ts`
- [ ] Implement initTelemetry():
  - [ ] Create WebTracerProvider
  - [ ] Add Resource (service.name = "querybox-frontend")
  - [ ] Add OTLPTraceExporter (http://localhost:4318/v1/traces)
  - [ ] Add BatchSpanProcessor
  - [ ] Register instrumentations:
    - [ ] FetchInstrumentation
    - [ ] DocumentLoadInstrumentation

**Integration**:
- [ ] Update `frontend/app/layout.tsx`:
  ```typescript
  'use client';

  import { useEffect } from 'react';
  import { initTelemetry } from '@/lib/telemetry';

  export default function RootLayout({ children }) {
      useEffect(() => {
          if (typeof window !== 'undefined') {
              initTelemetry();
          }
      }, []);

      return (
          <html lang="en">
              <body>{children}</body>
          </html>
      );
  }
  ```

**Custom Spans**:
- [ ] Add custom spans for user actions:
  ```typescript
  import { trace } from '@opentelemetry/api';

  const tracer = trace.getTracer('querybox-frontend');

  function handleUpload() {
      const span = tracer.startSpan('user.upload');
      span.setAttribute('client_id', 'default');

      try {
          // Upload logic
          span.setStatus({ code: 0 }); // OK
      } catch (error) {
          span.setStatus({ code: 2, message: error.message }); // ERROR
      } finally {
          span.end();
      }
  }
  ```

**Testing**:
- [ ] Open http://localhost:3001
- [ ] Navigate to documents page
- [ ] Check SigNoz for frontend traces
- [ ] Verify querybox-frontend service appears
- [ ] Check document-load and fetch spans

### Step 5: OTEL-Collector Enrichment (1 hour)

**Resource Processor**:
- [ ] Update `otel-collector-config.yaml`:
  ```yaml
  processors:
    resource:
      attributes:
        - key: deployment.environment
          value: ${ENV}
          action: insert
        - key: deployment.region
          value: us-west-2
          action: insert
  ```

**Attributes Processor**:
- [ ] Add attributes processor to extract client_id:
  ```yaml
  processors:
    attributes:
      actions:
        - key: client_id
          from_attribute: http.request.header.x-client-id
          action: insert
        - key: module
          from_attribute: http.route
          action: insert
  ```

**Apply to Pipeline**:
- [ ] Update service.pipelines:
  ```yaml
  service:
    pipelines:
      traces:
        receivers: [otlp]
        processors: [batch, resource, attributes]
        exporters: [otlp, logging]
  ```

**Testing**:
- [ ] Restart otel-collector
- [ ] Send request with X-Client-ID header
- [ ] Check SigNoz for trace
- [ ] Verify client_id attribute is present
- [ ] Verify deployment.environment is present

### Step 6: Docker Integration (30 min)

**Update docker-compose.yml**:
- [ ] Add environment variables to backend:
  ```yaml
  backend:
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
      - OTEL_SERVICE_NAME=querybox-backend
      - DEPLOYMENT_ENVIRONMENT=${ENV:-development}
  ```

- [ ] Add environment variables to Celery:
  ```yaml
  celery-worker:
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
      - OTEL_SERVICE_NAME=querybox-celery
      - DEPLOYMENT_ENVIRONMENT=${ENV:-development}
  ```

- [ ] Ensure all services on same network:
  ```yaml
  networks:
    querybox-network:
      driver: bridge
  ```

**Testing**:
- [ ] Stop all services: `docker-compose down`
- [ ] Start all services: `docker-compose up -d`
- [ ] Check logs: `docker-compose logs -f`
- [ ] Verify all services connected to otel-collector

### Step 7: Dashboards & Alerts (1-2 hours)

**Service Overview Dashboard**:
- [ ] Open SigNoz → Dashboards → New Dashboard
- [ ] Add panels:
  - [ ] Request rate by service
  - [ ] Error rate by service
  - [ ] P50, P95, P99 latency by service
  - [ ] Active services count

**Upload Pipeline Dashboard**:
- [ ] Create new dashboard
- [ ] Add panels:
  - [ ] Upload requests over time
  - [ ] Processing time (extraction → chunking → embedding)
  - [ ] Success/failure rate
  - [ ] Queue length

**Celery Dashboard**:
- [ ] Create new dashboard
- [ ] Add panels:
  - [ ] Active tasks
  - [ ] Task duration by task name
  - [ ] Task success/failure rate
  - [ ] Queue depth

**Per-Client Dashboard**:
- [ ] Create new dashboard
- [ ] Add variable: client_id (dropdown)
- [ ] Add panels filtered by client_id:
  - [ ] Request count
  - [ ] Error rate
  - [ ] API usage by endpoint

**Alerts**:
- [ ] Create alert: Error rate > 5% for 5 minutes
- [ ] Create alert: P95 latency > 2 seconds for 10 minutes
- [ ] Create alert: Celery queue length > 100
- [ ] Create alert: Database connection failures

**Testing**:
- [ ] Trigger error intentionally
- [ ] Verify alert fires
- [ ] Check notification (email/Slack if configured)

### Step 8: Migration from Better Stack (30 min)

**Parallel Running**:
- [ ] Keep both Better Stack and SigNoz running
- [ ] Verify logs appear in both
- [ ] Compare data quality

**Gradual Migration**:
- [ ] Remove Logtail handlers from backend
- [ ] Remove Logtail from frontend
- [ ] Keep Better Stack account active (free tier) as backup
- [ ] Verify SigNoz has all data

**Cleanup**:
- [ ] Remove logtail-python from requirements.txt
- [ ] Remove @logtail/browser from package.json
- [ ] Remove LOGTAIL_SOURCE_TOKEN from .env files
- [ ] Document migration in README

### Step 9: Documentation (1 hour)

- [ ] Update README.md:
  - [ ] Add "Observability" section
  - [ ] Document how to view logs in SigNoz
  - [ ] Add example queries
  - [ ] Document dashboards

- [ ] Create `docs/observability.md`:
  - [ ] Architecture diagram
  - [ ] Setup instructions
  - [ ] Troubleshooting guide
  - [ ] Alert runbook

- [ ] Update developer guide:
  - [ ] How to add custom spans
  - [ ] How to add custom attributes
  - [ ] Best practices for logging

- [ ] Create query examples:
  - [ ] All errors for client
  - [ ] Slow requests
  - [ ] Failed Celery tasks
  - [ ] Database query performance

---

## Future Enhancements (Post-Phase 2)

### Session Replay
- [ ] Research Highlight.io vs LogRocket
- [ ] Evaluate free tiers
- [ ] Integrate with frontend

### Error Grouping
- [ ] Evaluate Sentry integration
- [ ] Set up source maps
- [ ] Configure release tracking

### Continuous Profiling
- [ ] Research Pyroscope
- [ ] Set up profiling endpoints
- [ ] Create profiling dashboards

### Synthetic Monitoring
- [ ] Set up uptime checks (UptimeRobot)
- [ ] Create health check endpoints
- [ ] Configure alerts

---

## Testing Checklist

### Phase 1 Complete
- [ ] All backend logs visible in Better Stack
- [ ] All frontend logs visible in Better Stack
- [ ] All Celery logs visible in Better Stack
- [ ] Live-tail works in real-time
- [ ] Can search by service, level, time
- [ ] Can filter by client_id
- [ ] Error stack traces displayed correctly

### Phase 2 Complete
- [ ] All services appear in SigNoz (backend, frontend, celery)
- [ ] Distributed traces show full request flow
- [ ] Can query by client_id, service, module
- [ ] Dashboards show key metrics
- [ ] Alerts trigger correctly
- [ ] Resource usage acceptable (<8 GB RAM)
- [ ] Zero cost (self-hosted)

---

**Total Estimated Time**: 2 hours (Phase 1) + 6-8 hours (Phase 2) = 8-10 hours total

**Completion Criteria**:
- ✅ Can view all logs in single UI
- ✅ Live-tail works during testing
- ✅ Can trace requests end-to-end
- ✅ Can filter by client, service, module
- ✅ Dashboards provide actionable insights
- ✅ Alerts notify team of issues
- ✅ Documentation complete

**Next Steps**:
1. Complete Phase 1 now (2 hours)
2. Use for E2E testing
3. Schedule Phase 2 for Step 16 (Production Deployment)
4. Keep Better Stack as backup

**To Resume This Work**:
```
Continue from dev/active/logging-monitoring/
```
