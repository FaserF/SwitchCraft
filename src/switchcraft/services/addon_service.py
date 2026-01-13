import json
import logging
import importlib.util
import shutil
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

class AddonService:
    def __init__(self):
        # Determine addons directory (e.g. adjacent to src or in user profile)
        # For now using a dedicated folder in user home or adjacent to app
        self.addons_dir = Path.home() / ".switchcraft" / "addons"
        self.addons_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_addons = {} # id -> module/class info

    def list_addons(self):
        """
        Scans addons directory for valid manifests.
        Returns list of dicts.
        """
        addons = []
        for d in self.addons_dir.iterdir():
            if d.is_dir():
                manifest = d / "manifest.json"
                if manifest.exists():
                    try:
                        with open(manifest, "r") as f:
                            data = json.load(f)
                            # Basic validation
                            if "id" in data and "name" in data:
                                data["_path"] = str(d) # internal use
                                addons.append(data)
                    except Exception as e:
                        logger.error(f"Error reading addon manifest at {d}: {e}")
        return addons

    def load_addon_view(self, addon_id):
        """
        Dynamically loads the addon view class.
        Returns the Class object (not instance).
        """
        # Find path
        addon_path = None
        manifest_data = None

        for d in self.addons_dir.iterdir():
            if d.is_dir() and (d / "manifest.json").exists():
                 try:
                     with open(d / "manifest.json") as f:
                         data = json.load(f)
                         if data.get("id") == addon_id:
                             addon_path = d
                             manifest_data = data
                             break
                 except: pass

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
                    if not addon_id: raise Exception("Invalid manifest: missing id")

                # Extract
                target = self.addons_dir / addon_id
                if target.exists():
                    shutil.rmtree(target) # Overwrite
                target.mkdir()

                z.extractall(target)
                logger.info(f"Installed addon: {addon_id}")
                return True
        except Exception as e:
            logger.error(f"Install failed: {e}")
            raise e

    def delete_addon(self, addon_id):
         # Find and delete
         for d in self.addons_dir.iterdir():
            if d.is_dir() and (d / "manifest.json").exists():
                 try:
                     with open(d / "manifest.json") as f:
                         data = json.load(f)
                         if data.get("id") == addon_id:
                             shutil.rmtree(d)
                             return True
                 except: pass
         return False
