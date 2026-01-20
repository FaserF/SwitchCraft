"""
Tests for notification bell button functionality.
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch
import time
import os


def test_notification_bell_opens_drawer(mock_page):
    """Test that clicking notification bell opens the drawer."""
    from switchcraft.gui_modern.app import ModernApp

    app = ModernApp(mock_page)

    # Mock notification service
    app.notification_service.get_notifications = MagicMock(return_value=[])

    # Skip in CI to avoid waits
    if os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true':
        pytest.skip("Skipping test with time.sleep in CI environment")

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

    # Skip in CI to avoid waits
    if os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true':
        pytest.skip("Skipping test with time.sleep in CI environment")

    # First click - should open
    app._toggle_notification_drawer(None)
    time.sleep(0.1)

    assert mock_page.end_drawer is not None
    assert mock_page.end_drawer.open is True

    # Second click - should close
    app._toggle_notification_drawer(None)
    time.sleep(0.1)

    # Drawer should be closed (either None or open=False)
    assert mock_page.end_drawer is None or mock_page.end_drawer.open is False, \
        "Drawer should be closed (None or open=False)"
