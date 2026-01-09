import flet as ft
import threading
from datetime import datetime
from switchcraft.services.history_service import HistoryService


def ModernHistoryView(page: ft.Page):
    """History View."""
    history_service = HistoryService()
    list_view = ft.ListView(expand=True, spacing=10)
    loading = ft.ProgressBar(visible=False)

    def load_history():
        list_view.controls.clear()
        loading.visible = True
        page.update()

        def _fetch():
            items = []
            try:
                items = history_service.get_history()
            except Exception:
                pass

            if items:
                items.reverse()

            show_items(items)

        threading.Thread(target=_fetch, daemon=True).start()

    def show_items(items):
        loading.visible = False
        list_view.controls.clear()
        if not items:
            list_view.controls.append(ft.Text("No history found.", italic=True, color="grey"))
        else:
            for item in items:
                list_view.controls.append(create_tile(item))
        page.update()

    def create_tile(item):
        filename = item.get('filename', 'Unknown')
        product = item.get('product', 'Unknown')
        ts_str = item.get('timestamp', '')

        try:
            dt = datetime.fromisoformat(ts_str)
            date_display = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            date_display = ts_str

        return ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(filename, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{product} | {date_display}", size=12, color="grey")
                ], expand=True),
                ft.ElevatedButton("Load", on_click=lambda e: page.open(ft.SnackBar(ft.Text(f"Loading {filename}..."))))
            ]),
            padding=10,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST if hasattr(ft.Colors, "SURFACE_CONTAINER_HIGHEST") else ft.Colors.GREY_900,
            border_radius=5
        )

    def clear_history(e):
        history_service.clear()
        load_history()

    # Load on init
    load_history()

    # Toolbar
    toolbar = ft.Row([
        ft.Text("History", size=24, weight=ft.FontWeight.BOLD),
        ft.IconButton(ft.Icons.REFRESH, tooltip="Refresh", on_click=lambda e: load_history()),
        ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip="Clear All", icon_color="red", on_click=clear_history)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    return ft.Column([
        toolbar,
        loading,
        ft.Divider(),
        list_view
    ], expand=True)
