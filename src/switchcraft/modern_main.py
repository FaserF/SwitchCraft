import sys
import os

# Add src to path BEFORE importing switchcraft modules
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.dirname(current_dir)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Global splash process handle
splash_proc = None

def start_splash():
    global splash_proc
    try:
        import subprocess
        from pathlib import Path

        # Resolve path to splash.py (shared with Legacy)
        base_dir = Path(__file__).resolve().parent
        splash_script = base_dir / "gui" / "splash.py"

        if splash_script.exists():
            env = os.environ.copy()
            env["PYTHONPATH"] = str(base_dir.parent)

            creationflags = 0x08000000 if sys.platform == "win32" else 0

            splash_proc = subprocess.Popen(
                [sys.executable, str(splash_script)],
                env=env,
                creationflags=creationflags
            )
    except Exception:
        pass

# Start Splash IMMEDIATELY - before any heavy imports
if __name__ == "__main__":
    start_splash()

# Now do heavy imports
import flet as ft # noqa: E402

# Flet Colors compatibility patch
# Flet 0.80+ removed ft.Colors in favor of ft.colors (lowercase)
# Check if ft.Colors is broken and patch it if needed
try:
    _ = ft.Colors.RED  # Test if Colors works
except AttributeError:
    # ft.Colors is broken, patch it to use ft.colors
    if hasattr(ft, 'colors'):
        ft.Colors = ft.colors

# Flet Alignment compatibility patch
try:
    _ = ft.alignment.center
except AttributeError:
    # ft.alignment.center is missing, patch it
    if hasattr(ft, 'Alignment'):
        if not hasattr(ft, 'alignment') or ft.alignment is None:
            class DummyAlignment: pass
            ft.alignment = DummyAlignment()
        ft.alignment.center = ft.Alignment(0, 0)
    elif hasattr(ft, 'alignment') and hasattr(ft.alignment, 'CENTER'):
        ft.alignment.center = ft.alignment.CENTER

from switchcraft.gui_modern.app import ModernApp  # noqa: E402
from switchcraft.utils.logging_handler import setup_session_logging  # noqa: E402

# Setup session logging
setup_session_logging()

def write_crash_dump(exc_info):
    """Write crash dump to a file for debugging."""
    import traceback
    from datetime import datetime
    from pathlib import Path
    # Use standard SwitchCraft AppData location
    app_data = os.getenv('APPDATA')
    if app_data:
        dump_dir = Path(app_data) / "FaserF" / "SwitchCraft" / "Logs"
    else:
        dump_dir = Path.home() / ".switchcraft" / "Logs"
    dump_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = dump_dir / f"crash_dump_{timestamp}.txt"

    with open(dump_file, "w", encoding="utf-8") as f:
        f.write(f"SwitchCraft Crash Dump\n")
        f.write(f"Time: {datetime.now().isoformat()}\n")
        f.write(f"Python: {sys.version}\n")
        f.write(f"Platform: {sys.platform}\n")
        f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
        if getattr(sys, 'frozen', False):
            f.write(f"MEIPASS: {sys._MEIPASS}\n")
        f.write("\n" + "="*60 + "\n")
        f.write("TRACEBACK:\n")
        f.write("="*60 + "\n\n")
        traceback.print_exception(*exc_info, file=f)

    return dump_file

def main(page: ft.Page):
    """Entry point for the Modern Flet GUI."""
    try:
        # Pass splash proc to app for cleanup
        ModernApp(page, splash_proc)
    except Exception:
        dump_file = write_crash_dump(sys.exc_info())
        dump_folder = str(dump_file.parent)

        def open_dump_folder(e):
            import subprocess
            subprocess.Popen(f'explorer "{dump_folder}"')

        def copy_dump_path(e):
            page.set_clipboard(str(dump_file))
            page.show_snack_bar(ft.SnackBar(ft.Text("Path copied to clipboard!")))

        # Show error message with dump location - centered
        page.clean()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color=ft.Colors.RED, size=80),
                    ft.Text("SwitchCraft Initialization Error", size=28, weight=ft.FontWeight.BOLD),
                    ft.Container(height=10),
                    ft.Text("A critical error occurred during startup. Details saved to:", size=16),
                    ft.Text(str(dump_file), size=12, selectable=True, color=ft.Colors.BLUE_400, italic=True),
                    ft.Container(height=20),
                    ft.Row([
                        ft.ElevatedButton(
                            "Open Folder",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=open_dump_folder,
                            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_700)
                        ),
                        ft.ElevatedButton(
                            "Copy Path",
                            icon=ft.Icons.COPY,
                            on_click=copy_dump_path
                        ),
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                    ft.Container(height=30),
                    ft.Divider(color=ft.Colors.GREY_800),
                    ft.Text("Error Details:", size=14, weight=ft.FontWeight.W_500, color=ft.Colors.GREY_400),
                    ft.Text(f"{sys.exc_info()[1]}", size=14, color=ft.Colors.RED_400, italic=True),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment(0, 0),
                expand=True,
                padding=50,
            )
        )
        page.update()

if __name__ == "__main__":
    ft.app(target=main)
