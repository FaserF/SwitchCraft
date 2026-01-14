import pytest
import os
import shutil
from pathlib import Path
from switchcraft.services.addon_service import AddonService

from unittest.mock import patch
import sys # Added for sys.path and sys.modules cleanup

class TestAddonService:
    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path):
        # Mock the addon directory to a temporary one
        with patch.object(AddonService, 'get_addon_dir', return_value=tmp_path):
            # Create a dummy addon
            self.addon_id = "test_addon"
            self.addon_pkg = "switchcraft_test_addon"
            # AddonService.ADDONS[self.addon_id] = self.addon_pkg

            self.addon_path = tmp_path / self.addon_id
            self.addon_path.mkdir()
            (self.addon_path / "__init__.py").touch()
            import json
            manifest_path = self.addon_path / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump({"id": self.addon_id, "name": "Test", "entry_point": "__init__.py"}, f)

            # Ensure file is written and flushed
            manifest_path.stat()

            yield

            # Cleanup
            # if self.addon_id in AddonService.ADDONS:
            #     del AddonService.ADDONS[self.addon_id]

            # Remove from sys.path if it was added
            if str(tmp_path) in sys.path:
                sys.path.remove(str(tmp_path))
            if self.addon_pkg in sys.modules:
                del sys.modules[self.addon_pkg]

    def test_is_addon_installed(self):
        assert AddonService().is_addon_installed(self.addon_id) is True
        assert AddonService().is_addon_installed("non_existent") is False

    def test_import_addon_module(self):
        # Create a submodule
        sub_dir = self.addon_path / "sub"
        sub_dir.mkdir()
        (sub_dir / "__init__.py").touch()
        (sub_dir / "logic.py").write_text("DATA = 'hello'")

        mod = AddonService().import_addon_module(self.addon_id, "sub.logic")
        assert mod is not None
        assert mod.DATA == 'hello'

    def test_install_addon_mock(self, tmp_path):
        import zipfile
        import json
        zip_path = tmp_path / "test.zip"
        with zipfile.ZipFile(zip_path, 'w') as z:
            z.writestr("manifest.json", json.dumps({"id": "new_addon", "name": "New"}))
        assert AddonService().install_addon(str(zip_path)) is True

    def test_uninstall_addon(self):
        # Addon exists
        assert (self.addon_path).exists()

        # Uninstall (it should NOT delete if in dev mode, but we can mock dev mode check)
        # Mock frozen=True to allow deletion
        with patch.object(sys, 'frozen', True, create=True):
            assert AddonService().uninstall_addon(self.addon_id) is True
            assert not (self.addon_path).exists()

    def test_extract_and_install_zip_backslashes(self):
        """Test extraction of zip with backslash paths (Windows style)."""
        import zipfile
        import io

        # Create a mock zip with backslash names
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, 'w') as z:
            # We must force backslashes in arcname
            # Note: switchcraft_winget/utils/winget.py -> switchcraft_winget\utils\winget.py
            # But the content should be a valid pkg structure
            z.writestr('switchcraft_winget/__init__.py', '')
            z.writestr('switchcraft_winget/utils/__init__.py', '')
            z.writestr('switchcraft_winget/utils/winget.py', 'print("ok")')
            import json
            z.writestr('manifest.json', json.dumps({"id": "winget", "name": "Winget"}))

        zip_content = bio.getvalue()

        # Mock ADDONS map to recognize this package
        # AddonService.ADDONS["winget"] = "switchcraft_winget"

        # Call extraction (auto-detect=True matching install_addon_from_zip or manual logic)
        # Or explicit pkg_name
        result = AddonService()._extract_and_install_zip(zip_content, "switchcraft_winget", is_source=False, auto_detect=True)

        assert result is True, "Extraction failed for backslash zip"

        # Verify file existence
        # get_addon_dir() returns tmp_path from fixture
        root = AddonService.get_addon_dir()
        assert (root / "winget" / "switchcraft_winget" / "__init__.py").exists()
        assert (root / "winget" / "switchcraft_winget" / "utils" / "__init__.py").exists()
        assert (root / "winget" / "switchcraft_winget" / "utils" / "winget.py").exists()
