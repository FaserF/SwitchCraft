import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from switchcraft.services.sap_service import SapService

class TestSapService(unittest.TestCase):
    def setUp(self):
        self.service = SapService()

    @patch('pathlib.Path.exists')
    def test_detect_admin_tool(self, mock_exists):
        # Path.exists() is called on the Path object, no 'path' argument passed to it
        mock_exists.return_value = True

        result = self.service.detect_admin_tool("C:\\SAPServer")
        self.assertIsNotNone(result)
        # It should check Setup/NwSapSetupAdmin.exe first
        self.assertTrue("NwSapSetupAdmin.exe" in str(result))

    @patch('switchcraft.utils.shell_utils.ShellUtils.run_command')
    @patch('switchcraft.services.sap_service.SapService.detect_admin_tool')
    def test_merge_update_success(self, mock_detect, mock_run):
        mock_detect.return_value = Path("C:\\SAPServer\\Setup\\NwSapSetupAdmin.exe")
        mock_run.return_value = MagicMock(returncode=0)

        result = self.service.merge_update("C:\\SAPServer", "C:\\Update.exe")
        self.assertTrue(result)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("/UpdateServer", args)
        # Use substring check to avoid path separator issues
        self.assertTrue(any("C:\\SAPServer" in a or "C:/SAPServer" in a for a in args))

    @patch('xml.etree.ElementTree.parse')
    @patch('pathlib.Path.exists')
    @patch('os.path.exists')
    @patch('shutil.copy')
    def test_customize_server(self, mock_copy, mock_os_exists, mock_path_exists, mock_xml_parse):
        mock_path_exists.return_value = True
        mock_os_exists.return_value = True

        # Mock XML structure correctly
        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_param = MagicMock()
        mock_param.get.return_value = 'UseWebView2'

        # Mocking root.iter to return our param
        mock_root.iter.return_value = [mock_param]
        mock_tree.getroot.return_value = mock_root
        mock_xml_parse.return_value = mock_tree

        result = self.service.customize_server("C:\\SAPServer", "C:\\logo.png", True)
        self.assertTrue(result)
        mock_param.set.assert_called_with('Value', '1')
        mock_tree.write.assert_called_once()

    @patch('switchcraft.utils.shell_utils.ShellUtils.run_command')
    @patch('switchcraft.services.sap_service.SapService.detect_admin_tool')
    def test_create_single_file_installer(self, mock_detect, mock_run):
        mock_detect.return_value = Path("C:\\SAPServer\\Setup\\NwSapSetupAdmin.exe")
        mock_run.return_value = MagicMock(returncode=0)

        result = self.service.create_single_file_installer("C:\\SAPServer", "Package1", "C:\\Output.exe")
        self.assertEqual(result, "C:\\Output.exe")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        # Implementation now wraps command in a .bat file
        self.assertTrue(str(args[0]).endswith('.bat'), f"Expected a batch file argument, got: {args}")

if __name__ == '__main__':
    unittest.main()
