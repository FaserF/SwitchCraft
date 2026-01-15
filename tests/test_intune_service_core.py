import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from switchcraft.services.intune_service import IntuneService


class TestIntuneServiceCore(unittest.TestCase):
    def setUp(self):
        self.service = IntuneService()

    def test_intune_service_initialization(self):
        """Test that IntuneService initializes correctly."""
        self.assertIsNotNone(self.service)
        self.assertIsNotNone(self.service.tool_path)
        self.assertIsNotNone(self.service.tools_dir)

    def test_is_tool_available(self):
        """Test checking if IntuneWinAppUtil is available."""
        # This will check if the tool exists at the default path
        result = self.service.is_tool_available()
        self.assertIsInstance(result, bool)

    @patch('pathlib.Path.exists')
    def test_is_tool_available_mock(self, mock_exists):
        """Test is_tool_available with mocked path."""
        mock_exists.return_value = True
        result = self.service.is_tool_available()
        self.assertTrue(result)

    def test_tool_path_construction(self):
        """Test that tool path is constructed correctly."""
        self.assertEqual(self.service.tool_path.name, "IntuneWinAppUtil.exe")
        self.assertEqual(self.service.tool_path.parent, self.service.tools_dir)

    @patch('requests.get')
    @patch('pathlib.Path.mkdir')
    @patch('os.stat')
    @patch('os.chmod')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_tool_mock(self, mock_file, mock_chmod, mock_stat, mock_mkdir, mock_get):
        """Test downloading IntuneWinAppUtil with mocked requests."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b'fake', b'content']
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Mock os.stat to return a mock stat object
        mock_stat_obj = MagicMock()
        mock_stat_obj.st_mode = 0o644
        mock_stat.return_value = mock_stat_obj

        result = self.service.download_tool()
        self.assertTrue(result)
        mock_get.assert_called_once()

    def test_create_intunewin_requires_tool(self):
        """Test that create_intunewin requires the tool to be available."""
        # If tool is not available and download fails, should raise FileNotFoundError
        with patch.object(self.service, 'is_tool_available', return_value=False), \
             patch.object(self.service, 'download_tool', return_value=False):
            with self.assertRaises(FileNotFoundError):
                self.service.create_intunewin(
                    "C:\\test\\source",
                    "setup.exe",
                    "C:\\test\\output"
                )


if __name__ == '__main__':
    unittest.main()
