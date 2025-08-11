# 🏃‍♂️ EasySize - Telegram Body Measurement Bot

A powerful and scalable Telegram bot for athletes to track their body measurements with a clean database design and modern async architecture.

## ✨ Features

- 📊 **Flexible Measurement Tracking**: Users can choose which measurement types to track individually
- 📈 **Progress Monitoring**: View your improvement over time with detailed statistics
- 🔔 **Smart Notifications**: Customizable periodic reminders for measurement tracking
- 🔄 **Dynamic Configuration**: Add/remove measurement types without affecting existing data
- 📱 **User-Friendly Interface**: Intuitive inline keyboard navigation
- 🌍 **Multilingual Support**: Full English and Ukrainian language support
- 🚀 **High Performance**: Built with async/await for handling multiple users concurrently
- 🐳 **Docker Ready**: Complete containerization with PostgreSQL
- 🔒 **Production Ready**: Proper error handling, logging, and health checks

## 📊 Supported Measurements

- Weight (kg)
- Waist circumference (cm)
- Chest circumference (cm)
- Biceps circumference (cm)
- Thigh circumference (cm)
- Hip circumference (cm)
- Neck circumference (cm)
- Body Fat Percentage (%)
- Muscle Mass (kg)

*New measurement types can be easily added through the database.*

### 🔔 Notification System

- **Flexible Scheduling**: Daily or weekly reminders at your preferred time
- **Custom Time Selection**: 24-hour format time input (e.g., 09:00, 14:30, 21:00)
- **Multiple Schedules**: Set up different reminders for different days
- **Easy Management**: Enable/disable or delete notification schedules
- **Smart Reminders**: Motivational messages to encourage consistent tracking
- **Multilingual**: Notifications in English and Ukrainian

## 🛠 Tech Stack

- **Bot Framework**: aiogram 3.x (async)
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async ORM)
- **Migrations**: Alembic
- **Containerization**: Docker & Docker Compose
- **Language**: Python 3.11+

## 🏗 Architecture

### Database Schema

```sql
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│    Users    │    │ UserMeasurement  │    │ MeasurementType │
│             │    │      Types       │    │                 │
├─────────────┤    ├──────────────────┤    ├─────────────────┤
│ id (PK)     │◄──┤│ user_id (FK)     │   ┌┤│ id (PK)         │
│ telegram_id │   ││ measurement_     │   │││ name            │
│ username    │   ││   type_id (FK)   │───┘││ unit            │
│ first_name  │   ││ is_active        │    ││ description     │
│ last_name   │   ││ created_at       │    ││ is_active       │
│ is_active   │   ││ updated_at       │    │└─────────────────┘
│ created_at  │   │└──────────────────┘    │
│ updated_at  │   │                        │
└─────────────┘   │  ┌─────────────────┐   │
                  │  │  Measurements   │   │
                  │  │                 │   │
                  │  ├─────────────────┤   │
                  └─►│ user_id (FK)    │   │
                     │ measurement_    │───┘
                     │   type_id (FK)  │
                     │ value           │
                     │ measurement_    │
                     │   date          │
                     │ notes           │
                     │ created_at      │
                     │ updated_at      │
                     └─────────────────┘
```

### Key Design Decisions

1. **Flexible Measurement Types**: Users can select which measurements to track via `UserMeasurementType` junction table
2. **Extensible Schema**: New measurement types can be added without schema changes
3. **Async Architecture**: Full async/await implementation for concurrent user handling
4. **Repository Pattern**: Clean separation of data access logic
5. **Proper Indexing**: Optimized database queries for performance

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### 1. Clone and Setup

```bash
git clone <repository-url>
cd easy_track
make dev-setup  # This copies .env.example to .env
```

### 2. Configure Environment

Edit `.env` file:

```env
BOT_TOKEN=your_telegram_bot_token_here
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/easy_track
POSTGRES_DB=easy_track
POSTGRES_USER=user
POSTGRES_PASSWORD=your_secure_password
```

