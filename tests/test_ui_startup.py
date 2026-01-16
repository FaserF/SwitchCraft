import unittest
import flet as ft
from unittest.mock import MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath("src"))

from switchcraft.gui_modern.views.helper_view import ModernHelperView
from switchcraft.gui_modern.app import ModernApp

class TestUIIntegrity(unittest.TestCase):
    def setUp(self):
        self.page = MagicMock(spec=ft.Page)
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.platform = ft.PagePlatform.WINDOWS
        # Mock add/update/clean
        self.page.add = MagicMock()
        self.page.update = MagicMock()
        self.page.clean = MagicMock()
        self.page.open = MagicMock()

    def test_helper_view_init(self):
        """Test if HelperView initializes without TypeError."""
        try:
            view = ModernHelperView(self.page)
            self.assertIsInstance(view, ft.Column)
        except Exception as e:
            self.fail(f"HelperView init failed: {e}")

    def test_app_destinations(self):
        """Test if App builds destinations correctly."""
        try:
             # Mock the import inside setup_page causing issues if necessary
            with unittest.mock.patch("switchcraft.gui_modern.app.SwitchCraftConfig"):
                 app = ModernApp(self.page)
                 self.assertTrue(len(app.sidebar.all_destinations) > 0, "Sidebar has no destinations!")
        except Exception as e:
            self.fail(f"App init failed: {e}")

    def test_sidebar_has_bounded_height(self):
        """Test that Sidebar container has bounded height/expansion.
        """
        try:
            with unittest.mock.patch("switchcraft.gui_modern.app.SwitchCraftConfig"):
                app = ModernApp(self.page)

                # app.sidebar is the sidebar control
                # It should have expand=True to fill the column
                self.assertTrue(
                    app.sidebar.expand,
                    "HoverSidebar must have expand=True to fill the vertical space."
                )
        except Exception as e:
            self.fail(f"NavigationRail layout test failed: {e}")

if __name__ == "__main__":
    unittest.main()

class TestWindowIconPath(unittest.TestCase):
    """Test that window icon path is correctly resolved."""

    def test_icon_path_exists_in_dev_mode(self):
        """Test that icon path is resolved correctly in development mode."""
        import os
        import sys

        # Simulate dev mode (not frozen)
        if not getattr(sys, 'frozen', False):
            # tests folder -> root
            root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            ico_path = os.path.join(root_path, "src", "switchcraft", "assets", "switchcraft_logo.ico")

            self.assertTrue(
                os.path.exists(ico_path),
                f"Icon file should exist at: {ico_path}"
            )
