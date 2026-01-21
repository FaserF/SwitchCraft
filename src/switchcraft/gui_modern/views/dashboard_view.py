import flet as ft
from switchcraft.services.history_service import HistoryService
from switchcraft.utils.i18n import i18n
from collections import defaultdict
from datetime import datetime, timedelta
from switchcraft.services.exchange_service import ExchangeService

class DashboardView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, spacing=15)
        self.app_page = page
        self.history_service = HistoryService()
        self.exchange_service = ExchangeService()

        # Initial State (Empty)
        self.stats = {
            "analyzed": 0,
            "packaged": 0,
            "deployed": 0,
            "errors": 0
        }
        self.chart_data = []
        self.mail_flow_data = [] # New data for mail flow
        self.recent_items = []

        # Containers for dynamic updates
        self.stats_row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_EVENLY, wrap=True)
        # Initialize containers with placeholder content
        self.chart_container = ft.Container(
            content=ft.Column([
                ft.Text(i18n.get("chart_activity_title") or "Activity (Last 5 Days)", weight=ft.FontWeight.BOLD, size=18),
                ft.Container(height=20),
                ft.Row([], alignment=ft.MainAxisAlignment.SPACE_EVENLY, vertical_alignment=ft.CrossAxisAlignment.END),
            ]),
            bgcolor="SURFACE_VARIANT",
            border_radius=10,
            padding=20,
            expand=1
        )
        self.recent_container = ft.Container(
            content=ft.Column([
                ft.Text(i18n.get("recent_actions") or "Recent Actions", weight=ft.FontWeight.BOLD, size=18),
                ft.Container(height=10),
                ft.Column([], spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
            ], expand=True),
            bgcolor="SURFACE_VARIANT",
            border_radius=10,
            padding=20,
            width=350
        )

        # New Exchange Mail Flow Container
        self.mail_flow_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Exchange Online Mail Flow", weight=ft.FontWeight.BOLD, size=18),
                    ft.ElevatedButton("Start Mail Flow", icon=ft.Icons.SEND, on_click=self._start_mail_flow)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Container(height=20),
                ft.BarChart(
                   bar_groups=[],
                   border=ft.border.all(1, ft.colors.GREY_400),
                   left_axis=ft.ChartAxis(labels_size=40, title=ft.Text("Items")),
                   bottom_axis=ft.ChartAxis(labels=[ft.ChartAxisLabel(value=0, label=ft.Text("Day"))]),
                   horizontal_grid_lines=ft.ChartGridLines(color=ft.colors.GREY_300, width=1, dash_pattern=[3, 3]),
                   tooltip_bgcolor=ft.colors.with_opacity(0.8, ft.colors.GREY_900),
                   max_y=600,
                   interactive=True,
                   expand=True,
                   height=250
                )
            ]),
            bgcolor="SURFACE_VARIANT",
            border_radius=10,
            padding=20,
            expand=1
        )

        # Build initial content - simplified layout
        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text(i18n.get("dashboard_overview_title") or "Overview", size=28, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    self.stats_row,
                    ft.Container(height=20),
                    ft.Row([
                        self.chart_container,
                        self.mail_flow_container
                    ], spacing=20, wrap=False, expand=True),
                    ft.Container(height=20),
                    ft.Row([
                        self.recent_container
                    ], spacing=20, wrap=False, expand=True)
                ], spacing=15, expand=True),
                padding=20,
                expand=True
            )
        ]

        # Load data immediately instead of waiting for did_mount
        self._load_data()

    def did_mount(self):
        # Also load data on mount in case it wasn't loaded yet
        if not self.stats_row.controls:
            self._load_data()

    def _load_data(self):
        history = self.history_service.get_history()

        # Calculate Stats
        self.stats["analyzed"] = len(history)
        self.stats["packaged"] = sum(1 for h in history if h.get("status") == "Packaged") # hypothetical status
        self.stats["deployed"] = sum(1 for h in history if h.get("status") == "Deployed")
        self.stats["errors"] = sum(1 for h in history if h.get("status") == "Error")

        # Calculate Recent (Last 5)
        self.recent_items = history[:5]

        # Calculate Chart (Last 5 days)
        today = datetime.now().date()
        date_counts = defaultdict(int)
        for h in history:
            ts = h.get("timestamp")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts).date()
                    if (today - dt).days < 5:
                        date_counts[dt] += 1
                except ValueError as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to parse date '{ts}': {e}")

        self.chart_data = []
        for i in range(4, -1, -1):
            d = today - timedelta(days=i)
            self.chart_data.append((d.strftime("%a"), date_counts[d]))

        # Load Mail Flow Data (Mock for now or from service)
        # Using a valid token is required for real data. Passing None for mock return.
        try:
            self.mail_flow_data = self.exchange_service.get_mail_traffic_stats(token=None)
        except Exception:
             self.mail_flow_data = []

        self._refresh_ui()

    def _refresh_ui(self):
        # Stats
        """
        Refreshes the dashboard view's visual components to reflect the current stats, chart data, and recent activity.

        Rebuilds:
        - The stats row from self.stats using localized labels with sensible fallbacks.
        - The activity chart in self.chart_container from self.chart_data (produces a vertical bar per day).
        - The recent activity list in self.recent_container from self.recent_items; timestamps are formatted as "YYYY-MM-DD HH:MM" when ISO parsing succeeds, otherwise the raw timestamp is shown. Status values map to icons with fallbacks.

        After rebuilding, the method attempts to call update() on the stats row, chart container, recent container, and the view itself; any exceptions raised during these update attempts are caught and ignored.
        """
        self.stats_row.controls = [
            self._stat_card(i18n.get("stat_analyzed") or "Analyzed", str(self.stats["analyzed"]), ft.Icons.ANALYTICS, "BLUE"),
            self._stat_card(i18n.get("stat_packaged") or "Packaged", str(self.stats["packaged"]), ft.Icons.INVENTORY_2, "ORANGE"),
            self._stat_card(i18n.get("stat_deployed") or "Deployed", str(self.stats["deployed"]), ft.Icons.ROCKET_LAUNCH, "GREEN"),
            self._stat_card(i18n.get("stat_errors") or "Errors", str(self.stats["errors"]), ft.Icons.ERROR_OUTLINE, "RED"),
        ]

        # Force update of stats row
        if hasattr(self, 'stats_row'):
            try:
                self.stats_row.update()
            except Exception:
                pass

        # Chart
        bars = []
        max_val = max([v for _, v in self.chart_data], default=1)  # Default to 1 to avoid division by zero

        for day, val in self.chart_data:
            height_pct = (val / max_val) * 150 if max_val > 0 else 2 # min height 2
            color = "BLUE_400" if val > 0 else "GREY_800"
            bars.append(
                ft.Column([
                    ft.Container(
                        bgcolor=color,
                        width=30,
                        height=height_pct,
                        border_radius=ft.BorderRadius.only(top_left=4, top_right=4),
                        tooltip=f"{day}: {val}"
                    ),
                    ft.Text(day, size=10, color="ON_SURFACE_VARIANT")
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)
            )

        # Update chart container content - always rebuild to ensure proper rendering
        chart_content = ft.Column([
            ft.Text(i18n.get("chart_activity_title") or "Activity (Last 5 Days)", weight=ft.FontWeight.BOLD, size=18),
            ft.Container(height=20),
            ft.Row(bars, alignment=ft.MainAxisAlignment.SPACE_EVENLY, vertical_alignment=ft.CrossAxisAlignment.END, height=200),
        ], expand=True)
        self.chart_container.content = chart_content

        # Recent
        recent_list = []
        if not self.recent_items:
            recent_list.append(ft.Text(i18n.get("no_recent_activity") or "No recent activity.", color="ON_SURFACE_VARIANT", italic=True))
        else:
            for item in self.recent_items:
                # Format time
                ts = item.get("timestamp", "")
                try:
                    dt = datetime.fromisoformat(ts)
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    time_str = ts

                title = item.get("filename") or item.get("product") or i18n.get("unknown") or "Unknown"
                status = item.get("status", i18n.get("status_analyzed") or "Analyzed")
                icon = ft.Icons.ANALYTICS
                if status == "Packaged":
                    icon = ft.Icons.INVENTORY_2
                elif status == "Deployed":
                    icon = ft.Icons.ROCKET_LAUNCH
                elif status == "Error":
                    icon = ft.Icons.ERROR

                recent_list.append(
                    ft.ListTile(
                        leading=ft.Icon(icon, size=20),
                        title=ft.Text(title, size=14, weight=ft.FontWeight.BOLD, no_wrap=True),
                        subtitle=ft.Text(f"{status} • {time_str}", size=11, color="ON_SURFACE_VARIANT")
                    )
                )

        # Update recent container content
        recent_content = ft.Column([
            ft.Text(i18n.get("recent_actions") or "Recent Actions", weight=ft.FontWeight.BOLD, size=18),
            ft.Container(height=10),
            ft.Column(recent_list, spacing=8, scroll=ft.ScrollMode.AUTO, expand=True, height=200)
        ], expand=True)
        self.recent_container.content = recent_content

        # Update Mail Flow Chart
        if self.mail_flow_data:
            bar_groups = []
            for i, data_point in enumerate(self.mail_flow_data):
                # data_point keys: sent, received, date
                bar_groups.append(
                    ft.BarChartGroup(
                        x=i,
                        bar_rods=[
                            ft.BarChartRod(
                                from_y=0,
                                to_y=data_point.get("sent", 0),
                                width=15,
                                color=ft.colors.BLUE,
                                tooltip=f"Sent: {data_point.get('sent', 0)}",
                                border_radius=0
                            ),
                            ft.BarChartRod(
                                from_y=0,
                                to_y=data_point.get("received", 0),
                                width=15,
                                color=ft.colors.GREEN,
                                tooltip=f"Received: {data_point.get('received', 0)}",
                                border_radius=0
                            ),
                        ]
                    )
                )

            # Update the chart control inside mail_flow_container
            # Structure: Column -> [Row (Header), Spacer, BarChart]
            chart_control = self.mail_flow_container.content.controls[2]
            chart_control.bar_groups = bar_groups

            # Update bottom axis labels
            labels = []
            for i, data_point in enumerate(self.mail_flow_data):
                # Show simplified date (e.g. "Mon" or "10-01")
                try:
                     d_str = datetime.strptime(data_point["date"], "%Y-%m-%d").strftime("%d.%m")
                except:
                     d_str = data_point["date"]
                labels.append(ft.ChartAxisLabel(value=i, label=ft.Text(d_str, size=10, weight=ft.FontWeight.BOLD)))

            chart_control.bottom_axis.labels = labels

        # Force update of all containers
        try:
            self.stats_row.update()
            self.chart_container.update()
            self.recent_container.update()
            self.mail_flow_container.update()
            self.update()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to update dashboard UI: {e}", exc_info=True)


    def _stat_card(self, label, value, icon, color):
        """
        Create a styled statistic card container used in the dashboard.

        Parameters:
        	label (str): Text label shown under the main value (e.g., "Analyzed").
        	value (str | int): Primary statistic displayed prominently.
        	icon: Icon identifier used for the leading icon.
        	color (str): Color applied to the leading icon.

        Returns:
        	ft.Container: A container holding an icon at the left and a column with the value and label, styled for dashboard stat display.
        """
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, color=color, size=40),
                ft.Column([
                    ft.Text(value, size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(label, size=14, color="ON_SURFACE_VARIANT")
                ])
            ]),
            bgcolor="BLACK26",
            padding=20,
            border_radius=10,
            width=200
        )

    def _start_mail_flow(self, e):
        """
        Handler for Start Mail Flow button.
        """
        # In a real app, this would open a dialog to select sender/recipient or use defaults.
        # For now, we'll verify permissions and trigger a mock send or alert.
        def close_dlg(e):
             self.app_page.dialog.open = False
             self.app_page.update()

        def send_action(e):
             # Placeholder for real send logic requiring auth
             sender = sender_field.value
             recipient = recipient_field.value

             # Need a token - reusing Intune/Auth service or prompting login would be ideal.
             # self.exchange_service.authenticate(...)
             # For UI Demo:
             self.app_page.dialog.open = False
             self.app_page.update()

             self.app_page.snack_bar = ft.SnackBar(ft.Text(f"Mail flow started: {sender} -> {recipient} (Mock)"))
             self.app_page.snack_bar.open = True
             self.app_page.update()

        sender_field = ft.TextField(label="Sender (UPN)", value="admin@contoso.com")
        recipient_field = ft.TextField(label="Recipient", value="user@contoso.com")

        dlg = ft.AlertDialog(
            title=ft.Text("Start Mail Flow Test"),
            content=ft.Column([
                ft.Text("Send a test email to verify mail flow."),
                sender_field,
                recipient_field
            ], height=200),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.FilledButton("Send", on_click=send_action),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app_page.dialog = dlg
        dlg.open = True
        self.app_page.update()