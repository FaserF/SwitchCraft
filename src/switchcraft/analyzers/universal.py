import logging
import subprocess
import shutil
import tempfile
import os
from pathlib import Path
from typing import Optional, List, Dict
import py7zr

logger = logging.getLogger(__name__)

class UniversalAnalyzer:
    def __init__(self):
        self.msi_markers = [b"Windows Installer", b"msiexec", b"ProductCode", b".msi"]
        self.msi_help_keywords = ["/quiet", "/passive", "/norestart", "msiexec"]

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
                except:
                    pass

            # 2. Simple overlay scan (if not 7z, maybe standard zip or cab attached)
            # This is expensive, so maybe skip or do light scan
            pass

        except Exception as e:
            logger.warning(f"Wrapper check failed: {e}")

        return None

    def brute_force_help(self, file_path: Path) -> Dict[str, str]:
        """
        Runs the executable with /? and --help and captures output.
        Returns a dictionary with 'output' (combined stdout/stderr) and 'detected_type'.
        """
        result = {"output": "", "detected_type": None, "suggested_switches": []}

        # Commands to try. Order matters.
        # /? is standard for Windows. --help is standard for cross-platform/new tools.
        commands = [["/?"], ["--help"], ["-h"], ["/help"]]

        captured_output = ""

        for cmd_args in commands:
            try:
                # Run with timeout to prevent hanging.
                # DETACHED_PROCESS flag might be needed to avoid popping up windows, but strictly capturing
                # output from GUI apps is hard on Windows. cli apps work fine.
                # startupinfo to hide window?
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                proc = subprocess.run(
                    [str(file_path)] + cmd_args,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    startupinfo=startupinfo,
                    encoding='cp1252', # Default windows encoding usually
                    errors='ignore'
                )

                output = proc.stdout + "\n" + proc.stderr
                if output.strip():
                    captured_output += f"--- Command: {' '.join(cmd_args)} ---\n{output}\n"

                    # Analyze this output immediately
                    detected, switches = self._analyze_help_text(output)
                    if detected:
                        result["detected_type"] = detected
                        result["suggested_switches"] = switches
                        break # Found something useful!

            except subprocess.TimeoutExpired:
                 captured_output += f"--- Command: {' '.join(cmd_args)} ---\n[Timed Out]\n"
            except Exception as e:
                 captured_output += f"--- Command: {' '.join(cmd_args)} ---\n[Error: {e}]\n"

        result["output"] = captured_output
        return result

    def _analyze_help_text(self, text: str) -> (Optional[str], List[str]):
        """Analyzes help text for known patterns."""
        lower_text = text.lower()

        # MSI Standard Help
        if "/quiet" in lower_text and "/passive" in lower_text and "msiexec" in lower_text:
            return "MSI Wrapper", ["/quiet", "/norestart"]

        # InstallShield
        if "/s" in lower_text and "/v" in lower_text:
             return "InstallShield", ["/s", "/v\"/qn\""]

        # Inno Setup
        if "/verysilent" in lower_text:
            return "Inno Setup", ["/VERYSILENT", "/NORESTART"]

        # NSIS
        if "/s" in lower_text and "nullsoft" in lower_text:
             return "NSIS", ["/S"]

        # Generic "Silent" mentions
        if "silent" in lower_text or "quiet" in lower_text:
             # Try to start extracting switches? Too complex for regex maybe.
             pass

        return None, []
