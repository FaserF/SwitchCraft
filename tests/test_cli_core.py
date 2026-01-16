import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from switchcraft.cli.commands import cli
from switchcraft import __version__

class TestCliCore(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_version_flag(self):
        """Test that --version flag outputs the correct version."""
        result = self.runner.invoke(cli, ['--version'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn(f"SwitchCraft v{__version__}", result.output)

    @patch('switchcraft.utils.config.SwitchCraftConfig.get_value')
    def test_config_get(self, mock_get):
        """Test 'config get' command."""
        mock_get.return_value = "TestValue"
        result = self.runner.invoke(cli, ['config', 'get', 'SomeKey'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("SomeKey: TestValue", result.output)
        mock_get.assert_called_with("SomeKey")

    @patch('switchcraft.utils.config.SwitchCraftConfig.set_user_preference')
    def test_config_set(self, mock_set):
        """Test 'config set' command."""
        result = self.runner.invoke(cli, ['config', 'set', 'SomeKey', 'NewVal'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Set SomeKey = NewVal", result.output)
        mock_set.assert_called_with("SomeKey", "NewVal")

    @patch('switchcraft.utils.config.SwitchCraftConfig.set_secret')
    def test_config_set_secret(self, mock_set_secret):
        """Test 'config set-secret' command with interactive input."""
        # Now prompts for value if not provided via --value
        result = self.runner.invoke(cli, ['config', 'set-secret', 'MySecret'], input='HiddenVal')
        self.assertEqual(result.exit_code, 0)
        # Output likely contains "Secret value: " prompt which is hidden in output usually but check exit code
        self.assertIn("Secret MySecret saved securely.", result.output)
        mock_set_secret.assert_called_with("MySecret", "HiddenVal")

    @patch('switchcraft.cli.commands._run_analysis')
    def test_analyze_delegation(self, mock_run):
        """Test that 'analyze' subcommand delegates to internal logic."""
        with self.runner.isolated_filesystem():
            with open('test_installer.msi', 'w') as f:
                f.write('dummy')

            result = self.runner.invoke(cli, ['analyze', 'test_installer.msi'])
            self.assertEqual(result.exit_code, 0)
            mock_run.assert_called_once()
            # args passed to _run_analysis are (filepath, output_json)
            # click passes absolute path or relative?
            # actually mock_run call args check:
            args, _ = mock_run.call_args
            self.assertTrue(str(args[0]).endswith('test_installer.msi'))
            self.assertFalse(args[1]) # json flag false by default

    @patch('switchcraft.cli.commands.MsiAnalyzer')
    def test_run_analysis_internal(self, MockMsi):
        """Test the _run_analysis helper logic via the command (integration-ish)."""
        # Setup Mock Analyzer
        mock_instance = MockMsi.return_value
        mock_instance.can_analyze.return_value = True

        mock_info = MagicMock()
        mock_info.installer_type = "MSI"
        mock_info.product_name = "MockApp"
        mock_info.product_version = "1.0.0"
        mock_info.confidence = 0.9
        mock_info.file_path = "test.msi"
        mock_info.install_switches = ["/quiet"]
        mock_instance.analyze.return_value = mock_info

        # Run command
        with self.runner.isolated_filesystem():
            with open('test.msi', 'w') as f:
                f.write('dummy')

            result = self.runner.invoke(cli, ['analyze', 'test.msi'])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("SwitchCraft Analysis Result", result.output)
            self.assertIn("MockApp", result.output)
            self.assertIn("MSI", result.output)

    @patch('switchcraft.services.addon_service.AddonService.install_addon')
    def test_addon_install(self, mock_install):
        """Test addon install command."""
        mock_install.return_value = True
        # We need to simulate a valid addon ID or mock the ADDONS dict
        # with patch('switchcraft.services.addon_service.AddonService.ADDONS', {"test_addon": "pkg"}):
        result = self.runner.invoke(cli, ['addons', 'install', 'test_addon'])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Successfully installed test_addon", result.output)
        mock_install.assert_called_with("test_addon")

if __name__ == '__main__':
    unittest.main()
