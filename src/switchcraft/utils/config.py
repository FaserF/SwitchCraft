import sys
import logging
import os
from typing import Optional, Any, Dict
from contextvars import ContextVar
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# --- Configuration Backends ---

class ConfigBackend(ABC):
    @abstractmethod
    def get_value(self, value_name: str, default: Any = None) -> Any:
        pass

    @abstractmethod
    def set_value(self, value_name: str, value: Any, value_type: int = None):
        pass

    @abstractmethod
    def get_secure_value(self, value_name: str) -> Optional[str]:
        pass

    @abstractmethod
    def set_secure_value(self, value_name: str, value: str):
        pass

    @abstractmethod
    def delete_secure_value(self, value_name: str):
        pass

    @abstractmethod
    def is_managed(self, key: str = None) -> bool:
        pass

    @abstractmethod
    def export_all(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_value_with_source(self, value_name: str) -> Optional[Dict[str, Any]]:
        """Returns { 'value': any, 'source': str } or None."""
        pass

class RegistryBackend(ConfigBackend):
    """Windows Registry Backend for Desktop App"""
    POLICY_PATH = r"Software\Policies\FaserF\SwitchCraft"
    PREFERENCE_PATH = r"Software\FaserF\SwitchCraft"
    INTUNE_OMA_PATH = r"Software\Microsoft\PolicyManager\current\device\FaserF~SwitchCraft"

    def get_value(self, value_name: str, default: Any = None) -> Any:
        # Alias mapping for GPO
        key_map = {
            "IntuneTenantID": "GraphTenantId",
            "IntuneClientId": "GraphClientId",
            "IntuneClientSecret": "GraphClientSecret"
        }
        if value_name in key_map:
             alias_val = self.get_value(key_map[value_name], default=None)
             if alias_val is not None:
                 return alias_val

        if sys.platform != 'win32':
            return default

        try:
            import winreg
        except ImportError:
            return default

        # 1. HKLM Policy
        val = self._read_registry(winreg.HKEY_LOCAL_MACHINE, self.POLICY_PATH, value_name)
        if val is not None: return val
        # 2. HKCU Policy
        val = self._read_registry(winreg.HKEY_CURRENT_USER, self.POLICY_PATH, value_name)
        if val is not None: return val
        # 3. HKCU Preference
        val = self._read_registry(winreg.HKEY_CURRENT_USER, self.PREFERENCE_PATH, value_name)
        if val is not None: return val
        # 4. HKLM Preference
        val = self._read_registry(winreg.HKEY_LOCAL_MACHINE, self.PREFERENCE_PATH, value_name)
        if val is not None: return val

        return default

    def get_value_with_source(self, value_name: str) -> Optional[Dict[str, Any]]:
        if sys.platform != 'win32':
            return None

        try:
            import winreg
        except ImportError:
            return None

        # 1. HKLM Policy (GPO)
        val = self._read_registry(winreg.HKEY_LOCAL_MACHINE, self.POLICY_PATH, value_name)
        if val is not None: return {"value": val, "source": "GPO (Local Machine)"}

        # 2. HKCU Policy (GPO)
        val = self._read_registry(winreg.HKEY_CURRENT_USER, self.POLICY_PATH, value_name)
        if val is not None: return {"value": val, "source": "GPO (Current User)"}

        # 3. Intune OMA-URI
        val = self._read_registry(winreg.HKEY_LOCAL_MACHINE, self.INTUNE_OMA_PATH, value_name)
        if val is not None: return {"value": val, "source": "Intune OMA-URI"}

        # 4. HKCU Preference (User Registry)
        val = self._read_registry(winreg.HKEY_CURRENT_USER, self.PREFERENCE_PATH, value_name)
        if val is not None: return {"value": val, "source": "User Registry (HKCU)"}

        # 5. HKLM Preference (System Registry)
        val = self._read_registry(winreg.HKEY_LOCAL_MACHINE, self.PREFERENCE_PATH, value_name)
        if val is not None: return {"value": val, "source": "System Registry (HKLM)"}

        return None

    def is_managed(self, key: str = None) -> bool:
        """Check if a specific key (or any key) is managed by GPO."""
        if sys.platform != 'win32': return False
        try:
            import winreg
            if key:
                # Check if specific key exists in policy
                val = self._read_registry(winreg.HKEY_LOCAL_MACHINE, self.POLICY_PATH, key)
                if val is not None: return True
                val = self._read_registry(winreg.HKEY_CURRENT_USER, self.POLICY_PATH, key)
                if val is not None: return True
                return False
            else:
                # Check if ANY policy exists
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.POLICY_PATH):
                        return True
                except OSError:
                    pass
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.POLICY_PATH):
                        return True
                except OSError:
                    pass
        except Exception:
            pass
        return False

    def set_value(self, value_name: str, value: Any, value_type: int = None):
        if sys.platform != 'win32': return
        try:
            import winreg
            if value_type is None:
                if isinstance(value, bool):
                    value_type = winreg.REG_DWORD
                    value = 1 if value else 0
                elif isinstance(value, int):
                    value_type = winreg.REG_DWORD
                    if value < 0 or value > 0xFFFFFFFF: raise ValueError("REG_DWORD out of range")
                elif isinstance(value, float):
                    value_type = winreg.REG_DWORD
                    value = int(value)
                    if value < 0 or value > 0xFFFFFFFF: raise ValueError("REG_DWORD out of range")
                else:
                    value_type = winreg.REG_SZ
                    value = str(value)

            winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.PREFERENCE_PATH)
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.PREFERENCE_PATH, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, value_name, 0, value_type, value)
        except Exception as e:
            logger.error(f"Registry set failed: {e}")

    def get_secure_value(self, value_name: str) -> Optional[str]:
        # Check policies first (legacy GPO support)
        if sys.platform == 'win32':
             try:
                import winreg
                # Plain
                val = self._read_registry(winreg.HKEY_LOCAL_MACHINE, self.POLICY_PATH, value_name)
                if val is not None: return val
                val = self._read_registry(winreg.HKEY_CURRENT_USER, self.POLICY_PATH, value_name)
                if val is not None: return val

                # 2. Encrypted Policy (HKLM then HKCU) - Suffix _ENC
                from switchcraft.utils.crypto import SimpleCrypto
                enc_name = value_name + "_ENC"

                val_enc = self._read_registry(winreg.HKEY_LOCAL_MACHINE, self.POLICY_PATH, enc_name)
                if val_enc is not None:
                    dec = SimpleCrypto.decrypt(str(val_enc))
                    if dec is not None: return dec

                val_enc = self._read_registry(winreg.HKEY_CURRENT_USER, self.POLICY_PATH, enc_name)
                if val_enc is not None:
                    dec = SimpleCrypto.decrypt(str(val_enc))
                    if dec is not None: return dec

             except Exception as e:
                 logger.debug(f"Secure lookup failed: {e}")

        # Check Keyring
        try:
            import keyring
            keyring_val = keyring.get_password("SwitchCraft", value_name)
            if keyring_val is not None:
                return keyring_val
        except Exception:
            pass

        # 3. Legacy Migration: Check Registry Preference (Plain text)
        # If found, move to Keyring and delete from Registry
        if sys.platform == 'win32':
             try:
                 import winreg
                 val_legacy = self._read_registry(winreg.HKEY_CURRENT_USER, self.PREFERENCE_PATH, value_name)
                 if val_legacy is not None:
                     logger.info(f"Migrating legacy secret '{value_name}' to Keyring...")
                     try:
                         import keyring
                         keyring.set_password("SwitchCraft", value_name, str(val_legacy))
                         # Delete from registry
                         with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.PREFERENCE_PATH, 0, winreg.KEY_WRITE) as key:
                             winreg.DeleteValue(key, value_name)
                         return str(val_legacy)
                     except Exception as e:
                         logger.error(f"Migration failed: {e}")
                         return str(val_legacy) # Return it anyway so app works
             except Exception:
                 pass

        return None

    def set_secure_value(self, value_name: str, value: str):
        try:
             import keyring
             if value is None:
                 try: keyring.delete_password("SwitchCraft", value_name)
                 except: pass
                 return
             keyring.set_password("SwitchCraft", value_name, value)
        except Exception as e:
            logger.error(f"Keyring set failed: {e}")

    def delete_secure_value(self, value_name: str):
        try:
            import keyring
            keyring.delete_password("SwitchCraft", value_name)
        except:
            pass

    def export_all(self) -> Dict[str, Any]:
        if sys.platform != 'win32': return {}
        prefs = {}
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.PREFERENCE_PATH, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        prefs[name] = value
                        i += 1
                    except OSError:
                        break
        except Exception:
            pass
        return prefs

    def _read_registry(self, root_key, sub_key, value_name):
        try:
            import winreg
            with winreg.OpenKey(root_key, sub_key, 0, winreg.KEY_READ) as key:
                value, val_type = winreg.QueryValueEx(key, value_name)
                if val_type == winreg.REG_SZ or val_type == winreg.REG_EXPAND_SZ:
                    v_lower = str(value).lower()
                    if v_lower == "true": return True
                    if v_lower == "false": return False
                    if v_lower.isdigit(): return int(v_lower)
                    return value
                if val_type == winreg.REG_DWORD:
                    return int(value)
                return value
        except Exception:
            return None

