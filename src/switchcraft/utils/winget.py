import logging
import json
import yaml
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class WingetHelper:
    def __init__(self):
        # We don't use local repo in this new implementation generally, but keeping structure if needed
        self.local_repo = None

    def search_by_name(self, product_name: str) -> Optional[str]:
        """Search for a product name using PowerShell module or CLI."""
        if not product_name:
            return None

        # 1. PowerShell Search (Preferred)
        results = self.search_packages(product_name)
        if results:
            # Return winget.run link for the first match as a "URL" representation
            # or just the ID for internal use.
            # The original code expected a URL.
            first = results[0]
            pkg_id = first.get("Id")
            if pkg_id:
                parts = pkg_id.split(".")
                if len(parts) >= 2:
                     return f"https://winget.run/pkg/{parts[0]}/{'.'.join(parts[1:])}"
                return f"https://winget.run/pkg/{pkg_id}"

        return None

    def search_packages(self, query: str) -> List[Dict[str, str]]:
        """
        Search for packages using PowerShell Microsoft.WinGet.Client module.
        Returns list of {Id, Name, Version, Source}
        """
        import subprocess
        import json

        try:
            # Use PowerShell to find package and output as JSON
            # Find-WinGetPackage -Query <query> -Source winget | Select-Object Name, Id, Version, Source | ConvertTo-Json -Depth 1
            ps_script = f"Find-WinGetPackage -Query '{query}' -Source winget | Select-Object Name, Id, Version, Source | ConvertTo-Json -Depth 1"

            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]

            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo)

            if proc.returncode != 0:
                logger.warning(f"WinGet PS Search failed: {proc.stderr[:200]}")
                return []

            output = proc.stdout.strip()
            if not output: return []

            # PowerShell ConvertTo-Json can return single dict or list of dicts
            try:
                data = json.loads(output)
            except json.JSONDecodeError:
                return []

            results = []
            if isinstance(data, dict):
                data = [data] # Normalize to list

            for item in data:
                results.append({
                    "Name": item.get("Name", "Unknown"),
                    "Id": item.get("Id", "Unknown"),
                    "Version": item.get("Version", "Unknown"),
                    "Source": item.get("Source", "winget")
                })

            return results

        except Exception as e:
            logger.error(f"Winget PS Search Error: {e}")
            return []

    def get_package_details(self, package_id: str) -> Dict[str, str]:
        """Get details via PowerShell (Find-WinGetPackage)."""
        import subprocess
        import json

        try:
            # Find exact ID
            ps_script = f"Find-WinGetPackage -Id '{package_id}' -Source winget | ConvertTo-Json -Depth 2"

            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]

            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo)

            output = proc.stdout.strip()
            if not output: return {}

            item = json.loads(output)

            # Helper to safely get nested or direct keys
            # 'Provider' often holds Publisher name in PS object
            provider = item.get("Provider", {})
            publisher = provider.get("Name") if isinstance(provider, dict) else str(provider)

            return {
                "publisher": publisher or item.get("Source", ""),
                "name": item.get("Name", ""),
                "id": item.get("Id", ""),
                "version": item.get("Version", ""),
                "description": item.get("Description", ""),
                "homepage": item.get("Source", ""),
            }
        except Exception as e:
            logger.error(f"Winget PS Details Error: {e}")
            return {}
