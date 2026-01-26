import flet as ft
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.nav_constants import NavIndex
import logging
import threading
# Use ft.* directly
from switchcraft.services.exchange_service import ExchangeService
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.gui_modern.utils.view_utils import ViewMixin

logger = logging.getLogger(__name__)


class ExchangeView(ft.Column, ViewMixin):
    """Exchange Online Management View for Mail Flow Statistics and Management."""

    def __init__(self, page: ft.Page):
        super().__init__(expand=True, spacing=0)
        self.app_page = page
        self.exchange_service = ExchangeService()
        self.mail_flow_data = []
        self.token = None
        self._ui_initialized = False

        # Check for credentials first
        if not self._has_credentials():
            self.controls = [
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.EMAIL_OUTLINED, size=80, color="ORANGE_400"),
                        ft.Text(
                            i18n.get("intune_not_configured") or "Exchange is not configured",
                            size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER
                        ),
                        ft.Text(
                            i18n.get("intune_config_hint") or "Please configure Microsoft Graph API credentials in Settings.",
                            size=16, color="GREY_400", text_align=ft.TextAlign.CENTER
                        ),
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

    def _has_credentials(self) -> bool:
        """Check if Graph API credentials are configured."""
        tenant = SwitchCraftConfig.get_value("GraphTenantId")
        client = SwitchCraftConfig.get_value("GraphClientId")
        secret = SwitchCraftConfig.get_secure_value("GraphClientSecret")
        return bool(tenant and client and secret)

    def _go_to_settings(self, e):
        """Navigate to settings view."""
        if hasattr(self.app_page, 'switchcraft_app') and self.app_page.switchcraft_app:
            self.app_page.switchcraft_app.goto_tab(NavIndex.SETTINGS)

    def _init_ui(self):
        """Initialize the main UI components."""
        self._ui_initialized = True

        # Header
        self.header = ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(
                        i18n.get("exchange_title") or "Exchange Online",
                        size=28, weight=ft.FontWeight.BOLD
                    ),
                    ft.Text(
                        i18n.get("exchange_subtitle") or "Mailbox management and flow monitoring",
                        size=14, color="GREY_400"
                    )
                ], spacing=5, expand=True),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.Padding(left=20, right=20, top=20, bottom=10)
        )

        # Tab Content Containers
        self.mail_flow_content = self._build_mail_flow_tab()
        self.oof_content = self._build_oof_tab()
        self.delegation_content = self._build_delegation_tab()

        # Tab Content display
        self.tab_body = ft.Container(content=self.mail_flow_content, expand=True)

        # Tabs for different functions
        self.tabs = ft.Tabs(
            content=self.tab_body,
            length=3,
            selected_index=0,
            animation_duration=300,
            expand=True,
            on_change=self._on_tab_change
        )
        self.tabs.tabs = [
                ft.Tab(label=i18n.get("ex_tab_mail_flow") or "Mail Flow", icon=ft.Icons.SEARCH),
                ft.Tab(label=i18n.get("ex_tab_oof") or "Out of Office", icon=ft.Icons.OUTDOOR_GRILL),
                ft.Tab(label=i18n.get("ex_tab_delegation") or "Delegation", icon=ft.Icons.PEOPLE_OUTLINE),
            ]

        self.tab_container = ft.Container(
            content=self.mail_flow_content,
            expand=True,
            padding=20
        )

        # Build layout
        self.controls = [
            self.header,
            ft.Divider(height=1),
            self.tabs,
            self.tab_container
        ]

    def _on_tab_change(self, e):
        """Switch content based on selected tab."""
        idx = self.tabs.selected_index
        if idx == 0:
            self.tab_container.content = self.mail_flow_content
        elif idx == 1:
            self.tab_container.content = self.oof_content
            self._load_oof_data()
        elif idx == 2:
            self.tab_container.content = self.delegation_content
            self._load_delegation_data()
        self.tab_container.update()

    # --- Mail Flow Tab ---
    def _build_mail_flow_tab(self):
        self.mf_mailbox = ft.TextField(
            label=i18n.get("ex_mailbox_lbl") or "Mailbox (SMTP)",
            hint_text="user@domain.com",
            expand=True
        )
        self.mf_results = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True, spacing=5)

        # Dashboard Stats Area
        self.stats_row = ft.Row(spacing=20, alignment=ft.MainAxisAlignment.CENTER)
        self.mail_chart = ft.Column(spacing=2, expand=True)

        # Range Toggle
        self.mf_range_dd = ft.Dropdown(
            label="Range",
            value="7",
            options=[
                ft.dropdown.Option("7", "Last 7 Days"),
                ft.dropdown.Option("30", "Last 30 Days"),
            ],
            width=150
        )
        self.mf_range_dd.on_change = self._on_date_range_change

        return ft.Column([
            ft.Row([
                ft.Text(i18n.get("ex_dash_filters") or "Dashboard Filters", weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.IconButton(ft.Icons.REFRESH, on_click=self._refresh_data, tooltip=i18n.get("refresh") or "Refresh"),
            ]),
            ft.Row([
                self.mf_mailbox,
                self.mf_range_dd,
                ft.IconButton(ft.Icons.SEARCH, on_click=self._run_mail_search, tooltip=i18n.get("ex_btn_search"))
            ], spacing=10),
            ft.Divider(),
            ft.Container(
                content=ft.Column([
                    ft.Text(i18n.get("ex_mail_traffic") or "Mail Traffic Statistics", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                    self.stats_row,
                    ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                    self.mail_chart
                ]),
                padding=20,
                border_radius=10,
                bgcolor="SURFACE_VARIANT"
            ),
            ft.Divider(height=20, color="TRANSPARENT"),
            ft.Text(i18n.get("ex_msg_trace_title") or "Recent Messages", weight=ft.FontWeight.BOLD),
            ft.Container(
                content=self.mf_results,
                bgcolor="SURFACE_VARIANT",
                border_radius=10,
                padding=10,
                expand=True
            )
        ], expand=True)

    def _run_mail_search(self, e):
        mailbox = self.mf_mailbox.value.strip()
        if not mailbox:
            self._show_error("Please enter a mailbox SMTP address.")
            return

        self.mf_results.controls = [ft.ProgressRing()]
        self.mf_results.update()

        def _load():
            try:
                token = self._get_token()
                # Empty query to simulate general search
                results = self.exchange_service.search_messages(token, mailbox, "")
                self._run_task_with_fallback(lambda: self._display_mail_results(results))
            except Exception as ex:
                self._run_task_with_fallback(lambda error=ex: self._show_error(str(error)))

        threading.Thread(target=_load, daemon=True).start()

    def _display_mail_results(self, results):
        self.mf_results.controls = []
        if not results:
            self.mf_results.controls.append(ft.Text(i18n.get("ex_msg_no_results") or "No messages found.", italic=True))
        else:
            for msg in results:
                sender = msg.get("from", {}).get("emailAddress", {}).get("address", "Unknown")
                subject = msg.get("subject", "(No Subject)")
                received = msg.get("receivedDateTime", "")[:16].replace("T", " ")
                self.mf_results.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.EMAIL),
                        title=ft.Text(subject, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        subtitle=ft.Text(f"From: {sender} | {received}"),
                        dense=True
                    )
                )
        self.mf_results.update()

    # --- Out of Office Tab ---
    def _build_oof_tab(self):
        self.oof_mailbox = ft.TextField(label=i18n.get("ex_mailbox_lbl") or "Mailbox", hint_text="user@domain.com")
        self.oof_status = ft.Dropdown(
            label=i18n.get("ex_oof_status") or "Status",
            options=[
                ft.dropdown.Option("disabled", i18n.get("ex_oof_disabled") or "Disabled"),
                ft.dropdown.Option("alwaysEnabled", i18n.get("ex_oof_enabled") or "Enabled"),
                ft.dropdown.Option("scheduled", "Scheduled"),
            ],
            value="disabled"
        )
        self.oof_internal = ft.TextField(label=i18n.get("ex_oof_internal") or "Internal Reply", multiline=True, min_lines=3)
        self.oof_external = ft.TextField(label=i18n.get("ex_oof_external") or "External Reply", multiline=True, min_lines=3)

        return ft.Column([
            ft.Row([
                self.oof_mailbox,
                ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self._load_oof_data())
            ]),
            ft.Divider(),
            self.oof_status,
            self.oof_internal,
            self.oof_external,
            ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.SAVE), ft.Text(i18n.get("ex_btn_save_oof") or "Save")], alignment=ft.MainAxisAlignment.CENTER), on_click=self._save_oof_data)
        ], scroll=ft.ScrollMode.AUTO, expand=True)

    def _load_oof_data(self):
        mailbox = self.oof_mailbox.value.strip()
        if not mailbox: return

        def _load():
            try:
                token = self._get_token()
                data = self.exchange_service.get_oof_settings(token, mailbox)
                self._run_task_with_fallback(lambda: self._apply_oof_data(data))
            except Exception:
                pass

        threading.Thread(target=_load, daemon=True).start()

    def _apply_oof_data(self, data):
        self.oof_status.value = data.get("status", "disabled")
        self.oof_internal.value = data.get("internalReplyMessage", "")
        self.oof_external.value = data.get("externalReplyMessage", "")
        self.update()

    def _save_oof_data(self, e):
        mailbox = self.oof_mailbox.value.strip()
        if not mailbox: return
        oof_data = {
            "status": self.oof_status.value,
            "internalReplyMessage": self.oof_internal.value,
            "externalReplyMessage": self.oof_external.value
        }

        def _save():
            try:
                token = self._get_token()
                if self.exchange_service.set_oof_settings(token, mailbox, oof_data):
                    self._run_task_with_fallback(lambda: self._show_snack("OOF settings updated!", "GREEN"))
            except Exception as ex:
                self._run_task_with_fallback(lambda error=ex: self._show_error(str(error)))

        threading.Thread(target=_save, daemon=True).start()

    # --- Delegation Tab ---
    def _build_delegation_tab(self):
        self.del_mailbox = ft.TextField(label=i18n.get("ex_mailbox_lbl") or "Mailbox", hint_text="user@domain.com")
        self.del_list = ft.Column([], spacing=5)

        return ft.Column([
            ft.Row([
                self.del_mailbox,
                ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self._load_delegation_data())
            ]),
            ft.Divider(),
            ft.Text(i18n.get("ex_delegates_title") or "Delegates", weight=ft.FontWeight.BOLD),
            ft.Container(
                content=self.del_list,
                bgcolor="SURFACE_VARIANT",
                border_radius=10,
                padding=10
            ),
            ft.FilledButton(content=ft.Row([ft.Icon(ft.Icons.ADD), ft.Text(i18n.get("ex_add_delegate") or "Add Delegate")], alignment=ft.MainAxisAlignment.CENTER), disabled=True)
        ], scroll=ft.ScrollMode.AUTO, expand=True)

    def _load_delegation_data(self):
        mailbox = self.del_mailbox.value.strip()
        if not mailbox: return

        def _load():
            try:
                token = self._get_token()
                delegates = self.exchange_service.get_delegates(token, mailbox)
                self._run_task_with_fallback(lambda: self._display_delegates(delegates))
            except Exception:
                pass

        threading.Thread(target=_load, daemon=True).start()

    def _display_delegates(self, delegates):
        self.del_list.controls = []
        if not delegates:
            self.del_list.controls.append(ft.Text("No delegates found or permissions insufficient.", italic=True))
        else:
            for d in delegates:
                name = d.get("displayName", "Unknown")
                email = d.get("emailAddress", {}).get("address", "")
                self.del_list.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.PERSON),
                        title=ft.Text(name),
                        subtitle=ft.Text(email),
                        trailing=ft.IconButton(ft.Icons.DELETE, icon_color="RED", disabled=True)
                    )
                )
        self.del_list.update()

    def _get_token(self):
        tenant = SwitchCraftConfig.get_value("GraphTenantId")
        client = SwitchCraftConfig.get_value("GraphClientId")
        secret = SwitchCraftConfig.get_secure_value("GraphClientSecret")
        return self.exchange_service.authenticate(tenant, client, secret)

    def did_mount(self):
        """Called when the view is mounted."""
        self._refresh_data(None)

    def _on_date_range_change(self, e):
        self._refresh_data(e)

    def _refresh_data(self, e):
        """Refresh all dashboard data."""
        self._load_data_async()

    def _load_data_async(self):
        """Load data from service in background."""
        def _bg():
            try:
                # Fetch traffic stats
                days = 7
                if hasattr(self, 'mf_range_dd') and self.mf_range_dd.value:
                    days = int(self.mf_range_dd.value)

                stats = self.exchange_service.get_mail_traffic_stats(days=days)
                self.mail_flow_data = stats

                self._run_task_with_fallback(self._update_ui)
            except Exception as ex:
                logger.error(f"Failed to load exchange data: {ex}")
                self._run_task_with_fallback(lambda error=ex: self._show_error(str(error)))

        threading.Thread(target=_bg, daemon=True).start()

    def _update_ui(self):
        """Update all UI components from loaded data."""
        if not self._ui_initialized: return
        self._update_stats()
        self._update_chart()
        try:
            if self.page:
                self.update()
        except RuntimeError:
            pass


    def _update_stats(self):
        """Calculate and display statistics summary."""
        if not self.mail_flow_data: return

        total_sent = sum(d["sent"] for d in self.mail_flow_data)
        total_recv = sum(d["received"] for d in self.mail_flow_data)
        total_blocked = sum(d["blocked"] for d in self.mail_flow_data)

        self.stats_row.controls = [
            self._stat_card("Sent", str(total_sent), ft.Icons.SEND, "BLUE"),
            self._stat_card("Recv", str(total_recv), ft.Icons.MOVE_TO_INBOX, "GREEN"),
            self._stat_card("Blocked", str(total_blocked), ft.Icons.BLOCK, "RED"),
        ]

    def _stat_card(self, label, value, icon, color):
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, color=color, size=30),
                ft.Text(value, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(label, size=12, color="GREY_400"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            bgcolor="SURFACE_CONTAINER_LOW",
            border_radius=10,
            width=120
        )

    def _update_chart(self):
        """Draw a custom bar chart using simple containers."""
        if not self.mail_flow_data: return

        self.mail_chart.controls = []
        max_val = max(max(d["sent"], d["received"]) for d in self.mail_flow_data) or 1

        for d in self.mail_flow_data:
            sent_w = (d["sent"] / max_val) * 200
            recv_w = (d["received"] / max_val) * 200

            self.mail_chart.controls.append(
                ft.Row([
                    ft.Text(d["date"][-5:], size=10, width=40),
                    ft.Container(bgcolor="BLUE", width=sent_w, height=8, border_radius=4, tooltip=f"Sent: {d['sent']}"),
                    ft.Container(bgcolor="GREEN", width=recv_w, height=8, border_radius=4, tooltip=f"Received: {d['received']}"),
                ], spacing=5)
            )

    def _show_error(self, message: str):
        """Show error message."""
        self._show_snack(f"Exchange Error: {message}", "RED")
