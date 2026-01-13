import flet as ft
from switchcraft.services.history_service import HistoryService
from collections import Counter, defaultdict
from datetime import datetime, timedelta

class DashboardView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True, scroll=ft.ScrollMode.AUTO)
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
        self.stats_row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_EVENLY)
        self.chart_container = ft.Container(bgcolor="BLACK12", border_radius=10, padding=20)
        self.recent_container = ft.Container(bgcolor="BLACK12", border_radius=10, padding=20, width=350)

        self.controls = [
            ft.Text("Dashboard", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            self.stats_row,
            ft.Container(height=20),
            ft.Row([
                ft.Container(content=self.chart_container, expand=True),
                self.recent_container
            ], expand=True)
        ]

    def did_mount(self):
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
                except ValueError:
                    pass

        self.chart_data = []
        for i in range(4, -1, -1):
            d = today - timedelta(days=i)
            self.chart_data.append((d.strftime("%a"), date_counts[d]))

        self._refresh_ui()

    def _refresh_ui(self):
        # Stats
        self.stats_row.controls = [
            self._stat_card("Analyzed", str(self.stats["analyzed"]), ft.Icons.ANALYTICS, "BLUE"),
            self._stat_card("Packaged", str(self.stats["packaged"]), ft.Icons.INVENTORY_2, "ORANGE"),
            self._stat_card("Deployed", str(self.stats["deployed"]), ft.Icons.ROCKET_LAUNCH, "GREEN"),
            self._stat_card("Errors", str(self.stats["errors"]), ft.Icons.ERROR_OUTLINE, "RED"),
        ]

        # Chart
        bars = []
        max_val = max([v for _, v in self.chart_data], default=0)

        for day, val in self.chart_data:
            height_pct = (val / max_val) * 150 if max_val > 0 else 2 # min height 2
            color = "BLUE_400" if val > 0 else "GREY_800"
            bars.append(
                ft.Column([
                    ft.Container(
                        bgcolor=color,
                        width=30,
                        height=height_pct,
                        border_radius=ft.border_radius.only(top_left=4, top_right=4),
                        tooltip=f"{day}: {val}"
                    ),
                    ft.Text(day, size=10, color="GREY")
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4)
            )

        self.chart_container.content = ft.Column([
            ft.Text("Activity (Last 5 Days)", weight=ft.FontWeight.BOLD, size=18),
            ft.Container(height=20),
            ft.Row(bars, alignment=ft.MainAxisAlignment.SPACE_EVENLY, vertical_alignment=ft.CrossAxisAlignment.END),
        ])

        # Recent
        recent_list = []
        if not self.recent_items:
            recent_list.append(ft.Text("No recent activity.", color="GREY", italic=True))
        else:
            for item in self.recent_items:
                # Format time
                ts = item.get("timestamp", "")
                try:
                    dt = datetime.fromisoformat(ts)
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    time_str = ts

                title = item.get("filename") or item.get("product") or "Unknown"
                status = item.get("status", "Analyzed")
                icon = ft.Icons.ANALYTICS
                if status == "Packaged": icon = ft.Icons.INVENTORY_2
                elif status == "Deployed": icon = ft.Icons.ROCKET_LAUNCH
                elif status == "Error": icon = ft.Icons.ERROR

                recent_list.append(
                    ft.ListTile(
                        leading=ft.Icon(icon, size=20),
                        title=ft.Text(title, size=14, weight=ft.FontWeight.BOLD, no_wrap=True),
                        subtitle=ft.Text(f"{status} • {time_str}", size=11, color="GREY")
                    )
                )

        self.recent_container.content = ft.Column([
             ft.Text("Recent Actions", weight=ft.FontWeight.BOLD, size=18),
             ft.ListView(recent_list, height=300, spacing=0)
        ])

        if self.page:
            self.update()

    def _stat_card(self, label, value, icon, color):
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
