import logging
import json
import subprocess
import requests
import time
from pathlib import Path
from typing import Optional, List, Dict
import re

logger = logging.getLogger(__name__)

# API Configuration
WINGET_API_BASE = "https://winget-pkg-api.onrender.com/api/v1"
WINGET_API_TIMEOUT = 10  # seconds

class WingetHelper:
    # Class-level cache for search results
    _search_cache: Dict[str, tuple] = {}  # {query: (timestamp, results)}
    _cache_ttl = 300  # 5 minutes

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
        Search for packages. Tries API first, then falls back to local CLI.
        Results are cached for 5 minutes.
        """
        if not query:
            return []

        # Check cache first
        cache_key = query.lower().strip()
        if cache_key in self._search_cache:
            timestamp, cached_results = self._search_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                logger.debug(f"Winget cache hit for '{query}'")
                return cached_results

        # Try API first (faster)
        results = self._search_via_api(query)

        # If API returns empty or fails, try local CLI
        if not results:
            logger.info(f"API returned no results for '{query}', trying local CLI...")
            results = self._search_via_powershell(query)

        # If PowerShell fails, try CLI directly
        if not results:
            results = self._search_via_cli(query)

        # Cache results
        if results:
            self._search_cache[cache_key] = (time.time(), results)

        return results

    def _search_via_api(self, query: str) -> List[Dict[str, str]]:
        """Search using the winget-pkg-api (fast online API)."""
        try:
            url = f"{WINGET_API_BASE}/search"
            params = {"q": query}

            response = requests.get(url, params=params, timeout=WINGET_API_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                # API returns a list of packages
                if isinstance(data, list):
                    results = []
                    for pkg in data[:50]:  # Limit to 50 results
                        results.append({
                            "Name": pkg.get("PackageName", pkg.get("name", "")),
                            "Id": pkg.get("PackageIdentifier", pkg.get("id", "")),
                            "Version": pkg.get("PackageVersion", pkg.get("version", "")),
                            "Source": "winget"
                        })
                    logger.debug(f"API returned {len(results)} results for '{query}'")
                    return results
            else:
                logger.debug(f"API returned status {response.status_code}")

        except requests.exceptions.Timeout:
            logger.debug(f"API timeout for query '{query}'")
        except Exception as ex:
            logger.debug(f"API search failed: {ex}")

        return []

    def _search_via_powershell(self, query: str) -> List[Dict[str, str]]:
        """Search using PowerShell Microsoft.WinGet.Client module."""
        try:
            ps_script = f"Find-WinGetPackage -Query '{query}' | Select-Object Name, Id, Version, Source | ConvertTo-Json -Depth 1"
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script]
            startupinfo = self._get_startup_info()

            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo, timeout=30)

            if proc.returncode != 0:
                logger.debug(f"PowerShell search failed: {proc.stderr[:200] if proc.stderr else 'No error'}")
                return []

            output = proc.stdout.strip()
            if not output:
                logger.debug("Winget PS Search: Empty output")
                return []

            logger.debug(f"Winget PS Search raw output: {output}")
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
        """
        Get detailed package information using 'winget show' command.
        This provides full manifest details including Description, License, Homepage, etc.
        """
        try:
            # Use 'winget show' which provides full manifest details
            cmd = ["winget", "show", "--id", package_id, "--source", "winget", "--accept-source-agreements"]
            startupinfo = self._get_startup_info()

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                startupinfo=startupinfo
            )

            output = proc.stdout.strip()
            if not output:
                return {}

            # Parse the key: value format from winget show output
            details = self._parse_winget_show_output(output)
            return details

        except Exception as e:
            logger.error(f"Winget show error: {e}")
            return {}

    def _parse_winget_show_output(self, output: str) -> Dict[str, str]:
        """
        Parse the output of 'winget show' command into a dictionary.
        Handles multi-line values like Description and nested structure.
        """
        details = {}
        lines = output.splitlines()

        # Common field mappings (handles both English and German)
        field_mappings = {
            # English
            'name': 'Name',
            'id': 'Id',
            'version': 'Version',
            'publisher': 'Publisher',
            'publisher url': 'PublisherUrl',
            'publisher support url': 'PublisherSupportUrl',
            'author': 'Author',
            'moniker': 'Moniker',
            'description': 'Description',
            'homepage': 'Homepage',
            'license': 'License',
            'license url': 'LicenseUrl',
            'privacy url': 'PrivacyUrl',
            'copyright': 'Copyright',
            'copyright url': 'CopyrightUrl',
            'release notes': 'ReleaseNotes',
            'release notes url': 'ReleaseNotesUrl',
            'tags': 'Tags',
            'installer type': 'InstallerType',
            'installer url': 'InstallerUrl',
            'installer sha256': 'InstallerSha256',
            # German
            'herausgeber': 'Publisher',
            'herausgeber-url': 'PublisherUrl',
            'beschreibung': 'Description',
            'startseite': 'Homepage',
            'lizenz': 'License',
            'lizenz-url': 'LicenseUrl',
            'datenschutz-url': 'PrivacyUrl',
            'urheberrecht': 'Copyright',
            'versionshinweise': 'ReleaseNotes',
        }

        current_key = None
        current_value_lines = []

        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue

            # Check if this is a new key: value pair
            if ':' in line and not line.startswith(' ') and not line.startswith('\t'):
                # Save previous key if exists
                if current_key:
                    value = '\n'.join(current_value_lines).strip()
                    details[current_key] = value

                # Parse new key: value
                parts = line.split(':', 1)
                raw_key = parts[0].strip().lower()
                raw_value = parts[1].strip() if len(parts) > 1 else ''

                # Map to normalized key name
                normalized_key = field_mappings.get(raw_key, parts[0].strip())
                current_key = normalized_key
                current_value_lines = [raw_value] if raw_value else []

            elif current_key and (line.startswith(' ') or line.startswith('\t')):
                # This is a continuation of the previous value (multi-line description, etc.)
                current_value_lines.append(line.strip())

        # Don't forget the last key
        if current_key:
            value = '\n'.join(current_value_lines).strip()
            details[current_key] = value

        return details

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
             cmd = ["winget", "search", query, "--accept-source-agreements"]
             startupinfo = self._get_startup_info()

             proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo)
             if proc.returncode != 0:
                 return []

             # Skip any leading empty lines/garbage
             lines = [line for line in proc.stdout.splitlines() if line.strip()]
             logger.debug(f"Winget CLI fallback lines: {len(lines)}")
             if len(lines) < 2:
                 logger.debug(f"Winget CLI output too short: {proc.stdout}")
                 return []

             # Find header line (must contain Name, Id, Version)
             header_idx = -1
             for i, line in enumerate(lines):
                 lower_line = line.lower()
                 # Even more robust: just check for 'ID' and 'Version'/ 'Vers'
                 if "id" in lower_line and ("ver" in lower_line):
                     header_idx = i
                     break

             if header_idx == -1 or header_idx + 1 >= len(lines):
                 logger.debug("Failed to find Winget table header. Trying smart split on all lines.")
                 results = []
                 for line in lines:
                    if "---" in line:
                        continue
                    parts = re.split(r'\s{2,}', line.strip())
                    if len(parts) >= 3 and "." in parts[1]: # IDs usually have dots
                        results.append({
                            "Name": parts[0],
                            "Id": parts[1],
                            "Version": parts[2],
                            "Source": parts[3] if len(parts) > 3 else "winget"
                        })
                 return results

             header = lines[header_idx]

             # Locate column starts
             # We look for "ID" (case insensitive) and "Version" as anchors


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
             logger.debug(f"Winget CLI logic parsed {len(results)} results")
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
