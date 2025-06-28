#!/usr/bin/env python3
"""
Test Query Fix - Verify Repository Method

This script tests the current repository method to ensure it works correctly
and doesn't produce the SQLAlchemy boolean error.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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

async def setup_test_data():
    """Set up test data for the query fix test."""
    print("📝 Setting up test data...")

    async def create_test_scenario(session):
        # Clean existing data
        await session.execute(text("DELETE FROM user_measurement_types"))
        await session.execute(text("DELETE FROM measurements"))
        await session.execute(text("DELETE FROM measurement_types"))
        await session.execute(text("DELETE FROM users"))

        # Reset sequences
        await session.execute(text("ALTER SEQUENCE users_id_seq RESTART WITH 1"))
        await session.execute(text("ALTER SEQUENCE measurement_types_id_seq RESTART WITH 1"))
        await session.execute(text("ALTER SEQUENCE user_measurement_types_id_seq RESTART WITH 1"))

        # Create test user
        user = await UserRepository.create_user(
            session,
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        print(f"✅ Created user: {user.id}")

        # Create measurement types
        weight_type = await MeasurementTypeRepository.create_measurement_type(
            session, "Weight", "kg", "Body weight"
        )
        waist_type = await MeasurementTypeRepository.create_measurement_type(
            session, "Waist", "cm", "Waist circumference"
        )
        height_type = await MeasurementTypeRepository.create_measurement_type(
            session, "Height", "cm", "Body height"
        )
        print(f"✅ Created measurement types: {weight_type.id}, {waist_type.id}, {height_type.id}")

        return user.id, [weight_type.id, waist_type.id, height_type.id]

    return await DatabaseManager.execute_with_session(create_test_scenario)

async def test_repository_method(user_id, measurement_type_ids):
    """Test the repository method that was causing errors."""
    print(f"\n🧪 Testing UserMeasurementTypeRepository.get_user_measurement_types...")

    # Test 1: Empty result (no user measurement types)
    print("\n📋 Test 1: Empty result")
    try:
        async def _get_empty(session):
            return await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)

        user_types = await DatabaseManager.execute_with_session(_get_empty)
        print(f"   ✅ Empty query successful: {len(user_types)} results")
    except Exception as e:
        print(f"   ❌ Empty query failed: {e}")
        return False

    # Test 2: Add one measurement type and test
    print("\n📋 Test 2: Single measurement type")
    try:
        async def _add_one_type(session):
            await UserMeasurementTypeRepository.add_measurement_type_to_user(
                session, user_id, measurement_type_ids[0]
            )
            return await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)

        user_types = await DatabaseManager.execute_with_session(_add_one_type)
        print(f"   ✅ Single type query successful: {len(user_types)} results")
        if user_types:
            print(f"   📊 Type: {user_types[0].measurement_type.name} ({user_types[0].measurement_type.unit})")
    except Exception as e:
        print(f"   ❌ Single type query failed: {e}")
        return False

    # Test 3: Add multiple measurement types and test
    print("\n📋 Test 3: Multiple measurement types")
    try:
        async def _add_multiple_types(session):
            # Add remaining types
            for type_id in measurement_type_ids[1:]:
                await UserMeasurementTypeRepository.add_measurement_type_to_user(
                    session, user_id, type_id
                )
            return await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)

        user_types = await DatabaseManager.execute_with_session(_add_multiple_types)
        print(f"   ✅ Multiple types query successful: {len(user_types)} results")
        for user_type in user_types:
            print(f"   📊 Type: {user_type.measurement_type.name} ({user_type.measurement_type.unit})")
    except Exception as e:
        print(f"   ❌ Multiple types query failed: {e}")
        return False

    # Test 4: Test with inactive types
    print("\n📋 Test 4: With inactive types")
    try:
        async def _test_with_inactive(session):
            # Deactivate one type
            await UserMeasurementTypeRepository.remove_measurement_type_from_user(
                session, user_id, measurement_type_ids[1]
            )
            return await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)

        user_types = await DatabaseManager.execute_with_session(_test_with_inactive)
        print(f"   ✅ Inactive types query successful: {len(user_types)} results")
        for user_type in user_types:
            print(f"   📊 Active type: {user_type.measurement_type.name} ({user_type.measurement_type.unit})")
    except Exception as e:
        print(f"   ❌ Inactive types query failed: {e}")
        return False

    return True

async def test_direct_sql_comparison():
    """Test the SQL that should be generated vs the problematic SQL."""
    print(f"\n🔬 Testing SQL generation comparison...")

    async def _test_sql(session):
        # Test the correct SQL pattern
        correct_query = """
        SELECT umt.id, umt.user_id, umt.measurement_type_id, umt.is_active,
               umt.created_at, umt.updated_at
        FROM user_measurement_types umt
        WHERE umt.user_id = :user_id AND umt.is_active = true
        """

        try:
            result = await session.execute(text(correct_query), {"user_id": 1})
            rows = result.fetchall()
            print(f"   ✅ Correct SQL pattern works: {len(rows)} rows")
        except Exception as e:
            print(f"   ❌ Correct SQL pattern failed: {e}")

        # Show what the problematic SQL would look like (but don't execute it)
        problematic_sql = """
        -- This is the PROBLEMATIC SQL that was being generated:
        -- SELECT ... FROM user_measurement_types
        -- WHERE user_id = 1 AND is_active = true
        -- ORDER BY EXISTS (SELECT 1 FROM measurement_types
        --                  WHERE measurement_types.id = user_measurement_types.measurement_type_id
        --                  AND measurement_types.name)
        --                       ^^^^ This is wrong! measurement_types.name is not boolean
        """
        print(f"   📝 The problematic SQL pattern was:")
        print(f"   {problematic_sql}")

    await DatabaseManager.execute_with_session(_test_sql)

async def simulate_bot_scenario(user_id):
    """Simulate the exact bot scenario that was failing."""
    print(f"\n🤖 Simulating bot handle_add_measurement scenario...")

    try:
        # This is the EXACT code from bot.py handle_add_measurement
        async def _get_user_types(session):
            return await UserMeasurementTypeRepository.get_user_measurement_types(session, user_id)

        user_types = await DatabaseManager.execute_with_session(_get_user_types)

        if not user_types:
            print("   ⚠️  No measurement types found (would show 'configure types first' message)")
        else:
            print(f"   ✅ Found {len(user_types)} measurement types")
            print("   🎹 Would create keyboard with options:")
            for user_type in user_types:
                print(f"     - {user_type.measurement_type.name} ({user_type.measurement_type.unit})")

        return True

    except Exception as e:
        print(f"   ❌ Bot scenario failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test execution."""
    print("🧪 Query Fix Verification Test")
    print("=" * 50)

    try:
        # Initialize database
        await init_db()
        print("✅ Database initialized")

        # Setup test data
        user_id, measurement_type_ids = await setup_test_data()

        # Test the repository method
        success = await test_repository_method(user_id, measurement_type_ids)

        if not success:
            print("\n❌ Repository tests failed!")
            return

        # Test SQL comparison
        await test_direct_sql_comparison()

        # Simulate bot scenario
        bot_success = await simulate_bot_scenario(user_id)

        if bot_success:
            print("\n" + "="*60)
            print("🎉 ALL TESTS PASSED!")
            print("="*60)
            print("✅ The repository method works correctly")
            print("✅ No boolean type errors")
            print("✅ Bot scenario works as expected")
            print("✅ The fix is successful")
        else:
            print("\n❌ Bot simulation failed!")

    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
