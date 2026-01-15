import logging
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

        def update_context(self, data: dict):
            self.context = data

            title = i18n.get("ai_addon_required_title") or "🤖 **AI Addon Required**"
            msg = i18n.get("ai_addon_required_msg") or (
                "The AI Assistant addon is not installed. To get intelligent responses, "
                "please install the AI addon via the Addon Manager."
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
                f"Your question: *{query}*"
            )
