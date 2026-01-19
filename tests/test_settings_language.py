import unittest
from unittest.mock import MagicMock, patch
import flet as ft
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


class TestSettingsLanguage(unittest.TestCase):
    def setUp(self):
        """
        Prepare test fixtures: create a mocked `ft.Page` and attach a mocked `switchcraft_app`.

        The mocked page is assigned to `self.page`. A `switchcraft_app` mock is attached with an initial
        `_current_tab_index` of 0 and a `goto_tab` mock. The page's `show_snack_bar` is also mocked.
        """
        self.page = MagicMock(spec=ft.Page)
        self.page.switchcraft_app = MagicMock()
        self.page.switchcraft_app._current_tab_index = 0
        self.page.switchcraft_app.goto_tab = MagicMock()
        self.page.show_snack_bar = MagicMock()

    @patch('switchcraft.utils.config.SwitchCraftConfig.set_user_preference')
    @patch('switchcraft.utils.i18n.i18n.set_language')
    def test_language_change_immediate(self, mock_set_language, mock_set_pref):
        """Test that language change is applied immediately."""
        from switchcraft.gui_modern.views.settings_view import ModernSettingsView

        view = ModernSettingsView(self.page)
        # Ensure run_task is available for UI updates
        self.page.run_task = lambda func: func()

        # Simulate language change
        view._on_lang_change("en")

        # Verify config was updated
        mock_set_pref.assert_called_once_with("Language", "en")

        # Verify i18n was updated
        mock_set_language.assert_called_once_with("en")

        # Verify view reload was triggered
        self.page.switchcraft_app.goto_tab.assert_called_once_with(0)

    @patch('switchcraft.utils.config.SwitchCraftConfig.set_user_preference')
    @patch('switchcraft.utils.i18n.i18n.set_language')
    def test_language_change_german(self, mock_set_language, mock_set_pref):
        """Test changing language to German."""
        from switchcraft.gui_modern.views.settings_view import ModernSettingsView

        view = ModernSettingsView(self.page)
        view._on_lang_change("de")

        mock_set_pref.assert_called_once_with("Language", "de")
        mock_set_language.assert_called_once_with("de")

    @patch('switchcraft.utils.config.SwitchCraftConfig.get_value')
    def test_build_date_display(self, mock_get_value):
        """Test that build date is displayed in settings."""
        from switchcraft.gui_modern.views.settings_view import ModernSettingsView

        view = ModernSettingsView(self.page)
        build_date = view._get_build_date()

        # Build date should be a string
        self.assertIsInstance(build_date, str)
        self.assertGreater(len(build_date), 0)


if __name__ == '__main__':
    unittest.main()