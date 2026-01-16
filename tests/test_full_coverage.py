import pytest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
from switchcraft.services.winget_manifest_service import WingetManifestService
from switchcraft.services.intune_service import IntuneService
from switchcraft.services.addon_service import AddonService
from switchcraft.utils.config import SwitchCraftConfig

# --- Winget Manifest Service Tests ---

@pytest.fixture
def manifest_service():
    return WingetManifestService()

def test_manifest_generation(manifest_service, tmp_path):
    """Test standard manifest generation logic."""
    meta = {
        "PackageIdentifier": "Test.App",
        "PackageVersion": "1.0.0",
        "Publisher": "TestPub",
        "PackageName": "App",
        "License": "MIT",
        "ShortDescription": "A test app",
        "InstallerType": "exe",
        "Installers": [{"InstallerUrl": "http://test.com", "InstallerSha256": "ABC", "InstallerType": "exe"}],
        "DefaultLocale": "en-US"
    }

    output_dir = tmp_path / "repo"
    manifest_dir = manifest_service.generate_manifests(meta, output_base_dir=str(output_dir))

    manifest_path = Path(manifest_dir)
    assert manifest_path.exists()
    assert (manifest_path / "Test.App.yaml").exists() # Version
    assert (manifest_path / "Test.App.installer.yaml").exists() # Installer
    assert (manifest_path / "Test.App.locale.en-US.yaml").exists() # Locale

@patch("subprocess.run")
def test_manifest_validation(mock_run, manifest_service, tmp_path):
    """Test validation calls winget correctly."""
    mock_run.return_value = MagicMock(stdout="Manifest validation success", stderr="", returncode=0)

    res = manifest_service.validate_manifest(str(tmp_path))
    assert res["valid"] is True
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "winget" in args and "validate" in args

# --- Intune Service Tests ---

@pytest.fixture
def intune_service():
    return IntuneService()

@patch("switchcraft.services.intune_service.IntuneService.is_tool_available", return_value=True)
@patch("subprocess.Popen")
def test_intune_packaging(mock_popen, mock_is_avail, intune_service, tmp_path):
    """Test IntuneWin generation command."""
    setup_file = tmp_path / "setup.exe"
    setup_file.touch()
    out_dir = tmp_path / "out"

    # Setup Popen mock to return success
    process_mock = MagicMock()
    process_mock.stdout = ["Output line 1\n", "Output line 2\n"]
    process_mock.returncode = 0
    process_mock.wait.return_value = None
    mock_popen.return_value = process_mock

    # Correct args: source_folder, setup_file, output_folder
    res = intune_service.create_intunewin(str(tmp_path), str(setup_file), str(out_dir))

    # IntuneService returns joined output on success
    assert "Output line 1" in res

    # Verify subprocess called with correct args
    mock_popen.assert_called()
    cmd = mock_popen.call_args[0][0]
    # Cmd is list: [tool_path, -c, source, -s, setup, -o, out, -q]
    assert "-c" in cmd
    assert "-s" in cmd
    assert "-o" in cmd

# --- Config Tests ---

def test_config_defaults():
    """Ensure sensitive defaults are safe."""
    # Mocking behaviors usually required, testing core logic
    assert SwitchCraftConfig.get_value("NonExistent", "Default") == "Default"

# --- Addon Service Tests ---

@patch("winreg.OpenKey")
@pytest.mark.skipif(sys.platform != "win32", reason="winreg only on Windows")
def test_addon_detection(mock_open_key):
    pytest.importorskip("winreg")
    """Test registry detection for advanced addon."""
    # This is tricky to test on non-windows or without registry,
    # but we can verify it doesn't crash on import/usage
    assert not AddonService().is_addon_installed("fake_addon")

# --- Legacy/Modern Entry Point Safety ---

def test_entry_points_import():
    """Ensure entry points can at least check dependencies without crashing."""
    try:
        import switchcraft.modern_main
    except ImportError:
        # Flet might be missing in test env, which is 'valid' but we catch it
        pytest.skip("Flet not installed")
    except Exception as e:
        pytest.fail(f"Modern main raised exception on import: {e}")
