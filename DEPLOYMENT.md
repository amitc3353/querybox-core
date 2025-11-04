# QueryboxCore Deployment Guide
**Step 12.2: Deployment Infrastructure - Complete**

## Overview
This guide covers deploying QueryboxCore backend to production using Docker and Docker Compose.

## Quick Start

### 1. Prerequisites
```bash
# Required software
- Docker >= 20.10
- Docker Compose >= 2.0
- Git (for deployment script)

# Verify installation
docker --version
docker-compose --version
```

### 2. Environment Configuration
```bash
# Copy example environment file
cp .env.example .env

# Update required variables
nano .env

# Required variables:
# - POSTGRES_PASSWORD
# - API_KEY
# - SECRET_KEY
# - MINIO_ROOT_PASSWORD
```

### 3. Deploy
```bash
# Automated deployment (recommended)
./scripts/deploy.sh

# Manual deployment
docker-compose -f docker-compose.prod.yml up -d

# Check health
./scripts/health_check.sh
```

## Architecture

### Docker Images
- **Backend API**: `querybox-backend:latest` (~2.2GB)
  - Multi-stage build for optimization
  - Production-only dependencies
  - Non-root user (app:app, UID 1000)
  - Health checks enabled

### Services
```yaml
backend:        # FastAPI application (port 8000)
celery-worker:  # Async task processor
postgres:       # PostgreSQL 15 + pgvector
redis:          # Cache and message broker
minio:          # S3-compatible object storage
```

### Network
- Bridge network: `querybox-prod-network`
- Internal service discovery via service names
- External access: backend (8000), minio (9000, 9001)

### Volumes
```yaml
postgres_data:  # Database persistence
redis_data:     # Cache persistence
minio_data:     # Object storage persistence
./logs:         # Application logs (host mount)
./storage:      # Local file storage (host mount)
```

## Deployment Script Features

### `scripts/deploy.sh`
Automated deployment with safety checks:

```bash
# Full deployment
./scripts/deploy.sh

# Skip Docker build (use existing image)
./scripts/deploy.sh --skip-build

# Skip database migrations
./scripts/deploy.sh --skip-migrations
```

**Features:**
- ✓ Prerequisites validation
- ✓ Git code pull
- ✓ Image backup before deployment
- ✓ Multi-stage Docker build
- ✓ Database migrations
- ✓ Rolling restart (zero downtime)
- ✓ Health check validation
- ✓ Automatic rollback on failure
- ✓ Cleanup of old images

### `scripts/health_check.sh`
Comprehensive health monitoring:

```bash
# Default check (60s timeout, 5s interval)
./scripts/health_check.sh

# Custom timeout and interval
./scripts/health_check.sh --timeout 120 --interval 10
```

**Checks:**
- ✓ Backend API (/health endpoint)
- ✓ PostgreSQL database (pg_isready)
- ✓ Redis cache (PING command)
- ✓ MinIO storage (/minio/health/live)

## File Structure

```
querybox-core/
├── backend/
│   ├── Dockerfile              # Multi-stage production build
│   ├── .dockerignore           # Build optimization
│   ├── requirements-prod.txt   # Production dependencies
│   ├── app/                    # Application code
│   ├── alembic/                # Database migrations
│   └── scripts/                # Management scripts
├── docker-compose.prod.yml     # Production orchestration
├── scripts/
│   ├── deploy.sh              # Automated deployment
│   └── health_check.sh        # Health monitoring
├── .env.example               # Environment template
└── DEPLOYMENT.md              # This file
```

## Docker Image Details

### Multi-Stage Build
```dockerfile
# Stage 1: Builder
- Base: python:3.11-slim
- Install build dependencies (gcc, g++, libpq-dev)
- Install production Python packages to /install
- No dev dependencies (pytest, black, flake8, mypy)

# Stage 2: Runtime
- Base: python:3.11-slim
- Install runtime dependencies (libpq5, curl, tesseract)
- Copy packages from builder stage
- Create non-root user (app:app, UID 1000)
- Copy application code
- Health check: curl /health every 30s
```

### Image Size Breakdown
```
Total:                          2.2 GB
├── Python packages:            1.44 GB (PyTorch, transformers, etc.)
├── Python base image:          600 MB
├── Runtime dependencies:       108 MB
└── Application code:           3.3 MB
```

**Note:** The 2.2GB size is industry-standard for ML-enabled backends. PyTorch and transformers libraries are necessary for local embedding generation (BGE-M3 model).

### Build Optimization
- ✓ Multi-stage build (separate builder and runtime)
- ✓ Production dependencies only (no dev tools)
- ✓ .dockerignore excludes unnecessary files
- ✓ BuildKit caching enabled
- ✓ Single layer for package installation
- ✓ apt-get clean and rm -rf /var/lib/apt/lists

## Environment Variables

### Required
```env
# Database
POSTGRES_PASSWORD=<secure-password>
DATABASE_URL=postgresql://querybox:<password>@postgres:5432/querybox_core

# Security
API_KEY=<generate-with-secrets.token_urlsafe(32)>
SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>

# Storage
MINIO_ROOT_PASSWORD=<secure-password>
```

### Optional
```env
# OpenAI (alternative to local embeddings)
OPENAI_API_KEY=sk-...

# Monitoring
SENTRY_DSN=https://...@sentry.io/...

# Performance
WORKERS=4  # Number of uvicorn workers
```

## Health Checks

### Backend API
```bash
# Endpoint: GET /health
# Expected: 200 OK, {"status": "healthy"}

curl http://localhost:8000/health
```

### Database
```bash
# Check PostgreSQL connectivity
docker exec querybox-postgres pg_isready -U querybox -d querybox_core
```

