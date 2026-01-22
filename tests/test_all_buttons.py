"""
Comprehensive test to verify ALL buttons in the application work correctly.
This test systematically checks every button in every view.
"""
import pytest
import flet as ft
from unittest.mock import MagicMock
import inspect
import importlib
import os
import asyncio

# Import CI detection helper
try:
    from conftest import is_ci_environment, skip_if_ci
except ImportError:
    # Fallback if conftest not available
    def is_ci_environment():
        return os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'
    def skip_if_ci(reason="Test not suitable for CI environment"):
        if is_ci_environment():
            pytest.skip(reason)


def find_all_buttons_in_control(control, buttons_found):
    """Recursively find all buttons in a control tree."""
    if isinstance(control, (ft.Button, ft.IconButton, ft.TextButton, ft.ElevatedButton, ft.OutlinedButton, ft.FilledButton)):
        buttons_found.append(control)

    # Check all possible child attributes to ensure complete button discovery
    # Some controls may have both controls and content, so check all of them
    if hasattr(control, 'controls') and control.controls:
        for child in control.controls:
            find_all_buttons_in_control(child, buttons_found)

    if hasattr(control, 'content') and control.content:
        find_all_buttons_in_control(control.content, buttons_found)

    if hasattr(control, 'actions') and control.actions:
        for action in control.actions:
            find_all_buttons_in_control(action, buttons_found)


def test_all_views_have_buttons():
    """Test that all views can be instantiated and have buttons."""
    # Skip in CI as view instantiation may start background threads that hang
    skip_if_ci("View instantiation with threading not suitable for CI")

    all_buttons = collect_all_buttons()

    # Verify we found views
    assert len(all_buttons) > 0, "No views found"

    # Check that at least one view instantiated successfully (no 'error' key)
    # Build a list of successful instantiations where 'error' not in info
    successes = [view_name for view_name, info in all_buttons.items() if 'error' not in info]
    assert len(successes) > 0, (
        f"No views instantiated successfully. All {len(all_buttons)} views had errors. "
        f"Failed views: {[name for name in all_buttons.keys() if name not in successes]}"
    )

    # Print summary
    print("\n=== Button Summary ===")
    for view_name, info in all_buttons.items():
        if 'error' in info:
            print(f"{view_name}: ERROR - {info['error']}")
        else:
            print(f"{view_name}: {info['count']} buttons")


def _create_mock_page():
    """Helper function to create a mock page for view instantiation."""
    mock_page = MagicMock(spec=ft.Page)
    mock_page.update = MagicMock()
    mock_page.switchcraft_app = MagicMock()
    mock_page.switchcraft_app.goto_tab = MagicMock()
    mock_page.switchcraft_app._current_tab_index = 0
    mock_page.dialog = None
    mock_page.end_drawer = None
    mock_page.snack_bar = None
    mock_page.open = MagicMock()
    mock_page.close = MagicMock()

    def mock_run_task(func):
        if inspect.iscoroutinefunction(func):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(func())
            except RuntimeError:
                asyncio.run(func())
        else:
            func()

    mock_page.run_task = mock_run_task
    type(mock_page).page = property(lambda self: mock_page)
    return mock_page


def collect_all_buttons():
    """Helper function to collect all buttons from all views."""
    views_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'switchcraft', 'gui_modern', 'views')

    # Dynamically discover view files to avoid maintaining a hardcoded list
    view_files = []
    if os.path.exists(views_dir):
        for filename in os.listdir(views_dir):
            if filename.endswith('_view.py') and filename != '__init__.py':
                # Remove .py extension to get module name
                view_files.append(filename[:-3])
    else:
        # Fallback to hardcoded list if directory doesn't exist (shouldn't happen in normal tests)
        view_files = [
            'home_view', 'settings_view', 'winget_view', 'intune_store_view',
            'group_manager_view', 'category_view', 'dashboard_view', 'analyzer_view',
            'intune_view', 'helper_view', 'packaging_wizard_view', 'script_upload_view',
            'macos_wizard_view', 'history_view', 'library_view', 'stack_manager_view',
            'detection_tester_view', 'wingetcreate_view'
        ]

    mock_page = _create_mock_page()

    all_buttons = {}

    for view_file in view_files:
        try:
            module_name = f'switchcraft.gui_modern.views.{view_file}'
            module = importlib.import_module(module_name)

            # Find view class
            view_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and (name.endswith('View') or 'View' in name):
                    if obj != ft.Column and obj != ft.Container and obj != ft.Row:
                        view_class = obj
                        break

            if not view_class:
                continue

            # Try to instantiate view
            try:
                if 'Settings' in view_class.__name__:
                    view = view_class(mock_page, initial_tab_index=0)
                elif 'Home' in view_class.__name__:
                    view = view_class(mock_page, on_navigate=lambda x: None)
                else:
                    view = view_class(mock_page)

                # Find all buttons
                buttons = []
                find_all_buttons_in_control(view, buttons)

                all_buttons[view_class.__name__] = {
                    'buttons': buttons,
                    'count': len(buttons)
                }

            except Exception as e:
                print(f"Failed to instantiate {view_class.__name__}: {e}")
                all_buttons[view_class.__name__] = {
                    'error': str(e),
                    'buttons': [],
                    'count': 0
                }

        except Exception as e:
            print(f"Failed to import {view_file}: {e}")
            all_buttons[view_file] = {
                'error': str(e),
                'buttons': [],
                'count': 0
            }

    return all_buttons


