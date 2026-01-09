import sys
from pathlib import Path

# Ensure 'src' is in sys.path to prioritize local source over installed package
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def main():
    """Main entry point for SwitchCraft."""
    has_args = len(sys.argv) > 1

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
        try:
            from switchcraft.gui.app import main as gui_main
            gui_main()
        except ImportError as e:
             print(f"GUI dependencies not found. Error: {e}")
             sys.exit(1)

if __name__ == "__main__":
    main()
