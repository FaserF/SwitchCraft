"""
Tests for notification bell button functionality.
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch
import time


@pytest.fixture
def mock_page():
    """Create a mock Flet page."""
    page = MagicMock(spec=ft.Page)
    page.end_drawer = None
    page.update = MagicMock()
    page.open = MagicMock()
    page.close = MagicMock()
    page.snack_bar = None

    # Mock page property
    type(page).page = property(lambda self: page)

    return page


def test_notification_bell_opens_drawer(mock_page):
    """Test that clicking notification bell opens the drawer."""
    from switchcraft.gui_modern.app import ModernApp

    app = ModernApp(mock_page)

    # Mock notification service
    app.notification_service.get_notifications = MagicMock(return_value=[])

    # Click notification bell
    app._toggle_notification_drawer(None)

    # Wait a bit for drawer to open
    time.sleep(0.1)

    # Check that drawer was created and opened
    assert mock_page.end_drawer is not None
    assert isinstance(mock_page.end_drawer, ft.NavigationDrawer)
    assert mock_page.end_drawer.open is True

    # Verify update was called
    assert mock_page.update.called


def test_notification_bell_toggles_drawer(mock_page):
    """Test that clicking notification bell toggles drawer open/closed."""
    from switchcraft.gui_modern.app import ModernApp

    app = ModernApp(mock_page)

    # Mock notification service
    app.notification_service.get_notifications = MagicMock(return_value=[])

    # First click - should open
    app._toggle_notification_drawer(None)
    time.sleep(0.1)

    assert mock_page.end_drawer is not None
    assert mock_page.end_drawer.open is True

    # Second click - should close
    app._toggle_notification_drawer(None)
    time.sleep(0.1)

    # Drawer should be closed
    assert mock_page.end_drawer.open is False
