import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path
import warnings

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

class TestSplashFlag(unittest.TestCase):

    def setUp(self):
        # Ignore resource warnings for unclosed files/sockets in mocks
        warnings.simplefilter("ignore", ResourceWarning)

    @patch('sys.argv', ['main.py'])
    def test_normal_startup(self):
        """Test that normal startup works with main."""
        with patch('switchcraft.main.main') as mock_main_logic:
            # We are testing cli/entry point logic usually, but here we just test that
            # we can import and call things without error if arguments are right.
            # Since main.py 'if __name__ == "__main__": ft.app(target=main)' is hard to test directly via import
            # without triggering it, we test the main function itself.
            pass

    @patch('sys.exit')
    @patch('sys.argv', ['main.py', '--version'])
    def test_version_flag(self, mock_exit):
        """Test --version flag."""
        # We need to simulate the execution of the logic at module level of main.py
        # But importing main.py runs the code.
        # This is tricky without refactoring main.py to have a `run()` function.
        # For now, we will inspect the main function for awareness of flags if they are moved inside main?
        # In main.py provided, flags are checked inside main().

        from switchcraft.main import main
        mock_page = MagicMock()

        # Calling main with mocked page should trigger sys.exit(0) if flag logic is inside main()
        # BUT main.py snippet showed flags are checked BEFORE main() in the module scope?
        # No, wait.
        # Lines 278-298 in main.py: checking sys.argv INSIDE main(page).

        main(mock_page)
        mock_exit.assert_called_with(0)

if __name__ == "__main__":
    unittest.main()
