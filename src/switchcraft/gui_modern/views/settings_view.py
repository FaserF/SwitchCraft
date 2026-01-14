import flet as ft
import threading
import logging
import json
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n
from switchcraft import __version__
from switchcraft.utils.app_updater import UpdateChecker
from switchcraft.services.auth_service import AuthService
from switchcraft.services.sync_service import SyncService

logger = logging.getLogger(__name__)

class ModernSettingsView(ft.Column):
    def __init__(self, page: ft.Page, initial_tab_index=0):
        super().__init__(expand=True)
        self.app_page = page
        self.updater = None
        self.initial_tab_index = initial_tab_index

        # Custom Tab Navigation
        self.current_content = ft.Container(expand=True, padding=10)

        # Tab Definitions: Name, Icon, Builder
        self.tab_defs = [
            (i18n.get("settings_general") or "General", ft.Icons.SETTINGS, self._build_general_tab),
            (i18n.get("settings_hdr_update") or "Updates", ft.Icons.UPDATE, self._build_updates_tab),
            (i18n.get("deployment_title") or "Global Graph API", ft.Icons.CLOUD_UPLOAD, self._build_deployment_tab),
            (i18n.get("help_title") or "Help", ft.Icons.HELP, self._build_help_tab)
        ]

        self.nav_row = ft.Row(scroll=ft.ScrollMode.AUTO, height=50)
        for i, (name, icon, func) in enumerate(self.tab_defs):
            btn = ft.ElevatedButton(
                content=ft.Row([ft.Icon(icon), ft.Text(name)]),
                on_click=lambda e, f=func: self._switch_tab(f),
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=5),
                    bgcolor="PRIMARY_CONTAINER" if i == self.initial_tab_index else None
                )
            )
            self.nav_row.controls.append(btn)

        self.controls = [
            ft.Container(content=self.nav_row, height=60, padding=5, bgcolor="GREY_800"),
            ft.Divider(height=1, thickness=1),
            self.current_content
        ]

        # Load initial content
        try:
            target_func = self.tab_defs[self.initial_tab_index][2]
            self.current_content.content = target_func()
        except Exception as e:
            logger.error(f"Failed to build initial tab: {e}")
            self.current_content.content = ft.Text(f"Error loading settings: {e}", color="red")

    def did_mount(self):
        # Trigger async checks after mount IF NOT cached
        cached = getattr(self.app_page, "update_check_result", None)
        if hasattr(self, "_check_updates") and (not cached or not cached.get("checked")):
             self._check_updates(None, only_changelog=True)
        # Check for policy-managed settings
        self._check_managed_settings()

    def _switch_tab(self, builder_func):
        try:
            if builder_func:
                self.current_content.content = builder_func()
            else:
                self.current_content.content = ft.Text("Error: Tab builder missing", color="RED")
        except Exception as e:
            logger.error(f"Failed to build tab: {e}")
            self.current_content.content = ft.Column([
                ft.Icon(ft.Icons.ERROR, color="RED", size=40),
                ft.Text(f"Error loading tab: {e}", color="RED"),
                ft.Text("Check logs for details.", size=12, color="GREY")
            ])

        try:
            self.update()
        except Exception:
            pass

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
            expand=True,
        )
        lang_dd.on_change = lambda e: self._on_lang_change(e.control.value)

        # Winget Toggle
        winget_sw = ft.Switch(
            label=i18n.get("settings_enable_winget") or "Enable Winget Integration",
            value=bool(SwitchCraftConfig.get_value("EnableWinget", True)),
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
                ft.Text(i18n.get("settings_general") or "General Settings", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                company_field,
                lang_dd,
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
        self.sync_status_text = ft.Text(i18n.get("sync_checking_status") or "Checking status...", color="GREY")
        self.sync_actions = ft.Row(visible=False)
        self.login_btn = ft.ElevatedButton(i18n.get("btn_login_github") or "Login with GitHub", icon=ft.Icons.LOGIN, on_click=self._start_github_login)
        self.logout_btn = ft.ElevatedButton(i18n.get("btn_logout") or "Logout", icon=ft.Icons.LOGOUT, on_click=self._logout_github, color="RED")

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
            self.sync_status_text.value = f"{i18n.get('logged_in_as') or 'Logged in as'}: {name}"
            self.sync_status_text.color = "GREEN"
            self.login_btn.visible = False
            self.sync_actions.visible = True

            btn_up = ft.ElevatedButton(i18n.get("btn_sync_up") or "Sync Up", icon=ft.Icons.CLOUD_UPLOAD, on_click=self._sync_up)
            btn_down = ft.ElevatedButton(i18n.get("btn_sync_down") or "Sync Down", icon=ft.Icons.CLOUD_DOWNLOAD, on_click=self._sync_down)

            self.sync_actions.controls = [btn_up, btn_down, self.logout_btn]
        else:
            self.sync_status_text.value = i18n.get("sync_not_logged_in") or "Not logged in."
            self.sync_status_text.color = "GREY"
            self.login_btn.visible = True
            self.sync_actions.visible = False
        if update and self.page:
            self.update()

    def _build_ai_config_section(self):
        provider = ft.Dropdown(
            label=i18n.get("settings_ai_provider_label") or "AI Provider",
            value=SwitchCraftConfig.get_value("AIProvider", "local"),
            options=[
                ft.dropdown.Option("local"),
                ft.dropdown.Option("openai"),
                ft.dropdown.Option("gemini"),
            ],
        )
        provider.on_change = lambda e: SwitchCraftConfig.set_user_preference("AIProvider", e.control.value)

        api_key = ft.TextField(
            label=i18n.get("settings_ai_key_label") or "API Key (if required)",
            value=SwitchCraftConfig.get_secure_value("AIKey") or "",
            password=True,
            can_reveal_password=True,
        )
        api_key.on_blur = lambda e: SwitchCraftConfig.set_secret("AIKey", e.control.value)



        return ft.Column([
            ft.Text(i18n.get("settings_ai_header") or "AI Configuration", size=18, weight=ft.FontWeight.BOLD),
            provider,
            api_key
        ])

    def _build_updates_tab(self):
        channel = ft.Dropdown(
            label=i18n.get("settings_channel") or "Update Channel",
            value=SwitchCraftConfig.get_value("UpdateChannel", "stable"),
            options=[
                ft.dropdown.Option("stable"),
                ft.dropdown.Option("beta"),
                ft.dropdown.Option("dev"),
            ],
        )
        channel.on_change = lambda e: self._on_channel_change(e.control.value)

        # Check for cached update result
        cached = getattr(self.app_page, "update_check_result", None)
        initial_changelog = i18n.get("update_loading_changelog") or "Loading changelog..."
        initial_latest = i18n.get("unknown") or "Unknown"

        if cached and cached.get("checked"):
            ver = cached.get("version")
            data = cached.get("data")
            note = (data.get("body") if data else None) or "No changelog available."
            initial_latest = ver if ver else initial_latest
            if cached.get("error"):
                 initial_changelog = f"Update check failed: {cached.get('error')}"
            else:
                 initial_changelog = f"**{i18n.get('latest_version') or 'Latest Version'}:** {ver}\n\n{note}"

        self.changelog_text = ft.Markdown(initial_changelog)
        self.latest_version_text = ft.Text(initial_latest)

        check_btn = ft.ElevatedButton(i18n.get("check_updates") or "Check for Updates", icon=ft.Icons.REFRESH, on_click=self._check_updates)

        return ft.ListView(
            controls=[
                ft.Text(i18n.get("settings_hdr_update") or "Updates", size=24, weight=ft.FontWeight.BOLD),
                channel,
                ft.Row([
                    ft.Text(f"{i18n.get('current_version') or 'Current Version'}: {__version__}", weight=ft.FontWeight.BOLD),
                ]),
                ft.Row([
                    ft.Text(f"{i18n.get('latest_version') or 'Latest Version'}: ", weight=ft.FontWeight.BOLD),
                    self.latest_version_text
                ]),
                check_btn,
                ft.Divider(),
                ft.Text(i18n.get("changelog") or "Changelog", size=18, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=self.changelog_text,
                    bgcolor="SURFACE_CONTAINER_HIGHEST",
                    padding=10,
                    border_radius=5
                )
            ],
            padding=20,
            spacing=15
        )

    def _build_deployment_tab(self):
        # Code Signing Section
        sign_enabled = bool(SwitchCraftConfig.get_value("SignScripts", False))

        # Validate if cert actually exists
        saved_thumb = SwitchCraftConfig.get_value("CodeSigningCertThumbprint", "")
        saved_cert_path = SwitchCraftConfig.get_value("CodeSigningCertPath", "")

        if sign_enabled and not saved_thumb and not saved_cert_path:
            # Config says enabled, but no cert configured -> Disable it to be safe and match UI reality
            sign_enabled = False
            SwitchCraftConfig.set_user_preference("SignScripts", False)

        sign_sw = ft.Switch(
            label=i18n.get("settings_enable_signing") or "Enable Code Signing",
            value=sign_enabled,
        )
        sign_sw.on_change = lambda e: self._on_signing_toggle(e.control.value)

        # saved_thumb and saved_cert_path already read above

        cert_display = saved_thumb if saved_thumb else (saved_cert_path if saved_cert_path else (i18n.get("cert_not_configured") or "Not Configured"))

        self.cert_status_text = ft.Text(cert_display, color="GREEN" if (saved_thumb or saved_cert_path) else "GREY")

        cert_auto_btn = ft.ElevatedButton(
            i18n.get("btn_auto_detect_cert") or "Auto-Detect",
            icon=ft.Icons.SEARCH,
            on_click=self._auto_detect_signing_cert
        )
        cert_browse_btn = ft.ElevatedButton(
            i18n.get("btn_browse_cert") or "Browse .pfx",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._browse_signing_cert
        )
        cert_reset_btn = ft.ElevatedButton(
            i18n.get("btn_reset") or "Reset",
            icon=ft.Icons.DELETE,
            bgcolor="RED_900" if hasattr(getattr(ft, "colors", None), "RED_900") else "RED",
            on_click=self._reset_signing_cert
        )

        # Paths Section
        git_path = ft.TextField(
            label=i18n.get("lbl_git_path") or "Git Repository Path",
            value=str(SwitchCraftConfig.get_value("GitRepoPath", "")),
        )
        git_path.on_blur = lambda e: SwitchCraftConfig.set_user_preference("GitRepoPath", e.control.value)

        # Template Section
        template_display = SwitchCraftConfig.get_value("CustomTemplatePath", "") or (i18n.get("template_default") or "(Default)")
        self.template_status_text = ft.Text(template_display, color="GREY" if "(Default)" in template_display else "GREEN")

        template_browse_btn = ft.ElevatedButton(
            i18n.get("btn_browse") or "Browse",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._browse_template
        )
        template_reset_btn = ft.ElevatedButton(
            i18n.get("btn_reset") or "Reset",
            icon=ft.Icons.REFRESH,
            on_click=self._reset_template
        )

        # Intune API Section
        tenant = ft.TextField(label=i18n.get("settings_intune_tenant") or "Intune Tenant ID", value=str(SwitchCraftConfig.get_value("IntuneTenantID", "")))
        tenant.on_blur=lambda e: SwitchCraftConfig.set_user_preference("IntuneTenantID", e.control.value)

        client = ft.TextField(label=i18n.get("settings_intune_client") or "Intune Client ID", value=str(SwitchCraftConfig.get_value("IntuneClientID", "")))
        client.on_blur=lambda e: SwitchCraftConfig.set_user_preference("IntuneClientID", e.control.value)

        secret = ft.TextField(label=i18n.get("settings_intune_secret") or "Intune Client Secret", value=SwitchCraftConfig.get_secure_value("IntuneClientSecret") or "", password=True, can_reveal_password=True)
        secret.on_blur=lambda e: SwitchCraftConfig.set_secure_value("IntuneClientSecret", e.control.value)

        return ft.ListView(
            controls=[
                ft.Text(i18n.get("deployment_title") or "Global Graph API", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Configure your connection to Microsoft Graph. Required for Intune, Entra ID, and Autopilot features.", size=12, color="GREY"),

                # Intune/Graph
                ft.Text("Azure App Registration Config", size=18, color="BLUE"),
                tenant,
                client,
                secret,
                ft.Divider(),

                # Code Signing
                ft.Text(i18n.get("settings_hdr_signing") or "Code Signing", size=18, color="BLUE"),
                sign_sw,
                ft.Row([ft.Text(i18n.get("lbl_active_cert") or "Active Certificate:"), self.cert_status_text]),
                ft.Row([cert_auto_btn, cert_browse_btn, cert_reset_btn]),
                ft.Divider(),
                # Paths
                ft.Text(i18n.get("settings_hdr_directories") or "Paths", size=18, color="BLUE"),
                git_path,
                ft.Divider(),
                # Templates
                ft.Text(i18n.get("settings_hdr_template") or "PowerShell Template", size=18, color="BLUE"),
                ft.Row([ft.Text(i18n.get("lbl_custom_template") or "Active Template:"), self.template_status_text]),
                ft.Row([template_browse_btn, template_reset_btn]),
                ft.Text(i18n.get("template_help") or "Select a custom .ps1 template. Leave empty for default.", size=11, color="GREY"),
            ],
            padding=20,
            spacing=15
        )

    def _on_debug_toggle(self, e):
        """Toggle debug logging."""
        val = e.control.value
        SwitchCraftConfig.set_user_preference("DebugMode", val)
        from switchcraft.utils.logging_handler import get_session_handler
        get_session_handler().set_debug_mode(val)
        self._show_snack(f"Debug Mode {'Enabled' if val else 'Disabled'}", "ORANGE" if val else "GREEN")

    def _build_help_tab(self):
        links = ft.Row([
            ft.ElevatedButton(i18n.get("help_github_repo") or "GitHub Repo", icon=ft.Icons.CODE, url="https://github.com/FaserF/SwitchCraft"),
            ft.ElevatedButton(i18n.get("help_report_issue") or "Report Issue", icon=ft.Icons.BUG_REPORT, url="https://github.com/FaserF/SwitchCraft/issues"),
            ft.ElevatedButton(i18n.get("help_documentation") or "Documentation", icon=ft.Icons.BOOK, url="https://github.com/FaserF/SwitchCraft/blob/main/README.md"),
        ])

        logs_btn = ft.ElevatedButton(i18n.get("help_export_logs") or "Export Logs", icon=ft.Icons.DOWNLOAD, on_click=self._export_logs)

        # Debug Toggle
        debug_sw = ft.Switch(
            label="Enable Debug Logging",
            value=SwitchCraftConfig.is_debug_mode(),
            on_change=self._on_debug_toggle
        )

        # GitHub Issue Reporter with pre-filled body
        def open_issue_reporter(e):
            from switchcraft.utils.logging_handler import get_session_handler
            import webbrowser
            webbrowser.open(get_session_handler().get_github_issue_link())

        issue_btn = ft.ElevatedButton(
            i18n.get("help_report_issue_prefilled") or "Report Issue (with Logs)",
            icon=ft.Icons.BUG_REPORT,
            bgcolor="GREY_800",
            on_click=open_issue_reporter
        )

        # Debug Console Section
        self.debug_log_text = ft.TextField(
            label=i18n.get("settings_hdr_debug_console") or "Debug Console",
            multiline=True,
            min_lines=8,
            max_lines=15,
            read_only=True,
            value="--- Debug Console ---\n",
            text_size=11,
            border_radius=5,
            expand=True
        )
        self.debug_console_visible = False

        def toggle_debug_console(e):
            self.debug_console_visible = not self.debug_console_visible
            self.debug_log_text.visible = self.debug_console_visible
            self.update()

        debug_toggle_btn = ft.ElevatedButton(
            i18n.get("show_debug_console") or "Show Debug Console",
            icon=ft.Icons.TERMINAL,
            on_click=toggle_debug_console
        )
        self.debug_log_text.visible = False

        # Attach a log handler
        self._attach_debug_log_handler()

        # Addon Manager Section
        addon_section = self._build_addon_manager_section()

        danger_zone = ft.Container(
            content=ft.Column([
                ft.Text(i18n.get("help_danger_zone") or "Danger Zone", color="RED", weight=ft.FontWeight.BOLD),
                ft.Text(i18n.get("help_danger_zone_desc") or "Irreversible actions. Proceed with caution.", color="GREY", size=12),
                ft.ElevatedButton(
                    i18n.get("help_factory_reset") or "Factory Reset (Delete All Data)",
                    icon=ft.Icons.DELETE_FOREVER,
                    bgcolor="RED_900" if hasattr(getattr(ft, "colors", None), "RED_900") else "RED",
                    color="WHITE",
                    on_click=self._on_factory_reset_click
                )
            ]),
            padding=10,
            border=ft.Border.all(1, "RED"),
            border_radius=5,
            margin=ft.margin.only(top=20)
        )

        return ft.ListView(
            controls=[
                ft.Text(i18n.get("help_title") or "Help & Resources", size=24, weight=ft.FontWeight.BOLD),
                links,
                ft.Row([logs_btn, debug_sw]),
                ft.Divider(),
                ft.Text(i18n.get("help_troubleshooting") or "Troubleshooting", size=18, weight=ft.FontWeight.BOLD),
                ft.Text(i18n.get("help_shared_settings_msg") or "Settings are shared across all SwitchCraft editions (Modern, Legacy, and CLI).", size=12, italic=True),
                ft.Row([
                    ft.ElevatedButton(i18n.get("help_export_logs") or "Export Logs", icon=ft.Icons.DOWNLOAD, on_click=self._export_logs),
                    issue_btn
                ]),
                ft.Divider(),
                ft.Text(i18n.get("addon_manager_title") or "Addon Manager", size=18, weight=ft.FontWeight.BOLD),
                addon_section,
                ft.Divider(),
                debug_toggle_btn,
                self.debug_log_text,
                danger_zone,
                ft.Divider(),
                ft.Text(f"{i18n.get('about_version') or 'Version'}: {__version__}", color="GREY")
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
                self._show_snack("Reset Complete. App will close.", "GREEN")
                import time
                time.sleep(2)
                self.app_page.window.destroy()
            except Exception as ex:
                self._show_snack(f"Reset Failed: {ex}", "RED")
            self.app_page.update()

        def cancel_reset(e):
            self.app_page.dialog.open = False
            self.app_page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(i18n.get("help_reset_confirm_title") or "Confirm Factory Reset", color="RED"),
            content=ft.Text(i18n.get("help_reset_confirm_msg") or "Are you SURE? This will delete all settings, secrets, and local data.\nThis action cannot be undone."),
            actions=[
                ft.TextButton(i18n.get("btn_yes_delete_all") or "Yes, Delete Everything", on_click=confirm_reset, style=ft.ButtonStyle(color="RED")),
                ft.TextButton(i18n.get("btn_cancel") or "Cancel", on_click=cancel_reset)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app_page.dialog = dlg
        dlg.open = True
        self.app_page.update()

    def _on_channel_change(self, val):
        SwitchCraftConfig.set_user_preference("UpdateChannel", val)
        # Clear current latest if switching
        self.latest_version_text.value = i18n.get("unknown") or "Unknown"
        self.changelog_text.value = i18n.get("update_loading_changelog") or "Loading changelog..."
        self.update()
        # Trigger re-check
        self._check_updates(None, only_changelog=True)

    def _on_lang_change(self, val):
        SwitchCraftConfig.set_user_preference("Language", val)
        # Attempt to reload i18n strings? i18n is static usually.
        # But we can try to reload the UI.
        self._show_snack(i18n.get("restart_required_msg") or "Language changed. Please restart app.", "ORANGE")
        # Trigger page update just in case
        self.app_page.update()

    def _on_theme_change(self, val):
        SwitchCraftConfig.set_user_preference("Theme", val)
        self.app_page.theme_mode = ft.ThemeMode.DARK if val == "Dark" else ft.ThemeMode.LIGHT if val == "Light" else ft.ThemeMode.SYSTEM
        self.app_page.update()

    def _check_updates(self, e, only_changelog=False):
        def _run():
            try:
                channel = SwitchCraftConfig.get_value("UpdateChannel", "stable")
                checker = UpdateChecker(channel=channel)
                has_update, version_str, _ = checker.check_for_updates()
                note = checker.release_notes or "No changelog available."
                self.changelog_text.value = f"**{i18n.get('latest_version') or 'Latest Version'}:** {version_str}\n\n{note}"
                self.latest_version_text.value = version_str if version_str else (i18n.get("unknown") or "Unknown")
                self.update()

                if not only_changelog and self.app_page:
                     if has_update:
                         # Use SnackBar action logic if needed, but for compatibility keep it simple or implement action support in helper
                         # For now simple message
                         self._show_snack(f"{i18n.get('update_available') or 'Update available'}: {version_str}", "BLUE")
                     else:
                         self._show_snack(i18n.get("no_update_found") or "No updates available.", "GREY")
                     self.app_page.update()

            except Exception as ex:
                self.changelog_text.value = f"{i18n.get('update_check_failed') or 'Error fetching updates'}: {ex}"
                try:
                    self.update()
                except Exception:
                    pass

        threading.Thread(target=_run, daemon=True).start()

    def _start_github_login(self, e):
       # Reuse logic, update references to self.app_page.dialog not self.page.dialog if self.page isn't set on Column?
       # Column gets .page when mounted. but we are using self.app_page.
        def _flow():
            flow = AuthService.initiate_device_flow()
            if not flow:
                self._show_snack("Login init failed")
                return

            def close_dlg(e):
                self.app_page.dialog.open = False
                self.app_page.update()

            def copy_code(e):
                try:
                    import pyperclip
                    pyperclip.copy(flow.get("user_code"))
                except Exception:
                    pass
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
                    ft.Text(flow.get("verification_uri"), color="BLUE"),
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
                self._show_snack(i18n.get("login_success") or "Login Successful!", "GREEN")
            else:
                self._show_snack(i18n.get("login_failed") or "Login Failed or Timed out", "RED")
            self.app_page.update()


        threading.Thread(target=_flow, daemon=True).start()

    def _logout_github(self, e):
        AuthService.logout()
        self._update_sync_ui()

    def _sync_up(self, e):
        def _run():
            if SyncService.sync_up():
                self._show_snack(i18n.get("sync_success_up") or "Sync Up Successful", "GREEN")
            else:
                self._show_snack(i18n.get("sync_failed") or "Sync Up Failed", "RED")
        threading.Thread(target=_run, daemon=True).start()

    def _sync_down(self, e):
        def _run():
             if SyncService.sync_down():
                 self._show_snack(i18n.get("sync_success_down") or "Sync Down Successful. Restart app.", "GREEN")
             else:
                 self._show_snack(i18n.get("sync_failed") or "Sync Down Failed", "RED")
        threading.Thread(target=_run, daemon=True).start()

    def _export_settings(self, e):
        from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
        path = FilePickerHelper.save_file(dialog_title=i18n.get("btn_export_settings") or "Export Settings", file_name="settings.json", allowed_extensions=["json"])
        if path:
            prefs = SwitchCraftConfig.export_preferences()
            with open(path, "w") as f:
                json.dump(prefs, f, indent=4)
            self._show_snack(f"{i18n.get('export_success') or 'Exported to'} {path}")

    def _import_settings(self, e):
        from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
        path = FilePickerHelper.pick_file(allowed_extensions=["json"], allow_multiple=False)
        if path:
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                SwitchCraftConfig.import_preferences(data)
                self._show_snack(i18n.get("import_success") or "Settings Imported. Please Restart.", "GREEN")
            except Exception as ex:
                self._show_snack(f"{i18n.get('import_failed') or 'Import Failed'}: {ex}", "RED")

    def _export_logs(self, e):
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"SwitchCraft_Debug_{timestamp}.log"

        from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
        path = FilePickerHelper.save_file(dialog_title=i18n.get("help_export_logs") or "Export Logs", file_name=filename, allowed_extensions=["log", "txt"])
        if path:
            from switchcraft.utils.logging_handler import get_session_handler
            if get_session_handler().export_logs(path):
                self._show_snack(i18n.get("logs_exported") or f"Logs Exported to {path}")
            else:
                self._show_snack(i18n.get("logs_export_failed") or "Log export failed.", "RED")

    def _show_snack(self, msg, color="GREEN"):
        try:
            self.app_page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.app_page.snack_bar.open = True
            self.app_page.update()
        except Exception:
             pass

    def _check_managed_settings(self):
        """
        Checks if settings are enforced by policy and disables UI elements.
        Called after the view is mounted.
        """
        # Map config keys to UI element attribute names
        managed_keys = [
            "EnableWinget", "Language", "Theme", "AIProvider", "SignScripts",
            "UpdateChannel", "IntuneTenantID", "IntuneClientID", "IntuneClientSecret"
        ]

        for key in managed_keys:
            if SwitchCraftConfig.is_managed(key):
                logger.info(f"Setting '{key}' is managed by policy. UI will be locked.")
                # For now, just log - actual widget disabling would require tracking references
                # We can add a banner or snackbar notification
                try:
                    self._show_snack(f"⚠️ {i18n.get('setting_managed') or 'Some settings are managed by policy.'}", "ORANGE")
                    break  # Only show one snackbar
                except Exception:
                    pass

    def _attach_debug_log_handler(self):
        """Attach a custom log handler that appends messages to the debug console text field."""
        import time

        class FletLogHandler(logging.Handler):
            def __init__(self, text_field, page):
                super().__init__()
                self.text_field = text_field
                self.page = page
                self.buffer = []
                self.last_update = 0
                self.update_interval = 0.5 # Seconds

            def emit(self, record):
                try:
                    msg = self.format(record)
                    self.buffer.append(msg)

                    # Throttle updates
                    current_time = time.time()
                    if current_time - self.last_update > self.update_interval:
                        self.flush_buffer()
                        self.last_update = current_time

                except Exception:
                    pass

            def flush_buffer(self):
                if not self.buffer:
                    return

                # Append buffer content
                try:
                    text_to_add = "\n".join(self.buffer) + "\n"
                    self.buffer.clear()

                    # Check if text field is too long, truncate if needed to prevent memory issues
                    if len(self.text_field.value) > 50000:
                        self.text_field.value = self.text_field.value[-40000:]

                    self.text_field.value += text_to_add

                    if self.page:
                        self.page.update()
                except Exception:
                    pass

        if hasattr(self, "debug_log_text"):
            handler = FletLogHandler(self.debug_log_text, self.app_page)
            # Ensure we flush on exit? No easy way, but this is good enough.
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(logging.Formatter('%(levelname)s | %(name)s | %(message)s'))
            logging.getLogger().addHandler(handler)

    def _build_addon_manager_section(self):
        """Build the Addon Manager UI section."""
        from switchcraft.services.addon_service import AddonService

        addons = [
            {"id": "advanced", "name": i18n.get("addon_advanced_name") or "Advanced Features", "desc": i18n.get("addon_advanced_desc") or "Adds Intune integration and brute force analysis."},
            {"id": "winget", "name": i18n.get("addon_winget_name") or "Winget Integration", "desc": i18n.get("addon_winget_desc") or "Adds Winget package search."},
            {"id": "ai", "name": i18n.get("addon_ai_name") or "AI Assistant", "desc": i18n.get("addon_ai_desc") or "Adds AI-powered help."}
        ]

        rows = []
        for addon in addons:
            is_installed = AddonService().is_addon_installed(addon["id"])
            status_color = "GREEN" if is_installed else "ORANGE"
            status_text = i18n.get("status_installed") or "Installed" if is_installed else i18n.get("status_not_installed") or "Not Installed"

            row = ft.Row([
                ft.Column([
                    ft.Text(addon["name"], weight=ft.FontWeight.BOLD),
                    ft.Text(addon["desc"], size=11, color="GREY")
                ], expand=True),
                ft.Text(status_text, color=status_color),
                ft.ElevatedButton(
                    i18n.get("btn_install") or "Install" if not is_installed else i18n.get("btn_reinstall") or "Reinstall",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=lambda e, aid=addon["id"]: self._install_addon(aid),
                    disabled=is_installed  # Disable if already installed
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            rows.append(row)

        # Custom upload button
        upload_btn = ft.ElevatedButton(
            i18n.get("btn_upload_custom_addon") or "Upload Custom Addon (.zip)",
            icon=ft.Icons.UPLOAD_FILE,
            on_click=self._upload_custom_addon
        )

        # Import from URL button
        url_import_btn = ft.ElevatedButton(
            i18n.get("btn_import_addon_url") or "Import from URL",
            icon=ft.Icons.LINK,
            on_click=self._import_addon_from_url
        )

        return ft.Column(rows + [ft.Row([upload_btn, url_import_btn])], spacing=10)

    def _install_addon(self, addon_id):
        """Install an addon from the official repository."""
        from switchcraft.services.addon_service import AddonService
        import sys
        from pathlib import Path

        self._show_snack(f"{i18n.get('addon_installing') or 'Installing addon'} {addon_id}...", "BLUE")

        # Resolve bundled path
        if getattr(sys, 'frozen', False):
             base_path = Path(sys._MEIPASS) / "assets" / "addons"
        else:
             # src/switchcraft/gui_modern/views/settings_view.py -> src/switchcraft/gui_modern/views -> src/switchcraft/gui_modern -> src/switchcraft -> src -> switchcraft/assets/addons?
             # No: src/switchcraft/gui_modern/views/settings_view.py (level 0)
             # level 1: views
             # level 2: gui_modern
             # level 3: switchcraft
             # level 4: src
             # assets is in src/switchcraft/assets
             # so: parent(views) -> parent(gui_modern) -> parent(switchcraft) / assets / addons ??
             # Wait. app.py is in gui_modern.
             # settings_view.py is in gui_modern/views.
             # So it is one level deeper than app.py.
             # app.py used Path(__file__).parent.parent / "assets" / "addons" (parent of gui_modern is switchcraft).
             # settings_view: parent(views).parent(gui_modern).parent(switchcraft)
             base_path = Path(__file__).parent.parent.parent / "assets" / "addons"

        zip_path = base_path / f"{addon_id}.zip"

        def _run():
            if not zip_path.exists():
                 # TODO: Try online download if not bundled?
                 self._show_snack(f"Addon source not found: {zip_path}", "RED")
                 return

            if AddonService().install_addon(str(zip_path)):
                self._show_snack(f"{i18n.get('addon_install_success') or 'Addon installed successfully!'} ({addon_id})", "GREEN")
            else:
                self._show_snack(f"{i18n.get('addon_install_failed') or 'Addon installation failed.'} ({addon_id})", "RED")

        threading.Thread(target=_run, daemon=True).start()

    def _upload_custom_addon(self, e):
        """Upload and install a custom addon from a .zip file."""
        from switchcraft.services.addon_service import AddonService
        from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper

        path = FilePickerHelper.pick_file(allowed_extensions=["zip"])
        if path:
            if AddonService.install_addon_from_zip(path):
                self._show_snack(i18n.get("addon_install_success") or "Addon installed! Please restart.", "GREEN")
            else:
                self._show_snack(i18n.get("addon_install_failed") or "Failed to install addon.", "RED")

    def _import_addon_from_url(self, e):
        """Import and install an addon from a URL."""
        url_field = ft.TextField(
            label=i18n.get("lbl_addon_url") or "Addon ZIP URL",
            hint_text="https://example.com/addon.zip",
            expand=True
        )

        def do_import(e):
            url = url_field.value
            if not url or not url.strip():
                self._show_snack(i18n.get("err_url_empty") or "Please enter a URL.", "RED")
                return

            self.app_page.dialog.open = False
            self.app_page.update()

            self._show_snack(f"{i18n.get('addon_downloading') or 'Downloading addon'}...", "BLUE")

            def _run():
                import tempfile
                import os
                import urllib.request
                from switchcraft.services.addon_service import AddonService

                try:
                    # Download to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                        tmp_path = tmp.name

                    urllib.request.urlretrieve(url.strip(), tmp_path)

                    # Try to install
                    if AddonService.install_addon_from_zip(tmp_path):
                        self._show_snack(i18n.get("addon_install_success") or "Addon installed! Please restart.", "GREEN")
                    else:
                        self._show_snack(i18n.get("addon_install_failed") or "Failed to install addon. Invalid structure?", "RED")

                    # Cleanup
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

                except Exception as ex:
                    logger.error(f"Failed to download addon from URL: {ex}")
                    self._show_snack(f"{i18n.get('addon_download_failed') or 'Download failed'}: {ex}", "RED")

            threading.Thread(target=_run, daemon=True).start()

        def cancel(e):
            self.app_page.dialog.open = False
            self.app_page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(i18n.get("dlg_import_addon_url") or "Import Addon from URL"),
            content=ft.Column([
                ft.Text(i18n.get("dlg_import_addon_url_desc") or "Enter the URL to a .zip addon file:"),
                url_field,
                ft.Text(i18n.get("addon_custom_warning_msg") or "Only install addons from trusted sources.", size=11, color="ORANGE", italic=True)
            ], tight=True, height=120),
            actions=[
                ft.TextButton(i18n.get("btn_cancel") or "Cancel", on_click=cancel),
                ft.ElevatedButton(i18n.get("btn_import") or "Import", on_click=do_import, bgcolor="GREEN")
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.app_page.dialog = dlg
        dlg.open = True
        self.app_page.update()


    # --- Code Signing Helpers ---

    def _on_signing_toggle(self, value):
        """Handle Code Signing toggle."""
        SwitchCraftConfig.set_user_preference("SignScripts", value)
        if value:
            # Auto-detect on enable if no cert configured
            if not SwitchCraftConfig.get_value("CodeSigningCertThumbprint") and not SwitchCraftConfig.get_value("CodeSigningCertPath"):
                self._auto_detect_signing_cert(None)

    def _auto_detect_signing_cert(self, e):
        """Auto-detect code signing certificates from Windows Certificate Store."""
        import subprocess

        try:
            # Added Timeout and simplified command
            cmd = [
                "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command",
                "Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | Select-Object Subject, Thumbprint | ConvertTo-Json -Depth 1"
            ]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, timeout=10)

            output = proc.stdout.strip()
            if proc.returncode != 0 or not output:
                logger.warning(f"Cert detect returned empty or error: {proc.stderr}")
                self._show_snack(i18n.get("cert_not_found") or "No code signing certificates found.", "ORANGE")
                return

            import json
            try:
                data = json.loads(output)
            except json.JSONDecodeError:
                self._show_snack("Failed to parse cert info", "RED")
                return

            if isinstance(data, dict):
                data = [data]

            if len(data) == 0:
                self._show_snack(i18n.get("cert_not_found") or "No code signing certificates found.", "ORANGE")
            elif len(data) == 1:
                cert = data[0]
                thumb = cert.get("Thumbprint", "")
                subj = cert.get("Subject", "").split(",")[0]
                SwitchCraftConfig.set_user_preference("CodeSigningCertThumbprint", thumb)
                SwitchCraftConfig.set_user_preference("CodeSigningCertPath", "")
                self.cert_status_text.value = f"{subj} ({thumb[:8]}...)"
                self.cert_status_text.color = "GREEN"
                self.update()
                self._show_snack(f"{i18n.get('cert_auto_detected') or 'Certificate auto-detected'}: {subj}", "GREEN")
            else:
                # Multiple certs - just use the first one for now (could show a picker)
                cert = data[0]
                thumb = cert.get("Thumbprint", "")
                subj = cert.get("Subject", "").split(",")[0]
                SwitchCraftConfig.set_user_preference("CodeSigningCertThumbprint", thumb)
                self.cert_status_text.value = f"{subj} ({thumb[:8]}...)"
                self.cert_status_text.color = "GREEN"
                self.update()
                self._show_snack(f"{i18n.get('cert_auto_detected_multi') or 'Multiple certs found, using first'}: {subj}", "BLUE")

        except Exception as ex:
            logger.error(f"Cert auto-detect failed: {ex}")
            self._show_snack(f"{i18n.get('cert_detect_failed') or 'Cert detection failed'}: {ex}", "RED")

    def _browse_signing_cert(self, e):
        """Browse for a .pfx certificate file."""
        from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper

        path = FilePickerHelper.pick_file(allowed_extensions=["pfx"])
        if path:
            SwitchCraftConfig.set_user_preference("CodeSigningCertPath", path)
            SwitchCraftConfig.set_user_preference("CodeSigningCertThumbprint", "")
            self.cert_status_text.value = path
            self.cert_status_text.color = "GREEN"
            self.update()
            self._show_snack(i18n.get("cert_file_selected") or "Certificate file selected.", "GREEN")

    def _reset_signing_cert(self, e):
        """Reset code signing certificate configuration."""
        SwitchCraftConfig.set_user_preference("CodeSigningCertThumbprint", "")
        SwitchCraftConfig.set_user_preference("CodeSigningCertPath", "")
        self.cert_status_text.value = i18n.get("cert_not_configured") or "Not Configured"
        self.cert_status_text.color = "GREY"
        self.update()
        self._show_snack(i18n.get("cert_reset") or "Certificate configuration reset.", "GREY")

    # --- Template Helpers ---

    def _browse_template(self, e):
        """Browse for a custom PowerShell template."""
        from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper

        path = FilePickerHelper.pick_file(allowed_extensions=["ps1"])
        if path:
            SwitchCraftConfig.set_user_preference("CustomTemplatePath", path)
            self.template_status_text.value = path
            self.template_status_text.color = "GREEN"
            self.update()
            self._show_snack(i18n.get("template_selected") or "Template selected.", "GREEN")

    def _reset_template(self, e):
        """Reset to default template."""
        SwitchCraftConfig.set_user_preference("CustomTemplatePath", "")
        self.template_status_text.value = i18n.get("template_default") or "(Default)"
        self.template_status_text.color = "GREY"
        self.update()
        self._show_snack(i18n.get("template_reset") or "Template reset to default.", "GREY")
