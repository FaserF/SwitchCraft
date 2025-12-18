import sys
import logging
import os
from typing import Optional, Any

logger = logging.getLogger(__name__)

class SwitchCraftConfig:
    """
    Centralized configuration management for SwitchCraft.
    Handles precedence of settings:
    1. Machine Policy (HKLM\\Software\\Policies\\FaserF\\SwitchCraft) - Intune/GPO
    2. User Policy (HKCU\\Software\\Policies\\FaserF\\SwitchCraft) - Intune/GPO
    3. Machine Preference (HKLM\\Software\\FaserF\\SwitchCraft)
    4. User Preference (HKCU\\Software\\FaserF\\SwitchCraft) - Default User Settings
    """

    POLICY_PATH = r"Software\Policies\FaserF\SwitchCraft"
    PREFERENCE_PATH = r"Software\FaserF\SwitchCraft"

    @classmethod
    def get_value(cls, value_name: str, default: Any = None) -> Any:
        """
        Retrieves a registry value respecting the policy precedence order.
        Returns 'default' if the value is not found in any location.
        """
        if sys.platform != 'win32':
            return default

        try:
            import winreg
        except ImportError:
            return default

        # Precedence 1: Machine Policy (HKLM)
        val = cls._read_registry(winreg.HKEY_LOCAL_MACHINE, cls.POLICY_PATH, value_name)
        if val is not None:
            logger.debug(f"Config '{value_name}' found in HKLM Policy: {val}")
            return val

        # Precedence 2: User Policy (HKCU)
        val = cls._read_registry(winreg.HKEY_CURRENT_USER, cls.POLICY_PATH, value_name)
        if val is not None:
            logger.debug(f"Config '{value_name}' found in HKCU Policy: {val}")
            return val

        # Precedence 3: Machine Preference (HKLM)
        val = cls._read_registry(winreg.HKEY_LOCAL_MACHINE, cls.PREFERENCE_PATH, value_name)
        if val is not None:
            logger.debug(f"Config '{value_name}' found in HKLM Preference: {val}")
            return val

        # Precedence 4: User Preference (HKCU)
        val = cls._read_registry(winreg.HKEY_CURRENT_USER, cls.PREFERENCE_PATH, value_name)
        if val is not None:
            logger.debug(f"Config '{value_name}' found in HKCU Preference: {val}")
            return val

        return default

    @staticmethod
    def _read_registry(root_key, sub_key, value_name):
        try:
            import winreg
            with winreg.OpenKey(root_key, sub_key, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
                return value
        except (FileNotFoundError, OSError, WindowsError):
            return None

    @classmethod
    def is_debug_mode(cls) -> bool:
        """Checks if debug mode is enabled via Command Line, Environment, or Registry (Policy/Pref)."""
        # 1. CLI Arguments
        if '--debug' in sys.argv or '-d' in sys.argv:
            return True

        # 2. Environment Variable
        if os.environ.get('SWITCHCRAFT_DEBUG', '').lower() in ('1', 'true', 'yes'):
            return True

        # 3. Registry (reading policy first)
        val = cls.get_value("DebugMode")
        if val is not None:
             return val == 1

        # 4. Default for Nightly/Dev builds
        from switchcraft import __version__
        v_low = __version__.lower()
        if "dev" in v_low or "nightly" in v_low:
            return True

        return False

    @classmethod
    def get_update_channel(cls) -> str:
        """Returns the update channel (stable, beta, dev). Default: stable."""
        val = cls.get_value("UpdateChannel", "stable")
        valid_channels = ["stable", "beta", "dev"]
        if isinstance(val, str) and val.lower() in valid_channels:
            return val.lower()
        return "stable"

    @classmethod
    def set_user_preference(cls, value_name: str, value: Any, value_type: int = None):
        """
        Writes a value to the User Preference registry key (HKCU).
        Does NOT write to Policy keys (these are read-only for the app).
        """
        if sys.platform != 'win32':
            return

        try:
            import winreg
            if value_type is None:
                # Basic type inference
                if isinstance(value, int):
                    value_type = winreg.REG_DWORD
                else:
                    value_type = winreg.REG_SZ

            # Create key if not exists
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, cls.PREFERENCE_PATH)

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.PREFERENCE_PATH, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, value_name, 0, value_type, value)

        except Exception as e:
            logger.error(f"Failed to set user preference '{value_name}': {e}")

    @classmethod
    def get_secret(cls, key_name: str) -> Optional[str]:
        """Retrieve a secret from the system keyring."""
        try:
            import keyring
            return keyring.get_password("SwitchCraft", key_name)
        except Exception as e:
            logger.error(f"Failed to get secret '{key_name}': {e}")
            return None

    @classmethod
    def set_secret(cls, key_name: str, value: str):
        """Store a secret securely in the system keyring."""
        try:
            import keyring
            keyring.set_password("SwitchCraft", key_name, value)
        except Exception as e:
            logger.error(f"Failed to set secret '{key_name}': {e}")
