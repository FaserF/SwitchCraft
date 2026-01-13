import flet as ft
import threading
import logging
import os
from switchcraft.services.intune_service import IntuneService
from switchcraft.gui_modern.utils.file_picker_helper import FilePickerHelper

logger = logging.getLogger(__name__)

class ModernIntuneView(ft.Column):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.app_page = page
        self.intune_service = IntuneService()

        # Check Tool Availability
        if not self.intune_service.is_tool_available():
            btn_dl = ft.ElevatedButton("Download Intune Tool")
            btn_dl.on_click = lambda e: self._show_snack("Download feature coming soon")

            self.controls = [
                ft.Column([
                    ft.Icon(ft.Icons.WARNING_AMBER, size=50, color="orange"),
                    ft.Text("IntuneWinAppUtil not found.", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("This tool is required to package applications."),
                    btn_dl
                ], alignment=ft.MainAxisAlignment.CENTER)
            ]
            self.alignment = ft.MainAxisAlignment.CENTER
            self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            return

        self.log_view = ft.ListView(expand=True, spacing=5, auto_scroll=True)

        # Fields
        self.setup_field = ft.TextField(label="Setup File (.exe/.msi)", expand=True)
        self.source_field = ft.TextField(label="Source Folder", expand=True)
        self.output_field = ft.TextField(label="Output Folder", expand=True)
        self.quiet_check = ft.Checkbox(label="Quiet Mode (No UI)", value=True)

        # Helpers
        def pick_setup_file(e):
            path = FilePickerHelper.pick_file(allowed_extensions=["exe", "msi", "ps1", "bat", "cmd", "vbs", "wsf"])
            if path:
                self.setup_field.value = path
                parent = os.path.dirname(path)
                if not self.source_field.value:
                    self.source_field.value = parent
                if not self.output_field.value:
                    self.output_field.value = parent
                self.update()

        def pick_folder(e, field):
            path = FilePickerHelper.pick_directory()
            if path:
                field.value = path
                self.update()

        # Build Form Row Helpers
        def create_file_row():
            btn = ft.IconButton(ft.Icons.FILE_OPEN)
            btn.on_click = pick_setup_file
            return ft.Row([self.setup_field, btn])

        def create_folder_row(field):
            btn = ft.IconButton(ft.Icons.FOLDER_OPEN)
            # Capture field in default arg to avoid late binding issues if used in loop (not strict here but safe)
            btn.on_click = lambda e: pick_folder(e, field)
            return ft.Row([field, btn])

        btn_create = ft.ElevatedButton("Create .intunewin", bgcolor=ft.Colors.GREEN, color=ft.Colors.WHITE, height=50)
        btn_create.on_click = self._run_creation

        # Form UI
        form = ft.Container(
            content=ft.Column([
                ft.Text("Intune Packaging Tool", size=24, weight=ft.FontWeight.BOLD),
                create_file_row(),
                create_folder_row(self.source_field),
                create_folder_row(self.output_field),
                self.quiet_check,
                btn_create
            ]),
            padding=20,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST if hasattr(ft.Colors, "SURFACE_CONTAINER_HIGHEST") else ft.Colors.GREY_900,
            border_radius=10
        )

        self.controls = [
            ft.Column([
                form,
                ft.Divider(),
                ft.Text("Logs:", weight=ft.FontWeight.BOLD),
                ft.Container(content=self.log_view, expand=True, bgcolor=ft.Colors.BLACK, padding=10, border_radius=5)
            ], expand=True)
        ]

    def _log(self, msg):
        self.log_view.controls.append(ft.Text(msg, font_family="Consolas", size=12, color=ft.Colors.GREEN_400))
        self.update()

    def _run_creation(self, e):
        setup = self.setup_field.value
        source = self.source_field.value
        output = self.output_field.value
        quiet = self.quiet_check.value

        if not setup or not source or not output:
            self._show_snack("Please fill all fields", ft.Colors.RED)
            return

        # Validation
        if not os.path.exists(source):
             self._show_snack("Source folder does not exist", ft.Colors.RED)
             return
        if not os.path.exists(setup):
             self._show_snack("Setup file does not exist", ft.Colors.RED)
             return

        # Check if setup is inside source (warning)
        # Actually logic is robust in service, but good to check.

        self._log("Starting creation...")
        self.setup_field.disabled = True
        self.update()

        def _run():
            try:
                self.intune_service.create_intunewin(
                    source_folder=source,
                    setup_file=setup,
                    output_folder=output,
                    quiet=quiet,
                progress_callback=lambda line: self._log(line.strip())
                )
                self._log("DONE! Package created successfully.")
                self._show_snack("Package Created!", ft.Colors.GREEN)

                # Check for likely output name (setup_file.intunewin or such)
                # IntuneWinAppUtil uses [SetupFileName].intunewin logic usually
                possible_name = os.path.basename(setup) + ".intunewin"
                # Or just check last created file?
                # Best guess:
                target_file = os.path.join(output, possible_name)
                if not os.path.exists(target_file):
                     # Try removing extension
                     target_file = os.path.join(output, os.path.splitext(os.path.basename(setup))[0] + ".intunewin")

                if os.path.exists(target_file):
                    self._open_explorer_select(target_file)
                else:
                    self._open_explorer_select(output) # Open folder at least

            except Exception as ex:
                self._log(f"ERROR: {ex}")
                self._show_snack(f"Failed: {ex}", ft.Colors.RED)
            finally:
                self.setup_field.disabled = False
                self.update()

        threading.Thread(target=_run, daemon=True).start()

    def _open_explorer_select(self, path):
        import subprocess
        # Windows only feature
        if os.name == 'nt':
            try:
                # Normalize path to use backslashes and be absolute
                norm_path = os.path.abspath(os.path.normpath(path))
                subprocess.run(f'explorer /select,"{norm_path}"', shell=True)
            except Exception as e:
                self._log(f"Failed to open explorer: {e}")

    def _show_snack(self, msg, color=ft.Colors.GREEN):
        try:
            self.app_page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
            self.app_page.snack_bar.open = True
            self.app_page.update()
        except Exception:
             pass
