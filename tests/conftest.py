"""
Pytest configuration and shared fixtures.
"""
import os
import time
import asyncio
import pytest
from unittest.mock import MagicMock
import flet as ft


from tests.utils import is_ci_environment, skip_if_ci, poll_until


def _create_mock_page():
    """
    Helper function to create a mock Flet page with all necessary attributes.
    This can be called directly (unlike the pytest fixture).

    Returns:
        MockPage: A fully configured mock page instance.
    """
    class MockPage(ft.Page):
        """Mock Flet Page that supports direct attribute assignment."""
        def __init__(self):
            # Do not call super().__init__ as it requires connection
            # Initialize internal Flet attributes needed for __str__ and others
            self._c = "Page"
            self._i = "page"

            # Initialize Mock logic (backing fields)
            self._dialog = None
            self._end_drawer = None
            self._snack_bar = MagicMock(spec=ft.SnackBar)
            self._snack_bar.open = False

            self._controls = []
            self._views = [self] # Root view is self logic if needed, or just list
            self._padding = 10
            self._appbar = None
            self._overlay = []
            self._theme_mode = ft.ThemeMode.LIGHT

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
                    loop = asyncio.get_running_loop()
                    return asyncio.create_task(func(*args, **kwargs))
                except RuntimeError:
                    return asyncio.run(func(*args, **kwargs))
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
            if isinstance(control, ft.NavigationDrawer) and self.end_drawer == control:
                self.end_drawer.open = False
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

    page = MockPage()
    return page


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
    return _create_mock_page()
