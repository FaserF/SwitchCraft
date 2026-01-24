"""
Pytest configuration and shared fixtures.
"""
import os
import sys
import asyncio
import pytest
from unittest.mock import MagicMock
import flet as ft

# Make local tests helper module importable when running in CI or from repo root
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)


def is_ci_environment():
    """Returns True if running in a CI environment (GitHub Actions)."""
    return (
        os.environ.get('CI') == 'true' or
        os.environ.get('GITHUB_ACTIONS') == 'true' or
        os.environ.get('GITHUB_RUN_ID') is not None
    )


def skip_if_ci(reason="Test not suitable for CI environment"):
    """Pytest decorator/helper to skip tests in CI."""
    if is_ci_environment():
        pytest.skip(reason)


import time

def poll_until(condition, timeout=5.0, interval=0.1):
    """
    Polls the condition function until it returns True or timeout expires.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition():
            return True
        time.sleep(interval)
    return False


def _create_mock_page():
    """
    Helper function to create a mock Flet page with all necessary attributes.
    Returns:
        MockPage: A fully configured mock page instance.
    """
    class MockPage(ft.Page):
        """Mock Flet Page that supports direct attribute assignment."""
        def __init__(self):
            # Do not call super().__init__ as it requires connection
            self._c = "Page"
            self._i = "page"

            # Initialize Mock logic (backing fields)
            self._dialog = None
            self._end_drawer = None
            self._snack_bar = MagicMock(spec=ft.SnackBar)
            self._snack_bar.open = False

            self._controls = []
            self._views = [self]
            self._padding = 10
            self._appbar = None
            self._overlay = []
            self._theme_mode = ft.ThemeMode.LIGHT
            self.favicon = None

            # Mock update
            self.update = MagicMock()

            # Window (for silent mode)
            self.window = MagicMock()
            self.window.minimized = False

            # Mock app reference
            self.switchcraft_app = MagicMock()
            self.switchcraft_app._current_tab_index = 0
            self.switchcraft_app._view_cache = {}
            self.switchcraft_app.goto_tab = MagicMock()

        # Properties Overrides
        @property
        def dialog(self): return self._dialog
        @dialog.setter
        def dialog(self, value): self._dialog = value

        @property
        def end_drawer(self): return self._end_drawer
        @end_drawer.setter
        def end_drawer(self, value): self._end_drawer = value

        @property
        def snack_bar(self): return self._snack_bar
        @snack_bar.setter
        def snack_bar(self, value): self._snack_bar = value

        @property
        def controls(self): return self._controls
        @controls.setter
        def controls(self, value): self._controls = value

        @property
        def views(self): return self._views

        @property
        def padding(self): return self._padding
        @padding.setter
        def padding(self, value): self._padding = value

        @property
        def appbar(self): return self._appbar
        @appbar.setter
        def appbar(self, value): self._appbar = value

        @property
        def overlay(self): return self._overlay

        @property
        def theme_mode(self): return self._theme_mode
        @theme_mode.setter
        def theme_mode(self, value): self._theme_mode = value

        # Methods Overrides
        def run_task(self, func, *args, **kwargs):
            import inspect
            if inspect.iscoroutinefunction(func):
                try:
                    # Check if loop is running
                    loop = asyncio.get_running_loop()
                    return loop.create_task(func(*args, **kwargs))
                except RuntimeError:
                    # No loop running, use run execution
                    result = asyncio.run(func(*args, **kwargs))

                    # Return a completed awaitable to satisfy code that might await it
                    class CompletedTask:
                        def __init__(self, res): self._res = res
                        def __await__(self):
                            yield
                            return self._res
                        def result(self): return self._res
                        def done(self): return True
                        def cancel(self): return False

                    return CompletedTask(result)
            else:
                return func(*args, **kwargs)

        def add(self, *controls):
            import weakref
            def set_structure_recursive(ctrl, parent):
                try: ctrl._parent = weakref.ref(parent)
                except Exception: pass

                try: ctrl._page = self
                except AttributeError: pass

                # Recurse
                if hasattr(ctrl, 'controls') and ctrl.controls:
                    for child in ctrl.controls:
                        set_structure_recursive(child, ctrl)
                if hasattr(ctrl, 'content') and ctrl.content:
                    set_structure_recursive(ctrl.content, ctrl)

            for control in controls:
                set_structure_recursive(control, self)
            self._controls.extend(controls)
            self.update()

        def open(self, control):
            if isinstance(control, ft.AlertDialog):
                self.dialog = control
                control.open = True
            elif isinstance(control, ft.NavigationDrawer):
                self.end_drawer = control
                control.open = True
            elif isinstance(control, ft.SnackBar):
                self.snack_bar = control
                control.open = True
            self.update()

        def close(self, control):
            if isinstance(control, ft.AlertDialog) and self.dialog == control:
                control.open = False
                self.dialog = None
            elif isinstance(control, ft.NavigationDrawer) and self.end_drawer == control:
                control.open = False
                self.end_drawer = None
            elif isinstance(control, ft.SnackBar) and self.snack_bar == control:
                control.open = False
            self.update()

        def clean(self):
            self._controls.clear()
            self.update()

        def open_end_drawer(self, drawer):
            self.end_drawer = drawer
            self.end_drawer.open = True
            self.update()

        def close_end_drawer(self):
            if self.end_drawer:
                self.end_drawer.open = False
            self.update()

        def launch_url(self, url):
            """Mock launch_url."""
            pass

    return MockPage()


@pytest.fixture(autouse=True)
def mock_blocking_calls(monkeypatch, request):
    """Global fixture to mock all blocking OS/UI/Network calls."""
    import os
    import webbrowser
    import requests
    import subprocess
    try:
        import keyring
    except ImportError:
        keyring = MagicMock()

    from switchcraft.utils.config import SwitchCraftConfig
    from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper

    test_path = str(request.node.path)

    # Mock FilePickerHelper
    monkeypatch.setattr(FilePickerHelper, "pick_file", MagicMock(return_value="C:/test/file.exe"))
    monkeypatch.setattr(FilePickerHelper, "pick_directory", MagicMock(return_value="C:/test/dir"))
    monkeypatch.setattr(FilePickerHelper, "save_file", MagicMock(return_value="C:/test/save.exe"))

    # Mock webbrowser
    monkeypatch.setattr(webbrowser, "open", MagicMock(return_value=True))

    # Mock requests to prevent network I/O
    monkeypatch.setattr(requests, "get", MagicMock())
    monkeypatch.setattr(requests, "post", MagicMock())
    monkeypatch.setattr(requests, "put", MagicMock())
    monkeypatch.setattr(requests, "patch", MagicMock())
    monkeypatch.setattr(requests, "delete", MagicMock())

    # Mock subprocess to prevent heavy process spawning
    # But allow test_smoke.py to run real version checks
    if "test_smoke.py" not in test_path:
        monkeypatch.setattr(subprocess, "run", MagicMock())
        monkeypatch.setattr(subprocess, "Popen", MagicMock())

    # Mock keyring to prevent secret store hangs in CI/Local
    monkeypatch.setattr(keyring, "get_password", MagicMock(return_value="mock_password"))
    monkeypatch.setattr(keyring, "set_password", MagicMock())
    monkeypatch.setattr(keyring, "delete_password", MagicMock())

    # Mock SwitchCraftConfig to prevent registry/file I/O and GPO checks
    # BUT allow it for test_config*.py which tests the config logic itself
    test_path = str(request.node.path)
    if "test_config" not in test_path and "test_full_coverage" not in test_path and "test_critical_ui_flows" not in test_path and "test_github_login_integration" not in test_path:
        monkeypatch.setattr(SwitchCraftConfig, "get_value", MagicMock(return_value="test_value"))
        monkeypatch.setattr(SwitchCraftConfig, "get_secure_value", MagicMock(return_value="test_secret"))
        monkeypatch.setattr(SwitchCraftConfig, "set_user_preference", MagicMock())
        monkeypatch.setattr(SwitchCraftConfig, "set_secure_value", MagicMock())
        monkeypatch.setattr(SwitchCraftConfig, "is_managed", MagicMock(return_value=False))


    # Mock UpdateChecker to prevent real update checks
    from switchcraft.utils.app_updater import UpdateChecker
    if "test_updater_logic.py" not in test_path:
         monkeypatch.setattr(UpdateChecker, "check_for_updates", MagicMock(return_value=(False, "1.0.0", {})))


    # Mock os.startfile if it exists (Windows only)
    if hasattr(os, "startfile"):
        monkeypatch.setattr(os, "startfile", MagicMock())

    # Safely mock threading.Thread to prevent background threads from our code
    import threading
    original_thread_cls = threading.Thread

    class MockThread(original_thread_cls):
        def start(self):
            import inspect
            stack = inspect.stack()
            # Look for switchcraft in the caller's stack
            is_switchcraft = False
            is_safe_infrastructure = False

            for frame in stack:
                filename = frame.filename
                if "switchcraft" in filename:
                    is_switchcraft = True
                if ("concurrent" in filename and "futures" in filename) or "asyncio" in filename:
                    is_safe_infrastructure = True

            # Allow if it's infrastructure (asyncio/futures) OR if it's NOT switchcraft code
            # OR if it is being run from a test (test is in stack)
            is_test = False
            for frame in stack:
                if "tests" in frame.filename or "test_" in frame.filename:
                    is_test = True
                    break

            if is_safe_infrastructure or is_test or not is_switchcraft:
                super().start()
            else:
                # preventing thread start from direct switchcraft code (not driven by test)
                pass

    monkeypatch.setattr(threading, "Thread", MockThread)


@pytest.fixture
def mock_page():
    """
    Create a mock Flet page with all necessary attributes.
    """
    return _create_mock_page()
