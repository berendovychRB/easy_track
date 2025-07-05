#!/usr/bin/env python3
"""
Database Schema Inspector for EasyTrack

This script inspects the actual database schema to identify the root cause
of the SQLAlchemy boolean type mismatch error.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from sqlalchemy import text

from easy_track.database import DatabaseManager, init_db
from easy_track.models import UserMeasurementType

# Load environment variables
load_dotenv()


async def inspect_database_schema():
    """Comprehensive database schema inspection."""
    print("🔍 Database Schema Inspector")
    print("=" * 50)

    try:
        # Initialize database first
        await init_db()
        print("✅ Database initialized")

        async def detailed_inspection(session):
            print("\n📊 Table Information:")
            print("-" * 30)

            # Get all tables
            tables_result = await session.execute(
                text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            )
            tables = [row[0] for row in tables_result.fetchall()]
            print(f"Found tables: {', '.join(tables)}")

            # Inspect each table in detail
            for table_name in tables:
                print(f"\n🔍 Table: {table_name}")
                print("-" * 20)

                # Get column information
                columns_result = await session.execute(
                    text(f"""
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale
                    FROM information_schema.columns
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                """)
                )

                columns = columns_result.fetchall()
                for col in columns:
                    nullable = "NULL" if col.is_nullable == "YES" else "NOT NULL"
                    default = (
                        f" DEFAULT {col.column_default}" if col.column_default else ""
                    )
                    length = (
                        f"({col.character_maximum_length})"
                        if col.character_maximum_length
                        else ""
                    )
                    precision = (
                        f"({col.numeric_precision},{col.numeric_scale})"
                        if col.numeric_precision
                        else ""
                    )

                    print(
                        f"  {col.column_name}: {col.data_type}{length}{precision} {nullable}{default}"
                    )

            print("\n🔗 Foreign Key Constraints:")
            print("-" * 30)

            fk_result = await session.execute(
                text("""
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    tc.constraint_name
                FROM
                    information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                ORDER BY tc.table_name, kcu.column_name
            """)
            )

            fks = fk_result.fetchall()
            for fk in fks:
                print(
                    f"  {fk.table_name}.{fk.column_name} -> {fk.foreign_table_name}.{fk.foreign_column_name}"
                )

            print("\n📋 Indexes:")
            print("-" * 30)

            index_result = await session.execute(
                text("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname
            """)
            )

            indexes = index_result.fetchall()
            for idx in indexes:
                print(f"  {idx.tablename}: {idx.indexname}")
                print(f"    {idx.indexdef}")

        await DatabaseManager.execute_with_session(detailed_inspection)

    except Exception as e:
        print(f"❌ Schema inspection failed: {e}")
        import traceback

        traceback.print_exc()


async def test_problematic_queries():
    """Test the exact queries that are causing issues."""
    print("\n🧪 Testing Problematic Queries")
    print("=" * 40)

    async def run_query_tests(session):
        print("\n1. Testing raw SQL queries:")

        # Test 1: Basic user_measurement_types query
        try:
            result = await session.execute(
                text("""
                SELECT id, user_id, measurement_type_id, is_active, created_at, updated_at
                FROM user_measurement_types
                LIMIT 5
            """)
            )
            rows = result.fetchall()
            print(f"✅ Basic query: {len(rows)} rows")

            if rows:
                for row in rows[:2]:
                    print(
                        f"   Row: id={row.id}, user_id={row.user_id}, active={row.is_active} (type: {type(row.is_active)})"
                    )
        except Exception as e:
            print(f"❌ Basic query failed: {e}")

        # Test 2: Boolean filtering
        try:
            result = await session.execute(
                text("""
                SELECT id, user_id, measurement_type_id, is_active
                FROM user_measurement_types
                WHERE is_active = true
                LIMIT 5
            """)
            )
            rows = result.fetchall()
            print(f"✅ Boolean filter (true): {len(rows)} rows")
        except Exception as e:
            print(f"❌ Boolean filter failed: {e}")

        # Test 3: Check for any non-boolean values in is_active
        try:
            result = await session.execute(
                text("""
                SELECT is_active, COUNT(*)
                FROM user_measurement_types
                GROUP BY is_active
                ORDER BY is_active
            """)
            )
            rows = result.fetchall()
            print("✅ is_active value distribution:")
            for row in rows:
                print(
                    f"   {row.is_active} ({type(row.is_active).__name__}): {row.count} records"
                )
        except Exception as e:
            print(f"❌ Value distribution check failed: {e}")

        # Test 4: Check for any weird data types
        try:
            result = await session.execute(
                text("""
                SELECT
                    column_name,
                    data_type,
                    pg_typeof(is_active) as actual_type
                FROM user_measurement_types, information_schema.columns
                WHERE table_name = 'user_measurement_types'
                AND column_name = 'is_active'
                LIMIT 1
            """)
            )
            row = result.fetchone()
            if row:
                print("✅ is_active column type check:")
                print(f"   Schema type: {row.data_type}")
                print(f"   Actual type: {row.actual_type}")
        except Exception as e:
            print(f"❌ Type check failed: {e}")

        print("\n2. Testing SQLAlchemy queries:")

        # Test 5: Simple SQLAlchemy query
        try:
            from sqlalchemy import select

            result = await session.execute(
                select(UserMeasurementType.id, UserMeasurementType.is_active).limit(5)
            )
            rows = result.fetchall()
            print(f"✅ Simple SQLAlchemy: {len(rows)} rows")
            for row in rows[:2]:
                print(
                    f"   Row: id={row.id}, active={row.is_active} (type: {type(row.is_active)})"
                )
        except Exception as e:
            print(f"❌ Simple SQLAlchemy failed: {e}")

        # Test 6: SQLAlchemy with boolean filter
        try:
            result = await session.execute(
                select(UserMeasurementType)
                .where(UserMeasurementType.is_active == True)
                .limit(3)
            )
            rows = result.scalars().all()
            print(f"✅ SQLAlchemy boolean filter: {len(rows)} rows")
        except Exception as e:
            print(f"❌ SQLAlchemy boolean filter failed: {e}")
            print(f"   Error details: {e!s}")

        # Test 7: Alternative boolean comparisons
        try:
            result = await session.execute(
                select(UserMeasurementType)
                .where(UserMeasurementType.is_active.is_(True))
                .limit(3)
            )
            rows = result.scalars().all()
            print(f"✅ SQLAlchemy .is_(True): {len(rows)} rows")
        except Exception as e:
            print(f"❌ SQLAlchemy .is_(True) failed: {e}")

        # Test 8: Multiple where clauses (the problematic pattern)
        try:
            result = await session.execute(
                select(UserMeasurementType)
                .where(UserMeasurementType.user_id == 1)
                .where(UserMeasurementType.is_active == True)
                .limit(3)
            )
            rows = result.scalars().all()
            print(f"✅ Multiple where clauses: {len(rows)} rows")
        except Exception as e:
            print(f"❌ Multiple where clauses failed: {e}")
            print(f"   This might be our culprit: {e!s}")

    await DatabaseManager.execute_with_session(run_query_tests)


