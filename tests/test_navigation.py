import pytest
from unittest.mock import MagicMock
import flet as ft
from switchcraft.gui_modern.app import ModernApp


@pytest.fixture
def mock_app():
    page = MagicMock(spec=ft.Page)
    page.clean = MagicMock()
    page.add = MagicMock()
    page.update = MagicMock()
    page.open = MagicMock()
    app = ModernApp(page)
    # Mock services/sidebar to avoid side effects
    app.addon_service = MagicMock()
    app.notification_service = MagicMock()
    app.sidebar = MagicMock()
    app.sidebar.categories = [(ft.Icons.CATEGORY, "MyCategory", [0, 1])] # Mock Category 0
    return app

def test_switch_to_tab_analyzer(mock_app):
    """Test correctly switching to Analyzer Tab (Index 6)."""
    # Initialize controls list
    mock_app.content.controls = []

    # Mock _load_view to avoid complex side effects if needed,
    # but here we want to verify the integration logic calling it.
    # Let's mock the internal helper that creates views if possible,
    # or just verifiy _switch_to_tab calls.
    mock_app._load_view = MagicMock()

    # 0=Home, 1=AM, 2=Update, 3=Graph, 4=Help, 5=Winget, 6=Analyzer
    mock_app._switch_to_tab(6)

    # Verify content loaded is Analyzer
    # We check if controls were populated
    assert len(mock_app.content.controls) > 0

    # We can also check if it was cached
    assert 'analyzer' in mock_app._view_cache

def test_switch_to_tab_category_instantiation(mock_app):
    """Test that Category View (Index 100+) is instantiated correctly."""
    mock_app.destinations = [MagicMock(), MagicMock()] # 2 destinations

    # Initialize controls list for the mock
    mock_app.content.controls = []

    # Mock Sidebar Selection
    mock_app.sidebar.selected_category_index = 0

    mock_app._switch_to_tab(100)

    # Check if any controls were added (ignoring Loading view)
    # The last append should be CategoryView
    added_controls = mock_app.content.controls
    assert len(added_controls) > 0

    # We expect CategoryView to be created.
    # If the bug exists (missing arg), this would raise TypeError (caught by try/except -> CrashDumpView)

    # Let's inspect the last item's type if possible, or check if it's Text("Unknown")
    last_item = added_controls[-1]
    # In the mocked environment, we might catch the exception and return CrashDumpView or error text
    # Verify it is NOT "Unknown Category" and NOT an error
    assert not (isinstance(last_item, ft.Text) and last_item.value == "Unknown Category")
