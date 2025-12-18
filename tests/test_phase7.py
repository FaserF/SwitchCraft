
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from switchcraft.services.intune_service import IntuneService

class TestIntuneService(unittest.TestCase):
    def setUp(self):
        self.service = IntuneService(tools_dir="tools_test")

    def test_switchcraft_winget_fix(self):
        """Test that searching for 'SwitchCraft' returns the fixed URL."""
        from switchcraft.utils.winget import WingetHelper

        # Fake return value for search_packages
        fake_result = [{"Id": "FaserF.SwitchCraft", "Name": "SwitchCraft", "Source": "winget"}]

        with patch.object(WingetHelper, 'search_packages', return_value=fake_result):
            helper = WingetHelper()
            url = helper.search_by_name("SwitchCraft")
            # New URL format from refactor
            self.assertEqual(url, "https://github.com/microsoft/winget-pkgs/tree/master/manifests/s/FaserF/SwitchCraft")

            url_lower = helper.search_by_name("switchcraft")
            self.assertEqual(url_lower, "https://github.com/microsoft/winget-pkgs/tree/master/manifests/s/FaserF/SwitchCraft")

    @patch('switchcraft_advanced.services.intune_service.subprocess.run')
    def test_create_intunewin_args(self, mock_run):
        """Test that create_intunewin constructs the correct command line."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Done"

        with patch.object(IntuneService, 'is_tool_available', return_value=True), \
             patch.object(IntuneService, 'download_tool', return_value=True):

            # Mock paths to avoid unresolved path errors in test
            with patch('pathlib.Path.resolve') as mock_resolve:
                mock_resolve.side_effect = lambda: Path("/abs/path")
                with patch('pathlib.Path.mkdir'):
                     self.service.create_intunewin(
                        source_folder="src",
                        setup_file="setup.exe",
                        output_folder="out",
                        quiet=True,
                        catalog_folder="cat"
                    )

        # Verify args passed to subprocess
        args, kwargs = mock_run.call_args
        cmd = args[0]

        # We look for flags
        self.assertIn("-c", cmd)
        self.assertIn("-s", cmd)
        self.assertIn("-o", cmd)
        self.assertIn("-q", cmd)
        self.assertIn("-a", cmd) # Catalog was passed

if __name__ == '__main__':
    unittest.main()
