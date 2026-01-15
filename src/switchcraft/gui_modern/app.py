from pathlib import Path
import os
import flet as ft
from switchcraft import __version__
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n

from switchcraft.gui_modern.views.script_upload_view import ScriptUploadView
from switchcraft.gui_modern.views.macos_wizard_view import MacOSWizardView
from switchcraft.services.notification_service import NotificationService
from switchcraft.services.addon_service import AddonService
from switchcraft.gui_modern.controls.sidebar import HoverSidebar
from switchcraft.gui_modern.nav_constants import NavIndex
import logging
import time

try:
    from winotify import Notification, audio
    WINOTIFY_AVAILABLE = True
except ImportError:
    WINOTIFY_AVAILABLE = False

logger = logging.getLogger(__name__)

class ModernApp:
    def __init__(self, page: ft.Page, splash_proc=None):
        self.page = page
        self.page.switchcraft_app = self  # Store reference for views to access goto_tab
        self.page.clean()

        # Initialize Services EARLY
        self.notification_service = NotificationService()
        self._last_notif_id = None
        self.addon_service = AddonService()
        self.dynamic_addons = []

        # Initialize history
        self._navigation_history = [0]

        self.setup_page()

        # Build Actions (Theme Toggle + Notifications)
        self.theme_icon = ft.IconButton(
            ft.Icons.DARK_MODE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.Icons.LIGHT_MODE,
            on_click=self.toggle_theme,
            tooltip=i18n.get("toggle_theme")
        )

        # Notification button
        self.notif_btn = ft.IconButton(
            icon=ft.Icons.NOTIFICATIONS,
            tooltip="Notifications",
            on_click=self._toggle_notification_drawer
        )

        # Now add listener
        self.notification_service.add_listener(self._on_notification_update)
        # Sync initial state (badge, etc)
        self._on_notification_update()

        # Back button (Early init for AppBar)
        self.back_btn = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip=i18n.get("btn_back") or "Back",
            on_click=self._go_back_handler,
            icon_size=24,
            visible=False  # Hidden initially when no history
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



        self.build_ui()




    def _toggle_notification_drawer(self, e):
        """Toggles the notification drawer."""
        # Force fresh drawer build if not open
        if self.page.end_drawer and self.page.end_drawer.open:
             self.page.end_drawer.open = False
             self.page.update()
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

                # Check type safely
                ntype = n.get("type", "info")
                if ntype == "success":
                    icon = ft.Icons.CHECK_CIRCLE
                    color = "GREEN"
                elif ntype == "warning":
                    icon = ft.Icons.WARNING
                    color = "ORANGE"
                elif ntype == "error":
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
            on_dismiss=self._on_drawer_dismiss
        )

        self.page.end_drawer = drawer
        self.page.end_drawer.open = True
        self.page.update() # Ensure UI reflects new drawer
        self.notification_service.mark_all_read()

    def _on_drawer_dismiss(self, e):
        """Cleanup when drawer is dismissed."""
        # self._active_drawer = None # legacy
        pass

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
                            icon="assets/switchcraft_logo.ico",
                            arguments="--wizard",
                            description="Open Packaging Wizard"
                        ),
                        ft.JumpListItem(
                            text="All-in-One Analyzer",
                            icon="assets/switchcraft_logo.ico",
                            arguments="--analyzer",
                            description="Open Installer Analyzer"
                        ),
                    ]
            except Exception as e:
                logger.debug(f"JumpList not supported: {e}")

            # Set window icon paths
            import sys

            # Asset Path Resolution for Flet
            # In Dev: src/switchcraft/assets/
            # In Prod (Frozen): sys._MEIPASS / assets/
            if getattr(sys, 'frozen', False):
                base_assets = os.path.join(sys._MEIPASS, "assets")
            else:
                # src/switchcraft/gui_modern/app.py -> src/switchcraft/assets/
                base_assets = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

            ico_path = os.path.join(base_assets, "switchcraft_logo.ico")
            png_path = os.path.join(base_assets, "switchcraft_logo.png")

            self._ico_path = ico_path if os.path.exists(ico_path) else None
            self._png_path = png_path if os.path.exists(png_path) else self._ico_path

            if self._ico_path:
                self.page.window.icon = self._ico_path

            if hasattr(self.page, 'appbar') and self.page.appbar:
                # Use absolute path for logo in appbar to be safe, or /path if assets_dir works
                # Let's try the absolute path as fallback if simple / failed
                header_logo = ft.Image(src="/switchcraft_logo.png", width=30, height=30)
                self.page.appbar.leading = header_logo
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
            self._pending_nav_index = NavIndex.PACKAGING_WIZARD
        elif "--analyzer" in sys.argv or "--all-in-one" in sys.argv:
             self._pending_nav_index = NavIndex.ANALYZER
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
                        self.goto_tab(NavIndex.SETTINGS_UPDATES)
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

                    # Add persistent notification with system toast
                    self.notification_service.add_notification(
                        title=i18n.get("update_available") or "Update Available",
                        message=f"Version {version_str} is available. Click to view details.",
                        type="update",
                        notify_system=True,
                        data={"url": update_data.get("html_url")}
                    )
            except Exception as e:
                logger.error(f"Startup update check failed: {e}")
                self.page.update_check_result = {"checked": True, "error": str(e)}

        threading.Thread(target=_run, daemon=True).start()

        # Check for First Run conditions
        # 1. Local Bundle (Dev/Test)
        if self._check_local_bundle():
             logger.info("Local bundle detected and installed.")
             # Continue to wizard just in case 'advanced' is still missing

        # 2. First Run Wizard (Production)
        # We delay this slightly to ensure UI is ready
        self._first_run_setup()

    def _check_local_bundle(self):
        """
        Checks for bundled addons (assets/addons/*.zip).
        If found, installs them and returns True.
        Used for Local Dev/Test builds.
        """
        try:
            import sys
            from pathlib import Path
            if getattr(sys, 'frozen', False):
                base_path = Path(sys._MEIPASS) / "assets" / "addons"
            else:
                base_path = Path(__file__).parent.parent / "assets" / "addons"

            if not base_path.exists():
                return False

            found_any = False
            # Install any zip found
            for zip_file in base_path.glob("*.zip"):
                 # Check if already installed to avoid re-install work?
                 # Or force update for dev? Let's check installed.
                 # Actually, we don't know the ID easily without opening zip.
                 # Let's just try install. AddonService handles overwrite.
                 try:
                     logger.info(f"Installing local bundle: {zip_file.name}")
                     self.addon_service.install_addon(str(zip_file))
                     found_any = True
                 except Exception as e:
                     logger.error(f"Failed to bundle install {zip_file}: {e}")

            return found_any

        except Exception as e:
            logger.error(f"Error checking local bundle: {e}")
            return False

    def _first_run_setup(self):
        """
        On first run (if 'advanced' addon is missing), guide the user through setup.
        1. Auto-download 'advanced' (Essential).
        2. Prompt for optional addons.
        """
        if self.addon_service.is_addon_installed("advanced"):
            # Already setup or not first run
            return


        # Since we need UI interaction, we trigger this via a delayed call or just show a modal if needed.
        # Let's create a visual wizard style dialog.

        def close_wizard(e):
             self.page.close(dlg)

        def install_optional(e):
             # Trigger background download of optionals
             self.page.close(dlg)
             self.set_progress(None, True) # Indeterminate
             self.page.snack_bar = ft.SnackBar(ft.Text("Installing optional components..."))
             self.page.snack_bar.open = True
             self.page.update()

             import threading
             def _bg():
                 opts = ["ai", "winget"]
                 for opt in opts:
                     success, msg = self.addon_service.install_from_github(opt)
                     if success:
                         logger.info(f"Optional addon {opt} installed: {msg}")
                     else:
                         logger.warning(f"Optional addon {opt} failed: {msg}")

                 self.set_progress(0, False)
                 self._show_snack("Optional components installed!", "GREEN")
                 # We might need to reload UI/Sidebar
                 # self.build_ui() # Full reload might be jarring, maybe just refresh sidebar
                 # For now, require restart or just let dynamic addons load next time (or dynamic load?)
                 # Dynamic load is supported by app restart usually.

             threading.Thread(target=_bg, daemon=True).start()

        def start_setup(e):
            # Disable button, show progress
            e.control.disabled = True
            e.control.text = "Installing Base..."
            e.control.update()

            import threading
            def _base_install():
                # Install Advanced
                success, msg = self.addon_service.install_from_github("advanced")

                # UI Update needs to happen on loop? Flet is thread-safe for simple updates usually
                def update_ui():
                    if not dlg.open or (hasattr(self.page, "dialog") and dlg != self.page.dialog):
                        # Dialog might be closed or not active
                        return

                    try:
                        if success:
                            # Update Dialog to ask for Optional
                            content.controls.clear()
                            content.controls.append(ft.Icon(ft.Icons.CHECK_CIRCLE, color="GREEN", size=48))
                            content.controls.append(ft.Text("Base components installed!"))
                            content.controls.append(ft.Text("Do you want to install optional features (AI, Winget)?"))

                            dlg.actions.clear()
                            dlg.actions.append(ft.TextButton("No, thanks", on_click=close_wizard))
                            dlg.actions.append(ft.Button("Install Optional", on_click=install_optional))
                        else:
                            content.controls.append(ft.Text(f"Failed to install base: {msg}", color="RED"))
                            dlg.actions.clear()
                            dlg.actions.append(ft.TextButton("Close", on_click=close_wizard))

                        dlg.update()
                    except Exception as ex:
                        import logging
                        logging.getLogger(__name__).warning(f"Failed to update wizard UI: {ex}")

                if self.page:
                    self.page.run_task(update_ui)

            threading.Thread(target=_base_install, daemon=True).start()

        content = ft.Column([
            ft.Text("Welcome to SwitchCraft!", size=20, weight="bold"),
            ft.Text("It looks like this is your first run."),
            ft.Text("We classify 'Advanced Features' as an Essential add-on. Install it now?"),
        ], tight=True)

        dlg = ft.AlertDialog(
            title=ft.Text("Setup Wizard"),
            content=content,
            actions=[
                ft.TextButton("Skip", on_click=close_wizard),
                ft.Button("Install Essential", on_click=start_setup)
            ],
            modal=True,
        )
        self.page.open(dlg)

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

        self.destinations = [
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
                    icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label=i18n.get("settings_general") or "General Settings"
                ),  # 13 Settings
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
                ft.NavigationRailDestination(
                    icon=ft.Icons.TERMINAL, selected_icon=ft.Icons.TERMINAL, label="Winget Creator"
                ),  # 20 Winget Create
            ]


        # Capture the end of static destinations to calculate offset later
        self.first_dynamic_index = len(self.destinations)

        # Load Dynamic Addons
        try:
            self.dynamic_addons = self.addon_service.list_addons()
            for addon in self.dynamic_addons:
                icon_name = addon.get("icon", "EXTENSION") # Default icon
                # Resolve icon if possible, else default
                icon_code = getattr(ft.Icons, icon_name, ft.Icons.EXTENSION)

                self.destinations.append(
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
            destinations=self.destinations,
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
                self._update_back_btn_visibility()

    def _go_back_handler(self, e):
        """Handle back button click to navigate to previous view."""
        if hasattr(self, '_navigation_history') and len(self._navigation_history) > 1:
            # Pop current view
            self._navigation_history.pop()
            # Go to previous view
            prev_idx = self._navigation_history[-1]
            self.sidebar.set_selected_index(prev_idx)
            self._switch_to_tab(prev_idx)
            self._update_back_btn_visibility()

    def _update_back_btn_visibility(self):
        """Show/hide back button based on navigation history."""
        if hasattr(self, 'back_btn') and self.back_btn:
            # Show back button only if there's history to go back to
            should_show = len(self._navigation_history) > 1
            if self.back_btn.visible != should_show:
                self.back_btn.visible = should_show
                try:
                    self.back_btn.update()
                except RuntimeError:
                    pass  # Control not attached to page

    def nav_change(self, e):
        idx = int(e.control.selected_index)
        logger.info(f"Navigation changed to index: {idx}")
        self._switch_to_tab(idx)
        # Track history for back button
        if hasattr(self, '_navigation_history'):
            if not self._navigation_history or self._navigation_history[-1] != idx:
                self._navigation_history.append(idx)
                self._update_back_btn_visibility()

    def handle_window_drop(self, e):
        """Global drop handler - switches to analyzer if file is dropped anywhere."""
        if e.files:
            file_path = e.files[0].path
            if file_path.lower().endswith((".exe", ".msi")):
                logger.info(f"Global drop detected: {file_path}")
                # 1. Switch Tab to Analyzer
                self.goto_tab(NavIndex.ANALYZER)

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

        # Helper to safely load views
        def load_view(factory_func):
            try:
                new_controls.append(factory_func())
            except Exception as ex:
                import traceback
                print(f"DEBUG: Exception loading view: {ex}") # Keep print for immediate debug console visibility
                logger.error(f"Exception loading view: {ex}", exc_info=True)
                from switchcraft.gui_modern.views.crash_view import CrashDumpView
                new_controls.append(CrashDumpView(self.page, error=ex, traceback_str=traceback.format_exc()))

        if idx >= 100:
            # Handle Category View
            cat_index = 0 # Default
            if hasattr(self.sidebar, 'selected_category_index'):
                 cat_index = self.sidebar.selected_category_index

            if 0 <= cat_index < len(self.sidebar.categories):
                cat_data = self.sidebar.categories[cat_index]
                try:
                    from switchcraft.gui_modern.views.category_view import CategoryView
                    # Pass the destinations so the view can render cards
                    # cat_data is tuple: (Icon, Label, ItemsList)
                    cat_name = cat_data[1]
                    cat_view = CategoryView(self.page, category_name=cat_name, items=cat_data[2], app_destinations=self.destinations, on_navigate=self.goto_tab)
                    new_controls.append(cat_view)
                except Exception:
                    new_controls.append(ft.Text("Unknown Category", color="red"))
            else:
                new_controls.append(ft.Text("Unknown Category", color="red"))

        elif idx == NavIndex.HOME:
             # Home
             def _f():
                from switchcraft.gui_modern.views.home_view import ModernHomeView
                return ModernHomeView(self.page, on_navigate=self.goto_tab)
             load_view(_f)
        elif idx == NavIndex.ADDON_MANAGER:
             # Addon Manager
             def _f():
                 from switchcraft.gui_modern.views.addon_manager_view import AddonManagerView
                 return AddonManagerView(self.page)
             load_view(_f)
        elif idx == NavIndex.SETTINGS_UPDATES:
             # Updates (Settings sub)
             def _f():
                from switchcraft.gui_modern.views.settings_view import ModernSettingsView
                return ModernSettingsView(self.page, initial_tab_index=1)
             load_view(_f)
        elif idx == NavIndex.SETTINGS_GRAPH:
             # Deployment/Graph (Settings sub)
             def _f():
                from switchcraft.gui_modern.views.settings_view import ModernSettingsView
                return ModernSettingsView(self.page, initial_tab_index=2)
             load_view(_f)
        elif idx == NavIndex.SETTINGS_HELP:
             # Help (Settings sub)
             def _f():
                from switchcraft.gui_modern.views.settings_view import ModernSettingsView
                return ModernSettingsView(self.page, initial_tab_index=3)
             load_view(_f)
        elif idx == NavIndex.WINGET:
            # Apps (Winget)
            def _f():
                if 'winget' not in self._view_cache:
                    from switchcraft.gui_modern.views.winget_view import ModernWingetView
                    self._view_cache['winget'] = ModernWingetView(self.page)
                return self._view_cache['winget']
            load_view(_f)
        elif idx == NavIndex.ANALYZER:
            # Analyzer
            def _f():
                if 'analyzer' not in self._view_cache:
                    from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView
                    self._view_cache['analyzer'] = ModernAnalyzerView(self.page)
                return self._view_cache['analyzer']
            load_view(_f)
        elif idx == NavIndex.HELPER:
            # Generate (Helper)
            def _f():
                if 'helper' not in self._view_cache:
                    from switchcraft.gui_modern.views.helper_view import ModernHelperView
                    self._view_cache['helper'] = ModernHelperView(self.page)
                return self._view_cache['helper']
            load_view(_f)
        elif idx == NavIndex.INTUNE:
            # Intune
            def _f():
                from switchcraft.gui_modern.views.intune_view import ModernIntuneView
                return ModernIntuneView(self.page)
            load_view(_f)
        elif idx == NavIndex.INTUNE_STORE:
            # Intune Store
            def _f():
                from switchcraft.gui_modern.views.intune_store_view import ModernIntuneStoreView
                return ModernIntuneStoreView(self.page)
            load_view(_f)
        elif idx == NavIndex.SCRIPTS:
            # Scripts
            load_view(lambda: ScriptUploadView(self.page))
        elif idx == NavIndex.MACOS:
            # MacOS
            load_view(lambda: MacOSWizardView(self.page))
        elif idx == NavIndex.HISTORY:
            # History
            def _f():
                from switchcraft.gui_modern.views.history_view import ModernHistoryView
                return ModernHistoryView(self.page)
            load_view(_f)
        elif idx == NavIndex.SETTINGS:
            # Settings (General)
            def _f():
                from switchcraft.gui_modern.views.settings_view import ModernSettingsView
                # Tab 0 is General
                return ModernSettingsView(self.page, initial_tab_index=0)
            load_view(_f)
        elif idx == NavIndex.PACKAGING_WIZARD:
            # Wizard
            def _f():
                from switchcraft.gui_modern.views.packaging_wizard_view import PackagingWizardView
                return PackagingWizardView(self.page)
            load_view(_f)
        elif idx == NavIndex.DETECTION_TESTER:
            # Tester
            def _f():
                from switchcraft.gui_modern.views.detection_tester_view import DetectionTesterView
                return DetectionTesterView(self.page)
            load_view(_f)
        elif idx == NavIndex.STACK_MANAGER:
            # Stacks
            def _f():
                from switchcraft.gui_modern.views.stack_manager_view import StackManagerView
                return StackManagerView(self.page)
            load_view(_f)
        elif idx == NavIndex.DASHBOARD:
            # Dashboard
            def _f():
                from switchcraft.gui_modern.views.dashboard_view import DashboardView
                return DashboardView(self.page)
            load_view(_f)
        elif idx == NavIndex.LIBRARY:
            # Library
            def _f():
                from switchcraft.gui_modern.views.library_view import LibraryView
                return LibraryView(self.page)
            load_view(_f)
        elif idx == NavIndex.GROUP_MANAGER:
            # Groups
            def _f():
                from switchcraft.gui_modern.views.group_manager_view import GroupManagerView
                return GroupManagerView(self.page)
            load_view(_f)

        elif idx == NavIndex.WINGET_CREATE:
            # WingetCreate Manager
            def _f():
                from switchcraft.gui_modern.views.wingetcreate_view import WingetCreateView
                return WingetCreateView(self.page)
            load_view(_f)

        else:
            # Dynamic Addons
            # Robust calculation relying on captured start index
            if hasattr(self, 'first_dynamic_index'):
                dynamic_idx = idx - self.first_dynamic_index
            else:
                # Fallback if somehow not set (should not happen if build_ui called)
                # This fallback assumes WINGET_CREATE is last static
                dynamic_idx = idx - (NavIndex.WINGET_CREATE + 1)

            if 0 <= dynamic_idx < len(self.dynamic_addons):
                addon = self.dynamic_addons[dynamic_idx]
                def _f():
                    view_class = self.addon_service.load_addon_view(addon['id'])
                    return view_class(self.page)
                load_view(_f)
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
        try:
            fade_container.update()
        except RuntimeError as re:
             logger.debug(f"Fade container update failed: {re}")

    def _on_notification_update(self):
        """Update notification icon based on unread count and trigger Windows toast."""
        if not hasattr(self, 'notif_btn') or not self.notif_btn:
             return

        try:
             # 1. Update Badge
             notifs = self.notification_service.get_notifications()
             count = self.notification_service.get_unread_count()

             if count > 0:
                 self.notif_btn.icon = ft.Icons.NOTIFICATIONS_ACTIVE
                 self.notif_btn.icon_color = "RED"
                 self.notif_btn.tooltip = f"{count} New Notifications"
             else:
                 self.notif_btn.icon = ft.Icons.NOTIFICATIONS
                 self.notif_btn.icon_color = None
                 self.notif_btn.tooltip = "Notifications"
             try:
                 self.notif_btn.update()
             except RuntimeError as re:
                 logger.debug(f"Notification update failed (control likely detached): {re}")

             # 2. Windows Toast Logic
             if notifs and WINOTIFY_AVAILABLE:
                 latest = notifs[0]
                 latest_id = latest["id"]

                 # Only notify if it's new (not same as last processed) AND unread
                 # Check notify_system flag (default False if missing)
                 should_notify_system = latest.get("notify_system", False)

                 if should_notify_system and not latest["read"] and self._last_notif_id != latest_id:
                     self._last_notif_id = latest_id

                     # Map type to winotify sound/icon?
                     # Winotify doesn't support custom icons easily without path, use default app icon

                     toast = Notification(
                         app_id="SwitchCraft",
                         title=latest["title"],
                         msg=latest["message"],
                         duration="short",
                         icon=self._ico_path if hasattr(self, '_ico_path') and self._ico_path else ""
                     )

                     # Add action buttons
                     notif_type = latest.get("type")
                     n_data = latest.get("data", {})

                     if notif_type == "update":
                         # Button 1: Open Changelog
                         changelog_url = n_data.get("url") or "https://github.com/FaserF/SwitchCraft/releases"
                         toast.add_actions(label=i18n.get("notif_open_changelog") or "Open Changelog", launch=changelog_url)

                         # Button 2: Open App
                         toast.add_actions(label=i18n.get("notif_open_app") or "Open App", launch="switchcraft://notifications")
                     else:
                         # Regular notifications (error/info/warning)
                         # Button 1: Open Logs Folder (if exists)
                         logs_path = Path(os.getenv('APPDATA', '')) / "FaserF" / "SwitchCraft" / "Logs"
                         if logs_path.exists():
                             toast.add_actions(label=i18n.get("notif_open_logs") or "Open Logs", launch=f"file://{logs_path}")

                         if notif_type == "error":
                             toast.add_actions(label=i18n.get("notif_open_app") or "Open App", launch="switchcraft://notifications")

                     if notif_type == "error":
                         toast.set_audio(audio.LoopingAlarm, loop=False)
                     else:
                         toast.set_audio(audio.Default, loop=False)

                     toast.show()

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
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    ft.run(main, assets_dir=assets_dir)
