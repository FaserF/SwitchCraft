import locale
import json
import logging

logger = logging.getLogger(__name__)

class I18n:
    def __init__(self):
        self.language = self._detect_language()
        self.translations = {
            "en": {
                "app_title": "SwitchCraft 🧙‍♂️",
                "tab_analyzer": "Analyzer",
                "tab_helper": "AI Helper",
                "tab_settings": "Settings",
                "drag_drop": "Drag & Drop Installer Here\n(EXE / MSI)",
                "analyzing": "Analyzing",
                "analysis_complete": "Analysis Complete",
                "error": "Error",
                "file_not_found": "File not found.",
                "unknown_installer": "Could not identify installer type.",
                "silent_install": "Silent Install",
                "silent_uninstall": "Silent Uninstall",
                "no_switches": "No automatic switches found.",
                "brute_force_help": "Brute Force Help",
                "search_online": "Search Online for Switches",
                "view_winget": "View on Winget GitHub",
                "settings_theme": "Theme",
                "settings_lang": "Language",
                "settings_dark": "Dark",
                "settings_light": "Light",
                "about_dev": "Developer",
                "about_version": "Version",
                "winget_found": "Winget Match Found!",
                "manual_select": "Select File"
            },
            "de": {
                "app_title": "SwitchCraft 🧙‍♂️",
                "tab_analyzer": "Analyse",
                "tab_helper": "KI Helfer",
                "tab_settings": "Einstellungen",
                "drag_drop": "Installer hier ablegen\n(EXE / MSI)",
                "analyzing": "Analysiere",
                "analysis_complete": "Analyse abgeschlossen",
                "error": "Fehler",
                "file_not_found": "Datei nicht gefunden.",
                "unknown_installer": "Installer-Typ konnte nicht erkannt werden.",
                "silent_install": "Silent Installation",
                "silent_uninstall": "Silent Deinstallation",
                "no_switches": "Keine automatischen Switches gefunden.",
                "brute_force_help": "Brute Force Hilfe",
                "search_online": "Online nach Switches suchen",
                "view_winget": "Auf Winget GitHub ansehen",
                "settings_theme": "Design",
                "settings_lang": "Sprache",
                "settings_dark": "Dunkel",
                "settings_light": "Hell",
                "about_dev": "Entwickler",
                "about_version": "Version",
                "winget_found": "Winget Treffer gefunden!",
                "manual_select": "Datei auswählen"
            }
        }

    def _detect_language(self):
        try:
            lang, _ = locale.getdefaultlocale()
            if lang and lang.startswith("de"):
                return "de"
        except Exception as e:
            logger.warning(f"Could not detect language: {e}")
        return "en"

    def set_language(self, lang_code):
        if lang_code in self.translations:
            self.language = lang_code
        else:
            logger.warning(f"Language {lang_code} not supported, falling back to English.")
            self.language = "en"

    def get(self, key):
        return self.translations.get(self.language, self.translations["en"]).get(key, key)

i18n = I18n()
