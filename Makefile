help:
	@echo 'Available commands:'
	@echo 'make dev       - Start development environment'
	@echo 'make test      - Run all tests'
	@echo 'make build     - Build Docker images'
	@echo 'make deploy    - Deploy to production'

dev:
	docker-compose up

test:
	cd backend && pytest
	cd frontend && npm test

build:
	docker-compose build

deploy:
	./scripts/deploy.sh

.PHONY: help dev test build deploy

