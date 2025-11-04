#!/bin/bash

# QueryboxCore Production Deployment Script
# Step 12.2: Deployment Infrastructure
#
# This script handles safe deployment with:
# - Code pull and validation
# - Docker image building
# - Database migrations
# - Rolling restart
# - Health checks
# - Automatic rollback on failure
#
# Usage:
#   ./scripts/deploy.sh [--skip-build] [--skip-migrations]

set -e  # Exit on error
set -u  # Exit on undefined variable

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"
HEALTH_CHECK_SCRIPT="$SCRIPT_DIR/health_check.sh"
HEALTH_CHECK_TIMEOUT=60
BACKUP_TAG="backup-$(date +%Y%m%d-%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
SKIP_BUILD=false
SKIP_MIGRATIONS=false

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi

    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_warning ".env file not found. Using defaults."
    fi

    log_success "Prerequisites check passed"
}

pull_latest_code() {
    log_info "Pulling latest code from repository..."

    cd "$PROJECT_ROOT"

    # Check if git is available
    if command -v git &> /dev/null && [ -d .git ]; then
        # Stash any local changes
        if ! git diff-index --quiet HEAD --; then
            log_warning "Local changes detected. Stashing..."
            git stash
        fi

        # Pull latest code
        git pull origin "$(git rev-parse --abbrev-ref HEAD)"

        log_success "Code updated to latest version"
    else
        log_warning "Not a git repository. Skipping code pull."
    fi
}

backup_current_images() {
    log_info "Backing up current Docker images..."

    # Tag current backend image as backup
    if docker images querybox-backend:latest -q | grep -q .; then
        docker tag querybox-backend:latest "querybox-backend:$BACKUP_TAG"
        log_success "Backup created: querybox-backend:$BACKUP_TAG"
    else
        log_warning "No existing backend image to backup"
    fi
}

build_docker_images() {
    if [ "$SKIP_BUILD" = true ]; then
        log_warning "Skipping Docker image build (--skip-build flag set)"
        return
    fi

    log_info "Building Docker images..."

    cd "$PROJECT_ROOT"

    # Build with BuildKit for better caching and performance
    DOCKER_BUILDKIT=1 docker-compose -f "$COMPOSE_FILE" build --no-cache backend

    # Get image size
    IMAGE_SIZE=$(docker images querybox-backend:latest --format "{{.Size}}")
    log_success "Docker image built successfully (Size: $IMAGE_SIZE)"

    # Validate image size (should be ~400-500MB)
    IMAGE_SIZE_MB=$(docker images querybox-backend:latest --format "{{.Size}}" | sed 's/MB//' | awk '{print int($1)}')
    if [ "$IMAGE_SIZE_MB" -gt 600 ]; then
        log_warning "Image size ($IMAGE_SIZE) is larger than expected (~400-500MB)"
    fi
}

run_database_migrations() {
    if [ "$SKIP_MIGRATIONS" = true ]; then
        log_warning "Skipping database migrations (--skip-migrations flag set)"
        return
    fi

    log_info "Running database migrations..."

    # Ensure database is running
    docker-compose -f "$COMPOSE_FILE" up -d postgres
    sleep 5

    # Run migrations using the backend container
    docker-compose -f "$COMPOSE_FILE" run --rm backend \
        python scripts/migrate.py upgrade head

    log_success "Database migrations completed"
}

stop_old_containers() {
    log_info "Stopping old containers..."

    # Stop backend and celery worker
    docker-compose -f "$COMPOSE_FILE" stop backend celery-worker || true

    log_success "Old containers stopped"
}

start_new_containers() {
    log_info "Starting new containers..."

    cd "$PROJECT_ROOT"

    # Start all services
    docker-compose -f "$COMPOSE_FILE" up -d

    log_success "New containers started"
}

health_check() {
    log_info "Running health checks..."

    if [ -f "$HEALTH_CHECK_SCRIPT" ]; then
        chmod +x "$HEALTH_CHECK_SCRIPT"

        if bash "$HEALTH_CHECK_SCRIPT"; then
            log_success "Health checks passed"
            return 0
        else
            log_error "Health checks failed"
            return 1
        fi
    else
        log_warning "Health check script not found. Using basic curl check..."

        # Basic health check with timeout
        ELAPSED=0
        while [ $ELAPSED -lt $HEALTH_CHECK_TIMEOUT ]; do
            if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
                log_success "Backend is healthy"
                return 0
            fi

            sleep 5
            ELAPSED=$((ELAPSED + 5))
            log_info "Waiting for backend to become healthy... ($ELAPSED/$HEALTH_CHECK_TIMEOUT seconds)"
        done

        log_error "Backend failed to become healthy within $HEALTH_CHECK_TIMEOUT seconds"
        return 1
    fi
}

rollback() {
    log_error "Deployment failed. Rolling back..."

    # Stop new containers
    docker-compose -f "$COMPOSE_FILE" stop backend celery-worker || true

    # Restore backup image
    if docker images "querybox-backend:$BACKUP_TAG" -q | grep -q .; then
        docker tag "querybox-backend:$BACKUP_TAG" querybox-backend:latest
        log_info "Backup image restored"
    fi

    # Start old containers
    docker-compose -f "$COMPOSE_FILE" up -d backend celery-worker

    log_warning "Rollback completed. System restored to previous state."
    exit 1
}

cleanup() {
    log_info "Cleaning up old Docker resources..."

    # Remove old images (keep last 3 backups)
    docker images "querybox-backend:backup-*" --format "{{.Repository}}:{{.Tag}}" | \
        tail -n +4 | \
        xargs -r docker rmi || true

    # Remove dangling images
    docker image prune -f

    log_success "Cleanup completed"
}

# ============================================================================
# Main Deployment Flow
# ============================================================================

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-migrations)
                SKIP_MIGRATIONS=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Usage: $0 [--skip-build] [--skip-migrations]"
                exit 1
                ;;
        esac
    done

    echo ""
    log_info "========================================="
    log_info "QueryboxCore Production Deployment"
    log_info "========================================="
    echo ""

    # Step 1: Prerequisites
    check_prerequisites

    # Step 2: Pull latest code
    pull_latest_code

    # Step 3: Backup current state
    backup_current_images

    # Step 4: Build new images
    build_docker_images

    # Step 5: Run migrations
    run_database_migrations

    # Step 6: Stop old containers
    stop_old_containers

    # Step 7: Start new containers
    start_new_containers

    # Step 8: Health check
    if ! health_check; then
        rollback
    fi

    # Step 9: Cleanup
    cleanup

    echo ""
    log_success "========================================="
    log_success "Deployment completed successfully!"
    log_success "========================================="
    echo ""
    log_info "Services:"
    log_info "  - Backend API: http://localhost:8000"
    log_info "  - API Docs: http://localhost:8000/docs"
    log_info "  - MinIO Console: http://localhost:9001"
    echo ""
    log_info "View logs: docker-compose -f $COMPOSE_FILE logs -f backend"
    echo ""
}

# Trap errors and rollback
trap rollback ERR

# Run main function
main "$@"
