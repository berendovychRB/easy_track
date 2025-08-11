"""
Test script to verify coach functionality.
This script helps debug issues with coach role detection and menu display.
"""

import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from easy_track.database import DatabaseManager, init_db
from easy_track.models import UserRole
from easy_track.repositories import UserRepository


async def test_coach_functionality():
    """Test coach functionality and role detection."""
    print("🔍 Starting coach functionality test...")

    # Initialize database
    await init_db()
    print("✅ Database initialized")

    # Test data - replace with actual Telegram ID
    test_telegram_id = 123456789  # Replace with your Telegram ID

    async def test_user_role_operations(session):
        """Test user role operations."""
        print(f"\n📊 Testing user role operations for Telegram ID: {test_telegram_id}")

        # Get or create user
        user = await UserRepository.get_user_by_telegram_id(session, test_telegram_id)

        if not user:
            print(f"❌ User with Telegram ID {test_telegram_id} not found")
            print("📝 Creating test user...")
            user = await UserRepository.create_user(
                session,
                telegram_id=test_telegram_id,
                username="test_user",
                first_name="Test",
                last_name="User",
            )
            print(f"✅ Created user with ID: {user.id}")
        else:
            print(f"✅ Found user with ID: {user.id}")

        # Check current role
        current_role = await UserRepository.get_user_role(session, user.id)
        print(f"📋 Current role: {current_role}")

        # Test is_user_coach function
        is_coach = await UserRepository.is_user_coach(session, user.id)
        print(f"🎯 Is coach: {is_coach}")

        # Test updating role to coach
        if current_role == UserRole.ATHLETE:
            print("🔄 Updating role to BOTH (coach + athlete)...")
            await UserRepository.update_user_role(session, user.id, UserRole.BOTH)

            # Check again
            new_role = await UserRepository.get_user_role(session, user.id)
            print(f"📋 New role: {new_role}")

            is_coach_after = await UserRepository.is_user_coach(session, user.id)
            print(f"🎯 Is coach after update: {is_coach_after}")

        elif current_role == UserRole.COACH:
            print("ℹ️  User is already a coach")

        elif current_role == UserRole.BOTH:
            print("ℹ️  User already has both roles")

        return user.id

    user_id = await DatabaseManager.execute_with_session(test_user_role_operations)

    # Test role detection consistency
    print("\n🔍 Testing role detection consistency...")

    async def test_role_consistency(session):
        """Test that role detection is consistent."""
        role1 = await UserRepository.get_user_role(session, user_id)
        is_coach1 = await UserRepository.is_user_coach(session, user_id)

        role2 = await UserRepository.get_user_role(session, user_id)
        is_coach2 = await UserRepository.is_user_coach(session, user_id)

        print(f"📋 Role check 1: {role1} (is_coach: {is_coach1})")
        print(f"📋 Role check 2: {role2} (is_coach: {is_coach2})")

        if role1 == role2 and is_coach1 == is_coach2:
            print("✅ Role detection is consistent")
        else:
            print("❌ Role detection is inconsistent!")

        return role1, is_coach1

    role, is_coach = await DatabaseManager.execute_with_session(test_role_consistency)

    # Test menu logic simulation
    print("\n🎭 Simulating menu logic...")

    if is_coach:
        print("✅ User is coach - should show coach buttons:")
        print("   - My Athletes")
        print("   - Athletes Progress")
        print("   - Coach Notifications")
    else:
        print("✅ User is not coach - should show:")
        print("   - Become Coach button")

    # Test multiple sessions
    print("\n🔄 Testing multiple database sessions...")

    async def test_session_1(session):
        return await UserRepository.is_user_coach(session, user_id)

    async def test_session_2(session):
        return await UserRepository.is_user_coach(session, user_id)

    async def test_session_3(session):
        return await UserRepository.is_user_coach(session, user_id)

    result1 = await DatabaseManager.execute_with_session(test_session_1)
    result2 = await DatabaseManager.execute_with_session(test_session_2)
    result3 = await DatabaseManager.execute_with_session(test_session_3)

    print(f"📊 Session 1 result: {result1}")
    print(f"📊 Session 2 result: {result2}")
    print(f"📊 Session 3 result: {result3}")

    if result1 == result2 == result3:
        print("✅ All sessions return consistent results")
    else:
        print("❌ Sessions return inconsistent results!")

    print("\n🎯 Test Summary:")
    print(f"   - User ID: {user_id}")
    print(f"   - Current Role: {role}")
    print(f"   - Is Coach: {is_coach}")
    print(
        f"   - Menu should show: {'Coach buttons' if is_coach else 'Become Coach button'}"
    )

    print("\n✅ Coach functionality test completed!")


async def test_callback_handlers():
    """Test that callback handlers are properly registered."""
    print("\n🔧 Testing callback handler registration...")

    # Import bot handlers
    from easy_track.bot import dp

    # Check if handlers are registered
    callback_handlers = []
    for handler in dp.callback_query.handlers:
        if hasattr(handler, "callback") and hasattr(handler.callback, "filters"):
            for filter_obj in handler.callback.filters:
                if hasattr(filter_obj, "callback_data"):
                    callback_handlers.append(filter_obj.callback_data)

    print(f"📋 Registered callback handlers: {len(callback_handlers)}")

    # Check specific coach handlers
    coach_handlers = [
        "coach_athletes",
        "view_all_athletes_progress",
        "coach_notifications",
        "become_coach_callback",
    ]

    for handler in coach_handlers:
        if any(handler in str(cb) for cb in callback_handlers):
            print(f"✅ Handler '{handler}' is registered")
        else:
            print(f"❌ Handler '{handler}' is NOT registered")


if __name__ == "__main__":
    print("🚀 EasySize Coach Functionality Test")
    print("=" * 50)

    try:
        asyncio.run(test_coach_functionality())
        asyncio.run(test_callback_handlers())
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback

        traceback.print_exc()
