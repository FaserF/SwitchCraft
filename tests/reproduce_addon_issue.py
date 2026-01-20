import os
import zipfile
import shutil
import tempfile
import logging
from pathlib import Path
import sys

# Setup logging to STDOUT
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))
try:
    from switchcraft.services.addon_service import AddonService
except ImportError as e:
    print(f"CRITICAL ERROR: {e}")
    sys.exit(1)

def test_nested_manifest_install():
    print("--- Testing Nested Manifest Install ---")

    manifest_content = '{"id": "test.addon", "name": "Test Addon", "version": "1.0.0"}'

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = Path(temp_dir) / "test_nested.zip"

        with zipfile.ZipFile(zip_path, 'w') as z:
            z.writestr("Addon-Repo-Main/manifest.json", manifest_content)
            z.writestr("Addon-Repo-Main/script.py", "print('hello')")

        print(f"Created zip: {zip_path}")

        service = AddonService()

        with tempfile.TemporaryDirectory() as temp_install_dir:
            service.addons_dir = Path(temp_install_dir)
            print(f"Install Dir: {service.addons_dir}")

            try:
                service.install_addon(str(zip_path))

                addon_path = service.addons_dir / "test.addon"

                assert addon_path.exists(), f"Addon path does not exist. Contents of install dir: {list(service.addons_dir.iterdir())}"
                assert (addon_path / "manifest.json").exists(), f"manifest.json missing. Contents: {list(addon_path.rglob('*'))}"
                assert (addon_path / "script.py").exists(), "script.py missing."

def test_root_manifest_install():
    print("\n--- Testing Root Manifest Install ---")

    manifest_content = '{"id": "test.addon.root", "name": "Test Addon Root", "version": "1.0.0"}'

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = Path(temp_dir) / "test_root.zip"

        with zipfile.ZipFile(zip_path, 'w') as z:
            z.writestr("manifest.json", manifest_content)

        service = AddonService()
        with tempfile.TemporaryDirectory() as temp_install_dir:
            service.addons_dir = Path(temp_install_dir)

            service.install_addon(str(zip_path))
            addon_path = service.addons_dir / "test.addon.root"
            assert addon_path.exists(), f"Root addon path does not exist. Contents: {list(service.addons_dir.rglob('*'))}"
            assert (addon_path / "manifest.json").exists(), f"Root addon manifest.json missing. Contents: {list(service.addons_dir.rglob('*'))}"

if __name__ == "__main__":
    test_nested_manifest_install()
    test_root_manifest_install()
