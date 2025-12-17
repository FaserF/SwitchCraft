import re

class SwitchCraftAI:
    """
    A rule-based 'Mini KI' expert system for packaging advice.
    Does not use external LLMs, runs locally.
    """

    def __init__(self):
        self.context = {} # Stores current analysis data

    def update_context(self, data: dict):
        """Updates the context with the latest analysis results."""
        self.context = data

    def ask(self, query: str) -> str:
        """
        Determines the answer based on query patterns and current context.
        """
        q = query.lower()

        # 0. Language Guard & Detection
        # Simple heuristic: detections of common words in supported languages
        is_de = any(w in q for w in ["hallo", "wer", "was", "wie", "ist", "kannst", "machen", "unterstützt", "du", "neueste", "version", "welche", "für"])
        is_en = any(w in q for w in ["hello", "hi", "who", "what", "how", "is", "can", "do", "support", "latest", "version"])

        # If input seems to be another language (not perfect, but covers basic "non-match" if distinct chars used)
        # Actually, user requirement is: IF not supported question AND language is not DE/EN -> Fallback
        # But we don't have a reliable language detector for short strings without libs.
        # Strategy: If it matches NO rules and NO DE/EN keywords, assume unsupported/unknown.

        from switchcraft.utils.i18n import i18n

        # 1. Dynamic Smalltalk (DE + EN)
        # Prioritize specific questions over generic greetings
        if re.search(r"(wer bist du|who are you)", q):
             return i18n.get("ai_smalltalk_who", lang="de" if is_de else "en")

        if re.search(r"(was kannst du|what can you do)", q):
             return i18n.get("ai_smalltalk_what", lang="de" if is_de else "en")

        if re.search(r"(neueste version|latest version)", q):
            from switchcraft import __version__
            return i18n.get("ai_smalltalk_version", lang="de" if is_de else "en", version=__version__)

        if re.search(r"\b(hi|hallo|hello|greetings|moin|servus)\b", q):
            return i18n.get("ai_smalltalk_hello", lang="de" if is_de else "en")

        # 2. Context-Aware Questions
        if "switch" in q or "silent" in q or "install" in q or "parameter" in q or "argument" in q:
            if "how" in q or "what" in q or "wie" in q or "was" in q or "welche" in q:
                if self.context:
                    install_type = self.context.get("type", "Unknown")
                    switches = self.context.get("install_silent", "Unknown")
                    filename = self.context.get("filename", "")

                    target_lang = "de" if is_de else "en"

                    if "msi" in install_type.lower():
                        return i18n.get("ai_context_msi", lang=target_lang, filename=filename)

                    elif switches and switches != "Unknown":
                        return i18n.get("ai_context_switches", lang=target_lang, install_type=install_type, switches=switches, filename=filename)
                    else:
                        return i18n.get("ai_context_no_switches", lang=target_lang)
                else:
                    return i18n.get("ai_context_none", lang="de" if is_de else "en")

        # 3. General Knowledge Base
        rules = {
            r"msi": "ai_rules_msi",
            r"inno": "ai_rules_inno",
            r"nsis": "ai_rules_nsis",
            r"installshield": "ai_rules_installshield",
            r"intune": "ai_rules_intune",
            r"error 1603": "ai_rules_error1603",
            r"error 1618": "ai_rules_error1618",
            r"powershell": "ai_rules_powershell",
            r"(mac|macos|dmg|pkg)": "ai_rules_macos",
        }

        for pattern, key in rules.items():
            if re.search(pattern, q):
                return i18n.get(key, lang="de" if is_de else "en")

        # 4. Fallback / Language Guard

        if is_de:
            return i18n.get("ai_fallback", lang="de")
        elif is_en:
             return i18n.get("ai_fallback", lang="en")
        else:
            # Language Guard for unsupported inputs
            return i18n.get("ai_unsupported_lang", lang="en")
