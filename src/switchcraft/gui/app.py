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


from switchcraft.utils.i18n import i18n
from switchcraft.utils.updater import UpdateChecker
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.security import SecurityChecker
from switchcraft.services.notification_service import NotificationService
from switchcraft.services.addon_service import AddonService

from switchcraft.services.intune_service import IntuneService
from switchcraft.gui.views.intune_view import IntuneView
from switchcraft.gui.views.settings_view import SettingsView
# AIView imported dynamically if needed, or we keep it if it is just a view class (but moved to addon)
# Actually, AIView is in addon now, so we cannot import it unless we use AddonService or try/except
from switchcraft.gui.views.analyzer_view import AnalyzerView
from switchcraft.gui.views.winget_view import WingetView # Winget View depends on helper, verify usage
from switchcraft.gui.views.history_view import HistoryView
from switchcraft.services.history_service import HistoryService
from switchcraft import __version__
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
        if "--install-addons" in sys.argv:
            self.after(2000, self._check_addon_status)

        self.mainloop()
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title(i18n.get("app_title"))
        self.geometry("900x700")

        # Pending update info (for "Update Later" feature)
        self.pending_update = None

        # Load Assets
        self.logo_image = None
        self.load_assets()

        # Initialize Services early
        AddonService.register_addons()

        # 1. AI Addon
        self.ai_service = None
        try:
            ai_mod = AddonService.import_addon_module("ai", "service")
            if ai_mod:
                self.ai_service = ai_mod.SwitchCraftAI()
        except Exception as e:
            logger.info(f"AI Addon not loaded: {e}")

        # 2. Intune Service (Core or Addon? Currently Core/Universal stub, but let's keep as is)
        self.intune_service = IntuneService()
        self.history_service = HistoryService()

        # 3. Winget Addon
        self.winget_helper = None
        try:
            winget_mod = AddonService.import_addon_module("winget", "utils.winget")
            if winget_mod:
                self.winget_helper = winget_mod.WingetHelper()
        except Exception as e:
            logger.info(f"Winget Addon not loaded: {e}")

        # 4. Debug Addon (Just check presence, logic used in Settings)
        self.has_debug_addon = AddonService.is_addon_installed("debug")

        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.tab_analyzer = self.tabview.add(i18n.get("tab_analyzer"))

        # AI Helper tab (Always show)
        self.tab_helper = self.tabview.add(i18n.get("tab_helper"))
        self.setup_helper_tab()

        self.tab_settings = self.tabview.add(i18n.get("tab_settings"))

        # Initialize Tabs
        self.setup_analyzer_tab()
        if self.ai_service:
            self.setup_helper_tab()

        # Intune Utility Tab
        self.tab_intune = self.tabview.add("Intune Utility")
        self.setup_intune_tab()

        # Winget Tab (Always show, toggleable via settings but default ON/Persistent)
        # User requested: "Same for wingetstore tab" -> imply if missing, show missing view.
        if SwitchCraftConfig.get_value("EnableWinget", True):
            self.tab_winget = self.tabview.add("Winget Store")
            self.setup_winget_tab()

        self.tab_history = self.tabview.add("History")
        self.setup_history_tab()

        self.setup_settings_tab()

        # Setup Beta/Dev banner if pre-release
        self.setup_version_banner()


        # Handle window close for "Update Later" feature
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Demo / First Start Logic
        self.after(1000, self._run_demo_init)

        # Check for Addon (Virus Mitigation)
        self.after(4000, self._check_addon_status)

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
        """Check status. Auto-install for Dev builds silently. Prompt for others."""
        # 1. Check for Dev Build auto-install
        from switchcraft import __version__
        is_dev = "dev" in __version__.lower() or "beta" in __version__.lower()

        missing_any = not (AddonService.is_addon_installed("advanced") and AddonService.is_addon_installed("ai"))

        if is_dev and missing_any:
            logger.info("Dev build detected with missing addons. Auto-installing silently...")
            # Run in thread to not block UI
            threading.Thread(target=lambda: AddonService.install_addon("all"), daemon=True).start()
            return

        if not AddonService.is_addon_installed("advanced"):
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
                    if AddonService.install_addon("advanced"):
                        self.after(0, self._show_restart_countdown)
                    else:
                        self.after(0, lambda: messagebox.showerror("Error", i18n.get("addon_install_failed_manual")))

                threading.Thread(target=run_install, daemon=True).start()

    def _show_restart_countdown(self):
        from switchcraft.gui.components.countdown_dialog import CountdownDialog

        def do_restart():
            import sys
            import subprocess
            logger.info("Restarting application...")
            # Simple restart: Run executable again and exit
            try:
                subprocess.Popen([sys.executable] + sys.argv)
                sys.exit(0)
            except Exception as e:
                logger.error(f"Restart failed: {e}")
                messagebox.showerror("Error", "Could not restart automatically. Please restart manually.")

        CountdownDialog(
            self,
            "Restart Required",
            "Addon installed. Restarting automatically in:",
            timeout_seconds=5,
            on_timeout=do_restart
        )

    def _toggle_winget_tab(self, enabled):
        """Show or hide the Winget tab based on settings."""
        if enabled:
            if "Winget Store" not in self.tabview._tab_dict:
                # Re-add tab at the correct position (hard to force position, adds to end)
                # To keep order, we might need to recreate all... or just add it.
                # Adding to end is fine for now.
                self.tab_winget = self.tabview.add("Winget Store")
                self.setup_winget_tab()
        else:
            if "Winget Store" in self.tabview._tab_dict:
                self.tabview.delete("Winget Store")

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
                # src/switchcraft/gui/app.py -> root/images/
                base = Path(__file__).parent.parent.parent.parent
                logo_path = base / "images" / "switchcraft_logo.png"

            if logo_path.exists():
                pil_image = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(80, 80))

                # Set Window Icon (Taskbar/Titlebar)
                # Use iconphoto for PNG support
                from PIL import ImageTk
                icon_photo = ImageTk.PhotoImage(pil_image)
                self.iconphoto(True, icon_photo) # True applies to all future toplevels too

                # Fix Taskbar Grouping
                myappid = f"switchcraft.app.{__version__}"
                try:
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                except Exception:
                    pass
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
        self.analyzer_view = AnalyzerView(self.tab_analyzer, self.intune_service, self.ai_service, self)
        self.analyzer_view.pack(fill="both", expand=True)
        self.tab_analyzer.grid_rowconfigure(1, weight=1)

    # --- Helper Tab ---

    def setup_helper_tab(self):
        try:
            # Check if AI addon is loaded
            if self.ai_service:
                ai_view_mod = AddonService.import_addon_module("ai", "gui.view")
                if ai_view_mod:
                    AIView = ai_view_mod.AIView
                    self.ai_view = AIView(self.tab_helper, self.ai_service)
                    self.ai_view.pack(fill="both", expand=True)
                    return

            # Fallback: Missing Addon View
            from switchcraft.gui.views.missing_addon_view import MissingAddonView
            MissingAddonView(self.tab_helper, "ai", "AI Assistant", i18n.get("ai_addon_desc")).pack(fill="both", expand=True)

        except Exception as e:
            logger.exception(f"Failed to setup AI Helper tab: {e}")

    # --- Settings Tab ---

    def setup_settings_tab(self):
        """Setup the Settings tab."""
        self.settings_view = SettingsView(
            self.tab_settings,
            self._run_update_check,
            self.intune_service,
            on_winget_toggle=self._toggle_winget_tab
        )
        self.settings_view.pack(fill="both", expand=True)




    def setup_intune_tab(self):
        """Setup the dedicated Intune Utility tab."""
        self.intune_view = IntuneView(self.tab_intune, self.intune_service, NotificationService())
        self.intune_view.pack(fill="both", expand=True)

    def setup_winget_tab(self):
        if self.winget_helper:
            self.winget_view = WingetView(self.tab_winget, self.winget_helper, self.intune_service, NotificationService())
            self.winget_view.pack(fill="both", expand=True)
        else:
            from switchcraft.gui.views.missing_addon_view import MissingAddonView
            MissingAddonView(self.tab_winget, "winget", "Winget Integration", i18n.get("winget_addon_desc")).pack(fill="both", expand=True)

    def setup_history_tab(self):
        self.history_view = HistoryView(self.tab_history, self.history_service, self)
        self.history_view.pack(fill="both", expand=True)

    def start_analysis_tab(self, file_path):
        self.start_analysis(file_path)

    def show_intune_tab(self, setup_path, metadata=None):
        self.tabview.set("Intune Utility")
        self.intune_view.prefill_form(setup_path, metadata)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
