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

    def _parse_table(self, output):
        import re
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
            else:
                 # Fallback: maybe it's just ID and Version?
                 # For now, just log debug.
                 logger.debug(f"Skipping malformed line (parts={len(parts)}): {line}")
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
            return subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
        except subprocess.TimeoutExpired:
            raise Exception("Install timed out (5 minutes)")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Install failed: {e.stdout} {e.stderr}")
