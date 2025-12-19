import sys
import os

if getattr(sys, 'frozen', False):
    # RUNTIME SHADOWING FIX + BUNDLING HINT
    # 1. We import 'switchcraft.gui.app' here to force PyInstaller to bundle it
    #    (Static Analysis sees this import).
    # 2. We import it at runtime to populate sys.modules, bypassing any
    #    shadowing 'switchcraft' folder that might exist in _MEIPASS.
    #    (Static Analysis sees this import).
    # 2. We import it at runtime to populate sys.modules, bypassing any
    #    shadowing 'switchcraft' folder that might exist in _MEIPASS.
    print("DEBUG: Pre-Importing addon_service explicitly...")
    try:
        import switchcraft.services.addon_service  # noqa: F401
        print("DEBUG: SUCCESS importing switchcraft.services.addon_service")
    except ImportError as e:
        print(f"DEBUG: FAILURE importing switchcraft.services.addon_service: {e}")
        # Only in frozen mode do we care deeply, dev mode has source path
        if getattr(sys, 'frozen', False):
            print(f"DEBUG: sys.path in frozen mode: {sys.path}")

    print("DEBUG: Attempting to import switchcraft.gui.app...")
    print("DEBUG: Import GUI SUCCESS.")

# Ensure local source is found (Dev mode)
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from switchcraft.main import main

if __name__ == '__main__':
    try:
        main()
    except BaseException as e:
        if isinstance(e, SystemExit) and e.code == 0:
            pass
        else:
            import traceback
            traceback.print_exc()
            print(f"\nCRITICAL FAILURE: {e}")
            print("Abnormal termination.")
    finally:
        print("\nSession ended.")
        if getattr(sys, 'frozen', False):
             # Only pause in frozen (EXE) mode, so we don't annoy dev usage
             try:
                 input("Press Enter to close this window...")
             except (EOFError, RuntimeError):
                 # stdin lost or not available, just exit
                 pass
