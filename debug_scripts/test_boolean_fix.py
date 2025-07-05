#!/usr/bin/env python3
"""
Simple test to verify the boolean comparison fix for SQLAlchemy asyncpg issues.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

from easy_track.database import DatabaseManager, init_db
from easy_track.repositories import (
    MeasurementTypeRepository,
    UserMeasurementTypeRepository,
    UserRepository,
)

# Load environment variables
load_dotenv()


async def test_boolean_fix():
    """Test the boolean comparison fix."""
    print("🧪 Testing Boolean Comparison Fix")
    print("=" * 40)

    try:
        # Initialize database
        await init_db()
        print("✅ Database initialized")

        # Test scenario
        async def run_test(session):
            # Clean data first
            from sqlalchemy import text

            await session.execute(text("DELETE FROM user_measurement_types"))
            await session.execute(text("DELETE FROM measurements"))
            await session.execute(text("DELETE FROM measurement_types"))
            await session.execute(text("DELETE FROM users"))

            # Create test user
            user = await UserRepository.create_user(
                session,
                telegram_id=555666777,
                username="testfix",
                first_name="Test",
                last_name="Fix",
            )
            print(f"✅ Created user: {user.id}")

            # Create measurement type
            weight_type = await MeasurementTypeRepository.create_measurement_type(
                session, "Weight Test", "kg", "Test weight"
            )
            print(f"✅ Created measurement type: {weight_type.id}")

            # Test 1: Empty query (this was failing before)
            print("\n🧪 Test 1: Query with no results")
            user_types = await UserMeasurementTypeRepository.get_user_measurement_types(
                session, user.id
            )
            print(f"   ✅ Empty query successful: {len(user_types)} results")

            # Test 2: Add measurement type
            print("\n🧪 Test 2: Add measurement type")
            added = await UserMeasurementTypeRepository.add_measurement_type_to_user(
                session, user.id, weight_type.id
            )
            print(f"   ✅ Added measurement type: {added.id}")

            # Test 3: Query with results
            print("\n🧪 Test 3: Query with results")
            user_types = await UserMeasurementTypeRepository.get_user_measurement_types(
                session, user.id
            )
            print(f"   ✅ Query with results: {len(user_types)} results")

            for ut in user_types:
                print(
                    f"      - {ut.measurement_type.name} ({ut.measurement_type.unit})"
                )

            # Test 4: Get all active types
            print("\n🧪 Test 4: Get all active measurement types")
            all_types = await MeasurementTypeRepository.get_all_active_types(session)
            print(f"   ✅ All active types: {len(all_types)} results")

            # Test 5: Remove measurement type
            print("\n🧪 Test 5: Remove measurement type")
            removed = (
                await UserMeasurementTypeRepository.remove_measurement_type_from_user(
                    session, user.id, weight_type.id
                )
            )
            print(f"   ✅ Removed measurement type: {removed}")

            # Test 6: Query after removal
            print("\n🧪 Test 6: Query after removal")
            user_types = await UserMeasurementTypeRepository.get_user_measurement_types(
                session, user.id
            )
            print(f"   ✅ Query after removal: {len(user_types)} results")

            return True

        success = await DatabaseManager.execute_with_session(run_test)

        if success:
            print("\n🎉 ALL TESTS PASSED!")
            print("✅ Boolean comparison fix is working correctly")
            return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback

        traceback.print_exc()
        return False


async def test_bot_scenario():
    """Test the exact bot scenario that was failing."""
    print("\n🤖 Testing Bot Scenario")
    print("=" * 30)

    try:

        async def simulate_bot_flow(session):
            # Get a user (simulate user creation in bot)
            user = await UserRepository.get_user_by_telegram_id(session, 555666777)
            if not user:
                user = await UserRepository.create_user(
                    session,
                    telegram_id=555666777,
                    username="bottest",
                    first_name="Bot",
                    last_name="Test",
                )

            # This is the EXACT line that was failing in handle_add_measurement
            user_types = await UserMeasurementTypeRepository.get_user_measurement_types(
                session, user.id
            )

            print(f"✅ Bot scenario successful: {len(user_types)} measurement types")
            return True

        success = await DatabaseManager.execute_with_session(simulate_bot_flow)
        print("✅ Bot scenario test passed!")
        return success

    except Exception as e:
        print(f"❌ Bot scenario failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test execution."""
    print("🚀 Boolean Fix Verification Test")
    print("=" * 50)

    try:
        test1_result = await test_boolean_fix()
        test2_result = await test_bot_scenario()

        if test1_result and test2_result:
            print("\n🎊 SUCCESS: All tests passed!")
            print("The SQLAlchemy boolean comparison issue has been resolved.")
            return True
        else:
            print("\n💥 FAILURE: Some tests failed!")
            return False

    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
