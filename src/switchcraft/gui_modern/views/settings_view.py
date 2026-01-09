import flet as ft
import threading
import logging
import json
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n
from switchcraft import __version__
from switchcraft.utils.updater import UpdateChecker
from switchcraft.services.auth_service import AuthService
from switchcraft.services.sync_service import SyncService

logger = logging.getLogger(__name__)

class ModernSettingsView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.updater = None

        # Custom Tab Navigation
        self.current_content = ft.Container(expand=True, padding=10)

        # Tab Definitions: Name, Icon, Builder
        self.tab_defs = [
            (i18n.get("settings_general") or "General", ft.Icons.SETTINGS, self._build_general_tab),
            (i18n.get("settings_hdr_update") or "Updates", ft.Icons.UPDATE, self._build_updates_tab),
            (i18n.get("deployment_title") or "Deployment", ft.Icons.CLOUD_UPLOAD, self._build_deployment_tab),
            (i18n.get("help_title") or "Help", ft.Icons.HELP, self._build_help_tab)
        ]

        self.nav_row = ft.Row(scroll=ft.ScrollMode.AUTO, height=50)
        for name, icon, func in self.tab_defs:
            btn = ft.ElevatedButton(
                content=ft.Row([ft.Icon(icon), ft.Text(name)]),
                on_click=lambda e, f=func: self._switch_tab(f),
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=5))
            )
            self.nav_row.controls.append(btn)

        self.controls = [
            ft.Container(content=self.nav_row, height=60, padding=5, bgcolor=ft.Colors.GREY_800),
            ft.Divider(height=1, thickness=1),
            self.current_content
        ]

        # Load initial content without triggering update() since we are in init
        self.current_content.content = self._build_general_tab()

    def _switch_tab(self, builder_func):
        if builder_func:
            self.current_content.content = builder_func()
        try:
            self.update()
        except Exception:
            pass


    def did_mount(self):
        # Trigger async checks after mount
        if hasattr(self, "_check_updates"):
             self._check_updates(None, only_changelog=True)

    def _build_general_tab(self):
        # Company Name
        company_field = ft.TextField(
            label=i18n.get("settings_company_name") or "Company Name",
            value=SwitchCraftConfig.get_company_name(),
        )
        company_field.on_blur = lambda e: SwitchCraftConfig.set_user_preference("CompanyName", e.control.value)

        # Language
        lang_dd = ft.Dropdown(
            label=i18n.get("settings_language") or "Language",
            value=SwitchCraftConfig.get_value("Language", "en"),
            options=[
                ft.dropdown.Option("en", "English"),
                ft.dropdown.Option("de", "Deutsch"),
            ],
        )
        lang_dd.on_change = lambda e: self._on_lang_change(e.control.value)

        # Theme
        theme_dd = ft.Dropdown(
            label=i18n.get("settings_theme") or "Theme",
            value=SwitchCraftConfig.get_value("Theme", "System"),
            options=[
                ft.dropdown.Option("System", "System Default"),
                ft.dropdown.Option("Dark", "Dark Mode"),
                ft.dropdown.Option("Light", "Light Mode"),
            ],
        )
        theme_dd.on_change = lambda e: self._on_theme_change(e.control.value)

        # Winget Toggle
        winget_sw = ft.Switch(
            label=i18n.get("settings_enable_winget") or "Enable Winget Integration",
            value=SwitchCraftConfig.get_value("EnableWinget", True),
        )
        winget_sw.on_change = lambda e: SwitchCraftConfig.set_user_preference("EnableWinget", e.control.value)

        # Cloud Sync Section
        cloud_sync = self._build_cloud_sync_section()

        # AI Config Section
        ai_config = self._build_ai_config_section()

        # Export/Import buttons
        btn_export = ft.ElevatedButton(i18n.get("btn_export_settings") or "Export Settings", icon=ft.Icons.UPLOAD_FILE, on_click=self._export_settings)
        btn_import = ft.ElevatedButton(i18n.get("btn_import_settings") or "Import Settings", icon=ft.Icons.FILE_DOWNLOAD, on_click=self._import_settings)

        export_row = ft.Row([btn_export, btn_import])

        return ft.ListView(
            controls=[
                ft.Text("General Settings", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                company_field,
                ft.Row([lang_dd, theme_dd]),
                winget_sw,
                ft.Divider(),
                cloud_sync,
                ft.Divider(),
                ai_config,
                ft.Divider(),
                export_row
            ],
            padding=20,
            spacing=15,
        )

    def _build_cloud_sync_section(self):
        self.sync_status_text = ft.Text("Checking status...", color=ft.Colors.GREY)
        self.sync_actions = ft.Row(visible=False)
        self.login_btn = ft.ElevatedButton("Login with GitHub", icon=ft.Icons.LOGIN, on_click=self._start_github_login)
        self.logout_btn = ft.ElevatedButton("Logout", icon=ft.Icons.LOGOUT, on_click=self._logout_github, color=ft.Colors.RED)

        self._update_sync_ui(update=False)

        return ft.Column([
            ft.Text(i18n.get("cloudsync_title") or "Cloud Sync", size=18, weight=ft.FontWeight.BOLD),
            self.sync_status_text,
            self.login_btn,
            self.sync_actions,
        ])

    def _update_sync_ui(self, update=True):
        if AuthService.is_authenticated():
            user = AuthService.get_user_info()
            name = user.get("login", "Unknown") if user else "Unknown"
            self.sync_status_text.value = f"Logged in as: {name}"
            self.sync_status_text.color = ft.Colors.GREEN
            self.login_btn.visible = False
            self.sync_actions.visible = True

            btn_up = ft.ElevatedButton("Sync Up", icon=ft.Icons.CLOUD_UPLOAD, on_click=self._sync_up)
            btn_down = ft.ElevatedButton("Sync Down", icon=ft.Icons.CLOUD_DOWNLOAD, on_click=self._sync_down)

            self.sync_actions.controls = [btn_up, btn_down, self.logout_btn]
        else:
            self.sync_status_text.value = "Not logged in."
            self.sync_status_text.color = ft.Colors.GREY
            self.login_btn.visible = True
            self.sync_actions.visible = False
        if update and self.page:
            self.update()

    def _build_ai_config_section(self):
        provider = ft.Dropdown(
            label="AI Provider",
            value=SwitchCraftConfig.get_value("AIProvider", "local"),
            options=[
                ft.dropdown.Option("local"),
                ft.dropdown.Option("openai"),
                ft.dropdown.Option("gemini"),
            ],
        )
        provider.on_change = lambda e: SwitchCraftConfig.set_user_preference("AIProvider", e.control.value)

        api_key = ft.TextField(
            label="API Key (if required)",
            value=SwitchCraftConfig.get_secure_value("AIKey") or "",
            password=True,
            can_reveal_password=True,
        )
        api_key.on_blur = lambda e: SwitchCraftConfig.set_secure_value("AIKey", e.control.value)

        troubleshooting_section = ft.Column([
            ft.Text("Troubleshooting", size=20, weight=ft.FontWeight.BOLD),
            ft.Text("Settings are shared across all SwitchCraft editions (Modern, Legacy, and CLI).", size=12, italic=True),
        ])

        return ft.Column([
            ft.Text("AI Configuration", size=18, weight=ft.FontWeight.BOLD),
            provider,
            api_key
        ])

    def _build_updates_tab(self):
        channel = ft.Dropdown(
            label="Update Channel",
            value=SwitchCraftConfig.get_value("UpdateChannel", "stable"),
            options=[
                ft.dropdown.Option("stable"),
                ft.dropdown.Option("beta"),
                ft.dropdown.Option("dev"),
            ],
        )
        channel.on_change = lambda e: SwitchCraftConfig.set_user_preference("UpdateChannel", e.control.value)

        self.changelog_text = ft.Markdown("Loading changelog...")

        check_btn = ft.ElevatedButton("Check for Updates", icon=ft.Icons.REFRESH, on_click=self._check_updates)

        return ft.ListView(
            controls=[
                ft.Text("Updates", size=24, weight=ft.FontWeight.BOLD),
                channel,
                check_btn,
                ft.Divider(),
                ft.Text("Changelog", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=self.changelog_text,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    padding=10,
                    border_radius=5
                )
            ],
            padding=20,
            spacing=15
        )

    def _build_deployment_tab(self):
        sign_sw = ft.Switch(
            label="Enable Code Signing",
            value=SwitchCraftConfig.get_value("SignScripts", False),
        )
        sign_sw.on_change = lambda e: SwitchCraftConfig.set_user_preference("SignScripts", e.control.value)

        git_path = ft.TextField(
            label="Git Repository Path",
            value=SwitchCraftConfig.get_value("GitRepoPath", ""),
            suffix=ft.IconButton(ft.Icons.FOLDER_OPEN),
        )
        git_path.on_blur = lambda e: SwitchCraftConfig.set_user_preference("GitRepoPath", e.control.value)

        template_path = ft.TextField(
            label="Custom Template Path",
            value=SwitchCraftConfig.get_value("CustomTemplatePath", ""),
            suffix=ft.IconButton(ft.Icons.FOLDER_OPEN),
        )
        template_path.on_blur = lambda e: SwitchCraftConfig.set_user_preference("CustomTemplatePath", e.control.value)

        tenant = ft.TextField(label="Intune Tenant ID", value=SwitchCraftConfig.get_value("IntuneTenantID", ""))
        tenant.on_blur=lambda e: SwitchCraftConfig.set_user_preference("IntuneTenantID", e.control.value)

        client = ft.TextField(label="Intune Client ID", value=SwitchCraftConfig.get_value("IntuneClientId", ""))
        client.on_blur=lambda e: SwitchCraftConfig.set_user_preference("IntuneClientId", e.control.value)

        secret = ft.TextField(label="Intune Client Secret", value=SwitchCraftConfig.get_secure_value("IntuneClientSecret") or "", password=True, can_reveal_password=True)
        secret.on_blur=lambda e: SwitchCraftConfig.set_secure_value("IntuneClientSecret", e.control.value)

        return ft.ListView(
            controls=[
                ft.Text("Deployment Settings", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Code Signing", size=18, color=ft.Colors.BLUE),
                sign_sw,
                ft.Divider(),
                ft.Text("Paths", size=18, color=ft.Colors.BLUE),
                git_path,
                template_path,
                ft.Divider(),
                ft.Text("Microsoft Intune API", size=18, color=ft.Colors.BLUE),
                tenant,
                client,
                secret
            ],
            padding=20,
            spacing=15
        )

    def _build_help_tab(self):
        links = ft.Row([
            ft.ElevatedButton("GitHub Repo", icon=ft.Icons.CODE, url="https://github.com/FaserF/SwitchCraft"),
            ft.ElevatedButton("Report Issue", icon=ft.Icons.BUG_REPORT, url="https://github.com/FaserF/SwitchCraft/issues"),
            ft.ElevatedButton("Documentation", icon=ft.Icons.BOOK, url="https://github.com/FaserF/SwitchCraft/blob/main/README.md"),
        ])

        logs_btn = ft.ElevatedButton("Export Logs", icon=ft.Icons.DOWNLOAD, on_click=self._export_logs)

        danger_zone = ft.Container(
            content=ft.Column([
                ft.Text("Danger Zone", color=ft.Colors.RED, weight=ft.FontWeight.BOLD),
                ft.Text("Irreversible actions. Proceed with caution.", color=ft.Colors.GREY, size=12),
                ft.ElevatedButton(
                    "Factory Reset (Delete All Data)",
                    icon=ft.Icons.DELETE_FOREVER,
                    bgcolor=ft.Colors.RED_900 if hasattr(ft.Colors, "RED_900") else ft.Colors.RED,
                    color=ft.Colors.WHITE,
                    on_click=self._on_factory_reset_click
                )
            ]),
            padding=10,
            border=ft.border.all(1, ft.Colors.RED),
            border_radius=5,
            margin=ft.margin.only(top=20)
        )

        return ft.ListView(
            controls=[
                ft.Text("Help & Resources", size=24, weight=ft.FontWeight.BOLD),
                links,
                ft.Divider(),
                ft.Text("Troubleshooting", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("Settings are shared across all SwitchCraft editions (Modern, Legacy, and CLI).", size=12, italic=True),
                logs_btn,
                danger_zone,
                ft.Divider(),
                ft.Text(f"Version: {__version__}", color=ft.Colors.GREY)
            ],
            padding=20,
            spacing=15
        )

    # ... Helper methods same as before ...

    def _on_factory_reset_click(self, e):
        # Implementation needs to respect self.app_page
        def confirm_reset(e):
            self.app_page.dialog.open = False
            try:
                SwitchCraftConfig.delete_all_application_data()
                self.app_page.open(ft.SnackBar(ft.Text("Reset Complete. App will close."), bgcolor=ft.Colors.GREEN))
                import time
                time.sleep(2)
                self.app_page.window.close()
            except Exception as ex:
                self.app_page.open(ft.SnackBar(ft.Text(f"Reset Failed: {ex}"), bgcolor=ft.Colors.RED))
            self.app_page.update()

        def cancel_reset(e):
            self.app_page.dialog.open = False
            self.app_page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Confirm Factory Reset", color=ft.Colors.RED),
            content=ft.Text("Are you SURE? This will delete all settings, secrets, and local data.\nThis action cannot be undone."),
            actions=[
                ft.TextButton("Yes, Delete Everything", on_click=confirm_reset, style=ft.ButtonStyle(color=ft.Colors.RED)),
                ft.TextButton("Cancel", on_click=cancel_reset)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app_page.dialog = dlg
        dlg.open = True
        self.app_page.update()

    def _on_lang_change(self, val):
        SwitchCraftConfig.set_user_preference("Language", val)
        self.app_page.open(ft.SnackBar(ft.Text("Language changed. Please restart app.")))

    def _on_theme_change(self, val):
        SwitchCraftConfig.set_user_preference("Theme", val)
        self.app_page.theme_mode = ft.ThemeMode.DARK if val == "Dark" else ft.ThemeMode.LIGHT if val == "Light" else ft.ThemeMode.SYSTEM
        self.app_page.update()

    def _check_updates(self, e, only_changelog=False):
        def _run():
            try:
                channel = SwitchCraftConfig.get_value("UpdateChannel", "stable")
                checker = UpdateChecker(channel=channel)
                checker.check_for_updates()
                note = checker.release_notes or "No changelog available."
                self.changelog_text.value = f"**Latest Version:** {checker.latest_version}\n\n{note}"
                self.update()

                if not only_changelog and self.app_page:
                     if checker.is_update_available:
                         self.app_page.open(ft.SnackBar(ft.Text(f"Update available: {checker.latest_version}"), action="Download"))
                     else:
                         self.app_page.open(ft.SnackBar(ft.Text("No updates available.")))

            except Exception as ex:
                self.changelog_text.value = f"Error fetching updates: {ex}"
                try: self.update()
                except: pass

        threading.Thread(target=_run, daemon=True).start()

    def _start_github_login(self, e):
       # Reuse logic, update references to self.app_page.dialog not self.page.dialog if self.page isn't set on Column?
       # Column gets .page when mounted. but we are using self.app_page.
        def _flow():
            flow = AuthService.initiate_device_flow()
            if not flow:
                self.app_page.open(ft.SnackBar(ft.Text("Login init failed")))
                return

            def close_dlg(e):
                self.app_page.dialog.open = False
                self.app_page.update()

            def copy_code(e):
                self.app_page.set_clipboard(flow.get("user_code"))
                import webbrowser
                webbrowser.open(flow.get("verification_uri"))

            # Button handlers need to assign on_click here too?
            # ElevButton(on_click=...) seems to work in other views?
            # Wait, ElevButton usually supports on_click in init even in old versions.
            # But Dropdown/FilePicker didn't.
            # I will assume ElevatedButton works safe.
            btn_copy = ft.TextButton("Copy & Open", on_click=copy_code)
            btn_cancel = ft.TextButton("Cancel", on_click=close_dlg)

            dlg = ft.AlertDialog(
                title=ft.Text("GitHub Login"),
                content=ft.Column([
                    ft.Text("Please visit:"),
                    ft.Text(flow.get("verification_uri"), color=ft.Colors.BLUE),
                    ft.Text("And enter code:"),
                    ft.Text(flow.get("user_code"), size=24, weight=ft.FontWeight.BOLD),
                ], height=150),
                actions=[btn_copy, btn_cancel]
            )
            self.app_page.dialog = dlg
            dlg.open = True
            self.app_page.update()

            token = AuthService.poll_for_token(flow.get("device_code"), flow.get("interval"), flow.get("expires_in"))
            dlg.open = False
            if token:
                AuthService.save_token(token)
                self._update_sync_ui()
                self.app_page.open(ft.SnackBar(ft.Text("Login Successful!"), bgcolor=ft.Colors.GREEN))
            else:
                self.app_page.open(ft.SnackBar(ft.Text("Login Failed or Timed out"), bgcolor=ft.Colors.RED))
            self.app_page.update()

        threading.Thread(target=_flow, daemon=True).start()

    def _logout_github(self, e):
        AuthService.logout()
        self._update_sync_ui()

    def _sync_up(self, e):
        def _run():
            if SyncService.sync_up():
                self.app_page.open(ft.SnackBar(ft.Text("Sync Up Successful"), bgcolor=ft.Colors.GREEN))
            else:
                self.app_page.open(ft.SnackBar(ft.Text("Sync Up Failed"), bgcolor=ft.Colors.RED))
        threading.Thread(target=_run, daemon=True).start()

    def _sync_down(self, e):
        def _run():
             if SyncService.sync_down():
                 self.app_page.open(ft.SnackBar(ft.Text("Sync Down Successful. Restart app."), bgcolor=ft.Colors.GREEN))
             else:
                 self.app_page.open(ft.SnackBar(ft.Text("Sync Down Failed"), bgcolor=ft.Colors.RED))
        threading.Thread(target=_run, daemon=True).start()

    def _export_settings(self, e):
        from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
        path = FilePickerHelper.save_file(dialog_title="Export Settings", file_name="settings.json", allowed_extensions=["json"])
        if path:
            prefs = SwitchCraftConfig.export_preferences()
            with open(path, "w") as f:
                json.dump(prefs, f, indent=4)
            self.app_page.open(ft.SnackBar(ft.Text(f"Exported to {path}")))

    def _import_settings(self, e):
        from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
        path = FilePickerHelper.pick_file(allowed_extensions=["json"], allow_multiple=False)
        if path:
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                SwitchCraftConfig.import_preferences(data)
                self.app_page.open(ft.SnackBar(ft.Text("Settings Imported. Please Restart."), bgcolor=ft.Colors.GREEN))
            except Exception as ex:
                self.app_page.open(ft.SnackBar(ft.Text(f"Import Failed: {ex}"), bgcolor=ft.Colors.RED))

    def _export_logs(self, e):
        from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
        path = FilePickerHelper.save_file(dialog_title="Export Logs", file_name="logs.txt", allowed_extensions=["txt"])
        if path:
            from switchcraft.utils.logging_handler import get_session_handler
            if get_session_handler().export_logs(path):
                self.app_page.open(ft.SnackBar(ft.Text("Logs Exported!")))
            else:
                self.app_page.open(ft.SnackBar(ft.Text("Log export failed."), bgcolor=ft.Colors.RED))