async def check_database_version():
    """Check PostgreSQL and asyncpg versions."""
    print("\n🔧 Database Version Information")
    print("=" * 35)

    async def version_check(session):
        # PostgreSQL version
        result = await session.execute(text("SELECT version()"))
        pg_version = result.scalar()
        print(f"PostgreSQL: {pg_version}")

        # Check asyncpg version
        import asyncpg

        print(f"asyncpg: {asyncpg.__version__}")

        # Check SQLAlchemy version
        import sqlalchemy

        print(f"SQLAlchemy: {sqlalchemy.__version__}")

        # Check database encoding
        result = await session.execute(text("SHOW server_encoding"))
        encoding = result.scalar()
        print(f"Database encoding: {encoding}")

        # Check locale settings
        result = await session.execute(text("SHOW lc_collate"))
        collate = result.scalar()
        print(f"LC_COLLATE: {collate}")

    await DatabaseManager.execute_with_session(version_check)


async def create_minimal_test_data():
    """Create minimal test data to reproduce the issue."""
    print("\n📝 Creating Minimal Test Data")
    print("=" * 32)

    async def create_data(session):
        # Check if we already have test data
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar()

        if user_count > 0:
            print(f"Found {user_count} existing users, skipping data creation")
            return

        print("Creating test data...")

        # Create tables manually if they don't exist
        await session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        )

        await session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS measurement_types (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                unit VARCHAR(20) NOT NULL,
                description TEXT,
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        )

        await session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS user_measurement_types (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                measurement_type_id INTEGER NOT NULL REFERENCES measurement_types(id),
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                UNIQUE(user_id, measurement_type_id)
            )
        """)
        )

        # Insert test data
        await session.execute(
            text("""
            INSERT INTO users (telegram_id, username, first_name, last_name)
            VALUES (123456789, 'testuser', 'Test', 'User')
            ON CONFLICT (telegram_id) DO NOTHING
        """)
        )

        await session.execute(
            text("""
            INSERT INTO measurement_types (name, unit, description)
            VALUES
                ('Weight', 'kg', 'Body weight'),
                ('Height', 'cm', 'Body height')
            ON CONFLICT (name) DO NOTHING
        """)
        )

        await session.execute(
            text("""
            INSERT INTO user_measurement_types (user_id, measurement_type_id, is_active)
            SELECT u.id, mt.id, true
            FROM users u, measurement_types mt
            WHERE u.telegram_id = 123456789
            AND mt.name IN ('Weight', 'Height')
            ON CONFLICT (user_id, measurement_type_id) DO NOTHING
        """)
        )

        await session.commit()
        print("✅ Test data created successfully")

    await DatabaseManager.execute_with_session(create_data)


async def main():
    """Main inspection routine."""
    print("🚀 Starting Comprehensive Database Inspection")
    print("=" * 55)

    try:
        await check_database_version()
        await create_minimal_test_data()
        await inspect_database_schema()
        await test_problematic_queries()

        print("\n🎯 Summary and Recommendations:")
        print("=" * 35)
        print("1. Check the 'Multiple where clauses' test result above")
        print("2. Look for any non-boolean values in is_active columns")
        print("3. Verify SQLAlchemy and asyncpg version compatibility")
        print("4. Check if there are any custom types or constraints")
        print("\n✅ Inspection completed!")

    except Exception as e:
        print(f"\n❌ Inspection failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
