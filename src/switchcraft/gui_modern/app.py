import flet as ft
from switchcraft import __version__
from switchcraft.utils.i18n import i18n
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.gui_modern.views.script_upload_view import ScriptUploadView
from switchcraft.gui_modern.views.macos_wizard_view import MacOSWizardView
from switchcraft.services.notification_service import NotificationService
from switchcraft.services.addon_service import AddonService
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class ModernApp:
    def __init__(self, page: ft.Page, splash_proc=None):
        self.page = page
        self.page.clean()
        self.setup_page()


        # Notification Service
        self.notification_service = NotificationService()
        self.notification_service.add_listener(self._on_notification_update)

        # Addon Service
        self.addon_service = AddonService()
        self.dynamic_addons = []

        # Build Actions (Theme Toggle + Notifications)
        self.theme_icon = ft.IconButton(
            ft.Icons.DARK_MODE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE,
            on_click=self.toggle_theme,
            tooltip=i18n.get("toggle_theme")
        )

        self.notif_badge = ft.Badge(
            content=ft.Icon(ft.Icons.NOTIFICATIONS),
            text="0",
            visible=False
        )

        self.notif_btn = ft.IconButton(
            content=self.notif_badge,
            on_click=self._open_notifications
        )

        self.page.appbar = ft.AppBar(
            leading=ft.Icon(ft.Icons.INSTALL_DESKTOP, size=30),
            leading_width=40,
            title=ft.Text(f"SwitchCraft v{__version__}", weight=ft.FontWeight.BOLD),
            center_title=False,
            bgcolor=ft.Colors.SURFACE_VARIANT,
            actions=[
                self.notif_btn,
                self.theme_icon,
                ft.Container(width=10)
            ],
        )

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
                alignment=ft.Alignment(0, 0),  # Use the alignment constant
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
            self.page.window_prevent_close = True  # Handle custom close
            self.page.on_window_event = self.window_event
            self.page.window.min_width = 1200
            self.page.window.min_height = 800
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


        destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label=i18n.get("nav_home")
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.APPS_OUTLINED, selected_icon=ft.Icons.APPS, label=i18n.get("nav_apps")
                ),  # 1 Winget
                ft.NavigationRailDestination(
                    icon=ft.Icons.ANALYTICS_OUTLINED, selected_icon=ft.Icons.ANALYTICS, label=i18n.get("nav_analyze")
                ),  # 2 Analyze
                ft.NavigationRailDestination(
                    icon=ft.Icons.BUILD_OUTLINED, selected_icon=ft.Icons.BUILD, label=i18n.get("nav_generate")
                ),  # 3 Generate
                ft.NavigationRailDestination(
                    icon=ft.Icons.CLOUD_UPLOAD_OUTLINED,
                    selected_icon=ft.Icons.CLOUD_UPLOAD, label=i18n.get("nav_intune")
                ),  # 4 Intune
                ft.NavigationRailDestination(
                    icon=ft.Icons.SHOP_TWO_OUTLINED, selected_icon=ft.Icons.SHOP_TWO, label="Intune Store"
                ),  # 5 Intune Store
                ft.NavigationRailDestination(
                    icon=ft.Icons.DESCRIPTION_OUTLINED, selected_icon=ft.Icons.DESCRIPTION, label="Scripts"
                ),  # 6 Scripts
                ft.NavigationRailDestination(
                    icon=ft.Icons.APPLE_OUTLINED, selected_icon=ft.Icons.APPLE, label="MacOS"
                ),  # 7 MacOS
                ft.NavigationRailDestination(
                    icon=ft.Icons.HISTORY_OUTLINED, selected_icon=ft.Icons.HISTORY, label=i18n.get("nav_history")
                ),  # 8 History
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label=i18n.get("nav_settings")
                ),  # 7 Settings
                ft.NavigationRailDestination(
                    icon=ft.Icons.AUTO_FIX_HIGH, selected_icon=ft.Icons.AUTO_FIX_HIGH, label="Wizard"
                ),  # 8 Wizard
                ft.NavigationRailDestination(
                    icon=ft.Icons.RULE, selected_icon=ft.Icons.RULE, label="Tester"
                ),  # 9 Tester
                ft.NavigationRailDestination(
                    icon=ft.Icons.LAYERS, selected_icon=ft.Icons.LAYERS, label="Stacks"
                ),  # 10 Stacks
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD, selected_icon=ft.Icons.DASHBOARD, label="Dashboard"
                ),  # 11 Dashboard
                ft.NavigationRailDestination(
                    icon=ft.Icons.LIBRARY_BOOKS_OUTLINED, selected_icon=ft.Icons.LIBRARY_BOOKS, label="Library"
                ),  # 14 Library
                ft.NavigationRailDestination(
                     icon=ft.Icons.PEOPLE_OUTLINED, selected_icon=ft.Icons.PEOPLE, label="Groups"
                ),  # 15 Groups
                ft.NavigationRailDestination(
                     icon=ft.Icons.EXTENSION_OUTLINED, selected_icon=ft.Icons.EXTENSION, label="Addons"
                ),  # 16 Addon Manager
            ]

        # Load Dynamic Addons
        try:
            self.dynamic_addons = self.addon_service.list_addons()
            for addon in self.dynamic_addons:
                icon_name = addon.get("icon", "EXTENSION") # Default icon
                # Resolve icon if possible, else default
                icon_code = getattr(ft.Icons, icon_name, ft.Icons.EXTENSION)

                destinations.append(
                    ft.NavigationRailDestination(
                        icon=icon_code,
                        label=addon.get("name", "Addon")
                    )
                )
        except Exception as e:
            logger.error(f"Failed to load dynamic addons: {e}")

        # Navigation Rail
        self.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9,
            destinations=destinations,
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
                self.goto_tab(2) # Analyzer is now index 2

                # 2. Trigger Analysis
                # Our _switch_to_tab ensures 'analyzer' is in cache if it wasn't
                if 'analyzer' in self._view_cache:
                    self._view_cache['analyzer'].start_analysis(file_path)

    def _switch_to_tab(self, idx):
        """Internal method to switch to a specific tab index."""

        # 1. SHOW LOADING STATE IMMEDIATELY
        self.content.controls.clear()
        # Use a temporary loading container, but now let's make it smarter if we want smooth usage.
        # Actually, for smooth transitions, usage of AnimatedSwitcher is better than clearing controls.
        # But `self.content` is a Column. Let's change `self.content` to be an AnimatedSwitcher in init?
        # That would require refactoring `build_ui`.

        # For now, let's just fade in the new content
        loading_view = ft.Container(
                 content=ft.Column(
                     controls=[
                         ft.ProgressRing(),
                         ft.Text("Loading...", size=16)
                     ],
                     horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                     alignment=ft.MainAxisAlignment.CENTER
                 ),
                 alignment=ft.Alignment(0, 0),
                 expand=True,
                 animate_opacity=300,
                 opacity=1 # Start visible
             )
        self.content.controls.append(loading_view)
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
            # Winget (Apps)
            try:
                if 'winget' not in self._view_cache:
                    from switchcraft.gui_modern.views.winget_view import ModernWingetView
                    self._view_cache['winget'] = ModernWingetView(self.page)
                new_controls.append(self._view_cache['winget'])
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Winget: {ex}", color="red"))
        elif idx == 2:
            # Analyzer
            try:
                if 'analyzer' not in self._view_cache:
                    from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView
                    self._view_cache['analyzer'] = ModernAnalyzerView(self.page)
                new_controls.append(self._view_cache['analyzer'])
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Analyzer: {ex}", color="red"))
        elif idx == 3:
            # Helper (Generate)
            try:
                if 'helper' not in self._view_cache:
                    from switchcraft.gui_modern.views.helper_view import ModernHelperView
                    self._view_cache['helper'] = ModernHelperView(self.page)
                new_controls.append(self._view_cache['helper'])
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Helper: {ex}", color="red"))
        elif idx == 4:
            # Intune
            try:
                from switchcraft.gui_modern.views.intune_view import ModernIntuneView
                new_controls.append(ModernIntuneView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Intune: {ex}", color="red"))
        elif idx == 5:
            # Intune Store
             try:
                 from switchcraft.gui_modern.views.intune_store_view import ModernIntuneStoreView
                 new_controls.append(ModernIntuneStoreView(self.page))
             except Exception as ex:
                 new_controls.append(ft.Text(f"Error loading Intune Store: {ex}", color="red"))
        elif idx == 6:
            # Scripts
            try:
                new_controls.append(ScriptUploadView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Scripts: {ex}", color="red"))
        elif idx == 7:
            # MacOS Wizard (NEW)
            try:
                new_controls.append(MacOSWizardView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading MacOS Wizard: {ex}", color="red"))
        elif idx == 8:
            # History
            try:
                from switchcraft.gui_modern.views.history_view import ModernHistoryView
                new_controls.append(ModernHistoryView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading History: {ex}", color="red"))
        elif idx == 9:
            # Settings
            try:
                from switchcraft.gui_modern.views.settings_view import ModernSettingsView
                new_controls.append(ModernSettingsView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Settings: {ex}", color="red"))
        elif idx == 10: # Wizard
            try:
                from switchcraft.gui_modern.views.packaging_wizard_view import PackagingWizardView
                new_controls.append(PackagingWizardView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Wizard: {ex}", color="red"))
        elif idx == 11:  # Tester
            try:
                from switchcraft.gui_modern.views.detection_tester_view import DetectionTesterView
                new_controls.append(DetectionTesterView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Tester: {ex}", color="red"))
        elif idx == 12:  # Stacks
            try:
                from switchcraft.gui_modern.views.stack_manager_view import StackManagerView
                new_controls.append(StackManagerView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Stacks: {ex}", color="red"))
        elif idx == 13:  # Dashboard
            try:
                from switchcraft.gui_modern.views.dashboard_view import DashboardView
                new_controls.append(DashboardView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Dashboard: {ex}", color="red"))
        elif idx == 14:  # Library
            try:
                from switchcraft.gui_modern.views.library_view import LibraryView
                new_controls.append(LibraryView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Library: {ex}", color="red"))
        elif idx == 15:  # Groups
            try:
                from switchcraft.gui_modern.views.group_manager_view import GroupManagerView
                new_controls.append(GroupManagerView(self.page))
            except Exception as ex:
                new_controls.append(ft.Text(f"Error loading Groups: {ex}", color="red"))
        elif idx == 16: # Addon Manager
            try:
                from switchcraft.gui_modern.views.addon_manager_view import AddonManagerView
                new_controls.append(AddonManagerView(self.page))
            except Exception as ex:
                 new_controls.append(ft.Text(f"Error loading Addon Manager: {ex}", color="red"))
        else:
            # Dynamic Addons
            dynamic_idx = idx - 17
            if 0 <= dynamic_idx < len(self.dynamic_addons):
                addon = self.dynamic_addons[dynamic_idx]
                try:
                    view_class = self.addon_service.load_addon_view(addon['id'])
                    new_controls.append(view_class(self.page))
                except Exception as ex:
                     new_controls.append(ft.Text(f"Error loading addon {addon.get('name')}: {ex}", color="red"))
            else:
                 new_controls.append(ft.Text("Unknown Tab", color="red"))


        # 3. SWAP CONTENT with Fade In
        self.content.controls.clear()

        # Wrap new controls in a container with opacity 0 initially
        fade_container = ft.Container(
            content=new_controls[0] if new_controls else ft.Text("Error loading view"),
            expand=True,
            opacity=0,
            animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_OUT)
        )

        self.content.controls.append(fade_container)
        self.page.update()

        # Trigger fade in
        fade_container.opacity = 1
        fade_container.update()

    def _on_notification_update(self):
        count = self.notification_service.get_unread_count()
        if count > 0:
            self.notif_badge.text = str(count)
            self.notif_badge.visible = True
        else:
            self.notif_badge.visible = False
        self.notif_badge.update()

    def _open_notifications(self, e):
        # Build Drawer Content
        notifs = self.notification_service.get_notifications()

        items = []
        if not notifs:
            items.append(ft.Text("No notifications", italic=True))
        else:
            for n in notifs:
                icon = ft.Icons.INFO
                color = ft.Colors.BLUE
                if n["type"] == "success":
                    icon = ft.Icons.CHECK_CIRCLE
                    color = ft.Colors.GREEN
                elif n["type"] == "warning":
                    icon = ft.Icons.WARNING
                    color = ft.Colors.ORANGE
                elif n["type"] == "error":
                    icon = ft.Icons.ERROR
                    color = ft.Colors.RED

                items.append(
                    ft.ListTile(
                        leading=ft.Icon(icon, color=color),
                        title=ft.Text(n["title"], weight=ft.FontWeight.BOLD if not n["read"] else ft.FontWeight.NORMAL),
                        subtitle=ft.Text(n["message"]),
                        trailing=ft.Text(n["timestamp"].strftime("%H:%M"), size=10),
                        on_click=lambda _, nid=n["id"]: self._mark_read(nid)
                    )
                )

        drawer = ft.NavigationDrawer(
            controls=[
                ft.Container(height=12),
                ft.Row([
                    ft.Text("Notifications", size=20, weight=ft.FontWeight.BOLD),
                    ft.TextButton("Clear All", on_click=lambda _: [self.notification_service.clear_all(), self.page.close(drawer)])
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, run_spacing=10),
                ft.Divider(),
                *items
            ],
        )
        self.page.open(drawer)
        self.notification_service.mark_all_read()

    def _mark_read(self, nid):
        self.notification_service.mark_read(nid)
        # Refresh drawer? Or just let it be.
        # Drawer is static once opened unless we use stateful content.
        # For simple mark read, we handle it in service, app updates badge.
        pass

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
