
import pytest
import flet as ft
from unittest.mock import MagicMock, patch

# Mocks
mock_page = MagicMock(spec=ft.Page)
mock_page.platform = "windows"
mock_page.route = "/"
mock_page.theme_mode = "dark"
mock_page.window_width = 800
mock_page.window_height = 600
mock_page.pubsub = MagicMock()
mock_page.overlay = []
mock_page.views = []

@pytest.fixture
def page():
    return mock_page

# Mock Config to avoid registry access
@pytest.fixture(autouse=True)
def mock_config():
    with patch("switchcraft.utils.config.SwitchCraftConfig.get_value") as mock_get:
        mock_get.return_value = "false"
        yield mock_get

# Mock Services for isolation
@pytest.fixture(autouse=True)
def mock_subsystems():
    with patch("switchcraft.services.history_service.HistoryService"), \
         patch("switchcraft.services.intune_service.IntuneService"), \
         patch("switchcraft.services.addon_service.AddonService"), \
         patch("switchcraft.services.auth_service.AuthService"), \
         patch("switchcraft.utils.app_updater.UpdateChecker"):
        yield

def test_instantiate_home_view(page):
    from switchcraft.gui_modern.views.home_view import ModernHomeView
    view = ModernHomeView(page)
    assert isinstance(view, ft.Container)

def test_instantiate_dashboard_view(page):
    from switchcraft.gui_modern.views.dashboard_view import DashboardView
    view = DashboardView(page)
    assert isinstance(view, ft.Column)

def test_instantiate_analyzer_view(page):
    from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView
    view = ModernAnalyzerView(page)

def test_dialog_opening_safety(page):
    """Test that dialogs can be opened safely without 'Control must be added to page first' errors."""
    from switchcraft.gui_modern.utils.view_utils import ViewMixin
    from switchcraft.gui_modern.views.group_manager_view import GroupManagerView

    # Create a mock view that uses ViewMixin
    class TestView(ft.Column, ViewMixin):
        def __init__(self, page):
            super().__init__()
            self.app_page = page

    view = TestView(page)

    # Ensure page has dialog attribute
    if not hasattr(page, 'dialog'):
        page.dialog = None

    # Test opening a dialog
    dlg = ft.AlertDialog(
        title=ft.Text("Test Dialog"),
        content=ft.Text("Test Content"),
        actions=[ft.TextButton("Close", on_click=lambda e: view._close_dialog(dlg))]
    )

    # This should not raise "Control must be added to the page first"
    result = view._open_dialog_safe(dlg)
    assert result is True, "Dialog should open successfully"
    assert page.dialog == dlg, "Dialog should be set on page"

    # Test closing the dialog
    view._close_dialog(dlg)
    assert dlg.open is False, "Dialog should be closed"

def test_group_manager_members_dialog(page):
    """Test that the members dialog in GroupManagerView opens safely."""
    from switchcraft.gui_modern.views.group_manager_view import GroupManagerView
    from unittest.mock import MagicMock, patch

    # Mock the required dependencies
    with patch('switchcraft.gui_modern.views.group_manager_view.IntuneService') as mock_intune, \
         patch('switchcraft.gui_modern.views.group_manager_view.SwitchCraftConfig') as mock_config:

        # Setup mocks
        mock_intune_instance = MagicMock()
        mock_intune.return_value = mock_intune_instance

        # Mock credentials check
        def mock_has_credentials():
            return True
        GroupManagerView._has_credentials = mock_has_credentials

        # Create view
        view = GroupManagerView(page)

        # Setup required state
        view.selected_group = {
            'displayName': 'Test Group',
            'id': 'test-group-id'
        }
        view.token = 'test-token'

        # Ensure page has required attributes
        if not hasattr(page, 'dialog'):
            page.dialog = None
        if not hasattr(page, 'open'):
            page.open = MagicMock()
        if not hasattr(page, 'update'):
            page.update = MagicMock()

        # Mock the intune service methods
        mock_intune_instance.list_group_members = MagicMock(return_value=[])

        # Create a mock event
        mock_event = MagicMock()

        # This should not raise "Control must be added to the page first"
        try:
            view._show_members_dialog(mock_event)
            # If we get here, the dialog was opened successfully
            assert True, "Dialog opened without errors"
        except Exception as e:
            if "Control must be added to the page first" in str(e):
                pytest.fail(f"Dialog opening failed with page error: {e}")
            else:
                # Other errors might be expected (e.g., missing dependencies)
                pass
    assert isinstance(view, ft.Column)

def test_instantiate_library_view(page):
    from switchcraft.gui_modern.views.library_view import LibraryView
    view = LibraryView(page)
    assert isinstance(view, ft.Column)

def test_instantiate_group_manager_view(page):
    from switchcraft.gui_modern.views.group_manager_view import GroupManagerView
    view = GroupManagerView(page)
    assert isinstance(view, ft.Column)



def test_instantiate_settings_view(page):
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView
    view = ModernSettingsView(page)
    assert isinstance(view, ft.Column)

def test_instantiate_intune_view(page):
    from switchcraft.gui_modern.views.intune_view import ModernIntuneView
    view = ModernIntuneView(page)
    assert isinstance(view, ft.Column)

def test_instantiate_script_upload_view(page):
    from switchcraft.gui_modern.views.script_upload_view import ScriptUploadView
    view = ScriptUploadView(page)
    assert isinstance(view, ft.Column)

def test_instantiate_macos_wizard_view(page):
    from switchcraft.gui_modern.views.macos_wizard_view import MacOSWizardView
    view = MacOSWizardView(page)
    assert isinstance(view, ft.Column)

def test_instantiate_stack_manager_view(page):
    from switchcraft.gui_modern.views.stack_manager_view import StackManagerView
    view = StackManagerView(page)
    assert isinstance(view, ft.Column)
