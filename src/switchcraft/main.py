import sys
from pathlib import Path

# Ensure 'src' is in sys.path to prioritize local source over installed package
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def main():
    """
    Main entry point for SwitchCraft.
    Detects if arguments are passed.
    - If args present: Delegates to CLI (switchcraft.cli.commands).
    - If no args: Launches GUI (switchcraft.gui.app).
    """

    # Check if arguments provided (excluding script name)
    # Note: When running via PyInstaller, sys.argv[0] is the executable.
    has_args = len(sys.argv) > 1

    if has_args:
        try:
            from switchcraft.cli.commands import cli

            # Smart Argument Detection for Backward Compatibility
            # If the first argument is a file or path, inject 'analyze'
            first_arg = sys.argv[1]
            path_arg = Path(first_arg)

            # Simple heuristic: if it looks like a path/file, or isn't a known command
            known_commands = ['analyze', 'config', 'winget', 'intune', 'addons', '--help', '--json']
            if first_arg not in known_commands and not first_arg.startswith("-"):
                 # Inject 'analyze'
                 sys.argv.insert(1, 'analyze')

            cli()
        except ImportError as e:
            print(f"Failed to load CLI: {e}")
            sys.exit(1)
    else:
        try:
            # Lazy import to avoid loading GUI libs (Tkinter, CustomTkinter, PIL)
            # if we were just importing main.py for some reason.
            from switchcraft.gui.app import main as gui_main
            gui_main()
        except ImportError as e:
             # Basic fallback if GUI missing (should not happen in Standard build)
             print("GUI dependencies not found. Launching CLI help.")
             print(f"Error: {e}")

             # Fallback to CLI help
             try:
                from switchcraft.cli.commands import cli
                # Simulate passing '--help' so click prints help instead of nothing
                sys.argv.append('--help')
                cli()
             except Exception:
                 print("Critical: Could not launch GUI or CLI.")
                 sys.exit(1)

if __name__ == "__main__":
    main()
