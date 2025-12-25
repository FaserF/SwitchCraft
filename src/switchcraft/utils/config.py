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
    3. User Preference (HKCU\\Software\\FaserF\\SwitchCraft) - Default User Settings
    4. Machine Preference (HKLM\\Software\\FaserF\\SwitchCraft)
    """

    POLICY_PATH = r"Software\Policies\FaserF\SwitchCraft"
    PREFERENCE_PATH = r"Software\FaserF\SwitchCraft"

    @classmethod
    def get_company_name(cls) -> str:
        """Returns the configured company name or an empty string."""
        return cls.get_value("CompanyName", "")

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

        # Precedence 1: Machine Policy (HKLM) - Enforced
        val = cls._read_registry(winreg.HKEY_LOCAL_MACHINE, cls.POLICY_PATH, value_name)
        if val is not None:
            logger.debug(f"Config '{value_name}' found in HKLM Policy: {val}")
            return val

        # Precedence 2: User Policy (HKCU) - Enforced
        val = cls._read_registry(winreg.HKEY_CURRENT_USER, cls.POLICY_PATH, value_name)
        if val is not None:
            logger.debug(f"Config '{value_name}' found in HKCU Policy: {val}")
            return val

        # Precedence 3: User Preference (HKCU) - User Setting (Overrides Machine Default)
        val = cls._read_registry(winreg.HKEY_CURRENT_USER, cls.PREFERENCE_PATH, value_name)
        if val is not None:
            logger.debug(f"Config '{value_name}' found in HKCU Preference: {val}")
            return val

        # Precedence 4: Machine Preference (HKLM) - Admin Default
        val = cls._read_registry(winreg.HKEY_LOCAL_MACHINE, cls.PREFERENCE_PATH, value_name)
        if val is not None:
            logger.debug(f"Config '{value_name}' found in HKLM Preference: {val}")
            return val

        return default

    @classmethod
    def is_managed(cls, value_name: str) -> bool:
        """
        Returns True if the setting is enforced by Policy (Machine or User).
        Used to disable UI elements.
        """
        if sys.platform != 'win32':
            return False

        try:
            import winreg
            # Check HKLM Policy
            if cls._read_registry(winreg.HKEY_LOCAL_MACHINE, cls.POLICY_PATH, value_name) is not None:
                return True
            # Check HKCU Policy
            if cls._read_registry(winreg.HKEY_CURRENT_USER, cls.POLICY_PATH, value_name) is not None:
                return True
        except Exception:
            pass

        return False

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
                # Basic type inference - handle float by converting to int
                if isinstance(value, bool):
                    value_type = winreg.REG_DWORD
                    value = 1 if value else 0
                elif isinstance(value, float):
                    value_type = winreg.REG_DWORD
                    # Round standardly
                    val_int = int(round(value))
                    # Validate range for REG_DWORD (unsigned 32-bit: 0 to 4294967295)
                    if val_int < 0 or val_int > 0xFFFFFFFF:
                        raise ValueError(f"Registry value '{value_name}' out of range for REG_DWORD: {val_int}")
                    value = val_int
                elif isinstance(value, int):
                    value_type = winreg.REG_DWORD
                    # Validate range for REG_DWORD (unsigned 32-bit: 0 to 4294967295)
                    if value < 0 or value > 0xFFFFFFFF:
                        raise ValueError(f"Registry value '{value_name}' out of range for REG_DWORD: {value}")
                else:
                    value_type = winreg.REG_SZ
                    value = str(value)  # Ensure string

            # Create key if not exists
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, cls.PREFERENCE_PATH)

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.PREFERENCE_PATH, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, value_name, 0, value_type, value)

        except ValueError:
            raise  # Re-raise validation errors as requested
        except Exception as e:
            logger.error(f"Failed to set user preference '{value_name}': {e}")

    @classmethod
    def get_secure_value(cls, value_name: str) -> Optional[str]:
        """
        Retrieves a sensitive value (secret) with the following precedence:
        1. Machine Policy (HKLM Policy) - Enforced (Insecure but supported for GPO)
        2. User Policy (HKCU Policy) - Enforced (Insecure but supported for GPO)
        3. Keyring (Secure Store) - User Preference
        4. User Registry (HKCU Pref) - Legacy (Migrates to Keyring if found)
        5. Machine Registry (HKLM Pref) - Defaults

        If a value is found in the Legacy User Registry, it is migrated to Keyring
        and wiped from the Registry to improve security.
        """
        # 1. & 2. Check Policies (Enforced)
        # We use standard get_value for this, but restricting to policies would be cleaner.
        # However, is_managed uses the same keys.
        # Let's check policies manually to ensure we don't accidentally pick up preferences via get_value
        if sys.platform == 'win32':
             try:
                import winreg
                # HKLM Policy
                val = cls._read_registry(winreg.HKEY_LOCAL_MACHINE, cls.POLICY_PATH, value_name)
                if val:
                    return val
                # HKCU Policy
                val = cls._read_registry(winreg.HKEY_CURRENT_USER, cls.POLICY_PATH, value_name)
                if val:
                    return val
             except Exception:
                 pass

        # 3. Check Keyring (User Preference)
        secret = cls.get_secret(value_name)
        if secret:
            return secret

        # 4. Check Legacy User Registry & Migrate
        if sys.platform == 'win32':
            val = cls._read_registry(winreg.HKEY_CURRENT_USER, cls.PREFERENCE_PATH, value_name)
            if val:
                logger.info(f"Migrating legacy registry secret '{value_name}' to Keyring...")
                cls.set_secret(value_name, val)
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.PREFERENCE_PATH, 0, winreg.KEY_WRITE) as key:
                        winreg.DeleteValue(key, value_name)
                    logger.info("Legacy registry secret deleted.")
                except Exception as e:
                    logger.warning(f"Failed to delete legacy registry key for '{value_name}': {e}")
                return val

            # 5. Check Machine Preference (Defaults)
            val = cls._read_registry(winreg.HKEY_LOCAL_MACHINE, cls.PREFERENCE_PATH, value_name)
            if val:
                return val

        return None

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
             if not value:
                 # If empty, delete
                 try:
                     keyring.delete_password("SwitchCraft", key_name)
                 except keyring.errors.PasswordDeleteError:
                     pass
                 return

             keyring.set_password("SwitchCraft", key_name, value)
        except Exception as e:
            logger.error(f"Failed to set secret '{key_name}': {e}")

    @classmethod
    def delete_secret(cls, key_name: str):
        """Remove a secret from the system keyring."""
        try:
            import keyring
            keyring.delete_password("SwitchCraft", key_name)
        except Exception:
            # logger.error(f"Failed to delete secret '{key_name}': {e}")
            # Ignore if not found
            pass

    @classmethod
    def export_preferences(cls) -> dict:
        """
        Exports all User Preference values (HKCU) to a dictionary.
        This is used for CloudSync.
        """
        if sys.platform != 'win32':
            return {}

        prefs = {}
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.PREFERENCE_PATH, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        prefs[name] = value
                        i += 1
                    except OSError:
                        break
        except Exception as e:
            logger.error(f"Failed to export preferences: {e}")

        return prefs

    @classmethod
    def import_preferences(cls, data: dict):
        """
        Imports preferences from a dictionary to the User Preference registry key (HKCU).
        Overwrites existing values if they exist.
        """
        if not data or sys.platform != 'win32':
            return

        try:
            for key, value in data.items():
                cls.set_user_preference(key, value)
            logger.info("Preferences imported successfully.")
        except Exception as e:
            logger.error(f"Failed to import preferences: {e}")
