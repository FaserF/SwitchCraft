import logging
import json
import subprocess
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class WingetHelper:
    def __init__(self):
        self.local_repo = None

    def search_by_name(self, product_name: str) -> Optional[str]:
        """Search for a product name using PowerShell module or CLI."""
        if not product_name:
            return None
        results = self.search_packages(product_name)
        if results:
            first = results[0]
            pkg_id = first.get("Id")
            if pkg_id:
                # Construct GitHub URL for microsoft/winget-pkgs
                # Structure: manifests/{p_char}/{Publisher}/{Package}
                parts = pkg_id.split(".", 1)
                if len(parts) == 2:
                    publisher, package = parts
                    p_char = publisher[0].lower()
                    return f"https://github.com/microsoft/winget-pkgs/tree/master/manifests/{p_char}/{publisher}/{package}"

                # Fallback for simple IDs or weird structures
                return f"https://github.com/microsoft/winget-pkgs/search?q={pkg_id}"
        return None

    def search_packages(self, query: str) -> List[Dict[str, str]]:
        """
        Search for packages using PowerShell Microsoft.WinGet.Client module.
        Returns list of {Id, Name, Version, Source}
        """
        try:
            ps_script = f"Find-WinGetPackage -Query '{query}' -Source winget | Select-Object Name, Id, Version, Source | ConvertTo-Json -Depth 1"
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]
            startupinfo = self._get_startup_info()

            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo)

            if proc.returncode != 0:
                err_msg = proc.stderr.strip()
                if "Find-WinGetPackage" in err_msg:
                    logger.info("Winget PowerShell module not found. Attempting Winget CLI fallback...")
                    return self._search_via_cli(query)
                return []

            output = proc.stdout.strip()
            if not output:
                return []

            try:
                data = json.loads(output)
            except json.JSONDecodeError:
                return []

            results = []
            if isinstance(data, dict):
                data = [data]

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
        try:
            ps_script = f"Find-WinGetPackage -Id '{package_id}' -Source winget | ConvertTo-Json -Depth 2"
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]
            startupinfo = self._get_startup_info()

            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo)
            output = proc.stdout.strip()
            if not output:
                return {}

            item = json.loads(output)
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

    def install_package(self, package_id: str, scope: str = "machine") -> bool:
        """Install a package via Winget CLI."""
        if scope not in ("machine", "user"):
            logger.error(f"Invalid scope: {scope}")
            return False

        cmd = [
            "winget", "install",
            "--id", package_id,
            "--scope", scope,
            "--accept-package-agreements",
            "--accept-source-agreements"
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                logger.error(f"Winget install failed: {proc.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Winget install exception: {e}")
            return False

    def download_package(self, package_id: str, dest_dir: Path) -> Optional[Path]:
        """Download a package installer to dest_dir. Returns path to installer if found."""
        cmd = ["winget", "download", "--id", package_id, "--dir", str(dest_dir), "--accept-source-agreements", "--accept-package-agreements"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                logger.error(f"Winget download failed: {proc.stderr}")
                return None

            # Find the installer file
            files = list(dest_dir.glob("*.*"))
            for f in files:
                if f.suffix.lower() in [".exe", ".msi"]:
                    return f
            return None
        except Exception as e:
            logger.error(f"Winget download exception: {e}")
            return None

    def _search_via_cli(self, query: str) -> List[Dict[str, str]]:
        """Fallback search using winget CLI."""
        import re
        try:
             cmd = ["winget", "search", query, "--source", "winget", "--accept-source-agreements"]
             startupinfo = self._get_startup_info()

             proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo)
             if proc.returncode != 0:
                 return []

             lines = proc.stdout.strip().splitlines()
             if len(lines) < 3:
                 return []

             results = []
             start_idx = 0
             for i, line in enumerate(lines):
                 if hasattr(line, "startswith") and line.startswith("---"):
                     start_idx = i + 1
                     break

             for line in lines[start_idx:]:
                 if not line.strip():
                     continue
                 parts = re.split(r'\s{2,}', line.strip())
                 if len(parts) >= 3:
                     results.append({
                         "Name": parts[0],
                         "Id": parts[1],
                         "Version": parts[2],
                         "Source": parts[-1] if len(parts) > 3 else "winget"
                     })
             return results

        except Exception as e:
            logger.debug(f"Winget CLI fallback failed: {e}")
            return []

    def _get_startup_info(self):
        if hasattr(subprocess, 'STARTUPINFO'):
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            return si
        return None
