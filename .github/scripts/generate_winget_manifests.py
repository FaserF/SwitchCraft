import argparse
import hashlib
import requests

# Usage: python generate_winget_manifests.py --version 1.2.3

# --- Templates ---

TEMPLATE_VERSION = """# Created using SwitchCraft CI
# yaml-language-server: $schema=https://aka.ms/winget-manifest.version.1.10.0.schema.json

PackageIdentifier: {package_id}
PackageVersion: {version}
DefaultLocale: en-US
ManifestType: version
ManifestVersion: 1.10.0
"""

TEMPLATE_INSTALLER_GUI = """# Created using SwitchCraft CI
# yaml-language-server: $schema=https://aka.ms/winget-manifest.installer.1.10.0.schema.json

PackageIdentifier: {package_id}
PackageVersion: {version}
InstallModes:
  - silent
  - silentWithProgress
UpgradeBehavior: install
Installers:
  - Architecture: x64
    Scope: machine
    InstallerType: inno
    InstallerUrl: {installer_url}
    InstallerSha256: {installer_sha256}
    InstallerSwitches:
      Silent: /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
      SilentWithProgress: /SILENT /SUPPRESSMSGBOXES /NORESTART
      InstallLocation: /DIR="<INSTALLPATH>"
      Log: /LOG="<LOGPATH>"
  - Architecture: x64
    Scope: user
    InstallerType: inno
    InstallerUrl: {installer_url}
    InstallerSha256: {installer_sha256}
    InstallerSwitches:
      Silent: /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
      SilentWithProgress: /SILENT /SUPPRESSMSGBOXES /NORESTART
      InstallLocation: /DIR="<INSTALLPATH>"
      Log: /LOG="<LOGPATH>"
  - Architecture: x64
    InstallerType: portable
    InstallerUrl: {portable_url}
    InstallerSha256: {portable_hash}
    Commands:
      - switchcraft
ManifestType: installer
ManifestVersion: 1.10.0
"""

TEMPLATE_LOCALE_GUI = """# Created using SwitchCraft CI
# yaml-language-server: $schema=https://aka.ms/winget-manifest.defaultLocale.1.10.0.schema.json

PackageIdentifier: {package_id}
PackageVersion: {version}
PackageLocale: en-US
Publisher: FaserF
PublisherUrl: https://github.com/FaserF
PublisherSupportUrl: https://github.com/FaserF/SwitchCraft/issues
PrivacyUrl: https://github.com/FaserF/SwitchCraft
Author: FaserF
PackageName: SwitchCraft
PackageUrl: https://github.com/FaserF/SwitchCraft
License: MIT License
AppsAndFeaturesEntries:
  - DisplayName: SwitchCraft
    Publisher: FaserF
LicenseUrl: https://github.com/FaserF/SwitchCraft/blob/main/LICENSE
Copyright: Copyright (c) 2025 FaserF
CopyrightUrl: https://github.com/FaserF/SwitchCraft/blob/main/LICENSE
ShortDescription: Silent Install Switch Finder & Packaging Assistant
Description: |
  SwitchCraft is your comprehensive packaging assistant for IT Professionals. It goes beyond simple switch identification to streamline your entire application packaging workflow.
  Features:
  - Universal Analysis: Instantly identify silent switches for EXE, MSI, and obscure installer frameworks.
  - AI-Powered Helper: Get context-aware packaging advice and troubleshooting.
  - Intune Ready: Generate standardized PowerShell installation scripts automatically.
  - Cross-Platform: Manage installers for Windows, Linux, and macOS.
  - Winget Integration: Fast package detection.
Moniker: switchcraft
Tags:
  - installer
  - analysis
  - silent-install
  - packaging
  - intune
  - msi
  - exe
  - deployment
  - automation
ReleaseNotes: "v{version} Release"
ReleaseNotesUrl: https://github.com/FaserF/SwitchCraft/releases/tag/v{version}
ManifestType: defaultLocale
ManifestVersion: 1.10.0
"""

TEMPLATE_INSTALLER_CLI = """# Created using SwitchCraft CI
# yaml-language-server: $schema=https://aka.ms/winget-manifest.installer.1.10.0.schema.json

PackageIdentifier: {package_id}
PackageVersion: {version}
InstallModes:
  - silent
UpgradeBehavior: install
Installers:
  - Architecture: x64
    InstallerType: portable
    InstallerUrl: {installer_url}
    InstallerSha256: {installer_sha256}
    Commands:
      - switchcraft-cli
ManifestType: installer
ManifestVersion: 1.10.0
"""

