from pathlib import Path
import flet as ft
from switchcraft import __version__
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n

from switchcraft.gui_modern.views.script_upload_view import ScriptUploadView
from switchcraft.gui_modern.views.macos_wizard_view import MacOSWizardView
from switchcraft.services.notification_service import NotificationService
from switchcraft.services.addon_service import AddonService
from switchcraft.gui_modern.controls.sidebar import HoverSidebar
import logging
import time

logger = logging.getLogger(__name__)

class ModernApp:
    def __init__(self, page: ft.Page, splash_proc=None):
        self.page = page
        self.page.switchcraft_app = self  # Store reference for views to access goto_tab
        self.page.clean()

        # Initialize history early
        self._navigation_history = [0]

        self.setup_page()


        # Notification Service
        self.notification_service = NotificationService()
        # Listener added later after UI init

        # Addon Service
        self.addon_service = AddonService()
        self.dynamic_addons = []

        # Build Actions (Theme Toggle + Notifications)
        self.theme_icon = ft.IconButton(
            ft.Icons.DARK_MODE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE,
            on_click=self.toggle_theme,
            tooltip=i18n.get("toggle_theme")
        )

        # Notification button
        # Notification button
        self.notif_btn = ft.IconButton(
            icon=ft.Icons.NOTIFICATIONS,
            tooltip="Notifications",
            on_click=self._toggle_notification_drawer
        )

        # Now add listener
        self.notification_service.add_listener(self._on_notification_update)

        # Back button (Early init for AppBar)
        self.back_btn = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip=i18n.get("btn_back") or "Back",
            on_click=self._go_back_handler,
            icon_size=24
        )

        # Try to find logo for AppBar
        logo_icon = ft.Icon(ft.Icons.INSTALL_DESKTOP, size=30)

        self.page.appbar = ft.AppBar(
            leading=logo_icon,
            leading_width=40,
            title=ft.Text("SwitchCraft", weight=ft.FontWeight.BOLD),
            center_title=False,
            bgcolor="SURFACE_VARIANT",
            actions=[
                self.back_btn,
                self.notif_btn,
                self.theme_icon,
                ft.Container(width=10)
            ],
        )


        # Global Progress Bar (visible during long operations)
        self.global_progress = ft.ProgressBar(height=4, visible=False, color="BLUE_400", bgcolor="SURFACE_VARIANT")

        # Show Loading indicator - centered on full screen
        self.loading_text = ft.Text("Loading SwitchCraft...", size=24, weight=ft.FontWeight.BOLD)
        self.loading_bar = ft.ProgressBar(width=400, color="BLUE_400", bgcolor="SURFACE_VARIANT")

        # The initial page content is a loading screen.
        # The actual app layout will be built in build_ui() and replace this.
        self.page.add(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Container(height=40),
                        self.loading_bar,
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

        time.sleep(0.1) # Minimized startup delay

        # View cache - keeps views in memory to preserve state between tab switches
        self._view_cache = {}

        # Auto-install bundled addons on first start
        self._install_bundled_addons()

        self.build_ui()

    def _go_back_handler(self, e):
        """Handle back button click."""
        if len(self._navigation_history) > 1:
            self._navigation_history.pop()  # Remove current
            prev_idx = self._navigation_history[-1] if self._navigation_history else 0
            # Don't add to history when going back
            self._switch_to_tab(prev_idx)
            self.sidebar.set_selected_index(prev_idx)

    def _open_notifications(self, e):
        """Open notification history or drawer."""
        # For now, we will use a simple dialog to show notifications
        # In a real app this might be a navigation drawer

        notifications = self.notification_service.get_history()

        list_view = ft.ListView(expand=True, spacing=10, padding=10)

        if not notifications:
            list_view.controls.append(ft.Text(i18n.get("no_notifications") or "No notifications", italic=True))
        else:
            for notif in reversed(notifications):
                list_view.controls.append(
                   ft.ListTile(
                       leading=ft.Icon(ft.Icons.INFO if notif.type == "info" else ft.Icons.ERROR if notif.type == "error" else ft.Icons.WARNING),
                       title=ft.Text(notif.title),
                       subtitle=ft.Text(f"{notif.message}\n{notif.timestamp}", size=12),
                   )
                )

        self.page.open(dlg)

    def _toggle_notification_drawer(self, e):
        """Toggles the notification drawer."""
        # Check if drawer is currently open
        if hasattr(self, "_active_drawer") and self._active_drawer and self._active_drawer.open:
             self.page.close(self._active_drawer)
        else:
             self._open_notifications_drawer(e)

    def _open_notifications_drawer(self, e):
        """Builds and opens the notification drawer."""
        notifs = self.notification_service.get_notifications()
        items = []
        if not notifs:
            items.append(ft.Text("No notifications", italic=True))
        else:
            for n in notifs:
                icon = ft.Icons.INFO
                color = "BLUE"
                # ... (Logic identical to previous _open_notifications) ...
                if n["type"] == "success":
                    icon = ft.Icons.CHECK_CIRCLE
                    color = "GREEN"
                elif n["type"] == "warning":
                    icon = ft.Icons.WARNING
                    color = "ORANGE"
                elif n.get("type") == "error":
                    icon = ft.Icons.ERROR
                    color = "RED"

                items.append(
                    ft.ListTile(
                        leading=ft.Icon(icon, color=color),
                        title=ft.Text(n["title"], weight=ft.FontWeight.BOLD if not n.get("read") else ft.FontWeight.NORMAL),
                        subtitle=ft.Text(n["message"]),
                        trailing=ft.Text(n["timestamp"].strftime("%H:%M") if "timestamp" in n else "", size=10),
                        # on_click=lambda _, nid=n["id"]: self._mark_read(nid)
                    )
                )

        drawer = ft.NavigationDrawer(
            controls=[
                ft.Container(height=12),
                ft.Row([
                    ft.Text(i18n.get("notifications") or "Notifications", size=20, weight=ft.FontWeight.BOLD),
                    # ft.TextButton("Clear All", on_click=lambda _: self._clear_all_notifications(drawer))
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, run_spacing=10),
                ft.Divider(),
                ft.Column(items, scroll=ft.ScrollMode.AUTO, expand=True)
            ],
        )
        self._active_drawer = drawer
        self.page.open(drawer)
        self.notification_service.mark_all_read()

    def _clear_notifications(self, e, dlg):
        self.notification_service.clear()
        self.page.close(dlg)
        self.page.snack_bar = ft.SnackBar(ft.Text("Notifications cleared"))
        self.page.snack_bar.open = True
        self.page.update()

    def setup_page(self):
        self.page.title = f"SwitchCraft v{__version__}"
        # Parse theme
        theme_pref = SwitchCraftConfig.get_value("Theme", "System")
        self.page.theme_mode = ft.ThemeMode.DARK if theme_pref == "Dark" else ft.ThemeMode.LIGHT if theme_pref == "Light" else ft.ThemeMode.SYSTEM
        self.page.padding = 0

        try:
            self.page.window.min_width = 1200
            self.page.window.min_height = 800

            # For Flet 0.80.1, use on_window_event or on_close handler
            # Prefer on_resized/on_event pattern if available
            try:
                self.page.window.on_event = self.window_event
            except AttributeError:
                pass

            # Try new style event binding (Flet >= 0.21)
            try:
                self.page.on_window_event = self.window_event
            except AttributeError:
                pass

            # Jump List (Windows Quick Actions)
            try:
                if hasattr(ft, "JumpListItem"):
                    self.page.window.jump_list = [
                        ft.JumpListItem(
                            text="Packaging Wizard",
                            icon="images/switchcraft_logo.ico",
                            arguments="--wizard",
                            description="Open Packaging Wizard"
                        ),
                        ft.JumpListItem(
                            text="All-in-One Analyzer",
                            icon="images/switchcraft_logo.ico",
                            arguments="--analyzer",
                            description="Open Installer Analyzer"
                        ),
                    ]
            except Exception as e:
                logger.debug(f"JumpList not supported: {e}")

            # Set window icon paths
            import os
            import sys
            root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

            # Set window icon paths - Prefer local assets if available
            # We copied icons to src/switchcraft/assets
            # Calculate path relative to THIS file (app.py) -> assets/
            current_dir = os.path.dirname(os.path.abspath(__file__)) # src/switchcraft/gui_modern
            assets_dir = os.path.join(os.path.dirname(current_dir), "assets") # src/switchcraft/assets

            asset_ico = os.path.join(assets_dir, "switchcraft_logo.ico")
            asset_png = os.path.join(assets_dir, "switchcraft_logo.png")

            if os.path.exists(asset_ico):
                self._ico_path = asset_ico
                self._png_path = asset_png if os.path.exists(asset_png) else asset_ico
            else:
                # Fallback to root images logic
                if getattr(sys, 'frozen', False):
                    base_path = sys._MEIPASS
                    ico_path = os.path.join(base_path, "switchcraft_logo.ico")
                    png_path = os.path.join(base_path, "images", "switchcraft_logo.png")
                else:
                    ico_path = os.path.join(root_path, "images", "switchcraft_logo.ico")
                    png_path = os.path.join(root_path, "images", "switchcraft_logo.png")

                self._ico_path = os.path.abspath(ico_path) if os.path.exists(ico_path) else None
                self._png_path = os.path.abspath(png_path) if os.path.exists(png_path) else self._ico_path

            if self._ico_path:
                self.page.window.icon = self._ico_path

            if hasattr(self.page, 'appbar') and self.page.appbar:
                # Use asset URL for AppBar image if possible, or file path
                # Since we set assets_dir="assets", we can use "/switchcraft_logo.png"
                self.page.appbar.leading = ft.Image(src="/switchcraft_logo.png", width=30, height=30)
                # Fallback if that failed? No, we trust assets.
                # But to be safe, stick to what was working or new asset path?
                # Let's use the asset path relative URL which Flet handles best.
                # src="/switchcraft_logo.png"
                pass
                self.page.appbar.update()
        except Exception as e:
            logger.debug(f"Window properties not available during setup: {e}")

        # Enable Global Drag & Drop
        if hasattr(self.page, "on_drop"):
            self.page.on_drop = self.handle_window_drop

        self.banner_container = ft.Container() # Placeholder

        # Run Startup Update Check
        self._check_startup_updates()

        # Handle Jump List Arguments (Launch Flags)
        import sys
        if "--wizard" in sys.argv:
            # We need to defer this until UI is built
            self._pending_nav_index = 2 # Wizard index
        elif "--analyzer" in sys.argv or "--all-in-one" in sys.argv:
             self._pending_nav_index = 3 # Analyzer index
        else:
            self._pending_nav_index = None

    def set_progress(self, value=None, visible=True):
        """Update global progress bar state."""
        if not hasattr(self, 'global_progress'):
            return
        self.global_progress.value = value
        self.global_progress.visible = visible
        self.page.update()

    def _check_startup_updates(self):
        """Checks for updates in background and notifies user if available."""
        from switchcraft.utils.app_updater import UpdateChecker
        import threading

        def _run():
            try:
                channel = SwitchCraftConfig.get_value("UpdateChannel", "stable")
                checker = UpdateChecker(channel=channel)
                has_update, version_str, update_data = checker.check_for_updates()

                # Store results on page for Settings view to access
                self.page.update_check_result = {
                    "has_update": has_update,
                    "version": version_str,
                    "data": update_data,
                    "checked": True
                }

                if has_update:
                    def go_to_update(e):
                        self.goto_tab(9)
                        self.page.update()

                    snack = ft.SnackBar(
                        content=ft.Text(f"{i18n.get('update_available') or 'Update available'}: {version_str}"),
                        action=i18n.get("btn_details") or "Details",
                        on_action=go_to_update,
                        duration=10000, # Show for 10 seconds
                        bgcolor="BLUE"
                    )
                    self.page.snack_bar = snack
                    snack.open = True
                    self.page.update()
            except Exception as e:
                logger.error(f"Startup update check failed: {e}")
                self.page.update_check_result = {"checked": True, "error": str(e)}

        threading.Thread(target=_run, daemon=True).start()

    def _install_bundled_addons(self):
        """Auto-install bundled addons (advanced, ai) on first start."""
        try:
            # Check for bundled addons in assets
            import sys
            if getattr(sys, 'frozen', False):
                base_path = Path(sys._MEIPASS) / "assets" / "addons"
            else:
                 # src/switchcraft/gui_modern/app.py -> src/switchcraft/assets/addons
                base_path = Path(__file__).parent.parent / "assets" / "addons"

            if not base_path.exists():
                logger.warning(f"Bundled addons directory not found: {base_path}")
                return

            addons_to_install = ["advanced", "ai"]

            for addon_id in addons_to_install:
                 if self.addon_service.is_addon_installed(addon_id):
                     continue

                 zip_path = base_path / f"{addon_id}.zip"
                 if zip_path.exists():
                     self.loading_text.value = f"Installing {addon_id} addon..."
                     self.page.update()
                     try:
                        logger.info(f"Attempting to install bundled addon {addon_id} from {zip_path}")
                        if self.addon_service.install_addon(str(zip_path)):
                            logger.info(f"Bundled addon {addon_id} installed successfully.")
                        else:
                             logger.warning(f"Addon service returned False for {addon_id}")
                     except Exception as ex:
                        logger.error(f"Failed to install bundled addon {addon_id}: {ex}", exc_info=True)

        except Exception as e:
            logger.error(f"Error during bundled addon install: {e}")

    def toggle_theme(self, e):
        """Toggle between light and dark theme."""
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.theme_icon.icon = ft.Icons.DARK_MODE
            SwitchCraftConfig.set_user_preference("Theme", "Light")
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.theme_icon.icon = ft.Icons.LIGHT_MODE
            SwitchCraftConfig.set_user_preference("Theme", "Dark")
        self.page.update()





    def window_event(self, e):
        """Handle window events, specifically closing."""
        if e.data == "close":
            try:
                # Handle Flet API evolution (old vs new properties)
                if hasattr(self.page, "window"):
                    self.page.window.prevent_close = False
                    self.page.window.destroy()
                elif hasattr(self.page, "window_prevent_close"):
                    self.page.window_prevent_close = False
                    self.page.window_destroy()
                else:
                    # Fallback for very old or very new Flet
                    self.page.window_destroy()
            except Exception as ex:
                logger.error(f"Error handling close event: {ex}")
                import sys
                sys.exit(0)

    def setup_banner(self):
        from switchcraft.utils.i18n import i18n
        version_lower = __version__.lower()
        if "beta" in version_lower or "dev" in version_lower:
            key = "banner_dev_msg" if "dev" in version_lower else "banner_beta_msg"
            default_text = f"You are using a {('Development' if 'dev' in version_lower else 'Beta')} Build ({__version__}). Bugs may occur."
            text = i18n.get(key, version=__version__, default=default_text)

            bg_color = "RED" if "dev" in version_lower else "AMBER"
            text_color = "WHITE" if "dev" in version_lower else "BLACK"

            self.banner_container = ft.Container(
                content=ft.Text(text, color=text_color, weight="bold", text_align="center"),
                bgcolor=bg_color,
                padding=5,
                alignment=ft.Alignment(0, 0),  # Center alignment
                width=None  # Full width via expand
            )

    def build_ui(self):
        # Clear loading screen immediately before building new UI
        self.page.clean()

        destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label=i18n.get("nav_home")
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.EXTENSION, selected_icon=ft.Icons.EXTENSION, label=i18n.get("addon_manager_title") or "Addon Manager"
                ),
                # Settings Sub-Pages (Indices 17, 18, 19)
                ft.NavigationRailDestination(
                    icon=ft.Icons.UPDATE, label=i18n.get("settings_hdr_update") or "Updates"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.CLOUD_UPLOAD, label=i18n.get("deployment_title") or "Global Graph API"
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.HELP, label=i18n.get("help_title") or "Help & Resources"
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
                    icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label="General Settings"
                ),  # 9 Settings
                ft.NavigationRailDestination(
                    icon=ft.Icons.AUTO_FIX_HIGH, selected_icon=ft.Icons.AUTO_FIX_HIGH, label="Wizard"
                ),  # 10 Wizard
                ft.NavigationRailDestination(
                    icon=ft.Icons.RULE, selected_icon=ft.Icons.RULE, label="Tester"
                ),  # 11 Tester
                ft.NavigationRailDestination(
                    icon=ft.Icons.LAYERS, selected_icon=ft.Icons.LAYERS, label="Stacks"
                ),  # 12 Stacks
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD, selected_icon=ft.Icons.DASHBOARD, label="Dashboard"
                ),  # 13 Dashboard
                ft.NavigationRailDestination(
                    icon=ft.Icons.LIBRARY_BOOKS_OUTLINED, selected_icon=ft.Icons.LIBRARY_BOOKS, label="Library"
                ),  # 14 Library
                ft.NavigationRailDestination(
                     icon=ft.Icons.PEOPLE_OUTLINED, selected_icon=ft.Icons.PEOPLE, label="Groups"
                ),  # 15 Groups
            ]

        # Re-define version for NavigationRail trailing
        version_text = ft.Container(
            content=ft.Text(f"v{__version__}", size=10, color="GREY_500", text_align="center"),
            padding=ft.padding.only(bottom=10),
            alignment=ft.Alignment(0, 0)
        )

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

        # HoverSidebar Integration
        start_idx = self._pending_nav_index if self._pending_nav_index is not None else 0

        self.sidebar = HoverSidebar(
            app=self,
            destinations=destinations,
            on_navigate=self.goto_tab
        )



        self.content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)

        # Wrap content with global progress bar
        self.main_layout_wrapper = ft.Column(
            controls=[
                self.global_progress,
                self.content
            ],
            expand=True,
            spacing=0
        )
        self.sidebar.set_content(self.main_layout_wrapper)
        self.sidebar.set_selected_index(start_idx)

        if start_idx == 0:
            # Load Home by default
            from switchcraft.gui_modern.views.home_view import ModernHomeView
            self.content.controls.append(ModernHomeView(self.page, on_navigate=self.goto_tab))
        else:
             # Load pending tab
             self.goto_tab(start_idx)

        # Add Banner if needed
        self.setup_banner()



        # self.back_btn is now defined in __init__


        layout_controls = []
        if self.banner_container:
             layout_controls.append(self.banner_container)

        layout_controls.append(self.sidebar)

        self.page.add(
             ft.Column(layout_controls, expand=True, spacing=0)
        )

    def _open_notifications(self, e):
        """Opens or closes the notifications drawer."""
        # Simple toggle: if we have it and Flet thinks it's open, close it.
        # We also use a latch to handle cases where 'open' state is out of sync.
        if hasattr(self, "_active_drawer") and self._active_drawer:
            try:
                if self._active_drawer.open:
                    self.page.close(self._active_drawer)
                    return
            except Exception:
                pass

        # If we got here, we want to open a new one (or re-open)

        # Build Drawer Content
        notifs = self.notification_service.get_notifications()
        items = []
        if not notifs:
            items.append(ft.Text("No notifications", italic=True))
        else:
            for n in notifs:
                icon = ft.Icons.INFO
                color = "BLUE"
                if n["type"] == "success":
                    icon = ft.Icons.CHECK_CIRCLE
                    color = "GREEN"
                elif n["type"] == "warning":
                    icon = ft.Icons.WARNING
                    color = "ORANGE"
                elif n.get("type") == "error":
                    icon = ft.Icons.ERROR
                    color = "RED"

                items.append(
                    ft.ListTile(
                        leading=ft.Icon(icon, color=color),
                        title=ft.Text(n["title"], weight=ft.FontWeight.BOLD if not n.get("read") else ft.FontWeight.NORMAL),
                        subtitle=ft.Text(n["message"]),
                        trailing=ft.Text(n["timestamp"].strftime("%H:%M") if "timestamp" in n else "", size=10),
                        on_click=lambda _, nid=n["id"]: self._mark_read(nid)
                    )
                )

        drawer = ft.NavigationDrawer(
            controls=[
                ft.Container(height=12),
                ft.Row([
                    ft.Text("Notifications", size=20, weight=ft.FontWeight.BOLD),
                    ft.TextButton("Clear All", on_click=lambda _: self._clear_all_notifications(drawer))
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, run_spacing=10),
                ft.Divider(),
                ft.Column(items, scroll=ft.ScrollMode.AUTO, expand=True)
            ],
        )

        # In modern Flet, the drawer can be opened via page.open()
        self._active_drawer = drawer
        self.page.open(drawer)
        self.notification_service.mark_all_read()


    def _load_home(self):
        # This generic load home is replaced by ModernHomeView usage
        from switchcraft.gui_modern.views.home_view import ModernHomeView
        self.content.controls.clear()
        self.content.controls.append(ModernHomeView(self.page, on_navigate=self.goto_tab))

    def goto_tab(self, index):
        """Programmatically switch tabs."""
        self.sidebar.set_selected_index(index)
        self._switch_to_tab(index)
        # Track history for back button
        if hasattr(self, '_navigation_history'):
            if not self._navigation_history or self._navigation_history[-1] != index:
                self._navigation_history.append(index)

    def nav_change(self, e):
        idx = int(e.control.selected_index)
        logger.info(f"Navigation changed to index: {idx}")
        self._switch_to_tab(idx)
        # Track history for back button
        if hasattr(self, '_navigation_history'):
            if not self._navigation_history or self._navigation_history[-1] != idx:
                self._navigation_history.append(idx)

    def handle_window_drop(self, e):
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

        # 2. LOAD ACTUAL CONTENT
        new_controls = []

        if idx >= 100:
            # Handle Category View
            cat_index = idx - 100
        if idx == 100:
            # Special Category View
             # Find which category
             cat_index = 0 # Default
             if hasattr(self.sidebar, 'selected_category_index'):
                 cat_index = self.sidebar.selected_category_index

             if 0 <= cat_index < len(self.sidebar.categories):
                cat_data = self.sidebar.categories[cat_index]
                try:
                    from switchcraft.gui_modern.views.category_view import CategoryView
                    # Pass the destinations so the view can render cards
                    cat_view = CategoryView(self.page, items=cat_data[2], app_destinations=self.destinations, on_navigate=self.goto_tab)
                    new_controls.append(cat_view)
                except Exception as ex:
                    import traceback
                    from switchcraft.gui_modern.views.crash_view import CrashDumpView
                    new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
             else:
                new_controls.append(ft.Text("Unknown Category", color="red"))

        elif idx == 0:
             try:
                from switchcraft.gui_modern.views.home_view import ModernHomeView
                new_controls.append(ModernHomeView(self.page, on_navigate=self.goto_tab))
             except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 1:
            # Apps (Winget)
            try:
                if 'winget' not in self._view_cache:
                    from switchcraft.gui_modern.views.winget_view import ModernWingetView
                    self._view_cache['winget'] = ModernWingetView(self.page)
                new_controls.append(self._view_cache['winget'])
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 2:
            # Analyze
            try:
                if 'analyzer' not in self._view_cache:
                    from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView
                    self._view_cache['analyzer'] = ModernAnalyzerView(self.page)
                new_controls.append(self._view_cache['analyzer'])
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 3:
            # Generate (Helper)
            try:
                if 'helper' not in self._view_cache:
                    from switchcraft.gui_modern.views.helper_view import ModernHelperView
                    self._view_cache['helper'] = ModernHelperView(self.page)
                new_controls.append(self._view_cache['helper'])
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 4:
            # Intune
            try:
                from switchcraft.gui_modern.views.intune_view import ModernIntuneView
                new_controls.append(ModernIntuneView(self.page))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 5:
            # Intune Store
            try:
                from switchcraft.gui_modern.views.intune_store_view import ModernIntuneStoreView
                new_controls.append(ModernIntuneStoreView(self.page))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 6:
            # Scripts
            try:
                new_controls.append(ScriptUploadView(self.page))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 7:
            # MacOS
            try:
                new_controls.append(MacOSWizardView(self.page))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 8:
            # History
            try:
                from switchcraft.gui_modern.views.history_view import ModernHistoryView
                new_controls.append(ModernHistoryView(self.page))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 9:
            # Settings (General)
            try:
                from switchcraft.gui_modern.views.settings_view import ModernSettingsView
                new_controls.append(ModernSettingsView(self.page, initial_tab_index=0))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 10:
            # Wizard
            try:
                from switchcraft.gui_modern.views.packaging_wizard_view import PackagingWizardView
                new_controls.append(PackagingWizardView(self.page))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 11:
            # Tester
            try:
                from switchcraft.gui_modern.views.detection_tester_view import DetectionTesterView
                new_controls.append(DetectionTesterView(self.page))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 12:
            # Stacks
            try:
                from switchcraft.gui_modern.views.stack_manager_view import StackManagerView
                new_controls.append(StackManagerView(self.page))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 13:
            # Dashboard
            try:
                from switchcraft.gui_modern.views.dashboard_view import DashboardView
                new_controls.append(DashboardView(self.page))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 14:
            # Library
            try:
                from switchcraft.gui_modern.views.library_view import LibraryView
                new_controls.append(LibraryView(self.page))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 15:
            # Groups
            try:
                from switchcraft.gui_modern.views.group_manager_view import GroupManagerView
                new_controls.append(GroupManagerView(self.page))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
        elif idx == 16:
            # Addon Manager
            try:
                from switchcraft.gui_modern.views.addon_manager_view import AddonManagerView
                new_controls.append(AddonManagerView(self.page))
            except Exception as ex:
                import traceback
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))

        # New Settings Sub-Pages
        elif idx == 17: # Updates
             try:
                from switchcraft.gui_modern.views.settings_view import ModernSettingsView
                new_controls.append(ModernSettingsView(self.page, initial_tab_index=1))
             except Exception as ex:
                new_controls.append(ft.Text(f"Error: {ex}", color="red"))
        elif idx == 18: # Graph
             try:
                from switchcraft.gui_modern.views.settings_view import ModernSettingsView
                new_controls.append(ModernSettingsView(self.page, initial_tab_index=2))
             except Exception as ex:
                new_controls.append(ft.Text(f"Error: {ex}", color="red"))
        elif idx == 19: # Help
             try:
                from switchcraft.gui_modern.views.settings_view import ModernSettingsView
                new_controls.append(ModernSettingsView(self.page, initial_tab_index=3))
             except Exception as ex:
                new_controls.append(ft.Text(f"Error: {ex}", color="red"))

        else:
            # Dynamic Addons (start at idx 20)
            dynamic_idx = idx - 20
            if 0 <= dynamic_idx < len(self.dynamic_addons):
                addon = self.dynamic_addons[dynamic_idx]
                try:
                    view_class = self.addon_service.load_addon_view(addon['id'])
                    new_controls.append(view_class(self.page))
                except Exception as ex:
                    import traceback
                    from switchcraft.gui_modern.views.crash_view import CrashDumpView
                    new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))
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
        """Update notification icon based on unread count."""
        if not hasattr(self, 'notif_btn') or not self.notif_btn:
             return

        try:
             count = self.notification_service.get_unread_count()
             if count > 0:
                 self.notif_btn.icon = ft.Icons.NOTIFICATIONS_ACTIVE
                 self.notif_btn.icon_color = "RED"
                 self.notif_btn.tooltip = f"{count} New Notifications"
             else:
                 self.notif_btn.icon = ft.Icons.NOTIFICATIONS
                 self.notif_btn.icon_color = None
                 self.notif_btn.tooltip = "Notifications"
             self.notif_btn.update()
        except Exception as e:
             logger.error(f"Error updating notification icon: {e}")


    def _mark_read(self, nid):

        self.notification_service.mark_read(nid)
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
        time.sleep(2)
        self.page.window.destroy()

    def _clear_all_notifications(self, drawer):
        self.notification_service.clear_all()
        # Close Drawer
        if hasattr(self.page, "close"):
            self.page.close(drawer)
        else:
            drawer.open = False
            self.page.update()
        # Re-open empty? No, just close.

def main(page: ft.Page):
    """Entry point for Flet app."""
    # Add restart method to page for injection if needed, or pass app instance.
    app = ModernApp(page)
    page._show_restart_countdown = app._show_restart_countdown

if __name__ == "__main__":
    ft.run(main)
