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

from switchcraft.gui_modern.app import ModernApp
from switchcraft.utils.logging_handler import setup_session_logging

# Setup session logging
setup_session_logging()

def main(page: ft.Page):
    """Entry point for the Modern Flet GUI."""
    # Pass splash proc to app for cleanup
    ModernApp(page, splash_proc)

if __name__ == "__main__":
    ft.app(target=main)
