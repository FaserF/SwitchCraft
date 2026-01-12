import pytest
import flet as ft
from switchcraft.gui_modern.app import ModernApp

def test_modern_app_import():
    """Simple smoke test to ensure module can be imported without error."""
    assert ModernApp is not None

def test_modern_app_instantiation():
    """Test that ModernApp can be instantiated with a mock page."""
    # Mocking ft.Page is tricky as it's complex, but for basic init we can try a dummy class
    class MockPage:
        def __init__(self):
            self.title = ""
            self.theme_mode = None
            self.padding = 0
            self.window = type('obj', (object,), {'min_width': 0, 'min_height': 0})
            self.controls = []
            self.banner_container = None
            self.dialog = None
            self.platform = "windows"
            self.route = "/"

        def clean(self):
            pass

        def add(self, *args):
            pass

        def update(self):
            pass

    mock_page = MockPage()
    try:
        app = ModernApp(mock_page)
        assert app is not None
    except Exception as e:
        pytest.fail(f"ModernApp instantiation failed: {e}")

def test_view_imports():
    """Ensure all view modules can be imported."""
    from switchcraft.gui_modern.views import (
        home_view,
        analyzer_view,
        helper_view,
        winget_view,
        intune_view,
        intune_store_view,
        history_view,
        settings_view
    )
    assert home_view is not None
    assert analyzer_view is not None
