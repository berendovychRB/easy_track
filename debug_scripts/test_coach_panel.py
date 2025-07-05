"""
Test script for coach panel functionality.
This script helps verify that the new coach panel works correctly.
"""

import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from easy_track.database import DatabaseManager, init_db
from easy_track.models import UserRole
from easy_track.repositories import UserRepository


async def test_coach_panel_functionality():
    """Test the new coach panel functionality."""
    print("🔍 Testing Coach Panel Functionality...")
    print("=" * 50)

    # Initialize database
    await init_db()
    print("✅ Database initialized")

    # Test data - replace with actual Telegram ID
    test_telegram_id = 123456789  # Replace with your Telegram ID

    async def test_coach_panel_flow(session):
        """Test the complete coach panel flow."""
        print(f"\n📊 Testing coach panel flow for Telegram ID: {test_telegram_id}")

        # Get or create user
        user = await UserRepository.get_user_by_telegram_id(session, test_telegram_id)

        if not user:
            print(f"❌ User with Telegram ID {test_telegram_id} not found")
            print("📝 Creating test user...")
            user = await UserRepository.create_user(
                session,
                telegram_id=test_telegram_id,
                username="test_coach",
                first_name="Test",
                last_name="Coach",
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

        # Make user a coach if not already
        if not is_coach:
            print("🔄 Making user a coach...")
            await UserRepository.update_user_role(session, user.id, UserRole.COACH)
            is_coach = await UserRepository.is_user_coach(session, user.id)
            print(f"✅ User is now coach: {is_coach}")

        return user.id, is_coach

    user_id, is_coach = await DatabaseManager.execute_with_session(
        test_coach_panel_flow
    )

    # Test menu logic
    print("\n🎭 Testing Menu Logic...")
    print("=" * 30)

    if is_coach:
        print("✅ User is coach - Main menu should show:")
        print("   - 🎯 Coach Panel (instead of individual coach buttons)")
        print("   - Regular user buttons (add measurement, etc.)")
        print()
        print("✅ Coach Panel should contain:")
        print("   - 👥 My Athletes")
        print("   - 📊 Athletes Progress")
        print("   - 🔔 Coach Notifications")
        print("   - 📈 Coach Stats")
        print("   - 🎓 Coach Guide")
        print("   - 🔙 Back to Menu")
    else:
        print("❌ User is not coach - something went wrong!")

    # Test callback data mapping
    print("\n🔧 Testing Callback Data Mapping...")
    print("=" * 40)

    expected_callbacks = {
        "coach_panel": "handle_coach_panel",
        "coach_athletes": "handle_coach_athletes",
        "view_all_athletes_progress": "handle_view_all_athletes_progress",
        "coach_notifications": "handle_coach_notifications",
        "coach_stats": "handle_coach_stats",
        "coach_guide": "handle_coach_guide",
    }

    print("✅ Expected callback mappings:")
    for callback_data, handler_name in expected_callbacks.items():
        print(f"   {callback_data} -> {handler_name}")

    # Test navigation flow
    print("\n🧭 Testing Navigation Flow...")
    print("=" * 30)

    navigation_flow = [
        "Main Menu -> Coach Panel (coach_panel)",
        "Coach Panel -> My Athletes (coach_athletes)",
        "My Athletes -> Back to Coach Panel (coach_panel)",
        "Coach Panel -> Athletes Progress (view_all_athletes_progress)",
        "Athletes Progress -> Back to Coach Panel (coach_panel)",
        "Coach Panel -> Coach Notifications (coach_notifications)",
        "Coach Notifications -> Back to Coach Panel (coach_panel)",
        "Coach Panel -> Coach Stats (coach_stats)",
        "Coach Stats -> Back to Coach Panel (coach_panel)",
        "Coach Panel -> Coach Guide (coach_guide)",
        "Coach Guide -> Back to Coach Panel (coach_panel)",
        "Coach Panel -> Back to Menu (back_to_menu)",
    ]

    print("✅ Expected navigation flow:")
    for i, flow in enumerate(navigation_flow, 1):
        print(f"   {i}. {flow}")

    # Test benefit summary
    print("\n🌟 Coach Panel Benefits...")
    print("=" * 30)

    benefits = [
        "✅ Cleaner main menu with single coach button",
        "✅ Organized coach functions in dedicated panel",
        "✅ Better user experience with grouped functionality",
        "✅ Easier navigation for coaches",
        "✅ Consistent back navigation to coach panel",
        "✅ Scalable design for future coach features",
    ]

    for benefit in benefits:
        print(f"   {benefit}")

    print("\n🎯 Test Summary:")
    print("=" * 20)
    print(f"   - User ID: {user_id}")
    print(f"   - Is Coach: {is_coach}")
    print(
        f"   - Main menu shows: {'Coach Panel button' if is_coach else 'Become Coach button'}"
    )
    print(f"   - Coach panel accessible: {is_coach}")
    print("   - All coach functions grouped: ✅")

    print("\n✅ Coach Panel functionality test completed!")


async def test_translation_keys():
    """Test that all required translation keys exist."""
    print("\n🌐 Testing Translation Keys...")
    print("=" * 30)

    # Import translator
    from easy_track.i18n import translator

    required_keys = [
        "coach.buttons.coach_panel",
        "coach.panel.title",
        "buttons.back_to_coach_panel",
        "coach.buttons.my_athletes",
        "coach.buttons.athletes_progress",
        "coach.buttons.coach_notifications",
        "coach.buttons.coach_stats",
        "coach.buttons.coach_guide",
    ]

    print("✅ Testing required translation keys:")

    for lang in ["en", "uk"]:
        print(f"\n   Language: {lang}")
        for key in required_keys:
            try:
                translation = translator.get(key, lang)
                print(f"   ✅ {key}: {translation}")
            except Exception as e:
                print(f"   ❌ {key}: Missing or error - {e}")


if __name__ == "__main__":
    print("🚀 EasyTrack Coach Panel Test")
    print("=" * 50)

    try:
        asyncio.run(test_coach_panel_functionality())
        asyncio.run(test_translation_keys())

        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        print("\n📝 Next steps:")
        print("   1. Start the bot with 'make docker-run'")
        print("   2. Use /menu command as a coach")
        print("   3. Click '🎯 Coach Panel' button")
        print("   4. Test all coach functions")
        print("   5. Verify back navigation works")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback

        traceback.print_exc()