class EnvBackend(ConfigBackend):
    """Environment Variable Backend for Docker/Linux basics."""
    def get_value(self, value_name: str, default: Any = None) -> Any:
        # Map common keys to Env Vars: IntuneTenantID -> SC_INTUNE_TENANT_ID
        env_key = "SC_" + value_name.upper()
        # Also try exact match
        val = os.environ.get(env_key)
        if val is None:
             val = os.environ.get(value_name)

        if val is not None:
            # Type casting
            if val.lower() == 'true': return True
            if val.lower() == 'false': return False
            if val.isdigit(): return int(val)
            return val
        return default

    def set_value(self, value_name: str, value: Any, value_type: int = None):
        # Ephemeral set for runtime, doesn't persist to OS env
        os.environ["SC_" + value_name.upper()] = str(value)

    def get_secure_value(self, value_name: str) -> Optional[str]:
        return self.get_value(value_name)

    def set_secure_value(self, value_name: str, value: str):
        self.set_value(value_name, value)

    def delete_secure_value(self, value_name: str):
        k = "SC_" + value_name.upper()
        if k in os.environ: del os.environ[k]
        if value_name in os.environ: del os.environ[value_name]

    def is_managed(self, key: str = None) -> bool:
        return False

    def export_all(self) -> Dict[str, Any]:
        return {k: v for k, v in os.environ.items() if k.startswith("SC_")}

    def get_value_with_source(self, value_name: str) -> Optional[Dict[str, Any]]:
        val = self.get_value(value_name)
        if val is not None:
            return {"value": val, "source": "Environment Variable"}
        return None

