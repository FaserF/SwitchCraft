import flet as ft
from switchcraft.services.history_service import HistoryService
from switchcraft.utils.i18n import i18n
from collections import defaultdict
from datetime import datetime, timedelta

class DashboardView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO, spacing=15)
        self.app_page = page
        self.history_service = HistoryService()

        # Initial State (Empty)
        self.stats = {
            "analyzed": 0,
            "packaged": 0,
            "deployed": 0,
            "errors": 0
        }
        self.chart_data = []
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
            padding=20
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

        self.controls = [
            ft.Container(
                content=ft.Column([
                    ft.Text(i18n.get("dashboard_overview_title") or "Overview", size=28, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    self.stats_row,
                    ft.Container(height=20),
                    ft.Row([
                        ft.Container(
                            content=self.chart_container,
                            expand=2,
                            height=280
                        ),
                        ft.Container(
                            content=self.recent_container,
                            expand=1,
                            height=280
                        )
                    ], spacing=20, wrap=True)
                ], spacing=15, expand=True),
                padding=20,  # Consistent padding with other views
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
                    ft.Text(day, size=10, color="GREY")
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)
            )

        # Get the existing chart container's content Column
        chart_col = self.chart_container.content
        if isinstance(chart_col, ft.Column) and len(chart_col.controls) >= 3:
            # Update the bars row (index 2)
            chart_col.controls[2] = ft.Row(bars, alignment=ft.MainAxisAlignment.SPACE_EVENLY, vertical_alignment=ft.CrossAxisAlignment.END)
        else:
            # Rebuild entire chart content if structure is wrong
            chart_content = ft.Column([
                ft.Text(i18n.get("chart_activity_title") or "Activity (Last 5 Days)", weight=ft.FontWeight.BOLD, size=18),
                ft.Container(height=20),
                ft.Row(bars, alignment=ft.MainAxisAlignment.SPACE_EVENLY, vertical_alignment=ft.CrossAxisAlignment.END),
            ])
            self.chart_container.content = chart_content

        # Recent
        recent_list = []
        if not self.recent_items:
            recent_list.append(ft.Text(i18n.get("no_recent_activity") or "No recent activity.", color="GREY", italic=True))
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
                        subtitle=ft.Text(f"{status} • {time_str}", size=11, color="GREY")
                    )
                )

        # Get the existing recent container's content Column
        recent_col = self.recent_container.content
        if isinstance(recent_col, ft.Column) and len(recent_col.controls) >= 3:
            # Update the list column (index 2)
            recent_col.controls[2] = ft.Column(recent_list, spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        else:
            # Rebuild entire recent content if structure is wrong
            recent_content = ft.Column([
                 ft.Text(i18n.get("recent_actions") or "Recent Actions", weight=ft.FontWeight.BOLD, size=18),
                 ft.Container(height=10),
                 ft.Column(recent_list, spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
            ], expand=True)
            self.recent_container.content = recent_content

        # Force update of all containers
        # Use run_task to ensure updates happen on UI thread
        if hasattr(self, 'app_page') and hasattr(self.app_page, 'run_task'):
            def update_ui():
                try:
                    self.chart_container.update()
                    self.recent_container.update()
                    self.update()
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to update dashboard UI: {e}")

            # Wrap in async if needed
            import inspect
            if inspect.iscoroutinefunction(update_ui):
                self.app_page.run_task(update_ui)
            else:
                async def async_update():
                    update_ui()
                self.app_page.run_task(async_update)
        else:
            # Fallback: direct update
            try:
                self.chart_container.update()
                self.recent_container.update()
                self.update()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to update dashboard UI: {e}")


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
                    ft.Text(label, size=14, color="GREY")
                ])
            ]),
            bgcolor="BLACK26",
            padding=20,
            border_radius=10,
            width=200
        )