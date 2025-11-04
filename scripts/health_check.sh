#!/bin/bash

# QueryboxCore Health Check Script
# Step 12.2: Deployment Infrastructure
#
# This script performs comprehensive health checks on all services:
# - Backend API (/health endpoint)
# - PostgreSQL database
# - Redis cache
# - MinIO storage
#
# Usage:
#   ./scripts/health_check.sh [--timeout SECONDS] [--interval SECONDS]
#
# Exit codes:
#   0 - All services healthy
#   1 - One or more services unhealthy

set -u  # Exit on undefined variable

# ============================================================================
# Configuration
# ============================================================================

TIMEOUT=60              # Total timeout in seconds
INTERVAL=5              # Check interval in seconds
BACKEND_URL="http://localhost:8000"
POSTGRES_CONTAINER="querybox-postgres"
REDIS_CONTAINER="querybox-redis"
MINIO_CONTAINER="querybox-minio"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_backend_health() {
    local response
    local status_code
    local healthy

    # Make request to /health endpoint
    response=$(curl -s -w "\n%{http_code}" "$BACKEND_URL/health" 2>/dev/null || echo "000")
    status_code=$(echo "$response" | tail -n 1)

    if [ "$status_code" = "200" ]; then
        # Parse JSON response to check status
        body=$(echo "$response" | sed '$d')

        # Check if response contains "healthy" or "ok" status
        if echo "$body" | grep -q '"status".*"healthy"\|"status".*"ok"'; then
            log_success "Backend API is healthy"
            return 0
        else
            log_warning "Backend API returned 200 but status is not healthy"
            log_info "Response: $body"
            return 1
        fi
    else
        log_error "Backend API is unhealthy (HTTP $status_code)"
        return 1
    fi
}

check_postgres_health() {
    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
        log_error "PostgreSQL container is not running"
        return 1
    fi

    # Check PostgreSQL using pg_isready
    if docker exec "$POSTGRES_CONTAINER" pg_isready -U querybox -d querybox_core > /dev/null 2>&1; then
        log_success "PostgreSQL is healthy"
        return 0
    else
        log_error "PostgreSQL is unhealthy"
        return 1
    fi
}

check_redis_health() {
    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER}$"; then
        log_error "Redis container is not running"
        return 1
    fi

    # Check Redis using PING command
    if docker exec "$REDIS_CONTAINER" redis-cli ping 2>/dev/null | grep -q "PONG"; then
        log_success "Redis is healthy"
        return 0
    else
        log_error "Redis is unhealthy"
        return 1
    fi
}

check_minio_health() {
    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${MINIO_CONTAINER}$"; then
        log_error "MinIO container is not running"
        return 1
    fi

    # Check MinIO health endpoint
    if curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        log_success "MinIO is healthy"
        return 0
    else
        log_error "MinIO is unhealthy"
        return 1
    fi
}

check_all_services() {
    local all_healthy=true

    log_info "Checking all services..."
    echo ""

    # Check each service
    check_backend_health || all_healthy=false
    check_postgres_health || all_healthy=false
    check_redis_health || all_healthy=false
    check_minio_health || all_healthy=false

    echo ""

    if [ "$all_healthy" = true ]; then
        log_success "All services are healthy"
        return 0
    else
        log_error "One or more services are unhealthy"
        return 1
    fi
}

wait_for_health() {
    local elapsed=0
    local attempt=1

    log_info "Waiting for services to become healthy..."
    log_info "Timeout: ${TIMEOUT}s, Check interval: ${INTERVAL}s"
    echo ""

    while [ $elapsed -lt $TIMEOUT ]; do
        log_info "Health check attempt #$attempt (${elapsed}/${TIMEOUT}s elapsed)"
        echo ""

        if check_all_services; then
            echo ""
            log_success "========================================="
            log_success "All services are healthy!"
            log_success "========================================="
            return 0
        fi

        # Wait before next check
        if [ $elapsed -lt $TIMEOUT ]; then
            log_info "Waiting ${INTERVAL}s before next check..."
            sleep $INTERVAL
            elapsed=$((elapsed + INTERVAL))
            attempt=$((attempt + 1))
            echo ""
        fi
    done

    echo ""
    log_error "========================================="
    log_error "Health check timeout!"
    log_error "Services failed to become healthy within ${TIMEOUT}s"
    log_error "========================================="
    return 1
}

show_service_status() {
    log_info "Service Status:"
    echo ""

    # Show docker container status
    docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "querybox-" || true

    echo ""
}

# ============================================================================
# Main Function
# ============================================================================

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --interval)
                INTERVAL="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --timeout SECONDS   Total timeout for health checks (default: 60)"
                echo "  --interval SECONDS  Check interval (default: 5)"
                echo "  --help             Show this help message"
                echo ""
                echo "Exit codes:"
                echo "  0 - All services healthy"
                echo "  1 - One or more services unhealthy"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    echo ""
    log_info "========================================="
    log_info "QueryboxCore Health Check"
    log_info "========================================="
    echo ""

    # Show current service status
    show_service_status

    # Wait for all services to become healthy
    if wait_for_health; then
        exit 0
    else
        show_service_status
        exit 1
    fi
}

# Run main function
main "$@"
