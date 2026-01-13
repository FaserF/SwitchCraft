import flet as ft
import threading
import logging
import webbrowser
from switchcraft.services.addon_service import AddonService
from switchcraft.utils.i18n import i18n
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
        self.results_count = ft.Text("", size=12, color="GREY_500")

        # Filter dropdown
        self.filter_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("all", i18n.get("winget_filter_all") or "All Fields"),
                ft.dropdown.Option("name", i18n.get("winget_filter_name") or "Name"),
                ft.dropdown.Option("id", i18n.get("winget_filter_id") or "Package ID"),
                ft.dropdown.Option("publisher", i18n.get("winget_filter_publisher") or "Publisher"),
            ],
            value="all",
            width=130,
            height=48,
            text_size=14,
            content_padding=ft.Padding(10, 0, 10, 0),
            border_radius=8,
        )

        self.search_field = ft.TextField(
            hint_text=i18n.get("winget_search_hint") or "Search apps...",
            expand=True,
            height=48,
            text_size=14,
            content_padding=ft.Padding(12, 0, 12, 0),
            border_radius=8,
            on_submit=self._run_search
        )

        btn_search = ft.IconButton(
            icon=ft.Icons.SEARCH_ROUNDED,
            icon_color="BLUE_400",
            tooltip=i18n.get("search") or "Search",
            on_click=self._run_search
        )

        # Left Pane with filter row
        left_pane = ft.Container(
            content=ft.Column([
                ft.Text("Winget Explorer", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [self.filter_dropdown, self.search_field, btn_search],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                self.results_count,
                ft.Divider(height=10, thickness=1),
                self.search_results
            ], expand=True),
            width=420,
            padding=15,
            bgcolor="SURFACE_CONTAINER_HIGHEST" if hasattr(getattr(ft, "colors", None), "SURFACE_CONTAINER_HIGHEST") else "GREY_900",
            border_radius=15
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
                    ft.Icon(ft.Icons.SEARCH, size=40, color="GREY_600"),
                    ft.Text(i18n.get("winget_search_instruction") or "Enter a search term to start.",
                            color="GREY_600", text_align=ft.TextAlign.CENTER)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=20,
                alignment=ft.Alignment(0, 0)
            )
        )

        self.controls = [left_pane, right_pane]

    def _run_search(self, e):
        query = self.search_field.value
        if not query:
            return

        filter_by = self.filter_dropdown.value or "all"
        self.results_count.value = ""
        self.search_results.controls.clear()
        self.search_results.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.ProgressRing(width=40, height=40),
                    ft.Text(i18n.get("winget_searching") or "Searching...", size=16),
                    ft.Text(f"'{query}'", size=12, color="GREY_500")
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                alignment=ft.Alignment(0, 0),
                expand=True,
                padding=40
            )
        )
        try:
            self.page.update()
        except Exception:
            pass

        def _search():
            try:
                result_holder = {"data": None, "error": None}

                def target():
                    try:
                        result_holder["data"] = self.winget.search_packages(query)
                    except Exception as e:
                        result_holder["error"] = e

                t = threading.Thread(target=target)
                t.start()
                t.join(timeout=30)  # Reduced to 30 seconds

                if t.is_alive():
                    self.search_results.controls.clear()
                    self.search_results.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Icon(ft.Icons.WARNING, color="ORANGE", size=40),
                                ft.Text(i18n.get("winget_search_timeout") or "Search is taking too long...", color="ORANGE"),
                                ft.Text(i18n.get("winget_search_timeout_hint") or "Try a more specific search term.", size=12, color="GREY_500")
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                            alignment=ft.Alignment(0, 0),
                            padding=40
                        )
                    )
                    try:
                        self.page.update()
                    except Exception:
                        pass
                    return

                if result_holder["error"]:
                    raise result_holder["error"]

                self._show_list(result_holder["data"], filter_by, query)
            except Exception as ex:
                logger.error(f"Winget search error: {ex}")
                self.search_results.controls.clear()
                self.search_results.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.ERROR, color="RED", size=40),
                            ft.Text(f"Error: {ex}", color="RED")
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                        alignment=ft.Alignment(0, 0),
                        padding=40
                    )
                )
                try:
                    self.page.update()
                except Exception:
                    pass

        threading.Thread(target=_search, daemon=True).start()

    def _show_list(self, results, filter_by="all", query=""):
        logger.debug(f"Showing Winget results: count={len(results) if results else 0}, filter={filter_by}, query='{query}'")
        self.search_results.controls.clear()

        # Filter results based on selected filter
        if results and filter_by != "all" and query:
            query_lower = query.lower()
            filtered_results = []
            for item in results:
                if filter_by == "name" and query_lower in item.get('Name', '').lower():
                    filtered_results.append(item)
                elif filter_by == "id" and query_lower in item.get('Id', '').lower():
                    filtered_results.append(item)
                elif filter_by == "publisher":
                    # Publisher is in ID prefix (before the dot)
                    pkg_id = item.get('Id', '')
                    if '.' in pkg_id and query_lower in pkg_id.split('.')[0].lower():
                        filtered_results.append(item)
            results = filtered_results

        # Update results count
        count = len(results) if results else 0
        self.results_count.value = f"Found {count} app{'s' if count != 1 else ''}"

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

        # Header Section
        self.details_area.controls.append(ft.Text(info.get('Name', 'Unknown'), size=28, weight=ft.FontWeight.BOLD))
        self.details_area.controls.append(ft.Text(info.get('Id', ''), color="grey", size=14))

        # Version Badge
        version = info.get('Version', 'Unknown')
        self.details_area.controls.append(
            ft.Container(
                content=ft.Text(f"v{version}", color="WHITE", size=12),
                bgcolor="BLUE_700",
                padding=ft.Padding(8, 4, 8, 4),
                border_radius=4,
                margin=ft.Margin(0, 8, 0, 8)
            )
        )

        self.details_area.controls.append(ft.Divider())

        # Description Section (prominent like winstall.app)
        description = info.get('Description') or info.get('description')
        if description:
            self.details_area.controls.append(ft.Text("About", size=18, weight=ft.FontWeight.BOLD))
            self.details_area.controls.append(
                ft.Container(
                    content=ft.Text(description, size=14, selectable=True),
                    padding=ft.Padding(0, 8, 0, 16)
                )
            )

        # Publisher/Author Info
        publisher = info.get('Publisher') or info.get('publisher')
        author = info.get('Author') or info.get('author')
        if publisher or author:
            pub_text = publisher or author
            self.details_area.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.BUSINESS, size=16, color="GREY_500"),
                    ft.Text("Publisher: ", weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(pub_text, size=14)
                ], spacing=4)
            )

        # License Section
        license_val = info.get('License') or info.get('license')
        license_url = info.get('LicenseUrl') or info.get('license url')
        if license_val or license_url:
            license_row = [
                ft.Icon(ft.Icons.GAVEL, size=16, color="GREY_500"),
                ft.Text("License: ", weight=ft.FontWeight.BOLD, size=14),
            ]
            if license_url:
                license_row.append(ft.TextButton(
                    content=ft.Text(license_val or "View License"),
                    on_click=lambda e, url=license_url: self._open_url(url)
                ))
            else:
                license_row.append(ft.Text(license_val, size=14))
            self.details_area.controls.append(ft.Row(license_row, spacing=4))

        # Tags Section
        tags = info.get('Tags') or info.get('tags')
        if tags:
            tag_list = tags.split('\n') if '\n' in tags else tags.split(',') if ',' in tags else [tags]
            tag_chips = []
            for tag in tag_list[:10]:  # Limit to 10 tags
                tag = tag.strip()
                if tag:
                    tag_chips.append(
                        ft.Container(
                            content=ft.Text(tag, size=11, color="BLUE_700"),
                            bgcolor="BLUE_50" if hasattr(getattr(ft, "colors", None), "BLUE_50") else "BLUE_900",
                            padding=ft.Padding(8, 4, 8, 4),
                            border_radius=12
                        )
                    )
            if tag_chips:
                self.details_area.controls.append(ft.Container(height=8))
                self.details_area.controls.append(
                    ft.Row([
                        ft.Icon(ft.Icons.LABEL, size=16, color="GREY_500"),
                        ft.Text("Tags: ", weight=ft.FontWeight.BOLD, size=14),
                    ], spacing=4)
                )
                self.details_area.controls.append(ft.Row(tag_chips, wrap=True, spacing=6))

        self.details_area.controls.append(ft.Container(height=12))

        # Links Section
        self.details_area.controls.append(ft.Text("Links", size=16, weight=ft.FontWeight.BOLD))

        # Homepage
        homepage = info.get('Homepage') or info.get('homepage')
        if homepage:
            self.details_area.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.HOME, size=16, color="BLUE_400"),
                    ft.TextButton(content=ft.Text("Homepage"), on_click=lambda e, url=homepage: self._open_url(url))
                ], spacing=4)
            )

        # Publisher URL
        pub_url = info.get('PublisherUrl') or info.get('publisher url')
        if pub_url:
            self.details_area.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.BUSINESS, size=16, color="BLUE_400"),
                    ft.TextButton(content=ft.Text("Publisher Website"), on_click=lambda e, url=pub_url: self._open_url(url))
                ], spacing=4)
            )

        # Privacy URL
        privacy_url = info.get('PrivacyUrl') or info.get('privacy url')
        if privacy_url:
            self.details_area.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.PRIVACY_TIP, size=16, color="BLUE_400"),
                    ft.TextButton(content=ft.Text("Privacy Policy"), on_click=lambda e, url=privacy_url: self._open_url(url))
                ], spacing=4)
            )

        # Release Notes URL
        release_notes_url = info.get('ReleaseNotesUrl') or info.get('release notes url')
        if release_notes_url:
            self.details_area.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.NEW_RELEASES, size=16, color="BLUE_400"),
                    ft.TextButton(content=ft.Text("Release Notes"), on_click=lambda e, url=release_notes_url: self._open_url(url))
                ], spacing=4)
            )

        # Manifest Link (GitHub)
        manifest = info.get('ManifestUrl')
        if not manifest and info.get('Id'):
            pkg_id = info.get('Id')
            try:
                parts = pkg_id.split('.', 1)
                if len(parts) >= 2:
                    publisher_part = parts[0]
                    first_char = publisher_part[0].lower()
                    manifest = f"https://github.com/microsoft/winget-pkgs/tree/master/manifests/{first_char}/{publisher_part}/{parts[1]}"
                else:
                    manifest = f"https://github.com/microsoft/winget-pkgs/tree/master/manifests/{pkg_id[0].lower()}/{pkg_id}"
            except (IndexError, ValueError):
                pass

        if manifest:
            self.details_area.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.CODE, size=16, color="BLUE_400"),
                    ft.TextButton(content=ft.Text("View Manifest on GitHub"), on_click=lambda e, url=manifest: self._open_url(url))
                ], spacing=4)
            )

        # Winstall.app link
        pkg_id = info.get('Id')
        if pkg_id:
            winstall_url = f"https://winstall.app/apps/{pkg_id}"
            self.details_area.controls.append(
                ft.Row([
                    ft.Icon(ft.Icons.WEB, size=16, color="PURPLE_400"),
                    ft.TextButton(content=ft.Text("View on winstall.app"), on_click=lambda e, url=winstall_url: self._open_url(url))
                ], spacing=4)
            )

        self.details_area.controls.append(ft.Divider())

        # Actions
        btn_copy = ft.ElevatedButton("Copy Command", icon=ft.Icons.COPY, bgcolor="GREY_700", color="WHITE")
        btn_copy.on_click = lambda e, i=info: self._copy_install_command(i)

        btn_local = ft.ElevatedButton("Install Locally", icon=ft.Icons.DOWNLOAD, bgcolor="GREEN", color="WHITE")
        btn_local.on_click = self._install_local

        btn_deploy = ft.ElevatedButton("Deploy / Package...", icon=ft.Icons.CLOUD_UPLOAD, bgcolor="BLUE", color="WHITE")
        btn_deploy.on_click = lambda e: self._open_deploy_menu(info)

        self.details_area.controls.append(ft.Row([btn_copy, btn_local, btn_deploy], wrap=True, spacing=8))

        # Tip
        self.details_area.controls.append(ft.Container(height=20))
        self.details_area.controls.append(ft.Text("Tip: Use SwitchCraft Winget-AutoUpdate to keep apps fresh!", color="GREY", italic=True))

        self.update()

    def _copy_install_command(self, info):
        """Copy the winget install command to clipboard."""
        pkg_id = info.get('Id', '')
        command = f"winget install --id {pkg_id} --accept-package-agreements --accept-source-agreements"
        self._copy_to_clipboard(command)
        self._show_snack(f"Copied: {command}", "GREEN_700")

    def _open_url(self, url: str):
        """Open URL in default browser."""
        try:
            webbrowser.open(url)
        except Exception as ex:
            logger.error(f"Failed to open URL: {ex}")

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard."""
        try:
            import pyperclip
            pyperclip.copy(text)
        except ImportError:
            # Fallback for systems without pyperclip
            try:
                import subprocess
                subprocess.run(['clip'], input=text.encode('utf-8'), check=True)
            except Exception:
                pass

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
                    style=ft.ButtonStyle(bgcolor="GREEN", color="WHITE"),
                    on_click=lambda e: [close_dlg(e), self._deploy_wau(info)], width=250),
                ft.Text("Best for keeping apps updated automatically.", size=12, italic=True),

                ft.Container(height=5),
                ft.ElevatedButton("Download & Package", icon=ft.Icons.ARCHIVE,
                    style=ft.ButtonStyle(bgcolor="BLUE", color="WHITE"),
                    on_click=lambda e: [close_dlg(e), self._deploy_package(info)], width=250),
                ft.Text("Download installer and prepare for Intune.", size=12, italic=True),

                ft.Container(height=5),
                ft.ElevatedButton("Create Install Script", icon=ft.Icons.CODE,
                    style=ft.ButtonStyle(bgcolor="GREY_700", color="WHITE"),
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
        self._show_snack("WAU info opened in browser.")


    def _deploy_package(self, info):
        import tempfile
        import shutil
        import subprocess

        pkg_id = info.get('Id')
        self._show_snack(f"Downloading {pkg_id} for packaging...", "BLUE")

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

                    self._show_snack(f"Downloaded to {dest}", "GREEN")
                    # TODO: Maybe auto-switch to Analyzer?
                else:
                    self._show_snack("Download success but no installer found?", "ORANGE")

                shutil.rmtree(tmp_dir)

            except Exception as ex:
                self._show_snack(f"Download failed: {ex}", "RED")

        threading.Thread(target=_bg, daemon=True).start()

    def _deploy_script(self, info):
        self._create_script_click(None) # Re-use existing simple script or enhance it?
        # Enhancing existing method to be more advanced is better.

    def _install_local(self, e):
        if not self.current_pkg:
            return
        pkg_id = self.current_pkg.get('Id')
        cmd = f"winget install --id {pkg_id} --silent --accept-package-agreements --accept-source-agreements"

        def _run():
            import subprocess
            self._show_snack(f"Starting install for {pkg_id}...", "BLUE")
            try:
                subprocess.Popen(f'start cmd /k "{cmd}"', shell=True)
            except Exception as ex:
                self._show_snack(f"Failed to start install: {ex}", "RED")

        _run()

    def _create_script_click(self, e):
        if not self.current_pkg:
            return
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
                self._show_snack(f"Script saved to {path}", "GREEN")
            except Exception as ex:
                self._show_snack(f"Save failed: {ex}", "RED")

    def _show_snack(self, msg, color="GREEN"):
        try:
            self.app_page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.app_page.snack_bar.open = True
            self.app_page.update()
        except Exception:
             pass
