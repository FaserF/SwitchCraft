import pytest
from unittest.mock import MagicMock, patch
import flet as ft
from switchcraft.gui_modern.views.settings_view import ModernSettingsView
from switchcraft.gui_modern.views.dashboard_view import DashboardView
from switchcraft.gui_modern.views.home_view import ModernHomeView
from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView

@pytest.fixture
def mock_page():
    page = MagicMock(spec=ft.Page)
    page.clean = MagicMock()
    page.add = MagicMock()
    page.update = MagicMock()

    # Init empty dialogs
    page.dialog = None
    page.snack_bar = None
    # page.open = MagicMock() # Removed duplicate assignment

    # Mock window object
    page.window = MagicMock()
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10

    # Mock open for dialogs (newer Flet API)
    page.open = MagicMock()
    return page

def find_buttons(control):
    buttons = []
    # Check if it's a button
    # Note: ElevatedButton is deprecated, but we check for it if present
    button_types = (ft.FilledButton, ft.TextButton, ft.IconButton, ft.OutlinedButton)
    if hasattr(ft, "ElevatedButton"):
        button_types += (ft.ElevatedButton,)
    if hasattr(ft, "Button"):
        button_types += (ft.Button,)

    if isinstance(control, button_types):
        buttons.append(control)

    # Recurse
    if hasattr(control, "controls") and control.controls:
        for child in control.controls:
            buttons.extend(find_buttons(child))
    elif hasattr(control, "content") and control.content:
        buttons.extend(find_buttons(control.content))

    # Handle TabBar tabs
    if isinstance(control, ft.TabBar) and control.tabs:
        for tab in control.tabs:
             # Tabs usually have content if they are TabBarView, but Tab control has content/label
             # We just traverse Tab children? Tab doesn't have children usually unless it stores content
             # Wait, Tab has 'content' or 'icon' etc.
             pass

    return buttons

def test_settings_view_buttons(mock_page):
    """Test all buttons in SettingsView (General, Updates, Deployment, Help)."""

    # log_file = "test_result.log"
    # with open(log_file, "w") as f:
    #     f.write("Starting Button Test\n")

    def log(msg):
        # with open(log_file, "a") as f:
        #     f.write(msg + "\n")
        print(msg)

    # Mock necessary services to prevent side effects
    with patch("switchcraft.utils.config.SwitchCraftConfig.get_value") as mock_get, \
         patch("switchcraft.utils.config.SwitchCraftConfig.set_user_preference") as mock_set, \
         patch("threading.Thread") as mock_thread, \
         patch("switchcraft.gui_modern.views.settings_view.AuthService") as mock_auth, \
         patch("switchcraft.gui_modern.views.settings_view.SyncService") as mock_sync:

        # Mock thread start to just log it
        mock_thread.return_value.start.side_effect = lambda: log("Thread started!")

        # 1. Test Updates Tab (Index 1)
        log("Instantiating SettingsView (Updates Tab)")
        try:
            view = ModernSettingsView(mock_page, initial_tab_index=1)
        except Exception as e:
            log(f"CRITICAL: Failed to instantiate SettingsView: {e}")
            import traceback
            log(traceback.format_exc())
            pytest.fail(f"Init failed: {e}")

        buttons = find_buttons(view)
        log(f"Found {len(buttons)} buttons in Settings View (Updates Tab)")

        for btn in buttons:
            label = "Unknown"
            if hasattr(btn, "text") and btn.text:
                label = btn.text
            elif hasattr(btn, "label") and btn.label: # TextField check? No button usually doesn't have label but Tab does.
                 label = btn.label
            elif hasattr(btn, "content"):
                if isinstance(btn.content, str):
                    label = btn.content
                elif isinstance(btn.content, ft.Text):
                    label = btn.content.value
                elif isinstance(btn.content, ft.Row):
                    # Try to find text in Row
                    for c in btn.content.controls:
                        if isinstance(c, ft.Text):
                            label = c.value
                            break

            if label == "Unknown" and hasattr(btn, "tooltip"):
                label = btn.tooltip or "Unknown"

            log(f"Testing button: {label} (Type: {type(btn).__name__})")

            if btn.on_click:
                try:
                    # Simulate click
                    # Use dummy UID if not present
                    target_uid = getattr(btn, "uid", "mock_uid")
                    # Use Mock event to avoid signature issues
                    e = MagicMock(spec=ft.ControlEvent)
                    e.target = str(target_uid)
                    e.name = "click"
                    e.data = ""
                    e.control = btn
                    e.page = mock_page

                    btn.on_click(e)
                    log(f"Button '{label}' clicked successfully.")
                except Exception as ex:
                    import traceback
                    tb = traceback.format_exc()
                    log(f"CRITICAL: Button '{label}' crashed: {ex}\n{tb}")
                    pytest.fail(f"Button '{label}' crashed: {ex}")
            else:
                log(f"WARNING: Button '{label}' has no on_click handler.")


