import os
import sys
import logging
import shutil
from pathlib import Path
from typing import Optional, List
from switchcraft.utils.config import SwitchCraftConfig

logger = logging.getLogger(__name__)

class AddonService:
    # Addon Definitions
    ADDONS = {
        "advanced": "switchcraft_advanced",
        "winget": "switchcraft_winget",
        "ai": "switchcraft_ai",
        "debug": "switchcraft_debug"
    }

    @staticmethod
    def get_addon_dir() -> Path:
        """Returns the directory where addons are stored."""
        if getattr(sys, 'frozen', False):
            if SwitchCraftConfig.get_value("PortableMode"):
                 return Path(sys.executable).parent / "addons"

            app_data = os.getenv('APPDATA')
            if app_data:
                path = Path(app_data) / "FaserF" / "SwitchCraft" / "addons"
                path.mkdir(parents=True, exist_ok=True)
                return path

        # Dev mode: Parent of src/switchcraft is src/
        # Addons are in src/switchcraft_*, so basically the same level as switchcraft package
        # IF running from source, addons are just sibling packages.
        return Path(__file__).parent.parent.parent

    @classmethod
    def is_addon_installed(cls, addon_id: str) -> bool:
        """Check if a specific addon is installed."""
        package_name = cls.ADDONS.get(addon_id)
        if not package_name: return False

        addon_path = cls.get_addon_dir() / package_name

        # In Dev mode, they might be source folders
        if not getattr(sys, 'frozen', False):
            return (addon_path / "__init__.py").exists() or addon_path.is_dir()

        return (addon_path / "__init__.py").exists()

    @classmethod
    def register_addons(cls):
        """Register all found addons to sys.path."""
        addon_dir = cls.get_addon_dir()
        if str(addon_dir) not in sys.path:
            sys.path.insert(0, str(addon_dir))
            logger.info(f"Registered addon directory: {addon_dir}")

    @classmethod
    def import_addon_module(cls, addon_id: str, module_name: str):
        """Dynamically import a module from an addon."""
        package_root = cls.ADDONS.get(addon_id)
        if not package_root: return None

        cls.register_addons()
        full_name = f"{package_root}.{module_name}"
        # If module_name is empty, import just the package
        if not module_name: full_name = package_root

        try:
            import importlib
            return importlib.import_module(full_name)
        except ImportError as e:
            logger.warning(f"Failed to import {full_name}: {e}")
            return None

    @classmethod
    def install_addon(cls, addon_id: str) -> bool:
        """
        Install the specified addon.
        For MVP/Prototype: Since we don't have a download server,
        we simulate this or assume we are enabling it if disabled?
        Actually, in a release, addons would be ZIPs.

        If 'all', installs all.
        """
        if addon_id == "all":
            success = True
            for aid in cls.ADDONS.keys():
                if not cls.install_addon(aid): success = False
            return success

        pkg_name = cls.ADDONS.get(addon_id)
        if not pkg_name: return False

        logger.info(f"Installing addon: {addon_id} ({pkg_name})...")

        # TODO: Implement Download/Unzip logic here
        # For now, we assume success if we are just verifying structure or enabling
        # In a real scenario:
        # 1. Download ZIP from GitHub Release
        # 2. Extract to get_addon_dir()

        # Mocking success for dev environment where folders exist
        return True

    @classmethod
    def uninstall_addon(cls, addon_id: str) -> bool:
        """Uninstall (remove) the specified addon."""
        pkg_name = cls.ADDONS.get(addon_id)
        if not pkg_name: return False

        addon_path = cls.get_addon_dir() / pkg_name

        logger.info(f"Uninstalling addon: {addon_id} from {addon_path}")

        # Protection for Dev Environment: Don't delete source code!
        if not getattr(sys, 'frozen', False):
            logger.warning("Skipping logical deletion in Dev Mode to protect source code.")
            return True

        try:
            if addon_path.exists():
                shutil.rmtree(addon_path)
            return True
        except Exception as e:
            logger.error(f"Uninstall failed: {e}")
            return False
