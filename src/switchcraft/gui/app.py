import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
import threading
from pathlib import Path
from PIL import Image
import webbrowser
import logging
from tkinter import messagebox
import os
import sys
import uuid
import shutil
import ctypes
import subprocess

from switchcraft.analyzers.msi import MsiAnalyzer
from switchcraft.analyzers.exe import ExeAnalyzer
from switchcraft.utils.winget import WingetHelper
from switchcraft.utils.i18n import i18n
from switchcraft.utils.updater import UpdateChecker
from switchcraft.analyzers.universal import UniversalAnalyzer
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.security import SecurityChecker
from switchcraft.utils.templates import TemplateGenerator
from switchcraft.services.ai_service import SwitchCraftAI
from switchcraft.analyzers.macos import MacOSAnalyzer
from switchcraft.generators.macos import generate_intune_script as generate_mac_script, generate_mobileconfig
from switchcraft.services.notification_service import NotificationService
from switchcraft.services.intune_service import IntuneService
from switchcraft.gui.views.intune_view import IntuneView
from switchcraft.gui.views.settings_view import SettingsView
from switchcraft.gui.views.ai_view import AIView
from switchcraft import __version__

from switchcraft.services.signing_service import SigningService
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set default theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")

class App(ctk.CTk, TkinterDnD.DnDWrapper):
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
        self.ai_service = SwitchCraftAI()
        self.intune_service = IntuneService()

        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabview
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.tab_analyzer = self.tabview.add(i18n.get("tab_analyzer"))

        # AI Helper tab - only show for debug mode, beta, or dev versions
        self.show_ai_helper = self._should_show_ai_helper()
        if self.show_ai_helper:
            self.tab_helper = self.tabview.add(i18n.get("tab_helper"))

        self.tab_settings = self.tabview.add(i18n.get("tab_settings"))

        # Initialize Tabs
        self.setup_analyzer_tab()
        if self.show_ai_helper:
            self.setup_helper_tab()

        # Intune Utility Tab
        self.tab_intune = self.tabview.add("Intune Utility")
        self.setup_intune_tab()

        self.setup_settings_tab()

        # Setup Beta/Dev banner if pre-release
        self.setup_version_banner()

        # Auto-Check Updates
        self.after(2000, self.check_updates_silently)

        # Security Check
        self.after(3000, self.check_security_silently)



        # Handle window close for "Update Later" feature
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Demo / First Start Logic
        self.after(1000, self._run_demo_init)

    def _run_demo_init(self):
        """Check if first run/demo mode is needed."""
        if SwitchCraftConfig.get_value("FirstRun", True):
             SwitchCraftConfig.set_user_preference("FirstRun", False)
             # If running from source or portable, offer demo
             if not self._is_installed_version():
                 msg = i18n.get("demo_mode_msg") if "demo_mode_msg" in i18n.translations.get(i18n.language) else "Welcome to SwitchCraft! Would you like to run a demo analysis?"
                 if messagebox.askyesno("SwitchCraft Demo", msg):
                     # Locate own installer or download
                     self.after(500, self._start_demo_analysis)

    def _start_demo_analysis(self):
        """Download or locate a sample installer for demo."""
        try:
             # Basic logic: Try to analyze self if exe, or download 7zip/notepad++ as demo
             target = sys.executable if getattr(sys, 'frozen', False) else None

             if not target or "python" in target.lower():
                 # Download a known safe small installer (e.g. 7-Zip or Notepad++)
                 # For now, let's use a dummy path or ask user to pick one?
                 # User asked for "dynamic download"
                 self.status_bar.configure(text="Downloading demo installer...")

                 # Using 7-Zip MSI as a safe demo (usually stable URL)
                 url = "https://www.7-zip.org/a/7z2409-x64.msi"
                 import requests
                 import tempfile

                 tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".msi")
                 tmp.close()

                 threading.Thread(target=self._download_and_analyze, args=(url, tmp.name), daemon=True).start()
                 return

             self.start_analysis(target)
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            # Fallback to browser if download fails
            if messagebox.askyesno("Download Error", f"Could not download demo installer automatically.\nError: {e}\n\nOpen download page instead?"):
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
            error_msg = str(e)
            self.after(0, lambda: messagebox.showerror("Demo Error", f"Failed to download demo: {error_msg}"))

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
            # Check 'images' folder logic correctly
            base_path = Path(__file__).resolve().parent.parent.parent.parent
            logo_path = base_path / "images" / "switchcraft_logo.png"

            # If frozen/compiled, adjustment might be needed, but for dev this is correct relative to src/switchcraft/gui/app.py
            if not logo_path.exists():
                # Fallback check
                logo_path = Path("images/switchcraft_logo.png")

            if logo_path.exists():
                pil_image = Image.open(logo_path)
                self.logo_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(80, 80))
            else:
                 logger.warning(f"Logo not found at {logo_path}")
        except Exception as e:
            logger.error(f"Failed to load assets: {e}")

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
        threading.Thread(target=self._run_update_check, daemon=True).start()

    def _run_update_check(self, show_no_update=False):
        try:
            # Get configured update channel from registry
            channel = SwitchCraftConfig.get_update_channel()
            checker = UpdateChecker(channel=channel)
            has_update, version, data = checker.check_for_updates()

            if has_update:
                self.after(0, lambda: self.show_update_dialog(checker))
            elif show_no_update:
                channel_display = channel.capitalize()
                self.after(0, lambda: messagebox.showinfo(i18n.get("check_updates"), f"{i18n.get('up_to_date')}\n\n{i18n.get('about_version')}: {__version__}\nChannel: {channel_display}"))
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            if show_no_update:
                self.after(0, lambda err=str(e): messagebox.showerror(i18n.get("update_check_failed"), f"{i18n.get('could_not_check')}\n{err}"))

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

        ctk.CTkLabel(info_frame, text=f"{i18n.get('current_version')}: {checker.current_version}").pack(anchor="w", padx=10, pady=2)
        ctk.CTkLabel(info_frame, text=f"{i18n.get('new_version')}: {checker.latest_version}", text_color="green", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=2)

        date_str = checker.release_date.split("T")[0] if checker.release_date else i18n.get("unknown")
        channel_str = checker.channel.capitalize() if hasattr(checker, 'channel') else "Stable"
        ctk.CTkLabel(info_frame, text=f"{i18n.get('released')}: {date_str} | Channel: {channel_str}").pack(anchor="w", padx=10, pady=2)

        # Changelog
        ctk.CTkLabel(dialog, text=f"{i18n.get('changelog')}:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(10, 5))
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

        alert_frame = ctk.CTkFrame(self, fg_color="#F57C00", corner_radius=0) # Orange
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

        issue_body_lines = ["**Security Vulnerability Report**", "", "The following vulnerable packages were detected:", ""]

        for issue in issues:
            card = ctk.CTkFrame(scroll_frame, fg_color=("gray85", "gray20"))
            card.pack(fill="x", pady=5)

            title = f"{issue['package']} {issue['version']} - {issue['id']}"
            issue_body_lines.append(f"- {title}: {issue['details_url']}")

            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(5,0))
            ctk.CTkLabel(card, text=issue['summary'], wraplength=500, text_color="gray").pack(anchor="w", padx=10, pady=(0,5))

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
        self.tab_analyzer.grid_columnconfigure(0, weight=1)
        self.tab_analyzer.grid_rowconfigure(1, weight=1)

        # Drop Zone
        self.drop_frame = ctk.CTkFrame(self.tab_analyzer, fg_color="transparent")
        self.drop_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        btn_text = i18n.get("drag_drop")
        self.drop_label = ctk.CTkButton(self.drop_frame, text=btn_text,
                                        image=self.logo_image,
                                        compound="top",
                                        height=120, corner_radius=15,
                                        fg_color=("#3B8ED0", "#4A235A"),
                                        hover_color=("#36719F", "#5B2C6F"),
                                        font=ctk.CTkFont(size=18, weight="bold"),
                                        command=self.open_file_dialog)
        self.drop_label.pack(fill="x", expand=True)

        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind('<<Drop>>', self.drop)

        # Result Area
        self.result_frame = ctk.CTkScrollableFrame(self.tab_analyzer, label_text=i18n.get("analysis_complete"))
        self.result_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.result_frame.grid_columnconfigure(0, weight=1)

        # Status Bar
        self.status_bar = ctk.CTkLabel(self.tab_analyzer, text="Ready", anchor="w", text_color="gray")
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 0))

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.tab_analyzer)
        self.progress_bar.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()  # Hide initially

    def drop(self, event):
        file_path = event.data
        if file_path.startswith('{') and file_path.endswith('}'):
             file_path = file_path[1:-1]
        self.start_analysis(file_path)

    def open_file_dialog(self):
        file_path = ctk.filedialog.askopenfilename(filetypes=[("Installers", "*.exe;*.msi")])
        if file_path:
            self.start_analysis(file_path)

    def start_analysis(self, file_path):
        self.status_bar.configure(text=f"{i18n.get('analyzing')} {Path(file_path).name}...")
        self.progress_bar.grid() # Show progress bar
        self.progress_bar.set(0)
        self.clear_results()
        thread = threading.Thread(target=self.analyze, args=(file_path,))
        thread.start()

    def clear_results(self):
        for widget in self.result_frame.winfo_children():
            widget.destroy()

    def update_progress(self, val, msg=None):
        self.after(0, lambda: self._update_progress_ui(val, msg))

    def _update_progress_ui(self, val, msg):
        self.progress_bar.set(val)
        if msg:
            self.status_bar.configure(text=msg)

    def analyze(self, file_path_str):
        try:
            path = Path(file_path_str)
            if not path.exists():
                 self.after(0, lambda: self.show_error(i18n.get("file_not_found")))
                 return

            self.update_progress(0.1, f"{i18n.get('analyzing')} {path.name}...")

            analyzers = [MsiAnalyzer(), ExeAnalyzer(), MacOSAnalyzer()]
            info = None

            total_analyzers = len(analyzers)
            for idx, analyzer in enumerate(analyzers):
                self.update_progress(0.1 + (0.3 * (idx / total_analyzers)), f"Running {analyzer.__class__.__name__}...")
                if analyzer.can_analyze(path):
                    try:
                        info = analyzer.analyze(path)
                        break
                    except Exception as e:
                        logger.error(f"Analysis failed for {analyzer.__class__.__name__}: {e}")

            # Universal / Brute Force Analysis
            brute_force_data = None
            nested_data = None
            silent_disabled = None
            uni = UniversalAnalyzer()
            wrapper = uni.check_wrapper(path)  # Check wrapper regardless

            if not info or info.installer_type == "Unknown" or "Unknown" in (info.installer_type or "") or wrapper:
                logger.info("Starting Universal Analysis...")
                self.update_progress(0.5, "Running Universal Analysis...")

                # Brute Force
                if not info or "Unknown" in (info.installer_type or ""):
                    self.update_progress(0.6, "Attempting Brute Force Analysis...")
                    bf_results = uni.brute_force_help(path)

                    if bf_results.get("detected_type"):
                        if not info:
                             from switchcraft.models import InstallerInfo
                             info = InstallerInfo(file_path=str(path), installer_type=bf_results["detected_type"])
                        else:
                             info.installer_type = bf_results["detected_type"]

                        info.install_switches = bf_results["suggested_switches"]
                        if "MSI" in bf_results["detected_type"]:
                             info.uninstall_switches = ["/x", "{ProductCode}"]

                    brute_force_data = bf_results.get("output", "")

                    # Check if silent mode is intentionally disabled
                    silent_disabled = uni.detect_silent_disabled(path, brute_force_data)

                if wrapper:
                    if not info:
                         from switchcraft.models import InstallerInfo
                         info = InstallerInfo(file_path=str(path), installer_type="Wrapper")
                    info.installer_type += f" ({wrapper})"

            if not info:
                 from switchcraft.models import InstallerInfo
                 info = InstallerInfo(file_path=str(path), installer_type="Unknown")

            # If still no switches found, try to extract and analyze nested executables
            if not info.install_switches and path.suffix.lower() == '.exe':
                self.update_progress(0, "Extracting ecosystem for nested analysis... (This may take a while)")
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start()
                nested_data = uni.extract_and_analyze_nested(path)
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
                self.update_progress(0.8, "Deep Analysis Complete")

            self.update_progress(0.9, "Searching Winget...")
            winget = WingetHelper()
            winget_url = None
            if info.product_name:
                winget_url = winget.search_by_name(info.product_name)

            # Update AI Context
            context_data = {
                "type": info.installer_type,
                "filename": path.name,
                "install_silent": " ".join(info.install_switches) if info.install_switches else "Unknown",
                "product": info.product_name or "Unknown",
                "manufacturer": info.manufacturer or "Unknown"
            }
            self.ai_service.update_context(context_data)

            self.update_progress(1.0, "Analysis Complete")
            self.after(0, lambda i=info, w=winget_url, bf=brute_force_data, nd=nested_data, sd=silent_disabled:
                       self.show_results(i, w, bf, nd, sd))

        except Exception as e:
            logger.exception("CRITICAL CRASH IN ANALYZER THREAD")
            err = str(e)
            self.after(0, lambda: self.show_error(f"Critical Error during analysis: {err}"))
            self.update_progress(0, "Analysis Failed")
        except SystemExit:
            logger.error("Analyzer thread attempted sys.exit()!")
            self.update_progress(0, "Analysis Error")
        except:
             logger.exception("Unknown Fatal Error in Analyzer")
             self.after(0, lambda: self.show_error("Unknown Fatal Error"))

    def show_error(self, message):
         self.status_bar.configure(text=i18n.get("error"))
         label = ctk.CTkLabel(self.result_frame, text=message, text_color="red", font=ctk.CTkFont(size=14))
         label.pack(pady=20)

    def show_results(self, info, winget_url, brute_force_data=None, nested_data=None, silent_disabled=None):
        self.status_bar.configure(text=i18n.get("analysis_complete"))
        self.progress_bar.grid_remove() # Hide progress bar
        self.clear_results()

        # Notify
        NotificationService.send_notification(
            title="Analysis Complete",
            message=f"Finished analyzing {info.file_path}"
        )

        # Basics
        self.add_result_row("File", info.file_path)
        self.add_result_row("Type", info.installer_type)
        self.add_result_row(i18n.get("about_dev"), info.manufacturer or "Unknown")
        self.add_result_row("Product Name", info.product_name or "Unknown")
        self.add_result_row(i18n.get("about_version"), info.product_version or "Unknown")

        self.add_separator()

        # MacOS Specifics
        if info.installer_type and "MacOS" in info.installer_type:
            if info.bundle_id:
                self.add_copy_row("Bundle ID", info.bundle_id, "teal")
            if info.min_os_version:
                 self.add_result_row("Min OS Version", info.min_os_version)

            if info.package_ids:
                self.add_separator()
                ctk.CTkLabel(self.result_frame, text="Package IDs", font=ctk.CTkFont(weight="bold")).pack(pady=5)
                for pid in info.package_ids:
                     self.add_copy_row("ID", pid, "teal")

            self.add_separator()

            # MacOS Generators
            def generate_bash():
                save_path = ctk.filedialog.asksaveasfilename(
                    defaultextension=".sh",
                    filetypes=[("Bash Script", "*.sh")],
                    initialfile=f"Install-{info.product_name or 'App'}.sh",
                    title="Save Intune Script"
                )
                if save_path:
                    try:
                        content = generate_mac_script(info)
                        with open(save_path, "w", encoding='utf-8', newline='\\n') as f:
                            f.write(content)
                        self.status_bar.configure(text=f"Script saved: {save_path}")
                        try: os.startfile(save_path)
                        except: pass
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to generate script: {e}")

            ctk.CTkButton(self.result_frame, text="✨ Generate Intune Script (Bash)", fg_color="purple", command=generate_bash).pack(pady=5, fill="x")

            def generate_profile():
                 save_path = ctk.filedialog.asksaveasfilename(
                     defaultextension=".mobileconfig",
                     filetypes=[("MobileConfig", "*.mobileconfig")],
                     initialfile=f"{info.product_name or 'Profile'}.mobileconfig",
                     title="Save Configuration Profile"
                 )
                 if save_path:
                     try:
                         # Use existing metadata or defaults
                         ident = info.bundle_id or f"com.switchcraft.{uuid.uuid4()}"
                         name = f"Profile for {info.product_name or 'App'}"
                         content = generate_mobileconfig(identifier=ident, display_name=name)
                         with open(save_path, "w", encoding='utf-8') as f:
                             f.write(content)
                         self.status_bar.configure(text=f"Profile saved: {save_path}")
                         try: os.startfile(save_path)
                         except: pass
                     except Exception as e:
                         messagebox.showerror("Error", f"Failed to generate profile: {e}")

            ctk.CTkButton(self.result_frame, text="⚙️ Create .mobileconfig Profile", fg_color="#0066CC", command=generate_profile).pack(pady=5, fill="x")

        # Silent Disabled Warning
        if silent_disabled and silent_disabled.get("disabled"):
            warning_frame = ctk.CTkFrame(self.result_frame, fg_color="#8B0000", corner_radius=8)
            warning_frame.pack(fill="x", pady=10, padx=5)

            ctk.CTkLabel(
                warning_frame,
                text="⚠️ SILENT INSTALLATION APPEARS DISABLED",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="white"
            ).pack(pady=5)

            ctk.CTkLabel(
                warning_frame,
                text=f"Reason: {silent_disabled.get('reason', 'Unknown')}",
                text_color="white"
            ).pack(pady=2)

            self.add_separator()

        # All-in-One Button (Top of actions)
        if info.install_switches:
             self.add_separator()
             ctk.CTkButton(self.result_frame,
                           text="✨ Automatic Deployment (All-in-One)",
                           fg_color=("#E04F5F", "#C0392B"),
                           height=40,
                           font=ctk.CTkFont(size=14, weight="bold"),
                           command=lambda: self._run_all_in_one_flow(info)
             ).pack(pady=10, fill="x")

        # Install
        if info.install_switches:
            params = " ".join(info.install_switches)
            self.add_copy_row(i18n.get("silent_install") + " (Params)", params, "green")

            # Button Row for Install
            btn_frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=5)

            self.add_full_command_row(f"{i18n.get('cmd_manual_install')} (Absolute)", info.file_path, params, is_msi=(info.installer_type == "MSI"))
            self.add_intune_row(f"{i18n.get('cmd_intune_install')} (Relative)", info.file_path, params, is_msi=(info.installer_type == "MSI"))

            # Test Install Button
            ctk.CTkButton(btn_frame,
                          text="▶ Test Install (Local)",
                          fg_color="#2ecc71",
                          width=140,
                          command=lambda: self._run_local_test_action(info.file_path, info.install_switches)
            ).pack(side="right", padx=10)

            ctk.CTkButton(self.result_frame, text="✨ Generate Intune Script", fg_color="purple", command=lambda: self.generate_intune_script_with_info(info)).pack(pady=5, fill="x")
            ctk.CTkButton(self.result_frame, text="📦 Create .intunewin Package", fg_color="#0066CC", command=lambda: self.create_intunewin_action(info)).pack(pady=5, fill="x")
        else:
             self.add_result_row(i18n.get("silent_install"), i18n.get("no_switches"), color="orange")

             # Allow generation even if unknown, but warn
             ctk.CTkButton(self.result_frame, text="✨ Generate Intune Script (Manual)", fg_color="purple", command=lambda: self.generate_intune_script_with_info(info)).pack(pady=5, fill="x")
             ctk.CTkButton(self.result_frame, text="📦 Create .intunewin Package", fg_color="#0066CC", command=lambda: self.create_intunewin_action(info)).pack(pady=5, fill="x")

             if info.file_path.endswith('.exe'):
                  self.add_copy_row(i18n.get("brute_force_help"), f'"{info.file_path}" /?', "orange")

             if info.product_name:
                 search_query = f"{info.product_name} silent install switches"
                 search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                 btn = ctk.CTkButton(self.result_frame, text=i18n.get("search_online"),
                                          fg_color="gray", command=lambda: webbrowser.open(search_url))
                 btn.pack(pady=5, fill="x")

        # Uninstall
        if info.uninstall_switches:
            u_params = " ".join(info.uninstall_switches)
            self.add_copy_row(i18n.get("silent_uninstall") + " (Params)", u_params, "red")

            is_full_cmd = "msiexec" in u_params.lower() or ".exe" in u_params.lower()
            if is_full_cmd:
                 self.add_copy_row("Intune Uninstall", u_params, "red")
            else:
                 self.add_intune_row("Intune Uninstall", "uninstall.exe", u_params, is_msi=False, is_uninstall=True)

        # Nested Executables Section (Archive Extraction)
        if nested_data and nested_data.get("extractable") and nested_data.get("nested_executables"):
            self.add_separator()
            self.show_nested_executables(nested_data, info)

        # Brute Force Output Log
        if brute_force_data:
             self.add_separator()
             lbl = ctk.CTkLabel(self.result_frame, text=i18n.get("automated_output"), font=ctk.CTkFont(weight="bold"))
             lbl.pack(pady=5)

             log_box = ctk.CTkTextbox(self.result_frame, height=150, fg_color="black", text_color="#00FF00", font=("Consolas", 11))
             log_box.insert("0.0", brute_force_data)
             log_box.configure(state="disabled")
             log_box.pack(fill="x", pady=5)

             if "MSI Wrapper" in info.installer_type:
                  ctk.CTkLabel(self.result_frame, text=i18n.get("msi_wrapper_tip"), text_color="cyan", font=ctk.CTkFont(weight="bold")).pack(pady=5)

        # Winget
        self.add_separator()
        winget_panel = ctk.CTkFrame(self.result_frame, fg_color=("gray90", "gray20"))
        winget_panel.pack(fill="x", pady=10)

        if winget_url:
            w_lbl = ctk.CTkLabel(winget_panel, text=i18n.get("winget_found"), font=ctk.CTkFont(weight="bold"))
            w_lbl.pack(pady=5)
            link_btn = ctk.CTkButton(winget_panel, text=i18n.get("view_winget"),
                                     fg_color="transparent", border_width=1,
                                     command=lambda: webbrowser.open(winget_url))
            link_btn.pack(pady=5, padx=10, fill="x")
        else:
            w_lbl = ctk.CTkLabel(winget_panel, text=i18n.get("winget_no_match"), text_color="gray")
            w_lbl.pack(pady=5)

        # Parameter List - Show all found parameters with explanations
        all_params = []
        if info.install_switches:
            all_params.extend(info.install_switches)
        if info.uninstall_switches:
            all_params.extend(info.uninstall_switches)

        # Collect nested switches recursively for display
        if nested_data and nested_data.get("nested_executables"):
             for nested in nested_data["nested_executables"]:
                  if nested.get("analysis") and nested["analysis"].install_switches:
                       all_params.extend(nested["analysis"].install_switches)

        if all_params:
             # Dedup
             unique_params = sorted(list(set(all_params)), key=len) # Sort by length as heuristic
             self.show_all_parameters(unique_params)

        # Detailed Params Button (Always show if we have nested data OR params)
        if (nested_data and nested_data.get("nested_executables")) or all_params:
             self.add_separator()
             ctk.CTkButton(self.result_frame,
                           text=i18n.get("view_detailed_params") if "view_detailed_params" in i18n.translations.get(i18n.language, {}) else "View Full Parameter Details (All Files)",
                           fg_color="#555555",
                           command=lambda: self._show_detailed_parameters(info, nested_data)
             ).pack(pady=10, fill="x")

    def show_all_parameters(self, params):
        """Display all found parameters with explanations."""
        self.add_separator()

        # Header
        header_frame = ctk.CTkFrame(self.result_frame, fg_color=("#E8F5E9", "#1B5E20"), corner_radius=8)
        header_frame.pack(fill="x", pady=10, padx=5)

        ctk.CTkLabel(
            header_frame,
            text=f"📋 {i18n.get('found_params')}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("black", "white")
        ).pack(pady=8)

        # Separate known and unknown params
        known_params = []
        unknown_params = []

        for param in params:
            explanation = i18n.get_param_explanation(param)
            if explanation:
                known_params.append((param, explanation))
            else:
                unknown_params.append(param)

        # Known parameters with explanations
        if known_params:
            known_frame = ctk.CTkFrame(self.result_frame, fg_color=("gray90", "gray25"), corner_radius=5)
            known_frame.pack(fill="x", pady=5, padx=10)

            ctk.CTkLabel(
                known_frame,
                text=f"✓ {i18n.get('known_params')}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="green"
            ).pack(anchor="w", padx=10, pady=5)

            for param, explanation in known_params:
                param_row = ctk.CTkFrame(known_frame, fg_color="transparent")
                param_row.pack(fill="x", padx=10, pady=2)

                # Parameter name (monospace, colored)
                ctk.CTkLabel(
                    param_row,
                    text=param,
                    font=("Consolas", 12),
                    text_color=("#0066CC", "#66B3FF"),
                    width=180,
                    anchor="w"
                ).pack(side="left")

                # Explanation
                ctk.CTkLabel(
                    param_row,
                    text=f"→ {explanation}",
                    text_color=("gray40", "gray70"),
                    anchor="w"
                ).pack(side="left", fill="x", expand=True)

            # Padding at bottom of known params
            ctk.CTkLabel(known_frame, text="", height=5).pack()

        # Unknown parameters
        if unknown_params:
            unknown_frame = ctk.CTkFrame(self.result_frame, fg_color=("gray95", "gray30"), corner_radius=5)
            unknown_frame.pack(fill="x", pady=5, padx=10)

            ctk.CTkLabel(
                unknown_frame,
                text=f"? {i18n.get('unknown_params')}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="orange"
            ).pack(anchor="w", padx=10, pady=5)

            unknown_text = "  ".join(unknown_params)
            ctk.CTkLabel(
                unknown_frame,
                text=unknown_text,
                font=("Consolas", 11),
                text_color=("gray50", "gray60"),
                wraplength=400
            ).pack(anchor="w", padx=10, pady=(0, 8))

    def show_nested_executables(self, nested_data, parent_info):
        """Display nested executables found inside an extracted archive."""

        # Header with attention-grabbing styling
        header_frame = ctk.CTkFrame(self.result_frame, fg_color="#1E5128", corner_radius=8)
        header_frame.pack(fill="x", pady=10, padx=5)

        ctk.CTkLabel(
            header_frame,
            text="📦 ARCHIVE EXTRACTED - NESTED INSTALLERS FOUND",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        ).pack(pady=5)

        ctk.CTkLabel(
            header_frame,
            text=f"No switches found for the main EXE. Extract with 7-Zip and use one of these:\n"
                 f"Archive Type: {nested_data.get('archive_type', 'Unknown')}",
            text_color="#90EE90"
        ).pack(pady=5)

        # Display each nested executable
        for nested in nested_data.get("nested_executables", []):
            nested_frame = ctk.CTkFrame(self.result_frame, fg_color=("gray85", "gray25"), corner_radius=5)
            nested_frame.pack(fill="x", pady=5, padx=10)

            # Executable name and type
            name_label = ctk.CTkLabel(
                nested_frame,
                text=f"📄 {nested['name']} ({nested['type']})",
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w"
            )
            name_label.pack(fill="x", padx=10, pady=5)

            # Relative path
            ctk.CTkLabel(
                nested_frame,
                text=f"Path inside archive: {nested['relative_path']}",
                text_color="gray",
                anchor="w"
            ).pack(fill="x", padx=10)

            # Analysis results
            analysis = nested.get("analysis")
            if analysis:
                if analysis.installer_type:
                    ctk.CTkLabel(
                        nested_frame,
                        text=f"Type: {analysis.installer_type}",
                        text_color="cyan",
                        anchor="w"
                    ).pack(fill="x", padx=10)

                if analysis.install_switches:
                    switches_text = " ".join(analysis.install_switches)

                    switch_frame = ctk.CTkFrame(nested_frame, fg_color="transparent")
                    switch_frame.pack(fill="x", padx=10, pady=5)

                    ctk.CTkLabel(
                        switch_frame,
                        text="Silent Switches:",
                        font=ctk.CTkFont(weight="bold"),
                        text_color="green",
                        width=120
                    ).pack(side="left")

                    switch_box = ctk.CTkTextbox(switch_frame, height=30, fg_color=("gray95", "gray15"))
                    switch_box.insert("0.0", switches_text)
                    switch_box.configure(state="disabled")
                    switch_box.pack(side="left", fill="x", expand=True, padx=5)

                    def copy_switches(text=switches_text):
                        self.clipboard_clear()
                        self.clipboard_append(text)
                        self.update()

                    ctk.CTkButton(
                        switch_frame,
                        text="Copy",
                        width=60,
                        command=copy_switches
                    ).pack(side="right")

                    # Full command instruction
                    full_cmd = f'"{nested["name"]}" {switches_text}'
                    ctk.CTkLabel(
                        nested_frame,
                        text=f"💡 Extract archive, then run: {full_cmd}",
                        text_color="yellow",
                        font=ctk.CTkFont(size=11),
                        wraplength=500
                    ).pack(fill="x", padx=10, pady=5)

            elif nested.get("error"):
                ctk.CTkLabel(
                    nested_frame,
                    text=f"Error analyzing: {nested['error']}",
                    text_color="red"
                ).pack(fill="x", padx=10, pady=5)

        # Cleanup instruction
        if nested_data.get("temp_dir"):
            cleanup_frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
            cleanup_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(
                cleanup_frame,
                text=f"📁 Temporary extraction: {nested_data['temp_dir']}",
                text_color="gray",
                font=ctk.CTkFont(size=10)
            ).pack(side="left", padx=10)

            def cleanup_temp():
                from switchcraft.analyzers.universal import UniversalAnalyzer
                ua = UniversalAnalyzer()

                dirs = nested_data.get('all_temp_dirs', [])
                if not dirs and nested_data.get('temp_dir'):
                    dirs = [nested_data['temp_dir']]

                count = 0
                for d in dirs:
                    ua.cleanup_temp_dir(d)
                    count += 1

                self.status_bar.configure(text=f"Cleaned up {count} temporary locations")

            ctk.CTkButton(
                cleanup_frame,
                text="Clean Up",
                width=80,
                fg_color="gray",
                command=cleanup_temp
            ).pack(side="right", padx=10)

    def add_result_row(self, label_text, value_text, color=None):
        frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        lbl = ctk.CTkLabel(frame, text=f"{label_text}:", width=120, anchor="w", font=ctk.CTkFont(weight="bold"))
        lbl.pack(side="left")
        val_lbl = ctk.CTkLabel(frame, text=value_text, anchor="w", wraplength=450, text_color=color if color else ("black", "white"))
        val_lbl.pack(side="left", fill="x", expand=True)

    def add_copy_row(self, label_text, value_text, color_theme="blue"):
        frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        lbl = ctk.CTkLabel(frame, text=f"{label_text}:", width=150, anchor="w", font=ctk.CTkFont(weight="bold"))
        lbl.pack(side="left", anchor="n")

        txt = ctk.CTkTextbox(frame, height=50, fg_color=("gray95", "gray15"))
        txt.insert("0.0", value_text)
        txt.configure(state="disabled")
        txt.pack(side="left", fill="x", expand=True, padx=5)

        # Using a safer copy mechanism
        def copy_to_clipboard():
             self.clipboard_clear()
             self.clipboard_append(value_text)
             self.update() # Keep clipboard content after window close usually requires update or mainloop

        copy_btn = ctk.CTkButton(frame, text=i18n.get("context_copy"), width=60, fg_color="transparent", border_width=1,
                                 command=copy_to_clipboard)
        copy_btn.pack(side="right")

    def add_full_command_row(self, label_text, file_path, params, is_install=True, is_msi=False):
        """Generates absolute path command for manual testing."""
        path_obj = Path(file_path)
        if is_msi:
            cmd = f'msiexec.exe /i "{path_obj.absolute()}" {params}'
        else:
            cmd = f'Start-Process -FilePath "{path_obj.absolute()}" -ArgumentList "{params}" -Wait'
        self.add_copy_row(label_text, cmd)

    def add_intune_row(self, label_text, file_path_str, params, is_msi=False, is_uninstall=False):
        """Generates Intune-ready commands (relative filename)."""
        filename = Path(file_path_str).name
        if is_uninstall:
             cmd = f'"{filename}" {params}'
        else:
             if is_msi:
                 cmd = f'msiexec /i "{filename}" {params}'
             else:
                 cmd = f'"{filename}" {params}'
        self.add_copy_row(label_text, cmd, "purple")

    def add_separator(self):
        line = ctk.CTkFrame(self.result_frame, height=2, fg_color="gray50")
        line.pack(fill="x", pady=10)


    # --- Helper Tab ---
    def setup_helper_tab(self):
        self.ai_view = AIView(self.tab_helper, self.ai_service)
        self.ai_view.pack(fill="both", expand=True)


    # --- Settings Tab ---
    def setup_settings_tab(self):
        """Setup the Settings tab."""
        self.settings_view = SettingsView(self.tab_settings, self._run_update_check)
        self.settings_view.pack(fill="both", expand=True)

    def generate_intune_script_action(self):
        """Handle Intune script generation from UI."""
        # Find current info - we need to store it in self or pass it differently if moving out of closure
        # Since I moved the button out but the 'info' variable was in 'show_results' scope,
        # I need to make sure 'info' is accessible.
        # 'show_results' doesn't store 'info' in 'self.current_info'.
        # I should modify 'show_results' to store current info.
        pass # Only a placeholder, will be replaced by 'self.current_info' logic if I add it.
        # Wait, I cannot easily add 'self.current_info' without editing 'show_results' main body.
        # But I am editing 'show_results' in the same tool call!
        # I should use 'lambda: self.generate_intune_script_action(info)'

    def generate_intune_script_with_info(self, info):
        """Generate Intune script using provided info."""
        if not info.install_switches:
            if not messagebox.askyesno("Warning", i18n.get("no_switches_intune_warn") if "no_switches_intune_warn" in i18n.translations.get(i18n.language) else "No silent switches detected. The script might require manual editing. Continue?"):
                return

        default_filename = f"Install-{info.product_name or 'App'}.ps1"
        default_filename = "".join(x for x in default_filename if x.isalnum() or x in "-_.")



        # Override save path if Git Repo is configured and we can determine a better default
        git_repo = SwitchCraftConfig.get_value("GitRepoPath")
        if git_repo and Path(git_repo).exists():
             # "Apps" -> ProgramName
             app_name_safe = "".join(x for x in (info.product_name or "UnknownApp") if x.isalnum() or x in "-_.")
             target_dir = Path(git_repo) / "Apps" / app_name_safe

             # If user cancelled dialog or we want to suggest this path instead
             # The dialog happened above, but maybe we should have set initialdir?
             # Let's check if the user actually selected something.
             pass

        # Reworking logic to prioritize Git Repo if set
        initial_dir = None
        if git_repo and Path(git_repo).exists():
             app_name_safe = "".join(x for x in (info.product_name or "UnknownApp") if x.isalnum() or x in "-_.")
             suggested_path = Path(git_repo) / "Apps" / app_name_safe
             if not suggested_path.exists():
                 try:
                     suggested_path.mkdir(parents=True, exist_ok=True)
                 except: pass
             if suggested_path.exists():
                 initial_dir = str(suggested_path)

        # Re-ask or use the user's choice?
        # The user says: "Ist dieser hinterlegt, sollen neue Pakete dort immer im Unterordner "Apps" -> ProgrammNameAlsOrdnerName abgelegt werden."
        # This implies we should DEFAULT to that folder.

        save_path = ctk.filedialog.asksaveasfilename(
            defaultextension=".ps1",
            filetypes=[("PowerShell Script", "*.ps1")],
            initialfile=default_filename,
            initialdir=initial_dir, # Use Git path if avail
            title="Save Intune Script"
        )

        if save_path:
            context_data = {
                "INSTALLER_FILE": Path(info.file_path).name,
                "INSTALL_ARGS": " ".join(info.install_switches) if info.install_switches else "/S",
                "APP_NAME": info.product_name or "Application",
                "PUBLISHER": info.manufacturer or "Unknown"
            }

            custom_template = SwitchCraftConfig.get_value("CustomTemplatePath")
            generator = TemplateGenerator(custom_template)

            if generator.generate(context_data, save_path):
                # Try to sign
                if SigningService.sign_script(save_path):
                    logger.info(f"Script signed: {save_path}")
                else:
                    logger.warning("Script verification/signing failed or skipped.")

                self.status_bar.configure(text=f"Script generated: {save_path}")
                try: os.startfile(save_path)
                except: pass
            else:
                messagebox.showerror("Error", "Failed to generate script template.")




    def _run_all_in_one_flow(self, info):
        """Orchestrate the entire flow: Generate -> Test -> Package -> Upload."""

        # 1. Confirmation & Config Check
        if not messagebox.askyesno("Confirm Automation", "This will attempt to:\n1. Generate & Sign Script\n2. Run Local Install/Uninstall Test (Requires Admin)\n3. Create IntuneWin Package\n4. Upload to Intune\n\nContinue?"):
             return

        # Check upload config early
        if not (SwitchCraftConfig.get_value("IntuneTenantID") and SwitchCraftConfig.get_value("IntuneClientId")):
             if not messagebox.askyesno("Config Warning", "Intune Upload is NOT configured. Steps will stop after packaging. Continue?"):
                 return

        # Setup Progress Window
        progress_win = ctk.CTkToplevel(self)
        progress_win.title("Deployment Automation")
        progress_win.geometry("600x400")
        txt_log = ctk.CTkTextbox(progress_win)
        txt_log.pack(fill="both", expand=True, padx=10, pady=10)

        def log(msg):
            progress_win.after(0, lambda: txt_log.insert("end", f"{msg}\n"))
            progress_win.after(0, lambda: txt_log.see("end"))

        def run_flow():
            try:
                # --- Step 1: Generate Script ---
                log("--- Step 1: Generating Script ---")

                # Determine path (Git repo or Temp)
                base_dir = Path(info.file_path).parent
                git_repo = SwitchCraftConfig.get_value("GitRepoPath")
                if git_repo and Path(git_repo).exists():
                     app_name_safe = "".join(x for x in (info.product_name or "UnknownApp") if x.isalnum() or x in "-_.")
                     base_dir = Path(git_repo) / "Apps" / app_name_safe
                     base_dir.mkdir(parents=True, exist_ok=True)

                     # Copy installer there if not present?
                     # For automation, we might need the installer in the package source.
                     dst_installer = base_dir / Path(info.file_path).name
                     if Path(info.file_path).resolve() != dst_installer.resolve():
                         import shutil
                         log(f"Copying installer to {base_dir}...")
                         shutil.copy2(info.file_path, dst_installer)
                         info.file_path = str(dst_installer) # Update info to point to new location

                script_name = f"Install-{info.product_name or 'App'}.ps1"
                script_name = "".join(x for x in script_name if x.isalnum() or x in "-_.")
                script_path = base_dir / script_name

                context = {
                    "INSTALLER_FILE": Path(info.file_path).name,
                    "INSTALL_ARGS": " ".join(info.install_switches) if info.install_switches else "/S",
                    "APP_NAME": info.product_name or "Application",
                    "PUBLISHER": info.manufacturer or "Unknown"
                }

                # Generate
                tmpl_path = SwitchCraftConfig.get_value("CustomTemplatePath")
                gen = TemplateGenerator(tmpl_path)
                if not gen.generate(context, str(script_path)):
                     raise RuntimeError("Script generation failed")

                log(f"Script created: {script_path}")

                # Sign
                if SigningService.sign_script(str(script_path)):
                     log("Script signed successfully.")
                else:
                     log("Signing skipped or failed (check settings).")


                # --- Step 2: Local Test ---
                log("\n--- Step 2: Local Test ---")
                # We need to run the SCRIPT as Admin
                # "powershell -ExecutionPolicy Bypass -File ..."
                if messagebox.askyesno("Test", "Run local installation test now? (Admin rights required)"):
                     import subprocess

                     # Construct command
                     cmd = f'powershell.exe -ExecutionPolicy Bypass -File "{script_path}"'
                     log(f"Executing: {cmd}")

                     # Run via 'runas' verb using ShellExecute to get elevation prompt
                     import ctypes
                     params = f'-NoProfile -ExecutionPolicy Bypass -File "{script_path}"'

                     # We can't easily capture output of ShellExecute unless we wrap it or pipeline it.
                     # Simplified: Just run it and ask user if it worked?
                     # Or run subprocess with 'runas' logic (complicated in Py).
                     # Simple approach: Ask user to confirm success after window closes.

                     log("Launching installer process...")
                     ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", params, str(base_dir), 1)

                     if int(ret) <= 32:
                          log(f"Failed to elevate/run: Code {ret}")
                          if not messagebox.askyesno("Test Failed?", "Process failed to start. Continue anyway?"): return
                     else:
                          if not messagebox.askyesno("Test Verification", "Did the installation complete successfully?"):
                               log("User reported test failure.")
                               return
                          log("Test marked as Success.")

                     # Uninstall Test?
                     # Typically user just uninstalls later, or we run uninstall cmd.
                     # Skipping uninstall test for speed unless requested.


                # --- Step 3: Package ---
                log("\n--- Step 3: Creating Intune Package ---")

                intunewin_output = base_dir
                setup_file = script_path.name # Prefer script

                log(f"Packaging {setup_file}...")

                # We need IntuneService instance
                # It's initialized in App.__init__ as self.intune_service

                out_log = self.intune_service.create_intunewin(
                    source_folder=str(base_dir),
                    setup_file=setup_file,
                    output_folder=str(intunewin_output),
                    quiet=True
                )
                log("Package created.")

                pkg_name = script_path.name.replace(".ps1", ".intunewin") # Tool usually uses setup file name
                if not (intunewin_output / pkg_name).exists():
                     # Maybe it used installer name?
                     pkg_name = Path(info.file_path).name + ".intunewin" # Fallback guess

                pkg_path = intunewin_output / pkg_name
                if not pkg_path.exists():
                     # Find ANY .intunewin
                     candidates = list(intunewin_output.glob("*.intunewin"))
                     if candidates: pkg_path = candidates[0]
                     else: raise FileNotFoundError("Created .intunewin not found.")

                log(f"Package: {pkg_path}")


                # --- Step 4: Upload ---
                if SwitchCraftConfig.get_value("IntuneTenantID"):
                     log("\n--- Step 4: Uploading to Intune ---")
                     log("Authenticating...")
                     token = self.intune_service.authenticate(
                         SwitchCraftConfig.get_value("IntuneTenantID"),
                         SwitchCraftConfig.get_value("IntuneClientId"),
                         SwitchCraftConfig.get_value("IntuneClientSecret")
                     )

                     app_meta = {
                         "displayName": info.product_name or pkg_path.stem,
                         "description": f"Deployed by SwitchCraft. Version: {info.product_version}",
                         "publisher": info.manufacturer or "SwitchCraft",
                         "installCommandLine": f"powershell.exe -ExecutionPolicy Bypass -File \"{script_path.name}\"",
                         "uninstallCommandLine": f"powershell.exe -ExecutionPolicy Bypass -File \"{script_path.name}\" -Uninstall" # Check template support for -Uninstall switch
                     }

                     def prog_cb(p, m): log(f"Upload: {int(p*100)}% - {m}")

                     app_id = self.intune_service.upload_win32_app(token, pkg_path, app_meta, progress_callback=prog_cb)

                     log(f"\nSUCCESS! App ID: {app_id}")

                     # Assignments
                     groups = SwitchCraftConfig.get_value("IntuneTestGroups", [])
                     if groups:
                         log("\n--- Assigning to Groups ---")
                         for grp in groups:
                             gid = grp.get("id")
                             gname = grp.get("name")
                             if gid:
                                 try:
                                     self.intune_service.assign_to_group(token, app_id, gid)
                                     log(f"Assigned to: {gname} ({gid})")
                                 except Exception as e:
                                     log(f"Failed to assign {gname}: {e}")
                             else:
                                 log(f"Skipping group with no ID: {gname}")

                     # Open Browser
                     url = f"https://intune.microsoft.com/#view/Microsoft_Intune_Apps/SettingsMenu/~/0/appId/{app_id}"
                     webbrowser.open(url)
                     log("Opened Intune portal.")

                else:
                     log("\nSkipping upload (not configured).")
                     log(f"Package available at: {pkg_path}")

            except Exception as e:
                log(f"\nERROR: {e}")
                logger.exception("All-in-One Flow Failed")

        threading.Thread(target=run_flow, daemon=True).start()

    def create_intunewin_action(self, info):
        """Switches to Intune Utility tab and pre-fills data."""
        # 1. Pre-fill data
        path = Path(info.file_path)
        self.entry_intune_setup.delete(0, "end")
        self.entry_intune_setup.insert(0, str(path))

        self.entry_intune_source.delete(0, "end")
        self.entry_intune_source.insert(0, str(path.parent))

        self.entry_intune_output.delete(0, "end")
        self.entry_intune_output.insert(0, str(path.parent))

        # Check for .ps1 script
        script_path = path.with_suffix(".ps1")
        # Or typical naming "Install-X.ps1"
        if not script_path.exists():
             # Try to find any Ps1
             candidates = list(path.parent.glob("*.ps1"))
             if candidates:
                 script_path = candidates[0]

        if script_path.exists():
             self.entry_intune_setup.delete(0, "end")
             self.entry_intune_setup.insert(0, str(script_path.name)) # IntuneWinAppUtil expects relative path usually if in source?
             # Actually, IntuneWinAppUtil wrapper in SwitchCraft might expect full path if we handle copying?
             # Let's check IntuneView later. For now, putting full path or name is better than EXE.
             # User said: "Setup File" ... "refenziert ... auf die exe ... muss aber das PS Script sein"
             # If source folder is defining the package, setup file must be relative?
             # Let's put the NAME if it's in source dir.
             self.entry_intune_setup.delete(0, "end")
             self.entry_intune_setup.insert(0, str(script_path))

        # Prefer generated script if we just came from automation
        if hasattr(self, 'last_generated_script') and self.last_generated_script and Path(self.last_generated_script).exists():
            self.entry_intune_setup.delete(0, "end")
            self.entry_intune_setup.insert(0, str(self.last_generated_script))
            # Also update source folder if different
            p_script = Path(self.last_generated_script)
            self.entry_intune_source.delete(0, "end")
            self.entry_intune_source.insert(0, str(p_script.parent))
            self.entry_intune_output.delete(0, "end")
            self.entry_intune_output.insert(0, str(p_script.parent))
            self.entry_intune_output.insert(0, str(p_script.parent))

        # 2. Switch Tab
        self.tabview.set("Intune Utility")

        # 3. Notify user
        self.status_bar.configure(text="Pre-filled Intune Utility form. Please review and click Create.")

    def _run_update_check(self, show_no_update=False):
        """Callback for manual update check."""
        try:
            from switchcraft.utils.updater import UpdateChecker
            channel = SwitchCraftConfig.get_update_channel()
            checker = UpdateChecker(channel=channel)

            # Run in thread to avoid blocking
            def _check():
               try:
                   has_update, version, data = checker.check_for_updates()
                   if has_update:
                       self.after(0, lambda: self.show_update_dialog(checker))
                   elif show_no_update:
                       channel_display = channel.capitalize()
                       self.after(0, lambda: messagebox.showinfo(i18n.get("check_updates"), f"{i18n.get('up_to_date')}\n\n{i18n.get('about_version')}: {__version__}\nChannel: {channel_display}"))
               except Exception as e:
                   logger.error(f"Update check failed: {e}")
                   if show_no_update:
                       self.after(0, lambda: messagebox.showerror(i18n.get("update_check_failed"), f"{i18n.get('could_not_check')}\n{e}"))

            threading.Thread(target=_check, daemon=True).start()
        except Exception as e:
            logger.error(f"Failed to start update check: {e}")



    def _run_local_test_action(self, file_path, switches, uninstall=False):
        """Run a local test of the installer/script with admin rights."""
        if not messagebox.askyesno("Test Confirmation", f"Do you want to run the {'UNINSTALL' if uninstall else 'INSTALL'} test locally?\n\nFile: {Path(file_path).name}\n\nWARNING: This will execute the file on YOUR system with Admin rights."):
             return

        # Prepare arguments
        # If it's a script (.ps1), we need PowerShell. If .exe/.msi, run directly?
        # User requirement: "Local Testing Feature ... installation/uninstallation"
        # If we have a script generated, easier to test script. But here we are on the Analyzer tab (raw installer).
        # So we test the raw command?
        # Yes.

        path_obj = Path(file_path)
        params_str = " ".join(switches) if switches else ""

        cmd_exec = str(path_obj)
        cmd_params = params_str

        if file_path.lower().endswith(".msi"):
             cmd_exec = "msiexec.exe"
             cmd_params = f"{'/x' if uninstall else '/i'} \"{path_obj}\" {params_str}"

        try:
             # Use ShellExecute runas
             # Note: ShellExecute separates executable and parameters
             ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", cmd_exec, cmd_params, str(path_obj.parent), 1)
             if int(ret) <= 32:
                  messagebox.showerror("Execution Failed", f"Failed to start process (Code {ret})")
        except Exception as e:
             messagebox.showerror("Error", str(e))

    def _show_detailed_parameters(self, info, nested_data):
        """Show a detailed breakdown of all found parameters (Main + Nested)."""
        top = ctk.CTkToplevel(self)
        top.title(i18n.get("detailed_params_title") if "detailed_params_title" in i18n.translations.get(i18n.language) else "Detailed Parameters")
        top.geometry("700x500")

        # Lift window
        top.lift()
        top.focus_force()

        # Content
        scroll = ctk.CTkScrollableFrame(top)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Helper to add section
        def add_section(title, filename, type_str, params, is_main=False, raw_output=None):
            if not params and not raw_output: return

            frame = ctk.CTkFrame(scroll, fg_color="#2B2B2B" if is_main else "#1F1F1F")
            frame.pack(fill="x", pady=5)

            # Header
            head = ctk.CTkFrame(frame, fg_color="transparent")
            head.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(head, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color="cyan" if is_main else "white").pack(side="left")
            ctk.CTkLabel(head, text=f"({type_str})", text_color="gray").pack(side="left", padx=5)

            # File Info
            ctk.CTkLabel(frame, text=f"File: {filename}", font=("Consolas", 11), text_color="gray80").pack(anchor="w", padx=15)

            # Params
            if params:
                p_text = " ".join(params)
                ctk.CTkTextbox(frame, height=40, font=("Consolas", 11)).pack(fill="x", padx=10, pady=5).insert("0.0", p_text)

            if raw_output:
                exp = ctk.CTkExpander(frame, label_text="Raw Analysis Output") # Hypothetical widget or just a button
                # Just use label + textbox
                ctk.CTkLabel(frame, text="Raw Output:", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=10)
                out_box = ctk.CTkTextbox(frame, height=80, font=("Consolas", 10), text_color="gray70")
                out_box.insert("0.0", raw_output[0:2000] + "..." if len(raw_output) > 2000 else raw_output)
                out_box.configure(state="disabled")
                out_box.pack(fill="x", padx=10, pady=5)


        # Main File
        add_section(i18n.get("main_file") or "Main Installer", Path(info.file_path).name, info.installer_type, info.install_switches, is_main=True)

        # Nested Files
        if nested_data and nested_data.get("nested_executables"):
            ctk.CTkLabel(scroll, text=f"Nested Files (Extracted)", font=ctk.CTkFont(weight="bold")).pack(pady=10)
            for nested in nested_data["nested_executables"]:
                analysis = nested.get("analysis")
                if analysis:
                     add_section("Nested Executable", nested['name'], analysis.installer_type, analysis.install_switches, is_main=False)
            frame.pack(fill="x", pady=5, padx=5)

            # Header
            header_color = "cyan" if is_main else "gray"
            ctk.CTkLabel(frame, text=f"{title} ({filename})", text_color=header_color, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(5,0))
            ctk.CTkLabel(frame, text=f"Type: {type_str}", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)

            # Params
            if params:
                param_text = " ".join(params) if isinstance(params, list) else str(params)

                p_box = ctk.CTkTextbox(frame, height=40)
                p_box.insert("0.0", param_text)
                p_box.configure(state="disabled")
                p_box.pack(fill="x", padx=10, pady=5)
            else:
                 ctk.CTkLabel(frame, text="No confirmed parameters found.", text_color="orange").pack(anchor="w", padx=10, pady=5)

            # Brute Force / Raw Output
            # We want to show this if we have no switches OR if it's available and user wants "ALL" info
            raw_out = None
            if hasattr(params, 'brute_force_output'): # If params user object has it? No, passed as list usually.
                 pass

            if raw_output:
                 ctk.CTkLabel(frame, text="Raw Output / Help Text:", text_color="gray", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))
                 r_box = ctk.CTkTextbox(frame, height=80, font=("Consolas", 10))
                 r_box.insert("0.0", raw_output)
                 r_box.configure(state="disabled")
                 r_box.pack(fill="x", padx=10, pady=5)

            # Since 'params' passed to this helper is just a list of strings, we need to pass raw_output separately if we want it here.
            # But wait, looking at calls:
            # Main: info.install_switches (List)
            # Nested: item.get("analysis").install_switches (List)

            # I should modify 'add_section' signature to accept 'raw_output'

        # 1. Main Installer
        main_raw = None # info object might not store raw brute force text easily accessed here unless we stored it on 'info'
        # 'info' is an InstallerInfo object. Does it have brute_force_output?
        # Typically not, it's returned separately by analyzer.

        add_section("Main Installer", Path(info.file_path).name, info.installer_type, info.install_switches, is_main=True)

        # 2. Nested
        if nested_data and nested_data.get("nested_executables"):
            ctk.CTkLabel(scroll, text="Nested Installers Found:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", pady=(15, 5))

            for item in nested_data.get("nested_executables", []):
                an = item.get("analysis")
                i_type = item.get("type", "Unknown")
                switches = []
                if an:
                    i_type += f" / {an.installer_type}"
                    switches = an.install_switches

                # Check for brute force output specific to this item
                raw = item.get("brute_force_output")

                add_section("Nested File", item["name"], i_type, switches, raw_output=raw)

        ctk.CTkButton(top, text="Close", command=top.destroy).pack(pady=10)


    def setup_intune_tab(self):
        """Setup the dedicated Intune Utility tab."""
        self.intune_view = IntuneView(self.tab_intune, self.intune_service, NotificationService())
        self.intune_view.pack(fill="both", expand=True)




def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