TEMPLATE_LOCALE_CLI = """# Created using SwitchCraft CI
# yaml-language-server: $schema=https://aka.ms/winget-manifest.defaultLocale.1.10.0.schema.json

PackageIdentifier: {package_id}
PackageVersion: {version}
PackageLocale: en-US
Publisher: FaserF
PublisherUrl: https://github.com/FaserF
PublisherSupportUrl: https://github.com/FaserF/SwitchCraft/issues
PrivacyUrl: https://github.com/FaserF/SwitchCraft
Author: FaserF
PackageName: SwitchCraft CLI
PackageUrl: https://github.com/FaserF/SwitchCraft
License: MIT License
LicenseUrl: https://github.com/FaserF/SwitchCraft/blob/main/LICENSE
Copyright: Copyright (c) 2025 FaserF
CopyrightUrl: https://github.com/FaserF/SwitchCraft/blob/main/LICENSE
ShortDescription: Command-line interface for SwitchCraft automation tools
Description: |
  The Command-Line Interface (CLI) for SwitchCraft.
  Allows headless analysis of installers, generation of database records, and integration into CI/CD pipelines.
Moniker: switchcraft-cli
Tags:
  - cli
  - automation
  - intune
  - packaging
  - headless
ReleaseNotes: "v{version} Release"
ReleaseNotesUrl: https://github.com/FaserF/SwitchCraft/releases/tag/v{version}
ManifestType: defaultLocale
ManifestVersion: 1.10.0
"""

def computed_sha256(url):
    print(f"Downloading {url} for hashing...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        sha256_hash = hashlib.sha256()
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate Winget Manifests")
    parser.add_argument("--version", required=True, help="Release version (e.g., 2025.12.12.0)")
    args = parser.parse_args()
    version = args.version

    # Base URL construction
    # IMPORTANT: The tag might be v1.2.3, so URL is .../tags/v1.2.3/...
    # But usually releases/download/v1.2.3/file.ext
    base_url = f"https://github.com/FaserF/SwitchCraft/releases/download/v{version}"

    # === GUI Package ===
    gui_id = "FaserF.SwitchCraft"

    print(f"\nProcessing {gui_id}...")
    setup_url = f"{base_url}/SwitchCraft-Setup.exe"
    portable_url = f"{base_url}/SwitchCraft-windows.exe"

    setup_hash = computed_sha256(setup_url)
    portable_hash = computed_sha256(portable_url)

    if setup_hash and portable_hash:
        # Version
        print(f"\n### {gui_id}.yaml")
        print("```yaml")
        print(TEMPLATE_VERSION.format(package_id=gui_id, version=version))
        print("```")

        # Installer
        print(f"\n### {gui_id}.installer.yaml")
        print("```yaml")
        print(TEMPLATE_INSTALLER_GUI.format(
            package_id=gui_id,
            version=version,
            installer_url=setup_url,
            installer_sha256=setup_hash,
            portable_url=portable_url,
            portable_hash=portable_hash
        ))
        print("```")

        # Locale
        print(f"\n### {gui_id}.locale.en-US.yaml")
        print("```yaml")
        print(TEMPLATE_LOCALE_GUI.format(package_id=gui_id, version=version))
        print("```")
    else:
        print("Failed to calculate hashes for GUI package.")

    # === CLI Package ===
    cli_id = "FaserF.SwitchCraft.CLI"
    print(f"\nProcessing {cli_id}...")

    cli_url = f"{base_url}/SwitchCraft-CLI-windows.exe"
    cli_hash = computed_sha256(cli_url)

    if cli_hash:
        # Version
        print(f"\n### {cli_id}.yaml")
        print("```yaml")
        print(TEMPLATE_VERSION.format(package_id=cli_id, version=version))
        print("```")

        # Installer
        print(f"\n### {cli_id}.installer.yaml")
        print("```yaml")
        print(TEMPLATE_INSTALLER_CLI.format(
            package_id=cli_id,
            version=version,
            installer_url=cli_url,
            installer_sha256=cli_hash
        ))
        print("```")

        # Locale
        print(f"\n### {cli_id}.locale.en-US.yaml")
        print("```yaml")
        print(TEMPLATE_LOCALE_CLI.format(package_id=cli_id, version=version))
        print("```")
    else:
        print("Failed to calculate has for CLI package.")

if __name__ == "__main__":
    main()
