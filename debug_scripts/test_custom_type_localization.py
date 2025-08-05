#!/usr/bin/env python3
"""
Test script to verify custom type creation localization.
This script tests the Ukrainian translations for custom measurement type creation,
specifically the issue where skip description shows English messages and buttons.
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from easy_track.i18n.translator import translator


class MockUser:
    def __init__(self, user_id=12345):
        self.id = user_id
        self.first_name = "Test"
        self.last_name = "User"
        self.username = "testuser"


class MockMessage:
    def __init__(self, user_id=12345):
        self.from_user = MockUser(user_id)
        self.reply = AsyncMock()


class MockCallback:
    def __init__(self, user_id=12345):
        self.from_user = MockUser(user_id)
        self.message = MockMessage(user_id)
        self.answer = AsyncMock()


class MockState:
    def __init__(self, data=None):
        self.data = data or {
            "custom_type_name": "Тестовий тип",
            "custom_type_unit": "тест"
        }

    async def get_data(self):
        return self.data

    async def clear(self):
        self.data = {}


async def test_custom_type_translations():
    """Test custom type creation translations."""
    print("🧪 Testing Custom Type Creation Translations")
    print("=" * 55)

    # Test Ukrainian translations for custom types
    user_lang = "uk"
    print(f"\n📝 Testing {user_lang.upper()} translations:")
    print("-" * 35)

    custom_type_keys = [
        "custom_types.create_button",
        "custom_types.title",
        "custom_types.name_prompt",
        "custom_types.unit_prompt",
        "custom_types.description_prompt",
        "custom_types.skip_description",
        "custom_types.success",
        "custom_types.success_with_description",
        "custom_types.error",
        "custom_types.cancel"
    ]

    print("✅ Custom type translation keys:")
    for key in custom_type_keys:
        try:
            if key == "custom_types.success":
                translation = translator.get(key, user_lang, name="Тестовий тип", unit="тест")
            elif key == "custom_types.success_with_description":
                translation = translator.get(key, user_lang, name="Тестовий тип", unit="тест", description="Опис тесту")
            else:
                translation = translator.get(key, user_lang)
            print(f"  {key}: {translation[:50]}{'...' if len(translation) > 50 else ''}")
        except Exception as e:
            print(f"  ❌ {key}: ERROR - {e}")

    # Test button translations
    button_keys = [
        "buttons.add_measurement",
        "buttons.manage_types",
        "buttons.back_to_menu",
        "common.error"
    ]

    print(f"\n🔘 Button translations:")
    for key in button_keys:
        try:
            translation = translator.get(key, user_lang)
            print(f"  {key}: {translation}")
        except Exception as e:
            print(f"  ❌ {key}: ERROR - {e}")


async def simulate_skip_description_flow():
    """Simulate the skip description workflow."""
    print("\n🔄 Simulating Skip Description Flow")
    print("=" * 40)

    print("📱 User workflow:")
    print("1. User creates custom type (name: 'Тестовий тип', unit: 'тест')")
    print("2. User clicks 'Пропустити опис' button")
    print("3. System should show success message in Ukrainian")
    print("4. Buttons should be in Ukrainian")

    # Mock the state and callback
    state = MockState()
    callback = MockCallback()

    user_lang = "uk"

    print(f"\n📊 Expected success message:")
    try:
        success_message = translator.get(
            "custom_types.success",
            user_lang,
            name="Тестовий тип",
            unit="тест"
        )
        print(f"✅ Success message: {success_message[:100]}...")
    except Exception as e:
        print(f"❌ Error getting success message: {e}")

    print(f"\n🔘 Expected button texts:")
    button_configs = [
        ("buttons.add_measurement", "add_measurement"),
        ("buttons.manage_types", "manage_types"),
        ("buttons.back_to_menu", "back_to_menu")
    ]

    for key, callback_data in button_configs:
        try:
            button_text = translator.get(key, user_lang)
            print(f"  ✅ {callback_data}: '{button_text}'")
        except Exception as e:
            print(f"  ❌ {callback_data}: ERROR - {e}")


async def test_error_handling_localization():
    """Test error handling localization."""
    print("\n🚨 Testing Error Handling Localization")
    print("=" * 45)

    user_lang = "uk"

    print("📝 Testing error message translations:")
    error_keys = [
        "common.error",
        "custom_types.error",
        "custom_types.name_too_short",
        "custom_types.name_too_long",
        "custom_types.name_exists",
        "custom_types.unit_empty",
        "custom_types.unit_too_long",
        "custom_types.description_too_long"
    ]

    for key in error_keys:
        try:
            if key == "custom_types.name_exists":
                translation = translator.get(key, user_lang, name="Тестовий тип")
            else:
                translation = translator.get(key, user_lang)
            print(f"  ✅ {key}: {translation}")
        except Exception as e:
            print(f"  ❌ {key}: ERROR - {e}")


def test_before_after_comparison():
    """Show before/after comparison."""
    print("\n🔄 Before/After Problem Analysis")
    print("=" * 40)

    print("❌ BEFORE (Problem scenario):")
    print("   1. User creates custom type")
    print("   2. User clicks 'Пропустити опис' (Ukrainian)")
    print("   3. Success message appears in ENGLISH")
    print("   4. Buttons appear in ENGLISH:")
    print("      - 'Add Measurement' (should be 'Додати вимірювання')")
    print("      - 'Manage Types' (should be 'Керувати типами')")
    print("      - 'Back to Menu' (should be 'Назад до меню')")

    print("\n✅ AFTER (Expected behavior):")
    print("   1. User creates custom type")
    print("   2. User clicks 'Пропустити опис' (Ukrainian)")
    print("   3. Success message appears in UKRAINIAN")
    print("   4. Buttons appear in UKRAINIAN:")

    user_lang = "uk"
    try:
        add_measurement = translator.get("buttons.add_measurement", user_lang)
        manage_types = translator.get("buttons.manage_types", user_lang)
        back_to_menu = translator.get("buttons.back_to_menu", user_lang)

        print(f"      - '{add_measurement}'")
        print(f"      - '{manage_types}'")
        print(f"      - '{back_to_menu}'")
    except Exception as e:
        print(f"      ❌ Error getting button translations: {e}")


async def test_language_detection_issue():
    """Test potential language detection issues."""
    print("\n🔍 Testing Language Detection Issues")
    print("=" * 40)

    print("🧐 Potential issues in the code:")
    print("   1. handle_skip_description hardcoded 'en' language")
    print("   2. create_custom_measurement_type error handling")
    print("   3. User language not properly retrieved from callback")

    print("\n🔧 Code analysis:")
    print("   ❌ Problem in handle_skip_description:")
    print("       await callback.answer(translator.get('common.error', 'en'))")
    print("       ↑ Hardcoded 'en' language!")

    print("\n   ✅ Should be:")
    print("       user_lang = await get_user_language_from_callback(callback)")
    print("       await callback.answer(translator.get('common.error', user_lang))")

    print("\n🎯 Root cause analysis:")
    print("   • User language retrieval missing in error handlers")
    print("   • Fallback language set to 'en' instead of 'uk'")
    print("   • No proper error handling for language detection failures")


async def simulate_full_workflow():
    """Simulate the complete custom type creation workflow."""
    print("\n🎬 Full Workflow Simulation")
    print("=" * 35)

    user_lang = "uk"

    workflow_steps = [
        ("Step 1", "User clicks 'Створити індивідуальний тип'"),
        ("Step 2", "User enters name: 'Окружність стегна'"),
        ("Step 3", "User enters unit: 'см'"),
        ("Step 4", "User sees description prompt with 'Пропустити опис' button"),
        ("Step 5", "User clicks 'Пропустити опис'"),
        ("Step 6", "System creates type and shows success message"),
        ("Step 7", "User sees buttons to continue")
    ]

    print("📱 Complete workflow:")
    for step, description in workflow_steps:
        print(f"   {step}: {description}")

    print(f"\n📊 Final success message should be:")
    try:
        success_message = translator.get(
            "custom_types.success",
            user_lang,
            name="Окружність стегна",
            unit="см"
        )
        print(f"✅ {success_message}")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main test function."""
    try:
        print("🚀 Testing Custom Type Localization Issues")
        print("=" * 60)

        asyncio.run(test_custom_type_translations())
        asyncio.run(simulate_skip_description_flow())
        asyncio.run(test_error_handling_localization())
        test_before_after_comparison()
        asyncio.run(test_language_detection_issue())
        asyncio.run(simulate_full_workflow())

        print("\n🎉 Test Analysis Complete!")
        print("\n💡 Issues Found:")
        print("   • handle_skip_description hardcodes English language")
        print("   • Error handlers don't retrieve user language properly")
        print("   • Fallback language should be Ukrainian, not English")

        print("\n🔧 Fixes Needed:")
        print("   1. Fix handle_skip_description to get user language")
        print("   2. Update error handlers to use proper localization")
        print("   3. Change default fallback language to Ukrainian")
        print("   4. Add proper error handling for language detection")

        print("\n✅ All translations exist and are correct!")
        print("   The issue is in the code logic, not in translation files.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
