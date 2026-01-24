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
    # Skip splash on WASM (subprocess not supported)
    if sys.platform == "emscripten" or sys.platform == "wasi":
        return

    global splash_proc
    try:
        from switchcraft.utils.shell_utils import ShellUtils
        from pathlib import Path

        # Resolve path to splash.py (shared with Legacy)
        base_dir = Path(__file__).resolve().parent
        splash_script = base_dir / "gui" / "splash.py"

        if splash_script.exists():
            env = os.environ.copy()
            env["PYTHONPATH"] = str(base_dir.parent)

            # Use DETACHED_PROCESS instead of CREATE_NO_WINDOW
            # This ensures the process runs independently and GUI is not suppressed
            # Note: DETACHED_PROCESS may affect splash logging/cleanup on Windows
            creationflags = subprocess.DETACHED_PROCESS if sys.platform == "win32" and "subprocess" in globals() else 0

            splash_proc = ShellUtils.Popen(
                [sys.executable, str(splash_script)],
                env=env,
                creationflags=creationflags
            )
    except Exception as e:
        print(f"Failed to start splash screen: {e}")

# Start Splash IMMEDIATELY - before any heavy imports
if __name__ == "__main__":
    # NEW: Check for CLI commands that should run without GUI/Splash
    if "--help" in sys.argv or "-h" in sys.argv or "/?" in sys.argv:
        print("SwitchCraft - Packaging Assistant for IT Professionals")
        print("\nUsage: SwitchCraft.exe [OPTIONS]")
        print("\nOptions:")
        print("  --help, -h, /?          Show this help message")
        print("  --version, -v           Show version information")
        print("  --wizard                Open Packaging Wizard on startup")
        print("  --analyzer, --all-in-one Open Installer Analyzer on startup")
        print("  --factory-reset         Delete all user data and settings (requires confirmation)")
        print("  --protocol <URL>        Handle protocol URL (switchcraft://...)")
        print("  --silent                Silent mode (minimize UI, auto-accept prompts)")
        print("\nExamples:")
        print("  SwitchCraft.exe --wizard")
        print("  SwitchCraft.exe --analyzer")
        print("  SwitchCraft.exe --factory-reset")
        print("  SwitchCraft.exe switchcraft://analyzer")
        sys.exit(0)

    if "--version" in sys.argv or "-v" in sys.argv:
        try:
            # Local import to avoid top-level dependency
            from switchcraft import __version__
            print(f"SwitchCraft v{__version__}")
        except ImportError:
            print("SwitchCraft (version unknown)")
        sys.exit(0)

    if "--factory-reset" in sys.argv:
        try:
             # Local import only for this command
            from switchcraft.utils.config import SwitchCraftConfig
            print("WARNING: This will delete ALL user data, settings, and secrets.")
            print("Are you sure? (Type 'yes' to confirm)")
            confirmation = input("> ")
            if confirmation.strip().lower() == "yes":
                SwitchCraftConfig.delete_all_application_data()
                print("Factory reset complete.")
            else:
                print("Aborted.")
            sys.exit(0)
        except Exception as e:
            print(f"Factory reset failed: {e}")
            sys.exit(1)

    start_splash()

# Now do heavy imports
import flet as ft # noqa: E402

# --- MONKEY PATCH: Fix web_entry.py legacy ft.run call ---
# web_entry.py (generated) calls ft.run(target=...) but Pyodide flet might expect ft.app or different sig.
def flexible_run(*args, **kwargs):
    # Extract target from kwargs or args
    target = kwargs.get("target")
    if not target and args:
        target = args[0]

    # Use run() if available (Flet 0.80.0+), else app()
    clean_kwargs = {k: v for k, v in kwargs.items() if k != "target"}
    if hasattr(ft, "_original_run") and ft._original_run:
        return ft._original_run(target, **clean_kwargs)
    elif hasattr(ft, "run") and ft.run != flexible_run:
        return ft.run(target, **clean_kwargs)

    return ft.app(target=target, **clean_kwargs)

# Save original run and override
if not hasattr(ft, "_original_run"):
    ft._original_run = getattr(ft, "run", None)
ft.run = flexible_run
# ---------------------------------------------------------

# Flet Universal Compatibility Patch
def patch_flet():
    # 1. Colors & Alignment
    try:
        if not hasattr(ft, "colors"):
            # ft.colors = ft.Colors # This fallback might be the issue if Colors is broken
            pass

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

    # Import i18n early for loading screen text
    from switchcraft.utils.i18n import i18n  # noqa: E402

    from switchcraft.gui_modern.app import ModernApp  # noqa: E402
    from switchcraft.utils.logging_handler import setup_session_logging  # noqa: E402
    from switchcraft.utils.shell_utils import ShellUtils # noqa: E402
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
    # Ensure i18n is available even if import failed
    try:
        from switchcraft.utils.i18n import i18n  # noqa: E402
    except Exception:
        # Fallback: create a simple i18n mock
        class SimpleI18n:
            def get(self, key, default=None):
                """
                Always return the provided default value.

                Parameters:
                    key: The lookup key (ignored by this implementation).
                    default: The value to return.

                Returns:
                    The provided `default` value.
                """
                return default
        i18n = SimpleI18n()

