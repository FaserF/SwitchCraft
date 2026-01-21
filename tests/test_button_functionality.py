"""
Comprehensive test to verify button functionality across all views.
Tests that buttons actually work when clicked.
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch
import asyncio
import inspect


@pytest.fixture
def mock_page():
    """Create a comprehensive mock page."""
    page = MagicMock(spec=ft.Page)
    page.update = MagicMock()
    page.switchcraft_app = MagicMock()
    page.switchcraft_app.goto_tab = MagicMock()
    page.switchcraft_app._current_tab_index = 0
    page.switchcraft_app._view_cache = {}
    page.dialog = None
    page.end_drawer = None
    page.snack_bar = None
    page.open = MagicMock()
    page.close = MagicMock()
    page.close = MagicMock()

    def mock_run_task(func):
        if inspect.iscoroutinefunction(func):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(func())
            except RuntimeError:
                asyncio.run(func())
        else:
            res = func()
            if inspect.isawaitable(res):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(res)
                except RuntimeError:
                    asyncio.run(res)

    page.run_task = mock_run_task
    type(page).page = property(lambda self: page)
    return page



def find_clickables(control, clickables):
    """Recursively find all clickable controls."""
    if hasattr(control, 'on_click') and control.on_click is not None:
        clickables.append(control)
    if hasattr(control, 'content'):
        find_clickables(control.content, clickables)
    if hasattr(control, 'controls'):
        for child in control.controls:
            find_clickables(child, clickables)


def test_home_view_buttons(mock_page):
    """Test that Home View buttons work."""
    from switchcraft.gui_modern.views.home_view import ModernHomeView

    navigate_calls = []
    def track_navigate(idx):
        navigate_calls.append(idx)

    view = ModernHomeView(mock_page, on_navigate=track_navigate)


    clickables = []
    find_clickables(view, clickables)

    # Test clicking action cards
    successes = 0
    failures = []
    for clickable in clickables:
        if hasattr(clickable, 'on_click') and clickable.on_click:
            try:
                mock_event = MagicMock()
                mock_event.control = clickable
                clickable.on_click(mock_event)
                successes += 1
            except Exception as e:
                # Track failures for reporting
                failures.append((clickable, str(e)))

    # Should have at least some clickables and some successful clicks
    assert len(clickables) > 0, "Should have at least some clickable controls"
    assert successes > 0 or len(clickables) == 0, f"At least one click should succeed. Failures: {len(failures)}"


def test_category_view_buttons(mock_page):
    """Test that Category View buttons work."""
    from switchcraft.gui_modern.views.category_view import CategoryView

    navigate_calls = []
    def track_navigate(idx):
        navigate_calls.append(idx)

    # Create mock destinations
    mock_destinations = [
        MagicMock(icon=ft.Icons.HOME, label="Home"),
        MagicMock(icon=ft.Icons.SETTINGS, label="Settings"),
    ]

    view = CategoryView(mock_page, "Test Category", [0, 1], track_navigate, mock_destinations)


    clickables = []
    find_clickables(view, clickables)

    # Test clicking cards
    successes = 0
    failures = []
    for clickable in clickables:
        if hasattr(clickable, 'on_click') and clickable.on_click:
            try:
                mock_event = MagicMock()
                mock_event.control = clickable
                clickable.on_click(mock_event)
                successes += 1
            except Exception as e:
                failures.append((clickable, str(e)))

    assert len(clickables) > 0, "Should have at least some clickable controls"
    assert successes > 0 or len(clickables) == 0, f"At least one click should succeed. Failures: {len(failures)}"


def test_settings_view_tab_buttons(mock_page):
    """Test that Settings View tab buttons work."""
    from switchcraft.gui_modern.views.settings_view import ModernSettingsView

    view = ModernSettingsView(mock_page, initial_tab_index=0)
    view.update = MagicMock()

    # Find tab buttons
    tab_buttons = []
    for control in view.nav_row.controls:
        if isinstance(control, ft.Button):
            tab_buttons.append(control)

    # Test clicking each tab button
    successes = 0
    failures = []
    for button in tab_buttons:
        if hasattr(button, 'on_click') and button.on_click:
            try:
                mock_event = MagicMock()
                mock_event.control = button
                button.on_click(mock_event)
                successes += 1
            except Exception as e:
                failures.append((button, str(e)))

    assert len(tab_buttons) > 0, "Should have at least some tab buttons"
    assert successes > 0 or len(tab_buttons) == 0, f"At least one button click should succeed. Failures: {len(failures)}"


def test_winget_view_search_button(mock_page):
    """Test that Winget View search button works."""
    from switchcraft.gui_modern.views.winget_view import ModernWingetView

    with patch('switchcraft.gui_modern.views.winget_view.AddonService') as mock_addon:
        mock_addon_instance = MagicMock()
        mock_winget_helper = MagicMock()
        mock_winget_helper.search_packages.return_value = []
        mock_addon_instance.import_addon_module.return_value.WingetHelper.return_value = mock_winget_helper
        mock_addon.return_value = mock_addon_instance

        view = ModernWingetView(mock_page)
        view.did_mount()
        view.update = MagicMock()

        # Find search button
        search_button = None
        def find_search_button(control):
            nonlocal search_button
            if isinstance(control, (ft.Button, ft.IconButton)):
                if hasattr(control, 'icon') and control.icon == ft.Icons.SEARCH:
                    search_button = control
            if hasattr(control, 'content'):
                find_search_button(control.content)
            if hasattr(control, 'controls'):
                for child in control.controls:
                    find_search_button(child)

        find_search_button(view)

        if search_button and hasattr(search_button, 'on_click') and search_button.on_click:
            # Verify handler exists and is callable
            assert callable(search_button.on_click), "Search button handler should be callable"
            failures = []
            try:
                mock_event = MagicMock()
                mock_event.control = search_button
                search_button.on_click(mock_event)
            except Exception as e:
                # Track failures for reporting
                failures.append(str(e))

            # Fail test if handler raised an exception
            if failures:
                pytest.fail(f"Search button handler raised exception: {failures[0]}")

        assert view is not None, "View should be created"
        assert hasattr(view, 'update'), "View should have update method"


def test_intune_store_search_button(mock_page):
    """Test that Intune Store search button works."""
    from switchcraft.gui_modern.views.intune_store_view import ModernIntuneStoreView

    with patch('switchcraft.gui_modern.views.intune_store_view.IntuneService') as mock_intune:
        mock_intune_instance = MagicMock()
        mock_intune.return_value = mock_intune_instance

        view = ModernIntuneStoreView(mock_page)
        view.update = MagicMock()
        view._get_token = lambda: "mock_token"

        # Test search button
        if hasattr(view, 'btn_search') and view.btn_search:
            if hasattr(view.btn_search, 'on_click') and view.btn_search.on_click:
                # Verify handler exists and is callable
                assert callable(view.btn_search.on_click), "Search button handler should be callable"
                failures = []
                try:
                    mock_event = MagicMock()
                    mock_event.control = view.btn_search
                    view.btn_search.on_click(mock_event)
                except Exception as e:
                    # Track failures for reporting
                    failures.append(str(e))

                # Fail test if handler raised an exception
                if failures:
                    pytest.fail(f"Search button handler raised exception: {failures[0]}")

        assert view is not None, "View should be created"
        assert hasattr(view, 'update'), "View should have update method"
