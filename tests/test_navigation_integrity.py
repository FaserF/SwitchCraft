import unittest
from unittest.mock import MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import flet as ft
from switchcraft.gui_modern.app import ModernApp

class TestNavigationIntegrity(unittest.TestCase):
    def setUp(self):
        self.mock_page = MagicMock(spec=ft.Page)
        self.mock_page.window = MagicMock()
        self.mock_page.platform = "windows"
        self.mock_page.theme_mode = "dark"
        self.mock_page.controls = []
        self.mock_page.clean = MagicMock()
        self.mock_page.add = MagicMock()
        self.mock_page.update = MagicMock()
        self.mock_page.open = MagicMock()
        self.mock_page.favicon = None

        # Patch internal method that fails with mock page
        self.patcher = patch('switchcraft.gui_modern.app.ModernApp._on_notification_update')
        self.mock_notify = self.patcher.start()

        # Patch flet update to avoid "Control must be added to the page first"
        self.patcher_update = patch('flet.Control.update')
        self.mock_update = self.patcher_update.start()

    def tearDown(self):
        self.patcher.stop()
        self.patcher_update.stop()

    def test_navigation_indices_coverage(self):
        """Verify that all items in destinations can be navigated to without 'Unknown Tab'."""
        app = ModernApp(self.mock_page)

        # destinations is populated in build_ui
        # app.destinations should have 20 items (0-19)
        if not hasattr(app, 'destinations'):
             print(f"App attributes: {dir(app)}")
        self.assertTrue(hasattr(app, 'destinations'), "app.destinations not set!")
        count = len(app.destinations)
        print(f"Testing {count} navigation destinations...")

        for i in range(count):
            # Call internal switch
            app._switch_to_tab(i)

            # app.content.controls should have opacity container
            # The container content is new_controls[0]
            # Verify new_controls does NOT contain "Unknown Tab" text control

            # Since content.controls is cleared and appended:
            # self.content.controls.append(fade_container)
            # fade_container.content = new_controls[0]

            fade_container = app.content.controls[-1]
            view_content = fade_container.content

            # If it failed, view_content might be ft.Text("Unknown Tab", color="red")
            is_error = False
            if isinstance(view_content, ft.Text):
                if "Unknown Tab" in view_content.value or "Unknown Category" in view_content.value:
                    is_error = True

            self.assertFalse(is_error, f"Index {i} resulted in Unknown Tab/Category!")

    def test_dynamic_addon_handling(self):
        """Test that dynamic addons logic works (index >= 20)."""
        app = ModernApp(self.mock_page)

        # Mock dynamic addons
        app.dynamic_addons = [{'id': 'test_addon', 'name': 'Test Addon'}]
        # Mock addon service load
        app.addon_service = MagicMock()
        app.addon_service.load_addon_view.return_value = MagicMock()

        # Dynamic index calculation based on static constants
        from switchcraft.gui_modern.nav_constants import NavIndex

        # The test expects dynamic addons to start at EXCHANGE + 1.
        # However, SETTINGS_POLICIES was added at index 21.
        # We should use an index that is guaranteed to be handled as a dynamic addon.
        # Let's find the max static index and use max + 1.
        vals = [v for v in vars(NavIndex).values() if isinstance(v, int)]
        max_static = max(vals) if vals else 22
        target_idx = max_static + 1

        # Override first_dynamic_index to match our target
        app.first_dynamic_index = target_idx

        app._switch_to_tab(target_idx)

        # Check calls
        app.addon_service.load_addon_view.assert_called_with('test_addon')

if __name__ == '__main__':
    unittest.main()
