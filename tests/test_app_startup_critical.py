import unittest
from pathlib import Path
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

class TestAppStartupCritical(unittest.TestCase):
    """
    Critical startup tests ensuring main.py exists and handles basic launch.
    """

    def test_main_module_exists(self):
        """Test that switchcraft.main module exists."""
        try:
            import switchcraft.main
        except ImportError:
            self.fail("switchcraft.main module not found")

    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        try:
            from switchcraft.main import main
            self.assertTrue(callable(main))
        except ImportError as e:
            self.fail(f"Failed to import main function: {e}")

    def test_main_function_can_be_called(self):
        """
        Ensure switchcraft.main.main can be invoked with a mocked flet Page.
        """
        import flet as ft

        # Mock dependencies in main
        with patch("switchcraft.main.ModernApp") as mock_app_cls, \
             patch("switchcraft.main.is_protocol_registered", return_value=True), \
             patch("switchcraft.main.register_protocol_handler"), \
             patch("switchcraft.utils.config.SwitchCraftConfig"), \
             patch("sys.exit"):

            mock_page = MagicMock(spec=ft.Page)
            # Add required attributes used in main
            mock_page.web = False
            mock_page.route = "/"
            mock_page.session = MagicMock()
            mock_page.add = MagicMock()
            mock_page.update = MagicMock()
            mock_page.clean = MagicMock()

            # Import main inside patch
            from switchcraft.main import main

            try:
                main(mock_page)
            except Exception as e:
                self.fail(f"main(page) raised exception: {e}")

if __name__ == "__main__":
    unittest.main()