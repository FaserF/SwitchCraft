import logging
from pathlib import Path
import pefile
from typing import List
from switchcraft.analyzers.base import BaseAnalyzer
from switchcraft.models import InstallerInfo

logger = logging.getLogger(__name__)

class ExeAnalyzer(BaseAnalyzer):
    """Enhanced EXE analyzer with detection for many installer frameworks."""

    # Common silent install switches to scan for in binaries
    COMMON_SWITCHES = [
        b"/S", b"/s", b"/silent", b"/SILENT", b"/quiet", b"/QUIET",
        b"-q", b"-silent", b"/VERYSILENT", b"/SUPPRESSMSGBOXES",
        b"--silent", b"--quiet", b"/qn", b"/passive", b"/norestart"
    ]

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

        # Extract PE metadata first (always useful)
        self._extract_pe_metadata(pe, info)

        # 1. NSIS Detection
        if self._check_nsis(pe, file_path):
            info.installer_type = "NSIS"
            info.install_switches = ["/S"]
            info.uninstall_switches = ["/S"]
            info.confidence = 0.9
            pe.close()
            return info

        # 2. Inno Setup Detection
        if self._check_inno(pe, file_path):
            info.installer_type = "Inno Setup"
            info.install_switches = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/ALLUSERS", '/LOG="install.log"', '/DIR="C:\\InstallPath"']
            info.uninstall_switches = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", '/LOG="uninstall.log"']
            info.confidence = 0.9
            pe.close()
            return info

        # 3. InstallShield Detection
        if self._check_installshield(pe, file_path):
            info.installer_type = "InstallShield"
            info.install_switches = ["/s", "/v\"/qn\""]
            info.confidence = 0.8
            pe.close()
            return info

        # 4. 7-Zip SFX Detection
        if self._check_7zip(file_path):
            info.installer_type = "7-Zip SFX"
            info.install_switches = ["/S"]
            info.uninstall_switches = ["/S"]
            info.confidence = 0.9
            pe.close()
            return info

        # 5. PyInstaller Detection (Python-based EXE)
        if self._check_pyinstaller(pe, file_path):
            info.installer_type = "Portable App (PyInstaller)"
            info.install_switches = []
            info.confidence = 0.9
            pe.close()
            return info

        # PortableApps.com Format
        if self._check_portableapps(pe, file_path):
            info.installer_type = "PortableApps.com Formatter"
            info.install_switches = []
            info.confidence = 0.95
            pe.close()
            return info

        # Generic Portable Wrapper Detection
        if self._check_generic_portable(file_path):
            info.installer_type = "Portable Application (Generic)"
            info.install_switches = []
            info.confidence = 0.6
            pe.close()
            return info

        # 6. cx_Freeze Detection
        if self._check_cx_freeze(file_path):
            info.installer_type = "Portable App (cx_Freeze)"
            info.install_switches = []
            info.confidence = 0.8
            pe.close()
            return info

        # 7. WiX Burn Bundle Detection
        if self._check_wix_burn(file_path):
            info.installer_type = "WiX Burn Bundle"
            info.install_switches = ["/quiet", "/norestart"]
            info.uninstall_switches = ["/uninstall", "/quiet", "/norestart"]
            info.confidence = 0.85
            pe.close()
            return info

        # 8. Advanced Installer Detection
        if self._check_advanced_installer(file_path):
            info.installer_type = "Advanced Installer"
            info.install_switches = ["/exenoui", "/qn"]
            info.confidence = 0.8
            pe.close()
            return info

        # 9. Wise Installer Detection
        if self._check_wise(file_path):
            info.installer_type = "Wise Installer"
            info.install_switches = ["/S"]
            info.confidence = 0.8
            pe.close()
            return info

        # 10. Setup Factory Detection
        if self._check_setup_factory(file_path):
            info.installer_type = "Setup Factory"
            info.install_switches = ["/S"]
            info.confidence = 0.75
            pe.close()
            return info

        # 11. Squirrel Detection (Electron apps)
        if self._check_squirrel(file_path):
            info.installer_type = "Squirrel (Electron)"
            info.install_switches = ["--silent"]
            info.confidence = 0.8
            pe.close()
            return info

        # 12. HP Installer Detection
        if self._check_hp_installer(file_path):
            info.installer_type = "HP SoftPaq / HP Installer"
            info.install_switches = ["-s", "-e", "<extract_path>"]
            info.uninstall_switches = ["-s", "-u"]
            info.confidence = 0.85
            pe.close()
            return info

        # 13. Dell Installer Detection
        if self._check_dell_installer(file_path):
            info.installer_type = "Dell Update Package"
            info.install_switches = ["/s", "/l=<logfile>"]
            info.uninstall_switches = ["/s", "/u"]
            info.confidence = 0.85
            pe.close()
            return info

        # 14. SAP Installer Detection
        if self._check_sap_installer(file_path):
            info.installer_type = "SAP Installer"
            info.install_switches = ["/Silent"]
            info.confidence = 0.8
            pe.close()
            return info

        # 15. Lenovo System Update Detection
        if self._check_lenovo_installer(file_path):
            info.installer_type = "Lenovo System Update"
            info.install_switches = ["/SILENT", "/VERYSILENT", "/NOREBOOT"]
            info.confidence = 0.8
            pe.close()
            return info

        # 16. Intel Installer Detection
        if self._check_intel_installer(file_path):
            info.installer_type = "Intel Installer Framework"
            info.install_switches = ["-s", "-a", "-s2", "-norestart"]
            info.confidence = 0.8
            pe.close()
            return info

        # 17. NVIDIA Installer Detection
        if self._check_nvidia_installer(file_path):
            info.installer_type = "NVIDIA Installer"
            info.install_switches = ["-s", "-noreboot", "-clean"]
            info.confidence = 0.8
            pe.close()
            return info

        # 18. AMD/ATI Installer Detection
        if self._check_amd_installer(file_path):
            info.installer_type = "AMD/ATI Installer"
            info.install_switches = ["/S"]
            info.confidence = 0.75
            pe.close()
            return info

        # 19. Microsoft Visual C++ Redistributable
        if self._check_vcredist(file_path):
            info.installer_type = "Visual C++ Redistributable"
            info.install_switches = ["/quiet", "/norestart"]
            info.confidence = 0.9
            pe.close()
            return info

        # 20. Java Installer Detection
        if self._check_java_installer(file_path):
            info.installer_type = "Java/Oracle Installer"
            info.install_switches = ["/s", "INSTALL_SILENT=1", "STATIC=0"]
            info.confidence = 0.8
            pe.close()
            return info

        # Fallback: Scan for common switch strings in the binary
        found_switches = self._scan_strings(file_path)
        if found_switches:
            info.installer_type = "Unknown EXE (Switches Found)"
            info.install_switches = found_switches
            info.confidence = 0.5

        # Finally, check if it might be a portable app that just doesn't support switches
        # Only if nothing else found
        if "Unknown" in info.installer_type and not info.install_switches:
             if self._check_generic_portable(file_path, loose=True):
                 info.installer_type = "Likely Portable Application"
                 info.confidence = 0.4

        pe.close()
        return info

    def _extract_pe_metadata(self, pe: pefile.PE, info: InstallerInfo) -> None:
        """Extract version info from PE file."""
        try:
            if hasattr(pe, 'FileInfo') and pe.FileInfo:
                for file_info in pe.FileInfo:
                    for entry in file_info:
                        if hasattr(entry, 'StringTable'):
                            for st in entry.StringTable:
                                for key, value in st.entries.items():
                                    key_str = key.decode('utf-8', errors='ignore')
                                    val_str = value.decode('utf-8', errors='ignore')

                                    if key_str == 'ProductName':
                                        info.product_name = val_str
                                    elif key_str == 'ProductVersion':
                                        info.product_version = val_str
                                    elif key_str == 'CompanyName':
                                        info.manufacturer = val_str
                                    elif key_str == 'FileDescription':
                                        if not info.product_name:
                                            info.product_name = val_str
        except Exception as e:
            logger.debug(f"Failed to extract PE metadata: {e}")

    def _check_nsis(self, pe: pefile.PE, file_path: Path) -> bool:
        """Check for NSIS installer signature."""
        # Check section names
        for section in pe.sections:
            if b".ndata" in section.Name:
                return True

        # Check for NullsoftInst pattern in header
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4096)
                if b"NullsoftInst" in header:
                    return True
        except Exception:
            pass
        return False

    def _check_inno(self, pe: pefile.PE, file_path: Path) -> bool:
        """Check for Inno Setup signature."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)
                if b"Inno Setup" in data:
                    return True
                # Check for wide char version
                if b"I\x00n\x00n\x00o\x00 \x00S\x00e\x00t\x00u\x00p" in data:
                    return True
        except Exception:
            pass
        return False

    def _check_installshield(self, pe: pefile.PE, file_path: Path) -> bool:
        """Check for InstallShield signature."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)
                if b"InstallShield" in data:
                    return True
        except Exception:
            pass
        return False

    def _check_7zip(self, file_path: Path) -> bool:
        """Check for 7-Zip SFX signature."""
        try:
            with open(file_path, 'rb') as f:
                # Check first 200KB for 7z signature
                header = f.read(1024 * 200)
                if b"7z\xBC\xAF\x27\x1C" in header:
                    return True

                # For large SFX files, check for 7-Zip SFX markers in PE metadata/strings
                # These are present even when the archive starts later in the file
                markers_7z_sfx = [
                    b"7-Zip SFX",
                    b"7z SFX",
                    b"Oleg N. Scherbakov",  # Author of popular 7z SFX module
                    b"7zS.sfx",
                    b"7zSD.sfx",
                ]
                for marker in markers_7z_sfx:
                    if marker in header:
                        return True
        except Exception:
            pass
        return False


    def _check_pyinstaller(self, pe: pefile.PE, file_path: Path) -> bool:
        """Check for PyInstaller packaged executable."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024 * 2)  # Read 2MB

                # PyInstaller markers
                markers = [
                    b"_MEIPASS",
                    b"PyInstaller",
                    b"pyi_",
                    b"_pyi_main",
                    b"PYTHONPATH",
                ]

                for marker in markers:
                    if marker in data:
                        return True

                # Check for PyInstaller's bootloader section
                for section in pe.sections:
                    if b"_MEIPASS" in section.Name or b"PYI" in section.Name:
                        return True
        except Exception:
            pass
        return False

    def _check_cx_freeze(self, file_path: Path) -> bool:
        """Check for cx_Freeze packaged executable."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)
                if b"cx_Freeze" in data or b"cx-freeze" in data:
                    return True
        except Exception:
            pass
        return False

    def _check_wix_burn(self, file_path: Path) -> bool:
        """Check for WiX Burn bundle."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 512)  # Read 512KB

                markers = [
                    b".wixburn",
                    b"WixBurn",
                    b"burn.manifest",
                    b"BootstrapperApplication",
                    b"WixBundleManifest",
                ]

                for marker in markers:
                    if marker in data:
                        return True
        except Exception:
            pass
        return False

    def _check_advanced_installer(self, file_path: Path) -> bool:
        """Check for Advanced Installer signature."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)
                markers = [
                    b"Advanced Installer",
                    b"Caphyon",
                    b"advancedinstaller",
                ]
                for marker in markers:
                    if marker in data:
                        return True
        except Exception:
            pass
        return False

    def _check_wise(self, file_path: Path) -> bool:
        """Check for Wise Installer signature."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 512)
                markers = [
                    b"Wise Installation",
                    b"WiseMain",
                    b"WISESCRIPT",
                ]
                for marker in markers:
                    if marker in data:
                        return True
        except Exception:
            pass
        return False

    def _check_setup_factory(self, file_path: Path) -> bool:
        """Check for Setup Factory signature."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 512)
                if b"Setup Factory" in data or b"Indigo Rose" in data:
                    return True
        except Exception:
            pass
        return False

    def _check_squirrel(self, file_path: Path) -> bool:
        """Check for Squirrel installer (Electron apps)."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 512)
                markers = [
                    b"Squirrel",
                    b"squirrel.exe",
                    b"--squirrel",
                    b"Update.exe",
                ]
                for marker in markers:
                    if marker in data:
                        return True
        except Exception:
            pass
        return False

    def _scan_strings(self, file_path: Path) -> List[str]:
        """Scan for common silent switch strings in the binary."""
        found_switches = []

        try:
            with open(file_path, 'rb') as f:
                chunk_size = 1024 * 1024 * 5  # 5MB scan
                data = f.read(chunk_size)

                for switch in self.COMMON_SWITCHES:
                    if switch in data:
                        decoded = switch.decode('utf-8')
                        if decoded not in found_switches:
                            found_switches.append(decoded)
        except Exception:
            pass

        return found_switches

    def get_brute_force_help_command(self, file_path: Path) -> str:
        """Return a command to try and elicit help output."""
        return f'"{file_path}" /?'

    def _check_hp_installer(self, file_path: Path) -> bool:
        """Check for HP SoftPaq or HP installer signature."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)

                # Check for HP specific markers
                if b"Hewlett-Packard" in data or b"HP Inc." in data:
                    if b"SoftPaq" in data or b"Setup" in data:
                        return True
                # Also check filename pattern for HP
                if file_path.name.lower().startswith("sp") and file_path.name.lower().endswith(".exe"):
                    if any(m in data for m in [b"Hewlett", b"HP ", b"HP_"]):
                        return True
        except Exception:
            pass
        return False

    def _check_dell_installer(self, file_path: Path) -> bool:
        """Check for Dell Update Package signature."""
        try:
            # Check filename patterns first (fast check)
            name_lower = file_path.name.lower()
            dell_filename_patterns = [
                "dell-command",
                "dellcommand",
                "dell_command",
                "dell-update",
                "dellupdate",
            ]
            for pattern in dell_filename_patterns:
                if pattern in name_lower:
                    return True

            with open(file_path, 'rb') as f:
                # Read more data for Dell installers which may have markers deeper
                data = f.read(1024 * 1024 * 2)  # 2MB
                markers = [
                    b"Dell Inc.",
                    b"Dell Update Package",
                    b"DUP Framework",
                    b"Dell Command",
                    b"Dell Technologies",
                    b"Dell\\x00Inc",  # Wide char variant
                    b"D\x00e\x00l\x00l",  # UTF-16 "Dell"
                ]
                for marker in markers:
                    if marker in data:
                        return True
        except Exception:
            pass
        return False

    def _check_sap_installer(self, file_path: Path) -> bool:
        """Check for SAP installer signature."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)
                markers = [
                    b"SAP SE",
                    b"SAP AG",
                    b"SAP Setup",
                    b"SAPCAR",
                    b"SAPSetup",
                ]
                for marker in markers:
                    if marker in data:
                        return True
        except Exception:
            pass
        return False

    def _check_lenovo_installer(self, file_path: Path) -> bool:
        """Check for Lenovo installer signature."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)
                markers = [
                    b"Lenovo",
                    b"ThinkPad",
                    b"ThinkCentre",
                    b"Lenovo System Update",
                    b"Lenovo Vantage",
                ]
                for marker in markers:
                    if marker in data:
                        return True
        except Exception:
            pass
        return False

    def _check_intel_installer(self, file_path: Path) -> bool:
        """Check for Intel Installer Framework signature."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)
                markers = [
                    b"Intel Corporation",
                    b"Intel(R)",
                    b"Intel Driver",
                    b"Intel Setup",
                    b"Intel PROSet",
                ]
                for marker in markers:
                    if marker in data:
                        return True
        except Exception:
            pass
        return False

    def _check_nvidia_installer(self, file_path: Path) -> bool:
        """Check for NVIDIA installer signature."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)
                markers = [
                    b"NVIDIA Corporation",
                    b"NVIDIA",
                    b"GeForce",
                    b"nv_disp",
                    b"nvoglv",
                ]
                for marker in markers:
                    if marker in data:
                        return True
        except Exception:
            pass
        return False

    def _check_amd_installer(self, file_path: Path) -> bool:
        """Check for AMD/ATI installer signature."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024)
                markers = [
                    b"Advanced Micro Devices",
                    b"AMD Software",
                    b"ATI Technologies",
                    b"Radeon",
                    b"AMD Catalyst",
                ]
                for marker in markers:
                    if marker in data:
                        return True
        except Exception:
            pass
        return False

    def _check_vcredist(self, file_path: Path) -> bool:
        """Check for Visual C++ Redistributable."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 512)
                markers = [
                    b"Visual C++",
                    b"VC++ Redistributable",
                    b"vcredist",
                    b"Microsoft Visual C++",
                ]
                for marker in markers:
                    if marker in data:
                        return True
                # Also check filename
                if "vcredist" in file_path.name.lower() or "vc_redist" in file_path.name.lower():
                    return True
        except Exception:
            pass
        return False

    def _check_java_installer(self, file_path: Path) -> bool:
        """Check for Java/Oracle installer signature."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 512)
                markers = [
                    b"Oracle Corporation",
                    b"Java(TM)",
                    b"Java Runtime",
                    b"jre-",
                    b"jdk-",
                ]
                for marker in markers:
                    if marker in data:
                        return True
                # Also check filename
                name_lower = file_path.name.lower()
                if name_lower.startswith("jre") or name_lower.startswith("jdk"):
                    return True
        except Exception:
            pass
        return False

    def _check_portableapps(self, pe: pefile.PE, file_path: Path) -> bool:
        """Check for PortableApps.com launcher."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 512)
                markers = [
                    b"PortableApps.com",
                    b"PortableApps.comLauncher",
                    b"PortableApps.comInstaller",
                ]
                for marker in markers:
                    if marker in data:
                        return True

            # Check PE resources for "PortableApps.com"
            if hasattr(pe, 'FileInfo'):
                for file_info in pe.FileInfo:
                    for entry in file_info:
                        if hasattr(entry, 'StringTable'):
                            for st in entry.StringTable:
                                for key, value in st.entries.items():
                                    val_str = value.decode('utf-8', errors='ignore')
                                    if "PortableApps.com" in val_str:
                                        return True
        except Exception:
            pass
        return False

    def _check_generic_portable(self, file_path: Path, loose: bool = False) -> bool:
        """
        Check for signs of a generic portable app wrapper.
        If loose is True, checks for less specific indicators (fallback).
        """
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024) # Read 1MB

                # Strong indicators
                strong_markers = [
                    b"BoxedAppScanner",
                    b"Virtual Box",
                    b"Enigma Virtual Box",
                    b"VMWare ThinApp",
                    b"Turbo Studio",
                    b"Spoon Studio",
                    b"Cameyo",
                    b"Evalaze"
                ]

                for marker in strong_markers:
                    if marker in data:
                        return True

                if loose:
                    # Weak indicators / patterns for self-contained apps
                    weak_markers = [
                        b"App\\AppInfo", # Common portable structure reference
                        b"Data\\Settings",
                        b"Portable",
                    ]

                    found_weak = 0
                    for marker in weak_markers:
                        if marker in data:
                            found_weak += 1

                    if found_weak >= 2:
                        return True

        except Exception:
            pass
        return False
