#!/bin/bash
# QueryBox Development Helper Script
# Quick commands for managing services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

show_help() {
    echo -e "${BLUE}QueryBox Development Helper${NC}"
    echo ""
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  kill          - Kill all services (backend/celery/frontend)"
    echo "  restart       - Kill all and restart Docker services"
    echo "  start         - Start all services (Docker + backend + frontend)"
    echo "  stop          - Stop all services"
    echo "  status        - Show status of all services"
    echo "  backend       - Start backend only"
    echo "  frontend      - Start frontend only"
    echo "  logs-backend  - Show backend logs"
    echo "  logs-frontend - Show frontend logs"
    echo "  help          - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./dev.sh kill       # Kill everything"
    echo "  ./dev.sh restart    # Fresh restart"
    echo "  ./dev.sh status     # Check what's running"
    echo ""
}

kill_all() {
    echo -e "${YELLOW}🛑 Killing all services...${NC}"

    # Kill backend (port 8000)
    if lsof -ti:8000 >/dev/null 2>&1; then
        echo "   - Stopping backend (port 8000)..."
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    else
        echo "   - Backend not running"
    fi

    # Kill frontend (port 3000)
    if lsof -ti:3000 >/dev/null 2>&1; then
        echo "   - Stopping frontend (port 3000)..."
        lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    else
        echo "   - Frontend not running"
    fi

    # Kill Celery
    if pgrep -f "celery.*worker" >/dev/null 2>&1; then
        echo "   - Stopping Celery workers..."
        pkill -f "celery.*worker" 2>/dev/null || true
    else
        echo "   - Celery workers not running"
    fi

    if pgrep -f "celery.*beat" >/dev/null 2>&1; then
        echo "   - Stopping Celery beat..."
        pkill -f "celery.*beat" 2>/dev/null || true
    else
        echo "   - Celery beat not running"
    fi

    echo -e "${GREEN}✅ All services stopped${NC}"
}

restart_all() {
    echo -e "${BLUE}♻️  Restarting all services...${NC}"
    echo ""

    kill_all
    echo ""

    echo -e "${BLUE}🐳 Starting Docker services...${NC}"
    cd docker && docker-compose up -d
    cd ..

    echo ""
    echo -e "${YELLOW}⏳ Waiting for services to be ready (10s)...${NC}"
    sleep 10

    echo ""
    echo -e "${GREEN}=======================================${NC}"
    echo -e "${GREEN}✅ Services Ready!${NC}"
    echo -e "${GREEN}=======================================${NC}"
    echo ""
    echo "To start backend and frontend, run:"
    echo -e "  ${BLUE}./dev.sh backend${NC}   (in terminal 1)"
    echo -e "  ${BLUE}./dev.sh frontend${NC}  (in terminal 2)"
    echo ""
}

start_backend() {
    echo -e "${BLUE}🚀 Starting backend server...${NC}"
    cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

start_frontend() {
    echo -e "${BLUE}🚀 Starting frontend server...${NC}"
    cd frontend && npm run dev
}

show_status() {
    echo -e "${BLUE}📊 Service Status:${NC}"
    echo ""

    # Check backend
    if lsof -ti:8000 >/dev/null 2>&1; then
        echo -e "  Backend (port 8000):  ${GREEN}✅ Running${NC}"
    else
        echo -e "  Backend (port 8000):  ${RED}❌ Stopped${NC}"
    fi

    # Check frontend
    if lsof -ti:3000 >/dev/null 2>&1; then
        echo -e "  Frontend (port 3000): ${GREEN}✅ Running${NC}"
    else
        echo -e "  Frontend (port 3000): ${RED}❌ Stopped${NC}"
    fi

    # Check Celery worker
    if pgrep -f "celery.*worker" >/dev/null 2>&1; then
        echo -e "  Celery Worker:        ${GREEN}✅ Running${NC}"
    else
        echo -e "  Celery Worker:        ${RED}❌ Stopped${NC}"
    fi

    # Check Docker services
    echo ""
    echo -e "${BLUE}🐳 Docker Services:${NC}"

    if docker ps --format '{{.Names}}' | grep -q "querybox_postgres"; then
        echo -e "  PostgreSQL:           ${GREEN}✅ Running${NC}"
    else
        echo -e "  PostgreSQL:           ${RED}❌ Stopped${NC}"
    fi

    if docker ps --format '{{.Names}}' | grep -q "querybox_redis"; then
        echo -e "  Redis:                ${GREEN}✅ Running${NC}"
    else
        echo -e "  Redis:                ${RED}❌ Stopped${NC}"
    fi

    if docker ps --format '{{.Names}}' | grep -q "minio"; then
        echo -e "  MinIO:                ${GREEN}✅ Running${NC}"
    else
        echo -e "  MinIO:                ${RED}❌ Stopped${NC}"
    fi

    echo ""
}

logs_backend() {
    echo -e "${BLUE}📋 Backend logs (tail -f):${NC}"
    echo "Press Ctrl+C to exit"
    echo ""
    tail -f backend/logs/*.log 2>/dev/null || echo "No backend logs found"
}

logs_frontend() {
    echo -e "${BLUE}📋 Frontend logs:${NC}"
    echo "Press Ctrl+C to exit"
    echo ""
    cd frontend && npm run dev 2>&1 | grep -v "webpack"
}

# Main script
case "${1:-help}" in
    kill)
        kill_all
        ;;
    restart)
        restart_all
        ;;
    start)
        restart_all
        ;;
    stop)
        kill_all
        echo ""
        echo "🐳 Stopping Docker services..."
        cd docker && docker-compose down
        ;;
    status)
        show_status
        ;;
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    logs-backend)
        logs_backend
        ;;
    logs-frontend)
        logs_frontend
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
