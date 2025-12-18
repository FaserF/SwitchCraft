import logging
from switchcraft.services.addon_service import AddonService

logger = logging.getLogger(__name__)

# Try to import the real service from the addon
_real_module = AddonService.import_addon_module("advanced", "services.intune_service")

if _real_module:
    IntuneService = _real_module.IntuneService
else:
    class IntuneService:
        """
        Stub IntuneService when the Addon is not installed.
        """
        def __init__(self, tools_dir=None):
            logger.warning("IntuneService running in Stub mode (Addon missing).")

        def is_tool_available(self):
            return False

        def download_tool(self):
            return False

        def authenticate(self, *args, **kwargs):
            raise NotImplementedError("Advanced Feature: Intune integration requires the Addon.")

        def upload_win32_app(self, *args, **kwargs):
            raise NotImplementedError("Advanced Feature: Intune integration requires the Addon.")

        def create_intunewin(self, *args, **kwargs):
            raise NotImplementedError("Advanced Feature: Intune integration requires the Addon.")

        def assign_to_group(self, *args, **kwargs):
            raise NotImplementedError("Advanced Feature: Intune integration requires the Addon.")

        def get_device_groups(self, *args, **kwargs):
            return []
