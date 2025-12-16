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

from switchcraft.analyzers.msi import MsiAnalyzer
from switchcraft.analyzers.exe import ExeAnalyzer
from switchcraft.utils.winget import WingetHelper
from switchcraft.utils.i18n import i18n
from switchcraft.utils.updater import UpdateChecker
from switchcraft.analyzers.universal import UniversalAnalyzer
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
        self.tab_helper = self.tabview.add(i18n.get("tab_helper"))
        self.tab_settings = self.tabview.add(i18n.get("tab_settings"))

        # Initialize Tabs
        self.setup_analyzer_tab()
        self.setup_helper_tab()
        self.setup_settings_tab()

        # Setup Beta/Dev banner if pre-release
        self.setup_version_banner()

        # Auto-Check Updates
        self.after(2000, self.check_updates_silently)

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
            checker = UpdateChecker()
            has_update, version, data = checker.check_for_updates()

            if has_update:
                self.after(0, lambda: self.show_update_dialog(checker))
            elif show_no_update:
                self.after(0, lambda: messagebox.showinfo("Check for Updates", f"You are up to date! ({__version__})"))
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            if show_no_update:
                self.after(0, lambda err=str(e): messagebox.showerror(i18n.get("update_check_failed"), f"{i18n.get('could_not_check')}\n{err}"))

    def show_update_dialog(self, checker):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Update Available 🚀")
        dialog.geometry("500x400")
        dialog.transient(self)

        ctk.CTkLabel(dialog, text=i18n.get("update_available"), font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        info_frame = ctk.CTkFrame(dialog)
        info_frame.pack(fill="both", expand=True, padx=20, pady=10)

        ctk.CTkLabel(info_frame, text=f"{i18n.get('current_version')}: {checker.current_version}").pack(anchor="w", padx=10, pady=2)
        ctk.CTkLabel(info_frame, text=f"{i18n.get('new_version')}: {checker.latest_version}", text_color="green").pack(anchor="w", padx=10, pady=2)

        date_str = checker.release_date.split("T")[0] if checker.release_date else "Unknown"
        ctk.CTkLabel(info_frame, text=f"{i18n.get('released')}: {date_str}").pack(anchor="w", padx=10, pady=2)

        ctk.CTkLabel(dialog, text=f"{i18n.get('changelog')}:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20)
        textbox = ctk.CTkTextbox(dialog, height=100)
        textbox.pack(fill="x", padx=20, pady=5)
        textbox.insert("0.0", checker.release_notes or i18n.get("no_changelog"))
        textbox.configure(state="disabled")

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)

        download_url = checker.get_download_url()
        ctk.CTkButton(btn_frame, text=i18n.get("download_update"), command=lambda: webbrowser.open(download_url)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text=i18n.get("skip"), fg_color="gray", command=dialog.destroy).pack(side="right", padx=5)


    # --- Analyzer Tab ---
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

        analyzers = [MsiAnalyzer(), ExeAnalyzer()]
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

        input_frame = ctk.CTkFrame(self.tab_helper, fg_color="transparent")
        input_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

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
        self.after(500, lambda: self.append_chat("AI", f"I'm currently a mock helper, but I heard you say: '{msg}'. \nCheckout https://silent.ls/ for a database!"))

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

        # Update Check
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