class SessionStoreBackend(ConfigBackend):
    """In-Memory Backend for Web Sessions (isolated per user)."""
    def __init__(self, page_session):
        self.session = page_session # Reference to Flet page.session (dict-like)
        self.store = {} # Local fallback if session unimplemented or blocked

    def get_value(self, value_name: str, default: Any = None) -> Any:
        # Check session store
        try:
            if hasattr(self.session, 'get'):
                 val = self.session.get(f"sc_conf_{value_name}")
                 if val is not None: return val
        except Exception:
            pass # Session access blocked (e.g. tracking prevention)

        return self.store.get(value_name, default)

    def set_value(self, value_name: str, value: Any, value_type: int = None):
        try:
            if hasattr(self.session, 'set'):
                 self.session.set(f"sc_conf_{value_name}", value)
        except Exception:
            pass # Session access blocked

        self.store[value_name] = value

    def get_secure_value(self, value_name: str) -> Optional[str]:
        # Simple storage for secure values in session memory (encrypted by TLS in transit)
        return self.get_value(f"SECURE_{value_name}")

    def set_secure_value(self, value_name: str, value: str):
        self.set_value(f"SECURE_{value_name}", value)

    def delete_secure_value(self, value_name: str):
        key = f"SECURE_{value_name}"
        try:
            if hasattr(self.session, 'remove'):
                try: self.session.remove(f"sc_conf_{key}")
                except: pass
        except Exception:
            pass

        if key in self.store:
            del self.store[key]

    def is_managed(self, key: str = None) -> bool:
        return False

    def export_all(self) -> Dict[str, Any]:
        # Not easily exportable from Flet session without iteration keys
        return self.store

    def get_value_with_source(self, value_name: str) -> Optional[Dict[str, Any]]:
        val = self.get_value(value_name)
        if val is not None:
            return {"value": val, "source": "Web Session"}
        return None

