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


    def test_language_switch_functionality(self):
        """Test that language switch actually changes language (Interaction Test)."""
        from switchcraft.gui_modern.views.settings_view import ModernSettingsView
        from switchcraft.utils.i18n import i18n
        import flet as ft
        import time
        from unittest.mock import MagicMock

        view = ModernSettingsView(self.page)
        # Manually add view to page controls to satisfy Flet's requirement
        self.page.controls = [view]
        view._page = self.page

        # Find language dropdown
        general_tab = view._build_general_tab()
        lang_dd = None

        def find_dropdown(control):
            if isinstance(control, ft.Dropdown):
                if hasattr(control, 'options') and control.options:
                    option_values = [opt.key if hasattr(opt, 'key') else str(opt) for opt in control.options]
                    if 'en' in option_values and 'de' in option_values:
                        return control
            if hasattr(control, 'controls'):
                for child in control.controls:
                    result = find_dropdown(child)
                    if result:
                        return result
            if hasattr(control, 'content'):
                result = find_dropdown(control.content)
                if result:
                    return result
            return None

        lang_dd = find_dropdown(general_tab)

        assert lang_dd is not None, "Language dropdown should exist"
        assert lang_dd.on_change is not None, "Language dropdown should have on_change handler"

        # Simulate language change
        mock_event = MagicMock()
        mock_event.control = lang_dd
        lang_dd.value = "de"

        # Call handler
        lang_dd.on_change(mock_event)

        # Verify language was changed or UI was reloaded
        # Wait a bit for async operations
        time.sleep(0.2)
        assert self.page.switchcraft_app.goto_tab.called or self.page.dialog.open, "Language change should trigger UI reload or dialog"


if __name__ == '__main__':
    unittest.main()