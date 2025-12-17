import unittest
import sys
import subprocess
from pathlib import Path

class TestSmoke(unittest.TestCase):
    """Smoke tests to ensure no immediate crash on startup."""

    def test_import_analyzers(self):
        """Verify analyzers can be imported."""
        try:
            from switchcraft.analyzers.exe import ExeAnalyzer
            from switchcraft.analyzers.msi import MsiAnalyzer
            from switchcraft.analyzers.universal import UniversalAnalyzer
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import analyzers: {e}")

    def test_import_gui(self):
        """Verify GUI module can be imported (without initializing App)."""
        try:
            # Only test import, do not instantiate App() as it needs display
            import switchcraft.gui.app
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import GUI module: {e}")

    def test_cli_version(self):
        """Verify CLI --version runs without error."""
        cmd = [sys.executable, "-m", "switchcraft.main", "--version"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("SwitchCraft", result.stdout)

if __name__ == '__main__':
    unittest.main()
