import logging
import zipfile
import subprocess
import tempfile
import shutil
import plistlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Dict, Any

from switchcraft.analyzers.base import BaseAnalyzer
from switchcraft.models import InstallerInfo

logger = logging.getLogger(__name__)

class MacOSAnalyzer(BaseAnalyzer):
    def can_analyze(self, file_path: Path) -> bool:
        if not file_path.exists():
            return False

        suffix = file_path.suffix.lower()
        if suffix in ['.pkg', '.dmg', '.app', '.ipa']:
            return True

        # Check if it's a zip that might contain an app (simple check)
        if zipfile.is_zipfile(file_path):
            try:
                with zipfile.ZipFile(file_path, 'r') as z:
                    for name in z.namelist():
                        if name.endswith('.app/') or name.endswith('Info.plist'):
                            return True
            except:
                pass

        return False

    def analyze(self, file_path: Path) -> InstallerInfo:
        info = InstallerInfo(file_path=str(file_path), installer_type="MacOS Package")
        info.confidence = 0.0

        suffix = file_path.suffix.lower()

        try:
            if suffix == '.pkg':
                self._analyze_pkg(file_path, info)
            elif suffix == '.dmg':
                self._analyze_dmg(file_path, info)
            elif suffix == '.app':
                # Treat as directory or handled via zip/dmg logic usually,
                # but if user dragged a .app folder directly (rare on Windows but possible)
                if file_path.is_dir():
                    self._analyze_app_dir(file_path, info)
            elif suffix == '.ipa' or zipfile.is_zipfile(file_path):
                self._analyze_zip(file_path, info)

        except Exception as e:
            logger.error(f"Error analysing MacOS file {file_path}: {e}")
            info.properties['error'] = str(e)

        return info

    def _analyze_pkg(self, file_path: Path, info: InstallerInfo):
        """Analyze .pkg (xar archive)"""
        info.installer_type = "MacOS PKG"
        # We need 7z to extract Distribution or PackageInfo
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 1. Try to extract Distribution file (xml)
            # 7z x archive.pkg Distribution -oOutDir
            if self._extract_with_7z(file_path, temp_path, ["Distribution", "PackageInfo", "*.plist"]):

                # Check Distribution
                dist_file = temp_path / "Distribution"
                if dist_file.exists():
                    self._parse_distribution_xml(dist_file, info)

                # Check PackageInfo
                pkg_info_file = temp_path / "PackageInfo"
                if pkg_info_file.exists():
                    self._parse_package_info_xml(pkg_info_file, info)

        if info.bundle_id:
            info.confidence = 1.0

    def _analyze_dmg(self, file_path: Path, info: InstallerInfo):
        """Analyze .dmg (HFS+ image usually)"""
        info.installer_type = "MacOS DMG"
        # 7z can open DMG
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # We want to find .app folders inside the DMG
            # Listing first might be faster than extracting everything
            # But 7z listing is easy.

            # We try to extract Info.plist from any .app found inside
            # Pattern: *.app/Contents/Info.plist
            # 7z x file.dmg -oOutDir -r *.app/Contents/Info.plist

            if self._extract_with_7z(file_path, temp_path, ["*Info.plist"], recursive=True):
                # Find all Info.plist files
                plists = list(temp_path.rglob("Info.plist"))
                for plist in plists:
                    data = self._parse_plist(plist)
                    if data:
                        # Heuristic: the one with CFBundlePackageType APPL is likely the main app
                        if data.get('CFBundlePackageType') == 'APPL':
                            self._populate_from_plist(data, info)
                            info.confidence = 1.0
                            break # Found main app

                        # Fallback
                        if not info.bundle_id:
                             self._populate_from_plist(data, info)

    def _analyze_zip(self, file_path: Path, info: InstallerInfo):
         """Analyze zip containing .app or .ipa"""
         info.installer_type = "MacOS App Archive"
         with zipfile.ZipFile(file_path, 'r') as z:
            # Look for Info.plist
            possible_plists = [n for n in z.namelist() if n.endswith('Info.plist')]
            for pp in possible_plists:
                 with z.open(pp) as f:
                     try:
                         data = plistlib.load(f)
                         if data.get('CFBundlePackageType') == 'APPL' or file_path.suffix == '.ipa':
                             self._populate_from_plist(data, info)
                             info.confidence = 1.0
                             if info.bundle_id:
                                 break
                     except:
                         continue

    def _analyze_app_dir(self, file_path: Path, info: InstallerInfo):
        """Analyze .app directory"""
        info.installer_type = "MacOS App Bundle"
        plist_path = file_path / "Contents" / "Info.plist"
        if plist_path.exists():
            data = self._parse_plist(plist_path)
            if data:
                self._populate_from_plist(data, info)
                info.confidence = 1.0

    def _extract_with_7z(self, archive: Path, out_dir: Path, files: List[str], recursive=False) -> bool:
        """Run 7z to extract specific files."""
        # Assume 7z in path or typical location
        seven_z = self._find_7z()
        if not seven_z:
            logger.warning("7z not found. Cannot analyze MacOS archive.")
            return False

        args = [seven_z, "x", str(archive), f"-o{out_dir}", "-y"]
        if recursive:
            args.append("-r")

        args.extend(files)

        try:
            # Suppress output
            subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            return False

    def _find_7z(self) -> Optional[str]:
        # Check PATH
        path = shutil.which("7z")
        if path: return path

        # Check common Windows paths
        common_paths = [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe"
        ]
        for p in common_paths:
            if Path(p).exists():
                return p
        return None

    def _parse_plist(self, path: Path) -> Dict:
        try:
            with open(path, 'rb') as f:
                return plistlib.load(f)
        except Exception as e:
            logger.debug(f"Failed to parse plist {path}: {e}")
            return {}

    def _populate_from_plist(self, data: Dict, info: InstallerInfo):
        info.bundle_id = data.get('CFBundleIdentifier')
        info.product_version = data.get('CFBundleShortVersionString') or data.get('CFBundleVersion')
        info.product_name = data.get('CFBundleName') or data.get('CFBundleDisplayName')
        info.min_os_version = data.get('LSMinimumSystemVersion')

    def _parse_distribution_xml(self, path: Path, info: InstallerInfo):
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            # <pkg-ref id="com.example.pkg" ...>
            for pkg_ref in root.findall(".//pkg-ref"):
                pid = pkg_ref.get("id")
                if pid:
                    info.package_ids.append(pid)
                    if not info.bundle_id:
                        info.bundle_id = pid # Use first one as main?

            # <title>AppName</title>
            title = root.find(".//title")
            if title is not None:
                info.product_name = title.text

        except Exception as e:
            logger.debug(f"Failed to parse Distribution xml: {e}")

    def _parse_package_info_xml(self, path: Path, info: InstallerInfo):
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            # <pkg-info identifier="com.example.pkg" version="1.0" ...>
            if root.tag == 'pkg-info':
                pid = root.get('identifier')
                ver = root.get('version')
                if pid and not info.bundle_id:
                    info.bundle_id = pid
                if pid:
                    if pid not in info.package_ids:
                        info.package_ids.append(pid)
                if ver and not info.product_version:
                    info.product_version = ver
        except Exception as e:
            logger.debug(f"Failed to parse PackageInfo xml: {e}")