# Parse command line for protocol URL
_INITIAL_ACTION = None
if "parse_protocol_url" in globals() and callable(parse_protocol_url):
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
    """
    Initialize and run the Modern Flet GUI, handling early command-line options, applying compatibility patches to the provided Page, showing an immediate loading screen, and starting the ModernApp instance.

    This function:
    - Processes top-level CLI flags (--help, --version, --factory-reset, protocol handling) before performing any UI initialization.
    - Patches legacy Flet Page APIs (open, close, set_clipboard, show_snack_bar) to provide a consistent runtime surface across Flet versions.
    - Displays a lightweight loading screen immediately to ensure the user sees progress while heavy imports and initialization happen.
    - Attempts non-critical tasks such as registering a protocol handler, constructs the ModernApp, and dispatches any initial protocol-driven action.
    - On any initialization failure, writes a crash dump and replaces the UI with a crash screen that exposes the dump path and actions to open/copy it.

    Parameters:
        page (ft.Page): The Flet Page instance provided by ft.app; used for UI composition, updates, and patched legacy behaviors.
    """

    # --- Config Backend Initialization ---
    import sys  # Ensure sys is available for platform checks below
    try:
        from switchcraft.utils.config import SwitchCraftConfig, RegistryBackend, EnvBackend

        # Determine Backend Mode
        if page.web:
            # WEB MODE: Use ClientStorage for persistence across reloads!
            # SessionStoreBackend was ephemeral (RAM only).
            from switchcraft.utils.config import ClientStorageBackend

            # Switch to ClientStorageBackend
            storage_backend = ClientStorageBackend(page)
            SwitchCraftConfig.set_backend(storage_backend)

            # CRITICAL: Attach backend to page so we can restore it in callbacks
            # Flet callbacks in other threads/contexts might lose the ContextVar
            page.sc_backend = storage_backend

            # Apply Language from Session (if detected by middleware)
            if hasattr(page, 'switchcraft_session'):
                sess_lang = page.switchcraft_session.get('browser_language')
                if sess_lang and sess_lang in ['de', 'en']:
                    print(f"Applying session language: {sess_lang}")
                    SwitchCraftConfig.set_value("Language", sess_lang)
                    # Force update i18n immediate
                    from switchcraft.utils.i18n import i18n
                    i18n.set_language(sess_lang)

            print("Config Backend: ClientStorageBackend (Web/Persistent)")

            # --- WEB AUTHENTICATION (SSO) ---
            # Basic OAuth flow for Entra / GitHub
            # Requires SC_CLIENT_ID, SC_CLIENT_SECRET env vars

            provider = None
            # Check Env for Provider Selection (Simplification)
            if os.environ.get("SC_AUTH_PROVIDER") == "github":
                provider = ft.OAuthProvider(
                    client_id=os.environ.get("SC_GITHUB_CLIENT_ID", ""),
                    client_secret=os.environ.get("SC_GITHUB_CLIENT_SECRET", ""),
                    authorization_endpoint="https://github.com/login/oauth/authorize",
                    token_endpoint="https://github.com/login/oauth/access_token",
                    user_scopes=["read:user", "user:email"],
                    redirect_url=f"{page.route}/oauth_callback"
                )
            elif os.environ.get("SC_AUTH_PROVIDER") == "entra":
                 tenant_id = os.environ.get("SC_ENTRA_TENANT_ID", "common")
                 provider = ft.OAuthProvider(
                    client_id=os.environ.get("SC_ENTRA_CLIENT_ID", ""),
                    client_secret=os.environ.get("SC_ENTRA_CLIENT_SECRET", ""),
                    authorization_endpoint=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
                    token_endpoint=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                    user_scopes=["User.Read"],
                    redirect_url=f"{page.route}/oauth_callback"
                )

            if provider:
                page.login(provider) # Redirects if not logged in?
                # Note: Real implementation would check session first

        else:
            # DESKTOP MODE: Use Registry (Windows) or Env (Linux Local)
            # Default logic in SwitchCraftConfig handles this, but we can set explicitly to be safe
            if sys.platform == "win32":
                desktop_backend = RegistryBackend()
            else:
                desktop_backend = EnvBackend()

            SwitchCraftConfig.set_backend(desktop_backend)
            # CRITICAL: Attach backend to page so we can restore it in callbacks (fixing threading issues)
            page.sc_backend = desktop_backend

            print(f"Config Backend: {'RegistryBackend' if sys.platform == 'win32' else 'EnvBackend'} (Desktop)")

    except Exception as e:
        print(f"Failed to initialize Config Backend: {e}")
        # Continue... fallback defaults might work or fail gracefully later

    # --- UI Initialization ---
    page.title = "SwitchCraft"
    # Attempt to set window icon for Desktop (doesn't hurt Web if ignored)
    page.window_icon = "assets/favicon.ico"

    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.spacing = 0

    # Configure Fonts
    page.fonts = {
        "Segoe UI": "Segoe UI",
        "Roboto": "Roboto",
        "Open Sans": "Open Sans"
    }
    page.theme = ft.Theme(font_family="Segoe UI")

    # --- Handle Command Line Arguments FIRST ---
    # Moved to top-level `if __name__ == "__main__":` block to avoid starting Splash/GUI
    pass

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

    # --- Page Configuration ---
    page.title = "SwitchCraft Web" if page.web else "SwitchCraft"

    # Set favicon for web mode
    try:
        from pathlib import Path
        assets_dir = Path(__file__).parent / "assets"
        favicon_path = assets_dir / "switchcraft_logo.png"

        if page.web:
             page.favicon = "/switchcraft_logo.png"
        elif favicon_path.exists():
            page.favicon = str(favicon_path)
    except Exception:
        pass

    page.theme_mode = ft.ThemeMode.SYSTEM
    page.padding = 0
    page.spacing = 0
    # page.window_title_bar_hidden = True # Custom title bar
    # page.window_title_bar_buttons_hidden = True

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

    # Show loading screen IMMEDIATELY - FIRST THING, before ANY other operations
    # This must be the very first thing we do to ensure it's visible

    # Check if splash image exists (usually assets/splash.png)
    splash_image = None
    try:
        from pathlib import Path
        assets_dir = Path(__file__).parent / "assets"
        if (assets_dir / "splash.png").exists():
            splash_image = ft.Image(src="splash.png", width=400, border_radius=10)
    except Exception:
        pass

    loading_content = []
    if splash_image:
        loading_content = [
            splash_image,
            ft.Container(height=10),
            ft.ProgressRing(width=30, height=30, stroke_width=3, color="BLUE_400"),
        ]
    else:
        loading_content = [
            ft.Icon(ft.Icons.INSTALL_DESKTOP, size=64, color="BLUE_400"), # Reduced from 80
            ft.Text(i18n.get("app_title") or "SwitchCraft", size=26, weight=ft.FontWeight.BOLD), # Reduced from 32
            ft.Container(height=15),
            ft.ProgressRing(width=40, height=40, stroke_width=3, color="BLUE_400"), # Reduced from 50
            ft.Container(height=10),
            ft.Text(i18n.get("loading_switchcraft") or "Loading SwitchCraft...", size=14, color="GREY_400"), # Reduced from 18
        ]

    loading_container = ft.Container(
        content=ft.Column(
            controls=loading_content,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        ),
        expand=True,
        alignment=ft.Alignment(0, 0),
        bgcolor="SURFACE",
    )

    # Add loading screen FIRST - before any other operations
    page.add(loading_container)

    # Force immediate rendering - multiple updates to ensure visibility
    page.update()
    page.update()  # Second update to force render
    page.update()  # Third update to really ensure it's visible

    # Give Flet time to actually render the loading screen before heavy operations
    import time
    time.sleep(0.3)  # 300ms delay to ensure loading screen is rendered and visible
    page.update()  # Final update after delay

    # Close the native PyInstaller Splash Screen
    try:
        import pyi_splash
        pyi_splash.close()
        print("Closed PyInstaller splash screen")
    except ImportError:
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
        # Access module-level splash_proc variable (declared at module level)
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
            # Use ShellUtils for cross-platform explorer access
            ShellUtils.run_command(['explorer', dump_folder])

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
                # Use ShellUtils which handles wine prefixing on linux
                ShellUtils.run_command(['clip'], input=path_str.encode('utf-8'))
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
        # Modern Error Screen
        page.clean()

        # Determine strict web mode for button visibility
        is_web = getattr(page, 'web', False)

        actions = []

        # Open Folder (Desktop Only)
        if not is_web:
            actions.append(
                ft.ElevatedButton(
                    content=ft.Row([ft.Icon(ft.Icons.FOLDER_OPEN), ft.Text("Open Logs")], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                    on_click=open_dump_folder,
                    style=ft.ButtonStyle(bgcolor="BLUE_700", color="WHITE")
                )
            )
            actions.append(
                 ft.ElevatedButton(
                    content=ft.Row([ft.Icon(ft.Icons.DESCRIPTION), ft.Text("View File")], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                    on_click=open_dump_file
                )
            )

        # Copy Path/Error (Universal)
        actions.append(
            ft.TextButton(
                "Copy Error",
                icon=ft.Icons.COPY,
                on_click=lambda e: [
                    page.set_clipboard(f"Error: {sys.exc_info()[1]}\nFile: {dump_file}"),
                    page.show_snack_bar(ft.SnackBar(ft.Text("Error details copied!")))
                ]
            )
        )

        # Close/Reload (Contextual)
        if not is_web:
            actions.append(
                ft.ElevatedButton(
                    content=ft.Row([ft.Icon(ft.Icons.CLOSE), ft.Text("Exit")], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                    on_click=close_app,
                    style=ft.ButtonStyle(bgcolor="RED_700", color="WHITE")
                )
            )
        else:
             actions.append(
                ft.ElevatedButton(
                    content=ft.Row([ft.Icon(ft.Icons.REFRESH), ft.Text("Reload App")], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                    on_click=lambda e: page.launch_url(page.route or "/"),
                )
            )

        page.add(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Card(
                            content=ft.Container(
                                padding=40,
                                content=ft.Column(
                                    [
                                        ft.Icon(ft.Icons.GPP_MAYBE_ROUNDED, color="RED_400", size=64),
                                        ft.Text("Something went wrong", size=24, weight=ft.FontWeight.BOLD, color="ON_SURFACE"),
                                        ft.Text("SwitchCraft encountered a critical error during initialization.", size=16, color="ON_SURFACE_VARIANT"),

                                        ft.Divider(height=20, color="TRANSPARENT"),

                                        ft.Container(
                                            content=ft.Column([
                                                ft.Text("Error Details:", size=12, weight=ft.FontWeight.BOLD, color="GREY_500"),
                                                ft.Container(
                                                    content=ft.Text(
                                                        f"{sys.exc_info()[1]}",
                                                        font_family="Consolas, monospace",
                                                        color="RED_300",
                                                        size=13,
                                                        selectable=True
                                                    ),
                                                    bgcolor="GREY_900",
                                                    padding=15,
                                                    border_radius=8,
                                                    width=600
                                                ),
                                                 ft.Text(f"Log ID: {dump_file.name}", size=11, italic=True, color="GREY_600"),
                                            ]),
                                            alignment=ft.alignment.center
                                        ),

                                        ft.Divider(height=30, color="TRANSPARENT"),

                                        ft.Row(
                                            controls=actions,
                                            alignment=ft.MainAxisAlignment.CENTER,
                                            wrap=True,
                                            spacing=10
                                        )
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=5
                                ),
                            ),
                            elevation=10,
                        ),
                        ft.Container(height=20),
                        ft.Text("Please report this issue on GitHub if it persists.", size=12, color="GREY_500")
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER
                ),
                alignment=ft.alignment.center,
                expand=True,
                bgcolor="BACKGROUND",
            )
        )
        page.update()

def _ensure_pwa_manifest():
    """
    Ensure a PWA manifest.json exists in the assets directory with the correct version.
    This enables PWA installation for the self-hosted Docker version.
    """
    try:
        import json
        from pathlib import Path
        try:
            from switchcraft import __version__
        except ImportError:
            __version__ = "Unknown"

        base_dir = Path(__file__).parent
        assets_dir = base_dir / "assets"
        manifest_path = assets_dir / "manifest.json"

        # Define PWA Manifest content
        # Simplify icons to reduce 404/Cache errors
        manifest_data = {
            "name": "SwitchCraft",
            "short_name": "SwitchCraft",
            "id": "/",
            "start_url": "./?pwa=1",
            "display": "standalone",
            "background_color": "#111315",
            "theme_color": "#0066cc",
            "description": f"SwitchCraft Modern Software Management (v{__version__})",
            "icons": [
                {
                    "src": "icon-192.png",
                    "sizes": "192x192",
                    "type": "image/png"
                },
                {
                    "src": "icon-512.png",
                    "sizes": "512x512",
                    "type": "image/png"
                }
            ]
        }

        if assets_dir.exists():
            # Always overwrite/update to ensure version is current
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)
            # print(f"PWA Manifest updated: {manifest_path}")

    except Exception as e:
        print(f"Failed to generate PWA manifest: {e}")


if __name__ == "__main__":
    # Ensure PWA manifest exists for Web/Docker mode
    _ensure_pwa_manifest()

    # Fix Taskbar Icon on Windows (AppUserModelID)
    if sys.platform == "win32":
        try:
            import ctypes
            # Unique ID for the app - allows Taskbar to group windows and use correct icon
            myappid = u'FaserF.SwitchCraft.Modern.Release'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main, assets_dir="assets")
