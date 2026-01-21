"""
E2E Test for Winget View Flow
Simulates the user journey:
1. Initialize Winget View
2. Search for a package
3. Select a package from results
4. Verify details panel loads correct data
"""
import pytest
from unittest.mock import MagicMock, patch
import flet as ft
from conftest import poll_until, _create_mock_page

@pytest.fixture
def mock_winget_deps():
    with patch("switchcraft.gui_modern.views.winget_view.AddonService") as mock_addon:
        mock_instance = MagicMock()
        mock_helper = MagicMock()

        # Setup mock return chain
        mock_addon.return_value = mock_instance
        mock_instance.import_addon_module.return_value.WingetHelper.return_value = mock_helper

        yield mock_helper

def test_winget_e2e_flow(mock_winget_deps):
    """
    Test complete Winget search and selection flow.
    """
    from switchcraft.gui_modern.views.winget_view import ModernWingetView

    # Mock Data
    mock_results = [
        {"Id": "Test.App.1", "Name": "Test App One", "Version": "1.0", "Source": "winget"},
        {"Id": "Test.App.2", "Name": "Test App Two", "Version": "2.0", "Source": "winget"}
    ]

    mock_details = {
        "Id": "Test.App.1",
        "Name": "Test App One",
        "Version": "1.0",
        "Description": "This is a detailed description of Test App One.",
        "Publisher": "Test Publisher",
        "License": "MIT"
    }

    mock_winget_deps.search_packages.return_value = mock_results
    mock_winget_deps.get_package_details.return_value = mock_details

    # 1. Initialize View
    mock_page = _create_mock_page()
    view = ModernWingetView(mock_page)
    view.update = MagicMock()

    # 2. Perform Search
    # Find search field directly
    search_field = view.search_field

    # Input query
    search_field.value = "Test App"

    # Click Search
    # Invoke handler directly instead of traversing UI tree which is brittle
    mock_event = MagicMock()
    view._run_search(mock_event)

    # Wait for results
    def results_loaded():
        return len(view.search_results.controls) > 0 and len(view.results_list.controls) > 0 if hasattr(view, 'results_list') else len(view.search_results.controls) > 0

    # Note: ModernWingetView clears search_results and appends a "Searching" container, then clears and appends results.
    # The actual list is view.search_results which contains tiles.
    # But wait, does it have a 'results_list' property?
    # Checking code: self.search_results = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    # It populates self.search_results.controls with ListTile.
    # So we check len(view.search_results.controls)

    # However, initially it appends "Searching..." container (count=1).
    # Then it clears and adds results (count=2).
    # We need to wait for tiles.

    def tiles_loaded():
        controls = view.search_results.controls
        if len(controls) == 0: return False
        # Check if first item is a ListTile or if we have >1 item (if results > 0)
        # OR check if "Searching..." text is gone.
        return len(controls) == 2 and isinstance(controls[0], ft.ListTile)

    assert poll_until(tiles_loaded, timeout=3.0), "Results should populate list"

    # 3. Verify Results
    list_items = view.search_results.controls
    assert len(list_items) == 2
    first_item = list_items[0]
    # Check title/text of ListTile
    assert first_item.title.value == "Test App One"

    # 4. Select Package (Click Item)
    # Trigger on_click of the first result item wrapper
    # The view wraps handlers.

    # We can just check that on_click is callable.
    assert callable(first_item.on_click)

    # To verify details loading, we call _load_details directly to avoid event simulation complexity
    # OR we invoke the lambda. Invoking lambda is tricky as it's wrapped.
    # Let's call _load_details directly to verify the Logic flow.
    # This is a unit/integration test hybrid.

    view._load_details(mock_results[0])

    # 5. Verify Details Load
    # Check RIGHT PANE visibility and content
    def details_visible():
        return view.right_pane.visible and view.details_area is not None and len(view.details_area.controls) > 0

    assert poll_until(details_visible, timeout=3.0), "Details pane should become visible"

    # Verify details content
    # We look for the description text in the details area
    found_description = False

    def find_text(control, target_text):
        if isinstance(control, ft.Text) and control.value and target_text in control.value:
            return True
        if hasattr(control, "controls"):
            for child in control.controls:
                if find_text(child, target_text):
                    return True
        if hasattr(control, "content") and control.content:
            if find_text(control.content, target_text):
                return True
        return False

    # Need to wait for async detail fetch (thread)
    def description_loaded():
        return find_text(view.details_area, "detailed description")

    assert poll_until(description_loaded, timeout=3.0), "Description should be displayed in details area"

if __name__ == "__main__":
    pytest.main([__file__])
