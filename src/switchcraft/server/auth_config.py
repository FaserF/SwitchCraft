import json
import os
import secrets
from pathlib import Path
from typing import Optional, Dict
import logging

import bcrypt
import pyotp

logger = logging.getLogger("AuthConfig")

class AuthConfigManager:
    """Manages server-side authentication configuration with modern security."""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir:
            self.config_dir = config_dir
        else:
            # Default to /root/.switchcraft/server (Docker) or user home
            self.config_dir = Path.home() / ".switchcraft" / "server"

        self.config_file = self.config_dir / "auth_config.json"
        self._ensure_dir()

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt (Python 3.14 compatible)."""
        if password is None:
            return None
        pw_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pw_bytes, salt)
        return hashed.decode('utf-8')

    def _verify_password_hash(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        if not password or not password_hash:
            return False
        try:
            pw_bytes = password.encode('utf-8')
            hash_bytes = password_hash.encode('utf-8')
            return bcrypt.checkpw(pw_bytes, hash_bytes)
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def _ensure_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> Dict:
        if not self.config_file.exists():
            return self._create_default_config()

        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
                # Migration/Ensuring new fields exist
                if "admin_password_hash" not in data and "admin_password" in data:
                     # Migrate plain to hash
                     try:
                         data["admin_password_hash"] = self._hash_password(data["admin_password"])
                         del data["admin_password"]
                         self.save_config(data)
                     except Exception as e:
                         logger.error(f"Migration failed: {e}")

                # Defaults for new flags
                if "demo_mode" not in data:
                    data["demo_mode"] = False
                if "auth_disabled" not in data:
                    data["auth_disabled"] = False
                if "allow_sso_registration" not in data:
                    data["allow_sso_registration"] = True
                if "mfa_enabled" not in data:
                    data["mfa_enabled"] = False
                if "enforce_mfa" not in data:
                    data["enforce_mfa"] = False
                return data
        except Exception:
            return self._create_default_config()

    def save_config(self, config: Dict):
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=4)

    def _create_default_config(self) -> Dict:
        # User requested default "admin"
        default_hash = self._hash_password("admin")

        config = {
            "admin_password_hash": default_hash,
            "secret_key": secrets.token_hex(32),
            "demo_mode": False,
            "auth_disabled": False,
            "allow_sso_registration": True,
            "mfa_enabled": False,
            "enforce_mfa": False,
            "totp_secret": "", # Base32 secret
            "webauthn_credentials": [], # List of registered credentials
            "first_run": True
        }
        self.save_config(config)
        return config

    def get_secret_key(self) -> str:
        conf = self.load_config()
        return conf.get("secret_key", "fallback_secret")

    def verify_password(self, password: str) -> bool:
        conf = self.load_config()
        if conf.get("auth_disabled", False):
            return True
        if "admin_password_hash" in conf:
            return self._verify_password_hash(password, conf["admin_password_hash"])
        # Fallback for very old unmigrated
        return password == conf.get("admin_password")

    def update_password(self, new_password: str):
        conf = self.load_config()
        conf["admin_password_hash"] = self._hash_password(new_password)
        # Clear legacy plain if exists
        if "admin_password" in conf:
            del conf["admin_password"]
        conf["first_run"] = False
        self.save_config(conf)

    # --- Feature Flags ---

    def set_demo_mode(self, enabled: bool):
        conf = self.load_config()
        conf["demo_mode"] = enabled
        self.save_config(conf)

    def set_auth_disabled(self, enabled: bool):
        conf = self.load_config()
        conf["auth_disabled"] = enabled
        self.save_config(conf)

    def set_sso_registration(self, enabled: bool):
        conf = self.load_config()
        conf["allow_sso_registration"] = enabled
        self.save_config(conf)

    # --- MFA (TOTP) ---

    def enable_totp(self) -> str:
        """Generates a new TOTP secret, saves it, and returns the Provisioning URI for QR code."""
        secret = pyotp.random_base32()
        conf = self.load_config()
        conf["totp_secret"] = secret
        self.save_config(conf)
        # Return URI for QR Code
        return pyotp.totp.TOTP(secret).provisioning_uri(name="SwitchCraftAdmin", issuer_name="SwitchCraft")

    def confirm_totp(self, token: str) -> bool:
        """Verifies token and fully enables MFA if correct."""
        conf = self.load_config()
        secret = conf.get("totp_secret")
        if not secret:
            return False

        totp = pyotp.TOTP(secret)
        if totp.verify(token):
            conf["mfa_enabled"] = True
            self.save_config(conf)
            return True
        return False

    def verify_totp(self, token: str) -> bool:
        """Standard login verification."""
        conf = self.load_config()
        if not conf.get("mfa_enabled"):
            return True

        secret = conf.get("totp_secret")
        # Fail safe
        if not secret:
            return True

        totp = pyotp.TOTP(secret)
        return totp.verify(token)

    def is_mfa_enabled(self) -> bool:
        conf = self.load_config()
        return conf.get("mfa_enabled", False) and bool(conf.get("totp_secret"))
