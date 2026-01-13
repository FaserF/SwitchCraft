import flet as ft
import threading
import logging
import shutil
import ctypes
import webbrowser
from pathlib import Path

from switchcraft.controllers.analysis_controller import AnalysisController, AnalysisResult
from switchcraft.utils.i18n import i18n
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.services.notification_service import NotificationService
from switchcraft.services.signing_service import SigningService
from switchcraft.utils.templates import TemplateGenerator
from switchcraft.services.intune_service import IntuneService
from switchcraft.services.addon_service import AddonService
from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper

logger = logging.getLogger(__name__)

class ModernAnalyzerView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.controller = AnalysisController()
        self.intune_service = IntuneService()
        self.analyzing = False

        # State holder for current analysis info (needed for save callbacks)
        self.current_info = None

        # UI Components
        self.drop_text = ft.Text(i18n.get("drag_drop") or "Drag & Drop Installer Here", size=20, weight=ft.FontWeight.BOLD)
        self.status_text = ft.Text(i18n.get("ready") or "Ready", size=16, color="GREY")
        self.progress_bar = ft.ProgressBar(width=400, visible=False)
        self.addon_warning = ft.Container(visible=False)

        def on_drop_click(e):
             path = FilePickerHelper.pick_file(allowed_extensions=["exe", "msi"])
             if path:
                 self.start_analysis(path)

        def on_drag_enter(e):
            self.drop_zone.border = ft.Border.all(4, "BLUE_400")
            self.drop_text.value = "Release to analyze!"
            self.update()

        def on_drag_leave(e):
            self.drop_zone.border = ft.Border.all(2, "BLUE_700")
            self.drop_text.value = i18n.get("drag_drop") or "Drag & Drop Installer Here"
            self.update()

        def on_drop(e):
            if e.files:
                for f in e.files:
                     if f.name.lower().endswith((".exe", ".msi")):
                         # Flet for Windows provides path in f.path
                         self.start_analysis(f.path)
                         break
            on_drag_leave(None)

        # Enhanced Drop Zone matching Legacy aesthetic (Logo + Blue/Purple gradient)
        self.drop_zone = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.AUTO_AWESOME, size=60, color="AMBER_400"),
                    self.drop_text,
                    ft.Text("Click to browse or Drag & Drop (Windows)", size=12, color="GREY_400"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=float("inf"),
            height=200,
            border=ft.Border.all(2, "GREY_700"), # Dashed if possible? No, solid is fine but color matters.
            border_radius=15,
            # Explicitly set gradient with known hex codes if needed, but theme colors should work.
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=["#0D47A1", "#311B92"], # Blue 900 to Deep Purple 900
            ),
            bgcolor=None, # Ensure gradient is visible
            on_click=on_drop_click,
            on_hover=lambda e: setattr(self.drop_zone, "border", ft.Border.all(4, "BLUE_400") if e.data == "true" else ft.Border.all(2, "BLUE_700")) or self.update(),
            padding=20
        )

        self.results_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=15)

        self.controls = [
                ft.Row([
                    ft.Text("Installer Analyzer", size=32, weight=ft.FontWeight.BOLD),
                    ft.Icon(ft.Icons.ANALYTICS, size=32, color="BLUE_400")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=2, thickness=1),
                self.addon_warning,
                self.drop_zone,
                ft.Container(
                    content=ft.Column([
                        self.status_text,
                        self.progress_bar,
                    ], spacing=5),
                    margin=ft.margin.only(top=10)
                ),
                ft.Divider(height=2, thickness=1),
                self.results_column,
        ]
        self._check_addon()

    def _check_addon(self):
        """Check if Advanced addon is installed and show warning if not."""
        if not AddonService().is_addon_installed("advanced"):
            self.addon_warning.content = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="WHITE", size=30),
                    ft.Column([
                        ft.Text(i18n.get("analyzer_addon_warning") or "Advanced Analysis Addon is missing!", weight=ft.FontWeight.BOLD, color="WHITE"),
                        ft.Text("Standard detection will be limited.", size=12, color="WHITE70"),
                    ], expand=True),
                    ft.ElevatedButton(
                        i18n.get("analyzer_addon_install") or "Install Now",
                        color="WHITE",
                        bgcolor="RED_700",
                        on_click=self._install_advanced_addon
                    )
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="RED_900",
                padding=15,
                border_radius=10,
                margin=ft.margin.only(bottom=15)
            )
            self.addon_warning.visible = True
            # Note: Don't call self.update() here - view isn't added to page yet

    def _install_advanced_addon(self, e):
        e.control.disabled = True
        e.control.text = "Installing..."
        self.update()

        def _run():
            success = AddonService().install_addon("advanced")
            if success:
                self._show_snack("Addon installed! Please restart SwitchCraft.", "GREEN")
                self.addon_warning.visible = False
            else:
                self._show_snack("Installation failed. Check logs.", "RED")
            e.control.disabled = False
            e.control.text = i18n.get("analyzer_addon_install") or "Install Now"
            self.update()

        threading.Thread(target=_run, daemon=True).start()

    def start_analysis(self, filepath):
        if self.analyzing:
            return

        self.analyzing = True
        self.progress_bar.visible = True
        self.status_text.value = f"Analyzing {Path(filepath).name}..."
        self.results_column.controls.clear()
        self.update()

        def _run():
            try:
                # Progress Adapter
                def on_progress(pct, msg, eta=None):
                    self.status_text.value = f"{msg} ({int(pct*100)}%)"
                    self.progress_bar.value = pct
                    self.update()

                result = self.controller.analyze_file(filepath, progress_callback=on_progress)
                self.status_text.value = "Analysis Complete"
                self.progress_bar.visible = False
                self.analyzing = False
                self._show_results(result)
            except Exception as ex:
                logger.exception("Analysis failed")
                self.status_text.value = f"Error: {ex}"
                self.status_text.color = "RED"
                self.progress_bar.visible = False
                self.analyzing = False
                self.update()

        threading.Thread(target=_run, daemon=True).start()

    def _show_results(self, result: AnalysisResult):
        self.results_column.controls.clear()
        self.current_info = result.info
        info = result.info

        # Save to History
        try:
             from switchcraft.services.history_service import HistoryService
             h_service = HistoryService()
             entry = {
                 "filename": Path(info.file_path).name,
                 "product": info.product_name or "Unknown",
                 "version": info.product_version or "Unknown",
                 "status": "Analyzed",
                 "manufacturer": info.manufacturer
             }
             h_service.add_entry(entry)
        except Exception as ex:
             logger.error(f"Failed to save history: {ex}")

        if result.error:
             self.results_column.controls.append(ft.Text(f"Analysis Error: {result.error}", color="RED", size=16))
             self.update()
             return

        # 1. Primary Info Table
        table = ft.DataTable(
            columns=[ft.DataColumn(ft.Text("Field")), ft.DataColumn(ft.Text("Value"))],
            rows=[
                ft.DataRow([ft.DataCell(ft.Text("Product")), ft.DataCell(ft.Text(info.product_name or "Unknown"))]),
                ft.DataRow([ft.DataCell(ft.Text("Version")), ft.DataCell(ft.Text(info.product_version or "Unknown"))]),
                ft.DataRow([ft.DataCell(ft.Text("Manufacturer")), ft.DataCell(ft.Text(info.manufacturer or "Unknown"))]),
                ft.DataRow([ft.DataCell(ft.Text("Type")), ft.DataCell(ft.Text(info.installer_type or "Unknown"))]),
                ft.DataRow([ft.DataCell(ft.Text("File")), ft.DataCell(ft.Text(info.file_path, size=11, font_family="Consolas"))]),
            ],
            width=float("inf"),
        )
        self.results_column.controls.append(table)

        # 2. macOS Specific Info
        if info.installer_type and "MacOS" in info.installer_type:
            mac_rows = []
            if info.bundle_id:
                mac_rows.append(ft.DataRow([ft.DataCell(ft.Text("Bundle ID")), ft.DataCell(ft.Text(info.bundle_id))]))
            if info.min_os_version:
                mac_rows.append(ft.DataRow([ft.DataCell(ft.Text("Min OS")), ft.DataCell(ft.Text(info.min_os_version))]))
            if mac_rows:
                self.results_column.controls.append(ft.DataTable(columns=[ft.DataColumn(ft.Text("macOS Property")), ft.DataColumn(ft.Text("Value"))], rows=mac_rows, width=float("inf")))

        # 3. Warnings and Notices (SFX, Disabled Silent)
        if result.silent_disabled_info and result.silent_disabled_info.get("disabled"):
            self.results_column.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.ERROR_OUTLINE, color="WHITE"), ft.Text("SILENT INSTALLATION DISABLED", weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Text(f"Reason: {result.silent_disabled_info.get('reason', 'Unknown')}", color="WHITE"),
                    ]),
                    bgcolor="RED_900", padding=10, border_radius=5
                )
            )

        if result.nested_data and result.nested_data.get("archive_type") == "PE/SFX Archive":
            self.results_column.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Icon(ft.Icons.INFO_OUTLINE, color="WHITE"), ft.Text("7-ZIP SFX DETECTED", weight=ft.FontWeight.BOLD)]),
                        ft.Text(i18n.get("sfx_notice_msg") or "This is a self-extracting archive. Silent switches might apply to the wrapper or the content inside.", size=12),
                    ]),
                    bgcolor="BLUE_900", padding=10, border_radius=5
                )
            )

        # 4. Primary Actions (All-in-One, Test Locally)
        action_buttons = ft.Row([
            ft.ElevatedButton("Auto Deploy (All-in-One)", icon=ft.Icons.AUTO_FIX_HIGH, bgcolor="RED_700", color="WHITE", on_click=lambda _: self._run_all_in_one_flow(result)),
            ft.ElevatedButton("Test Locally (Admin)", icon=ft.Icons.PLAY_ARROW, bgcolor="GREEN_700", color="WHITE", on_click=lambda _: self._run_local_test_action(info.file_path, info.install_switches)),
            ft.ElevatedButton("Winget Manifest", icon=ft.Icons.DESCRIPTION, on_click=lambda _: self._open_manifest_dialog(info)),
        ], wrap=True)
        self.results_column.controls.append(action_buttons)

        # 5. Silent Installation Parameters
        switches_str = " ".join(info.install_switches) if info.install_switches else "None detected"
        color = "GREEN" if info.install_switches else "ORANGE"

        self.results_column.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text("Silent Install Parameters", weight=ft.FontWeight.BOLD),
                    ft.TextField(value=switches_str, read_only=True, text_style=ft.TextStyle(color=color, font_family="Consolas"), suffix=ft.IconButton(ft.Icons.COPY, on_click=lambda _, s=switches_str: self._copy_to_clipboard(s))),
                ]),
                padding=10, bgcolor="SURFACE_CONTAINER_HIGHEST", border_radius=5
            )
        )

        # 6. Uninstall switches
        if info.uninstall_switches:
            un_switches = " ".join(info.uninstall_switches)
            self.results_column.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text("Silent Uninstall Parameters", weight=ft.FontWeight.BOLD, color="RED_400"),
                        ft.TextField(value=un_switches, read_only=True, text_style=ft.TextStyle(color="RED_200", font_family="Consolas"), suffix=ft.IconButton(ft.Icons.COPY, on_click=lambda _, s=un_switches: self._copy_to_clipboard(s))),
                    ]),
                    padding=10, bgcolor="SURFACE_CONTAINER_HIGHEST", border_radius=5
                )
            )

        # 7. Deployment Actions (Intune, IntuneWin)
        self.results_column.controls.append(
            ft.Row([
                ft.ElevatedButton("Generate Intune Script", icon=ft.Icons.CODE, on_click=self._on_click_create_script),
                ft.ElevatedButton("Create .intunewin", icon=ft.Icons.INVENTORY, on_click=self._on_click_create_intunewin),
                ft.ElevatedButton("Manual Commands", icon=ft.Icons.TERMINAL, on_click=self._show_manual_cmds),
            ], wrap=True)
        )

        # 8. Parameter Explanations
        if info.install_switches:
            self.results_column.controls.append(self._build_param_explanations(info.install_switches))

        # 9. Nested Data (ExpansionTile)
        if result.nested_data and result.nested_data.get("nested_executables"):
            nested_panel = ft.ExpansionTile(
                title=ft.Text("Nested Installers / SFX Content", color="CYAN", weight=ft.FontWeight.BOLD),
                subtitle=ft.Text(f"Found {len(result.nested_data['nested_executables'])} items inside", size=12),
                controls=[]
            )
            for nest in result.nested_data["nested_executables"]:
                name = nest.get("name")
                n_type = nest.get("type", "Unknown")
                details = f"Path: {nest.get('relative_path')}"
                sw_text = ""
                n_analysis = nest.get("analysis")
                if n_analysis and n_analysis.install_switches:
                    sw_text = " ".join(n_analysis.install_switches)
                    details += f"\nSwitches: {sw_text}"

                nested_panel.controls.append(
                    ft.ListTile(
                        title=ft.Text(f"{name} ({n_type})"),
                        subtitle=ft.Text(details, font_family="Consolas", size=11),
                        leading=ft.Icon(ft.Icons.SUBDIRECTORY_ARROW_RIGHT),
                        trailing=ft.IconButton(ft.Icons.COPY, on_click=lambda _, s=sw_text: self._copy_to_clipboard(s)) if sw_text else None
                    )
                )

            # Cleanup button for nested temp dir
            if result.nested_data.get("temp_dir"):
                nested_panel.controls.append(
                    ft.Padding(
                        padding=10,
                        content=ft.TextButton("Cleanup Temporary Extraction", icon=ft.Icons.DELETE_SWEEP, on_click=lambda _: self._cleanup_temp(result.nested_data))
                    )
                )
            self.results_column.controls.append(nested_panel)

        # 10. Brute Force Log
        if result.brute_force_data:
            log_panel = ft.ExpansionTile(
                title=ft.Text("Brute Force Analysis Log"),
                controls=[
                    ft.Container(
                        content=ft.Text(result.brute_force_data, font_family="Consolas", color="GREEN_400", size=11),
                        bgcolor="BLACK", padding=10, width=float("inf")
                    )
                ]
            )
            self.results_column.controls.append(log_panel)

        # 11. Winget Info
        if result.winget_url:
            self.results_column.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color="GREEN"),
                        ft.Text("Matches Winget Package!", weight=ft.FontWeight.BOLD, expand=True),
                        ft.TextButton("View on Web", on_click=lambda _: webbrowser.open(result.winget_url))
                    ]),
                    padding=10, bgcolor="GREEN_900", border_radius=5
                )
            )

        # 12. View Detailed Button
        self.results_column.controls.append(
            ft.ElevatedButton("View Detailed Analysis Data", icon=ft.Icons.ZOOM_IN, on_click=lambda _: self._show_detailed_parameters(result))
        )

        self.update()

    def _build_param_explanations(self, params):
        known = []
        unknown = []
        for p in params:
            expl = i18n.get_param_explanation(p)
            if expl:
                known.append((p, expl))
            else:
                unknown.append(p)

        controls = [ft.Text("Parameter Explanations", weight=ft.FontWeight.BOLD, size=14)]

        if known:
            k_list = ft.Column(spacing=2)
            for p, e in known:
                k_list.controls.append(ft.Text(f"• {p}: {e}", size=12, color="GREEN_200"))
            controls.append(k_list)

        if unknown:
            u_text = ", ".join(unknown)
            controls.append(ft.Text(f"Unknown: {u_text}", size=11, color="GREY_400", italic=True))

        return ft.Container(content=ft.Column(controls, spacing=5), padding=10, bgcolor="BLACK45", border_radius=5)

    def _cleanup_temp(self, nested_data):
        from switchcraft.analyzers.universal import UniversalAnalyzer
        ua = UniversalAnalyzer()
        dirs = [nested_data.get("temp_dir")]
        if nested_data.get("all_temp_dirs"):
            dirs = nested_data["all_temp_dirs"]
        for d in dirs:
            if d:
                ua.cleanup_temp_dir(d)
        self._show_snack("Cleanup complete.", "GREEN")

    def _on_click_create_script(self, e):
        if not self.current_info:
            return
        # Ask where to save
        default_name = f"Install-{self.current_info.product_name or 'App'}.ps1"
        # Sanitize
        default_name = "".join(x for x in default_name if x.isalnum() or x in "-_.")

        git_repo = SwitchCraftConfig.get_value("GitRepoPath")
        initial_dir = None
        if git_repo and Path(git_repo).exists():
            app_name_safe = "".join(x for x in (self.current_info.product_name or "UnknownApp") if x.isalnum() or x in "-_.")
            suggested_path = Path(git_repo) / "Apps" / app_name_safe
            if not suggested_path.exists():
                try:
                    suggested_path.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
            if suggested_path.exists():
                initial_dir = str(suggested_path)

        path = FilePickerHelper.save_file(
            dialog_title="Save PowerShell Script",
            file_name=default_name,
            allowed_extensions=["ps1"],
            initial_directory=initial_dir
        )

        if path:
            context = {
                "INSTALLER_FILE": Path(self.current_info.file_path).name,
                "INSTALL_ARGS": " ".join(self.current_info.install_switches) if self.current_info.install_switches else "/S",
                "APP_NAME": self.current_info.product_name or "Application",
                "PUBLISHER": self.current_info.manufacturer or "Unknown"
            }
            # Use template
            tmpl_path = SwitchCraftConfig.get_value("CustomTemplatePath")
            gen = TemplateGenerator(tmpl_path)
            if gen.generate(context, path):
                self._show_snack(f"Script saved to {path}", "GREEN")
                # Optional: Sign
                if SwitchCraftConfig.get_value("SignScripts", False):
                     if SigningService.sign_script(path):
                         self._show_snack("Script signed successfully!", "GREEN")
                     else:
                         self._show_snack("Signing failed (check logs)", "ORANGE")
            else:
                 self._show_snack("Failed to generate script", "RED")

    def _run_all_in_one_flow(self, result: AnalysisResult):
        # info unused here

        # Confirmation Dialog
        def start_flow(e):
            dlg.open = False
            self.update()
            self._execute_all_in_one_sequence(result)

        dlg = ft.AlertDialog(
            title=ft.Text("Auto-Deploy Confirmation"),
            content=ft.Text(i18n.get("confirm_automation_msg") or "This will generate a script, test it, and upload to Intune. Continue?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: setattr(dlg, "open", False)),
                ft.ElevatedButton("Start Flow", bgcolor="RED_700", color="WHITE", on_click=start_flow),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app_page.dialog = dlg
        dlg.open = True
        self.app_page.update()

    def _execute_all_in_one_sequence(self, result: AnalysisResult):
        info = result.info

        # Progress Window (Dialog with Log)
        log_text = ft.Text("Starting Sequence...\n", font_family="Consolas", size=12)
        progress_dlg = ft.AlertDialog(
            title=ft.Text("Deployment Progress"),
            content=ft.Container(
                content=ft.Column([
                    ft.ProgressBar(width=600),
                    ft.Container(
                        content=ft.Column([log_text], scroll=ft.ScrollMode.AUTO),
                        height=300, bgcolor="BLACK", padding=10, border_radius=5
                    )
                ], spacing=10),
                width=600
            ),
            actions=[ft.TextButton("Close", on_click=lambda _: setattr(progress_dlg, "open", False), visible=False)],
        )
        self.app_page.dialog = progress_dlg
        progress_dlg.open = True
        self.app_page.update()

        def log(msg):
            log_text.value += f"{msg}\n"
            self.update()

        def _bg():
            try:
                # Step 1: Script Generation
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

                context = {
                    "INSTALLER_FILE": Path(info.file_path).name,
                    "INSTALL_ARGS": " ".join(info.install_switches) if info.install_switches else "/S",
                    "APP_NAME": info.product_name or "Application",
                    "PUBLISHER": info.manufacturer or "Unknown"
                }

                tmpl_path = SwitchCraftConfig.get_value("CustomTemplatePath")
                gen = TemplateGenerator(tmpl_path)
                if not gen.generate(context, str(script_path)):
                    raise RuntimeError("Script generation failed")
                log(f"Script created: {script_path}")

                if SigningService.sign_script(str(script_path)):
                    log("Script signed successfully.")

                # Step 2: Packaging
                log("\n--- Step 2: Creating Intune Package ---")
                self.intune_service.create_intunewin(str(base_dir), script_path.name, str(base_dir), quiet=True)
                log("Packaging complete.")

                # Step 3: Upload
                if SwitchCraftConfig.get_value("IntuneTenantID"):
                    log("\n--- Step 3: Uploading to Intune ---")
                    pkg_name = script_path.name.replace(".ps1", ".intunewin")
                    pkg_path = base_dir / pkg_name

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
                        "uninstallCommandLine": f"powershell.exe -ExecutionPolicy Bypass -File \"{script_path.name}\" -Uninstall"
                    }

                    def prog_cb(p, m): log(f"Upload: {int(p * 100)}% - {m}")
                    app_id = self.intune_service.upload_win32_app(token, pkg_path, app_meta, progress_callback=prog_cb)
                    log(f"\nSUCCESS! App ID: {app_id}")
                    NotificationService.send_notification("Intune Upload Success", f"Uploaded {info.product_name} to Intune.")
                else:
                    log("\nSkipping Intune Upload (No Tenant ID configured).")

                log("\n--- ALL STEPS COMPLETED ---")
            except Exception as e:
                log(f"\nCRITICAL ERROR: {e}")
            finally:
                progress_dlg.actions[0].visible = True
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _run_local_test_action(self, file_path, switches):
        if not file_path:
            return

        def on_confirm(e):
            local_dlg.open = False
            self.update()

            path_obj = Path(file_path)
            params_str = " ".join(switches) if switches else ""
            cmd_exec = str(path_obj)
            cmd_params = params_str

            if file_path.lower().endswith(".msi"):
                cmd_exec = "msiexec.exe"
                cmd_params = f"/i \"{path_obj}\" {params_str}"

            try:
                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", cmd_exec, cmd_params, str(path_obj.parent), 1)
                if int(ret) <= 32:
                    self._show_snack(f"Failed to start process (Code {ret})", "RED")
            except Exception as ex:
                self._show_snack(str(ex), "RED")

        local_dlg = ft.AlertDialog(
            title=ft.Text("Run Test Locally"),
            content=ft.Text(f"Do you want to run the installer locally?\n\nFile: {Path(file_path).name}\n\nWARNING: This will execute with Admin rights."),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: setattr(local_dlg, "open", False)),
                ft.ElevatedButton("Run Now (Admin)", bgcolor="GREEN_700", color="WHITE", on_click=on_confirm),
            ],
        )
        self.app_page.dialog = local_dlg
        local_dlg.open = True
        self.app_page.update()

    def _open_manifest_dialog(self, info):
        # Placeholder for Winget Manifest Creation (Similar to Legacy)
        self._show_snack("Winget Manifest Creation not yet fully ported, but coming soon!", "BLUE")

    def _show_detailed_parameters(self, result: AnalysisResult):
        info = result.info
        content = ft.Column([
            ft.Text(f"Analysis Details for {Path(info.file_path).name}", weight=ft.FontWeight.BOLD, size=18),
            ft.Markdown(f"**Installer Type:** {info.installer_type}\n**Product:** {info.product_name}\n**Version:** {info.product_version}"),
            ft.Divider(),
            ft.Text("Raw Analysis Output:", weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Column([
                    ft.Text(result.brute_force_data or "No raw data available.", font_family="Consolas", size=10),
                ], scroll=ft.ScrollMode.AUTO),
                height=300, bgcolor="BLACK", padding=10, border_radius=5, width=float("inf")
            )
        ], scroll=ft.ScrollMode.AUTO, tight=True)

        dlg = ft.AlertDialog(
            content=content,
            actions=[ft.TextButton("Close", on_click=lambda _: setattr(dlg, "open", False))],
        )
        self.app_page.dialog = dlg
        dlg.open = True
        self.app_page.update()

    def _on_click_create_intunewin(self, e):
        # We need a source folder and output. For simplicity, use installer dir and create alongside.
        if not self.current_info:
            return

        installer = Path(self.current_info.file_path)
        source = installer.parent
        output = source
        setup_file = installer.name

        self._show_snack("Creating .intunewin package...", "BLUE")

        def _bg():
            try:
                self.intune_service.create_intunewin(str(source), setup_file, str(output), quiet=True)
                self._show_snack("Package Created Successfully!", "GREEN")
            except Exception as ex:
                self._show_snack(f"Packaging Failed: {ex}", "RED")

        threading.Thread(target=_bg, daemon=True).start()

    def _show_manual_cmds(self, e):
        if not self.current_info:
            return
        switches = " ".join(self.current_info.install_switches)
        path = self.current_info.file_path

        dlg = ft.AlertDialog(
            title=ft.Text("Manual Commands"),
            content=ft.Column([
                ft.Text("CMD / Batch:", weight=ft.FontWeight.BOLD),
                ft.TextField(value=f'"{path}" {switches}', read_only=True, suffix=ft.IconButton(ft.Icons.COPY, on_click=lambda _, cmd=f'"{path}" {switches}': self._copy_to_clipboard(cmd))),
                ft.Text("PowerShell:", weight=ft.FontWeight.BOLD),
                ft.TextField(value=f'Start-Process -FilePath "{path}" -ArgumentList "{switches}" -Wait', read_only=True, suffix=ft.IconButton(ft.Icons.COPY, on_click=lambda _, cmd=f'Start-Process -FilePath "{path}" -ArgumentList "{switches}" -Wait': self._copy_to_clipboard(cmd))),
            ], height=240, spacing=10),
        )
        self.app_page.dialog = dlg
        dlg.open = True
        self.app_page.update()

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        try:
            import pyperclip
            pyperclip.copy(text)
            self._show_snack("Copied to clipboard!", "GREEN_700")
        except ImportError:
            try:
                import subprocess
                subprocess.run(['clip'], input=text.encode('utf-8'), check=True)
                self._show_snack("Copied to clipboard!", "GREEN_700")
            except Exception:
                self._show_snack("Failed to copy", "RED")

    def _show_snack(self, msg, color="GREEN"):
        try:
            self.app_page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.app_page.snack_bar.open = True
            self.app_page.update()
        except Exception:
             pass
