import unittest
from unittest.mock import MagicMock, patch
import flet as ft
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


class TestPackagingWizard(unittest.TestCase):
    def setUp(self):
        self.page = MagicMock(spec=ft.Page)
        self.page.switchcraft_session = {}
        self.page.show_snack_bar = MagicMock()
        self.page.update = MagicMock()

    def test_packaging_wizard_initialization(self):
        """Test that PackagingWizardView initializes correctly."""
        from switchcraft.gui_modern.views.packaging_wizard_view import PackagingWizardView

        view = PackagingWizardView(self.page)
        self.assertIsNotNone(view)

    def test_packaging_wizard_with_pending_app(self):
        """Test PackagingWizardView with pending app data from session."""
        from switchcraft.gui_modern.views.packaging_wizard_view import PackagingWizardView

        # Set up pending app in session
        pending_app = {
            "displayName": "Test App",
            "publisher": "Test Publisher",
            "description": "Test Description"
        }
        self.page.switchcraft_session["pending_packaging_app"] = pending_app

        view = PackagingWizardView(self.page)

        # Simulate did_mount (which would normally be called by Flet)
        if hasattr(view, 'did_mount'):
            view.did_mount()

        # Verify that upload_info was populated
        if hasattr(view, 'upload_info'):
            self.assertEqual(view.upload_info["displayName"], "Test App")
            self.assertEqual(view.upload_info["publisher"], "Test Publisher")

    def test_packaging_wizard_clears_session(self):
        """Test that PackagingWizardView clears pending app from session after use."""
        from switchcraft.gui_modern.views.packaging_wizard_view import PackagingWizardView

        pending_app = {
            "displayName": "Test App",
            "publisher": "Test Publisher"
        }
        self.page.switchcraft_session["pending_packaging_app"] = pending_app

        view = PackagingWizardView(self.page)

        # After did_mount, session should be cleared
        if hasattr(view, 'did_mount'):
            view.did_mount()

        # Session should be cleared (set to None)
        self.assertIsNone(self.page.switchcraft_session.get("pending_packaging_app"))


if __name__ == '__main__':
    unittest.main()