class ClientStorageBackend(ConfigBackend):
    """Persistent Web Backend using Flet Client Storage (Cookies/LocalStorage)."""
    def __init__(self, page):
        self.page = page
        self.cleanup_keys = []

    def get_value(self, value_name: str, default: Any = None) -> Any:
        try:
            # Add prefix to avoid collision with other apps on localhost
            key = f"sc_{value_name}"
            if hasattr(self.page, 'client_storage'):
                val = self.page.client_storage.get(key)
                if val is not None:
                    # Flet stores as strings usually, but supports JSON types if natively handled?
                    # client_storage.get returns parsed JSON usually.
                    return val
        except Exception:
            pass
        return default

    def set_value(self, value_name: str, value: Any, value_type: int = None):
        try:
            key = f"sc_{value_name}"
            if hasattr(self.page, 'client_storage'):
                self.page.client_storage.set(key, value)
        except Exception:
            pass

    def get_secure_value(self, value_name: str) -> Optional[str]:
        # Web storage is NOT secure, but it's isolated by origin.
        # We perform simple obfuscation if needed, or just store plainly.
        # For a demo, plain storage is acceptable given HTTPS.
        return self.get_value(f"SECURE_{value_name}")

    def set_secure_value(self, value_name: str, value: str):
        self.set_value(f"SECURE_{value_name}", value)

    def delete_secure_value(self, value_name: str):
        key = f"sc_SECURE_{value_name}"
        try:
             if hasattr(self.page, 'client_storage'):
                 self.page.client_storage.remove(key)
        except Exception:
            pass

    def is_managed(self, key: str = None) -> bool:
        return False

    def export_all(self) -> Dict[str, Any]:
        return {} # Hard to enumerate client storage without known keys

    def get_value_with_source(self, value_name: str) -> Optional[Dict[str, Any]]:
        val = self.get_value(value_name)
        if val is not None:
             return {"value": val, "source": "Browser Storage"}
        return None

# Global context variable to hold the active backend logic
# If None, falls back to default logic (Registry on Win, Env on Linux)
_config_context: ContextVar[Optional[ConfigBackend]] = ContextVar("config_context", default=None)

