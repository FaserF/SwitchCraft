import logging
import re
from switchcraft.services.addon_service import AddonService
from switchcraft.utils.i18n import i18n

logger = logging.getLogger(__name__)

# Try to import the real service from the addon
_real_module = AddonService().import_addon_module("ai", "service")

if _real_module:
    SwitchCraftAI = _real_module.SwitchCraftAI
else:
    class SwitchCraftAI:
        """
        Stub SwitchCraftAI when the Addon is not installed.
        Provides helpful guidance instead of just echoing input.
        """
        def __init__(self):
            logger.warning("SwitchCraftAI running in Stub mode (Addon missing).")
            self.context = {}

        @staticmethod
        def _is_greeting(query: str) -> bool:
            """Check if the query is a greeting using regex word boundaries."""
            q = query.lower()
            return bool(re.search(r'\b(hi|hello|hallo|hey|moin|servus)\b', q))

        def update_context(self, data: dict):
            self.context = data
            query = self.context.get('query', '')

            if self._is_greeting(query):
                return i18n.get("ai_stub_greeting") or "Hello! I am your local AI assistant. I can help you with packaging questions."

            title = i18n.get("ai_addon_required_title") or "🤖 **AI Addon Required**"
            msg = i18n.get("ai_addon_required_msg") or (
                "The AI Assistant addon is not installed. This feature requires the AI Addon "
                "to be installed via the Addon Manager to get intelligent responses."
            )
            tips_header = i18n.get("ai_tips_header") or "**In the meantime, here are some tips:**"

            return (
                f"{title}\n\n"
                f"{msg}\n\n"
                f"{tips_header}\n"
                "• For MSI files: Use `/qn /norestart` for silent install\n"
                "• For NSIS: Use `/S` (case sensitive)\n"
                "• For Inno Setup: Use `/VERYSILENT /SUPPRESSMSGBOXES`\n"
                "• For InstallShield: Use `/s /v\"/qn\"`\n\n"
                f"Your question: *{self.context.get('query', 'Unknown')}*"
            )

        def ask(self, query):
            """Stub ask method - returns a helpful message when AI addon is missing."""
            if self._is_greeting(query):
                return i18n.get("ai_stub_welcome") or "Hello! I am the local SwitchCraft AI helper. Install the AI Addon for full functionality."

            # Provide helpful response even without addon
            title = i18n.get("ai_addon_required_title") or "🤖 **AI Addon Required**"
            msg = i18n.get("ai_addon_required_msg") or (
                "The AI Assistant addon is not installed. This feature requires the AI Addon "
                "to be installed via the Addon Manager to get intelligent responses."
            )
            tips_header = i18n.get("ai_tips_header") or "**In the meantime, here are some tips:**"

            # Use the same helpful format as update_context
            return (
                f"{title}\n\n"
                f"{msg}\n\n"
                f"{tips_header}\n"
                "• For MSI files: Use `/qn /norestart` for silent install\n"
                "• For NSIS: Use `/S` (case sensitive)\n"
                "• For Inno Setup: Use `/VERYSILENT /SUPPRESSMSGBOXES`\n"
                "• For InstallShield: Use `/s /v\"/qn\"`\n\n"
                f"Your question: *{query}*"
            )
