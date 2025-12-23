
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure we load from local src, not installed site-packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

try:
    from switchcraft.utils.config import SwitchCraftConfig
except ImportError:
    pass

class TestSecureConfig(unittest.TestCase):

    def setUp(self):
        # Patch keyring globally since it is imported inside functions
        self.keyring_get_patcher = patch('keyring.get_password')
        self.mock_keyring_get = self.keyring_get_patcher.start()
        self.mock_keyring_get.return_value = None

        self.keyring_set_patcher = patch('keyring.set_password')
        self.mock_keyring_set = self.keyring_set_patcher.start()

        self.keyring_del_patcher = patch('keyring.delete_password')
        self.mock_keyring_del = self.keyring_del_patcher.start()

        # Mock sys.platform to win32
        self.sys_platform_patcher = patch('sys.platform', 'win32')
        self.sys_platform_patcher.start()

        # Mock winreg via sys.modules
        self.mock_winreg = MagicMock()
        # Set constants used in config.py
        self.mock_winreg.HKEY_LOCAL_MACHINE = 1
        self.mock_winreg.HKEY_CURRENT_USER = 2
        self.mock_winreg.KEY_READ = 131097
        self.mock_winreg.KEY_WRITE = 131078

        self.winreg_patcher = patch.dict(sys.modules, {'winreg': self.mock_winreg})
        self.winreg_patcher.start()

    def tearDown(self):
        self.keyring_get_patcher.stop()
        self.keyring_set_patcher.stop()
        self.keyring_del_patcher.stop()
        self.sys_platform_patcher.stop()
        self.winreg_patcher.stop()

    def test_get_secure_value_policy_precedence(self):
        # Simulate HKLM Policy presence
        # config._read_registry calls winreg.OpenKey
        # We need to ensure OpenKey returns a context manager
        self.mock_winreg.OpenKey.return_value.__enter__.return_value = MagicMock()
        self.mock_winreg.QueryValueEx.return_value = ("PolicySecret", 1)

        # Should return policy value even if keyring has something
        self.mock_keyring_get.return_value = "KeyringSecret"

        val = SwitchCraftConfig.get_secure_value("MySecret")
        self.assertEqual(val, "PolicySecret")

    def test_get_secure_value_keyring(self):
        # Simulate No Policy
        self.mock_winreg.OpenKey.side_effect = FileNotFoundError

        # Simulate Keyring presence
        self.mock_keyring_get.return_value = "KeyringSecret"

        val = SwitchCraftConfig.get_secure_value("MySecret")
        self.assertEqual(val, "KeyringSecret")

    def test_migration_from_registry(self):
        # Simulate No Policy
        # Simulate No Keyring
        self.mock_keyring_get.return_value = None

        # Simulate Registry Preference Presence (Legacy)
        # We need to mock _read_registry carefully since get_secure_value calls it multiple times
        # 1. HKLM Policy -> Fail
        # 2. HKCU Policy -> Fail
        # 3. Keyring -> None
        # 4. HKCU Pref -> "LegacySecret"

        with patch.object(SwitchCraftConfig, '_read_registry') as mock_read:
            def side_effect(root, path, name):
                if path == SwitchCraftConfig.POLICY_PATH:
                    return None
                if path == SwitchCraftConfig.PREFERENCE_PATH and root == self.mock_winreg.HKEY_CURRENT_USER:
                    return "LegacySecret"
                return None
            mock_read.side_effect = side_effect

            # We also need to mock winreg.DeleteValue for the cleanup part
            self.mock_winreg.OpenKey.side_effect = None # Reset side effect for openkey used in migration delete
            self.mock_winreg.OpenKey.return_value.__enter__.return_value = MagicMock()

            val = SwitchCraftConfig.get_secure_value("MySecret")

            self.assertEqual(val, "LegacySecret")
            # Verify migration calls
            self.mock_keyring_set.assert_called_with("SwitchCraft", "MySecret", "LegacySecret")
            self.mock_winreg.DeleteValue.assert_called()

if __name__ == '__main__':
    unittest.main()
