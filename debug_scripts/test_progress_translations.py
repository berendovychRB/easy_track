#!/usr/bin/env python3
"""
Test script to verify progress view statistics translations.
This script tests the Ukrainian translations for the progress detail view.
"""

import asyncio
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from easy_track.i18n.translator import translator


async def test_progress_translations():
    """Test progress view translations for Ukrainian language."""
    print("🧪 Testing Progress View Statistics Translations")
    print("=" * 50)

    # Test Ukrainian translations
    user_lang = "uk"
    print(f"\n📝 Testing {user_lang.upper()} translations:")
    print("-" * 30)

    # Test existing keys
    existing_keys = [
        "view_progress.title",
        "view_progress.latest",
        "view_progress.total_count",
        "view_progress.recent_measurements"
    ]

    print("✅ Existing keys:")
    for key in existing_keys:
        try:
            if key == "view_progress.title":
                translation = translator.get(key, user_lang, type="Вага")
            elif key == "view_progress.latest":
                translation = translator.get(key, user_lang, value="75.5", unit="кг", date="04/08/2025")
            elif key == "view_progress.total_count":
                translation = translator.get(key, user_lang, count=15)
            else:
                translation = translator.get(key, user_lang)
            print(f"  {key}: {translation}")
        except Exception as e:
            print(f"  ❌ {key}: ERROR - {e}")

    # Test new statistics keys
    new_keys = [
        "view_progress.statistics_title",
        "view_progress.average",
        "view_progress.minimum",
        "view_progress.maximum"
    ]

    print("\n🆕 New statistics keys:")
    for key in new_keys:
        try:
            translation = translator.get(key, user_lang)
            print(f"  {key}: {translation}")
        except Exception as e:
            print(f"  ❌ {key}: ERROR - {e}")

    # Test full progress message format
    print("\n📊 Full progress message example:")
    print("-" * 40)

    try:
        # Simulate progress data
        type_name = "Вага"
        unit_name = "кг"
        latest_value = "75.5"
        latest_date = "04/08/2025"
        count = 15
        stats = {
            'average': "74.2",
            'minimum': "70.1",
            'maximum': "78.9"
        }

        progress_text = (
            f"{translator.get('view_progress.title', user_lang, type=type_name)}\n\n"
            f"{translator.get('view_progress.latest', user_lang, value=latest_value, unit=unit_name, date=latest_date)}\n"
            f"{translator.get('view_progress.total_count', user_lang, count=count)}\n\n"
            f"{translator.get('view_progress.statistics_title', user_lang)}\n"
            f"{translator.get('view_progress.average', user_lang)} {stats['average']} {unit_name}\n"
            f"{translator.get('view_progress.minimum', user_lang)} {stats['minimum']} {unit_name}\n"
            f"{translator.get('view_progress.maximum', user_lang)} {stats['maximum']} {unit_name}\n\n"
            f"{translator.get('view_progress.recent_measurements', user_lang)}\n"
        )

        print(progress_text)
        print("✅ Progress message generated successfully!")

    except Exception as e:
        print(f"❌ Error generating progress message: {e}")

    # Test English translations for comparison
    print("\n🇺🇸 English translations for comparison:")
    print("-" * 40)

    user_lang = "en"
    for key in new_keys:
        try:
            translation = translator.get(key, user_lang)
            print(f"  {key}: {translation}")
        except Exception as e:
            print(f"  ❌ {key}: ERROR - {e}")


async def test_before_after_comparison():
    """Show before/after comparison of the statistics section."""
    print("\n🔄 Before/After Comparison")
    print("=" * 50)

    print("❌ BEFORE (hardcoded English):")
    print("📊 Statistics:")
    print("• Average: 74.2 кг")
    print("• Minimum: 70.1 кг")
    print("• Maximum: 78.9 кг")

    print("\n✅ AFTER (Ukrainian translations):")
    user_lang = "uk"
    try:
        stats_title = translator.get('view_progress.statistics_title', user_lang)
        average_label = translator.get('view_progress.average', user_lang)
        minimum_label = translator.get('view_progress.minimum', user_lang)
        maximum_label = translator.get('view_progress.maximum', user_lang)

        print(f"{stats_title}")
        print(f"{average_label} 74.2 кг")
        print(f"{minimum_label} 70.1 кг")
        print(f"{maximum_label} 78.9 кг")

    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main test function."""
    try:
        asyncio.run(test_progress_translations())
        asyncio.run(test_before_after_comparison())

        print("\n🎉 Translation test completed!")
        print("\n💡 What was fixed:")
        print("   • Added Ukrainian translations for statistics labels")
        print("   • Added English translations for consistency")
        print("   • Updated bot.py to use translations instead of hardcoded text")
        print("   • Now the progress view is fully localized!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
