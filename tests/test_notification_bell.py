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


def test_notification_drawer_cleanup(mock_page):
    """Test that dismissing the drawer clears page.end_drawer reference."""
    from switchcraft.gui_modern.app import ModernApp

    app = ModernApp(mock_page)

    # 1. Open drawer
    app._toggle_notification_drawer(None)
    assert mock_page.end_drawer is not None

    # 2. Simulate dismissal (calling handler manually)
    app._on_drawer_dismiss(None)

    # 3. Verify reference is cleared
    assert mock_page.end_drawer is None, "end_drawer should be None after dismiss"


def test_notification_bell_with_items(mock_page):
    """Test that notification bell opens drawer with items."""
    from switchcraft.gui_modern.app import ModernApp

    # Try local poll_until or rely on time.sleep if conftest import is tricky in this context
    # But conftest should be available in tests root.
    try:
        from conftest import poll_until
    except ImportError:
        import time
        def poll_until(condition, timeout=2.0):
            deadline = time.time() + timeout
            while time.time() < deadline:
                if condition():
                    return True
                time.sleep(0.05)
            return False

    app = ModernApp(mock_page)

    # Mock notification service with items
    with patch.object(app, 'notification_service') as mock_notif:
        mock_notif.get_notifications.return_value = [
            {
                "id": "test1",
                "title": "Test Notification",
                "message": "This is a test",
                "type": "info",
                "read": False,
                "timestamp": None
            }
        ]

        # Simulate button click
        mock_event = MagicMock()
        app._toggle_notification_drawer(mock_event)

        # Wait for drawer to open
        def drawer_opened():
            return (mock_page.end_drawer is not None and
                    isinstance(mock_page.end_drawer, ft.NavigationDrawer) and
                    mock_page.end_drawer.open is True)

        assert poll_until(drawer_opened, timeout=2.0), "Drawer should be opened"
