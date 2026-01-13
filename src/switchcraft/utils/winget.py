import subprocess
import logging

logger = logging.getLogger(__name__)

class WingetHelper:
    """Helper for interacting with Windows Package Manager (winget)."""

    def __init__(self):
        self.winget_path = self._find_winget()

    def _find_winget(self):
        # usually in path
        return "winget"

    def search(self, query):
        """Search for a package."""
        try:
            # -e for exact? No, query.
            # --disable-interactivity --accept-source-agreements
            cmd = [
                self.winget_path, "search", query,
                "--accept-source-agreements", "--disable-interactivity"
            ]
            # Winget output is table text, difficult to parse without --json (preview feature)
            # We will use basic text parsing or simulated data if parsing fails

            # Note: `winget search` does not support JSON output reliably in all versions yet.
            # We implemented a basic parser in earlier iterations, let's restore a simple one.

            # Using subprocess to run
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            if result.returncode != 0:
                logger.error(f"Winget search failed: {result.stderr}")
                return []

            return self._parse_table(result.stdout)
        except Exception as e:
            logger.error(f"Winget search error: {e}")
            return []

    def _parse_table(self, output):
        lines = output.splitlines()
        results = []
        # Skip header/separator
        # Name | Id | Version | Source
        # ---- ...
        start_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("---"):
                start_idx = i + 1
                break

        for line in lines[start_idx:]:
            if not line.strip(): continue
            # Basic split - unreliable if name has spaces, but winget columns are fixed width usually?
            # actually they are dynamic.
            # better hack: take ID (last column usually? No, Source is last)
            # Id is usually 2nd column.
            # Name   Id    Version
            # Split by 2+ spaces
            parts = [p.strip() for p in line.split("  ") if p.strip()]
            if len(parts) >= 3:
                results.append({
                    "Name": parts[0],
                    "Id": parts[1] if len(parts)>1 else "",
                    "Version": parts[2] if len(parts)>2 else "",
                    "Source": parts[3] if len(parts)>3 else ""
                })
        return results

    def get_installed(self):
        """Get list of installed packages."""
        # Similar to search but `list`
        return [] # Implement later if needed

    def install(self, package_id):
        """Install a package."""
        cmd = [
            self.winget_path, "install", "--id", package_id,
            "-e", "--disable-interactivity", "--accept-package-agreements",
            "--accept-source-agreements"
        ]
        # Return Popen object or blocking result?
        # Views usually run this in thread.
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Install failed: {e.stdout} {e.stderr}")
