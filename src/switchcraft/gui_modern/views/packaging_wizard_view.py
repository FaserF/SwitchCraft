import flet as ft
import logging
import threading
import requests
import tempfile
import subprocess
from pathlib import Path

from switchcraft.controllers.analysis_controller import AnalysisController
from switchcraft.services.intune_service import IntuneService
from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.utils.view_utils import ViewMixin

logger = logging.getLogger(__name__)


class PackagingWizardView(ft.Column, ViewMixin):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.analysis_controller = AnalysisController()
        self.intune_service = IntuneService()

        # State
        self.current_step = 0
        self.installer_path = None
        self.analysis_result = None
        self.generated_script_path = None
        self.package_path = None
        self.upload_info = {}
        self.signing_cert = SwitchCraftConfig.get_value("SigningCertThumbprint")
        self.packaging_mode = "win32" # win32 or lob
        self.supersede_app_id = None # ID of app to superseded

        # Steps UI Containers
        self.step_content_area = ft.Container(expand=True, padding=20)

        # Build UI
        # Build UI
        # Wrap everything in a container to provide consistent padding
        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text("End-to-End Packaging Wizard", size=28, weight=ft.FontWeight.BOLD),
                    self._build_stepper_header(),
                    ft.Divider(),
                    self.step_content_area,
                    ft.Divider(),
                    self._build_nav_buttons()
                ], expand=True, spacing=10),
                padding=20,
                expand=True
            )
        ]

        self._load_step(0, update=False)

    def did_mount(self):
        # Check for pre-filled data from Intune Store
        # Use switchcraft_session dict instead of page.session
        """
        Populate upload fields from any pending packaging data stored in the app's session.

        If a 'pending_packaging_app' entry exists in self.app_page.switchcraft_session, copy its `displayName`, `publisher`, and `description` into self.upload_info, clear the pending entry, and show a notification to the user.
        """
        session_storage = getattr(self.app_page, 'switchcraft_session', {})
        pending_app = session_storage.get("pending_packaging_app")
        if pending_app:
            self.upload_info = {
                "displayName": pending_app.get("displayName"),
                "publisher": pending_app.get("publisher"),
                "description": pending_app.get("description"),
            }
            # If we have a download URL or similar, we could pre-fill it too.
            # For now, just pre-filling the upload info.
            session_storage["pending_packaging_app"] = None  # Clear it
            self._show_snack(f"Pre-filled info for {pending_app.get('displayName')}", "BLUE")

    def _build_stepper_header(self):
        """
        Create the header row containing the wizard's five step indicators.

        The indicators (Select, Analyze, Script, Package, Upload) are created and stored on
        self.steps_indicators for later updates.

        Returns:
            ft.Row: A row widget with the five step indicators centered and spaced by 20.
        """
        self.steps_indicators = [
            self._create_step_indicator(0, "Select", ft.Icons.FILE_UPLOAD),
            self._create_step_indicator(1, "Analyze", ft.Icons.ANALYTICS),
            self._create_step_indicator(2, "Script", ft.Icons.CODE),
            self._create_step_indicator(3, "Package", ft.Icons.INVENTORY),
            self._create_step_indicator(4, "Upload", ft.Icons.CLOUD_UPLOAD),
        ]
        return ft.Row(self.steps_indicators, alignment=ft.MainAxisAlignment.CENTER, spacing=20)

    def _create_step_indicator(self, index, label, icon):
        color = "BLUE" if index == self.current_step else "GREY"
        return ft.Column([
            ft.Icon(icon, color=color, size=30),
            ft.Text(label, color=color, size=12)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def _update_stepper(self, update=True):
        for i, indicator in enumerate(self.steps_indicators):
            if i < self.current_step:
                color = "GREEN"
            elif i == self.current_step:
                color = "BLUE"
            else:
                color = "GREY"
            indicator.controls[0].color = color
            indicator.controls[1].color = color
        if update:
            self.update()

    def _build_nav_buttons(self):
        self.btn_prev = ft.ElevatedButton(
            text="Previous", on_click=self._prev_step, disabled=True
        )
        self.btn_next = ft.ElevatedButton(
            text="Next", on_click=self._next_step, bgcolor="BLUE", color="WHITE"
        )
        return ft.Row(
            [self.btn_prev, ft.Container(expand=True), self.btn_next],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

    def _load_step(self, index, update=True):
        self.current_step = index
        self._update_stepper(update=update)

        # Loading placeholder if updating, else just set content
        if update:
            self.step_content_area.content = ft.ProgressBar()
            self.update()

        content = None
        if index == 0:
            content = self._step_select_ui()
            self.btn_next.text = "Analyze >"
            self.btn_prev.disabled = True
        elif index == 1:
            content = self._step_analyze_ui()
            self.btn_next.text = "Generate Script >"
            self.btn_prev.disabled = False
        elif index == 2:
            content = self._step_script_ui()
            self.btn_next.text = "Package >"
            self.btn_prev.disabled = False
        elif index == 3:
            content = self._step_package_ui()
            self.btn_next.text = "Upload to Intune >"
            self.btn_prev.disabled = False
        elif index == 4:
            content = self._step_upload_ui()
            self.btn_next.text = "Finish"
            self.btn_prev.disabled = False

        self.step_content_area.content = content
        if update:
            self.update()

        # Auto-trigger analysis if entering step 1 and path is set
        if index == 1 and self.installer_path and not self.analysis_result:
            self._run_analysis()

    def _prev_step(self, e):
        if self.current_step > 0:
            self._load_step(self.current_step - 1)

    def _next_step(self, e):
        if self.current_step == 0:
            # Save Mode
            self.packaging_mode = self.mode_radio.value

            if not self.installer_path:
                self._show_snack("Please select a file first", "RED")
                return

            # Validate LOB
            if self.packaging_mode == "lob":
                if not self.installer_path.lower().endswith(".msi"):
                     self._show_snack("LOB Mode requires an .msi file", "RED")
                     return

        elif self.current_step == 1:
            # Analyze Step
            if self.packaging_mode == "lob":
                # Skip to Upload (Step 4)
                self._load_step(4)
                return

        elif self.current_step == 2:
            # Save script before moving
            if not self._save_script():
                return
        elif self.current_step == 3:
            # Check package
            if not self.package_path or not Path(self.package_path).exists():
                self._show_snack("Package creation failed or not executed", "RED")
                return

        if self.current_step < 4:
            self._load_step(self.current_step + 1)
        else:
            # Finish
            self._show_snack("Wizard Completed!", "GREEN")

    def _step_select_ui(self):
        self.mode_radio = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="win32", label="Win32 App (Standard)"),
                ft.Radio(value="lob", label="Direct MSI (LOB)")
            ]),
            value=self.packaging_mode
        )

        self.file_text = ft.Text(self.installer_path or "No file selected", size=16)

        # Tab 1: Local File
        local_content = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.FILE_UPLOAD, size=60, color="BLUE_400"),
                ft.Text("Select Installer", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Supported: .exe, .msi", color="ON_SURFACE_VARIANT"),
                ft.Container(height=20),
                ft.ElevatedButton(text="Browse File...", icon=ft.Icons.FOLDER_OPEN, on_click=self._pick_file),
                ft.Container(height=10),
                self.file_text
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.Alignment(0, 0),
            padding=20
        )

        # Tab 2: URL Download
        self.url_field = ft.TextField(label="Direct Download URL", expand=True, hint_text="https://example.com/installer.msi")
        self.download_status = ft.Text("", italic=True)
        self.download_progress = ft.ProgressBar(width=400, visible=False)

        url_content = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.CLOUD_DOWNLOAD, size=60, color="ORANGE_400"),
                ft.Text("Download from Web", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Enter a direct link to an .exe or .msi file", color="ON_SURFACE_VARIANT"),
                ft.Container(height=20),
                ft.Row([self.url_field, ft.ElevatedButton(text="Download", icon=ft.Icons.DOWNLOAD, on_click=self._start_download)]),
                ft.Container(height=10),
                self.download_progress,
                self.download_status
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.Alignment(0, 0),
            padding=20
        )

        # Tab Content Container
        self.wizard_tab_body = ft.Container(content=local_content, padding=20)

        def on_source_change(e):
            idx = int(e.control.selected_index)
            if idx == 0:
                 self.wizard_tab_body.content = local_content
            else:
                 self.wizard_tab_body.content = url_content
            self.wizard_tab_body.update()

        tabs = ft.Tabs(
            content=self.wizard_tab_body,
            length=2,
            selected_index=0,
            animation_duration=300,
            expand=True,
            on_change=on_source_change
        )
        tabs.tabs = [
                ft.Tab(label="Local File", icon=ft.Icons.COMPUTER),
                ft.Tab(label="Download URL", icon=ft.Icons.LINK),
            ]

        self.autopilot_btn = ft.OutlinedButton(
            "Auto-Pilot (Magic Mode) 🪄",
            icon=ft.Icons.AUTO_FIX_HIGH,
            style=ft.ButtonStyle(color="PURPLE_200"),
            on_click=self._run_autopilot
        )

        return ft.Column([
            ft.Text("Select Packaging Mode", weight=ft.FontWeight.BOLD),
            self.mode_radio,
            ft.Divider(),
            tabs,
            ft.Divider(),
            ft.Row([ft.Text("Experimental:"), self.autopilot_btn], alignment=ft.MainAxisAlignment.END)
        ], spacing=10, scroll=ft.ScrollMode.AUTO)

    def _start_download(self, e):
        url = self.url_field.value
        if not url:
            self.download_status.value = "Please enter a URL"
            self.update()
            return

        self.download_status.value = "Starting download..."
        self.download_progress.visible = True
        self.update()

        def _bg():
            try:
                # Get filename from URL or header
                filename = url.split("/")[-1] or "installer.exe"
                # Use temp dir
                temp_dir = Path(tempfile.gettempdir()) / "SwitchCraft_Downloads"
                temp_dir.mkdir(parents=True, exist_ok=True)
                target_path = temp_dir / filename

                with requests.get(url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    total_length = r.headers.get('content-length')

                    with open(target_path, 'wb') as f:
                         if total_length is None: # no content length header
                             f.write(r.content)
                         else:
                             dl = 0
                             total_length = int(total_length)
                             for data in r.iter_content(chunk_size=4096):
                                 dl += len(data)
                                 f.write(data)
                                 # self.download_progress.value = dl / total_length
                                 # self.update()

                self.installer_path = str(target_path)
                self.file_text.value = str(target_path) # sync with other tab
                self.download_status.value = f"Downloaded: {filename}"
                self.download_status.color = "GREEN"
                self.download_progress.visible = False
            except Exception as ex:
                self.download_status.value = f"Error: {ex}"
                self.download_status.color = "RED"
                self.download_progress.visible = False

            self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _pick_file(self, e):
        path = FilePickerHelper.pick_file(allowed_extensions=["exe", "msi", "ps1", "bat", "cmd", "vbs", "msp"])
        if path:
            self.installer_path = path
            self.file_text.value = path
            self.update()

    # --- Step 1: Analyze ---
    def _step_analyze_ui(self):
        self.analysis_progress = ft.ProgressBar(width=400, visible=False)
        self.analysis_status = ft.Text("", italic=True, size=14)
        self.analysis_dt = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(i18n.get("table_header_field") or "Property")),
                ft.DataColumn(ft.Text(i18n.get("table_header_value") or "Value"))
            ],
            rows=[],
            width=float("inf")
        )
        self.analysis_error_container = ft.Container(visible=False)

        return ft.Column([
            ft.Text(
                i18n.get("analyzing_installer") or "Analyzing Installer...",
                size=20,
                weight=ft.FontWeight.BOLD
            ),
            ft.Container(height=10),
            self.analysis_progress,
            self.analysis_status,
            ft.Container(height=10),
            self.analysis_error_container,
            self.analysis_dt
        ], scroll=ft.ScrollMode.AUTO)

    def _run_analysis(self):
        self.analysis_status.value = ""
        self.analysis_progress.visible = True
        self.analysis_progress.value = None  # Indeterminate mode
        self.analysis_error_container.visible = False
        self.analysis_dt.rows.clear()
        self.update()

        def _bg():
            try:
                # Progress callback to update UI
                def on_progress(pct, msg, eta=None):
                    self.analysis_progress.value = pct
                    self.analysis_status.value = msg
                    self.update()

                # Use the same analyze_file method as ModernAnalyzerView
                res = self.analysis_controller.analyze_file(
                    self.installer_path,
                    progress_callback=on_progress
                )
                self.analysis_result = res

                # Check for errors
                if res.error:
                    self.analysis_error_container.content = ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.ERROR_OUTLINE, color="WHITE"),
                            ft.Text(f"Error: {res.error}", color="WHITE")
                        ]),
                        bgcolor="RED_700",
                        padding=10,
                        border_radius=8
                    )
                    self.analysis_error_container.visible = True
                    self.analysis_status.value = i18n.get("analysis_failed") or "Analysis failed"
                    self.analysis_status.color = "RED"
                    self.analysis_progress.visible = False
                    self.update()
                    return

                # Success - populate table
                self.analysis_progress.visible = False
                self.analysis_status.value = i18n.get("analysis_complete") or "Analysis Complete"
                self.analysis_status.color = "GREEN"

                info = res.info
                if info:
                    rows = [
                        ft.DataRow([
                            ft.DataCell(ft.Text(i18n.get("field_product") or "Name")),
                            ft.DataCell(ft.Text(info.product_name or "Unknown"))
                        ]),
                        ft.DataRow([
                            ft.DataCell(ft.Text(i18n.get("field_manufacturer") or "Publisher")),
                            ft.DataCell(ft.Text(info.manufacturer or "Unknown"))
                        ]),
                        ft.DataRow([
                            ft.DataCell(ft.Text(i18n.get("field_version") or "Version")),
                            ft.DataCell(ft.Text(info.product_version or "Unknown"))
                        ]),
                        ft.DataRow([
                            ft.DataCell(ft.Text(i18n.get("field_type") or "Type")),
                            ft.DataCell(ft.Text(info.installer_type or "Unknown"))
                        ]),
                        ft.DataRow([
                            ft.DataCell(ft.Text(i18n.get("silent_switches") or "Switches")),
                            ft.DataCell(ft.Text(
                                " ".join(info.install_switches) if info.install_switches else "None detected",
                                color="GREEN" if info.install_switches else "ORANGE"
                            ))
                        ]),
                    ]
                    self.analysis_dt.rows = rows

                self.update()

            except Exception as ex:
                logger.error(f"Analysis error: {ex}")
                self.analysis_progress.visible = False
                self.analysis_status.value = f"Error: {ex}"
                self.analysis_status.color = "RED"
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    # --- Step 2: Script ---
    def _step_script_ui(self):
        self.script_field = ft.TextField(
            label="PowerShell Install Script",
            multiline=True,
            min_lines=10,
            max_lines=15,
            text_size=12,
            text_style=ft.TextStyle(font_family="Consolas")
        )
        # Load template or generate
        if not self.generated_script_path:
             self._generate_script_content()

        sign_status = ft.Row([
            ft.Icon(ft.Icons.VERIFIED_USER, color="GREEN" if self.signing_cert else "GREY"),
            ft.Text(f"Auto-Signing: {'Enabled' if self.signing_cert else 'Disabled (No Cert Configured)'}",
                    color="GREEN" if self.signing_cert else "GREY")
        ])

        return ft.Column([
            ft.Text("Review & Edit Script", size=20, weight=ft.FontWeight.BOLD),
            sign_status,
            self.script_field,
            ft.ElevatedButton(text="Regenerate", on_click=lambda _: self._generate_script_content())
        ], scroll=ft.ScrollMode.AUTO)

    def _generate_script_content(self):
        info = self.analysis_result.info if self.analysis_result else None
        installer = Path(self.installer_path).name if self.installer_path else "installer.exe"

        args = " ".join(info.install_switches) if info and info.install_switches else "/S"

        # Basic PS1 Template
        script = f"""# Auto-generated by SwitchCraft
$Installer = "{installer}"
$Args = "{args}"

# Install
Start-Process -FilePath "$PSScriptRoot\\$Installer" -ArgumentList $Args -Wait -Passthru
"""
        self.script_field.value = script
        self.update()

    def _save_script(self):
        try:
             # Save to temp or same dir
             script_dir = Path(self.installer_path).parent
             script_path = script_dir / "install.ps1"

             with open(script_path, "w") as f:
                 f.write(self.script_field.value)

             self.generated_script_path = str(script_path)

             # Auto-Sign
             if self.signing_cert:
                 self._sign_script(script_path)

             return True
        except Exception as e:
            self._show_snack(f"Failed to save script: {e}", "RED")
            return False

    def _sign_script(self, path):
        try:
            cmd = [
                "powershell.exe",
                "-ExecutionPolicy", "Bypass",
                "-Command",
                f"Set-AuthenticodeSignature -FilePath '{path}' -Certificate (Get-Item Cert:\\CurrentUser\\My\\{self.signing_cert})"
            ]
            # Verify cert store location (CurrentUser\My is standard for user certs, usually CodeSigning)
            # If stored in LocalMachine, change path. Config should ideally specify.

            subprocess.run(cmd, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self._show_snack("Script Signed Successfully!", "GREEN")
        except Exception as e:
            logger.error(f"Signing failed: {e}")
            self._show_snack(f"Signing Warning: {e}", "ORANGE")

    def _step_package_ui(self):
        self.pkg_status = ft.Text("Ready to package.", size=16)
        self.pkg_btn = ft.ElevatedButton(
            text="Start Packaging", on_click=self._run_packaging, bgcolor="GREEN", color="WHITE"
        )
        return ft.Column([
            ft.Text("Create Intune Package (.intunewin)", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(f"Source: {Path(self.installer_path).parent}", italic=True),
            # Split line to avoid E501
            ft.Text(f"Setup File: {Path(self.generated_script_path).name if self.generated_script_path else 'N/A'}",
                    italic=True),
            ft.Container(height=20),
            self.pkg_status,
            self.pkg_btn
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)

    def _run_packaging(self, e):
        self.pkg_status.value = "Packaging in progress..."
        self.pkg_btn.disabled = True
        self.update()

        def _bg():
            try:
                base_dir = Path(self.installer_path).parent
                setup_file = Path(self.generated_script_path).name
                self.intune_service.create_intunewin(str(base_dir), setup_file, str(base_dir), quiet=True)

                # Assume output
                pkg = base_dir / (setup_file + ".intunewin")
                if not pkg.exists():
                    # try alternate name
                    pkg = base_dir / (Path(setup_file).stem + ".intunewin")

                if pkg.exists():
                    self.package_path = str(pkg)
                    self.pkg_status.value = f"Success: {pkg.name}"
                    self.pkg_status.color = "GREEN"
                else:
                    self.pkg_status.value = "Failed: .intunewin not found"
                    self.pkg_status.color = "RED"
            except Exception as ex:
                self.pkg_status.value = f"Error: {ex}"
                self.pkg_status.color = "RED"
            finally:
                self.pkg_btn.disabled = False
                if self.page:
                    self.update()

        threading.Thread(target=_bg, daemon=True).start()

    # --- Step 4: Upload ---
    def _step_upload_ui(self):
        # Load Defaults
        tenant = SwitchCraftConfig.get_value("IntuneTenantID", "")
        client = SwitchCraftConfig.get_value("IntuneClientID", "")
        secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret") or ""

        self.txt_tenant = ft.TextField(label="Tenant ID", value=tenant, password=True, can_reveal_password=True)
        self.txt_client = ft.TextField(label="Client ID", value=client)
        self.txt_secret = ft.TextField(label="Client Secret", value=secret, password=True, can_reveal_password=True)

        # App Info (Pre-filled)
        info = self.analysis_result.info if self.analysis_result else None

        self.txt_app_name = ft.TextField(label="Display Name", value=info.product_name if info else "New App")
        self.txt_publisher = ft.TextField(label="Publisher", value=info.manufacturer if info else "Unknown")
        self.txt_desc = ft.TextField(label="Description", value=f"Packaged by SwitchCraft based on {Path(self.installer_path).name if self.installer_path else 'installer'}", multiline=True)

        self.upload_status = ft.Text("Waiting for authentication...", italic=True)
        self.btn_upload = ft.ElevatedButton(text="Upload to Intune", on_click=self._run_upload, icon=ft.Icons.CLOUD_UPLOAD, disabled=True)
        self.btn_connect = ft.ElevatedButton(text="Connect", on_click=self._connect_intune)

        return ft.Column([
            ft.Text("Upload to Microsoft Intune", size=20, weight=ft.FontWeight.BOLD),
            ft.Text("Credentials", weight=ft.FontWeight.BOLD),
            self.txt_tenant,
            self.txt_client,
            self.txt_secret,
            self.btn_connect,
            ft.Divider(),
            ft.Text("App Details", weight=ft.FontWeight.BOLD),
            self.txt_app_name,
            self.txt_publisher,
            self.txt_desc,
            ft.Divider(),
            ft.Text("Supersedence (Upgrade)", weight=ft.FontWeight.BOLD),
            self._build_supersedence_ui(),
            ft.Divider(),
            self.upload_status,
            self.btn_upload
        ], scroll=ft.ScrollMode.AUTO)

    def _connect_intune(self, e):
        tenant = self.txt_tenant.value
        client = self.txt_client.value
        secret = self.txt_secret.value

        if not all([tenant, client, secret]):
            self._show_snack("Please fill all credentials", "RED")
            return

        self.upload_status.value = "Authenticating..."
        self.update()

        def _bg():
            try:
                token = self.intune_service.authenticate(tenant, client, secret)
                # Verify perm
                ok, msg = self.intune_service.verify_graph_permissions(token)
                if not ok:
                    self.upload_status.value = f"Permission Error: {msg}"
                    self.upload_status.color = "RED"
                else:
                     self.token = token # Store for upload
                     self.upload_status.value = "Connected! Ready to upload."
                     self.upload_status.color = "GREEN"
                     self.btn_upload.disabled = False

                     # Save valid creds
                     SwitchCraftConfig.set_value("IntuneTenantID", tenant)
                     SwitchCraftConfig.set_value("IntuneClientID", client)
                     SwitchCraftConfig.set_secret("IntuneClientSecret", secret) # Use set_secret if available, else standard?
            except Exception as ex:
                self.upload_status.value = f"Auth Failed: {ex}"
                self.upload_status.color = "RED"
            self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _build_supersedence_ui(self):
        self.search_supersede_field = ft.TextField(label="Search App to Replace", height=40, expand=True)
        self.supersede_status = ft.Text("None selected", italic=True, size=12)
        self.supersede_option = ft.Dropdown(label="Select App", options=[], visible=False)
        self.supersede_option.on_change = self._on_supersede_select
        self.supersede_uninstall = ft.Switch(label="Uninstall previous version?", value=True)

        return ft.Column([
            ft.Row([
                self.search_supersede_field,
                ft.IconButton(ft.Icons.SEARCH, on_click=self._on_search_supersedence)
            ]),
            self.supersede_option,
            self.supersede_status,
            self.supersede_uninstall
        ])

    def _on_search_supersedence(self, e):
        if not hasattr(self, 'token'):
             self._show_snack("Connect to Intune first", "RED")
             return

        query = self.search_supersede_field.value
        if not query:
            return

        self.supersede_status.value = "Searching..."
        self.update()

        def _bg():
            apps = self.intune_service.search_apps(self.token, query)
            self.found_apps = apps # list of dicts {id, displayName, ...}

            options = [ft.dropdown.Option(app['id'], f"{app['displayName']} ({app.get('appVersion','Unknown')})") for app in apps]

            if not options:
                self.supersede_status.value = "No apps found"
                self.supersede_option.visible = False
            else:
                self.supersede_option.options = options
                self.supersede_option.visible = True
                self.supersede_status.value = f"Found {len(apps)} apps"
            self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _on_supersede_select(self, e):
        self.supersede_app_id = self.supersede_option.value
        self.supersede_status.value = f"Selected ID: {self.supersede_app_id}"
        self.update()



    def _run_upload(self, e):
        if not hasattr(self, 'token'):
            self._show_snack("Not authenticated", "RED")
            return

        self.upload_status.value = "Starting upload..."
        self.btn_upload.disabled = True
        self.update()

        # Build App Info
        app_info = {
            "displayName": self.txt_app_name.value,
            "description": self.txt_desc.value,
            "publisher": self.txt_publisher.value,
        }

        # Handle Mode Specifics
        if self.packaging_mode == "lob":
             # LOB specific fields
             switches = "/q"
             if self.analysis_result and self.analysis_result.info and self.analysis_result.info.install_switches:
                 switches = " ".join(self.analysis_result.info.install_switches)
             app_info["installCommandLine"] = switches
             # productCode is CRITICAL for MSI LOB
             if self.analysis_result and self.analysis_result.info:
                 app_info["productCode"] = self.analysis_result.info.product_code
                 app_info["productVersion"] = self.analysis_result.info.product_version
        else:
             # Win32 specific fields
             script_name = Path(self.generated_script_path).name if self.generated_script_path else "install.ps1"
             app_info["installCommandLine"] = f"powershell.exe -ExecutionPolicy Bypass -File {script_name}"
             app_info["uninstallCommandLine"] = "cmd /c echo Uninstall logic in script"

        # Auto-Detection Rules (Win32 Only usually, LOB handles it via ProductCode automatically)
        if self.packaging_mode != "lob":
            detection_rules = []
            info = self.analysis_result.info if self.analysis_result else None

            if info and info.product_code:
                detection_rules.append({
                    "@odata.type": "#microsoft.graph.win32LobAppProductCodeDetectionRule",
                    "productCode": info.product_code,
                    "productVersionOperator": "notConfigured",
                    "productVersion": None
                })
                self.upload_status.value = f"Starting upload... (Auto-Detected MSI Rule: {info.product_code})"
            elif info and info.product_name:
                 # Fallback to File detection?
                 pass

            if detection_rules:
                app_info["detectionRules"] = detection_rules
            else:
                self._show_snack("Warning: No detection rules generated (Win32)", "ORANGE")

        self.update()

        def _prog(pct, msg):
             self.upload_status.value = f"{msg} ({int(pct*100)}%)"
             self.update()

        def _bg():
            try:
                if self.packaging_mode == "lob":
                     new_app_id = self.intune_service.upload_mobile_lob_app(
                        self.token,
                        self.installer_path,
                        app_info,
                        progress_callback=_prog
                     )
                else:
                    new_app_id = self.intune_service.upload_win32_app(
                        self.token,
                        self.package_path,
                        app_info,
                        progress_callback=_prog
                    )

                # Handle Supersedence
                if self.supersede_app_id:
                    self.upload_status.value = "Configuring Supersedence..."
                    self.update()
                    self.intune_service.add_supersedence(
                        self.token,
                        new_app_id,
                        self.supersede_app_id,
                        uninstall_prev=self.supersede_uninstall.value
                    )

                self.upload_status.value = "Upload Complete! App is now in Intune."
                self.upload_status.color = "GREEN"
            except Exception as ex:
                self.upload_status.value = f"Upload Error: {ex}"
                self.upload_status.color = "RED"
            finally:
                self.btn_upload.disabled = False
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _run_autopilot(self, e):
        """
        Magic Mode: Automates the entire flow.
        1. Analyze
        2. Generate Script (defaults)
        3. Package (if Win32)
        4. Upload
        """
        if not self.installer_path:
             self._show_snack("Please select a file first", "RED")
             return

        # Check creds
        tenant = SwitchCraftConfig.get_value("IntuneTenantID")
        client = SwitchCraftConfig.get_value("IntuneClientID")
        secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret")
        if not all([tenant, client, secret]):
             self._show_snack("Intune Credentials missing in Settings", "RED")
             return

        self._show_snack("Starting Auto-Pilot...", "PURPLE")

        # We need a progress dialog or overlying status
        self.autopilot_dlg = ft.AlertDialog(
            title=ft.Text("Auto-Pilot Running 🪄"),
            content=ft.Column([
                ft.ProgressBar(),
                ft.Text("Please wait, performing magic...", key="status_txt")
            ], height=100, tight=True),
            modal=True,
            on_dismiss=lambda e: print("Autopilot finished")
        )
        if hasattr(self.app_page, "open"):
            self.app_page.open(self.autopilot_dlg)
        else:
            self.app_page.dialog = self.autopilot_dlg
            self.autopilot_dlg.open = True
            self.app_page.update()

        def _update_status(msg):
            # Hacky way to update dialog content if we don't have ref
            self.autopilot_dlg.content.controls[1].value = msg
            if self.autopilot_dlg._page:
                self.autopilot_dlg.update()

        def _bg():
            try:
                # 0. Set Mode
                self.packaging_mode = self.mode_radio.value

                # 1. Analyze
                _update_status("Step 1/4: Analyzing...")
                res = self.analysis_controller.analyze_file(self.installer_path)
                self.analysis_result = res

                # 2. Script
                _update_status("Step 2/4: Generating Script...")
                # Generate default script logic
                info = res.info
                installer_name = Path(self.installer_path).name
                args = " ".join(info.install_switches) if info.install_switches else "/S"

                # We need to save the script to disk
                script_dir = Path(self.installer_path).parent
                script_path = script_dir / "install.ps1"

                script_content = f"# Auto-generated\nStart-Process -FilePath \"$PSScriptRoot\\{installer_name}\" -ArgumentList \"{args}\" -Wait -Passthru"
                with open(script_path, "w") as f:
                    f.write(script_content)
                self.generated_script_path = str(script_path)

                # Sign if needed
                if self.signing_cert:
                    _update_status("Signing Script...")
                    self._sign_script(str(script_path)) # reusing existing method (might fail if UI thread req? No, uses subprocess)

                # 3. Package (Win32 Only)
                if self.packaging_mode == "win32":
                    _update_status("Step 3/4: Packaging .intunewin...")
                    base_dir = Path(self.installer_path).parent
                    self.intune_service.create_intunewin(str(base_dir), installer_name, str(base_dir), quiet=True)
                    # Deduce package path
                    pkg = base_dir / (installer_name + ".intunewin")
                    if not pkg.exists():
                        pkg = base_dir / (Path(installer_name).stem + ".intunewin")

                    if not pkg.exists():
                        raise Exception("Package creation failed")
                    self.package_path = str(pkg)

                # 4. Upload
                _update_status("Step 4/4: Uploading to Intune...")

                # Auth
                token = self.intune_service.authenticate(tenant, client, secret)
                self.token = token

                # Prepare Info
                app_info = {
                    "displayName": info.product_name or "New App",
                    "description": "Uploaded via SwitchCraft Magic Mode",
                    "publisher": info.manufacturer or "Unknown",
                }

                if self.packaging_mode == "lob":
                    switches = "/q"
                    if info.install_switches:
                        switches = " ".join(info.install_switches)
                    app_info["installCommandLine"] = switches
                    if info.product_code:
                         app_info["productCode"] = info.product_code
                         app_info["productVersion"] = info.product_version
                else:
                    app_info["installCommandLine"] = "powershell.exe -ExecutionPolicy Bypass -File install.ps1"
                    app_info["uninstallCommandLine"] = "cmd /c echo Uninstall not implemented"

                    # Detection
                    if info.product_code:
                         app_info["detectionRules"] = [{
                             "@odata.type": "#microsoft.graph.win32LobAppProductCodeDetectionRule",
                             "productCode": info.product_code,
                             "productVersionOperator": "notConfigured",
                             "productVersion": None
                         }]

                # Do Upload
                if self.packaging_mode == "lob":
                     self.intune_service.upload_mobile_lob_app(token, self.installer_path, app_info)
                else:
                     self.intune_service.upload_win32_app(token, self.package_path, app_info)

                _update_status("Magic Complete! ✨")
                self.autopilot_dlg.title = ft.Text("Success!")
                self.autopilot_dlg.actions = [ft.TextButton("Close", on_click=lambda e: self._close_autopilot())]
                self.autopilot_dlg.update()

            except Exception as ex:
                if self.autopilot_dlg.open:
                     self.autopilot_dlg.title = ft.Text("Magic Failed 💀")
                     _update_status(f"Error: {ex}")
                     self.autopilot_dlg.actions = [ft.TextButton("Close", on_click=lambda e: self._close_autopilot())]
                     if self.autopilot_dlg._page:
                        self.autopilot_dlg.update()
                logger.error(f"Autopilot error: {ex}")

        threading.Thread(target=_bg, daemon=True).start()

    def _close_autopilot(self, e=None):
        """Close the autopilot dialog."""
        self._close_dialog(self.autopilot_dlg)
