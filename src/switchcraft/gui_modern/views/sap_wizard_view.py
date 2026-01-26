import flet as ft
import logging
import os
from pathlib import Path
from switchcraft.gui_modern.utils.view_utils import ViewMixin
from switchcraft.utils.i18n import i18n
from switchcraft.services.sap_service import SapService

logger = logging.getLogger(__name__)

class SapWizardView(ft.Column, ViewMixin):
    """
    Wizard-style UI for SAP Installation Server management.
    Handles merging updates, customization, and packaging.
    """

    def __init__(self, page: ft.Page):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
        self.app_page = page
        self.sap_service = SapService()

        # State
        self.server_path = ""
        self.update_files = []
        self.logo_path = ""
        self.use_webview2 = True
        self.arch_group = ft.RadioGroup(content=ft.Row([
            ft.Radio(value="32", label="32-bit (Win32)"),
            ft.Radio(value="64", label="64-bit (Win64)")
        ]), value="64")

        self.current_step = 1
        self.content_area = ft.Container(expand=True)
        self.controls = [
            ft.Text(i18n.get("sap_wizard_title") or "SAP Management Wizard", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            self.content_area,
            self._build_nav_buttons()
        ]

        from switchcraft.utils.shell_utils import ShellUtils
        self.is_admin = ShellUtils.is_admin()

        if not self.is_admin:
             self.content_area.content = self._build_admin_warning()
             # Hide nav buttons if not admin
             self.controls[-1].visible = False
        else:
             self._show_step(1)

    def _build_admin_warning(self):
        from switchcraft.utils.shell_utils import ShellUtils
        return ft.Column([
            ft.Icon(ft.Icons.SECURITY, size=64, color="RED"),
            ft.Text(i18n.get("sap_admin_required_title") or "Administrator Privileges Required", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(i18n.get("sap_admin_required_desc") or "The SAP Installation Server Administration Tool (NwSapSetupAdmin.exe) requires administrative rights to merge updates and create packages."),
            ft.Container(height=20),
            ft.FilledButton(
                i18n.get("btn_restart_admin") or "Restart SwitchCraft as Admin",
                icon=ft.Icons.SHIELD,
                on_click=lambda _: ShellUtils.restart_as_admin(),
                bgcolor="RED", color="WHITE"
            )
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True)

    def _show_step(self, step_num):
        if not self.is_admin:
            return

        self.current_step = step_num
        if step_num == 1:
            self.content_area.content = self._build_step_1()
        elif step_num == 2:
            self.content_area.content = self._build_step_2()
        elif step_num == 3:
            self.content_area.content = self._build_step_3()
        elif step_num == 4:
            self.content_area.content = self._build_step_4()
        self.update()

    def _build_step_1(self):
        """Step 1: Select SAP Installation Server path."""
        def on_pick_server(e: ft.FilePickerResultEvent):
            if e.path:
                self.server_path = e.path
                path_text.value = e.path
                self.update()

        path_text = ft.Text(self.server_path or "No path selected", italic=True)
        fp = ft.FilePicker()
        fp.on_result = on_pick_server
        self.app_page.overlay.append(fp)

        return ft.Column([
            ft.Text(i18n.get("sap_step1_title") or "1. Select SAP Installation Server", size=18, weight=ft.FontWeight.BOLD),
            ft.Text(i18n.get("sap_step1_desc") or "Point to the root folder of your SAP nwsetupadmin server."),
            ft.Row([
                ft.FilledButton(i18n.get("btn_browse_folder") or "Browse Server Folder", icon=ft.Icons.FOLDER_OPEN, on_click=lambda _: fp.get_directory_path()),
                path_text
            ]),
            ft.Divider(height=20, color="TRANSPARENT"),
            ft.Text(i18n.get("sap_arch_select") or "Architecture:", weight=ft.FontWeight.BOLD),
            self.arch_group
        ])

    def _build_step_2(self):
        """Step 2: Add Updates/Add-ons."""
        return ft.Column([
            ft.Text(i18n.get("sap_step2_title") or "2. Add Updates & Add-ons (Optional)", size=18, weight=ft.FontWeight.BOLD),
            ft.Text(i18n.get("sap_step2_desc") or "Select .exe files to merge into the installation server."),
            ft.FilledButton(i18n.get("btn_add_update") or "Add Update EXE", icon=ft.Icons.ADD, on_click=lambda _: self._show_snack("Not implemented in stub")),
            ft.ListView(expand=True, height=100) # Placeholder for file list
        ])

    def _build_step_3(self):
        """Step 3: Customization."""
        return ft.Column([
            ft.Text(i18n.get("sap_step3_title") or "3. Customization", size=18, weight=ft.FontWeight.BOLD),
            ft.Checkbox(label=i18n.get("sap_use_webview2") or "Default to Edge WebView2 (Recommended)", value=self.use_webview2, on_change=lambda e: setattr(self, 'use_webview2', e.control.value)),
            ft.Row([
                ft.FilledButton(i18n.get("btn_select_logo") or "Select Custom Logo", icon=ft.Icons.IMAGE),
                ft.Text(i18n.get("no_logo_selected") or "No logo selected", italic=True)
            ])
        ])

    def _build_step_4(self):
        """Step 4: Summary & Packaging."""
        # Refresh packages list on entry
        packages = []
        try:
            packages = self.sap_service.list_packages(self.server_path)
        except:
            pass

        opts = [ft.dropdown.Option(p['name']) for p in packages]
        # Default to first if available, else standard SAPGUI
        default_val = packages[0]['name'] if packages else "SAPGUI"

        self.package_dd = ft.Dropdown(
            label=i18n.get("sap_package_select") or "Select Package to Build",
            options=opts,
            value=default_val,
            width=400
        )

        return ft.Column([
            ft.Text(i18n.get("sap_step4_title") or "4. Summary & Packaging", size=18, weight=ft.FontWeight.BOLD),
            ft.Text(f"{i18n.get('label_server') or 'Server'}: {self.server_path}"),
            ft.Text(f"Architecture: {self.arch_group.value}-bit"),
            ft.Text(f"{i18n.get('label_custom_logo') or 'Custom Logo'}: {'Yes' if self.logo_path else 'No'}"),
            ft.Text(f"{i18n.get('label_webview2') or 'Edge WebView2'}: {'Enabled' if self.use_webview2 else 'Disabled'}"),
            ft.Divider(),
            self.package_dd,
            ft.Container(height=10),
            ft.FilledButton(i18n.get("btn_apply_build") or "Apply & Build Packaging", icon=ft.Icons.BUILD_CIRCLE, bgcolor="PRIMARY", color="WHITE", on_click=self._on_finalize)
        ])

    def _build_nav_buttons(self):
        return ft.Row([
            ft.TextButton(i18n.get("btn_back") or "Back", on_click=lambda _: self._show_step(self.current_step - 1) if self.current_step > 1 else None),
            ft.FilledButton(i18n.get("btn_next") or "Next", on_click=lambda _: self._show_step(self.current_step + 1) if self.current_step < 4 else None)
        ], alignment=ft.MainAxisAlignment.END)

    def _on_finalize(self, _):
        if not self.server_path:
            self._show_snack("Please select a server path first.", color="RED")
            return

        try:
            target_path = self.server_path
            if self.arch_group.value == "64":
                 if "Win32" in target_path:
                     target_path = target_path.replace("Win32", "Win64")
                 elif "Win64" not in target_path and (Path(target_path) / "Win64").exists():
                     target_path = str(Path(target_path) / "Win64")

            # 1. Customize
            self.sap_service.customize_server(target_path, self.logo_path, self.use_webview2)
            self._show_snack("SAP Server customized successfully!", color="GREEN")

            # 2. Build
            pkg_name = self.package_dd.value
            if not pkg_name:
                self._show_snack("Please select a package to build.", color="RED")
                return

            import tempfile
            # Use %TEMP%\SwitchCraft\Dist
            temp_dir = Path(tempfile.gettempdir()) / "SwitchCraft" / "Dist"
            out_dir = str(temp_dir)

            self._show_snack(f"Building package '{pkg_name}'... Please wait...", color="BLUE")
            self.app_page.update()

            # Use threading to avoid UI freeze if desired, but for now simple blocking is safer for debugging logic
            out_file = self.sap_service.create_single_file_installer(target_path, pkg_name, out_dir)

            self._show_snack(f"Build Success! Installer at: {out_file}", color="GREEN", duration=5000)

            # Auto-open in Explorer
            try:
                os.startfile(out_dir)
            except Exception as e:
                logger.error(f"Failed to open explorer: {e}")

        except Exception as e:
            logger.error(f"SAP Finalize Error: {e}")
            self._show_snack(f"Error: {e}", color="RED")
