-- Database initialization script for EasySize
-- This script sets up the database with proper permissions and extensions

-- Create database if it doesn't exist (handled by docker-compose)
-- CREATE DATABASE easy_track;

-- Connect to the database
\c easy_track;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create indexes for better performance
-- These will be created after tables are set up by SQLAlchemy

-- Grant permissions to the application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "user";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "user";
GRANT ALL PRIVILEGES ON SCHEMA public TO "user";

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "user";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO "user";

-- Optimize PostgreSQL settings for the application
-- These are basic optimizations, adjust based on your server resources
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.7;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Create custom indexes that will be useful for the application
-- Note: These will be created after SQLAlchemy creates the tables

-- Function to create indexes after tables exist
CREATE OR REPLACE FUNCTION create_performance_indexes()
RETURNS void AS $$
BEGIN
    -- Only create indexes if tables exist
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users') THEN
        -- Index for fast user lookups by telegram_id
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_telegram_id
        ON users(telegram_id);

        -- Index for active users
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active
        ON users(is_active) WHERE is_active = true;
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'measurements') THEN
        -- Composite index for user measurements queries
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_measurements_user_type_date
        ON measurements(user_id, measurement_type_id, measurement_date DESC);

        -- Index for date range queries
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_measurements_date
        ON measurements(measurement_date DESC);

        -- Index for user-specific queries
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_measurements_user_id
        ON measurements(user_id);
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_measurement_types') THEN
        -- Index for active user measurement types
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_measurement_types_active
        ON user_measurement_types(user_id, is_active) WHERE is_active = true;
    END IF;

    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'measurement_types') THEN
        -- Index for active measurement types
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_measurement_types_active
        ON measurement_types(is_active, name) WHERE is_active = true;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create a function to clean up old data (optional, for maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_data(days_to_keep INTEGER DEFAULT 365)
RETURNS void AS $$
BEGIN
    -- This function can be used to clean up very old measurements if needed
    -- Uncomment and modify as needed for your retention policy

    -- DELETE FROM measurements
    -- WHERE measurement_date < NOW() - INTERVAL '%s days', days_to_keep
    -- AND user_id IN (SELECT id FROM users WHERE is_active = false);

    RAISE NOTICE 'Cleanup function ready (currently disabled for safety)';
END;
$$ LANGUAGE plpgsql;

-- Create a function to get user statistics
CREATE OR REPLACE FUNCTION get_user_measurement_stats(p_user_id INTEGER, p_measurement_type_id INTEGER)
RETURNS TABLE(
    measurement_count BIGINT,
    avg_value NUMERIC,
    min_value NUMERIC,
    max_value NUMERIC,
    latest_value NUMERIC,
    latest_date TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as measurement_count,
        AVG(m.value)::NUMERIC as avg_value,
        MIN(m.value)::NUMERIC as min_value,
        MAX(m.value)::NUMERIC as max_value,
        (SELECT value FROM measurements
         WHERE user_id = p_user_id AND measurement_type_id = p_measurement_type_id
         ORDER BY measurement_date DESC LIMIT 1)::NUMERIC as latest_value,
        (SELECT measurement_date FROM measurements
         WHERE user_id = p_user_id AND measurement_type_id = p_measurement_type_id
         ORDER BY measurement_date DESC LIMIT 1) as latest_date
    FROM measurements m
    WHERE m.user_id = p_user_id
    AND m.measurement_type_id = p_measurement_type_id;
END;
$$ LANGUAGE plpgsql;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'EasySize database initialization completed successfully';
    RAISE NOTICE 'Database: easy_track';
    RAISE NOTICE 'Timestamp: %', NOW();
END $$;
