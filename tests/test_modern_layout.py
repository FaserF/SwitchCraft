
import flet as ft
from unittest.mock import MagicMock
from switchcraft.gui_modern.app import ModernApp

class TestModernLayout:
    def test_sidebar_initialization(self):
        """Verify HoverSidebar is initialized correctly."""
        page = MagicMock(spec=ft.Page)
        page.theme_mode = "System"
        page.open = MagicMock()
        app = ModernApp(page)

        # Check sidebar existence
        assert hasattr(app, "sidebar"), "App must have a sidebar attribute"
        is_sidebar = app.sidebar.__class__.__name__ == "HoverSidebar"
        assert is_sidebar, "SideBar must be an instance of HoverSidebar"

        # Check categories
        assert hasattr(app.sidebar, "categories"), "Sidebar must have categories defined"
        assert len(app.sidebar.categories) > 0, "Sidebar categories must not be empty"

    def test_content_scrolling(self):
        """Verify the main content column enables scrolling."""
        page = MagicMock(spec=ft.Page)
        page.open = MagicMock()
        app = ModernApp(page)

        assert app.content.scroll == ft.ScrollMode.AUTO, "Main content column must have scroll enabled"
        assert app.content.expand is True, "Main content column must expand to fill container"

    def test_appbar_structure(self):
        """Verify AppBar has correct actions and leading control."""
        page = MagicMock(spec=ft.Page)
        page.open = MagicMock()
        app = ModernApp(page)

        # App sets page.appbar
        assert isinstance(page.appbar, ft.AppBar)

        # Check Leading (Logo)
        # It might be an Icon or Image depending on file existence
        assert page.appbar.leading is not None

        # Check Actions
        actions = page.appbar.actions
        assert len(actions) >= 3
        # We expect Back, Notif, Theme buttons
        assert app.back_btn in actions
        assert app.notif_btn in actions
        assert app.theme_icon in actions

        # Check Title (Should be in appbar, not duplicated in body)
        assert isinstance(page.appbar.title, ft.Text)
        assert page.appbar.title.value == "SwitchCraft"

    def test_buttons_configured(self):
        """Verify buttons have on_click handlers."""
        page = MagicMock(spec=ft.Page)
        page.open = MagicMock()
        app = ModernApp(page)

        assert app.back_btn.on_click is not None
        assert app.notif_btn.on_click is not None
        assert app.theme_icon.on_click is not None
