import unittest
from unittest.mock import patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Import shared helper function
from conftest import _create_mock_page


class TestSettingsLanguage(unittest.TestCase):
    def setUp(self):
        """
        Prepare test fixtures using shared mock_page fixture from conftest.
        """
        self.page = _create_mock_page()

    @patch('switchcraft.utils.config.SwitchCraftConfig.set_user_preference')
    def test_language_change_immediate(self, mock_set_pref):
        """Test that language change saves preference and shows restart dialog."""
        from switchcraft.gui_modern.views.settings_view import ModernSettingsView

        view = ModernSettingsView(self.page)
        # Manually add view to page controls to satisfy Flet's requirement
        self.page.controls = [view]
        view._page = self.page

        # Simulate language change
        view._on_lang_change("en")

        # Verify config was updated
        mock_set_pref.assert_called_once_with("Language", "en")

        # Verify restart dialog was shown instead of immediate reload
        assert self.page.dialog is not None
        assert self.page.dialog.open is True
        # Verify goto_tab was NOT called
        self.page.switchcraft_app.goto_tab.assert_not_called()

    @patch('switchcraft.utils.config.SwitchCraftConfig.set_user_preference')
    def test_language_change_german(self, mock_set_pref):
        """Test changing language to German shows restart dialog."""
        from switchcraft.gui_modern.views.settings_view import ModernSettingsView

        view = ModernSettingsView(self.page)
        # Manually add view to page controls to satisfy Flet's requirement
        self.page.controls = [view]
        view._page = self.page

        view._on_lang_change("de")

        mock_set_pref.assert_called_once_with("Language", "de")
        assert self.page.dialog is not None
        assert self.page.dialog.open is True

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