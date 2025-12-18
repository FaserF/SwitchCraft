import json
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.services.auth_service import AuthService

logger = logging.getLogger(__name__)

class SyncService:
    """
    Handles syncing SwitchCraft settings to GitHub Gists.
    """

    GIST_API = "https://api.github.com/gists"
    GIST_FILENAME = "switchcraft_settings.json"
    GIST_DESCRIPTION = "SwitchCraft CloudSync Settings"

    @classmethod
    def _get_headers(cls) -> Optional[Dict[str, str]]:
        token = AuthService.get_token()
        if not token:
            logger.warning("No auth token found. Cannot sync.")
            return None
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    @classmethod
    def find_sync_gist(cls) -> Optional[str]:
        """
        Finds the Gist ID for SwitchCraft settings.
        Iterates through user's gists to find one with the specific filename.
        """
        headers = cls._get_headers()
        if not headers:
            return None

        try:
            # List user's gists
            # Note: Pagination might be needed if user has many gists,
            # but for now we check the first page (default 30).
            response = requests.get(cls.GIST_API, headers=headers, timeout=10)
            response.raise_for_status()
            gists = response.json()

            for gist in gists:
                if cls.GIST_FILENAME in gist.get('files', {}):
                    return gist['id']
            return None

        except requests.RequestException as e:
            logger.error(f"Failed to find sync gist: {e}")
            return None

    @classmethod
    def create_sync_gist(cls, content: Dict[str, Any]) -> Optional[str]:
        """
        Creates a new Gist with the settings.
        """
        headers = cls._get_headers()
        if not headers:
            return None

        payload = {
            "description": cls.GIST_DESCRIPTION,
            "public": False,
            "files": {
                cls.GIST_FILENAME: {
                    "content": json.dumps(content, indent=4)
                }
            }
        }

        try:
            response = requests.post(cls.GIST_API, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            gist = response.json()
            return gist['id']
        except requests.RequestException as e:
            logger.error(f"Failed to create sync gist: {e}")
            return None

    @classmethod
    def update_sync_gist(cls, gist_id: str, content: Dict[str, Any]) -> bool:
        """
        Updates an existing Gist with new settings.
        """
        headers = cls._get_headers()
        if not headers:
            return False

        payload = {
            "files": {
                cls.GIST_FILENAME: {
                    "content": json.dumps(content, indent=4)
                }
            }
        }

        try:
            url = f"{cls.GIST_API}/{gist_id}"
            response = requests.patch(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error(f"Failed to update sync gist: {e}")
            return False

    @classmethod
    def get_remote_settings(cls, gist_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves settings from the Gist.
        """
        headers = cls._get_headers()
        if not headers:
            return None

        try:
            url = f"{cls.GIST_API}/{gist_id}"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            gist = response.json()

            file_data = gist.get('files', {}).get(cls.GIST_FILENAME, {})
            content = file_data.get('content')

            if content:
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    logger.error("Failed to decode remote settings JSON.")
                    return None
            return None

        except requests.RequestException as e:
            logger.error(f"Failed to get remote settings: {e}")
            return None

    @classmethod
    def sync_up(cls) -> bool:
        """
        Uploads local settings to the Cloud (Gist).
        Creates the Gist if it doesn't exist.
        """
        local_prefs = SwitchCraftConfig.export_preferences()
        gist_id = cls.find_sync_gist()

        if gist_id:
            logger.info(f"Found existing Gist {gist_id}. Updating...")
            return cls.update_sync_gist(gist_id, local_prefs)
        else:
            logger.info("No Gist found. Creating new...")
            new_id = cls.create_sync_gist(local_prefs)
            return new_id is not None

    @classmethod
    def sync_down(cls) -> bool:
        """
        Downloads settings from Cloud (Gist) and applies them locally.
        """
        gist_id = cls.find_sync_gist()
        if not gist_id:
            logger.warning("No sync Gist found on GitHub.")
            return False

        remote_prefs = cls.get_remote_settings(gist_id)
        if remote_prefs:
            SwitchCraftConfig.import_preferences(remote_prefs)
            return True

        return False
