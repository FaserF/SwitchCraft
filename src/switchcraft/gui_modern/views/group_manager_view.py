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
        super().__init__(expand=True)
        self.app_page = page
        self.intune_service = IntuneService()
        self.groups = []
        self.filtered_groups = []
        self.token = None  # Initialize token

        # State
        self.selected_group = None

        # Check for credentials first
        if not self._has_credentials():
            self.controls = [
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.LOCK_RESET_ROUNDED, size=80, color="ORANGE_400"),
                        ft.Text(i18n.get("intune_not_configured") or "Intune is not configured", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                        ft.Text(i18n.get("intune_config_hint") or "Please configure Microsoft Graph API credentials in Settings.", size=16, color="GREY_400", text_align=ft.TextAlign.CENTER),
                        ft.Container(height=20),
                        ft.Button(
                            i18n.get("tab_settings") or "Go to Settings",
                            icon=ft.Icons.SETTINGS,
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

        # self._load_data() moved to did_mount

    def did_mount(self):
        self._load_data()

    def _init_ui(self):
        # Header
        self.search_field = ft.TextField(
            label=i18n.get("search_groups") or "Search Groups",
            width=300,
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_search
        )

        self.refresh_btn = ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self._load_data())
        self.create_btn = ft.Button(i18n.get("btn_create_group") or "Create Group", icon=ft.Icons.ADD, on_click=self._show_create_dialog)

        self.delete_toggle = ft.Switch(label=i18n.get("enable_delete_mode") or "Enable Deletion (Danger Zone)", value=False, on_change=self._toggle_delete_mode)
        self.delete_btn = ft.Button(
            i18n.get("btn_delete_selected") or "Delete Selected",
            icon=ft.Icons.DELETE_FOREVER,
            bgcolor="RED",
            color="WHITE",
            disabled=True,
            on_click=self._confirm_delete
        )

        self.members_btn = ft.Button(
            i18n.get("btn_manage_members") or "Manage Members",
            icon=ft.Icons.PEOPLE,
            disabled=True,
            on_click=self._safe_event_handler(self._show_members_dialog, "Manage Members button")
        )

        header = ft.Row([
            self.search_field,
            self.refresh_btn,
            ft.VerticalDivider(),
            self.create_btn,
            ft.Container(expand=True),
            self.members_btn,
            self.delete_toggle,
            self.delete_btn
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # Groups List (replacing DataTable with clickable ListView)
        self.groups_list = ft.ListView(expand=True, spacing=5)

        self.list_container = ft.Column([self.groups_list], scroll=ft.ScrollMode.AUTO, expand=True)

        # Main Layout
        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text(i18n.get("entra_group_manager_title") or "Entra Group Manager", size=28, weight=ft.FontWeight.BOLD),
                    ft.Text(i18n.get("entra_group_manager_desc") or "Manage your Microsoft Entra ID (Azure AD) groups.", color="GREY"),
                    ft.Divider(),
                    header,
                    ft.Divider(),
                    self.list_container
                ], expand=True, spacing=10),
                padding=20,
                expand=True
            )
        ]

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
                self.token = self.intune_service.authenticate(tenant, client, secret)
                self.groups = self.intune_service.list_groups(self.token)
                self.filtered_groups = self.groups
                # Marshal UI update to main thread
                def update_table():
                    try:
                        self._update_table()
                    except (RuntimeError, AttributeError):
                        # Control not added to page yet (common in tests)
                        logger.debug("Cannot update table: control not added to page")
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
                    except (RuntimeError, AttributeError) as e:
                        logger.debug(f"Control not added to page (RuntimeError/AttributeError): {e}")
                self._run_task_safe(show_error)
            except Exception as e:
                error_str = str(e).lower()
                # Detect permission issues from error message
                if "403" in error_str or "forbidden" in error_str or "insufficient" in error_str:
                    error_msg = i18n.get("graph_permission_error", permissions="Group.Read.All") or "Missing Graph API permissions: Group.Read.All"
                elif "401" in error_str or "unauthorized" in error_str:
                    error_msg = i18n.get("graph_auth_error") or "Authentication failed. Please check your credentials."
                else:
                    logger.error(f"Failed to load groups: {e}")
                    error_msg = f"Error loading groups: {e}"
                # Marshal UI update to main thread
                def show_error():
                    try:
                        self._show_snack(error_msg, "RED")
                    except (RuntimeError, AttributeError) as e:
                        logger.debug(f"Control not added to page (RuntimeError/AttributeError): {e}")
                self._run_task_safe(show_error)
            except BaseException as be:
                # Catch all exceptions including KeyboardInterrupt to prevent unhandled thread exceptions
                logger.exception("Unexpected error in group loading background thread")
                # Marshal UI update to main thread
                def update_ui():
                    try:
                        self.list_container.disabled = False
                        self.update()
                    except (RuntimeError, AttributeError):
                        pass
                self._run_task_safe(update_ui)
            else:
                # Only update UI if no exception occurred - marshal to main thread
                def update_ui():
                    try:
                        self.list_container.disabled = False
                        self.update()
                    except (RuntimeError, AttributeError):
                        pass
                self._run_task_safe(update_ui)

        threading.Thread(target=_bg, daemon=True).start()

    def _update_table(self):
        try:
            self.groups_list.controls.clear()

            if not self.filtered_groups:
                self.groups_list.controls.append(
                    ft.Container(
                        content=ft.Text(i18n.get("no_groups_found") or "No groups found.", italic=True, color="GREY"),
                        padding=20,
                        alignment=ft.Alignment(0, 0)
                    )
                )
            else:
                for g in self.filtered_groups:
                    is_selected = self.selected_group == g or (self.selected_group and self.selected_group.get('id') == g.get('id'))

                    # Create clickable tile for each group
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
                                ft.Text(f"Type: {', '.join(g.get('groupTypes', [])) or 'Security'}", size=10, color="GREY_500"),
                            ], spacing=2, tight=True),
                            trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, color="GREY_400") if is_selected else None,
                        ),
                        bgcolor="BLUE_50" if is_selected else None,
                        border=ft.Border.all(2, "BLUE" if is_selected else "GREY_300"),
                        border_radius=5,
                        padding=5,
                        on_click=lambda e, grp=g: self._on_group_click(grp),
                        data=g  # Store group data in container
                    )
                    self.groups_list.controls.append(tile)

            self.update()
        except (RuntimeError, AttributeError) as e:
            # Control not added to page yet (common in tests)
            logger.debug(f"Cannot update groups list: control not added to page: {e}")

    def _on_search(self, e):
        query = self.search_field.value.lower()
        if not query:
            self.filtered_groups = self.groups
        else:
            self.filtered_groups = [
                g for g in self.groups
                if query in (g.get('displayName') or '').lower() or query in (g.get('description') or '').lower()
            ]
        self._update_table()

    def _on_group_click(self, group):
        """Handle click on a group tile to select/deselect it."""
        # Toggle selection: if same group clicked, deselect; otherwise select new group
        if self.selected_group and self.selected_group.get('id') == group.get('id'):
            self.selected_group = None
        else:
            self.selected_group = group

        # Update UI to reflect selection
        self._update_table()

        # Enable delete only if toggle on and item selected
        self.delete_btn.disabled = not (self.delete_toggle.value and self.selected_group)
        self.members_btn.disabled = not self.selected_group

        # Show feedback
        if self.selected_group:
            self._show_snack(f"Selected: {self.selected_group.get('displayName', '')}", "BLUE")
        else:
            self._show_snack(i18n.get("group_deselected") or "Group deselected", "GREY")

    def _toggle_delete_mode(self, e):
        self.delete_btn.disabled = not (self.delete_toggle.value and self.selected_group)
        self.update()

    def _show_create_dialog(self, e):
        def close_dlg(e):
            self._close_dialog(dlg)

        name_field = ft.TextField(label=i18n.get("group_name") or "Group Name", autofocus=True)
        desc_field = ft.TextField(label=i18n.get("group_desc") or "Description")

        def create(e):
            if not name_field.value:
                return
            if not self.token:
                self._show_snack(i18n.get("not_connected_intune") or "Not connected to Intune", "RED")
                return

            def _bg():
                try:
                    self.intune_service.create_group(self.token, name_field.value, desc_field.value)
                    self._show_snack(f"Group '{name_field.value}' created!", "GREEN")
                    self._close_dialog(dlg)
                    self._load_data()
                except Exception as ex:
                    self._show_snack(f"Creation failed: {ex}", "RED")
                except BaseException:
                    # Catch all exceptions including KeyboardInterrupt to prevent unhandled thread exceptions
                    logger.exception("Unexpected error in group creation background thread")

            threading.Thread(target=_bg, daemon=True).start()

        dlg = ft.AlertDialog(
            title=ft.Text(i18n.get("create_new_group") or "Create New Group"),
            content=ft.Column([name_field, desc_field], height=150),
            actions=[
                ft.TextButton(i18n.get("cancel") or "Cancel", on_click=close_dlg),
                ft.Button(i18n.get("create") or "Create", on_click=create, bgcolor="BLUE", color="WHITE")
            ],
        )
        self.app_page.open(dlg)
        self.app_page.update()

    def _confirm_delete(self, e):
        if not self.selected_group:
            return

        def close_dlg(e):
            self._close_dialog(dlg)

        def delete(e):
            grp_id = self.selected_group['id']
            if not self.token:
                self._show_snack("Not connected to Intune", "RED")
                return
            def _bg():
                try:
                    self.intune_service.delete_group(self.token, grp_id)
                    self._show_snack("Group deleted.", "GREEN")
                    self._close_dialog(dlg)
                    self.selected_group = None
                    self._load_data()
                except Exception as ex:
                    self._show_snack(f"Deletion failed: {ex}", "RED")
            threading.Thread(target=_bg, daemon=True).start()

        dlg = ft.AlertDialog(
            title=ft.Text("Confirm Deletion"),
            content=ft.Text(f"Are you sure you want to delete '{self.selected_group.get('displayName')}'? This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.Button("Delete", on_click=delete, bgcolor="RED", color="WHITE")
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app_page.open(dlg)
        self.app_page.update()



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
        if not self.selected_group or not self.token:
            logger.warning("Cannot show members dialog: no group selected or no token")
            return

        group_name = self.selected_group.get('displayName')
        group_id = self.selected_group.get('id')

        if not group_id:
            logger.error(f"Cannot show members dialog: group has no ID. Group: {self.selected_group}")
            self._show_snack("Error: Selected group has no ID", "RED")
            return

        # Dialog controls
        members_list = ft.ListView(expand=True, spacing=10, height=300)
        loading = ft.ProgressBar(width=None)

        def remove_member(user_id):
            def _bg():
                try:
                    self.intune_service.remove_group_member(self.token, group_id, user_id)
                    self._show_snack(i18n.get("member_removed") or "Member removed", "GREEN")
                    load_members() # Refresh
                except Exception as ex:
                    logger.error(f"Failed to remove member {user_id} from group {group_id}: {ex}", exc_info=True)
                    self._show_snack(f"Failed to remove member: {ex}", "RED")
            threading.Thread(target=_bg, daemon=True).start()

        def load_members():
            """Load members list - must be called after dialog is created and opened."""
            try:
                members_list.controls.clear()
                members_list.controls.append(loading)
                # Use _run_task_safe to ensure dialog is on page before updating
                self._run_task_safe(lambda: dlg.update())
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
                            dlg.update()
                        except Exception as ex:
                            logger.error(f"Error updating members list UI: {ex}", exc_info=True)

                    self._run_task_safe(update_ui)
                except Exception as ex:
                    logger.error(f"Error loading group members: {ex}", exc_info=True)
                    def show_error():
                        try:
                            members_list.controls.clear()
                            error_tmpl = i18n.get("error_loading_members") or "Error loading members: {error}"
                            members_list.controls.append(ft.Text(error_tmpl.format(error=ex), color="RED"))
                            dlg.update()
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
                        def show_error():
                            try:
                                results_list.controls.clear()
                                error_tmpl = i18n.get("error_search_failed") or "Search failed: {error}"
                                results_list.controls.append(ft.Text(error_tmpl.format(error=ex), color="RED"))
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
                        self._show_snack(i18n.get("member_added") or "Member added successfully", "GREEN")
                        load_members() # Refresh main list
                    except Exception as ex:
                        logger.error(f"Failed to add member {user_id} to group {group_id}: {ex}", exc_info=True)
                        self._show_snack(f"Failed to add member: {ex}", "RED")
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
                    ft.Button(i18n.get("btn_add_member") or "Add Member", icon=ft.Icons.ADD, on_click=show_add_dialog)
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
