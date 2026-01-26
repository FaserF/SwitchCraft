import os
import logging
from pathlib import Path
from typing import List, Optional
from switchcraft.utils.shell_utils import ShellUtils
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class SapService:
    """
    Service for managing SAP Installation Servers (nwsetupadmin).
    Handles updates, customization (Logo, WebView2), and packaging.
    """

    def __init__(self):
        pass

    def detect_admin_tool(self, server_path: str) -> Optional[Path]:
        """Tries to find NwSapSetupAdmin.exe in the given server path."""
        p = Path(server_path)
        # Usually in /Setup/NwSapSetupAdmin.exe or directly in root
        candidates = [
            p / "Setup" / "NwSapSetupAdmin.exe",
            p / "NwSapSetupAdmin.exe"
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def merge_update(self, server_path: str, update_exe: str) -> bool:
        """Merges an update into the installation server."""
        admin_tool = self.detect_admin_tool(server_path)
        if not admin_tool:
            raise FileNotFoundError(f"SAP Admin Tool (NwSapSetupAdmin.exe) not found in {server_path}")

        # Command: NwSapSetupAdmin.exe /UpdateServer /dest:"server_path" /source:"update_exe"
        cmd = [
            str(admin_tool),
            "/UpdateServer",
            f"/dest={server_path}",
            f"/source={update_exe}"
        ]

        logger.info(f"Merging SAP update: {cmd}")
        result = ShellUtils.run_command(cmd)
        if result and result.returncode == 0:
            return True

        error_msg = result.stderr if result else "Unknown error"
        logger.error(f"SAP Merge failed: {error_msg}")
        raise RuntimeError(f"Failed to merge SAP update: {error_msg}")

    def customize_server(self, server_path: str, logo_path: Optional[str] = None, use_webview2: bool = True) -> bool:
        """
        Customizes the SAP Installation Server.
        - Logo: Copies the logo and updates config if necessary.
        - WebView2: Sets Edge WebView2 as default in the config XML.
        """
        setup_dir = Path(server_path) / "Setup"
        if not setup_dir.exists():
            raise FileNotFoundError(f"SAP Setup directory not found: {setup_dir}")

        # 1. Custom Logo
        if logo_path and os.path.exists(logo_path):
            target_logo = setup_dir / "custom_logo.png"
            import shutil
            shutil.copy(logo_path, target_logo)
            logger.info(f"Custom SAP logo copied to {target_logo}")
            # Note: SAP usually expects a specific filename or XML ref.
            # We assume 'custom_logo.png' is used or we'll update the XML.

        # 2. WebView2 & XML Customization
        # SAP often uses 'SapGuiSetup.xml' or similar in the Setup folder
        config_file = setup_dir / "SapGuiSetup.xml"
        if config_file.exists():
            try:
                tree = ET.parse(config_file)
                root = tree.getroot()

                # Logic to find/update WebView2 pref
                # This is a best-effort based on common SAP XML structures
                changed = False
                for param in root.iter('Parameter'):
                    if param.get('Name') == 'UseWebView2':
                        param.set('Value', '1' if use_webview2 else '0')
                        changed = True

                if changed:
                    tree.write(config_file, encoding='utf-8', xml_declaration=True)
                    logger.info("SAP WebView2 configuration updated in XML.")
            except Exception as e:
                logger.warning(f"Failed to patch SAP XML config: {e}")

        return True

    def list_packages(self, server_path: str) -> List[dict]:
        """
        Parses SapSetup.xml or SapGuiSetup.xml to list available products/packages.
        Returns list of dicts: {'name': 'Package Name', 'id': 'Guid'}
        """
        packages = []

        # Possible XML files defining products
        candidates = ["SapSetup.xml", "SapGuiSetup.xml"]

        base_path = Path(server_path)
        # Handle architecture path adjustments (if user selected root, we look in Setup)
        setup_path = base_path / "Setup"
        if not setup_path.exists():
            setup_path = base_path # Maybe user pointed directly to Setup?

        for xml_name in candidates:
             xml_path = setup_path / xml_name
             if not xml_path.exists():
                 continue

             try:
                 tree = ET.parse(xml_path)
                 root = tree.getroot()

                 # Look for <Product> or <SapSetupProduct>
                 for tag in ["Product", "SapSetupProduct"]:
                     for product in root.findall(f".//{tag}"):
                         name = product.get("Name")
                         guid = product.get("Guid")
                         if name:
                             packages.append({"name": name, "id": guid})

             except Exception as e:
                 logger.error(f"Failed to parse {xml_name}: {e}")

        return packages

    def create_single_file_installer(self, server_path: str, package_name: str, output_dir: str) -> str:
        """
        Creates a Single File Installer (SFU) for the specified package.
        UsesNwSapSetupAdmin.exe from the server path.
        """
        admin_tool = self.detect_admin_tool(server_path)
        if not admin_tool:
            raise FileNotFoundError("SAP Admin Tool not found.")

        output_path = Path(output_dir)
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)

        # Use a temporary batch file to guarantee exact quoting behavior.
        import tempfile
        import os

        # Ensure output_dir is the directory
        output_dir = Path(output_path)
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        # Target file must be specified in /Dest for many SFU creators
        target_file_path = output_dir / f"{package_name}.exe"

        # Using colon-based syntax which is often required for legacy SAP tools
        # /CreateSFU:"Path" /Package:"Name" /Silent
        bat_content = f"""
@echo off
"{str(admin_tool)}" /CreateSFU:"{str(target_file_path)}" /Package:"{package_name}" /Silent
echo Exit Code: %ERRORLEVEL%
"""
        fd, bat_path = tempfile.mkstemp(suffix=".bat", text=True)
        os.close(fd)

        try:
            with open(bat_path, "w") as f:
                f.write(bat_content)

            logger.info(f"Executing SAP Batch Wrapper: {bat_path}")
            logger.info(f"Command: \"{str(admin_tool)}\" /CreateSFU:\"{str(target_file_path)}\" /Package:\"{package_name}\" /Silent")

            # Run the batch file
            result = ShellUtils.run_command([bat_path])

            if result:
                 logger.info(f"SAP Batch Output: {result.stdout}")
                 if result.stderr:
                     logger.error(f"SAP Batch Stderr: {result.stderr}")

        finally:
            if os.path.exists(bat_path):
                os.unlink(bat_path)

        if target_file_path.exists():
            return str(target_file_path)

        # If result was OK, return dir
        if result and result.returncode == 0:
             return str(output_path)

        raise RuntimeError(f"Failed to create SAP SFU. ReturnCode: {result.returncode if result else 'None'}.")
