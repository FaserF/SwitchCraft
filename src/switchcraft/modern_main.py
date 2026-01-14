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
    except Exception as e:
        print(f"Failed to start splash screen: {e}")

# Start Splash IMMEDIATELY - before any heavy imports
if __name__ == "__main__":
    start_splash()

# Now do heavy imports
import flet as ft # noqa: E402

# Flet Universal Compatibility Patch
def patch_flet():
    # 1. Colors & Alignment
    try:
        if not hasattr(ft, "colors"):
            ft.colors = ft.Colors
    except Exception:
        # Flet version likely compatible or different structure
        pass

    try:
        _ = ft.alignment.center
    except AttributeError:
        if hasattr(ft, 'Alignment'):
            if not hasattr(ft, 'alignment') or ft.alignment is None:
                class DummyAlignment:
                    pass
                ft.alignment = DummyAlignment()
            ft.alignment.center = ft.Alignment(0, 0)
        elif hasattr(ft, 'alignment') and hasattr(ft.alignment, 'CENTER'):
            ft.alignment.center = ft.alignment.CENTER

    # 2. Page Methods (Open, Dialogs, Clipboard)
    # We will wrap page methods in main() to handle version differences
    pass

patch_flet()

_IMPORT_ERROR = None
_IMPORT_EXC_INFO = None

try:
    # Explicitly import updater to ensure PyInstaller bundles it
    import switchcraft.utils.app_updater # noqa: F401

    from switchcraft.gui_modern.app import ModernApp  # noqa: E402
    from switchcraft.utils.logging_handler import setup_session_logging  # noqa: E402
    from switchcraft.utils.protocol_handler import (
        register_protocol_handler,
        parse_protocol_url,
        is_protocol_registered
    )  # noqa: E402
    # Setup session logging
    setup_session_logging()
except Exception:
    _IMPORT_ERROR = True
    _IMPORT_EXC_INFO = sys.exc_info()

# Parse command line for protocol URL
_INITIAL_ACTION = None
for i, arg in enumerate(sys.argv):
    if arg == "--protocol" and i + 1 < len(sys.argv):
        try:
            _INITIAL_ACTION = parse_protocol_url(sys.argv[i + 1])
        except Exception:
            pass
        break
    elif arg.startswith("switchcraft://"):
        try:
            _INITIAL_ACTION = parse_protocol_url(arg)
        except Exception:
            pass
        break

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
        f.write("SwitchCraft Crash Dump\n")
        f.write(f"Time: {datetime.now().isoformat()}\n")
        f.write(f"Python: {sys.version}\n")
        f.write(f"Platform: {sys.platform}\n")
        f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
        if getattr(sys, 'frozen', False):
            f.write(f"MEIPASS: {sys._MEIPASS}\n")

        # Extended Metadata
        try:
            from switchcraft import __version__
            f.write(f"App Version: {__version__}\n")
        except Exception:
             f.write("App Version: unknown\n")

        try:
             from switchcraft.utils.config import SwitchCraftConfig
             channel = SwitchCraftConfig.get_value("UpdateChannel", "stable")
             f.write(f"Update Channel: {channel}\n")
        except Exception:
             f.write("Update Channel: unknown\n")

        f.write("\n" + "="*60 + "\n")
        f.write("TRACEBACK:\n")
        f.write("="*60 + "\n\n")
        traceback.print_exception(*exc_info, file=f)

        # Enhanced Debugging: Inspect Module Loader
        f.write("\n" + "="*60 + "\n")
        f.write("DEBUG: Internal Module Inspection:\n")
        f.write("="*60 + "\n")
        try:
            import pkgutil
            import switchcraft.gui_modern.views
            f.write(f"Views Package Path: {switchcraft.gui_modern.views.__path__}\n")
            f.write("Available Modules in 'switchcraft.gui_modern.views':\n")
            for importer, name, ispkg in pkgutil.iter_modules(switchcraft.gui_modern.views.__path__):
                f.write(f" - {name} (Package: {ispkg})\n")
        except Exception as e:
            f.write(f"Failed to inspect modules: {e}\n")

        if getattr(sys, 'frozen', False):
            # Also dump sys.modules keys related to views
            f.write("\nLoaded View Modules:\n")
            for k in sorted(sys.modules.keys()):
                if "gui_modern.views" in k:
                    f.write(f" - {k}\n")

    return dump_file

