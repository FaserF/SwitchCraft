import logging
import subprocess
import re
import shutil
import tempfile
import os
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import py7zr

logger = logging.getLogger(__name__)

class UniversalAnalyzer:
    """Universal analyzer with wrapper detection and comprehensive brute force parameter discovery."""

    def __init__(self):
        self.msi_markers = [b"Windows Installer", b"msiexec", b"ProductCode", b".msi"]
        self.msi_help_keywords = ["/quiet", "/passive", "/norestart", "msiexec"]

        # Extended list of commands to try for brute force help discovery
        self.brute_force_commands = [
            ["/?"],
            ["--help"],
            ["-h"],
            ["/help"],
            ["/h"],
            ["-?"],
            ["--info"],
            ["-help"],
            ["--usage"],
            ["-V"],
            ["--version"],
            ["/info"],
            ["-i"],
            ["--silent"],
            ["/silent"],
            # Expanded params for Phase 2
            ["/S"],
            ["-s"],
            ["/quiet"],
            ["-quiet"],
            ["/qn"],
            ["/q"],
            ["--quite"], # typo safety
            ["/verysilent"],
            ["-verysilent"],
        ]



    def check_corruption(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Checks for basic file corruption using header validation.
        Returns (is_corrupted, reason).
        """
        try:
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                 return True, "File is empty or does not exist."

            with open(file_path, 'rb') as f:
                header = f.read(4)

            # EXE (MZ)
            if str(file_path).lower().endswith(".exe"):
                if not header.startswith(b'MZ'):
                     return True, "Invalid EXE header (missing 'MZ')."

            # MSI (OLE Compound File)
            elif str(file_path).lower().endswith(".msi"):
                if not header.startswith(b'\xD0\xCF\x11\xE0'):
                     return True, "Invalid MSI header (missing OLE signature)."

            return False, None
        except Exception as e:
            return True, f"Read error: {e}"

    def check_wrapper(self, file_path: Path) -> Optional[str]:
        """
        Inspects the file to see if it wraps an MSI.
        Returns 'MSI Wrapper' if detected, else None.
        """
        try:
            # 1. Check with py7zr (7-Zip)
            if py7zr.is_7zfile(file_path):
                try:
                    with py7zr.SevenZipFile(file_path, mode='r') as z:
                        for filename in z.getnames():
                            if filename.lower().endswith('.msi'):
                                return f"MSI Wrapper (contains {filename})"
                except Exception:
                    pass

            # 2. Simple binary scan for embedded MSI markers
            try:
                with open(file_path, 'rb') as f:
                    data = f.read(1024 * 1024 * 5)  # Read 5MB

                    # Check for MSI file signature embedded
                    if b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" in data:  # OLE signature
                        # Check if it contains MSI-like properties
                        if b"ProductCode" in data or b"UpgradeCode" in data:
                            return "MSI Wrapper (embedded MSI detected)"
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Wrapper check failed: {e}")

        return None

    def brute_force_help(self, file_path: Path) -> Dict[str, any]:
        """
        Runs the executable with various help arguments and captures output.
        Returns a dictionary with 'output' (combined stdout/stderr), 'detected_type', and 'suggested_switches'.
        """
        result = {
            "output": "",
            "detected_type": None,
            "suggested_switches": [],
            "all_attempts": []
        }

        captured_output = ""

        # 0. Try "All at once" strategy first (Phase 2 Req)
        # Many CLIs basically dump help if you send ANY invalid or help arg.
        # Sending multiple might trigger help immediately or error-help.
        # We skip params that trigger installation (/silent, /s) for safety here.

        try:
             # Just try a few common ones concatenated? No, usually executables take one mode.
             # But we can try to RUN once with a safe help argument and see if it dumps EVERYTHING.
             pass
        except Exception:
            pass

        # Actually, the user requirement is: "Try all brute force parameters AT ONCE".
        # This implies running: `setup.exe /? --help -h /help ...`
        # This often confuses the parser into showing help/error usage.

        try:
             all_safe_args = [x[0] for x in self.brute_force_commands if "silent" not in x[0] and "/s" not in x[0].lower() and "/q" not in x[0].lower()]
             # Limit to avoid command line length issues
             all_safe_args = all_safe_args[:10]

             cmd_args = all_safe_args

             startupinfo = None
             if os.name == 'nt':
                 startupinfo = subprocess.STARTUPINFO()
                 startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

             proc = subprocess.run(
                 [str(file_path)] + cmd_args,
                 capture_output=True,
                 text=True,
                 timeout=5,
                 startupinfo=startupinfo,
                 encoding='cp1252' if os.name == 'nt' else 'utf-8',
                 errors='ignore'
             )
             output = proc.stdout + "\n" + proc.stderr

             if output.strip():
                 captured_output += f"--- Attempt: ALL PARAMS (Exit: {proc.returncode}) ---\n"
                 detected, switches = self._analyze_help_text(output)
                 if detected:
                     result["detected_type"] = detected
                     result["suggested_switches"] = switches
                     result["output"] = captured_output + output
                     return result # Success on first try!

                 captured_output += output + "\n"

        except Exception as e:
             captured_output += f"--- Attempt: ALL PARAMS Failed: {e} ---\n"


        for cmd_args in self.brute_force_commands:
            try:
                # Prepare to hide window on Windows
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                proc = subprocess.run(
                    [str(file_path)] + cmd_args,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    startupinfo=startupinfo,
                    encoding='cp1252' if os.name == 'nt' else 'utf-8',
                    errors='ignore'
                )

                output = proc.stdout + "\n" + proc.stderr
                attempt_info = {
                    "command": " ".join(cmd_args),
                    "return_code": proc.returncode,
                    "has_output": bool(output.strip())
                }
                result["all_attempts"].append(attempt_info)

                if output.strip():
                    captured_output += f"--- Command: {' '.join(cmd_args)} (Exit: {proc.returncode}) ---\n{output}\n"

                    # Analyze this output immediately
                    detected, switches = self._analyze_help_text(output)
                    if detected:
                        result["detected_type"] = detected
                        result["suggested_switches"] = switches
                        break  # Found something useful!

            except subprocess.TimeoutExpired:
                captured_output += f"--- Command: {' '.join(cmd_args)} ---\n[Timed Out - may be waiting for user input]\n"
                result["all_attempts"].append({
                    "command": " ".join(cmd_args),
                    "return_code": -1,
                    "has_output": False,
                    "timed_out": True
                })
            except Exception as e:
                captured_output += f"--- Command: {' '.join(cmd_args)} ---\n[Error: {e}]\n"

        result["output"] = captured_output

        # If no specific type detected, try to extract any switches from the output
        if not result["detected_type"] and captured_output:
            extracted = self._extract_switches_from_text(captured_output)
            if extracted:
                result["suggested_switches"] = extracted
                result["detected_type"] = "Generic (switches extracted from help)"

        return result

    def _analyze_help_text(self, text: str) -> Tuple[Optional[str], List[str]]:
        """Analyzes help text for known patterns."""
        lower_text = text.lower()

        # MSI Standard Help
        if "/quiet" in lower_text and "/passive" in lower_text and "msiexec" in lower_text:
            return "MSI Wrapper", ["/quiet", "/norestart"]

        # InstallShield patterns
        if ("/s" in lower_text and "/v" in lower_text) or "installshield" in lower_text:
            return "InstallShield", ["/s", "/v\"/qn\""]

        # Inno Setup patterns
        if "/verysilent" in lower_text or "inno setup" in lower_text:
            return "Inno Setup", ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]

        # Nullsoft (NSIS) patterns
        if "/s" in lower_text and "/ncij" not in lower_text: # avoid false positive with some weird installers
            # NSIS usually supports /S (case sensitive sometimes)
            if "nsis" in lower_text or "nullsoft" in lower_text:
                 return "NSIS", ["/S"]

        # Wise Installer
        if "/s" in lower_text and "wise" in lower_text:
            return "Wise Installer", ["/s"]

        # TeamViewer (Common in DE)
        if "teamviewer" in lower_text or "/s" in lower_text and "apitoken" in lower_text:
            return "TeamViewer", ["/S"]

        # SAP GUI / SAP FrontEnd (Common in DE)
        if "sap" in lower_text and ("nwbc" in lower_text or "/silent" in lower_text):
             # SAP often uses specific switches
             return "SAP Installer", ["/Silent", "/NoDlg"]

        # Datev (Common in DE)
        if "datev" in lower_text or "dvd" in lower_text:
             # Datev often wraps MSI or uses proprietary switches
             return "Datev Installer", ["/Silent", "/Quiet"]

        # Matrix42 (Common in DE)
        if "matrix42" in lower_text or "empirum" in lower_text:
             return "Matrix42/Empirum", ["/S2"]

        # Abacus (Common in CH/DE)
        if "abacus" in lower_text:
             return "Abacus Installer", ["/SILENT"]

        # Sage (Common in DE)
        if "sage" in lower_text:
             return "Sage Installer", ["/silent", "/quiet"]

        # Wix Toolset (Burns)
        if "wix" in lower_text or "burn" in lower_text:
            return "Wix Bundle", ["/quiet", "/norestart"]

        # Squirrel (Discord, Slack, etc)
        if "squirrel" in lower_text or "update.exe" in lower_text:
             return "Squirrel", ["--silent"]

        # Advanced Installer
        if "advanced installer" in lower_text or "/exenoui" in lower_text:
            return "Advanced Installer", ["/exenoui", "/qn"]

        # Generic /S detection if nothing else matched but /S is present
        if ("/s" in lower_text and "silent" in lower_text) or re.search(r"/\s", lower_text):
             return "Generic (Silent supported)", ["/S", "/silent", "/quiet"]

        # Generic silent/quiet detection
        if "/silent" in lower_text or "--silent" in lower_text:
            if "/silent" in lower_text:
                return "Generic Installer", ["/silent"]
            return "Generic Installer", ["--silent"]

        if "/quiet" in lower_text or "--quiet" in lower_text:
            if "/quiet" in lower_text:
                return "Generic Installer", ["/quiet"]
            return "Generic Installer", ["--quiet"]

        return None, []

    def _extract_switches_from_text(self, text: str) -> List[str]:
        """Extract potential switches from help text using regex patterns."""
        switches = []

        # Common switch patterns
        patterns = [
            r'(\/[Ss](?:ilent)?)\b',          # /S, /s, /Silent
            r'(\/[Qq](?:uiet)?)\b',           # /Q, /q, /Quiet
            r'(--silent)\b',                   # --silent
            r'(--quiet)\b',                    # --quiet
            r'(\/VERYSILENT)\b',              # /VERYSILENT
            r'(\/SUPPRESSMSGBOXES)\b',        # /SUPPRESSMSGBOXES
            r'(\/NORESTART)\b',               # /NORESTART
            r'(\/norestart)\b',               # /norestart
            r'(\/passive)\b',                 # /passive
            r'(-q)\b',                        # -q
            r'(\/qn)\b',                      # /qn (MSI)
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match and match not in switches:
                    switches.append(match)

        return switches[:5]  # Limit to 5 most relevant switches

    def extract_and_analyze_nested(self, file_path: Path, depth: int = 1, max_depth: int = 2, progress_callback=None) -> Dict:
        """
        Attempts to extract the archive (SFX or otherwise) and analyze nested executables.
        Uses 7-Zip command line for maximum compatibility.
        Recursively extracts nested wrappers up to max_depth.

        Returns:
            Dict with keys:
                - extractable: bool
                - nested_executables: List of dicts with name, path, analysis results
                - temp_dir: Path to temp extraction dir (caller should clean up)
                - archive_type: Detected archive type
        """
        result = {
            "extractable": False,
            "nested_executables": [],
            "temp_dir": None,
            "all_temp_dirs": [],
            "archive_type": None,
            "error": None
        }

        # Find 7-Zip executable
        seven_zip_paths = [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
            shutil.which("7z"),
            shutil.which("7za"),
        ]

        seven_zip = None
        for path in seven_zip_paths:
            if path and os.path.exists(path):
                seven_zip = path
                break

        if not seven_zip:
            result["error"] = "7-Zip not found. Please install 7-Zip for archive extraction."
            return result

        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix="switchcraft_extract_")
        result["temp_dir"] = temp_dir
        result["all_temp_dirs"].append(temp_dir)

        try:
            # Try to list archive contents first
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            if progress_callback:
                progress_callback(10, f"Listing archive content ({file_path.name})...")

            list_proc = subprocess.run(
                [seven_zip, "l", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
                startupinfo=startupinfo
            )

            if list_proc.returncode != 0:
                result["error"] = "Cannot read archive - may not be extractable"
                return result

            # Detect archive type from 7z output
            output_lines = list_proc.stdout
            if "Type = PE" in output_lines:
                result["archive_type"] = "PE/SFX Archive"
            elif "Type = 7z" in output_lines:
                result["archive_type"] = "7-Zip Archive"
            elif "Type = Nsis" in output_lines:
                result["archive_type"] = "NSIS Installer"
            elif "Type = Cab" in output_lines:
                result["archive_type"] = "Windows Cabinet"
            else:
                result["archive_type"] = "Unknown Archive"

            # Extract to temp directory
            if progress_callback:
                progress_callback(20, f"Extracting {file_path.name}...")
            extract_proc = subprocess.run(
                [seven_zip, "x", "-y", f"-o{temp_dir}", str(file_path)],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minutes for large files
                startupinfo=startupinfo
            )

            if extract_proc.returncode != 0:
                result["error"] = f"Extraction failed: {extract_proc.stderr[:200]}"
                return result

            result["extractable"] = True

            # Find executables in extracted content
            from switchcraft.analyzers.exe import ExeAnalyzer
            from switchcraft.analyzers.msi import MsiAnalyzer

            exe_analyzer = ExeAnalyzer()
            msi_analyzer = MsiAnalyzer()

            for root, dirs, files in os.walk(temp_dir):
                # Pre-count for progress
                total_files = len(files)
                for i, file in enumerate(files):
                    # Progress calculation: 30% to 90%
                    pct = 30 + (int((i / total_files) * 60) if total_files > 0 else 0)
                    if progress_callback:
                        progress_callback(pct, f"Analyzing nested file: {file}")

                    ext = os.path.splitext(file)[1].lower()
                    if ext in ['.exe', '.msi']:
                        full_path = Path(os.path.join(root, file))
                        rel_path = os.path.relpath(full_path, temp_dir)

                        nested_info = {
                            "name": file,
                            "relative_path": rel_path,
                            "full_path": str(full_path),
                            "type": ext.upper()[1:],
                            "analysis": None
                        }

                        # Analyze the nested executable
                        try:
                            if ext == '.msi' and msi_analyzer.can_analyze(full_path):
                                nested_info["analysis"] = msi_analyzer.analyze(full_path)
                            elif ext == '.exe' and exe_analyzer.can_analyze(full_path):
                                nested_info["analysis"] = exe_analyzer.analyze(full_path)

                                # If EXE analysis returns unknown, try brute force
                                if nested_info["analysis"] and "Unknown" in nested_info["analysis"].installer_type:
                                    bf_result = self.brute_force_help(full_path)
                                    if bf_result.get("detected_type"):
                                        nested_info["analysis"].installer_type = bf_result["detected_type"]
                                        nested_info["analysis"].install_switches = bf_result.get("suggested_switches", [])
                                    nested_info["brute_force_output"] = bf_result.get("output", "")
                        except Exception as e:
                            nested_info["error"] = str(e)

                        result["nested_executables"].append(nested_info)

                        # Recursive Extraction Check
                        if depth < max_depth and ext == '.exe':
                             # Quick check if it is a wrapper
                            is_wrapper = self.check_wrapper(full_path)
                            if is_wrapper:
                                logger.info(f"Detected nested wrapper: {file} ({is_wrapper}). Recursing...")

                                # Recurse
                                sub_result = self.extract_and_analyze_nested(full_path, depth=depth+1, max_depth=max_depth, progress_callback=progress_callback)

                                if sub_result["extractable"]:
                                    # Add children to our list, modifying path to show hierarchy
                                    for sub in sub_result.get("nested_executables", []):
                                        sub["relative_path"] = f"{rel_path}/{sub['relative_path']}"
                                        result["nested_executables"].append(sub)

                                    # Track sub temp dirs for cleanup
                                    if "all_temp_dirs" in sub_result:
                                        result["all_temp_dirs"].extend(sub_result["all_temp_dirs"])
                                    elif sub_result.get("temp_dir"):
                                         result["all_temp_dirs"].append(sub_result["temp_dir"])

            # Sort by likelihood - MSI first, then EXE with detected type
            result["nested_executables"].sort(
                key=lambda x: (
                    0 if x["type"] == "MSI" else 1,
                    0 if x.get("analysis") and "Unknown" not in x["analysis"].installer_type else 1
                )
            )

        except subprocess.TimeoutExpired:
            result["error"] = "Extraction timed out"
        except Exception as e:
            result["error"] = str(e)

        return result

    def detect_silent_disabled(self, file_path: Path, brute_force_output: str = "") -> Dict:
        """
        Attempts to detect if silent installation has been intentionally disabled.

        Returns:
            Dict with:
                - disabled: bool
                - reason: str (explanation)
                - indicators: List of detected indicators
        """
        result = {
            "disabled": False,
            "reason": None,
            "indicators": []
        }

        # Check brute force output for indicators of disabled silent mode
        lower_output = brute_force_output.lower()

        disabled_indicators = [
            ("silent mode is not supported", "Developer explicitly disabled silent mode"),
            ("silent installation is disabled", "Developer explicitly disabled silent mode"),
            ("silent mode not available", "Developer explicitly disabled silent mode"),
            ("cannot run in silent mode", "Developer explicitly disabled silent mode"),
            ("/s is not supported", "/S switch explicitly disabled"),
            ("--silent is not available", "--silent switch explicitly disabled"),
            ("interactive mode only", "Installer requires user interaction"),
            ("gui required", "GUI is required for installation"),
            ("no command line", "No command line interface available"),
            ("must run interactively", "Interactive mode required"),
        ]

        for indicator, reason in disabled_indicators:
            if indicator in lower_output:
                result["disabled"] = True
                result["reason"] = reason
                result["indicators"].append(indicator)

        # Also check the binary for similar strings
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024 * 1024 * 2)  # Read 2MB

                binary_indicators = [
                    (b"SilentModeDisabled", "SilentModeDisabled flag found in binary"),
                    (b"SILENT_DISABLED", "SILENT_DISABLED flag found in binary"),
                    (b"NoSilentInstall", "NoSilentInstall flag found in binary"),
                    (b"DisableSilent", "DisableSilent configuration found"),
                    (b"RequireGUI", "RequireGUI flag found in binary"),
                ]

                for indicator, reason in binary_indicators:
                    if indicator in data:
                        result["disabled"] = True
                        result["reason"] = reason
                        result["indicators"].append(indicator.decode('utf-8', errors='ignore'))
        except Exception:
            pass

        return result

    def cleanup_temp_dir(self, temp_dir: str) -> None:
        """Clean up temporary extraction directory."""
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir {temp_dir}: {e}")
