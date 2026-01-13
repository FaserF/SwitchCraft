import flet as ft




class DashboardView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page

        # Mock Data
        self.stats = {
            "analyzed": 42,
            "packaged": 15,
            "deployed": 7,
            "errors": 2
        }

        self.controls = [
            ft.Text("Dashboard", size=28, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            self._build_stats_row(),
            ft.Container(height=20),
            ft.Row([
                self._build_chart_section(),
                self._build_recent_activity()
            ], expand=True)
        ]

    def _build_stats_row(self):
        return ft.Row([
            self._stat_card("Analyzed", str(self.stats["analyzed"]), ft.Icons.ANALYTICS, ft.Colors.BLUE),
            self._stat_card("Packaged", str(self.stats["packaged"]), ft.Icons.INVENTORY_2, ft.Colors.ORANGE),
            self._stat_card("Deployed", str(self.stats["deployed"]), ft.Icons.ROCKET_LAUNCH, ft.Colors.GREEN),
            self._stat_card("Errors", str(self.stats["errors"]), ft.Icons.ERROR_OUTLINE, ft.Colors.RED),
        ], alignment=ft.MainAxisAlignment.SPACE_EVENLY)

    def _stat_card(self, label, value, icon, color):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, color=color, size=40),
                ft.Column([
                    ft.Text(value, size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(label, size=14, color=ft.Colors.GREY)
                ])
            ]),
            bgcolor=ft.Colors.BLACK26,
            padding=20,
            border_radius=10,
            width=200
        )

    def _build_chart_section(self):
        # Mock Bar Chart
        return ft.Container(
            content=ft.Column([
                ft.Text("Weekly Activity", weight=ft.FontWeight.BOLD, size=18),
                ft.BarChart(
                    bar_groups=[
                        ft.BarChartGroup(x=0, bar_rods=[ft.BarChartRod(from_y=0, to_y=5, color=ft.Colors.BLUE)]),
                        ft.BarChartGroup(x=1, bar_rods=[ft.BarChartRod(from_y=0, to_y=8, color=ft.Colors.BLUE)]),
                        ft.BarChartGroup(x=2, bar_rods=[ft.BarChartRod(from_y=0, to_y=3, color=ft.Colors.BLUE)]),
                        ft.BarChartGroup(x=3, bar_rods=[ft.BarChartRod(from_y=0, to_y=12, color=ft.Colors.BLUE)]),
                        ft.BarChartGroup(x=4, bar_rods=[ft.BarChartRod(from_y=0, to_y=7, color=ft.Colors.BLUE)]),
                    ],
                    border=ft.border.all(1, ft.Colors.GREY_400),
                    left_axis=ft.ChartAxis(labels_size=40, title=ft.Text("Count")),
                    bottom_axis=ft.ChartAxis(
                        labels=[
                            ft.ChartAxisLabel(value=0, label=ft.Text("Mon")),
                            ft.ChartAxisLabel(value=1, label=ft.Text("Tue")),
                            ft.ChartAxisLabel(value=2, label=ft.Text("Wed")),
                            ft.ChartAxisLabel(value=3, label=ft.Text("Thu")),
                            ft.ChartAxisLabel(value=4, label=ft.Text("Fri")),
                        ],
                        labels_size=32,
                    ),
                    horizontal_grid_lines=ft.ChartGridLines(color=ft.Colors.GREY_800, width=1, dash_pattern=[3, 3]),
                    tooltip_bgcolor=ft.Colors.GREY_900,
                    max_y=15,
                    interactive=True,
                    expand=True
                )
            ]),
            expand=True,
            padding=20,
            bgcolor=ft.Colors.BLACK12,
            border_radius=10
        )

    def _build_recent_activity(self):
        return ft.Container(
            content=ft.Column([
                ft.Text("Recent Actions", weight=ft.FontWeight.BOLD, size=18),
                ft.ListView([
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.CHECK), title=ft.Text("Packaged VSCode"),
                        subtitle=ft.Text("Today, 10:00 AM")
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.CHECK), title=ft.Text("Deployed Chrome"),
                        subtitle=ft.Text("Yesterday, 2:30 PM")
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED), title=ft.Text("Failed Adobe Reader"),
                        subtitle=ft.Text("Yesterday, 11:00 AM")
                    ),
                ], expand=True)
            ]),
            width=350,
            padding=20,
            bgcolor=ft.Colors.BLACK12,
            border_radius=10
        )
