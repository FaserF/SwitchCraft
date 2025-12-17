import logging
from switchcraft.services.addon_service import AddonService

logger = logging.getLogger(__name__)

# Try to import the real service from the addon
_real_module = AddonService.import_advanced_module("switchcraft_advanced.services.intune_service")

if _real_module:
    IntuneService = _real_module.IntuneService
else:
    class IntuneService:
        """
        Stub IntuneService when the Addon is not installed.
        """
        def __init__(self):
            logger.warning("IntuneService running in Stub mode (Addon missing).")

        def is_available(self):
            return False

        def authenticate(self, *args, **kwargs):
            raise NotImplementedError("Advanced Feature: Intune integration requires the Addon.")

        def upload_win32_app(self, *args, **kwargs):
            raise NotImplementedError("Advanced Feature: Intune integration requires the Addon.")

        def create_intunewin(self, *args, **kwargs):
             raise NotImplementedError("Advanced Feature: Intune integration requires the Addon.")

        def assign_to_group(self, *args, **kwargs):
             pass

        def get_device_groups(self, *args, **kwargs):
            return []
