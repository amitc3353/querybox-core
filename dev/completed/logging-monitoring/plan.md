# Logging & Monitoring Infrastructure - Strategic Plan

**Feature**: Comprehensive logging and monitoring for QueryBox
**Timeline**: Phase 1 (2 hours) + Phase 2 (6-8 hours)
**Status**: Planning Complete → Ready for Implementation
**Last Updated**: 2025-01-05

---

## 1. Problem Statement

### Current Issues
- **Terminal-only logging**: Checking logs requires switching between multiple terminal windows (backend, frontend, Celery worker)
- **No log aggregation**: Logs from different services aren't unified
- **Poor visibility**: Hard to correlate errors across frontend → backend → Celery chains
- **No live-tail**: Can't watch logs in real-time during testing
- **Missing structure**: Logs aren't easily searchable or filterable
- **No alerting**: Can't get notified about errors or performance issues
- **Manual troubleshooting**: Debugging requires grepping through terminal output

### Impact on Development
- Slow debugging cycles
- Missed errors during E2E testing
- Difficulty reproducing issues
- No performance insights
- Can't track down root causes efficiently

---

## 2. Goals & Success Criteria

### Primary Goals
1. **Unified Log Viewing**: See all logs (frontend, backend, Celery) in one place
2. **Live-Tail Capability**: Watch logs in real-time during testing
3. **Advanced Search**: Filter by service, level, timerange, custom fields
4. **Error Tracking**: Automatic error detection with stack traces
5. **Performance Metrics**: Track request latency, database queries, Celery tasks
6. **Easy UI/UX**: Beautiful, intuitive dashboard (not CLI-based)
7. **Cost-Effective**: Free for development, minimal cost for production
8. **Future-Proof**: Easy to migrate between observability backends

### Success Criteria
- ✅ Can see frontend + backend + Celery logs in single UI
- ✅ Live-tail works during E2E testing
- ✅ Can search logs by client_id, service, module, error level
- ✅ Errors automatically highlighted with stack traces
- ✅ Can view request traces end-to-end (Next.js → FastAPI → Celery → LLM)
- ✅ Performance bottlenecks visible in dashboard
- ✅ Setup time < 2 hours for Phase 1
- ✅ Zero cost for development environment

---

## 3. Architecture Decisions

### Two-Phase Approach

#### Phase 1: Better Stack (Immediate - Development)
**When**: NOW (before E2E testing)
**Why**: Get logging working TODAY with minimal setup
**How**: Cloud-based SaaS with generous free tier

**Architecture**:
```
┌─────────────┐
│   FastAPI   │────┐
│   Next.js   │────┼──▶ Better Stack Cloud
│   Celery    │────┘     (3 GB/day free)
└─────────────┘
```

**Trade-offs**:
- ✅ **Pro**: Setup in 1-2 hours, zero infrastructure
- ✅ **Pro**: Beautiful UI, excellent search
- ✅ **Pro**: Works immediately for E2E testing
- ⚠️ **Con**: 3-day retention on free tier
- ⚠️ **Con**: Data sent to cloud (privacy consideration)
- ⚠️ **Con**: 3 GB/day limit (enough for dev, not production)

#### Phase 2: SigNoz + OTEL-Collector (Production)
**When**: LATER (Step 16 - Production Deployment)
**Why**: Self-hosted, unlimited, production-grade observability
**How**: Docker-based stack with vendor-agnostic middleware

**Architecture**:
```
┌─────────────┐     ┌──────────────┐     ┌──────────┐
│   FastAPI   │────▶│              │────▶│          │
│   Next.js   │     │ otel-        │     │  SigNoz  │
│   Celery    │────▶│ collector    │────▶│ (self-   │
│             │     │ (middleware) │     │ hosted)  │
└─────────────┘     └──────────────┘     └──────────┘
    Apps              Buffering/           Observability
                      Enrichment           Backend
```

**Trade-offs**:
- ✅ **Pro**: Completely free and open-source
- ✅ **Pro**: Unlimited logs, long retention
- ✅ **Pro**: Full control over data (privacy)
- ✅ **Pro**: Vendor-agnostic (can switch to Grafana/DataDog later)
- ✅ **Pro**: Production-grade APM + traces + metrics
- ⚠️ **Con**: Requires 6-8 GB RAM (resource intensive)
- ⚠️ **Con**: 6-8 hour setup time
- ⚠️ **Con**: More complex to maintain

### Why OTEL-Collector in Phase 2?

**Problem**: Directly instrumenting apps to send to SigNoz creates vendor lock-in.

**Solution**: Use OpenTelemetry Collector as middleware layer.

