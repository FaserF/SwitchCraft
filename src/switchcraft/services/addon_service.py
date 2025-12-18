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
    def install_addon(cls, addon_id: str, prompt_callback=None) -> bool:
        """
        Install the specified addon with robust fallback strategy.
        prompt_callback: function(type, **kwargs) -> result
            Types: 'ask_browser', 'ask_file', 'ask_manual_zip'
        """
        if addon_id == "all":
            success = True
            for aid in cls.ADDONS.keys():
                if not cls.install_addon(aid, prompt_callback):
                    success = False
            return success

        pkg_name = cls.ADDONS.get(addon_id)
        if not pkg_name:
            return False

        logger.info(f"Starting installation for addon: {addon_id} ({pkg_name})...")

        # 0. Dev/Source Check
        if not getattr(sys, 'frozen', False):
             logger.info("Running from source, addons should be present locally.")
             return True

        from switchcraft import __version__
        is_dev_build = "dev" in __version__.lower() or "beta" in __version__.lower()

        # Helper to try download and install
        def try_install_url(url, desc):
            try:
                logger.info(f"Attempting strategy: {desc}")
                r = requests.get(url, stream=True, timeout=60)
                if r.status_code == 200:
                    return cls._extract_and_install_zip(r.content, pkg_name, is_source="archive/refs" in url)
            except Exception as e:
                logger.warning(f"Strategy {desc} failed: {e}")
            return False

        # Strategy 1: Local Check (Skip if we are here, means it's missing)

        # Strategy 2: Current Release Asset
        if not is_dev_build:
            try:
                api_url = "https://api.github.com/repos/FaserF/SwitchCraft/releases/latest"
                resp = requests.get(api_url, timeout=5)
                if resp.status_code == 200:
                    assets = resp.json().get("assets", [])
                    target_name = f"{pkg_name}.zip"
                    for asset in assets:
                        if asset["name"] == target_name:
                            if try_install_url(asset["browser_download_url"], "Current Release Asset"):
                                return True
            except Exception as e:
                logger.warning(f"Release check failed: {e}")

        # Strategy 3: Main Branch Source
        # Often valid for dev builds or if release asset is missing
        main_zip_url = "https://github.com/FaserF/SwitchCraft/archive/refs/heads/main.zip"
        if try_install_url(main_zip_url, "Main Branch Source"):
            return True

        # Strategy 4: Older Releases (Scan last 5 releases)
        try:
            api_url = "https://api.github.com/repos/FaserF/SwitchCraft/releases?per_page=5"
            resp = requests.get(api_url, timeout=5)
            if resp.status_code == 200:
                for release in resp.json():
                    for asset in release.get("assets", []):
                        if asset["name"] == f"{pkg_name}.zip":
                             if try_install_url(asset["browser_download_url"], f"Release {release['tag_name']}"):
                                 return True
        except Exception:
            pass

        # Strategy 5: Browser Prompt
        if prompt_callback:
            if prompt_callback("ask_browser", url="https://github.com/FaserF/SwitchCraft/releases"):
                 # User opened browser, maybe they downloaded it?
                 if prompt_callback("ask_manual_zip", addon_id=addon_id):
                     return True
                 return False # User cancelled manual selection

        # Strategy 6: Manual ZIP (Direct prompt if browser step skipped or failed logic)
        if prompt_callback:
             return prompt_callback("ask_manual_zip", addon_id=addon_id)

        return False

    @classmethod
    def install_addon_from_zip(cls, zip_path_or_bytes):
        """Install addon from a local zip file or bytes."""
        try:
            if isinstance(zip_path_or_bytes, (str, Path)):
                with open(zip_path_or_bytes, "rb") as f:
                    content = f.read()
            else:
                content = zip_path_or_bytes

            # We don't know the package name for sure, so we have to INSPECT the zip
            # to find a valid addon package (switchcraft_*).
            return cls._extract_and_install_zip(content, None, is_source=True, auto_detect=True)
        except Exception as e:
            logger.error(f"Manual install failed: {e}")
            return False

    @classmethod
    def _extract_and_install_zip(cls, zip_content, pkg_name, is_source=False, auto_detect=False):
        try:
            z = zipfile.ZipFile(io.BytesIO(zip_content))
            addon_root = cls.get_addon_dir()
            addon_root.mkdir(parents=True, exist_ok=True)

            source_prefix = None
            detected_pkg_name = pkg_name

            if auto_detect:
                # Find any folder matching switchcraft_* containing __init__.py
                for f in z.namelist():
                    parts = f.split('/')
                    for part in parts:
                        if part.startswith("switchcraft_") and not part.endswith(".zip"):
                            # Check if valid package (has init)
                            # Checking rigid path: .../switchcraft_xxx/__init__.py
                            if f.endswith(f"{part}/__init__.py"):
                                detected_pkg_name = part
                                # Calulcate prefix
                                suffix = f"{part}/__init__.py"
                                source_prefix = f[:-len(suffix)]
                                break
                    if detected_pkg_name and detected_pkg_name != pkg_name:
                        break

                if not detected_pkg_name:
                    logger.error("Could not auto-detect valid switchcraft addon in zip.")
                    return False
            elif is_source:
                 # Standard logic for source zips (SwitchCraft-main/...)
                 init_file = f"{pkg_name}/__init__.py"
                 for fname in z.namelist():
                    if fname.endswith(init_file):
                        suffix_len = len(init_file)
                        source_prefix = fname[:-suffix_len]
                        break

            # If not source and not auto-detect (e.g. release asset), we assume root is package content?
            # Actually release assets are usually just the folder zipped?
            # Or content of folder?
            # Standard SwitchCraft release asset: switchcraft_winget.zip -> contains switchcraft_winget/ folder?
            # Let's handle both.

            if not source_prefix:
                # Maybe it is at root
                if f"{detected_pkg_name}/__init__.py" in z.namelist():
                    source_prefix = ""
                else:
                    # Try to see if it is just flat files? (Unlikely for python pkg)
                    pass

            if source_prefix is None:
                logger.error(f"Structure mismatch in zip for {detected_pkg_name}")
                return False

            logger.info(f"Extracting {detected_pkg_name} from prefix '{source_prefix}'")

            # Cleanup existing if any
            target_dir = addon_root / detected_pkg_name
            if target_dir.exists():
                shutil.rmtree(target_dir)

            for member in z.infolist():
                if member.filename.startswith(source_prefix):
                    rel_path = member.filename[len(source_prefix):]
                    if not rel_path or rel_path.startswith("__MACOSX"): continue # Skip junk

                    # Ensure we are extracting into package folder
                    full_target = target_dir / rel_path
                    if member.is_dir():
                        full_target.mkdir(parents=True, exist_ok=True)
                    else:
                        full_target.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(member) as s, open(full_target, "wb") as t:
                            shutil.copyfileobj(s, t)

            logger.info(f"Installed {detected_pkg_name}")
            return True

        except Exception as e:
            logger.error(f"Extraction failed: {e}")
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
