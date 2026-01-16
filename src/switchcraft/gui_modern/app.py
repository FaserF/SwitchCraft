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
        """
        Initialize the ModernApp instance, attach it to the provided page, prepare services and UI, and preserve the startup splash until the UI is ready.

        This constructor:
        - Attaches the app instance to the page for inter-view access and ensures a per-page session store exists.
        - Initializes core services (notifications, addon management), navigation history, a view cache, and UI controls (app bar, theme toggle, notification and back buttons, and a global progress bar).
        - Registers notification listeners and synchronizes initial notification state.
        - Builds the main UI and, if a splash process was provided, attempts to terminate it after the UI is constructed.

        Parameters:
            page: The Flet Page object that the application will attach to and manage.
            splash_proc: Optional process handle for an external splash screen; if provided, it will be terminated after the UI is built.
        """
        self.page = page
        self.splash_proc = splash_proc  # Store splash_proc as instance variable
        self.page.switchcraft_app = self  # Store reference for views to access goto_tab
        # Create a simple session storage dict for inter-view communication
        if not hasattr(page, 'switchcraft_session'):
            page.switchcraft_session = {}
        # Don't clean page here - we want to keep the loading screen from modern_main.py
        # The loading screen will be replaced in build_ui()

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

        # Hamburger menu button for mobile (will be shown/hidden based on screen size)
        self.menu_btn = ft.IconButton(
            icon=ft.Icons.MENU,
            tooltip=i18n.get("menu") or "Menu",
            on_click=self._toggle_navigation_drawer,
            icon_size=24,
            visible=False  # Will be shown on mobile devices
        )

        # Try to find logo for AppBar
        logo_icon = ft.Icon(ft.Icons.INSTALL_DESKTOP, size=30)

        self.page.appbar = ft.AppBar(
            leading=ft.Row([
                self.menu_btn,
                logo_icon
            ], spacing=0, tight=True),
            leading_width=80,
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

        # Loading screen is already shown in modern_main.py before ModernApp is created
        # No need to add another one here - it will be replaced in build_ui()

        # Keep splash visible during build_ui - don't terminate yet
        # View cache - keeps views in memory to preserve state between tab switches
        self._view_cache = {}

        self.build_ui()

        # Now that UI is built, shutdown splash screen
        if self.splash_proc:
            try:
                self.splash_proc.terminate()
            except Exception:
                pass




    def _toggle_notification_drawer(self, e):
        """
        Toggle the notifications drawer: close it if currently open, otherwise open it.

        Attempts several methods to close an open drawer (setting open to False, calling page.close, or removing the drawer) and falls back to opening the notifications drawer when closed or when an error occurs.

        Parameters:
            e: UI event or payload passed from the caller; forwarded to the drawer-opening handler.
        """
        try:
            logger.debug("_toggle_notification_drawer called")
            # Check if drawer is currently open
            is_open = False
            if hasattr(self.page, 'end_drawer') and self.page.end_drawer is not None:
                try:
                    is_open = getattr(self.page.end_drawer, 'open', False)
                    logger.debug(f"Drawer open state: {is_open}")
                except Exception as ex:
                    logger.debug(f"Could not get drawer open state: {ex}")
                    is_open = False

            if is_open:
                # Close drawer
                logger.debug("Closing notification drawer")
                try:
                    # Method 1: Set open to False first
                    if hasattr(self.page.end_drawer, 'open'):
                        self.page.end_drawer.open = False
                    # Method 2: Use page.close if available
                    if hasattr(self.page, 'close'):
                        try:
                            self.page.close(self.page.end_drawer)
                        except Exception:
                            pass
                    # Method 3: Remove drawer entirely
                    if hasattr(self.page, 'end_drawer'):
                        self.page.end_drawer = None
                    self.page.update()
                    logger.debug("Notification drawer closed successfully")
                except Exception as ex:
                    logger.error(f"Failed to close drawer: {ex}")
                    # Force close by removing drawer
                    self.page.end_drawer = None
                    self.page.update()
            else:
                # Open drawer
                logger.debug("Opening notification drawer")
                self._open_notifications_drawer(e)
        except Exception as ex:
            logger.exception(f"Error toggling notification drawer: {ex}")
            # Try to open anyway
            try:
                self._open_notifications_drawer(e)
            except Exception as ex2:
                logger.error(f"Failed to open drawer after error: {ex2}")
                # Show error to user
                try:
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Failed to open notifications: {ex2}"),
                        bgcolor="RED"
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                except Exception:
                    pass

    def _open_notifications_drawer(self, e):
        """
        Open a navigation drawer containing current notifications.

        Builds a notifications drawer from the notification service, opens it on the page, and marks all notifications as read. If there are no notifications, displays a localized "No notifications" message. On failure, attempts to surface an error via a snackbar.
        """
        try:
            notifs = self.notification_service.get_notifications()
            items = []
            if not notifs:
                items.append(ft.Text(i18n.get("no_notifications") or "No notifications", italic=True, size=14))
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
                            subtitle=ft.Text(n.get("message", ""), size=12),
                            trailing=ft.Text(n["timestamp"].strftime("%H:%M") if "timestamp" in n and n.get("timestamp") else "", size=10, color="GREY_400"),
                            on_click=lambda _, nid=n["id"]: self._mark_notification_read(nid)
                        )
                    )

            # Add Clear All button if there are notifications
            header_controls = [
                ft.Text(i18n.get("notifications") or "Notifications", size=20, weight=ft.FontWeight.BOLD, expand=True)
            ]
            if notifs:
                header_controls.append(
                    ft.TextButton(
                        i18n.get("clear_all") or "Clear All",
                        on_click=lambda _: self._clear_all_notifications()
                    )
                )

            drawer = ft.NavigationDrawer(
                controls=[
                    ft.Container(height=12),
                    ft.Row(header_controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.Column(items, scroll=ft.ScrollMode.AUTO, expand=True)
                ],
                on_dismiss=self._on_drawer_dismiss
            )

            # Set drawer and open it
            self.page.end_drawer = drawer

            # Force update BEFORE setting open to ensure drawer is attached
            self.page.update()

            # Now set open and update again
            drawer.open = True
            self.page.update()

            # Try additional methods if drawer didn't open
            try:
                if hasattr(self.page, 'open'):
                    self.page.open(drawer)
                    self.page.update()
            except Exception as ex:
                logger.debug(f"page.open() not available or failed: {ex}, using direct assignment")

            # Final update to ensure drawer is visible
            self.page.update()

            # Mark all as read after opening
            self.notification_service.mark_all_read()
            logger.debug("Notification drawer opened successfully")
        except Exception as ex:
            logger.exception(f"Failed to open notification drawer: {ex}")
            # Show error via snackbar
            try:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Failed to open notifications: {ex}"), bgcolor="RED")
                self.page.snack_bar.open = True
                self.page.update()
            except Exception:
                pass

    def _on_drawer_dismiss(self, e):
        """
        Refresh the notification UI state when a navigation drawer is dismissed.

        Parameters:
            e: The drawer-dismiss event object received from the UI callback. This function suppresses and logs any exceptions raised while updating notification state.
        """
        try:
            # Update notification button state when drawer is dismissed
            self._on_notification_update()
        except Exception as ex:
            logger.debug(f"Error in drawer dismiss handler: {ex}")

    def _mark_notification_read(self, notification_id):
        """
        Mark the notification identified by `notification_id` as read and refresh the notifications drawer.

        Parameters:
            notification_id: Identifier of the notification to mark as read. The identifier type is determined by the notification service (commonly a string or integer).
        """
        try:
            self.notification_service.mark_read(notification_id)
            # Refresh drawer content
            self._open_notifications_drawer(None)
        except Exception as ex:
            logger.error(f"Failed to mark notification as read: {ex}")

    def _clear_all_notifications(self):
        """
        Clear all notifications and close any open notification drawer.

        On success, displays a "Notifications cleared" snackbar. Any exceptions raised while clearing notifications or closing the drawer are caught and logged; they are not propagated.
        """
        try:
            self.notification_service.clear_all()
            # Close drawer
            if hasattr(self.page, 'end_drawer') and self.page.end_drawer:
                if hasattr(self.page, 'close'):
                    self.page.close(self.page.end_drawer)
                else:
                    self.page.end_drawer.open = False
            self.page.update()
            # Show success message
            try:
                self.page.snack_bar = ft.SnackBar(ft.Text(i18n.get("notifications_cleared") or "Notifications cleared"), bgcolor="GREEN")
                self.page.snack_bar.open = True
                self.page.update()
            except Exception:
                pass
        except Exception as ex:
            logger.exception(f"Failed to clear notifications: {ex}")

    def _clear_notifications(self, e, dlg):
        """
        Clear all notifications, close the given dialog, and show a confirmation snackbar.

        Parameters:
            e: The event that triggered this action (unused by the method).
            dlg: The dialog control to close after clearing notifications.
        """
        self.notification_service.clear()
        self.page.close(dlg)
        self.page.snack_bar = ft.SnackBar(ft.Text(i18n.get("notifications_cleared") or "Notifications cleared"))
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
        Show a first-run setup wizard that installs the required "advanced" addon and optionally installs additional components.

        If the "advanced" addon is already installed, this method returns immediately. Otherwise it opens a modal dialog that prompts the user to install the essential "advanced" addon; if installation succeeds the dialog then offers to install optional components (for example, AI helpers and winget). Installations are performed in the background and progress is surfaced via the app's progress indicator and snackbars. The dialog may be skipped to leave the app unchanged. Dynamic loading of newly installed addons may require an application restart to be visible in all UI areas.
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
             """
             Start background installation of optional addons and update the UI with progress.

             Closes the provided dialog, displays an indeterminate global progress indicator and a snackbar, and launches a background thread that installs the "ai" and "winget" optional addons via the app's addon service. On completion the progress indicator is cleared and a success snackbar is shown; individual install failures are logged. This function does not perform a full UI reload and does not guarantee immediate availability of newly installed dynamic addons.
             """
             self.page.close(dlg)
             self.set_progress(None, True) # Indeterminate
             self.page.snack_bar = ft.SnackBar(ft.Text(i18n.get("installing_optional") or "Installing optional components..."))
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
            """
            Start the base setup flow: disable the triggering control, start installing the "advanced" addon in a background thread, and update the wizard dialog when installation completes.

            Parameters:
                e: The click/event object from the UI control that initiated the setup; its control will be disabled and its text updated while installation runs.

            Behavior:
                - Disables the invoking button and shows an in-progress label.
                - Runs addon_service.install_from_github("advanced") on a background thread.
                - When the install finishes, updates the open wizard dialog to either:
                    * show success and offer to install optional features (AI, Winget), or
                    * show the failure message and a Close action.
                - Safely skips UI updates if the dialog has been closed.
            """
            e.control.disabled = True
            e.control.text = "Installing Base..."
            e.control.update()

            import threading
            def _base_install():
                # Install Advanced
                """
                Install the "advanced" addon and update the setup wizard dialog to reflect success or failure.

                Attempts to install the "advanced" addon via the AddonService and schedules a UI update on the page thread to modify the provided dialog:
                - On success: replaces dialog content with a success icon and messages, and changes actions to offer installing optional features or skipping.
                - On failure: appends an error message to the dialog and replaces actions with a Close button.

                The function has side effects on the addon service and the active dialog; it does not return a value.
                """
                success, msg = self.addon_service.install_from_github("advanced")

                # UI Update needs to happen on loop? Flet is thread-safe for simple updates usually
                def update_ui():
                    """
                    Update the setup wizard dialog to reflect the result of the base addon installation.

                    If the dialog is closed or no longer the active page dialog, this function returns without changes. When the installation succeeded, the dialog content is replaced with a success icon, confirmation text, and actions offering to skip or install optional features; when the installation failed, an error message is appended and a Close action is shown. Any exceptions during UI updates are logged and do not propagate.
                    """
                    if not dlg.open or (hasattr(self.page, "dialog") and dlg != self.page.dialog):
                        # Dialog might be closed or not active
                        return

                    try:
                        if success:
                            # Update Dialog to ask for Optional
                            content.controls.clear()
                            content.controls.append(ft.Icon(ft.Icons.CHECK_CIRCLE, color="GREEN", size=48))
                            content.controls.append(ft.Text(i18n.get("base_components_installed") or "Base components installed!"))
                            content.controls.append(ft.Text(i18n.get("install_optional_features") or "Do you want to install optional features (AI, Winget)?"))

                            dlg.actions.clear()
                            dlg.actions.append(ft.TextButton("No, thanks", on_click=close_wizard))
                            dlg.actions.append(ft.Button("Install Optional", on_click=install_optional))
                        else:
                            content.controls.append(ft.Text(i18n.get("failed_install_base", msg=msg) or f"Failed to install base: {msg}", color="RED"))
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
            ft.Text(i18n.get("welcome_switchcraft") or "Welcome to SwitchCraft!", size=20, weight="bold"),
            ft.Text(i18n.get("first_run_detected") or "It looks like this is your first run."),
            ft.Text(i18n.get("advanced_features_essential") or "We classify 'Advanced Features' as an Essential add-on. Install it now?"),
        ], tight=True)

        dlg = ft.AlertDialog(
            title=ft.Text(i18n.get("setup_wizard") or "Setup Wizard"),
            content=content,
            actions=[
                ft.TextButton("Skip", on_click=close_wizard),
                ft.Button("Install Essential", on_click=start_setup)
            ],
            modal=True,
        )
        self.page.open(dlg)

    def toggle_theme(self, e):
        """
        Toggle the application's theme between Light and Dark.

        Updates the page's ThemeMode and the theme icon, persists the selected preference via SwitchCraftConfig.set_user_preference("Theme", ...), and calls page.update(). If an error occurs while toggling, the method attempts to display an error SnackBar.
        """
        try:
            logger.debug(f"Toggle theme called. Current mode: {self.page.theme_mode}")
            if self.page.theme_mode == ft.ThemeMode.DARK:
                self.page.theme_mode = ft.ThemeMode.LIGHT
                self.theme_icon.icon = ft.Icons.DARK_MODE
                SwitchCraftConfig.set_user_preference("Theme", "Light")
                logger.debug("Switched to LIGHT theme")
            else:
                self.page.theme_mode = ft.ThemeMode.DARK
                self.theme_icon.icon = ft.Icons.LIGHT_MODE
                SwitchCraftConfig.set_user_preference("Theme", "Dark")
                logger.debug("Switched to DARK theme")
            self.page.update()
        except Exception as ex:
            logger.exception(f"Error toggling theme: {ex}")
            try:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Failed to toggle theme: {ex}"),
                    bgcolor="RED"
                )
                self.page.snack_bar.open = True
                self.page.update()
            except Exception:
                pass





    def window_event(self, e):
        """
        Handle window-level events such as mouse back navigation and window close.

        Detects mouse "back" button presses (XButton1) and delegates to the app's back-navigation handler.
        On a "close" event, attempts to cleanly destroy the window using available Flet API variants; if window destruction fails, the process will be terminated.

        Parameters:
            e: The window event object. Its `.data` (or string form) is inspected to determine the event type.
        """
        # Handle mouse back button (XButton1 on Windows)
        # Flet may send this as different event types depending on version
        event_data = str(e.data) if hasattr(e, 'data') else str(e)
        if "xbutton1" in event_data.lower() or event_data == "5":  # XButton1 is typically event code 5
            logger.debug("Mouse back button pressed")
            self._go_back_handler(e)
            return

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
        """
        Show a prominent banner for development or beta builds.

        If the app version string contains "dev" or "beta", sets self.banner_container to a Flet Container displaying a localized banner message (falls back to a default message containing the version). The banner uses a red/white color scheme for development builds and an amber/black scheme for beta builds, and is centered with padding.
        """
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
        # Keep loading screen visible during build - clear only at the end
        # Don't clear page.clean() here - we'll replace the loading screen with the actual UI

        """
        Constructs and attaches the main application UI: navigation rail (including dynamic addon destinations), sidebar, content area, banner, and global progress wrapper.

        This method prepares static navigation destinations, appends dynamically discovered addon entries, initializes the HoverSidebar and the main content column, schedules first-run/demo checks, handles command-line-driven initial navigation (wizard/analyzer) and silent-mode behavior, and finally replaces the startup loading screen with the built UI. If a splash process was provided, it is terminated after the UI is visible.
        """
        self.destinations = [
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label=i18n.get("nav_home")
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
                ),  # 4 Winget
                ft.NavigationRailDestination(
                    icon=ft.Icons.ANALYTICS_OUTLINED, selected_icon=ft.Icons.ANALYTICS, label=i18n.get("nav_analyze")
                ),  # 5 Analyze
                ft.NavigationRailDestination(
                    icon=ft.Icons.SMART_TOY_OUTLINED, selected_icon=ft.Icons.SMART_TOY, label=i18n.get("nav_helper")
                ),  # 6 AI Helper
                ft.NavigationRailDestination(
                    icon=ft.Icons.CLOUD_UPLOAD_OUTLINED,
                    selected_icon=ft.Icons.CLOUD_UPLOAD, label=i18n.get("nav_intune")
                ),  # 7 Intune
                ft.NavigationRailDestination(
                    icon=ft.Icons.SHOP_TWO_OUTLINED, selected_icon=ft.Icons.SHOP_TWO, label=i18n.get("nav_intune_store")
                ),  # 8 Intune Store
                ft.NavigationRailDestination(
                    icon=ft.Icons.DESCRIPTION_OUTLINED, selected_icon=ft.Icons.DESCRIPTION, label=i18n.get("nav_scripts")
                ),  # 9 Scripts
                ft.NavigationRailDestination(
                    icon=ft.Icons.APPLE_OUTLINED, selected_icon=ft.Icons.APPLE, label=i18n.get("nav_macos")
                ),  # 10 MacOS
                ft.NavigationRailDestination(
                    icon=ft.Icons.HISTORY_OUTLINED, selected_icon=ft.Icons.HISTORY, label=i18n.get("nav_history")
                ),  # 11 History
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label=i18n.get("nav_settings")
                ),  # 12 Settings
                ft.NavigationRailDestination(
                    icon=ft.Icons.AUTO_FIX_HIGH, selected_icon=ft.Icons.AUTO_FIX_HIGH, label=i18n.get("nav_wizard")
                ),  # 13 Wizard
                ft.NavigationRailDestination(
                    icon=ft.Icons.RULE, selected_icon=ft.Icons.RULE, label=i18n.get("nav_tester")
                ),  # 14 Tester
                ft.NavigationRailDestination(
                    icon=ft.Icons.LAYERS, selected_icon=ft.Icons.LAYERS, label=i18n.get("nav_stacks")
                ),  # 15 Stacks
                ft.NavigationRailDestination(
                    icon=ft.Icons.DASHBOARD, selected_icon=ft.Icons.DASHBOARD, label=i18n.get("nav_dashboard")
                ),  # 16 Dashboard
                ft.NavigationRailDestination(
                    icon=ft.Icons.LIBRARY_BOOKS_OUTLINED, selected_icon=ft.Icons.LIBRARY_BOOKS, label=i18n.get("nav_library")
                ),  # 17 Library
                ft.NavigationRailDestination(
                    icon=ft.Icons.PEOPLE_OUTLINED, selected_icon=ft.Icons.PEOPLE, label=i18n.get("nav_groups")
                ),  # 18 Groups
                ft.NavigationRailDestination(
                    icon=ft.Icons.TERMINAL, selected_icon=ft.Icons.TERMINAL, label=i18n.get("nav_winget_create")
                ),  # 19 Winget Create
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

        # First run / Demo mode check
        import threading
        threading.Thread(target=self._check_first_run, daemon=True).start()

        # Handle command line arguments for initial navigation
        import sys
        # Check for silent mode (minimize UI, auto-accept prompts)
        self.silent_mode = "--silent" in sys.argv

        if "--wizard" in sys.argv:
            # Delay navigation slightly to ensure UI is ready
            def nav_to_wizard():
                """
                Navigate to the Packaging Wizard tab after a short delay to allow the UI to finish rendering.

                This helper waits approximately 0.5 seconds and then switches the application view to the Packaging Wizard.
                """
                import time
                time.sleep(0.5)  # Wait for UI to be fully rendered
                from switchcraft.gui_modern.nav_constants import NavIndex
                self.goto_tab(NavIndex.PACKAGING_WIZARD)
            threading.Thread(target=nav_to_wizard, daemon=True).start()
        elif "--analyzer" in sys.argv or "--all-in-one" in sys.argv:
            # Delay navigation slightly to ensure UI is ready
            def nav_to_analyzer():
                """
                Navigate the application to the Analyzer tab after a short delay to allow the UI to finish rendering.
                """
                import time
                time.sleep(0.5)  # Wait for UI to be fully rendered
                from switchcraft.gui_modern.nav_constants import NavIndex
                self.goto_tab(NavIndex.ANALYZER)
            threading.Thread(target=nav_to_analyzer, daemon=True).start()

        # In silent mode, minimize window and suppress first-run dialogs
        if self.silent_mode:
            try:
                if hasattr(self.page, 'window'):
                    self.page.window.minimized = True
            except Exception:
                pass

        # self.back_btn is now defined in __init__


        layout_controls = []
        if self.banner_container:
             layout_controls.append(self.banner_container)

        layout_controls.append(self.sidebar)

        # Replace loading screen with actual UI (like RDM - banner stays visible until app is ready)
        # Ensure UI is fully built before replacing loading screen
        # IMPORTANT: Only replace loading screen if it exists (from modern_main.py)
        # Check if page has controls and if first control is the loading container
        has_loading_screen = len(self.page.controls) > 0

        self.page.clean()
        self.page.add(
             ft.Column(layout_controls, expand=True, spacing=0)
        )
        # Force multiple updates to ensure UI is visible and rendered
        self.page.update()
        self.page.update()  # Second update to ensure rendering
        self.page.update()  # Third update for good measure

        # Setup responsive UI (hide/show sidebar and menu button based on window size)
        self._update_responsive_ui()

        # Add window resize listener if available
        try:
            if hasattr(self.page, 'on_resized'):
                self.page.on_resized = lambda e: self._update_responsive_ui()
        except Exception:
            pass

        # Now shutdown splash screen after UI is fully visible
        if self.splash_proc:
            try:
                self.splash_proc.terminate()
            except Exception:
                pass


    def _open_notifications(self, e):
        """
        Show the notifications drawer populated from the notification service, or close the drawer if it is currently open.

        Builds a NavigationDrawer containing the current notifications and opens it on the page; when opened, all notifications are marked as read. If a notifications drawer is already active and open, the drawer is closed instead. This method updates the instance's active drawer state as a side effect.
        """
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
            items.append(ft.Text(i18n.get("no_notifications") or "No notifications", italic=True))
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
        try:
            logger.debug(f"Back button clicked. History: {getattr(self, '_navigation_history', [])}")
            if hasattr(self, '_navigation_history') and len(self._navigation_history) > 1:
                # Pop current view
                self._navigation_history.pop()
                # Go to previous view
                prev_idx = self._navigation_history[-1]
                logger.debug(f"Navigating back to index: {prev_idx}")
                self.sidebar.set_selected_index(prev_idx)
                self._switch_to_tab(prev_idx)
                self._update_back_btn_visibility()
            else:
                logger.debug("No history to go back to")
        except Exception as ex:
            logger.exception(f"Error in back button handler: {ex}")
            try:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Failed to go back: {ex}"),
                    bgcolor="RED"
                )
                self.page.snack_bar.open = True
                self.page.update()
            except Exception:
                pass

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

    def _build_navigation_drawer(self):
        """Build the navigation drawer with all destinations for mobile."""
        if not hasattr(self, 'destinations') or not self.destinations:
            return None

        drawer_items = []
        for i, dest in enumerate(self.destinations):
            # Get label and icon from destination
            label = getattr(dest, 'label', f'Item {i}')
            icon = getattr(dest, 'icon', ft.Icons.CIRCLE)
            selected_icon = getattr(dest, 'selected_icon', icon)

            # Use selected icon if this is the current tab
            current_icon = selected_icon if i == getattr(self, '_current_tab_index', 0) else icon

            drawer_items.append(
                ft.ListTile(
                    leading=ft.Icon(current_icon),
                    title=ft.Text(label),
                    on_click=lambda e, idx=i: self._on_drawer_navigate(idx),
                    selected=i == getattr(self, '_current_tab_index', 0)
                )
            )

        # Add dynamic addon destinations if any
        if hasattr(self, 'dynamic_addons') and self.dynamic_addons and hasattr(self, 'first_dynamic_index'):
            drawer_items.append(ft.Divider())
            for idx, addon in enumerate(self.dynamic_addons):
                addon_idx = self.first_dynamic_index + idx
                icon_name = addon.get("icon", "EXTENSION")
                icon_code = getattr(ft.Icons, icon_name, ft.Icons.EXTENSION)
                drawer_items.append(
                    ft.ListTile(
                        leading=ft.Icon(icon_code),
                        title=ft.Text(addon.get("name", "Addon")),
                        on_click=lambda e, nav_idx=addon_idx: self._on_drawer_navigate(nav_idx),
                        selected=addon_idx == getattr(self, '_current_tab_index', 0)
                    )
                )

        drawer = ft.NavigationDrawer(
            controls=drawer_items,
            on_dismiss=self._on_navigation_drawer_dismiss
        )
        return drawer

    def _toggle_navigation_drawer(self, e):
        """Toggle the navigation drawer for mobile devices."""
        try:
            # Check if drawer is currently open
            is_open = False
            if hasattr(self.page, 'drawer') and self.page.drawer is not None:
                try:
                    is_open = getattr(self.page.drawer, 'open', False)
                except Exception:
                    is_open = False

            if is_open:
                # Close drawer
                if hasattr(self.page.drawer, 'open'):
                    self.page.drawer.open = False
                if hasattr(self.page, 'close') and self.page.drawer:
                    try:
                        self.page.close(self.page.drawer)
                    except Exception:
                        pass
                self.page.drawer = None
                self.page.update()
            else:
                # Open drawer
                drawer = self._build_navigation_drawer()
                if drawer:
                    self.page.drawer = drawer
                    self.page.update()
                    drawer.open = True
                    self.page.update()
        except Exception as ex:
            logger.exception(f"Error toggling navigation drawer: {ex}")

    def _on_drawer_navigate(self, index):
        """Handle navigation from drawer item click."""
        try:
            # Close drawer first
            if hasattr(self.page, 'drawer') and self.page.drawer:
                self.page.drawer.open = False
                self.page.drawer = None
                self.page.update()

            # Navigate to the selected tab
            self.goto_tab(index)
        except Exception as ex:
            logger.exception(f"Error navigating from drawer: {ex}")

    def _on_navigation_drawer_dismiss(self, e):
        """Handle navigation drawer dismiss event."""
        try:
            if hasattr(self.page, 'drawer') and self.page.drawer:
                self.page.drawer.open = False
                self.page.drawer = None
                self.page.update()
        except Exception as ex:
            logger.debug(f"Error in navigation drawer dismiss handler: {ex}")

    def _update_responsive_ui(self):
        """Update UI based on window size - hide sidebar on mobile, show hamburger menu."""
        try:
            # Get window width if available
            window_width = None
            if hasattr(self.page, 'window') and hasattr(self.page.window, 'width'):
                window_width = self.page.window.width
            elif hasattr(self.page, 'width'):
                window_width = self.page.width

            # Use breakpoint of 800px - below this is considered mobile
            is_mobile = window_width is not None and window_width < 800

            # Update sidebar visibility
            if hasattr(self, 'sidebar') and hasattr(self.sidebar, 'sidebar_container'):
                self.sidebar.sidebar_container.visible = not is_mobile
                try:
                    self.sidebar.sidebar_container.update()
                except Exception:
                    pass

            # Update hamburger menu button visibility
            if hasattr(self, 'menu_btn'):
                self.menu_btn.visible = is_mobile
                try:
                    self.menu_btn.update()
                except Exception:
                    pass

            # Update logo visibility in AppBar leading (hide on mobile to make room for menu)
            if hasattr(self.page, 'appbar') and self.page.appbar and hasattr(self.page.appbar, 'leading'):
                # The leading is now a Row with menu_btn and logo_icon
                # We'll keep both but adjust spacing
                pass

        except Exception as ex:
            logger.debug(f"Error updating responsive UI: {ex}")

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
        """
        Switch the main content area to the view identified by a navigation index.

        Loads and displays the view corresponding to `idx`: shows an immediate loading indicator, instantiates the target view (with error fallback to a crash dump view), supports cached views and dynamically loaded addon views, then swaps the content with a fade-in transition. Also records the selected index on self._current_tab_index and updates the page.

        Parameters:
            idx (int): Navigation index representing a destination, settings sub-tab, category view (>=100), or a dynamic addon slot (computed from self.first_dynamic_index).
        """
        # Store current tab index for language change refresh
        self._current_tab_index = idx

        # 1. SHOW LOADING STATE IMMEDIATELY
        self.content.controls.clear()

        # For now, let's just fade in the new content
        loading_view = ft.Container(
                 content=ft.Column(
                     controls=[
                         ft.ProgressRing(),
                         ft.Text(i18n.get("loading_view") or "Loading...", size=16)
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
                    new_controls.append(ft.Text(i18n.get("unknown_category") or "Unknown Category", color="red"))
            else:
                new_controls.append(ft.Text("Unknown Category", color="red"))

        elif idx == NavIndex.HOME:
             # Home
             def _f():
                from switchcraft.gui_modern.views.home_view import ModernHomeView
                return ModernHomeView(self.page, on_navigate=self.goto_tab)
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
                    """
                    Load the addon view class for the addon identified by `addon['id']` and return an instance bound to the app's page.

                    Returns:
                        The instantiated view for the addon, constructed with `self.page`.
                    """
                    view_class = self.addon_service.load_addon_view(addon['id'])
                    return view_class(self.page)
                load_view(_f)
            else:
                new_controls.append(ft.Text(i18n.get("unknown_tab") or "Unknown Tab", color="red"))


        # 3. SWAP CONTENT with Fade In
        self.content.controls.clear()

        # Wrap new controls in a container with opacity 0 initially
        fade_container = ft.Container(
            content=new_controls[0] if new_controls else ft.Text(i18n.get("error_loading") or "Error loading view"),
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
        """
        Show a modal restart-required dialog and then terminate the application window.

        Displays a modal alert dialog with a localized title and message indicating that a restart is required, waits briefly to allow the user to see the message, and then destroys the application window.
        """
        dlg = ft.AlertDialog(
            title=ft.Text(i18n.get("restart_required_title") or "Restart Required"),
            content=ft.Text(i18n.get("restart_required_msg") or "Settings changed. Restarting app..."),
            modal=True,
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()
        time.sleep(2)
        self.page.window.destroy()

    def _clear_all_notifications(self, drawer):
        """
        Close the notifications drawer and clear all stored notifications.

        Parameters:
            drawer: The navigation drawer control instance to close after clearing notifications.
        """
        self.notification_service.clear_all()
        # Close Drawer
        if hasattr(self.page, "close"):
            self.page.close(drawer)
        else:
            drawer.open = False
            self.page.update()
        # Re-open empty? No, just close.

    def _check_first_run(self):
        """
        Check whether the application is running for the first time and, if so, clear the first-run flag and optionally offer a demo.

        If the stored "FirstRun" flag is true, this method sets it to false. When running from source (not a frozen/packaged build), it opens a modal dialog offering to start a demo analysis; choosing to start the demo navigates to the Analyzer tab and initiates the demo analysis, while choosing to defer simply closes the dialog.
        """
        from switchcraft.utils.config import SwitchCraftConfig
        from switchcraft.utils.i18n import i18n
        import sys

        if SwitchCraftConfig.get_value("FirstRun", True):
            SwitchCraftConfig.set_user_preference("FirstRun", False)
            # If running from source or portable, offer demo
            if not getattr(sys, 'frozen', False):
                def show_demo_dialog():
                    """
                    Show a modal dialog offering the user to run a demo analysis.

                    The dialog presents a brief message and two actions: "Start Demo" begins a demo analysis by navigating to the analyzer view and triggering the demo workflow; "Later" simply closes the dialog.
                    """
                    def start_demo(e):
                        dlg.open = False
                        self.page.update()
                        # Navigate to analyzer and start demo
                        self.goto_tab(NavIndex.ANALYZER)
                        # Wait a bit for view to load, then trigger demo
                        import time
                        time.sleep(0.5)
                        self._start_demo_analysis()

                    def skip_demo(e):
                        """
                        Close the demo dialog and refresh the UI.

                        Intended as an event handler invoked when the user opts to skip the demo; closes the dialog and updates the page.
                        """
                        dlg.open = False
                        self.page.update()

                    dlg = ft.AlertDialog(
                        title=ft.Text(i18n.get("welcome_switchcraft") or "Welcome to SwitchCraft!"),
                        content=ft.Column([
                            ft.Text(i18n.get("demo_mode_msg") or "Welcome to SwitchCraft! Would you like to run a demo analysis?", size=14),
                        ], tight=True),
                        actions=[
                            ft.TextButton(i18n.get("btn_later") or "Later", on_click=skip_demo),
                            ft.Button(
                                "Start Demo",
                                on_click=start_demo,
                                bgcolor="BLUE_700",
                                color="WHITE"
                            ),
                        ]
                    )
                    self.page.open(dlg)

                # Show dialog on UI thread
                self.page.run_task(show_demo_dialog)

    def _start_demo_analysis(self):
        """
        Download a sample installer and initiate a demo analysis in the Analyzer view.

        Runs in a background thread: shows a "Downloading..." snack, downloads a demo installer to a temporary file, navigates to the Analyzer tab if necessary, waits briefly for the view to load, and then triggers the analyzer view's start_analysis with the downloaded file path. On failure logs the error and presents a dialog offering to open the project's download/releases page.
        """
        import tempfile
        import threading
        import requests
        from switchcraft.utils.i18n import i18n
        from switchcraft.gui_modern.nav_constants import NavIndex

        def download_and_analyze():
            """
            Download a demo installer to a temporary file and, if possible, navigate to the Analyzer view and start analysis on the downloaded file.

            Downloads the 7-Zip MSI to a temporary file (left on disk), displays a "downloading" snack while in progress, then navigates to the ANALYZER tab and invokes `start_analysis(path)` on the cached analyzer view if available. On failure, logs the error and opens a dialog offering to open the project's download/releases page.

            Note: This function writes a temporary .msi file with delete=False and will not remove it automatically; it performs network I/O and may raise exceptions internally which are handled by showing a user-facing dialog.
            """
            try:
                # Show downloading message
                self._show_snack(i18n.get("demo_downloading") or "Downloading demo installer...", "BLUE")

                # Use 7-Zip MSI as a safe demo
                url = "https://www.7-zip.org/a/7z2409-x64.msi"

                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".msi")
                tmp.close()

                # Download
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()

                with open(tmp.name, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Navigate to analyzer if not already there
                if hasattr(self, '_current_tab_index') and self._current_tab_index != NavIndex.ANALYZER:
                    self.goto_tab(NavIndex.ANALYZER)

                # Wait a bit for view to load
                import time
                time.sleep(0.5)

                # Trigger analysis
                if 'analyzer' in self._view_cache:
                    analyzer_view = self._view_cache['analyzer']
                    if hasattr(analyzer_view, 'start_analysis'):
                        self.page.run_task(lambda: analyzer_view.start_analysis(tmp.name))

            except Exception as e:
                logger.error(f"Demo failed: {e}")
                def show_error():
                    def open_download(e):
                        dlg.open = False
                        self.page.update()
                        webbrowser.open("https://github.com/FaserF/SwitchCraft/releases")

                    dlg = ft.AlertDialog(
                        title=ft.Text(i18n.get("demo_error_title") or "Download Error"),
                        content=ft.Text(i18n.get("demo_ask_download", error=str(e)) or f"Could not download demo installer.\nError: {e}\n\nOpen download page instead?"),
                        actions=[
                            ft.TextButton(i18n.get("btn_cancel") or "Cancel", on_click=lambda e: setattr(dlg, "open", False) or self.page.update()),
                            ft.Button("Open Download Page", on_click=open_download, bgcolor="BLUE_700", color="WHITE"),
                        ]
                    )
                    self.page.open(dlg)

                self.page.run_task(show_error)

        threading.Thread(target=download_and_analyze, daemon=True).start()

def main(page: ft.Page):
    """
    Create and attach the ModernApp application to the given Flet page.

    Instantiates ModernApp with the provided page and exposes its _show_restart_countdown method on the page as page._show_restart_countdown for external use.
    """
    # Add restart method to page for injection if needed, or pass app instance.
    app = ModernApp(page)
    page._show_restart_countdown = app._show_restart_countdown

if __name__ == "__main__":
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    ft.run(main, assets_dir=assets_dir)