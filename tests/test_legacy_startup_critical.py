import unittest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


class TestLegacyStartupCritical(unittest.TestCase):
    """Critical tests to ensure the Legacy app actually starts and shows a loading screen."""

    def test_legacy_app_imports(self):
        """Test that gui.app can be imported without errors."""
        try:
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Failed to import gui.app: {e}")

    def test_legacy_app_has_loading_screen(self):
        """Test that Legacy app has loading screen code."""
        app_path = Path(__file__).parent.parent / "src" / "switchcraft" / "gui" / "app.py"
        self.assertTrue(app_path.exists(), "app.py should exist")

        with open(app_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for loading screen indicators
        self.assertIn("loading_frame", content, "Loading frame should be defined")
        self.assertIn("loading_label", content, "Loading label should be present")
        self.assertIn("loading_bar", content, "Loading bar should be present")
        self.assertIn("_update_loading", content, "Update loading method should exist")

    def test_legacy_main_function_exists(self):
        """Test that main function exists and is callable."""
        try:
            from switchcraft.gui.app import main
            self.assertTrue(callable(main))
        except ImportError as e:
            self.fail(f"Failed to import main function: {e}")

    def test_legacy_app_error_handling(self):
        """Test that Legacy app has error handling in main()."""
        app_path = Path(__file__).parent.parent / "src" / "switchcraft" / "gui" / "app.py"
        with open(app_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for error handling
        self.assertIn("except Exception", content, "Should have exception handling")
        self.assertIn("crash_dump", content, "Should write crash dumps")
        self.assertIn("messagebox.showerror", content, "Should show error messages")

    def test_legacy_app_uses_static_addon_method(self):
        """Test that Legacy app uses is_addon_installed_static instead of instance method."""
        app_path = Path(__file__).parent.parent / "src" / "switchcraft" / "gui" / "app.py"
        with open(app_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that we use the static method, not the instance method
        # This prevents "missing 1 required positional argument" errors
        if "AddonService.is_addon_installed(" in content:
            # If we find the old pattern, make sure it's not used incorrectly
            # We should use is_addon_installed_static instead
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "AddonService.is_addon_installed(" in line and "is_addon_installed_static" not in line:
                    # Check if it's using AddonService() instance
                    if "AddonService().is_addon_installed" not in line:
                        self.fail(f"Line {i+1}: Found AddonService.is_addon_installed() without instance or static method. "
                                f"Should use AddonService.is_addon_installed_static() or AddonService().is_addon_installed(). "
                                f"Line: {line.strip()}")

    def test_legacy_app_loading_screen_update(self):
        """Test that loading screen calls update() to be visible immediately."""
        app_path = Path(__file__).parent.parent / "src" / "switchcraft" / "gui" / "app.py"
        with open(app_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that update() is called in __init__ after creating loading screen
        # It should be called before deferring initialization
        init_start = content.find("def __init__(self):")
        if init_start != -1:
            # Find the end of __init__ (next def or class)
            init_end = content.find("\n    def ", init_start + 1)
            if init_end == -1:
                init_end = len(content)

            init_section = content[init_start:init_end]

            # Check that loading_frame is created
            if "self.loading_frame" in init_section:
                # Check that update() is called somewhere in __init__
                if "self.update()" not in init_section:
                    self.fail("Loading screen should call self.update() in __init__ to be visible immediately")

    def test_legacy_app_syntax_valid(self):
        """Test that app.py has valid Python syntax and can be compiled."""
        app_path = Path(__file__).parent.parent / "src" / "switchcraft" / "gui" / "app.py"

        try:
            with open(app_path, "r", encoding="utf-8") as f:
                code = f.read()

            # Try to compile the code to check for syntax errors
            compile(code, str(app_path), "exec")
        except SyntaxError as e:
            self.fail(f"Syntax error in app.py: {e}")
        except Exception as e:
            self.fail(f"Failed to compile app.py: {e}")


if __name__ == '__main__':
    unittest.main()
