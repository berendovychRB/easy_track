# Makefile for EasyTrack - Telegram Bot for Body Measurement Tracking
# =======================================================================

# Configuration
# =============================================================================
SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: help install install-dev clean test lint format type-check security-check
.PHONY: build run stop restart logs docker-build docker-run docker-stop docker-clean
.PHONY: db-init db-migrate db-upgrade db-downgrade db-reset db-shell db-backup db-restore
.PHONY: deploy deploy-prod deploy-staging health-check scale-up scale-down
.PHONY: requirements freeze update-deps dev-setup pre-commit release rebuild-and-start rebuild-fresh

# Variables
PROJECT_NAME := easy-track
PYTHON := python3
PIP := pip3
DOCKER_COMPOSE := docker-compose
ALEMBIC := alembic
PYTEST := pytest

# Docker and Environment
DOCKER_IMAGE := $(PROJECT_NAME):latest
CONTAINER_NAME := $(PROJECT_NAME)_bot
POSTGRES_CONTAINER := $(PROJECT_NAME)_postgres

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
PURPLE := \033[0;35m
CYAN := \033[0;36m
WHITE := \033[0;37m
NC := \033[0m # No Color

# Help target
# =============================================================================
help: ## Show this help message
	@echo "$(CYAN)EasyTrack Bot - Makefile Commands$(NC)"
	@echo "=================================="
	@echo ""
	@echo "$(GREEN)Development Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(install|clean|test|lint|format|type-check|security-check|dev-setup|pre-commit)"
	@echo ""
	@echo "$(GREEN)Docker Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(build|run|stop|restart|logs|docker-)"
	@echo ""
	@echo "$(GREEN)Database Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "db-"
	@echo ""
	@echo "$(GREEN)Deployment Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(deploy|health-check|scale-)"
	@echo ""
	@echo "$(GREEN)Utility Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | grep -E "(requirements|freeze|update-deps|release)"

# Development Setup
# =============================================================================
install: ## Install production dependencies
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	@echo "$(GREEN)✅ Production dependencies installed!$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev,test]"
	@echo "$(GREEN)✅ Development dependencies installed!$(NC)"

dev-setup: install-dev ## Complete development environment setup
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(YELLOW)⚠️  Please configure .env file with your settings!$(NC)"; \
	fi
	@mkdir -p logs
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit install; \
		echo "$(GREEN)✅ Pre-commit hooks installed!$(NC)"; \
	fi
	@echo "$(GREEN)✅ Development environment ready!$(NC)"

requirements: ## Generate requirements.txt from current environment
	@echo "$(BLUE)Generating requirements.txt...$(NC)"
	$(PIP) freeze > requirements.txt
	@echo "$(GREEN)✅ Requirements file updated!$(NC)"

freeze: requirements ## Alias for requirements

update-deps: ## Update all dependencies to latest versions
	@echo "$(BLUE)Updating dependencies...$(NC)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install --upgrade -r requirements.txt
	@echo "$(GREEN)✅ Dependencies updated!$(NC)"

# Code Quality
# =============================================================================
clean: ## Clean up temporary files and caches
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@echo "$(GREEN)✅ Cleanup completed!$(NC)"

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(PYTEST) -v --tb=short
	@echo "$(GREEN)✅ Tests completed!$(NC)"

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(PYTEST) --cov=src/easy_track --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)✅ Tests with coverage completed!$(NC)"

lint: ## Run linting checks with ruff
	@echo "$(BLUE)Running linting checks with ruff...$(NC)"
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check src/ --fix; \
	else \
		echo "$(YELLOW)⚠️  ruff not installed, installing...$(NC)"; \
		pip install ruff; \
		ruff check src/ --fix; \
	fi
	@echo "$(GREEN)✅ Linting completed!$(NC)"

format: ## Format code with ruff
	@echo "$(BLUE)Formatting code with ruff...$(NC)"
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format src/; \
	else \
		echo "$(YELLOW)⚠️  ruff not installed, installing...$(NC)"; \
		pip install ruff; \
		ruff format src/; \
	fi
	@echo "$(GREEN)✅ Code formatting completed!$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	@if command -v mypy >/dev/null 2>&1; then \
		mypy src/easy_track --ignore-missing-imports; \
	else \
		echo "$(YELLOW)⚠️  mypy not installed, skipping...$(NC)"; \
	fi
	@echo "$(GREEN)✅ Type checking completed!$(NC)"

security-check: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	@if command -v bandit >/dev/null 2>&1; then \
		bandit -r src/; \
	else \
		echo "$(YELLOW)⚠️  bandit not installed, skipping...$(NC)"; \
	fi
	@echo "$(GREEN)✅ Security check completed!$(NC)"

pre-commit: ## Run all pre-commit checks
	@echo "$(BLUE)Running pre-commit checks...$(NC)"
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit run --all-files; \
	else \
		$(MAKE) format lint type-check; \
	fi
	@echo "$(GREEN)✅ Pre-commit checks completed!$(NC)"

# Docker Commands
# =============================================================================
build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t $(DOCKER_IMAGE) .
	@echo "$(GREEN)✅ Docker image built!$(NC)"

docker-build: build ## Alias for build

run: ## Run the bot locally (without Docker)
	@echo "$(BLUE)Starting bot locally...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ .env file not found! Copy .env.example and configure it.$(NC)"; \
		exit 1; \
	fi
	$(PYTHON) -m easy_track.main

docker-run: ## Run with Docker Compose
	@echo "$(BLUE)Starting services with Docker Compose...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ .env file not found! Copy .env.example and configure it.$(NC)"; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✅ Services started!$(NC)"

stop: ## Stop local bot
	@echo "$(BLUE)Stopping bot...$(NC)"
	@pkill -f "easy_track.main" || echo "Bot not running"
	@echo "$(GREEN)✅ Bot stopped!$(NC)"

docker-stop: ## Stop Docker Compose services
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✅ Services stopped!$(NC)"

restart: stop run ## Restart local bot

docker-restart: docker-stop docker-run ## Restart Docker services

logs: ## Show local logs
	@echo "$(BLUE)Showing logs...$(NC)"
	@if [ -f logs/bot.log ]; then \
		tail -f logs/bot.log; \
	else \
		echo "$(YELLOW)⚠️  No log file found$(NC)"; \
	fi

docker-logs: ## Show Docker Compose logs
	@echo "$(BLUE)Showing Docker logs...$(NC)"
	$(DOCKER_COMPOSE) logs -f

rebuild-and-start: ## Rebuild containers and start with logs
	@echo "$(BLUE)Rebuilding and starting containers...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ .env file not found! Copy .env.example and configure it.$(NC)"; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) build --no-cache
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✅ Containers rebuilt and started!$(NC)"
	@echo "$(BLUE)Following logs... (Press Ctrl+C to stop)$(NC)"
	$(DOCKER_COMPOSE) logs -f

rebuild-fresh: ## Complete rebuild with cleanup, pull latest images, and start with logs
	@echo "$(BLUE)Performing fresh rebuild with cleanup...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ .env file not found! Copy .env.example and configure it.$(NC)"; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker system prune -f
	docker pull postgres:15-alpine
	$(DOCKER_COMPOSE) build --no-cache --pull
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✅ Fresh rebuild completed and containers started!$(NC)"
	@echo "$(BLUE)Following logs... (Press Ctrl+C to stop)$(NC)"
	$(DOCKER_COMPOSE) logs -f

docker-clean: ## Clean Docker images and containers
	@echo "$(BLUE)Cleaning Docker resources...$(NC)"
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker image prune -f
	docker container prune -f
	@echo "$(GREEN)✅ Docker cleanup completed!$(NC)"

# Database Commands
# =============================================================================
db-init: ## Initialize database
	@echo "$(BLUE)Initializing database...$(NC)"
	$(ALEMBIC) upgrade head
	@echo "$(GREEN)✅ Database initialized!$(NC)"

db-migrate: ## Create new migration
	@echo "$(BLUE)Creating new migration...$(NC)"
	@read -p "Migration description: " desc; \
	$(ALEMBIC) revision --autogenerate -m "$$desc"
	@echo "$(GREEN)✅ Migration created!$(NC)"

db-upgrade: ## Upgrade database to latest migration
	@echo "$(BLUE)Upgrading database...$(NC)"
	$(ALEMBIC) upgrade head
	@echo "$(GREEN)✅ Database upgraded!$(NC)"

db-downgrade: ## Downgrade database by one migration
	@echo "$(BLUE)Downgrading database...$(NC)"
	$(ALEMBIC) downgrade -1
	@echo "$(GREEN)✅ Database downgraded!$(NC)"

db-reset: ## Reset database (dangerous!)
	@echo "$(RED)⚠️  This will destroy all data!$(NC)"
	@read -p "Are you sure? [y/N]: " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		$(DOCKER_COMPOSE) down -v; \
		docker volume rm easy_track_postgres_data 2>/dev/null || true; \
		$(DOCKER_COMPOSE) up -d postgres; \
		sleep 5; \
		$(MAKE) db-init; \
		echo "$(GREEN)✅ Database reset completed!$(NC)"; \
	else \
		echo "$(YELLOW)Database reset cancelled$(NC)"; \
	fi

db-shell: ## Connect to database shell
	@echo "$(BLUE)Connecting to database...$(NC)"
	$(DOCKER_COMPOSE) exec postgres psql -U user -d easy_track

db-backup: ## Backup database
	@echo "$(BLUE)Creating database backup...$(NC)"
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	$(DOCKER_COMPOSE) exec postgres pg_dump -U user easy_track > backups/backup_$$timestamp.sql; \
	echo "$(GREEN)✅ Backup created: backups/backup_$$timestamp.sql$(NC)"

db-restore: ## Restore database from backup
	@echo "$(BLUE)Available backups:$(NC)"
	@ls -la backups/*.sql 2>/dev/null || echo "No backups found"
	@read -p "Enter backup filename: " backup; \
	if [ -f "backups/$$backup" ]; then \
		$(DOCKER_COMPOSE) exec -T postgres psql -U user -d easy_track < backups/$$backup; \
		echo "$(GREEN)✅ Database restored from $$backup$(NC)"; \
	else \
		echo "$(RED)❌ Backup file not found!$(NC)"; \
	fi

# Deployment Commands
# =============================================================================
deploy: docker-run ## Deploy to production
	@echo "$(BLUE)Deploying to production...$(NC)"
	$(MAKE) health-check
	@echo "$(GREEN)✅ Deployment completed!$(NC)"

deploy-prod: ## Deploy to production environment
	@echo "$(BLUE)Deploying to production...$(NC)"
	@if [ ! -f .env.production ]; then \
		echo "$(RED)❌ .env.production file not found!$(NC)"; \
		exit 1; \
	fi
	cp .env.production .env
	$(DOCKER_COMPOSE) -f docker-compose.yml up -d --build
	$(MAKE) health-check
	@echo "$(GREEN)✅ Production deployment completed!$(NC)"

deploy-staging: ## Deploy to staging environment
	@echo "$(BLUE)Deploying to staging...$(NC)"
	@if [ ! -f .env.staging ]; then \
		echo "$(RED)❌ .env.staging file not found!$(NC)"; \
		exit 1; \
	fi
	cp .env.staging .env
	$(DOCKER_COMPOSE) -f docker-compose.yml up -d --build
	$(MAKE) health-check
	@echo "$(GREEN)✅ Staging deployment completed!$(NC)"

health-check: ## Check service health
	@echo "$(BLUE)Checking service health...$(NC)"
	@timeout=60; \
	while [ $$timeout -gt 0 ]; do \
		if $(DOCKER_COMPOSE) ps | grep -q "Up"; then \
			echo "$(GREEN)✅ Services are healthy!$(NC)"; \
			exit 0; \
		fi; \
		echo "Waiting for services... ($$timeout seconds remaining)"; \
		sleep 5; \
		timeout=$$((timeout-5)); \
	done; \
	echo "$(RED)❌ Health check failed!$(NC)"; \
	exit 1

scale-up: ## Scale up bot instances
	@echo "$(BLUE)Scaling up bot instances...$(NC)"
	@read -p "Number of instances [3]: " instances; \
	instances=$${instances:-3}; \
	$(DOCKER_COMPOSE) up -d --scale bot=$$instances
	@echo "$(GREEN)✅ Scaled up to $$instances instances!$(NC)"

scale-down: ## Scale down to single bot instance
	@echo "$(BLUE)Scaling down to single instance...$(NC)"
	$(DOCKER_COMPOSE) up -d --scale bot=1
	@echo "$(GREEN)✅ Scaled down to 1 instance!$(NC)"

# Release Commands
# =============================================================================
release: ## Create a new release
	@echo "$(BLUE)Creating new release...$(NC)"
	@echo "Current version: $$(grep -E "^__version__" src/easy_track/__init__.py | cut -d'"' -f2)"
	@read -p "Enter new version: " version; \
	if [ -n "$$version" ]; then \
		sed -i.bak "s/__version__ = \".*\"/__version__ = \"$$version\"/" src/easy_track/__init__.py; \
		sed -i.bak "s/version=\".*\"/version=\"$$version\"/" setup.py; \
		rm -f src/easy_track/__init__.py.bak setup.py.bak; \
		git add src/easy_track/__init__.py setup.py; \
		git commit -m "Bump version to $$version"; \
		git tag -a "v$$version" -m "Release version $$version"; \
		echo "$(GREEN)✅ Release $$version created!$(NC)"; \
		echo "$(YELLOW)Don't forget to: git push && git push --tags$(NC)"; \
	else \
		echo "$(RED)❌ Version not provided!$(NC)"; \
	fi

# Monitoring Commands
# =============================================================================
status: ## Show service status
	@echo "$(BLUE)Service Status:$(NC)"
	@echo "==============="
	@$(DOCKER_COMPOSE) ps || echo "Docker Compose not running"
	@echo ""
	@echo "$(BLUE)Docker Images:$(NC)"
	@docker images | grep $(PROJECT_NAME) || echo "No images found"
	@echo ""
	@echo "$(BLUE)Log Files:$(NC)"
	@ls -la logs/ 2>/dev/null || echo "No log directory found"

monitor: ## Monitor logs in real-time
	@echo "$(BLUE)Monitoring logs...$(NC)"
	@echo "Press Ctrl+C to stop"
	@$(DOCKER_COMPOSE) logs -f bot postgres

# Development Utilities
# =============================================================================
shell: ## Open Python shell with project context
	@echo "$(BLUE)Opening Python shell...$(NC)"
	@PYTHONPATH=src $(PYTHON) -c "import sys; sys.path.insert(0, 'src'); from easy_track import *; print('EasyTrack modules loaded!')"

jupyter: ## Start Jupyter notebook for development
	@echo "$(BLUE)Starting Jupyter notebook...$(NC)"
	@if command -v jupyter >/dev/null 2>&1; then \
		PYTHONPATH=src jupyter notebook; \
	else \
		echo "$(RED)❌ Jupyter not installed. Install with: pip install jupyter$(NC)"; \
	fi

docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	@if command -v sphinx-build >/dev/null 2>&1; then \
		sphinx-build -b html docs/ docs/_build/html/; \
		echo "$(GREEN)✅ Documentation generated in docs/_build/html/$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Sphinx not installed, skipping...$(NC)"; \
	fi

# Emergency Commands
# =============================================================================
emergency-stop: ## Emergency stop all services
	@echo "$(RED)🚨 EMERGENCY STOP$(NC)"
	@$(DOCKER_COMPOSE) kill
	@docker kill $$(docker ps -q --filter ancestor=$(DOCKER_IMAGE)) 2>/dev/null || true
	@pkill -f "easy_track" || true
	@echo "$(GREEN)✅ Emergency stop completed!$(NC)"

emergency-logs: ## Show recent error logs
	@echo "$(RED)🚨 RECENT ERROR LOGS$(NC)"
	@echo "===================="
	@$(DOCKER_COMPOSE) logs --tail=50 bot | grep -i error || echo "No recent errors in bot logs"
	@$(DOCKER_COMPOSE) logs --tail=50 postgres | grep -i error || echo "No recent errors in database logs"

# Quick Development Commands
# =============================================================================
dev: dev-setup docker-run ## Quick development setup and run
	@echo "$(GREEN)✅ Development environment ready!$(NC)"
	@echo "$(CYAN)Bot is running at: check Docker logs$(NC)"

prod: deploy-prod ## Quick production deployment

quick-test: format lint test ## Quick code quality check

all-checks: clean format lint type-check test-cov ## Run all quality checks

# Print variables for debugging
debug: ## Show Makefile variables
	@echo "$(BLUE)Makefile Variables:$(NC)"
	@echo "=================="
	@echo "PROJECT_NAME: $(PROJECT_NAME)"
	@echo "PYTHON: $(PYTHON)"
	@echo "DOCKER_IMAGE: $(DOCKER_IMAGE)"
	@echo "CONTAINER_NAME: $(CONTAINER_NAME)"
	@echo "POSTGRES_CONTAINER: $(POSTGRES_CONTAINER)"