class SwitchCraftConfig:
    @staticmethod
    def set_backend(backend: ConfigBackend):
        """Sets the backend for the current context (thread/task)."""
        _config_context.set(backend)

    @staticmethod
    def _get_active_backend() -> ConfigBackend:
        backend = _config_context.get()
        if backend:
            return backend

        # Fallback Logic
        if sys.platform == 'win32':
             # Default to Registry singleton if not set
             if not hasattr(SwitchCraftConfig, '_default_reg_backend'):
                 SwitchCraftConfig._default_reg_backend = RegistryBackend()
             return SwitchCraftConfig._default_reg_backend
        elif sys.platform == "emscripten" or sys.platform == "wasi":
            # Default to InMemory/Session for WASM (no persistent OS storage)
             if not hasattr(SwitchCraftConfig, '_default_mem_backend'):
                 # We don't have access to page.session here easily without context
                 # So we use a dummy session store that is just in-memory
                 class DummySession:
                     pass
                 SwitchCraftConfig._default_mem_backend = SessionStoreBackend(DummySession())
             return SwitchCraftConfig._default_mem_backend
        else:
             # Default to Env for Linux/Docker
             if not hasattr(SwitchCraftConfig, '_default_env_backend'):
                 SwitchCraftConfig._default_env_backend = EnvBackend()
             return SwitchCraftConfig._default_env_backend

    @classmethod
    def get_value(cls, value_name: str, default: Any = None) -> Any:
        return cls._get_active_backend().get_value(value_name, default)

    @classmethod
    def set_user_preference(cls, value_name: str, value: Any, value_type: int = None):
        cls._get_active_backend().set_value(value_name, value, value_type)

    @classmethod
    def get_secure_value(cls, value_name: str) -> Optional[str]:
        return cls._get_active_backend().get_secure_value(value_name)

    @classmethod
    def set_secure_value(cls, value_name: str, value: str):
        cls._get_active_backend().set_secure_value(value_name, value)

    # Aliases for backwards compatibility
    @classmethod
    def get_secret(cls, value_name: str) -> Optional[str]:
        """Alias for get_secure_value()."""
        return cls.get_secure_value(value_name)

    @classmethod
    def set_secret(cls, value_name: str, value: str):
        """Alias for set_secure_value()."""
        cls.set_secure_value(value_name, value)

    @classmethod
    def is_managed(cls, key: str = None) -> bool:
        """Check if application (or specific key) is managed by GPO/Intune."""
        return cls._get_active_backend().is_managed(key)

    @classmethod
    def delete_secret(cls, key_name: str):
         cls._get_active_backend().delete_secure_value(key_name)

    @classmethod
    def export_preferences(cls) -> dict:
        return cls._get_active_backend().export_all()

    @classmethod
    def get_value_with_source(cls, value_name: str) -> Optional[Dict[str, Any]]:
        """Returns the value and its source (GPO, Registry, etc.)."""
        return cls._get_active_backend().get_value_with_source(value_name)

    @classmethod
    def import_preferences(cls, data: dict):
        # Import to current backend
        backend = cls._get_active_backend()
        for k, v in data.items():
            backend.set_value(k, v)

    @classmethod
    def delete_all_application_data(cls):
        """
        Factory Reset: Removes all data, secrets, and configuration.
        """
        backend = cls._get_active_backend()
        cleaned_up = []

        # 1. Platform independent cleanup (if any generic caches exist)
        # ...

        if sys.platform == 'win32':
             import winreg
             import shutil
             import keyring

             # A. Delete Registry Preferences (HKCU\Software\FaserF\SwitchCraft)
             try:
                 winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\FaserF\SwitchCraft")
                 cleaned_up.append("Registry Settings")
             except FileNotFoundError:
                 pass
             except Exception as e:
                 logger.error(f"Failed to delete registry key: {e}")

             # B. Delete all secrets from Keyring
             # Known secrets list to iterate and delete? Keyring doesn't easily list all per service.
             # We try to delete known common keys
             known_secrets = [
                 "IntuneClientSecret", "GraphClientSecret",
                 "EntraClientSecret", "PAT", "GitHubToken"
             ]
             for sec in known_secrets:
                 try:
                     keyring.delete_password("SwitchCraft", sec)
                 except: pass
             cleaned_up.append("Stored Credentials")

             # C. Delete AppData (%APPDATA%\FaserF\SwitchCraft)
             app_data = os.path.join(os.environ.get("APPDATA", ""), "FaserF", "SwitchCraft")
             if os.path.exists(app_data):
                 try:
                     shutil.rmtree(app_data)
                     cleaned_up.append("App Data (Logs, Cache, History)")
                 except Exception as e:
                     logger.error(f"Failed to delete AppData: {e}")

             # D. Delete .switchcraft (%USERPROFILE%\.switchcraft)
             user_profile = os.environ.get("USERPROFILE")
             if user_profile:
                 dot_switchcraft = os.path.join(user_profile, ".switchcraft")
                 if os.path.exists(dot_switchcraft):
                     try:
                         shutil.rmtree(dot_switchcraft)
                         cleaned_up.append("Addons & User Data")
                     except Exception as e:
                         logger.error(f"Failed to delete .switchcraft: {e}")

        logger.info(f"Factory Reset Complete. Cleared: {', '.join(cleaned_up)}")

    # --- Helpers ---
    @classmethod
    def is_debug_mode(cls) -> bool:
        if '--debug' in sys.argv: return True
        if os.environ.get("SWITCHCRAFT_DEBUG") == "1": return True
        return cls.get_value("DebugMode", 0) == 1

    @classmethod
    def get_update_channel(cls) -> str:
        return cls.get_value("UpdateChannel", "stable")

    @classmethod
    def get_company_name(cls) -> str:
        """Get the configured company name."""
        return cls.get_value("CompanyName", "")
