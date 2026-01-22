"""
Real test for GitHub login - ensures dialog actually opens.
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch
import os

# Import shared fixtures and helpers from conftest
try:
    from .utils import poll_until
except ImportError:
    # Fallback if run as script
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tests.utils import poll_until


@pytest.fixture
def mock_auth_service():
    """Mock AuthService responses."""
    with patch('switchcraft.gui_modern.views.settings_view.AuthService') as mock:
        mock.initiate_device_flow.return_value = {
            "device_code": "test_code",
            "user_code": "ABC-123",
            "verification_uri": "https://github.com/login/device",
            "interval": 5,
            "expires_in": 900
        }
        mock.poll_for_token.return_value = "test_token_123"
        mock.save_token = MagicMock()
        yield mock


def test_github_login_dialog_opens(mock_page, mock_auth_service):
    """Test that GitHub login dialog actually opens when button is clicked."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    view = ModernSettingsView(mock_page)
    mock_page.add(view)

    # Skip in CI to avoid long waits
    if os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true':
        pytest.skip("Skipping test with time.sleep in CI environment")

    # Simulate button click
    mock_event = MagicMock()
    view._start_github_login(mock_event)

    # Wait for dialog to be created and opened using polling
    def dialog_ready():
        return (mock_page.dialog is not None and
                isinstance(mock_page.dialog, ft.AlertDialog) and
                mock_page.dialog.open is True)

    assert poll_until(dialog_ready, timeout=2.0), "Dialog should be created and opened within timeout"

    # Check that dialog was created and opened
    assert mock_page.dialog is not None, "Dialog should be created"
    assert isinstance(mock_page.dialog, ft.AlertDialog), "Dialog should be AlertDialog"
    assert mock_page.dialog.open is True, "Dialog should be open"
    assert mock_page.update.called, "Page should be updated"


def test_language_change_updates_ui(mock_page):
    """Test that language change actually updates the UI."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    view = ModernSettingsView(mock_page)
    mock_page.add(view)

    # Mock app reference
    mock_app = MagicMock()
    mock_app._current_tab_index = 0
    mock_app._view_cache = {}
    mock_app.goto_tab = MagicMock()
    mock_page.switchcraft_app = mock_app

    # Simulate language change
    view._on_lang_change("de")

    # Check that app was reloaded
    # Check that restart dialog opened
    assert mock_page.dialog is not None and mock_page.dialog.open is True, "Restart dialog should be open"


def test_notification_bell_opens_drawer(mock_page):
    """Test that notification bell actually opens the drawer."""
    from switchcraft.gui_modern.app import ModernApp

    app = ModernApp(mock_page)
    # Ensure run_task is available for UI updates
    mock_page.run_task = lambda func: func()

    # Mock notification service
    with patch.object(app, 'notification_service') as mock_notif:
        mock_notif.get_notifications.return_value = []

        # Simulate button click
        mock_event = MagicMock()
        app._toggle_notification_drawer(mock_event)

        # Check that drawer was created and opened
        # Note: self.page.end_drawer should be set by _open_notifications_drawer
        # Since self.page = mock_page, we check mock_page.end_drawer
        assert app.page.end_drawer is not None, "Drawer should be created"
        assert isinstance(app.page.end_drawer, ft.NavigationDrawer), "Drawer should be NavigationDrawer"
        assert app.page.end_drawer.open is True, "Drawer should be open"
        assert mock_page.update.called, "Page should be updated"
