import logging
import json
import yaml
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# WINGET_PKGS_PATH removed (deprecated)
GITHUB_WINGET_URL = "https://github.com/microsoft/winget-pkgs/tree/master/manifests"

class WingetHelper:
    def __init__(self):
        self.local_repo = None # Local repo support removed

    def search_by_product_code(self, product_code: str) -> Optional[str]:
        return None

    def search_by_name(self, product_name: str) -> Optional[str]:
        """Search for a product name using CLI."""
        if not product_name:
            return None

        # Self-check
        if "switchcraft" in product_name.lower():
            return "https://github.com/microsoft/winget-pkgs/tree/master/manifests/s/FaserF/SwitchCraft"

        return self._search_cli(product_name)

    def _search_local_repo(self, product_name: str) -> Optional[str]:
        return None

    def _search_cli(self, query: str) -> Optional[str]:
        """Run winget search and parse ID."""
        if not query: return None
        import subprocess
        import shutil

        if not shutil.which("winget"):
            return None

        try:
            # Clean query
            clean_query = "".join(x for x in query if x.isalnum() or x in " -_.")

            # winget search --name <query> --source winget
            cmd = ["winget", "search", "--name", clean_query, "--source", "winget", "--accept-source-agreements", "--disable-interactivity"]

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
                # Code 1 usually means no results, but we should verify stdout
                pass

            # Parse Header: Name Id Version Match Source
            lines = proc.stdout.strip().splitlines()
            if len(lines) < 3: return None

            header_idx = -1
            for i, line in enumerate(lines):
                if "Id" in line and "Version" in line:
                    header_idx = i
                    break

            if header_idx == -1 or header_idx + 2 >= len(lines):
                return None

            first_row = lines[header_idx + 2]
            header = lines[header_idx]
            id_start = header.find("Id")
            version_start = header.find("Version")

            if id_start == -1 or version_start == -1: return None

            app_id = first_row[id_start:version_start].strip()

            if app_id:
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
            logger.warning("Winget CLI not found in PATH")
            return []

        try:
            # --exact match is too strict for general search
            cmd = ["winget", "search", query, "--source", "winget", "--accept-source-agreements", "--disable-interactivity"]

            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", startupinfo=startupinfo)

            # If nothing found, winget often returns 1 and prints "No package found..."
            if "No package found" in proc.stdout:
                return []

            if proc.returncode != 0 and proc.returncode != 1: # 0=Success, 1=No results
                logger.error(f"Winget CLI error {proc.returncode}: {proc.stderr or proc.stdout}")
                msg = f"Winget Error {proc.returncode}: {proc.stdout}"
                raise RuntimeError(msg)

            lines = proc.stdout.strip().splitlines()
            results = []

            # Header parsing logic
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

                # Stop if we hit footer or progress
                if line.startswith("---") or "package found" in line: continue

                name = line[:id_idx].strip()
                p_id = line[id_idx:ver_idx].strip()

                end_ver = match_idx if match_idx != -1 else src_idx
                if end_ver == -1: end_ver = len(line)

                version = line[ver_idx:end_ver].strip()

                if name and p_id:
                    results.append({"Name": name, "Id": p_id, "Version": version})

            return results

        except RuntimeError as e:
            raise e
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
