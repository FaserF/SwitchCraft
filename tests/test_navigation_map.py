import pytest
from unittest.mock import MagicMock, patch
import flet as ft
from switchcraft.gui_modern.app import ModernApp

# Import ALL Views to check types
from switchcraft.gui_modern.views.home_view import ModernHomeView
from switchcraft.gui_modern.views.winget_view import ModernWingetView
from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView
from switchcraft.gui_modern.views.helper_view import ModernHelperView
from switchcraft.gui_modern.views.intune_view import ModernIntuneView
from switchcraft.gui_modern.views.intune_store_view import ModernIntuneStoreView
from switchcraft.gui_modern.views.script_upload_view import ScriptUploadView
from switchcraft.gui_modern.views.macos_wizard_view import MacOSWizardView
from switchcraft.gui_modern.views.history_view import ModernHistoryView
from switchcraft.gui_modern.views.settings_view import ModernSettingsView
from switchcraft.gui_modern.views.packaging_wizard_view import PackagingWizardView
from switchcraft.gui_modern.views.detection_tester_view import DetectionTesterView
from switchcraft.gui_modern.views.stack_manager_view import StackManagerView
from switchcraft.gui_modern.views.dashboard_view import DashboardView
from switchcraft.gui_modern.views.library_view import LibraryView
from switchcraft.gui_modern.views.group_manager_view import GroupManagerView
from switchcraft.gui_modern.views.addon_manager_view import AddonManagerView

@pytest.fixture
def app_instance(monkeypatch):
    # Monkeypatch Control.update to avoid "must be added to page" error
    monkeypatch.setattr(ft.Control, "update", lambda self: None)
    monkeypatch.setattr(ft.Container, "update", lambda self: None)
    monkeypatch.setattr(ft.Page, "update", lambda self: None)

    page = MagicMock(spec=ft.Page)
    page.clean = MagicMock()
    page.add = MagicMock()
    # Mock window object
    page.window = MagicMock()
    page.window.jump_list = []
    # Configure page attributes that strictly exist
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10

    # We must patch HistoryService WHERE IT IS USED, and keep it patched if instantiated later?
    # DashboardView is instantiated inside _switch_to_tab, so the patch must be active during the TEST, not just app init.
    # So we should yield the app or rely on the fact that if DashboardView is imported, we can patch the class?

    # Actually, DashboardView is instantiated when needed.
    # The fixture returns the app. The test runs later.
    # So the patch context manager must wrap the test execution or be a fixture itself.

    app = ModernApp(page)
    # Disable actual file system/network calls
    app.addon_service = MagicMock()
    app.addon_service.is_addon_installed.return_value = False # Force wizard check if it ran
    app.notification_service = MagicMock()

    return app

def test_sidebar_navigation_consistency(app_instance):
    """
    Verifies that every index in Sidebar categories maps to the CORRECT View class.
    """
    # Expected Mapping based on sidebar/app logic
    # We define what we EXPECT index X to be.
    # From app.py destinations list (0-indexed):
    # 0: Home
    # 1: Addon Manager (Extensions) -> Wait, currently UpdateChecker? No AddonMgr?
    #    Let's check app.py dest definitions.
    #    Line 586: Extensions/Addon Manager.
    #    Index 1 -> AddonManagerView (or similar).
    # 2: Updates -> Settings(1)
    # 3: Global Graph -> Settings(2)
    # 4: Help -> Settings(3) (Since we moved it)
    # 5: Apps (Winget) -> ModernWingetView
    # 6: Analyze -> ModernAnalyzerView
    # 7: Generate -> ModernHelperView
    # 8: Intune -> ModernIntuneView
    # 9: Intune Store -> ModernIntuneStoreView
    # 10: Scripts -> ScriptUploadView
    # 11: MacOS -> MacOSWizardView
    # 12: History -> ModernHistoryView
    # 13: Settings -> ModernSettingsView(0)
    # 14: Wizard -> PackagingWizardView
    # 15: Tester -> DetectionTesterView
    # 16: Stacks -> StackManagerView
    # 17: Dashboard -> DashboardView
    # 18: Library -> LibraryView
    # 19: Groups -> GroupManagerView

    expected_views = {
        0: ModernHomeView,
        1: AddonManagerView,
        2: ModernSettingsView,
        3: ModernSettingsView,
        4: ModernSettingsView,
        5: ModernWingetView,
        6: ModernAnalyzerView,
        7: ft.Column, # ModernHelperView is a function returning Column
        8: ModernIntuneView,
        9: ModernIntuneStoreView,
        10: ScriptUploadView,
        11: MacOSWizardView,
        12: ft.Column, # ModernHistoryView is a function
        13: ModernSettingsView,
        14: PackagingWizardView,
        15: DetectionTesterView,
        16: StackManagerView,
        17: DashboardView,
        18: LibraryView,
        19: GroupManagerView
    }

    # Iterate Sidebar Categories
    with patch("switchcraft.gui_modern.views.dashboard_view.HistoryService") as MockHistoryService:
        for cat_icon, cat_name, indices in app_instance.sidebar.categories:
            print(f"\nTesting Category: {cat_name}")
            for idx in indices:
                print(f"  Testing Index {idx}...")

                # Action: Switch Tab
                # _switch_to_tab usually calls load_view which appends to new_controls
                # We mock load_view inside app or just inspect internal state?
                # app._view_cache logic makes this tricky if we don't really instantiate.
                # But the test imports real classes.

                # Clear previous content to be sure
                app_instance.content.controls.clear()

                # Run switch (simulated)
                app_instance._switch_to_tab(idx)

                # Check what was added
                # Note: _switch_to_tab creates a Fade Container. Content is inside.
                assert len(app_instance.content.controls) > 0, f"Index {idx} added no controls"
                fade_container = app_instance.content.controls[-1]
                view_instance = fade_container.content

                expected_type = expected_views.get(idx)

                if isinstance(expected_type, tuple):
                     # Handle placeholders (Type, Value)
                     t, val = expected_type
                     assert isinstance(view_instance, t), f"Index {idx} expected {t}, got {type(view_instance)}"
                     if isinstance(view_instance, ft.Text):
                          # Allow "Unknown Tab" if expected?
                          pass
                else:
                     # Real View
                     # Handle cases where view is wrapped or loaded differently?
                     # Usually it's the direct instance.

                     # Settings View checks:
                     if expected_type == ModernSettingsView:
                          assert isinstance(view_instance, ModernSettingsView)
                          # Verify Sub-Tab?
                          # Index 2 -> Updates (Tab 1)
                          # Index 3 -> Graph (Tab 2)
                          # Index 4 -> Help (Tab 3)
                          # Index 13 -> General (Tab 0)
                          if idx == 2: assert view_instance.initial_tab_index == 1, f"Index {idx} should be Settings Tab 1"
                          if idx == 3: assert view_instance.initial_tab_index == 2, f"Index {idx} should be Settings Tab 2"
                          if idx == 4: assert view_instance.initial_tab_index == 3, f"Index {idx} should be Settings Tab 3"
                          if idx == 13: assert view_instance.initial_tab_index == 0, f"Index {idx} should be Settings Tab 0"
                     else:
                          assert isinstance(view_instance, expected_type), f"Index {idx} ({app_instance.destinations[idx].label}) expected {expected_type.__name__}, got {type(view_instance).__name__}"
