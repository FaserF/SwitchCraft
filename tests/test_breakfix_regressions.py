"""
Regression tests for recent break-fixes:
1. Group Manager View: Dialog opening logic and threading safety.
2. Addon Service: Manifest discovery (recursive, case-insensitive).
"""
import pytest
from unittest.mock import MagicMock, patch
import tempfile
import zipfile
import shutil
from pathlib import Path
import flet as ft

# --- Group Manager Tests ---

def test_group_manager_show_members_no_selection():
    """Test that _show_members_dialog gracefully handles no selection."""
    from switchcraft.gui_modern.views.group_manager_view import GroupManagerView

    # Mock page and view
    mock_page = MagicMock()
    mock_page.snack_bar = MagicMock()

    with patch('switchcraft.gui_modern.views.group_manager_view.GroupManagerView._has_credentials', return_value=True):
        view = GroupManagerView(mock_page)

        # Setup state: No selection
        view.selected_group = None
        view.token = "test_token"

        # Track logging and dialog opening
        with patch('switchcraft.gui_modern.views.group_manager_view.logger') as mock_logger, \
             patch('switchcraft.gui_modern.views.group_manager_view.GroupManagerView._open_dialog_safe') as mock_open:

            view._show_members_dialog(None)

            # Assertions
            mock_logger.warning.assert_called_with("Cannot show members dialog: no group selected")
            # Should NOT try to open dialog
            mock_open.assert_not_called()

def test_group_manager_show_members_no_token():
    """Test that _show_members_dialog gracefully handles missing token."""
    from switchcraft.gui_modern.views.group_manager_view import GroupManagerView

    mock_page = MagicMock()

    with patch('switchcraft.gui_modern.views.group_manager_view.GroupManagerView._has_credentials', return_value=True):
        view = GroupManagerView(mock_page)

        # Setup state: Selection but no token
        view.selected_group = {'id': '123', 'displayName': 'Test Group'}
        view.token = None

        with patch('switchcraft.gui_modern.views.group_manager_view.logger') as mock_logger:
            view._show_members_dialog(None)

            mock_logger.warning.assert_called_with("Cannot show members dialog: no token")

def test_group_manager_show_members_success():
    """Test successful opening of members dialog."""
    from switchcraft.gui_modern.views.group_manager_view import GroupManagerView

    mock_page = MagicMock()
    mock_page.dialog = None

    # Mock _open_dialog_safe to simulate success
    with patch('switchcraft.gui_modern.views.group_manager_view.GroupManagerView._has_credentials', return_value=True), \
         patch('switchcraft.gui_modern.views.group_manager_view.GroupManagerView._open_dialog_safe', return_value=True) as mock_open:

        view = GroupManagerView(mock_page)
        view.token = "test_token"
        view.selected_group = {'id': '123', 'displayName': 'Test Group'}

        # Mock background thread starting
        with patch('threading.Thread.start'):
            view._show_members_dialog(None)

            # Assertions
            mock_open.assert_called_once()
            # args[0] should be the dialog
            assert isinstance(mock_open.call_args[0][0], ft.AlertDialog)


# --- Addon Service Tests ---

@pytest.fixture
def temp_addon_structure():
    """Create a temp directory for addon testing."""
    tmp_dir = tempfile.mkdtemp()
    yield Path(tmp_dir)
    shutil.rmtree(tmp_dir)

def create_zip_with_files(zip_path, file_dict):
    """Helper to create a zip file with specific content structure."""
    with zipfile.ZipFile(zip_path, 'w') as z:
        for path, content in file_dict.items():
            z.writestr(path, content)

