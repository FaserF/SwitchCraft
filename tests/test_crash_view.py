import unittest
from unittest.mock import MagicMock, patch
import flet as ft
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from switchcraft.gui_modern.views.crash_view import CrashDumpView


class TestCrashView(unittest.TestCase):
    def setUp(self):
        """
        Prepare a mocked flet Page object with commonly used attributes for tests.

        Creates self.page as a MagicMock(spec=ft.Page) and configures attributes used by the test suite:
        - snack_bar set to None
        - set_clipboard, update, clean, add, show_snack_bar set to MagicMock instances
        """
        self.page = MagicMock(spec=ft.Page)
        self.page.snack_bar = None
        self.page.set_clipboard = MagicMock()
        self.page.update = MagicMock()
        self.page.clean = MagicMock()
        self.page.add = MagicMock()
        self.page.show_snack_bar = MagicMock()

    def test_crash_view_initialization(self):
        """Test that CrashDumpView initializes correctly."""
        error = ValueError("Test error")
        view = CrashDumpView(self.page, error)
        self.assertIsNotNone(view)
        self.assertEqual(view.bgcolor, "#1a1a1a")
        self.assertIsNotNone(view.content)

    def test_crash_view_with_traceback(self):
        """Test CrashDumpView with custom traceback."""
        error = RuntimeError("Test runtime error")
        traceback_str = "Traceback (most recent call last):\n  File \"test.py\", line 1, in <module>\n    raise RuntimeError('Test')\nRuntimeError: Test runtime error"
        view = CrashDumpView(self.page, error, traceback_str)
        self.assertEqual(view._traceback_str, traceback_str)

    def test_copy_error_with_pyperclip(self):
        """Test copying error to clipboard using pyperclip."""
        error = ValueError("Test error")
        view = CrashDumpView(self.page, error, "Test traceback")

        # Try to import pyperclip, skip test if not available
        try:
            import pyperclip
        except ImportError:
            self.skipTest("pyperclip not available")

        with patch('pyperclip.copy') as mock_copy:
            event = MagicMock()
            view._copy_error(event)
            mock_copy.assert_called_once_with("Test traceback")

    def test_copy_error_fallback_to_flet(self):
        """Test copying error falls back to Flet clipboard if pyperclip fails."""
        error = ValueError("Test error")
        view = CrashDumpView(self.page, error, "Test traceback")

        # Try to import pyperclip, skip test if not available
        try:
            import pyperclip
            with patch('pyperclip.copy', side_effect=Exception("pyperclip failed")):
                event = MagicMock()
                view._copy_error(event)
                self.page.set_clipboard.assert_called_once_with("Test traceback")
        except ImportError:
            # If pyperclip is not available, test that Flet clipboard is used
            event = MagicMock()
            view._copy_error(event)
            self.page.set_clipboard.assert_called_once_with("Test traceback")

    def test_close_app_disables_button(self):
        """Test that Close App button is disabled when clicked."""
        error = ValueError("Test error")
        view = CrashDumpView(self.page, error)

        event = MagicMock()
        event.control = MagicMock()
        event.control.disabled = False
        event.control.text = "Close App"

        with patch('threading.Thread') as mock_thread:
            view._close_app(event)
            self.assertTrue(event.control.disabled)
            self.assertEqual(event.control.text, "Closing...")
            self.page.update.assert_called()

    @patch('subprocess.Popen')
    @patch('sys.exit')
    def test_reload_app_calls_subprocess(self, mock_exit, mock_popen):
        """Test that reload app calls subprocess.Popen."""
        error = ValueError("Test error")
        view = CrashDumpView(self.page, error)

        # Test that reload_app calls subprocess.Popen
        # We don't need to mock sys.frozen since getattr handles it gracefully
        view._reload_app(self.page)
        # Popen should be called at least once (may be called multiple times in test environment)
        self.assertGreaterEqual(mock_popen.call_count, 1, "Popen should be called at least once")
        self.page.clean.assert_called_once()
        self.page.add.assert_called_once()


if __name__ == '__main__':
    unittest.main()