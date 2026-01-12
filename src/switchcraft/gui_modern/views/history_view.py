import flet as ft
from datetime import datetime
from switchcraft.services.history_service import HistoryService
from switchcraft.utils.i18n import i18n


def ModernHistoryView(page: ft.Page):
    """History View."""
    history_service = HistoryService()
    list_view = ft.ListView(expand=True, spacing=10)
    loading = ft.ProgressBar(visible=False)

    def show_snack(msg):
        try:
             page.snack_bar = ft.SnackBar(ft.Text(msg))
             page.snack_bar.open = True
             page.update()
        except:
             pass

    def load_history():
        list_view.controls.clear()
        loading.visible = True
        try:
            page.update()
        except:
            pass

        # Load synchronously - history file is small and local, no need for threading
        items = []
        try:
            items = history_service.get_history()
        except Exception:
            pass

        # No need to reverse - already sorted newest first by service
        show_items(items)

    def show_items(items):
        loading.visible = False
        list_view.controls.clear()
        if not items:
            list_view.controls.append(ft.Text(i18n.get("history_empty") or "No history found.", italic=True, color="grey"))
        else:
            for item in items:
                list_view.controls.append(create_tile(item))
        try:
            page.update()
        except:
            pass

    def create_tile(item):
        filename = item.get('filename', i18n.get("unknown") or 'Unknown')
        product = item.get('product', i18n.get("unknown") or 'Unknown')
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
                ft.ElevatedButton(i18n.get("btn_load") or "Load", on_click=lambda e: show_snack(f"{i18n.get('loading') or 'Loading'} {filename}..."))
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
        ft.Text(i18n.get("tab_history") or "History", size=24, weight=ft.FontWeight.BOLD),
        ft.IconButton(ft.Icons.REFRESH, tooltip=i18n.get("btn_refresh") or "Refresh", on_click=lambda e: load_history()),
        ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip=i18n.get("btn_clear_all") or "Clear All", icon_color="red", on_click=clear_history)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    return ft.Column([
        toolbar,
        loading,
        ft.Divider(),
        list_view
    ], expand=True)
