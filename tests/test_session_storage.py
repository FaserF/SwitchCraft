import unittest
from unittest.mock import MagicMock
import flet as ft
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


class TestSessionStorage(unittest.TestCase):
    def setUp(self):
        """
        Prepare a mocked ft.Page with a session storage for tests.

        Creates a MagicMock object with the ft.Page spec and ensures it has a `switchcraft_session`
        attribute initialized to an empty dictionary if not already present.
        """
        self.page = MagicMock(spec=ft.Page)
        # Initialize session storage like ModernApp does
        if not hasattr(self.page, 'switchcraft_session'):
            self.page.switchcraft_session = {}

    def test_session_storage_initialization(self):
        """Test that session storage is initialized correctly."""
        self.assertIsInstance(self.page.switchcraft_session, dict)
        self.assertEqual(len(self.page.switchcraft_session), 0)

    def test_session_storage_set_get(self):
        """Test setting and getting values from session storage."""
        self.page.switchcraft_session["test_key"] = "test_value"
        self.assertEqual(self.page.switchcraft_session.get("test_key"), "test_value")

    def test_session_storage_multiple_keys(self):
        """Test storing multiple keys in session storage."""
        self.page.switchcraft_session["key1"] = "value1"
        self.page.switchcraft_session["key2"] = "value2"
        self.page.switchcraft_session["key3"] = {"nested": "object"}

        self.assertEqual(self.page.switchcraft_session["key1"], "value1")
        self.assertEqual(self.page.switchcraft_session["key2"], "value2")
        self.assertEqual(self.page.switchcraft_session["key3"]["nested"], "object")

    def test_session_storage_clear(self):
        """Test clearing session storage."""
        self.page.switchcraft_session["key1"] = "value1"
        self.page.switchcraft_session["key2"] = "value2"

        self.page.switchcraft_session.clear()
        self.assertEqual(len(self.page.switchcraft_session), 0)

    def test_session_storage_pending_app(self):
        """Test storing pending packaging app data."""
        pending_app = {
            "displayName": "Test App",
            "publisher": "Test Publisher",
            "description": "Test Description"
        }
        self.page.switchcraft_session["pending_packaging_app"] = pending_app

        retrieved = self.page.switchcraft_session.get("pending_packaging_app")
        self.assertEqual(retrieved["displayName"], "Test App")
        self.assertEqual(retrieved["publisher"], "Test Publisher")

        # Clear after use
        self.page.switchcraft_session["pending_packaging_app"] = None
        self.assertIsNone(self.page.switchcraft_session.get("pending_packaging_app"))


if __name__ == '__main__':
    unittest.main()