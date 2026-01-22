"""
Tests for language change functionality in settings.
"""
from unittest.mock import MagicMock, patch





def test_language_change_updates_config(mock_page):
    """Test that language change updates config and shows restart dialog."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    with patch('switchcraft.utils.config.SwitchCraftConfig.set_user_preference') as mock_set_pref:
        view = ModernSettingsView(mock_page)
        view.update = MagicMock()
        view._page = mock_page

        # Change language
        view._on_lang_change("de")

        # Verify config was updated
        mock_set_pref.assert_called_once_with("Language", "de")

        # Verify restart dialog shown
        assert mock_page.dialog is not None
        assert mock_page.dialog.open is True


def test_language_change_shows_restart_dialog_content(mock_page):
    """Test that language change restart dialog has correct content."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    view = ModernSettingsView(mock_page)
    view._page = mock_page
    view.update = MagicMock()

    with patch('switchcraft.utils.config.SwitchCraftConfig.set_user_preference'):
        view._on_lang_change("de")

        assert mock_page.dialog is not None
        assert mock_page.dialog.open is True

        # Check title
        assert "Restart" in mock_page.dialog.title.value or "Neustart" in mock_page.dialog.title.value
