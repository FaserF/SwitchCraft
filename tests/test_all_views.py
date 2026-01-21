
import pytest
import flet as ft
from unittest.mock import MagicMock

# Mock imports that might be troublesome if environment is partial
# (Though we prefer testing real imports to catch the bugs!)

class TestAllViews:
    @pytest.fixture
    def page(self):
        page = MagicMock(spec=ft.Page)
        page.theme_mode = "System"
        page.client_storage = MagicMock()
        page.client_storage = MagicMock()
        page.favicon = None
        return page

    def test_view_instantiation_home(self, page):
        from switchcraft.gui_modern.views.home_view import ModernHomeView
        view = ModernHomeView(page, on_navigate=MagicMock())
        assert view is not None

    def test_view_instantiation_winget(self, page):
        from switchcraft.gui_modern.views.winget_view import ModernWingetView
        view = ModernWingetView(page)
        assert view is not None

    def test_view_instantiation_analyzer(self, page):
        from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView
        view = ModernAnalyzerView(page)
        assert view is not None

    def test_view_instantiation_helper(self, page):
        from switchcraft.gui_modern.views.helper_view import ModernHelperView
        view = ModernHelperView(page)
        assert view is not None

    def test_view_instantiation_intune(self, page):
        from switchcraft.gui_modern.views.intune_view import ModernIntuneView
        view = ModernIntuneView(page)
        assert view is not None

    def test_view_instantiation_intune_store(self, page):
        from switchcraft.gui_modern.views.intune_store_view import ModernIntuneStoreView
        view = ModernIntuneStoreView(page)
        assert view is not None

    def test_view_instantiation_scripts(self, page):
        from switchcraft.gui_modern.views.script_upload_view import ScriptUploadView
        view = ScriptUploadView(page)
        assert view is not None

    def test_view_instantiation_macos(self, page):
        from switchcraft.gui_modern.views.macos_wizard_view import MacOSWizardView
        view = MacOSWizardView(page)
        assert view is not None

    def test_view_instantiation_history(self, page):
        from switchcraft.gui_modern.views.history_view import ModernHistoryView
        view = ModernHistoryView(page)
        assert view is not None

    def test_view_instantiation_settings(self, page):
        from switchcraft.gui_modern.views.settings_view import ModernSettingsView
        view = ModernSettingsView(page)
        assert view is not None

    def test_view_instantiation_wizard(self, page):
        from switchcraft.gui_modern.views.packaging_wizard_view import PackagingWizardView
        view = PackagingWizardView(page)
        assert view is not None

    def test_view_instantiation_tester(self, page):
        from switchcraft.gui_modern.views.detection_tester_view import DetectionTesterView
        view = DetectionTesterView(page)
        assert view is not None

    def test_view_instantiation_stacks(self, page):
        from switchcraft.gui_modern.views.stack_manager_view import StackManagerView
        view = StackManagerView(page)
        assert view is not None

    def test_view_instantiation_dashboard(self, page):
        from switchcraft.gui_modern.views.dashboard_view import DashboardView
        view = DashboardView(page)
        assert view is not None

    def test_view_instantiation_library(self, page):
        from switchcraft.gui_modern.views.library_view import LibraryView
        view = LibraryView(page)
        assert view is not None

    def test_view_instantiation_groups(self, page):
        from switchcraft.gui_modern.views.group_manager_view import GroupManagerView
        view = GroupManagerView(page)
        assert view is not None



    def test_view_instantiation_category(self, page):
        from switchcraft.gui_modern.views.category_view import CategoryView
        view = CategoryView(page, "Test Category", items=[], app_destinations=[], on_navigate=MagicMock())
        assert view is not None

    def test_view_instantiation_crash(self, page):
        from switchcraft.gui_modern.views.crash_view import CrashDumpView
        view = CrashDumpView(page, error=Exception("Test Error"))
        assert view is not None