**Benefits**:
1. **Vendor-Agnostic**: Switch from SigNoz to Grafana/Honeycomb without changing app code
2. **Buffering**: Collector buffers logs, reduces app overhead
3. **Data Enrichment**: Automatically add labels (environment, region, client_id)
4. **Filtering**: Drop noisy logs, sample high-volume data
5. **Multi-Backend**: Send to SigNoz + S3 backup simultaneously
6. **Industry Standard**: Cloud-native best practice (used by Kubernetes, AWS, GCP)

**Example Enrichment**:
```yaml
# otel-collector-config.yaml
processors:
  resource:
    attributes:
      - key: service.name
        value: ${SERVICE_NAME}
      - key: deployment.environment
        value: ${ENV}
      - key: deployment.region
        value: us-west-2

  attributes:
    actions:
      - key: client_id
        from_attribute: http.headers.x-client-id
        action: insert
```

This allows queries like:
```
client_id="client-123" AND service="backend" AND module="celery"
```

---

## 4. Technology Stack

### Phase 1: Better Stack
- **Backend**: `logtail-python` (pip package)
- **Frontend**: `@logtail/browser` (npm package)
- **Format**: JSON structured logs via structlog
- **Protocol**: HTTPS POST to Better Stack API
- **Cost**: Free (3 GB/day, 3-day retention)

### Phase 2: SigNoz + OTEL
- **Apps**: OpenTelemetry SDKs (Python, JavaScript)
- **Middleware**: OpenTelemetry Collector (Docker container)
- **Backend**: SigNoz (ClickHouse + 6 microservices)
- **Format**: OTLP (OpenTelemetry Protocol)
- **Protocol**: gRPC (4317) or HTTP (4318)
- **Storage**: ClickHouse (efficient columnar DB)
- **Cost**: Free (self-hosted)

---

## 5. Multi-Tenant Label Strategy

### Problem
QueryBox may serve multiple clients. Need to filter logs per client.

### Solution
Add `client_id` label to all logs and traces.

### Implementation

**FastAPI Middleware** (`backend/app/middleware/telemetry.py`):
```python
@app.middleware("http")
async def add_client_context(request: Request, call_next):
    # Extract client ID from header or JWT
    client_id = request.headers.get("X-Client-ID", "default")

    # Add to OpenTelemetry span (Phase 2)
    span = trace.get_current_span()
    span.set_attribute("client_id", client_id)
    span.set_attribute("service", "backend")
    span.set_attribute("module", request.url.path.split("/")[2])

    # Add to structlog context (Phase 1 & 2)
    structlog.contextvars.bind_contextvars(
        client_id=client_id,
        service="backend"
    )

    response = await call_next(request)
    return response
```

**Celery Task Context**:
```python
@app.task(bind=True)
def process_document(self, document_id: str, client_id: str):
    logger = structlog.get_logger()
    logger = logger.bind(
        client_id=client_id,
        service="celery",
        module="upload",
        document_id=document_id
    )

    logger.info("Starting document processing")
    # ... processing logic
```

**Query Examples**:
- All errors for client-123: `client_id="client-123" AND level="error"`
- Slow Celery tasks: `service="celery" AND duration>5000`
- Upload module errors: `module="upload" AND error=true`

---

## 6. Implementation Phases

### Phase 1: Better Stack (2 hours)

**Step 1: Setup** (15 min)
- Sign up at betterstack.com/logtail
- Get source token
- Add to `.env.local` and `backend/.env`

**Step 2: Backend Integration** (45 min)
- Add `logtail-python` to requirements.txt
- Configure structlog with JSON formatter
- Add LogtailHandler to logging
- Test with sample logs

**Step 3: Frontend Integration** (30 min)
- Install `@logtail/browser`
- Create `frontend/lib/logger.ts`
- Add error boundary logging
- Integrate with API client error handling

**Step 4: Celery Integration** (15 min)
- Add Logtail handler to Celery worker
- Test with document processing task

**Step 5: Testing** (15 min)
- Upload document, verify logs
- Run search, check query logs
- Generate answer, check Celery logs
- Test live-tail feature

---

### Phase 2: SigNoz + OTEL-Collector (6-8 hours)

**Step 1: Infrastructure** (1 hour)
- Install OpenTelemetry Collector via Docker
- Install SigNoz via install script
- Configure collector config YAML
- Set up Docker networks

**Step 2: Backend Instrumentation** (2-3 hours)
- Install OpenTelemetry Python SDK
- Auto-instrument FastAPI, Celery, SQLAlchemy, Redis
- Create custom spans for business logic
- Add resource attributes (service.name, environment)

**Step 3: Frontend Instrumentation** (1-2 hours)
- Install OpenTelemetry Web SDK
- Auto-instrument fetch, XHR, page loads
- Create custom spans for user actions
- Configure OTLP exporter to collector

