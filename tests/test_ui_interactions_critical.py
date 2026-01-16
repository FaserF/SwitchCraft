"""
Tests for critical UI interaction features:
- GitHub OAuth login dialog functionality
- Language change and UI refresh
- Notification drawer toggle
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch, Mock
import threading
import time
import os

@pytest.fixture
def mock_page():
    """Create a mock Flet page with all necessary attributes."""
    page = MagicMock(spec=ft.Page)
    page.dialog = None
    page.end_drawer = None
    page.update = MagicMock()
    page.snack_bar = MagicMock(spec=ft.SnackBar)
    page.snack_bar.open = False
    
    # Mock app reference
    mock_app = MagicMock()
    mock_app._current_tab_index = 0
    mock_app._view_cache = {}
    mock_app.goto_tab = MagicMock()
    page.switchcraft_app = mock_app
    
    # Mock run_task to actually execute the function
    def run_task(func):
        func()
    page.run_task = run_task
    
    # Mock page.open to set dialog and open it
    def mock_open(control):
        if isinstance(control, ft.AlertDialog):
            page.dialog = control
            control.open = True
        elif isinstance(control, ft.NavigationDrawer):
            page.end_drawer = control
            control.open = True
        page.update()
    page.open = mock_open
    
    return page


@pytest.fixture
def mock_auth_service():
    """Mock AuthService responses."""
    with patch('switchcraft.gui_modern.views.settings_view.AuthService') as mock:
        mock_service = MagicMock()
        mock.initiate_device_flow.return_value = {
            "device_code": "test_code",
            "user_code": "ABC-123",
            "verification_uri": "https://github.com/login/device",
            "interval": 5,
            "expires_in": 900
        }
        mock.poll_for_token.return_value = "test_token_123"
        mock.save_token = MagicMock()
        mock_service.initiate_device_flow = mock.initiate_device_flow
        mock_service.poll_for_token = mock.poll_for_token
        mock_service.save_token = mock.save_token
        return mock


def test_github_login_opens_dialog(mock_page, mock_auth_service):
    """Test that GitHub login button click opens the dialog."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView
    
    view = ModernSettingsView(mock_page)
    mock_page.add(view)
    
    # Skip in CI to avoid long waits
    if os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true':
        pytest.skip("Skipping test with time.sleep in CI environment")
    
    # Simulate button click
    mock_event = MagicMock()
    view._start_github_login(mock_event)
    
    # Wait for background thread to complete
    time.sleep(1.0)
    
    # Check that dialog was created and opened
    assert mock_page.dialog is not None, "Dialog should be created"
    assert isinstance(mock_page.dialog, ft.AlertDialog), "Dialog should be AlertDialog"
    assert mock_page.dialog.open is True, "Dialog should be open"
    assert mock_page.update.called, "Page should be updated"


def test_language_change_updates_ui(mock_page):
    """Test that language change actually updates the UI."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView
    from switchcraft.utils.i18n import i18n
    
    view = ModernSettingsView(mock_page)
    mock_page.add(view)
    
    # Get the language dropdown from the general tab
    general_tab = view._build_general_tab()
    lang_dd = None
    # Search recursively in ListView controls
    def find_dropdown(control):
        if isinstance(control, ft.Dropdown):
            if control.label and ("Language" in control.label or "language" in control.label.lower()):
                return control
        if hasattr(control, 'controls'):
            for child in control.controls:
                result = find_dropdown(child)
                if result:
                    return result
        return None
    
    lang_dd = find_dropdown(general_tab)
    
    assert lang_dd is not None, "Language dropdown should exist"
    assert lang_dd.on_change is not None, "Language dropdown should have on_change handler"
    
    # Simulate language change
    mock_event = MagicMock()
    mock_event.control = lang_dd
    lang_dd.value = "de"
    
    # Skip in CI to avoid long waits
    if os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true':
        pytest.skip("Skipping test with time.sleep in CI environment")
    
    # Call the handler directly
    if lang_dd.on_change:
        lang_dd.on_change(mock_event)
    
    # Wait a bit for any background operations
    time.sleep(0.5)
    
    # Check that app was reloaded
    assert mock_page.switchcraft_app.goto_tab.called, "goto_tab should be called to reload UI"


def test_notification_bell_opens_drawer(mock_page):
    """Test that notification bell click opens the drawer."""
    from switchcraft.gui_modern.app import ModernApp
    
    app = ModernApp(mock_page)
    
    # Mock notification service
    with patch.object(app, 'notification_service') as mock_notif:
        mock_notif.get_notifications.return_value = [
            {
                "id": "test1",
                "title": "Test Notification",
                "message": "This is a test",
                "type": "info",
                "read": False,
                "timestamp": None
            }
        ]
        
        # Simulate button click
        mock_event = MagicMock()
        app._toggle_notification_drawer(mock_event)
        
        # Check that drawer was created and opened
        assert mock_page.end_drawer is not None, "Drawer should be created"
        assert isinstance(mock_page.end_drawer, ft.NavigationDrawer), "Drawer should be NavigationDrawer"
        assert mock_page.end_drawer.open is True, "Drawer should be open"
        assert mock_page.update.called, "Page should be updated"


def test_language_dropdown_handler_exists(mock_page):
    """Test that language dropdown has a proper on_change handler."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView
    
    view = ModernSettingsView(mock_page)
    mock_page.add(view)
    
    # Get the language dropdown
    general_tab = view._build_general_tab()
    lang_dd = None
    for control in general_tab.controls:
        if isinstance(control, ft.Dropdown):
            lang_dd = control
            break
    
    assert lang_dd is not None, "Language dropdown should exist"
    assert lang_dd.on_change is not None, "Language dropdown must have on_change handler"
    
    # Verify handler is callable
    assert callable(lang_dd.on_change), "on_change handler must be callable"


def test_github_login_button_exists(mock_page):
    """Test that GitHub login button exists and has on_click handler."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView
    
    view = ModernSettingsView(mock_page)
    mock_page.add(view)
    
    # Get the login button from cloud sync section
    cloud_sync = view._build_cloud_sync_section()
    
    assert hasattr(view, 'login_btn'), "Login button should exist"
    assert view.login_btn is not None, "Login button should not be None"
    assert view.login_btn.on_click is not None, "Login button must have on_click handler"
    assert callable(view.login_btn.on_click), "on_click handler must be callable"


def test_notification_button_exists(mock_page):
    """Test that notification button exists and has on_click handler."""
    from switchcraft.gui_modern.app import ModernApp
    
    app = ModernApp(mock_page)
    
    assert hasattr(app, 'notif_btn'), "Notification button should exist"
    assert app.notif_btn is not None, "Notification button should not be None"
    assert app.notif_btn.on_click is not None, "Notification button must have on_click handler"
    assert callable(app.notif_btn.on_click), "on_click handler must be callable"
