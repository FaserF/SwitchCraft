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
    print("DEBUG: Attempting to import switchcraft.gui.app...")
    import switchcraft.gui.app
    print("DEBUG: Import SUCCESS.")

# Ensure local source is found (Dev mode)
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from switchcraft.main import cli

if __name__ == '__main__':
    cli()
