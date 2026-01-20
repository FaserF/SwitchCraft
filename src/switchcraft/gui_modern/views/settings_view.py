import flet as ft
import threading
import logging
import json
import os
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n
from switchcraft import __version__
from switchcraft.utils.app_updater import UpdateChecker
from switchcraft.services.auth_service import AuthService
from switchcraft.services.sync_service import SyncService
from switchcraft.services.intune_service import IntuneService
from switchcraft.services.addon_service import AddonService
from switchcraft.gui_modern.utils.view_utils import ViewMixin

logger = logging.getLogger(__name__)

class ModernSettingsView(ft.Column, ViewMixin):
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
            btn = ft.Button(
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
        """
        Switches the view to a new tab by invoking the provided tab builder and updating the UI.

        If `builder_func` is callable, its return value is assigned to `self.current_content.content`. If `builder_func` is None, a localized error message is shown. If the builder raises an exception, the error is logged and a fallback error UI (icon, error text, and guidance) is displayed. The method then attempts to refresh the UI; update failures are ignored.

        Parameters:
            builder_func (Callable[[], ft.Control] | None): Function that constructs and returns the Flet control for the tab, or None to indicate a missing builder.
        """
        try:
            if builder_func:
                self.current_content.content = builder_func()
            else:
                self.current_content.content = ft.Text(i18n.get("error_tab_builder") or "Error: Tab builder missing", color="RED")
        except Exception as e:
            logger.error(f"Failed to build tab: {e}")
            self.current_content.content = ft.Column([
                ft.Icon(ft.Icons.ERROR, color="RED", size=40),
                ft.Text(f"Error loading tab: {e}", color="RED"),
                ft.Text(i18n.get("error_check_logs") or "Check logs for details.", size=12, color="GREY")
            ])

        try:
            self.update()
        except Exception as e:
            logger.warning(f"Failed to update settings view after tab switch: {e}", exc_info=True)

    def _build_general_tab(self):
        # Company Name
        """
        Builds the General settings tab UI.

        Constructs and returns a ListView containing controls for company name, language selection, Winget integration toggle, cloud sync section, AI configuration, export/import settings actions, and a test notification button.

        Returns:
            ft.ListView: A configured ListView that represents the General Settings tab.
        """
        company_field = ft.TextField(
            label=i18n.get("settings_company_name") or "Company Name",
            value=SwitchCraftConfig.get_company_name(),
        )
        company_field.on_blur = lambda e: SwitchCraftConfig.set_user_preference("CompanyName", e.control.value)

        # Language - Always use current i18n language to ensure it's up-to-date
        current_lang = i18n.language  # Get current language from i18n singleton
        lang_dd = ft.Dropdown(
            label=i18n.get("settings_language") or "Language",
            value=current_lang,  # Use current language from i18n, not config (config might be stale)
            options=[
                ft.dropdown.Option("en", "English"),
                ft.dropdown.Option("de", "Deutsch"),
            ],
            expand=True,
        )
        # Set on_change handler - consolidated error handling
        def safe_lang_handler(e):
            try:
                if e.control.value:
                    logger.info(f"Language dropdown changed to: {e.control.value}")
                    self._on_lang_change(e.control.value)
                else:
                    logger.warning("Language dropdown changed but value is None/empty")
            except Exception as ex:
                logger.exception(f"Error in language change handler: {ex}")
                # Show error in crash view for better debugging
                self._show_error_view(ex, "Language dropdown change")
                # Also show snackbar for user feedback
                try:
                    self._show_snack(f"Failed to change language: {ex}", "RED")
                except Exception:
                    pass  # If snackbar fails, error view already shown

        lang_dd.on_change = safe_lang_handler

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
        btn_export = ft.Button(i18n.get("btn_export_settings") or "Export Settings", icon=ft.Icons.UPLOAD_FILE, on_click=self._export_settings)
        btn_import = ft.Button(i18n.get("btn_import_settings") or "Import Settings", icon=ft.Icons.FILE_DOWNLOAD, on_click=self._import_settings)

        export_row = ft.Row([btn_export, btn_import])

        return ft.ListView(
            controls=[
                ft.Text(i18n.get("settings_general") or "General Settings", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Divider(),
                company_field,
                lang_dd,
                winget_sw,
                ft.Divider(),
                cloud_sync,
                ft.Divider(),
                ai_config,
                ft.Divider(),
                ft.Row([
                    ft.Button("Test Notification", icon=ft.Icons.NOTIFICATIONS_ACTIVE, on_click=self._send_test_notification),
                    export_row
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ],
            padding=20,
            spacing=15,
        )

    def _build_cloud_sync_section(self):
        self.sync_status_text = ft.Text(i18n.get("sync_checking_status") or "Checking status...", color="GREY")
        self.sync_actions = ft.Row(visible=False)
        self.login_btn = ft.Button(
            i18n.get("btn_login_github") or "Login with GitHub",
            icon=ft.Icons.LOGIN,
            on_click=self._safe_event_handler(self._start_github_login, "GitHub login button")
        )
        self.logout_btn = ft.Button(i18n.get("btn_logout") or "Logout", icon=ft.Icons.LOGOUT, on_click=self._logout_github, color="RED")

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

            btn_up = ft.Button(i18n.get("btn_sync_up") or "Sync Up", icon=ft.Icons.CLOUD_UPLOAD, on_click=self._sync_up)
            btn_down = ft.Button(i18n.get("btn_sync_down") or "Sync Down", icon=ft.Icons.CLOUD_DOWNLOAD, on_click=self._sync_down)

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
        """
        Builds the Updates settings tab UI.

        Creates and returns a ListView containing:
        - An update channel selector (stable/beta/dev) wired to save changes.
        - Current version and build date display.
        - Latest version display (updated from cached or live checks).
        - A "Check for Updates" button that triggers an update check.
        - A changelog Markdown view populated from cached results or a loading message.

        Returns:
            ft.ListView: The assembled ListView for the Updates tab with version info, controls, and changelog.
        """
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

        check_btn = ft.Button(i18n.get("check_updates") or "Check for Updates", icon=ft.Icons.REFRESH, on_click=self._check_updates)

        return ft.ListView(
            controls=[
                ft.Text(i18n.get("settings_hdr_update") or "Updates", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                channel,
                ft.Row([
                    ft.Text(f"{i18n.get('current_version') or 'Current Version'}: {__version__} ({self._get_build_date()})", weight=ft.FontWeight.BOLD),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([
                    ft.Text(f"{i18n.get('latest_version') or 'Latest Version'}: ", weight=ft.FontWeight.BOLD),
                    self.latest_version_text
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([check_btn], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(),
                ft.Text(i18n.get("changelog") or "Changelog", size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
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
        """
        Builds the Deployment / Global Graph API settings tab UI.

        Constructs and returns a ListView containing controls to configure Entra/Microsoft Graph (tenant, client, secret) with a connection test button, code signing settings (enable switch, certificate display and management buttons), repository and template path fields, and related actions.

        The method also stores references to the tenant, client, and secret input fields and to status text controls (certificate and template status, and test result) on the instance for use by other methods.

        Returns:
            ft.ListView: A ListView populated with controls for Graph/Intune configuration, code signing, paths, and template management.
        """
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

        self.cert_status_text = ft.Text(
            cert_display,
            color="GREEN" if (saved_thumb or saved_cert_path) else "GREY",
            selectable=True  # Make thumbprint selectable for copying
        )

        # Create copy button for thumbprint (only visible if thumbprint exists)
        self.cert_copy_btn = ft.IconButton(
            ft.Icons.COPY,
            tooltip=i18n.get("btn_copy_thumbprint") or "Copy Thumbprint",
            on_click=self._copy_cert_thumbprint,
            visible=bool(saved_thumb),  # Only visible if thumbprint exists
            icon_size=18
        )

        cert_auto_btn = ft.Button(
            i18n.get("btn_auto_detect_cert") or "Auto-Detect",
            icon=ft.Icons.SEARCH,
            on_click=self._auto_detect_signing_cert
        )
        cert_browse_btn = ft.Button(
            i18n.get("btn_browse_cert") or "Browse .pfx",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._browse_signing_cert
        )
        cert_reset_btn = ft.Button(
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

        template_browse_btn = ft.Button(
            i18n.get("btn_browse") or "Browse",
            icon=ft.Icons.FOLDER_OPEN,
            on_click=self._browse_template
        )
        template_reset_btn = ft.Button(
            i18n.get("btn_reset") or "Reset",
            icon=ft.Icons.REFRESH,
            on_click=self._reset_template
        )

        # Intune API Section
        tenant = ft.TextField(label=i18n.get("settings_entra_tenant") or "Entra Tenant ID", value=str(SwitchCraftConfig.get_value("GraphTenantId", "")))
        tenant.on_change=lambda e: SwitchCraftConfig.set_user_preference("GraphTenantId", e.control.value)

        client = ft.TextField(label=i18n.get("settings_entra_client") or "Entra Client ID", value=str(SwitchCraftConfig.get_value("GraphClientId", "")))
        client.on_change=lambda e: SwitchCraftConfig.set_user_preference("GraphClientId", e.control.value)

        secret = ft.TextField(label=i18n.get("settings_entra_secret") or "Entra Client Secret", value=SwitchCraftConfig.get_secure_value("GraphClientSecret") or "", password=True, can_reveal_password=True)
        secret.on_change=lambda e: SwitchCraftConfig.set_secret("GraphClientSecret", e.control.value)

        # Store references for test button
        self.raw_tenant_field = tenant
        self.raw_client_field = client
        self.raw_secret_field = secret

        test_btn = ft.Button(
            "Test Connection",
            icon=ft.Icons.CHECK_CIRCLE,
            on_click=self._test_graph_connection
        )
        self.test_conn_res = ft.Text("", size=12)

        return ft.ListView(
            controls=[
                ft.Text(i18n.get("deployment_title") or "Global Graph API", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(i18n.get("configure_graph_connection") or "Configure your connection to Microsoft Graph. Required for Intune, Entra ID, and Autopilot features.", size=12, color="GREY"),

                # Intune/Graph
                ft.Text(i18n.get("entra_app_reg_config") or "Entra Enterprise App Registration Config", size=18, color="BLUE"),
                tenant,
                client,
                secret,
                ft.Row([test_btn, self.test_conn_res]),
                ft.Divider(),

                # Code Signing
                ft.Text(i18n.get("settings_hdr_signing") or "Code Signing", size=18, color="BLUE"),
                sign_sw,
                ft.Row([
                    ft.Text(i18n.get("lbl_active_cert") or "Active Certificate:"),
                    self.cert_status_text,
                    self.cert_copy_btn  # Copy button for thumbprint
                ], wrap=False),
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
        """
        Builds the Help & Resources tab UI for the settings view.

        The returned view includes links to the project, issue reporter, and documentation; controls to export logs and toggle debug logging; a debug console with streamed logs; a prefilled GitHub issue reporter flow; an addon manager section; a "Danger Zone" factory reset action; and version/credits footer.

        Returns:
            ft.ListView: A ListView containing the assembled controls for the Help & Resources tab.
        """
        links = ft.Row([
            ft.Button(i18n.get("help_github_repo") or "GitHub Repo", icon=ft.Icons.CODE, url="https://github.com/FaserF/SwitchCraft"),
            ft.Button(i18n.get("help_report_issue") or "Report Issue", icon=ft.Icons.BUG_REPORT, url="https://github.com/FaserF/SwitchCraft/issues"),
            ft.Button(i18n.get("help_documentation") or "Documentation", icon=ft.Icons.BOOK, url="https://switchcraft.fabiseitz.de"),
        ])

        logs_btn = ft.Button(i18n.get("help_export_logs") or "Export Logs", icon=ft.Icons.DOWNLOAD, on_click=self._export_logs)

        # Debug Toggle
        debug_sw = ft.Switch(
            label="Enable Debug Logging",
            value=SwitchCraftConfig.is_debug_mode(),
            on_change=self._on_debug_toggle
        )

        # GitHub Issue Reporter with pre-filled body
        def open_issue_reporter(e):
            """
            Open the application's pre-filled GitHub issue reporter for the current session.

            Attempts to open the generated issue URL in the user's default web browser; if that fails, copies the URL to the clipboard. Shows an in-app notification indicating the action taken and logs successes or failures.

            Parameters:
                e: UI event object (ignored).
            """
            try:
                from switchcraft.utils.logging_handler import get_session_handler
                import webbrowser

                logger.info("Opening GitHub issue reporter...")
                url = get_session_handler().get_github_issue_link()
                logger.info(f"Issue URL: {url}")

                # Try to open in default browser
                try:
                    webbrowser.open(url)
                    self._show_snack(i18n.get("issue_reporter_opened") or "Opening GitHub issue reporter...", "BLUE")
                except Exception as ex:
                    logger.error(f"Failed to open browser: {ex}")
                    # Fallback: Copy URL to clipboard and show message
                    try:
                        if hasattr(self.app_page, 'set_clipboard'):
                            self.app_page.set_clipboard(url)
                            self._show_snack(f"{i18n.get('issue_url_copied') or 'Issue URL copied to clipboard'}: {url[:50]}...", "BLUE")
                        else:
                            import pyperclip
                            pyperclip.copy(url)
                            self._show_snack(f"{i18n.get('issue_url_copied') or 'Issue URL copied to clipboard'}: {url[:50]}...", "BLUE")
                    except Exception as ex2:
                        logger.error(f"Failed to copy URL: {ex2}")
                        self._show_snack(f"{i18n.get('issue_reporter_failed') or 'Failed to open issue reporter'}: {ex}", "RED")
            except Exception as ex:
                logger.exception(f"Error opening issue reporter: {ex}")
                self._show_snack(f"{i18n.get('issue_reporter_failed') or 'Failed to open issue reporter'}: {ex}", "RED")

        issue_btn = ft.Button(
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

        debug_toggle_btn = ft.Button(
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
                ft.Button(
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
            margin=ft.Margin.only(top=20)
        )

        return ft.ListView(
            controls=[
                ft.Text(i18n.get("help_title") or "Help & Resources", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Row([links], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([logs_btn, debug_sw], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(),
                ft.Text(i18n.get("help_troubleshooting") or "Troubleshooting", size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Text(i18n.get("help_shared_settings_msg") or "Settings are shared across all SwitchCraft editions (Modern, Legacy, and CLI).", size=12, italic=True, text_align=ft.TextAlign.CENTER),
                ft.Row([
                    issue_btn
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(),
                ft.Text(i18n.get("addon_manager_title") or "Addon Manager", size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                addon_section,
                ft.Divider(),
                ft.Row([debug_toggle_btn], alignment=ft.MainAxisAlignment.CENTER),
                self.debug_log_text,
                danger_zone,
                ft.Divider(),
                ft.Text(f"{i18n.get('about_version') or 'Version'}: {__version__} ({self._get_build_date()})", color="GREY", text_align=ft.TextAlign.CENTER),
                ft.Text(i18n.get("brought_by") or "Brought to you by Fabian Seitz (FaserF)", color="GREY", size=11, text_align=ft.TextAlign.CENTER, italic=True),
                ft.Text(i18n.get("created_with_ai") or "(erstellt mit Hilfe von KI)", color="GREY", size=10, text_align=ft.TextAlign.CENTER, italic=True)
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
        """
        Start an interactive GitHub device‑flow login in a background thread and handle the result.

        Starts the device authorization flow, presents a dialog with the verification URL and user code, opens the browser when requested, polls for an access token, and on success saves the token, updates the cloud-sync UI, and shows a success or failure notification. The dialog is shown on the main thread, but network calls run in background threads.

        Parameters:
            e: The triggering event (e.g., button click). The value is accepted but not used by this method.
        """
        logger.info("GitHub login button clicked, starting device flow...")

        # Store original button state for restoration
        original_text = None
        original_icon = None
        if hasattr(self, 'login_btn'):
            if hasattr(self.login_btn, 'text'):
                original_text = self.login_btn.text
                self.login_btn.text = "Starting..."
            else:
                original_text = self.login_btn.content
                self.login_btn.content = "Starting..."

            original_icon = self.login_btn.icon
            self.login_btn.icon = ft.Icons.HOURGLASS_EMPTY
            self.login_btn.update()

        # Show loading dialog immediately on main thread using safe dialog opening
        loading_dlg = ft.AlertDialog(
            title=ft.Text("Initializing..."),
            content=ft.Column([
                ft.ProgressRing(),
                ft.Text("Connecting to GitHub...")
            ], tight=True)
        )
        # Use _open_dialog_safe for consistent dialog handling
        if not self._open_dialog_safe(loading_dlg):
            logger.error("Failed to open loading dialog for GitHub login")
            self._show_snack("Failed to open login dialog", "RED")
            # Restore button state on early failure
            if hasattr(self, 'login_btn'):
                if hasattr(self.login_btn, 'text'):
                    self.login_btn.text = original_text
                else:
                    self.login_btn.content = original_text
                self.login_btn.icon = original_icon
                self.login_btn.update()
            return

        # Force update to show loading dialog
        self.app_page.update()

        # Start device flow in background (network call)

        def _init_flow():
            try:
                flow = AuthService.initiate_device_flow()
                if not flow:
                    # Marshal UI updates to main thread
                    # Capture original button state in closure using default parameter to avoid scope issues
                    def _handle_no_flow(orig_text=original_text, orig_icon=original_icon):
                        loading_dlg.open = False
                        self.app_page.update()
                        self._show_snack("Login init failed", "RED")
                        # Restore button state
                        if hasattr(self, 'login_btn'):
                            if hasattr(self.login_btn, 'text'):
                                self.login_btn.text = orig_text
                            else:
                                self.login_btn.content = orig_text
                            self.login_btn.icon = orig_icon
                            self.login_btn.update()
                    self._run_task_with_fallback(_handle_no_flow, error_msg="Failed to initialize login flow")
                    return None
                return flow
            except Exception as ex:
                logger.exception(f"Error initiating device flow: {ex}")
                # Marshal UI updates to main thread
                error_msg = f"Failed to initiate login flow: {ex}"
                # Capture error_msg and original button state in closure using default parameter to avoid scope issues
                def _handle_error(msg=error_msg, orig_text=original_text, orig_icon=original_icon):
                    loading_dlg.open = False
                    self.app_page.update()
                    self._show_snack(f"Login error: {msg}", "RED")
                    # Restore button state
                    if hasattr(self, 'login_btn'):
                        if hasattr(self.login_btn, 'text'):
                            self.login_btn.text = orig_text
                        else:
                            self.login_btn.content = orig_text
                        self.login_btn.icon = orig_icon
                        self.login_btn.update()
                self._run_task_with_fallback(_handle_error, error_msg=error_msg)
                return None

        # Show dialog with flow data on main thread
        def _show_dialog_with_flow(flow):
            if not flow:
                return

            def close_dlg(e):
                self.app_page.dialog.open = False
                self.app_page.update()

            def copy_code(e):
                try:
                    import pyperclip
                    pyperclip.copy(flow.get("user_code"))
                except Exception as e:
                    logger.debug(f"Failed to copy user code to clipboard: {e}")
                import webbrowser
                webbrowser.open(flow.get("verification_uri"))

            btn_copy = ft.TextButton("Copy & Open", on_click=copy_code)
            btn_cancel = ft.TextButton("Cancel", on_click=close_dlg)

            dlg = ft.AlertDialog(
                title=ft.Text(i18n.get("github_login") or "GitHub Login"),
                content=ft.Column([
                    ft.Text(i18n.get("please_visit") or "Please visit:"),
                    ft.Text(flow.get("verification_uri"), color="BLUE", selectable=True),
                    ft.Text(i18n.get("and_enter_code") or "And enter code:"),
                    ft.Text(flow.get("user_code"), size=24, weight=ft.FontWeight.BOLD, selectable=True),
                ], height=150, scroll=ft.ScrollMode.AUTO),
                actions=[btn_copy, btn_cancel]
            )

            # Close loading dialog first
            try:
                if hasattr(self.app_page, 'dialog') and self.app_page.dialog:
                    self.app_page.dialog.open = False
                    self.app_page.update()
            except Exception:
                pass

            # Show dialog on main thread
            logger.info("Showing GitHub login dialog...")
            # Use _open_dialog_safe for consistent dialog handling
            if not self._open_dialog_safe(dlg):
                logger.error("Failed to open GitHub login dialog")
                self._show_snack("Failed to show login dialog", "RED")
                return
            logger.info(f"Dialog opened successfully. open={dlg.open}, page.dialog={self.app_page.dialog is not None}")

            # Verify dialog state (if not open after attempts, log warning but don't force)
            if not dlg.open:
                logger.warning("Dialog open flag is False after all attempts. This may indicate a race condition or dialog opening issue.")

            # Poll for token in background thread
            def _poll_token():
                try:
                    token = AuthService.poll_for_token(flow.get("device_code"), flow.get("interval"), flow.get("expires_in"))

                    # Close dialog and show result on main thread
                    async def _close_and_result():
                        dlg.open = False
                        self.app_page.update()
                        # Restore button state
                        if hasattr(self, 'login_btn'):
                            self.login_btn.text = original_text
                            self.login_btn.icon = original_icon
                            self.login_btn.update()
                        if token:
                            AuthService.save_token(token)
                            self._update_sync_ui()
                            self._show_snack(i18n.get("login_success") or "Login Successful!", "GREEN")
                        else:
                            self._show_snack(i18n.get("login_failed") or "Login Failed or Timed out", "RED")

                    if hasattr(self.app_page, 'run_task'):
                        self.app_page.run_task(_close_and_result)
                    else:
                        # Fallback: execute synchronously if run_task not available
                        # Note: This is not ideal but provides backward compatibility
                        import asyncio
                        try:
                            # In a background thread, there's no running loop, so go directly to asyncio.run
                            asyncio.run(_close_and_result())
                        except Exception as e:
                            logger.warning(f"Failed to run async close_and_result: {e}", exc_info=True)
                            # Last resort: try to execute the logic directly
                            dlg.open = False
                            self.app_page.update()
                            if token:
                                AuthService.save_token(token)
                                self._update_sync_ui()
                                self._show_snack(i18n.get("login_success") or "Login Successful!", "GREEN")
                            else:
                                self._show_snack(i18n.get("login_failed") or "Login Failed or Timed out", "RED")
                except Exception as e:
                    # Catch all exceptions including KeyboardInterrupt to prevent unhandled thread exceptions
                    logger.exception(f"Unexpected error in token polling background thread: {e}")

            threading.Thread(target=_poll_token, daemon=True).start()

        # Start flow initiation in background, then show dialog on main thread
        def _flow_complete():
            flow = _init_flow()
            if flow:
                # Create a wrapper function that binds the flow argument
                # This avoids lambda and ensures proper integration with run_task
                def _show_dialog_wrapper():
                    _show_dialog_with_flow(flow)

                def _fallback_show_dialog():
                    try:
                        _show_dialog_with_flow(flow)
                    except Exception as ex2:
                        logger.exception(f"Error showing dialog directly: {ex2}")
                        loading_dlg.open = False
                        self.app_page.update()
                        raise  # Re-raise to trigger error handling in helper

                # Use shared helper for run_task with fallback
                self._run_task_with_fallback(
                    _show_dialog_wrapper,
                    fallback_func=_fallback_show_dialog,
                    error_msg="Failed to show login dialog"
                )

        threading.Thread(target=_flow_complete, daemon=True).start()

    def _logout_github(self, e):
        """
        Logs out the current GitHub/cloud authentication session, refreshes the sync UI, and shows a success or failure notification.

        Performs the logout action, updates the cloud sync section to reflect the unauthenticated state, and displays a green success snackbar on success or a red failure snackbar if an error occurs.

        Parameters:
            e: The triggering event (typically a UI event). This parameter is accepted but not used.
        """
        try:
            AuthService.logout()
            self._update_sync_ui()
            self._show_snack(i18n.get("logout_success") or "Logged out successfully", "GREEN")
        except Exception as ex:
            logger.exception(f"Error logging out: {ex}")
            self._show_snack(f"{i18n.get('logout_failed') or 'Logout failed'}: {ex}", "RED")

    def _sync_up(self, e):
        """
        Start an asynchronous upload of user settings to cloud storage and show a success or failure snack.

        Parameters:
            e: The triggering UI event (unused).
        """
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
        """
        Open a file-save dialog and write current user preferences to a JSON file.

        Opens a save-file picker prompting the user for a destination (default filename "settings.json"); if a path is selected, exports the application preferences to that file as pretty-printed JSON and shows a success notification.
        """
        from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
        path = FilePickerHelper.save_file(dialog_title=i18n.get("btn_export_settings") or "Export Settings", file_name="settings.json", allowed_extensions=["json"])
        if path:
            prefs = SwitchCraftConfig.export_preferences()
            with open(path, "w") as f:
                json.dump(prefs, f, indent=4)
            self._show_snack(f"{i18n.get('export_success') or 'Exported to'} {path}")

    def _import_settings(self, e):
        """
        Import application settings from a user-selected JSON file.

        Opens a file picker restricted to a single `.json` file, parses the selected file as JSON, and applies the data via SwitchCraftConfig.import_preferences. Displays a success snack on successful import; on failure shows an error snack and logs the exception. JSON decoding errors are reported as an invalid JSON file.

        Parameters:
            e: UI event or trigger that invoked this handler (ignored).
        """
        try:
            from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
            path = FilePickerHelper.pick_file(allowed_extensions=["json"], allow_multiple=False)
            if path:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    SwitchCraftConfig.import_preferences(data)
                    self._show_snack(i18n.get("import_success") or "Settings Imported. Please Restart.", "GREEN")
                except json.JSONDecodeError as ex:
                    logger.error(f"Invalid JSON in settings file: {ex}")
                    self._show_snack(f"{i18n.get('import_failed') or 'Import Failed'}: Invalid JSON file", "RED")
                except Exception as ex:
                    logger.exception(f"Error importing settings: {ex}")
                    self._show_snack(f"{i18n.get('import_failed') or 'Import Failed'}: {ex}", "RED")
        except Exception as ex:
            logger.exception(f"Error in import settings handler: {ex}")
            self._show_snack(f"{i18n.get('import_failed') or 'Import Failed'}: {ex}", "RED")

    def _export_logs(self, e):
        """Export logs to a file. Includes current session log and recent log files."""
        import datetime
        import os
        from pathlib import Path

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"SwitchCraft_Debug_{timestamp}.log"

        from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper
        path = FilePickerHelper.save_file(dialog_title=i18n.get("help_export_logs") or "Export Logs", file_name=filename, allowed_extensions=["log", "txt"])

        if not path:
            return  # User cancelled

        try:
            from switchcraft.utils.logging_handler import get_session_handler
            handler = get_session_handler()

            # Try to export current session log first
            exported = False
            if handler.current_log_path and handler.current_log_path.exists():
                try:
                    if handler.file_handler:
                        handler.file_handler.flush()
                    import shutil
                    shutil.copy2(handler.current_log_path, path)
                    exported = True
                    logger.info(f"Exported current session log to {path}")
                except Exception as ex:
                    logger.warning(f"Failed to export current session log: {ex}")

            # If no current log, try to find and export recent log files
            if not exported:
                # Find log directory
                app_data = os.getenv('APPDATA')
                if app_data:
                    log_dir = Path(app_data) / "FaserF" / "SwitchCraft" / "Logs"
                else:
                    log_dir = Path.home() / ".switchcraft" / "logs"

                if log_dir.exists():
                    # Find all session log files
                    log_files = sorted(log_dir.glob("SwitchCraft_Session_*.log"), key=os.path.getmtime, reverse=True)

                    if log_files:
                        # Export the most recent log file
                        try:
                            import shutil
                            shutil.copy2(log_files[0], path)
                            exported = True
                            logger.info(f"Exported recent log file to {path}")
                        except Exception as ex:
                            logger.error(f"Failed to export log file: {ex}")
                            self._show_snack(f"{i18n.get('logs_export_failed') or 'Log export failed'}: {ex}", "RED")
                            return
                    else:
                        logger.warning("No log files found to export")
                        self._show_snack(i18n.get("logs_no_logs_found") or "No log files found to export.", "ORANGE")
                        return
                else:
                    logger.warning(f"Log directory does not exist: {log_dir}")
                    self._show_snack(i18n.get("logs_no_logs_found") or "No log files found to export.", "ORANGE")
                    return

            if exported:
                self._show_snack(i18n.get("logs_exported") or f"Logs exported to {path}", "GREEN")
                # Open the folder containing the exported file
                try:
                    folder_path = Path(path).parent
                    if os.name == 'nt':  # Windows
                        import subprocess
                        subprocess.Popen(['explorer', str(folder_path)])
                    else:
                        # Use ViewMixin's _open_path method for cross-platform support
                        self._open_path(str(folder_path))
                except Exception as ex:
                    logger.debug(f"Failed to open folder: {ex}")
                    # Don't show error to user, folder opening is a nice-to-have feature
            else:
                self._show_snack(i18n.get("logs_export_failed") or "Log export failed.", "RED")

        except Exception as ex:
            logger.exception(f"Error exporting logs: {ex}")
            self._show_snack(f"{i18n.get('logs_export_failed') or 'Log export failed'}: {ex}", "RED")



    def _on_lang_change(self, val):
        """
        Handle a change to the UI language and apply it across the application.

        Saves the selected language to user preferences, updates the i18n singleton, rebuilds the settings view (and main app navigation) to reflect the new language, and shows a confirmation snack. If the app page reference is unavailable, prompts the user to restart the application and performs a restart when confirmed.

        Parameters:
            val (str): Language code or identifier to set (e.g., "en", "fr", etc.).
        """
        logger.info(f"Language change requested: {val}")
        logger.debug(f"Current app_page: {getattr(self, 'app_page', 'Not Set')}, type: {type(getattr(self, 'app_page', None))}")
        try:
            from switchcraft.utils.config import SwitchCraftConfig
            from switchcraft.utils.i18n import i18n

            # Save preference
            SwitchCraftConfig.set_user_preference("Language", val)
            logger.debug(f"Language preference saved: {val}")

            # Actually update the i18n singleton
            i18n.set_language(val)
            logger.debug(f"i18n language updated: {val}")

            # Immediately refresh the current view to apply language change
            # Get current tab index and reload the view
            if hasattr(self.app_page, 'switchcraft_app'):
                app = self.app_page.switchcraft_app
                current_idx = getattr(app, '_current_tab_index', 0)
            else:
                app = None
                current_idx = 0

            # Clear ALL view cache to force rebuild with new language
            if app and hasattr(app, '_view_cache'):
                app._view_cache.clear()

            # Rebuild the Settings View itself (since we're in it)
            # Get current tab index within settings
            current_settings_tab = self.initial_tab_index

            # Rebuild tab definitions with new language
            self.tab_defs = [
                (i18n.get("settings_general") or "General", ft.Icons.SETTINGS, self._build_general_tab),
                (i18n.get("settings_hdr_update") or "Updates", ft.Icons.UPDATE, self._build_updates_tab),
                (i18n.get("deployment_title") or "Global Graph API", ft.Icons.CLOUD_UPLOAD, self._build_deployment_tab),
                (i18n.get("help_title") or "Help", ft.Icons.HELP, self._build_help_tab)
            ]

            # Rebuild tab navigation buttons with new language
            self.nav_row.controls.clear()
            for i, (name, icon, func) in enumerate(self.tab_defs):
                btn = ft.Button(
                    content=ft.Row([ft.Icon(icon), ft.Text(name)]),
                    on_click=lambda e, f=func: self._switch_tab(f),
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=5),
                        bgcolor="PRIMARY_CONTAINER" if i == current_settings_tab else None
                    )
                )
                self.nav_row.controls.append(btn)

            # Rebuild current tab content
            self._switch_tab(self.tab_defs[current_settings_tab][2])

            # Update the nav_row to reflect changes (only if page is attached)
            try:
                if hasattr(self, 'page') and self.page:
                    self.update()
            except RuntimeError as e:
                # Control not attached to page yet, skip update
                logger.debug(f"Control not attached to page yet (RuntimeError): {e}")

            # Reload the main app view to update sidebar labels
            # Use run_task to ensure UI updates happen on main thread
            def _reload_app():
                try:
                    # Get app reference from page
                    if hasattr(self.app_page, 'switchcraft_app'):
                        app = self.app_page.switchcraft_app
                        app.goto_tab(current_idx)
                        self._show_snack(
                            i18n.get("language_changed") or "Language changed. UI updated.",
                            "GREEN"
                        )
                    else:
                        # Fallback: just show message
                        self._show_snack(
                            i18n.get("language_changed") or "Language changed. Please restart to see all changes.",
                            "GREEN"
                        )
                except Exception as ex:
                    logger.exception(f"Error reloading app view: {ex}")
                    # Fallback: just show message
                    self._show_snack(
                        i18n.get("language_changed") or "Language changed. Please restart to see all changes.",
                        "GREEN"
                    )

            # Use _run_task_safe to ensure UI updates happen on main thread
            self._run_task_safe(_reload_app)
            # Force restart dialog if app reload failed or partial
            self._run_task_safe(lambda: self._show_snack("Language changed. Restarting app is recommended.", "ORANGE"))
        except Exception as ex:
            logger.exception(f"Error in language change handler: {ex}")
            self._show_snack(f"Failed to change language: {ex}", "RED")


        # Show restart dialog if app reference not available (outside try-except)
        if not hasattr(self.app_page, 'switchcraft_app') or not self.app_page.switchcraft_app:
            def do_restart(e):
                """
                Restart the application by launching a new process and exiting the current process.

                This function attempts a clean restart by shutting down logging, forcing garbage collection, removing PyInstaller-related environment variables (e.g., `_MEI*`), and spawning a new process with the same executable and arguments. On Windows the new process is started detached and in a new process group. Standard input/output/error are suppressed for the spawned process. If the restart fails, an error snack is shown via self._show_snack.
                """
                dlg.open = False
                self.app_page.update()
                import sys
                import os
                import subprocess
                import time
                import gc
                import logging

                try:
                    if getattr(sys, 'frozen', False):
                        executable = sys.executable
                        args = sys.argv[1:]
                        cwd = os.path.dirname(executable)
                    else:
                        executable = sys.executable
                        args = sys.argv
                        cwd = os.getcwd()

                    # 1. Close all file handles and release resources
                    try:
                        logging.shutdown()
                    except Exception as e:
                        logger.debug(f"Error during logging shutdown: {e}")

                    # 2. Force garbage collection
                    gc.collect()

                    # 3. Small delay to allow file handles to be released
                    time.sleep(0.2)

                    # 4. Prepare environment: remove PyInstaller's _MEIPASS
                    env = os.environ.copy()
                    for key in list(env.keys()):
                        if key.startswith('_MEI'):
                            env.pop(key)
                    env.pop('LD_LIBRARY_PATH', None)

                    # 5. Launch new process
                    creationflags = 0
                    if sys.platform == 'win32':
                        creationflags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

                    subprocess.Popen(
                        [executable] + args,
                        cwd=cwd,
                        env=env,
                        close_fds=True,
                        creationflags=creationflags,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                    # 6. Give the new process a moment to start
                    time.sleep(0.3)

                    # 7. Exit
                    os._exit(0)
                except Exception as ex:
                    self._show_snack(f"Restart failed: {ex}", "RED")

            dlg = ft.AlertDialog(
                title=ft.Text(i18n.get("language_changed") or "Language Changed"),
                content=ft.Text(
                    i18n.get("restart_to_apply") or
                    "The application needs to restart to apply the new language. Restart now?"
                ),
                actions=[
                    ft.TextButton(i18n.get("btn_later") or "Later", on_click=lambda e: setattr(dlg, "open", False) or self.app_page.update()),
                    ft.Button(
                        i18n.get("btn_restart_now") or "Restart Now",
                        on_click=do_restart,
                        bgcolor="BLUE_700",
                        color="WHITE"
                    ),
                ]
            )
            # Use _open_dialog_safe for consistent dialog handling
            if not self._open_dialog_safe(dlg):
                logger.warning("Failed to open restart dialog")

    def _test_graph_connection(self, e):
        """
        Validate Entra (Microsoft Graph/Intune) credentials from the UI fields and report the result.

        Reads tenant ID, client ID, and client secret from the view's credential fields; if any are missing, updates the test result text and color to indicate the missing input. If present, starts an asynchronous authentication attempt and updates the test result text and color to show progress, success, or failure. On success or failure a notification snack is displayed. The method does not raise exceptions (authentication errors are reported in the UI).
        """
        t_id = self.raw_tenant_field.value.strip()
        c_id = self.raw_client_field.value.strip()
        sec = self.raw_secret_field.value.strip()

        if not t_id or not c_id or not sec:
            self.test_conn_res.value = i18n.get("settings_verify_incomplete") or "Missing fields!"
            self.test_conn_res.color = "RED"
            self.update()
            return

        self.test_conn_res.value = i18n.get("settings_verify_progress") or "Connecting..."
        self.test_conn_res.color = "ORANGE"
        self.update()

        def _run():
            try:
                svc = IntuneService()
                svc.authenticate(t_id, c_id, sec)
                self.test_conn_res.value = i18n.get("settings_verify_success") or "Connection Successful!"
                self.test_conn_res.color = "GREEN"
                self._show_snack(i18n.get("settings_verify_success_title") or "Graph Connection Verified!", "GREEN")
            except Exception as ex:
                logger.error(f"Graph Test Failed: {ex}")
                self.test_conn_res.value = f"{i18n.get('settings_verify_fail') or 'Failed'}: {ex}"
                self.test_conn_res.color = "RED"
                self._show_snack(i18n.get("settings_verify_fail_msg", error=str(ex)) or "Graph Connection Failed", "RED")

            self.update()

        threading.Thread(target=_run, daemon=True).start()

    def _send_test_notification(self, e):
        from switchcraft.services.notification_service import NotificationService
        ns = NotificationService()
        ns.add_notification(
            title=i18n.get("notif_test_title") or "Test Notification",
            message=i18n.get("notif_test_msg") or "This is a test notification from Settings! It should trigger a Windows Toast.",
            type="info", # Default info, but forced system notify
            notify_system=True
        )
        self._show_snack(i18n.get("notif_test_sent") or "Test notification sent!", "GREEN")

    def _check_managed_settings(self):
        """
        Checks if settings are enforced by policy and disables UI elements.
        Called after the view is mounted.
        """
        # Map config keys to UI element attribute names
        managed_keys = [
            "EnableWinget", "Language", "Theme", "AIProvider", "SignScripts",
            "UpdateChannel", "GraphTenantId", "GraphClientId", "GraphClientSecret"
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

                except Exception as e:
                    # Use print to avoid recursion if logging fails
                    print(f"FletLogHandler.emit error: {e}")

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
                except Exception as e:
                    # Use print to avoid recursion if logging fails
                    print(f"FletLogHandler.flush_buffer error: {e}")

        if hasattr(self, "debug_log_text"):
            handler = FletLogHandler(self.debug_log_text, self.app_page)
            # Ensure we flush on exit? No easy way, but this is good enough.
            # Set to DEBUG to capture all levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s'))
            # Only add handler if not already added (check by type to avoid duplicate instances)
            root_logger = logging.getLogger()
            # FletLogHandler is defined in this file (line 1304), no need to import
            if not any(isinstance(h, FletLogHandler) for h in root_logger.handlers):
                root_logger.addHandler(handler)
                logger.info("Debug log handler attached to root logger - all log levels will be captured")

    def _build_addon_manager_section(self):
        """
        Create the Addon Manager UI section listing available addons and actions.
        """
        from switchcraft.services.addon_service import AddonService

        # Define addons
        addons = [
            {"id": "advanced", "name": i18n.get("addon_advanced_name") or "Advanced Features", "desc": i18n.get("addon_advanced_desc") or "Adds Intune integration and brute force analysis."},
            {"id": "winget", "name": i18n.get("addon_winget_name") or "Winget Integration", "desc": i18n.get("addon_winget_desc") or "Adds Winget package search."},
            {"id": "ai", "name": i18n.get("addon_ai_name") or "AI Assistant", "desc": i18n.get("addon_ai_desc") or "Adds AI-powered help."}
        ]

        self.addon_controls = {} # Map addon_id -> {btn, progress, status}

        rows = []
        for addon in addons:
            element = self._create_addon_row(addon, AddonService)
            rows.append(element)

        # Custom upload button
        upload_btn = ft.Button(
            i18n.get("btn_upload_custom_addon") or "Upload Custom Addon (.zip)",
            icon=ft.Icons.UPLOAD_FILE,
            on_click=self._upload_custom_addon
        )

        # Import from URL button
        url_import_btn = ft.Button(
            i18n.get("btn_import_addon_url") or "Import from URL",
            icon=ft.Icons.LINK,
            on_click=self._import_addon_from_url
        )

        self.addon_list_container = ft.Column(rows, spacing=10)

        return ft.Column([
            self.addon_list_container,
            ft.Row([upload_btn, url_import_btn])
        ], spacing=10)

    def _create_addon_row(self, addon, AddonService):
        """Helper to create a single addon row and register controls."""
        is_installed = AddonService().is_addon_installed(addon["id"])

        status_text = ft.Text(
            i18n.get("status_installed") or "Installed" if is_installed else i18n.get("status_not_installed") or "Not Installed",
            color="GREEN" if is_installed else "ORANGE"
        )

        install_btn = ft.Button(
            i18n.get("btn_install") or "Install" if not is_installed else i18n.get("btn_reinstall") or "Reinstall",
            icon=ft.Icons.DOWNLOAD,
            on_click=lambda e, aid=addon["id"]: self._install_addon_click(aid),
            disabled=False
        )

        progress = ft.ProgressRing(width=20, height=20, visible=False)

        # Container for Action (Button or Progress)
        action_container = ft.Column([
            install_btn,
            progress
        ], alignment=ft.MainAxisAlignment.CENTER)

        row = ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(addon["name"], weight=ft.FontWeight.BOLD),
                    ft.Text(addon["desc"], size=11, color="GREY")
                ], expand=True),
                status_text,
                action_container
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=10,
            bgcolor="SURFACE_CONTAINER_HIGHEST",
            border_radius=5
        )

        # Store references
        self.addon_controls[addon["id"]] = {
            "btn": install_btn,
            "progress": progress,
            "status": status_text,
            "row": row
        }

        return row

    def _install_addon_click(self, addon_id):
        """Handle install button click with UI updates."""
        controls = self.addon_controls.get(addon_id)
        if not controls:
            return

        # Update UI to loading state
        controls["btn"].visible = False
        controls["progress"].visible = True
        controls["status"].value = i18n.get("addon_installing") or "Installing..."
        controls["status"].color = "BLUE"
        try:
            self.update()
        except Exception:
            pass

        # Determine path (logic from original _install_addon)
        import sys
        from pathlib import Path

        if getattr(sys, 'frozen', False):
             base_path = Path(sys._MEIPASS) / "assets" / "addons"
        else:
             base_path = Path(__file__).parent.parent.parent / "assets" / "addons"

        zip_path = base_path / f"{addon_id}.zip"

        def _run():
            from switchcraft.services.addon_service import AddonService
            success = False
            error_msg = None

            try:
                # 1. Try Bundled
                if zip_path.exists():
                     logger.info(f"Installing {addon_id} from {zip_path}")
                     success = AddonService().install_addon(str(zip_path))
                else:
                     # 2. Try Download
                     logger.info(f"Downloading {addon_id} from GitHub...")
                     success = self._download_and_install_github(addon_id)
            except Exception as e:
                logger.exception(f"Addon install error: {e}")
                error_msg = str(e)
                # Improve error message for common issues
                if "manifest.json" in error_msg.lower():
                    if "missing" in error_msg.lower() or "not found" in error_msg.lower():
                        error_msg = (
                            f"Invalid addon package: manifest.json not found.\n\n"
                            f"The addon ZIP file must contain a manifest.json file at the root level.\n"
                            f"Please ensure the addon is packaged correctly.\n\n"
                            f"Original error: {str(e)}"
                        )
                    else:
                        error_msg = f"Addon validation failed: {str(e)}"
                elif "not found in latest release" in error_msg.lower():
                    error_msg = (
                        f"Addon not available: {addon_id}\n\n"
                        f"The addon was not found in the latest GitHub release.\n"
                        f"Please check if the addon name is correct or if it's available in a different release.\n\n"
                        f"Original error: {str(e)}"
                    )

            # UI Update needs to be safe - must be async for run_task
            async def _ui_update():
                controls["btn"].visible = True
                controls["progress"].visible = False

                if success:
                    controls["status"].value = i18n.get("status_installed") or "Installed"
                    controls["status"].color = "GREEN"
                    controls["btn"].text = i18n.get("btn_reinstall") or "Reinstall"
                    self._show_snack(f"{i18n.get('addon_install_success') or 'Success'}: {addon_id}", "GREEN")
                else:
                    controls["status"].value = i18n.get("status_failed") or "Failed"
                    controls["status"].color = "RED"
                    # Show error message - truncate if too long for snackbar
                    display_error = error_msg or 'Unknown Error'
                    if len(display_error) > 200:
                        display_error = display_error[:197] + "..."
                    self._show_snack(f"{i18n.get('addon_install_failed') or 'Failed'}: {display_error}", "RED")
                    # Also log the full error for debugging
                    logger.error(f"Full addon install error: {error_msg}")

                self.update()

            # Marshal UI update to main thread using run_task (requires async function)
            try:
                if hasattr(self.app_page, 'run_task'):
                    self.app_page.run_task(_ui_update)
                else:
                    # Fallback: execute synchronously if run_task not available
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        task = asyncio.create_task(_ui_update())
                        # Add exception handler to catch and log exceptions from the task
                        def handle_task_exception(task):
                            try:
                                task.result()
                            except Exception as task_ex:
                                logger.exception(f"Exception in async UI update task: {task_ex}")
                        task.add_done_callback(handle_task_exception)
                    except RuntimeError as e:
                        logger.debug(f"No running event loop, using asyncio.run: {e}")
                        asyncio.run(_ui_update())
            except Exception as e:
                logger.error(f"UI update failed: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def _select_addon_asset(self, assets, addon_id):
        """
        Select an addon asset from a list of GitHub release assets.

        Searches for assets matching naming conventions:
        - switchcraft_{addon_id}.zip
        - {addon_id}.zip
        - Prefix-based matches

        Parameters:
            assets: List of asset dictionaries from GitHub API
            addon_id: The addon identifier to search for

        Returns:
            Asset dictionary if found, None otherwise
        """
        # Naming convention: switchcraft_{addon_id}.zip OR {addon_id}.zip
        # Try both naming patterns (matching AddonService.install_from_github logic)
        candidates = [f"switchcraft_{addon_id}.zip", f"{addon_id}.zip"]

        asset = None
        for candidate in candidates:
            # Try exact match first
            asset = next((a for a in assets if a["name"] == candidate), None)
            if asset:
                break

            # Fallback: try case-insensitive match
            asset = next((a for a in assets if a["name"].lower() == candidate.lower()), None)
            if asset:
                break

        # Fallback: try prefix-based match (e.g., "ai" matches "switchcraft_ai.zip")
        if not asset:
            asset = next((a for a in assets if a["name"].startswith(f"switchcraft_{addon_id}") and a["name"].endswith(".zip")), None)

        # Last fallback: try any match with addon_id prefix
        if not asset:
            asset = next((a for a in assets if a["name"].startswith(addon_id) and a["name"].endswith(".zip")), None)

        return asset

    def _download_and_install_github(self, addon_id):
        """Helper to download/install without UI code mixed in."""
        import requests
        import tempfile
        from switchcraft.services.addon_service import AddonService

        repo = "FaserF/SwitchCraft"
        api_url = f"https://api.github.com/repos/{repo}/releases/latest"

        resp = requests.get(api_url, timeout=10)
        resp.raise_for_status()

        assets = resp.json().get("assets", [])
        asset = self._select_addon_asset(assets, addon_id)

        if not asset:
            # List available assets for debugging
            available_assets = [a["name"] for a in assets]
            candidates = [f"switchcraft_{addon_id}.zip", f"{addon_id}.zip"]
            logger.warning(f"Addon {addon_id} not found in latest release. Searched for: {candidates}. Available assets: {available_assets}")
            raise Exception(f"Addon {addon_id} not found in latest release. Searched for: {', '.join(candidates)}. Available: {', '.join(available_assets[:10])}")

        download_url = asset["browser_download_url"]
        asset_name = asset.get("name", f"{addon_id}.zip")
        logger.info(f"Found {asset_name} in release, downloading from: {download_url}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            d_resp = requests.get(download_url, timeout=30)
            d_resp.raise_for_status()
            tmp.write(d_resp.content)
            tmp_path = tmp.name

        try:
            return AddonService().install_addon(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.debug(f"Failed to cleanup temp file {tmp_path}: {e}")

    def _download_addon_from_github(self, addon_id):
        """
        Download and install an addon ZIP named "<addon_id>.zip" from the repository's latest GitHub release.

        Looks up the latest release for the bundled SwitchCraft repository, downloads the release asset matching "{addon_id}.zip", attempts installation via AddonService.install_addon, and removes the temporary download file. Shows user-facing notifications for success or failure and logs errors.

        Parameters:
            addon_id (str): Identifier of the addon; corresponds to the asset filename without the ".zip" extension.
        """
        try:
            import requests

            logger.info(f"Attempting to download {addon_id} from GitHub releases")
            self._show_snack(f"Downloading {addon_id} from GitHub...", "BLUE")

            # Try to get from latest release
            repo = "FaserF/SwitchCraft"
            api_url = f"https://api.github.com/repos/{repo}/releases/latest"

            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                release = response.json()
                assets = release.get("assets", [])
                asset = self._select_addon_asset(assets, addon_id)

                if asset:
                    download_url = asset["browser_download_url"]
                    asset_name = asset.get("name", f"{addon_id}.zip")
                    logger.info(f"Found {asset_name} in release, downloading from: {download_url}")

                    # Download to temp location
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                        download_response = requests.get(download_url, timeout=30)
                        download_response.raise_for_status()
                        tmp.write(download_response.content)
                        tmp_path = tmp.name

                    # Install from downloaded file
                    if AddonService().install_addon(tmp_path):
                        self._show_snack(f"{i18n.get('addon_install_success') or 'Addon installed successfully!'} ({addon_id})", "GREEN")
                    else:
                        self._show_snack(f"{i18n.get('addon_install_failed') or 'Addon installation failed.'} ({addon_id})", "RED")

                    # Cleanup
                    try:
                        os.unlink(tmp_path)
                    except Exception as e:
                        logger.debug(f"Failed to cleanup temp file {tmp_path}: {e}")
                    return

            # If not found in latest release, show error
            available_assets = [a["name"] for a in assets] if assets else []
            candidates = [f"switchcraft_{addon_id}.zip", f"{addon_id}.zip"]
            logger.warning(f"Addon {addon_id} not found in GitHub releases. Searched for: {candidates}. Available assets: {available_assets}")
            self._show_snack(f"Addon {addon_id} not found. Searched for: {', '.join(candidates)}. Available: {', '.join(available_assets[:10]) if available_assets else 'none'}", "RED")
        except Exception as ex:
            logger.exception(f"Failed to download addon from GitHub: {ex}")
            self._show_snack(f"Failed to download addon: {str(ex)}", "RED")

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
                    except Exception as e:
                        logger.debug(f"Failed to cleanup temp file {tmp_path}: {e}")

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
                ft.Button(i18n.get("btn_import") or "Import", on_click=do_import, bgcolor="GREEN")
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
            # Always run auto-detect when enabling code signing
            # This ensures GPO-configured certificates are detected automatically
            # If a cert is already configured, auto-detect will update it if a better match is found
            self._auto_detect_signing_cert(None)

    def _auto_detect_signing_cert(self, e):
        """Auto-detect code signing certificates from Windows Certificate Store.

        Checks in order:
        1. GPO/Policy configured certificate (CodeSigningCertThumbprint from Policy)
        2. CurrentUser\\My certificate store (user certificates)
        3. LocalMachine\\My certificate store (GPO-deployed certificates)
        """
        import subprocess
        import json

        # First, check if GPO/Policy has configured a certificate
        # SwitchCraftConfig.get_value() already checks Policy paths first
        gpo_thumb = SwitchCraftConfig.get_value("CodeSigningCertThumbprint", "")
        gpo_cert_path = SwitchCraftConfig.get_value("CodeSigningCertPath", "")

        # Check if either value is managed by GPO/Policy
        is_gpo_thumb = SwitchCraftConfig.is_managed("CodeSigningCertThumbprint")
        is_gpo_path = SwitchCraftConfig.is_managed("CodeSigningCertPath")

        # If GPO has configured a certificate (either thumbprint or path), honor it and skip auto-detection
        # Check is_managed() first - if policy manages either setting, skip auto-detection entirely
        if is_gpo_thumb or is_gpo_path:
            # Verify the certificate exists in the store if we have a thumbprint
            try:
                if is_gpo_thumb and gpo_thumb:
                    # Check if thumbprint exists in certificate stores
                    verify_cmd = [
                        "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command",
                        f"$cert = Get-ChildItem -Recurse Cert:\\ -CodeSigningCert | Where-Object {{ $_.Thumbprint -eq '{gpo_thumb}' }} | Select-Object -First 1; "
                        f"if ($cert) {{ Write-Output 'FOUND' }} else {{ Write-Output 'NOT_FOUND' }}"
                    ]
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    verify_proc = subprocess.run(verify_cmd, capture_output=True, text=True, startupinfo=startupinfo, timeout=5)

                    if verify_proc.returncode == 0 and "FOUND" in verify_proc.stdout:
                        # GPO certificate exists, use it
                        # Don't overwrite Policy settings, just display them
                        self.cert_status_text.value = f"GPO: {gpo_thumb[:8]}..."
                        self.cert_status_text.color = "GREEN"
                        # Show copy button for GPO thumbprint
                        if hasattr(self, 'cert_copy_btn'):
                            self.cert_copy_btn.visible = True
                        self.update()
                        self._show_snack(i18n.get("cert_gpo_detected") or "GPO-configured certificate detected.", "GREEN")
                        return
                elif is_gpo_path:
                    # GPO has configured a cert path (with or without value), honor it
                    # Don't proceed with auto-detection - policy takes precedence
                    display_path = gpo_cert_path if gpo_cert_path else "(Policy Set)"
                    self.cert_status_text.value = f"GPO: {display_path}"
                    self.cert_status_text.color = "GREEN"
                    self.update()
                    self._show_snack(i18n.get("cert_gpo_detected") or "GPO-configured certificate detected.", "GREEN")
                    return
            except Exception as ex:
                logger.debug(f"GPO cert verification failed: {ex}")
                # If GPO cert is managed but verification fails, validate that we have usable values
                if is_gpo_thumb or is_gpo_path:
                    # Validate that we have actual values, not just policy flags
                    has_usable_value = False
                    if is_gpo_thumb and gpo_thumb and len(gpo_thumb.strip()) > 0:
                        has_usable_value = True
                        display_value = f"{gpo_thumb[:8]}..."
                    elif is_gpo_path and gpo_cert_path and len(gpo_cert_path.strip()) > 0:
                        has_usable_value = True
                        display_value = gpo_cert_path

                    if has_usable_value:
                        # GPO has configured a value, honor it even if verification failed
                        self.cert_status_text.value = f"GPO: {display_value}"
                        self.cert_status_text.color = "ORANGE"  # Orange to indicate verification failed
                        self.update()
                        self._show_snack(i18n.get("cert_gpo_detected") or "GPO-configured certificate detected (verification failed).", "ORANGE")
                        return
                    else:
                        # GPO policy is set but no usable value - warn user
                        logger.warning("GPO policy manages certificate but no usable value found")
                        self.cert_status_text.value = i18n.get("cert_gpo_no_value") or "GPO: Policy set but no value"
                        self.cert_status_text.color = "ORANGE"
                        self.update()
                        self._show_snack(i18n.get("cert_gpo_no_value") or "GPO policy set but certificate value is missing.", "ORANGE")
                        return

        try:
            # Search in order: CurrentUser\\My, then LocalMachine\\My (for GPO-deployed certs)
            cmd = [
                "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command",
                "$certs = @(); "
                "$certs += Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert -ErrorAction SilentlyContinue | Select-Object Subject, Thumbprint; "
                "$certs += Get-ChildItem Cert:\\LocalMachine\\My -CodeSigningCert -ErrorAction SilentlyContinue | Select-Object Subject, Thumbprint; "
                "$certs | ConvertTo-Json -Depth 1"
            ]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, timeout=10)

            output = proc.stdout.strip()
            if proc.returncode != 0 or not output:
                logger.warning(f"Cert detect returned empty or error: {proc.stderr}")
                # If GPO cert was found but verification failed, don't show error
                if not (gpo_thumb or gpo_cert_path):
                    self._show_snack(i18n.get("cert_not_found") or "No code signing certificates found.", "ORANGE")
                return

            try:
                data = json.loads(output)
            except json.JSONDecodeError:
                self._show_snack("Failed to parse cert info", "RED")
                return

            if isinstance(data, dict):
                data = [data]

            if len(data) == 0:
                # If GPO cert was found but not in store, don't show error
                if not (gpo_thumb or gpo_cert_path):
                    self._show_snack(i18n.get("cert_not_found") or "No code signing certificates found.", "ORANGE")
            elif len(data) == 1:
                cert = data[0]
                thumb = cert.get("Thumbprint", "")
                subj = cert.get("Subject", "").split(",")[0]
                # Only save to user preferences if not set by GPO
                if not is_gpo_thumb and not is_gpo_path:
                    SwitchCraftConfig.set_user_preference("CodeSigningCertThumbprint", thumb)
                    SwitchCraftConfig.set_user_preference("CodeSigningCertPath", "")
                self.cert_status_text.value = f"{subj} ({thumb[:8]}...)"
                self.cert_status_text.color = "GREEN"
                # Show copy button when thumbprint is set
                if hasattr(self, 'cert_copy_btn'):
                    self.cert_copy_btn.visible = True
                self.update()
                self._show_snack(f"{i18n.get('cert_auto_detected') or 'Certificate auto-detected'}: {subj}", "GREEN")
            else:
                # Multiple certs - prefer CurrentUser over LocalMachine, use first one
                # Sort: CurrentUser first, then LocalMachine
                cert = data[0]
                thumb = cert.get("Thumbprint", "")
                subj = cert.get("Subject", "").split(",")[0]
                # Only save to user preferences if not set by GPO
                if not is_gpo_thumb and not is_gpo_path:
                    SwitchCraftConfig.set_user_preference("CodeSigningCertThumbprint", thumb)
                self.cert_status_text.value = f"{subj} ({thumb[:8]}...)"
                self.cert_status_text.color = "GREEN"
                # Show copy button when thumbprint is set
                if hasattr(self, 'cert_copy_btn'):
                    self.cert_copy_btn.visible = True
                self.update()
                self._show_snack(f"{i18n.get('cert_auto_detected_multi') or 'Multiple certs found, using first'}: {subj}", "BLUE")

        except Exception as ex:
            logger.error(f"Cert auto-detect failed: {ex}")
            # If GPO cert exists, don't show error
            if not (gpo_thumb or gpo_cert_path):
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
            # Hide copy button when using cert path (not thumbprint)
            if hasattr(self, 'cert_copy_btn'):
                self.cert_copy_btn.visible = False
            self.update()
            self._show_snack(i18n.get("cert_file_selected") or "Certificate file selected.", "GREEN")

    def _reset_signing_cert(self, e):
        """Reset code signing certificate configuration."""
        SwitchCraftConfig.set_user_preference("CodeSigningCertThumbprint", "")
        SwitchCraftConfig.set_user_preference("CodeSigningCertPath", "")
        self.cert_status_text.value = i18n.get("cert_not_configured") or "Not Configured"
        self.cert_status_text.color = "GREY"
        # Hide copy button when cert is reset
        if hasattr(self, 'cert_copy_btn'):
            self.cert_copy_btn.visible = False
        self.update()
        self._show_snack(i18n.get("cert_reset") or "Certificate configuration reset.", "GREY")

    def _copy_cert_thumbprint(self, e):
        """Copy the full certificate thumbprint to clipboard."""
        saved_thumb = SwitchCraftConfig.get_value("CodeSigningCertThumbprint", "")
        if not saved_thumb:
            self._show_snack(i18n.get("cert_not_configured") or "No certificate configured", "ORANGE")
            return

        # Copy to clipboard using the same pattern as other views
        success = False
        try:
            import pyperclip
            pyperclip.copy(saved_thumb)
            success = True
        except ImportError:
            # Fallback to Windows clip command
            try:
                import subprocess
                subprocess.run(['clip'], input=saved_thumb.encode('utf-8'), check=True)
                success = True
            except Exception:
                pass
        except Exception:
            # Try Flet's clipboard as last resort
            try:
                if hasattr(self.app_page, 'set_clipboard'):
                    self.app_page.set_clipboard(saved_thumb)
                    success = True
            except Exception:
                pass

        if success:
            self._show_snack(i18n.get("thumbprint_copied") or f"Thumbprint copied: {saved_thumb[:8]}...", "GREEN")
        else:
            self._show_snack(i18n.get("copy_failed") or "Failed to copy thumbprint", "RED")

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
        """
        Reset the custom template selection to the default.

        Clears the stored CustomTemplatePath user preference, updates the template status label and its color, refreshes the view, and shows a confirmation snackbar.
        """
        SwitchCraftConfig.set_user_preference("CustomTemplatePath", "")
        self.template_status_text.value = i18n.get("template_default") or "(Default)"
        self.template_status_text.color = "GREY"
        self.update()
        self._show_snack(i18n.get("template_reset") or "Template reset to default.", "GREY")

    def _get_build_date(self):
        """
        Return a human-readable build date/time derived from the application's file modification time.

        If the application is running from a frozen (packaged) executable the executable's modification time is used; otherwise the package's __init__.py (or this file as a fallback) is used. If the build date cannot be determined, returns "Unknown".

        Returns:
            A string containing the build date/time in "YYYY-MM-DD HH:MM:SS" format, or "Unknown" if unavailable.
        """
        try:
            import sys
            import os
            from datetime import datetime

            # Try to get build date from __init__.py modification time
            if getattr(sys, 'frozen', False):
                # In frozen build, use executable modification time
                build_time = os.path.getmtime(sys.executable)
            else:
                # In dev, use __init__.py modification time
                init_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "__init__.py")
                if os.path.exists(init_file):
                    build_time = os.path.getmtime(init_file)
                else:
                    build_time = os.path.getmtime(__file__)

            dt = datetime.fromtimestamp(build_time)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "Unknown"