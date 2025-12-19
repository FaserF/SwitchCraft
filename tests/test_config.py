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

        # Mock winreg for Linux CI
        self.winreg_mock = MagicMock()
        self.winreg_mock.HKEY_LOCAL_MACHINE = -2147483646
        self.winreg_mock.HKEY_CURRENT_USER = -2147483647
        self.winreg_mock.KEY_READ = 131097
        self.winreg_mock.KEY_WRITE = 131078
        self.winreg_mock.REG_SZ = 1
        self.winreg_mock.REG_DWORD = 4

        sys.modules['winreg'] = self.winreg_mock

    def tearDown(self):
        # Clean up winreg mock
        if 'winreg' in sys.modules:
            del sys.modules['winreg']

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
                 if root == -2147483647: # HKCU
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

    @patch('sys.platform', 'win32')
    def test_set_user_preference_float(self):
        """Test that float values are converted to int for REG_DWORD."""
        import time
        now = time.time()  # This is a float

        with patch.object(self.winreg_mock, 'CreateKey'):
            mock_key = MagicMock()
            self.winreg_mock.OpenKey = MagicMock(return_value=mock_key)
            mock_key.__enter__ = MagicMock(return_value=mock_key)
            mock_key.__exit__ = MagicMock(return_value=False)

            # Should not raise - float should be converted to int
            SwitchCraftConfig.set_user_preference("TestFloat", now)
            # Verify SetValueEx was called with int, not float
            self.winreg_mock.SetValueEx.assert_called_once()
            call_args = self.winreg_mock.SetValueEx.call_args[0]
            # SetValueEx(key, name, reserved, type, value)
            # Index 3 is type, Index 4 is value
            self.assertEqual(call_args[3], self.winreg_mock.REG_DWORD)
            self.assertIsInstance(call_args[4], int)
            # Optional verification of converted value
            self.assertEqual(call_args[4], int(round(now)))

    @patch('sys.platform', 'win32')
    def test_set_user_preference_float_edge_cases(self):
        """Test edge cases for float conversion."""
        with patch.object(self.winreg_mock, 'CreateKey'), \
             patch.object(self.winreg_mock, 'SetValueEx') as mock_set_value:

            mock_key = MagicMock()
            self.winreg_mock.OpenKey = MagicMock(return_value=mock_key)
            mock_key.__enter__ = MagicMock(return_value=mock_key)
            mock_key.__exit__ = MagicMock(return_value=False)

            # Case 1: Negative float (Should RAISE ValueError now)
            with self.assertRaises(ValueError):
                 SwitchCraftConfig.set_user_preference("NegativeFloat", -123.45)

            # Case 2: Precision loss (Rounding)
            # 123.99 -> 124
            SwitchCraftConfig.set_user_preference("PrecisionFloat", 123.99)
            args = mock_set_value.call_args_list[-1][0]
            self.assertEqual(args[4], 124) # Expect rounded up

            # Case 3: Large float (Should RAISE ValueError if > 0xFFFFFFFF)
            large_val = 5000000000.5 # > 2^32
            with self.assertRaises(ValueError):
                SwitchCraftConfig.set_user_preference("LargeFloat", large_val)


    @patch('sys.platform', 'win32')
    def test_set_user_preference_bool(self):
        """Test that bool values are converted to 0/1 for REG_DWORD."""
        with patch.object(self.winreg_mock, 'CreateKey'):
            mock_key = MagicMock()
            self.winreg_mock.OpenKey = MagicMock(return_value=mock_key)
            mock_key.__enter__ = MagicMock(return_value=mock_key)
            mock_key.__exit__ = MagicMock(return_value=False)

            SwitchCraftConfig.set_user_preference("TestBool", True)
            call_args = self.winreg_mock.SetValueEx.call_args[0]
            self.assertEqual(call_args[4], 1)
            self.assertEqual(call_args[3], self.winreg_mock.REG_DWORD)

    @patch('sys.platform', 'win32')
    def test_set_user_preference_bool_false(self):
        """Test that False is converted to 0 for REG_DWORD."""
        with patch.object(self.winreg_mock, 'CreateKey'), \
             patch.object(self.winreg_mock, 'SetValueEx') as mock_set_value:

            mock_key = MagicMock()
            self.winreg_mock.OpenKey = MagicMock(return_value=mock_key)
            mock_key.__enter__ = MagicMock(return_value=mock_key)
            mock_key.__exit__ = MagicMock(return_value=False)

            SwitchCraftConfig.set_user_preference("TestBoolFalse", False)
            call_args = mock_set_value.call_args[0]
            # Expect 0
            self.assertEqual(call_args[4], 0)
            # Expect REG_DWORD
            self.assertEqual(call_args[3], self.winreg_mock.REG_DWORD)


if __name__ == '__main__':
    unittest.main()
