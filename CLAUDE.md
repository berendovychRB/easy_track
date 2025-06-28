# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EasyTrack is a Telegram bot for tracking body measurements built with Python 3.11+, aiogram 3.x, SQLAlchemy 2.0 (async), and PostgreSQL. The architecture uses async/await throughout with a repository pattern for data access.

## Development Commands

### Setup and Installation
- `make dev-setup` - Complete development environment setup (installs deps, creates .env from template, sets up pre-commit)
- `make install-dev` - Install development dependencies
- `make install` - Install production dependencies only

### Running the Application
- `make run` - Run bot locally (requires .env file and database setup)
- `make docker-run` - Start with Docker Compose (recommended for development)
- `make dev` - Quick setup and run (combines dev-setup + docker-run)

### Code Quality
- `make test` - Run tests with pytest
- `make test-cov` - Run tests with coverage report
- `make lint` - Run flake8 linting
- `make format` - Format code with black (line length 88)
- `make type-check` - Run mypy type checking
- `make pre-commit` - Run all quality checks
- `make all-checks` - Complete quality check suite (clean, format, lint, type-check, security-check, test-cov)

### Docker Operations
- `make build` - Build Docker image
- `make docker-stop` - Stop Docker services
- `make docker-logs` - Show Docker logs
- `make docker-clean` - Clean Docker resources
- `make rebuild-and-start` - Rebuild containers and start with logs
- `make rebuild-fresh` - Complete rebuild with cleanup and fresh images

### Database Management
- `make db-init` - Initialize database (run alembic upgrade head)
- `make db-migrate` - Create new migration (prompts for description)
- `make db-upgrade` - Apply pending migrations
- `make db-downgrade` - Rollback one migration
- `make db-reset` - Reset database (DANGEROUS - destroys all data)
- `make db-shell` - Connect to PostgreSQL database shell
- `make db-backup` - Create timestamped database backup
- `make db-restore` - Restore from backup file

## Architecture

### Database Schema
The system uses a flexible measurement tracking design:
- **Users**: Store Telegram user information
- **MeasurementTypes**: Define available measurement types (weight, waist, chest, etc.) with units
- **UserMeasurementTypes**: Junction table - users select which measurement types to track
- **Measurements**: Actual measurement values with timestamps

### Key Design Patterns
- **Repository Pattern**: Data access layer in `repositories.py` with separate classes for each entity
- **Async Architecture**: Full async/await using aiogram 3.x and SQLAlchemy 2.0 async
- **Modern SQLAlchemy**: Uses `Mapped` annotations and declarative model definitions
- **Database Session Management**: Centralized in `database.py` with proper connection pooling

### Code Structure
- `src/easy_track/main.py` - Application entry point with logging setup
- `src/easy_track/bot.py` - Telegram bot handlers and FSM states
- `src/easy_track/models.py` - SQLAlchemy ORM models with proper relationships
- `src/easy_track/database.py` - Database configuration and session management
- `src/easy_track/repositories.py` - Data access layer with repository pattern
- `alembic/` - Database migrations

### Environment Configuration
Copy `.env.example` to `.env` and configure:
- `BOT_TOKEN` - Telegram bot token from @BotFather
- `DATABASE_URL` - PostgreSQL connection string (async format with asyncpg)
- Database credentials for Docker Compose setup

### Bot Features
- Flexible measurement type selection per user
- Inline keyboard navigation
- FSM (Finite State Machine) for complex interactions
- Progress tracking and statistics
- Notes support for measurements

## Testing and Quality Assurance

- Tests are run with pytest and should include async test support
- Code is formatted with black (88 character line length)
- Type checking with mypy (ignore missing imports flag used)
- Linting with flake8 (extends ignore: E203,W503)
- Pre-commit hooks available for automated quality checks

## Database Migrations

Use Alembic for schema changes:
1. Modify models in `models.py`
2. Run `make db-migrate` and provide description
3. Review generated migration in `alembic/versions/`
4. Apply with `make db-upgrade`

## Production Deployment

- Docker Compose setup with PostgreSQL and bot services
- Health checks configured for both services
- Proper logging to files and stdout
- Environment-based configuration
- Database connection pooling and optimization settings