#!/usr/bin/env python3
"""
Minimal bot test to reproduce the SQLAlchemy boolean error.
This script creates a minimal setup to test the problematic query.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from sqlalchemy import text

from easy_track.models import User, MeasurementType, UserMeasurementType
from easy_track.database import DatabaseManager, init_db, AsyncSessionLocal
from easy_track.repositories import (
    UserRepository,
    MeasurementTypeRepository,
    UserMeasurementTypeRepository
)

# Load environment variables
load_dotenv()

async def minimal_test():
    """Run minimal test to reproduce the error."""
    print("🔬 Minimal Bot Test - Reproducing SQLAlchemy Error")
    print("=" * 50)

    try:
        # Step 1: Initialize database
        print("1. Initializing database...")
        await init_db()
        print("   ✅ Database initialized")

        # Step 2: Create basic test data
        print("2. Creating test data...")

        async def create_minimal_data(session):
            # Create user
            user = User(
                telegram_id=999888777,
                username="minimal_test",
                first_name="Minimal",
                last_name="Test"
            )
            session.add(user)
            await session.flush()

            # Create measurement type
            measurement_type = MeasurementType(
                name="Test Weight",
                unit="kg",
                description="Test measurement type",
                is_active=True
            )
            session.add(measurement_type)
            await session.flush()

            # Create user measurement type relationship
            user_measurement_type = UserMeasurementType(
                user_id=user.id,
                measurement_type_id=measurement_type.id,
                is_active=True
            )
            session.add(user_measurement_type)
            await session.flush()

            return user.id, measurement_type.id

        user_id, measurement_type_id = await DatabaseManager.execute_with_session(create_minimal_data)
        print(f"   ✅ Created user {user_id} and measurement type {measurement_type_id}")

        # Step 3: Test the problematic query directly
        print("3. Testing problematic query...")

        async def test_direct_query(session):
            # Test 1: Raw SQL first
            print("   3a. Testing raw SQL...")
            result = await session.execute(
                text("""
                    SELECT umt.id, umt.user_id, umt.measurement_type_id, umt.is_active
                    FROM user_measurement_types umt
                    WHERE umt.user_id = :user_id AND umt.is_active = true
                """),
                {"user_id": user_id}
            )
            rows = result.fetchall()
            print(f"      ✅ Raw SQL: {len(rows)} results")

            # Test 2: Simple SQLAlchemy query
            print("   3b. Testing simple SQLAlchemy query...")
            from sqlalchemy import select
            result = await session.execute(
                select(UserMeasurementType).where(UserMeasurementType.user_id == user_id)
            )
            user_types = result.scalars().all()
            print(f"      ✅ Simple query: {len(user_types)} results")

            # Test 3: Query with boolean filter
            print("   3c. Testing boolean filter...")
            result = await session.execute(
                select(UserMeasurementType)
                .where(UserMeasurementType.user_id == user_id)
                .where(UserMeasurementType.is_active == True)
            )
            user_types = result.scalars().all()
            print(f"      ✅ Boolean filter: {len(user_types)} results")

            # Test 4: Query with selectinload
            print("   3d. Testing selectinload...")
            from sqlalchemy.orm import selectinload
            result = await session.execute(
                select(UserMeasurementType)
                .options(selectinload(UserMeasurementType.measurement_type))
                .where(UserMeasurementType.user_id == user_id)
                .where(UserMeasurementType.is_active == True)
            )
            user_types = result.scalars().all()
            print(f"      ✅ Selectinload: {len(user_types)} results")

            # Test each measurement type
            for ut in user_types:
                print(f"         - {ut.measurement_type.name} ({ut.measurement_type.unit})")

            return user_types

        user_types = await DatabaseManager.execute_with_session(test_direct_query)

        # Step 4: Test repository method
        print("4. Testing repository method...")

        async def test_repository(session):
            return await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)

        repo_result = await DatabaseManager.execute_with_session(test_repository)
        print(f"   ✅ Repository method: {len(repo_result)} results")

        # Step 5: Simulate bot scenario
        print("5. Simulating bot add_measurement scenario...")

        async def simulate_bot_scenario(session):
            # This mimics the exact flow in handle_add_measurement
            user_types = await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)

            if not user_types:
                print("   ⚠️  No measurement types found")
                return []

            # Simulate keyboard creation (this is where the error might occur)
            keyboard_data = []
            for user_type in user_types:
                keyboard_data.append({
                    'text': f"{user_type.measurement_type.name} ({user_type.measurement_type.unit})",
                    'callback_data': f"measure_{user_type.measurement_type.id}"
                })

            return keyboard_data

        keyboard_data = await DatabaseManager.execute_with_session(simulate_bot_scenario)
        print(f"   ✅ Bot simulation successful: {len(keyboard_data)} keyboard items")

        for item in keyboard_data:
            print(f"      - {item['text']} -> {item['callback_data']}")

        print("\n🎉 All tests passed! No error reproduced.")
        print("💡 The original error may have been resolved by the query fixes.")

    except Exception as e:
        print(f"\n❌ Error reproduced: {e}")
        print(f"Error type: {type(e).__name__}")

        # Print detailed error information
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

        # Try to diagnose the specific issue
        print("\n🔍 Error Analysis:")
        error_str = str(e).lower()

        if "datatype mismatch" in error_str:
            print("- This is a PostgreSQL datatype mismatch error")
        if "boolean" in error_str and "character varying" in error_str:
            print("- Boolean vs varchar comparison detected")
        if "and must be type boolean" in error_str:
            print("- Issue with AND clause boolean logic")

        print("\n💡 Possible solutions:")
        print("1. Check column types in database")
        print("2. Use explicit boolean casting: .is_(True) instead of == True")
        print("3. Check for string/boolean confusion in WHERE clauses")

        return False

    return True

async def check_database_schema():
    """Check the actual database schema to understand column types."""
    print("\n🔍 Checking database schema...")

    async def check_schema(session):
        # Check column types for user_measurement_types table
        result = await session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'user_measurement_types'
            ORDER BY ordinal_position
        """))

        columns = result.fetchall()
        print("user_measurement_types table schema:")
        for col in columns:
            print(f"  - {col.column_name}: {col.data_type} ({'nullable' if col.is_nullable == 'YES' else 'not null'})")

    try:
        await DatabaseManager.execute_with_session(check_schema)
    except Exception as e:
        print(f"Schema check failed: {e}")

if __name__ == "__main__":
    print("Starting minimal bot test...")

    try:
        success = asyncio.run(minimal_test())
        asyncio.run(check_database_schema())

        if success:
            print("\n✅ Test completed successfully!")
        else:
            print("\n❌ Test failed!")

    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
