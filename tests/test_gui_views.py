
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
