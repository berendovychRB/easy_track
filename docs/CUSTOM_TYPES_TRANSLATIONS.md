# Custom Measurement Types - Translation Implementation

This document details the translation implementation for the custom measurement types feature in EasyTrack bot.

## 🌐 Supported Languages

- **English (en)** 🇺🇸 - Default language
- **Ukrainian (uk)** 🇺🇦 - Full localization

## 📝 Translation Keys

### Custom Type Creation Flow

| Key | Purpose | Example (EN) | Example (UK) |
|-----|---------|--------------|--------------|
| `custom_types.create_button` | Main creation button | "✨ Create Custom Type" | "✨ Створити індивідуальний тип" |
| `custom_types.title` | Creation flow title | "✨ Create Custom Measurement Type" | "✨ Створити індивідуальний тип вимірювання" |
| `custom_types.name_prompt` | Name input prompt | "Please enter the name for your custom measurement type..." | "Будь ласка, введіть назву для вашого індивідуального типу..." |
| `custom_types.unit_prompt` | Unit input prompt | "Now enter the unit of measurement..." | "Тепер введіть одиницю вимірювання..." |
| `custom_types.description_prompt` | Description input prompt | "Optionally, enter a description..." | "За бажанням введіть опис..." |

### Validation Messages

| Key | Purpose | Parameters |
|-----|---------|------------|
| `custom_types.name_too_short` | Name length validation | None |
| `custom_types.name_too_long` | Name length validation | None |
| `custom_types.name_exists` | Duplicate name error | `{name}` |
| `custom_types.unit_empty` | Empty unit validation | None |
| `custom_types.unit_too_long` | Unit length validation | None |
| `custom_types.description_too_long` | Description length validation | None |

### Success Messages

| Key | Purpose | Parameters |
|-----|---------|------------|
| `custom_types.success` | Creation success | `{name}`, `{unit}` |
| `custom_types.success_with_description` | Creation success with description | `{name}`, `{unit}`, `{description}` |

### Navigation & Actions

| Key | Purpose | Example (EN) | Example (UK) |
|-----|---------|--------------|--------------|
| `custom_types.skip_description` | Skip description button | "⏭️ Skip Description" | "⏭️ Пропустити опис" |
| `custom_types.cancel` | Cancel button | "❌ Cancel" | "❌ Скасувати" |
| `custom_types.error` | General error message | "❌ Error occurred while creating custom type..." | "❌ Помилка при створенні індивідуального типу..." |

### Updated Existing Keys

| Key | Purpose | Change |
|-----|---------|--------|
| `add_types.no_available` | Empty types message | Updated to explain custom types are already active |

## 🔧 Technical Implementation

### Translation Files Location
```
src/easy_track/i18n/translations/
├── en.json  # English translations
└── uk.json  # Ukrainian translations
```

### Usage in Code
```python
# Get user's language
user_lang = await BotHandlers.get_user_language(user_id)

# Simple translation
text = translator.get("custom_types.title", user_lang)

# Parameterized translation
error_msg = translator.get(
    "custom_types.name_exists", 
    user_lang, 
    name="Blood Pressure"
)
```

### Handler Updates
All custom type creation handlers now support translations:
- `handle_create_custom_type()`
- `handle_custom_type_name()`
- `handle_custom_type_unit()`
- `handle_custom_type_description()`
- `handle_skip_description()`
- `create_custom_measurement_type()`

## 🌍 Localization Features

### Automatic Language Detection
- User's language preference is automatically detected from their profile
- All messages in the custom type flow use the user's selected language
- Fallback to English if user's language is not supported

### Dynamic Content
- Success messages dynamically include the created type name and unit
- Error messages include context-specific information (e.g., duplicate name)
- All validation messages are localized

### Consistent UI
- All buttons and navigation elements use translated text
- Icons are preserved across languages for visual consistency
- Message formatting maintained while text is localized

## 📋 Translation Guidelines

### Adding New Languages
1. Create new JSON file in `translations/` directory (e.g., `fr.json`)
2. Add language code to `translator.py` supported languages list
3. Translate all `custom_types.*` keys
4. Test with the translation test script

### Translation Best Practices
1. **Maintain Context**: Keep the meaning and tone consistent
2. **Preserve Formatting**: Maintain emojis, line breaks, and markdown
3. **Parameter Placeholders**: Don't translate `{name}`, `{unit}`, etc.
4. **Cultural Adaptation**: Adapt examples to local context when appropriate

### Required Keys for New Languages
When adding a new language, these keys must be translated:
```
custom_types.create_button
custom_types.title
custom_types.name_prompt
custom_types.unit_prompt
custom_types.description_prompt
custom_types.skip_description
custom_types.name_too_short
custom_types.name_too_long
custom_types.name_exists
custom_types.unit_empty
custom_types.unit_too_long
custom_types.description_too_long
custom_types.success
custom_types.success_with_description
custom_types.error
custom_types.cancel
add_types.no_available
```

## 🧪 Testing Translations

### Automated Testing
A translation test script verifies:
- All required keys exist
- Translations are not empty
- Parameterized translations work correctly
- Language fallback mechanism functions
- Different languages have different translations

### Manual Testing
1. Change bot language to Ukrainian via `/menu` → 🌐 Language
2. Test complete custom type creation flow
3. Verify all messages appear in Ukrainian
4. Test error conditions to verify error messages
5. Switch back to English and repeat

## 🚀 Future Enhancements

### Potential Additions
- **More Languages**: French, Spanish, German, etc.
- **Regional Variants**: US English vs UK English
- **Cultural Adaptations**: Different measurement examples per region
- **RTL Support**: For Arabic, Hebrew, etc.

### Translation Management
- **Translation Keys Validation**: Automated checks for missing keys
- **Translation Quality**: Native speaker review process
- **Version Control**: Track translation changes across updates
- **Crowdsourcing**: Community translation contributions

## 🔗 Related Documentation

- [Custom Measurement Types Overview](CUSTOM_MEASUREMENT_TYPES.md)
- [Custom Types User Guide](CUSTOM_TYPES_USER_GUIDE.md)
- [Translation System Documentation](../src/easy_track/i18n/README.md)

---

*Last Updated: July 1, 2025*
*Translation Coverage: 100% for EN/UK languages*