import subprocess
import sys
import os
import logging
from typing import List, Optional, Union

logger = logging.getLogger(__name__)

class ShellUtils:
    """Utility for running system commands with cross-platform and environment awareness (Windows, Linux/Wine, Web)."""

    @staticmethod
    def is_wine_available() -> bool:
        """Checks if Wine is installed and available in the system path (Linux/macOS)."""
        if sys.platform == "win32":
            return True # Not needed on Windows
        import shutil
        return shutil.which("wine") is not None

    @staticmethod
    def run_command(cmd: Union[str, List[str]], capture_output: bool = True, text: bool = True, timeout: Optional[int] = None, silent: bool = False, **kwargs) -> Optional[subprocess.CompletedProcess]:
        """
        Runs a system command, automatically prefixing with 'wine' if on Linux and it's a Windows executable.
        Handles Web/WASM by returning a mock failure.
        """
        from switchcraft import IS_DEMO

        # 1. Check for Web/WASM (subprocess not supported)
        if sys.platform == "emscripten" or sys.platform == "wasi":
            logger.debug(f"Skipping command execution in WASM environment: {cmd}")
            # Return a mock process that indicates failure but doesn't crash
            msg = "Subprocess not supported in browser environment."
            if IS_DEMO:
                msg = "Feature restricted: This action is not available in the Web Demo."
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr=msg)

        # 2. Convert string to list if needed safely
        import shlex
        if isinstance(cmd, str):
            if sys.platform == "win32":
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
                # Check if Wine is available
                if not ShellUtils.is_wine_available():
                    err_msg = f"Wine is required to run '{binary_name}' on {sys.platform} but was not found. Please install Wine."
                    logger.error(err_msg)
                    return subprocess.CompletedProcess(args=cmd_list, returncode=127, stdout="", stderr=err_msg)

                # Prefix with wine if it's not already there
                if cmd_list[0].lower() != "wine":
                    logger.info(f"Prefixing Windows command with wine: {cmd_list}")
                    cmd_list.insert(0, "wine")

        # 4. Windows specific: Hide window if silent
        if sys.platform == "win32" and silent:
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
        from switchcraft import IS_DEMO

        if sys.platform == "emscripten" or sys.platform == "wasi":
            logger.debug(f"Skipping Popen in WASM environment: {cmd}")
            # We can't return a "mock Popen" easily, so we return None.
            # Callers should handle None return.
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
                if not ShellUtils.is_wine_available():
                    logger.error(f"Wine missing for Popen: {binary_name}")
                    return None

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

    @staticmethod
    def is_admin() -> bool:
        """Checks if the current process has administrative privileges."""
        try:
            if sys.platform == 'win32':
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except Exception:
            return False

    @staticmethod
    def restart_as_admin():
        """Restarts the current script with administrative privileges."""
        if sys.platform != 'win32':
            logger.warning("Elevated restart only supported on Windows.")
            return

        import ctypes

        # Get current executable and arguments
        # If running from python script: python.exe script.py args
        # If frozen (exe): switchcraft.exe args

        try:
            cwd = os.getcwd()
            if getattr(sys, 'frozen', False):
                # Running as compiled exe
                executable = sys.executable
                params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            else:
                # Running as script
                executable = sys.executable
                # Ensure script path is absolute so it works from System32/Admin context
                script_abs = os.path.abspath(sys.argv[0])
                script_path = f'"{script_abs}"'
                args = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
                params = f"{script_path} {args}"

            logger.info(f"Triggering UAC elevation for: {executable} {params} in {cwd}")

            # ShellExecute with 'runas' verb triggers UAC
            ret = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                executable,
                params,
                cwd, # Output directory
                1 # SW_SHOWNORMAL
            )

            if ret > 32:
                 # Success, exit current process
                 sys.exit(0)
            else:
                 logger.error(f"ShellExecute failed with code {ret}")

        except Exception as e:
            logger.error(f"Failed to restart as admin: {e}")
