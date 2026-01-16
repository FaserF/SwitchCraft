"""
Tests for GitHub login functionality in Modern Settings View.
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch, Mock
import threading
import time


@pytest.fixture
def mock_page():
    """Create a mock Flet page with run_task support."""
    page = MagicMock(spec=ft.Page)
    page.dialog = None
    page.update = MagicMock()
    page.snack_bar = MagicMock(spec=ft.SnackBar)
    page.snack_bar.open = False

    # Mock run_task to actually execute the function
    def run_task(func):
        func()
    page.run_task = run_task

    # Mock page.open to set dialog and open it
    def mock_open(control):
        if isinstance(control, ft.AlertDialog):
            page.dialog = control
            control.open = True
        page.update()
    page.open = mock_open

    return page


@pytest.fixture
def mock_auth_service():
    """Mock AuthService responses."""
    with patch('switchcraft.gui_modern.views.settings_view.AuthService') as mock_auth:
        yield mock_auth


def test_github_login_button_click_opens_dialog(mock_page, mock_auth_service):
    """Test that clicking GitHub login button opens a dialog."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    # Mock successful device flow initiation
    mock_flow = {
        "device_code": "test_device_code",
        "user_code": "ABCD-1234",
        "verification_uri": "https://github.com/login/device",
        "interval": 5,
        "expires_in": 900
    }
    mock_auth_service.initiate_device_flow.return_value = mock_flow
    mock_auth_service.poll_for_token.return_value = None  # User hasn't authorized yet

    view = ModernSettingsView(mock_page)
    mock_page.add(view)

    # Mock the page property to avoid RuntimeError
    def get_page():
        return mock_page
    type(view).page = property(lambda self: mock_page)

    # Mock update to prevent errors
    view.update = MagicMock()

    # Simulate button click
    view._start_github_login(None)

    # Wait a bit for thread to start and complete
    time.sleep(0.5)

    # Check that dialog was set
    assert mock_page.dialog is not None
    assert isinstance(mock_page.dialog, ft.AlertDialog)
    assert mock_page.dialog.open is True

    # Check dialog content
    assert len(mock_page.dialog.content.controls) > 0
    assert "ABCD-1234" in str(mock_page.dialog.content.controls)
    assert "github.com/login/device" in str(mock_page.dialog.content.controls)

    # Verify update was called
    assert mock_page.update.called


def test_github_login_shows_error_on_failure(mock_page, mock_auth_service):
    """Test that GitHub login shows error when flow initiation fails."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    # Mock failed device flow initiation
    mock_auth_service.initiate_device_flow.return_value = None

    view = ModernSettingsView(mock_page)
    mock_page.add(view)

    # Mock the page property to avoid RuntimeError
    def get_page():
        return mock_page
    type(view).page = property(lambda self: mock_page)

    # Mock update to prevent errors
    view.update = MagicMock()

    # Track snack calls
    snack_calls = []
    def track_snack(msg, color):
        snack_calls.append((msg, color))
    view._show_snack = track_snack

    # Simulate button click
    view._start_github_login(None)

    # Wait a bit for thread to start and complete
    time.sleep(0.5)

    # Check that error snack was shown
    assert len(snack_calls) > 0
    assert "failed" in snack_calls[0][0].lower() or "error" in snack_calls[0][0].lower()


def test_github_login_success_saves_token(mock_page, mock_auth_service):
    """Test that successful GitHub login saves token and updates UI."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    # Mock successful flow
    mock_flow = {
        "device_code": "test_device_code",
        "user_code": "ABCD-1234",
        "verification_uri": "https://github.com/login/device",
        "interval": 5,
        "expires_in": 900
    }
    mock_auth_service.initiate_device_flow.return_value = mock_flow
    mock_auth_service.poll_for_token.return_value = "test_access_token"
    mock_auth_service.save_token = MagicMock()

    view = ModernSettingsView(mock_page)
    mock_page.add(view)

    # Mock the page property to avoid RuntimeError
    def get_page():
        return mock_page
    type(view).page = property(lambda self: mock_page)

    # Mock update to prevent errors
    view.update = MagicMock()

    # Track UI updates
    ui_updates = []
    original_update_sync_ui = view._update_sync_ui
    def track_update_sync_ui():
        ui_updates.append("sync_ui")
        original_update_sync_ui()
    view._update_sync_ui = track_update_sync_ui

    snack_calls = []
    def track_snack(msg, color):
        snack_calls.append((msg, color))
    view._show_snack = track_snack

    # Simulate button click
    view._start_github_login(None)

    # Wait for polling to complete (mock returns immediately)
    time.sleep(0.5)

    # Check that token was saved
    mock_auth_service.save_token.assert_called_once_with("test_access_token")

    # Check that UI was updated
    assert "sync_ui" in ui_updates

    # Check that success message was shown
    assert len(snack_calls) > 0
    assert any("success" in str(call[0]).lower() for call in snack_calls)
