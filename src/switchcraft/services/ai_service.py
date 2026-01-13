import logging
from switchcraft.services.addon_service import AddonService

logger = logging.getLogger(__name__)

# Try to import the real service from the addon
_real_module = AddonService().import_addon_module("ai", "service")

if _real_module:
    SwitchCraftAI = _real_module.SwitchCraftAI
else:
    class SwitchCraftAI:
        """
        Stub SwitchCraftAI when the Addon is not installed.
        """
        def __init__(self):
            logger.warning("SwitchCraftAI running in Stub mode (Addon missing).")
            self.context = {}

        def update_context(self, data: dict):
            self.context = data

        def ask(self, query: str) -> str:
            return "Advanced Feature: AI Assistant requires the AI Addon."
