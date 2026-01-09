
import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

import flet as ft

# Mock Page
class MockPage:
    def __init__(self):
        self.overlay = []
        self.services = [] # Check if this exists
        self.platform = "windows"
        self.window = self
        self.min_width = 0
        self.min_height = 0
    def update(self): print("Page update called")
    def add(self, *args): print("Page add called")
    def clean(self): print("Page clean called")
    def open(self, *args): print("Page open called")
    def extend(self, *args): self.overlay.extend(args)
    def append(self, *args): self.overlay.append(args)

    # Mock window props
    @property
    def width(self): return 1000
    @property
    def height(self): return 800

def test_views():
    print("--- Starting View Test ---")
    try:
        print(f"Flet Version: {ft.version}")
    except:
        print("Flet Version: Unknown (no version attr)")
    page = MockPage()

    # 1. Helper View
    print("\nTesting Helper View...")
    try:
        from switchcraft.gui_modern.views.helper_view import ModernHelperView
        view = ModernHelperView(page)
        print("Helper View Instantiated Successfully")
    except Exception as e:
        print(f"FAIL Helper View: {e}")
        import traceback
        traceback.print_exc()

    # 2. Intune View
    print("\nTesting Intune View...")
    try:
        from switchcraft.gui_modern.views.intune_view import ModernIntuneView
        view = ModernIntuneView(page)
        print("Intune View Instantiated Successfully")
        # Try build
        if hasattr(view, 'build'):
            view.build()
            print("Intune View Built Successfully")
    except Exception as e:
        print(f"FAIL Intune View: {e}")
        import traceback
        traceback.print_exc()

    # 3. Winget View
    print("\nTesting Winget View...")
    try:
        from switchcraft.gui_modern.views.winget_view import ModernWingetView
        view = ModernWingetView(page)
        print("Winget View Instantiated Successfully")
        if hasattr(view, 'build'):
            view.build()
            print("Winget View Built Successfully")
    except Exception as e:
        print(f"FAIL Winget View: {e}")
        import traceback
        traceback.print_exc()

    # 4. Analyzer View
    print("\nTesting Analyzer View...")
    try:
        from switchcraft.gui_modern.views.analyzer_view import ModernAnalyzerView
        view = ModernAnalyzerView(page)
        print("Analyzer View Instantiated Successfully")
        if hasattr(view, 'build'):
            view.build()
            print("Analyzer View Built Successfully")
    except Exception as e:
        print(f"FAIL Analyzer View: {e}")
        import traceback
        traceback.print_exc()

    # 5. Settings View
    print("\nTesting Settings View...")
    try:
        from switchcraft.gui_modern.views.settings_view import ModernSettingsView
        view = ModernSettingsView(page)
        print("Settings View Instantiated Successfully")
        if hasattr(view, 'did_mount'):
             view.did_mount()
             print("Settings View did_mount Successfully")
        if hasattr(view, 'build'):
            view.build()
            print("Settings View Built Successfully")
    except Exception as e:
        print(f"FAIL Settings View: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_views()
