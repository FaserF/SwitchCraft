import flet as ft
import threading
import logging
from switchcraft.services.addon_service import AddonService
from switchcraft.utils.i18n import i18n
from switchcraft.utils.config import SwitchCraftConfig
from pathlib import Path
from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper

logger = logging.getLogger(__name__)

class ModernWingetView(ft.Row):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.winget = None

        # Try to load helper
        winget_mod = AddonService.import_addon_module("winget", "utils.winget")
        if winget_mod:
            try:
                self.winget = winget_mod.WingetHelper()
            except Exception:
                pass

        self.current_pkg = None

        if not self.winget:
            self.controls = [
                ft.Column([
                    ft.Icon(ft.Icons.ERROR, color="red", size=50),
                    ft.Text("Winget Addon not available.", size=20)
                ], alignment=ft.MainAxisAlignment.CENTER, expand=True)
            ]
            self.alignment = ft.MainAxisAlignment.CENTER
            return

        # State
        self.search_results = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        self.details_area = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        self.search_field = ft.TextField(
            label=i18n.get("tab_winget") or "Search Winget",
            hint_text=i18n.get("winget_search_placeholder") or "Apps suchen...",
            expand=True,
        )
        self.search_field.on_submit = self._run_search

        btn_search = ft.IconButton(ft.Icons.SEARCH)
        btn_search.on_click = self._run_search

        # Left Pane
        left_pane = ft.Container(
            content=ft.Column([
                ft.Row([self.search_field, btn_search]),
                ft.Divider(),
                self.search_results
            ], expand=True),
            width=350,
            padding=10,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST if hasattr(ft.Colors, "SURFACE_CONTAINER_HIGHEST") else ft.Colors.GREY_900,
            border_radius=10
        )

        # Right Pane
        right_pane = ft.Container(
            content=self.details_area,
            expand=True,
            padding=20,
        )

        # Initial instruction
        self.search_results.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.SEARCH, size=40, color=ft.Colors.GREY_600),
                    ft.Text(i18n.get("winget_search_instruction") or "Enter a search term to start.",
                            color=ft.Colors.GREY_600, text_align=ft.TextAlign.CENTER)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
                alignment=ft.Alignment.CENTER
            )
        )

        self.controls = [left_pane, right_pane]

    def _run_search(self, e):
        query = self.search_field.value
        if not query:
            return

        self.search_results.controls.clear()
        self.search_results.controls.append(
            ft.Column([
                ft.ProgressBar(),
                ft.Text(i18n.get("winget_searching") or "Searching...")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        self.update()

        def _search():
            try:
                results = self.winget.search_packages(query)
                self._show_list(results)
            except Exception as ex:
                self.search_results.controls.clear()
                self.search_results.controls.append(ft.Text(f"Error: {ex}", color="red"))
                self.update()

        threading.Thread(target=_search, daemon=True).start()

    def _show_list(self, results):
        self.search_results.controls.clear()
        if not results:
            self.search_results.controls.append(ft.Text(i18n.get("winget_no_results") or "No results found."))
        else:
            for item in results:
                tile = ft.ListTile(
                    leading=ft.Icon(ft.Icons.APPS),
                    title=ft.Text(item.get('Name', 'Unknown')),
                    subtitle=ft.Text(f"{item.get('Id', '')} - {item.get('Version', '')}"),
                )
                # Capture item in lambda default arg
                tile.on_click = lambda e, i=item: self._load_details(i)
                self.search_results.controls.append(tile)
        self.update()

    def _load_details(self, short_info):
        self.details_area.controls.clear()
        self.details_area.controls.append(ft.ProgressBar())
        self.update()

        def _fetch():
            try:
                full = self.winget.get_package_details(short_info['Id'])
                merged = {**short_info, **full}
                self.current_pkg = merged
                self._show_details_ui(merged)
            except Exception as ex:
                self.details_area.controls.clear()
                self.details_area.controls.append(ft.Text(f"Error: {ex}", color="red"))
                self.update()

        threading.Thread(target=_fetch, daemon=True).start()

    def _show_details_ui(self, info):
        self.details_area.controls.clear()
        self.details_area.controls.append(ft.Text(info.get('Name', 'Unknown'), size=28, weight=ft.FontWeight.BOLD))
        self.details_area.controls.append(ft.Text(info.get('Id', ''), color="grey"))
        self.details_area.controls.append(ft.Divider())

        for key in ['Publisher', 'Description', 'License', 'Homepage']:
            val = info.get(key.lower()) or info.get(key)
            if val:
                self.details_area.controls.append(ft.Text(f"{key}: {val}"))

        self.details_area.controls.append(ft.Divider())

        # Actions
        btn_local = ft.ElevatedButton("Install Locally", icon=ft.Icons.DOWNLOAD, bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE)
        btn_local.on_click = self._install_local

        btn_deploy = ft.ElevatedButton("Deploy / Package...", icon=ft.Icons.CLOUD_UPLOAD, bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)
        btn_deploy.on_click = lambda e: self._open_deploy_menu(info)

        self.details_area.controls.append(ft.Row([btn_local, btn_deploy], wrap=True))

        # Tip
        self.details_area.controls.append(ft.Container(height=20))
        self.details_area.controls.append(ft.Text("Tip: Use SwitchCraft Winget-AutoUpdate to keep apps fresh!", color=ft.Colors.GREY, italic=True))

        self.update()

    def _open_deploy_menu(self, info):
        def close_dlg(e):
            self.app_page.dialog.open = False
            self.app_page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Deploy {info.get('Name')}", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text("Select a deployment method:", size=16),
                ft.Container(height=10),

                ft.ElevatedButton("Winget-AutoUpdate (WAU)", icon=ft.Icons.UPDATE,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE),
                    on_click=lambda e: [close_dlg(e), self._deploy_wau(info)], width=250),
                ft.Text("Best for keeping apps updated automatically.", size=12, italic=True),

                ft.Container(height=5),
                ft.ElevatedButton("Download & Package", icon=ft.Icons.ARCHIVE,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE),
                    on_click=lambda e: [close_dlg(e), self._deploy_package(info)], width=250),
                ft.Text("Download installer and prepare for Intune.", size=12, italic=True),

                ft.Container(height=5),
                ft.ElevatedButton("Create Install Script", icon=ft.Icons.CODE,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_700, color=ft.Colors.WHITE),
                    on_click=lambda e: [close_dlg(e), self._deploy_script(info)], width=250),
                ft.Text("Generate PowerShell script for deployment.", size=12, italic=True),
            ], height=300, width=400, alignment=ft.MainAxisAlignment.CENTER),
            actions=[ft.TextButton("Cancel", on_click=close_dlg)],
        )
        self.app_page.dialog = dlg
        dlg.open = True
        self.app_page.update()

    def _deploy_wau(self, info):
        import webbrowser
        webbrowser.open("https://github.com/Romanitho/Winget-AutoUpdate")
        self.app_page.open(ft.SnackBar(ft.Text("WAU info opened in browser.")))

    def _deploy_package(self, info):
        import tempfile
        import shutil
        import subprocess

        pkg_id = info.get('Id')
        self.app_page.open(ft.SnackBar(ft.Text(f"Downloading {pkg_id} for packaging...")))

        def _bg():
            try:
                tmp_dir = tempfile.mkdtemp()
                # Run winget download
                # Note: 'winget download' requires a newer winget version, but user has it if using SwitchCraft
                cmd = f'winget download --id {pkg_id} --dir "{tmp_dir}" --accept-source-agreements --accept-package-agreements --silent'
                subprocess.run(cmd, shell=True, check=True)

                # Find file
                files = list(Path(tmp_dir).glob("*.*"))
                installer = None
                for f in files:
                    if f.suffix.lower() in [".exe", ".msi"]:
                        installer = f
                        break

                if installer:
                    dest_dir = Path.home() / "Downloads" / "SwitchCraft_Winget"
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest = dest_dir / installer.name
                    shutil.copy(installer, dest)

                    self.app_page.open(ft.SnackBar(ft.Text(f"Downloaded to {dest}"), bgcolor=ft.Colors.GREEN))
                    # TODO: Maybe auto-switch to Analyzer?
                else:
                    self.app_page.open(ft.SnackBar(ft.Text("Download success but no installer found?"), bgcolor=ft.Colors.ORANGE))

                shutil.rmtree(tmp_dir)

            except Exception as ex:
                self.app_page.open(ft.SnackBar(ft.Text(f"Download failed: {ex}"), bgcolor=ft.Colors.RED))

        threading.Thread(target=_bg, daemon=True).start()

    def _deploy_script(self, info):
        self._create_script_click(None) # Re-use existing simple script or enhance it?
        # Enhancing existing method to be more advanced is better.

    def _install_local(self, e):
        if not self.current_pkg: return
        pkg_id = self.current_pkg.get('Id')
        cmd = f"winget install --id {pkg_id} --silent --accept-package-agreements --accept-source-agreements"

        def _run():
            import subprocess
            self.app_page.open(ft.SnackBar(ft.Text(f"Starting install for {pkg_id}...")))
            try:
                subprocess.Popen(f'start cmd /k "{cmd}"', shell=True)
            except Exception as ex:
                self.app_page.open(ft.SnackBar(ft.Text(f"Failed to start install: {ex}"), bgcolor=ft.Colors.RED))

        _run()

    def _create_script_click(self, e):
        if not self.current_pkg: return
        default_name = f"Install-{self.current_pkg.get('Name', 'App')}.ps1"
        default_name = "".join(x for x in default_name if x.isalnum() or x in "-_.")

        path = FilePickerHelper.save_file(dialog_title="Save Winget Script", file_name=default_name, allowed_extensions=["ps1"])
        if path:
            script_content = f"""<#
.NOTES
Generated by SwitchCraft via Winget Integration
App: {self.current_pkg.get('Name')}
ID: {self.current_pkg.get('Id')}
#>
$PackageId = "{self.current_pkg.get('Id')}"
$LogPath = "$env:ProgramData\\Microsoft\\IntuneManagementExtension\\Logs\\Winget-$PackageId.log"

Start-Transcript -Path $LogPath -Force

Write-Host "Installing $PackageId via Winget..."
$winget = Get-Command winget -ErrorAction SilentlyContinue
if (!$winget) {{
    Write-Error "Winget not found!"
    exit 1
}}

& winget install --id $PackageId --accept-package-agreements --accept-source-agreements --scope machine
$err = $LASTEXITCODE

Stop-Transcript
exit $err
"""
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(script_content)
                self.app_page.open(ft.SnackBar(ft.Text(f"Script saved to {path}"), bgcolor=ft.Colors.GREEN))
            except Exception as ex:
                self.app_page.open(ft.SnackBar(ft.Text(f"Save failed: {ex}"), bgcolor=ft.Colors.RED))
