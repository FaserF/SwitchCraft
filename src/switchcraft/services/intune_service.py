
import logging
import os
import subprocess
import requests
from pathlib import Path
from switchcraft.utils.i18n import i18n

logger = logging.getLogger(__name__)

class IntuneService:
    """
    Service to handle Microsoft Win32 Content Prep Tool operations.
    """

    TOOL_URL = "https://github.com/microsoft/Microsoft-Win32-Content-Prep-Tool/raw/master/IntuneWinAppUtil.exe"
    TOOL_FILENAME = "IntuneWinAppUtil.exe"

    def __init__(self, tools_dir: str = None):
        if tools_dir:
            self.tools_dir = Path(tools_dir)
        else:
            # Default to a 'tools' directory in the user's home or app data
            self.tools_dir = Path.home() / ".switchcraft" / "tools"

        self.tool_path = self.tools_dir / self.TOOL_FILENAME

    def is_tool_available(self) -> bool:
        return self.tool_path.exists()

    def download_tool(self) -> bool:
        """Downloads the IntuneWinAppUtil.exe from Microsoft."""
        try:
            self.tools_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Downloading IntuneWinAppUtil from {self.TOOL_URL}...")

            response = requests.get(self.TOOL_URL, stream=True)
            response.raise_for_status()

            with open(self.tool_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info("IntuneWinAppUtil downloaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to download IntuneWinAppUtil: {e}")
            return False

    def create_intunewin(self, source_folder: str, setup_file: str, output_folder: str, catalog_folder: str = None, quiet: bool = True) -> str:
        """
        Runs the IntuneWinAppUtil to generate the .intunewin package.
        Returns the output text from the tool.
        """
        if not self.is_tool_available():
            if not self.download_tool():
                raise FileNotFoundError("IntuneWinAppUtil.exe not found and could not be downloaded.")

        # Ensure paths are absolute strings
        source_folder = str(Path(source_folder).resolve())

        # Check if setup_file looks like a full path, verify it is inside source_folder
        setup_path = Path(setup_file)
        if setup_path.is_absolute():
            # If absolute, verify it starts with source_folder
             try:
                 rel_path = setup_path.relative_to(source_folder)
                 setup_arg = str(rel_path)
             except ValueError:
                 # It's not inside? Intune tool might fail.
                 # But let's assume the user provided just the filename or correct relative path if possible.
                 setup_arg = setup_file
        else:
            setup_arg = setup_file

        output_folder = str(Path(output_folder).resolve())
        Path(output_folder).mkdir(parents=True, exist_ok=True)

        cmd = [
            str(self.tool_path),
            "-c", source_folder,
            "-s", setup_arg,
            "-o", output_folder
        ]

        if catalog_folder:
             cmd.extend(["-a", str(Path(catalog_folder).resolve())])

        if quiet:
            cmd.append("-q")

        logger.info(f"Running IntuneWinAppUtil: {cmd}")

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='cp1252', # Windows tool output encoding
                startupinfo=startupinfo
            )

            if process.returncode == 0:
                logger.info("IntuneWin package created successfully.")
                return process.stdout
            else:
                logger.error(f"IntuneWin creation failed: {process.stderr}")
                raise RuntimeError(f"Tool exited with code {process.returncode}: {process.stdout}")

        except Exception as e:
            logger.error(f"Error running IntuneWinAppUtil: {e}")
            raise e
