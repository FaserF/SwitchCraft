import re
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Optional
import sys

logger = logging.getLogger(__name__)

class TemplateGenerator:
    """Generates PowerShell scripts from templates."""

    DEFAULT_TEMPLATE_PATH = Path(__file__).parent.parent / "assets" / "templates" / "DefaultIntuneTemplate.ps1"

    def __init__(self, custom_template_path: str = None):
        from switchcraft.utils.config import SwitchCraftConfig
        self.template_content = None

        # 1. Argument override
        if custom_template_path and Path(custom_template_path).exists():
            self.template_path = Path(custom_template_path)
            self.is_custom = True
            return

        # 2. Config override
        config_path = SwitchCraftConfig.get_value("CustomTemplatePath")
        if config_path and Path(config_path).exists():
            self.template_path = Path(config_path)
            self.is_custom = True
            return

        # 3. Default
        self.template_path = self.DEFAULT_TEMPLATE_PATH
        self.is_custom = False

    def generate(self, context: Dict[str, str], output_path: str) -> bool:
        """
        Generates the script.
        context keys expected:
        - INSTALLER_FILE (e.g. setup.exe)
        - INSTALL_ARGS (e.g. /S)
        - APP_NAME (Product Name)
        - PUBLISHER (Company Name)
        """
        try:
            if self.template_content:
                content = self.template_content
            elif self.template_path.exists():
                content = self.template_path.read_text(encoding="utf-8")
            else:
                logger.error(f"Template not found: {self.template_path}")
                return False

            # Add global SwitchCraft metadata
            from switchcraft import __version__
            if "SWITCHCRAFT_VERSION" not in context:
                 context["SWITCHCRAFT_VERSION"] = __version__
            if "SWITCHCRAFT_GITHUB" not in context:
                 context["SWITCHCRAFT_GITHUB"] = "https://github.com/FaserF/SwitchCraft"

            # 1. Enterprise Template Specific Logic (Regex Replacement)
            # Detect if it's the specific enterprise template by looking for unique function names
            # User requested anonymization of company name "PARI"
            is_enterprise_template = "Start-Process-Function" in content and "Uninstall-SoftwareByFilter" in content

            if is_enterprise_template:
                logger.info("Detected Enterprise Intune Template structure.")

                # Replace Installer Path
                # Pattern: $Installer = Join-Path -Path $PSScriptRoot -ChildPath "Setup.exe"
                content = re.sub(
                    r'(\$Installer\s*=\s*Join-Path\s*-Path\s*\$PSScriptRoot\s*-ChildPath\s*")(.+?)(")',
                    f'\\1{context.get("INSTALLER_FILE")}\\3',
                    content
                )

                # Replace Install Args
                # Check for $Arguments = "..." style
                content = re.sub(
                    r'(\$Arguments\s*=\s*")(.+?)(")',
                    f'\\1{context.get("INSTALL_ARGS")}\\3',
                    content
                )

                # Also check for inline -ArgumentList "..." just in case
                content = re.sub(
                    r'(Start-Process-Function\s*-FilePath\s*\$Installer\s*-ArgumentList\s*")(.+?)(")',
                    f'\\1{context.get("INSTALL_ARGS")}\\3',
                    content
                )

                # Replace Uninstall Logic if possible
                # The template has: Uninstall-SoftwareByFilter -NameFilter "MySoftware" -Publisher "MyPublisher"
                app_name = context.get("APP_NAME", "MySoftware")
                publisher = context.get("PUBLISHER", "MyPublisher")

                content = re.sub(
                    r'(Uninstall-SoftwareByFilter\s*-NameFilter\s*")(.+?)(")',
                    f'\\1{app_name}\\3',
                    content
                )

                content = re.sub(
                    r'(Uninstall-SoftwareByFilter\s*-NameFilter\s*".+?"\s*-Publisher\s*")(.+?)(")',
                    f'\\1{publisher}\\3',
                    content
                )

            # 2. Generic Placeholder Replacement (Always try this too)
            for key, value in context.items():
                placeholder = f"{{{{{key}}}}}" # {{KEY}}
                if placeholder in content:
                    content = content.replace(placeholder, str(value))

            # Write output
            Path(output_path).write_text(content, encoding="utf-8")
            return True

        except Exception as e:
            logger.error(f"Failed to generate template: {e}")
            return False
