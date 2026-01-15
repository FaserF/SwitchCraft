import flet as ft
import threading
import logging
from switchcraft.services.intune_service import IntuneService
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.nav_constants import NavIndex
from switchcraft.gui_modern.utils.view_utils import ViewMixin

logger = logging.getLogger(__name__)

class ModernIntuneStoreView(ft.Column, ViewMixin):
    def __init__(self, page: ft.Page):
        """
        Initialize the view: configure state and services, build the search/list left pane and the details right pane, and replace the UI with a credentials prompt when Graph credentials are missing.
        
        Parameters:
            page (ft.Page): The host Flet page used for rendering, navigation, and storing cross-view session data.
        """
        super().__init__(expand=True)
        self.app_page = page
        self.intune_service = IntuneService()

        # State
        self.search_query = ""
        self.apps_list = []
        self.selected_app = None

        # UI Components
        self.search_field = ft.TextField(
            hint_text=i18n.get("search_intune_apps", default="Search Intune Apps..."),
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
            bgcolor="SURFACE_CONTAINER_HIGHEST" if hasattr(getattr(ft, "colors", None), "SURFACE_CONTAINER_HIGHEST") else "GREY_900",
            border_radius=10
        )

        # Right Pane (Details)
        self.right_pane = ft.Container(
            content=self.details_area,
            expand=True,
            padding=20,
            bgcolor="BLACK12",
            border_radius=10,
            visible=True  # Ensure it's visible
        )

        # Add initial placeholder text
        self.details_area.controls.append(
            ft.Text(
                i18n.get("intune_store_select_app") or "Select an app from the list to view details.",
                size=16,
                color="GREY_500",
                italic=True
            )
        )

        self.controls = [
            ft.Text(i18n.get("intune_store_title") or "Intune Store", size=24, weight="bold"),
            ft.Row([self.left_pane, self.right_pane], expand=True)
        ]

        if not self._has_credentials():
             self.controls = [
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.LOCK_RESET_ROUNDED, size=80, color="ORANGE_400"),
                        ft.Text(i18n.get("intune_not_configured") or "Intune is not configured", size=28, weight="bold", text_align=ft.TextAlign.CENTER),
                        ft.Text(i18n.get("intune_config_hint") or "Please configure Microsoft Graph API credentials in Settings.", size=16, color="GREY_400", text_align=ft.TextAlign.CENTER),
                        ft.Container(height=20),
                        ft.Button(
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
        if hasattr(self.app_page, "switchcraft_app") and hasattr(self.app_page.switchcraft_app, "goto_tab"):
            self.app_page.switchcraft_app.goto_tab(NavIndex.SETTINGS_GRAPH)
        elif hasattr(self.app_page, "go"):
            # If using routing
            self.app_page.go("/settings")
        else:
             # Fallback: check if we have a way to signal tab change
             # ModernApp stores 'app' on page in some instances or we can find the rail
             # Since this is a view, we usually just show snackbar or let user navigate.
             self._show_snack(i18n.get("nav_error") or "Cannot navigate to Settings automatically.", "ORANGE")

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
        """
        Populate the results list with the given apps and refresh the UI.
        
        Renders each app as a ListTile showing the app's display name and publisher, using an app logo when available. If `apps` is empty or falsy, inserts a single "No apps found." message. After building the list, triggers a UI update.
        
        Parameters:
            apps (iterable[dict] | None): Iterable of app objects (as returned by IntuneService). Expected keys that are used: `displayName`, `publisher`, and one of `largeIcon` (dict with `value`), `iconUrl`, or `logoUrl` for the logo image.
        """
        self.results_list.controls.clear()
        if not apps:
            self.results_list.controls.append(ft.Text("No apps found."))
        else:
            for app in apps:
                # Try to get logo - robust extraction
                logo_url = None
                large_icon = app.get("largeIcon")
                if isinstance(large_icon, dict):
                    logo_url = large_icon.get("value")
                    # If it's base64, format as data URL
                    if logo_url and not logo_url.startswith(("http://", "https://", "data:")):
                        logo_url = f"data:image/png;base64,{logo_url}"
                elif not logo_url:
                    logo_url = app.get("iconUrl") or app.get("logoUrl")

                leading_widget = ft.Icon(ft.Icons.APPS)
                if logo_url:
                    try:
                        leading_widget = ft.Image(src=logo_url, width=40, height=40, fit=ft.ImageFit.CONTAIN, error_content=ft.Icon(ft.Icons.APPS))
                    except Exception as ex:
                        logger.debug(f"Failed to load logo in list: {ex}")
                        pass

                # Create ListTile with direct lambda (like winget_view does)
                # Capture app in lambda default argument to avoid closure issues
                app_copy = app  # Create a copy reference for closure
                tile = ft.ListTile(
                    leading=leading_widget,
                    title=ft.Text(app.get("displayName", i18n.get("unknown") or "Unknown"), selectable=True),
                    subtitle=ft.Text(app.get("publisher", ""), selectable=True),
                    on_click=lambda e, a=app_copy: self._handle_app_click(a)
                )
                self.results_list.controls.append(tile)
        self.update()

    def _handle_app_click(self, app):
        """
        Handle selection of an app list item and display its details.
        
        Attempts to show the app's details using the page's `run_task` mechanism to ensure UI-thread execution; if `run_task` is unavailable or fails, falls back to a direct call. On error, logs the exception and surfaces an error message in the UI.
        
        Parameters:
            app (dict): Intune app object (as returned by the service) whose details should be displayed.
        """
        try:
            logger.info(f"App clicked: {app.get('displayName', 'Unknown')}")
            # Use run_task to ensure UI updates happen on the correct thread
            if hasattr(self.app_page, 'run_task'):
                try:
                    self.app_page.run_task(lambda: self._show_details(app))
                except Exception:
                    # Fallback if run_task fails
                    self._show_details(app)
            else:
                self._show_details(app)
        except Exception as ex:
            logger.exception(f"Error handling app click: {ex}")
            self._show_error(f"Failed to show details: {ex}")

    def _show_details(self, app):
        """
        Render the detailed view for a given Intune app in the details pane.
        
        Builds and displays the app's title, metadata, description, assignments (loaded asynchronously), available install/uninstall commands, and a Deploy / Package action. The view shows a loading indicator while content and assignments are fetched and forces a UI update on the enclosing page.
        
        Parameters:
            app (dict): Intune app object (expected keys include `id`, `displayName`, `publisher`, `createdDateTime`, `owner`, `@odata.type`, `description`, `largeIcon`/`iconUrl`/`logoUrl`, `installCommandLine`, `uninstallCommandLine`) used to populate the details UI.
        """
        try:
            logger.info(f"_show_details called for app: {app.get('displayName', 'Unknown')}")
            self.selected_app = app

            # Show loading indicator immediately
            self.details_area.controls.clear()
            self.details_area.controls.append(ft.ProgressBar())
            # Force update on the page, not just self
            if hasattr(self, 'app_page'):
                self.app_page.update()
            else:
                self.update()

            # Logo and Title - robust extraction
            logo_url = None
            large_icon = app.get("largeIcon")
            if isinstance(large_icon, dict):
                logo_url = large_icon.get("value")
                # If it's base64, format as data URL
                if logo_url and not logo_url.startswith(("http://", "https://", "data:")):
                    logo_url = f"data:image/png;base64,{logo_url}"
            elif not logo_url:
                logo_url = app.get("iconUrl") or app.get("logoUrl")

            # Remove progress bar and add content
            self.details_area.controls.clear()

            title_row = [ft.Text(app.get("displayName", i18n.get("unknown") or "Unknown"), size=28, weight="bold", selectable=True)]
            if logo_url:
                try:
                    title_row.insert(0, ft.Image(src=logo_url, width=64, height=64, fit=ft.ImageFit.CONTAIN, error_content=ft.Icon(ft.Icons.APPS, size=64)))
                except Exception as ex:
                    logger.debug(f"Failed to load logo: {ex}")
                    pass

            self.details_area.controls.append(
                ft.Row(title_row, spacing=15, vertical_alignment=ft.CrossAxisAlignment.START)
            )

            # Metadata
            meta_rows = [
                (i18n.get("field_id", default="ID"), app.get("id")),
                (i18n.get("field_publisher", default="Publisher"), app.get("publisher")),
                (i18n.get("field_created", default="Created"), app.get("createdDateTime")),
                (i18n.get("field_owner", default="Owner"), app.get("owner")),
                (i18n.get("field_app_type", default="App Type"), app.get("@odata.type", "").replace("#microsoft.graph.", ""))
            ]

            for k, v in meta_rows:
                if v:
                    self.details_area.controls.append(ft.Text(f"{k}: {v}", selectable=True))

            self.details_area.controls.append(ft.Divider())

            # Description
            desc = app.get("description") or i18n.get("no_description") or "No description."
            self.details_area.controls.append(ft.Text(i18n.get("field_description") or "Description:", weight="bold", selectable=True))
            self.details_area.controls.append(ft.Text(desc, selectable=True))

            self.details_area.controls.append(ft.Divider())

            # Assignments (Async Loading)
            self.assignments_col = ft.Column([ft.ProgressBar(width=200)])
            self.details_area.controls.append(ft.Text(i18n.get("group_assignments") or "Group Assignments:", weight="bold", selectable=True))
            self.details_area.controls.append(self.assignments_col)
            self.details_area.controls.append(ft.Divider())

            def _load_assignments():
                """
                Load and display assignment information for the currently selected app into the view's assignments column.
                
                This function fetches app assignments from Intune using the configured token and the current app's id, then clears and populates self.assignments_col.controls with:
                - A centered configuration prompt if Graph credentials are missing.
                - "Not assigned." text when no assignments are returned.
                - Grouped sections for each assignment intent ("Required", "Available", "Uninstall") listing target group identifiers.
                
                On failure, the function logs the exception and displays an error message in the assignments column. The view is updated at the end of the operation.
                """
                try:
                    token = self._get_token()
                    if not token:
                        self.assignments_col.controls.clear()
                        self.assignments_col.controls.append(ft.Text(i18n.get("intune_not_configured") or "Intune not configured.", italic=True, selectable=True))
                        self.update()
                        return

                    assignments = self.intune_service.list_app_assignments(token, app.get("id"))
                    self.assignments_col.controls.clear()
                    if not assignments:
                        self.assignments_col.controls.append(ft.Text(i18n.get("not_assigned") or "Not assigned.", italic=True, selectable=True))
                    else:
                        # Filter for Required, Available, Uninstall
                        types = ["required", "available", "uninstall"]
                        for t in types:
                            typed_assignments = [asgn for asgn in assignments if asgn.get("intent") == t]
                            if typed_assignments:
                                self.assignments_col.controls.append(ft.Text(f"{t.capitalize()}:", weight="bold", size=12, selectable=True))
                                for ta in typed_assignments:
                                    target = ta.get("target", {})
                                    group_id = target.get("groupId") or i18n.get("all_users_devices") or "All Users/Devices"
                                    self.assignments_col.controls.append(ft.Text(f" • {group_id}", size=12, selectable=True))
                except Exception as ex:
                    logger.exception("Failed to load assignments")
                    self.assignments_col.controls.clear()
                    self.assignments_col.controls.append(ft.Text(f"{i18n.get('error') or 'Error'}: {ex}", color="red", selectable=True))
                finally:
                    self.update()

            threading.Thread(target=_load_assignments, daemon=True).start()

            # Install Info
            if "installCommandLine" in app or "uninstallCommandLine" in app:
                 self.details_area.controls.append(ft.Text(i18n.get("commands") or "Commands:", weight="bold", selectable=True))
                 if app.get("installCommandLine"):
                     self.details_area.controls.append(ft.Text(f"{i18n.get('field_install', default='Install')}: `{app.get('installCommandLine')}`", font_family="Consolas", selectable=True))
                 if app.get("uninstallCommandLine"):
                     self.details_area.controls.append(ft.Text(f"{i18n.get('field_uninstall', default='Uninstall')}: `{app.get('uninstallCommandLine')}`", font_family="Consolas", selectable=True))

            self.details_area.controls.append(ft.Container(height=20))
            self.details_area.controls.append(
                ft.Row([
                    ft.Button(
                        i18n.get("btn_deploy_package") or "Deploy / Package...",
                        icon=ft.Icons.CLOUD_UPLOAD,
                        bgcolor="BLUE",
                        color="WHITE",
                        on_click=lambda e, a=app: self._start_packaging_wizard(a)
                    )
                ])
            )

            # Force update on the page to ensure details are visible
            if hasattr(self, 'app_page'):
                self.app_page.update()
            else:
                self.update()

            logger.info(f"Details displayed for: {app.get('displayName', 'Unknown')}")
        except Exception as ex:
            logger.exception(f"Failed to show app details: {ex}")
            self.details_area.controls.clear()
            self.details_area.controls.append(ft.Text(f"{i18n.get('error') or 'Error'}: {str(ex)}", color="red", selectable=True))
            # Force update on the page
            if hasattr(self, 'app_page'):
                self.app_page.update()
            else:
                self.update()

    def _start_packaging_wizard(self, app):
        """
        Open the Packaging Wizard for the given Intune app and make the app available to the wizard.
        
        If the view's page exposes a `switchcraft_app` with a `goto_tab` method, navigates to the packaging wizard tab and stores the provided `app` in the page's `switchcraft_session` under the key `"pending_packaging_app"` so the wizard can prefill its context. If automatic navigation is not available, shows a notification and does nothing else.
        
        Parameters:
            app (dict): Intune app object (as returned by the Intune service) to be provided to the Packaging Wizard for pre-population.
        """
        if not hasattr(self.app_page, "switchcraft_app"):
             self._show_snack("Cannot navigate to Wizard automatically.", "ORANGE")
             return

        # Navigate to Packaging Wizard (NavIndex.PACKAGING_WIZARD)
        app_ref = self.app_page.switchcraft_app
        if hasattr(app_ref, 'goto_tab'):
             app_ref.goto_tab(NavIndex.PACKAGING_WIZARD)
             # Wait a bit and try to populate? Better if we have a state manager.
             # In this architecture, we can try to find the view in the cache or wait for it to be created.
             # Store it in switchcraft_session dict for inter-view communication
             session_storage = getattr(self.app_page, 'switchcraft_session', {})
             session_storage["pending_packaging_app"] = app
             self._show_snack(f"Starting wizard for {app.get('displayName')}...", "BLUE")