
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from switchcraft.services.intune_service import IntuneService
from switchcraft.services.notification_service import NotificationService

class TestPhase4Features(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.intune_service = IntuneService(tools_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_notification_service_init(self):
        """Test NotificationService handles missing plyer gracefully."""
        # We can't easily test the visual notification, but we can call the method
        try:
            NotificationService().add_notification("Test Title", "Test Message")
            self.assertTrue(True) # Should not raise exception
        except Exception as e:
            self.fail(f"NotificationService raised exception: {e}")

    @patch('switchcraft.services.intune_service.requests.get')
    def test_intune_download(self, mock_get):
        """Test downloading the Intune tool."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"fake_exe_content"]
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Ensure tool path doesn't exist
        self.assertFalse(self.intune_service.is_tool_available())

        # Mock successful download
        success = self.intune_service.download_tool()
        self.assertTrue(success)
        self.assertTrue(self.intune_service.is_tool_available())

        # Verify content
        with open(self.intune_service.tool_path, 'rb') as f:
            self.assertEqual(f.read(), b"fake_exe_content")

    @patch('switchcraft.services.intune_service.subprocess.Popen')
    def test_create_intunewin(self, mock_popen):
        """Test creating .intunewin package."""
        # Create dummy setup file
        setup_file = Path(self.test_dir) / "setup.exe"
        setup_file.touch()

        # Create dummy tool
        (Path(self.test_dir) / "IntuneWinAppUtil.exe").touch()

        # Mock Popen return value (process)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = ["Package created\n"] # Iterable
        mock_proc.wait.return_value = None
        mock_popen.return_value = mock_proc

        output_dir = Path(self.test_dir) / "output"

        result = self.intune_service.create_intunewin(
            source_folder=str(self.test_dir),
            setup_file="setup.exe",
            output_folder=str(output_dir)
        )

        self.assertIn("Package created", result)
        mock_popen.assert_called_once()
