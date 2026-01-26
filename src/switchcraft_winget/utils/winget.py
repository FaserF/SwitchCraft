import logging
import json
import subprocess
import requests
import time
from pathlib import Path
from typing import Optional, List, Dict
import re

logger = logging.getLogger(__name__)

# API Configuration - using winget.run v2 API which is more reliable and comprehensive
WINGET_API_BASE = "https://api.winget.run/v2"
WINGET_API_TIMEOUT = 20  # seconds

class WingetHelper:
    # Class-level cache for search results
    _search_cache: Dict[str, tuple] = {}  # {query: (timestamp, results)}
    _cache_ttl = 300  # 5 minutes

    def __init__(self, auto_install_winget: bool = True, github_token: str = None):
        # Detect WASM environment
        import sys
        self.is_wasm = sys.platform == "emscripten" or sys.platform == "wasi"

        self.local_repo = None
        # Disable auto-install if on WASM
        self.auto_install_winget = auto_install_winget and not self.is_wasm
        self.github_token = github_token

        if self.is_wasm:
            logger.info("WingetHelper running in WASM mode. Subprocess dependent features are disabled.")

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
        Search for Winget packages matching a query using multiple sources and cache results.

        Performs searches in this order:
        1. PowerShell (Microsoft.WinGet.Client) - Native, most reliable.
        2. GitHub API (Official Repo) - If 'github_token' is provided (avoids rate limits).
        3. Winget.run API (Official Mirror) - Fast, public, comprehensive V2 API.
        4. CLI (winget search) - Native fallback.
        5. Static Dataset - Offline fallback.

        Parameters:
            query (str): The search term to query for; ignored if empty.

        Returns:
            results (List[Dict[str, str]]): A list of result dictionaries.
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

        # 1. Try PowerShell first (most reliable on Desktop)
        results = self._search_via_powershell(query)

        # 2. If PowerShell fails, try GitHub API (Official Source) IF token is available
        if not results and self.github_token:
            logger.info(f"PowerShell search failed. specific token provided. Using GitHub Official Source for '{query}'...")
            results = self._search_via_github(query)

        # 3. If GitHub unavailable/failed, try Winget.run API (Official Mirror)
        if not results:
            logger.info(f"Trying Winget.run API (Official Mirror) for '{query}'...")
            results = self._search_via_api(query)

        # 4. If API also fails, try CLI directly as last resort
        if not results:
            logger.info(f"API returned no results for '{query}', trying CLI as fallback...")
            results = self._search_via_cli(query)

        # 5. If CLI also fails, use static dataset (always available)
        if not results:
            logger.info(f"CLI returned no results for '{query}', using static dataset...")
            results = self._search_via_static_dataset(query)

        # Cache results
        if results:
            self._search_cache[cache_key] = (time.time(), results)

        return results

    def _search_via_github(self, query: str) -> List[Dict[str, str]]:
        """
        Search the official microsoft/winget-pkgs repository via GitHub API.
        Requires self.github_token to be set to avoid strict rate limits.
        """
        if not self.github_token:
            return []

        try:
            url = "https://api.github.com/search/code"
            # Search for manifests in the microsoft/winget-pkgs repo
            # Using filename match for better relevance
            q = f"{query} repo:microsoft/winget-pkgs path:manifests"
            params = {"q": q, "per_page": 20}
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {self.github_token}"
            }

            logger.debug(f"Querying GitHub API (Official Source): {q}")
            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                results = []

                for item in items:
                    path = item.get("path", "")
                    # Path format: manifests/p/Publisher/Package/Version/Package.yaml
                    # Example: manifests/g/Google/Chrome/113.0.5672.93/Google.Chrome.installer.yaml
                    parts = path.split("/")
                    if len(parts) >= 5:
                        publisher = parts[2]
                        package = parts[3]
                        version = parts[4]
                        pkg_id = f"{publisher}.{package}"
                        name = package # Fallback name

                        results.append({
                            "Name": name, # Ideally we fetch content to get real name, but path is fast
                            "Id": pkg_id,
                            "Version": version,
                            "Source": "github"
                        })
                logger.info(f"GitHub API returned {len(results)} results")
                return results
            elif response.status_code == 403 or response.status_code == 429:
                logger.warning("GitHub API rate limit exceeded.")
            else:
                logger.warning(f"GitHub API returned status {response.status_code}: {response.text[:100]}")

        except Exception as ex:
            logger.error(f"GitHub Search failed: {ex}")

        return []

    def _search_via_api(self, query: str) -> List[Dict[str, str]]:
        """Search using winget.run v2 API for comprehensive Winget package data."""
        try:
            # winget.run search endpoint
            url = f"{WINGET_API_BASE}/packages"
            params = {"query": query} # v2 uses 'query' parameter

            logger.debug(f"Querying Winget API: {url} with params {params}")
            response = requests.get(url, params=params, timeout=WINGET_API_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                results = []

                # winget.run v2 returns structure: {"Packages": [...], "Total": ...}
                packages = data.get("Packages", [])

                for pkg in packages[:100]:  # Return up to 100 results
                    pkg_id = pkg.get("Id")
                    latest = pkg.get("Latest", {})
                    name = latest.get("Name")

                    # Some packages might be missing Latest info, try top level or skip
                    if not name: name = pkg_id

                    versions = pkg.get("Versions", [])
                    version = versions[0] if versions else "Latest"

                    if name and pkg_id:
                        results.append({
                            "Name": name,
                            "Id": pkg_id,
                            "Version": version,
                            "Source": "winget"
                        })

                logger.info(f"winget.run API returned {len(results)} results for '{query}'")
                return results
            else:
                logger.debug(f"winget.run API returned status {response.status_code}")

        except requests.exceptions.Timeout:
            logger.debug(f"winget.run API timeout for query '{query}'")
        except Exception as ex:
            logger.debug(f"winget.run API search failed: {ex}")

        # Fallback to static dataset if API fails completely
        return self._search_via_static_dataset(query)

    def _search_via_static_dataset(self, query: str) -> List[Dict[str, str]]:
        """Search using a static dataset of popular packages as fallback.

        The GitHub code search API requires authentication, and other APIs
        are unreliable from Docker. This provides offline functionality.
        """
        try:
            # Load static data from JSON file in the same directory
            static_file = Path(__file__).parent / "static_data.json"
            if not static_file.exists():
                logger.warning(f"Static Winget dataset not found at {static_file}")
                return []

            import json
            with open(static_file, "r", encoding="utf-8") as f:
                popular_packages = json.load(f)

            query_lower = query.lower()
            results = []

            for pkg in popular_packages:
                name = pkg.get("Name", "").lower()
                pid = pkg.get("Id", "").lower()

                # Loose matching: check if query is in name or ID
                if query_lower in name or query_lower in pid:
                    results.append(pkg)

            logger.info(f"Static dataset returned {len(results)} results for '{query}'")
            return results

        except Exception as ex:
            logger.debug(f"Static fallback search failed: {ex}")
        return []

    def _search_via_powershell(self, query: str) -> List[Dict[str, str]]:
        """
        Perform a Winget package search via PowerShell and return normalized results.

        Parameters:
            query (str): Search query string used to find matching packages.

        Returns:
            List[Dict[str, str]]: A list of result dictionaries with keys 'Name', 'Id', 'Version', and 'Source'. Returns an empty list when no results are found or on error.
        """
        if self.is_wasm:
            return []

        try:
            # Note: On Linux/Docker, powershell might be missing.
            # Catch FileNotFoundError explicitly.
            try:
                # Ensure module is available (but don't fail if it's not - we have fallbacks)
                self._ensure_winget_module()
            except Exception as e:
                logger.debug(f"Winget module check failed: {e}")
                # Don't return yet, try running command anyway? No, command needs module.
                # Actually subprocess call handles it if command itself fails.

            # Use parameterized PowerShell to avoid command injection
            ps_script = """
            param($query)
            Import-Module Microsoft.WinGet.Client -ErrorAction SilentlyContinue
            Find-WinGetPackage -Query $query | Select-Object Name, Id, Version, Source | ConvertTo-Json -Depth 1
            """
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script, "-query", query]
            kwargs = self._get_subprocess_kwargs()
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=45, **kwargs)
            except FileNotFoundError:
                logger.debug("PowerShell binary not found (Linux/Docker?)")
                return []
            except OSError as e:
                logger.debug(f"PowerShell execution failed: {e}")
                return []

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
        Get detailed package information using PowerShell Get-WinGetPackage cmdlet (primary) or 'winget show' (fallback).
        This provides full manifest details including Description, License, Homepage, etc.
        """
        # Try PowerShell first (preferred method)
        try:
            details = self._get_package_details_via_powershell(package_id)
            if details:
                return details
        except Exception as e:
            logger.debug(f"PowerShell Get-WinGetPackage failed for {package_id}, falling back to CLI: {e}")

        # Fallback to CLI
        try:
            # Use 'winget show' which provides full manifest details
            # Add --disable-interactivity to prevent any interactive prompts
            cmd = ["winget", "show", "--id", package_id, "--source", "winget",
                   "--disable-interactivity"]
            kwargs = self._get_subprocess_kwargs()
            logger.debug(f"Getting package details via CLI for: {package_id}")
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=30,  # Add timeout
                **kwargs
            )

            if proc.returncode != 0:
                error_msg = proc.stderr.strip() if proc.stderr else proc.stdout.strip() or "Unknown error"
                logger.error(f"Winget show failed for package {package_id}: returncode={proc.returncode}, error={error_msg}")
                # Check for common error patterns
                if "No package found" in error_msg or "No installed package found" in error_msg:
                    logger.warning(f"Package {package_id} not found in winget")
                    raise Exception(f"Package not found: {package_id}")
                raise Exception(f"Failed to get package details: {error_msg}")

            output = proc.stdout.strip()
            if not output:
                logger.warning(f"Winget show returned empty output for package: {package_id}")
                return {}

            # Parse the key: value format from winget show output
            details = self._parse_winget_show_output(output)
            logger.debug(f"Successfully retrieved package details via CLI for {package_id}: {list(details.keys())}")
            return details

        except subprocess.TimeoutExpired:
            logger.error(f"Winget show timed out for package: {package_id}")
            raise Exception("Request timed out. The winget command took too long to respond.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Winget show failed for package {package_id}: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            raise Exception(f"Failed to get package details: {e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)}")
        except Exception as e:
            logger.error(f"Winget show error: {e}")
            raise Exception(f"Error getting package details: {str(e)}")

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
            # Improved regex to handle various winget output styles (bullet points, spaces, etc.)
            if ':' in line and not line.strip().startswith(('*', '-', '·')):
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
        """Install a package via PowerShell Install-WinGetPackage (primary) or Winget CLI (fallback)."""
        if scope not in ("machine", "user"):
            logger.error(f"Invalid scope: {scope}")
            return False

        # Try PowerShell first (preferred method)
        try:
            if self._install_via_powershell(package_id, scope):
                return True
        except Exception as e:
            logger.debug(f"PowerShell Install-WinGetPackage failed for {package_id}, falling back to CLI: {e}")

        # Fallback to CLI
        cmd = [
            "winget", "install",
            "--id", package_id,
            "--scope", scope,
            "--accept-package-agreements",
            "--accept-source-agreements"
        ]
        try:
            kwargs = self._get_subprocess_kwargs()
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, **kwargs)
            if proc.returncode != 0:
                logger.error(f"Winget install failed: {proc.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Winget install exception: {e}")
            return False

    def download_package(self, package_id: str, dest_dir: Path) -> Optional[Path]:
        """Download a package installer to dest_dir using PowerShell (primary) or Winget CLI (fallback). Returns path to installer if found."""
        # Try PowerShell first (preferred method) - verify package exists
        try:
            if not self._verify_package_exists_via_powershell(package_id):
                logger.warning(f"Package {package_id} not found via PowerShell")
                # Fall through to CLI fallback
        except Exception as e:
            logger.debug(f"PowerShell package verification failed for {package_id}, falling back to CLI: {e}")

        # Fallback to CLI
        cmd = ["winget", "download", "--id", package_id, "--dir", str(dest_dir), "--accept-source-agreements", "--accept-package-agreements"]
        try:
            kwargs = self._get_subprocess_kwargs()
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, **kwargs)
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


    def _parse_search_results(self, stdout: str) -> List[Dict[str, str]]:
        """Parse the standard output from winget search command."""
        try:
             # Skip any leading empty lines/garbage
             lines = [line for line in stdout.splitlines() if line.strip()]
             logger.debug(f"Winget CLI fallback lines: {len(lines)}")
             if len(lines) < 2:
                 logger.debug(f"Winget CLI output too short: {stdout[:100]}...")
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
             match_ver = re.search(r'\bVersion\b|\bVers\b', header, re.IGNORECASE) # Allow partial 'Vers'
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
            logger.debug(f"Winget CLI parsing failed: {e}")
            return []

    def _search_via_cli(self, query: str) -> List[Dict[str, str]]:
        """Fallback search using winget CLI with robust table parsing."""
        if self.is_wasm:
            return []

        try:
             cmd = ["winget", "search", query, "--accept-source-agreements"]
             kwargs = self._get_subprocess_kwargs()
             proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=60, **kwargs)
             if proc.returncode != 0:
                 return []

             return self._parse_search_results(proc.stdout)
        except subprocess.TimeoutExpired:
             logger.warning(f"Winget CLI search timed out for query '{query}'")
             return []
        except Exception as e:
             logger.debug(f"Winget CLI search failed: {e}")
             return []


    def _ensure_winget_module(self) -> bool:
        """
        Ensure Microsoft.WinGet.Client module is available.
        Returns True if module is available or successfully installed, False otherwise.

        If auto_install_winget is False, skips installation and returns False if module is not available,
        allowing CLI fallback to be used.
        """
        try:
            ps_script = """
            if (-not (Get-Module -ListAvailable -Name Microsoft.WinGet.Client)) {
                Write-Output "NOT_AVAILABLE"
            } else {
                Write-Output "AVAILABLE"
            }
            """
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script]
            kwargs = self._get_subprocess_kwargs()
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=60, **kwargs)

            if proc.returncode == 0 and "AVAILABLE" in proc.stdout:
                return True

            # Module not available - check if we should auto-install
            if not self.auto_install_winget:
                logger.debug("WinGet module not available and auto-install is disabled, using CLI fallback")
                return False

            # Attempt installation
            logger.info("Microsoft.WinGet.Client module not found, attempting automatic installation...")
            install_script = """
            try {
                Install-Module -Name Microsoft.WinGet.Client -Scope CurrentUser -Force -AllowClobber -ErrorAction Stop
                Write-Output "INSTALLED"
            } catch {
                Write-Output "FAILED: $_"
                exit 1
            }
            """
            install_cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", install_script]
            install_proc = subprocess.run(install_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=60, **kwargs)

            if install_proc.returncode == 0 and "INSTALLED" in install_proc.stdout:
                logger.info("Automatically installed Microsoft.WinGet.Client")
                return True

            logger.warning(f"WinGet module installation failed: {install_proc.stderr}")
            return False
        except Exception as e:
            logger.debug(f"WinGet module check exception: {e}")
            return False

    def _get_package_details_via_powershell(self, package_id: str) -> Dict[str, str]:
        """Get package details using PowerShell Get-WinGetPackage cmdlet."""
        try:
            # Ensure module is available
            if not self._ensure_winget_module():
                return {}

            # Use parameterized PowerShell to avoid command injection
            ps_script = """
            param($id)
            Import-Module Microsoft.WinGet.Client -ErrorAction SilentlyContinue
            $pkg = Get-WinGetPackage -Id $id -ErrorAction SilentlyContinue
            if ($pkg) {
                $pkg | Select-Object Name, Id, Version, Publisher, Description, Homepage, License, LicenseUrl, PrivacyUrl, Copyright, ReleaseNotes, Tags | ConvertTo-Json -Depth 2
            } else {
                Write-Output "NOT_FOUND"
            }
            """
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script, "-id", package_id]
            kwargs = self._get_subprocess_kwargs()
            logger.debug(f"Getting package details via PowerShell for: {package_id}")
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=30, **kwargs)

            if proc.returncode != 0:
                error_msg = proc.stderr.strip() if proc.stderr else "Unknown error"
                logger.warning(f"PowerShell Get-WinGetPackage failed for {package_id}: returncode={proc.returncode}, stderr={error_msg}")
                return {}

            output = proc.stdout.strip()
            if not output or output == "NOT_FOUND":
                logger.warning(f"PowerShell Get-WinGetPackage returned no data for {package_id}")
                return {}

            try:
                data = json.loads(output)
                # Convert PowerShell object to our format
                details = {
                    "Name": data.get("Name", ""),
                    "Id": data.get("Id", package_id),
                    "Version": str(data.get("Version", "")),
                    "Publisher": data.get("Publisher", ""),
                    "Description": data.get("Description", ""),
                    "Homepage": data.get("Homepage", ""),
                    "License": data.get("License", ""),
                    "LicenseUrl": data.get("LicenseUrl", ""),
                    "PrivacyUrl": data.get("PrivacyUrl", ""),
                    "Copyright": data.get("Copyright", ""),
                    "ReleaseNotes": data.get("ReleaseNotes", ""),
                    "Tags": ", ".join(data.get("Tags", [])) if isinstance(data.get("Tags"), list) else str(data.get("Tags", ""))
                }
                result = {k: v for k, v in details.items() if v}  # Remove empty values
                logger.debug(f"Successfully retrieved package details for {package_id}: {list(result.keys())}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse PowerShell JSON output for {package_id}: {e}, output={output[:200]}")
                return {}
        except subprocess.TimeoutExpired:
            logger.error(f"PowerShell Get-WinGetPackage timed out for {package_id}")
            return {}
        except Exception as e:
            logger.error(f"PowerShell Get-WinGetPackage error for {package_id}: {e}", exc_info=True)
            return {}

    def _install_via_powershell(self, package_id: str, scope: str) -> bool:
        """Install a package using PowerShell Install-WinGetPackage cmdlet."""
        try:
            # Ensure module is available
            if not self._ensure_winget_module():
                return False

            scope_param = "Machine" if scope == "machine" else "User"
            # Use parameterized PowerShell to avoid command injection
            ps_script = """
            param($id, $scope)
            Import-Module Microsoft.WinGet.Client -ErrorAction SilentlyContinue
            $result = Install-WinGetPackage -Id $id -Scope $scope -AcceptPackageAgreements -AcceptSourceAgreements -ErrorAction Stop
            if ($result -and $result.ExitCode -eq 0) {
                Write-Output "SUCCESS"
            } else {
                Write-Output "FAILED"
                exit 1
            }
            """
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script, "-id", package_id, "-scope", scope_param]
            kwargs = self._get_subprocess_kwargs()
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=300, **kwargs)
            return proc.returncode == 0 and "SUCCESS" in proc.stdout
        except Exception as e:
            logger.debug(f"PowerShell Install-WinGetPackage error: {e}")
            return False

    def _verify_package_exists_via_powershell(self, package_id: str) -> bool:
        """Verify that a package exists using PowerShell Get-WinGetPackage cmdlet.

        Returns True if the package exists, False otherwise. Raises an exception on error.
        """
        try:
            if not self._ensure_winget_module():
                return False

            # Use parameterized PowerShell to avoid command injection
            ps_script = """
            param($id)
            Import-Module Microsoft.WinGet.Client -ErrorAction SilentlyContinue
            $pkg = Get-WinGetPackage -Id $id -ErrorAction SilentlyContinue
            if ($pkg) {
                Write-Output "EXISTS"
            } else {
                Write-Output "NOT_FOUND"
                exit 1
            }
            """
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script, "-id", package_id]
            kwargs = self._get_subprocess_kwargs()
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=30, **kwargs)

            if proc.returncode == 0 and "EXISTS" in proc.stdout:
                return True
            return False
        except Exception as e:
            logger.debug(f"PowerShell package verification error: {e}")
            raise

    def _get_startup_info(self):
        """Create STARTUPINFO to hide console window on Windows."""
        if hasattr(subprocess, 'STARTUPINFO'):
            import sys
            if sys.platform == "win32":
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                si.wShowWindow = subprocess.SW_HIDE  # Explicitly hide the window
                return si
        return None


    def _get_subprocess_kwargs(self):
        """
        Get common subprocess kwargs for hiding console window on Windows.

        Returns a dictionary with startupinfo and creationflags (if on Windows).
        This consolidates the repeated pattern of setting up subprocess kwargs.
        """
        import sys
        kwargs = {}
        startupinfo = self._get_startup_info()
        if startupinfo:
            kwargs['startupinfo'] = startupinfo
        if sys.platform == "win32":
            # Use the constant if available (Python 3.7+), otherwise use the hex literal
            if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            else:
                kwargs['creationflags'] = 0x08000000  # CREATE_NO_WINDOW fallback
        return kwargs