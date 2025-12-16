import locale
import json
import logging

logger = logging.getLogger(__name__)

# Known parameter explanations (used in GUI for parameter list)
KNOWN_PARAMS = {
    "/S": ("Silent mode", "Stiller Modus - Keine Benutzerinteraktion"),
    "/s": ("Silent mode", "Stiller Modus - Keine Benutzerinteraktion"),
    "/SILENT": ("Silent install", "Stille Installation ohne Dialoge"),
    "/VERYSILENT": ("Very silent install (no progress)", "Komplett stille Installation ohne Fortschrittsanzeige"),
    "/NORESTART": ("Prevent automatic restart", "Automatischen Neustart verhindern"),
    "/SUPPRESSMSGBOXES": ("Suppress message boxes", "Meldungsfenster unterdrücken"),
    "/SP-": ("Disable 'This will install...' prompt", "'Dies wird installieren...' Dialog deaktivieren"),
    "/CLOSEAPPLICATIONS": ("Close running applications", "Laufende Anwendungen schließen"),
    "/RESTARTAPPLICATIONS": ("Restart closed applications", "Geschlossene Anwendungen neu starten"),
    "/NOCANCEL": ("Disable cancel button", "Abbrechen-Button deaktivieren"),
    "/NOICONS": ("Don't create Start Menu icons", "Keine Startmenü-Icons erstellen"),
    "/DIR=": ("Installation directory", "Installationsverzeichnis"),
    "/LOG=": ("Log file path", "Protokolldatei-Pfad"),
    "/LOG": ("Enable logging", "Protokollierung aktivieren"),
    "/FORCECLOSEAPPLICATIONS": ("Force close applications", "Anwendungen erzwingen schließen"),
    "/q": ("Quiet mode (MSI)", "Stiller Modus (MSI)"),
    "/qn": ("Quiet, no UI (MSI)", "Komplett still, keine UI (MSI)"),
    "/qb": ("Basic UI (MSI)", "Basis-UI (MSI)"),
    "/qr": ("Reduced UI (MSI)", "Reduzierte UI (MSI)"),
    "/passive": ("Passive mode, progress only (MSI)", "Passiver Modus, nur Fortschritt (MSI)"),
    "/norestart": ("No restart (MSI)", "Kein Neustart (MSI)"),
    "/l*v": ("Verbose logging (MSI)", "Ausführliche Protokollierung (MSI)"),
    "/i": ("Install (MSI)", "Installieren (MSI)"),
    "/x": ("Uninstall (MSI)", "Deinstallieren (MSI)"),
    "-silent": ("Silent mode (alternative)", "Stiller Modus (alternativ)"),
    "-q": ("Quiet mode", "Stiller Modus"),
    "-s": ("Silent mode", "Stiller Modus"),
    "--silent": ("Silent mode (GNU style)", "Stiller Modus (GNU-Stil)"),
    "--quiet": ("Quiet mode (GNU style)", "Stiller Modus (GNU-Stil)"),
    "-y": ("Auto-confirm (yes to all)", "Automatische Bestätigung (Ja zu allem)"),
    "/extract": ("Extract only, no install", "Nur extrahieren, nicht installieren"),
    "/D=": ("Destination directory (NSIS)", "Zielverzeichnis (NSIS)"),
    "/COMPONENTS=": ("Select components", "Komponenten auswählen"),
    "/TASKS=": ("Select tasks", "Aufgaben auswählen"),
    "/MERGETASKS=": ("Merge tasks", "Aufgaben zusammenführen"),
    "REBOOT=ReallySuppress": ("Suppress reboot (MSI)", "Neustart unterdrücken (MSI)"),
    "ALLUSERS=1": ("Install for all users (MSI)", "Für alle Benutzer installieren (MSI)"),
    "INSTALLLEVEL=": ("Installation level (MSI)", "Installationsstufe (MSI)"),
    "ADDLOCAL=ALL": ("Install all features (MSI)", "Alle Funktionen installieren (MSI)"),
}

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
                "settings_debug": "Debug Logging",
                "settings_channel": "Update Channel",
                "settings_dark": "Dark",
                "settings_light": "Light",
                "about_dev": "Developer",
                "about_version": "Version",
                "winget_found": "Winget Match Found!",
                "winget_no_match": "Winget: No match found",
                "manual_select": "Select File",
                # New translations
                "ready": "Ready",
                "copy": "Copy",
                "send": "Send",
                "skip": "Skip",
                "clean_up": "Clean Up",
                "check_updates": "Check for Updates",
                "update_available": "A new version of SwitchCraft is available!",
                "update_available_title": "Update Available 🚀",
                "update_now": "Update Now",
                "update_later": "Update Later",
                "skip_version": "Skip Version",
                "changelog": "Changelog",
                "download_update": "Download Update",
                "current_version": "Current Version",
                "new_version": "New Version",
                "released": "Released",
                "unknown": "Unknown",
                "no_changelog": "No changelog provided.",
                "up_to_date": "You are up to date!",
                "update_check_failed": "Update Check Failed",
                "could_not_check": "Could not check for updates:",
                "extracting_archive": "Extracting archive for nested analysis...",
                "temp_cleaned": "Temporary files cleaned up",
                "automated_output": "Automated Analysis Output",
                "silent_switches": "Silent Switches",
                "ask_something": "Ask something...",
                "ai_helper_welcome": "Welcome to the AI Helper!\nAsk me about silent switches or command line arguments.",
                "brought_by": "Brought to you by FaserF",
                "msi_wrapper_tip": "💡 Detected MSI Wrapper! Standard MSI switches may work.",
                # Parameter list
                "found_params": "Found Parameters",
                "known_params": "Known Parameters",
                "unknown_params": "Unknown Parameters",
                "param_explanation": "Explanation",
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
                "settings_debug": "Debug-Protokollierung",
                "settings_channel": "Update-Kanal",
                "settings_dark": "Dunkel",
                "settings_light": "Hell",
                "about_dev": "Entwickler",
                "about_version": "Version",
                "winget_found": "Winget Treffer gefunden!",
                "winget_no_match": "Winget: Kein Treffer gefunden",
                "manual_select": "Datei auswählen",
                # New translations
                "ready": "Bereit",
                "copy": "Kopieren",
                "send": "Senden",
                "skip": "Überspringen",
                "clean_up": "Aufräumen",
                "check_updates": "Nach Updates suchen",
                "update_available": "Eine neue Version von SwitchCraft ist verfügbar!",
                "update_available_title": "Update verfügbar 🚀",
                "update_now": "Jetzt aktualisieren",
                "update_later": "Später aktualisieren",
                "skip_version": "Version überspringen",
                "changelog": "Änderungsprotokoll",
                "download_update": "Update herunterladen",
                "current_version": "Aktuelle Version",
                "new_version": "Neue Version",
                "released": "Veröffentlicht",
                "unknown": "Unbekannt",
                "no_changelog": "Kein Änderungsprotokoll vorhanden.",
                "up_to_date": "Du bist auf dem neuesten Stand!",
                "update_check_failed": "Update-Prüfung fehlgeschlagen",
                "could_not_check": "Update-Prüfung fehlgeschlagen:",
                "extracting_archive": "Entpacke Archiv für verschachtelte Analyse...",
                "temp_cleaned": "Temporäre Dateien aufgeräumt",
                "automated_output": "Automatisierte Analyse-Ausgabe",
                "silent_switches": "Silent Switches",
                "ask_something": "Frage etwas...",
                "ai_helper_welcome": "Willkommen beim KI Helfer!\nFrage mich nach Silent Switches oder Kommandozeilen-Argumenten.",
                "brought_by": "Ein Projekt von FaserF",
                "msi_wrapper_tip": "💡 MSI Wrapper erkannt! Standard MSI-Switches funktionieren möglicherweise.",
                # Parameter list
                "found_params": "Gefundene Parameter",
                "known_params": "Bekannte Parameter",
                "unknown_params": "Unbekannte Parameter",
                "param_explanation": "Erklärung",
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

    def get_param_explanation(self, param):
        """Get explanation for a known parameter in current language."""
        if param in KNOWN_PARAMS:
            en, de = KNOWN_PARAMS[param]
            return de if self.language == "de" else en
        # Try partial match (for params like /DIR=path)
        base_param = param.split("=")[0] + "=" if "=" in param else None
        if base_param and base_param in KNOWN_PARAMS:
            en, de = KNOWN_PARAMS[base_param]
            return de if self.language == "de" else en
        return None

i18n = I18n()
