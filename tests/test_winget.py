import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from switchcraft.utils.winget import WingetHelper

class TestWinget(unittest.TestCase):
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.iterdir')
    def test_search_by_name_found(self, mock_iterdir, mock_exists):
        # Setup mock directory structure for "7zip"
        # root/7/7zip.Mobile/manifest.yaml

        mock_vendor_dir = MagicMock()
        mock_vendor_dir.name = "7zip.Mobile"
        mock_vendor_dir.is_dir.return_value = True

        # Configure relative_to to return a mock that behaves like a Path
        mock_rel_path = MagicMock()
        mock_rel_path.as_posix.return_value = "7/7zip.Mobile"
        mock_vendor_dir.relative_to.return_value = mock_rel_path

        # When searching, we check the letter folder first
        mock_iterdir.return_value = [mock_vendor_dir]

        # Configure package inside vendor
        mock_pkg_dir = MagicMock()
        mock_pkg_dir.name = "7zip"

        # Configure relative_to on the package mock
        mock_pkg_rel_path = MagicMock()
        mock_pkg_rel_path.as_posix.return_value = "7/7zip.Mobile/7zip"
        mock_pkg_dir.relative_to.return_value = mock_pkg_rel_path

        # Important: The code now iterates inside the vendor dir
        mock_vendor_dir.iterdir.return_value = [mock_pkg_dir]

        helper = WingetHelper()
        # Mock relative_to to return a clean path string
        # with patch('pathlib.Path.relative_to', return_value=Path("7/7zip.Mobile")): # Not needed since we mock the instance method
        url = helper.search_by_name("7zip")
        self.assertIsNotNone(url)
        self.assertIn("github.com/microsoft/winget-pkgs", url)
        self.assertIn("7/7zip.Mobile/7zip", url)

    @patch('pathlib.Path.exists', return_value=False)
    def test_search_no_local_repo(self, mock_exists):
        helper = WingetHelper()
        self.assertIsNone(helper.search_by_name("AnyApp"))

if __name__ == '__main__':
    unittest.main()
