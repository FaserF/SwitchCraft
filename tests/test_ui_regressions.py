import pytest
import flet as ft
from unittest.mock import MagicMock
from switchcraft.gui_modern.app import ModernApp
from switchcraft.gui_modern.controls.sidebar import HoverSidebar

class TestUIRegressions:
    def test_app_icon_is_set(self):
        """Regression Test: App icon should be set correctly."""
        page = MagicMock(spec=ft.Page)
        page.theme_mode = "System"
        page.open = MagicMock()

        # Mock window object
        page.window = MagicMock()
        page.window.icon = None # Start as None

        _ = ModernApp(page)

        # Depending on environment, it might set icon or not.
        # But our app code tries to resolve strict paths now.
        # We expect it to be set if the file exists.
        # Since we are in the repo, it should resolve to src/switchcraft/assets/switchcraft_logo.ico

        assert page.window.icon is not None, "Window icon should be set"
        assert "switchcraft_logo.ico" in page.window.icon, f"Icon path incorrect: {page.window.icon}"

    def test_loading_screen_removal(self):
        """Regression Test: Ensure loading screen is cleared before building UI."""
        page = MagicMock(spec=ft.Page)
        page.theme_mode = "System"
        page.clean = MagicMock()
        page.open = MagicMock()
        page.update = MagicMock()
        page.add = MagicMock()
        page.switchcraft_session = {}
        page.appbar = None
        page.snack_bar = None
        page.dialog = None
        page.bottom_sheet = None
        page.banner = None
        page.end_drawer = None
        page.drawer = None
        page.set_clipboard = MagicMock()
        page.show_snack_bar = MagicMock()
        page.close = MagicMock()
        page.window = MagicMock()
        page.window.min_width = 1200
        page.window.min_height = 800

        _ = ModernApp(page)

        # verify clean called at least once (in build_ui)
        assert page.clean.call_count >= 1, "page.clean() should be called to remove loading screen"

    def test_sidebar_is_compact(self):
        """Regression Test: Sidebar buttons should be compact (no text labels in main column)."""
        page = MagicMock(spec=ft.Page)
        page.open = MagicMock()
        app = ModernApp(page)

        sidebar = app.sidebar
        assert isinstance(sidebar, HoverSidebar)

        column_controls = sidebar.sidebar_column.controls
        for ctrl in column_controls:
            if isinstance(ctrl, ft.Container) and isinstance(ctrl.content, ft.Column):
                 inner_col = ctrl.content
                 has_text = any(isinstance(c, ft.Text) for c in inner_col.controls)
                 assert not has_text, "Sidebar buttons should not have text labels in compact mode"

    def test_sidebar_click_navigation_model(self):
        """Regression Test: Sidebar should rely on click navigation (no flyouts)."""
        page = MagicMock(spec=ft.Page)
        page.open = MagicMock()
        app = ModernApp(page)

        sidebar = app.sidebar
        assert isinstance(sidebar, HoverSidebar)

        # Verify NO flyout container exists in the new model
        assert not hasattr(sidebar, "flyout_container"), "Sidebar should not have a flyout container in click-based model"

        # Verify click handler is bound
        btn = sidebar.sidebar_column.controls[1] # Skip spacer
        assert isinstance(btn, ft.Container)
        assert btn.on_click is not None, "Sidebar buttons must have click handlers"

    def test_category_view_instantiation(self):
        """Regression Test: CategoryView should initialize without property setter errors."""
        from switchcraft.gui_modern.views.category_view import CategoryView

        page = MagicMock(spec=ft.Page)
        page.open = MagicMock()
        destinations = [MagicMock(icon="icon", label="label")] * 20
        on_navigate = MagicMock()

        # This attempt should NOT raise "property 'page' ... has no setter"
        try:
            view = CategoryView(page, "Test Category", [0, 1], on_navigate, destinations)
        except AttributeError as e:
            pytest.fail(f"CategoryView instantiation failed with AttributeError: {e}")
        except Exception as e:
            pytest.fail(f"CategoryView instantiation failed: {e}")

        assert view is not None
        assert view.app_page == page