**Step 4: Multi-Tenant Labels** (1 hour)
- Add middleware to extract client_id
- Propagate context through Celery
- Configure collector processors for enrichment
- Test label queries in SigNoz

**Step 5: Docker Integration** (30 min)
- Update docker-compose.yml
- Add otel-collector service
- Configure networks and volumes
- Set environment variables

**Step 6: Dashboards & Alerts** (1-2 hours)
- Create service overview dashboard
- Create per-client dashboard (client_id filter)
- Create module-specific dashboards
- Set up error rate alerts
- Configure latency alerts (p95, p99)

---

## 7. Migration Path

### Phase 1 → Phase 2

**Shared Foundation**:
- Both use structured JSON logs
- Both use same log levels (DEBUG, INFO, WARNING, ERROR)
- Both support custom fields (client_id, service, module)

**Migration Steps**:
1. Keep Better Stack running during Phase 2 setup
2. Install OpenTelemetry SDKs alongside Logtail
3. Send logs to both destinations temporarily
4. Verify SigNoz has all data
5. Remove Logtail handlers
6. Keep Better Stack as backup (free tier)

**Backwards Compatibility**:
- Structlog configuration works for both
- Custom labels (client_id) work in both systems
- No code changes needed to switch backends

---

## 8. Potential Challenges & Solutions

### Challenge 1: Resource Usage (Phase 2)
**Problem**: SigNoz requires 6-8 GB RAM, may impact development machine

**Solutions**:
- Use Docker resource limits
- Run SigNoz only when needed (not 24/7)
- Consider cloud deployment for SigNoz (Fly.io, Railway)
- Fallback to Better Stack if resources insufficient

### Challenge 2: Log Volume
**Problem**: High-traffic testing may exceed Better Stack free tier (3 GB/day)

**Solutions**:
- Use sampling (log 1 in 10 requests)
- Filter noisy logs (health checks, static assets)
- Upgrade to Better Stack paid tier temporarily ($25/month)
- Move to Phase 2 sooner

### Challenge 3: Context Propagation
**Problem**: Celery tasks lose client_id context

**Solutions**:
- Pass client_id as task argument
- Use Celery headers for context propagation
- Store in Redis with document_id key

### Challenge 4: Frontend Source Maps
**Problem**: Minified production code hard to debug

**Solutions**:
- Upload source maps to Better Stack
- Use Sentry for better source map support (if needed)
- Keep development builds for testing

---

## 9. Success Metrics

### Development (Phase 1)
- [ ] All logs visible in Better Stack UI within 5 seconds
- [ ] Can filter by service (backend, frontend, celery)
- [ ] Can search by client_id, document_id, error message
- [ ] Live-tail shows logs in real-time
- [ ] Error stack traces displayed correctly
- [ ] Setup completed in < 2 hours

### Production (Phase 2)
- [ ] Self-hosted SigNoz running stably
- [ ] All services instrumented (backend, frontend, celery)
- [ ] Distributed traces show full request flow
- [ ] Can query by client_id, service, module
- [ ] Dashboards show key metrics (latency, error rate, throughput)
- [ ] Alerts trigger on errors and performance issues
- [ ] Total cost = $0 (self-hosted)

---

## 10. Documentation & Knowledge Transfer

### Documentation to Create
- [ ] README section on viewing logs
- [ ] Development guide for adding new logs
- [ ] Troubleshooting guide for common queries
- [ ] Alert runbook for production incidents
- [ ] Architecture diagram (apps → collector → SigNoz)

### Team Training
- [ ] How to view logs in Better Stack UI
- [ ] How to write structured logs with structlog
- [ ] How to add custom labels (client_id, module)
- [ ] How to create SigNoz dashboards
- [ ] How to troubleshoot with distributed traces

---

## 11. Future Enhancements

### Post-Phase 2
- **Session Replay**: Add Highlight.io or LogRocket for frontend session replay
- **Error Grouping**: Use Sentry for advanced error grouping and release tracking
- **Profiling**: Add continuous profiling (Pyroscope) for performance optimization
- **Synthetic Monitoring**: Add uptime monitoring (UptimeRobot, Pingdom)
- **Cost Dashboards**: Track AWS/cloud costs if deployed to cloud
- **Compliance Logging**: Add audit logs for GDPR/SOC2 compliance

---

## Summary

**Phase 1 (Better Stack)**: Get logging working TODAY for E2E testing with minimal effort.

**Phase 2 (SigNoz + OTEL)**: Production-grade, self-hosted observability with unlimited scaling and vendor flexibility.

**Key Decision**: Use OpenTelemetry Collector as middleware for future-proofing and flexibility.

**Next Steps**: Implement Phase 1 now, schedule Phase 2 for Step 16 (Production Deployment).
