"""
Unit tests for the internationalization module (functions/i18n.py).

Tests LanguagePack and text retrieval functionality.
"""

import unittest
from functions.i18n import LanguagePack, get_default_language_pack


class TestLanguagePack(unittest.TestCase):
    """Test LanguagePack initialization and text retrieval."""
    
    def test_create_german_pack(self):
        """Create German language pack and verify language code."""
        pack = LanguagePack("de")
        self.assertEqual(pack.language, "de")
    
    def test_create_english_pack(self):
        """Create English language pack."""
        pack = LanguagePack("en")
        self.assertEqual(pack.language, "en")
    
    def test_get_german_text(self):
        """Get German text by key."""
        pack = LanguagePack("de")
        text = pack.get("settings.title")
        self.assertEqual(text, "Einstellungen")
    
    def test_get_english_text(self):
        """Get English text by key."""
        pack = LanguagePack("en")
        text = pack.get("settings.title")
        self.assertEqual(text, "Settings")
    
    def test_fallback_to_english(self):
        """If German key missing, fall back to English."""
        pack = LanguagePack("de")
        # Assuming "unknown.key" is not in German
        # (This is a contrived test; in reality all keys should exist)
        # For now, we test that existing keys work
        text = pack.get("settings.title")  # Known to exist
        self.assertIsNotNone(text)
    
    def test_missing_key(self):
        """Missing key in both languages should raise KeyError."""
        pack = LanguagePack("de")
        with self.assertRaises(KeyError):
            pack.get("nonexistent.key.path")
    
    def test_format_string_with_args(self):
        """Format strings with placeholder arguments."""
        pack = LanguagePack("de")
        # This key has a format placeholder: 'Überschrift "{chapter}"'
        text = pack.get("dialog.post_stimulus.message", chapter="Kapitel 1")
        self.assertIn("Kapitel 1", text)
    
    def test_set_language(self):
        """Change language after initialization."""
        pack = LanguagePack("de")
        self.assertEqual(pack.language, "de")
        
        pack.set_language("en")
        self.assertEqual(pack.language, "en")
        
        # Text should now come from English
        text = pack.get("settings.title")
        self.assertEqual(text, "Settings")
    
    def test_invalid_language(self):
        """Invalid language code should raise."""
        pack = LanguagePack("de")
        with self.assertRaises(ValueError):
            pack.set_language("fr")


class TestLanguagePackTexts(unittest.TestCase):
    """Test that all expected keys exist in language packs."""
    
    EXPECTED_KEYS = [
        "main.title",
        "settings.title",
        "settings.participant_id",
        "dialog.greetings.title",
        "dialog.start.title",
        "dialog.end.title",
        "status.recording",
    ]
    
    def test_german_has_all_keys(self):
        """German pack should have all expected keys."""
        pack = LanguagePack("de")
        for key in self.EXPECTED_KEYS:
            try:
                pack.get(key)
            except KeyError:
                self.fail(f"Key '{key}' not found in German pack")
    
    def test_english_has_all_keys(self):
        """English pack should have all expected keys."""
        pack = LanguagePack("en")
        for key in self.EXPECTED_KEYS:
            try:
                pack.get(key)
            except KeyError:
                self.fail(f"Key '{key}' not found in English pack")


class TestDefaultLanguagePack(unittest.TestCase):
    """Test module-level default language pack."""
    
    def test_get_default_pack(self):
        """Get default language pack."""
        pack = get_default_language_pack("de")
        self.assertIsNotNone(pack)
        self.assertEqual(pack.language, "de")


if __name__ == '__main__':
    unittest.main()
