"""
Internationalization and localization for the rating toolbox.

Provides language packs and utilities for supporting multiple languages
(German and English by default, extensible for others).
"""

from typing import Dict, Optional, Literal


class LanguagePack:
    """Container for localized strings.
    
    Manages text in multiple languages for GUI elements, dialogs, and messages.
    Falls back to English if a key is not available in the requested language.
    """
    
    def __init__(self, language: Literal["de", "en"] = "de"):
        """Initialize language pack.
        
        Args:
            language: Language code ('de' for German, 'en' for English)
        """
        self.language = language
        self._strings = _build_language_strings()
    
    def get(self, key: str, **kwargs) -> str:
        """Get localized string by key.
        
        Args:
            key: String key (e.g., "dialog.start.ready")
            **kwargs: String format arguments (if string contains {placeholders})
            
        Returns:
            Localized string, or English fallback if unavailable in current language.
            
        Raises:
            KeyError: If key not found in any language
        """
        # Try current language first
        if self.language in self._strings and key in self._strings[self.language]:
            text = self._strings[self.language][key]
            return text.format(**kwargs) if kwargs else text
        
        # Fall back to English
        if "en" in self._strings and key in self._strings["en"]:
            text = self._strings["en"][key]
            return text.format(**kwargs) if kwargs else text
        
        raise KeyError(f"Translation key '{key}' not found in language '{self.language}' or English fallback")
    
    def set_language(self, language: Literal["de", "en"]):
        """Change active language.
        
        Args:
            language: Language code
        """
        if language not in ("de", "en"):
            raise ValueError(f"Unsupported language: {language}")
        self.language = language


def _build_language_strings() -> Dict[str, Dict[str, str]]:
    """Build the complete language string dictionary.
    
    Returns:
        Dict mapping language code → (key → translated string)
    """
    return {
        "de": {
            # Main heading
            "main.title": "Schieber",
            
            # Settings dialog
            "settings.title": "Einstellungen",
            "settings.participant_id": "Teilnehmer-ID",
            "settings.measurement_list": "Messliste",
            "settings.device": "Audiogerät",
            "settings.blocksize": "Blockgröße",
            "settings.buffersize": "Puffergröße",
            "settings.language": "Sprache",
            "settings.button_start": "Beginnen",
            "settings.button_cancel": "Abbrechen",
            
            # Greetings dialog
            "dialog.greetings.title": "Willkommen",
            "dialog.greetings.message": (
                "Willkommen zu unserer Studie. Wenn Sie den Instruktionsbogen gelesen haben, "
                "drücken Sie bitte auf \"Beginnen\"! Vor jedem Abschnitt öffnet sich ein Fenster, "
                "in dem Sie durch Drücken von \"Start\" das Abspielen des Audios beginnen können."
            ),
            "dialog.greetings.button": "Beginnen",
            
            # Start dialog
            "dialog.start.title": "Bereit?",
            "dialog.start.message": "Drücken Sie \"Start\", wenn Sie die Kopfhörer aufgesetzt haben und bereit sind!",
            "dialog.start.button": "Start",
            
            # End screen
            "dialog.end.title": "Abgeschlossen",
            "dialog.end.message": "Sie haben die Studie abgeschlossen. Vielen Dank für Ihre Teilnahme!",
            "dialog.end.button": "Fertig",
            
            # Post-stimulus dialog
            "dialog.post_stimulus.message": (
                "Bitte beantworten Sie die Fragen auf dem Fragebogen mit Überschrift \"{chapter}\"! "
                "Drücken Sie \"Weiter\", wenn Sie alle Fragen beantwortet haben!"
            ),
            "dialog.post_stimulus.button": "Weiter",
            
            # Logging/status
            "status.loading": "Laden...",
            "status.recording": "Aufnahme läuft",
            "status.paused": "Pausiert",
            "status.error": "Fehler",
        },
        "en": {
            # Main heading
            "main.title": "Rating Slider",
            
            # Settings dialog
            "settings.title": "Settings",
            "settings.participant_id": "Participant ID",
            "settings.measurement_list": "Measurement List",
            "settings.device": "Audio Device",
            "settings.blocksize": "Block Size",
            "settings.buffersize": "Buffer Size",
            "settings.language": "Language",
            "settings.button_start": "Start",
            "settings.button_cancel": "Cancel",
            
            # Greetings dialog
            "dialog.greetings.title": "Welcome",
            "dialog.greetings.message": (
                "Welcome to our study. If you have read the instructions, "
                "please click \"Start\"! Before each section, a dialog will appear "
                "where you can click \"Start\" to begin audio playback."
            ),
            "dialog.greetings.button": "Start",
            
            # Start dialog
            "dialog.start.title": "Ready?",
            "dialog.start.message": "Press \"Start\" when you have put on your headphones and are ready!",
            "dialog.start.button": "Start",
            
            # End screen
            "dialog.end.title": "Completed",
            "dialog.end.message": "You have completed the study. Thank you for your participation!",
            "dialog.end.button": "Done",
            
            # Post-stimulus dialog
            "dialog.post_stimulus.message": (
                "Please answer the questions on the questionnaire with heading \"{chapter}\". "
                "Press \"Continue\" when you have answered all questions!"
            ),
            "dialog.post_stimulus.button": "Continue",
            
            # Logging/status
            "status.loading": "Loading...",
            "status.recording": "Recording",
            "status.paused": "Paused",
            "status.error": "Error",
        },
    }



