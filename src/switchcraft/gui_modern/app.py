import flet as ft
from switchcraft import __version__
from switchcraft.utils.i18n import i18n
from switchcraft.utils.config import SwitchCraftConfig
import logging
import time

logger = logging.getLogger(__name__)

class ModernApp:
    def __init__(self, page: ft.Page, splash_proc=None):
        self.page = page
        self.page.clean()
        self.setup_page()

        # Show Loading indicator - centered on full screen
        self.loading_text = ft.Text("Loading SwitchCraft...", size=24, weight=ft.FontWeight.BOLD)
        self.loading_ring = ft.ProgressRing(width=50, height=50, stroke_width=3)

        self.page.add(
            ft.Container(
                content=ft.Column(
                    controls=[
                        self.loading_ring,
                        self.loading_text,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20,
                ),
                expand=True,
                alignment=ft.alignment.center,  # Use the alignment constant
            )
        )
        self.page.update()

        # Shutdown Splash Screen now that Flet window is visible
        if splash_proc:
            try:
                splash_proc.terminate()
            except Exception:
                pass


        # Perform deferred UI building.
        # User requested visible loading screen. Since Flet execution here is linear during init,
        # we add a small sleep to ensure the "Loading..." ring is perceived.
        import time
        time.sleep(1.5)

        # View cache - keeps views in memory to preserve state between tab switches
        self._view_cache = {}

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

        # Enable Global Drag & Drop (Safety check for older Flet)
        if hasattr(self.page, "on_drop"):
            self.page.on_drop = self.handle_window_drop

        self.banner_container = ft.Container() # Placeholder

    def setup_banner(self):
        from switchcraft.utils.i18n import i18n
        version_lower = __version__.lower()
        if "beta" in version_lower or "dev" in version_lower:
            key = "banner_dev_msg" if "dev" in version_lower else "banner_beta_msg"
            default_text = f"You are using a {('Development' if 'dev' in version_lower else 'Beta')} Build ({__version__}). Bugs may occur."
            text = i18n.get(key, version=__version__, default=default_text)

            bg_color = ft.Colors.RED if "dev" in version_lower else ft.Colors.AMBER
            text_color = ft.Colors.WHITE if "dev" in version_lower else ft.Colors.BLACK

            self.banner_container = ft.Container(
                content=ft.Text(text, color=text_color, weight="bold", text_align="center"),
                bgcolor=bg_color,
                padding=5,
                alignment=ft.Alignment(0, 0),  # Center alignment
                width=None  # Full width via expand
            )

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
                ft.NavigationRailDestination(icon=ft.Icons.STORE_MALL_DIRECTORY_OUTLINED, selected_icon=ft.Icons.STORE, label="Intune Store"),
                ft.NavigationRailDestination(icon=ft.Icons.HISTORY, selected_icon=ft.Icons.HISTORY, label=i18n.get("tab_history") or "History"),
                ft.NavigationRailDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label=i18n.get("tab_settings") or "Settings"),
            ],
            on_change=self.nav_change,
        )

        # Content Area

        self.content = ft.Column(expand=True)

        # Load Home by default
        self._load_home()
        from switchcraft.gui_modern.views.home_view import ModernHomeView
        self.content = ft.Column(
            expand=True,
            controls=[
                ModernHomeView(self.page, on_navigate=self.goto_tab)
            ],
        )

        # Add Banner if needed
        self.setup_banner()

        self.page.clean()
        self.page.add(
            ft.Column([
                ft.Row(
                    controls=[
                        self.rail,
                        ft.VerticalDivider(width=1),
                        ft.Container(content=self.content, expand=True, padding=20),
                    ],
                    expand=True,
                ),
                self.banner_container # Add banner at bottom
            ], expand=True)
        )
        self.page.update()

    def _load_home(self):
        # This generic load home is replaced by ModernHomeView usage
        from switchcraft.gui_modern.views.home_view import ModernHomeView
        self.content.controls.clear()
        self.content.controls.append(ModernHomeView(self.page, on_navigate=self.goto_tab))

    def goto_tab(self, index):
        """Programmatically switch tabs."""
        self.rail.selected_index = index
        self._switch_to_tab(index)

    def nav_change(self, e):
        idx = int(e.control.selected_index)
        logger.info(f"Navigation changed to index: {idx}")
        self._switch_to_tab(idx)

    def handle_window_drop(self, e: ft.ControlEvent):
        """Global drop handler - switches to analyzer if file is dropped anywhere."""
        if e.files:
            file_path = e.files[0].path
            if file_path.lower().endswith((".exe", ".msi")):
                logger.info(f"Global drop detected: {file_path}")
                # 1. Switch Tab to Analyzer
                self.goto_tab(1)

                # 2. Trigger Analysis
                # Our _switch_to_tab ensures 'analyzer' is in cache if it wasn't
                if 'analyzer' in self._view_cache:
                    self._view_cache['analyzer'].start_analysis(file_path)

    def _switch_to_tab(self, idx):
        """Internal method to switch to a specific tab index."""

        # 1. SHOW LOADING STATE IMMEDIATELY
        self.content.controls.clear()
        self.content.controls.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.ProgressRing(),
                        ft.Text("Loading...", size=16)
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                alignment=ft.Alignment(0, 0),
                expand=True
            )
        )
        self.page.update()

        # Small sleep to ensure the UI has time to render the loading state
        # before the main thread potentially gets blocked by heavy view initialization.
        time.sleep(0.05)

        # 2. LOAD ACTUAL CONTENT
        # We prepare the new controls in a list, then swap them in.
        new_controls = []

        if idx == 0:
            from switchcraft.gui_modern.views.home_view import ModernHomeView
            new_controls.append(ModernHomeView(self.page, on_navigate=self.goto_tab))
        elif idx == 1:
            # Analyzer - cached
            try:
                if 'analyzer' not in self._view_cache:
                    from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView
                    self._view_cache['analyzer'] = ModernAnalyzerView(self.page)
                new_controls.append(self._view_cache['analyzer'])
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Analyzer: {ex}", color="red"))
        elif idx == 2:
            # Helper - cached
            try:
                if 'helper' not in self._view_cache:
                    from switchcraft.gui_modern.views.helper_view import ModernHelperView
                    self._view_cache['helper'] = ModernHelperView(self.page)
                new_controls.append(self._view_cache['helper'])
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Helper: {ex}", color="red"))
        elif idx == 3:
            # Winget - cached
            try:
                if 'winget' not in self._view_cache:
                    from switchcraft.gui_modern.views.winget_view import ModernWingetView
                    self._view_cache['winget'] = ModernWingetView(self.page)
                new_controls.append(self._view_cache['winget'])
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Winget: {ex}", color="red"))
        elif idx == 4:
            try:
                from switchcraft.gui_modern.views.intune_view import ModernIntuneView
                new_controls.append(ModernIntuneView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Intune: {ex}", color="red"))
        elif idx == 5:
             try:
                 from switchcraft.gui_modern.views.intune_store_view import ModernIntuneStoreView
                 new_controls.append(ModernIntuneStoreView(self.page))
             except Exception as ex:
                 new_controls.append(ft.Text(f"Error loading Intune Store: {ex}", color="red"))
        elif idx == 6:
            try:
                from switchcraft.gui_modern.views.history_view import ModernHistoryView
                new_controls.append(ModernHistoryView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading History: {ex}", color="red"))
        elif idx == 7:
            try:
                from switchcraft.gui_modern.views.settings_view import ModernSettingsView
                new_controls.append(ModernSettingsView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Settings: {ex}", color="red"))

        # 3. SWAP CONTENT
        self.content.controls.clear()
        self.content.controls.extend(new_controls)
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
