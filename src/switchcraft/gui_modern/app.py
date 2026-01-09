import flet as ft
from switchcraft import __version__
from switchcraft.utils.i18n import i18n
from switchcraft.utils.config import SwitchCraftConfig
import logging
import time

logger = logging.getLogger(__name__)

class ModernApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.clean()
        self.setup_page()

        # Show Loading indicator
        self.loading_text = ft.Text("Loading SwitchCraft...", size=20)
        self.loading_ring = ft.ProgressRing(width=40, height=40, stroke_width=2)

        self.page.add(
            ft.Container(
                content=ft.Column(
                    controls=[
                        self.loading_ring,
                        self.loading_text,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                expand=True,
                alignment=ft.Alignment.CENTER,
            )
        )
        self.page.update()

        # Perform deferred UI building
        self.build_ui()

    def setup_page(self):
        self.page.title = f"SwitchCraft v{__version__}"
        # Parse theme
        theme_pref = SwitchCraftConfig.get_value("Theme", "System")
        self.page.theme_mode = ft.ThemeMode.DARK if theme_pref == "Dark" else ft.ThemeMode.LIGHT if theme_pref == "Light" else ft.ThemeMode.SYSTEM
        self.page.padding = 0
        try:
            self.page.window.min_width = 1000
            self.page.window.min_height = 700
        except Exception:
            pass

    def build_ui(self):
        # Sidebar Navigation
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label=i18n.get("nav_home") or "Home"),
                ft.NavigationRailDestination(icon=ft.Icons.SEARCH, selected_icon=ft.Icons.SEARCH, label=i18n.get("tab_analyzer") or "Analyzer"),
                ft.NavigationRailDestination(icon=ft.Icons.SMART_TOY_OUTLINED, selected_icon=ft.Icons.SMART_TOY, label=i18n.get("tab_helper") or "AI Helper"),
                ft.NavigationRailDestination(icon=ft.Icons.SHOP_TWO_OUTLINED, selected_icon=ft.Icons.SHOP_TWO, label=i18n.get("tab_winget") or "Winget"),
                ft.NavigationRailDestination(icon=ft.Icons.CLOUD_UPLOAD_OUTLINED, selected_icon=ft.Icons.CLOUD_UPLOAD, label=i18n.get("tab_intune") or "Intune"),
                ft.NavigationRailDestination(icon=ft.Icons.HISTORY, selected_icon=ft.Icons.HISTORY, label=i18n.get("tab_history") or "History"),
                ft.NavigationRailDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label=i18n.get("tab_settings") or "Settings"),
            ],
            on_change=self.nav_change,
        )

        # Content Area
        self.content = ft.Column(expand=True)

        # Load Home by default
        self._load_home()

        # Main Layout
        self.page.clean()
        self.page.add(
            ft.Row(
                controls=[
                    self.rail,
                    ft.VerticalDivider(width=1),
                    ft.Container(content=self.content, expand=True, padding=0),
                ],
                expand=True,
            )
        )

    def _load_home(self):
        self.content.controls.clear()
        self.content.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text(i18n.get("welcome_title") or "Welcome to Modern SwitchCraft", size=40, weight=ft.FontWeight.BOLD),
                    ft.Text(i18n.get("welcome_subtitle") or "Select a tool from the sidebar to get started.", size=16),
                    ft.Container(height=20),
                    ft.Icon(ft.Icons.AUTO_AWESOME, size=100, color=ft.Colors.BLUE_200)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment.CENTER,
                expand=True
            )
        )

    def nav_change(self, e):
        idx = e.control.selected_index
        self.content.controls.clear()

        if idx == 0:
            self._load_home()
        elif idx == 1:
            try:
                from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView
                self.content.controls.append(ModernAnalyzerView(self.page))
            except Exception as ex:
                self.content.controls.append(ft.Text(f"Error loading Analyzer: {ex}", color="red"))
        elif idx == 2:
            try:
                from switchcraft.gui_modern.views.helper_view import ModernHelperView
                self.content.controls.append(ModernHelperView(self.page))
            except Exception as ex:
                self.content.controls.append(ft.Text(f"Error loading Helper: {ex}", color="red"))
        elif idx == 3:
            try:
                from switchcraft.gui_modern.views.winget_view import ModernWingetView
                self.content.controls.append(ModernWingetView(self.page))
            except Exception as ex:
                self.content.controls.append(ft.Text(f"Error loading Winget: {ex}", color="red"))
        elif idx == 4:
            try:
                from switchcraft.gui_modern.views.intune_view import ModernIntuneView
                self.content.controls.append(ModernIntuneView(self.page))
            except Exception as ex:
                self.content.controls.append(ft.Text(f"Error loading Intune: {ex}", color="red"))
        elif idx == 5:
            try:
                from switchcraft.gui_modern.views.history_view import ModernHistoryView
                self.content.controls.append(ModernHistoryView(self.page))
            except Exception as ex:
                self.content.controls.append(ft.Text(f"Error loading History: {ex}", color="red"))
        elif idx == 6:
            try:
                from switchcraft.gui_modern.views.settings_view import ModernSettingsView
                self.content.controls.append(ModernSettingsView(self.page))
            except Exception as ex:
                self.content.controls.append(ft.Text(f"Error loading Settings: {ex}", color="red"))

        self.page.update()

    def _show_restart_countdown(self):
        """Overlay for restart required."""
        dlg = ft.AlertDialog(
            title=ft.Text("Restart Required"),
            content=ft.Text("Settings changed. Restarting app..."),
            modal=True,
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

        # In a real scenario we'd trigger a restart of process,
        # but here we just show message or close.
        # Flet window.close() closes the app.
        time.sleep(2)
        import sys
        # For now just close, user has to reopen.
        # Process restart is tricky without external launcher.
        self.page.window.close()


def main(page: ft.Page):
    """Entry point for Flet app."""
    # Add restart method to page for injection if needed, or pass app instance.
    app = ModernApp(page)
    # Monkey patch page to have access to app restart logic?
    # Better: Views should accept 'app' instance or page should store logic.
    # Current Views accept 'page'. We can add '_show_restart_countdown' to page object dynamically if needed,
    # but clean way is views taking app.
    # Since we didn't refactor all views signature, we'll monkeypatch page for backward compat in this refactor.
    page._show_restart_countdown = app._show_restart_countdown


if __name__ == "__main__":
    ft.run(main)
