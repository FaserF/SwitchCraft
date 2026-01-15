import subprocess
import logging
import re

logger = logging.getLogger(__name__)

class WingetHelper:
    """Helper for interacting with Windows Package Manager (winget)."""

    def __init__(self):
        self.winget_path = self._find_winget()

    def _find_winget(self):
        # usually in path
        return "winget"

    def search_by_name(self, name):
        """Search by name and return the most likely Winget ID or link."""
        if not name:
            return None
        results = self.search_packages(name)
        if results:
            return results[0].get("Id")
        return None

    def search_packages(self, query):
        """Search for a package."""
        try:
            cmd = [
                self.winget_path, "search", query,
                "--accept-source-agreements", "--disable-interactivity"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=30)
            if result.returncode != 0:
                logger.error(f"Winget search failed: {result.stderr}")
                return []

            return self._parse_table(result.stdout)
        except subprocess.TimeoutExpired:
            logger.error("Winget search timed out")
            return []
        except Exception as e:
            logger.error(f"Winget search error: {e}")
            return []

    def get_package_details(self, package_id):
        """Get full details for a package using 'winget show'."""
        try:
            cmd = [
                self.winget_path, "show", "--id", package_id,
                "--accept-source-agreements", "--disable-interactivity"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=20)
            if result.returncode != 0:
                return {}

            return self._parse_details(result.stdout)
        except Exception as e:
            logger.error(f"Failed to get winget details for {package_id}: {e}")
            return {}

    def _parse_table(self, output):
        lines = output.splitlines()
        results = []

        start_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("---"):
                start_idx = i + 1
                break

        for line in lines[start_idx:]:
            if not line.strip():
                continue

            # Use regex to split by 2 or more spaces
            parts = re.split(r'\s{2,}', line.strip())

            if len(parts) >= 3:
                results.append({
                    "Name": parts[0],
                    "Id": parts[1],
                    "Version": parts[2],
                    "Source": parts[3] if len(parts) > 3 else ""
                })
        return results

    def _parse_details(self, output):
        """Parse 'winget show' output into a dictionary."""
        details = {}
        for line in output.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                details[key.strip()] = val.strip()
        return details

    def get_installed(self):
        """Get list of installed packages."""
        return [] # Implement later if needed

    def install(self, package_id):
        """Install a package."""
        cmd = [
            self.winget_path, "install", "--id", package_id,
            "-e", "--disable-interactivity", "--accept-package-agreements",
            "--accept-source-agreements"
        ]
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
        except subprocess.TimeoutExpired:
            raise Exception("Install timed out (5 minutes)")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Install failed: {e.stdout} {e.stderr}")
