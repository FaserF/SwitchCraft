import flet as ft
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.nav_constants import NavIndex
import logging
import threading
from flet_charts import BarChart, BarChartGroup, BarChartRod, ChartAxisLabel, ChartAxis, ChartGridLines
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

    def _has_credentials(self) -> bool:
        """Check if Graph API credentials are configured."""
        tenant = SwitchCraftConfig.get_value("entra_tenant_id")
        client = SwitchCraftConfig.get_value("entra_client_id")
        secret = SwitchCraftConfig.get_secure_value("entra_client_secret")
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
                        i18n.get("exchange_subtitle") or "Mail flow statistics and management",
                        size=14, color="GREY_400"
                    )
                ], spacing=5, expand=True),
                ft.Row([
                    ft.Button(
                        i18n.get("btn_refresh") or "Refresh",
                        icon=ft.Icons.REFRESH,
                        on_click=self._refresh_data
                    )
                ], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.Padding(left=20, right=20, top=20, bottom=10)
        )

        # Date range selector
        self.days_dropdown = ft.Dropdown(
            label=i18n.get("date_range") or "Date Range",
            value="7",
            options=[
                ft.dropdown.Option("1", "Last 24 Hours"),
                ft.dropdown.Option("7", "Last 7 Days"),
                ft.dropdown.Option("14", "Last 14 Days"),
                ft.dropdown.Option("30", "Last 30 Days"),
            ],
            width=200,
        )
        self.days_dropdown.on_change = self._on_date_range_change

        # Stats row
        self.stats_row = ft.Row([], alignment=ft.MainAxisAlignment.SPACE_EVENLY, wrap=True)

        # Mail flow chart placeholder - will be updated with real data
        self.mail_chart = ft.Container(
            content=ft.Column([
                ft.Text(i18n.get("mail_flow_chart") or "Mail Flow Chart", weight=ft.FontWeight.BOLD, size=18),
                ft.Container(height=10),
                ft.Text(i18n.get("loading") or "Loading...", color="GREY_500")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="SURFACE_VARIANT",
            border_radius=10,
            padding=20,
            expand=True,
            height=300
        )

        # Recent messages list
        self.messages_list = ft.Column([], scroll=ft.ScrollMode.AUTO, expand=True, spacing=5)

        # Build layout
        self.controls = [
            self.header,
            ft.Divider(height=1),
            ft.Container(
                content=ft.Column([
                    # Controls row
                    ft.Row([
                        self.days_dropdown,
                    ], alignment=ft.MainAxisAlignment.START),
                    ft.Container(height=20),
                    # Stats
                    self.stats_row,
                    ft.Container(height=20),
                    # Chart
                    self.mail_chart,
                    ft.Container(height=20),
                    # Recent messages
                    ft.Text(i18n.get("recent_messages") or "Recent Email Activity", weight=ft.FontWeight.BOLD, size=18),
                    ft.Container(height=10),
                    ft.Container(
                        content=self.messages_list,
                        bgcolor="SURFACE_VARIANT",
                        border_radius=10,
                        padding=15,
                        expand=True,
                        height=250
                    )
                ], spacing=0, expand=True),
                padding=20,
                expand=True
            )
        ]

    def did_mount(self):
        """Called when the view is mounted."""
        logger.info("ExchangeView did_mount called")
        if not getattr(self, '_ui_initialized', False):
            logger.warning("ExchangeView did_mount called but UI not initialized")
            return
        self._load_data_async()

    def _on_date_range_change(self, e):
        """Handle date range dropdown change."""
        self._load_data_async()

    def _refresh_data(self, e):
        """Refresh mail flow data."""
        self._load_data_async()

    def _load_data_async(self):
        """Load mail flow data in background thread."""
        def _load():
            try:
                days = int(self.days_dropdown.value) if hasattr(self, 'days_dropdown') else 7
                logger.info(f"Loading Exchange mail flow data for last {days} days...")

                # Get mail flow stats from Exchange service
                data = self.exchange_service.get_mail_traffic_stats(days=days)

                if data:
                    self.mail_flow_data = data
                    logger.info(f"Loaded {len(data)} days of mail flow data")
                else:
                    self.mail_flow_data = []
                    logger.warning("No mail flow data returned")

                # Update UI on main thread
                self._run_task_with_fallback(self._update_ui)

            except Exception as ex:
                logger.exception(f"Error loading Exchange data: {ex}")
                self._run_task_with_fallback(lambda: self._show_error(str(ex)))

        thread = threading.Thread(target=_load, daemon=True)
        thread.start()

    def _update_ui(self):
        """Update UI with loaded data."""
        try:
            self._update_stats()
            self._update_chart()
            self.update()
        except Exception as ex:
            logger.exception(f"Error updating Exchange UI: {ex}")

    def _update_stats(self):
        """Update statistics cards."""
        total_sent = sum(d.get("sent", 0) for d in self.mail_flow_data)
        total_received = sum(d.get("received", 0) for d in self.mail_flow_data)
        total_blocked = sum(d.get("blocked", 0) for d in self.mail_flow_data)
        avg_daily = (total_sent + total_received) // max(len(self.mail_flow_data), 1)

        self.stats_row.controls = [
            self._stat_card("Sent", str(total_sent), ft.Icons.SEND, "BLUE"),
            self._stat_card("Received", str(total_received), ft.Icons.INBOX, "GREEN"),
            self._stat_card("Blocked", str(total_blocked), ft.Icons.BLOCK, "RED"),
            self._stat_card("Avg/Day", str(avg_daily), ft.Icons.ANALYTICS, "PURPLE"),
        ]

    def _stat_card(self, label: str, value: str, icon, color: str) -> ft.Container:
        """Create a statistics card."""
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=32, color=color),
                ft.Text(value, size=28, weight=ft.FontWeight.BOLD),
                ft.Text(label, size=12, color="GREY_500")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            bgcolor="SURFACE_VARIANT",
            border_radius=10,
            padding=20,
            width=150
        )

    def _update_chart(self):
        """Update mail flow chart with data."""
        if not self.mail_flow_data:
            self.mail_chart.content = ft.Column([
                ft.Icon(ft.Icons.ANALYTICS_OUTLINED, size=60, color="GREY_400"),
                ft.Text(
                    i18n.get("no_data") or "No mail flow data available",
                    color="GREY_500", text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    i18n.get("exchange_connect_hint") or "Connect to Exchange Online to view statistics",
                    size=12, color="GREY_400", text_align=ft.TextAlign.CENTER
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)
            return

        # Build bar groups for chart
        bar_groups = []
        labels = []

        for i, data_point in enumerate(self.mail_flow_data):
            bar_groups.append(
                BarChartGroup(
                    x=i,
                    rods=[
                        BarChartRod(
                            from_y=0,
                            to_y=data_point.get("sent", 0),
                            width=12,
                            color=ft.Colors.BLUE,
                            tooltip=f"Sent: {data_point.get('sent', 0)}",
                            border_radius=2
                        ),
                        BarChartRod(
                            from_y=0,
                            to_y=data_point.get("received", 0),
                            width=12,
                            color=ft.Colors.GREEN,
                            tooltip=f"Received: {data_point.get('received', 0)}",
                            border_radius=2
                        ),
                    ]
                )
            )

            # Format date label
            try:
                d_str = datetime.strptime(data_point["date"], "%Y-%m-%d").strftime("%d.%m")
            except Exception:
                d_str = str(data_point.get("date", ""))
            labels.append(ChartAxisLabel(value=i, label=ft.Text(d_str, size=10)))

        # Create bar chart
        max_val = max(
            max(d.get("sent", 0), d.get("received", 0))
            for d in self.mail_flow_data
        ) if self.mail_flow_data else 100

        # Assuming flet_charts uses 'groups' instead of 'bar_groups' if bar_groups was invalid
        # Or maybe it expects positional? No.
        # Let's try 'bar_groups' again BUT with flet_charts import restored, check if Error changes.
        # Actually in Step 1050 (flet_charts imported), error was 'unexpected keyword argument bar_groups'.
        # So it is definitely NOT bar_groups.
        # Most likely 'groups'? Or 'items'?
        # Trying 'bar_groups' -> 'groups'
        chart = BarChart(
            groups=bar_groups,

            border=ft.Border.all(1, ft.Colors.GREY_300),
            left_axis=ChartAxis(label_size=40, title=ft.Text("Messages")),
            bottom_axis=ChartAxis(labels=labels, label_size=32),
            horizontal_grid_lines=ChartGridLines(color=ft.Colors.GREY_200, width=1, dash_pattern=[3, 3]),
            # tooltip_bgcolor=ft.Colors.with_opacity(0.8, ft.Colors.BLACK), # Not supported in flet_charts?
            max_y=int(max_val * 1.2),
            interactive=True,
            expand=True,
            height=250
        )

        self.mail_chart.content = ft.Column([
            ft.Row([
                ft.Text(i18n.get("mail_flow_chart") or "Mail Flow Chart", weight=ft.FontWeight.BOLD, size=18),
                ft.Row([
                    ft.Container(width=12, height=12, bgcolor="BLUE", border_radius=2),
                    ft.Text("Sent", size=12),
                    ft.Container(width=10),
                    ft.Container(width=12, height=12, bgcolor="GREEN", border_radius=2),
                    ft.Text("Received", size=12)
                ])
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=10),
            chart
        ])

    def _show_error(self, message: str):
        """Show error message."""
        self._show_snack(f"Exchange Error: {message}", "RED")
