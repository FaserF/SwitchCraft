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
        """Search local winget repo for a product name (folder match)."""
        if not self.local_repo or not product_name:
            return None

        # Simple heuristic: try to find a folder matching the first letter
        first_char = product_name[0].lower()
        if not first_char.isalnum():
            first_char = "_"

        search_root = self.local_repo / first_char.lower()
        if not search_root.exists():
            return None

        # Try to find loose match
        for vendor_dir in search_root.iterdir():
            # Check vendor name match or inside
            if product_name.lower() in vendor_dir.name.lower():
                 return self._construct_github_url(vendor_dir)

            if vendor_dir.is_dir():
                for pkg_dir in vendor_dir.iterdir():
                    if product_name.lower() in pkg_dir.name.lower():
                        return self._construct_github_url(pkg_dir)
        return None

    def _construct_github_url(self, path: Path) -> str:
        # Convert local path to GitHub URL
        rel_path = path.relative_to(WINGET_PKGS_PATH)
        # Replacing backslashes for URL
        return f"{GITHUB_WINGET_URL}/{rel_path.as_posix()}"
