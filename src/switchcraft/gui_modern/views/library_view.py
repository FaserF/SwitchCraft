import flet as ft
from switchcraft.services.history_service import HistoryService
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class LibraryView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.history_service = HistoryService()
        self.all_items = []

        # State
        self.search_val = ""
        self.status_filter = "All"

        # UI Components
        self.grid = ft.GridView(
            runs_count=5,
            max_extent=250,
            child_aspect_ratio=1.0,
            spacing=10,
            run_spacing=10,
            expand=True
        )

        self.search_field = ft.TextField(
            hint_text="Search Library...",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=self._on_search_change
        )

        self.filter_dd = ft.Dropdown(
            options=[
                 ft.dropdown.Option("All"),
                 ft.dropdown.Option("Analyzed"),
                 ft.dropdown.Option("Packaged"),
            ],
            value="All",
            width=150,
            on_change=self._on_filter_change
        )

        self.controls = [
            ft.Row([
                ft.Text("My Library", size=28, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                ft.IconButton(ft.Icons.REFRESH, on_click=self._load_data)
            ]),
            ft.Divider(),
            ft.Row([self.search_field, self.filter_dd]),
            ft.Container(height=10),
            self.grid
        ]

    def did_mount(self):
        self._load_data(None)

    def _load_data(self, e):
        self.all_items = self.history_service.get_history()
        self._refresh_grid()

    def _on_search_change(self, e):
        self.search_val = e.control.value.lower()
        self._refresh_grid()

    def _on_filter_change(self, e):
        self.status_filter = e.control.value
        self._refresh_grid()

    def _refresh_grid(self):
        self.grid.controls.clear()

        filtered = []
        for item in self.all_items:
            # Filter Logic
            name = item.get('filename', '').lower() + " " + item.get('product', '').lower()
            if self.search_val and self.search_val not in name:
                continue

            # Mock status for now since history doesn't strictly track "Packaged" vs "Analyzed"
            # In real impl, we'd check item fields.
            item_status = item.get('status', 'Analyzed')
            if self.status_filter != "All" and self.status_filter != item_status:
                continue

            filtered.append(item)

        for item in filtered:
            self.grid.controls.append(self._create_tile(item))

        self.update()

    def _create_tile(self, item):
        filename = item.get('filename', 'Unknown')
        product = item.get('product', 'Unknown')
        ver = item.get('version', '?')
        ts = item.get('timestamp', '')

        try:
            dt = datetime.fromisoformat(ts).strftime("%Y-%m-%d")
        except ValueError:
            dt = ts

        return ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.INVENTORY_2_OUTLINED, size=40, color="BLUE_200"),
                ft.Text(filename, weight=ft.FontWeight.BOLD, no_wrap=True, tooltip=filename),
                ft.Text(f"{product} v{ver}", size=12, color="GREY", no_wrap=True),
                ft.Container(expand=True),
                ft.Row([
                    ft.Text(dt, size=10, color="GREY_500"),
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=14, color="GREEN")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ]),
            bgcolor="WHITE,0.1",
            border=ft.Border.all(1, "WHITE,0.1"),
            border_radius=10,
            padding=15,
            on_hover=lambda e: self._on_tile_hover(e)
        )

    def _on_tile_hover(self, e):
        e.control.bgcolor = "WHITE,0.2" if e.data == "true" else "WHITE,0.1"
        e.control.update()
