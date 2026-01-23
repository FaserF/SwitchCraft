import sys
import os

if getattr(sys, 'frozen', False):
    try:
        import switchcraft.gui.app # noqa: F401
    except ImportError:
        pass

# Ensure local source is found (Dev mode)
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from switchcraft.main_legacy import main


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
        if getattr(sys, 'frozen', False):
             # Only pause in frozen (EXE) mode, so we don't annoy dev usage
             # But suppress PyInstaller cleanup warnings about temp dir
             import warnings
             warnings.filterwarnings('ignore', category=ResourceWarning)

             try:
                 # Small delay to allow PyInstaller to clean up temp directory
                 import time
                 time.sleep(0.1)
                 input("Press Enter to close this window...")
             except (EOFError, RuntimeError):
                 # stdin lost or not available, just exit
                 pass