def test_dashboard_view_buttons(mock_page):
    """Test buttons in DashboardView."""
    # log_file = "test_result.log"
    def log(msg):
        # with open(log_file, "a") as f:
        #     f.write(msg + "\n")
        print(msg)

    with patch("switchcraft.gui_modern.views.dashboard_view.HistoryService") as MockHistoryService:
        log("\nInstantiating DashboardView")
        try:
             # Mock the get_history return value to avoid iterating over MagicMock
             MockHistoryService.return_value.get_history.return_value = []
             view = DashboardView(mock_page)
             view.update = MagicMock() # Mock update to avoid "Control must be added" error
             # Manually trigger did_mount as Flet triggers it when added to page
             view.did_mount()
        except Exception as e:
            log(f"CRITICAL: DashboardView init failed: {e}")
            import traceback
            log(traceback.format_exc())
            pytest.fail(f"Dashboard init failed: {e}")

        buttons = find_buttons(view)
        log(f"Found {len(buttons)} buttons in Dashboard View")
        for btn in buttons:
             label = "Unknown"
             if hasattr(btn, "text") and btn.text:
                label = btn.text
             elif hasattr(btn, "content"):
                if isinstance(btn.content, str):
                    label = btn.content
                elif isinstance(btn.content, ft.Text):
                    label = btn.content.value

             if label == "Unknown":
                 label = getattr(btn, "tooltip", "Unknown") or "Icon Button"

             log(f"Testing button: {label}")
             if btn.on_click:
                try:
                    e = MagicMock(spec=ft.ControlEvent)
                    e.control = btn
                    e.page = mock_page
                    e.target = "mock_uid"
                    btn.on_click(e)
                    log(f"Button '{label}' clicked successfully.")
                except Exception as ex:
                    log(f"CRITICAL: Button '{label}' crashed: {ex}")
                    pytest.fail(f"Button '{label}' crashed: {ex}")

def test_analyzer_view_buttons(mock_page):
    """Test buttons in AnalyzerView."""
    # log_file = "test_result.log"
    def log(msg):
        # with open(log_file, "a") as f:
        #     f.write(msg + "\n")
        print(msg)

    # Mock Dropzone which might be platform dependent, and HistoryService
    # Patch the SOURCE of HistoryService so local imports mock it too
    with patch("switchcraft.gui_modern.views.analyzer_view.HAS_DROPZONE", True), \
         patch("switchcraft.services.history_service.HistoryService") as MockHistoryService, \
         patch("switchcraft.gui_modern.views.analyzer_view.webbrowser") as MockWebReader:

        log("\nInstantiating AnalyzerView")

        try:
            view = ModernAnalyzerView(mock_page)
            view.update = MagicMock() # Mock update to prevent "Control must be added" error

            # Simulate Analysis Completion to show dynamic buttons
            log("Simulating Analysis Completion...")
            # Mock Result
            mock_result = MagicMock()
            mock_result.error = None
            mock_result.info.file_path = "C:\\dummy\\installer.exe"
            mock_result.info.product_name = "Dummy Product"
            mock_result.info.product_version = "1.0.0"
            mock_result.info.manufacturer = "Dummy Corp"
            mock_result.info.installer_type = "Inno Setup"
            mock_result.info.install_switches = ["/VERYSILENT"]
            mock_result.brute_force_data = "Raw Data"
            # Add nested data for cleanup button test
            mock_result.nested_data = {"temp_dir": "C:\\temp", "nested_executables": []}
            mock_result.winget_url = "https://example.com/winget" # Valid string

            # Call internal method to render results
            view._show_results(mock_result)
            log("Results rendered.")
        except Exception as e:
             log(f"CRITICAL: AnalyzerView init/render failed: {e}")
             import traceback
             log(traceback.format_exc())
             pytest.fail(f"AnalyzerView failed: {e}")

        buttons = find_buttons(view)
        log(f"Found {len(buttons)} buttons in Analyzer View (after analysis)")

        # Test Dynamic Buttons (Winget, Test Locally, etc.)
        for btn in buttons:
             label = "Unknown"
             if hasattr(btn, "text") and btn.text:
                label = btn.text
             elif hasattr(btn, "content") and isinstance(btn.content, str):
                 label = btn.content
             elif hasattr(btn, "content") and isinstance(btn.content, ft.Text):
                 label = btn.content.value

             if label == "Unknown":
                  label = getattr(btn, "tooltip", "Unknown") or "Icon Button"

             log(f"Testing button: {label}")
             if btn.on_click:
                try:
                    e = MagicMock(spec=ft.ControlEvent)
                    e.control = btn
                    e.page = mock_page
                    e.target = "mock_uid"
                    # Mock callbacks
                    btn.on_click(e)
                    log(f"Button '{label}' clicked successfully.")
                except Exception as ex:
                    log(f"CRITICAL: Button '{label}' crashed: {ex}")
                    import traceback
                    log(traceback.format_exc())
                    # Don't fail immediately, try others? No, fail is better to fix one by one.
                    pytest.fail(f"Button '{label}' crashed: {ex}")

