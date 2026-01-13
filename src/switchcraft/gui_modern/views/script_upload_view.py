import flet as ft
from switchcraft.services.intune_service import IntuneService
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ScriptUploadView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.intune_service = IntuneService()

        # State
        self.script_path = None
        self.detect_path = None # For Remediation
        self.remediate_path = None # For Remediation

        # UI Components
        self.controls = [
            ft.Text("Script Management Center", size=28, weight=ft.FontWeight.BOLD),
            ft.Text("Upload PowerShell & Remediation Scripts directly to Intune", size=16, color="GREY"),
            ft.Divider(),
            self._build_tabs()
        ]

    def _build_tabs(self):
        tab1 = ft.Tab("Platform Scripts", icon=ft.Icons.TERMINAL)
        tab1.content = self._build_platform_script_tab()

        tab2 = ft.Tab("Remediations", icon=ft.Icons.HEALING)
        tab2.content = self._build_remediation_tab()

        t = ft.Tabs(
            content=None,
            length=0,
            animation_duration=300,
            expand=True
        )
        t.tabs = [tab1, tab2]
        return t

    # --- Platform Script Tab ---
    def _build_platform_script_tab(self):
        self.ps_name = ft.TextField(label="Script Name")
        self.ps_desc = ft.TextField(label="Description", multiline=True)
        self.ps_file_btn = ft.ElevatedButton("Select Script (.ps1)...", icon=ft.Icons.FILE_OPEN, on_click=self._pick_ps_file)
        self.ps_file_label = ft.Text("No file selected", italic=True)
        self.ps_context = ft.Dropdown(
            label="Run Context",
            options=[ft.dropdown.Option("system"), ft.dropdown.Option("user")],
            value="system"
        )
        self.ps_btn_upload = ft.ElevatedButton("Upload Script", icon=ft.Icons.CLOUD_UPLOAD, on_click=self._upload_ps_script)
        self.ps_status = ft.Text("")

        return ft.Container(
            content=ft.Column([
                ft.Text("Upload Standard PowerShell Script", size=20, weight=ft.FontWeight.BOLD),
                self.ps_name,
                self.ps_desc,
                ft.Row([self.ps_file_btn, self.ps_file_label]),
                self.ps_context,
                ft.Container(height=20),
                self.ps_btn_upload,
                self.ps_status
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            padding=20
        )

    def _pick_ps_file(self, e):
        path = FilePickerHelper.pick_file(allowed_extensions=["ps1"])
        if path:
            self.script_path = path
            self.ps_file_label.value = Path(path).name
            if not self.ps_name.value:
                self.ps_name.value = Path(path).stem
            self.update()

    def _upload_ps_script(self, e):
        if not self.script_path or not self.ps_name.value:
            self._show_snack("Name and Script File are required", "RED")
            return

        # Check Credentials
        tenant = SwitchCraftConfig.get_value("IntuneTenantID")
        client = SwitchCraftConfig.get_value("IntuneClientID")
        secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret")

        if not all([tenant, client, secret]):
            self._show_snack("Intune Credentials missing in Settings", "RED")
            return

        self.ps_status.value = "Uploading..."
        self.ps_btn_upload.disabled = True
        self.update()

        def _bg():
            try:
                token = self.intune_service.authenticate(tenant, client, secret)
                with open(self.script_path, "r", encoding="utf-8") as f:
                    content = f.read()

                self.intune_service.upload_powershell_script(
                    token, self.ps_name.value, self.ps_desc.value, content, self.ps_context.value
                )

                self.ps_status.value = "Success! Script Created."
                self.ps_status.color = "GREEN"
            except Exception as ex:
                self.ps_status.value = f"Error: {ex}"
                self.ps_status.color = "RED"
            finally:
                self.ps_btn_upload.disabled = False
                self.update()

        import threading
        threading.Thread(target=_bg, daemon=True).start()


    # --- Remediation Tab ---
    def _build_remediation_tab(self):
        self.rem_name = ft.TextField(label="Remediation Name")
        self.rem_desc = ft.TextField(label="Description", multiline=True)

        self.det_file_btn = ft.ElevatedButton("Select Detection (.ps1)...", icon=ft.Icons.SEARCH, on_click=self._pick_det_file)
        self.det_file_label = ft.Text("No detection script", italic=True)

        self.rem_file_btn = ft.ElevatedButton("Select Remediation (.ps1)...", icon=ft.Icons.HEALING, on_click=self._pick_rem_file)
        self.rem_file_label = ft.Text("No remediation script", italic=True)

        self.rem_context = ft.Dropdown(
            label="Run Context",
            options=[ft.dropdown.Option("system"), ft.dropdown.Option("user")],
            value="system"
        )
        self.rem_btn_upload = ft.ElevatedButton("Upload Remediation", icon=ft.Icons.CLOUD_UPLOAD, on_click=self._upload_rem_script)
        self.rem_status = ft.Text("")

        return ft.Container(
            content=ft.Column([
                ft.Text("Upload Proactive Remediation", size=20, weight=ft.FontWeight.BOLD),
                self.rem_name,
                self.rem_desc,
                ft.Row([self.det_file_btn, self.det_file_label]),
                ft.Row([self.rem_file_btn, self.rem_file_label]),
                self.rem_context,
                ft.Container(height=20),
                self.rem_btn_upload,
                self.rem_status
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            padding=20
        )

    def _pick_det_file(self, e):
        path = FilePickerHelper.pick_file(allowed_extensions=["ps1"])
        if path:
            self.detect_path = path
            self.det_file_label.value = Path(path).name
            if not self.rem_name.value:
                self.rem_name.value = Path(path).stem
            self.update()

    def _pick_rem_file(self, e):
        path = FilePickerHelper.pick_file(allowed_extensions=["ps1"])
        if path:
            self.remediate_path = path
            self.rem_file_label.value = Path(path).name
            self.update()

    def _upload_rem_script(self, e):
        if not self.rem_name.value or not self.detect_path or not self.remediate_path:
            self._show_snack("Name, Detection and Remediation scripts are required", "RED")
            return

        # Check Credentials
        tenant = SwitchCraftConfig.get_value("IntuneTenantID")
        client = SwitchCraftConfig.get_value("IntuneClientID")
        secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret")

        if not all([tenant, client, secret]):
            self._show_snack("Intune Credentials missing in Settings", "RED")
            return

        self.rem_status.value = "Uploading..."
        self.rem_btn_upload.disabled = True
        self.update()

        def _bg():
            try:
                token = self.intune_service.authenticate(tenant, client, secret)

                with open(self.detect_path, "r", encoding="utf-8") as f:
                    det_content = f.read()
                with open(self.remediate_path, "r", encoding="utf-8") as f:
                    rem_content = f.read()

                self.intune_service.upload_remediation_script(
                    token, self.rem_name.value, self.rem_desc.value, det_content, rem_content, self.rem_context.value
                )

                self.rem_status.value = "Success! Remediation Created."
                self.rem_status.color = "GREEN"
            except Exception as ex:
                self.rem_status.value = f"Error: {ex}"
                self.rem_status.color = "RED"
            finally:
                self.rem_btn_upload.disabled = False
                self.update()

        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _show_snack(self, msg, color="GREEN"):
        try:
            self.app_page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.app_page.snack_bar.open = True
            self.app_page.update()
        except Exception:
            pass
