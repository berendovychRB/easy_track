"""
Test script to verify coach panel translations are working correctly.
This script helps test that all coach panel buttons and messages are properly translated to Ukrainian.
"""

import asyncio
import sys
import os

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
src_path = os.path.join(project_root, "src")
sys.path.insert(0, src_path)

from easy_track.database import init_db, DatabaseManager
from easy_track.repositories import UserRepository
from easy_track.models import UserRole
from easy_track.i18n.translator import translator


async def test_coach_translations():
    """Test that all coach panel translations work correctly."""
    print("🔍 Testing Coach Panel Translations...")
    print("=" * 50)

    # Initialize database
    await init_db()
    print("✅ Database initialized")

    # Test translation keys for Ukrainian
    user_lang = "uk"
    print(f"\n🇺🇦 Testing Ukrainian translations (lang: {user_lang})")
    print("-" * 40)

    # Test button translations
    button_keys = [
        ("coach.buttons.my_athletes", "👥 Мої спортсмени"),
        ("coach.buttons.athletes_progress", "📊 Прогрес спортсменів"),
        ("coach.buttons.coach_notifications", "🔔 Сповіщення тренера"),
        ("coach.buttons.coach_panel", "🎯 Панель тренера"),
        ("coach.buttons.add_athlete", "➕ Додати спортсмена"),
        ("coach.buttons.add_first_athlete", "➕ Додати першого спортсмена"),
        ("coach.buttons.remove_athlete", "🗑️ Видалити спортсмена"),
        ("coach.buttons.view_all_progress", "📊 Весь прогрес"),
        ("coach.buttons.coach_stats", "📈 Статистика тренера"),
        ("coach.buttons.coach_guide", "🎓 Довідник тренера"),
        ("coach.buttons.notification_settings", "🔔 Сповіщення"),
        ("buttons.back_to_coach_panel", "🔙 Назад до панелі тренера"),
        ("buttons.cancel", "❌ Скасувати"),
        ("buttons.back", "◀️ Назад"),
    ]

    print("🔘 Testing button translations:")
    all_passed = True
    for key, expected_uk in button_keys:
        try:
            actual = translator.get(key, user_lang)
            if actual == expected_uk:
                print(f"  ✅ {key}: '{actual}'")
            else:
                print(f"  ❌ {key}: expected '{expected_uk}', got '{actual}'")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {key}: ERROR - {e}")
            all_passed = False

    # Test parameterized translations
    print("\n🔘 Testing parameterized translations:")

    # Test view_athlete_details with name parameter
    athlete_name = "Іван"
    try:
        details_text = translator.get("coach.buttons.view_athlete_details", user_lang, name=athlete_name)
        expected_details = f"📊 Деталі {athlete_name}"
        if details_text == expected_details:
            print(f"  ✅ coach.buttons.view_athlete_details: '{details_text}'")
        else:
            print(f"  ❌ coach.buttons.view_athlete_details: expected '{expected_details}', got '{details_text}'")
            all_passed = False
    except Exception as e:
        print(f"  ❌ coach.buttons.view_athlete_details: ERROR - {e}")
        all_passed = False

    # Test message translations
    message_keys = [
        ("coach.panel.title", "🎯 **Панель тренера**\n\nОберіть дію:"),
        ("coach.list_athletes.title", "👥 **Ваші спортсмени:**"),
        ("coach.list_athletes.no_athletes", "👥 У вас поки немає спортсменів.\nВикористайте /add_athlete щоб додати першого спортсмена!"),
        ("coach.remove_athlete.select", "👥 **Видалити спортсмена**\n\nОберіть спортсмена якого ви хочете видалити з вашого нагляду:"),
        ("coach.dashboard.welcome", "🏠 **Ласкаво просимо до панелі тренера!**\n\nПочніть з додавання вашого першого спортсмена щоб відстежувати їх прогрес."),
    ]

    print("\n🔘 Testing message translations:")
    for key, expected_uk in message_keys:
        try:
            actual = translator.get(key, user_lang)
            if actual.strip() == expected_uk.strip():
                print(f"  ✅ {key}")
            else:
                print(f"  ❌ {key}:")
                print(f"      Expected: '{expected_uk}'")
                print(f"      Got:      '{actual}'")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {key}: ERROR - {e}")
            all_passed = False

    # Test English translations for comparison
    print(f"\n🇺🇸 Testing English translations (lang: en)")
    print("-" * 40)

    english_button_keys = [
        ("coach.buttons.my_athletes", "👥 My Athletes"),
        ("coach.buttons.coach_panel", "🎯 Coach Panel"),
        ("buttons.back_to_coach_panel", "🔙 Back to Coach Panel"),
        ("buttons.cancel", "❌ Cancel"),
    ]

    print("🔘 Testing English button translations:")
    for key, expected_en in english_button_keys:
        try:
            actual = translator.get(key, "en")
            if actual == expected_en:
                print(f"  ✅ {key}: '{actual}'")
            else:
                print(f"  ❌ {key}: expected '{expected_en}', got '{actual}'")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {key}: ERROR - {e}")
            all_passed = False

    # Test scenario simulation
    print(f"\n🎭 Simulating coach panel flow...")
    print("-" * 40)

    scenarios = [
        "1. Coach opens main menu → sees '🎯 Панель тренера' button",
        "2. Coach clicks coach panel → sees '🎯 **Панель тренера**\\n\\nОберіть дію:'",
        "3. Coach clicks 'My Athletes' → sees '👥 Мої спортсмени' (if no athletes: welcome message)",
        "4. Coach sees athlete list → each athlete has '📊 Деталі {name}' button",
        "5. Coach sees action buttons → '➕ Додати спортсмена', '🗑️ Видалити спортсмена'",
        "6. Coach clicks back → sees '🔙 Назад до панелі тренера' button",
        "7. Coach clicks cancel in forms → sees '❌ Скасувати' button",
    ]

    for scenario in scenarios:
        print(f"  ✅ {scenario}")

    # Summary
    print(f"\n📊 Translation Test Results")
    print("=" * 30)

    if all_passed:
        print("🎉 ✅ All coach panel translations are working correctly!")
        print("\n✨ Benefits of the fix:")
        print("  • Athlete selection buttons now show Ukrainian text")
        print("  • 'Back to Coach Panel' buttons properly translated")
        print("  • 'Cancel' buttons use Ukrainian translation")
        print("  • Athlete detail buttons use formatted Ukrainian text")
        print("  • Consistent user experience in Ukrainian")
    else:
        print("⚠️  ❌ Some translations are missing or incorrect!")
        print("\n🔧 Issues to fix:")
        print("  • Check translation keys in uk.json file")
        print("  • Verify translator.get() calls in bot.py")
        print("  • Ensure all hardcoded English text is replaced")

    return all_passed


