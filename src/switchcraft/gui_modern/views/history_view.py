import flet as ft
from datetime import datetime
import logging
from switchcraft.services.history_service import HistoryService
from switchcraft.utils.i18n import i18n
from switchcraft.gui_modern.utils.view_utils import ViewMixin

logger = logging.getLogger(__name__)

class HistoryView(ft.Column, ViewMixin):
    """Modern History View."""
    def __init__(self, page: ft.Page):
        super().__init__(expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.app_page = page
        self.history_service = HistoryService()

        # UI Components
        self.history_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text(i18n.get("col_filename") or "File")),
                ft.DataColumn(ft.Text(i18n.get("col_product") or "Product")),
                ft.DataColumn(ft.Text(i18n.get("col_date") or "Date")),
                ft.DataColumn(ft.Text(i18n.get("col_action") or "Action")),
            ],
            rows=[],
            border=ft.Border.all(1, "grey"),
            vertical_lines=ft.border.BorderSide(1, "grey"),
            horizontal_lines=ft.border.BorderSide(1, "grey"),
            heading_row_color="SURFACE_VARIANT",
        )

        self.loading = ft.ProgressBar(width=400, color="BLUE", bgcolor="GREY_900", visible=False)

        # Toolbar
        self.toolbar = ft.Row([
            ft.Text(i18n.get("tab_history") or "History", size=24, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            ft.Row([
                ft.IconButton(
                    ft.Icons.REFRESH,
                    tooltip=i18n.get("btn_refresh") or "Refresh",
                    on_click=self._safe_event_handler(lambda e: self.load_history(), "Refresh history")
                ),
                ft.IconButton(
                    ft.Icons.DELETE_FOREVER,
                    tooltip=i18n.get("btn_clear_all") or "Clear All",
                    icon_color="red",
                    on_click=self._safe_event_handler(self.clear_history, "Clear history")
                )
            ])
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        self.controls = [
            ft.Container(content=self.toolbar, padding=ft.Padding.only(left=20, right=20, top=10)),
            self.loading,
            ft.Divider(),
            ft.Column([self.history_table], scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        ]

        # Load on init
        self.load_history()

    def load_history(self):
        """Loads and displays the history."""
        self.history_table.rows.clear()
        self.loading.visible = True
        self._safe_update()

        def _bg():
            items = []
            try:
                items = self.history_service.get_history()
            except Exception as e:
                logger.error(f"Failed to load history: {e}")

            def _update():
                self.show_items(items)

            self._run_task_safe(_update)

        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def show_items(self, items):
        """Updates the table with history items."""
        self.loading.visible = False
        self.history_table.rows.clear()

        if not items:
            self._show_snack(i18n.get("no_history") or "No history found.", "BLUE")
        else:
            for item in items:
                self.history_table.rows.append(self.create_row(item))

        self._safe_update()

    def create_row(self, item):
        """Creates a DataRow for a history item."""
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
                icon=ft.Icons.PLAY_ARROW,
                tooltip=i18n.get("btn_load") or "Load",
                on_click=self._safe_event_handler(
                    lambda e, f=filename: self._show_snack(f"{(i18n.get('loading') or 'Loading')} {f}..."),
                    f"Load history item {filename}"
                )
            )),
        ])

    def clear_history(self, e):
        """Clears the history."""
        self.history_service.clear()
        self.load_history()

# For backward compatibility with existing imports if any
def ModernHistoryView(page: ft.Page):
    return HistoryView(page)