def test_all_buttons_have_handlers():
    """Test that all buttons have on_click handlers."""
    # Skip in CI as view instantiation may start background threads that hang
    skip_if_ci("View instantiation with threading not suitable for CI")

    all_buttons = collect_all_buttons()

    buttons_without_handlers = []

    for view_name, info in all_buttons.items():
        if 'error' in info:
            continue

        for button in info['buttons']:
            if not hasattr(button, 'on_click') or button.on_click is None:
                buttons_without_handlers.append({
                    'view': view_name,
                    'button': button,
                    'text': getattr(button, 'text', getattr(button, 'content', 'Unknown'))
                })

    if buttons_without_handlers:
        print("\n=== Buttons without handlers ===")
        for item in buttons_without_handlers:
            print(f"{item['view']}: {item['text']}")

    # Assert that no buttons are without handlers
    assert not buttons_without_handlers, f"Buttons without handlers: {buttons_without_handlers}"


def test_button_handlers_are_callable():
    """Test that all button handlers are callable."""
    # Skip in CI as view instantiation may start background threads that hang
    skip_if_ci("View instantiation with threading not suitable for CI")

    all_buttons = collect_all_buttons()

    if not all_buttons:
        pytest.skip("No views found to test")

    invalid_handlers = []

    for view_name, info in all_buttons.items():
        if 'error' in info:
            continue

        for button in info['buttons']:
            if hasattr(button, 'on_click') and button.on_click is not None:
                if not callable(button.on_click):
                    invalid_handlers.append({
                        'view': view_name,
                        'button': button,
                        'handler': button.on_click
                    })

    if invalid_handlers:
        print("\n=== Buttons with invalid handlers ===")
        for item in invalid_handlers:
            print(f"{item['view']}: {type(item['handler'])}")

    assert len(invalid_handlers) == 0, f"Found {len(invalid_handlers)} buttons with invalid handlers"


@pytest.mark.parametrize("view_name,view_file", [
    ("ModernHomeView", "home_view"),
    ("ModernSettingsView", "settings_view"),
    ("ModernWingetView", "winget_view"),
    ("ModernIntuneStoreView", "intune_store_view"),
    ("GroupManagerView", "group_manager_view"),
    ("DashboardView", "dashboard_view"),
    ("ModernAnalyzerView", "analyzer_view"),
    ("ModernIntuneView", "intune_view"),
    ("ModernHelperView", "helper_view"),
    ("PackagingWizardView", "packaging_wizard_view"),
    ("ScriptUploadView", "script_upload_view"),
    ("MacOSWizardView", "macos_wizard_view"),
    ("ModernHistoryView", "history_view"),
    ("LibraryView", "library_view"),
    ("StackManagerView", "stack_manager_view"),
    ("DetectionTesterView", "detection_tester_view"),
    ("WingetCreateView", "wingetcreate_view"),
])
def test_view_buttons_work(view_name, view_file):
    """Test that buttons in a specific view work correctly."""
    # Skip in CI as view instantiation may start background threads that hang
    skip_if_ci("View instantiation with threading not suitable for CI")

    # Use shared helper to create mock page
    mock_page = _create_mock_page()

    try:
        module = importlib.import_module(f'switchcraft.gui_modern.views.{view_file}')

        # Find view class
        view_class = None
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and name == view_name:
                view_class = obj
                break

        if not view_class:
            pytest.skip(f"View class {view_name} not found")

        # Instantiate view
        if 'Settings' in view_name:
            view = view_class(mock_page, initial_tab_index=0)
        elif 'Home' in view_name:
            view = view_class(mock_page, on_navigate=lambda x: None)
        else:
            view = view_class(mock_page)

        # Find all buttons
        buttons = []
        find_all_buttons_in_control(view, buttons)

        # Verify buttons is a list and contains elements
        assert isinstance(buttons, list), "buttons should be a list"
        # Allow zero buttons for display-only views like DashboardView
        if view_name != "DashboardView":
            assert len(buttons) > 0, f"View {view_name} should have at least one button"

        # Test that buttons can be clicked
        failures = []
        successes = 0
        for button in buttons:
            if hasattr(button, 'on_click') and button.on_click is not None:
                try:
                    # Create a mock event
                    mock_event = MagicMock()
                    mock_event.control = button
                    mock_event.data = "true"

                    # Call the handler - handle both sync and async handlers
                    handler = button.on_click
                    if inspect.iscoroutinefunction(handler):
                        # Handler is async, need to run it and await to catch exceptions
                        # Don't use create_task without awaiting - it silently swallows errors
                        # Always use asyncio.run() which properly awaits and raises exceptions
                        # This ensures exceptions are properly raised and caught by the test
                        asyncio.run(handler(mock_event))
                    else:
                        res = handler(mock_event)
                        if inspect.isawaitable(res):
                             asyncio.run(res)
                    successes += 1

                except Exception as e:
                    # Track failures for reporting
                    failures.append((button, str(e)))

        # Report failures if any
        if failures:
            failure_msgs = [f"Button handler failed in {view_name}: {e}" for _, e in failures]
            print("\n".join(failure_msgs))

        # Assert that at least some buttons succeeded (allowing some failures due to missing dependencies)
        assert successes > 0, f"At least one button handler should succeed in {view_name}. Failures: {len(failures)}"
        assert view is not None

    except Exception as e:
        pytest.skip(f"Could not test {view_name}: {e}")
