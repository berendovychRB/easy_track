#!/usr/bin/env python3
"""
Reproduce Bot Error - Exact Bot Scenario Test

This script reproduces the exact scenario that causes the SQLAlchemy boolean error
by simulating the bot's handle_add_measurement flow step by step.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from sqlalchemy import text

from easy_track.database import DatabaseManager, init_db
from easy_track.repositories import (
    UserRepository,
    MeasurementTypeRepository,
    UserMeasurementTypeRepository
)

# Load environment variables
load_dotenv()

async def setup_bot_test_data():
    """Set up the exact data scenario that triggers the error."""
    print("📝 Setting up bot test data...")

    async def create_bot_scenario(session):
        # Clean existing data
        await session.execute(text("DELETE FROM user_measurement_types"))
        await session.execute(text("DELETE FROM measurements"))
        await session.execute(text("DELETE FROM measurement_types"))
        await session.execute(text("DELETE FROM users"))

        # Reset sequences
        await session.execute(text("ALTER SEQUENCE users_id_seq RESTART WITH 1"))
        await session.execute(text("ALTER SEQUENCE measurement_types_id_seq RESTART WITH 1"))
        await session.execute(text("ALTER SEQUENCE user_measurement_types_id_seq RESTART WITH 1"))

        # Create user exactly like the bot does
        user = await UserRepository.create_user(
            session,
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        print(f"✅ Created user: {user.id} (telegram_id: {user.telegram_id})")

        # Create measurement types like the bot initialization
        weight_type = await MeasurementTypeRepository.create_measurement_type(
            session, "Weight", "kg", "Body weight"
        )
        waist_type = await MeasurementTypeRepository.create_measurement_type(
            session, "Waist", "cm", "Waist circumference"
        )
        print(f"✅ Created measurement types: {weight_type.id}, {waist_type.id}")

        return user.id, weight_type.id, waist_type.id

    return await DatabaseManager.execute_with_session(create_bot_scenario)

async def reproduce_handle_add_measurement_error(user_id):
    """Reproduce the exact error from handle_add_measurement method."""
    print(f"\n🎯 Reproducing handle_add_measurement error for user {user_id}...")

    # This is the EXACT code from the bot's handle_add_measurement method
    try:
        async def _get_user_types(session):
            print("   📋 Calling UserMeasurementTypeRepository.get_user_measurement_types...")
            return await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)

        print("   🔄 Executing with session...")
        user_types = await DatabaseManager.execute_with_session(_get_user_types)
        print(f"   ✅ Success! Found {len(user_types)} user measurement types")

        return user_types

    except Exception as e:
        print(f"   ❌ ERROR REPRODUCED: {e}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error module: {type(e).__module__}")

        # Print the exact error details
        import traceback
        print(f"   Full traceback:")
        traceback.print_exc()

        return None

async def reproduce_add_measurement_type_scenario(user_id, measurement_type_id):
    """Reproduce the scenario where user adds a measurement type."""
    print(f"\n🔧 Testing add_measurement_type_to_user scenario...")

    try:
        async def _add_type(session):
            print(f"   📋 Adding measurement type {measurement_type_id} to user {user_id}...")
            return await UserMeasurementTypeRepository.add_measurement_type_to_user(
                session, user_id, measurement_type_id
            )

        result = await DatabaseManager.execute_with_session(_add_type)
        print(f"   ✅ Successfully added measurement type: {result.id}")
        return result

    except Exception as e:
        print(f"   ❌ ERROR in add_measurement_type: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_raw_sql_equivalent():
    """Test the raw SQL equivalent of the problematic query."""
    print(f"\n🔬 Testing raw SQL equivalent...")

    async def _test_raw(session):
        # Test the exact query that should be generated
        query = """
        SELECT umt.id, umt.user_id, umt.measurement_type_id, umt.is_active,
               umt.created_at, umt.updated_at,
               mt.id as mt_id, mt.name, mt.unit, mt.description,
               mt.is_active as mt_is_active, mt.created_at as mt_created_at
        FROM user_measurement_types umt
        JOIN measurement_types mt ON umt.measurement_type_id = mt.id
        WHERE umt.user_id = :user_id AND umt.is_active = true
        ORDER BY mt.name
        """

        # Test with different user IDs
        for test_user_id in [1, 123456789, 999]:
            try:
                result = await session.execute(text(query), {"user_id": test_user_id})
                rows = result.fetchall()
                print(f"   ✅ Raw SQL for user {test_user_id}: {len(rows)} rows")
            except Exception as e:
                print(f"   ❌ Raw SQL failed for user {test_user_id}: {e}")

    await DatabaseManager.execute_with_session(_test_raw)

async def test_original_sqlalchemy_query(user_id):
    """Test the original SQLAlchemy query that was causing issues."""
    print(f"\n⚠️  Testing ORIGINAL problematic SQLAlchemy query...")

    async def _test_original(session):
        from sqlalchemy import select, and_
        from sqlalchemy.orm import selectinload
        from easy_track.models import UserMeasurementType, MeasurementType

        try:
            # This was the original problematic query
            print("   🧪 Testing original query with and_()...")
            result = await session.execute(
                select(UserMeasurementType)
                .options(selectinload(UserMeasurementType.measurement_type))
                .where(
                    and_(
                        UserMeasurementType.user_id == user_id,
                        UserMeasurementType.is_active == True
                    )
                )
                .join(MeasurementType)
                .order_by(MeasurementType.name)
            )
            user_types = result.scalars().all()
            print(f"   ✅ Original query worked: {len(user_types)} results")

        except Exception as e:
            print(f"   ❌ Original query failed: {e}")
            print("   This confirms the original issue!")

        try:
            # Test the "fixed" version with multiple where clauses
            print("   🧪 Testing 'fixed' query with multiple where()...")
            result = await session.execute(
                select(UserMeasurementType)
                .options(selectinload(UserMeasurementType.measurement_type))
                .where(UserMeasurementType.user_id == user_id)
                .where(UserMeasurementType.is_active == True)
            )
            user_types = result.scalars().all()
            print(f"   ✅ Fixed query worked: {len(user_types)} results")

        except Exception as e:
            print(f"   ❌ Fixed query also failed: {e}")
            print("   The issue persists even with the fix!")

    await DatabaseManager.execute_with_session(_test_original)

async def check_data_types_in_database(user_id):
    """Check actual data types in the database for debugging."""
    print(f"\n🔍 Checking actual data types in database...")

    async def _check_types(session):
        # Check what type the user_id actually is
        result = await session.execute(
            text("SELECT pg_typeof(:user_id) as user_id_type"),
            {"user_id": user_id}
        )
        row = result.fetchone()
        print(f"   user_id parameter type: {row.user_id_type}")

        # Check actual user table
        result = await session.execute(
            text("SELECT id, telegram_id, pg_typeof(id) as id_type FROM users LIMIT 1")
        )
        row = result.fetchone()
        if row:
            print(f"   Actual user.id: {row.id} (type: {row.id_type})")
            print(f"   Actual telegram_id: {row.telegram_id}")

        # Check boolean values
        result = await session.execute(
            text("""
                SELECT is_active, pg_typeof(is_active) as bool_type, COUNT(*)
                FROM user_measurement_types
                GROUP BY is_active, pg_typeof(is_active)
            """)
        )
        rows = result.fetchall()
        for row in rows:
            print(f"   is_active value: {row.is_active} (type: {row.bool_type}) - count: {row.count}")

    await DatabaseManager.execute_with_session(_check_types)

async def main():
    """Main test execution."""
    print("🚀 Bot Error Reproduction Test")
    print("=" * 50)

    try:
        # Initialize database
        await init_db()
        print("✅ Database initialized")

        # Setup test data
        user_id, weight_type_id, waist_type_id = await setup_bot_test_data()

        # Test 1: Reproduce the error with no user measurement types (empty result)
        print("\n" + "="*60)
        print("TEST 1: Empty user_measurement_types (typical first-time user)")
        print("="*60)
        await reproduce_handle_add_measurement_error(user_id)
        await test_raw_sql_equivalent()
        await check_data_types_in_database(user_id)
        await test_original_sqlalchemy_query(user_id)

        # Test 2: Add a measurement type and test again
        print("\n" + "="*60)
        print("TEST 2: After adding measurement type")
        print("="*60)
        await reproduce_add_measurement_type_scenario(user_id, weight_type_id)
        await reproduce_handle_add_measurement_error(user_id)

        # Test 3: Add another and test with multiple records
        print("\n" + "="*60)
        print("TEST 3: Multiple measurement types")
        print("="*60)
        await reproduce_add_measurement_type_scenario(user_id, waist_type_id)
        await reproduce_handle_add_measurement_error(user_id)

        print("\n" + "="*60)
        print("🎯 ANALYSIS COMPLETE")
        print("="*60)
        print("Check the error messages above to identify:")
        print("1. Which specific query is failing")
        print("2. What data types are being compared")
        print("3. Whether it's SQLAlchemy version specific")
        print("4. If raw SQL works but SQLAlchemy doesn't")

    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