def test_library_view_buttons(mock_page):
    """Test buttons in LibraryView."""
    # log_file = "test_result.log"
    def log(msg):
        # with open(log_file, "a") as f:
        #      f.write(msg + "\n")
        print(msg)

    # 1. Test "Intune not configured" state
    with patch("switchcraft.gui_modern.views.library_view.SwitchCraftConfig.get_value") as mock_get, \
         patch("switchcraft.gui_modern.views.library_view.SwitchCraftConfig.get_secure_value") as mock_secure:

        # Simulate missing credentials
        mock_get.return_value = None
        mock_secure.return_value = None

        log("\nInstantiating LibraryView (No Credentials)")
        try:
            from switchcraft.gui_modern.views.library_view import LibraryView
            view = LibraryView(mock_page)
            # IMPORTANT: view.update calls self.page.update() if mounted, or errors if not.
            # Since we are testing in isolation, we must mock it.
            view.update = MagicMock()
        except Exception as e:
            log(f"CRITICAL: LibraryView init failed: {e}")
            pytest.fail(f"LibraryView init failed: {e}")

        buttons = find_buttons(view)
        log(f"Found {len(buttons)} buttons in LibraryView (No Creds)")

        for btn in buttons:
            label = "Unknown"
            if hasattr(btn, "text") and btn.text:
                label = btn.text
            elif hasattr(btn, "content"):
                if isinstance(btn.content, str):
                    label = btn.content
                elif isinstance(btn.content, ft.Text):
                    label = btn.content.value

            if label == "Unknown":
                label = getattr(btn, "tooltip", "Unknown") or "Icon Button"
            log(f"Testing button: {label}")
            if btn.on_click:
                try:
                     e = MagicMock(spec=ft.ControlEvent)
                     e.control = btn
                     e.page = mock_page
                     e.target = "mock_uid"
                     btn.on_click(e)
                     log(f"Button '{label}' clicked successfully.")
                except Exception as ex:
                     log(f"CRITICAL: Button '{label}' crashed: {ex}")
                     pytest.fail(f"Button '{label}' crashed: {ex}")

    # 2. Test "Intune Configured" state with history items
    with patch("switchcraft.gui_modern.views.library_view.SwitchCraftConfig.get_value") as mock_get, \
         patch("switchcraft.gui_modern.views.library_view.SwitchCraftConfig.get_secure_value") as mock_secure:

        # Simulate valid credentials
        mock_get.return_value = "dummy_val"
        mock_secure.return_value = "dummy_secret"

        log("\nInstantiating LibraryView (With Credentials)")
        try:
             view = LibraryView(mock_page)
             view.update = MagicMock() # Mock update
             view.did_mount()
        except Exception as e:
            log(f"CRITICAL: LibraryView init failed (With Creds): {e}")
            pytest.fail(f"LibraryView init failed: {e}")

        buttons = find_buttons(view)
        log(f"Found {len(buttons)} buttons in LibraryView (With Creds)")

        for btn in buttons:
            label = "Unknown"
            if hasattr(btn, "text") and btn.text:
                label = btn.text
            elif hasattr(btn, "content"):
                if isinstance(btn.content, str):
                    label = btn.content
                elif isinstance(btn.content, ft.Text):
                    label = btn.content.value

            if label == "Unknown":
                label = getattr(btn, "tooltip", "Unknown") or "Icon Button"
            log(f"Testing button: {label}")
            if btn.on_click:
                try:
                     e = MagicMock(spec=ft.ControlEvent)
                     e.control = btn
                     e.page = mock_page
                     e.target = "mock_uid"
                     btn.on_click(e)
                     log(f"Button '{label}' clicked successfully.")
                except Exception as ex:
                     log(f"CRITICAL: Button '{label}' crashed: {ex}")
                     pytest.fail(f"Button '{label}' crashed: {ex}")

