import flet as ft
import threading
import logging
from switchcraft.services.intune_service import IntuneService

logger = logging.getLogger(__name__)


def ModernIntuneView(page: ft.Page):
    """Intune Packaging View."""
    intune_service = IntuneService()

    log_view = ft.ListView(expand=True, spacing=2, auto_scroll=True)

    # Form Controls
    setup_field = ft.TextField(label="Setup File (.exe/.msi)", expand=True)
    source_field = ft.TextField(label="Source Folder", expand=True)
    output_field = ft.TextField(label="Output Folder", expand=True)
    quiet_check = ft.Checkbox(label="Quiet Mode (No UI)", value=True)

    file_picker = ft.FilePicker(on_result=lambda e: on_file_pick(e))
    dir_picker = ft.FilePicker(on_result=lambda e: on_dir_pick(e))
    page.overlay.extend([file_picker, dir_picker])

    active_field = {"ref": None}

    def on_file_pick(e: ft.FilePickerResultEvent):
        if e.files:
            setup_field.value = e.files[0].path
            import os
            parent = os.path.dirname(e.files[0].path)
            if not source_field.value:
                source_field.value = parent
            if not output_field.value:
                output_field.value = parent
            page.update()

    def on_dir_pick(e: ft.FilePickerResultEvent):
        if e.path and active_field["ref"]:
            active_field["ref"].value = e.path
            page.update()

    def pick_dir(field):
        active_field["ref"] = field
        dir_picker.get_directory_path()

    def log(msg):
        log_view.controls.append(ft.Text(msg, font_family="Consolas", size=12))
        page.update()

    def run_creation(e):
        setup = setup_field.value
        source = source_field.value
        output = output_field.value

        if not setup or not source or not output:
            page.show_snack_bar(ft.SnackBar(ft.Text("Please fill all fields")))
            return

        log("Starting creation...")

        def _run():
            try:
                intune_service.create_intunewin(
                    source_folder=source,
                    setup_file=setup,
                    output_folder=output,
                    quiet=quiet_check.value,
                    progress_callback=lambda l: log(l.strip())
                )
                log("DONE! Package created.")
                page.show_snack_bar(ft.SnackBar(ft.Text("Package Created!"), bgcolor="green"))
            except Exception as ex:
                log(f"ERROR: {ex}")

        threading.Thread(target=_run, daemon=True).start()

    # Check Tool Availability
    if not intune_service.is_tool_available():
        return ft.Column([
            ft.Icon(ft.Icons.WARNING_AMBER, size=50, color="orange"),
            ft.Text("IntuneWinAppUtil not found.", size=20, weight=ft.FontWeight.BOLD),
            ft.Text("This tool is required to package applications."),
            ft.ElevatedButton("Download Intune Tool", on_click=lambda e: page.show_snack_bar(ft.SnackBar(ft.Text("Download feature coming soon")))),
        ], alignment=ft.MainAxisAlignment.CENTER)

    # Form UI
    form = ft.Container(
        content=ft.Column([
            ft.Text("Intune Packaging Tool", size=24, weight=ft.FontWeight.BOLD),
            ft.Row([setup_field, ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=lambda _: file_picker.pick_files(allow_multiple=False))]),
            ft.Row([source_field, ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=lambda _: pick_dir(source_field))]),
            ft.Row([output_field, ft.IconButton(ft.Icons.FOLDER_OPEN, on_click=lambda _: pick_dir(output_field))]),
            quiet_check,
            ft.ElevatedButton("Create .intunewin", bgcolor=ft.colors.GREEN, color=ft.colors.WHITE, on_click=run_creation),
        ]),
        padding=20,
        bgcolor=ft.colors.SURFACE_CONTAINER_HIGHEST if hasattr(ft.colors, "SURFACE_CONTAINER_HIGHEST") else ft.colors.GREY_900,
        border_radius=10
    )

    return ft.Column([
        form,
        ft.Divider(),
        ft.Text("Logs:", weight=ft.FontWeight.BOLD),
        ft.Container(content=log_view, expand=True, bgcolor=ft.colors.BLACK, padding=10, border_radius=5)
    ], expand=True)
