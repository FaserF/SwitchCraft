import requests
import logging
import sys
from packaging import version
from switchcraft import __version__

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
        Checks for updates based on configured channel with cross-channel logic.
        Returns (has_update, latest_version_str, release_info_dict)
        """
        # If running from source (not frozen), assume dev and skip update check
        if not getattr(sys, 'frozen', False):
             return False, self.current_version, None

        candidates = []

        # Always check Stable
        stable_ver, stable_data = self._get_latest_stable_release()
        if stable_ver:
            candidates.append((stable_ver, stable_data, "stable"))

        # If Beta or Dev, check Beta
        if self.channel in [self.CHANNEL_BETA, self.CHANNEL_DEV]:
             beta_ver, beta_data = self._get_latest_beta_release()
             if beta_ver:
                 candidates.append((beta_ver, beta_data, "beta"))

        # If Dev, check Dev
        if self.channel == self.CHANNEL_DEV:
            dev_ver, dev_data = self._get_latest_dev_commit()
            if dev_ver:
                candidates.append((dev_ver, dev_data, "dev"))

        if not candidates:
            return False, self.current_version, None

        return self._resolve_best_update(candidates)

    def _resolve_best_update(self, candidates):
        """
        Selects the best update from candidates and populates fields.
        Candidate tuple: (version_str, data_dict, source_channel)
        """
        valid_updates = []

        try:
            curr_parsed = version.parse(self.current_version)
        except Exception:
            # Fallback for non-standard versions like 'dev-xxxx'
            curr_parsed = version.Version("0.0.0")

        for ver, data, source in candidates:
             is_newer = False
             if source == "dev":
                 # For dev, check if SHA is different
                 # Current version format might be:
                 # - PEP 440: 2026.1.2.dev0+9d07a00
                 # - Legacy: 2026.1.1-dev-abcdef OR just dev-abcdef
                 if "dev" in self.current_version.lower():
                      curr_sha = ""
                      # Try PEP 440 format first: YYYY.M.P.dev0+SHA
                      if "+" in self.current_version:
                           # Extract SHA after the + sign
                           parts = self.current_version.split("+")
                           if len(parts) >= 2:
                                curr_sha = parts[-1]
                      # Fallback to legacy format: YYYY.M.P-dev-SHA or dev-SHA
                      if not curr_sha:
                           parts = self.current_version.split("-")
                           # If format is YYYY.M.P-dev-SHA
                           if len(parts) >= 3 and len(parts[-1]) >= 7:
                                curr_sha = parts[-1]
                           # If format is dev-SHA
                           elif len(parts) == 2 and parts[0].lower() == "dev":
                                curr_sha = parts[1]

                      # Remote 'ver' from _get_latest_dev_commit is 'dev-{sha}'
                      new_sha = ver.split("-")[-1] if "-" in ver else ""

                      if curr_sha and new_sha and curr_sha != new_sha:
                           is_newer = True
                      elif not curr_sha:
                           # If we can't extract current SHA, assume update available
                           is_newer = True
                 else:
                      # If currently on Stable/Beta and switching to Dev channel
                      is_newer = True
             else:
                 # Standard version compare for Stable/Beta
                 try:
                     v_cand = version.parse(ver)
                     if v_cand > curr_parsed:
                         is_newer = True
                 except Exception:
                     # If parsing fails, but it's different from current, maybe it's newer?
                     # But safer to just ignore if we can't parse.
                     pass

             if is_newer:
                 valid_updates.append((ver, data, source))

        if not valid_updates:
            # Even if no update, populate latest_version for display
            if candidates:
               # Sort candidates by same key to find what IS latest even if not "newer"
               candidates.sort(key=self._sort_key, reverse=True)
               best_cand_ver, best_cand_data, _ = candidates[0]
               self._populate_fields(best_cand_ver, best_cand_data)
               # Return the LATEST REMOTE version so UI shows it, even if no update needed
               return False, best_cand_ver, best_cand_data

            return False, self.current_version, None

        # Sort candidates to find the "best" one.
        valid_updates.sort(key=self._sort_key, reverse=True)

        best_ver, best_data, _ = valid_updates[0]
        self._populate_fields(best_ver, best_data)
        return True, best_ver, best_data

    def _sort_key(self, item):
        ver_str, data, source = item

        # Priority: Date > Version > Channel
        # Get date
        date_str = data.get("published_at") or ""

        try:
            v = version.parse(ver_str)
        except Exception:
            v = version.Version("0.0.0")

        # Channel tie-breaker: Stable (2) > Beta (1) > Dev (0)
        # But Date should be the main factor for "latest"
        priority = 2 if source == "stable" else 1 if source == "beta" else 0

        return (date_str, v, priority)

    def _populate_fields(self, ver, data):
        self.latest_version = ver
        self.release_url = data.get("html_url")
        self.release_notes = data.get("body")
        self.release_date = data.get("published_at")
        self.assets = data.get("assets", [])
        self.is_prerelease = data.get("prerelease", False)


    def _get_latest_stable_release(self):
        try:
            response = requests.get(f"{self.API_BASE}/releases/latest", timeout=5)
            if response.status_code == 200:
                data = response.json()
                tag = data.get("tag_name", "").lstrip("v")
                return tag, data
        except Exception:
            pass
        return None, None

    def _get_latest_beta_release(self):
        try:
            response = requests.get(f"{self.API_BASE}/releases", timeout=5)
            if response.status_code == 200:
                # First release that is prerelease=True? Or just first release?
                # GitHub list is sorted by date.
                # We want the newest release that IS a beta (prerelease).
                for rel in response.json():
                    if rel.get("prerelease"):
                        tag = rel.get("tag_name", "").lstrip("v")
                        return tag, rel
        except Exception:
            pass
        return None, None

    def _get_latest_dev_commit(self):
        try:
            response = requests.get(f"{self.API_BASE}/commits/main", timeout=5)
            if response.status_code == 200:
                data = response.json()
                sha = data.get("sha", "")[:7]
                msg = data.get("commit", {}).get("message", "").split("\n")[0]
                # Construct a pseudo-data dict that mimics release
                date = data.get("commit", {}).get("committer", {}).get("date", "")
                fake_data = {
                    "html_url": f"https://github.com/{self.GITHUB_REPO}/commit/{data.get('sha', '')}",
                    "body": f"Latest commit: {msg}",
                    "published_at": date,
                    "name": f"Dev Build {sha}",
                    "assets": [] # Dev has no assets usually
                }
                return f"dev-{sha}", fake_data
        except Exception:
            pass
        return None, None


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
