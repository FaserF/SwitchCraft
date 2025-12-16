import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mocking winreg before importing config if possible
# But we can patch it inside the test methods

from switchcraft.utils.config import SwitchCraftConfig

class TestSwitchCraftConfig(unittest.TestCase):

    def setUp(self):
        # Reset environment variables
        if 'SWITCHCRAFT_DEBUG' in os.environ:
            del os.environ['SWITCHCRAFT_DEBUG']

    @patch('sys.platform', 'win32')
    @patch('switchcraft.utils.config.SwitchCraftConfig._read_registry')
    def test_precedence_policy_over_preference(self, mock_read_reg):
        """Test that Policy (HKLM/HKCU) overrides Preference (HKLM/HKCU)."""

        # Scenario:
        # Machine Policy = None
        # User Policy = 1 (Intune Set)
        # Machine Preference = 0
        # User Preference = 0

        def side_effect(root, key, value_name):
            if "Policies" in key:
                 # Simulate User Policy being set
                 if root == -2147483647: # HKCU (approximate value check, better to check by arg matching)
                     return 1
                 return None
            return 0 # Preferences are set to 0

        # Refined side effect based on call order in config.py:
        # 1. HKLM Policy
        # 2. HKCU Policy
        # 3. HKLM Pref
        # 4. HKCU Pref

        mock_read_reg.side_effect = [None, 1, 0, 0]

        val = SwitchCraftConfig.get_value("DebugMode")
        self.assertEqual(val, 1, "Should respect User Policy value (1) over Preference (0)")

    @patch('sys.platform', 'win32')
    @patch('switchcraft.utils.config.SwitchCraftConfig._read_registry')
    def test_precedence_machine_policy_highest(self, mock_read_reg):
        """Test that Machine Policy has highest priority."""
        # 1. HKLM Policy = 2
        # 2. HKCU Policy = 1
        # ...
        mock_read_reg.side_effect = [2, 1, 0, 0]

        val = SwitchCraftConfig.get_value("DebugMode")
        self.assertEqual(val, 2, "Should respect Machine Policy")

    @patch('sys.platform', 'win32')
    @patch('switchcraft.utils.config.SwitchCraftConfig._read_registry')
    def test_fallback_to_default(self, mock_read_reg):
        """Test fallback when no registry keys exist."""
        mock_read_reg.return_value = None

        val = SwitchCraftConfig.get_value("MissingKey", default="default_val")
        self.assertEqual(val, "default_val")

    @patch('sys.platform', 'win32')
    @patch('switchcraft.utils.config.SwitchCraftConfig.get_value')
    def test_is_debug_mode_registry(self, mock_get_value):
        mock_get_value.return_value = 1
        self.assertTrue(SwitchCraftConfig.is_debug_mode())

        mock_get_value.return_value = 0
        self.assertFalse(SwitchCraftConfig.is_debug_mode())

    def test_is_debug_mode_env(self):
        os.environ['SWITCHCRAFT_DEBUG'] = '1'
        self.assertTrue(SwitchCraftConfig.is_debug_mode())

if __name__ == '__main__':
    unittest.main()
