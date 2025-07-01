import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class Translator:
    """Translation service for handling internationalization."""

    def __init__(self):
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.default_language = "en"
        self.supported_languages = ["en", "uk"]
        self._load_translations()

    def _load_translations(self):
        """Load all translation files."""
        translations_dir = Path(__file__).parent / "translations"

        for lang in self.supported_languages:
            translation_file = translations_dir / f"{lang}.json"
            if translation_file.exists():
                try:
                    with open(translation_file, "r", encoding="utf-8") as f:
                        self.translations[lang] = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    # Fallback to empty dict if translation file is corrupted
                    self.translations[lang] = {}
                    print(f"Error loading translation file {lang}.json: {e}")
            else:
                self.translations[lang] = {}

    def get(self, key: str, language: str = None, **kwargs) -> str:
        """
        Get translated text by key.

        Args:
            key: Translation key in dot notation (e.g., 'commands.start.welcome')
            language: Language code ('en', 'uk'). Uses default if None.
            **kwargs: Format parameters for the translation string

        Returns:
            Translated and formatted string
        """
        if language is None:
            language = self.default_language

        if language not in self.supported_languages:
            language = self.default_language

        # Get translation from the language dict
        translation = self._get_nested_value(self.translations.get(language, {}), key)

        # Fallback to default language if translation not found
        if translation is None and language != self.default_language:
            translation = self._get_nested_value(
                self.translations.get(self.default_language, {}), key
            )

        # Fallback to key if no translation found
        if translation is None:
            translation = key

        # Format the translation with provided parameters
        try:
            return translation.format(**kwargs)
        except (KeyError, ValueError):
            # Return unformatted string if formatting fails
            return translation

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Optional[str]:
        """
        Get value from nested dictionary using dot notation.

        Args:
            data: Dictionary to search in
            key: Key in dot notation (e.g., 'commands.start.welcome')

        Returns:
            Value if found, None otherwise
        """
        keys = key.split(".")
        current = data

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        return current if isinstance(current, str) else None

    def get_language_name(self, language_code: str) -> str:
        """Get display name for language code."""
        language_names = {"en": "English", "uk": "Українська"}
        return language_names.get(language_code, language_code)

    def is_supported_language(self, language_code: str) -> bool:
        """Check if language code is supported."""
        return language_code in self.supported_languages

    def get_supported_languages(self) -> list:
        """Get list of supported language codes."""
        return self.supported_languages.copy()

    def get_measurement_type_name(self, type_name: str, language: str = None) -> str:
        """Get localized measurement type name."""
        key = f"measurement_types.{type_name.lower()}"
        return self.get(key, language) if self.get(key, language) != key else type_name

    def get_unit_name(self, unit: str, language: str = None) -> str:
        """Get localized unit name."""
        key = f"units.{unit.lower()}"
        return self.get(key, language) if self.get(key, language) != key else unit


# Global translator instance
translator = Translator()
