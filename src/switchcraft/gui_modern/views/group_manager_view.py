import flet as ft
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.nav_constants import NavIndex
import logging
import threading
import requests
from switchcraft.services.intune_service import IntuneService
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.gui_modern.utils.view_utils import ViewMixin

logger = logging.getLogger(__name__)

class GroupManagerView(ft.Column, ViewMixin):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True, spacing=0)
        self.app_page = page
        self.intune_service = IntuneService()
        self.groups = []
        self.filtered_groups = []
        self.token = None  # Initialize token

        # State
        self.selected_group = None
        self._ui_initialized = False # Track initialization state

        # Check for credentials first
        if not self._has_credentials():
            self.controls = [
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.LOCK_RESET_ROUNDED, size=80, color="ORANGE_400"),
                        ft.Text(i18n.get("intune_not_configured") or "Intune is not configured", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        ft.Text(i18n.get("intune_config_hint") or "Please configure Microsoft Graph API credentials in Settings.", size=16, color="GREY_400", text_align=ft.TextAlign.CENTER),
                        ft.Container(height=20),
                        ft.FilledButton(
                            content=ft.Row([ft.Icon(ft.Icons.SETTINGS), ft.Text(i18n.get("tab_settings") or "Go to Settings")], alignment=ft.MainAxisAlignment.CENTER),
                            on_click=self._go_to_settings
                        )
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    expand=True,
                    alignment=ft.Alignment(0, 0)
                )
            ]
            return

        # UI Components
        self._init_ui()

        # Ensure filtered_groups is initialized
        if not hasattr(self, 'filtered_groups') or self.filtered_groups is None:
            self.filtered_groups = []

    def did_mount(self):
        """Called when the view is mounted to the page. Load initial data."""
        logger.info("GroupManagerView did_mount called")

        # Guard against uninitialized UI (e.g. missing credentials)
        if not getattr(self, '_ui_initialized', False):
             logger.warning("GroupManagerView did_mount called but UI not initialized (likely missing credentials)")
             return

        # Optimization: Do NOT load all groups on start. Wait for user search.
        # self._load_data()
        self.groups_list.controls.clear()
        self.groups_list.controls.append(
             ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.SEARCH, size=48, color="GREY_400"),
                    ft.Text(i18n.get("entra_search_hint") or "Search to find groups...", color="GREY_500")
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                padding=20
            )
        )
        self.groups_list.update()

    def _init_ui(self):
        # Header
        self.search_field = ft.TextField(
            label=i18n.get("search_groups") or "Search Groups",
            width=300,
            prefix_icon=ft.Icons.SEARCH,
            on_submit=self._safe_event_handler(self._on_search, "Search field submit") # Optimize: Search on enter
        )

        self.refresh_btn = ft.IconButton(ft.Icons.REFRESH, on_click=self._safe_event_handler(lambda _: self._load_data(), "Refresh button"))
        self.create_btn = ft.FilledButton(
            content=ft.Row([ft.Icon(ft.Icons.ADD), ft.Text(i18n.get("btn_create_group") or "Create Group")], alignment=ft.MainAxisAlignment.CENTER),
            on_click=self._safe_event_handler(self._show_create_dialog, "Create group button")
        )

        self.delete_toggle = ft.Switch(
            label=i18n.get("enable_delete_mode") or "Enable Deletion (Danger Zone)",
            value=False,
            on_change=self._safe_event_handler(self._toggle_delete_mode, "Delete toggle")
        )
        self.delete_btn = ft.FilledButton(
            content=ft.Row([ft.Icon(ft.Icons.DELETE_FOREVER), ft.Text(i18n.get("btn_delete_selected") or "Delete Selected")], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="RED",
            color="WHITE",
            disabled=True,
            on_click=self._safe_event_handler(self._confirm_delete, "Delete selected button")
        )

        self.members_btn = ft.FilledButton(
            content=ft.Row([ft.Icon(ft.Icons.PEOPLE), ft.Text(i18n.get("btn_manage_members") or "Manage Members")], alignment=ft.MainAxisAlignment.CENTER),
            disabled=True,
            on_click=self._safe_event_handler(self._show_members_dialog, "Manage Members button")
        )

        # Split header into two rows to prevent buttons from going out of view
        header = ft.Column([
            ft.Row([
                self.search_field,
                self.refresh_btn,
                ft.Container(width=10), # Spacer instead of Divider
                self.create_btn,
                ft.Container(expand=True),
                self.members_btn
            ], alignment=ft.MainAxisAlignment.START), # Use START + Spacer to push items
            ft.Row([
                ft.Container(expand=True),
                self.delete_toggle,
                self.delete_btn
            ], alignment=ft.MainAxisAlignment.END)
        ], spacing=10)

        # Groups List (replacing DataTable with clickable ListView)
        self.groups_list = ft.ListView(expand=True, spacing=5)

        # Initialize with empty state message
        self.groups_list.controls.append(
            ft.Container(
                content=ft.Text(i18n.get("loading_groups") or "Loading groups...", italic=True, color="GREY_500"),
                padding=20,
                alignment=ft.Alignment(0, 0)
            )
        )

        self.list_container = ft.Column([self.groups_list], scroll=ft.ScrollMode.AUTO, expand=True)

        # Main Layout - ensure proper structure
        main_column = ft.Column([
            ft.Text(i18n.get("entra_group_manager_title") or "Entra Group Manager", size=28, weight=ft.FontWeight.BOLD),
            ft.Text(i18n.get("entra_group_manager_desc") or "Manage your Microsoft Entra ID (Azure AD) groups.", color="ON_SURFACE_VARIANT"),
            ft.Divider(),
            header,
            ft.Divider(),
            self.list_container
        ], expand=True, spacing=10)

        main_container = ft.Container(
            content=main_column,
            padding=20,
            expand=True # Ensure container expands
        )

        self.controls = [main_container]

        # Ensure Column properties are set
        self.expand = True
        self.spacing = 0
        self._ui_initialized = True
        logger.debug("GroupManagerView UI initialized successfully")

    def _load_data(self):
        tenant = SwitchCraftConfig.get_value("IntuneTenantID")
        client = SwitchCraftConfig.get_value("IntuneClientID")
        secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret")

        if not all([tenant, client, secret]):
            self._show_snack("Please configure Intune Credentials in Settings", "RED")
            return

        self.list_container.disabled = True
        self.app_page.update()

        def _bg():
            try:
                logger.info("Authenticating with Intune...")
                self.token = self.intune_service.authenticate(tenant, client, secret)
                logger.info("Authentication successful, fetching groups...")
                self.groups = self.intune_service.list_groups(self.token)
                logger.info(f"Fetched {len(self.groups)} groups")
                self.filtered_groups = self.groups.copy() if self.groups else []
                logger.info(f"Filtered groups set to {len(self.filtered_groups)}")

                # Marshal UI update to main thread
                def update_table():
                    try:
                        logger.debug("Updating table UI...")
                        self._update_table()
                        logger.debug("Table UI updated successfully")
                    except (RuntimeError, AttributeError) as e:
                        # Control not added to page yet (common in tests)
                        logger.debug(f"Cannot update table: control not added to page: {e}")
                    except Exception as ex:
                        logger.exception(f"Error updating table: {ex}")
                        self._show_error_view(ex, "Update table")
                self._run_task_safe(update_table)
            except requests.exceptions.HTTPError as e:
                # Handle specific permission error (403)
                logger.error(f"Permission denied loading groups: {e}")
                if e.response is not None and e.response.status_code == 403:
                    missing_perms = "Group.Read.All, Group.ReadWrite.All"
                    error_msg = i18n.get("graph_permission_error", permissions=missing_perms) or f"Missing Graph API permissions: {missing_perms}"
                else:
                    error_msg = f"HTTP Error: {e}"
                # Marshal UI update to main thread
                def show_error():
                    try:
                        self._show_snack(error_msg, "RED")
                        self.list_container.disabled = False
                        self.update()
                    except (RuntimeError, AttributeError) as e:
                        logger.debug(f"Control not added to page (RuntimeError/AttributeError): {e}")
                self._run_task_safe(show_error)
            except requests.exceptions.ConnectionError as e:
                # Handle authentication failure
                logger.error(f"Authentication failed: {e}")
                error_msg = i18n.get("graph_auth_error") or "Authentication failed. Please check your credentials."
                # Marshal UI update to main thread
                def show_error():
                    try:
                        self._show_snack(error_msg, "RED")
                        self.list_container.disabled = False
                        self.update()
                    except (RuntimeError, AttributeError) as e:
                        logger.debug(f"Control not added to page (RuntimeError/AttributeError): {e}")
                self._run_task_safe(show_error)
            except Exception as e:
                # Catch-all for any other errors to ensure UI releases loading state
                logger.exception(f"Critical error in group loading thread: {e}")

                error_str = str(e).lower()
                # Detect permission issues from error message
                if "403" in error_str or "forbidden" in error_str or "insufficient" in error_str:
                    error_msg = i18n.get("graph_permission_error", permissions="Group.Read.All") or "Missing Graph API permissions: Group.Read.All"
                elif "401" in error_str or "unauthorized" in error_str:
                    error_msg = i18n.get("graph_auth_error") or "Authentication failed. Please check your credentials."
                else:
                    error_msg = f"Failed to load groups: {e}"

                def show_critical_error():
                    try:
                        self._show_snack(error_msg, "RED")
                        self.list_container.disabled = False
                        if hasattr(self, 'groups_list'):
                            self.groups_list.controls.clear()
                            self.groups_list.controls.append(
                                ft.Container(
                                    content=ft.Column([
                                        ft.Icon(ft.Icons.ERROR_OUTLINE, color="RED", size=48),
                                        ft.Text(error_msg, color="RED", text_align=ft.TextAlign.CENTER),
                                        ft.FilledButton(content=ft.Text("Retry"), on_click=lambda _: self._load_data())
                                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                    alignment=ft.alignment.center,
                                    padding=20
                                )
                            )
                            try:
                                self.groups_list.update()
                            except Exception:
                                pass
                        self.update()
                    except Exception as ui_ex:
                        logger.error(f"Failed to update UI with error: {ui_ex}")
                self._run_task_safe(show_critical_error)

        threading.Thread(target=_bg, daemon=True).start()

    def _update_table(self):
        """Update the groups list UI. Must be called on UI thread."""
        logger.info(f"_update_table called with {len(self.filtered_groups) if hasattr(self, 'filtered_groups') and self.filtered_groups else 0} filtered groups")

        # This method is already expected to be called on the UI thread (via _run_task_safe)
        # So we can directly update the UI without another wrapper
        try:
            logger.debug("Clearing groups list...")
            self.groups_list.controls.clear()

            if not self.filtered_groups:
                logger.info("No filtered groups, showing empty state")
                self.groups_list.controls.append(
                    ft.Container(
                        content=ft.Text(i18n.get("no_groups_found") or "No groups found.", italic=True, color="ON_SURFACE_VARIANT"),
                        padding=20,
                        alignment=ft.Alignment(0, 0)
                    )
                )
            else:
                logger.info(f"Adding {len(self.filtered_groups)} groups to list...")
                for g in self.filtered_groups:
                    is_selected = self.selected_group == g or (self.selected_group and self.selected_group.get('id') == g.get('id'))

                    # Create clickable tile for each group
                    # Fix: Move on_click to ListTile for reliable selection handling
                    tile = ft.Container(
                        content=ft.ListTile(
                            leading=ft.Icon(
                                ft.Icons.CHECK_CIRCLE if is_selected else ft.Icons.RADIO_BUTTON_UNCHECKED,
                                color="BLUE" if is_selected else "GREY"
                            ),
                            title=ft.Text(g.get('displayName', ''), weight=ft.FontWeight.BOLD if is_selected else None),
                            subtitle=ft.Column([
                                ft.Text(g.get('description', '') or i18n.get("no_description") or "No description", size=12, color="GREY_600"),
                                ft.Text(f"ID: {g.get('id', '')}", size=10, color="GREY_500"),
                                ft.Text(f"Type: {', '.join(g.get('groupTypes') or []) or 'Security'}", size=10, color="GREY_500"),
                            ], spacing=2, tight=True),
                            trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, color="GREY_400") if is_selected else None,
                            on_click=self._safe_event_handler(lambda e, grp=g: self._on_group_click(grp), f"Group click {g.get('displayName', 'Unknown')}")
                        ),
                        bgcolor="BLUE_50" if is_selected else None,
                        border=ft.Border.all(2, "BLUE" if is_selected else "GREY_300"),
                        border_radius=5,
                        padding=0, # Padding managed by ListTile
                        data=g
                    )
                    self.groups_list.controls.append(tile)

                logger.info(f"Added {len(self.groups_list.controls)} tiles to groups list")

            logger.debug("Updating groups_list and view...")
            try:
                self.groups_list.update()
                logger.debug("groups_list.update() called successfully")
            except Exception as ex:
                logger.error(f"Error updating groups_list: {ex}", exc_info=True)

            try:
                self.update()
                logger.debug("self.update() called successfully")
            except Exception as ex:
                logger.error(f"Error updating view: {ex}", exc_info=True)

            # Also update app_page if available
            if hasattr(self, 'app_page') and self.app_page:
                try:
                    self.app_page.update()
                    logger.debug("app_page.update() called successfully")
                except Exception as ex:
                    logger.error(f"Error updating app_page: {ex}", exc_info=True)

            logger.info("Table UI update complete")
        except (RuntimeError, AttributeError) as e:
            # Control not added to page yet (common in tests)
            logger.debug(f"Cannot update groups list: control not added to page: {e}")
        except Exception as ex:
            logger.exception(f"Unexpected error in _update_table: {ex}")
            self._show_error_view(ex, "Update table")

    def _on_search(self, e):
        """
        Handle search submission.
        Triggers server-side search instead of client-side filtering.
        """
        try:
            query = self.search_field.value
            logger.info(f"Search query: {query}")

            if not query or not query.strip():
                # self._load_data() # Optionally load all or clear
                self.filtered_groups = []
                self._update_table()
                return

            self.list_container.disabled = True
            self.update()

            def _bg():
                try:
                    # Use IntuneService to search/filter
                    # Graph API filter for groups: startswith(displayName, 'query')
                    # Note: IntuneService needs a dedicated search method or we adapt list_groups
                    # Using list_groups with filter query manually for now:

                     # Authenticate if needed
                    if not self.token:
                         tenant = SwitchCraftConfig.get_value("IntuneTenantID")
                         client = SwitchCraftConfig.get_value("IntuneClientID")
                         secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret")
                         self.token = self.intune_service.authenticate(tenant, client, secret)

                    # Build filter
                    # Case-insensitive usually requires specific headers or advanced query,
                    # but 'startswith' is often case-insensitive in Graph for some properties or we try best effort.
                    # Simple filter: startswith(displayName, 'query')
                    escaped_query = query.replace("'", "''")
                    filter_str = f"startswith(displayName, '{escaped_query}')"

                    self.groups = self.intune_service.list_groups(self.token, filter_query=filter_str)
                    self.filtered_groups = self.groups # Result is already filtered

                    self._run_task_safe(lambda: [
                        setattr(self.list_container, 'disabled', False),
                        self._update_table()
                    ])
                except Exception as ex:
                    logger.error(f"Search failed: {ex}", exc_info=True)
                    error_msg = f"Search failed: {ex}"
                    self._run_task_safe(lambda: [
                        setattr(self.list_container, 'disabled', False),
                        self._show_snack(error_msg, "RED"),
                        self.update()
                    ])

            threading.Thread(target=_bg, daemon=True).start()

        except Exception as ex:
            logger.error(f"Error in search: {ex}", exc_info=True)
            self._show_error_view(ex, "Search")

    def _on_group_click(self, group):
        """Handle click on a group tile to select/deselect it."""
        try:
            # Toggle selection: if same group clicked, deselect; otherwise select new group
            if self.selected_group and self.selected_group.get('id') == group.get('id'):
                self.selected_group = None
            else:
                self.selected_group = group

            # Update UI to reflect selection
            self._update_table()

            # Enable delete only if toggle on and item selected
            is_delete_enabled = self.delete_toggle.value and self.selected_group is not None
            self.delete_btn.disabled = not is_delete_enabled
            self.members_btn.disabled = not self.selected_group

            # Force UI update
            self._run_task_safe(lambda: self.update())

            # Show feedback
            if self.selected_group:
                self._show_snack(f"Selected: {self.selected_group.get('displayName', '')}", "BLUE")
            else:
                self._show_snack(i18n.get("group_deselected") or "Group deselected", "GREY")
        except Exception as ex:
            logger.exception(f"Error handling group click: {ex}")
            self._show_error_view(ex, "Group click handler")

    def _toggle_delete_mode(self, e):
        """Toggle delete mode and update delete button state."""
        try:
            is_enabled = self.delete_toggle.value and self.selected_group is not None
            self.delete_btn.disabled = not is_enabled
            logger.debug(f"Delete mode toggled: {self.delete_toggle.value}, selected_group: {self.selected_group is not None}, delete_btn disabled: {not is_enabled}")
            self._run_task_safe(lambda: self.update())
        except Exception as ex:
            logger.exception(f"Error toggling delete mode: {ex}")
            self._show_error_view(ex, "Toggle delete mode")

    def _show_create_dialog(self, e):
        """Show dialog to create a new group."""
        try:
            def close_dlg(e):
                self._close_dialog(dlg)

            name_field = ft.TextField(label=i18n.get("group_name") or "Group Name", autofocus=True)
            desc_field = ft.TextField(label=i18n.get("group_desc") or "Description", multiline=True)

            def create(e):
                if not name_field.value or not name_field.value.strip():
                    self._show_snack(i18n.get("group_name_required") or "Group name is required", "RED")
                    return
                if not self.token:
                    self._show_snack(i18n.get("not_connected_intune") or "Not connected to Intune", "RED")
                    self._close_dialog(dlg)
                    return

                def _bg():
                    try:
                        self.intune_service.create_group(self.token, name_field.value.strip(), desc_field.value or "")
                        def update_ui():
                            try:
                                self._show_snack(f"Group '{name_field.value}' created!", "GREEN")
                                self._close_dialog(dlg)
                                self._load_data()
                            except Exception as ex:
                                logger.error(f"Error updating UI after group creation: {ex}", exc_info=True)
                        self._run_task_safe(update_ui)
                    except Exception as ex:
                        logger.error(f"Failed to create group: {ex}", exc_info=True)
                        def show_error(error=ex):
                            try:
                                msg = f"Creation failed: {error}"
                                self._show_snack(msg, "RED")
                            except Exception:
                                pass
                        self._run_task_safe(show_error)
                    except BaseException:
                        # Catch all exceptions including KeyboardInterrupt to prevent unhandled thread exceptions
                        logger.exception("Unexpected error in group creation background thread")

                threading.Thread(target=_bg, daemon=True).start()

            dlg = ft.AlertDialog(
                title=ft.Text(i18n.get("create_new_group") or "Create New Group"),
                content=ft.Column([name_field, desc_field], height=150, width=400),
                actions=[
                    ft.TextButton(i18n.get("cancel") or "Cancel", on_click=close_dlg),
                    ft.FilledButton(content=ft.Text(i18n.get("create") or "Create"), on_click=self._safe_event_handler(create, "Create group button"), bgcolor="BLUE", color="WHITE")
                ],
            )
            if not self._open_dialog_safe(dlg):
                self._show_snack("Failed to open create group dialog", "RED")
        except Exception as ex:
            logger.exception(f"Error showing create dialog: {ex}")
            self._show_snack(f"Failed to open create dialog: {ex}", "RED")

    def _confirm_delete(self, e):
        """Show confirmation dialog and delete selected group."""
        if not self.selected_group:
            self._show_snack(i18n.get("no_group_selected") or "No group selected", "ORANGE")
            return

        if not self.delete_toggle.value:
            self._show_snack(i18n.get("delete_mode_not_enabled") or "Delete mode is not enabled", "ORANGE")
            return

        try:
            def close_dlg(e):
                self._close_dialog(dlg)

            def delete(e):
                grp_id = self.selected_group.get('id')
                if not grp_id:
                    self._show_snack("Error: Selected group has no ID", "RED")
                    self._close_dialog(dlg)
                    return
                if not self.token:
                    self._show_snack("Not connected to Intune", "RED")
                    self._close_dialog(dlg)
                    return

                def _bg():
                    try:
                        self.intune_service.delete_group(self.token, grp_id)
                        def update_ui():
                            try:
                                self._show_snack("Group deleted.", "GREEN")
                                self._close_dialog(dlg)
                                self.selected_group = None
                                self.delete_btn.disabled = True
                                self.members_btn.disabled = True
                                self._load_data()
                            except Exception as ex:
                                logger.error(f"Error updating UI after deletion: {ex}", exc_info=True)
                        self._run_task_safe(update_ui)
                    except Exception as ex:
                        logger.error(f"Failed to delete group: {ex}", exc_info=True)
                        def show_error(error=ex):
                            try:
                                msg = f"Deletion failed: {error}"
                                self._show_snack(msg, "RED")
                            except Exception:
                                pass
                        self._run_task_safe(show_error)
                threading.Thread(target=_bg, daemon=True).start()

            group_name = self.selected_group.get('displayName', 'Unknown')
            dlg = ft.AlertDialog(
                title=ft.Text(i18n.get("confirm_deletion") or "Confirm Deletion"),
                content=ft.Text(
                    i18n.get("confirm_delete_group") or f"Are you sure you want to delete '{group_name}'? This cannot be undone.",
                    selectable=True
                ),
                actions=[
                    ft.TextButton(i18n.get("cancel") or "Cancel", on_click=close_dlg),
                    ft.FilledButton(
                        content=ft.Text(i18n.get("delete") or "Delete"),
                        on_click=self._safe_event_handler(delete, "Delete group button"),
                        bgcolor="RED",
                        color="WHITE"
                    )
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            if not self._open_dialog_safe(dlg):
                self._show_snack("Failed to open delete confirmation dialog", "RED")
        except Exception as ex:
            logger.exception(f"Error showing delete confirmation: {ex}")
            self._show_snack(f"Failed to show delete confirmation: {ex}", "RED")



    def _has_credentials(self):
        """Check if Graph API credentials are configured."""
        tenant_id = SwitchCraftConfig.get_value("IntuneTenantID")
        client_id = SwitchCraftConfig.get_value("IntuneClientID")
        client_secret = SwitchCraftConfig.get_secure_value("IntuneClientSecret")
        return bool(tenant_id and client_id and client_secret)

    def _go_to_settings(self, e):
        """Navigate to Settings tab."""
        try:
            if hasattr(self.app_page, 'switchcraft_app'):
                self.app_page.switchcraft_app.goto_tab(NavIndex.SETTINGS_GRAPH)
                return

            for attr in dir(self.app_page):
                if 'app' in attr.lower():
                    app_ref = getattr(self.app_page, attr, None)
                    if app_ref and hasattr(app_ref, 'goto_tab'):
                        app_ref.goto_tab(NavIndex.SETTINGS_GRAPH)
                        return
        except Exception:
            pass
        self._show_snack("Please navigate to Settings tab manually", "ORANGE")

    def _show_members_dialog(self, e):
        """Show dialog to manage group members."""
        try:
            logger.info("Opening 'Manage Members' dialog...")
            if not self.selected_group:
                logger.warning("Cannot show members dialog: no group selected")
                self._show_snack(i18n.get("select_group_first") or "Please select a group first.", "ORANGE")
                return

            if not self.token:
                logger.warning("Cannot show members dialog: no token")
                self._show_snack(i18n.get("not_connected_intune") or "Not connected to Intune. Please refresh.", "RED")
                return

            group_name = self.selected_group.get('displayName', 'Unknown')
            group_id = self.selected_group.get('id')
            logger.debug(f"Managing members for group: {group_name} ({group_id})")

            if not group_id:
                logger.error(f"Cannot show members dialog: group has no ID. Group: {self.selected_group}")
                self._show_snack("Error: Selected group has no ID", "RED")
                return
        except Exception as ex:
            logger.exception(f"Error in _show_members_dialog setup: {ex}")
            self._show_snack(f"Failed to open members dialog: {ex}", "RED")
            return

        # Dialog controls
        members_list = ft.ListView(expand=True, spacing=10, height=300)
        loading = ft.ProgressBar(width=None)

        def remove_member(user_id):
            def _bg():
                try:
                    self.intune_service.remove_group_member(self.token, group_id, user_id)
                    # Marshal UI updates to main thread
                    self._run_task_safe(lambda: self._show_snack(i18n.get("member_removed") or "Member removed", "GREEN"))
                    self._run_task_safe(load_members) # Refresh
                except Exception as ex:
                    logger.error(f"Failed to remove member {user_id} from group {group_id}: {ex}", exc_info=True)
                    # Marshal error UI update to main thread
                    msg = f"Failed to remove member: {ex}"
                    self._run_task_safe(lambda: self._show_snack(msg, "RED"))
            threading.Thread(target=_bg, daemon=True).start()

        def load_members():
            """Load members list - must be called after dialog is created and opened."""
            try:
                members_list.controls.clear()
                members_list.controls.append(loading)
                # Update page instead of dialog to avoid "Control must be added to page first" error
                self._run_task_safe(lambda: self.app_page.update() if self.app_page else None)
            except Exception as ex:
                logger.error(f"Error initializing members list: {ex}", exc_info=True)

            def _bg():
                try:
                    members = self.intune_service.list_group_members(self.token, group_id)
                    logger.debug(f"Loaded {len(members)} members for group {group_id}")

                    def update_ui():
                        try:
                            members_list.controls.clear()

                            if not members:
                                members_list.controls.append(ft.Text(i18n.get("no_members") or "No members found.", italic=True))
                            else:
                                for m in members:
                                    members_list.controls.append(
                                        ft.ListTile(
                                            leading=ft.Icon(ft.Icons.PERSON),
                                            title=ft.Text(m.get('displayName') or "Unknown"),
                                            subtitle=ft.Text(m.get('userPrincipalName') or m.get('mail') or "No Email"),
                                            trailing=ft.IconButton(
                                                ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                                icon_color="RED",
                                                tooltip=i18n.get("remove_member") or "Remove Member",
                                                on_click=lambda e, uid=m.get('id'): remove_member(uid)
                                            )
                                        )
                                    )
                            # Use page update to ensure everything renders correctly without "not added" errors
                            if self.app_page:
                                self.app_page.update()
                        except Exception as ex:
                            logger.error(f"Error updating members list UI: {ex}", exc_info=True)

                    self._run_task_safe(update_ui)
                except Exception as ex:
                    import logging
                    logging.getLogger(__name__).error(f"Error loading members: {ex}", exc_info=True)
                    def show_error(error=ex):
                        try:
                            if members_list:
                                members_list.controls.clear()
                                error_tmpl = i18n.get("error_loading_members") or "Error loading members: {error}"
                                msg = error_tmpl.format(error=error)
                                members_list.controls.append(ft.Text(msg, color="RED"))
                                if self.app_page:
                                    self.app_page.update()
                        except Exception as ex2:
                            logger.error(f"Error showing error message in members dialog: {ex2}", exc_info=True)
                    self._run_task_safe(show_error)

            threading.Thread(target=_bg, daemon=True).start()

        def show_add_dialog(e):
            """Show nested dialog for adding members."""
            # Nested dialog for searching users
            search_box = ft.TextField(
                label=i18n.get("search_user_hint") or "Search User (Name or Email)",
                autofocus=True,
                on_submit=lambda e: search_users(e)
            )
            results_list = ft.ListView(expand=True, height=200)

            def search_users(e):
                query = search_box.value
                if not query or not query.strip():
                    return

                try:
                    results_list.controls.clear()
                    results_list.controls.append(ft.ProgressBar())
                    add_dlg.update()
                except Exception as ex:
                    logger.error(f"Error updating search UI: {ex}", exc_info=True)
                    return

                def _bg():
                    try:
                        bg_users = self.intune_service.search_users(self.token, query)
                        logger.debug(f"Found {len(bg_users)} users for query: {query}")

                        def update_results():
                            try:
                                results_list.controls.clear()
                                if not bg_users:
                                    results_list.controls.append(ft.Text(i18n.get("no_users_found") or "No users found.", italic=True))
                                else:
                                    for u in bg_users:
                                        results_list.controls.append(
                                            ft.ListTile(
                                                leading=ft.Icon(ft.Icons.PERSON_ADD),
                                                title=ft.Text(u.get('displayName')),
                                                subtitle=ft.Text(u.get('userPrincipalName') or u.get('mail')),
                                                on_click=lambda e, uid=u.get('id'): add_user(uid)
                                            )
                                        )
                                add_dlg.update()
                            except Exception as ex:
                                logger.error(f"Error updating search results UI: {ex}", exc_info=True)

                        self._run_task_safe(update_results)
                    except Exception as ex:
                        logger.error(f"Error searching users: {ex}", exc_info=True)
                        def show_error(error=ex):
                            try:
                                if results_list:
                                    results_list.controls.clear()
                                    error_tmpl = i18n.get("error_search_failed") or "Search failed: {error}"
                                    results_list.controls.append(ft.Text(error_tmpl.format(error=error), color="RED"))
                                    add_dlg.update()
                            except Exception as ex2:
                                logger.error(f"Error showing search error: {ex2}", exc_info=True)
                        self._run_task_safe(show_error)

                threading.Thread(target=_bg, daemon=True).start()

            def add_user(user_id):
                """Add a user to the group."""
                try:
                    self._close_dialog(add_dlg) # Close add dialog
                except Exception as ex:
                    logger.warning(f"Error closing add dialog: {ex}", exc_info=True)

                def _bg():
                    try:
                        self.intune_service.add_group_member(self.token, group_id, user_id)
                        logger.info(f"Added user {user_id} to group {group_id}")
                        # Marshal UI updates to main thread
                        self._run_task_safe(lambda: self._show_snack(i18n.get("member_added") or "Member added successfully", "GREEN"))
                        self._run_task_safe(load_members) # Refresh main list
                    except Exception as ex:
                        logger.error(f"Failed to add member {user_id} to group {group_id}: {ex}", exc_info=True)
                        # Marshal error UI update to main thread
                        msg = f"Failed to add member: {ex}"
                        self._run_task_safe(lambda: self._show_snack(msg, "RED"))
                threading.Thread(target=_bg, daemon=True).start()

            # Create dialog first so it can be referenced in nested functions
            add_dlg = ft.AlertDialog(
                title=ft.Text(i18n.get("dlg_add_member") or "Add Member"),
                content=ft.Column([search_box, results_list], height=300, width=400),
                actions=[ft.TextButton(i18n.get("btn_close") or "Close", on_click=lambda e: self._close_dialog(add_dlg))]
            )

            if not self._open_dialog_safe(add_dlg):
                self._show_snack("Failed to open add member dialog", "RED")

        # Create main dialog FIRST before defining load_members (which references dlg)
        title_tmpl = i18n.get("members_title") or "Members: {group}"
        dlg = ft.AlertDialog(
            title=ft.Text(title_tmpl.format(group=group_name)),
            content=ft.Column([
                ft.Row([
                    ft.Text(i18n.get("current_members") or "Current Members", weight=ft.FontWeight.BOLD, size=16),
                    ft.Container(expand=True),
                    ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.ADD), ft.Text(i18n.get("btn_add_member") or "Add Member")], alignment=ft.MainAxisAlignment.CENTER), on_click=show_add_dialog)
                ]),
                ft.Divider(),
                members_list
            ], height=400, width=500),
            actions=[ft.TextButton(i18n.get("btn_close") or "Close", on_click=lambda e: self._close_dialog(dlg))],
        )

        if not self._open_dialog_safe(dlg):
            self._show_snack("Failed to open members dialog", "RED")
            return
        # Now load members after dialog is opened
        load_members()
