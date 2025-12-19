import customtkinter as ctk
from tkinterdnd2 import DND_FILES
import threading
from pathlib import Path
import webbrowser
import logging
from tkinter import messagebox
import os
import shutil
import ctypes
import time

from switchcraft.analyzers.msi import MsiAnalyzer
from switchcraft.analyzers.exe import ExeAnalyzer
from switchcraft.analyzers.macos import MacOSAnalyzer
from switchcraft.analyzers.universal import UniversalAnalyzer
# WingetHelper imported dynamically from addon
from switchcraft.utils.i18n import i18n
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.services.notification_service import NotificationService
from switchcraft.services.signing_service import SigningService
from switchcraft.utils.templates import TemplateGenerator

logger = logging.getLogger(__name__)

class AnalyzerView(ctk.CTkFrame):
    def __init__(self, parent, intune_service, ai_service, app_context):
        super().__init__(parent)
        self.intune_service = intune_service
        self.ai_service = ai_service
        self.app = app_context # Access to main app for tab switching or shared state if really needed

        self.queue = []
        self._is_analyzing = False

        # Grid layout - column expands, rows configured in setup_ui
        self.grid_columnconfigure(0, weight=1)

        self.setup_ui()

    def setup_ui(self):
        # Drop Zone
        row_offset = 0

        # Check for Advanced Addon
        from switchcraft.services.addon_service import AddonService
        if not AddonService.is_addon_installed("advanced"):
            self._create_addon_warning(row_offset)
            row_offset += 1

        # Drop zone - fixed height, no expansion
        self.drop_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.drop_frame.grid(row=row_offset, column=0, sticky="ew", padx=10, pady=(10, 5))

        btn_text = i18n.get("drag_drop")
        image = getattr(self.app, 'logo_image', None)

        self.drop_label = ctk.CTkButton(self.drop_frame, text=btn_text,
                                        image=image,
                                        compound="left",
                                        height=50, corner_radius=10,
                                        fg_color=("#3B8ED0", "#4A235A"),
                                        hover_color=("#36719F", "#5B2C6F"),
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        command=self._on_browse)
        self.drop_label.pack(fill="x")

        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind('<<Drop>>', self._on_drop)

        # Result Area - this row should expand
        result_row = row_offset + 1
        self.result_frame = ctk.CTkScrollableFrame(self, label_text=i18n.get("analysis_complete"))
        self.result_frame.grid(row=result_row, column=0, sticky="nsew", padx=10, pady=(0, 5))
        self.result_frame.grid_columnconfigure(0, weight=1)

        # Configure grid: only result row expands
        self.grid_rowconfigure(result_row, weight=1)

        # Status Bar
        self.status_bar = ctk.CTkLabel(self, text="Ready", anchor="w", text_color="gray")
        self.status_bar.grid(row=result_row+1, column=0, sticky="ew", padx=10, pady=(5, 0))

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=result_row+2, column=0, sticky="ew", padx=10, pady=(0, 5))
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()

    def _create_addon_warning(self, row):
        # from switchcraft.services.addon_service import AddonService  # Avoid Circular Import if not needed

        warning_frame = ctk.CTkFrame(self, fg_color="#5e1b1b") # Dark red bg
        warning_frame.grid(row=row, column=0, sticky="ew", padx=10, pady=(10,0))
        warning_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(warning_frame, text="⚠️", font=ctk.CTkFont(size=24)).grid(row=0, column=0, padx=10, pady=5)

        ctk.CTkLabel(warning_frame,
                     text=i18n.get("analyzer_addon_warning"),
                     text_color="white",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=1, sticky="w", pady=5)

        self.btn_install_advanced = ctk.CTkButton(warning_frame,
                      text=i18n.get("analyzer_addon_install"),
                      fg_color="#cf3a3a", hover_color="#a12d2d", text_color="white",
                      width=150,
                      command=self._install_advanced_with_feedback
                      )
        self.btn_install_advanced.grid(row=0, column=2, padx=10, pady=10)

    def _install_advanced_with_feedback(self):
        self.btn_install_advanced.configure(state="disabled", text=i18n.get("status_downloading") or "Downloading...")
        from switchcraft.services.addon_service import AddonService

        def _run():
            success = AddonService.install_addon("advanced")
            def _done():
                self.btn_install_advanced.configure(state="normal", text=i18n.get("analyzer_addon_install"))
                if success:
                    # Use the app's restart logic if available
                    if hasattr(self.app, '_show_restart_countdown'):
                        self.app._show_restart_countdown()
                    else:
                        from tkinter import messagebox
                        messagebox.showinfo("Success", "Addon installed. Please restart.")
                else:
                    from tkinter import messagebox
                    messagebox.showerror("Error", "Installation failed. Check logs.")

            self.after(0, _done)

        threading.Thread(target=_run, daemon=True).start()

    def _on_drop(self, event):
        data = event.data
        files = []

        # Parse TkinterDnD file list (space-separated, curlies for spaces)
        import re
        # Match {path with spaces} OR non-space-sequence
        pattern = r'\{([^{}]+)\}|(\S+)'
        matches = re.findall(pattern, data)

        for m in matches:
            # m is tuple (group1, group2), only one is non-empty
            path = m[0] if m[0] else m[1]
            if path:
                files.append(path)

        if not files:
            return

        self.queue.extend(files)
        self._process_queue()

    def _process_queue(self):
        if self._is_analyzing:
            return

        if not self.queue:
            return  # Done

        next_file = self.queue.pop(0)
        self._start_analysis(next_file)

    def _on_browse(self):
        file_path = ctk.filedialog.askopenfilename(filetypes=[("Installers", "*.exe;*.msi")])
        if file_path:
            self._start_analysis(file_path)

    def _start_analysis(self, file_path):
        if self._is_analyzing:
            self.queue.append(file_path)
            return

        self._is_analyzing = True
        self.status_bar.configure(text=f"{i18n.get('analyzing')} {Path(file_path).name}...")
        self.progress_bar.grid()
        self.progress_bar.set(0)
        self._clear_results()
        thread = threading.Thread(target=self._analyze_thread, args=(file_path,))
        thread.start()

    def _clear_results(self):
        for widget in self.result_frame.winfo_children():
            widget.destroy()

    def _update_progress(self, val, msg=None, eta_seconds=None):
        current_time = time.time()
        # Throttle updates to ~20FPS unless critical (0 or 1.0 or explicit message change)
        if hasattr(self, '_last_update_time'):
             if val not in [0, 1.0] and (current_time - self._last_update_time < 0.05):
                 return

        self._last_update_time = current_time
        self.after(0, lambda: self._update_progress_ui(val, msg, eta_seconds))

    def _update_progress_ui(self, val, msg, eta_seconds=None):
        self.progress_bar.set(val)
        if msg:
            eta_str = ""
            if eta_seconds is not None:
                if eta_seconds > 60:
                   eta_str = f" (ETA: {int(eta_seconds // 60)}m {int(eta_seconds % 60)}s)"
                else:
                   eta_str = f" (ETA: {int(eta_seconds)}s)"

            self.status_bar.configure(text=f"{msg}{eta_str}")

    def _show_error(self, message):
        self.status_bar.configure(text=i18n.get("error"))
        label = ctk.CTkLabel(self.result_frame, text=message, text_color="red", font=ctk.CTkFont(size=14))
        label.pack(pady=20)

    def _analyze_thread(self, file_path_str):
        try:
            path = Path(file_path_str)
            if not path.exists():
                self.after(0, lambda: self._show_error(i18n.get("file_not_found")))
                return

            self._update_progress(0.1, f"{i18n.get('analyzing')} {path.name}...")

            analyzers = [MsiAnalyzer(), ExeAnalyzer(), MacOSAnalyzer()]
            info = None
            total_analyzers = len(analyzers)

            start_time = time.time()

            def progress_handler(pct, message, _=None):
                 # Map 0-100 from sub-task to global progress range [0.5, 0.9]
                 # We are in deep analysis phase
                 global_pct = 0.5 + (pct / 100 * 0.4)

                 # ETA Calculation
                 elapsed = time.time() - start_time
                 # Heuristic: If we are at global_pct, expected total time = elapsed / global_pct
                 # But global_pct is rough.
                 # Let's use simple logic:
                 eta = 0
                 if global_pct > 0.1:
                     total_est = elapsed / global_pct
                     eta = total_est - elapsed

                 self._update_progress(global_pct, message, eta)

            for idx, analyzer in enumerate(analyzers):
                self._update_progress(0.1 + (0.3 * (idx / total_analyzers)), f"Running {analyzer.__class__.__name__}...")
                if analyzer.can_analyze(path):
                    try:
                        info = analyzer.analyze(path)
                        break
                    except Exception as e:
                        logger.error(f"Analysis failed for {analyzer.__class__.__name__}: {e}")

            brute_force_data = None
            nested_data = None
            silent_disabled = None
            uni = UniversalAnalyzer()
            wrapper = uni.check_wrapper(path)

            if not info or info.installer_type == "Unknown" or "Unknown" in (info.installer_type or "") or wrapper:
                logger.info("Starting Universal Analysis...")
                self._update_progress(0.5, "Running Universal Analysis...")

                if not info or "Unknown" in (info.installer_type or ""):
                    self._update_progress(0.6, "Attempting Brute Force Analysis...")
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
                    silent_disabled = uni.detect_silent_disabled(path, brute_force_data)

                if wrapper:
                    if not info:
                        from switchcraft.models import InstallerInfo
                        info = InstallerInfo(file_path=str(path), installer_type="Wrapper")
                    info.installer_type += f" ({wrapper})"

            if not info:
                from switchcraft.models import InstallerInfo
                info = InstallerInfo(file_path=str(path), installer_type="Unknown")

            if not info.install_switches and path.suffix.lower() == '.exe':
                self._update_progress(0.5, "Extracting ecosystem for nested analysis... (This may take a while)", eta_seconds=15)
                # progress_bar to determinate mode if it was indeterminate
                self.progress_bar.configure(mode="determinate")

                # Use callback
                nested_data = uni.extract_and_analyze_nested(path, progress_callback=progress_handler)

                self.progress_bar.configure(mode="determinate")
                self._update_progress(0.9, "Deep Analysis Complete")

            self._update_progress(0.9, "Searching Winget...")
            winget_url = None
            if SwitchCraftConfig.get_value("EnableWinget", True):
                from switchcraft.services.addon_service import AddonService
                winget_mod = AddonService.import_addon_module("winget", "utils.winget")
                if winget_mod and info.product_name:
                    winget = winget_mod.WingetHelper()
                    winget_url = winget.search_by_name(info.product_name)
            else:
                logger.info("Winget search disabled in settings.")

            context_data = {
                "type": info.installer_type,
                "filename": path.name,
                "install_silent": " ".join(info.install_switches) if info.install_switches else "Unknown",
                "product": info.product_name or "Unknown",
                "manufacturer": info.manufacturer or "Unknown"
            }
            if self.ai_service:
                self.ai_service.update_context(context_data)

            if hasattr(self.app, 'history_service'):
                try:
                    self.app.history_service.add_entry({
                        "filename": path.name,
                        "filepath": str(path),
                        "product": info.product_name or "Unknown",
                        "type": info.installer_type
                    })
                except Exception:
                    logger.exception("Failed to save history")

            self._update_progress(1.0, "Analysis Complete")
            self.after(0, lambda i=info, w=winget_url, bf=brute_force_data, nd=nested_data, sd=silent_disabled:
                       self._show_results(i, w, bf, nd, sd))

        except Exception as e:
            logger.exception("CRITICAL CRASH IN ANALYZER THREAD")
            err = str(e)
            self.after(0, lambda: self._show_error(f"Critical Error during analysis: {err}"))
            self._update_progress(0, "Analysis Failed")
            self._is_analyzing = False
            NotificationService.send_notification("Analysis Failed", f"Error analyzing {Path(file_path_str).name}: {err}")
        except SystemExit:
            logger.error("Analyzer thread attempted sys.exit()!")
            self._update_progress(0, "Analysis Error")
            NotificationService.send_notification("Analysis Error", "Critical system error during analysis.")

    def _show_results(self, info, winget_url, brute_force_data=None, nested_data=None, silent_disabled=None):
        self._is_analyzing = False

        self.status_bar.configure(text=i18n.get("analysis_complete"))
        self.progress_bar.grid_remove()
        self._clear_results()

        NotificationService.send_notification(
            title=i18n.get("analysis_complete") or "Analysis Complete",
            message=f"Finished analyzing {Path(info.file_path).name}"
        )

        self._add_result_row("File", info.file_path)
        self._add_result_row("Type", info.installer_type)
        self._add_result_row(i18n.get("about_dev"), info.manufacturer or "Unknown")
        self._add_result_row("Product Name", info.product_name or "Unknown")
        self._add_result_row(i18n.get("about_version"), info.product_version or "Unknown")

        self._add_separator()

        if info.installer_type and "MacOS" in info.installer_type:
            if info.bundle_id:
                self._add_copy_row("Bundle ID", info.bundle_id, "teal")
            if info.min_os_version:
                self._add_result_row("Min OS Version", info.min_os_version)

            if info.package_ids:
                self._add_separator()
                ctk.CTkLabel(self.result_frame, text="Package IDs", font=ctk.CTkFont(weight="bold")).pack(pady=5)
                for pid in info.package_ids:
                    self._add_copy_row("ID", pid, "teal")

            self._add_separator()

        if silent_disabled and silent_disabled.get("disabled"):
            warning_frame = ctk.CTkFrame(self.result_frame, fg_color="#8B0000", corner_radius=8)
            warning_frame.pack(fill="x", pady=10, padx=5)
            ctk.CTkLabel(warning_frame, text="⚠️ SILENT INSTALLATION APPEARS DISABLED", font=ctk.CTkFont(size=14, weight="bold"), text_color="white").pack(pady=5)
            ctk.CTkLabel(warning_frame, text=f"Reason: {silent_disabled.get('reason', 'Unknown')}", text_color="white").pack(pady=2)
            self._add_separator()

        if nested_data and nested_data.get("archive_type") == "PE/SFX Archive":
            sfx_frame = ctk.CTkFrame(self.result_frame, fg_color="#2980B9", corner_radius=8)
            sfx_frame.pack(fill="x", pady=10, padx=5)
            ctk.CTkLabel(sfx_frame, text="ℹ️ " + (i18n.get("sfx_notice_title") or "7-ZIP SFX DETECTED"), font=ctk.CTkFont(size=14, weight="bold"), text_color="white").pack(pady=5)
            ctk.CTkLabel(sfx_frame, text=i18n.get("sfx_notice_msg"), text_color="white", wraplength=450).pack(pady=2)
            ctk.CTkLabel(sfx_frame, text=i18n.get("sfx_howto_7zip"), text_color="#BDC3C7", font=ctk.CTkFont(size=11, slant="italic")).pack(pady=5)
            self._add_separator()

        if info.install_switches:
            self._add_separator()

            # All-in-One button with docs link
            aio_frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
            aio_frame.pack(fill="x", pady=10)

            ctk.CTkButton(aio_frame,
                          text=i18n.get("auto_deploy_btn"),
                          fg_color=("#E04F5F", "#C0392B"),
                          height=40,
                          font=ctk.CTkFont(size=14, weight="bold"),
                          command=lambda: self._run_all_in_one_flow(info)
                          ).pack(side="left", fill="x", expand=True, padx=(0,5))

            ctk.CTkButton(aio_frame,
                          text="ℹ️",
                          width=40,
                          height=40,
                          fg_color="gray",
                          command=lambda: webbrowser.open("https://github.com/FaserF/SwitchCraft/blob/main/docs/ALL_IN_ONE.md")
                          ).pack(side="right")

        if info.install_switches:
            params = " ".join(info.install_switches)
            self._add_copy_row(i18n.get("silent_install") + " (Params)", params, "green")

            btn_frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
            btn_frame.pack(fill="x", pady=5)

            self._add_full_command_row(f"{i18n.get('cmd_manual_install')} (Absolute)", info.file_path, params, is_msi=(info.installer_type == "MSI"))
            self._add_intune_row(f"{i18n.get('cmd_intune_install')} (Relative)", info.file_path, params, is_msi=(info.installer_type == "MSI"))

            ctk.CTkButton(btn_frame,
                          text=i18n.get("test_install_local"),
                          fg_color="#2ecc71",
                          width=140,
                          command=lambda: self._run_local_test_action(info.file_path, info.install_switches)
                          ).pack(side="right", padx=10)

            ctk.CTkButton(self.result_frame,
                          text=i18n.get("gen_intune_script"),
                          fg_color="purple",
                          command=lambda: self._generate_intune_script_with_info(info)).pack(pady=5, fill="x")

            ctk.CTkButton(self.result_frame,
                          text=i18n.get("create_intunewin_pkg"),
                          fg_color="#0066CC",
                          command=lambda: self._create_intunewin_action(info)).pack(pady=5, fill="x")

            # [NEW] Winget Manifest Button
            ctk.CTkButton(self.result_frame,
                          text="Create Winget Manifest",
                          fg_color=("#D35400", "#E67E22"), # Burnt Orange
                          command=lambda: self._open_manifest_dialog(info)
                          ).pack(pady=5, fill="x")
        else:
             self._add_result_row(i18n.get("silent_install"), i18n.get("no_switches"), color="orange")
             ctk.CTkButton(self.result_frame, text=i18n.get("gen_intune_script"), fg_color="purple", command=lambda: self._generate_intune_script_with_info(info)).pack(pady=5, fill="x")
             ctk.CTkButton(self.result_frame, text=i18n.get("create_intunewin_pkg"), fg_color="#0066CC", command=lambda: self._create_intunewin_action(info)).pack(pady=5, fill="x")

             if info.file_path.endswith('.exe'):
                 self._add_copy_row(i18n.get("brute_force_help"), f'"{info.file_path}" /?', "orange")

             if info.product_name:
                search_query = f"{info.product_name} silent install switches"
                search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                btn = ctk.CTkButton(self.result_frame, text=i18n.get("search_online"), fg_color="gray", command=lambda: webbrowser.open(search_url))
                btn.pack(pady=5, fill="x")

        if info.uninstall_switches:
            u_params = " ".join(info.uninstall_switches)
            self._add_copy_row(i18n.get("silent_uninstall") + " (Params)", u_params, "red")
            is_full_cmd = "msiexec" in u_params.lower() or ".exe" in u_params.lower()
            if is_full_cmd:
                self._add_copy_row("Intune Uninstall", u_params, "red")
            else:
                self._add_intune_row("Intune Uninstall", "uninstall.exe", u_params, is_msi=False, is_uninstall=True)

        if nested_data and nested_data.get("nested_executables"):
            self._add_separator()
            self._show_nested_executables(nested_data, info)

        if brute_force_data:
            self._add_separator()
            lbl = ctk.CTkLabel(self.result_frame, text=i18n.get("automated_output"), font=ctk.CTkFont(weight="bold"))
            lbl.pack(pady=5)
            log_box = ctk.CTkTextbox(self.result_frame, height=150, fg_color="black", text_color="#00FF00", font=("Consolas", 11))
            log_box.insert("0.0", brute_force_data)
            log_box.configure(state="disabled")
            log_box.pack(fill="x", pady=5)

        self._add_separator()
        winget_panel = ctk.CTkFrame(self.result_frame, fg_color=("gray90", "gray20"))
        winget_panel.pack(fill="x", pady=10)

        if winget_url:
            w_lbl = ctk.CTkLabel(winget_panel, text=i18n.get("winget_found"), font=ctk.CTkFont(weight="bold"))
            w_lbl.pack(pady=5)

            # Button Row
            btn_row = ctk.CTkFrame(winget_panel, fg_color="transparent")
            btn_row.pack(fill="x", pady=5)

            ctk.CTkButton(btn_row, text=i18n.get("view_winget"), fg_color="transparent", border_width=1, command=lambda: webbrowser.open(winget_url)).pack(side="left", padx=10, expand=True, fill="x")

            # Create Install Script Button
            def create_winget_script():
                 # Extract ID from URL if possible, otherwise ask user
                 # URL format: https://winget.run/pkg/Microsoft/PowerToys or similar
                 default_id = ""
                 if "/pkg/" in winget_url:
                     default_id = winget_url.split("/pkg/")[-1].replace("/", ".")

                 app_id = ctk.CTkInputDialog(text=i18n.get("winget_script_id_prompt"), title=i18n.get("winget_script_title")).get_input()
                 if not app_id:
                     if default_id:
                         app_id = default_id
                     else:
                         return

                 self._generate_winget_install_script(app_id, info)

            ctk.CTkButton(btn_row, text=i18n.get("winget_create_script_btn"), fg_color="green", command=create_winget_script).pack(side="left", padx=10, expand=True, fill="x")

            # Winget-AutoUpdate Hint
            hint_frame = ctk.CTkFrame(winget_panel, fg_color="transparent")
            hint_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(hint_frame, text=i18n.get("winget_tip"), text_color="gray").pack(side="left", padx=(10,0))
            link = ctk.CTkButton(hint_frame, text="Winget-AutoUpdate", fg_color="transparent", text_color="#3B8ED0", hover=False, width=120,
                                 command=lambda: webbrowser.open("https://github.com/Romanitho/Winget-AutoUpdate?tab=readme-ov-file#custom-scripts-mods-feature-for-apps"))
            link.pack(side="left")

        else:
            ctk.CTkLabel(winget_panel, text=i18n.get("winget_no_match"), text_color="gray").pack(pady=5)

        all_params = []
        if info.install_switches:
            all_params.extend(info.install_switches)
        if info.uninstall_switches:
            all_params.extend(info.uninstall_switches)

        if nested_data and nested_data.get("nested_executables"):
            for nested in nested_data["nested_executables"]:
                if nested.get("analysis") and nested["analysis"].install_switches:
                    all_params.extend(nested["analysis"].install_switches)

        if all_params:
            unique_params = sorted(list(set(all_params)), key=len)
            self._show_all_parameters(unique_params)

        if (nested_data and nested_data.get("nested_executables")) or all_params:
            ctk.CTkButton(self.result_frame, text=i18n.get("view_full_params"), fg_color="#555555", command=lambda: self._show_detailed_parameters(info, nested_data)).pack(pady=10, fill="x")

        # Batch Queue handling
        if self.queue:
            remaining = len(self.queue)
            self.status_bar.configure(text=f"Batch Processing... ({remaining} remaining)")
            self.after(1500, self._process_queue)

    def _show_nested_executables(self, nested_data, parent_info):
        """Display nested executables found inside an extracted archive."""
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

        for nested in nested_data.get("nested_executables", []):
            nested_frame = ctk.CTkFrame(self.result_frame, fg_color=("gray85", "gray25"), corner_radius=5)
            nested_frame.pack(fill="x", pady=5, padx=10)

            name_label = ctk.CTkLabel(nested_frame, text=f"📄 {nested['name']} ({nested['type']})", font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
            name_label.pack(fill="x", padx=10, pady=5)

            ctk.CTkLabel(nested_frame, text=f"Path inside archive: {nested['relative_path']}", text_color="gray", anchor="w").pack(fill="x", padx=10)

            analysis = nested.get("analysis")
            if analysis:
                if analysis.installer_type:
                    ctk.CTkLabel(nested_frame, text=f"Type: {analysis.installer_type}", text_color="cyan", anchor="w").pack(fill="x", padx=10)

                if analysis.install_switches:
                    switches_text = " ".join(analysis.install_switches)
                    switch_frame = ctk.CTkFrame(nested_frame, fg_color="transparent")
                    switch_frame.pack(fill="x", padx=10, pady=5)
                    ctk.CTkLabel(switch_frame, text="Silent Switches:", font=ctk.CTkFont(weight="bold"), text_color="green", width=120).pack(side="left")
                    switch_box = ctk.CTkTextbox(switch_frame, height=30, fg_color=("gray95", "gray15"))
                    switch_box.insert("0.0", switches_text)
                    switch_box.configure(state="disabled")
                    switch_box.pack(side="left", fill="x", expand=True, padx=5)

                    def copy_switches(text=switches_text):
                        self.clipboard_clear()
                        self.clipboard_append(text)
                        self.update()
                    ctk.CTkButton(switch_frame, text="Copy", width=60, command=copy_switches).pack(side="right")
                    full_cmd = f'"{nested["name"]}" {switches_text}'
                    ctk.CTkLabel(nested_frame, text=f"💡 Extract archive, then run: {full_cmd}", text_color="yellow", font=ctk.CTkFont(size=11), wraplength=500).pack(fill="x", padx=10, pady=5)

            elif nested.get("error"):
                ctk.CTkLabel(nested_frame, text=f"Error analyzing: {nested['error']}", text_color="red").pack(fill="x", padx=10, pady=5)

        if nested_data.get("temp_dir"):
            cleanup_frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
            cleanup_frame.pack(fill="x", pady=5)
            ctk.CTkLabel(cleanup_frame, text=f"📁 Temporary extraction: {nested_data['temp_dir']}", text_color="gray", font=ctk.CTkFont(size=10)).pack(side="left", padx=10)
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
            ctk.CTkButton(cleanup_frame, text="Clean Up", width=80, fg_color="gray", command=cleanup_temp).pack(side="right", padx=10)

    def _add_result_row(self, label, value, color=None):
        frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        ctk.CTkLabel(frame, text=f"{label}:", width=120, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(frame, text=value, anchor="w", wraplength=450, text_color=color if color else ("black", "white")).pack(side="left", fill="x", expand=True)

    def _add_copy_row(self, label, value, color_theme="blue"):
        frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        ctk.CTkLabel(frame, text=f"{label}:", width=150, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", anchor="n")
        txt = ctk.CTkTextbox(frame, height=50, fg_color=("gray95", "gray15"))
        txt.insert("0.0", value)
        txt.configure(state="disabled")
        txt.pack(side="left", fill="x", expand=True, padx=5)
        def copy():
            self.clipboard_clear()
            self.clipboard_append(value)
            self.update()
        ctk.CTkButton(frame, text="Copy", width=60, fg_color="transparent", border_width=1, command=copy).pack(side="right")

    def _add_full_command_row(self, label_text, file_path, params, is_install=True, is_msi=False):
        """Generates absolute path command for manual testing."""
        path_obj = Path(file_path)
        if is_msi:
            cmd = f'msiexec.exe /i "{path_obj.absolute()}" {params}'
        else:
            cmd = f'Start-Process -FilePath "{path_obj.absolute()}" -ArgumentList "{params}" -Wait'
        self._add_copy_row(label_text, cmd)

    def _add_intune_row(self, label_text, file_path_str, params, is_msi=False, is_uninstall=False):
        """Generates Intune-ready commands (relative filename)."""
        filename = Path(file_path_str).name
        if is_uninstall:
            cmd = f'"{filename}" {params}'
        else:
            if is_msi:
                cmd = f'msiexec /i "{filename}" {params}'
            else:
                cmd = f'"{filename}" {params}'
        self._add_copy_row(label_text, cmd, "purple")

    def _add_separator(self):
        ctk.CTkFrame(self.result_frame, height=2, fg_color="gray50").pack(fill="x", pady=10)

    def _show_all_parameters(self, params):
        self._add_separator()
        header_frame = ctk.CTkFrame(self.result_frame, fg_color=("#E8F5E9", "#1B5E20"), corner_radius=8)
        header_frame.pack(fill="x", pady=10, padx=5)
        ctk.CTkLabel(header_frame, text=f"📋 {i18n.get('found_params')}", font=ctk.CTkFont(size=14, weight="bold"), text_color=("black", "white")).pack(pady=8)
        known_params = []
        unknown_params = []
        for param in params:
            explanation = i18n.get_param_explanation(param)
            if explanation:
                known_params.append((param, explanation))
            else:
                unknown_params.append(param)
        if known_params:
            known_frame = ctk.CTkFrame(self.result_frame, fg_color=("gray90", "gray25"), corner_radius=5)
            known_frame.pack(fill="x", pady=5, padx=10)
            ctk.CTkLabel(known_frame, text=f"✓ {i18n.get('known_params')}", font=ctk.CTkFont(size=12, weight="bold"), text_color="green").pack(anchor="w", padx=10, pady=5)
            for param, explanation in known_params:
                param_row = ctk.CTkFrame(known_frame, fg_color="transparent")
                param_row.pack(fill="x", padx=10, pady=2)
                ctk.CTkLabel(param_row, text=param, font=("Consolas", 12), text_color=("#0066CC", "#66B3FF"), width=180, anchor="w").pack(side="left")
                ctk.CTkLabel(param_row, text=f"→ {explanation}", text_color=("gray40", "gray70"), anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(known_frame, text="", height=5).pack()
        if unknown_params:
            unknown_frame = ctk.CTkFrame(self.result_frame, fg_color=("gray95", "gray30"), corner_radius=5)
            unknown_frame.pack(fill="x", pady=5, padx=10)
            ctk.CTkLabel(unknown_frame, text=f"? {i18n.get('unknown_params')}", font=ctk.CTkFont(size=12, weight="bold"), text_color="orange").pack(anchor="w", padx=10, pady=5)
            unknown_text = "  ".join(unknown_params)
            ctk.CTkLabel(unknown_frame, text=unknown_text, font=("Consolas", 11), text_color=("gray50", "gray60"), wraplength=400).pack(anchor="w", padx=10, pady=(0, 8))

    def _show_detailed_parameters(self, info, nested_data):
        top = ctk.CTkToplevel(self)
        top.title(i18n.get("detailed_params_title") if "detailed_params_title" in i18n.translations.get(i18n.language) else "Detailed Parameters")
        top.geometry("700x500")
        top.transient(self.winfo_toplevel())  # Set parent window
        top.grab_set()  # Modal - keep focus
        top.lift()
        top.focus_force()
        scroll = ctk.CTkScrollableFrame(top)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        def add_section(title, filename, type_str, params, is_main=False, raw_output=None):
            if not params and not raw_output:
                return
            frame = ctk.CTkFrame(scroll, fg_color="#2B2B2B" if is_main else "#1F1F1F")
            frame.pack(fill="x", pady=5)
            head = ctk.CTkFrame(frame, fg_color="transparent")
            head.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(head, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color="cyan" if is_main else "white").pack(side="left")
            ctk.CTkLabel(head, text=f"({type_str})", text_color="gray").pack(side="left", padx=5)
            ctk.CTkLabel(frame, text=f"File: {filename}", font=("Consolas", 11), text_color="gray80").pack(anchor="w", padx=15)
            if params:
                p_text = " ".join(params)
                tb = ctk.CTkTextbox(frame, height=40, font=("Consolas", 11))
                tb.pack(fill="x", padx=10, pady=5)
                tb.insert("0.0", p_text)
            if raw_output:
                ctk.CTkLabel(frame, text="Raw Output:", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=10)
                out_box = ctk.CTkTextbox(frame, height=80, font=("Consolas", 10), text_color="gray70")
                out_box.insert("0.0", raw_output[0:2000] + "..." if len(raw_output) > 2000 else raw_output)
                out_box.configure(state="disabled")
                out_box.pack(fill="x", padx=10, pady=5)
        add_section(i18n.get("main_file") or "Main Installer", Path(info.file_path).name, info.installer_type, info.install_switches, is_main=True)
        if nested_data and nested_data.get("nested_executables"):
            for nested in nested_data["nested_executables"]:
                analysis = nested.get("analysis")
                if analysis:
                    add_section(f"Nested: {nested['name']}", nested['relative_path'], analysis.installer_type, analysis.install_switches, raw_output=nested.get("brute_force_output"))

    def _run_local_test_action(self, file_path, switches, uninstall=False):
        if not messagebox.askyesno("Test Confirmation", f"Do you want to run the {'UNINSTALL' if uninstall else 'INSTALL'} test locally?\n\nFile: {Path(file_path).name}\n\nWARNING: This will execute the file on YOUR system with Admin rights."):
            return
        path_obj = Path(file_path)
        params_str = " ".join(switches) if switches else ""
        cmd_exec = str(path_obj)
        cmd_params = params_str
        if file_path.lower().endswith(".msi"):
            cmd_exec = "msiexec.exe"
            cmd_params = f"{'/x' if uninstall else '/i'} \"{path_obj}\" {params_str}"
        try:
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", cmd_exec, cmd_params, str(path_obj.parent), 1)
            if int(ret) <= 32:
                messagebox.showerror("Execution Failed", f"Failed to start process (Code {ret})")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _generate_intune_script_with_info(self, info):
        if not info.install_switches:
            if not messagebox.askyesno("Warning", i18n.get("no_switches_intune_warn") if "no_switches_intune_warn" in i18n.translations.get(i18n.language) else "No silent switches detected. The script might require manual editing. Continue?"):
                return
        default_filename = f"Install-{info.product_name or 'App'}.ps1"
        default_filename = "".join(x for x in default_filename if x.isalnum() or x in "-_.")
        git_repo = SwitchCraftConfig.get_value("GitRepoPath")
        initial_dir = None
        if git_repo and Path(git_repo).exists():
            app_name_safe = "".join(x for x in (info.product_name or "UnknownApp") if x.isalnum() or x in "-_.")
            suggested_path = Path(git_repo) / "Apps" / app_name_safe
            if not suggested_path.exists():
                try:
                    suggested_path.mkdir(parents=True, exist_ok=True)
                except BaseException:
                    pass
            if suggested_path.exists():
                initial_dir = str(suggested_path)
        save_path = ctk.filedialog.asksaveasfilename(defaultextension=".ps1", filetypes=[("PowerShell Script", "*.ps1")], initialfile=default_filename, initialdir=initial_dir, title="Save Intune Script")
        if save_path:
            context_data = {"INSTALLER_FILE": Path(info.file_path).name, "INSTALL_ARGS": " ".join(info.install_switches) if info.install_switches else "/S", "APP_NAME": info.product_name or "Application", "PUBLISHER": info.manufacturer or "Unknown"}
            custom_template = SwitchCraftConfig.get_value("CustomTemplatePath")
            generator = TemplateGenerator(custom_template)
            if generator.generate(context_data, save_path):
                if SigningService.sign_script(save_path):
                    logger.info(f"Script signed: {save_path}")
                else:
                    logger.warning("Script verification/signing failed or skipped.")
                self.status_bar.configure(text=f"Script generated: {save_path}")
                try:
                    os.startfile(save_path)
                except BaseException:
                    pass
            else:
                messagebox.showerror("Error", "Failed to generate script template.")

    def _run_all_in_one_flow(self, info):
        if not messagebox.askyesno(i18n.get("confirm_automation"), i18n.get("confirm_automation_msg")):
            return
        if not (SwitchCraftConfig.get_value("IntuneTenantID") and SwitchCraftConfig.get_value("IntuneClientId")):
            if not messagebox.askyesno(i18n.get("config_warning"), i18n.get("config_warning_msg")):
                return
        progress_win = ctk.CTkToplevel(self)
        progress_win.title(i18n.get("deployment_title"))
        progress_win.geometry("600x400")
        txt_log = ctk.CTkTextbox(progress_win)
        txt_log.pack(fill="both", expand=True, padx=10, pady=10)
        def log(msg):
            progress_win.after(0, lambda: txt_log.insert("end", f"{msg}\n"))
            progress_win.after(0, lambda: txt_log.see("end"))
        def run_flow():
            try:
                log("--- Step 1: Generating Script ---")
                base_dir = Path(info.file_path).parent
                git_repo = SwitchCraftConfig.get_value("GitRepoPath")
                if git_repo and Path(git_repo).exists():
                    app_name_safe = "".join(x for x in (info.product_name or "UnknownApp") if x.isalnum() or x in "-_.")
                    base_dir = Path(git_repo) / "Apps" / app_name_safe
                    base_dir.mkdir(parents=True, exist_ok=True)
                    dst_installer = base_dir / Path(info.file_path).name
                    if Path(info.file_path).resolve() != dst_installer.resolve():
                        log(f"Copying installer to {base_dir}...")
                        shutil.copy2(info.file_path, dst_installer)
                        info.file_path = str(dst_installer)
                script_name = f"Install-{info.product_name or 'App'}.ps1"
                script_name = "".join(x for x in script_name if x.isalnum() or x in "-_.")
                script_path = base_dir / script_name
                context = {"INSTALLER_FILE": Path(info.file_path).name, "INSTALL_ARGS": " ".join(info.install_switches) if info.install_switches else "/S", "APP_NAME": info.product_name or "Application", "PUBLISHER": info.manufacturer or "Unknown"}
                tmpl_path = SwitchCraftConfig.get_value("CustomTemplatePath")
                gen = TemplateGenerator(tmpl_path)
                if not gen.generate(context, str(script_path)):
                    raise RuntimeError("Script generation failed")
                log(f"Script created: {script_path}")
                if SigningService.sign_script(str(script_path)):
                    log("Script signed successfully.")
                else:
                    log("Signing skipped or failed (check settings).")
                log("\n--- Step 2: Local Test ---")
                if messagebox.askyesno("Test", "Run local installation test now? (Admin rights required)"):
                    params = f'-NoProfile -ExecutionPolicy Bypass -File "{script_path}"'
                    log("Launching installer process...")
                    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "powershell.exe", params, str(base_dir), 1)
                    if int(ret) <= 32:
                        log(f"Failed to elevate/run: Code {ret}")
                        if not messagebox.askyesno("Test Failed?", "Process failed to start. Continue anyway?"):
                            return
                    else:
                        if not messagebox.askyesno("Test Verification", "Did the installation complete successfully?"):
                            log("User reported test failure.")
                            return
                        log("Test marked as Success.")
                log("\n--- Step 3: Creating Intune Package ---")
                intunewin_output = base_dir
                setup_file = script_path.name
                log(f"Packaging {setup_file}...")
                out_log = self.intune_service.create_intunewin(source_folder=str(base_dir), setup_file=setup_file, output_folder=str(intunewin_output), quiet=True)
                log(f"Tool Output:\n{out_log}")
                log("Package created.")
                pkg_name = script_path.name.replace(".ps1", ".intunewin")
                if not (intunewin_output / pkg_name).exists():
                    pkg_name = Path(info.file_path).name + ".intunewin"
                pkg_path = intunewin_output / pkg_name
                if not pkg_path.exists():
                     candidates = list(intunewin_output.glob("*.intunewin"))
                     if candidates:
                         pkg_path = candidates[0]
                     else:
                         raise FileNotFoundError("Created .intunewin not found.")
                log(f"Package: {pkg_path}")
                if SwitchCraftConfig.get_value("IntuneTenantID"):
                    log("\n--- Step 4: Uploading to Intune ---")
                    log("Authenticating...")
                    token = self.intune_service.authenticate(SwitchCraftConfig.get_value("IntuneTenantID"), SwitchCraftConfig.get_value("IntuneClientId"), SwitchCraftConfig.get_value("IntuneClientSecret"))
                    app_meta = {"displayName": info.product_name or pkg_path.stem, "description": f"Deployed by SwitchCraft. Version: {info.product_version}", "publisher": info.manufacturer or "SwitchCraft", "installCommandLine": f"powershell.exe -ExecutionPolicy Bypass -File \"{script_path.name}\"", "uninstallCommandLine": f"powershell.exe -ExecutionPolicy Bypass -File \"{script_path.name}\" -Uninstall"}
                    def prog_cb(p, m): log(f"Upload: {int(p * 100)}% - {m}")
                    app_id = self.intune_service.upload_win32_app(token, pkg_path, app_meta, progress_callback=prog_cb)
                    log(f"\nSUCCESS! App ID: {app_id}")
                    NotificationService.send_notification("Intune Upload Success", f"Uploaded {info.product_name} to Intune successfully.")
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
                    url = f"https://intune.microsoft.com/#view/Microsoft_Intune_Apps/SettingsMenu/~/0/appId/{app_id}"
                    webbrowser.open(url)
                    log("Opened Intune portal.")
                else:
                    log("\nSkipping upload (not configured).")
                    log(f"Package available at: {pkg_path}")
            except Exception as e:
                log(f"\nERROR: {e}")
                logger.exception("All-in-One Flow Failed")
                NotificationService.send_notification("Deployment Failed", f"Automation failed: {e}")
        threading.Thread(target=run_flow, daemon=True).start()

    def _create_intunewin_action(self, info):
        path = Path(info.file_path)
        script_path = path.with_suffix(".ps1")
        if not script_path.exists():
            candidates = list(path.parent.glob("*.ps1"))
            if candidates:
                script_path = candidates[0]
        setup_file = script_path if script_path.exists() else path
        if hasattr(self.app, 'intune_view'):
            self.app.intune_view.prefill_form(setup_file)
            if hasattr(self.app, 'tabview'):
                self.app.tabview.set("Intune Utility")
        else:
            logger.error("IntuneView not found on App")

    def _generate_winget_install_script(self, app_id, info):
        """Generates a small Winget install script."""
        filename = f"Install-{app_id}.ps1"
        save_path = ctk.filedialog.asksaveasfilename(defaultextension=".ps1", filetypes=[("PowerShell Script", "*.ps1")], initialfile=filename, title="Save Winget Script")

        if save_path:
            script_content = f"""<#
.SYNOPSIS
    Installs {info.product_name or app_id} via Winget using Winget-AutoUpdate or standard Winget.
.DESCRIPTION
    Generated by SwitchCraft.
    App ID: {app_id}
#>

$AppID = "{app_id}"

Write-Host "Installing $AppID via Winget..." -ForegroundColor Cyan

# Check for Winget
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {{
    Write-Error "Winget is not installed or not in PATH."
    exit 1
}}

# Install
winget install --id $AppID --exact --source winget --accept-package-agreements --accept-source-agreements --scope machine

if ($LASTEXITCODE -eq 0) {{
    Write-Host "Installation successful." -ForegroundColor Green
}} else {{
    Write-Error "Winget exited with code $LASTEXITCODE"
}}
"""
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(script_content)
                self.status_bar.configure(text=f"Script saved: {save_path}")

                # Optional: Sign it
                if SigningService.sign_script(save_path):
                     logger.info("Winget script signed.")

                os.startfile(save_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save script: {e}")

    def _open_manifest_dialog(self, info):
        # Check Config
        repo_path = SwitchCraftConfig.get_value("WingetRepoPath")
        if not repo_path:
             # Optional: Ask user if they want to configure it, or just rely on default logic in Service
             pass

        from switchcraft.gui.views.manifest_dialog import ManifestDialog
        dlg = ManifestDialog(self.winfo_toplevel(), info)
        dlg.grab_set()
