import logging
import json
import yaml
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

WINGET_PKGS_PATH = Path("c:/Users/fseitz/GitHub/winget-pkgs/manifests") # Local optimization
GITHUB_WINGET_URL = "https://github.com/microsoft/winget-pkgs/tree/master/manifests"

class WingetHelper:
    def __init__(self):
        self.local_repo = WINGET_PKGS_PATH if WINGET_PKGS_PATH.exists() else None

    def search_by_product_code(self, product_code: str) -> Optional[str]:
        """Search local winget repo for a product code."""
        if not self.local_repo or not product_code:
            return None

        product_code = product_code.strip("{}").upper() # Normalize MSI product code

        # This is a naive scan. A real index would be better, but this is MVP.
        # We can use 'grep' or 'findstr' via generic search if we want speed,
        # but purely pythonic recursive glob might be slow on 400k files.
        # So we might skip deep scan for now or limit it.
        # Using 'fd' or 'ripgrep' if available would be best.
        return None

    def search_by_name(self, product_name: str) -> Optional[str]:
        """Search for a product name using local repo or CLI."""
        if not product_name:
            return None

        # Special Case for SwitchCraft (Self-detection)
        if "switchcraft" in product_name.lower():
            return "https://github.com/microsoft/winget-pkgs/tree/master/manifests/s/FaserF/SwitchCraft"

        # 1. Try Local Repo (if valid)
        if self.local_repo:
            url = self._search_local_repo(product_name)
            if url: return url

        # 2. Try CLI Search (Robust Fallback)
        return self._search_cli(product_name)

    def _search_local_repo(self, product_name: str) -> Optional[str]:
        import difflib
        search_term = product_name.lower().replace(" ", "")
        first_char = search_term[0] if search_term[0].isalnum() else "_"
        search_root = self.local_repo / first_char.lower()

        if not search_root.exists(): return None

        found_matches = []
        for vendor_dir in search_root.iterdir():
            if vendor_dir.is_dir():
                # Vendor match
                if search_term in vendor_dir.name.lower():
                    for pkg_dir in vendor_dir.iterdir(): found_matches.append(pkg_dir)
                else:
                    # Package match
                    for pkg_dir in vendor_dir.iterdir():
                         if search_term in pkg_dir.name.lower(): found_matches.append(pkg_dir)

        if found_matches:
            best_match = max(found_matches, key=lambda p: difflib.SequenceMatcher(None, product_name.lower(), p.name.lower()).ratio())
            return self._construct_github_url(best_match)
        return None

    def _search_cli(self, query: str) -> Optional[str]:
        """Run winget search and parse ID."""
        import subprocess
        import shutil

        if not shutil.which("winget"):
            return None

        try:
            # Clean query
            clean_query = "".join(x for x in query if x.isalnum() or x in " -_.")

            # winget search --name "Node.js" --source winget
            cmd = ["winget", "search", "--name", clean_query, "--source", "winget", "--accept-source-agreements"]

            # Run without window (Windows specific)
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                startupinfo=startupinfo
            )

            if proc.returncode != 0:
                logger.warning(f"Winget CLI failed code {proc.returncode}")
                return None

            # Parse Header: Name Id Version Match Source
            lines = proc.stdout.strip().splitlines()
            if len(lines) < 3: return None

            # Skip Header and Separator (usually lines 0 and 1)
            # Find the header line index just in case
            header_idx = -1
            for i, line in enumerate(lines):
                if "Id" in line and "Version" in line:
                    header_idx = i
                    break

            if header_idx == -1 or header_idx + 2 >= len(lines):
                return None

            # Analyzing offsets is tricky due to variable spacing.
            # But columns are spaced. Usually Name (variable) Id (variable) ...
            # Let's take the first result line roughly.
            first_row = lines[header_idx + 2]

            # Robust split? It's column based.
            # Usually the ID is the second "token" if the Name doesn't contain spaces? No, Name has spaces.
            # Column-based parsing required.

            header = lines[header_idx]
            id_start = header.find("Id")
            version_start = header.find("Version")

            if id_start == -1 or version_start == -1: return None

            app_id = first_row[id_start:version_start].strip()

            if app_id:
                # Construct winget.run URL (Unofficial but contains the ID for our parser)
                # Format: https://winget.run/pkg/<Publisher>/<Package>
                # But our parser uses split("/pkg/")[-1].replace("/", ".")
                # So if ID is "OpenJS.NodeJS", we want "OpenJS/NodeJS"

                parts = app_id.split(".")
                if len(parts) >= 2:
                    return f"https://winget.run/pkg/{parts[0]}/{'.'.join(parts[1:])}"
                return f"https://winget.run/pkg/{app_id}"

        except Exception as e:
            logger.error(f"Winget CLI search error: {e}")
            return None

        return None

    def search_packages(self, query: str) -> List[Dict[str, str]]:
        """
        Search for packages using Winget CLI and return structured data.
        Returns list of {Id, Name, Version, Source}
        """
        import subprocess
        import shutil

        if not shutil.which("winget"):
            return []

        try:
            # winget search <query> --source winget --accept-source-agreements
            # Note: without --exact it searches fuzzy
            cmd = ["winget", "search", query, "--source", "winget", "--accept-source-agreements"]

            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo)

            if proc.returncode != 0 and proc.returncode != 1: # 0=Success, 1=No results
                return []

            lines = proc.stdout.strip().splitlines()
            results = []

            # Header parsing logic
            # Name      Id          Version   Match Source
            # ---------------------------------------------
            if len(lines) < 3: return []

            header = lines[0]
            # If header doesn't contain "Id", search subsequent lines
            id_idx = header.find("Id")
            if id_idx == -1:
                # Try to find header line
                for i, l in enumerate(lines):
                    if "Id" in l and "Version" in l:
                        header = l
                        id_idx = header.find("Id")
                        ver_idx = header.find("Version")
                        lines = lines[i:] # Adjust start
                        break

            if id_idx == -1: return []

            ver_idx = header.find("Version")
            match_idx = header.find("Match")
            src_idx = header.find("Source")

            # Parse lines (skip header and dashes)
            for line in lines[2:]:
                if not line.strip(): continue

                # Fixed width parsing based on header offsets
                # Name is from 0 to id_idx
                # Id is from id_idx to ver_idx
                # Version is from ver_idx ...

                # Careful: The last column might not have a start index if header ended

                name = line[:id_idx].strip()
                p_id = line[id_idx:ver_idx].strip()

                # Version usually ends at Match or Source
                end_ver = match_idx if match_idx != -1 else src_idx
                if end_ver == -1: end_ver = len(line)

                version = line[ver_idx:end_ver].strip()

                if name and p_id:
                    results.append({"Name": name, "Id": p_id, "Version": version})

            return results

        except Exception as e:
            logger.error(f"Winget Search Error: {e}")
            return []

    def get_package_details(self, package_id: str) -> Dict[str, str]:
        """Run winget show to get details."""
        import subprocess
        data = {}
        try:
            cmd = ["winget", "show", "--id", package_id, "--source", "winget", "--accept-source-agreements", "--disable-interactivity"]
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo)

            key_map = {
                "Publisher": "publisher",
                "Author": "author",
                "Description": "description",
                "Homepage": "homepage",
                "License": "license",
                "License Url": "license_url",
                "Installer Url": "installer_url",
                "Installer Type": "installer_type",
                "SHA256": "sha256"
            }

            current_key = None
            for line in proc.stdout.splitlines():
                if ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip()
                    val = parts[1].strip()

                    if key in key_map:
                        data[key_map[key]] = val
                        current_key = key_map[key]
                    elif key == "Installer": # Section header sometimes?
                        pass
                elif current_key and line.startswith(" "):
                    # Continuation
                    data[current_key] += " " + line.strip()

            return data
        except Exception as e:
            logger.error(f"Winget Show Error: {e}")
            return {}

    def _construct_github_url(self, path: Path) -> str:
        # Convert local path to GitHub URL
        try:
            rel_path = path.relative_to(self.local_repo)
            return f"{GITHUB_WINGET_URL}/{rel_path.as_posix()}"
        except:
            return ""
