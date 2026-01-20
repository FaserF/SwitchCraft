import flet as ft
import threading
import logging
import time
import requests
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
        self.results_list.controls.append(ft.Text(i18n.get("searching", default="Searching..."), color="GREY_500", italic=True))
        try:
            self.update()
        except Exception as ex:
            logger.debug(f"Error updating view in _run_search: {ex}")
            # Try updating just the results list if view update fails
            try:
                self.results_list.update()
            except Exception:
                pass

        def _bg():
            result_holder = {"apps": None, "error": None, "completed": False}

            def _search_task():
                try:
                    token = self._get_token()
                    if not token:
                        result_holder["error"] = "Intune not configured. Please check Settings."
                        result_holder["completed"] = True
                        return

                    if query:
                        apps = self.intune_service.search_apps(token, query)
                    else:
                        apps = self.intune_service.list_apps(token) # Top 50?

                    result_holder["apps"] = apps if apps else []
                    result_holder["completed"] = True
                except requests.exceptions.Timeout:
                    result_holder["error"] = "Request timed out after 30 seconds. Please check your connection and try again."
                    result_holder["completed"] = True
                except requests.exceptions.RequestException as ex:
                    result_holder["error"] = f"Network error: {str(ex)}. Please check your connection."
                    result_holder["completed"] = True
                except Exception as ex:
                    error_msg = str(ex)
                    if "timeout" in error_msg.lower():
                        result_holder["error"] = "Request timed out. Please check your connection and try again."
                    else:
                        result_holder["error"] = f"Error: {error_msg}"
                    result_holder["completed"] = True

            # Start search in background thread
            search_thread = threading.Thread(target=_search_task, daemon=True)
            search_thread.start()

            # Wait for completion with timeout (60 seconds total)
            search_thread.join(timeout=60)

            # Check if thread is still running (timeout occurred)
            if search_thread.is_alive():
                result_holder["error"] = "Search timed out after 60 seconds. Please check your connection and try again."
                result_holder["completed"] = True
                # Force stop the thread (it's daemon, so it will be killed when main thread exits)
                logger.warning("Search thread timed out and is still running")

            # Wait a bit more to ensure result_holder is set (max 1 second)
            timeout_count = 0
            while not result_holder["completed"] and timeout_count < 10:
                time.sleep(0.1)
                timeout_count += 1

            # Ensure completed is set
            if not result_holder["completed"]:
                result_holder["completed"] = True
                if not result_holder["error"] and result_holder["apps"] is None:
                    result_holder["error"] = "Search failed: No response received."

            # Update UI on main thread - use run_task to marshal UI updates to the page event loop
            def _update_ui():
                try:
                    if result_holder["error"]:
                        self._show_error(result_holder["error"])
                    elif result_holder["apps"] is not None:
                        self._update_list(result_holder["apps"])
                    else:
                        self._show_error("Search failed: No results and no error message.")
                except Exception as ex:
                    logger.exception(f"Error in _update_ui: {ex}")
                    self._show_error(f"Error updating UI: {ex}")

            # Use run_task_safe to marshal UI updates to the page event loop
            self._run_task_safe(_update_ui)

        threading.Thread(target=_bg, daemon=True).start()

    def _show_error(self, msg):
        self.results_list.controls.clear()
        self.results_list.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ERROR, color="RED", size=40),
                    ft.Text(f"Error: {msg}", color="red", size=14, selectable=True),
                    ft.Text("Please check your connection and credentials.", color="GREY_500", size=12, italic=True)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                padding=20,
                alignment=ft.Alignment(0, 0)
            )
        )
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
                    title=ft.Text(app.get("displayName", i18n.get("unknown") or "Unknown")),
                    subtitle=ft.Text(app.get("publisher", "")),
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
            # Use run_task_safe to ensure UI updates happen on the correct thread
            self._run_task_safe(lambda: self._show_details(app))
        except Exception as ex:
            logger.exception(f"Error handling app click: {ex}")
            self._show_error(f"Failed to show details: {ex}")

    def _show_details(self, app):
        """
        Render the detailed view for a given Intune app in the details pane with editable fields.

        Builds and displays the app's title (editable), metadata, description (editable), assignments (editable),
        available install/uninstall commands, and action buttons including "Open in Intune" and "Save Changes".
        The view shows a loading indicator while content and assignments are fetched.

        Parameters:
            app (dict): Intune app object (expected keys include `id`, `displayName`, `publisher`, `createdDateTime`,
                       `owner`, `@odata.type`, `description`, `largeIcon`/`iconUrl`/`logoUrl`, `installCommandLine`,
                       `uninstallCommandLine`) used to populate the details UI.
        """
        try:
            logger.info(f"_show_details called for app: {app.get('displayName', 'Unknown')}")
            self.selected_app = app

            # Show loading indicator immediately
            self.details_area.controls.clear()
            self.details_area.controls.append(ft.ProgressBar())
            self.right_pane.visible = True

            # Force update
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

            # Build all content first
            detail_controls = []

            # Create title row with icon placeholder first (images loaded later to avoid blocking UI)
            title_row_container = ft.Row(
                [ft.Icon(ft.Icons.APPS, size=64), ft.Text(app.get("displayName", i18n.get("unknown") or "Unknown"), size=28, weight="bold", selectable=True)],
                spacing=15,
                vertical_alignment=ft.CrossAxisAlignment.START
            )
            detail_controls.append(title_row_container)

            # Load image asynchronously after UI is rendered
            if logo_url:
                def _load_image_async():
                    try:
                        img = ft.Image(src=logo_url, width=64, height=64, fit=ft.ImageFit.CONTAIN, error_content=ft.Icon(ft.Icons.APPS, size=64))
                        # Replace icon with image in title row
                        self._run_task_safe(lambda: self._replace_title_icon(title_row_container, img))
                    except Exception as ex:
                        logger.debug(f"Failed to load logo: {ex}")

                threading.Thread(target=_load_image_async, daemon=True).start()

            # Editable Title Field
            self.title_field = ft.TextField(
                label=i18n.get("field_display_name") or "Display Name",
                value=app.get("displayName", ""),
                expand=True
            )
            detail_controls.append(self.title_field)

            # Metadata (read-only)
            meta_rows = [
                (i18n.get("field_id", default="ID"), app.get("id")),
                (i18n.get("field_publisher", default="Publisher"), app.get("publisher")),
                (i18n.get("field_created", default="Created"), app.get("createdDateTime")),
                (i18n.get("field_owner", default="Owner"), app.get("owner")),
                (i18n.get("field_app_type", default="App Type"), app.get("@odata.type", "").replace("#microsoft.graph.", ""))
            ]

            for k, v in meta_rows:
                if v:
                    detail_controls.append(ft.Text(f"{k}: {v}", selectable=True))

            detail_controls.append(ft.Divider())

            # Editable Description Field
            desc = app.get("description") or ""
            self.description_field = ft.TextField(
                label=i18n.get("field_description") or "Description",
                value=desc,
                multiline=True,
                min_lines=3,
                max_lines=10,
                expand=True
            )
            detail_controls.append(self.description_field)

            detail_controls.append(ft.Divider())

            # Editable Assignments (Async Loading)
            self.assignments_col = ft.Column([ft.ProgressBar(width=200)])
            detail_controls.append(ft.Text(i18n.get("group_assignments") or "Group Assignments:", weight="bold", selectable=True))
            detail_controls.append(self.assignments_col)

            # Store assignments data for editing
            self.current_assignments = []

            def _load_assignments():
                """
                Load and display assignment information for the currently selected app into the view's assignments column.
                Makes assignments editable.
                """
                try:
                    token = self._get_token()
                    if not token:
                        # Marshal UI updates to main thread via _run_task_safe
                        def _show_no_token():
                            self.assignments_col.controls.clear()
                            self.assignments_col.controls.append(ft.Text(i18n.get("intune_not_configured") or "Intune not configured.", italic=True, selectable=True))
                            self.update()
                        self._run_task_safe(_show_no_token)
                        return

                    assignments = self.intune_service.list_app_assignments(token, app.get("id"))
                    self.current_assignments = assignments if assignments else []

                    def _update_assignments_ui():
                        self.assignments_col.controls.clear()
                        if not self.current_assignments:
                            self.assignments_col.controls.append(ft.Text(i18n.get("not_assigned") or "Not assigned.", italic=True, selectable=True))
                            # Add button to add assignment
                            self.assignments_col.controls.append(
                                ft.Button(
                                    i18n.get("btn_add_assignment") or "Add Assignment",
                                    icon=ft.Icons.ADD,
                                    on_click=lambda e: self._add_assignment_row()
                                )
                            )
                        else:
                            # Display editable assignment rows
                            for idx, assignment in enumerate(self.current_assignments):
                                self.assignments_col.controls.append(self._create_assignment_row(assignment, idx))

                            # Add button to add more assignments
                            self.assignments_col.controls.append(
                                ft.Button(
                                    i18n.get("btn_add_assignment") or "Add Assignment",
                                    icon=ft.Icons.ADD,
                                    on_click=lambda e: self._add_assignment_row()
                                )
                            )
                        self.update()

                    self._run_task_safe(_update_assignments_ui)
                except Exception as ex:
                    logger.exception("Failed to load assignments")
                    def _show_error():
                        self.assignments_col.controls.clear()
                        self.assignments_col.controls.append(ft.Text(f"{i18n.get('error') or 'Error'}: {ex}", color="red", selectable=True))
                        self.update()
                    self._run_task_safe(_show_error)

            threading.Thread(target=_load_assignments, daemon=True).start()

            # Install Info (editable if available)
            if "installCommandLine" in app or "uninstallCommandLine" in app:
                 detail_controls.append(ft.Text(i18n.get("commands") or "Commands:", weight="bold", selectable=True))
                 if app.get("installCommandLine"):
                     self.install_cmd_field = ft.TextField(
                         label=i18n.get("field_install", default="Install Command"),
                         value=app.get("installCommandLine", ""),
                         expand=True
                     )
                     detail_controls.append(self.install_cmd_field)
                 if app.get("uninstallCommandLine"):
                     self.uninstall_cmd_field = ft.TextField(
                         label=i18n.get("field_uninstall", default="Uninstall Command"),
                         value=app.get("uninstallCommandLine", ""),
                         expand=True
                     )
                     detail_controls.append(self.uninstall_cmd_field)

            detail_controls.append(ft.Divider())

            # Status and Progress Bar (initially hidden)
            self.save_status_text = ft.Text("", size=12, color="GREY")
            self.save_progress = ft.ProgressBar(width=None, visible=False)
            detail_controls.append(self.save_status_text)
            detail_controls.append(self.save_progress)

            detail_controls.append(ft.Container(height=10))

            # Action Buttons
            detail_controls.append(
                ft.Row([
                    ft.Button(
                        i18n.get("btn_open_in_intune") or "Open in Intune",
                        icon=ft.Icons.OPEN_IN_NEW,
                        bgcolor="BLUE_700",
                        color="WHITE",
                        on_click=lambda e, a=app: self._open_in_intune(a)
                    ),
                    ft.Button(
                        i18n.get("btn_save_changes") or "Save Changes",
                        icon=ft.Icons.SAVE,
                        bgcolor="GREEN",
                        color="WHITE",
                        on_click=lambda e, a=app: self._save_changes(a)
                    ),
                    ft.Button(
                        i18n.get("btn_deploy_assignment") or "Deploy / Assign...",
                        icon=ft.Icons.CLOUD_UPLOAD,
                        bgcolor="BLUE",
                        color="WHITE",
                        on_click=lambda e, a=app: self._show_deployment_dialog(a)
                    )
                ], wrap=True)
            )

            # Update controls in place
            self.details_area.controls = detail_controls
            self.update()

            logger.info(f"Details displayed for: {app.get('displayName', 'Unknown')}")
        except Exception as ex:
            logger.exception(f"Failed to show app details: {ex}")
            self.details_area.controls.clear()
            self.details_area.controls.append(ft.Text(f"{i18n.get('error') or 'Error'}: {str(ex)}", color="red", selectable=True))
            if hasattr(self, 'app_page'):
                self.app_page.update()
            else:
                self.update()

    def _replace_title_icon(self, title_row, image):
        """Replace the icon in title_row with the loaded image."""
        try:
            if len(title_row.controls) >= 2 and isinstance(title_row.controls[0], ft.Icon):
                title_row.controls[0] = image
                title_row.update()
                if hasattr(self, 'app_page'):
                    self.app_page.update()
        except Exception as ex:
            logger.debug(f"Failed to replace title icon: {ex}")

    def _show_deployment_dialog(self, app):
        """
        Show dialog to assign (deploy) the app to a group.
        """
        if not self._get_token():
            self._show_snack("Intune not configured.", "RED")
            return

        # Components
        search_box = ft.TextField(
            label=i18n.get("search_groups") or "Search Groups",
            hint_text="Start typing group name...",
            autofocus=True,
            on_submit=lambda e: _search_groups(e.control.value)
        )
        groups_list = ft.ListView(height=200, spacing=5)

        intent_dropdown = ft.Dropdown(
            label=i18n.get("intent") or "Assignment Intent",
            options=[
                ft.dropdown.Option("required", "Required"),
                ft.dropdown.Option("available", "Available"),
                ft.dropdown.Option("uninstall", "Uninstall")
            ],
            value="required",
            width=150
        )

        selected_group_id = [None] # List to hold ref

        def _search_groups(query):
            groups_list.controls.clear()
            groups_list.controls.append(ft.ProgressBar())
            groups_list.update()

            def _bg():
                try:
                    token = self._get_token()
                    # Filter query for Graph
                    # startswith(displayName, 'query')
                    # Sanitize: Escape single quotes
                    safe_query = query.replace("'", "''")
                    filter_q = f"startswith(displayName, '{safe_query}')" if query else None
                    groups = self.intune_service.list_groups(token, filter_query=filter_q)

                    groups_list.controls.clear()
                    if not groups:
                        groups_list.controls.append(ft.Text("No groups found."))
                    else:
                        for g in groups:
                            def _select(e, gid=g['id'], gname=g['displayName']):
                                selected_group_id[0] = gid
                                search_box.value = gname
                                search_box.update()
                                # Visual feedback could be improved but simple selection for now
                                self._show_snack(f"Selected: {gname}", "BLUE")

                            groups_list.controls.append(
                                ft.ListTile(
                                    title=ft.Text(g.get('displayName', 'Unknown')),
                                    subtitle=ft.Text(g.get('mail', g.get('description', ''))),
                                    leading=ft.Icon(ft.Icons.GROUP),
                                    on_click=_select
                                )
                            )
                    groups_list.update()
                except Exception as ex:
                    logger.error(f"Group search failed: {ex}")
                    groups_list.controls.clear()
                    groups_list.controls.append(ft.Text(f"Error: {ex}", color="RED"))
                    groups_list.update()

            threading.Thread(target=_bg, daemon=True).start()

        def _confirm_assign(e):
            if not selected_group_id[0]:
                self._show_snack("Please select a group first.", "RED")
                return

            dlg.open = False
            self.app_page.update()

            intent = intent_dropdown.value
            group_id = selected_group_id[0]

            self._show_snack(f"Assigning app to {group_id}...", "BLUE")

            def _deploy_bg():
                try:
                    token = self._get_token()
                    self.intune_service.assign_to_group(token, app['id'], group_id, intent)
                    self._show_snack(f"Successfully assigned as {intent}!", "GREEN")
                    # Refresh details
                    # Use run_task_safe to ensure thread safety when calling show_details
                    self._run_task_safe(lambda: self._show_details(app))
                except Exception as ex:
                    self._show_snack(f"Assignment failed: {ex}", "RED")

            threading.Thread(target=_deploy_bg, daemon=True).start()

        dlg = ft.AlertDialog(
            title=ft.Text(i18n.get("deploy_app_title") or f"Deploy '{app.get('displayName')}'"),
            content=ft.Container(
                content=ft.Column([
                    search_box,
                    ft.Button(
                        i18n.get("search") or "Search",
                        icon=ft.Icons.SEARCH,
                        on_click=lambda e: _search_groups(search_box.value)
                    ),
                    ft.Divider(),
                    ft.Text(i18n.get("select_group") or "Select Group:", weight="bold"),
                    groups_list,
                    ft.Divider(),
                    intent_dropdown
                ], spacing=10),
                width=500,
                height=450
            ),
            actions=[
                ft.TextButton(i18n.get("cancel") or "Cancel", on_click=lambda e: setattr(dlg, 'open', False) or self.app_page.update()),
                ft.Button(i18n.get("assign") or "Assign", on_click=_confirm_assign, bgcolor="BLUE", color="WHITE")
            ]
        )

        self.app_page.dialog = dlg
        dlg.open = True
        self.app_page.update()

        # Trigger initial load if search is empty? Maybe top groups.
        _search_groups("")