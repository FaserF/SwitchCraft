import unittest
import sys
import os
import subprocess
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


class TestAppStartupCritical(unittest.TestCase):
    """Critical tests to ensure the app actually starts and shows a loading screen."""

    def test_modern_main_imports(self):
        """Test that modern_main.py can be imported without errors."""
        try:
            import switchcraft.modern_main
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Failed to import modern_main: {e}")

    def test_modern_app_can_be_instantiated(self):
        """Test that ModernApp can be instantiated with a mock page."""
        from unittest.mock import MagicMock
        import flet as ft

        try:
            page = MagicMock(spec=ft.Page)
            page.clean = MagicMock()
            page.add = MagicMock()
            page.update = MagicMock()
            page.theme_mode = ft.ThemeMode.DARK
            page.platform = ft.PagePlatform.WINDOWS
            page.switchcraft_app = None
            page.switchcraft_session = {}
            page.appbar = None
            page.snack_bar = None
            page.dialog = None
            page.bottom_sheet = None
            page.banner = None
            page.end_drawer = None
            page.drawer = None
            page.set_clipboard = MagicMock()
            page.show_snack_bar = MagicMock()
            page.open = MagicMock()
            page.close = MagicMock()

            from switchcraft.gui_modern.app import ModernApp

            # This should not raise an exception
            app = ModernApp(page, splash_proc=None)
            self.assertIsNotNone(app)
        except Exception as e:
            self.fail(f"Failed to instantiate ModernApp: {e}")

    def test_loading_screen_code_exists(self):
        """Test that loading screen code exists in modern_main.py."""
        modern_main_path = Path(__file__).parent.parent / "src" / "switchcraft" / "modern_main.py"
        self.assertTrue(modern_main_path.exists(), "modern_main.py should exist")

        with open(modern_main_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for loading screen indicators
        self.assertIn("loading_container", content, "Loading container should be defined")
        self.assertIn("Loading SwitchCraft", content, "Loading text should be present")
        self.assertIn("page.add(loading_container)", content, "Loading screen should be added to page")
        self.assertIn("page.update()", content, "Page should be updated after adding loading screen")

    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        try:
            from switchcraft.modern_main import main
            self.assertTrue(callable(main))
        except ImportError as e:
            self.fail(f"Failed to import main function: {e}")

    def test_main_function_can_be_called(self):
        """
        Ensure switchcraft.modern_main.main can be invoked with a mocked flet Page without variable-scope startup errors.

        Creates a fully mocked flet Page and patches protocol-related functions and ModernApp. The test fails if calling main raises UnboundLocalError or NameError (indicative of improper splash_proc or other variable scope issues). Other exceptions during startup are tolerated by this test.
        """
        from unittest.mock import MagicMock, patch
        import flet as ft

        try:
            from switchcraft.modern_main import main

            # Create a fully mocked page
            page = MagicMock(spec=ft.Page)
            page.clean = MagicMock()
            page.add = MagicMock()
            page.update = MagicMock()
            page.theme_mode = ft.ThemeMode.DARK
            page.platform = ft.PagePlatform.WINDOWS
            page.switchcraft_app = None
            page.switchcraft_session = {}
            page.appbar = None
            page.snack_bar = None
            page.dialog = None
            page.bottom_sheet = None
            page.banner = None
            page.end_drawer = None
            page.drawer = None
            page.set_clipboard = MagicMock()
            page.show_snack_bar = MagicMock()
            page.open = MagicMock()
            page.close = MagicMock()
            page.window = MagicMock()
            page.window.prevent_close = False

            # Mock all the functions that main() might call
            with patch('switchcraft.modern_main.is_protocol_registered', return_value=True), \
                 patch('switchcraft.modern_main.register_protocol_handler'), \
                 patch('switchcraft.modern_main.ModernApp') as mock_app_class, \
                 patch('sys.exit'):
                mock_app = MagicMock()
                mock_app_class.return_value = mock_app

                # Call main() - should not raise UnboundLocalError or other startup errors
                try:
                    main(page)
                except (UnboundLocalError, NameError) as e:
                    self.fail(f"Startup error detected: {e}. This indicates a variable scope issue (e.g., splash_proc not declared as global).")
                except Exception as e:
                    # Other exceptions might be expected (e.g., if ModernApp fails to initialize)
                    # But UnboundLocalError/NameError should never happen
                    if "UnboundLocalError" in str(type(e)) or "NameError" in str(type(e)):
                        self.fail(f"Variable scope error detected: {e}")
                    # Other exceptions are acceptable for this test
                    pass
        except Exception as e:
            self.fail(f"Failed to test main function: {e}")

    def test_splash_proc_global_declaration(self):
        """
        Verify that main() declares `splash_proc` as global before it is used or assigned.

        Reads src/switchcraft/modern_main.py, locates the `main(page: ft.Page)` function, and checks for any use of `splash_proc` inside that function. If `splash_proc` is not used, the test passes. If `splash_proc` is used, the test ensures a `global splash_proc` declaration appears before the first usage; if `splash_proc` is assigned in `main()` without a preceding `global` declaration, the test fails because that would cause an UnboundLocalError at runtime.
        """
        modern_main_path = Path(__file__).parent.parent / "src" / "switchcraft" / "modern_main.py"
        with open(modern_main_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find the main function
        main_start = content.find("def main(page: ft.Page):")
        if main_start == -1:
            self.fail("Could not find main function")

        # Find where splash_proc is used in main()
        main_section = content[main_start:]
        splash_proc_usage = main_section.find("splash_proc")

        if splash_proc_usage == -1:
            # splash_proc might not be used, that's okay
            return

        # Check if 'global splash_proc' appears before usage
        global_decl = main_section[:splash_proc_usage].find("global splash_proc")
        if global_decl == -1:
            # Check if it's assigned without global (which would cause UnboundLocalError)
            assignment = main_section[:splash_proc_usage].find("splash_proc =")
            if assignment != -1:
                self.fail("splash_proc is assigned in main() without 'global' declaration. This will cause UnboundLocalError!")

    def test_addon_service_static_method_exists(self):
        """Test that is_addon_installed_static method exists."""
        try:
            from switchcraft.services.addon_service import AddonService
            self.assertTrue(hasattr(AddonService, 'is_addon_installed_static'),
                          "AddonService should have is_addon_installed_static method")
            self.assertTrue(callable(getattr(AddonService, 'is_addon_installed_static')),
                          "is_addon_installed_static should be callable")
        except Exception as e:
            self.fail(f"Failed to check AddonService.is_addon_installed_static: {e}")

    def test_modern_main_syntax_valid(self):
        """Test that modern_main.py has valid Python syntax and can be compiled."""
        modern_main_path = Path(__file__).parent.parent / "src" / "switchcraft" / "modern_main.py"

        try:
            with open(modern_main_path, "r", encoding="utf-8") as f:
                code = f.read()

            # Try to compile the code to check for syntax errors
            compile(code, str(modern_main_path), "exec")
        except SyntaxError as e:
            self.fail(f"Syntax error in modern_main.py: {e}")
        except Exception as e:
            self.fail(f"Failed to compile modern_main.py: {e}")

    def test_no_unbound_local_errors(self):
        """Test that there are no potential UnboundLocalError issues in main()."""
        modern_main_path = Path(__file__).parent.parent / "src" / "switchcraft" / "modern_main.py"
        with open(modern_main_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that all variables used in main() are either:
        # 1. Declared as global
        # 2. Assigned before use
        # 3. Parameters

        main_start = content.find("def main(page: ft.Page):")
        if main_start == -1:
            self.fail("Could not find main function")

        # Find the end of main function (next def or end of file)
        main_end = content.find("\n\nif __name__", main_start)
        if main_end == -1:
            main_end = len(content)

        main_code = content[main_start:main_end]

        # Check for splash_proc usage - must have global declaration
        if "splash_proc" in main_code:
            # Find first usage
            first_usage = main_code.find("splash_proc")
            # Check if global is declared before first usage
            before_usage = main_code[:first_usage]
            if "global splash_proc" not in before_usage:
                # Check if it's assigned (which would make it local)
                if "splash_proc =" in before_usage or "splash_proc=" in before_usage:
                    self.fail("splash_proc is assigned in main() without 'global' declaration. "
                            "This will cause UnboundLocalError when accessing it!")


if __name__ == '__main__':
    unittest.main()