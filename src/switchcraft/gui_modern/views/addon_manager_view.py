import flet as ft
import logging
import threading

from switchcraft.services.addon_service import AddonService
from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper

logger = logging.getLogger(__name__)

class AddonManagerView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.addon_service = AddonService()
        self.addons = []

        # State
        self.selected_addon = None

        # UI
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        # Header
        self.refresh_btn = ft.IconButton(ft.Icons.REFRESH, on_click=lambda _: self._load_data())
        self.install_btn = ft.ElevatedButton("Install Addon (.zip)", icon=ft.Icons.UPLOAD_FILE, on_click=self._pick_zip)
        self.delete_btn = ft.ElevatedButton(
            "Delete Selected",
            icon=ft.Icons.DELETE,
            bgcolor=ft.Colors.RED,
            color=ft.Colors.WHITE,
            disabled=True,
            on_click=self._confirm_delete
        )

        # Datatable
        self.dt = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Name")),
                ft.DataColumn(ft.Text("Version")),
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Author")),
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.GREY_400),
            vertical_lines=ft.border.BorderSide(1, ft.Colors.GREY_400),
            horizontal_lines=ft.border.BorderSide(1, ft.Colors.GREY_400),
            heading_row_color=ft.Colors.BLACK12,
        )

        self.list_container = ft.Column([self.dt], scroll=ft.ScrollMode.AUTO, expand=True)

        self.controls = [
            ft.Text("Addon Manager", size=28, weight=ft.FontWeight.BOLD),
            ft.Text(" Extend functionality with custom addons.", color=ft.Colors.GREY),
            ft.Divider(),
            ft.Row([self.refresh_btn, self.install_btn, ft.Container(expand=True), self.delete_btn]),
            ft.Divider(),
            self.list_container
        ]

    def _load_data(self):
        self.list_container.disabled = True
        self.update()

        def _bg():
            try:
                self.addons = self.addon_service.list_addons()
                self._update_table()
            except Exception as e:
                logger.error(f"Failed to list addons: {e}")
            finally:
                self.list_container.disabled = False
                self.update()

        threading.Thread(target=_bg, daemon=True).start()

    def _update_table(self):
        self.dt.rows.clear()
        for a in self.addons:
             self.dt.rows.append(
                 ft.DataRow(
                     cells=[
                         ft.DataCell(ft.Text(a.get('name', 'Unknown'))),
                         ft.DataCell(ft.Text(a.get('version', '0.0'))),
                         ft.DataCell(ft.Text(a.get('id', ''))),
                         ft.DataCell(ft.Text(a.get('author', 'Unknown'))),
                     ],
                     on_select_changed=lambda e, ad=a: self._on_select(e.control.selected, ad),
                     selected=self.selected_addon == a
                 )
             )
        self.update()

    def _on_select(self, selected, addon):
        if selected:
            self.selected_addon = addon
        else:
            self.selected_addon = None
        self.delete_btn.disabled = not self.selected_addon
        self.update()

    def _pick_zip(self, e):
        path = FilePickerHelper.pick_file(allowed_extensions=["zip"])
        if path:
            self._install(path)

    def _install(self, path):
        def _bg():
            try:
                self.addon_service.install_addon(path)
                self._show_snack("Addon installed successfully!", ft.Colors.GREEN)
                self._load_data()
            except Exception as e:
                self._show_snack(f"Install failed: {e}", ft.Colors.RED)

        threading.Thread(target=_bg, daemon=True).start()

    def _confirm_delete(self, e):
        if not self.selected_addon: return

        def close_dlg(e):
            self.app_page.close_dialog()

        def delete(e):
            aid = self.selected_addon['id']
            def _bg():
                try:
                    self.addon_service.delete_addon(aid)
                    self._show_snack("Addon deleted.", ft.Colors.GREEN)
                    self.selected_addon = None
                    self.app_page.close_dialog()
                    self._load_data()
                except Exception as ex:
                     self._show_snack(f"Delete failed: {ex}", ft.Colors.RED)
            threading.Thread(target=_bg, daemon=True).start()

        dlg = ft.AlertDialog(
            title=ft.Text("Confirm Deletion"),
            content=ft.Text(f"Delete addon '{self.selected_addon.get('name')}'?"),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
                ft.ElevatedButton("Delete", on_click=delete, bgcolor=ft.Colors.RED, color=ft.Colors.WHITE)
            ]
        )
        self.app_page.dialog = dlg
        dlg.open = True
        self.app_page.update()

    def _show_snack(self, msg, color=ft.Colors.GREEN):
        try:
            self.app_page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.app_page.snack_bar.open = True
            self.app_page.update()
        except Exception:
            pass
