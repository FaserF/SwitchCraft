import os
import zipfile
import shutil
import tempfile
import logging
from pathlib import Path
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock AddonService basics to avoid full app dependency if possible,
# or import if the environment allows.
# Trying to import directly first.
try:
    # Adjust path to include src
    sys.path.append(str(Path(__file__).parent.parent / "src"))
    from switchcraft.services.addon_service import AddonService
except ImportError:
    logger.error("Could not import AddonService. Please check path.")
    sys.exit(1)

def test_nested_manifest_install():
    print("Testing installation of addon with nested manifest.json...")

    # Create valid manifest content
    manifest_content = '{"id": "test.addon", "name": "Test Addon", "version": "1.0.0"}'

    # Create a temporary directory for the mock zip
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = Path(temp_dir) / "test_addon.zip"

        # Create a zip with manifest in a subdirectory (simulate GitHub release)
        with zipfile.ZipFile(zip_path, 'w') as z:
            z.writestr("Addon-Repo-Main/manifest.json", manifest_content)
            z.writestr("Addon-Repo-Main/script.py", "print('hello')")

        print(f"Created mock zip at {zip_path}")

        # Initialize service
        service = AddonService()

        # Override addons_dir to a temp dir to avoid polluting real install
        with tempfile.TemporaryDirectory() as temp_install_dir:
            service.addons_dir = Path(temp_install_dir)
            print(f"Using temp install dir: {service.addons_dir}")

            try:
                # Attempt install
                service.install_addon(str(zip_path))

                # Verify installation
                installed_path = service.addons_dir / "test.addon"
                if installed_path.exists() and (installed_path / "manifest.json").exists():
                    print("SUCCESS: Addon installed and manifest found.")
                    # Check if script was extracted
                    if (installed_path / "script.py").exists():
                        print("SUCCESS: Subfiles extracted correctly.")
                    else:
                        print("FAILURE: script.py not found in installed folder.")
                else:
                    print("FAILURE: Addon folder or manifest not found after install.")

            except Exception as e:
                print(f"FAILURE: Install raised exception: {e}")
                import traceback
                traceback.print_exc()

def test_root_manifest_install():
    print("\nTesting installation of addon with root manifest.json...")

    manifest_content = '{"id": "test.addon.root", "name": "Test Addon Root", "version": "1.0.0"}'

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = Path(temp_dir) / "test_addon_root.zip"

        with zipfile.ZipFile(zip_path, 'w') as z:
            z.writestr("manifest.json", manifest_content)

        service = AddonService()
        with tempfile.TemporaryDirectory() as temp_install_dir:
            service.addons_dir = Path(temp_install_dir)

            try:
                service.install_addon(str(zip_path))
                installed_path = service.addons_dir / "test.addon.root"
                if installed_path.exists() and (installed_path / "manifest.json").exists():
                    print("SUCCESS: Root addon installed.")
                else:
                    print("FAILURE: Root addon failed.")
            except Exception as e:
                print(f"FAILURE: Root install raised exception: {e}")

if __name__ == "__main__":
    test_nested_manifest_install()
    test_root_manifest_install()
