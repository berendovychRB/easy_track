#!/usr/bin/env python3
"""
Debug script to test the problematic SQLAlchemy query that's causing the boolean error.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from easy_track.models import User, MeasurementType, UserMeasurementType, Measurement
from easy_track.database import DatabaseManager, init_db
from easy_track.repositories import UserMeasurementTypeRepository

# Load environment variables
load_dotenv()

async def debug_queries():
    """Debug the problematic queries step by step."""
    print("🔍 Starting query debugging...")

    try:
        # Initialize database
        await init_db()
        print("✅ Database initialized")

        # Test basic queries first
        async def test_basic_queries(session):
            print("\n🧪 Testing basic queries...")

            # Test 1: Simple MeasurementType query
            print("1. Testing MeasurementType query...")
            result = await session.execute(select(MeasurementType))
            types = result.scalars().all()
            print(f"   Found {len(types)} measurement types")

            # Test 2: Simple User query
            print("2. Testing User query...")
            result = await session.execute(select(User))
            users = result.scalars().all()
            print(f"   Found {len(users)} users")

            # Test 3: Simple UserMeasurementType query
            print("3. Testing UserMeasurementType query...")
            result = await session.execute(select(UserMeasurementType))
            user_types = result.scalars().all()
            print(f"   Found {len(user_types)} user measurement types")

            return len(users) > 0

        has_users = await DatabaseManager.execute_with_session(test_basic_queries)

        if not has_users:
            print("⚠️  No users found. Creating test data...")
            await create_test_data()

        # Test the problematic query step by step
        async def test_problematic_query(session):
            print("\n🎯 Testing the problematic query...")

            # Get a test user
            result = await session.execute(select(User).limit(1))
            user = result.scalar_one_or_none()

            if not user:
                print("❌ No user found for testing")
                return

            print(f"   Using user: {user.telegram_id}")

            # Test the original problematic query components
            print("4. Testing UserMeasurementType with boolean filter...")
            try:
                # Original problematic query
                query = (
                    select(UserMeasurementType)
                    .options(selectinload(UserMeasurementType.measurement_type))
                    .where(
                        and_(
                            UserMeasurementType.user_id == user.id,
                            UserMeasurementType.is_active == True
                        )
                    )
                )
                result = await session.execute(query)
                user_types = result.scalars().all()
                print(f"   ✅ Query successful: {len(user_types)} results")

            except Exception as e:
                print(f"   ❌ Query failed: {e}")

                # Try alternative boolean comparison
                print("5. Testing with .is_(True) instead...")
                try:
                    query = (
                        select(UserMeasurementType)
                        .options(selectinload(UserMeasurementType.measurement_type))
                        .where(
                            and_(
                                UserMeasurementType.user_id == user.id,
                                UserMeasurementType.is_active.is_(True)
                            )
                        )
                    )
                    result = await session.execute(query)
                    user_types = result.scalars().all()
                    print(f"   ✅ Alternative query successful: {len(user_types)} results")

                except Exception as e2:
                    print(f"   ❌ Alternative query also failed: {e2}")

            # Test with JOIN
            print("6. Testing with explicit JOIN...")
            try:
                query = (
                    select(UserMeasurementType)
                    .options(selectinload(UserMeasurementType.measurement_type))
                    .join(MeasurementType)
                    .where(
                        and_(
                            UserMeasurementType.user_id == user.id,
                            UserMeasurementType.is_active.is_(True)
                        )
                    )
                    .order_by(MeasurementType.name)
                )
                result = await session.execute(query)
                user_types = result.scalars().all()
                print(f"   ✅ JOIN query successful: {len(user_types)} results")

                for ut in user_types:
                    print(f"      - {ut.measurement_type.name} ({ut.measurement_type.unit})")

            except Exception as e:
                print(f"   ❌ JOIN query failed: {e}")

            # Test repository method
            print("7. Testing repository method...")
            try:
                user_types = await UserMeasurementTypeRepository.get_user_measurement_types(
                    session, user.id
                )
                print(f"   ✅ Repository method successful: {len(user_types)} results")

            except Exception as e:
                print(f"   ❌ Repository method failed: {e}")

        await DatabaseManager.execute_with_session(test_problematic_query)

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

async def create_test_data():
    """Create test data for debugging."""
    print("📝 Creating test data...")

    async def _create_data(session):
        # Create a test user
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        session.add(user)
        await session.flush()

        # Create measurement types
        weight_type = MeasurementType(
            name="Weight",
            unit="kg",
            description="Body weight"
        )
        waist_type = MeasurementType(
            name="Waist",
            unit="cm",
            description="Waist circumference"
        )

        session.add(weight_type)
        session.add(waist_type)
        await session.flush()

        # Create user measurement types
        user_weight = UserMeasurementType(
            user_id=user.id,
            measurement_type_id=weight_type.id,
            is_active=True
        )
        user_waist = UserMeasurementType(
            user_id=user.id,
            measurement_type_id=waist_type.id,
            is_active=True
        )

        session.add(user_weight)
        session.add(user_waist)
        await session.flush()

        print(f"   Created user {user.telegram_id} with 2 measurement types")

    await DatabaseManager.execute_with_session(_create_data)

async def test_raw_sql():
    """Test with raw SQL to isolate the issue."""
    print("\n🔬 Testing with raw SQL...")

    async def _test_raw(session):
        # Test raw SQL equivalent
        raw_query = """
        SELECT umt.id, umt.user_id, umt.measurement_type_id, umt.is_active,
               mt.name, mt.unit
        FROM user_measurement_types umt
        JOIN measurement_types mt ON umt.measurement_type_id = mt.id
        WHERE umt.user_id = :user_id AND umt.is_active = true
        ORDER BY mt.name
        """

        # Get a user ID
        result = await session.execute(select(User.id).limit(1))
        user_id = result.scalar_one_or_none()

        if not user_id:
            print("   No user found for raw SQL test")
            return

        try:
            result = await session.execute(raw_query, {"user_id": user_id})
            rows = result.fetchall()
            print(f"   ✅ Raw SQL successful: {len(rows)} results")

            for row in rows:
                print(f"      - {row.name} ({row.unit})")

        except Exception as e:
            print(f"   ❌ Raw SQL failed: {e}")

    await DatabaseManager.execute_with_session(_test_raw)

if __name__ == "__main__":
    print("🚀 SQLAlchemy Query Debugging Tool")
    print("=" * 40)

    try:
        asyncio.run(debug_queries())
        asyncio.run(test_raw_sql())
        print("\n✅ Debugging completed!")

    except KeyboardInterrupt:
        print("\n🛑 Debugging interrupted")
    except Exception as e:
        print(f"\n❌ Debugging failed: {e}")
        import traceback
        traceback.print_exc()
