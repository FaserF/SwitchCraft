"""
Pytest configuration and shared fixtures.
"""
import os
import time
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
    Skip test if running in CI environment.

    Args:
        reason: Reason for skipping the test.

    Returns:
        pytest.skip decorator or None.
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

            # Mock app reference
            self.switchcraft_app = MagicMock()
            self.switchcraft_app._current_tab_index = 0
            self.switchcraft_app._view_cache = {}
            self.switchcraft_app.goto_tab = MagicMock()

            # Mock run_task to actually execute the function
            def run_task(func):
                func()
            self.run_task = run_task

            # Mock page.open to set dialog/drawer and open it
            def mock_open(control):
                if isinstance(control, ft.AlertDialog):
                    self.dialog = control
                    control.open = True
                elif isinstance(control, ft.NavigationDrawer):
                    self.end_drawer = control
                    control.open = True
                self.update()
            self.open = mock_open

            # Add MagicMock methods for compatibility (e.g., add)
            self.add = MagicMock()

    page = MockPage()
    return page
