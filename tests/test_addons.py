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
        with patch.object(AddonService, 'get_addon_dir', return_value=str(tmp_path)):
            # Create a dummy addon
            self.addon_id = "test_addon"
            self.addon_pkg = "switchcraft_test_addon"
            AddonService.ADDONS[self.addon_id] = self.addon_pkg

            self.addon_path = tmp_path / self.addon_pkg
            self.addon_path.mkdir()
            (self.addon_path / "__init__.py").touch()

            yield

            # Cleanup
            if self.addon_id in AddonService.ADDONS:
                del AddonService.ADDONS[self.addon_id]

            # Remove from sys.path if it was added
            if str(tmp_path) in sys.path:
                sys.path.remove(str(tmp_path))
            if self.addon_pkg in sys.modules:
                del sys.modules[self.addon_pkg]

    def test_is_addon_installed(self):
        assert AddonService.is_addon_installed(self.addon_id) is True
        assert AddonService.is_addon_installed("non_existent") is False

    def test_import_addon_module(self):
        # Create a submodule
        sub_dir = self.addon_path / "sub"
        sub_dir.mkdir()
        (sub_dir / "__init__.py").touch()
        (sub_dir / "logic.py").write_text("DATA = 'hello'")

        mod = AddonService.import_addon_module(self.addon_id, "sub.logic")
        assert mod is not None
        assert mod.DATA == 'hello'

    def test_install_addon_mock(self):
        # Current implementation is a mock that just returns True
        assert AddonService.install_addon("any") is True

    def test_uninstall_addon(self):
        # Addon exists
        assert (self.addon_path).exists()

        # Uninstall (it should NOT delete if in dev mode, but we can mock dev mode check)
        # Actually, let's just test that it attempts to remove it if we bypass the dev check
        # For simplicity, we just test that it returns True if directory exists
        assert AddonService.uninstall_addon(self.addon_id) is True

        # If we weren't in dev mode, it would be gone.
        # But wait, AddonService has:
        # if os.path.exists(os.path.join(cls.get_addon_dir(), "..", ".git")): return True
        # Since tmp_path doesn't have .git, it SHOULD delete it.
        assert not (self.addon_path).exists()
