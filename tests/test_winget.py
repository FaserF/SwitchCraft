import unittest
from unittest.mock import MagicMock, patch
from switchcraft_advanced.utils.winget import WingetHelper

class TestWinget(unittest.TestCase):
    @patch('shutil.which', return_value="C:\\winget.exe")
    @patch('subprocess.run')
    def test_search_by_name_cli_found(self, mock_run, mock_which):
        # Mock successful winget search output
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = """
Name      Id             Version  Match Source
---------------------------------------------
7-Zip     7zip.7zip      24.08          winget
"""
        mock_run.return_value = mock_proc

        helper = WingetHelper()
        url = helper.search_by_name("7zip")

        self.assertIsNotNone(url)
        # Expect winget.run URL based on new logic
        self.assertEqual(url, "https://winget.run/pkg/7zip/7zip")

    @patch('shutil.which', return_value="C:\\winget.exe")
    @patch('subprocess.run')
    def test_search_packages_found(self, mock_run, mock_which):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = """
Name      Id             Version  Match Source
---------------------------------------------
Node.js   OpenJS.NodeJS  20.0.0         winget
"""
        mock_run.return_value = mock_proc

        helper = WingetHelper()
        results = helper.search_packages("node")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["Id"], "OpenJS.NodeJS")
        self.assertEqual(results[0]["Name"], "Node.js")

    @patch('shutil.which', return_value=None)
    def test_search_no_cli(self, mock_which):
        helper = WingetHelper()
        self.assertIsNone(helper.search_by_name("AnyApp"))
        self.assertEqual(helper.search_packages("AnyApp"), [])

if __name__ == '__main__':
    unittest.main()
