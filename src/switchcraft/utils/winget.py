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
        """Search local winget repo for a product name using fuzzy matching."""
        if not self.local_repo or not product_name:
            return None

        # Special Case for SwitchCraft (Self-detection)
        if "switchcraft" in product_name.lower():
            return "https://github.com/microsoft/winget-pkgs/tree/master/manifests/s/FaserF/SwitchCraft"

        import difflib

        # Strategy:
        # 1. Direct search (fast)
        # 2. Fuzzy search on relevant subdirectories (slower)

        # Normalize
        search_term = product_name.lower().replace(" ", "")

        # 1. Try first letter optimization first (Standard Winget structure)
        first_char = search_term[0] if search_term[0].isalnum() else "_"
        search_root = self.local_repo / first_char.lower()

        found_matches = []

        if search_root.exists():
            # Quick scan in the first-letter directory
            for vendor_dir in search_root.iterdir():
                if vendor_dir.is_dir():
                    # Check vendor name
                    if search_term in vendor_dir.name.lower():
                        # Vendor match? Look inside for package
                        for pkg_dir in vendor_dir.iterdir():
                            found_matches.append(pkg_dir)
                    else:
                        # Check inside vendor dir for package name match
                        for pkg_dir in vendor_dir.iterdir():
                             if search_term in pkg_dir.name.lower():
                                 found_matches.append(pkg_dir)

        if found_matches:
            # Sort by similarity to original product code
            # We use the pkg_dir name vs product_name
            best_match = max(found_matches, key=lambda p: difflib.SequenceMatcher(None, product_name.lower(), p.name.lower()).ratio())
            return self._construct_github_url(best_match)

        # 2. Broader Fuzzy Search (if quick scan failed)
        # We can't scan EVERYTHING, but we can try to guess the Publisher
        # For now, let's look at the first-char directory again but use difflib on ALL vendor names there
        if search_root.exists():
            vendors = [d.name for d in search_root.iterdir() if d.is_dir()]
            # Find close matches to product_name in vendors (maybe the vendor IS the product name, like "7zip")
            close_vendors = difflib.get_close_matches(product_name, vendors, n=3, cutoff=0.6)

            for vendor_name in close_vendors:
                vendor_dir = search_root / vendor_name
                # Return the first package inside? Or look for close match inside?
                # Usually there's one or few packages.
                for pkg_dir in vendor_dir.iterdir():
                     return self._construct_github_url(pkg_dir)

        # If still nothing, maybe the Manufacturer is completely different.
        # This becomes an O(N) scan which is too slow for 400k files without an index.
        # We stop here for the "dynamic/probability" requirement.

        return None

    def _construct_github_url(self, path: Path) -> str:
        # Convert local path to GitHub URL
        rel_path = path.relative_to(WINGET_PKGS_PATH)
        # Replacing backslashes for URL
        return f"{GITHUB_WINGET_URL}/{rel_path.as_posix()}"