def test_install_addon_root_manifest(temp_addon_structure):
    """Test installing an addon with manifest.json at the root."""
    from switchcraft.services.addon_service import AddonService

    service = AddonService()
    service.addons_dir = temp_addon_structure / "installed_addons"
    service.addons_dir.mkdir()

    zip_path = temp_addon_structure / "test_addon.zip"
    manifest_content = '{"id": "test_root", "version": "1.0", "name": "Test Root"}'

    create_zip_with_files(zip_path, {
        "manifest.json": manifest_content,
        "script.py": "print('hello')"
    })

    success = service.install_addon(str(zip_path))
    assert success
    assert (service.addons_dir / "test_root" / "manifest.json").exists()
    assert (service.addons_dir / "test_root" / "script.py").exists()

def test_install_addon_nested_manifest(temp_addon_structure):
    """Test installing an addon with manifest.json in a subdirectory."""
    from switchcraft.services.addon_service import AddonService

    service = AddonService()
    service.addons_dir = temp_addon_structure / "installed_addons"
    service.addons_dir.mkdir()

    zip_path = temp_addon_structure / "test_nested.zip"
    manifest_content = '{"id": "test_nested", "version": "1.0", "name": "Test Nested"}'

    # Structure: folder/manifest.json
    create_zip_with_files(zip_path, {
        "my_addon/manifest.json": manifest_content,
        "my_addon/lib/utils.py": "pass"
    })

    success = service.install_addon(str(zip_path))
    assert success
    # Should flatten: manifest should be at root of installed dir
    assert (service.addons_dir / "test_nested" / "manifest.json").exists()
    assert (service.addons_dir / "test_nested" / "lib" / "utils.py").exists()

def test_install_addon_deep_nested_manifest(temp_addon_structure):
    """Test installing an addon with manifest.json deep in hierarchy."""
    from switchcraft.services.addon_service import AddonService

    service = AddonService()
    service.addons_dir = temp_addon_structure / "installed_addons"
    service.addons_dir.mkdir()

    zip_path = temp_addon_structure / "test_deep.zip"
    manifest_content = '{"id": "test_deep", "version": "1.0", "name": "Test Deep"}'

    # Structure: depth1/depth2/depth3/manifest.json
    create_zip_with_files(zip_path, {
        "a/b/c/manifest.json": manifest_content,
        "a/b/c/data.txt": "data"
    })

    success = service.install_addon(str(zip_path))
    assert success
    assert (service.addons_dir / "test_deep" / "manifest.json").exists()

def test_install_addon_case_insensitive_manifest(temp_addon_structure):
    """Test installing an addon with mixed case filenames (MANIFEST.JSON)."""
    from switchcraft.services.addon_service import AddonService

    service = AddonService()
    service.addons_dir = temp_addon_structure / "installed_addons"
    service.addons_dir.mkdir()

    zip_path = temp_addon_structure / "test_case.zip"
    manifest_content = '{"id": "test_case", "version": "1.0", "name": "Test Case"}'

    create_zip_with_files(zip_path, {
        "Folder/MANIFEST.JSON": manifest_content
    })

    success = service.install_addon(str(zip_path))
    assert success
    # Note: extracted filename case depends on OS/Zip extraction, but we care that it was found
    # Our extraction logic preserves original filename case from zip member
    # So we check if the directory was created (ID extracted correctly)
    assert (service.addons_dir / "test_case").exists()
    # Check if a manifest file exists regardless of exact case
    files = list((service.addons_dir / "test_case").iterdir())
    assert any(f.name.lower() == "manifest.json" for f in files)

def test_install_addon_missing_manifest(temp_addon_structure):
    """Test failure when no manifest exists."""
    from switchcraft.services.addon_service import AddonService

    service = AddonService()
    service.addons_dir = temp_addon_structure / "installed_addons"
    service.addons_dir.mkdir()

    zip_path = temp_addon_structure / "test_bad.zip"

    create_zip_with_files(zip_path, {
        "random.txt": "hello"
    })

    with pytest.raises(Exception) as excinfo:
        service.install_addon(str(zip_path))

    assert "Invalid addon: manifest.json not found" in str(excinfo.value)
    assert "random.txt" in str(excinfo.value) # Check that it lists files