### 3. Start the Application

```bash
# Quick development start
make dev

# Or step by step:
# Start with Docker Compose
make docker-run
# Or: docker-compose up -d

# Check logs
make docker-logs
# Or: docker-compose logs -f bot

# Stop the application
make docker-stop
# Or: docker-compose down
```

### 4. Test Your Bot

1. Start a chat with your bot on Telegram
2. Send `/start` to begin
3. Use `/menu` to access all features

## 🛠️ Makefile Commands

The project includes a comprehensive Makefile for easy development and deployment:

### Development Commands
```bash
make help              # Show all available commands
make dev-setup         # Complete development environment setup
make install           # Install production dependencies
make install-dev       # Install development dependencies
make run               # Run bot locally
make clean             # Clean temporary files
```

### Code Quality
```bash
make test              # Run tests
make test-cov          # Run tests with coverage
make lint              # Run linting checks
make format            # Format code with black
make type-check        # Run type checking
make pre-commit        # Run all pre-commit checks
```

### Docker Commands
```bash
make build             # Build Docker image
make docker-run        # Start with Docker Compose
make docker-stop       # Stop Docker services
make docker-logs       # Show Docker logs
make docker-clean      # Clean Docker resources
```

### Database Commands
```bash
make db-init           # Initialize database
make db-migrate        # Create new migration
make db-upgrade        # Apply migrations
make db-downgrade      # Rollback migration
make db-reset          # Reset database (dangerous!)
make db-shell          # Connect to database
make db-backup         # Create database backup
make db-restore        # Restore from backup
```

### Deployment Commands
```bash
make deploy            # Deploy to production
make health-check      # Check service health
make scale-up          # Scale up bot instances
make scale-down        # Scale down to single instance
```

## 🔧 Development Setup

### Local Development

```bash
# Quick setup with Makefile
make dev-setup

# Or manual setup:
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
make install-dev
# Or: pip install -r requirements-dev.txt

# Set up local PostgreSQL
# Update DATABASE_URL in .env to point to your local instance

# Run database migrations
make db-upgrade
# Or: alembic upgrade head

# Start the bot locally
make run
# Or: python -m easy_track.main
```

### Database Migrations

```bash
# Create a new migration
make db-migrate
# Or: alembic revision --autogenerate -m "description of changes"

# Apply migrations
make db-upgrade
# Or: alembic upgrade head

# Rollback migrations
make db-downgrade
# Or: alembic downgrade -1

# Reset database (development only)
make db-reset
```

### Adding New Measurement Types

```sql
INSERT INTO measurement_types (name, unit, description, is_active)
VALUES ('New Measurement', 'unit', 'Description', true);
```

## 📁 Project Structure

```
easy_track/
├── 📄 Makefile                # Development and deployment commands
├── 📄 setup.py                # Package configuration
├── 📄 requirements.txt        # Production dependencies
├── 📄 requirements-dev.txt    # Development dependencies
├── 📄 Dockerfile              # Container configuration
├── 📄 docker-compose.yml      # Multi-container setup
├── 📄 alembic.ini             # Migration configuration
├── 📄 init-db.sql             # Database initialization
├── 📄 start.sh                # Production startup script
├── 📄 .env.example            # Environment template
├── 📄 .pre-commit-config.yaml # Code quality hooks
├── 📁 src/easy_track/         # Main application package
│   ├── 📄 __init__.py         # Package initialization
│   ├── 📄 main.py             # Application entry point
│   ├── 📄 bot.py              # Telegram bot implementation
│   ├── 📄 models.py           # SQLAlchemy ORM models
│   ├── 📄 database.py         # Database configuration
│   └── 📄 repositories.py     # Data access layer
├── 📁 alembic/                # Database migrations
│   ├── 📄 env.py
│   ├── 📄 script.py.mako
│   └── 📁 versions/
├── 📁 tests/                  # Test files (to be created)
├── 📁 docs/                   # Documentation (to be created)
├── 📁 backups/                # Database backups
└── 📁 logs/                   # Application logs
```

