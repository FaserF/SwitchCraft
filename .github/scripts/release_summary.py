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
    ]

    print("\n## Download Overview\n")
    print("| Asset | Description | Direct Download |")
    print("| :--- | :--- | :--- |")

    for filename, desc in assets:
        download_url = f"{base_url}/{filename}"
        print(f"| `{filename}` | {desc} | [Download]({download_url}) |")

if __name__ == "__main__":
    main()
