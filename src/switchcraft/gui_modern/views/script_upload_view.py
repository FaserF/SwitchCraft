import flet as ft
from switchcraft.services.intune_service import IntuneService
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.utils.flet_compat import create_tabs
import logging
from pathlib import Path
import threading
import requests
from switchcraft.gui_modern.utils.view_utils import ViewMixin

logger = logging.getLogger(__name__)


class ScriptUploadView(ft.Column, ViewMixin):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.intune_service = IntuneService()

        # State
        self.script_path = None
        self.detect_path = None  # For Remediation
        self.remediate_path = None  # For Remediation
        self.repo_script_items = []  # Track (path, checkbox) for GitHub View
        self.current_owner = None
        self.current_repo = None

        # Initialize File Pickers once to prevent duplicate overlays on tab switch
        self.ps_picker = ft.FilePicker()
        self.ps_picker.on_result = self._on_ps_picked

        self.det_picker = ft.FilePicker()
        self.det_picker.on_result = self._on_det_picked

        self.rem_picker = ft.FilePicker()
        self.rem_picker.on_result = self._on_rem_picked

        self.folder_picker = ft.FilePicker()
        self.folder_picker.on_result = self._on_import_folder_picked

        if self.app_page:
            self.app_page.overlay.extend([self.ps_picker, self.det_picker, self.rem_picker, self.folder_picker])
            self.app_page.update()

        # UI Components - wrapped in container with proper padding
        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text(
                        i18n.get("script_management_title") or "Script Management Center",
                        size=28,
                        weight=ft.FontWeight.BOLD
                    ),
                    ft.Text(
                        i18n.get("script_management_subtitle") or
                        "Upload PowerShell & Remediation Scripts directly to Intune",
                        size=16,
                        color="GREY_400"
                    ),
                    ft.Divider(height=20),
                    self._build_tabs()
                ], expand=True, spacing=10),
                padding=20,
                expand=True
            )
        ]

    def _build_tabs(self):
        # Container to hold current tab content
        self.tab_body = ft.Container(content=self._build_platform_script_tab(), expand=True)

        def on_change(e):
            idx = int(e.control.selected_index)
            if idx == 0:
                self.tab_body.content = self._build_platform_script_tab()
            elif idx == 1:
                self.tab_body.content = self._build_remediation_tab()
            else:
                self.tab_body.content = self._build_github_tab()
            self.tab_body.update()

        t = create_tabs(
            selected_index=0,
            animation_duration=300,
            expand=True,
            on_change=on_change,
            tabs=[
                ft.Tab(
                    label=i18n.get("tab_platform_scripts") or "Platform Scripts",
                    icon=ft.Icons.TERMINAL
                ),
                ft.Tab(
                    label=i18n.get("tab_remediations") or "Remediations",
                    icon=ft.Icons.HEALING
                ),
                ft.Tab(
                    label=i18n.get("tab_github_import") or "GitHub Import",
                    icon=ft.Icons.CODE
                )
            ]
        )

        return ft.Column([t, self.tab_body], expand=True)

    # --- Platform Script Tab ---
    def _build_platform_script_tab(self):
        self.ps_name = ft.TextField(
            label=i18n.get("script_name") or "Script Name",
            border_radius=8
        )
        self.ps_desc = ft.TextField(
            label=i18n.get("script_description") or "Description",
            multiline=True,
            min_lines=2,
            border_radius=8
        )
        self.ps_file_btn = ft.FilledButton(
            content=ft.Row([ft.Icon(ft.Icons.FILE_OPEN), ft.Text(i18n.get("select_script_file") or "Select Script (.ps1)...")], alignment=ft.MainAxisAlignment.CENTER),
            on_click=lambda _: self.ps_picker.pick_files(allowed_extensions=["ps1"])
        )
        self.ps_file_label = ft.Text(
            i18n.get("no_file_selected") or "No file selected",
            italic=True,
            color="GREY_500"
        )
        self.ps_context = ft.Dropdown(
            label=i18n.get("run_context") or "Run Context",
            options=[
                ft.dropdown.Option("system", text=i18n.get("context_system") or "System"),
                ft.dropdown.Option("user", text=i18n.get("context_user") or "User")
            ],
            value="system",
            width=200
        )
        self.ps_btn_upload = ft.FilledButton(
            content=ft.Row([ft.Icon(ft.Icons.CLOUD_UPLOAD), ft.Text(i18n.get("upload_script") or "Upload Script")], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="BLUE_700",
            color="WHITE",
            on_click=self._upload_ps_script
        )
        self.ps_status = ft.Text("")

        return ft.Container(
            content=ft.Column([
                ft.Text(
                    i18n.get("upload_platform_script") or "Upload Standard PowerShell Script",
                    size=20,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Container(height=10),
                self.ps_name,
                self.ps_desc,
                ft.Row([self.ps_file_btn, self.ps_file_label], spacing=15),
                self.ps_context,
                ft.Container(height=20),
                ft.Row([self.ps_btn_upload, self.ps_status], spacing=15)
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            padding=20
        )

    def _on_ps_picked(self, e):
        if e.files and e.files[0]:
            file_obj = e.files[0]
            # Web check: file_obj.path might be None
            if file_obj.path:
                self.script_path = file_obj.path
            else:
                self.script_path = None # Handle Web Upload later if needed

            self.ps_file_label.value = file_obj.name
            if not self.ps_name.value:
                self.ps_name.value = Path(file_obj.name).stem
            self.update()

    def _upload_ps_script(self, e):
        if not self.script_path:
             self._show_snack("Script file not selected (or upload required on Web)", "RED")
             return

        if not self.ps_name.value:
            self._show_snack(
                i18n.get("script_name_required") or "Name and Script File are required",
                "RED"
            )
            return

        # Check Credentials
        tenant = SwitchCraftConfig.get_value("IntuneTenantID")
        client = SwitchCraftConfig.get_value("IntuneClientID")
        secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret")

        if not all([tenant, client, secret]):
            self._show_snack(
                i18n.get("intune_creds_missing") or "Intune Credentials missing in Settings",
                "RED"
            )
            return

        self.ps_status.value = i18n.get("uploading") or "Uploading..."
        self.ps_status.color = "BLUE"
        self.ps_btn_upload.disabled = True
        self.update()

        def _bg():
            try:
                token = self.intune_service.authenticate(tenant, client, secret)

                content = ""
                # Handle Web vs Local read
                # If script_path is None or we are Web, we might need to handle content differently
                # But FilePicker usually gives path on Desktop.
                # If Web, we need to upload first?
                # Assuming Desktop/Docker-Local for now.
                # If failing on web due to missing path, we need Full Upload implementation.

                with open(self.script_path, "r", encoding="utf-8") as f:
                    content = f.read()

                self.intune_service.upload_powershell_script(
                    token, self.ps_name.value, self.ps_desc.value, content, self.ps_context.value
                )

                self.ps_status.value = i18n.get("script_upload_success") or "Success! Script Created."
                self.ps_status.color = "GREEN"
            except Exception as ex:
                self.ps_status.value = f"{i18n.get('error') or 'Error'}: {ex}"
                self.ps_status.color = "RED"
            finally:
                self.ps_btn_upload.disabled = False
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    # --- Remediation Tab ---
    def _build_remediation_tab(self):
        self.rem_name = ft.TextField(
            label=i18n.get("remediation_name") or "Remediation Name",
            border_radius=8
        )
        self.rem_desc = ft.TextField(
            label=i18n.get("remediation_description") or "Description",
            multiline=True,
            min_lines=2,
            border_radius=8
        )

        self.det_file_btn = ft.FilledButton(
            content=ft.Row([ft.Icon(ft.Icons.SEARCH), ft.Text(i18n.get("select_detection_script") or "Select Detection (.ps1)...")], alignment=ft.MainAxisAlignment.CENTER),
            on_click=lambda _: self.det_picker.pick_files(allowed_extensions=["ps1"])
        )
        self.det_file_label = ft.Text(
            i18n.get("no_detection_script") or "No detection script",
            italic=True,
            color="GREY_500"
        )

        self.rem_file_btn = ft.FilledButton(
            content=ft.Row([ft.Icon(ft.Icons.HEALING), ft.Text(i18n.get("select_remediation_script") or "Select Remediation (.ps1)...")], alignment=ft.MainAxisAlignment.CENTER),
            on_click=lambda _: self.rem_picker.pick_files(allowed_extensions=["ps1"])
        )
        self.rem_file_label = ft.Text(
            i18n.get("no_remediation_script") or "No remediation script",
            italic=True,
            color="GREY_500"
        )

        self.rem_context = ft.Dropdown(
            label=i18n.get("run_context") or "Run Context",
            options=[
                ft.dropdown.Option("system", text=i18n.get("context_system") or "System"),
                ft.dropdown.Option("user", text=i18n.get("context_user") or "User")
            ],
            value="system",
            width=200
        )
        self.rem_btn_upload = ft.FilledButton(
            content=ft.Row([ft.Icon(ft.Icons.CLOUD_UPLOAD), ft.Text(i18n.get("upload_remediation") or "Upload Remediation")], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="BLUE_700",
            color="WHITE",
            on_click=self._upload_rem_script
        )
        self.rem_status = ft.Text("")

        return ft.Container(
            content=ft.Column([
                ft.Text(
                    i18n.get("upload_proactive_remediation") or "Upload Proactive Remediation",
                    size=20,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Container(height=10),
                self.rem_name,
                self.rem_desc,
                ft.Row([self.det_file_btn, self.det_file_label], spacing=15),
                ft.Row([self.rem_file_btn, self.rem_file_label], spacing=15),
                self.rem_context,
                ft.Container(height=20),
                ft.Row([self.rem_btn_upload, self.rem_status], spacing=15)
            ], spacing=15, scroll=ft.ScrollMode.AUTO),
            padding=20
        )

    def _on_det_picked(self, e):
        if e.files and e.files[0]:
            file_obj = e.files[0]
            if not file_obj.path:
                 # Web case or error
                 self.det_file_label.value = "Path unavailable (Web Upload?)"
                 self.update()
                 return

            self.detect_path = file_obj.path
            self.det_file_label.value = file_obj.name
            if not self.rem_name.value:
                self.rem_name.value = Path(file_obj.name).stem
            self.update()

    def _on_rem_picked(self, e):
        if e.files and e.files[0]:
            file_obj = e.files[0]
            if not file_obj.path:
                 self.rem_file_label.value = "Path unavailable (Web Upload?)"
                 self.update()
                 return

            self.remediate_path = file_obj.path
            self.rem_file_label.value = file_obj.name
            self.update()

    def _upload_rem_script(self, e):
        if not self.rem_name.value or not self.detect_path or not self.remediate_path:
            self._show_snack(
                i18n.get("remediation_files_required") or
                "Name, Detection and Remediation scripts are required",
                "RED"
            )
            return

        # Check Credentials
        tenant = SwitchCraftConfig.get_value("IntuneTenantID")
        client = SwitchCraftConfig.get_value("IntuneClientID")
        secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret")

        if not all([tenant, client, secret]):
            self._show_snack(
                i18n.get("intune_creds_missing") or "Intune Credentials missing in Settings",
                "RED"
            )
            return

        self.rem_status.value = i18n.get("uploading") or "Uploading..."
        self.rem_status.color = "BLUE"
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
                    token, self.rem_name.value, self.rem_desc.value,
                    det_content, rem_content, self.rem_context.value
                )

                self.rem_status.value = i18n.get("remediation_upload_success") or "Success! Remediation Created."
                self.rem_status.color = "GREEN"
            except Exception as ex:
                self.rem_status.value = f"{i18n.get('error') or 'Error'}: {ex}"
                self.rem_status.color = "RED"
            finally:
                self.rem_btn_upload.disabled = False
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    # --- GitHub Import Tab ---
    def _build_github_tab(self):
        self.github_repo = ft.TextField(
            label=i18n.get("github_repo_url") or "GitHub Repository URL",
            hint_text="https://github.com/user/repo",
            border_radius=8,
            expand=True
        )
        self.github_pat = ft.TextField(
            label=i18n.get("github_pat") or "Personal Access Token (for private repos)",
            hint_text=i18n.get("github_pat_hint") or "Leave empty for public repos",
            password=True,
            can_reveal_password=True,
            border_radius=8,
            expand=True
        )
        self.github_branch = ft.TextField(
            label=i18n.get("github_branch") or "Branch",
            value="main",
            width=150,
            border_radius=8
        )
        self.github_path = ft.TextField(
            label=i18n.get("github_script_path") or "Script Path in Repo",
            hint_text=i18n.get("github_path_hint") or "e.g. scripts/detection.ps1",
            border_radius=8,
            expand=True
        )

        self.github_status = ft.Text("")
        self.github_script_list = ft.ListView(expand=True, spacing=5, padding=10)

        return ft.Container(
            content=ft.Column([
                ft.Text(
                    i18n.get("import_from_github") or "Import Scripts from GitHub",
                    size=20,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Container(height=5),
                ft.Text(
                    i18n.get("github_import_desc") or
                    "Import PowerShell scripts directly from a GitHub repository and deploy them to Intune.",
                    size=14,
                    color="GREY_400"
                ),
                ft.Container(height=15),
                ft.Row([self.github_repo, self.github_branch], spacing=10),
                self.github_pat,
                ft.Row([
                    self.github_path,
                    ft.FilledButton(
                        content=ft.Row([ft.Icon(ft.Icons.FOLDER_OPEN), ft.Text(i18n.get("browse_repo") or "Browse Repo")], alignment=ft.MainAxisAlignment.CENTER),
                        on_click=self._browse_github_repo
                    )
                ], spacing=10),
                ft.Container(height=10),
                ft.Container(
                    content=self.github_script_list,
                    expand=True,
                    bgcolor="BLACK12",
                    border_radius=10,
                    border=ft.Border.all(1, "WHITE10")
                ),
                ft.Container(height=10),
                ft.Row([
                    ft.FilledButton(
                        content=ft.Row([ft.Icon(ft.Icons.DOWNLOAD), ft.Text(i18n.get("import_selected") or "Import Selected")], alignment=ft.MainAxisAlignment.CENTER),
                        on_click=self._import_github_scripts
                    ),
                    ft.FilledButton(
                        content=ft.Row([ft.Icon(ft.Icons.CLOUD_UPLOAD), ft.Text(i18n.get("deploy_to_intune") or "Deploy to Intune")], alignment=ft.MainAxisAlignment.CENTER),
                        bgcolor="BLUE_700",
                        color="WHITE",
                        on_click=self._deploy_github_scripts
                    ),
                    self.github_status
                ], spacing=10)
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            padding=20,
            expand=True
        )

    def _browse_github_repo(self, e):
        repo_url = self.github_repo.value
        if not repo_url:
            self._show_snack(
                i18n.get("enter_repo_url") or "Please enter a repository URL",
                "ORANGE"
            )
            return

        self.github_status.value = i18n.get("fetching_scripts") or "Fetching scripts..."
        self.github_status.color = "BLUE"
        self.update()

        def _bg():
            try:
                # Parse GitHub URL
                from urllib.parse import urlparse
                clean_url = repo_url.strip()
                if clean_url.endswith(".git"):
                    clean_url = clean_url[:-4]

                # Handle git@github.com:owner/repo
                if clean_url.startswith("git@"):
                    clean_url = clean_url.replace(":", "/").replace("git@", "https://")

                if not clean_url.startswith("http"):
                    clean_url = "https://" + clean_url

                parsed = urlparse(clean_url)
                path_parts = [p for p in parsed.path.split('/') if p]

                if len(path_parts) < 2:
                     raise ValueError(i18n.get("invalid_github_url") or "Invalid GitHub URL")

                owner = path_parts[0]
                repo = path_parts[1]
                branch = self.github_branch.value or "main"

                self.current_owner = owner
                self.current_repo = repo

                # Use GitHub API to list files
                api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
                headers = {}
                if self.github_pat.value:
                    headers["Authorization"] = f"token {self.github_pat.value}"

                response = requests.get(api_url, headers=headers, timeout=15)

                if response.status_code == 401:
                    raise PermissionError(
                        i18n.get("github_auth_failed") or
                        "Authentication failed. Check your PAT for private repos."
                    )
                elif response.status_code == 403:
                    # Check for rate limit
                    reset_time = response.headers.get("X-RateLimit-Reset")
                    msg = "GitHub API Rate Limit Exceeded."
                    if reset_time:
                        import datetime
                        try:
                            reset_dt = datetime.datetime.fromtimestamp(int(reset_time))
                            msg += f" Resets at {reset_dt.strftime('%H:%M:%S')}."
                        except (ValueError, TypeError, OSError):
                            pass
                    raise PermissionError(msg)
                elif response.status_code == 404:
                    raise ValueError(
                        i18n.get("github_repo_not_found") or
                        "Repository not found. Check URL and branch."
                    )

                response.raise_for_status()
                data = response.json()

                # Filter for .ps1 files
                ps_files = [
                    item["path"] for item in data.get("tree", [])
                    if item["path"].endswith(".ps1") and item["type"] == "blob"
                ]

                self.github_script_list.controls.clear()
                if not ps_files:
                    self.github_script_list.controls.append(
                        ft.Text(
                            i18n.get("no_scripts_found") or "No .ps1 scripts found in repository",
                            italic=True,
                            color="GREY_500"
                        )
                    )
                else:
                    self.repo_script_items = []
                    limit = 50
                    for script_path in ps_files[:limit]:
                        cb = ft.Checkbox(value=False)
                        self.repo_script_items.append({"path": script_path, "checkbox": cb})

                        self.github_script_list.controls.append(
                            ft.ListTile(
                                leading=cb,
                                title=ft.Text(script_path),
                                trailing=ft.Icon(ft.Icons.DESCRIPTION, color="BLUE_400")
                            )
                        )

                    if len(ps_files) > limit:
                        self.github_script_list.controls.append(
                            ft.Container(
                                content=ft.Text(
                                    f"... and {len(ps_files) - limit} more scripts. (Showing first {limit})",
                                    italic=True,
                                    size=12,
                                    color="GREY_400"
                                ),
                                padding=ft.padding.only(left=20, top=5)
                            )
                        )

                self.github_status.value = f"{len(ps_files)} {i18n.get('scripts_found') or 'scripts found'}"
                self.github_status.color = "GREEN"

            except Exception as ex:
                self.github_status.value = f"{i18n.get('error') or 'Error'}: {ex}"
                self.github_status.color = "RED"
                logger.error(f"GitHub browse failed: {ex}")
            finally:
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _fetch_github_content(self, path, branch):
        if not self.current_owner or not self.current_repo:
            raise ValueError("Repository info missing")

        url = f"https://api.github.com/repos/{self.current_owner}/{self.current_repo}/contents/{path}?ref={branch}"
        headers = {"Accept": "application/vnd.github.v3.raw"}
        if self.github_pat.value:
            headers["Authorization"] = f"token {self.github_pat.value}"

        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.text

    def _on_import_folder_picked(self, e):
        if e.path:
            self._start_download_import(e.path)

    def _import_github_scripts(self, e):
        selected = [item["path"] for item in self.repo_script_items if item["checkbox"].value]
        if not selected:
            self._show_snack(i18n.get("no_scripts_selected") or "No scripts selected", "ORANGE")
            return

        self.folder_picker.get_directory_path(dialog_title="Select Destination Folder")

    def _start_download_import(self, dest_path):
        selected = [item["path"] for item in self.repo_script_items if item["checkbox"].value]
        self.github_status.value = f"Downloading {len(selected)} scripts..."
        self.github_status.color = "BLUE"
        self.update()

        def _bg():
            count = 0
            errors = []
            try:
                dest = Path(dest_path)
                branch = self.github_branch.value or "main"
                for script_path in selected:
                    try:
                        content = self._fetch_github_content(script_path, branch)
                        # Save to file, preserving structure? No, flatten or prompt?
                        # Flattening is safer for now, using filename
                        filename = Path(script_path).name
                        with open(dest / filename, "w", encoding="utf-8") as f:
                            f.write(content)
                        count += 1
                    except Exception as sub_ex:
                        errors.append(f"{script_path}: {sub_ex}")

                if errors:
                    self.github_status.value = f"Downloaded {count}. Errors: {len(errors)}"
                    self.github_status.color = "ORANGE"
                    logger.error(f"Import errors: {errors}")
                else:
                    self.github_status.value = f"Successfully imported {count} scripts!"
                    self.github_status.color = "GREEN"
            except Exception as ex:
                self.github_status.value = f"Import failed: {ex}"
                self.github_status.color = "RED"
            finally:
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _deploy_github_scripts(self, e):
        selected = [item["path"] for item in self.repo_script_items if item["checkbox"].value]
        if not selected:
            self._show_snack(i18n.get("no_scripts_selected") or "No scripts selected", "ORANGE")
            return

        # Check Credentials
        tenant = SwitchCraftConfig.get_value("IntuneTenantID")
        client = SwitchCraftConfig.get_value("IntuneClientID")
        secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret")

        if not all([tenant, client, secret]):
            self._show_snack(i18n.get("intune_creds_missing") or "Intune Credentials missing in Settings", "RED")
            return

        self.github_status.value = f"Deploying {len(selected)} scripts..."
        self.github_status.color = "BLUE"
        self.update()

        def _bg():
            count = 0
            errors = []
            try:
                token = self.intune_service.authenticate(tenant, client, secret)
                branch = self.github_branch.value or "main"

                for script_path in selected:
                    try:
                        content = self._fetch_github_content(script_path, branch)
                        name = Path(script_path).stem
                        desc = f"Imported from {self.current_owner}/{self.current_repo} ({script_path})"

                        self.intune_service.upload_powershell_script(
                            token, name, desc, content, run_as_account="system"
                        )
                        count += 1
                    except Exception as sub_ex:
                        errors.append(f"{script_path}: {sub_ex}")

                if errors:
                    self.github_status.value = f"Deployed {count}. Errors: {len(errors)}"
                    self.github_status.color = "ORANGE"
                    logger.error(f"Deploy errors: {errors}")
                else:
                    self.github_status.value = f"Successfully deployed {count} scripts to Intune!"
                    self.github_status.color = "GREEN"

            except Exception as ex:
                self.github_status.value = f"Deployment failed: {ex}"
                self.github_status.color = "RED"
            finally:
                self.update()

        threading.Thread(target=_bg, daemon=True).start()
