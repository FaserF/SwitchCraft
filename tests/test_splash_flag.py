import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from switchcraft import main as app_main
try:
    import switchcraft.gui.app
except ImportError:
    pass

class TestSplashFlag(unittest.TestCase):

    @patch('sys.argv', ['main.py', '--splash-internal'])
    @patch('switchcraft.gui.splash.main')
    @patch('sys.exit')
    def test_splash_internal_flag(self, mock_exit, mock_splash):
        """Test that --splash-internal flag calls splash.main() and exits."""
        # Make sys.exit raise SystemExit so execution stops
        mock_exit.side_effect = SystemExit

        with self.assertRaises(SystemExit):
            app_main.main()

        # Verify splash.main was called
        mock_splash.assert_called_once()

        # Verify sys.exit(0) was called
        mock_exit.assert_called_once_with(0)

    @patch('sys.argv', ['main.py'])
    @patch('subprocess.Popen')
    @patch('switchcraft.gui.app.main')
    def test_normal_startup_launches_splash(self, mock_gui_main, mock_popen):
        """Test that normal startup attempts to launch splash process."""
        # Mock Path.exists to return True for splash.py
        original_exists = Path.exists

        try:
           with patch('pathlib.Path.exists', return_value=True):
                app_main.main()

                # Verify subprocess.Popen was called to start splash
                mock_popen.assert_called_once()
                args = mock_popen.call_args[0][0]
                self.assertEqual(args[0], sys.executable)
                # We can't strictly compare the path string as it depends on absolute paths,
                # but we can check it ends with splash.py
                self.assertTrue(str(args[1]).endswith('splash.py'))

                # Verify gui_main was called with the process
                mock_gui_main.assert_called_once()
        except ImportError:
             pass # Skipped if dependencies missing

if __name__ == '__main__':
    unittest.main()
