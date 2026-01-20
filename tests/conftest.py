"""
Pytest configuration and shared fixtures.
"""
import os
import time
import asyncio
import pytest
from unittest.mock import MagicMock
import flet as ft


def is_ci_environment():
    """
    Check if running in a CI environment (GitHub Actions, etc.).

    Returns:
        bool: True if running in CI, False otherwise.
    """
    return (
        os.environ.get('CI') == 'true' or
        os.environ.get('GITHUB_ACTIONS') == 'true' or
        os.environ.get('GITHUB_RUN_ID') is not None
    )


def skip_if_ci(reason="Test not suitable for CI environment"):
    """
    Immediately skip the test if running in CI environment.

    This function calls pytest.skip() immediately if is_ci_environment() returns True,
    causing the test to be skipped with the provided reason.

    Args:
        reason: Reason for skipping the test.

    Note:
        This function performs an immediate skip by calling pytest.skip() when
        running in CI, so it should be called at the beginning of a test function.
    """
    if is_ci_environment():
        pytest.skip(reason)


def poll_until(condition, timeout=2.0, interval=0.05):
    """
    Poll until condition is met or timeout is reached.

    Parameters:
        condition: Callable that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between polls in seconds

    Returns:
        True if condition was met, False if timeout
    """
    elapsed = 0.0
    while elapsed < timeout:
        if condition():
            return True
        time.sleep(interval)
        elapsed += interval
    return False


@pytest.fixture
def mock_page():
    """
    Create a mock Flet page with all necessary attributes.

    This fixture provides a fully configured mock page that handles:
    - Dialogs (AlertDialog)
    - Navigation drawers (NavigationDrawer) - supports direct assignment via page.end_drawer = drawer
    - Snack bars
    - App references (switchcraft_app)
    - run_task for UI updates

    The fixture uses a custom class to ensure direct assignments to page.end_drawer
    work correctly, as the code may set end_drawer directly rather than using page.open().
    """
    class MockPage:
        """Mock Flet Page that supports direct attribute assignment."""
        def __init__(self):
            self.dialog = None
            self.end_drawer = None
            self.update = MagicMock()
            self.snack_bar = MagicMock(spec=ft.SnackBar)
            self.snack_bar.open = False

            # Controls list for page content
            self.controls = []

            # Theme mode
            self.theme_mode = ft.ThemeMode.LIGHT

            # AppBar
            self.appbar = None

            # Window (for silent mode)
            self.window = MagicMock()
            self.window.minimized = False

            # Mock app reference
            self.switchcraft_app = MagicMock()
            self.switchcraft_app._current_tab_index = 0
            self.switchcraft_app._view_cache = {}
            self.switchcraft_app.goto_tab = MagicMock()

            # Mock run_task to actually execute the function (handle both sync and async)
            import inspect
            def run_task(func):
                if inspect.iscoroutinefunction(func):
                    # For async functions, create a task and run it
                    try:
                        # Use get_running_loop() instead of deprecated get_event_loop()
                        loop = asyncio.get_running_loop()
                        # If loop is running, schedule the coroutine
                        task = asyncio.create_task(func())
                        # In test environment, we can't await, so just create the task
                        # The warning is expected in test environment
                        return task
                    except RuntimeError:
                        # No event loop, create one and run
                        asyncio.run(func())
                else:
                    # For sync functions, call directly
                    func()
            self.run_task = run_task

            # Mock page.open to set dialog/drawer/snackbar and open it
            def mock_open(control):
                if isinstance(control, ft.AlertDialog):
                    self.dialog = control
                    setattr(control, 'open', True)
                elif isinstance(control, ft.NavigationDrawer):
                    self.end_drawer = control
                    setattr(control, 'open', True)
                elif isinstance(control, ft.SnackBar):
                    self.snack_bar = control
                    setattr(control, 'open', True)
                self.update()
            self.open = mock_open

            # Mock page.close for closing drawers
            def mock_close(control):
                if isinstance(control, ft.NavigationDrawer):
                    if self.end_drawer == control:
                        setattr(self.end_drawer, 'open', False)
                self.update()
            self.close = mock_close

            # Mock page.add to add controls to the page
            # Mock page.add to add controls to the page
            def mock_add(*controls):
                import weakref
                def set_structure_recursive(ctrl, parent):
                    try:
                        # Try public setter first if available? No, Flet usually internal.
                        # But let's try direct setting if no property setter.
                         ctrl._parent = weakref.ref(parent)
                    except Exception:
                        # If simple assignment fails (unlikely for _parent), just proceed
                        pass

                    try:
                        ctrl._page = self
                    except AttributeError:
                        pass

                    # Recurse for children
                    if hasattr(ctrl, 'controls') and ctrl.controls:
                        for child in ctrl.controls:
                            set_structure_recursive(child, ctrl)
                    if hasattr(ctrl, 'content') and ctrl.content:
                        set_structure_recursive(ctrl.content, ctrl)

                for control in controls:
                    set_structure_recursive(control, self)
                self.controls.extend(controls)
                self.update()
            self.add = mock_add

            # Mock page.clean to clear controls
            def mock_clean():
                self.controls.clear()
                self.update()
            self.clean = mock_clean

    page = MockPage()
    return page
