import time
import requests
import logging
from typing import Optional, Dict, Any
from switchcraft.utils.config import SwitchCraftConfig

logger = logging.getLogger(__name__)

class AuthService:
    """
    Handles GitHub Authentication using the OAuth Device Flow.
    Stores the access token securely using the keyring service via SwitchCraftConfig.
    """

    # Replace with your actual GitHub App Client ID
    # For open source projects, this is typically public.
    CLIENT_ID = "Ov23liFQxD8H5In5LqBM"
    SCOPE = "gist read:user"

    AUTH_URL = "https://github.com/login/device/code"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_API = "https://api.github.com/user"

    KEYRING_SERVICE_NAME = "SwitchCraft_GitHub_Token"

    @classmethod
    def initiate_device_flow(cls) -> Optional[Dict[str, Any]]:
        """
        Step 1: Request a device code from GitHub.
        Returns a dictionary containing 'device_code', 'user_code', 'verification_uri', etc.
        """
        headers = {"Accept": "application/json"}
        data = {
            "client_id": cls.CLIENT_ID,
            "scope": cls.SCOPE
        }

        try:
            logger.info(f"Initiating GitHub device flow for client {cls.CLIENT_ID}...")
            response = requests.post(cls.AUTH_URL, headers=headers, data=data, timeout=10)
            logger.debug(f"GitHub response: {response.status_code} - {response.text}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to initiate device flow: {e}")
            return None

    @classmethod
    def poll_for_token(cls, device_code: str, interval: int = 5, expires_in: int = 900) -> Optional[str]:
        """
        Step 2: Poll GitHub for the access token until the user authorizes or the code expires.
        """
        start_time = time.time()

        headers = {"Accept": "application/json"}
        data = {
            "client_id": cls.CLIENT_ID,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
        }

        while time.time() - start_time < expires_in:
            try:
                response = requests.post(cls.TOKEN_URL, headers=headers, data=data, timeout=10)
                response.raise_for_status()
                resp_data = response.json()

                if "access_token" in resp_data:
                    return resp_data["access_token"]

                error = resp_data.get("error")
                if error == "authorization_pending":
                    pass # Continue polling
                elif error == "slow_down":
                    interval += 5 # GitHub asks to slow down
                elif error == "expired_token":
                    logger.error("Device code expired.")
                    return None
                elif error == "access_denied":
                    logger.error("User denied access.")
                    return None
                else:
                    logger.error(f"Unknown error during polling: {error}")

                time.sleep(interval)

            except requests.RequestException as e:
                logger.error(f"Network error during polling: {e}")
                time.sleep(interval)

        logger.error("Polling timed out.")
        return None

    @classmethod
    def save_token(cls, token: str):
        """Saves the token to the secure keyring."""
        SwitchCraftConfig.set_secret(cls.KEYRING_SERVICE_NAME, token)

    @classmethod
    def get_token(cls) -> Optional[str]:
        """Retrieves the token from the secure keyring."""
        return SwitchCraftConfig.get_secret(cls.KEYRING_SERVICE_NAME)

    @classmethod
    def logout(cls):
        """Removes the token from the keyring."""
        SwitchCraftConfig.delete_secret(cls.KEYRING_SERVICE_NAME)

    @classmethod
    def is_authenticated(cls) -> bool:
        """Checks if a token exists."""
        return cls.get_token() is not None

    @classmethod
    def get_user_info(cls) -> Optional[Dict[str, Any]]:
        """
        Fetches the authenticated user's profile info.
        """
        token = cls.get_token()
        if not token:
            return None

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            response = requests.get(cls.USER_API, headers=headers, timeout=10)
            if response.status_code == 401:
                # Token might be expired/revoked
                logger.warning("Token unauthorized. Clearing token.")
                cls.logout()
                return None
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch user info: {e}")
            return None
