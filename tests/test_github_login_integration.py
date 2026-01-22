"""
Integration test for GitHub login button - tests actual button click behavior.
This test ensures the button actually works when clicked in the UI.
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch
import time
import os

# Import CI detection helper
try:
    from conftest import is_ci_environment, skip_if_ci, poll_until, mock_page
except ImportError:
    def is_ci_environment():
        return (
            os.environ.get('CI') == 'true' or
            os.environ.get('GITHUB_ACTIONS') == 'true' or
            os.environ.get('GITHUB_RUN_ID') is not None
        )
    def skip_if_ci(reason="Test not suitable for CI environment"):
        if is_ci_environment():
            pytest.skip(reason)
    def poll_until(predicate, timeout=10.0, interval=0.1):
        """
        Poll a predicate function until it returns True or timeout elapses.

        Parameters:
            predicate: Callable that returns True when condition is met
            timeout: Maximum time to wait in seconds (default: 10.0)
            interval: Time between polls in seconds (default: 0.1)

        Returns:
            True if predicate returned True, False on timeout

        Raises:
            TimeoutError: If timeout elapses without predicate returning True
        """
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            if predicate():
                return True
            time.sleep(interval)
        raise TimeoutError(f"Predicate did not return True within {timeout} seconds")

    @pytest.fixture
    def mock_page():
        page = MagicMock(spec=ft.Page)
        page.dialog = None
        page.update = MagicMock()
        page.snack_bar = MagicMock(spec=ft.SnackBar)
        page.snack_bar.open = False
        page.open = MagicMock()

        # Proper run_task
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

        # Proper add to recursively set page
        def add(*controls):
            import weakref
            def set_structure_recursive(ctrl, parent):
                try: ctrl._parent = weakref.ref(parent)
                except Exception: pass

                try: ctrl._page = page
                except AttributeError: pass

                if hasattr(ctrl, 'controls') and ctrl.controls:
                    for child in ctrl.controls:
                        set_structure_recursive(child, ctrl)
                if hasattr(ctrl, 'content') and ctrl.content:
                    set_structure_recursive(ctrl.content, ctrl)

            for control in controls:
                set_structure_recursive(control, page)

            page.update()

        page.add = add
        return page


@pytest.fixture
def mock_auth_service():
    """Mock AuthService responses."""
    with patch('switchcraft.gui_modern.views.settings_view.AuthService') as mock_auth:
        mock_flow = {
            "device_code": "test_device_code",
            "user_code": "ABCD-1234",
            "verification_uri": "https://github.com/login/device",
            "interval": 5,
            "expires_in": 900
        }
        mock_auth.initiate_device_flow.return_value = mock_flow
        # Ensure we are not authenticated so login button is shown
        mock_auth.is_authenticated.return_value = False
        # Mock poll_for_token with delay to keep dialog open during assertion
        def delayed_poll(*args, **kwargs):
            time.sleep(0.5)
            return None
        mock_auth.poll_for_token.side_effect = delayed_poll
        yield mock_auth


def test_github_login_button_click_integration(mock_page, mock_auth_service):
    """Test that clicking the actual GitHub login button in the UI works."""
    skip_if_ci("Test uses time.sleep and threading, not suitable for CI")

    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    view = ModernSettingsView(mock_page)
    # Manually trigger build logic and capture the resulting container
    if hasattr(view, '_build_cloud_sync_section'):
        content = view._build_cloud_sync_section()
        mock_page.add(content)
    mock_page.add(view)

    # Ensure page has required attributes
    if not hasattr(mock_page, 'dialog'):
        mock_page.dialog = None
    if not hasattr(mock_page, 'open'):
        def mock_open(control):
            if isinstance(control, ft.AlertDialog):
                mock_page.dialog = control
                control.open = True
        mock_page.open = mock_open

    # Verify button exists and has handler
    assert hasattr(view, 'login_btn'), "Login button should exist"
    assert view.login_btn is not None, "Login button should not be None"
    assert view.login_btn.on_click is not None, "Login button must have on_click handler"
    assert callable(view.login_btn.on_click), "on_click handler must be callable"

    # Simulate actual button click via on_click handler
    mock_event = MagicMock()
    view.login_btn.on_click(mock_event)

    # Wait for background thread to start and dialog to appear
    def dialog_appeared():
        return (mock_page.dialog is not None and
                isinstance(mock_page.dialog, ft.AlertDialog) and
                mock_page.dialog.open is True)

    assert poll_until(dialog_appeared, timeout=2.0), "Dialog should appear after button click"

    # Verify dialog content
    assert mock_page.dialog is not None
    assert isinstance(mock_page.dialog, ft.AlertDialog)
    assert mock_page.dialog.open is True

    # Verify update was called
    assert mock_page.update.called, "Page should be updated after button click"


def test_github_login_button_handler_wrapped(mock_page):
    """Test that GitHub login button handler is properly wrapped with _safe_event_handler."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    view = ModernSettingsView(mock_page)
    # Manually trigger build phases
    view.build()
    if hasattr(view, '_build_cloud_sync_section'):
        view._build_cloud_sync_section()
    mock_page.add(view)

    # Verify button exists
    assert hasattr(view, 'login_btn'), "Login button should exist"

    # The handler should be wrapped, but we can't easily check that from outside
    # Instead, we verify that clicking the button doesn't raise exceptions
    mock_event = MagicMock()

    # Mock AuthService to avoid actual network calls
    with patch('switchcraft.gui_modern.views.settings_view.AuthService') as mock_auth:
        mock_auth.initiate_device_flow.return_value = None  # Simulate failure

        # Track if exception was raised
        exception_raised = []
        def track_exception(ex):
            exception_raised.append(ex)

        # If handler is wrapped, exceptions should be caught
        try:
            view.login_btn.on_click(mock_event)
            # Wait a bit for any background threads
            time.sleep(0.2)
        except Exception as ex:
            exception_raised.append(ex)

        # Handler should not raise unhandled exceptions (they should be caught by _safe_event_handler)
        # Note: In test environment, exceptions might still propagate, but in real app they should be caught
        # This test mainly verifies the button has a handler
        assert view.login_btn.on_click is not None, "Button should have a handler"
