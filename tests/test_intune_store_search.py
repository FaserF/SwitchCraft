"""
Tests for Intune Store search functionality with timeout handling.
"""
import pytest
import flet as ft
from unittest.mock import MagicMock, patch, Mock
import threading
import time
import requests
import os

# Import CI detection helper
try:
    from tests.conftest import is_ci_environment, skip_if_ci
except ImportError:
    # Fallback if conftest not available
    def is_ci_environment():
        return os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'
    def skip_if_ci(reason="Test not suitable for CI environment"):
        if is_ci_environment():
            pytest.skip(reason)


def poll_until(condition, timeout=2.0, interval=0.05):
    """
    Poll until condition is met or timeout is reached.

    Parameters:
        condition: Callable that returns True when condition is met
        timeout: Maximum time to wait in seconds
        interval: Time between polls in seconds

    Returns:
        True if condition was met, False if timeout
    """
    elapsed = 0.0
    while elapsed < timeout:
        if condition():
            return True
        time.sleep(interval)
        elapsed += interval
    return False


@pytest.fixture
def mock_page():
    """Create a mock Flet page with run_task support."""
    page = MagicMock(spec=ft.Page)
    page.update = MagicMock()
    page.run_task = lambda func: func()  # Execute immediately for testing

    # Mock page property to avoid RuntimeError
    type(page).page = property(lambda self: page)

    return page


@pytest.fixture
def mock_intune_service():
    """Mock IntuneService."""
    with patch('switchcraft.gui_modern.views.intune_store_view.IntuneService') as mock_service:
        service_instance = MagicMock()
        mock_service.return_value = service_instance
        yield service_instance


def test_intune_search_shows_timeout_error(mock_page, mock_intune_service):
    """Test that Intune search shows timeout error after 60 seconds."""
    from switchcraft.gui_modern.views.intune_store_view import ModernIntuneStoreView

    # Skip in CI to avoid 70 second wait
    if os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true':
        pytest.skip("Skipping test with long time.sleep in CI environment")

    # Mock slow search that times out - use Event to block without long sleep
    search_blocker = threading.Event()
    def slow_search(token, query):
        # Block indefinitely until test completes (no actual sleep)
        search_blocker.wait(timeout=300)  # Long timeout, but test will finish before
        return []
    mock_intune_service.search_apps = slow_search
    mock_intune_service.list_apps = slow_search

    # Mock token
    view = ModernIntuneStoreView(mock_page)
    view._get_token = lambda: "mock_token"

    # Track error calls
    error_calls = []
    def track_error(msg):
        error_calls.append(msg)
    view._show_error = track_error

    # Create a Thread subclass that simulates timeout behavior
    class TimeoutThread(threading.Thread):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._timeout_simulated = True

        def join(self, timeout=None):
            # Simulate timeout by returning immediately (thread still alive)
            return None

        def is_alive(self):
            # Return True to simulate thread still running (timeout occurred)
            return True

    # Use patch to override Thread for threads created by view._run_search
    with patch('threading.Thread', TimeoutThread):
        # Start search
        view.search_field.value = "test"
        view._run_search(None)

        # Wait a bit for the timeout handling to complete
        time.sleep(0.2)

        # Check that timeout error was shown
        assert len(error_calls) > 0, "Timeout error should have been shown"
        assert any("timeout" in str(msg).lower() or "60 seconds" in str(msg) for msg in error_calls), \
            f"Expected timeout message, but got: {error_calls}"

        # Clean up: unblock the search thread so it can exit (it's daemon, but good practice)
        search_blocker.set()


def test_intune_search_handles_network_error(mock_page, mock_intune_service):
    """Test that Intune search handles network errors properly."""
    # Skip in CI as this test uses time.sleep and threading
    skip_if_ci("Test uses time.sleep and threading, not suitable for CI")

    from switchcraft.gui_modern.views.intune_store_view import ModernIntuneStoreView

    # Mock network error
    mock_intune_service.search_apps.side_effect = requests.exceptions.RequestException("Network error")

    view = ModernIntuneStoreView(mock_page)
    view._get_token = lambda: "mock_token"

    error_calls = []
    def track_error(msg):
        error_calls.append(msg)
    view._show_error = track_error

    # Start search
    view.search_field.value = "test"
    view._run_search(None)

    # Wait for error handling
    time.sleep(0.3)

    # Check that error was shown
    assert len(error_calls) > 0
    assert "error" in error_calls[0].lower() or "network" in error_calls[0].lower()


