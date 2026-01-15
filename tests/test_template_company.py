import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from switchcraft.utils.templates import TemplateGenerator

class TestTemplateWithCompany(unittest.TestCase):
    def setUp(self):
        self.output_path = Path("test_output.ps1")

    def tearDown(self):
        """
        Remove the test output file if it exists.
        
        If the configured output path exists, attempt to delete it. On a PermissionError (e.g., file temporarily locked) the method waits 0.1 seconds and retries once; any PermissionError or FileNotFoundError on the retry is ignored.
        """
        if self.output_path.exists():
            try:
                self.output_path.unlink()
            except PermissionError:
                # File might still be open, try again after a short delay
                import time
                time.sleep(0.1)
                try:
                    self.output_path.unlink()
                except (PermissionError, FileNotFoundError):
                    pass  # File was deleted or still locked, skip

    @patch("switchcraft.utils.config.SwitchCraftConfig.get_value")
    @patch("switchcraft.utils.config.SwitchCraftConfig.get_company_name")
    @patch("os.environ.get")
    def test_generate_with_company_name(self, mock_env, mock_get_company, mock_get_value):
        # Setup Mocks
        mock_get_company.return_value = "SwitchCraft Corp"
        mock_env.return_value = "TestUser"
        # Ensure 'CustomTemplatePath' returns None so default template is used
        mock_get_value.return_value = None

        generator = TemplateGenerator()

        context = {
            "INSTALLER_FILE": "setup.exe",
            "INSTALL_ARGS": "/S",
            "APP_NAME": "TestApp",
            "PUBLISHER": "TestPub"
        }

        success = generator.generate(context, str(self.output_path))
        self.assertTrue(success)

        content = self.output_path.read_text(encoding="utf-8")

        # Should contain full header
        self.assertIn('company "SwitchCraft Corp"', content)
        self.assertIn('Created by "TestUser"', content)
        self.assertIn('with SwitchCraft automatically', content)

    @patch("switchcraft.utils.config.SwitchCraftConfig.get_value")
    @patch("switchcraft.utils.config.SwitchCraftConfig.get_company_name")
    @patch("os.environ.get")
    def test_generate_without_company_name(self, mock_env, mock_get_company, mock_get_value):
        # Setup Mocks
        mock_get_company.return_value = "" # No company
        mock_env.return_value = "TestUser"
        # Ensure 'CustomTemplatePath' returns None
        mock_get_value.return_value = None

        generator = TemplateGenerator()
        context = { "INSTALLER_FILE": "setup.exe", "INSTALL_ARGS": "/S" }

        success = generator.generate(context, str(self.output_path))
        self.assertTrue(success)

        content = self.output_path.read_text(encoding="utf-8")

        # Should NOT contain "company" string in header
        self.assertNotIn('company "', content)
        # Should contain simpler header
        self.assertIn('Created by "TestUser" with SwitchCraft automatically', content)

if __name__ == "__main__":
    unittest.main()