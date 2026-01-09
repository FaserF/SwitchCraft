import flet as ft
import threading
import logging
from switchcraft.controllers.analysis_controller import AnalysisController, AnalysisResult

logger = logging.getLogger(__name__)


def ModernAnalyzerView(page: ft.Page):
    """Analyzer View - Drag & Drop file analysis."""
    controller = AnalysisController()

    # State
    result_container = ft.Column(visible=False)
    progress_bar = ft.ProgressBar(visible=False, width=400)
    status_text = ft.Text("", visible=False)

    def on_file_drop(e: ft.FilePickerResultEvent):
        if e.files:
            start_analysis(e.files[0].path)

    file_picker = ft.FilePicker(on_result=on_file_drop)
    page.overlay.append(file_picker)

    def start_analysis(filepath):
        progress_bar.visible = True
        status_text.visible = True
        status_text.value = f"Analyzing {filepath}..."
        result_container.visible = False
        page.update()

        def _run():
            try:
                result = controller.analyze_file(filepath)
                show_results(result)
            except Exception as ex:
                status_text.value = f"Error: {ex}"
                status_text.color = "red"
                progress_bar.visible = False
                page.update()

        threading.Thread(target=_run, daemon=True).start()

    def show_results(result: AnalysisResult):
        progress_bar.visible = False
        status_text.visible = False
        result_container.controls.clear()

        if result.error:
            result_container.controls.append(ft.Text(f"Error: {result.error}", color="red"))
        else:
            info = result.installer_info
            result_container.controls.append(ft.Text(f"Product: {info.product_name or 'Unknown'}", size=20, weight=ft.FontWeight.BOLD))
            result_container.controls.append(ft.Text(f"Version: {info.version or 'Unknown'}"))
            result_container.controls.append(ft.Text(f"Installer Type: {info.installer_type or 'Unknown'}"))
            result_container.controls.append(ft.Text(f"Silent Args: {info.silent_args or 'None detected'}"))

        result_container.visible = True
        page.update()

    # UI
    drop_zone = ft.Container(
        content=ft.Column([
            ft.Icon(ft.Icons.CLOUD_UPLOAD, size=60, color=ft.Colors.BLUE),
            ft.Text("Drag & Drop Installer Here", size=18),
            ft.Text("Or click to browse", size=12, color="grey"),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        width=400,
        height=200,
        border=ft.border.all(2, ft.colors.BLUE_700),
        border_radius=10,
        alignment=ft.alignment.center,
        on_click=lambda _: file_picker.pick_files(allow_multiple=False),
    )

    return ft.Column([
        ft.Text("Installer Analyzer", size=28, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        drop_zone,
        progress_bar,
        status_text,
        result_container,
    ], expand=True, scroll=ft.ScrollMode.AUTO)
