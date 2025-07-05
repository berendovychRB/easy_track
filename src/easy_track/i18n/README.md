# Internationalization (i18n) System

This directory contains the internationalization system for the EasyTrack bot, supporting multiple languages for all user-facing text.

## Supported Languages

- **English (en)** - Default language
- **Ukrainian (uk)** - Українська

## Directory Structure

```
i18n/
├── __init__.py          # Package initialization
├── translator.py        # Translation service
├── translations/        # Translation files
│   ├── en.json         # English translations
│   └── uk.json         # Ukrainian translations
└── README.md           # This file
```

## How It Works

### Translation Files

Translation files are JSON files organized in a hierarchical structure using dot notation keys:

```json
{
  "commands": {
    "start": {
      "welcome": "👋 Welcome to EasyTrack, {name}!"
    }
  },
  "buttons": {
    "add_measurement": "📝 Add Measurement"
  }
}
```

### Using Translations

The translator service provides several methods:

```python
from easy_track.i18n import translator

# Basic translation
text = translator.get("commands.start.welcome", "en", name="John")

# Measurement type translation
type_name = translator.get_measurement_type_name("weight", "uk")  # Returns "Вага"

# Unit translation
unit_name = translator.get_unit_name("kg", "uk")  # Returns "кг"

# Language validation
is_supported = translator.is_supported_language("uk")  # Returns True
```

## Translation Categories

### 1. Commands
- `/start` command messages
- `/menu` command messages
- Error messages

### 2. Buttons
- All inline keyboard buttons
- Navigation buttons
- Action buttons

### 3. Bot Features
- Add measurement flow
- Manage measurement types
- View progress and statistics
- Date-based viewing
- Language selection

### 4. Measurement Types
Localized names for body measurements:
- Weight/Вага
- Height/Зріст
- Waist/Талія
- Chest/Груди
- etc.

### 5. Units
Localized unit names:
- kg/кг
- cm/см
- inches/дюймів
- etc.

### 6. Common Messages
- Success/error messages
- Loading states
- No data messages

## Adding New Languages

1. Create a new JSON file in `translations/` directory (e.g., `de.json`)
2. Copy the structure from `en.json`
3. Translate all text values
4. Add the language code to `supported_languages` in `translator.py`
5. Add language name to `get_language_name()` method
6. Update bot handlers to include the new language option

## Adding New Translation Keys

1. Add the key-value pair to all translation files
2. Use the translator service in bot handlers:
   ```python
   text = translator.get("your.new.key", user_lang, param="value")
   ```

## Database Integration

User language preferences are stored in the `users` table:
- `language` column stores the language code
- Default language is 'en'
- Updated via language selection in bot

## Features

### Automatic Fallback
- If a translation is missing in the requested language, falls back to English
- If English translation is also missing, returns the key itself

### Parameter Substitution
- Support for dynamic content using `{parameter}` syntax
- Example: `"Welcome, {name}!"` with `name="John"` becomes `"Welcome, John!"`

### Language Detection
- Users can change language via bot interface
- Language preference is persisted in database
- All subsequent messages use selected language

## Bot Integration

The translation system is integrated throughout the bot:

1. **User Registration**: Language preference stored on user creation
2. **Message Handlers**: All text uses translator service
3. **Callback Handlers**: Dynamic button text based on user language
4. **State Management**: FSM states work with any language
5. **Error Handling**: Localized error messages

## Best Practices

1. **Consistent Keys**: Use descriptive, hierarchical keys
2. **Parameter Names**: Use clear parameter names in translations
3. **Context**: Group related translations together
4. **Fallbacks**: Always provide English translations as fallback
5. **Testing**: Test all languages thoroughly
6. **Updates**: Keep all language files synchronized when adding new features

## Language Selection Flow

1. User clicks "🌐 Language" button
2. Bot shows available languages with flags
3. User selects preferred language
4. Database is updated with new preference
5. Bot confirms change in new language
6. All subsequent interactions use selected language

## Technical Notes

- Translation files are loaded once at startup
- Translations are cached in memory for performance
- File encoding is UTF-8 to support all characters
- JSON structure allows for easy maintenance and updates
