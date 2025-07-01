#!/usr/bin/env python3
"""
Debug script to investigate custom measurement type tracking list visibility issues.
This script checks if custom types appear in the user's tracking list.
"""
import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from easy_track.database import DatabaseManager, init_db
from easy_track.repositories import (
    UserRepository,
    MeasurementTypeRepository,
    UserMeasurementTypeRepository,
)


async def debug_tracking_list():
    """Debug tracking list visibility for custom measurement types."""
    print("🔍 Debugging Tracking List Visibility...")

    # Initialize database
    await init_db()

    # Use the known large Telegram ID
    telegram_id = 8065740908

    try:
        # Step 1: Get user
        print(f"\n1️⃣ Getting user with Telegram ID: {telegram_id}")

        async def get_user(session):
            return await UserRepository.get_user_by_telegram_id(session, telegram_id)

        user = await DatabaseManager.execute_with_session(get_user)
        if not user:
            print("❌ User not found!")
            return

        print(f"✅ Found user: {user.first_name} {user.last_name} (ID: {user.id})")

        # Step 2: Get ALL user measurement types (including inactive)
        print(f"\n2️⃣ Getting ALL user measurement type records...")

        async def get_all_user_measurement_types(session):
            from sqlalchemy import select
            from easy_track.models import UserMeasurementType
            result = await session.execute(
                select(UserMeasurementType)
                .where(UserMeasurementType.user_id == user.id)
                .options(selectinload(UserMeasurementType.measurement_type))
            )
            return result.scalars().all()

        # Fix import issue
        async def get_all_user_measurement_types_fixed(session):
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from easy_track.models import UserMeasurementType
            result = await session.execute(
                select(UserMeasurementType)
                .where(UserMeasurementType.user_id == user.id)
                .options(selectinload(UserMeasurementType.measurement_type))
            )
            return result.scalars().all()

        all_user_types = await DatabaseManager.execute_with_session(get_all_user_measurement_types_fixed)
        print(f"✅ Found {len(all_user_types)} user measurement type records")

        for ut in all_user_types:
            icon = "🔧" if ut.measurement_type.is_custom else "📏"
            status = "✅ Active" if ut.is_active else "❌ Inactive"
            print(f"   {icon} {ut.measurement_type.name} ({ut.measurement_type.unit}) - {status}")
            print(f"      UserMeasurementType ID: {ut.id}")
            print(f"      MeasurementType ID: {ut.measurement_type_id}")
            print(f"      Created: {ut.created_at}")

        # Step 3: Get active user measurement types (what shows in tracking list)
        print(f"\n3️⃣ Getting ACTIVE user measurement types (tracking list)...")

        async def get_active_tracking_types(session):
            return await UserMeasurementTypeRepository.get_user_measurement_types(session, user.id)

        active_types = await DatabaseManager.execute_with_session(get_active_tracking_types)
        print(f"✅ Active tracking types: {len(active_types)}")

        custom_active = [ut for ut in active_types if ut.measurement_type.is_custom]
        system_active = [ut for ut in active_types if not ut.measurement_type.is_custom]

        print(f"   📏 Active system types: {len(system_active)}")
        print(f"   🔧 Active custom types: {len(custom_active)}")

        for ut in active_types:
            icon = "🔧" if ut.measurement_type.is_custom else "📏"
            print(f"   {icon} {ut.measurement_type.name} ({ut.measurement_type.unit})")

        # Step 4: Check the repository method logic
        print(f"\n4️⃣ Testing repository method directly...")

        async def test_repository_method(session):
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from easy_track.models import UserMeasurementType

            # Test the exact query from the repository
            result = await session.execute(
                select(UserMeasurementType)
                .options(selectinload(UserMeasurementType.measurement_type))
                .where(UserMeasurementType.user_id == user.id)
                .where(UserMeasurementType.is_active.is_(True))
            )
            user_types = result.scalars().all()

            # Filter and sort in Python (as done in repository)
            active_types = [ut for ut in user_types if ut.is_active]
            sorted_types = sorted(
                active_types,
                key=lambda x: x.measurement_type.name if x.measurement_type else "",
            )

            return sorted_types

        repo_result = await DatabaseManager.execute_with_session(test_repository_method)
        print(f"✅ Repository method returns: {len(repo_result)} types")

        for ut in repo_result:
            icon = "🔧" if ut.measurement_type.is_custom else "📏"
            print(f"   {icon} {ut.measurement_type.name} ({ut.measurement_type.unit})")

        # Step 5: Check if there's a difference between all records and active ones
        print(f"\n5️⃣ Analyzing discrepancies...")

        all_ids = {ut.id for ut in all_user_types}
        active_ids = {ut.id for ut in active_types}
        inactive_ids = all_ids - active_ids

        if inactive_ids:
            print(f"⚠️  Found {len(inactive_ids)} inactive user measurement types:")
            for ut in all_user_types:
                if ut.id in inactive_ids:
                    icon = "🔧" if ut.measurement_type.is_custom else "📏"
                    print(f"   {icon} {ut.measurement_type.name} - INACTIVE")
        else:
            print("✅ All user measurement types are active")

        # Step 6: Simulate the "Manage Types" display logic
        print(f"\n6️⃣ Simulating Manage Types display...")

        # This is what would show in the bot's "Manage Types" menu
        tracking_custom = [ut for ut in active_types if ut.measurement_type.is_custom]
        tracking_system = [ut for ut in active_types if not ut.measurement_type.is_custom]

        print(f"   Types that SHOULD appear in tracking list:")
        print(f"   📏 System types: {len(tracking_system)}")
        print(f"   🔧 Custom types: {len(tracking_custom)}")

        if len(tracking_custom) == 0:
            print("   ❌ NO CUSTOM TYPES would appear in tracking list!")
        else:
            print("   ✅ Custom types should appear in tracking list:")
            for ut in tracking_custom:
                print(f"      🔧 {ut.measurement_type.name} ({ut.measurement_type.unit})")

        # Step 7: Check for potential issues
        print(f"\n7️⃣ Checking for potential issues...")

        issues_found = False

        # Check if user has any custom types at all
        user_custom_types = await DatabaseManager.execute_with_session(
            lambda session: MeasurementTypeRepository.get_user_custom_types(session, user.id)
        )

        if len(user_custom_types) == 0:
            print("❌ ISSUE: User has no custom measurement types!")
            issues_found = True
        else:
            print(f"✅ User has {len(user_custom_types)} custom types")

        # Check if custom types are in user_measurement_types table
        custom_in_tracking_table = [ut for ut in all_user_types if ut.measurement_type.is_custom]

        if len(custom_in_tracking_table) == 0:
            print("❌ ISSUE: Custom types not found in user_measurement_types table!")
            issues_found = True
        elif len(custom_in_tracking_table) != len(user_custom_types):
            print(f"⚠️  PARTIAL ISSUE: Only {len(custom_in_tracking_table)} of {len(user_custom_types)} custom types in tracking table")
            issues_found = True
        else:
            print(f"✅ All {len(user_custom_types)} custom types found in tracking table")

        # Check if custom types in tracking table are active
        active_custom_in_tracking = [ut for ut in custom_in_tracking_table if ut.is_active]

        if len(active_custom_in_tracking) != len(custom_in_tracking_table):
            print(f"❌ ISSUE: Only {len(active_custom_in_tracking)} of {len(custom_in_tracking_table)} custom types are active!")
            issues_found = True
        else:
            print(f"✅ All custom types in tracking table are active")

        if not issues_found:
            print("✅ No obvious issues found - custom types should be visible!")

        # Step 8: Final summary
        print(f"\n8️⃣ Final Summary...")
        print(f"   User's custom measurement types: {len(user_custom_types)}")
        print(f"   Custom types in tracking table: {len(custom_in_tracking_table)}")
        print(f"   Active custom types in tracking: {len(active_custom_in_tracking)}")
        print(f"   Custom types visible in UI: {len(tracking_custom)}")

        if len(tracking_custom) > 0:
            print("✅ CONCLUSION: Custom types SHOULD be visible in tracking list")
        else:
            print("❌ CONCLUSION: Custom types will NOT be visible in tracking list")
            print("   This explains why the user can't see them!")

    except Exception as e:
        print(f"\n❌ Debug failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_tracking_list())
