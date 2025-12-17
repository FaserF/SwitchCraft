import locale
import json
import logging
import os

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
        self.translations = {}
        self._load_translations()

    def _load_translations(self):
        """Load translations from JSON files in assets/lang."""
        try:
            # Use pathlib for better cross-platform handling
            from pathlib import Path
            base_path = Path(__file__).parent
            # src/switchcraft/utils/../assets/lang -> src/switchcraft/assets/lang
            lang_dir = base_path.parent / "assets" / "lang"

            logger.debug(f"Loading translations from: {lang_dir.resolve()}")

            if not lang_dir.exists():
                logger.error(f"Language directory not found: {lang_dir.resolve()}")

            for lang_code in ["en", "de"]:
                file_path = lang_dir / f"{lang_code}.json"
                if file_path.exists():
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            self.translations[lang_code] = json.load(f)
                    except Exception as e:
                         logger.error(f"Failed to load {lang_code} translation: {e}")
                else:
                    logger.warning(f"Translation file missing: {file_path}")

            # Ensure English exists as fallback at minimum
            if "en" not in self.translations:
                self.translations["en"] = {} # Will cause issues but prevents crash

        except Exception as e:
            logger.error(f"Critical i18n error: {e}")

    def _detect_language(self):
        try:
            # Fix DeprecationWarning for Python 3.11+
            lang = locale.getlocale()[0]
            if not lang:
                 lang = locale.getdefaultlocale()[0] # Fallback if getlocale returns None (e.g. C locale)

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

    def get(self, key, lang=None, default=None, **kwargs):
        """
        Get translated string.
        Supports explicit language override 'lang'.
        Supports format arguments explicitly passed as kwargs.
        """
        target_lang = lang if lang else self.language

        # Get dictionary for target language, fallback to EN
        lang_dict = self.translations.get(target_lang, self.translations.get("en", {}))

        # Get value, fallback to English value, then to default (if provided), else key
        val = lang_dict.get(key)
        if val is None:
             val = self.translations.get("en", {}).get(key)

        if val is None:
            val = default if default is not None else key

        # Format if kwargs provided
        if kwargs and isinstance(val, str):
            try:
                return val.format(**kwargs)
            except Exception as e:
                logger.warning(f"Failed to format string '{key}': {e}")
                return val

        return val

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
