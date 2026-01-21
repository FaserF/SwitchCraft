import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

class TestLoadingScreen(unittest.TestCase):

    def test_loading_screen_is_displayed(self):
        """Test that loading screen is displayed in main function."""
        import flet as ft

        with patch("switchcraft.main.ModernApp"), \
             patch("switchcraft.main.start_splash"), \
             patch("switchcraft.utils.config.SwitchCraftConfig"):

            from switchcraft.main import main

            mock_page = MagicMock(spec=ft.Page)
            mock_page.web = False
            mock_page.controls = []

            # Mock add to capture controls
            def mock_add(*args):
                mock_page.controls.extend(args)
            mock_page.add.side_effect = mock_add

            main(mock_page)

            # Check if any added control looks like a loading screen
            found_loading = False
            for control in mock_page.controls:
                # Look for ProgressRing or typical loading text
                if isinstance(control, ft.Container) and isinstance(control.content, ft.Column):
                    col = control.content
                    for child in col.controls:
                        if isinstance(child, ft.ProgressRing):
                            found_loading = True
                            break

            self.assertTrue(found_loading, "Loading screen with ProgressRing should be added to page")

if __name__ == "__main__":
    unittest.main()
