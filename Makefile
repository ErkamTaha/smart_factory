# Smart Factory Development Makefile

.PHONY: help build up down logs clean test lint format

# Default target
help:
	@echo "Smart Factory Development Commands:"
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make up-dev     - Start development environment"
	@echo "  make up-prod    - Start production environment" 
	@echo "  make down       - Stop all services"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make build      - Build all Docker images"
	@echo "  make logs       - Show all logs"
	@echo "  make logs-be    - Show backend logs"
	@echo "  make logs-fe    - Show frontend logs"
	@echo "  make shell-be   - Shell into backend container"
	@echo "  make shell-db   - Shell into database container"
	@echo ""
	@echo "🗄️  Database:"
	@echo "  make db-init    - Initialize database"
	@echo "  make db-reset   - Reset database (WARNING: deletes data)"
	@echo "  make db-backup  - Create database backup"
	@echo "  make db-restore - Restore database from backup"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean      - Clean Docker resources"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linting"
	@echo "  make format     - Format code"

# Detect Docker Compose command
DOCKER_COMPOSE := $(shell command -v docker-compose 2> /dev/null)
ifndef DOCKER_COMPOSE
	DOCKER_COMPOSE := docker compose
endif

# Development Environment
up-dev:
	@echo "🚀 Starting Smart Factory development environment..."
	$(DOCKER_COMPOSE) up -d
	@echo "✅ Services started!"
	@echo "📱 Frontend: http://localhost:3000"
	@echo "🔧 Backend API: http://localhost:8000"
	@echo "🗄️  pgAdmin: http://localhost:8080"
	@echo "📊 Health Check: http://localhost:8000/api/health"

# Production Environment
up-prod:
	@echo "🚀 Starting Smart Factory production environment..."
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml up -d
	@echo "✅ Production services started!"

# Stop services
down:
	@echo "🛑 Stopping Smart Factory services..."
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml down 2>/dev/null || true
	@echo "✅ Services stopped!"

# Build all images
build:
	@echo "🔨 Building Smart Factory images..."
	$(DOCKER_COMPOSE) build
	@echo "✅ Images built!"

# Show logs
logs:
	$(DOCKER_COMPOSE) logs -f

logs-be:
	$(DOCKER_COMPOSE) logs -f backend

logs-fe:
	$(DOCKER_COMPOSE) logs -f frontend

logs-db:
	$(DOCKER_COMPOSE) logs -f postgres

# Shell access
shell-be:
	docker-compose exec backend /bin/bash

shell-fe:
	docker-compose exec frontend /bin/sh

shell-db:
	docker-compose exec postgres psql -U smartfactory -d smartfactory

# Database operations
db-init:
	@echo "🗄️ Initializing database..."
	docker-compose exec backend python -c "from app.database.database import init_database; init_database()"
	@echo "✅ Database initialized!"

db-reset:
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		echo "🗑️  Resetting database..."; \
		docker-compose down; \
		docker volume rm smartfactory_postgres_data 2>/dev/null || true; \
		docker-compose up -d postgres; \
		sleep 10; \
		docker-compose up -d; \
		sleep 5; \
		make db-init; \
		echo "✅ Database reset complete!"; \
	else \
		echo ""; \
		echo "❌ Operation cancelled."; \
	fi

db-backup:
	@echo "💾 Creating database backup..."
	mkdir -p ./backups
	docker-compose exec postgres pg_dump -U smartfactory smartfactory > ./backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created in ./backups/"

db-restore:
	@echo "📥 Available backups:"
	@ls -1 ./backups/*.sql 2>/dev/null || echo "No backups found"
	@read -p "Enter backup filename: " backup; \
	if [ -f "./backups/$$backup" ]; then \
		echo "🔄 Restoring database from $$backup..."; \
		docker-compose exec -T postgres psql -U smartfactory -d smartfactory < "./backups/$$backup"; \
		echo "✅ Database restored!"; \
	else \
		echo "❌ Backup file not found!"; \
	fi

# Testing and Quality
test:
	@echo "🧪 Running tests..."
	docker-compose exec backend python -m pytest
	@echo "✅ Tests completed!"

lint:
	@echo "🔍 Running linting..."
	docker-compose exec backend python -m flake8 app/
	docker-compose exec frontend npm run lint
	@echo "✅ Linting completed!"

format:
	@echo "✨ Formatting code..."
	docker-compose exec backend python -m black app/
	docker-compose exec frontend npm run format
	@echo "✅ Code formatted!"

# Cleanup
clean:
	@echo "🧹 Cleaning Docker resources..."
	docker system prune -f
	docker volume prune -f
	docker network prune -f
	@echo "✅ Cleanup completed!"

# Status check
status:
	@echo "📊 Smart Factory Status:"
	@echo "========================"
	docker-compose ps
	@echo ""
	@echo "🔗 Service URLs:"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  Backend:   http://localhost:8000"
	@echo "  pgAdmin:   http://localhost:8080" 
	@echo "  Health:    http://localhost:8000/api/health"

# Install development dependencies
install:
	@echo "📦 Installing development dependencies..."
	cd backend && pip install -r requirements.txt
	cd frontend && npm install
	@echo "✅ Dependencies installed!"

# Show system resources
resources:
	@echo "💻 System Resources:"
	@echo "==================="
	docker stats --no-stream
	@echo ""
	@echo "📊 Volume Usage:"
	docker system df

# Update services
update:
	@echo "🔄 Updating Smart Factory..."
	git pull
	docker-compose pull
	docker-compose build
	docker-compose up -d
	@echo "✅ Update completed!"
