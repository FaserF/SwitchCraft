import flet as ft
import traceback

class CrashDumpView(ft.Container):
    def __init__(self, page: ft.Page, error: Exception, traceback_str: str = None):
        super().__init__(expand=True)
        self.bgcolor = "#1a1a1a" # Dark background like BSOD but modern
        self.padding = 30

        if not traceback_str:
            traceback_str = traceback.format_exc()

        self._traceback_str = traceback_str
        self.content = ft.Column(
            controls=[
                ft.Icon(ft.Icons.ERROR_OUTLINE, color="RED_400", size=64),
                ft.Text("Something went wrong", size=32, weight=ft.FontWeight.BOLD, color="WHITE"),
                ft.Text("An unexpected error occurred while loading this view.", size=16, color="GREY_400"),
                ft.Container(height=20),
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Error: {str(error)}", color="RED_200", weight=ft.FontWeight.BOLD),
                        ft.Divider(color="GREY_700"),
                        ft.Text(traceback_str, font_family="Consolas", size=12, color="WHITE")
                    ], scroll=ft.ScrollMode.AUTO),
                    bgcolor="#2d2d2d",
                    padding=15,
                    border_radius=8,
                    expand=True
                ),
                ft.Container(height=20),
                ft.Row([
                    ft.ElevatedButton("Copy Error", icon=ft.Icons.COPY, on_click=self._copy_error),
                    ft.ElevatedButton("Reload App", icon=ft.Icons.REFRESH, on_click=lambda e: self._reload_app(page)),
                ], alignment=ft.MainAxisAlignment.END)
            ],
            expand=True
        )

    def _copy_error(self, e):
        # The traceback string was captured in __init__ scope or passed down?
        # We need access to it. We'll store it.
        if hasattr(self, '_traceback_str'):
             self.page.set_clipboard(self._traceback_str)
             self.page.show_snack_bar(ft.SnackBar(ft.Text("Error details copied to clipboard")))
             self.page.update()

    def _reload_app(self, page):
        import sys
        import subprocess

        page.clean()
        page.add(ft.Text("Reloading...", size=20))
        page.update()

        # Robust Restart Logic
        try:
            if getattr(sys, 'frozen', False):
                # Running as PyInstaller Bundle
                executable = sys.executable
                args = sys.argv[1:]
            else:
                # Running as Script
                executable = sys.executable
                args = sys.argv

            # Launch new instance
            subprocess.Popen([executable] + args)

            # Kill current instance
            sys.exit(0)
        except Exception as e:
            text = f"Failed to reload automatically: {e}\nPlease restart manually."
            page.show_snack_bar(ft.SnackBar(ft.Text(text)))
            page.update()
