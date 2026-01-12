import flet as ft
import threading
import logging
from switchcraft.services.intune_service import IntuneService
from switchcraft.utils.config import SwitchCraftConfig

logger = logging.getLogger(__name__)

class ModernIntuneStoreView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.intune_service = IntuneService()

        # State
        self.search_query = ""
        self.apps_list = []
        self.selected_app = None

        # UI Components
        self.search_field = ft.TextField(
            hint_text="Search Intune Apps...",
            expand=True,
            on_submit=self._run_search
        )
        self.btn_search = ft.IconButton(ft.Icons.SEARCH, on_click=self._run_search)

        self.results_list = ft.ListView(expand=True, spacing=5)
        self.details_area = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)

        # Left Pane (Search + List)
        self.left_pane = ft.Container(
            content=ft.Column([
                ft.Row([self.search_field, self.btn_search]),
                ft.Divider(),
                self.results_list
            ], expand=True),
            width=350,
            padding=10,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST if hasattr(ft.Colors, "SURFACE_CONTAINER_HIGHEST") else ft.Colors.GREY_900,
            border_radius=10
        )

        # Right Pane (Details)
        self.right_pane = ft.Container(
            content=self.details_area,
            expand=True,
            padding=20,
            bgcolor=ft.Colors.BLACK12,
            border_radius=10
        )

        self.controls = [
            ft.Text("Intune Store", size=24, weight="bold"),
            ft.Row([self.left_pane, self.right_pane], expand=True)
        ]

        if not self._has_credentials():
             self.controls = [
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.LOCK_RESET_ROUNDED, size=80, color=ft.Colors.ORANGE_400),
                        ft.Text(i18n.get("intune_not_configured") or "Intune is not configured", size=28, weight="bold", text_align=ft.TextAlign.CENTER),
                        ft.Text(i18n.get("intune_config_hint") or "Please configure Microsoft Graph API credentials in Settings.", size=16, color=ft.Colors.GREY_400, text_align=ft.TextAlign.CENTER),
                        ft.Container(height=20),
                        ft.ElevatedButton(
                            i18n.get("tab_settings") or "Go to Settings",
                            icon=ft.Icons.SETTINGS,
                            on_click=lambda _: self._switch_to_settings()
                        )
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    expand=True,
                    alignment=ft.Alignment(0, 0)
                )
             ]
             self.alignment = ft.MainAxisAlignment.CENTER

    def _switch_to_settings(self):
        """Helper to jump to settings."""
        if hasattr(self.app_page, "go"):
            # If using routing
            self.app_page.go("/settings")
        else:
             # Fallback: check if we have a way to signal tab change
             # ModernApp stores 'app' on page in some instances or we can find the rail
             # Since this is a view, we usually just show snackbar or let user navigate.
             # But for best UX, we attempt to find the navigation method.
             pass

    def _has_credentials(self):
        tenant_id = SwitchCraftConfig.get_value("GraphTenantId")
        client_id = SwitchCraftConfig.get_value("GraphClientId")
        client_secret = SwitchCraftConfig.get_secure_value("GraphClientSecret")
        return bool(tenant_id and client_id and client_secret)

    def _get_token(self):
        tenant_id = SwitchCraftConfig.get_value("GraphTenantId")
        client_id = SwitchCraftConfig.get_value("GraphClientId")
        client_secret = SwitchCraftConfig.get_secure_value("GraphClientSecret")
        if not (tenant_id and client_id and client_secret):
            return None
        return self.intune_service.authenticate(tenant_id, client_id, client_secret)

    def _run_search(self, e):
        query = self.search_field.value
        self.results_list.controls.clear()
        self.results_list.controls.append(ft.ProgressBar())
        self.update()

        def _bg():
            try:
                token = self._get_token()
                if not token:
                    self._show_error("Intune not configured. Please check Settings.")
                    return

                if query:
                    apps = self.intune_service.search_apps(token, query)
                else:
                    apps = self.intune_service.list_apps(token) # Top 50?

                self._update_list(apps)
            except Exception as ex:
                self._show_error(str(ex))

        threading.Thread(target=_bg, daemon=True).start()

    def _show_error(self, msg):
        self.results_list.controls.clear()
        self.results_list.controls.append(ft.Text(f"Error: {msg}", color="red"))
        self.update()

    def _update_list(self, apps):
        self.results_list.controls.clear()
        if not apps:
            self.results_list.controls.append(ft.Text("No apps found."))
        else:
            for app in apps:
                self.results_list.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.APPS),
                        title=ft.Text(app.get("displayName", "Unknown")),
                        subtitle=ft.Text(app.get("publisher", "")),
                        on_click=lambda e, a=app: self._show_details(a)
                    )
                )
        self.update()

    def _show_details(self, app):
        self.selected_app = app
        self.details_area.controls.clear()

        # Title
        self.details_area.controls.append(
            ft.Text(app.get("displayName", "Unknown"), size=28, weight="bold")
        )

        # Metadata
        meta_rows = [
            ("ID", app.get("id")),
            ("Publisher", app.get("publisher")),
            ("Created", app.get("createdDateTime")),
            ("Owner", app.get("owner")),
            ("App Type", app.get("@odata.type", "").replace("#microsoft.graph.", ""))
        ]

        for k, v in meta_rows:
            if v:
                self.details_area.controls.append(ft.Text(f"{k}: {v}"))

        self.details_area.controls.append(ft.Divider())

        # Description
        desc = app.get("description", "No description.")
        self.details_area.controls.append(ft.Text("Description:", weight="bold"))
        self.details_area.controls.append(ft.Text(desc))

        self.details_area.controls.append(ft.Divider())

        # Install Info
        if "installCommandLine" in app or "uninstallCommandLine" in app:
             self.details_area.controls.append(ft.Text("Commands:", weight="bold"))
             if app.get("installCommandLine"):
                 self.details_area.controls.append(ft.Text(f"Install: `{app.get('installCommandLine')}`", font_family="Consolas"))
             if app.get("uninstallCommandLine"):
                 self.details_area.controls.append(ft.Text(f"Uninstall: `{app.get('uninstallCommandLine')}`", font_family="Consolas"))

        self.update()
