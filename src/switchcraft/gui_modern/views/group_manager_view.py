import flet as ft
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.nav_constants import NavIndex
import logging
import threading
import requests
from switchcraft.services.intune_service import IntuneService
from switchcraft.utils.config import SwitchCraftConfig

logger = logging.getLogger(__name__)

class GroupManagerView(ft.Column):
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

        header = ft.Row([
            self.search_field,
            self.refresh_btn,
            ft.VerticalDivider(),
            self.create_btn,
            ft.Container(expand=True),
            self.delete_toggle,
            self.delete_btn
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # Datatable
        self.dt = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Name")),
                ft.DataColumn(ft.Text("Description")),
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Type")),
            ],
            rows=[],
            border=ft.border.all(1, "GREY_400"),
            vertical_lines=ft.border.BorderSide(1, "GREY_400"),
            horizontal_lines=ft.border.BorderSide(1, "GREY_400"),
            heading_row_color="BLACK12",
        )

        self.list_container = ft.Column([self.dt], scroll=ft.ScrollMode.AUTO, expand=True)

        # Main Layout
        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text("Entra Group Manager", size=28, weight=ft.FontWeight.BOLD),
                    ft.Text("Manage your Microsoft Entra ID (Azure AD) groups.", color="GREY"),
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
                self._update_table()
            except requests.exceptions.HTTPError as e:
                # Handle specific permission error (403)
                logger.error(f"Permission denied loading groups: {e}")
                missing_perms = str(e) if str(e) else "Group.Read.All, Group.ReadWrite.All"
                error_msg = i18n.get("graph_permission_error", permissions=missing_perms) or f"Missing Graph API permissions: {missing_perms}"
                self._show_snack(error_msg, "RED")
            except requests.exceptions.ConnectionError as e:
                # Handle authentication failure
                logger.error(f"Authentication failed: {e}")
                error_msg = i18n.get("graph_auth_error") or "Authentication failed. Please check your credentials."
                self._show_snack(error_msg, "RED")
            except Exception as e:
                error_str = str(e).lower()
                # Detect permission issues from error message
                if "403" in error_str or "forbidden" in error_str or "insufficient" in error_str:
                    error_msg = i18n.get("graph_permission_error", permissions="Group.Read.All") or "Missing Graph API permissions: Group.Read.All"
                    self._show_snack(error_msg, "RED")
                elif "401" in error_str or "unauthorized" in error_str:
                    error_msg = i18n.get("graph_auth_error") or "Authentication failed. Please check your credentials."
                    self._show_snack(error_msg, "RED")
                else:
                    logger.error(f"Failed to load groups: {e}")
                    self._show_snack(f"Error loading groups: {e}", "RED")
            finally:
                self.list_container.disabled = False
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _update_table(self):
        self.dt.rows.clear()
        for g in self.filtered_groups:
             self.dt.rows.append(
                 ft.DataRow(
                     cells=[
                         ft.DataCell(ft.Text(g.get('displayName', ''))),
                         ft.DataCell(ft.Text(g.get('description', ''))),
                         ft.DataCell(ft.Text(g.get('id', ''))),
                         ft.DataCell(ft.Text(", ".join(g.get('groupTypes', [])) or "Security")),
                     ],
                     on_select_changed=lambda e, grp=g: self._on_select(e.control.selected, grp),
                     selected=self.selected_group == g
                 )
             )
        self.update()

    def _on_search(self, e):
        query = self.search_field.value.lower()
        if not query:
            self.filtered_groups = self.groups
        else:
            self.filtered_groups = [
                g for g in self.groups
                if query in g.get('displayName', '').lower() or query in g.get('description', '').lower()
            ]
        self._update_table()

    def _on_select(self, selected, group):
        if selected:
            self.selected_group = group
        else:
            self.selected_group = None

        # Enable delete only if toggle on and item selected
        self.delete_btn.disabled = not (self.delete_toggle.value and self.selected_group)
        self.update()

    def _toggle_delete_mode(self, e):
        self.delete_btn.disabled = not (self.delete_toggle.value and self.selected_group)
        self.update()

    def _show_create_dialog(self, e):
        def close_dlg(e):
            self.app_page.close_dialog()

        name_field = ft.TextField(label="Group Name", autofocus=True)
        desc_field = ft.TextField(label="Description")

        def create(e):
            if not name_field.value:
                return
            if not self.token:
                self._show_snack("Not connected to Intune", "RED")
                return

            def _bg():
                try:
                    self.intune_service.create_group(self.token, name_field.value, desc_field.value)
                    self._show_snack(f"Group '{name_field.value}' created!", "GREEN")
                    self.app_page.close_dialog()
                    self._load_data()
                except Exception as ex:
                    self._show_snack(f"Creation failed: {ex}", "RED")

            threading.Thread(target=_bg, daemon=True).start()

        dlg = ft.AlertDialog(
            title=ft.Text("Create New Group"),
            content=ft.Column([name_field, desc_field], height=150),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.Button("Create", on_click=create, bgcolor="BLUE", color="WHITE")
            ],
        )
        self.app_page.open(dlg)
        self.app_page.update()

    def _confirm_delete(self, e):
        if not self.selected_group:
            return

        def close_dlg(e):
            self.app_page.close_dialog()

        def delete(e):
            grp_id = self.selected_group['id']
            if not self.token:
                self._show_snack("Not connected to Intune", "RED")
                return
            def _bg():
                try:
                    self.intune_service.delete_group(self.token, grp_id)
                    self._show_snack("Group deleted.", "GREEN")
                    self.app_page.close_dialog()
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

    def _show_snack(self, msg, color="GREEN"):
        try:
            self.app_page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.app_page.snack_bar.open = True
            self.app_page.update()
        except Exception:
            pass

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
