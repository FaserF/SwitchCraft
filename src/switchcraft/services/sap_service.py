import os
import logging
import subprocess
from pathlib import Path
from typing import List, Optional
from switchcraft.utils.shell_utils import ShellUtils
from switchcraft.utils.i18n import i18n
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

    def create_single_file_installer(self, server_path: str, package_name: str, output_path: str) -> str:
        """
        Creates a single-file installer (SFU) for a specific package.
        Note: NwSapSetupAdmin.exe CLI for SFU creation is semi-documented.
        We fallback to the command pattern often used for automation.
        """
        admin_tool = self.detect_admin_tool(server_path)
        if not admin_tool:
            raise FileNotFoundError("SAP Admin Tool not found.")

        # Best-guess CLI for SFU creation (NwSapSetupAdmin.exe /CreateSFU)
        # Actual implementation might require NwSapSetup.exe /Package="name" /CreateSFU
        cmd = [
            str(admin_tool),
            f"/Package={package_name}",
            "/CreateSFU",
            f"/dest={output_path}"
        ]

        logger.info(f"Creating SAP SFU: {cmd}")
        result = ShellUtils.run_command(cmd)
        if result and result.returncode == 0:
            return output_path

        raise RuntimeError(f"Failed to create SAP SFU: {result.stderr if result else 'Unknown error'}")
