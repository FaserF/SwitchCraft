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

    def test_helper_view_init(self):
        """Test if HelperView initializes without TypeError."""
        print("\nTesting HelperView init...")
        try:
            view = ModernHelperView(self.page)
            print("HelperView initialized successfully.")
        except TypeError as e:
            self.fail(f"HelperView init failed: {e}")

    def test_app_destinations(self):
        """Test if App builds destinations correctly."""
        print("\nTesting App build_ui...")
        try:
            # We need to mock the page more for App
            app = ModernApp(self.page)
            # app.__init__ calls build_ui

            # Check if rail has destinations
            self.assertTrue(len(app.rail.destinations) > 0, "NavigationRail has no destinations!")
            print(f"App initialized with {len(app.rail.destinations)} destinations.")

        except Exception as e:
            self.fail(f"App init failed: {e}")

if __name__ == "__main__":
    unittest.main()
