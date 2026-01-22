import subprocess
import sys
import os
import logging
from typing import List, Optional, Union

logger = logging.getLogger(__name__)

class ShellUtils:
    """Utility for running system commands with cross-platform and environment awareness (Windows, Linux/Wine, Web)."""

    @staticmethod
    def run_command(cmd: Union[str, List[str]], capture_output: bool = True, text: bool = True, timeout: Optional[int] = None, silent: bool = False, **kwargs) -> Optional[subprocess.CompletedProcess]:
        """
        Runs a system command, automatically prefixing with 'wine' if on Linux and it's a Windows executable.
        Handles Web/WASM by returning a mock failure.
        """
        # 1. Check for Web/WASM (subprocess not supported)
        if sys.platform == "emscripten" or sys.platform == "wasi":
            logger.debug(f"Skipping command execution in WASM environment: {cmd}")
            # Return a mock process that indicates failure but doesn't crash
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="Subprocess not supported in browser environment.")

        # 2. Convert string to list if needed safely
        import shlex
        if isinstance(cmd, str):
            # shlex.split handles quotes correctly (unlike cmd.split())
            if sys.platform == "win32":
                # shlex default is POSIX, but for Windows we want posix=False
                # to preserve backslashes as part of paths
                cmd_list = shlex.split(cmd, posix=False)
            else:
                cmd_list = shlex.split(cmd)
        else:
            cmd_list = list(cmd)

        if not cmd_list:
            return None

        # 3. Handle Linux/Wine/Cross-Platform environment
        binary_name = cmd_list[0].lower()
        if sys.platform != "win32":
            # Check for native alternatives first
            if binary_name == "powershell":
                # Try pwsh (Powershell Core) which is the native Linux way
                import shutil
                if shutil.which("pwsh"):
                    logger.debug("Substituting 'powershell' with native 'pwsh' on Linux")
                    cmd_list[0] = "pwsh"
                    binary_name = "pwsh"
                else:
                    logger.info("Native 'pwsh' not found, falling back to Wine for 'powershell'")

            # Determine if it's a Windows-specific tool that needs Wine
            win_tools = ["winget", "msiexec", "cmd", "explorer", "clip"]
            is_win_exe = binary_name.endswith(".exe") or binary_name in win_tools

            if is_win_exe:
                # Prefix with wine if it's not already there and if native is not found
                if cmd_list[0].lower() != "wine":
                    logger.info(f"Prefixing Windows command with wine: {cmd_list}")
                    cmd_list.insert(0, "wine")

        # 4. Windows specific: Hide window if silent
        if sys.platform == "win32" and silent:
            # CREATE_NO_WINDOW = 0x08000000
            creationflags = kwargs.get("creationflags", 0)
            creationflags |= 0x08000000
            kwargs["creationflags"] = creationflags

        # 5. Execute
        try:
            return subprocess.run(cmd_list, capture_output=capture_output, text=text, timeout=timeout, **kwargs)
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out: {cmd_list}")
            raise e
        except FileNotFoundError:
            logger.error(f"Command not found: {cmd_list[0]}")
            return subprocess.CompletedProcess(args=cmd_list, returncode=127, stdout="", stderr=f"Command '{cmd_list[0]}' not found.")
        except Exception as e:
            logger.error(f"Unexpected error running command {cmd_list}: {e}")
            return subprocess.CompletedProcess(args=cmd_list, returncode=1, stdout="", stderr=str(e))

    @staticmethod
    def Popen(cmd: Union[str, List[str]], silent: bool = False, **kwargs) -> Optional[subprocess.Popen]:
        """
        Wraps subprocess.Popen with Wine awareness.
        Returns None in WASM environment.
        """
        if sys.platform == "emscripten" or sys.platform == "wasi":
            logger.debug(f"Skipping Popen in WASM environment: {cmd}")
            return None

        import shlex
        if isinstance(cmd, str):
            if sys.platform == "win32":
                cmd_list = shlex.split(cmd, posix=False)
            else:
                cmd_list = shlex.split(cmd)
        else:
            cmd_list = list(cmd)

        binary_name = cmd_list[0].lower()
        if sys.platform != "win32":
            if binary_name == "powershell":
                import shutil
                if shutil.which("pwsh"):
                    cmd_list[0] = "pwsh"
                    binary_name = "pwsh"

            win_tools = ["winget", "msiexec", "cmd", "explorer", "clip"]
            if binary_name.endswith(".exe") or binary_name in win_tools:
                if cmd_list[0].lower() != "wine":
                    cmd_list.insert(0, "wine")

        # Windows specific: Hide window if silent
        if sys.platform == "win32" and silent:
            creationflags = kwargs.get("creationflags", 0)
            creationflags |= 0x08000000
            kwargs["creationflags"] = creationflags

        try:
            return subprocess.Popen(cmd_list, **kwargs)
        except Exception as e:
            logger.error(f"Popen failed: {e}")
            return None
