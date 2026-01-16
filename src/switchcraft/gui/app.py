import customtkinter as ctk
from tkinterdnd2 import TkinterDnD
import threading
from pathlib import Path
from PIL import Image
import webbrowser
import logging
from tkinter import messagebox
import os
import sys
import ctypes

from switchcraft.utils.logging_handler import setup_session_logging
from switchcraft.utils.i18n import i18n
from switchcraft.utils.app_updater import UpdateChecker
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.security import SecurityChecker
from switchcraft import __version__

# Setup session logging early to capture all events
setup_session_logging()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set default theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def on_closing(self):
        self.destroy()

    def run(self):
        # CLI Argument Handling for Addons
        # CLI flag triggers addon check/prompt on startup
        """
        Start the application's GUI loop, honoring the "--install-addons" CLI flag.

        If "--install-addons" appears in sys.argv, schedule an addon status check to run after 2 seconds, then enter the Tkinter main event loop.
        """
        if "--install-addons" in sys.argv:
            self.after(2000, self._check_addon_status)

        self.mainloop()
    def __init__(self):
        """
        Initialize the main application window, load visual assets, and display the startup loading screen.

        Performs initial window setup (title, size, TkinterDnD integration), loads the app logo, initializes state such as `pending_update`, and constructs a centered loading UI (logo, app title, loading text, indeterminate progress bar). Forces an immediate UI update to show the loading screen and schedules heavy initialization via `_perform_initialization` to run after a short delay.

        Raises:
            Exception: If any initialization step fails; the exception is logged and re-raised.
        """
        try:
            super().__init__()
            self.TkdndVersion = TkinterDnD._require(self)
            self.title(f"SwitchCraft Legacy v{__version__}")
            self.geometry(f"{1100}x{580}")

            # Assets & State
            self.logo_image = None
            self.load_assets()


            # Pending update info (for "Update Later" feature)
            self.pending_update = None

            # 1. Show Loading Screen immediately
            # Configure main window grid first
            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(0, weight=1)

            self.loading_frame = ctk.CTkFrame(self)
            self.loading_frame.grid(row=0, column=0, sticky="nsew")
            self.loading_frame.grid_columnconfigure(0, weight=1)
            # Configure all rows that will be used (0-3)
            self.loading_frame.grid_rowconfigure(0, weight=1)
            self.loading_frame.grid_rowconfigure(1, weight=0)
            self.loading_frame.grid_rowconfigure(2, weight=0)
            self.loading_frame.grid_rowconfigure(3, weight=0)
            self.loading_frame.grid_rowconfigure(4, weight=1)

            # Create a centered container for better layout
            center_frame = ctk.CTkFrame(self.loading_frame, fg_color="transparent")
            center_frame.grid(row=1, column=0, rowspan=3, sticky="", pady=20)

            if self.logo_image:
                 ctk.CTkLabel(center_frame, image=self.logo_image, text="").pack(pady=(0, 20))

            ctk.CTkLabel(
                center_frame,
                text=i18n.get("app_title") or "SwitchCraft",
                font=ctk.CTkFont(size=24, weight="bold")
            ).pack(pady=(0, 20))

            self.loading_label = ctk.CTkLabel(center_frame, text="Loading components...")
            self.loading_label.pack(pady=(0, 20))

            self.loading_bar = ctk.CTkProgressBar(center_frame, mode="indeterminate", width=400)
            self.loading_bar.pack(pady=(0, 20))
            self.loading_bar.start()

            # Force update to show loading screen immediately
            self.update()

            # Defer initialization
            self.after(100, self._perform_initialization)
        except Exception as e:
            # If initialization fails, log and re-raise so main() can handle it
            logger.exception(f"Failed to initialize App window: {e}")
            raise

    def _update_loading(self, text):
        """
        Set the loading message shown on the startup screen and refresh the UI.

        Also logs the message at info level and forces a UI update so the new text is rendered immediately.

        Parameters:
            text (str): The loading message to display.
        """
        logger.info(f"Init: {text}")
        self.loading_label.configure(text=text)
        self.update_idletasks()

    def _perform_initialization(self):
        """Start heavy initialization in a background thread."""
        threading.Thread(target=self._run_background_init, daemon=True).start()

    def _run_background_init(self):
        """
        Initialize heavy addons and core services on a background thread and schedule final UI setup on the main thread.

        This method performs long-running imports and initialization tasks off the UI thread:
        - Registers available addons and assigns the application window to the notification service.
        - Attempts to load the AI addon and sets `self.ai_service` when available.
        - Instantiates `IntuneService` and `HistoryService` and assigns them to `self.intune_service` and `self.history_service`.
        - Attempts to load the Winget addon helper; on failure records a human-readable message in `self.winget_load_error` if the addon is installed but failed to load, otherwise leaves `self.winget_helper` as `None`.
        - Detects whether the debug addon is installed and sets `self.has_debug_addon`.
        - When initialization completes, schedules `self._finalize_startup` to run on the main/UI thread.

        On an unexpected, critical error during background initialization, writes a crash dump to a platform-appropriate Logs directory (APPDATA on Windows or a home-directory fallback) and schedules a non-blocking error dialog describing the failure.
        """
        try:
            self.after(0, lambda: self._update_loading("Registering Addons..."))
            from switchcraft.services.addon_service import AddonService
            AddonService.register_addons()

            self.after(0, lambda: self._update_loading("Setting up Notifications..."))
            from switchcraft.services.notification_service import NotificationService
            NotificationService.set_app_window(self)

            self.after(0, lambda: self._update_loading("Loading Services..."))

            # 1. AI Addon (Heavy Import)
            self.ai_service = None
            try:
                from switchcraft.services.addon_service import AddonService
                addon_service = AddonService()
                ai_mod = addon_service.import_addon_module("ai", "service")
                if ai_mod:
                    self.ai_service = ai_mod.SwitchCraftAI()
            except Exception as e:
                logger.info(f"AI Addon not loaded: {e}")

            # 2. Standard Services
            from switchcraft.services.intune_service import IntuneService
            self.intune_service = IntuneService()
            from switchcraft.services.history_service import HistoryService
            self.history_service = HistoryService()

            # 3. Winget Addon
            self.winget_helper = None
            self.winget_load_error = None
            try:
                from switchcraft.services.addon_service import AddonService
                addon_service = AddonService()
                winget_mod = addon_service.import_addon_module("winget", "utils.winget")
                if winget_mod:
                    self.winget_helper = winget_mod.WingetHelper()
                elif AddonService.is_addon_installed_static("winget"):
                    # Addon is installed but failed to load
                    self.winget_load_error = "Addon is installed but failed to load. Check logs."
            except Exception as e:
                logger.exception(f"Winget Addon import crashed: {e}")
                if AddonService.is_addon_installed_static("winget"):
                    self.winget_load_error = str(e)

            # 4. Debug Addon
            from switchcraft.services.addon_service import AddonService
            self.has_debug_addon = AddonService.is_addon_installed_static("debug")

            # Initialization done, switch to main thread for UI
            self.after(0, self._finalize_startup)

        except Exception as e:
            logger.exception(f"Critical error during background init: {e}")
            # Write crash dump
            try:
                import traceback
                from datetime import datetime
                from pathlib import Path
                import os

                app_data = os.getenv('APPDATA')
                if app_data:
                    dump_dir = Path(app_data) / "FaserF" / "SwitchCraft" / "Logs"
                else:
                    dump_dir = Path.home() / ".switchcraft" / "Logs"
                dump_dir.mkdir(parents=True, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dump_file = dump_dir / f"crash_dump_{timestamp}.txt"

                with open(dump_file, "w", encoding="utf-8") as f:
                    f.write("SwitchCraft Legacy Crash Dump\n")
                    f.write(f"Time: {datetime.now().isoformat()}\n")
                    f.write(f"Error: {str(e)}\n\n")
                    f.write("Traceback:\n")
                    f.write("="*60 + "\n")
                    traceback.print_exception(type(e), e, e.__traceback__, file=f)

                err_msg = f"Critical error during startup:\n{str(e)}\n\nCrash dump saved to:\n{dump_file}"
            except Exception:
                err_msg = f"Critical error during startup:\n{str(e)}"

            # Show error dialog with crash dump info
            def show_error():
                """
                Display a startup error dialog showing the current error message.

                Attempts to show a messagebox with the startup error text stored in `err_msg`. Any exceptions raised while displaying the dialog are suppressed to avoid further failures. The function does not close or destroy the application automatically; the user must dismiss the dialog manually.
                """
                try:
                    messagebox.showerror("SwitchCraft Startup Error", err_msg)
                except Exception:
                    pass
                finally:
                    # Don't destroy immediately - let user see the error
                    # They can close manually
                    pass

            self.after(0, show_error)

    def _finalize_startup(self):
        """Build UI components on main thread after services are loaded."""
        self._update_loading("Building Tabs...")

        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # Ensure loading screen stays on top while we build the UI
        self.loading_frame.lift()

        self.tab_analyzer = self.tabview.add(i18n.get("tab_analyzer"))
        self.tab_helper = self.tabview.add(i18n.get("tab_helper"))
        self.setup_helper_tab()
        self.tab_settings = self.tabview.add(i18n.get("tab_settings"))

        self.setup_analyzer_tab()

        self.tab_intune = self.tabview.add("Intune")
        self.setup_intune_tab()

        # Intune Store
        self.tab_intune_store = self.tabview.add("Intune Store")
        self.setup_intune_store_tab()

        if SwitchCraftConfig.get_value("EnableWinget", True):
            self.tab_winget = self.tabview.add("Winget Store")
            self.setup_winget_tab()

        self.tab_history = self.tabview.add("History")
        self.setup_history_tab()

        self.setup_settings_tab()

        self._update_loading("Finalizing UI...")
        self.setup_version_banner()

        # Demo / First Start Logic
        self.after(500, self._run_demo_init)

        # Check for Load Errors (Winget etc)
        self.after(1000, self._check_init_errors)

        # Check for Addon (Virus Mitigation)
        self.after(3000, self._check_addon_status)

        # Cloud Backup Check (Weekly)
        self.after(5000, self._check_cloud_backup_auto)

        # Update Check
        self.after(2000, self.check_updates_silently)

        # Security Check
        self.after(4000, self.check_security_silently)

        # Finally, remove loading screen
        self.after(800, self._finish_initialization)

    def _finish_initialization(self):
        # Remove Loading Screen
        if hasattr(self, 'loading_frame') and self.loading_frame:
            self.loading_frame.destroy()
        logger.info("Initialization complete.")

    def _run_demo_init(self):
        """Check if first run/demo mode is needed."""
        if SwitchCraftConfig.get_value("FirstRun", True):
            SwitchCraftConfig.set_user_preference("FirstRun", False)
            # If running from source or portable, offer demo
            if not self._is_installed_version():
                msg = i18n.get("demo_mode_msg") if "demo_mode_msg" in i18n.translations.get(
                    i18n.language) else "Welcome to SwitchCraft! Would you like to run a demo analysis?"
                if messagebox.askyesno("SwitchCraft Demo", msg):
                    # Locate own installer or download
                    self.after(500, self._start_demo_analysis)


    def _check_addon_status(self):
        """
        Check and handle missing addons, installing or prompting as appropriate.

        Checks whether the "advanced" and "ai" addons are installed. If running a dev or beta build and any are missing, attempts to install all missing addons silently in a background thread and, on success, schedules a restart countdown. For non-dev builds, if the "advanced" addon is missing and the user has not already been prompted, records that the prompt was shown, asks the user to confirm installation, and if accepted installs the addon in a background thread; on success schedules a restart countdown, otherwise shows an error dialog.
        """
        # 1. Check for Dev Build auto-install
        from switchcraft import __version__
        is_dev = "dev" in __version__.lower() or "beta" in __version__.lower()

        from switchcraft.services.addon_service import AddonService
        missing_any = not (AddonService.is_addon_installed_static("advanced") and AddonService.is_addon_installed_static("ai"))

        if is_dev and missing_any:
            logger.info("Dev build detected with missing addons. Auto-installing silently...")
            # Run in thread to not block UI, then show restart prompt
            def auto_install_all():
                from switchcraft.services.addon_service import AddonService
                success = AddonService.install_all_missing()
                if success:
                    logger.info("All addons installed successfully. Prompting for restart...")
                    self.after(0, self._show_restart_countdown)
                else:
                    logger.error("Some addons failed to install.")

            threading.Thread(target=auto_install_all, daemon=True).start()
            return

        from switchcraft.services.addon_service import AddonService
        if not AddonService.is_addon_installed_static("advanced"):
            # Only ask once per session or use config to remember "Don't ask again"
            if SwitchCraftConfig.get_value("AddonPromptShown", False):
                return

            SwitchCraftConfig.set_user_preference("AddonPromptShown", True)

            msg = (i18n.get("addon_missing_msg") or
                   "Advanced Features (Intune, Brute Force) are not installed.\n\n"
                   "These are packaged separately to avoid false-positive virus detection.\n\n"
                   "Download 'Advanced Features Addon' now?")

            if messagebox.askyesno(i18n.get("addon_missing_title") or "Advanced Features Missing", msg):
                # Auto-install with restart countdown
                def run_install():
                    from switchcraft.services.addon_service import AddonService
                    if AddonService.install_addon("advanced"):
                        self.after(0, self._show_restart_countdown)
                    else:
                        self.after(0, lambda: messagebox.showerror("Error", i18n.get("addon_install_failed_manual")))

                threading.Thread(target=run_install, daemon=True).start()

    def _show_restart_countdown(self):
        """
        Show a short countdown dialog and then attempt to restart the application to apply changes.

        Displays a modal countdown informing the user that a restart is required; when the countdown expires the app launches a replacement process and exits the current process. If the automatic restart fails, an error dialog is shown and the current process remains running.
        """
        from switchcraft.gui.components.countdown_dialog import CountdownDialog

        def do_restart():
            """
            Attempt to restart the running application by launching a new process and exiting the current one.

            Performs a best-effort relaunch that handles both frozen (PyInstaller) executables and running scripts: it prepares a cleaned environment, spawns a detached child process with the same invocation, allows it to start, then terminates the current process. On failure, logs the error and shows an error dialog prompting the user to restart manually.
            """
            import sys
            import subprocess
            import os
            import logging
            import time
            import gc

            logger.info("Restarting application...")

            executable = sys.executable
            # Handle arguments based on execution mode
            if getattr(sys, 'frozen', False):
                # Frozen: executable is the app itself. argv[0] is the exe path (same as executable).
                # New args should be just the parameters (argv[1:])
                launch_args = sys.argv[1:]
            else:
                # Script: executable is python.exe. argv[0] is the script path (app.py).
                # We need to pass [script_path] + parameters
                launch_args = sys.argv

            cwd = os.path.dirname(executable) if getattr(sys, 'frozen', False) else os.getcwd()

            try:
                # 1. Close all file handles and release resources
                # Flush and close logging handlers to release file locks
                logging.shutdown()

                # 2. Force garbage collection to close any remaining file handles
                gc.collect()

                # 3. Close all open windows/widgets to release resources
                try:
                    self.destroy()
                except Exception:
                    pass

                # 4. Small delay to allow file handles to be released
                time.sleep(0.2)

                # 5. Prepare environment: remove PyInstaller's _MEIPASS
                env = os.environ.copy()
                for key in list(env.keys()):
                    if key.startswith('_MEI'):
                        env.pop(key)

                # Check for other Pyinstaller vars
                env.pop('LD_LIBRARY_PATH', None) # Linux related but good practice

                if sys.platform == 'win32':
                    # Use Popen directly with DETACHED_PROCESS to survive parent death
                    # and explicit env.
                    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

                    cmd = [executable] + launch_args
                    logger.info(f"Restarting with command: {cmd}")

                    # Launch new process BEFORE quitting current one
                    subprocess.Popen(
                        cmd,
                        creationflags=flags,
                        close_fds=True,
                        env=env,
                        cwd=cwd,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                    # Give the new process a moment to start
                    time.sleep(0.3)
                else:
                    # Linux/Mac
                    subprocess.Popen(
                        [executable] + launch_args,
                        close_fds=True,
                        env=env,
                        cwd=cwd,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    time.sleep(0.3)

                # 6. Now quit and exit - the new process is already running
                self.quit()
                sys.exit(0)
            except Exception as e:
                # Re-setup logger to show error if possible (since we shut it down)
                logging.basicConfig(level=logging.INFO)
                logger.error(f"Restart failed: {e}")
                try:
                    messagebox.showerror("Error", "Could not restart automatically. Please restart manually.")
                except Exception:
                    pass

        CountdownDialog(
            self,
            i18n.get("restart_imminent") or "Restart Required",
            "Addon installed. Restarting automatically in:",
            timeout_seconds=5,
            on_timeout=do_restart
        )

    def _check_init_errors(self):
        """Check for initialization errors (e.g. addon load failures)."""
        if getattr(self, 'winget_load_error', None):
            msg = f"Winget Addon is installed but failed to load.\n\nError: {self.winget_load_error}\n\nPlease check logs or Reinstall."
            messagebox.showerror("Addon Load Error", msg)
            logger.error(f"Displaying Winget Load Error: {self.winget_load_error}")

    def _check_cloud_backup_auto(self):
        """Perform weekly cloud backup if enabled."""
        if not SwitchCraftConfig.get_value("CloudSyncAuto", True): # Default True as requested
            return

        from switchcraft.services.auth_service import AuthService
        from switchcraft.services.sync_service import SyncService

        # Must be authenticated
        if not AuthService.is_authenticated():
            return

        import time
        import json
        import threading

        last_backup = SwitchCraftConfig.get_value("LastCloudBackup", 0)
        now = time.time()

        # Weekly = 7 * 24 * 3600 = 604800 seconds
        if (now - last_backup) > 604800:
             logger.info("Weekly cloud backup check triggered.")
             def _run():
                 try:
                     import hashlib
                     # Hash current prefs to check against last known backup hash
                     current_prefs = SwitchCraftConfig.export_preferences()
                     current_hash = hashlib.md5(json.dumps(current_prefs, sort_keys=True).encode()).hexdigest()

                     last_hash = SwitchCraftConfig.get_value("LastBackupHash", "")

                     if current_hash != last_hash:
                         logger.info("Changes detected since last backup. Performing auto-backup...")
                         if SyncService.sync_up():
                             logger.info("Auto-backup successful.")
                             SwitchCraftConfig.set_user_preference("LastCloudBackup", now)
                             SwitchCraftConfig.set_user_preference("LastBackupHash", current_hash)
                         else:
                             # Sync failed but didn't raise - update timestamp to avoid continuous retries
                             logger.warning("Auto-backup returned False. Will retry next week.")
                             SwitchCraftConfig.set_user_preference("LastCloudBackup", now)
                     else:
                         logger.info("No changes since last backup. Skipping.")
                         # Update timestamp so we don't check every restart for another week
                         SwitchCraftConfig.set_user_preference("LastCloudBackup", now)
                 except Exception as e:
                     logger.exception(f"Auto-backup failed: {e}")
                     # Still update LastCloudBackup so we don't retry continuously on next start
                     SwitchCraftConfig.set_user_preference("LastCloudBackup", now)

             threading.Thread(target=_run, daemon=True).start()


    def _toggle_winget_tab(self, enabled):
        """Show or hide the Winget tab based on settings."""
        logger.debug(f"Toggling Winget tab: enabled={enabled}")
        logger.debug(f"Current tabs before toggle: {list(self.tabview._tab_dict.keys())}")

        if enabled:
            if "Winget Store" not in self.tabview._tab_dict:
                # CTkTabview.add() appends to the end.
                # To insert at correct position (after Intune Utility, before History),
                # we need to temporarily remove and re-add History tab.
                history_exists = "History" in self.tabview._tab_dict
                history_view_ref = None

                if history_exists:
                    # Store reference to existing History view to preserve state
                    history_view_ref = getattr(self, 'history_view', None)
                    if history_view_ref:
                        history_view_ref.pack_forget()  # Detach but don't destroy
                    self.tabview.delete("History")
                    logger.debug("Temporarily removed History tab for repositioning")

                # Add Winget Store
                self.tab_winget = self.tabview.add("Winget Store")
                self.setup_winget_tab()
                logger.debug("Added Winget Store tab")

                if history_exists:
                    # Re-add History tab and reattach preserved view
                    self.tab_history = self.tabview.add("History")
                    if history_view_ref:
                        # Reparent and repack the existing view to preserve state
                        history_view_ref.master = self.tab_history
                        history_view_ref.pack(fill="both", expand=True)
                        logger.debug("Re-attached existing History view (state preserved)")
                    else:
                        # Fallback: create new view if reference was lost
                        self.setup_history_tab()
                        logger.debug("Re-created History tab (no view reference)")
        else:
            if "Winget Store" in self.tabview._tab_dict:
                self.tabview.delete("Winget Store")
                self.tab_winget = None
                logger.debug("Deleted Winget Store tab")

        logger.debug(f"Current tabs after toggle: {list(self.tabview._tab_dict.keys())}")

    def _start_demo_analysis(self):
        """Download or locate a sample installer for demo."""
        try:
            # Basic logic: Try to analyze self if exe, or download 7zip/notepad++ as demo
            target = sys.executable if getattr(sys, 'frozen', False) else None

            if not target or "python" in target.lower():
                # Download a known safe small installer (e.g. 7-Zip or Notepad++)
                # For now, let's use a dummy path or ask user to pick one?
                # User asked for "dynamic download"
                self.status_bar.configure(text=i18n.get("demo_downloading"))

                # Using 7-Zip MSI as a safe demo (usually stable URL)
                url = "https://www.7-zip.org/a/7z2409-x64.msi"

                import tempfile

                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".msi")
                tmp.close()

                threading.Thread(target=self._download_and_analyze, args=(url, tmp.name), daemon=True).start()
                return

            self.start_analysis(target)
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            # Fallback to browser if download fails
            if messagebox.askyesno(
                    i18n.get("demo_error_title"), i18n.get("demo_ask_download", error=str(e))):
                webbrowser.open("https://github.com/FaserF/SwitchCraft/releases")

    def _download_and_analyze(self, url, path):
        try:
            import requests
            r = requests.get(url, stream=True)
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            self.after(0, lambda: self.start_analysis(path))
        except Exception as e:
            logger.error(f"Download failed: {e}")
            err_msg = str(e)
            self.after(0, lambda: messagebox.showerror("Download Error", err_msg))

    def start_analysis(self, file_path):
        """Delegate analysis to AnalyzerView and switch tabs."""
        try:
            self.tabview.set(i18n.get("tab_analyzer"))
            # Ensure analyzer view is ready
            if hasattr(self, 'analyzer_view'):
                self.analyzer_view._start_analysis(file_path)
            else:
                logger.error("Analyzer View not initialized")
                messagebox.showerror(i18n.get("error"), "Analyzer component not ready.")
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda: messagebox.showerror(i18n.get("demo_error_title"), i18n.get("demo_ask_download", error=error_msg)))

    def _should_show_ai_helper(self):
        """Determine if AI Helper tab should be shown."""
        # Always show AI helper for now, as requested
        return True

    def on_close(self):
        """Handle app close - open update if scheduled."""
        if self.pending_update:
            logger.info(f"Opening pending update: {self.pending_update['version']}")
            webbrowser.open(self.pending_update['url'])
        self.destroy()

    def load_assets(self):
        try:
            # Load Logo
            logo_path = self._get_resource_path("switchcraft_logo.png")

            # Dev environment fallback (if not found at root in dev)
            if not logo_path.exists():
                # Try standard project structure relative to this file
                # src/switchcraft/gui/app.py -> src/switchcraft/assets/
                base = Path(__file__).parent.parent
                logo_path = base / "assets" / "switchcraft_logo.png"

            if logo_path.exists():
                pil_image = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(80, 80))

                # Fix Taskbar Grouping (MUST BE DONE BEFORE SETTING ICON)
                myappid = f"switchcraft.app.{__version__}"
                try:
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                except Exception:
                    pass

                # Set Window Icon (Taskbar/Titlebar)
                # Use iconphoto for PNG support
                from PIL import ImageTk
                icon_photo = ImageTk.PhotoImage(pil_image)
                self.iconphoto(True, icon_photo) # True applies to all future toplevels too
            else:
                logger.warning(f"Logo not found at {logo_path}")
        except Exception as e:
            logger.error(f"Failed to load assets: {e}")

    def _get_resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller."""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return Path(base_path) / relative_path

    def setup_version_banner(self):
        """Display a warning banner for beta/dev versions."""
        version_lower = __version__.lower()

        if "beta" in version_lower or "dev" in version_lower:
            # Determine banner color and text based on version type
            if "dev" in version_lower:
                bg_color = "#DC3545"  # Red for development
                text = i18n.get("beta_warning_dev", version=__version__)
            else:
                bg_color = "#FFC107"  # Orange/Yellow for beta
                text = i18n.get("beta_warning_beta", version=__version__)

            # Create banner at the bottom of the window
            self.grid_rowconfigure(1, weight=0)

            banner_frame = ctk.CTkFrame(self, fg_color=bg_color, corner_radius=0)
            banner_frame.grid(row=1, column=0, sticky="ew")

            banner_label = ctk.CTkLabel(
                banner_frame,
                text=text,
                text_color="black" if "beta" in version_lower else "white",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            banner_label.pack(pady=5)

    # --- Update Logic ---
    def check_updates_silently(self):
        self._run_update_check(show_no_update=False)

    def _run_update_check(self, show_no_update=True):
        def _target():
            try:
                checker = UpdateChecker()
                has_update, version_str, _ = checker.check_for_updates()

                if has_update:
                    # If called silently (startup), treat as startup check
                    is_startup = not show_no_update
                    self.after(0, lambda: self.show_update_dialog(checker, is_startup=is_startup))
                elif show_no_update:
                    self.after(0, lambda: messagebox.showinfo(i18n.get("update_check_title"), i18n.get("no_update_found") or "No updates available."))
            except Exception as e:
                logger.error(f"Update check failed: {e}")
                error_msg = str(e)
                if show_no_update:
                    self.after(0, lambda: messagebox.showerror("Update Error", error_msg))

        threading.Thread(target=_target, daemon=True).start()

    def _is_installed_version(self):
        """Check if running as installed version (has registry entry) or portable."""
        if sys.platform != 'win32':
            return False

        path = SwitchCraftConfig.get_value('InstallPath')
        if path:
            return path.lower() in sys.executable.lower()
        return False

    def _get_skipped_version(self):
        """Get the version that user chose to skip."""
        return SwitchCraftConfig.get_value("SkippedVersion", "")

    def _set_skipped_version(self, version):
        """Save skipped version to registry."""
        SwitchCraftConfig.set_user_preference("SkippedVersion", version)

    def show_update_dialog(self, checker, is_startup=False):
        """Show update dialog with three options: Update Now, Update Later, Skip Version."""
        # Check if this version was skipped
        if is_startup and checker.latest_version == self._get_skipped_version():
            logger.info(f"Skipping update dialog for skipped version: {checker.latest_version}")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(i18n.get("update_available_title"))
        dialog.geometry("520x450")
        dialog.transient(self)
        dialog.grab_set()  # Modal

        # Header
        ctk.CTkLabel(
            dialog,
            text=i18n.get("update_available"),
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=15)

        # Version info
        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            info_frame,
            text=f"{i18n.get('current_version')}: {checker.current_version}"
        ).pack(
            anchor="w",
            padx=10,
            pady=2)
        ctk.CTkLabel(
            info_frame,
            text=f"{i18n.get('new_version')}: {checker.latest_version}",
            text_color="green",
            font=ctk.CTkFont(
                weight="bold")).pack(
                    anchor="w",
                    padx=10,
            pady=2)

        date_str = checker.release_date.split("T")[0] if checker.release_date else i18n.get("unknown")
        channel_str = checker.channel.capitalize() if hasattr(checker, 'channel') else "Stable"
        ctk.CTkLabel(
            dialog,
            text=f"{i18n.get('released')}: {date_str} | Channel: {channel_str}").pack(
            anchor="w", padx=10, pady=2)

        # Changelog
        ctk.CTkLabel(
            dialog,
            text=f"{i18n.get('changelog')}:",
            font=ctk.CTkFont(
                weight="bold")).pack(
            anchor="w",
            padx=20,
            pady=(
                10,
                5))
        textbox = ctk.CTkTextbox(dialog, height=120)
        textbox.pack(fill="x", padx=20, pady=5)
        textbox.insert("0.0", checker.release_notes or i18n.get("no_changelog"))
        textbox.configure(state="disabled")

        # Get appropriate download URL (installer for installed, portable for portable)
        is_installed = self._is_installed_version()
        if is_installed:
            # Prefer installer
            download_url = self._get_installer_url(checker)
        else:
            # Prefer portable
            download_url = self._get_portable_url(checker)

        # Buttons frame
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        # Update Now
        def update_now():
            webbrowser.open(download_url)
            dialog.destroy()

        ctk.CTkButton(
            btn_frame,
            text=i18n.get("update_now"),
            fg_color="green",
            command=update_now
        ).pack(side="left", padx=5)

        # Update Later (when closing app)
        def update_later():
            self.pending_update = {"url": download_url, "version": checker.latest_version}
            dialog.destroy()
            logger.info(f"Update scheduled for app close: {checker.latest_version}")

        ctk.CTkButton(
            btn_frame,
            text=i18n.get("update_later"),
            fg_color="#2B7A0B",
            command=update_later
        ).pack(side="left", padx=5)

        # Skip this version
        def skip_version():
            self._set_skipped_version(checker.latest_version)
            dialog.destroy()
            logger.info(f"User skipped version: {checker.latest_version}")

        ctk.CTkButton(
            btn_frame,
            text=i18n.get("skip_version"),
            fg_color="gray",
            command=skip_version
        ).pack(side="right", padx=5)

    def _get_installer_url(self, checker):
        """Get installer download URL."""
        for asset in checker.assets:
            name = asset.get("name", "")
            if "Setup" in name and name.endswith(".exe"):
                return asset.get("browser_download_url")
        return checker.release_url

    def _get_portable_url(self, checker):
        """Get portable download URL."""
        for asset in checker.assets:
            name = asset.get("name", "")
            if "windows" in name.lower() and name.endswith(".exe") and "Setup" not in name:
                return asset.get("browser_download_url")
        return checker.release_url

    # --- Security Logic ---

    def check_security_silently(self):
        threading.Thread(target=self._run_security_check, daemon=True).start()

    def _run_security_check(self):
        try:
            issues = SecurityChecker.check_vulnerabilities()
            if issues:
                self.after(0, lambda: self.show_security_alert(issues))
        except Exception as e:
            logger.error(f"Security check error: {e}")

    def show_security_alert(self, issues):
        """Display non-intrusive warning about vulnerable dependencies."""
        count = len(issues)
        logger.warning(f"Security check found {count} vulnerable packages.")

        # Create localized warning bar below banner (or row 2 if banner exists)
        row_idx = 2

        # Check if version banner exists (it would be at row 1)
        # We can just pack/grid into a new frame.
        # Let's verify grid config first: row 0 is tabview.
        # Version banner uses row 1.

        self.grid_rowconfigure(row_idx, weight=0)

        alert_frame = ctk.CTkFrame(self, fg_color="#F57C00", corner_radius=0)  # Orange
        alert_frame.grid(row=row_idx, column=0, sticky="ew")

        msg = f"🛡️ Security Notice: {count} installed component(s) have known vulnerabilities."

        label = ctk.CTkLabel(alert_frame, text=msg, text_color="white", font=ctk.CTkFont(weight="bold"))
        label.pack(side="left", padx=20, pady=5)

        view_btn = ctk.CTkButton(
            alert_frame,
            text="View Details",
            fg_color="white",
            text_color="#E65100",
            hover_color="#FFCC80",
            width=100,
            command=lambda: self.show_security_details(issues)
        )
        view_btn.pack(side="right", padx=20, pady=5)

    def show_security_details(self, issues):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Dependency Security Report")
        dialog.geometry("600x500")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Vulnerability Report", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)

        ctk.CTkLabel(
            dialog,
            text="The following Python libraries used by this internal tool have known vulnerabilities.\n"
                 "This does NOT mean your computer is compromised, but these libraries should be updated in a future release.",
            wraplength=550,
            justify="left"
        ).pack(pady=5, padx=20)

        scroll_frame = ctk.CTkScrollableFrame(dialog)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

        issue_body_lines = ["**Security Vulnerability Report**", "",
                            "The following vulnerable packages were detected:", ""]

        for issue in issues:
            card = ctk.CTkFrame(scroll_frame, fg_color=("gray85", "gray20"))
            card.pack(fill="x", pady=5)

            title = f"{issue['package']} {issue['version']} - {issue['id']}"
            issue_body_lines.append(f"- {title}: {issue['details_url']}")

            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))
            ctk.CTkLabel(
                card,
                text=issue['summary'],
                wraplength=500,
                text_color="gray").pack(
                anchor="w",
                padx=10,
                pady=(
                    0,
                    5))

            link_btn = ctk.CTkButton(
                card,
                text="Open OSV.dev Entry",
                height=24,
                fg_color="transparent",
                border_width=1,
                command=lambda url=issue['details_url']: webbrowser.open(url)
            )
            link_btn.pack(anchor="e", padx=10, pady=5)

        # Report Button
        ctk.CTkLabel(dialog, text="Please report this to the developer so dependencies can be updated.").pack(pady=5)

        def open_github_issue():
            import requests
            title = f"Security Vulnerability Report: {len(issues)} packages"
            body = "\n".join(issue_body_lines)
            url = f"https://github.com/FaserF/SwitchCraft/issues/new?title={requests.utils.quote(title)}&body={requests.utils.quote(body)}"
            webbrowser.open(url)
            dialog.destroy()

        ctk.CTkButton(
            dialog,
            text="Report Issue on GitHub",
            fg_color="green",
            command=open_github_issue
        ).pack(pady=10)

    def setup_analyzer_tab(self):
        from switchcraft.gui.views.analyzer_view import AnalyzerView
        self.analyzer_view = AnalyzerView(self.tab_analyzer, self.intune_service, self.ai_service, self)
        self.analyzer_view.pack(fill="both", expand=True)
        self.tab_analyzer.grid_rowconfigure(1, weight=1)

    # --- Helper Tab ---

    def setup_helper_tab(self):
        """
        Populate the Helper tab with the AI helper view if the AI addon is available, otherwise show a missing-addon placeholder.

        Attempts to load the AI addon's GUI view and instantiate it into the Helper tab when an AI service is present; if the addon view cannot be loaded or the AI service is not available, inserts a MissingAddonView describing the AI Assistant. Any initialization errors are logged.
        """
        try:
            # Check if AI addon is loaded
            if self.ai_service:
                from switchcraft.services.addon_service import AddonService
                addon_service = AddonService()
                ai_view_mod = addon_service.import_addon_module("ai", "gui.view")
                if ai_view_mod:
                    AIView = ai_view_mod.AIView
                    self.ai_view = AIView(self.tab_helper, self.ai_service)
                    self.ai_view.pack(fill="both", expand=True)
                    return

            # Fallback: Missing Addon View
            from switchcraft.gui.views.missing_addon_view import MissingAddonView
            MissingAddonView(self.tab_helper, self, "ai", "AI Assistant", i18n.get("ai_addon_desc")).pack(fill="both", expand=True)

        except Exception as e:
            logger.exception(f"Failed to setup AI Helper tab: {e}")

    # --- Settings Tab ---

    def setup_settings_tab(self):
        """Setup the Settings tab."""
        from switchcraft.gui.views.settings_view import SettingsView
        self.settings_view = SettingsView(
            self.tab_settings,
            self,
            self._run_update_check,
            self.intune_service,
            on_winget_toggle=self._toggle_winget_tab
        )
        self.settings_view.pack(fill="both", expand=True)




    def setup_intune_store_tab(self):
        from switchcraft.gui.views.intune_store_view import IntuneStoreView
        self.intune_store_view = IntuneStoreView(self.tab_intune_store)
        self.intune_store_view.pack(fill="both", expand=True)

    def setup_intune_tab(self):
        """Setup the dedicated Intune Utility tab."""
        from switchcraft.gui.views.intune_view import IntuneView
        from switchcraft.services.notification_service import NotificationService
        self.intune_view = IntuneView(self.tab_intune, self.intune_service, NotificationService())
        self.intune_view.pack(fill="both", expand=True)

    def setup_winget_tab(self):
        if self.winget_helper:
            from switchcraft.gui.views.winget_view import WingetView
            from switchcraft.services.notification_service import NotificationService
            self.winget_view = WingetView(self.tab_winget, self.winget_helper, self.intune_service, NotificationService())
            self.winget_view.pack(fill="both", expand=True)
        else:
            from switchcraft.gui.views.missing_addon_view import MissingAddonView
            MissingAddonView(self.tab_winget, self, "winget", "Winget Integration", i18n.get("winget_addon_desc")).pack(fill="both", expand=True)

    def setup_history_tab(self):
        from switchcraft.gui.views.history_view import HistoryView
        self.history_view = HistoryView(self.tab_history, self.history_service, self)
        self.history_view.pack(fill="both", expand=True)

    def start_analysis_tab(self, file_path):
        self.start_analysis(file_path)

    def show_intune_tab(self, setup_path, metadata=None):
        self.tabview.set("Intune Utility")
        self.intune_view.prefill_form(setup_path, metadata)


def main(splash_proc=None):
    """
    Start and run the SwitchCraft GUI application, optionally closing a provided splash process.

    If an uncaught exception occurs during startup or runtime, write a crash dump to the platform-appropriate Logs directory (or crash.log as a fallback), show a fatal error dialog to the user if possible, and exit with status 1.

    Parameters:
        splash_proc (optional): A subprocess-like object for the splash screen (must support terminate()). If provided, the function will attempt to terminate it after the main window is painted.
    """
    app = None
    try:
        # --- Auto-Enable Debug Console for Dev/Nightly Builds ---
        from switchcraft import __version__
        if "dev" in __version__.lower() or "nightly" in __version__.lower():
            # Force Debug Console ON for Dev/Nightly builds at startup for better troubleshooting.
            # This overrides user preference for the session but respects if user manually closes/disables it later.
            logger.info(f"Dev/Nightly build detected ({__version__}): Auto-enabling debug console for troubleshooting.")
            SwitchCraftConfig.set_user_preference("ShowDebugConsole", True)

        app = App()

        # Force one update to ensure main window is painted before killing splash
        app.update()

        if splash_proc:
            try:
                # Small delay to ensure smooth transition visually
                # time.sleep(0.1)
                splash_proc.terminate()
            except Exception:
                pass

        app.mainloop()
    except Exception as e:
        import traceback
        from datetime import datetime
        from pathlib import Path
        import os

        traceback.print_exc()

        # Write crash dump
        try:
            app_data = os.getenv('APPDATA')
            if app_data:
                dump_dir = Path(app_data) / "FaserF" / "SwitchCraft" / "Logs"
            else:
                dump_dir = Path.home() / ".switchcraft" / "Logs"
            dump_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dump_file = dump_dir / f"crash_dump_{timestamp}.txt"

            with open(dump_file, "w", encoding="utf-8") as f:
                f.write("SwitchCraft Legacy Crash Dump\n")
                f.write(f"Time: {datetime.now().isoformat()}\n")
                f.write(f"Python: {sys.version}\n")
                f.write(f"Platform: {sys.platform}\n")
                f.write("\n" + "="*60 + "\n")
                f.write("TRACEBACK:\n")
                f.write("="*60 + "\n\n")
                traceback.print_exception(type(e), e, e.__traceback__, file=f)

            error_msg = f"SwitchCraft crashed on startup:\n{str(e)}\n\nCrash dump saved to:\n{dump_file}\n\nSee console for details."
        except Exception:
            error_msg = f"SwitchCraft crashed on startup:\n{str(e)}\n\nSee console for details."

        try:
            from tkinter import messagebox, Tk
            # Attempt to create a root for messagebox if app failed
            root = Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error", error_msg)
            root.destroy()
        except Exception:
            pass

        # Also write to crash.log in current directory as fallback
        try:
            with open("crash.log", "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())
        except Exception:
            pass

        # Don't raise - we've shown the error to the user
        sys.exit(1)



if __name__ == "__main__":
    main()