def test_intune_search_shows_results(mock_page, mock_intune_service):
    """Test that Intune search shows results when successful."""
    # Skip in CI as this test uses time.sleep and threading
    skip_if_ci("Test uses time.sleep and threading, not suitable for CI")

    from switchcraft.gui_modern.views.intune_store_view import ModernIntuneStoreView

    # Mock successful search
    mock_results = [
        {"id": "app1", "displayName": "Test App 1", "publisher": "Test Publisher"},
        {"id": "app2", "displayName": "Test App 2", "publisher": "Test Publisher 2"}
    ]
    mock_intune_service.search_apps.return_value = mock_results

    view = ModernIntuneStoreView(mock_page)
    view._get_token = lambda: "mock_token"

    update_calls = []
    def track_update(apps):
        update_calls.append(apps)
    view._update_list = track_update

    # Start search
    view.search_field.value = "test"
    view._run_search(None)

    # Wait for results
    time.sleep(0.3)

    # Check that results were shown
    assert len(update_calls) > 0
    assert len(update_calls[0]) == 2
    assert update_calls[0][0]["displayName"] == "Test App 1"


def test_intune_search_timeout_mechanism(mock_page, mock_intune_service):
    """Test that Intune search properly times out after 60 seconds."""
    from switchcraft.gui_modern.views.intune_store_view import ModernIntuneStoreView

    # Skip in CI to avoid 65 second wait
    if os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true':
        pytest.skip("Skipping test with long time.sleep in CI environment")

    # Mock a search that takes longer than timeout - use Event to block without long sleep
    search_started = threading.Event()
    search_completed = threading.Event()
    search_blocker = threading.Event()

    def slow_search(token, query):
        search_started.set()
        # Block indefinitely until test completes (no actual sleep)
        search_blocker.wait(timeout=300)  # Long timeout, but test will finish before
        search_completed.set()
        return []

    def slow_list(token):
        search_started.set()
        # Block indefinitely until test completes (no actual sleep)
        search_blocker.wait(timeout=300)  # Long timeout, but test will finish before
        search_completed.set()
        return []

    # Mock both methods to ensure test works regardless of which path is taken
    mock_intune_service.search_apps = slow_search
    mock_intune_service.list_apps = slow_list

    view = ModernIntuneStoreView(mock_page)
    view._get_token = lambda: "mock_token"

    error_calls = []
    def track_error(msg):
        error_calls.append(msg)
    view._show_error = track_error

    # Mock Thread.join to simulate timeout (thread.join returns immediately but thread is still alive)
    original_thread = threading.Thread
    def mock_thread(target=None, daemon=False, **kwargs):
        thread = original_thread(target=target, daemon=daemon, **kwargs)
        # Override join to simulate timeout
        original_join = thread.join
        def mock_join(timeout=None):
            # Simulate timeout by returning immediately (thread still alive)
            return None
        thread.join = mock_join
        # Make is_alive return True to simulate timeout
        original_is_alive = thread.is_alive
        def mock_is_alive():
            # Return True to simulate thread still running (timeout occurred)
            return True
        thread.is_alive = mock_is_alive
        return thread
    threading.Thread = mock_thread

    try:
        # Start search
        view.search_field.value = "test"
        view._run_search(None)

        # Wait for search to start using polling (more reliable than fixed timeout)
        def search_started_check():
            return search_started.is_set()

        assert poll_until(search_started_check, timeout=2.0), "Search should start within timeout"

        # Wait for timeout handling using polling
        def timeout_error_shown():
            return len(error_calls) > 0 and any(
                "timeout" in str(msg).lower() or "60 seconds" in str(msg)
                for msg in error_calls
            )

        assert poll_until(timeout_error_shown, timeout=2.0), \
            f"Timeout error should be shown within timeout. Got: {error_calls}"

        # Verify that timeout error was shown
        assert len(error_calls) > 0, "Timeout error should have been shown"
        assert any("timeout" in str(msg).lower() or "60 seconds" in str(msg) for msg in error_calls), \
            f"Expected timeout message, but got: {error_calls}"

        # Clean up: unblock the search thread so it can exit (it's daemon, but good practice)
        search_blocker.set()
        # Verify that search did not complete
        assert not search_completed.is_set(), "Search should not have completed due to timeout"
    finally:
        threading.Thread = original_thread
