"""
Tests for Group Manager View interactions (Create, Members, Delete, etc.).
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch
import time
from conftest import poll_until, _create_mock_page

def test_group_manager_create_button():
    """Test that Group Manager create button opens dialog."""
    from switchcraft.gui_modern.views.group_manager_view import GroupManagerView

    mock_page = _create_mock_page()

    # Mock credentials check
    with patch.object(GroupManagerView, '_has_credentials', return_value=True):
        view = GroupManagerView(mock_page)

        # Find create button
        create_btn = view.create_btn

        assert create_btn is not None, "Create button should exist"
        assert create_btn.on_click is not None, "Create button should have on_click handler"

        # Mock token
        view.token = "test_token"

        # Simulate click
        mock_event = MagicMock()
        create_btn.on_click(mock_event)

        # Wait for dialog to open
        def dialog_opened():
            return mock_page.dialog is not None and isinstance(mock_page.dialog, ft.AlertDialog)

        assert poll_until(dialog_opened, timeout=2.0), "Create dialog should be opened"


def test_group_manager_members_button():
    """Test that Group Manager members button opens dialog when group is selected."""
    from switchcraft.gui_modern.views.group_manager_view import GroupManagerView

    mock_page = _create_mock_page()

    # Mock credentials check
    with patch.object(GroupManagerView, '_has_credentials', return_value=True):
        view = GroupManagerView(mock_page)

        # Mock token and selected group
        view.token = "test_token"
        view.selected_group = {
            'id': 'test-group-id',
            'displayName': 'Test Group'
        }
        view.members_btn.disabled = False

        # Mock intune service
        with patch.object(view.intune_service, 'list_group_members', return_value=[]):
            # Simulate click
            mock_event = MagicMock()
            view.members_btn.on_click(mock_event)

            # Wait for dialog to open
            def dialog_opened():
                return mock_page.dialog is not None and isinstance(mock_page.dialog, ft.AlertDialog)

            assert poll_until(dialog_opened, timeout=2.0), "Members dialog should be opened"


def test_group_manager_delete_toggle():
    """Test that Group Manager delete toggle enables/disables delete button."""
    from switchcraft.gui_modern.views.group_manager_view import GroupManagerView

    mock_page = _create_mock_page()

    # Mock credentials check
    with patch.object(GroupManagerView, '_has_credentials', return_value=True):
        view = GroupManagerView(mock_page)

        # Select a group
        view.selected_group = {'id': 'test-group-id', 'displayName': 'Test Group'}

        # Initially disabled
        assert view.delete_btn.disabled is True, "Delete button should be disabled initially"

        # Enable toggle
        view.delete_toggle.value = True
        mock_event = MagicMock()
        view.delete_toggle.on_change(mock_event)

        # Wait a bit for UI update
        time.sleep(0.1)

        # Delete button should now be enabled
        assert view.delete_btn.disabled is False, "Delete button should be enabled when toggle is on and group is selected"


def test_group_manager_delete_button():
    """Test that Group Manager delete button opens confirmation dialog."""
    from switchcraft.gui_modern.views.group_manager_view import GroupManagerView

    mock_page = _create_mock_page()

    # Mock credentials check
    with patch.object(GroupManagerView, '_has_credentials', return_value=True):
        view = GroupManagerView(mock_page)

        # Set up state
        view.token = "test_token"
        view.selected_group = {'id': 'test-group-id', 'displayName': 'Test Group'}
        view.delete_toggle.value = True
        view.delete_btn.disabled = False

        # Mock intune service
        with patch.object(view.intune_service, 'delete_group', return_value=None):
            # Simulate click
            mock_event = MagicMock()
            view.delete_btn.on_click(mock_event)

            # Wait for dialog to open
            def dialog_opened():
                return mock_page.dialog is not None and isinstance(mock_page.dialog, ft.AlertDialog)

            assert poll_until(dialog_opened, timeout=2.0), "Delete confirmation dialog should be opened"
