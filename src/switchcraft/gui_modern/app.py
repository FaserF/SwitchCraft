import flet as ft
from switchcraft import __version__
from switchcraft.utils.i18n import i18n
import logging

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
                alignment=ft.alignment.center,
            )
        )
        self.page.update()

        # Perform deferred UI building
        self.build_ui()

    def setup_page(self):
        self.page.title = f"SwitchCraft v{__version__}"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        try:
            self.page.window.min_width = 800
            self.page.window.min_height = 600
        except Exception:
            pass  # Older Flet versions

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

        # Content Area - Simple Column
        self.content = ft.Column(
            expand=True,
            controls=[
                ft.Text(i18n.get("welcome_title") or "Welcome to Modern SwitchCraft", size=30, weight=ft.FontWeight.BOLD),
                ft.Text(i18n.get("welcome_subtitle") or "Select a tool from the sidebar to get started."),
            ],
        )

        # Main Layout
        self.page.clean()
        self.page.add(
            ft.Row(
                controls=[
                    self.rail,
                    ft.VerticalDivider(width=1),
                    ft.Container(content=self.content, expand=True, padding=20),
                ],
                expand=True,
            )
        )

    def nav_change(self, e):
        idx = e.control.selected_index
        logger.info(f"Navigation changed to index: {idx}")

        # Clear and rebuild content
        self.content.controls.clear()

        if idx == 0:
            self.content.controls.append(ft.Text(i18n.get("nav_home") or "Home Dashboard", size=30, weight=ft.FontWeight.BOLD))
            self.content.controls.append(ft.Text(i18n.get("welcome_subtitle") or "Welcome to SwitchCraft Modern UI!"))
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
        else:
            self.content.controls.append(ft.Text(f"Unknown tab: {idx}", color="orange"))

        self.page.update()


def main(page: ft.Page):
    """Entry point for Flet app."""
    ModernApp(page)


if __name__ == "__main__":
    ft.app(target=main)
