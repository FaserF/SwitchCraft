"""
Tests for language change functionality in settings.
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch
import time


@pytest.fixture
def mock_page():
    """Create a mock Flet page."""
    page = MagicMock(spec=ft.Page)
    page.update = MagicMock()
    page.switchcraft_app = MagicMock()
    page.switchcraft_app.goto_tab = MagicMock()
    page.switchcraft_app._current_tab_index = 0

    # Mock page property
    type(page).page = property(lambda self: page)

    return page


def test_language_change_updates_config(mock_page):
    """Test that language change updates config and i18n."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    with patch('switchcraft.utils.config.SwitchCraftConfig.set_user_preference') as mock_set_pref, \
         patch('switchcraft.utils.i18n.i18n.set_language') as mock_set_lang:

        view = ModernSettingsView(mock_page)
        view.update = MagicMock()

        # Change language
        view._on_lang_change("de")

        # Verify config was updated
        mock_set_pref.assert_called_once_with("Language", "de")

        # Verify i18n was updated
        mock_set_lang.assert_called_once_with("de")

        # Verify view was reloaded (goto_tab called)
        mock_page.switchcraft_app.goto_tab.assert_called()


def test_language_change_shows_restart_message(mock_page):
    """Test that language change shows restart message."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    snack_calls = []
    def track_snack(msg, color):
        snack_calls.append((msg, color))

    view = ModernSettingsView(mock_page)
    view._show_snack = track_snack
    view.update = MagicMock()

    with patch('switchcraft.utils.config.SwitchCraftConfig.set_user_preference'), \
         patch('switchcraft.utils.i18n.i18n.set_language'):

        view._on_lang_change("de")

        # Should show restart message
        assert len(snack_calls) > 0
        assert any("restart" in str(call[0]).lower() for call in snack_calls)
