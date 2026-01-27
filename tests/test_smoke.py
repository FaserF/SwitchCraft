import unittest
import sys
import subprocess

class TestSmoke(unittest.TestCase):
    """Smoke tests to ensure no immediate crash on startup."""

    def test_import_analyzers(self):
        """Verify analyzers can be imported."""
        try:
            from switchcraft.analyzers.exe import ExeAnalyzer  # noqa: F401
            from switchcraft.analyzers.msi import MsiAnalyzer  # noqa: F401
            from switchcraft.analyzers.universal import UniversalAnalyzer  # noqa: F401
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import analyzers: {e}")

    def test_import_gui(self):
        """Verify GUI module can be imported (without initializing App)."""
        try:
            # Only test import, do not instantiate App() as it needs display
            import switchcraft.gui.app  # noqa: F401
            self.assertTrue(True)
        except ImportError as e:
            # Skip if GUI dependencies are not installed (customtkinter is optional)
            if "customtkinter" in str(e) or "No module named 'customtkinter'" in str(e):
                self.skipTest(f"GUI dependencies not installed: {e}")
            self.fail(f"Failed to import GUI module: {e}")

    def test_cli_version(self):
        """Verify CLI --version runs without error."""
        import os
        env = os.environ.copy()
        # Add src to PYTHONPATH so it finds switchcraft module without installation
        src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
        env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

        cmd = [sys.executable, "-m", "switchcraft.main", "--version"]
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0)
        self.assertIn("SwitchCraft", result.stdout)

if __name__ == '__main__':
    unittest.main()
