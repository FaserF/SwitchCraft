import json
import logging
import importlib.util
import shutil
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Legacy compatibility: singleton instance for static method calls
_addon_service_instance = None

def _get_addon_service_instance():
    global _addon_service_instance
    if _addon_service_instance is None:
        _addon_service_instance = AddonService()
    return _addon_service_instance

class AddonService:
    def __init__(self):
        # Use static method for directory to allow easier mocking
        self.addons_dir = self.get_addon_dir()
        self.loaded_addons = {} # id -> module/class info

    @staticmethod
    def get_addon_dir():
        """Returns the base directory for addons."""
        path = Path.home() / ".switchcraft" / "addons"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def read_manifest(addon_dir):
        """Reads and validates the manifest.json file from an addon directory."""
        manifest = addon_dir / "manifest.json"
        if not manifest.exists():
            return None

        try:
            with open(manifest, "r") as f:
                data = json.load(f)
                if "id" in data:
                    return data
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            logger.warning(f"Error reading addon manifest at {addon_dir}: {e}")
        return None

    def _iter_addons(self):
        """
        Yields (path, manifest_data) for all valid addons found.
        """
        for d in self.addons_dir.iterdir():
            if d.is_dir():
                data = self.read_manifest(d)
                if data:
                    yield d, data

    def list_addons(self):
        """
        Scans addons directory for valid manifests.
        Returns list of dicts.
        """
        addons = []
        for d, data in self._iter_addons():
             data["_path"] = str(d) # internal use
             addons.append(data)
        return addons

    def load_addon_view(self, addon_id):
        """
        Dynamically loads the addon view class.
        Returns the Class object (not instance).
        """
        # Find path
        addon_path = None
        manifest_data = None

        for d, data in self._iter_addons():
             if data.get("id") == addon_id:
                 addon_path = d
                 manifest_data = data
                 break

        if not addon_path:
            raise FileNotFoundError(f"Addon {addon_id} not found")

        entry_point = manifest_data.get("entry_point", "view.py")
        class_name = manifest_data.get("class_name", "AddonView")

        file_path = addon_path / entry_point
        if not file_path.exists():
             raise FileNotFoundError(f"Entry point {entry_point} not found for addon {addon_id}")

        # Magic import
        try:
            spec = importlib.util.spec_from_file_location(f"addons.{addon_id}", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, class_name):
                return getattr(module, class_name)
            else:
                raise AttributeError(f"Class {class_name} not found in {entry_point}")
        except Exception as e:
            logger.error(f"Failed to load addon {addon_id}: {e}")
            raise e

    def import_addon_module(self, addon_id, module_name):
        """
        Attempts to import a specific module from an addon.
        Returns the module object or None if not found/error.
        """
        # Find addon path
        addon_path = None
        for d, data in self._iter_addons():
             if data.get("id") == addon_id:
                 addon_path = d
                 break

        if not addon_path:
            return None

        # Resolve file path from module name (dotted)
        # e.g. "analyzers.universal" -> "analyzers/universal.py"
        rel_path = module_name.replace(".", "/") + ".py"
        file_path = addon_path / rel_path

        if not file_path.exists():
            # Try as package (dir/__init__.py)
            rel_path = module_name.replace(".", "/") + "/__init__.py"
            file_path = addon_path / rel_path
            if not file_path.exists():
                return None

        try:
            name = f"addons.{addon_id}.{module_name}"
            spec = importlib.util.spec_from_file_location(name, file_path)
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            logger.error(f"Failed to import addon module {name}: {e}")
            return None

    def install_addon(self, zip_path):
        """
        Installs an addon from a zip file.
        Expects zip to contain manifest.json at root or in a subfolder.
        """
        zip_path = Path(zip_path)
        if not zip_path.exists():
            raise FileNotFoundError(f"Zip not found: {zip_path}")

        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Validate manifest
                valid = False
                files = z.namelist()
                # Simple check for manifest.json at root
                if "manifest.json" in files:
                     valid = True

                # TODO: Support nested, but let's strict for now
                if not valid:
                    raise Exception("Invalid addon: manifest.json missing from root")

                # Check ID from manifest
                with z.open("manifest.json") as f:
                    data = json.load(f)
                    addon_id = data.get("id")
                    if not addon_id:
                        raise Exception("Invalid manifest: missing id")

                # Extract
                target = self.addons_dir / addon_id
                if target.exists():
                    shutil.rmtree(target) # Overwrite
                target.mkdir()

                # target.mkdir() was already called above

                # Secure extraction
                for member in z.infolist():
                    # Resolve the target path for this member
                    file_path = (target / member.filename).resolve()

                    # Ensure the resolved path starts with the target directory (prevent Zip Slip)
                    if not str(file_path).startswith(str(target.resolve())):
                        logger.error(f"Security Alert: Attempted Zip Slip with {member.filename}")
                        continue

                    # Create parent directories
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    # Extract file
                    if not member.is_dir():
                        with z.open(member, 'r') as source, open(file_path, 'wb') as dest:
                            shutil.copyfileobj(source, dest)

                logger.info(f"Installed addon: {addon_id}")
                return True
        except Exception as e:
            logger.error(f"Install failed: {e}")
            raise e

    def delete_addon(self, addon_id):
         # Find and delete
         addons = list(self._iter_addons())
         for d, data in addons:
             if data.get("id") == addon_id:
                 try:
                     shutil.rmtree(d)
                     return True
                 except OSError as e:
                     logger.error(f"Failed to delete addon {addon_id} at {d}: {e}")
         return False

    def is_addon_installed(self, addon_id):
        """
        Checks if an addon is installed by ID.
        """
        for _, data in self._iter_addons():
            if data.get("id") == addon_id:
                return True
        return False

    def uninstall_addon(self, addon_id):
        """Legacy alias for delete_addon."""
        return self.delete_addon(addon_id)

    def _extract_and_install_zip(self, zip_content, pkg_name, is_source=False, auto_detect=False):
        """Legacy method for tests."""
        # Create a temp zip file and call install_addon
        temp_zip = self.addons_dir / "_temp_install.zip"
        with open(temp_zip, "wb") as f:
            f.write(zip_content)
        try:
            return self.install_addon(str(temp_zip))
        finally:
            if temp_zip.exists():
                temp_zip.unlink()

    # --- Legacy Static Methods ---
    @staticmethod
    def register_addons():
        """Legacy: No-op for backwards compatibility."""
        pass

    @staticmethod
    def set_app_window(window):
        """Legacy: No-op for backwards compatibility."""
        pass

    @staticmethod
    def install_all_missing():
        """Legacy: No-op for backwards compatibility."""
        return True
