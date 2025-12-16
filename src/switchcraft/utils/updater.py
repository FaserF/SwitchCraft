import requests
import logging
from packaging import version
from switchcraft import __version__
import webbrowser

logger = logging.getLogger(__name__)

class UpdateChecker:
    GITHUB_REPO = "FaserF/SwitchCraft"
    API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    def __init__(self):
        self.current_version = __version__
        self.latest_version = None
        self.release_url = None
        self.release_notes = None
        self.release_date = None
        self.assets = []

    def check_for_updates(self):
        """
        Checks for updates. Returns (has_update, latest_version_str, release_info_dict)
        """
        try:
            response = requests.get(self.API_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                tag_name = data.get("tag_name", "").lstrip("v")
                self.latest_version = tag_name
                self.release_url = data.get("html_url")
                self.release_notes = data.get("body")
                self.release_date = data.get("published_at")
                self.assets = data.get("assets", [])

                if version.parse(tag_name) > version.parse(self.current_version):
                    return True, tag_name, data
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")

        return False, None, None

    def get_download_url(self, file_extension=".exe"):
        for asset in self.assets:
            if asset.get("name", "").endswith(file_extension):
                return asset.get("browser_download_url")
        return self.release_url
