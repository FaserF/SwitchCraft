
import pytest
import flet as ft
from unittest.mock import MagicMock, patch
import logging

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

def test_instantiate_home_view(page):
    from switchcraft.gui_modern.views.home_view import ModernHomeView
    view = ModernHomeView(page)
    assert isinstance(view, ft.Container)

def test_instantiate_dashboard_view(page):
    from switchcraft.gui_modern.views.dashboard_view import DashboardView
    try:
        view = DashboardView(page)
    except Exception as e:
        pytest.fail(f"DashboardView init failed: {e}")

def test_instantiate_analyzer_view(page):
    from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView
    try:
        view = ModernAnalyzerView(page)
    except Exception as e:
        pytest.fail(f"AnalyzerView init failed: {e}")

def test_instantiate_library_view(page):
    from switchcraft.gui_modern.views.library_view import LibraryView
    try:
        view = LibraryView(page)
    except Exception as e:
        pytest.fail(f"LibraryView init failed: {e}")

def test_instantiate_group_manager_view(page):
    from switchcraft.gui_modern.views.group_manager_view import GroupManagerView
    try:
         view = GroupManagerView(page)
    except Exception as e:
        pytest.fail(f"GroupManagerView init failed: {e}")

def test_instantiate_addon_manager_view(page):
    from switchcraft.gui_modern.views.addon_manager_view import AddonManagerView
    try:
        view = AddonManagerView(page)
    except Exception as e:
        pytest.fail(f"AddonManagerView init failed: {e}")

def test_instantiate_settings_view(page):
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView
    try:
        view = ModernSettingsView(page)
    except Exception as e:
        pytest.fail(f"SettingsView init failed: {e}")

def test_instantiate_intune_view(page):
    from switchcraft.gui_modern.views.intune_view import ModernIntuneView
    try:
        view = ModernIntuneView(page)
    except Exception as e:
        pytest.fail(f"IntuneView init failed: {e}")

def test_instantiate_script_upload_view(page):
    from switchcraft.gui_modern.views.script_upload_view import ScriptUploadView
    try:
        view = ScriptUploadView(page)
    except Exception as e:
        pytest.fail(f"ScriptUploadView init failed: {e}")

def test_instantiate_macos_wizard_view(page):
    from switchcraft.gui_modern.views.macos_wizard_view import MacOSWizardView
    try:
        view = MacOSWizardView(page)
    except Exception as e:
        pytest.fail(f"MacOSWizardView init failed: {e}")

def test_instantiate_stack_manager_view(page):
    from switchcraft.gui_modern.views.stack_manager_view import StackManagerView
    try:
        view = StackManagerView(page)
    except Exception as e:
        pytest.fail(f"StackManagerView init failed: {e}")
