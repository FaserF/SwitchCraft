"""
Shared utilities for tests.
"""
import os
import time
import pytest

def is_ci_environment():
    """
    Check if running in a CI environment (GitHub Actions, etc.).

    Returns:
        bool: True if running in CI, False otherwise.
    """
    return (
        os.environ.get('CI') == 'true' or
        os.environ.get('GITHUB_ACTIONS') == 'true' or
        os.environ.get('GITHUB_RUN_ID') is not None
    )


def skip_if_ci(reason="Test not suitable for CI environment"):
    """
    Immediately skip the test if running in CI environment.

    This function calls pytest.skip() immediately if is_ci_environment() returns True,
    causing the test to be skipped with the provided reason.

    Args:
        reason: Reason for skipping the test.

    Note:
        This function performs an immediate skip by calling pytest.skip() when
        running in CI, so it should be called at the beginning of a test function.
    """
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
