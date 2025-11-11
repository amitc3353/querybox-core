.PHONY: help setup run migrate migration-create migration-history migration-current test clean docker-up docker-down install lint format seed-demo demo-setup health kill-all restart dev-frontend kill-frontend

# Default target
help:
	@echo "QueryBox Core - Available commands:"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  kill-all           - Kill all running services (backend/celery/frontend)"
	@echo "  restart            - Kill all services and restart fresh (full rebuild)"
	@echo "  dev-frontend       - Start frontend dev server (Next.js)"
	@echo "  kill-frontend      - Kill frontend dev server"
	@echo ""
	@echo "🔧 Development:"
	@echo "  setup              - Set up the development environment"
	@echo "  install            - Install Python dependencies"
	@echo "  run                - Start the FastAPI development server"
	@echo "  migrate            - Run database migrations"
	@echo "  migration-create   - Create new migration (auto-detect changes)"
	@echo "  migration-history  - Show migration history"
	@echo "  migration-current  - Show current migration version"
	@echo "  test               - Run tests"
	@echo "  lint               - Run linting (flake8, mypy)"
	@echo "  format             - Format code (black, isort)"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  docker-up          - Start all services with Docker Compose"
	@echo "  docker-down        - Stop all Docker services"
	@echo ""
	@echo "🌱 Demo & Health:"
	@echo "  seed-demo          - Seed demo data (5 sample documents)"
	@echo "  demo-setup         - Full demo setup (Docker + migrations + seed)"
	@echo "  health             - Check health status of all services"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  clean              - Clean up cache and temporary files"

# Set up development environment
setup: install docker-up migrate
	@echo "✅ Development environment setup complete!"
	@echo "🚀 Run 'make run' to start the API server"

# Install Python dependencies
install:
	@echo "📦 Installing Python dependencies..."
	pip install -r requirements.txt

# Start FastAPI development server
run:
	@echo "🚀 Starting FastAPI development server..."
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run database migrations
migrate:
	@echo "🗄️  Running database migrations..."
	cd backend && python scripts/migrate.py upgrade

# Create new migration (auto-detect changes)
migration-create:
	@echo "📝 Creating new migration (auto-detect changes)..."
	@read -p "Migration message: " msg; \
	cd backend && python scripts/migrate.py create "$$msg"

# Show migration history
migration-history:
	@echo "📜 Migration history:"
	cd backend && python scripts/migrate.py history

# Show current migration version
migration-current:
	@echo "🔍 Current migration version:"
	cd backend && python scripts/migrate.py current

# Legacy migration command (kept for backward compatibility)
migration:
	@echo "⚠️  Deprecated: Use 'make migration-create' instead"
	@read -p "Migration message: " msg; \
	cd backend && alembic revision --autogenerate -m "$$msg"

# Run tests
test:
	@echo "🧪 Running tests..."
	cd backend && pytest tests/ -v

# Run linting
lint:
	@echo "🔍 Running linting..."
	cd backend && flake8 app/
	cd backend && mypy app/

# Format code
format:
	@echo "🎨 Formatting code..."
	cd backend && black app/
	cd backend && isort app/

# Start Docker services
docker-up:
	@echo "🐳 Starting Docker services..."
	cd docker && docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10

# Stop Docker services
docker-down:
	@echo "🛑 Stopping Docker services..."
	cd docker && docker-compose down

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

# Initialize Alembic (run once)
init-alembic:
	@echo "🗄️  Initializing Alembic..."
	cd backend && alembic init migrations

# Seed demo data (Step 12.3)
seed-demo:
	@echo "🌱 Seeding demo data..."
	@echo "   - Generating 5 sample documents"
	@echo "   - Uploading to QueryboxCore"
	@echo "   - Waiting for processing (max 120s)"
	@echo "   - Verifying search functionality"
	@echo ""
	python backend/scripts/seed_demo.py
	@echo ""
	@echo "✅ Demo data seeded successfully!"

# Full demo environment setup (Step 12.3)
demo-setup: docker-up migrate
	@echo "⏳ Waiting for services to stabilize..."
	@sleep 5
	@echo "🌱 Seeding demo data..."
	@make seed-demo
	@echo ""
	@echo "========================================"
	@echo "✅ Demo Environment Ready!"
	@echo "========================================"
	@echo "API:    http://localhost:8000"
	@echo "Docs:   http://localhost:8000/docs"
	@echo "Health: http://localhost:8000/health"
	@echo "MinIO:  http://localhost:9001"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Visit http://localhost:8000/docs for API documentation"
	@echo "  2. Try: curl http://localhost:8000/api/v1/documents"
	@echo "  3. Search: curl -X POST http://localhost:8000/api/v1/search -d '{\"query\":\"deployment\"}'"
	@echo "========================================"

# Check services health
health:
	@echo "🏥 Checking services health..."
	@curl -s http://localhost:8000/health || echo "❌ API not responding"
	@docker exec querybox_postgres pg_isready -U querybox -d querybox > /dev/null 2>&1 && echo "✅ PostgreSQL healthy" || echo "❌ PostgreSQL not healthy"
	@docker exec querybox_redis redis-cli ping > /dev/null 2>&1 && echo "✅ Redis healthy" || echo "❌ Redis not healthy"
	@curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1 && echo "✅ MinIO healthy" || echo "❌ MinIO not healthy"

# Kill all running services
kill-all:
	@echo "🛑 Killing all services..."
	@echo "   - Stopping backend (uvicorn on port 8000)..."
	@-lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	@echo "   - Stopping frontend (Next.js on port 3000)..."
	@-lsof -ti:3000 | xargs kill -9 2>/dev/null || true
	@echo "   - Stopping Celery workers..."
	@-pkill -f "celery.*worker" 2>/dev/null || true
	@echo "   - Stopping Celery beat..."
	@-pkill -f "celery.*beat" 2>/dev/null || true
	@echo "✅ All services stopped"

# Kill frontend only
kill-frontend:
	@echo "🛑 Killing frontend (Next.js)..."
	@-lsof -ti:3000 | xargs kill -9 2>/dev/null || true
	@echo "✅ Frontend stopped"

# Start frontend dev server
dev-frontend:
	@echo "🚀 Starting Next.js frontend..."
	cd frontend && npm run dev

# Full restart - kill all and rebuild
restart: kill-all
	@echo ""
	@echo "♻️  Restarting all services..."
	@echo ""
	@echo "🐳 Starting Docker services (postgres, redis, minio)..."
	@make docker-up
	@echo ""
	@echo "⏳ Waiting for Docker services to be ready..."
	@sleep 5
	@echo ""
	@echo "🚀 Starting backend server on http://localhost:8000..."
	@echo "   (Run in new terminal: make run)"
	@echo ""
	@echo "🚀 Starting frontend server on http://localhost:3000..."
	@echo "   (Run in new terminal: make dev-frontend)"
	@echo ""
	@echo "========================================"
	@echo "✅ Services Ready to Start!"
	@echo "========================================"
	@echo "Run these commands in separate terminals:"
	@echo "  Terminal 1: make run           (backend)"
	@echo "  Terminal 2: make dev-frontend  (frontend)"
	@echo ""
	@echo "Or run both in background:"
	@echo "  make run &"
	@echo "  make dev-frontend &"
	@echo "========================================"