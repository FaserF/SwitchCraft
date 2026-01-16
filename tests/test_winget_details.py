"""
Tests for Winget Explorer app details display.
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch, Mock
import threading
import time


@pytest.fixture
def mock_page():
    """Create a mock Flet page with run_task support."""
    page = MagicMock(spec=ft.Page)
    page.update = MagicMock()
    page.run_task = lambda func: func()  # Execute immediately for testing

    # Mock page property to avoid RuntimeError
    def get_page():
        return page
    type(page).page = property(lambda self: page)

    return page


@pytest.fixture
def mock_winget_helper():
    """Mock WingetHelper."""
    with patch('switchcraft.gui_modern.views.winget_view.AddonService') as mock_addon:
        mock_addon_instance = MagicMock()
        mock_winget_helper = MagicMock()
        mock_addon_instance.import_addon_module.return_value.WingetHelper.return_value = mock_winget_helper
        mock_addon.return_value = mock_addon_instance
        yield mock_winget_helper


def test_winget_details_loads_and_displays(mock_page, mock_winget_helper):
    """Test that clicking on a Winget app loads and displays details."""
    from switchcraft.gui_modern.views.winget_view import ModernWingetView

    # Mock package details
    short_info = {
        "Id": "Microsoft.PowerToys",
        "Name": "PowerToys",
        "Version": "0.70.0"
    }

    full_details = {
        "Id": "Microsoft.PowerToys",
        "Name": "PowerToys",
        "Version": "0.70.0",
        "Description": "Windows system utilities to maximize productivity.",
        "Publisher": "Microsoft",
        "License": "MIT"
    }

    mock_winget_helper.get_package_details.return_value = full_details

    view = ModernWingetView(mock_page)
    mock_page.add(view)
    view.did_mount()

    # Track UI updates
    details_shown = []
    original_show_details_ui = view._show_details_ui
    def track_show_details_ui(info):
        details_shown.append(info)
        original_show_details_ui(info)
    view._show_details_ui = track_show_details_ui

    # Load details
    view._load_details(short_info)

    # Wait for details to load
    time.sleep(0.3)

    # Check that details were loaded
    assert len(details_shown) > 0
    assert details_shown[0]["Name"] == "PowerToys"
    assert details_shown[0]["Description"] == "Windows system utilities to maximize productivity."

    # Check that details_area was updated
    assert view.details_area is not None
    assert isinstance(view.details_area, ft.Column)
    assert len(view.details_area.controls) > 1  # More than just progress bar

    # Check that right_pane is visible
    assert view.right_pane.visible is True
    assert view.right_pane.content == view.details_area


def test_winget_details_shows_loading_state(mock_page, mock_winget_helper):
    """Test that Winget details shows loading state immediately."""
    from switchcraft.gui_modern.views.winget_view import ModernWingetView

    short_info = {"Id": "Microsoft.PowerToys", "Name": "PowerToys"}

    # Mock slow details loading
    def slow_get_details(package_id):
        time.sleep(0.2)
        return {"Description": "Test description"}
    mock_winget_helper.get_package_details = slow_get_details

    view = ModernWingetView(mock_page)
    mock_page.add(view)
    view.did_mount()

    # Load details
    view._load_details(short_info)

    # Immediately check loading state
    assert view.details_area is not None
    assert isinstance(view.details_area, ft.Column)
    assert len(view.details_area.controls) > 0
    # Should have progress bar
    assert any(isinstance(c, ft.ProgressBar) for c in view.details_area.controls)

    # Check that right_pane is visible
    assert view.right_pane.visible is True


def test_winget_details_shows_error_on_failure(mock_page, mock_winget_helper):
    """Test that Winget details shows error when loading fails."""
    from switchcraft.gui_modern.views.winget_view import ModernWingetView

    short_info = {"Id": "Microsoft.PowerToys", "Name": "PowerToys"}

    # Mock error
    mock_winget_helper.get_package_details.side_effect = Exception("Package not found")

    view = ModernWingetView(mock_page)
    mock_page.add(view)
    view.did_mount()

    # Load details
    view._load_details(short_info)

    # Wait for error handling
    time.sleep(0.3)

    # Check that error was shown
    assert view.details_area is not None
    assert isinstance(view.details_area, ft.Column)
    # Should have error message
    error_texts = []
    def collect_text(control):
        if isinstance(control, ft.Text):
            error_texts.append(control.value)
        elif hasattr(control, 'controls'):
            for c in control.controls:
                collect_text(c)
        elif hasattr(control, 'content'):
            collect_text(control.content)

    collect_text(view.details_area)
    assert any("error" in str(text).lower() or "failed" in str(text).lower() for text in error_texts)


def test_winget_details_updates_ui_correctly(mock_page, mock_winget_helper):
    """Test that Winget details properly updates all UI components."""
    from switchcraft.gui_modern.views.winget_view import ModernWingetView

    short_info = {"Id": "Microsoft.PowerToys", "Name": "PowerToys"}
    full_details = {
        "Id": "Microsoft.PowerToys",
        "Name": "PowerToys",
        "Description": "Test description"
    }

    mock_winget_helper.get_package_details.return_value = full_details

    view = ModernWingetView(mock_page)
    mock_page.add(view)
    view.did_mount()

    # Track update calls
    update_calls = []
    original_update = view.update
    def track_update():
        update_calls.append("view_update")
        original_update()
    view.update = track_update

    page_update_calls = []
    original_page_update = mock_page.update
    def track_page_update():
        page_update_calls.append("page_update")
        original_page_update()
    mock_page.update = track_page_update

    # Load details
    view._load_details(short_info)

    # Wait for details to load
    time.sleep(0.3)

    # Check that updates were called
    assert len(update_calls) > 0 or len(page_update_calls) > 0

    # Check that details_area content was set
    assert view.details_area is not None
    assert view.right_pane.content == view.details_area
    assert view.right_pane.visible is True