## 🤖 Bot Commands

- `/start` - Initialize bot and show welcome message
- `/menu` - Display main menu with all options

### Bot Features

1. **📝 Add Measurement** - Record new measurements
2. **⚙️ Manage Types** - Add/remove measurement types to track
3. **📊 View Progress** - See detailed progress for each measurement type
4. **📈 Statistics** - Overview of all your tracking data

## 🔍 Monitoring & Logs

### Health Checks

```bash
# Check container health
docker-compose ps

# View bot logs
docker-compose logs bot

# View database logs
docker-compose logs postgres
```

### Database Monitoring

```bash
# Connect to database
docker-compose exec postgres psql -U user -d easy_track

# Check database statistics
SELECT
    schemaname,
    tablename,
    n_tup_ins as "Inserts",
    n_tup_upd as "Updates",
    n_tup_del as "Deletes"
FROM pg_stat_user_tables;
```

## 🛡 Security Best Practices

1. **Environment Variables**: Never commit sensitive data
2. **Database Security**: Use strong passwords and limit connections
3. **Bot Token**: Keep your bot token secure and rotate regularly
4. **Container Security**: Run containers with non-root users
5. **Network Security**: Use Docker networks for service isolation

## 🚀 Production Deployment

### Docker Deployment

```bash
# Production deployment
make deploy-prod

# Or manual:
# Production build
docker-compose -f docker-compose.yml up -d

# Scale bot instances (if needed)
make scale-up
# Or: docker-compose up -d --scale bot=3
```

### Environment Variables for Production

```env
BOT_TOKEN=your_production_bot_token
DATABASE_URL=postgresql+asyncpg://user:secure_password@db_host:5432/easy_track
APP_ENV=production
LOG_LEVEL=INFO
```

### Performance Tuning

1. **Database**: Adjust PostgreSQL settings in `init-db.sql`
2. **Connection Pool**: Modify pool settings in `database.py`
3. **Bot Concurrency**: aiogram handles concurrent users automatically

## 🧪 Testing

```bash
# Run basic connectivity tests
python -c "
import asyncio
from database import init_db
asyncio.run(init_db())
print('✅ Database connection successful')
"

# Test bot token
python -c "
import os
from aiogram import Bot
bot = Bot(token=os.getenv('BOT_TOKEN'))
print('✅ Bot token valid')
"
```

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check bot token validity
   - Verify webhook isn't set (use polling)
   - Check network connectivity

2. **Database connection failed**
   - Verify PostgreSQL is running
   - Check connection string format
   - Ensure database exists

3. **Migration errors**
   - Check Alembic configuration
   - Verify database permissions
   - Review migration scripts

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
make run
# Or: python -m easy_track.main

# Show recent error logs
make emergency-logs

# Monitor logs in real-time
make monitor
```

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale bot instances
make scale-up
# Or: docker-compose up -d --scale bot=3

# Scale down
make scale-down

# Use load balancer for webhook mode
# Configure Redis for shared session storage
```

### Database Optimization

```sql
-- Monitor slow queries
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Add custom indexes
CREATE INDEX CONCURRENTLY idx_custom
ON table_name(column_name);
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Set up development environment: `make dev-setup`
4. Make your changes
5. Run quality checks: `make all-checks`
6. Add tests if applicable: `make test`
7. Submit a pull request

### Development Workflow
```bash
# Setup development environment
make dev-setup

# Make your changes
# ...

# Run all quality checks before committing
make all-checks

# Create a commit (pre-commit hooks will run automatically)
git commit -m "Your changes"

# Push your branch
git push origin your-feature-branch
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review Docker logs for error details

---

**Made with ❤️ for athletes who want to track their progress efficiently!**
