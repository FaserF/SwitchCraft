import flet as ft
import threading
import logging
from switchcraft.services.addon_service import AddonService
from switchcraft.utils.i18n import i18n

logger = logging.getLogger(__name__)


def ModernWingetView(page: ft.Page):
    """Winget Store View."""
    winget = None

    # Try to load helper
    winget_mod = AddonService.import_addon_module("winget", "utils.winget")
    if winget_mod:
        try:
            winget = winget_mod.WingetHelper()
        except Exception:
            pass

    if not winget:
        return ft.Column([
            ft.Icon(ft.Icons.ERROR, color="red", size=50),
            ft.Text("Winget Addon not available.", size=20)
        ], alignment=ft.MainAxisAlignment.CENTER)

    # State
    search_results = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    # Initial instruction
    search_results.controls.append(
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.SEARCH, size=40, color=ft.colors.GREY_600),
                ft.Text(i18n.get("winget_search_instruction") or "Enter a search term to start searching.",
                        color=ft.colors.GREY_600, text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=20,
            alignment=ft.alignment.center
        )
    )

    details_area = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    search_field = ft.TextField(
        label=i18n.get("tab_winget") or "Search Winget",
        placeholder=i18n.get("winget_search_placeholder") or "Apps suchen...",
        expand=True
    )

    def run_search(e):
        query = search_field.value
        if not query:
            return

        search_results.controls.clear()
        search_results.controls.append(
            ft.Column([
                ft.ProgressBar(),
                ft.Text(i18n.get("winget_searching") or "Searching...")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        page.update()

        def _search():
            try:
                results = winget.search_packages(query)
                show_list(results)
            except Exception as ex:
                search_results.controls.clear()
                search_results.controls.append(ft.Text(f"Error: {ex}", color="red"))
                page.update()

        threading.Thread(target=_search, daemon=True).start()

    def show_list(results):
        search_results.controls.clear()
        if not results:
            search_results.controls.append(ft.Text(i18n.get("winget_no_results") or "No results found."))
        else:
            for item in results:
                search_results.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.APPS),
                        title=ft.Text(item.get('Name', 'Unknown')),
                        subtitle=ft.Text(f"{item.get('Id', '')} - {item.get('Version', '')}"),
                        on_click=lambda e, i=item: load_details(i)
                    )
                )
        page.update()

    def load_details(short_info):
        details_area.controls.clear()
        details_area.controls.append(ft.ProgressBar())
        page.update()

        def _fetch():
            try:
                full = winget.get_package_details(short_info['Id'])
                merged = {**short_info, **full}
                show_details_ui(merged)
            except Exception as ex:
                details_area.controls.clear()
                details_area.controls.append(ft.Text(f"Error: {ex}", color="red"))
                page.update()

        threading.Thread(target=_fetch, daemon=True).start()

    def show_details_ui(info):
        details_area.controls.clear()
        details_area.controls.append(ft.Text(info.get('Name', 'Unknown'), size=28, weight=ft.FontWeight.BOLD))
        details_area.controls.append(ft.Text(info.get('Id', ''), color="grey"))
        details_area.controls.append(ft.Divider())

        for key in ['Publisher', 'Description', 'License']:
            val = info.get(key.lower())
            if val:
                details_area.controls.append(ft.Text(f"{key}: {val}"))

        details_area.controls.append(ft.Divider())
        details_area.controls.append(
            ft.ElevatedButton("Install Locally", icon=ft.Icons.DOWNLOAD, bgcolor=ft.colors.GREEN,
                              on_click=lambda e: page.show_snack_bar(ft.SnackBar(ft.Text("Install feature coming soon"))))
        )
        page.update()

    search_field.on_submit = run_search

    # Layout
    left_pane = ft.Container(
        content=ft.Column([
            ft.Row([search_field, ft.IconButton(ft.Icons.SEARCH, on_click=run_search)]),
            ft.Divider(),
            search_results
        ], expand=True),
        width=350,
        padding=10,
        bgcolor=ft.colors.SURFACE_CONTAINER_HIGHEST if hasattr(ft.colors, "SURFACE_CONTAINER_HIGHEST") else ft.colors.GREY_900,
        border_radius=10
    )

    right_pane = ft.Container(
        content=details_area,
        expand=True,
        padding=20,
    )

    return ft.Row([left_pane, right_pane], expand=True)
