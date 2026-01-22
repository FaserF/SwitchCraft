import yaml
import logging
import subprocess
from pathlib import Path
from switchcraft.utils.config import SwitchCraftConfig
from switchcraft.utils.shell_utils import ShellUtils

logger = logging.getLogger(__name__)

class WingetManifestService:
    """Service to generate and validate Winget Manifests."""

    def __init__(self):
        self.winget_exe = "winget" # Assumes in PATH

    def generate_manifests(self, meta: dict, output_base_dir: str = None) -> str:
        """
        Generates the standard multifile manifest structure.

        Args:
            meta (dict): Metadata including:
                - PackageIdentifier (e.g. 'Publisher.App')
                - PackageVersion
                - Publisher
                - PackageName
                - License
                - ShortDescription
                - InstallerType (exe, msi, etc)
                - Installers: List of dicts [{Architecture, InstallerUrl, InstallerSha256, InstallerType, Scope}]
                - DefaultLocale (en-US)
            output_base_dir (str): Root of the winget repo (switches to manifests/p/Pub/...)

        Returns:
            str: Path to the version directory containing the manifests.
        """
        pkg_id = meta.get("PackageIdentifier")
        version = meta.get("PackageVersion")
        publisher = meta.get("Publisher")

        if not (pkg_id and version and publisher):
            raise ValueError("Missing required fields: PackageIdentifier, PackageVersion, Publisher")

        # Determine output path
        # Standard: manifests/p/Publisher/PackageName/Version
        # We handle the 'lower case first letter' folder structure if strict compliance is needed,
        # but for local generation we stick to the provided path or Config default.

        repo_root = output_base_dir or SwitchCraftConfig.get_value("WingetRepoPath")
        if not repo_root:
            # Fallback to a local 'manifests' folder in user's home or temp
            repo_root = str(Path.home() / "SwitchCraft_Winget_Manifests")

        # Folder structure: manifests/{first_char_lower}/{Publisher}/{PackageName}/{Version}
        p_char = publisher[0].lower() if publisher else "_"
        package_name = meta.get("PackageName", pkg_id.split('.')[-1])

        manifest_dir = Path(repo_root) / "manifests" / p_char / publisher / package_name / version
        manifest_dir.mkdir(parents=True, exist_ok=True)

        # 1. Version Manifest
        self._write_version_manifest(manifest_dir, meta)

        # 2. Installer Manifest
        self._write_installer_manifest(manifest_dir, meta)

        # 3. Locale Manifest
        self._write_locale_manifest(manifest_dir, meta)

        return str(manifest_dir)

    def validate_manifest(self, manifest_dir: str) -> dict:
        """
        Validates the generated manifests using 'winget validate'.
        Returns dict with keys: 'valid' (bool), 'output' (str), 'errors' (list)
        """
        try:
            # winget validate --manifest <path_to_directory>
            cmd = [self.winget_exe, "validate", "--manifest", str(manifest_dir)]

            # Start process without window
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO') and 'subprocess' in globals():
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = ShellUtils.run_command(
                cmd,
                startupinfo=startupinfo
            )

            is_valid = "Manifest validation success" in result.stdout
            return {
                "valid": is_valid,
                "output": result.stdout + "\n" + result.stderr,
                "errors": [] if is_valid else [line for line in result.stdout.splitlines() if "Error" in line]
            }

        except FileNotFoundError:
            return {"valid": False, "output": "Winget CLI not found.", "errors": ["Winget CLI not found in PATH"]}
        except Exception as e:
            return {"valid": False, "output": str(e), "errors": [str(e)]}

    def _write_version_manifest(self, folder: Path, meta: dict):
        data = {
            "PackageIdentifier": meta["PackageIdentifier"],
            "PackageVersion": meta["PackageVersion"],
            "DefaultLocale": meta.get("DefaultLocale", "en-US"),
            "ManifestType": "version",
            "ManifestVersion": "1.6.0"
        }
        filename = f"{meta['PackageIdentifier']}.yaml"
        self._dump_yaml(folder / filename, data)

    def _write_installer_manifest(self, folder: Path, meta: dict):
        installers = meta.get("Installers", [])
        # Ensure minimal fields for installer

        data = {
            "PackageIdentifier": meta["PackageIdentifier"],
            "PackageVersion": meta["PackageVersion"],
            "InstallerLocale": meta.get("DefaultLocale", "en-US"),
            "MinimumOSVersion": "10.0.0.0",
            "Platform": ["Windows.Desktop"],
            "Installers": installers,
            "ManifestType": "installer",
            "ManifestVersion": "1.6.0"
        }

        # Global scope/type if consistent across installers
        if len(installers) > 0:
            first = installers[0]
            if "InstallerType" in first: # If all have same type, can move to root, but keeping explicit is safer
                 pass

        filename = f"{meta['PackageIdentifier']}.installer.yaml"
        self._dump_yaml(folder / filename, data)

    def _write_locale_manifest(self, folder: Path, meta: dict):
        locale = meta.get("DefaultLocale", "en-US")
        data = {
            "PackageIdentifier": meta["PackageIdentifier"],
            "PackageVersion": meta["PackageVersion"],
            "PackageLocale": locale,
            "Publisher": meta["Publisher"],
            "PublisherUrl": meta.get("PublisherUrl", ""),
            "PublisherSupportUrl": meta.get("PublisherSupportUrl", ""),
            "PrivacyUrl": meta.get("PrivacyUrl", ""),
            "Author": meta.get("Author", meta["Publisher"]),
            "PackageName": meta["PackageName"],
            "PackageUrl": meta.get("PackageUrl", ""),
            "License": meta.get("License", "Proprietary"),
            "LicenseUrl": meta.get("LicenseUrl", ""),
            "Copyright": meta.get("Copyright", ""),
            "CopyrightUrl": meta.get("CopyrightUrl", ""),
            "ShortDescription": meta.get("ShortDescription", meta["PackageName"]),
            "Description": meta.get("Description", meta.get("ShortDescription", "")),
            "Tags": meta.get("Tags", []),
            "ManifestType": "defaultLocale",
            "ManifestVersion": "1.6.0"
        }

        # Remove empty fields to keep it clean
        data = {k: v for k, v in data.items() if v}

        filename = f"{meta['PackageIdentifier']}.locale.{locale}.yaml"
        self._dump_yaml(folder / filename, data)

    def _dump_yaml(self, path: Path, data: dict):
        # Custom dumper to avoid aliases and handle clean formatting
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
