# SwitchCraft CLI Reference

SwitchCraft can be used as a headless command-line tool, ideal for automation scripts and AI-driven debugging pipelines.

## Installation from Source

For a lightweight, CLI-only installation (excludes GUI dependencies like Tkinter/CustomTkinter):
```bash
pip install .
```

For the full experience including the GUI:
```bash
pip install .[gui]
```

## Usage

### Basic Analysis
Analyze an installer to detect silent switches, type, and detailed metadata.

```bash
switchcraft path/to/installer.exe
```

### JSON Output (Machine Readable)
Best for CI pipelines or AI Agents.
```bash
switchcraft path/to/installer.exe --json
```

**Example Output:**
```json
{
  "file_path": "C:\\Installers\\setup.exe",
  "installer_type": "Inno Setup",
  "product_name": "Example App",
  "product_version": "1.0.0",
  "confidence": 1.0,
  "install_switches": ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
  "uninstall_switches": ["/SILENT"],
  "winget_url": "https://config.winget.com/manifests/e/Example/App/1.0.0.yaml"
}
```

### Help
```bash
switchcraft --help
```

## Entry Points
- **`switchcraft`**: Main entry point. Attempts to load CLI first if arguments are present. If no arguments, tries to launch GUI.
- **`src/switchcraft/cli_main.py`**: Strict CLI-only entry point. Does not import any GUI libraries. Safe for headless servers.
