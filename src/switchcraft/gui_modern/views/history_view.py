import flet as ft
from datetime import datetime
from switchcraft.services.history_service import HistoryService
from switchcraft.utils.i18n import i18n


def ModernHistoryView(page: ft.Page):
    """History View."""
    history_service = HistoryService()
    # DataTable
    history_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text(i18n.get("col_filename") or "File")),
            ft.DataColumn(ft.Text(i18n.get("col_product") or "Product")),
            ft.DataColumn(ft.Text(i18n.get("col_date") or "Date")),
            ft.DataColumn(ft.Text(i18n.get("col_action") or "Action")),
        ],
        rows=[],
        border=ft.border.all(1, "grey"),
        vertical_lines=ft.border.BorderSide(1, "grey"),
        horizontal_lines=ft.border.BorderSide(1, "grey"),
        heading_row_color="SURFACE_VARIANT",
    )

    loading = ft.ProgressBar(width=400, color="BLUE", bgcolor="GREY_900", visible=False)

    def show_snack(msg):
        try:
             page.snack_bar = ft.SnackBar(ft.Text(msg))
             page.snack_bar.open = True
             page.update()
        except Exception:
             pass

    def load_history():
        # Define loading indicator if not present (although scope is tricky in function-based view)
        # Actually, this file structure is: def ModernHistoryView(page).
        # We need a loading control defined in outer scope.

        # Clear rows
        history_table.rows.clear()
        loading.visible = True
        try:
            page.update()
        except Exception:
            pass

        items = []
        try:
            items = history_service.get_history()
        except Exception:
            pass

        show_items(items)

    def show_items(items):
        loading.visible = False
        history_table.rows.clear()

        if not items:
            # Show empty state
            show_snack(i18n.get("no_history") or "No history found.")
            pass
        else:
            for item in items:
                history_table.rows.append(create_row(item))

        try:
            page.update()
        except Exception:
            pass

    def create_row(item):
        filename = item.get('filename', i18n.get("unknown") or 'Unknown')
        product = item.get('product', i18n.get("unknown") or 'Unknown')
        ts_str = item.get('timestamp', '')

        try:
            dt = datetime.fromisoformat(ts_str)
            date_display = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            date_display = ts_str

        return ft.DataRow(cells=[
            ft.DataCell(ft.Text(filename, weight=ft.FontWeight.BOLD)),
            ft.DataCell(ft.Text(product)),
            ft.DataCell(ft.Text(date_display)),
            ft.DataCell(ft.IconButton(
                icon = ft.Icons.PLAY_ARROW,
                tooltip = i18n.get("btn_load") or "Load",
                on_click=lambda e, f=filename: show_snack(f"{i18n.get('loading') or 'Loading'} {f}...")
            )),
        ])

    def clear_history(e):
        history_service.clear()
        load_history()

    # Load on init
    load_history()

    # Toolbar
    toolbar = ft.Row([
        ft.Text(i18n.get("tab_history") or "History", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
        ft.Row([
            ft.IconButton(ft.Icons.REFRESH, tooltip=i18n.get("btn_refresh") or "Refresh", on_click=lambda e: load_history()),
            ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip=i18n.get("btn_clear_all") or "Clear All", icon_color="red", on_click=clear_history)
        ])
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    return ft.Column([
        ft.Container(content=toolbar, padding=ft.padding.only(left=20, right=20, top=10)),
        loading,
        ft.Divider(),
        ft.Column([history_table], scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
