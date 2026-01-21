import unittest
from unittest.mock import MagicMock, patch
from switchcraft_winget.utils.winget import WingetHelper

class TestWinget(unittest.TestCase):
    @patch('subprocess.run')
    def test_search_by_name_powershell_success(self, mock_run):
        # Mock successful winget search output
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = """
[
  {
    "Name": "7-Zip",
    "Id": "7zip.7zip",
    "Version": "24.08",
    "Source": "winget"
  }
]
"""
        mock_run.return_value = mock_proc

        helper = WingetHelper()
        url = helper.search_by_name("7zip")

        self.assertIsNotNone(url)
        # Expect winget.run URL based on new logic
        self.assertEqual(url, "https://github.com/microsoft/winget-pkgs/tree/master/manifests/7/7zip/7zip")


    @patch('subprocess.run')
    def test_search_packages_found(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = """
[
  {
    "Name": "Node.js",
    "Id": "OpenJS.NodeJS",
    "Version": "20.0.0",
    "Source": "winget"
  }
]
"""
        mock_run.return_value = mock_proc

        helper = WingetHelper()
        results = helper.search_packages("node")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["Id"], "OpenJS.NodeJS")
        self.assertEqual(results[0]["Name"], "Node.js")

    @patch('shutil.which', return_value=None)
    @patch('switchcraft_winget.utils.winget.WingetHelper._search_via_github', return_value=[])
    @patch('switchcraft_winget.utils.winget.WingetHelper._search_via_api', return_value=[])
    @patch('switchcraft_winget.utils.winget.WingetHelper._search_via_static_dataset', return_value=[])
    def test_search_no_cli(self, mock_static, mock_api, mock_github, mock_which):
        helper = WingetHelper()
        self.assertIsNone(helper.search_by_name("AnyApp"))
        self.assertEqual(helper.search_packages("AnyApp"), [])

if __name__ == '__main__':
    unittest.main()
