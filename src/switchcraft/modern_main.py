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

from switchcraft.gui_modern.app import ModernApp  # noqa: E402
from switchcraft.utils.logging_handler import setup_session_logging  # noqa: E402

# Setup session logging
setup_session_logging()

def write_crash_dump(exc_info):
    """Write crash dump to a file for debugging."""
    import traceback
    from datetime import datetime
    from pathlib import Path

    # Write to user's home directory or temp
    dump_dir = Path.home() / "SwitchCraft_Logs"
    dump_dir.mkdir(exist_ok=True)

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
        # Show error message with dump location
        page.clean()
        page.add(
            ft.Column([
                ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED, size=60),
                ft.Text("SwitchCraft encountered an error", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(f"Crash dump saved to:", size=14),
                ft.Text(str(dump_file), size=12, selectable=True, color=ft.Colors.BLUE),
                ft.Text(f"\nError: {sys.exc_info()[1]}", size=14, color=ft.Colors.RED),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER)
        )
        page.update()

if __name__ == "__main__":
    ft.app(target=main)
