
import pytest
from pathlib import Path
from switchcraft.utils.templates import TemplateGenerator

# Mock context
CONTEXT = {
    "INSTALLER_FILE": "setup.exe",
    "INSTALL_ARGS": "/S /v/qn",
    "APP_NAME": "MyApp",
    "PUBLISHER": "MyCompany"
}

def test_default_template_loading():
    """Test that default template loads if no custom path is provided."""
    gen = TemplateGenerator()
    assert gen.template_path == gen.DEFAULT_TEMPLATE_PATH
    assert not gen.is_custom

def test_basic_replacement(tmp_path):
    """Test simple placeholder replacement."""
    gen = TemplateGenerator()
    # Mock template content to avoid dependency on actual asset file
    gen.template_content = "Run {{INSTALLER_FILE}} with {{INSTALL_ARGS}}."

    output_file = tmp_path / "output.ps1"
    gen.generate(CONTEXT, str(output_file))

    content = output_file.read_text()
    assert "Run setup.exe with /S /v/qn." in content

def test_custom_template_loading(tmp_path):
    """Test loading a custom template."""
    custom_tmpl = tmp_path / "custom.ps1"
    custom_tmpl.write_text("Custom {{APP_NAME}} logic.")

    gen = TemplateGenerator(str(custom_tmpl))
    assert gen.template_content == "Custom {{APP_NAME}} logic."

    output_file = tmp_path / "output_custom.ps1"
    gen.generate(CONTEXT, str(output_file))

    content = output_file.read_text()
    assert "Custom MyApp logic." in content

def test_pari_regex_replacement(tmp_path):
    """Test the smart regex replacement for PARI-style templates."""
    # This simulates the specific logic in the user's PARI template
    pari_content = '''
    $Installer = Join-Path -Path $PSScriptRoot -ChildPath "old_installer.exe"
    $Arguments = "/old /args"
    Start-Process-Function -FilePath $Installer -ArgumentList $Arguments
    Uninstall-SoftwareByFilter -NameFilter "Test"
    '''

    gen = TemplateGenerator()
    gen.template_content = pari_content

    output_file = tmp_path / "pari_output.ps1"
    gen.generate(CONTEXT, str(output_file))

    content = output_file.read_text()

    # Check that $Installer was updated
    assert '$Installer = "setup.exe"' in content
    # Check that $Arguments was updated
    assert '$Arguments = "/S /v/qn"' in content
