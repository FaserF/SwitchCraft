"""
E2E Test for Exchange View Flow
Simulates the user journey:
1. Initialize Exchange View (with credential mocking)
2. Verify initial data load (Charts, Stats)
3. Change Date Range Filter
4. Verify data refresh/update logic
"""
import pytest
from unittest.mock import MagicMock, patch
from conftest import poll_until, _create_mock_page

def test_exchange_e2e_flow():
    """
    Test complete Exchange view dashboard flow.
    """
    from switchcraft.gui_modern.views.exchange_view import ExchangeView

    # 1. Initialize View
    mock_page = _create_mock_page()

    # Mock SwitchCraftConfig to return credentials so _init_ui is called
    with patch("switchcraft.gui_modern.views.exchange_view.SwitchCraftConfig.get_value") as mock_get, \
         patch("switchcraft.gui_modern.views.exchange_view.SwitchCraftConfig.get_secure_value") as mock_secure, \
         patch("threading.Thread") as mock_thread:

        mock_get.return_value = "dummy"
        mock_secure.return_value = "dummy"

        # Make threads run immediately
        mock_thread.return_value.start.side_effect = lambda: None # We will call target manually or assume thread logic is not critical for basic UI structure check?
        # Actually, ExchangeView uses thread to load data. If we mock Thread, data won't load unless we extract the target.
        # Better: let thread run but join it? Or use poll_until.

    # Let's NOT patch Thread effectively effectively prevents execution.
    # Let's use real threads but poll.

    with patch("switchcraft.gui_modern.views.exchange_view.SwitchCraftConfig.get_value") as mock_get, \
         patch("switchcraft.gui_modern.views.exchange_view.SwitchCraftConfig.get_secure_value") as mock_secure:

        mock_get.return_value = "dummy"
        mock_secure.return_value = "dummy"

        view = ExchangeView(mock_page)
        # Wrap update to track calls effectively
        original_update = view.update
        view.update = MagicMock(side_effect=original_update)

        # Properly add to page (this sets internal page reference in mock)
        mock_page.add(view)

        # Trigger did_mount manually to start data loading
        view.did_mount()

        # 2. Verify Initial Data Load
        # Check Stats Cards
        assert hasattr(view, 'stats_row'), "Stats row should exist when credentials are valid"

        # Check Chart
        assert hasattr(view, 'mail_chart'), "Chart container should exist"

        # 3. Change Date Range Filter
        if hasattr(view, 'days_dropdown'):
            dropdown = view.days_dropdown

            # Change value
            dropdown.value = "14"

            # Trigger Change Event
            mock_event = MagicMock()
            mock_event.control = dropdown
            if dropdown.on_change:
                dropdown.on_change(mock_event)

        # 4. Verify Data Refresh
        # Use polling to wait for the thread to call update
        def update_called():
            return view.update.called

        assert poll_until(update_called, timeout=3.0), "View update should be called asynchronously"

if __name__ == "__main__":
    pytest.main([__file__])
