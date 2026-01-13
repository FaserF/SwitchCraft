import json
import logging
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class CommunityDBService:
    def __init__(self):
        # In a real scenario, this would fetch from a CDN or API.
        # For now, we simulate a local DB.
        self.db_path = Path("src/switchcraft/data/community/switches.json")
        self.db = self._load_db()

    def _load_db(self):
        if not self.db_path.exists():
            # Seed with some known tricky apps
            return {
                "hash_map": {
                    # Example Hash -> Switches
                    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855": ["/S", "/AllUsers"],
                },
                "name_map": {
                    "vlc": ["/L=1033", "/S"],
                    "notepad++": ["/S"],
                    "firefox": ["-ms"],
                    "chrome": ["/silent", "/install"],
                    "adobe reader": ["/sAll", "/rs", "/msi", "EULA_ACCEPT=YES"]
                }
            }
        try:
            with open(self.db_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load DB: {e}")
            return {}

    def get_switches_by_hash(self, file_path):
        """Calculate hash and lookup."""
        if not Path(file_path).exists():
            return None

        sha256 = self._get_hash(file_path)
        return self.db.get("hash_map", {}).get(sha256)

    def get_switches_by_name(self, filename):
        """Fuzzy lookup by filename."""
        name = Path(filename).stem.lower()
        # Very basic partial match
        for key, val in self.db.get("name_map", {}).items():
            if key in name:
                return val
        return None

    def _get_hash(self, filepath):
        try:
            h = hashlib.sha256()
            with open(filepath, "rb") as f:
                while chunk := f.read(8192):
                    h.update(chunk)
            return h.hexdigest()
        except (OSError, IOError) as e:
            logger.warning(f"Could not hash file {filepath}: {e}")
            return None
