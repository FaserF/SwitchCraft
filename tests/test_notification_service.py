import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from switchcraft.services.notification_service import NotificationService


class TestNotificationService(unittest.TestCase):
    def setUp(self):
        # Clear singleton instance to start fresh
        NotificationService._instance = None
        self.service = NotificationService()
        # Clear any existing notifications for clean test state
        initial_count = len(self.service.notifications)
        if initial_count > 0:
            self.service.clear_all()

    def test_notification_service_initialization(self):
        """Test that NotificationService initializes correctly."""
        self.assertIsNotNone(self.service)
        self.assertIsInstance(self.service.notifications, list)

    def test_add_notification(self):
        """Test adding a notification."""
        initial_count = len(self.service.notifications)
        self.service.add_notification("Test Title", "Test Message", "info")
        self.assertEqual(len(self.service.notifications), initial_count + 1)
        self.assertEqual(self.service.notifications[0]["title"], "Test Title")
        self.assertEqual(self.service.notifications[0]["message"], "Test Message")
        self.assertEqual(self.service.notifications[0]["type"], "info")

    def test_get_unread_count(self):
        """Test getting unread notification count."""
        initial_count = len(self.service.notifications)
        self.service.add_notification("Title 1", "Message 1", "info")
        self.service.add_notification("Title 2", "Message 2", "warning")
        # Mark first one as read
        if len(self.service.notifications) > 0:
            self.service.notifications[0]["read"] = True

        unread_count = self.service.get_unread_count()
        # Should have at least 1 unread (the second one)
        self.assertGreaterEqual(unread_count, 1)

    def test_mark_all_read(self):
        """Test marking all notifications as read."""
        self.service.add_notification("Title 1", "Message 1", "info")
        self.service.add_notification("Title 2", "Message 2", "warning")

        self.service.mark_all_read()
        for notification in self.service.notifications:
            self.assertTrue(notification["read"])

    def test_clear_notifications(self):
        """Test clearing all notifications."""
        self.service.add_notification("Title 1", "Message 1", "info")
        self.service.add_notification("Title 2", "Message 2", "warning")

        self.service.clear_all()
        self.assertEqual(len(self.service.notifications), 0)

    def test_get_notifications(self):
        """Test getting all notifications."""
        self.service.add_notification("Title 1", "Message 1", "info")
        self.service.add_notification("Title 2", "Message 2", "warning")
        self.service.add_notification("Title 3", "Message 3", "error")

        all_notifications = self.service.get_notifications()
        # Should have at least 3 notifications
        self.assertGreaterEqual(len(all_notifications), 3)
        # Most recent should be first (inserted at index 0)
        self.assertEqual(all_notifications[0]["title"], "Title 3")


if __name__ == '__main__':
    unittest.main()
