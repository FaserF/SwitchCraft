import os
import sys
import logging
import shutil
import requests
import zipfile
import io
from pathlib import Path
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
        if not package_name:
            return False

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
        if not cls.is_addon_installed(addon_id):
            return None

        package_root = cls.ADDONS.get(addon_id)
        if not package_root:
            return None

        cls.register_addons()
        full_name = f"{package_root}.{module_name}" if module_name else package_root

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
        - Release Builds: Download 'switchcraft_{id}.zip' from release assets.
        - Dev Builds (or fallback): Download source code from main branch and extract.
        """
        if addon_id == "all":
            success = True
            for aid in cls.ADDONS.keys():
                if not cls.install_addon(aid):
                    success = False
            return success

        pkg_name = cls.ADDONS.get(addon_id)
        if not pkg_name:
            return False

        logger.info(f"Installing addon: {addon_id} ({pkg_name})...")

        # Running from source (True Dev Environment) - usually already there, but just in case
        if not getattr(sys, 'frozen', False):
             logger.info("Running from source, addons should be present locally.")
             return True

        from switchcraft import __version__
        is_dev_build = "dev" in __version__.lower() or "beta" in __version__.lower()

        try:
            download_url = None
            is_source_zip = False

            # Strategy 1: Release Asset (Preferred for Stable)
            if not is_dev_build:
                try:
                    logger.debug(f"Fetching release info for v{__version__}...")
                    api_url = "https://api.github.com/repos/FaserF/SwitchCraft/releases/latest"
                    resp = requests.get(api_url, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        assets = data.get("assets", [])
                        target_name = f"{pkg_name}.zip"
                        for asset in assets:
                            if asset["name"] == target_name:
                                download_url = asset["browser_download_url"]
                                break
                except Exception as e:
                    logger.warning(f"Failed to fetch release info: {e}")

            # Strategy 2: Main Branch Source (Fallback or Explicit Dev)
            # Implemented fallback: If not found in releases, or if we are dev build
            if not download_url:
                logger.info("Dev build or asset missing. Falling back to main branch source.")
                download_url = "https://github.com/FaserF/SwitchCraft/archive/refs/heads/main.zip"
                is_source_zip = True

            if not download_url:
                logger.error("Could not determine download URL for addon.")
                return False

            # Download
            logger.info(f"Downloading {download_url}...")
            r = requests.get(download_url, stream=True, timeout=60)
            r.raise_for_status()

            # Extract
            z = zipfile.ZipFile(io.BytesIO(r.content))
            addon_root = cls.get_addon_dir()
            addon_root.mkdir(parents=True, exist_ok=True)

            if is_source_zip:
                # Dynamic search for the source folder in the zip
                # e.g., SwitchCraft-main/src/switchcraft_advanced/

                source_prefix = None
                # Normalize pkg_name for matching
                search_target = f"src/{pkg_name}/"

                all_files = z.namelist()
                for fname in all_files:
                    if search_target in fname and fname.endswith(search_target):
                         # Found the directory entry (e.g., 'SwitchCraft-main/src/switchcraft_winget/')
                         source_prefix = fname
                         break

                # If directory entry not found explicitly, search for files containing the path
                if not source_prefix:
                    for fname in all_files:
                        if f"/src/{pkg_name}/" in fname or fname.startswith(f"src/{pkg_name}/"):
                             # Reconstruct prefix
                             parts = fname.split(f"/src/{pkg_name}/")
                             source_prefix = f"{parts[0]}/src/{pkg_name}/"
                             break

                if not source_prefix:
                    logger.error(f"Could not find '/src/{pkg_name}/' in zip. Available paths: {all_files[:5]}...")
                    return False

                logger.info(f"Extracting addon from: {source_prefix}")

                found_any = False
                for member in z.infolist():
                    if member.filename.startswith(source_prefix):
                        found_any = True
                        rel_path = member.filename[len(source_prefix):]
                        if not rel_path:
                            continue

                        target_path = addon_root / pkg_name / rel_path
                        if member.is_dir():
                            target_path.mkdir(parents=True, exist_ok=True)
                        else:
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            with z.open(member) as source, open(target_path, "wb") as target:
                                shutil.copyfileobj(source, target)

                # Verify installation immediately
                if (addon_root / pkg_name / "__init__.py").exists():
                     logger.info(f"Verified installation of {pkg_name} at {addon_root / pkg_name}")
                else:
                     logger.warning(f"Installation of {pkg_name} might have failed. __init__.py not found at {addon_root / pkg_name}")

                if not found_any:
                    logger.error(f"Could not find {pkg_name} in source zip (Prefix: {source_prefix}).")
                    return False
            else:
                z.extractall(addon_root)

            logger.info(f"Successfully installed {addon_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to install addon {addon_id}: {e}", exc_info=False) # Reduced verbosity
            return False

    @classmethod
    def uninstall_addon(cls, addon_id: str) -> bool:
        """Uninstall (remove) the specified addon."""
        pkg_name = cls.ADDONS.get(addon_id)
        if not pkg_name:
            return False

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
