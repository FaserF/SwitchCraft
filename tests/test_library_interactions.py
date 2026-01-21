"""
Tests for Library View interactions (Folder button, Refresh button, etc.).
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch
import time
from conftest import poll_until, _create_mock_page

def test_library_view_folder_button():
    """Test that Library View folder button opens dialog."""
    from switchcraft.gui_modern.views.library_view import LibraryView

    # Use helper to create mock page
    mock_page = _create_mock_page()

    view = LibraryView(mock_page)

    # Find folder button
    folder_btn = None
    def find_folder_button(control):
        if isinstance(control, ft.IconButton):
            if hasattr(control, 'icon') and control.icon == ft.Icons.FOLDER_OPEN:
                return control
        if hasattr(control, 'controls'):
            for child in control.controls:
                result = find_folder_button(child)
                if result:
                    return result
        if hasattr(control, 'content'):
            result = find_folder_button(control.content)
            if result:
                return result
        return None

    folder_btn = find_folder_button(view)

    assert folder_btn is not None, "Folder button should exist"
    assert folder_btn.on_click is not None, "Folder button should have on_click handler"

    # Simulate click
    mock_event = MagicMock()
    folder_btn.on_click(mock_event)

    # Wait for dialog to open
    def dialog_opened():
        return mock_page.dialog is not None and isinstance(mock_page.dialog, ft.AlertDialog)

    assert poll_until(dialog_opened, timeout=2.0), "Dialog should be opened"


def test_library_view_refresh_button():
    """Test that Library View refresh button loads data."""
    from switchcraft.gui_modern.views.library_view import LibraryView

    mock_page = _create_mock_page()

    with patch.object(LibraryView, '_load_data') as mock_load_data:
        view = LibraryView(mock_page)

        # Find refresh button
        refresh_btn = None
        def find_refresh_button(control):
            if isinstance(control, ft.IconButton):
                if hasattr(control, 'icon') and control.icon == ft.Icons.REFRESH:
                    return control
            if hasattr(control, 'controls'):
                for child in control.controls:
                    result = find_refresh_button(child)
                    if result:
                        return result
            if hasattr(control, 'content'):
                result = find_refresh_button(control.content)
                if result:
                    return result
            return None

        refresh_btn = find_refresh_button(view)

        assert refresh_btn is not None, "Refresh button should exist"
        assert refresh_btn.on_click is not None, "Refresh button should have on_click handler"

        # Reset mock causing by init/other calls if any
        mock_load_data.reset_mock()

        # Simulate click
        mock_event = MagicMock()
        refresh_btn.on_click(mock_event)

        # Wait a bit
        time.sleep(0.1)

        # Verify call
        assert mock_load_data.called, "Refresh button should trigger _load_data method"
