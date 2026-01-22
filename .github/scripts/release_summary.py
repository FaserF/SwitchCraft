import sys

def main():
    if len(sys.argv) < 3:
        print("Usage: python release_summary.py <version> <repo_url>")
        sys.exit(1)

    version = sys.argv[1].lstrip('v')
    repo_url = sys.argv[2].rstrip('/')
    base_url = f"{repo_url}/releases/download/v{version}"

    assets = [
        ("SwitchCraft-windows.exe", "Modern GUI for Windows (64-bit)"),
        ("SwitchCraft-linux", "Modern GUI for Linux"),
        ("SwitchCraft-macos", "Modern GUI for macOS"),
        ("SwitchCraft-Setup.exe", "Windows Installer (Modern)"),
        ("SwitchCraft-Legacy.exe", "Legacy GUI for older Windows"),
        ("SwitchCraft-Legacy-Setup.exe", "Legacy Windows Installer"),
        ("SwitchCraft-CLI-windows.exe", "Command Line Interface (Windows)"),
        ("switchcraft_advanced.zip", "Advanced Addon"),
        ("switchcraft_ai.zip", "AI Addon"),
        ("switchcraft_winget.zip", "WinGet Addon"),
    ]

    # Extract repo owner for Docker image URL
    # repo_url format: https://github.com/FaserF/SwitchCraft
    repo_parts = repo_url.replace("https://github.com/", "").split("/")
    repo_owner = repo_parts[0].lower() if len(repo_parts) > 0 else "faserf"
    repo_name = repo_parts[1].lower() if len(repo_parts) > 1 else "switchcraft"
    docker_image = f"ghcr.io/{repo_owner}/{repo_name}:{version}"

    print("\n## Download Overview\n")
    print("| Asset | Description | Direct Download |")
    print("| :--- | :--- | :--- |")

    for filename, desc in assets:
        download_url = f"{base_url}/{filename}"
        print(f"| `{filename}` | {desc} | [Download]({download_url}) |")

    # Add Docker image entry
    gh_pkg_url = f"https://github.com/{repo_owner}/{repo_name}/pkgs/container/{repo_name}"
    print(f"| 🐳 **Docker Image** | Container for server/headless use (`docker pull {docker_image}`) | [View on GitHub]({gh_pkg_url}) |")


if __name__ == "__main__":
    main()