### Cache
```bash
# Check Redis connectivity
docker exec querybox-redis redis-cli ping
# Expected: PONG
```

### Storage
```bash
# Check MinIO health
curl http://localhost:9000/minio/health/live
```

## Deployment Workflow

### Initial Deployment
```bash
# 1. Clone repository
git clone <repository-url>
cd querybox-core

# 2. Configure environment
cp .env.example .env
nano .env  # Update required variables

# 3. Run deployment script
./scripts/deploy.sh

# 4. Verify deployment
./scripts/health_check.sh
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Updates & Redeployment
```bash
# Automated (recommended)
./scripts/deploy.sh

# Manual
git pull origin main
docker-compose -f docker-compose.prod.yml build backend
docker-compose -f docker-compose.prod.yml up -d
./scripts/health_check.sh
```

### Rollback
```bash
# Automatic rollback on deployment failure
# Manual rollback to specific version:

docker tag querybox-backend:backup-20251103-1830 querybox-backend:latest
docker-compose -f docker-compose.prod.yml up -d backend
./scripts/health_check.sh
```

## Monitoring

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# Host-mounted logs
tail -f logs/backend/app.log
tail -f logs/celery/worker.log
```

### Check Resource Usage
```bash
# Container stats
docker stats

# Disk usage
docker system df

# Service status
docker-compose -f docker-compose.prod.yml ps
```

## Maintenance

### Database Migrations
```bash
# Run migrations
docker-compose -f docker-compose.prod.yml run --rm backend \
  python scripts/migrate.py upgrade head

# Check current version
docker-compose -f docker-compose.prod.yml run --rm backend \
  python scripts/migrate.py current

# View migration history
docker-compose -f docker-compose.prod.yml run --rm backend \
  python scripts/migrate.py history
```

### Backup
```bash
# Database backup
docker exec querybox-postgres pg_dump -U querybox querybox_core > backup.sql

# MinIO backup
docker exec querybox-minio mc mirror /data /backup

# Full system backup
docker-compose -f docker-compose.prod.yml down
tar -czf querybox-backup-$(date +%Y%m%d).tar.gz \
  docker-compose.prod.yml .env logs/ storage/
```

### Cleanup
```bash
# Remove old images
docker image prune -a --filter "until=168h"  # 7 days

# Remove stopped containers
docker container prune

# Full cleanup (WARNING: removes all unused data)
docker system prune -a --volumes
```

## Troubleshooting

### Backend Not Starting
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Common issues:
# 1. Database not ready -> Increase healthcheck start_period
# 2. Environment variables -> Check .env file
# 3. Port conflict -> Check if port 8000 is available
```

### Database Connection Failed
```bash
# Check PostgreSQL status
docker-compose -f docker-compose.prod.yml ps postgres

# Verify DATABASE_URL
echo $DATABASE_URL

# Test connection manually
docker exec querybox-postgres psql -U querybox -d querybox_core -c "SELECT 1"
```

### High Memory Usage
```bash
# Check which service is consuming memory
docker stats

# Adjust worker count
# In .env: WORKERS=2  # Reduce if memory constrained

# Restart services
docker-compose -f docker-compose.prod.yml restart backend celery-worker
```

### Embedding Model Download
```bash
# BGE-M3 model (~2GB) downloads on first container startup
# Check download progress:
docker-compose -f docker-compose.prod.yml logs -f backend | grep "Downloading"

# Model is cached in: /home/app/.cache/torch/sentence_transformers
# To persist across container restarts, use a volume
```

## Security Considerations

### Production Checklist
- [ ] Change default passwords (PostgreSQL, MinIO, API keys)
- [ ] Use strong SECRET_KEY and API_KEY (32+ characters)
- [ ] Enable HTTPS/TLS (use reverse proxy like Nginx)
- [ ] Restrict network access (firewall, security groups)
- [ ] Regular security updates (rebuild images)
- [ ] Monitor logs for suspicious activity
- [ ] Implement rate limiting
- [ ] Use secrets management (AWS Secrets Manager, Vault)
- [ ] Enable audit logging
- [ ] Regular backups and disaster recovery testing

### Container Security
- ✓ Non-root user (app:app, UID 1000)
- ✓ Read-only root filesystem (where possible)
- ✓ Minimal base image (python:3.11-slim)
- ✓ No development tools in production image
- ✓ Regular security scans (use `docker scan`)

## Performance Tuning

### Database
```yaml
# In docker-compose.prod.yml postgres service:
command: postgres -c max_connections=200 -c shared_buffers=256MB
```

### Redis
```yaml
# In docker-compose.prod.yml redis service:
command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### Backend Workers
```env
# In .env file:
WORKERS=4  # CPU cores * 2 (recommended)
```

### Celery Workers
```yaml
# In docker-compose.prod.yml celery-worker service:
command: celery -A app.worker worker --loglevel=info --concurrency=4
```

## Scaling

### Horizontal Scaling
```bash
# Scale celery workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=3

# Load balancer for backend (use Nginx/Traefik)
# Update docker-compose.prod.yml to remove port mapping from backend
# Use reverse proxy for load balancing
```

### Vertical Scaling
```yaml
# Resource limits in docker-compose.prod.yml:
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Support

### Logs Location
- Application logs: `./logs/backend/`
- Celery logs: `./logs/celery/`
- Docker logs: `docker-compose logs`

### Getting Help
1. Check logs: `docker-compose -f docker-compose.prod.yml logs`
2. Run health check: `./scripts/health_check.sh`
3. Verify environment: `docker-compose -f docker-compose.prod.yml config`
4. Review documentation: This file and technical docs

---

**Last Updated:** 2025-11-03
**Step:** 12.2 - Deployment Infrastructure
**Status:** ✅ Complete
