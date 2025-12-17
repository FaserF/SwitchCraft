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
from switchcraft import __version__

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

        # Initialize AI
        self.ai_service = SwitchCraftAI()
        self.intune_service = IntuneService()



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
            current_dir = os.path.dirname(os.path.abspath(__file__))
            asset_path = os.path.join(current_dir, "..", "assets", "logo.png")
            if os.path.exists(asset_path):
                self.logo_image = ctk.CTkImage(light_image=Image.open(asset_path),
                                             dark_image=Image.open(asset_path),
                                             size=(64, 64))
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
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

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
        self.clear_results()
        thread = threading.Thread(target=self.analyze, args=(file_path,))
        thread.start()

    def clear_results(self):
        for widget in self.result_frame.winfo_children():
            widget.destroy()

    def analyze(self, file_path_str):
        path = Path(file_path_str)
        if not path.exists():
             self.after(0, lambda: self.show_error(i18n.get("file_not_found")))
             return

        analyzers = [MsiAnalyzer(), ExeAnalyzer(), MacOSAnalyzer()]
        info = None
        for analyzer in analyzers:
            if analyzer.can_analyze(path):
                try:
                    info = analyzer.analyze(path)
                    break
                except Exception as e:
                    logger.error(f"Analysis failed: {e}")

        # Universal / Brute Force Analysis
        brute_force_data = None
        nested_data = None
        silent_disabled = None
        uni = UniversalAnalyzer()
        wrapper = uni.check_wrapper(path)  # Check wrapper regardless

        if not info or info.installer_type == "Unknown" or "Unknown" in (info.installer_type or "") or wrapper:
            logger.info("Starting Universal Analysis...")

            # Brute Force
            if not info or "Unknown" in (info.installer_type or ""):
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
            self.after(0, lambda: self.status_bar.configure(text="Extracting archive for nested analysis..."))
            nested_data = uni.extract_and_analyze_nested(path)

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

        self.after(0, lambda i=info, w=winget_url, bf=brute_force_data, nd=nested_data, sd=silent_disabled:
                   self.show_results(i, w, bf, nd, sd))

    def show_error(self, message):
         self.status_bar.configure(text=i18n.get("error"))
         label = ctk.CTkLabel(self.result_frame, text=message, text_color="red", font=ctk.CTkFont(size=14))
         label.pack(pady=20)

    def show_results(self, info, winget_url, brute_force_data=None, nested_data=None, silent_disabled=None):
        self.status_bar.configure(text=i18n.get("analysis_complete"))
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

        # Install
        if info.install_switches:
            params = " ".join(info.install_switches)
            self.add_copy_row(i18n.get("silent_install") + " (Params)", params, "green")
            self.add_full_command_row("Install Command (Full)", info.file_path, params, is_install=True, is_msi=("MSI" in info.installer_type))
            self.add_intune_row("Intune Install", info.file_path, params, is_msi=("MSI" in info.installer_type))




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

        if all_params:
            self.show_all_parameters(all_params)

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
                UniversalAnalyzer().cleanup_temp_dir(nested_data['temp_dir'])
                self.status_bar.configure(text="Temporary files cleaned up")

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
        self.tab_helper.grid_columnconfigure(0, weight=1)
        self.tab_helper.grid_rowconfigure(0, weight=1)

        self.chat_frame = ctk.CTkTextbox(self.tab_helper, state="disabled")
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.append_chat("System", i18n.get("ai_helper_welcome"))

        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Privacy Disclaimer (Green Text)
        disclaimer_frame = ctk.CTkFrame(self.tab_helper, fg_color="transparent")
        disclaimer_frame.grid(row=1, column=0, sticky="ew", padx=10)

        ctk.CTkLabel(
            disclaimer_frame,
            text=f"🔒 {i18n.get('privacy_note')}",
            text_color="green",
            font=ctk.CTkFont(size=11, weight="bold")
        ).pack(anchor="w")

        input_frame = ctk.CTkFrame(self.tab_helper, fg_color="transparent")
        input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        self.chat_entry = ctk.CTkEntry(input_frame, placeholder_text="Ask something...")
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.chat_entry.bind("<Return>", self.handle_chat)

        send_btn = ctk.CTkButton(input_frame, text="Send", width=80, command=self.handle_chat)
        send_btn.pack(side="right")

    def handle_chat(self, event=None):
        msg = self.chat_entry.get()
        if not msg: return
        self.append_chat("You", msg)
        self.chat_entry.delete(0, "end")

        # Query AI
        if hasattr(self, 'ai_service'):
            answer = self.ai_service.ask(msg)
            self.after(200, lambda: self.append_chat("SwitchCraft AI", answer))
        else:
            self.after(500, lambda: self.append_chat("System", "AI Service not initialized."))

    def append_chat(self, sender, message):
        self.chat_frame.configure(state="normal")
        self.chat_frame.insert("end", f"[{sender}]: {message}\n\n")
        self.chat_frame.configure(state="disabled")
        self.chat_frame.see("end")

    # --- Settings Tab ---
    def setup_settings_tab(self):
        self.tab_settings.grid_columnconfigure(0, weight=1)
        self.tab_settings.grid_rowconfigure(0, weight=1)

        # Scrollable Container
        self.settings_scroll = ctk.CTkScrollableFrame(self.tab_settings, fg_color="transparent")
        self.settings_scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.settings_scroll.grid_columnconfigure(0, weight=1)

        # Appearance
        frame_app = ctk.CTkFrame(self.settings_scroll)
        frame_app.pack(fill="x", padx=10, pady=10)

        lbl_theme = ctk.CTkLabel(frame_app, text=i18n.get("settings_theme"), font=ctk.CTkFont(weight="bold"))
        lbl_theme.pack(pady=5)

        self.theme_opt = ctk.CTkSegmentedButton(frame_app, values=[i18n.get("settings_light"), i18n.get("settings_dark"), "System"],
                                                command=self.change_theme)
        self.theme_opt.set("System")
        self.theme_opt.pack(pady=10)

        # Language
        frame_lang = ctk.CTkFrame(self.settings_scroll)
        frame_lang.pack(fill="x", padx=10, pady=10)

        lbl_lang = ctk.CTkLabel(frame_lang, text=i18n.get("settings_lang"), font=ctk.CTkFont(weight="bold"))
        lbl_lang.pack(pady=5)

        self.lang_opt = ctk.CTkOptionMenu(frame_lang, values=["English (en)", "German (de)"], command=self.change_language)
        current_lang = "German (de)" if i18n.language == "de" else "English (en)"
        self.lang_opt.set(current_lang)
        self.lang_opt.pack(pady=10)

        # Debug Mode Toggle
        frame_debug = ctk.CTkFrame(self.settings_scroll)
        frame_debug.pack(fill="x", padx=10, pady=10)

        debug_label = i18n.get("settings_debug") if "settings_debug" in i18n.translations.get(i18n.language, {}) else "Debug Logging"
        lbl_debug = ctk.CTkLabel(frame_debug, text=debug_label, font=ctk.CTkFont(weight="bold"))
        lbl_debug.pack(pady=5)

        self.debug_switch = ctk.CTkSwitch(
            frame_debug,
            text=i18n.get("enable_verbose"),
            command=self.toggle_debug_mode,
            onvalue=1,
            offvalue=0
        )
        # Load current debug setting
        if self._get_registry_value("DebugMode", 0) == 1:
            self.debug_switch.select()
        self.debug_switch.pack(pady=5)

        debug_hint = ctk.CTkLabel(
            frame_debug,
            text=i18n.get("requires_restart"),
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        debug_hint.pack(pady=2)

        # Update Channel Selection
        frame_channel = ctk.CTkFrame(self.settings_scroll)
        frame_channel.pack(fill="x", padx=10, pady=10)

        channel_label = i18n.get("settings_channel") if "settings_channel" in i18n.translations.get(i18n.language, {}) else "Update Channel"
        lbl_channel = ctk.CTkLabel(frame_channel, text=channel_label, font=ctk.CTkFont(weight="bold"))
        lbl_channel.pack(pady=5)

        self.channel_opt = ctk.CTkSegmentedButton(
            frame_channel,
            values=["Stable", "Beta", "Dev"],
            command=self.change_update_channel
        )
        # Load current channel from registry
        current_channel = self._get_registry_value("UpdateChannel")
        if not current_channel:
            # Smart Detection: Default to Beta/Dev if running pre-release
            v_low = __version__.lower()
            if "dev" in v_low: current_channel = "dev"
            elif "beta" in v_low: current_channel = "beta"
            else: current_channel = "stable"

        channel_map = {"stable": "Stable", "beta": "Beta", "dev": "Dev"}
        self.channel_opt.set(channel_map.get(current_channel, "Stable"))
        self.channel_opt.pack(pady=5)

        channel_desc = ctk.CTkLabel(
            frame_channel,
            text=i18n.get("settings_channel_desc"),
            text_color="gray",
            font=ctk.CTkFont(size=11),
            wraplength=350
        )
        channel_desc.pack(pady=2)

        # Template Selection
        frame_tmpl = ctk.CTkFrame(self.settings_scroll)
        frame_tmpl.pack(fill="x", padx=10, pady=10)

        lbl_tmpl = ctk.CTkLabel(frame_tmpl, text=i18n.get("settings_tmpl_title"), font=ctk.CTkFont(weight="bold"))
        lbl_tmpl.pack(pady=5)

        current_tmpl = SwitchCraftConfig.get_value("CustomTemplatePath")
        display_tmpl = current_tmpl if current_tmpl else i18n.get("settings_tmpl_default")

        self.tmpl_path_label = ctk.CTkLabel(frame_tmpl, text=display_tmpl, text_color="gray", wraplength=300)
        self.tmpl_path_label.pack(pady=2)

        def select_template():
            path = ctk.filedialog.askopenfilename(filetypes=[("PowerShell", "*.ps1")])
            if path:
                SwitchCraftConfig.set_user_preference("CustomTemplatePath", path)
                self.tmpl_path_label.configure(text=path)

        ctk.CTkButton(frame_tmpl, text=i18n.get("settings_tmpl_select"), command=select_template).pack(pady=5)

        def reset_template():
            SwitchCraftConfig.set_user_preference("CustomTemplatePath", "")
            # Or remove value entirely? set_user_preference doesn't support delete easily without modification,
            # but empty string might be enough if logic checks `if current_tmpl`.
            # Let's check `SwitchCraftConfig` again. It has `set_user_preference`.
            # Actually, let's implement a clean delete or set to empty.
            self.tmpl_path_label.configure(text="Default Internal Template")

        ctk.CTkButton(frame_tmpl, text=i18n.get("settings_tmpl_reset"), fg_color="transparent", border_width=1, command=reset_template).pack(pady=2)


        # Help & Documentation
        frame_docs = ctk.CTkFrame(self.settings_scroll)
        frame_docs.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(frame_docs, text="Help & Support", font=ctk.CTkFont(weight="bold")).pack(pady=5)

        btn_docs = ctk.CTkButton(frame_docs, text="Open Documentation (README)",
                               command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft/blob/main/README.md"))
        btn_docs.pack(pady=5, fill="x")

        btn_help = ctk.CTkButton(frame_docs, text="Get Help (GitHub Issues)", fg_color="transparent", border_width=1,
                               command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft/issues"))
        btn_help.pack(pady=5, fill="x")

        # Debug Console Toggle (Windows Only)
        if sys.platform == 'win32':
             frame_debug = ctk.CTkFrame(self.settings_scroll)
             frame_debug.pack(fill="x", padx=10, pady=10)

             ctk.CTkLabel(frame_debug, text=i18n.get("settings_debug_title"), font=ctk.CTkFont(weight="bold")).pack(pady=5)

             self.debug_console_var = ctk.BooleanVar(value=False)

             def toggle_console():
                 import ctypes
                 kernel32 = ctypes.windll.kernel32
                 if self.debug_console_var.get():
                     kernel32.AllocConsole()
                     sys.stdout = open("CONOUT$", "w")
                     sys.stderr = open("CONOUT$", "w")
                     print("SwitchCraft Debug Console [Enabled]")
                 else:
                     try:
                         sys.stdout.close()
                         sys.stderr.close()
                         # Restore std streams to avoid errors
                         sys.stdout = sys.__stdout__
                         sys.stderr = sys.__stderr__
                     except: pass
                     kernel32.FreeConsole()

             ctk.CTkSwitch(frame_debug, text=i18n.get("settings_debug_console"), variable=self.debug_console_var, command=toggle_console).pack(pady=5)



        # Update Check Button
        frame_upd = ctk.CTkFrame(self.settings_scroll)
        frame_upd.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(frame_upd, text=i18n.get("check_updates"), command=lambda: self._run_update_check(show_no_update=True)).pack(pady=10)

        # About
        frame_about = ctk.CTkFrame(self.settings_scroll, fg_color="transparent")
        frame_about.pack(fill="x", padx=10, pady=20)

        ctk.CTkLabel(frame_about, text="SwitchCraft", font=ctk.CTkFont(size=24, weight="bold")).pack()
        ctk.CTkLabel(frame_about, text=f"{i18n.get('about_version')}: {__version__}").pack()
        ctk.CTkLabel(frame_about, text=f"{i18n.get('about_dev')}: FaserF").pack()

        link = ctk.CTkButton(frame_about, text="GitHub: FaserF/SwitchCraft", fg_color="transparent", text_color="cyan", hover=False,
                             command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft"))
        link.pack(pady=5)

        # Footer
        ctk.CTkLabel(self.settings_scroll, text=i18n.get("brought_by"), text_color="gray").pack(side="bottom", pady=10)

    def _get_registry_value(self, name, default=None):
        """Read a value from the Windows registry."""
        if sys.platform != 'win32':
            return default
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\FaserF\SwitchCraft', 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            return value
        except:
            return default

    def _set_registry_value(self, name, value, value_type=None):
        """Write a value to the Windows registry."""
        if sys.platform != 'win32':
            return
        try:
            import winreg
            # Determine value type
            if value_type is None:
                if isinstance(value, int):
                    value_type = winreg.REG_DWORD
                else:
                    value_type = winreg.REG_SZ

            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\FaserF\SwitchCraft')
            winreg.SetValueEx(key, name, 0, value_type, value)
            winreg.CloseKey(key)
        except Exception as e:
            logger.error(f"Failed to write registry value {name}: {e}")

    def toggle_debug_mode(self):
        """Toggle debug mode setting."""
        enabled = self.debug_switch.get()
        self._set_registry_value("DebugMode", int(enabled))
        logger.info(f"Debug mode {'enabled' if enabled else 'disabled'} (restart required)")

    def change_update_channel(self, value):
        """Change update channel setting."""
        channel_map = {"Stable": "stable", "Beta": "beta", "Dev": "dev"}
        channel = channel_map.get(value, "stable")
        self._set_registry_value("UpdateChannel", channel)
        logger.info(f"Update channel changed to: {channel}")

    def change_theme(self, value):
        if value == i18n.get("settings_light"): ctk.set_appearance_mode("Light")
        elif value == i18n.get("settings_dark"): ctk.set_appearance_mode("Dark")
        else: ctk.set_appearance_mode("System")

    def change_language(self, value):
        code = "de" if "de" in value else "en"
        if code != i18n.language:
            i18n.set_language(code)
            self.tabview._segmented_button.configure(values=[i18n.get("tab_analyzer"), i18n.get("tab_helper"), i18n.get("tab_settings")])
            self.title(i18n.get("app_title"))

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

        save_path = ctk.filedialog.asksaveasfilename(
            defaultextension=".ps1",
            filetypes=[("PowerShell Script", "*.ps1")],
            initialfile=default_filename,
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
                self.status_bar.configure(text=f"Script generated: {save_path}")
                try: os.startfile(save_path)
                except: pass
            else:
                messagebox.showerror("Error", "Failed to generate script template.")

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

        # 2. Switch Tab
        self.tabview.set("Intune Utility")

        # 3. Notify user
        self.status_bar.configure(text="Pre-filled Intune Utility form. Please review and click Create.")



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
        def add_section(title, filename, type_str, params, is_main=False):
            frame = ctk.CTkFrame(scroll, fg_color="#2B2B2B" if is_main else "#1F1F1F")
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

        # 1. Main Installer
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
                if not switches and item.get("brute_force_output"):
                    # Maybe parsing brute force output needed?
                    # For now just show "See Log below" or similar?
                    pass

                add_section("Nested File", item["name"], i_type, switches)

        ctk.CTkButton(top, text="Close", command=top.destroy).pack(pady=10)


    def setup_intune_tab(self):
        """Setup the dedicated Intune Utility tab."""
        # Main Layout
        self.tab_intune.grid_columnconfigure(0, weight=1)
        self.tab_intune.grid_rowconfigure(3, weight=1) # Log area expands

        # Header
        header = ctk.CTkFrame(self.tab_intune, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(header, text="Intune Content Prep Utility", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(header, text="Create .intunewin packages for Microsoft Intune deployment.", text_color="gray").pack(anchor="w")

        # Tool Status / Activation
        self.intune_status_frame = ctk.CTkFrame(self.tab_intune)
        self.intune_status_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self._refresh_intune_status()

    def _refresh_intune_status(self):
        """Check if tool exists and show appropriate UI."""
        for widget in self.intune_status_frame.winfo_children():
            widget.destroy()

        if self.intune_service.is_tool_available():
            self._show_intune_form()
        else:
            self._show_intune_activation()

    def _show_intune_activation(self):
        ctk.CTkLabel(self.intune_status_frame, text=i18n.get("intune_util_missing")).pack(pady=(10, 5))
        ctk.CTkButton(self.intune_status_frame, text=i18n.get("intune_download_activate"), command=self._activate_intune_tool).pack(pady=10)

    def _activate_intune_tool(self):
        self.status_bar.configure(text=i18n.get("intune_downloading"))
        def _download():
            if self.intune_service.download_tool():
                self.after(0, lambda: messagebox.showinfo("Success", i18n.get("intune_success")))
                self.after(0, self._refresh_intune_status)
                self.after(0, lambda: self.status_bar.configure(text=i18n.get("intune_ready")))
            else:
                self.after(0, lambda: messagebox.showerror("Error", i18n.get("intune_failed")))
                self.after(0, lambda: self.status_bar.configure(text=i18n.get("error")))
        threading.Thread(target=_download, daemon=True).start()

    def _show_intune_form(self):
        # Tool Path
        tool_frame = ctk.CTkFrame(self.intune_status_frame, fg_color="transparent")
        tool_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(tool_frame, text=i18n.get("intune_tool_path"), width=100, anchor="w").pack(side="left")

        self.entry_intune_tool = ctk.CTkEntry(tool_frame)
        self.entry_intune_tool.pack(side="left", fill="x", expand=True, padx=5)
        self.entry_intune_tool.insert(0, str(self.intune_service.tool_path))

        # Setup File
        setup_frame = ctk.CTkFrame(self.intune_status_frame, fg_color="transparent")
        setup_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(setup_frame, text=i18n.get("intune_setup_file"), width=100, anchor="w").pack(side="left")

        self.entry_intune_setup = ctk.CTkEntry(setup_frame)
        self.entry_intune_setup.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(setup_frame, text=i18n.get("browse"), width=60, command=self._browse_intune_setup).pack(side="right")

        # Source Folder
        src_frame = ctk.CTkFrame(self.intune_status_frame, fg_color="transparent")
        src_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(src_frame, text=i18n.get("intune_source_folder"), width=100, anchor="w").pack(side="left")

        self.entry_intune_source = ctk.CTkEntry(src_frame)
        self.entry_intune_source.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(src_frame, text=i18n.get("browse"), width=60, command=lambda: self._browse_folder(self.entry_intune_source)).pack(side="right")

        # Output Folder
        out_frame = ctk.CTkFrame(self.intune_status_frame, fg_color="transparent")
        out_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(out_frame, text=i18n.get("intune_output_folder"), width=100, anchor="w").pack(side="left")

        self.entry_intune_output = ctk.CTkEntry(out_frame)
        self.entry_intune_output.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(out_frame, text=i18n.get("browse"), width=60, command=lambda: self._browse_folder(self.entry_intune_output)).pack(side="right")

        # Options
        opt_frame = ctk.CTkFrame(self.intune_status_frame, fg_color="transparent")
        opt_frame.pack(fill="x", padx=5, pady=5)

        self.var_intune_quiet = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_frame, text=i18n.get("intune_quiet"), variable=self.var_intune_quiet).pack(side="left", padx=10)

        # Action
        ctk.CTkButton(self.intune_status_frame, text=i18n.get("intune_create_btn"), fg_color="green", height=40, command=self._run_intune_creation).pack(fill="x", padx=20, pady=15)

        # Log Output
        ctk.CTkLabel(self.tab_intune, text=i18n.get("intune_log_label"), anchor="w").grid(row=2, column=0, sticky="w", padx=10)
        self.txt_intune_log = ctk.CTkTextbox(self.tab_intune)
        self.txt_intune_log.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def _browse_intune_setup(self):
        f = ctk.filedialog.askopenfilename()
        if f:
            self.entry_intune_setup.delete(0, "end")
            self.entry_intune_setup.insert(0, f)
            # Auto-fill source and output if empty
            if not self.entry_intune_source.get():
                self.entry_intune_source.insert(0, str(Path(f).parent))
            if not self.entry_intune_output.get():
                self.entry_intune_output.insert(0, str(Path(f).parent))

    def _browse_folder(self, entry_widget):
        d = ctk.filedialog.askdirectory()
        if d:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, d)

    def _run_intune_creation(self):
        s_setup = self.entry_intune_setup.get()
        s_source = self.entry_intune_source.get()
        s_output = self.entry_intune_output.get()
        b_quiet = self.var_intune_quiet.get()

        if not s_setup or not s_source or not s_output:
            messagebox.showerror("Error", "Please fill in all required fields (Setup, Source, Output).")
            return

        self.txt_intune_log.delete("0.0", "end")
        self.txt_intune_log.insert("end", i18n.get("intune_start_creation") + "\n")

        def _process():
            try:
                out = self.intune_service.create_intunewin(
                    source_folder=s_source,
                    setup_file=s_setup,
                    output_folder=s_output,
                    quiet=b_quiet
                )
                self.after(0, lambda: self.txt_intune_log.insert("end", out + "\n\nDONE!"))
                self.after(0, lambda: messagebox.showinfo("Success", i18n.get("intune_pkg_success", path=s_output)))
            except Exception as e:
                self.after(0, lambda: self.txt_intune_log.insert("end", f"ERROR: {e}\n"))
                self.after(0, lambda: messagebox.showerror("Failed", str(e)))

        threading.Thread(target=_process, daemon=True).start()


def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
