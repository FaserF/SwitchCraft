import logging
from pathlib import Path
import pefile
from typing import Optional
from switchcraft.analyzers.base import BaseAnalyzer
from switchcraft.models import InstallerInfo

logger = logging.getLogger(__name__)

class ExeAnalyzer(BaseAnalyzer):
    def can_analyze(self, file_path: Path) -> bool:
        if not file_path.exists():
            return False
        if file_path.suffix.lower() == '.exe':
            return True
        return False

    def analyze(self, file_path: Path) -> InstallerInfo:
        info = InstallerInfo(file_path=str(file_path), installer_type="Unknown EXE")

        try:
            pe = pefile.PE(str(file_path))
        except pefile.PEFormatError:
            logger.warning(f"Not a valid PE file: {file_path}")
            return info

        # 1. NSIS Detection
        # NSIS often has a section named .ndata or check for "NullsoftInst" signature overlay
        if self._check_nsis(pe, file_path):
            info.installer_type = "NSIS"
            info.install_switches = ["/S"]
            info.uninstall_switches = ["/S"] # Standard NSIS uninstaller argument
            info.confidence = 0.9
            return info

        # 2. Inno Setup Detection
        if self._check_inno(pe, file_path):
            info.installer_type = "Inno Setup"
            info.install_switches = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
            info.uninstall_switches = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"] # Typically uninstaller takes same args
            info.confidence = 0.9
            return info

        # 3. InstallShield Detection
        if self._check_installshield(pe, file_path):
            info.installer_type = "InstallShield"
            info.install_switches = ["/s", "/v\"/qn\""]
            info.confidence = 0.8
            return info

        if self._check_7zip(file_path):
            info.installer_type = "7-Zip SFX"
            info.install_switches = ["/S"]
            info.uninstall_switches = ["/S"]
            info.confidence = 0.9
            return info

        # Fallback: Brute string search in valid sections or overlay
        # TODO: Implement string search

        pe.close()
        return info

    def _check_nsis(self, pe: pefile.PE, file_path: Path) -> bool:
        # Check section names
        for section in pe.sections:
            if b".ndata" in section.Name:
                return True

        # Check overlay for NullsoftInst pattern?
        # Easier: Read file content near header or specific offset if known.
        # A simple string check in the first 4KB often finds "NullsoftInst"
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4096)
                if b"NullsoftInst" in header:
                    return True
        except:
            pass
        return False

    def _check_inno(self, pe: pefile.PE, file_path: Path) -> bool:
        # Inno Setup usually has "Inno Setup" string in the binary, often in the manifesto or overlay.
        # Simplified check: Look for "Inno Setup" string in the first 1MB or overlay
        try:
            with open(file_path, 'rb') as f:
                 # Read start
                data = f.read(1024 * 1024)
                if b"Inno Setup" in data:
                    return True
                if b"Inno Setup" in data.replace(b'\x00', b''): # Sometimes wide chars
                    return True
        except:
            pass
        return False

    def _check_installshield(self, pe: pefile.PE, file_path: Path) -> bool:
        # Check "InstallShield" string
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)
                if b"InstallShield" in data:
                    return True
        except:
            pass
        return False

    def _scan_strings(self, file_path: Path) -> None:
        """Scan for common silent switch strings."""
        # Common switches to look for
        COMMON_SWITCHES = [b"/S", b"/silent", b"/quiet", b"-q", b"-silent", b"/VERYSILENT"]
        found_switches = []

        try:
            with open(file_path, 'rb') as f:
                # Read chunks to avoid memory issues with large installers
                chunk_size = 1024 * 1024 * 5 # 5MB scan
                data = f.read(chunk_size)

                for switch in COMMON_SWITCHES:
                    if switch in data or switch.upper() in data:
                        found_switches.append(switch.decode('utf-8'))
        except:
            pass

        return found_switches

    def get_brute_force_help_command(self, file_path: Path) -> str:
        """Return a command to try and elicit help output."""
        return f'"{file_path}" /?'

    def _check_7zip(self, file_path: Path) -> bool:
        """Check for 7-Zip SFX signature."""
        try:
            with open(file_path, 'rb') as f:
                # 7z SFX usually starts with MZ but has '7z¼¯'' signature inside or at beginning of overlay
                header = f.read(1024 * 200) # Check first 200KB
                if b"7z\xBC\xAF\x27\x1C" in header:
                    return True
        except:
            pass
        return False
