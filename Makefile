.PHONY: help setup run migrate test clean docker-up docker-down install lint format

# Default target
help:
	@echo "QueryBox Core - Available commands:"
	@echo "  setup        - Set up the development environment"
	@echo "  install      - Install Python dependencies"
	@echo "  run          - Start the FastAPI development server"
	@echo "  migrate      - Run database migrations"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting (flake8, mypy)"
	@echo "  format       - Format code (black, isort)"
	@echo "  docker-up    - Start all services with Docker Compose"
	@echo "  docker-down  - Stop all Docker services"
	@echo "  clean        - Clean up cache and temporary files"

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
	cd backend && alembic upgrade head

# Create new migration
migration:
	@echo "📝 Creating new migration..."
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

# Seed demo data
seed-demo:
	@echo "🌱 Seeding demo data..."
	cd backend && python scripts/seed_demo.py

# Check services health
health:
	@echo "🏥 Checking services health..."
	@curl -s http://localhost:8000/health || echo "❌ API not responding"
	@docker exec querybox_postgres pg_isready -U querybox -d querybox > /dev/null 2>&1 && echo "✅ PostgreSQL healthy" || echo "❌ PostgreSQL not healthy"
	@docker exec querybox_redis redis-cli ping > /dev/null 2>&1 && echo "✅ Redis healthy" || echo "❌ Redis not healthy"
	@curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1 && echo "✅ MinIO healthy" || echo "❌ MinIO not healthy"