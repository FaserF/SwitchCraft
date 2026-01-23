import flet as ft
import threading
import logging
import shutil
import ctypes

import requests
import tempfile
from pathlib import Path

from switchcraft.controllers.analysis_controller import AnalysisController, AnalysisResult
from switchcraft.utils.i18n import i18n
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.services.notification_service import NotificationService
from switchcraft.services.signing_service import SigningService
from switchcraft.utils.templates import TemplateGenerator
from switchcraft.services.intune_service import IntuneService
from switchcraft.services.winget_manifest_service import WingetManifestService
from switchcraft.services.addon_service import AddonService
from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
from switchcraft.gui_modern.utils.flet_compat import create_tabs
from switchcraft.gui_modern.utils.view_utils import ViewMixin

# Try to import flet_dropzone for native file DnD
try:
    import flet_dropzone as ftd
    HAS_DROPZONE = False # Forced False to fix compiled exe issues
except ImportError:
    HAS_DROPZONE = False
    ftd = None

logger = logging.getLogger(__name__)

class ModernAnalyzerView(ft.Column, ViewMixin):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.controller = AnalysisController()
        self.intune_service = IntuneService()
        self.winget_service = WingetManifestService()
        self.addon_service = AddonService()
        self.analyzing = False

        # State holder for current analysis info (needed for save callbacks)
        self.current_info = None

        # UI Components
        self.drop_text = ft.Text(i18n.get("drag_drop") or "Drag & Drop Installer Here", size=20, weight=ft.FontWeight.BOLD)
        self.status_text = ft.Text(i18n.get("ready") or "Ready", size=16, color="ON_SURFACE_VARIANT")
        self.progress_bar = ft.ProgressBar(width=400, visible=False)
        self.addon_warning = ft.Container(visible=False)

        def on_drop_click(e):
             path = FilePickerHelper.pick_file(allowed_extensions=["exe", "msi", "ps1", "bat", "cmd", "vbs", "msp"])
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
        # Show DnD hint only if dropzone is available
        drop_hint = "Click to browse or Drag & Drop" if HAS_DROPZONE else "Click to browse"

        drop_container = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.AUTO_AWESOME, size=60, color="AMBER_400"),
                    self.drop_text,
                    ft.Text(drop_hint, size=12, color="GREY_400"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            width=float("inf"),
            height=200,
            border=ft.Border.all(2, "GREY_700"),
            border_radius=15,
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=["#0D47A1", "#311B92"],
            ),
            bgcolor=None,
            on_click=on_drop_click,
            # Make sure the container itself accepts dropped files if possible,
            # though page.on_file_drop is global.
        )

        self.drop_zone = drop_container

        # Wrap with Dropzone if available for native file DnD
        if HAS_DROPZONE and ftd:
            def handle_dropzone_drop(e):
                if e.files:
                    for fpath in e.files:
                        if fpath.lower().endswith((".exe", ".msi")):
                            self.start_analysis(fpath)
                            break

            self.drop_zone = ftd.Dropzone(
                content=drop_container,
                on_dropped=handle_dropzone_drop,
                on_entered=lambda e: setattr(drop_container, "border", ft.Border.all(4, "GREEN_400")) or self.update(),
                on_exited=lambda e: setattr(drop_container, "border", ft.Border.all(2, "GREY_700")) or self.update(),
            )
        else:
            self.drop_zone = drop_container

        # URL Download UI
        self.url_field = ft.TextField(
            label=i18n.get("download_url") or "Direct Download URL",
            hint_text="https://example.com/installer.exe",
            expand=True,
            border_radius=8
        )
        self.url_download_progress = ft.ProgressBar(width=400, visible=False)
        self.url_download_status = ft.Text("", italic=True, size=12)

        url_content = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.CLOUD_DOWNLOAD, size=60, color="ORANGE_400"),
                ft.Text(
                    i18n.get("download_from_web") or "Download from Web",
                    size=20,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Text(
                    i18n.get("enter_direct_link") or "Enter a direct link to an .exe or .msi file",
                    size=12,
                    color="GREY_400"
                ),
                ft.Container(height=10),
                ft.Row([
                    self.url_field,
                    ft.FilledButton(
                        content=ft.Row([ft.Icon(ft.Icons.DOWNLOAD), ft.Text(i18n.get("download_and_analyze") or "Download & Analyze")], alignment=ft.MainAxisAlignment.CENTER),
                        on_click=self._start_url_download
                    )
                ], spacing=10),
                self.url_download_progress,
                self.url_download_status
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            padding=20,
            alignment=ft.Alignment(0, 0)
        )

        # Tab container
        self.source_tab_body = ft.Container(content=self.drop_zone, expand=True)

        def on_source_tab_change(e):
            idx = int(e.control.selected_index)
            if idx == 0:
                self.source_tab_body.content = self.drop_zone
            else:
                self.source_tab_body.content = url_content
            self.source_tab_body.update()

        source_tabs = create_tabs(
            tabs=[
                ft.Tab(
                    label=i18n.get("local_file") or "Local File",
                    icon=ft.Icons.COMPUTER
                ),
                ft.Tab(
                    label=i18n.get("download_url") or "URL Download",
                    icon=ft.Icons.LINK
                )
            ],
            selected_index=0,
            animation_duration=300,
        )
        source_tabs.on_change = on_source_tab_change

        self.results_column = ft.Column(expand=False, spacing=15)

        self.controls = [
            ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Row([
                        ft.Text(i18n.get("analyzer_view_title"), size=32, weight=ft.FontWeight.BOLD),
                        ft.Icon(ft.Icons.ANALYTICS, size=32, color="BLUE_400")
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=2, thickness=1),
                    self.addon_warning,
                    source_tabs,
                    self.source_tab_body,
                    ft.Container(
                        content=ft.Column([
                            self.status_text,
                            self.progress_bar,
                        ], spacing=5),
                        margin=ft.Margin.only(top=10)
                    ),
                    ft.Divider(height=2, thickness=1),
                    self.results_column,
                ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True),
                expand=True
            )
        ]
        self._check_addon()

    def did_mount(self):
        # Register global file drop handler when this view is active
        self.app_page.on_file_drop = self._on_global_file_drop
        if self.page:
             self.app_page.update()

    def will_unmount(self):
        # Unregister handler to avoid conflicts
        self.app_page.on_file_drop = None

    def _on_global_file_drop(self, e):
        # Handle file drop on the window
        files = e.files
        if files:
            logger.info(f"File drop detected: {len(files)} files")
            for f in files:
                logger.debug(f"Dropped file: {f.name}, Path: {getattr(f, 'path', 'No Path')}")
                # Flet for Windows provides path in f.path
                file_path = getattr(f, "path", None)
                if file_path:
                     if file_path.lower().endswith((".exe", ".msi", ".ps1", ".bat", ".cmd", ".vbs", ".msp")):
                         logger.info(f"Starting analysis for: {file_path}")
                         self.start_analysis(file_path)
                         break
                     else:
                         logger.warning(f"File ignored (extension mismatch): {file_path}")
                else:
                    logger.warning(f"File object has no path: {f}")


    def _start_url_download(self, e):
        """Download installer from URL and start analysis."""
        url = self.url_field.value.strip()
        if not url:
            self._show_snack(
                i18n.get("urls_required") or "Please enter a URL",
                "RED"
            )
            return

        # Validate URL

        if not url.startswith(("http://", "https://")):
            self._show_snack(i18n.get("invalid_url_format") or "Invalid URL format", "RED")
            return

        self.url_download_progress.visible = True
        self.url_download_progress.value = None  # Indeterminate
        self.url_download_status.value = i18n.get("starting_download") or "Starting download..."
        self.url_download_status.color = "BLUE"
        self.update()

        def _bg():
            temp_dir = None
            analysis_started = False
            try:
                # Get filename from URL
                raw_filename = url.split("/")[-1].split("?")[0]
                # Sanitize filename (basic)
                keep_chars = ("-", "_", ".")
                filename = "".join(c for c in raw_filename if c.isalnum() or c in keep_chars).strip()

                if not filename or not filename.lower().endswith((".exe", ".msi")):
                    filename = "installer.exe"

                # Create temp directory
                temp_dir = tempfile.mkdtemp(prefix="switchcraft_")
                temp_path = Path(temp_dir) / filename

                # Download with progress
                with requests.get(url, stream=True, timeout=60) as response:
                    response.raise_for_status()

                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0

                    with open(temp_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    pct = downloaded / total_size
                                    self.url_download_progress.value = pct
                                    self.url_download_status.value = f"{i18n.get('downloading') or 'Downloading'}: {int(pct*100)}%"
                                    self.update()

                self.url_download_progress.visible = False
                self.url_download_status.value = f"{i18n.get('downloaded') or 'Downloaded'}: {filename}"
                self.url_download_status.color = "GREEN"
                self.update()

                # Start analysis with downloaded file
                # Pass temp_dir as cleanup_path so the whole directory is removed
                self.start_analysis(str(temp_path), cleanup_path=str(temp_dir))
                analysis_started = True

            except requests.exceptions.RequestException as ex:
                self.url_download_progress.visible = False
                self.url_download_status.value = f"Download failed: {ex}"
                self.url_download_status.color = "RED"
                self.update()
                logger.error(f"URL download failed: {ex}")
            except Exception as ex:
                self.url_download_progress.visible = False
                self.url_download_status.value = f"Error: {ex}"
                self.url_download_status.color = "RED"
                self.update()
                logger.error(f"URL download error: {ex}")
            finally:
                # If analysis didn't start (e.g. download failed), clean up temp dir immediately
                if temp_dir and not analysis_started:
                     try:
                         shutil.rmtree(temp_dir, ignore_errors=True)
                     except Exception as e:
                         logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")

        threading.Thread(target=_bg, daemon=True).start()

    def _check_addon(self):
        """Check if Advanced addon is installed and show warning if not."""
        if not self.addon_service.is_addon_installed("advanced"):
            self.addon_warning.content = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="WHITE", size=30),
                    ft.Column([
                        ft.Text(i18n.get("analyzer_addon_warning") or "Advanced Analysis Addon is missing!", weight=ft.FontWeight.BOLD, color="WHITE"),
                        ft.Text("Standard detection will be limited.", size=12, color="WHITE70"),
                    ], expand=True),
                    ft.FilledButton(
                        content=ft.Text(i18n.get("analyzer_addon_install") or "Install via Settings"),
                        color="WHITE",
                        bgcolor="RED_700",
                        on_click=self._go_to_settings
                    )
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="RED_900",
                padding=15,
                border_radius=10,
                margin=ft.Margin.only(bottom=15)
            )
            self.addon_warning.visible = True
            # Note: Don't call self.update() here - view isn't added to page yet

    def _go_to_settings(self, e):
        # Redirect to Addon Manager (Settings -> Help)
        if hasattr(self.page, 'switchcraft_app') and hasattr(self.page.switchcraft_app, 'goto_tab'):
            from switchcraft.gui_modern.nav_constants import NavIndex
            self.page.switchcraft_app.goto_tab(NavIndex.SETTINGS_HELP)
        else:
            self._show_snack("Please go to Settings > Help manually.", "ORANGE")

    def _install_advanced_addon(self, e):
        e.control.disabled = True
        e.control.text = "Installing..."
        self.update()

        def _run():
            import sys
            # Locate bundled addon
            if getattr(sys, 'frozen', False):
                 base = Path(sys._MEIPASS) / "assets" / "addons"
            else:
                 # src/switchcraft/gui_modern/views/analyzer_view.py -> src/switchcraft/assets/addons
                 base = Path(__file__).parent.parent.parent / "assets" / "addons"

            addon_zip = base / "advanced.zip"
            if not addon_zip.exists():
                 # Fallback/Error
                 self._show_snack(f"Addon file not found: {addon_zip}", "RED")
                 success = False
            else:
                 success = AddonService().install_addon(str(addon_zip))
            if success:
                self._show_snack("Addon installed! Please restart SwitchCraft.", "GREEN")
                self.addon_warning.visible = False
            else:
                self._show_snack("Installation failed. Check logs.", "RED")
            e.control.disabled = False
            e.control.text = i18n.get("analyzer_addon_install") or "Install Now"
            self.update()

        threading.Thread(target=_run, daemon=True).start()

    def start_analysis(self, filepath, cleanup_path=None):
        if self.analyzing:
            return

        self.analyzing = True
        self.progress_bar.visible = True
        self.status_text.value = f"Analyzing {Path(filepath).name}..."
        self.results_column.controls.clear()

        # Sync with global progress
        if hasattr(self.page, "switchcraft_app"):
            self.page.switchcraft_app.set_progress(value=0, visible=True)
        else:
            self.update()

        def _run():
            try:
                # Progress Adapter
                def on_progress(pct, msg, eta=None):
                    self.status_text.value = f"{msg} ({int(pct*100)}%)"
                    self.progress_bar.value = pct
                    if hasattr(self.page, "switchcraft_app"):
                        self.page.switchcraft_app.set_progress(value=pct, visible=True)
                    else:
                        self.update()

                result = self.controller.analyze_file(filepath, progress_callback=on_progress)
                self.status_text.value = "Analysis Complete"
                self.progress_bar.visible = False
                self.analyzing = False

                # Update global progress
                if hasattr(self.page, "switchcraft_app"):
                    self.page.switchcraft_app.set_progress(visible=False)

                self._show_results(result)
            except Exception as ex:
                logger.exception("Analysis failed")
                self.status_text.value = f"Error: {ex}"
                self.status_text.color = "RED"
                self.progress_bar.visible = False
                self.analyzing = False

                if hasattr(self.page, "switchcraft_app"):
                    self.page.switchcraft_app.set_progress(visible=False)
                else:
                    self.update()

            finally:
                if cleanup_path:
                    try:
                        import os
                        if os.path.isdir(cleanup_path):
                            shutil.rmtree(cleanup_path, ignore_errors=True)
                        elif os.path.exists(cleanup_path):
                            os.remove(cleanup_path)
                    except Exception as ex:
                        logger.warning(f"Failed to cleanup temp analysis file {cleanup_path}: {ex}")

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
            columns=[ft.DataColumn(ft.Text(i18n.get("table_header_field") or "Field")), ft.DataColumn(ft.Text(i18n.get("table_header_value") or "Value"))],
            rows=[
                ft.DataRow([ft.DataCell(ft.Text(i18n.get("field_product") or "Product")), ft.DataCell(ft.Text(info.product_name or "Unknown"))]),
                ft.DataRow([ft.DataCell(ft.Text(i18n.get("field_version") or "Version")), ft.DataCell(ft.Text(info.product_version or "Unknown"))]),
                ft.DataRow([ft.DataCell(ft.Text(i18n.get("field_manufacturer") or "Manufacturer")), ft.DataCell(ft.Text(info.manufacturer or "Unknown"))]),
                ft.DataRow([ft.DataCell(ft.Text(i18n.get("field_type") or "Type")), ft.DataCell(ft.Text(info.installer_type or "Unknown"))]),
                ft.DataRow([ft.DataCell(ft.Text(i18n.get("field_file") or "File")), ft.DataCell(ft.Text(info.file_path, size=11, font_family="Consolas"))]),
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
                        ft.Container(
                            content=ft.Text(i18n.get("sfx_notice_msg") or "This is a self-extracting archive. Silent switches might apply to the wrapper or the content inside.", size=12),
                            expand=True,
                            width=None
                        ),
                    ]),
                    bgcolor="BLUE_900", padding=10, border_radius=5
                )
            )

        action_buttons = ft.Row([
            ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.AUTO_FIX_HIGH), ft.Text(i18n.get("btn_auto_deploy") or "Auto Deploy (All-in-One)")], alignment=ft.MainAxisAlignment.CENTER), style=ft.ButtonStyle(bgcolor="RED_700", color="WHITE"), on_click=lambda _: self._run_all_in_one_flow(result)),
            ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.PLAY_ARROW), ft.Text(i18n.get("btn_test_locally") or "Test Locally (Admin)")], alignment=ft.MainAxisAlignment.CENTER), style=ft.ButtonStyle(bgcolor="GREEN_700", color="WHITE"), on_click=lambda _: self._run_local_test_action(info.file_path, info.install_switches)),
            ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.DESCRIPTION), ft.Text(i18n.get("btn_winget_manifest") or "Winget Manifest")], alignment=ft.MainAxisAlignment.CENTER), on_click=lambda _: self._open_manifest_dialog(info)),
        ], wrap=True)
        self.results_column.controls.append(action_buttons)

        # 5. Silent Installation Parameters
        switches_str = " ".join(info.install_switches) if info.install_switches else "None detected"
        color = "GREEN" if info.install_switches else "ORANGE"

        self.results_column.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text(i18n.get("silent_switches") or "Silent Install Parameters", weight=ft.FontWeight.BOLD),
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
                        ft.Text(i18n.get("silent_uninstall") or "Silent Uninstall Parameters", weight=ft.FontWeight.BOLD, color="RED_400"),
                        ft.TextField(value=un_switches, read_only=True, text_style=ft.TextStyle(color="RED_200", font_family="Consolas"), suffix=ft.IconButton(ft.Icons.COPY, on_click=lambda _, s=un_switches: self._copy_to_clipboard(s))),
                    ]),
                    padding=10, bgcolor="SURFACE_CONTAINER_HIGHEST", border_radius=5
                )
            )

        # 7. Deployment Actions (Intune, IntuneWin)
        self.results_column.controls.append(
            ft.Row([
                ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.CODE), ft.Text(i18n.get("generate_intune_script") or "Generate Intune Script")], alignment=ft.MainAxisAlignment.CENTER), on_click=self._on_click_create_script),
                ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.INVENTORY), ft.Text(i18n.get("btn_create_intunewin") or "Create .intunewin")], alignment=ft.MainAxisAlignment.CENTER), on_click=self._on_click_create_intunewin),
                ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.TERMINAL), ft.Text(i18n.get("btn_manual_cmds") or "Manual Commands")], alignment=ft.MainAxisAlignment.CENTER), on_click=self._show_manual_cmds),
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
                    ft.Container(
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
                        ft.TextButton(i18n.get("view_winget") or "View on Web", on_click=lambda _: self._launch_url(result.winget_url))
                    ]),
                    padding=10, bgcolor="GREEN_900", border_radius=5
                )
            )

        # 12. View Detailed Button
        self.results_column.controls.append(
            ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.ZOOM_IN), ft.Text(i18n.get("view_full_params") or "View Detailed Analysis Data")], alignment=ft.MainAxisAlignment.CENTER), on_click=lambda _: self._show_detailed_parameters(result))
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

        controls = [ft.Text(i18n.get("known_params") or "Parameter Explanations", weight=ft.FontWeight.BOLD, size=14)]

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
                ft.TextButton("Cancel", on_click=lambda _: self._close_dialog(dlg)),
                ft.FilledButton(content=ft.Text("Start Flow"), bgcolor="RED_700", color="WHITE", on_click=start_flow),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._open_dialog_safe(dlg)

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
            actions=[ft.TextButton("Close", on_click=lambda _: self._close_dialog(progress_dlg), visible=False)],
        )
        self._open_dialog_safe(progress_dlg)

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
                self._add_history_entry(info, "Packaged")

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
                    self._add_history_entry(info, "Deployed")
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
        """
        Prompt the user to run the installer locally with elevated privileges and execute it if confirmed.

        If the current process lacks administrative rights, shows a confirmation dialog that attempts to restart the application as Administrator (Windows only). If already running as admin, shows a confirmation dialog to run the installer now; constructs an msiexec command for .msi files or uses the installer path directly for other file types, appends provided switches, and launches the command via a UAC-elevated ShellExecute call. Displays user-facing status/snack messages for failures or unsupported platforms.

        Parameters:
            file_path (str): Path to the installer file to run.
            switches (Sequence[str]): Command-line switches/arguments to pass to the installer.
        """
        if not file_path:
            return

        # Check if we are already admin
        is_admin = False
        try:
            import sys
            if sys.platform == "win32":
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                # Assume non-windows doesn't need elevation or handled differently
                is_admin = True
        except Exception:
            pass

        if not is_admin:
            def on_restart_confirm(e):
                """
                Attempt to relaunch the application with elevated (administrator) privileges on Windows and exit the current process.

                Closes the restart dialog, performs preparatory resource cleanup, launches a new process with administrator rights, and then terminates the current process. If the platform is not Windows or elevation fails, a user-facing error snack is shown instead of relaunching.

                Parameters:
                    e: The confirmation event from the restart dialog (unused beyond dismissing the dialog).
                """
                restart_dlg.open = False
                self.app_page.update()

                # Restart as admin
                try:
                    import sys
                    import time
                    import gc
                    import logging

                    if sys.platform != "win32":
                         self._show_snack("Elevation only supported on Windows.", "RED")
                         return

                    # 1. Close all file handles and release resources
                    try:
                        logging.shutdown()
                    except Exception:
                        pass

                    # 2. Force garbage collection
                    gc.collect()

                    # 3. Small delay to allow file handles to be released
                    time.sleep(0.2)

                    executable = sys.executable
                    params = f'"{sys.argv[0]}"'
                    if len(sys.argv) > 1:
                        params += " " + " ".join(f'"{a}"' for a in sys.argv[1:])

                    # 4. Launch as admin
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)

                    # 5. Give the new process a moment to start
                    time.sleep(0.3)

                    # 6. Exit
                    sys.exit(0)
                except Exception as ex:
                    self._show_snack(f"Failed to elevate: {ex}", "RED")

            restart_dlg = ft.AlertDialog(
                title=ft.Text(i18n.get("admin_required_title") or "Admin Rights Required"),
                content=ft.Text(i18n.get("admin_required_msg") or "Local testing requires administrative privileges. Would you like to restart SwitchCraft as Administrator?"),
                actions=[
                    ft.TextButton(i18n.get("btn_cancel") or "Cancel", on_click=lambda _: self._close_dialog(restart_dlg)),
                    ft.FilledButton(content=ft.Text(i18n.get("btn_restart_admin") or "Restart as Admin"), bgcolor="RED_700", color="WHITE", on_click=on_restart_confirm),
                ],
            )
            self._open_dialog_safe(restart_dlg)
            return

        # If already admin, proceed with normal confirmation
        def on_confirm(e):
            local_dlg.open = False
            self.app_page.update()

            path_obj = Path(file_path)
            params_str = " ".join(switches) if switches else ""
            cmd_exec = str(path_obj)
            cmd_params = params_str

            if file_path.lower().endswith(".msi"):
                cmd_exec = "msiexec.exe"
                cmd_params = f"/i \"{path_obj}\" {params_str}"

            if sys.platform != "win32":
                self._show_snack("Local testing is only supported on Windows.", "RED")
                return

            try:
                # We already checked for admin, but runas ensures UAC if somehow needed
                ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", cmd_exec, cmd_params, str(path_obj.parent), 1)
                if int(ret) <= 32:
                    self._show_snack(f"Failed to start process (Code {ret})", "RED")
            except Exception as ex:
                self._show_snack(str(ex), "RED")

        local_dlg = ft.AlertDialog(
            title=ft.Text(i18n.get("run_local_test") or "Run Test Locally"),
            content=ft.Text(f"{i18n.get('confirm_local_test_msg') or 'Do you want to run the installer locally?'}\n\nFile: {Path(file_path).name}"),
            actions=[
                ft.TextButton(i18n.get("btn_cancel") or "Cancel", on_click=lambda _: self._close_dialog(local_dlg)),
                ft.FilledButton(content=ft.Text(i18n.get("btn_run_now") or "Run Now (Admin)"), bgcolor="GREEN_700", color="WHITE", on_click=on_confirm),
            ],
        )
        self._open_dialog_safe(local_dlg)

    def _open_manifest_dialog(self, info):
        # Quick manifest generation using WingetManifestService
        def generate_local(e):
            try:
                # Prepare metadata for service
                meta = {
                    "PackageIdentifier": f"{info.manufacturer or 'Unknown'}.{info.product_name or 'App'}",
                    "PackageVersion": info.product_version or "1.0.0",
                    "Publisher": info.manufacturer or "Unknown",
                    "PackageName": info.product_name or "App",
                    "InstallerType": info.installer_type or "exe",
                    "Installers": [{
                        "Architecture": "x64",
                        "InstallerUrl": f"file:///{info.file_path.replace('\\', '/')}",
                        "InstallerSha256": "0000000000000000000000000000000000000000000000000000000000000000", # Placeholder
                        "InstallerType": info.installer_type or "exe",
                        "Scope": "machine"
                    }]
                }

                # Sanitize PackageIdentifier (winget prefers no spaces)
                meta["PackageIdentifier"] = meta["PackageIdentifier"].replace(" ", "")
                meta["Publisher"] = meta["Publisher"].replace(" ", "")

                out_dir = self.winget_service.generate_manifests(meta)
                self._show_snack(f"Manifests generated in: {out_dir}", "GREEN")

                # Close dialog
                dlg.open = False
                self.app_page.update()

                self._open_path(out_dir)
            except Exception as ex:
                self._show_snack(f"Generation failed: {ex}", "RED")

        def open_winget_manager(e):
            dlg.open = False
            self.app_page.update()
            # If we had a router, we would navigate. For now, we just suggest it
            self._show_snack("Please use the 'WingetCreate Manager' from the side menu for advanced options.", "BLUE")

        dlg = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.DESCRIPTION, color="BLUE"), ft.Text("Winget Manifest Creation")]),
            content=ft.Column([
                ft.Text("Quickly generate a local manifest structure based on analysis results."),
                ft.Text(f"Target: {info.manufacturer}.{info.product_name}", size=12, italic=True),
                ft.Container(height=5),
                ft.Row([
                    ft.Icon(ft.Icons.WARNING_AMBER, color="ORANGE", size=16),
                    ft.Text("Note: Manifests use a placeholder SHA256. Manual update required before submission.", size=11, color="ORANGE", italic=True)
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ], height=110, tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self._close_dialog(dlg)),
                ft.TextButton("Open Manager", on_click=open_winget_manager),
                ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.BUILD), ft.Text("Generate Locals")], alignment=ft.MainAxisAlignment.CENTER), on_click=generate_local, bgcolor="BLUE_700", color="WHITE"),
            ],
        )

        self._open_dialog_safe(dlg)

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

        def close_dlg(e):
            dlg.open = False
            self.app_page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(i18n.get("detailed_params_title") or "Detailed Parameters Analysis"),
            content=content,
            actions=[ft.TextButton(i18n.get("btn_cancel") or "Close", on_click=close_dlg)],
        )

        self._open_dialog_safe(dlg)

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard using Flet first, then fallbacks."""
        # 1. Try Flet Page (Best for Web)
        if self.app_page:
            try:
                self.app_page.set_clipboard(text)
                self._show_snack("Copied to clipboard!", "GREEN_700")
                return
            except Exception:
                pass

        # 2. Try Pyperclip
        try:
            import pyperclip
            pyperclip.copy(text)
            self._show_snack("Copied to clipboard!", "GREEN_700")
        except ImportError:
            # 3. Fallback to Windows Clip via ShellUtils
            try:
                from switchcraft.utils.shell_utils import ShellUtils
                ShellUtils.run_command(['clip'], input=text.encode('utf-8'), check=True, silent=True)
                self._show_snack("Copied to clipboard!", "GREEN_700")
            except Exception:
                self._show_snack("Failed to copy", "RED")

    def _on_click_create_intunewin(self, e):
        # We need a source folder and output. For simplicity, use installer dir and create alongside.
        if not self.current_info:
            return

        installer = Path(self.current_info.file_path)
        source = installer.parent
        output = source
        setup_file = installer.name

        # Show progress
        self._show_snack(i18n.get("creating_intunewin") or "Creating .intunewin package...", "BLUE")

        def _bg():
            try:
                self.intune_service.create_intunewin(str(source), setup_file, str(output), quiet=True)

                # Find the created file
                expected_intunewin = source / (installer.stem + ".intunewin")
                if expected_intunewin.exists():
                    output_file = str(expected_intunewin)
                else:
                    # Search for any .intunewin in folder
                    intunewin_files = list(source.glob("*.intunewin"))
                    output_file = str(intunewin_files[0]) if intunewin_files else str(source)

                # Show success dialog
                def open_folder(e):
                    try:
                        self._open_path(str(source))
                    except Exception as ex:
                        self._show_snack(f"Failed to open folder: {ex}", "RED")

                    dlg.open = False
                    self.app_page.update()

                def close_dlg(e):
                    dlg.open = False
                    self.app_page.update()

                dlg = ft.AlertDialog(
                    title=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color="GREEN", size=30),
                        ft.Text(i18n.get("package_created_title") or "Package Created!", weight=ft.FontWeight.BOLD)
                    ]),
                    content=ft.Column([
                        ft.Text(i18n.get("intunewin_created_success") or "Your .intunewin package was created successfully!"),
                        ft.Container(height=10),
                        ft.Text(i18n.get("location") or "Location:", weight=ft.FontWeight.BOLD),
                        ft.Text(output_file, size=12, selectable=True, color="GREY_400")
                    ], tight=True),
                    actions=[
                        ft.TextButton(i18n.get("btn_close") or "Close", on_click=close_dlg),
                        ft.FilledButton(
                            content=ft.Row([ft.Icon(ft.Icons.FOLDER_OPEN), ft.Text(i18n.get("open_folder") or "Open Folder")], alignment=ft.MainAxisAlignment.CENTER),
                            on_click=open_folder
                        )
                    ]
                )
                self._open_dialog_safe(dlg)

            except Exception as ex:
                logger.error(f"IntuneWin creation failed: {ex}")
                self._show_snack(f"{i18n.get('packaging_failed') or 'Packaging Failed'}: {ex}", "RED")

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
        self._open_dialog_safe(dlg)

    def _add_history_entry(self, info, status):
        try:
            from switchcraft.services.history_service import HistoryService
            h_service = HistoryService()
            entry = {
                "filename": Path(info.file_path).name,
                "product": info.product_name or "Unknown",
                "version": info.product_version or "Unknown",
                "status": status,
                "manufacturer": info.manufacturer
            }
            h_service.add_entry(entry)
        except Exception as e:
            logger.error(f"Failed to update history: {e}")
