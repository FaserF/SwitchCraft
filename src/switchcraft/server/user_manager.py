import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
import secrets
import bcrypt
from switchcraft.utils.crypto import SimpleCrypto

logger = logging.getLogger("UserManager")

class UserManager:
    """Manages users for the SwitchCraft Server (stored in users.json)."""

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir:
            self.data_dir = data_dir
        else:
            self.data_dir = Path.home() / ".switchcraft" / "server"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.users_file = self.data_dir / "users.json"

        self.crypto = SimpleCrypto()
        self._ensure_users_file()

    def _hash_password(self, password: str) -> Optional[str]:
        """Hash a password using bcrypt (Python 3.14 compatible)."""
        if password is None:
            return None
        # Encode to bytes and hash
        pw_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(pw_bytes, salt)
        return hashed.decode('utf-8')

    def _verify_password(self, password: str, password_hash: str) -> bool:
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

    def _ensure_users_file(self):
        if not self.users_file.exists():
            # Create default admin user with a secure random password
            generated_password = secrets.token_urlsafe(16)
            logger.info("*" * 60)
            logger.info("Initial admin password generated and printed to stdout")
            logger.info("PLEASE RECORD THIS PASSWORD IMMEDIATELY.")
            logger.info("*" * 60)

            # Also print to stdout to ensure visibility in Docker logs / terminal
            print("\n" + "!" * 60)
            print(f"!!! INITIAL ADMIN PASSWORD: {generated_password} !!!")
            print("!" * 60 + "\n")

            default_admin_hash = self._hash_password(generated_password)
            initial_data = {
                "users": {
                    "admin": {
                        "password_hash": default_admin_hash,
                        "role": "admin",
                        "created_at": 0,
                        "is_active": True,
                        "must_change_password": True
                    }
                }
            }
            self._save_data(initial_data)

    def _load_data(self) -> Dict:
        try:
            if self.users_file.exists():
                with open(self.users_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load users: {e}")
        return {"users": {}}

    def _save_data(self, data: Dict):
        with open(self.users_file, "w") as f:
            json.dump(data, f, indent=4)

    def get_user(self, username: str) -> Optional[Dict]:
        data = self._load_data()
        return data.get("users", {}).get(username)

    def list_users(self) -> List[Dict]:
        data = self._load_data()
        result = []
        for uname, info in data.get("users", {}).items():
            info = info.copy()
            info["username"] = uname
            info.pop("password_hash", None) # Don't leak hash
            result.append(info)
        return result

    def create_user(self, username: str, password: str = None, role: str = "user", auto_hash: bool = True) -> bool:
        data = self._load_data()
        if username in data["users"]:
            return False

        pwd_hash = None
        if password:
            if auto_hash:
                pwd_hash = self._hash_password(password)
            else:
                pwd_hash = password # Already hashed or managed elsewhere

        data["users"][username] = {
            "password_hash": pwd_hash,
            "role": role,
            "is_active": True,
            "config_path": f"users/{username}/config.json" # convention
        }
        self._save_data(data)
        return True

    def delete_user(self, username: str):
        data = self._load_data()
        if username in data["users"]:
            del data["users"][username]
            self._save_data(data)

    def verify_password(self, username: str, password: str) -> bool:
        user = self.get_user(username)
        if not user or not user.get("is_active"):
            return False

        stored_hash = user.get("password_hash")
        if not stored_hash:
            return False # User has no password (maybe SSO only?)

        return self._verify_password(password, stored_hash)

    def update_password(self, username: str, new_password: str):
        data = self._load_data()
        if username in data["users"]:
            data["users"][username]["password_hash"] = self._hash_password(new_password)
            # Clear must_change_password flag upon successful manual update
            data["users"][username]["must_change_password"] = False
            self._save_data(data)
            return True
        return False

    def get_user_config_path(self, username: str) -> Path:
        """Returns the absolute path to the user's config.json."""
        user = self.get_user(username)
        if user and user.get("config_path"):
            # If path is relative, it's relative to server dir
            p = Path(user["config_path"])
            if not p.is_absolute():
                return self.data_dir / p
            return p

        # Default
        return self.data_dir / "users" / username / "config.json"

    def set_totp_secret(self, username: str, secret: str):
        """Store a TOTP secret for the given user, encrypted."""
        data = self._load_data()
        if username in data["users"]:
            # Encrypt secret before storing
            ciphertext = self.crypto.encrypt(secret)
            data["users"][username]["totp_secret"] = ciphertext
            self._save_data(data)

    def get_totp_secret(self, username: str) -> Optional[str]:
        """Retrieve and decrypt the TOTP secret for the given user."""
        user = self.get_user(username)
        ciphertext = user.get("totp_secret") if user else None
        if not ciphertext:
            return None

        try:
            return self.crypto.decrypt(ciphertext)
        except Exception as e:
            logger.error(f"Failed to decrypt TOTP secret for {username}: {e}")
            return None
