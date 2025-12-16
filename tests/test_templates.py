
import unittest
import tempfile
import shutil
import os
from pathlib import Path
from switchcraft.utils.templates import TemplateGenerator

# Mock context
CONTEXT = {
    "INSTALLER_FILE": "setup.exe",
    "INSTALL_ARGS": "/S /v/qn",
    "APP_NAME": "MyApp",
    "PUBLISHER": "MyCompany"
}

class TestTemplateGenerator(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)

    def test_default_template_loading(self):
        """Test that default template loads if no custom path is provided."""
        gen = TemplateGenerator()
        self.assertEqual(gen.template_path, gen.DEFAULT_TEMPLATE_PATH)
        self.assertFalse(gen.is_custom)

    def test_basic_replacement(self):
        """Test simple placeholder replacement."""
        gen = TemplateGenerator()
        # Mock template content to avoid dependency on actual asset file
        gen.template_content = "Run {{INSTALLER_FILE}} with {{INSTALL_ARGS}}."

        output_file = self.test_path / "output.ps1"
        gen.generate(CONTEXT, str(output_file))

        content = output_file.read_text()
        self.assertIn("Run setup.exe with /S /v/qn.", content)

    def test_custom_template_loading(self):
        """Test loading a custom template."""
        custom_tmpl = self.test_path / "custom.ps1"
        custom_tmpl.write_text("Custom {{APP_NAME}} logic.", encoding='utf-8')

        gen = TemplateGenerator(str(custom_tmpl))
        self.assertTrue(gen.is_custom)

        output_file = self.test_path / "output_custom.ps1"
        gen.generate(CONTEXT, str(output_file))

        content = output_file.read_text(encoding='utf-8')
        self.assertIn("Custom MyApp logic.", content)

    def test_enterprise_regex_replacement(self):
        """Test the smart regex replacement for Enterprise-style templates."""
        # This simulates the specific logic in the user's Enterprise template
        # Updated to match the new detection logic (Start-Process-Function)
        enterprise_content = '''
        $Installer = Join-Path -Path $PSScriptRoot -ChildPath "old_installer.exe"
        $Arguments = "/old /args"
        Start-Process-Function -FilePath $Installer -ArgumentList $Arguments
        Uninstall-SoftwareByFilter -NameFilter "Test"
        '''

        gen = TemplateGenerator()
        gen.template_content = enterprise_content

        output_file = self.test_path / "enterprise_output.ps1"
        gen.generate(CONTEXT, str(output_file))

        content = output_file.read_text(encoding='utf-8')

        # Check that $Installer was updated
        self.assertIn('$Installer = Join-Path -Path $PSScriptRoot -ChildPath "setup.exe"', content)
        # Check that $Arguments was updated
        self.assertIn('$Arguments = "/S /v/qn"', content)

if __name__ == '__main__':
    unittest.main()
