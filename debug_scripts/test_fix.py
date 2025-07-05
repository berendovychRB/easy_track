#!/usr/bin/env python3
"""
Simple test script to verify the SQLAlchemy query fix.
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


async def test_fix():
    """Test the fix for the SQLAlchemy boolean error."""
    print("🧪 Testing SQLAlchemy query fix...")

    try:
        # Initialize database
        await init_db()
        print("✅ Database initialized")

        # Create test data
        async def create_test_data(session):
            # Create a test user
            user = await UserRepository.create_user(
                session,
                telegram_id=987654321,
                username="testuser2",
                first_name="Test",
                last_name="User",
            )

            # Create measurement types
            weight_type = await MeasurementTypeRepository.create_measurement_type(
                session, "Weight", "kg", "Body weight"
            )

            # Add measurement type to user
            await UserMeasurementTypeRepository.add_measurement_type_to_user(
                session, user.id, weight_type.id
            )

            return user.id

        user_id = await DatabaseManager.execute_with_session(create_test_data)
        print(f"✅ Test data created for user {user_id}")

        # Test the problematic query
        async def test_query(session):
            user_types = await UserMeasurementTypeRepository.get_user_measurement_types(
                session, user_id
            )
            return user_types

        user_types = await DatabaseManager.execute_with_session(test_query)
        print(f"✅ Query successful! Found {len(user_types)} measurement types")

        for ut in user_types:
            print(f"   - {ut.measurement_type.name} ({ut.measurement_type.unit})")

        print("🎉 Fix verified successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_fix())
    sys.exit(0 if success else 1)
