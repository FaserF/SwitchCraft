import pytest
from unittest.mock import MagicMock, patch
import flet as ft
from switchcraft.gui_modern.app import ModernApp

# Import ALL Views to check types
from switchcraft.gui_modern.views.home_view import ModernHomeView
from switchcraft.gui_modern.views.winget_view import ModernWingetView
from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView
from switchcraft.gui_modern.views.intune_view import ModernIntuneView
from switchcraft.gui_modern.views.intune_store_view import ModernIntuneStoreView
from switchcraft.gui_modern.views.script_upload_view import ScriptUploadView
from switchcraft.gui_modern.views.macos_wizard_view import MacOSWizardView
from switchcraft.gui_modern.views.settings_view import ModernSettingsView
from switchcraft.gui_modern.views.packaging_wizard_view import PackagingWizardView
from switchcraft.gui_modern.views.detection_tester_view import DetectionTesterView
from switchcraft.gui_modern.views.stack_manager_view import StackManagerView
from switchcraft.gui_modern.views.dashboard_view import DashboardView
from switchcraft.gui_modern.views.library_view import LibraryView
from switchcraft.gui_modern.views.group_manager_view import GroupManagerView

@pytest.fixture
def app_instance(monkeypatch):
    # Monkeypatch Control.update to avoid "must be added to page" error
    monkeypatch.setattr(ft.Control, "update", lambda self: None)
    monkeypatch.setattr(ft.Container, "update", lambda self: None)
    monkeypatch.setattr(ft.Page, "update", lambda self: None)

    page = MagicMock(spec=ft.Page)
    page.clean = MagicMock()
    page.add = MagicMock()
    page.open = MagicMock()
    # Mock window object
    page.window = MagicMock()
    page.window.jump_list = []
    # Configure page attributes that strictly exist
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10
    page.favicon = None

    app = ModernApp(page)
    # Disable actual file system/network calls
    app.addon_service = MagicMock()
    app.addon_service.is_addon_installed.return_value = False # Force wizard check if it ran
    app.notification_service = MagicMock()

    return app

def test_sidebar_navigation_consistency(app_instance):
    """
    Verify that each sidebar index opens the intended view.

    For every index listed in the app's sidebar categories this test switches to the tab and asserts that the view appended to app_instance.content matches the expected view type. For indices mapped to the settings view, the test also verifies the expected initial sub-tab index.
    """
    # Expected Mapping based on sidebar/app logic (nav_constants.py)
    expected_views = {
        0: ModernHomeView,
        1: ModernSettingsView,
        2: ModernSettingsView,
        3: ModernSettingsView,
        4: ModernWingetView,
        5: ModernAnalyzerView,
        6: ft.Column, # ModernHelperView is a function returning Column
        7: ModernIntuneView,
        8: ModernIntuneStoreView,
        9: ScriptUploadView,
        10: MacOSWizardView,
        11: ft.Column, # ModernHistoryView is a function
        12: ModernSettingsView,
        13: PackagingWizardView,
        14: DetectionTesterView,
        15: StackManagerView,
        16: DashboardView,
        17: LibraryView,
        18: GroupManagerView
    }

    # Iterate Sidebar Categories
    with patch("switchcraft.gui_modern.views.dashboard_view.HistoryService"):
        for cat_icon, cat_name, indices in app_instance.sidebar.categories:
            print(f"\nTesting Category: {cat_name}")
            for idx in indices:
                print(f"  Testing Index {idx}...")

                # Clear previous content to be sure
                app_instance.content.controls.clear()

                # Run switch (simulated)
                app_instance._switch_to_tab(idx)

                # Check what was added
                assert len(app_instance.content.controls) > 0, f"Index {idx} added no controls"
                fade_container = app_instance.content.controls[-1]
                view_instance = fade_container.content

                expected_type = expected_views.get(idx)

                if expected_type is None:
                    # No expectation defined, skip validation
                    continue
                elif isinstance(expected_type, tuple):
                     # Handle placeholders (Type, Value)
                     t, val = expected_type
                     assert isinstance(view_instance, t), f"Index {idx} expected {t}, got {type(view_instance)}"
                else:
                     # Real View
                     # Settings View checks:
                     if expected_type == ModernSettingsView:
                          assert isinstance(view_instance, ModernSettingsView)
                          # Verify Sub-Tab
                          # Index 1 -> Updates (Tab 1)
                          # Index 2 -> Graph (Tab 2)
                          # Index 3 -> Help (Tab 3)
                          # Index 12 -> General (Tab 0)
                          if idx == 1:
                              assert view_instance.initial_tab_index == 1, f"Index {idx} should be Settings Tab 1"
                          if idx == 2:
                              assert view_instance.initial_tab_index == 2, f"Index {idx} should be Settings Tab 2"
                          if idx == 3:
                              assert view_instance.initial_tab_index == 4, f"Index {idx} should be Settings Tab 4"
                          if idx == 21:
                              assert view_instance.initial_tab_index == 3, f"Index {idx} should be Settings Tab 3"
                          if idx == 12:
                              assert view_instance.initial_tab_index == 0, f"Index {idx} should be Settings Tab 0"
                     else:
                          assert isinstance(view_instance, expected_type), f"Index {idx} ({app_instance.destinations[idx].label}) expected {expected_type.__name__}, got {type(view_instance).__name__}"