def main(page: ft.Page):
    """Entry point for the Modern Flet GUI."""
    # --- Robust Page Patching ---

    # Patch page.open (Flet < 0.21.0 used page.dialog.open = True)
    if not hasattr(page, "open"):
        def legacy_open(control):
            if isinstance(control, ft.AlertDialog):
                page.dialog = control
                page.dialog.open = True
            elif isinstance(control, ft.BottomSheet):
                page.bottom_sheet = control
                page.bottom_sheet.open = True
            elif isinstance(control, ft.Banner):
                page.banner = control
                page.banner.open = True
            elif isinstance(control, ft.NavigationDrawer):
                page.end_drawer = control
                page.end_drawer.open = True
            page.update()
        page.open = legacy_open

    # Patch page.close
    if not hasattr(page, "close"):
        def legacy_close(control=None):
            if control:
                control.open = False
            elif page.dialog:
                page.dialog.open = False
            elif page.bottom_sheet:
                page.bottom_sheet.open = False
            elif page.banner:
                page.banner.open = False
            elif page.end_drawer:
                page.end_drawer.open = False
            elif page.drawer:
                page.drawer.open = False
            page.update()
        page.close = legacy_close

    # Patch page.set_clipboard
    if not hasattr(page, "set_clipboard"):
        # Older Flet might have it directly on the window or not at all
        def dummy_set_clipboard(text):
            print(f"Clipboard (fallback): {text}")
        page.set_clipboard = getattr(page, "set_clipboard", dummy_set_clipboard)

    # Patch page.show_snack_bar
    if not hasattr(page, "show_snack_bar"):
        def legacy_show_snack(snack):
            page.snack_bar = snack
            page.snack_bar.open = True
            page.update()
        page.show_snack_bar = legacy_show_snack

    # --- End Patching ---

    # Check for Import Errors first
    if _IMPORT_ERROR:
        # Re-raise to trigger the exception handler below
        # Or better, manually trigger the crash UI logic directly
        # to ensure we use the _IMPORT_EXC_INFO
        try:
             raise _IMPORT_EXC_INFO[1].with_traceback(_IMPORT_EXC_INFO[2])
        except Exception:
             # This will be caught by the general catch-all below usually,
             # but we want to ensure we pass the specific EXC_INFO to write_crash_dump
             pass

    try:
        # If we had an import error, we shouldn't even be here effectively,
        # but let's handle the control flow.
        if _IMPORT_ERROR:
             raise _IMPORT_EXC_INFO[1] # Re-raise for the except block

        # Auto-register protocol handler on first run
        try:
            if not is_protocol_registered():
                register_protocol_handler()
        except Exception:
            pass  # Non-critical

        # Pass splash proc to app for cleanup
        app = ModernApp(page, splash_proc=splash_proc)

        # Handle initial action from protocol URL
        if _INITIAL_ACTION:
            action = _INITIAL_ACTION.get("action", "home")
            from switchcraft.gui_modern.nav_constants import NavIndex

            action_map = {
                "notifications": lambda: app._toggle_notification_drawer(None),
                "settings": lambda: app.goto_tab(NavIndex.SETTINGS),
                "updates": lambda: app.goto_tab(NavIndex.SETTINGS_UPDATES),
                "analyzer": lambda: app.goto_tab(NavIndex.ANALYZER),
                "home": lambda: app.goto_tab(NavIndex.HOME),
            }

            handler = action_map.get(action)
            if handler:
                try:
                    handler()
                except Exception:
                    pass
    except Exception:
        # Ensure window can be closed even if the app failed during setup
        try:
            # Handle both old and new window closing APIs
            if hasattr(page, "window"):
                page.window.prevent_close = False
            elif hasattr(page, "window_prevent_close"):
                page.window_prevent_close = False
        except Exception:
            pass

        dump_file = write_crash_dump(sys.exc_info())
        dump_folder = str(dump_file.parent)

        def open_dump_folder(e):
            import subprocess
            subprocess.Popen(f'explorer "{dump_folder}"')

        def open_dump_file(e):
            import os
            try:
                os.startfile(dump_file)
            except Exception:
                pass

        def copy_dump_path(e):
            path_str = str(dump_file)
            # 1. Try Flet Clipboard
            try:
                page.set_clipboard(path_str)
                page.show_snack_bar(ft.SnackBar(ft.Text("Path copied to clipboard!")))
                page.update()
            except Exception:
                pass

            # 2. Force Windows Clipboard (cmd /c check)
            try:
                import subprocess
                # Use shell=False and pass input via stdin to avoid injection
                if sys.platform == "win32":
                     subprocess.run(['clip'], input=path_str.encode('utf-8'), check=False)
            except Exception:
                pass

        def close_app(e):
            import ctypes
            # Nuclear option: Win32 ExitProcess
            # This cannot be blocked or ignored by Python/Flet
            if sys.platform == "win32":
                try:
                    ctypes.windll.kernel32.ExitProcess(1)
                except Exception:
                    sys.exit(1)
            else:
                 sys.exit(1)

        # Show error message with dump location - centered
        page.clean()
        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ERROR_OUTLINE_ROUNDED, color="RED", size=80),
                    ft.Text("SwitchCraft Initialization Error", size=28, weight=ft.FontWeight.BOLD),
                    ft.Container(height=10),
                    ft.Text("A critical error occurred during startup.\nDetails saved to log file.", size=16, text_align="center"),
                    ft.Text(str(dump_file), size=12, selectable=True, color="BLUE_400", weight="bold"),
                    ft.Container(height=20),
                    ft.Row([
                        ft.ElevatedButton(
                            "Open Dump Folder",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=open_dump_folder,
                            style=ft.ButtonStyle(color="WHITE", bgcolor="BLUE_700")
                        ),
                        ft.ElevatedButton(
                            "Open Dump File",
                            icon=ft.Icons.DESCRIPTION,
                            on_click=open_dump_file,
                            style=ft.ButtonStyle(color="WHITE", bgcolor="BLUE_700")
                        ),
                        ft.ElevatedButton(
                            "Copy Path",
                            icon=ft.Icons.COPY,
                            on_click=copy_dump_path
                        ),
                        ft.ElevatedButton(
                            "Close App",
                            icon=ft.Icons.CLOSE,
                            on_click=close_app,
                            style=ft.ButtonStyle(color="WHITE", bgcolor="RED_700")
                        ),
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=20, wrap=True),
                    ft.Container(height=30),
                    ft.Divider(color="GREY_800"),
                    ft.Text("Error Details:", size=14, weight=ft.FontWeight.W_500, color="GREY_400"),
                    ft.Text(f"{sys.exc_info()[1]}", size=14, color="RED_400", italic=True),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.Alignment(0, 0),
                expand=True,
                padding=50,
            )
        )
        page.update()

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