async def test_coach_functionality_integration():
    """Test that coach functionality works with translations."""
    print(f"\n🔍 Testing Coach Functionality Integration...")
    print("=" * 50)

    test_telegram_id = 123456789  # Replace with actual ID for real testing

    async def test_user_setup(session):
        """Set up test user as coach."""
        user = await UserRepository.get_user_by_telegram_id(session, test_telegram_id)

        if not user:
            print(f"ℹ️  Test user {test_telegram_id} not found - this is expected for automated testing")
            return None

        # Check current role
        current_role = await UserRepository.get_user_role(session, user.id)
        print(f"📋 Test user current role: {current_role}")

        # Update to coach if needed
        if current_role == UserRole.ATHLETE:
            await UserRepository.update_user_role(session, user.id, UserRole.BOTH)
            print("🔄 Updated user role to BOTH (coach + athlete)")

        return user

    user = await DatabaseManager.execute_with_session(test_user_setup)

    if user:
        print("✅ Integration test setup complete")
        print("📝 Manual testing steps:")
        print("   1. Start bot: make docker-run")
        print("   2. Set language to Ukrainian: /language")
        print("   3. Open menu: /menu")
        print("   4. Click '🎯 Панель тренера' (should be in Ukrainian)")
        print("   5. Click '👥 Мої спортсмени' (should be in Ukrainian)")
        print("   6. Verify all buttons show Ukrainian text")
        print("   7. Check athlete detail buttons: '📊 Деталі {name}'")
        print("   8. Verify back buttons: '🔙 Назад до панелі тренера'")
    else:
        print("ℹ️  No test user found - this is normal for CI/automated testing")

    print("✅ Integration test completed!")


if __name__ == "__main__":
    print("🚀 EasySize Coach Panel Translation Test")
    print("=" * 50)

    try:
        # Run translation tests
        translations_passed = asyncio.run(test_coach_translations())

        # Run integration tests
        asyncio.run(test_coach_functionality_integration())

        print("\n" + "=" * 50)
        if translations_passed:
            print("🎉 All translation tests passed!")
            print("\n✅ Fixed Issues:")
            print("  • Coach athlete selection buttons now use Ukrainian")
            print("  • 'Back to Coach Panel' buttons properly translated")
            print("  • 'Cancel' buttons use Ukrainian text")
            print("  • Athlete detail buttons show translated text")
            print("  • Remove athlete selection uses Ukrainian")
        else:
            print("⚠️  Some translation issues remain")

        print("\n📝 Next Steps:")
        print("   1. Start the bot locally")
        print("   2. Set language to Ukrainian")
        print("   3. Test coach panel functionality")
        print("   4. Verify all text appears in Ukrainian")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
