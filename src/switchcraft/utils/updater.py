import requests
import logging
from packaging import version
from switchcraft import __version__
from datetime import datetime

logger = logging.getLogger(__name__)

class UpdateChecker:
    GITHUB_REPO = "FaserF/SwitchCraft"
    API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}"

    # Update channels
    CHANNEL_STABLE = "stable"
    CHANNEL_BETA = "beta"
    CHANNEL_DEV = "dev"

    def __init__(self, channel=None):
        self.current_version = __version__
        self.channel = channel or self.CHANNEL_STABLE
        self.latest_version = None
        self.release_url = None
        self.release_notes = None
        self.release_date = None
        self.assets = []
        self.is_prerelease = False
        self.commit_sha = None
        self.commit_date = None

    def check_for_updates(self):
        """
        Checks for updates based on configured channel.
        Returns (has_update, latest_version_str, release_info_dict)
        """
        if self.channel == self.CHANNEL_DEV:
            return self._check_dev_channel()
        elif self.channel == self.CHANNEL_BETA:
            return self._check_beta_channel()
        else:
            return self._check_stable_channel()

    def _check_stable_channel(self):
        """Check for stable releases (non-prerelease)."""
        try:
            response = requests.get(f"{self.API_BASE}/releases/latest", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return self._process_release(data)
        except Exception as e:
            logger.error(f"Failed to check stable updates: {e}")
        return False, None, None

    def _check_beta_channel(self):
        """Check for beta/pre-releases."""
        try:
            response = requests.get(f"{self.API_BASE}/releases", timeout=5)
            if response.status_code == 200:
                releases = response.json()
                # Find latest release (including pre-releases)
                for release in releases:
                    # Return the first one (most recent)
                    return self._process_release(release)
        except Exception as e:
            logger.error(f"Failed to check beta updates: {e}")
        return False, None, None

    def _check_dev_channel(self):
        """Check for development updates (latest commit on main branch)."""
        try:
            # Get latest commit on main branch
            response = requests.get(f"{self.API_BASE}/commits/main", timeout=5)
            if response.status_code == 200:
                data = response.json()
                commit_sha = data.get("sha", "")[:7]
                commit_date_str = data.get("commit", {}).get("committer", {}).get("date", "")
                commit_message = data.get("commit", {}).get("message", "").split("\n")[0]

                self.commit_sha = commit_sha
                self.latest_version = f"dev-{commit_sha}"
                self.release_url = f"https://github.com/{self.GITHUB_REPO}/commit/{data.get('sha', '')}"
                self.release_notes = f"Latest commit: {commit_message}"

                if commit_date_str:
                    self.commit_date = datetime.fromisoformat(commit_date_str.replace("Z", "+00:00"))
                    self.release_date = commit_date_str

                # For dev channel, always show update if different commit
                # Parse current version to check if it's already a dev version
                if "-dev" in self.current_version or "-beta" in self.current_version:
                    # Currently on dev/beta - check if commit is newer
                    if commit_sha not in self.current_version:
                        return True, self.latest_version, {"sha": commit_sha, "message": commit_message}
                else:
                    # On stable - offer dev if user specifically chose dev channel
                    return True, self.latest_version, {"sha": commit_sha, "message": commit_message}

        except Exception as e:
            logger.error(f"Failed to check dev updates: {e}")
        return False, None, None

    def _process_release(self, data):
        """Process release data and check if update available."""
        tag_name = data.get("tag_name", "").lstrip("v")
        self.latest_version = tag_name
        self.release_url = data.get("html_url")
        self.release_notes = data.get("body")
        self.release_date = data.get("published_at")
        self.assets = data.get("assets", [])
        self.is_prerelease = data.get("prerelease", False)

        try:
            # Parse versions - handle dev/beta suffixes
            current_base = self.current_version.split("-")[0]

            # If on beta channel, accept pre-releases as updates
            if self.channel == self.CHANNEL_BETA:
                if version.parse(tag_name) > version.parse(self.current_version):
                    return True, tag_name, data
            else:
                # Stable channel - only stable releases
                if not self.is_prerelease:
                    if version.parse(tag_name) > version.parse(current_base):
                        return True, tag_name, data
        except Exception as e:
            logger.error(f"Version comparison failed: {e}")

        return False, None, None

    def get_download_url(self, file_extension=".exe"):
        """Get download URL for the appropriate asset."""
        # For dev channel, point to actions/builds or source
        if self.channel == self.CHANNEL_DEV:
            return f"https://github.com/{self.GITHUB_REPO}/archive/refs/heads/main.zip"

        for asset in self.assets:
            name = asset.get("name", "")
            # Prefer installer for stable/beta
            if "Setup" in name and name.endswith(file_extension):
                return asset.get("browser_download_url")

        # Fallback to portable
        for asset in self.assets:
            if asset.get("name", "").endswith(file_extension):
                return asset.get("browser_download_url")

        return self.release_url