def test_settings_view_entra_test_connection(mock_page):
    """Test custom buttons like Entra Test Connection in SettingsView."""
    # log_file = "test_result.log"
    def log(msg):
        # with open(log_file, "a") as f:
        #      f.write(msg + "\n")
        print(msg)

    with patch("switchcraft.gui_modern.views.settings_view.SwitchCraftConfig") as verify_config, \
         patch("switchcraft.gui_modern.views.settings_view.IntuneService") as MockIntune, \
         patch("switchcraft.gui_modern.views.settings_view.AuthService") as MockAuth, \
         patch("threading.Thread") as mock_thread:

        # Mock Config interactions
        verify_config.get_value.return_value = "dummy_val"
        verify_config.get_secure_value.return_value = "dummy_secret"
        verify_config.is_managed.return_value = False

        log("\nInstantiating ModernSettingsView (Tab 2: Graph API)")
        try:
            from switchcraft.gui_modern.views.settings_view import ModernSettingsView
            view = ModernSettingsView(mock_page, initial_tab_index=2)
            # IMPORTANT: Mock update to prevent "Control must be added to page" error
            view.update = MagicMock()
        except Exception as e:
             log(f"CRITICAL: SettingsView init failed: {e}")
             pytest.fail(f"SettingsView init failed: {e}")

        # Helper to find items
        def find_all_buttons_and_inputs(control):
            items = []
            button_types = (ft.FilledButton, ft.TextButton, ft.IconButton, ft.OutlinedButton, ft.TextField)
            if hasattr(ft, "ElevatedButton"):
                button_types += (ft.ElevatedButton,)
            if hasattr(ft, "Button"):
                button_types += (ft.Button,)

            if isinstance(control, button_types):
                items.append(control)

            # Recursive traversal
            children = []
            if hasattr(control, "controls") and control.controls:
                children.extend(control.controls)
            if hasattr(control, "content") and control.content:
                children.append(control.content)

            # Handle TabBar
            if isinstance(control, ft.TabBar) and control.tabs:
                children.extend(control.tabs)

            # Handle Tabs (Old alias compatibility check?)
            # No, assume Flet 0.80.1, we traverse content.

            for child in children:
                items.extend(find_all_buttons_and_inputs(child))
            return items

        items = find_all_buttons_and_inputs(view)
        log(f"Found {len(items)} interactive items in SettingsView")

        test_btn = None
        tenant_field = None

        found_labels = []
        for item in items:
            label = "Unknown"
            if hasattr(item, "text") and item.text:
                label = item.text
            elif hasattr(item, "label") and item.label:
                label = item.label
            elif hasattr(item, "content"):
                if isinstance(item.content, str):
                    label = item.content
                elif isinstance(item.content, ft.Text):
                    label = item.content.value

            found_labels.append(label)
            if label == "Test Connection":
                test_btn = item
            if label == "Entra Tenant ID":
                tenant_field = item

        log(f"All found labels: {found_labels}")

        if not test_btn:
             log("CRITICAL: 'Test Connection' button NOT FOUND in SettingsView!")
             pytest.fail("'Test Connection' button missing")
        else:
             log("SUCCESS: 'Test Connection' button found.")
             # Click it
             try:
                 e = MagicMock(spec=ft.ControlEvent)
                 e.control = test_btn
                 e.page = mock_page
                 if hasattr(view, 'raw_tenant_field'):
                     view.raw_tenant_field.value = "test-tenant"
                     view.raw_client_field.value = "test-client"
                     view.raw_secret_field.value = "test-secret"

                 test_btn.on_click(e)
                 log("Clicked 'Test Connection' - invoked handler")
             except Exception as ex:
                 log(f"CRITICAL: 'Test Connection' click failed: {ex}")

        if not tenant_field:
            log("CRITICAL: 'Entra Tenant ID' field NOT FOUND")
        else:
             log("SUCCESS: 'Entra Tenant ID' field found.")
             # Check on_change
             if tenant_field.on_change:
                 log("SUCCESS: 'Entra Tenant ID' has on_change handler.")
             else:
                 log("CRITICAL: 'Entra Tenant ID' missing on_change handler!")
                 pytest.fail("'Entra Tenant ID' missing on_change handler!")
