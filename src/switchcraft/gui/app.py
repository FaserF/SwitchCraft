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
        self.setup_settings_tab()

        # Setup Beta/Dev banner if pre-release
        self.setup_version_banner()

        # Auto-Check Updates
        self.after(2000, self.check_updates_silently)

        # Security Check
        self.after(3000, self.check_security_silently)

        # Initialize AI
        self.ai_service = SwitchCraftAI()



        # Handle window close for "Update Later" feature
        self.protocol("WM_DELETE_WINDOW", self.on_close)

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
                text = f"⚠️ DEVELOPMENT BUILD ({__version__}) - Unstable, for testing only"
            else:
                bg_color = "#FFC107"  # Orange/Yellow for beta
                text = f"⚠️ BETA VERSION ({__version__}) - Not for production use"

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

        self.after(0, lambda i=info, w=winget_url, bf=brute_force_data, nd=nested_data, sd=silent_disabled:
                   self.show_results(i, w, bf, nd, sd))

    def show_error(self, message):
         self.status_bar.configure(text=i18n.get("error"))
         label = ctk.CTkLabel(self.result_frame, text=message, text_color="red", font=ctk.CTkFont(size=14))
         label.pack(pady=20)

    def show_results(self, info, winget_url, brute_force_data=None, nested_data=None, silent_disabled=None):
        self.status_bar.configure(text=i18n.get("analysis_complete"))
        self.clear_results()

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

            # --- Intune Script Generation ---
            def generate_intune_script():
                default_filename = f"Install-{info.product_name or 'App'}.ps1"
                # Sanitize filename
                default_filename = "".join(x for x in default_filename if x.isalnum() or x in "-_.")

                save_path = ctk.filedialog.asksaveasfilename(
                    defaultextension=".ps1",
                    filetypes=[("PowerShell Script", "*.ps1")],
                    initialfile=default_filename,
                    title="Save Intune Script"
                )
                if save_path:
                    # Collect metadata
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
                        try:
                            # Open file in editor
                            os.startfile(save_path)
                        except: pass
                    else:
                        messagebox.showerror("Error", "Failed to generate script template.")

            ctk.CTkButton(self.result_frame, text="✨ Generate Intune Script", fg_color="purple", command=generate_intune_script).pack(pady=5, fill="x")
        else:
             self.add_result_row(i18n.get("silent_install"), i18n.get("no_switches"), color="orange")
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

        copy_btn = ctk.CTkButton(frame, text="Copy", width=60, fg_color="transparent", border_width=1,
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
        self.append_chat("System", "Welcome to the AI Helper! (Mock Version)\nAsk me about silent switches or command line arguments.")

        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Privacy Disclaimer (Green Text)
        disclaimer_frame = ctk.CTkFrame(self.tab_helper, fg_color="transparent")
        disclaimer_frame.grid(row=1, column=0, sticky="ew", padx=10)

        ctk.CTkLabel(
            disclaimer_frame,
            text="🔒 Privacy Note: This AI is a local rule-based system. No data leaves your machine.",
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

        # Appearance
        frame_app = ctk.CTkFrame(self.tab_settings)
        frame_app.pack(fill="x", padx=10, pady=10)

        lbl_theme = ctk.CTkLabel(frame_app, text=i18n.get("settings_theme"), font=ctk.CTkFont(weight="bold"))
        lbl_theme.pack(pady=5)

        self.theme_opt = ctk.CTkSegmentedButton(frame_app, values=[i18n.get("settings_light"), i18n.get("settings_dark"), "System"],
                                                command=self.change_theme)
        self.theme_opt.set("System")
        self.theme_opt.pack(pady=10)

        # Language
        frame_lang = ctk.CTkFrame(self.tab_settings)
        frame_lang.pack(fill="x", padx=10, pady=10)

        lbl_lang = ctk.CTkLabel(frame_lang, text=i18n.get("settings_lang"), font=ctk.CTkFont(weight="bold"))
        lbl_lang.pack(pady=5)

        self.lang_opt = ctk.CTkOptionMenu(frame_lang, values=["English (en)", "German (de)"], command=self.change_language)
        current_lang = "German (de)" if i18n.language == "de" else "English (en)"
        self.lang_opt.set(current_lang)
        self.lang_opt.pack(pady=10)

        # Debug Mode Toggle
        frame_debug = ctk.CTkFrame(self.tab_settings)
        frame_debug.pack(fill="x", padx=10, pady=10)

        debug_label = i18n.get("settings_debug") if "settings_debug" in i18n.translations.get(i18n.language, {}) else "Debug Logging"
        lbl_debug = ctk.CTkLabel(frame_debug, text=debug_label, font=ctk.CTkFont(weight="bold"))
        lbl_debug.pack(pady=5)

        self.debug_switch = ctk.CTkSwitch(
            frame_debug,
            text="Enable verbose logging",
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
            text="Requires restart to take effect",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        debug_hint.pack(pady=2)

        # Update Channel Selection
        frame_channel = ctk.CTkFrame(self.tab_settings)
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
        current_channel = self._get_registry_value("UpdateChannel", "stable")
        channel_map = {"stable": "Stable", "beta": "Beta", "dev": "Dev"}
        self.channel_opt.set(channel_map.get(current_channel, "Stable"))
        self.channel_opt.pack(pady=5)

        channel_desc = ctk.CTkLabel(
            frame_channel,
            text="Stable: Releases only | Beta: Pre-releases | Dev: Latest commits",
            text_color="gray",
            font=ctk.CTkFont(size=11),
            wraplength=350
        )
        channel_desc.pack(pady=2)

        # Template Selection
        frame_tmpl = ctk.CTkFrame(self.tab_settings)
        frame_tmpl.pack(fill="x", padx=10, pady=10)

        lbl_tmpl = ctk.CTkLabel(frame_tmpl, text="PowerShell Template (Intune)", font=ctk.CTkFont(weight="bold"))
        lbl_tmpl.pack(pady=5)

        current_tmpl = SwitchCraftConfig.get_value("CustomTemplatePath")
        display_tmpl = current_tmpl if current_tmpl else "Default Internal Template"

        self.tmpl_path_label = ctk.CTkLabel(frame_tmpl, text=display_tmpl, text_color="gray", wraplength=300)
        self.tmpl_path_label.pack(pady=2)

        def select_template():
            path = ctk.filedialog.askopenfilename(filetypes=[("PowerShell", "*.ps1")])
            if path:
                SwitchCraftConfig.set_user_preference("CustomTemplatePath", path)
                self.tmpl_path_label.configure(text=path)

        ctk.CTkButton(frame_tmpl, text="Select Custom Template", command=select_template).pack(pady=5)

        def reset_template():
             SwitchCraftConfig.set_user_preference("CustomTemplatePath", "")
             self.tmpl_path_label.configure(text="Default Internal Template")

        ctk.CTkButton(frame_tmpl, text="Reset to Default", fg_color="transparent", border_width=1, command=reset_template).pack(pady=2)



        # Update Check Button
        frame_upd = ctk.CTkFrame(self.tab_settings)
        frame_upd.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(frame_upd, text=i18n.get("check_updates"), command=lambda: self._run_update_check(show_no_update=True)).pack(pady=10)

        # About
        frame_about = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        frame_about.pack(fill="x", padx=10, pady=20)

        ctk.CTkLabel(frame_about, text="SwitchCraft", font=ctk.CTkFont(size=24, weight="bold")).pack()
        ctk.CTkLabel(frame_about, text=f"{i18n.get('about_version')}: {__version__}").pack()
        ctk.CTkLabel(frame_about, text=f"{i18n.get('about_dev')}: FaserF").pack()

        link = ctk.CTkButton(frame_about, text="GitHub: FaserF/SwitchCraft", fg_color="transparent", text_color="cyan", hover=False,
                             command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft"))
        link.pack(pady=5)

        # Footer
        ctk.CTkLabel(self.tab_settings, text=i18n.get("brought_by"), text_color="gray").pack(side="bottom", pady=10)

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

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
