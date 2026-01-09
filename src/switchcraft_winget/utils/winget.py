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
        """Fallback search using winget CLI with robust table parsing."""
        try:
             cmd = ["winget", "search", query, "--source", "winget", "--accept-source-agreements"]
             startupinfo = self._get_startup_info()

             proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo)
             if proc.returncode != 0:
                 return []

             # Skip any leading empty lines/garbage
             lines = [l for l in proc.stdout.splitlines() if l.strip()]
             if len(lines) < 2:
                 return []

             # Find header line (must contain Name, Id, Version)
             header_idx = -1
             for i, line in enumerate(lines):
                 lower_line = line.lower()
                 # Use localized name detection or common substrings
                 # German: Name, ID, Version, Übereinstimmung
                 # English: Name, Id, Version, Match
                 if "name" in lower_line and "id" in lower_line and "version" in lower_line:
                     header_idx = i
                     break

             if header_idx == -1 or header_idx + 1 >= len(lines):
                 return []

             header = lines[header_idx]

             # Locate column starts
             # We look for "ID" (case insensitive) and "Version" as anchors
             import re

             # Robust ID anchor
             match_id = re.search(r'\bID\b', header, re.IGNORECASE)
             # Robust Version anchor
             match_ver = re.search(r'\bVersion\b', header, re.IGNORECASE)
             # Robust Source anchor (optional)
             match_source = re.search(r'\bSource\b|\bQuelle\b', header, re.IGNORECASE)

             if not match_id or not match_ver:
                 # Fallback to smart split if anchors fail
                 results = []
                 data_start = header_idx + 1
                 if lines[data_start].startswith("---"):
                     data_start += 1

                 for line in lines[data_start:]:
                     parts = re.split(r'\s{2,}', line.strip())
                     if len(parts) >= 3:
                         results.append({
                             "Name": parts[0],
                             "Id": parts[1],
                             "Version": parts[2],
                             "Source": parts[3] if len(parts) > 3 else "winget"
                         })
                 return results

             idx_id = match_id.start()
             idx_ver = match_ver.start()
             idx_source = match_source.start() if match_source else -1

             # The line below header is usually dashes, skip it
             data_start = header_idx + 1
             if lines[data_start].startswith("---"):
                 data_start += 1

             results = []
             for line in lines[data_start:]:
                 if not line.strip() or len(line) < idx_ver:
                     continue

                 name = line[:idx_id].strip()
                 pkg_id = line[idx_id:idx_ver].strip()

                 if idx_source != -1 and len(line) > idx_source:
                     version = line[idx_ver:idx_source].strip()
                     source = line[idx_source:].strip()
                 else:
                     version = line[idx_ver:].strip()
                     # If there's content after version but no source column detected,
                     # we might need to split version from a potential 'Match' column
                     if "  " in version:
                         v_parts = re.split(r'\s{2,}', version)
                         version = v_parts[0]
                     source = "winget"

                 if name and pkg_id:
                     results.append({
                         "Name": name,
                         "Id": pkg_id,
                         "Version": version,
                         "Source": source
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
