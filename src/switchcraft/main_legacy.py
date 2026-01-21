import sys
from pathlib import Path

# Ensure 'src' is in sys.path to prioritize local source over installed package
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def main():
    """Main entry point for SwitchCraft."""
    has_args = len(sys.argv) > 1

    # Check for internal splash flag first
    if "--splash-internal" in sys.argv:
        try:
            # Setup extremely early logging to catch import errors
            import traceback
            import tempfile
            debug_log = Path(tempfile.gettempdir()) / "switchcraft_splash_startup.log"

            with open(debug_log, "a") as f:
                f.write(f"Splash internal started. Args: {sys.argv}\n")

            try:
                from switchcraft.gui.splash import main as splash_main
                splash_main()
                sys.exit(0)
            except Exception as e:
                with open(debug_log, "a") as f:
                    f.write(f"Splash execution failed: {e}\n{traceback.format_exc()}\n")
                sys.exit(1)
        except Exception as e:
            # Fallback if logging fails
            sys.exit(1)

    if has_args:
        if "--factory-reset" in sys.argv:
            try:
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

        try:
            from switchcraft.cli.commands import cli
            cli()
        except ImportError as e:
            print(f"Failed to load CLI: {e}")
            sys.exit(1)
    else:
        # NOTE: Splash screen removed to avoid Tkinter dual-root conflict.
        # CTk creates its own Tk root, so a separate tk.Tk() splash causes
        # "pyimage doesn't exist" errors when loading images.
        # FIX: We now run splash in a separate process to avoid these conflicts AND show it immediately.
        splash_proc = None
        try:
            import subprocess
            import os

            # Determine how to launch splash based on environment (Source vs Frozen)
            is_frozen = getattr(sys, 'frozen', False)

            cmd = []
            env = os.environ.copy()

            # Default to hiding window (for console processes)
            creationflags = 0x08000000 if sys.platform == "win32" else 0 # CREATE_NO_WINDOW

            if is_frozen:
                # In frozen app, sys.executable is the exe itself.
                # We call the exe again with a special flag to run only the splash code.
                cmd = [sys.executable, "--splash-internal"]
                # For frozen GUI app, it has no console, so we don't need to suppress it.
                # Suppressing it might suppress the GUI window itself depending on implementation.
                creationflags = 0
            else:
                # Running from source
                base_dir = Path(__file__).resolve().parent
                splash_script = base_dir / "gui" / "splash.py"
                if splash_script.exists():
                    env["PYTHONPATH"] = str(base_dir.parent) # Ensure src is in path
                    cmd = [sys.executable, str(splash_script)]
                    # Hide console window when running python script directly
                    if sys.platform == "win32":
                         creationflags = 0x08000000 # CREATE_NO_WINDOW

            if cmd:
                splash_proc = subprocess.Popen(
                    cmd,
                    env=env,
                    creationflags=creationflags
                )
        except Exception as e:
            print(f"Failed to launch splash: {e}")

        try:
            from switchcraft.gui.app import main as gui_main
            gui_main(splash_proc)
        except ImportError as e:
             print(f"GUI dependencies not found. Error: {e}")
             if splash_proc:
                 splash_proc.terminate()
             sys.exit(1)

if __name__ == "__main__":
    main()
