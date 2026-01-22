"""
Tests for GitHub login functionality in Modern Settings View.
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch
import threading
import time
import os

# Import CI detection helper and shared fixtures
try:
    from conftest import is_ci_environment, skip_if_ci, mock_page
except ImportError:
    # Fallback if conftest not available
    def is_ci_environment():
        return (
            os.environ.get('CI') == 'true' or
            os.environ.get('GITHUB_ACTIONS') == 'true' or
            os.environ.get('GITHUB_RUN_ID') is not None
        )
    def skip_if_ci(reason="Test not suitable for CI environment"):
        if is_ci_environment():
            pytest.skip(reason)
    # Fallback mock_page if conftest not available
    @pytest.fixture
    def mock_page():
        page = MagicMock(spec=ft.Page)
        page.dialog = None
        page.update = MagicMock()
        page.snack_bar = MagicMock(spec=ft.SnackBar)
        page.snack_bar.open = False
        def run_task(func, *args, **kwargs):
            import asyncio
            import inspect
            if inspect.iscoroutinefunction(func):
                try:
                    asyncio.get_running_loop()
                    return asyncio.create_task(func(*args, **kwargs))
                except RuntimeError:
                    return asyncio.run(func(*args, **kwargs))
            else:
                return func(*args, **kwargs)
        page.run_task = run_task
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
    # Skip in CI as this test uses time.sleep and threading
    skip_if_ci("Test uses time.sleep and threading, not suitable for CI")

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
    # Mock poll_for_token with delay to keep dialog open during assertion
    def delayed_poll(*args, **kwargs):
        time.sleep(1.0)
        return None
    mock_auth_service.poll_for_token.side_effect = delayed_poll

    view = ModernSettingsView(mock_page)
    # Manually trigger build phases
    view.build()
    if hasattr(view, '_build_cloud_sync_section'):
        view._build_cloud_sync_section()
    mock_page.add(view)

    # Mock the page property to avoid RuntimeError
    type(view).page = mock_page

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
    # Skip in CI as this test uses time.sleep and threading
    skip_if_ci("Test uses time.sleep and threading, not suitable for CI")

    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    # Mock failed device flow initiation
    mock_auth_service.initiate_device_flow.return_value = None

    view = ModernSettingsView(mock_page)
    # Manually trigger build phases
    view.build()
    if hasattr(view, '_build_cloud_sync_section'):
        view._build_cloud_sync_section()
    mock_page.add(view)

    # Mock the page property to avoid RuntimeError
    type(view).page = mock_page

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

    # Skip in CI to avoid long waits
    if os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true':
        pytest.skip("Skipping test with time.sleep in CI environment")

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
    # Manually trigger build phases
    view.build()
    if hasattr(view, '_build_cloud_sync_section'):
        view._build_cloud_sync_section()
    mock_page.add(view)

    # Mock the page property to avoid RuntimeError
    type(view).page = mock_page

    # Mock update to prevent errors
    view.update = MagicMock()

    # Track UI updates
    ui_updates = []
    original_update_sync_ui = view._update_sync_ui
    def track_update_sync_ui():
        ui_updates.append("sync_ui")
        # Do not call original as it might fail in test env
        pass
    view._update_sync_ui = track_update_sync_ui

    snack_calls = []
    def track_snack(msg, color):
        snack_calls.append((msg, color))
    view._show_snack = track_snack

    # Mock Thread to execute immediately - use ImmediateThread class
    class ImmediateThread:
        """Thread-like mock that executes target immediately when start() is called."""
        def __init__(self, target=None, daemon=False, **kwargs):
            self.target = target
            self.daemon = daemon
            self.kwargs = kwargs
            self._started = False

        def start(self):
            """Execute the stored target exactly once."""
            if not self._started and self.target:
                self._started = True
                self.target()

        def join(self, timeout=None):
            """No-op for compatibility."""
            pass

        def is_alive(self):
            """Return False since we execute immediately."""
            return False

    original_thread = threading.Thread
    threading.Thread = ImmediateThread

    try:
        # Simulate button click
        view._start_github_login(None)

        # Wait for operations to complete
        time.sleep(0.5)

        # Check that token was saved (may be called multiple times due to async execution)
        assert mock_auth_service.save_token.called, "save_token should be called"
        # Get the last call to verify the token
        if mock_auth_service.save_token.call_count > 0:
            last_call = mock_auth_service.save_token.call_args_list[-1]
            assert last_call[0][0] == "test_access_token", f"Expected token 'test_access_token', got {last_call[0][0]}"

        # Check that UI was updated
        assert "sync_ui" in ui_updates

        # Check that success message was shown
        assert len(snack_calls) > 0
        assert any("success" in str(call[0]).lower() or "login" in str(call[0]).lower() for call in snack_calls)
    finally:
        threading.Thread = original_thread
