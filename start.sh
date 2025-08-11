#!/bin/bash

# EasySize Bot - Production Startup Script
set -e

echo "🚀 Starting EasySize Bot..."

# Function to check if a service is ready
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1

    echo "⏳ Waiting for $service_name to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            echo "✅ $service_name is ready!"
            return 0
        fi

        echo "🔄 Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 2
        ((attempt++))
    done

    echo "❌ $service_name failed to start within expected time"
    exit 1
}

# Function to check environment variables
check_env_vars() {
    echo "🔍 Checking environment variables..."

    if [ -z "$BOT_TOKEN" ]; then
        echo "❌ BOT_TOKEN is not set"
        exit 1
    fi

    if [ -z "$DATABASE_URL" ]; then
        echo "❌ DATABASE_URL is not set"
        exit 1
    fi

    echo "✅ Environment variables are set"
}

# Function to test database connection
test_database() {
    echo "🔍 Testing database connection..."

    python3 -c "
import asyncio
import asyncpg
import os
import sys

# Add src to path for imports
sys.path.insert(0, 'src')

async def test_connection():
    try:
        # Extract connection details from DATABASE_URL
        db_url = os.getenv('DATABASE_URL')
        if 'postgresql+asyncpg://' in db_url:
            db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')

        conn = await asyncpg.connect(db_url)
        await conn.execute('SELECT 1')
        await conn.close()
        print('✅ Database connection successful')
        return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False

result = asyncio.run(test_connection())
sys.exit(0 if result else 1)
"

    if [ $? -ne 0 ]; then
        echo "❌ Database connection test failed"
        exit 1
    fi
}

# Function to run database migrations
run_migrations() {
    echo "🔄 Running database migrations..."

    if [ -f "alembic.ini" ]; then
        # Check if alembic is available
        if command -v alembic &> /dev/null; then
            # Run migrations
            alembic upgrade head
            echo "✅ Database migrations completed"
        else
            echo "⚠️  Alembic not found, skipping migrations"
            echo "💡 Database tables will be created automatically by SQLAlchemy"
        fi
    else
        echo "⚠️  No alembic.ini found, skipping migrations"
        echo "💡 Database tables will be created automatically by SQLAlchemy"
    fi
}

# Function to create log directory
setup_logging() {
    echo "📁 Setting up logging..."

    if [ ! -d "logs" ]; then
        mkdir -p logs
        echo "✅ Created logs directory"
    fi

    # Set proper permissions for log directory
    chmod 755 logs
    echo "✅ Logging setup complete"
}

# Function to validate bot token
validate_bot_token() {
    echo "🤖 Validating bot token..."

    python3 -c "
import asyncio
import aiohttp
import os
import sys

# Add src to path for imports
sys.path.insert(0, 'src')

async def validate_token():
    token = os.getenv('BOT_TOKEN')
    if not token:
        print('❌ Bot token not found')
        return False

    try:
        async with aiohttp.ClientSession() as session:
            url = f'https://api.telegram.org/bot{token}/getMe'
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        bot_info = data.get('result', {})
                        print(f'✅ Bot token valid - Bot: @{bot_info.get(\"username\", \"unknown\")}')
                        return True
                    else:
                        print(f'❌ Bot token invalid: {data.get(\"description\", \"Unknown error\")}')
                        return False
                else:
                    print(f'❌ HTTP {response.status}: Failed to validate bot token')
                    return False
    except Exception as e:
        print(f'❌ Error validating bot token: {e}')
        return False

result = asyncio.run(validate_token())
sys.exit(0 if result else 1)
"

    if [ $? -ne 0 ]; then
        echo "❌ Bot token validation failed"
        exit 1
    fi
}

# Function to handle graceful shutdown
cleanup() {
    echo ""
    echo "🛑 Received shutdown signal"
    echo "🧹 Cleaning up..."

    # Kill the bot process if it's running
    if [ ! -z "$BOT_PID" ]; then
        echo "🔄 Stopping bot process (PID: $BOT_PID)..."
        kill -TERM "$BOT_PID" 2>/dev/null || true
        wait "$BOT_PID" 2>/dev/null || true
    fi

    echo "✅ Cleanup completed"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Main execution flow
main() {
    echo "======================================"
    echo "🤖 EasySize Telegram Bot"
    echo "📅 $(date)"
    echo "======================================"

    # Load environment variables from .env if it exists
    if [ -f ".env" ]; then
        echo "📄 Loading environment variables from .env file..."
        export $(grep -v '^#' .env | xargs)
        echo "✅ Environment variables loaded"
    fi

    # Check prerequisites
    check_env_vars
    setup_logging
    validate_bot_token

    # If running with docker-compose, wait for postgres
    if [ "$WAIT_FOR_POSTGRES" = "true" ] || [ ! -z "$POSTGRES_HOST" ]; then
        POSTGRES_HOST=${POSTGRES_HOST:-postgres}
        POSTGRES_PORT=${POSTGRES_PORT:-5432}
        wait_for_service "$POSTGRES_HOST" "$POSTGRES_PORT" "PostgreSQL"
    fi

    # Test database connection
    test_database

    # Run migrations
    run_migrations

    echo "🎯 Starting bot application..."
    echo "📊 Bot will begin polling for messages..."
    echo "🔄 Use Ctrl+C to stop the bot gracefully"
    echo ""

    # Start the bot
    python3 -m easy_track.main &
    BOT_PID=$!

    echo "🚀 Bot started with PID: $BOT_PID"
    echo "📋 Monitor logs in the logs/ directory"
    echo ""

    # Wait for the bot process
    wait "$BOT_PID"

    echo "🛑 Bot process exited"
}

# Check if required commands are available
check_dependencies() {
    local deps=("python3" "nc")
    local missing_deps=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
        fi
    done

    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo "❌ Missing dependencies: ${missing_deps[*]}"
        echo "💡 Please install the missing dependencies and try again"
        exit 1
    fi
}

# Pre-flight checks
check_dependencies

# Run main function
main "$@"
