import flet as ft
import threading
import logging
import os

from switchcraft.services.intune_service import IntuneService
from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.utils.flet_compat import create_tabs

logger = logging.getLogger(__name__)

class ModernIntuneView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.intune_service = IntuneService()

        # Check Tool Availability
        if not self.intune_service.is_tool_available():
            btn_dl = ft.Button(i18n.get("btn_download_tool") or "Download Intune Tool")
            btn_dl.on_click = lambda e: self._show_snack("Download feature coming soon")

            self.controls = [
                ft.Column([
                    ft.Icon(ft.Icons.WARNING_AMBER, size=50, color="orange"),
                    ft.Text("IntuneWinAppUtil not found.", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("This tool is required to package applications."),
                    btn_dl
                ], alignment=ft.MainAxisAlignment.CENTER)
            ]
            self.alignment = ft.MainAxisAlignment.CENTER
            self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            return

        # Main Layout: Tabs
        self.packager_content = self._build_packager_tab()
        self.uploader_content = self._build_uploader_tab()
        self.tab_body = ft.Container(content=self.packager_content, expand=True)

        def on_tab_change(e):
             idx = int(e.control.selected_index)
             if idx == 0:
                 self.tab_body.content = self.packager_content
             else:
                 self.tab_body.content = self.uploader_content
             self.tab_body.update()

        self.tabs = create_tabs(
            selected_index=0,
            animation_duration=300,
            on_change=on_tab_change,
            tabs=[
                ft.Tab(
                    label=i18n.get("tab_packager") or "Packager",
                    icon=ft.Icons.INVENTORY_2
                ),
                ft.Tab(
                    label=i18n.get("tab_uploader") or "Uploader & Update",
                    icon=ft.Icons.CLOUD_UPLOAD
                ),
            ],
            expand=False
        )

        self.controls = [
            ft.Text(i18n.get("intune_manager_title") or "Intune Manager", size=28, weight=ft.FontWeight.BOLD),
            ft.Text(i18n.get("intune_manager_desc") or "Package and Upload Win32 Apps", color="GREY"),
            ft.Divider(),
            self.tabs,
            self.tab_body
        ]

    # --- Packager Tab ---
    def _build_packager_tab(self):
        self.log_view = ft.ListView(expand=True, spacing=5, auto_scroll=True)

        self.setup_field = ft.TextField(label=i18n.get("lbl_setup_file") or "Setup File (.exe/.msi)", expand=True)
        self.source_field = ft.TextField(label=i18n.get("lbl_source_folder") or "Source Folder", expand=True)
        self.output_field = ft.TextField(label=i18n.get("lbl_output_folder") or "Output Folder", expand=True)
        self.quiet_check = ft.Checkbox(label=i18n.get("lbl_quiet_mode") or "Quiet Mode (No UI)", value=True)

        # Helpers
        def pick_setup_file(e):
            path = FilePickerHelper.pick_file(allowed_extensions=["exe", "msi", "ps1", "bat", "cmd", "vbs", "wsf", "msp"])
            if path:
                self.setup_field.value = path
                parent = os.path.dirname(path)
                if not self.source_field.value:
                    self.source_field.value = parent
                if not self.output_field.value:
                    self.output_field.value = parent
                self.update()

        def pick_folder(e, field):
            path = FilePickerHelper.pick_directory()
            if path:
                field.value = path
                self.update()

        def create_file_row():
            btn = ft.IconButton(ft.Icons.FILE_OPEN, on_click=pick_setup_file)
            return ft.Row([self.setup_field, btn])

        def create_folder_row(field):
            btn = ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=lambda e: pick_folder(e, field))
            return ft.Row([field, btn])

        btn_create = ft.ElevatedButton(
            i18n.get("btn_create_intunewin") or "Create .intunewin",
            style=ft.ButtonStyle(
                bgcolor="GREEN_700",
                color="WHITE",
            ),
            height=50,
            on_click=self._run_creation
        )

        return ft.Container(
            content=ft.Column([
                ft.Text(i18n.get("packager_title") or "Create Package", size=20, weight=ft.FontWeight.BOLD),
                create_file_row(),
                create_folder_row(self.source_field),
                create_folder_row(self.output_field),
                self.quiet_check,
                btn_create,
                ft.Divider(),
                ft.Text(i18n.get("lbl_logs") or "Logs:", weight=ft.FontWeight.BOLD),
                ft.Container(content=self.log_view, expand=True, bgcolor="BLACK", padding=10, border_radius=5)
            ], expand=True, spacing=15),
            padding=20
        )

    # --- Uploader Tab ---
    def _build_uploader_tab(self):
        # Credentials
        self.tenant_id = SwitchCraftConfig.get_value("IntuneTenantID", "")
        self.client_id = SwitchCraftConfig.get_value("IntuneClientID", "")
        self.client_secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret") or ""

        # UI Elements
        self.up_file_field = ft.TextField(label=i18n.get("lbl_intunewin_file") or ".intunewin File", expand=True)
        self.up_display_name = ft.TextField(label=i18n.get("lbl_display_name") or "Display Name", expand=True)
        self.up_description = ft.TextField(label=i18n.get("lbl_description") or "Description", multiline=True, min_lines=2)
        self.up_publisher = ft.TextField(label=i18n.get("lbl_publisher") or "Publisher")
        self.up_install_cmd = ft.TextField(label=i18n.get("lbl_install_cmd") or "Install Command")
        self.up_uninstall_cmd = ft.TextField(label=i18n.get("lbl_uninstall_cmd") or "Uninstall Command")

        self.up_status = ft.Text(i18n.get("status_not_connected") or "Not connected", color="GREY")
        self.btn_upload = ft.Button(
            i18n.get("btn_upload_intune") or "Upload to Intune",
            icon=ft.Icons.CLOUD_UPLOAD,
            disabled=True,
            on_click=self._run_upload
        )

        # Supersedence UI
        self.search_supersede_field = ft.TextField(label=i18n.get("lbl_search_replace") or "Search App to Replace/Update", height=40, expand=True)
        self.supersede_options = ft.Dropdown(label=i18n.get("lbl_select_app") or "Select App", options=[], visible=False)
        self.supersede_copy_btn = ft.Button(
            i18n.get("btn_copy_metadata") or "Copy Metadata",
            icon=ft.Icons.COPY,
            disabled=True,
            visible=False,
            on_click=self._copy_metadata_from_supersedence
        )
        self.supersede_uninstall_sw = ft.Switch(label=i18n.get("lbl_uninstall_prev") or "Uninstall previous version?", value=True)
        self.supersede_status_text = ft.Text("", size=12, italic=True)

        # Connect Logic
        def connect(e):
            self.up_status.value = "Connecting..."
            self.update()
            def _bg():
                try:
                    if not self.tenant_id or not self.client_id or not self.client_secret:
                        def update_fail_creds():
                            self.up_status.value = "Missing Credentials (check Settings)"
                            self.up_status.color = "RED"
                            self.update()
                        self.app_page.run_task(update_fail_creds)
                        return

                    auth_token = self.intune_service.authenticate(self.tenant_id, self.client_id, self.client_secret)

                    def update_success():
                        self.token = auth_token
                        self.up_status.value = "Connected"
                        self.up_status.color = "GREEN"
                        self.btn_upload.disabled = False
                        self.update()
                    self.app_page.run_task(update_success)

                except Exception as ex:
                    def update_error():
                        self.up_status.value = f"Connection Failed: {ex}"
                        self.up_status.color = "RED"
                        self.update()
                    self.app_page.run_task(update_error)

            threading.Thread(target=_bg, daemon=True).start()

        btn_connect = ft.Button(i18n.get("btn_connect") or "Connect", on_click=connect)

        # Supersedence Logic
        def search_apps(e):
            if not hasattr(self, 'token'):
                self._show_snack("Connect first", "RED")
                return
            query = self.search_supersede_field.value
            if not query: return

            self.supersede_status_text.value = "Searching..."
            self.update()

            def _bg():
                try:
                    apps = self.intune_service.search_apps(self.token, query)

                    def update_results():
                        self.found_apps = {app['id']: app for app in apps}
                        options = [ft.dropdown.Option(app['id'], f"{app['displayName']} ({app.get('appVersion', 'Unknown')})") for app in apps]

                        if not options:
                            self.supersede_status_text.value = "No apps found"
                            self.supersede_options.visible = False
                            self.supersede_copy_btn.visible = False
                        else:
                            self.supersede_options.options = options
                            self.supersede_options.visible = True
                            self.supersede_status_text.value = f"Found {len(apps)} apps"
                        self.update()
                    self.app_page.run_task(update_results)

                except Exception as ex:
                    def update_error():
                        self.supersede_status_text.value = f"Search Error: {ex}"
                        self.update()
                    self.app_page.run_task(update_error)
            threading.Thread(target=_bg, daemon=True).start()

        def on_app_select(e):
            self.selected_supersede_id = self.supersede_options.value
            self.supersede_copy_btn.disabled = False
            self.supersede_copy_btn.visible = True
            self.update()

        self.supersede_options.on_change = on_app_select

        def pick_intunewin(e):
            path = FilePickerHelper.pick_file(allowed_extensions=["intunewin"])
            if path:
                self.up_file_field.value = path
                self.update()

        btn_pick = ft.IconButton(ft.Icons.FILE_OPEN, on_click=pick_intunewin)

        return ft.Container(
            content=ft.ListView([
                ft.Text(i18n.get("upload_title") or "Upload & Update App", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([btn_connect, self.up_status]),
                ft.Divider(),

                ft.Text(i18n.get("hdr_supersedence") or "Update Existing App (Supersedence)", weight=ft.FontWeight.BOLD, color="BLUE"),
                ft.Row([self.search_supersede_field, ft.IconButton(ft.Icons.SEARCH, on_click=search_apps)]),
                self.supersede_options,
                self.supersede_copy_btn,
                self.supersede_uninstall_sw,
                self.supersede_status_text,
                ft.Divider(),

                ft.Text(i18n.get("hdr_app_details") or "New App Details", weight=ft.FontWeight.BOLD),
                ft.Row([self.up_file_field, btn_pick]),
                self.up_display_name,
                self.up_publisher,
                self.up_description,
                ft.Row([self.up_install_cmd, self.up_uninstall_cmd]),

                ft.Container(height=10),
                self.btn_upload
            ], spacing=15, padding=10),
            padding=20,
            expand=True
        )

    def _copy_metadata_from_supersedence(self, e):
        app_id = self.supersede_options.value
        if not app_id: return

        self.supersede_status_text.value = "Fetching details..."
        self.update()

        def _bg():
            try:
                # Get full details if needed, or use cached search result
                # Search result is usually summary, get_app_details is better
                full_app = self.intune_service.get_app_details(self.token, app_id)

                def update_ui():
                    self.up_display_name.value = full_app.get("displayName", "")
                    self.up_description.value = full_app.get("description", "")
                    self.up_publisher.value = full_app.get("publisher", "")

                    # Try to preserve commands if possible? Or maybe not, user should probably update them.
                    # But user asked for "Select which it replaces... automatically take info"
                    self.up_install_cmd.value = full_app.get("installCommandLine", "")
                    self.up_uninstall_cmd.value = full_app.get("uninstallCommandLine", "")

                    self.supersede_status_text.value = "Metadata copied!"
                    self.supersede_status_text.color = "GREEN"
                    self.update()
                    self._show_snack("Metadata copied from " + full_app.get("displayName", ""), "GREEN")
                self.app_page.run_task(update_ui)

            except Exception as ex:
                def update_error():
                    self.supersede_status_text.value = f"Copy Failed: {ex}"
                    self.supersede_status_text.color = "RED"
                    self.update()
                self.app_page.run_task(update_error)
        threading.Thread(target=_bg, daemon=True).start()

    def _log(self, msg):
        self.log_view.controls.append(ft.Text(msg, font_family="Consolas", size=12, color="GREEN_400"))
        self.update()

    def _run_creation(self, e):
        # ... logic mainly same as before ...
        setup = self.setup_field.value
        source = self.source_field.value
        output = self.output_field.value
        quiet = self.quiet_check.value

        if not setup or not source or not output:
            self._show_snack(i18n.get("fill_all_fields") or "Please fill all fields", "RED")
            return

        self._log(i18n.get("starting_creation") or "Starting creation...")
        # ... (rest of creation logic similar to previous implementation)
        # simplified for brevity in this replacement block, but need to keep full logic

        def _bg():
            try:
                self.intune_service.create_intunewin(
                    source_folder=source,
                    setup_file=setup,
                    output_folder=output,
                    quiet=quiet,
                    progress_callback=lambda line: self._log(line.strip())
                )
                self._log("DONE! Package created successfully.")

                # Feedback logic verified in previous step
                possible_names = [
                    os.path.basename(setup) + ".intunewin",
                    os.path.splitext(os.path.basename(setup))[0] + ".intunewin"
                ]
                output_file = str(output) # Fallback
                for name in possible_names:
                     f = os.path.join(output, name)
                     if os.path.exists(f):
                         output_file = f
                         break

                def open_folder(e):
                    import subprocess
                    if os.name == 'nt':
                        # Use normpath to ensure backslashes
                        safe_path = os.path.normpath(output_file)
                        # Quote the path in the argument if it has spaces?
                        # subprocess.run handles list args by quoting if needed usually,
                        # but /select,path is tricky as it is one arg for explorer.
                        # However, explorer /select,"path" works.
                        # subprocess will quote individual args.
                        # We need to pass the whole string "/select,path" as one arg if we want explorer to receive it?
                        # Actually explorer expects: explorer /select,path
                        # If we pass ["explorer", "/select," + safe_path] it might be quoted as "/select,path" which is fine.
                        subprocess.run(['explorer', f'/select,{safe_path}'])
                    dlg.open = False
                    self.app_page.update()

                dlg = ft.AlertDialog(
                    title=ft.Text(i18n.get("package_created_title") or "Package Created!", color="GREEN"),
                    content=ft.Text(f"{i18n.get('location')}: {output_file}"),
                    actions=[ft.Button(i18n.get("open_folder") or "Open Folder", on_click=open_folder)]
                )
                self.app_page.open(dlg)

            except Exception as ex:
                self._log(f"ERROR: {ex}")
                self._show_snack(f"Failed: {ex}", "RED")

        threading.Thread(target=_bg, daemon=True).start()

    def _run_upload(self, e):
        # Upload Logic
        path = self.up_file_field.value
        if not path or not os.path.exists(path):
            self._show_snack("Invalid File", "RED")
            return

        app_info = {
            "displayName": self.up_display_name.value,
            "description": self.up_description.value,
            "publisher": self.up_publisher.value,
            "installCommandLine": self.up_install_cmd.value,
            "uninstallCommandLine": self.up_uninstall_cmd.value
        }

        child_supersede = self.supersede_options.value
        uninstall_prev = self.supersede_uninstall_sw.value

        self.up_status.value = "Uploading..."
        self.up_status.color = "BLUE"
        self.btn_upload.disabled = True
        self.update()

        def _bg():
            try:
                def update_progress(pct, msg):
                    def _u():
                        self.up_status.value = f"{int(pct*100)}% - {msg}"
                        self.update()
                    self.app_page.run_task(_u)

                # 1. Upload
                new_app_id = self.intune_service.upload_win32_app(
                    self.token,
                    path,
                    app_info,
                    progress_callback=update_progress
                )

                # 2. Add Supersedence if selected
                if child_supersede:
                    def update_sup():
                        self.up_status.value = "Adding Supersedence..."
                        self.update()
                    self.app_page.run_task(update_sup)

                    self.intune_service.add_supersedence(self.token, new_app_id, child_supersede, uninstall_prev=uninstall_prev)

                def update_done():
                    self.up_status.value = "Upload Complete!"
                    self.up_status.color = "GREEN"
                    self.btn_upload.disabled = False
                    self.update()
                    self._show_success_dialog(new_app_id)
                self.app_page.run_task(update_done)

            except Exception as ex:
                logger.error(f"Upload failed: {ex}")
                def update_fail():
                    self.up_status.value = f"Error: {ex}"
                    self.up_status.color = "RED"
                    self.btn_upload.disabled = False
                    self.update()
                self.app_page.run_task(update_fail)

        threading.Thread(target=_bg, daemon=True).start()

    def _show_success_dialog(self, app_id):
        dlg = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, color="GREEN"), ft.Text("Upload Successful")]),
            content=ft.Text(f"App ID: {app_id}\nSupersedence configured if selected."),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, "open", False) or self.app_page.update())]
        )
        self.app_page.open(dlg)


    def _show_snack(self, msg, color="GREEN"):
        try:
            self.app_page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.app_page.snack_bar.open = True
            self.app_page.update()
        except Exception as e:
            logger.warning(f"Failed to show snackbar: {e}")
