# SwitchCraft 🧙‍♂️

<img src="images/switchcraft_logo_with_Text.png" width="200" alt="SwitchCraft Logo">

[![GitHub all releases](https://img.shields.io/github/downloads/FaserF/SwitchCraft/total?color=blue&style=flat-square&logo=github&label=Downloads)](https://github.com/FaserF/SwitchCraft/releases)

**SwitchCraft is your comprehensive packaging assistant for IT Professionals. It goes beyond simple switch identification to streamline your entire application packaging workflow.**

<div align="center">
  <img src="images/switchcraft_ui.png" alt="SwitchCraft UI" width="1000" />
</div>

> [!NOTE]
> **Active development is for Windows only.** Linux and macOS builds are untested but available. Bug reports for other platforms are welcome!

## 📚 Documentation
## 📚 Documentation
- [**✨ Features & Analysis**](docs/FEATURES.md): Detailed breakdown of supported installers and analysis capabilities.
- [**🤖 CLI Reference**](docs/CLI_Reference.md): Command-line usage, JSON output, and headless operation.
- [**🏗️ CI Architecture**](docs/CI_Architecture.md): Build process, pip structure, and testing guide.
- [**📦 Winget Store & Integration**](docs/WINGET.md): Using the Winget Store and Auto-Update deployment.
- [**☁️ Enterprise & Intune**](docs/INTUNE.md): Guide to Automation, Intune Uploads, Group Assignments, and Script Signing.
- [**Registry Reference**](docs/Registry.md): Configuration via Registry.
- [**GPO / Policies**](docs/PolicyDefinitions/README.md): ADMX Templates.
- [**🔐 Security Guide**](docs/SECURITY.md): Details on Encryption, ASR, and Safe Usage.

## 🧩 Addons & Extensions

SwitchCraft uses a modular addon system for advanced features like **Intune Integration** and **AI Analysis**. This ensures the core tool remains lightweight and less prone to false-positive antivirus detections.

- **Automatic Install**: The app will prompt you to download missing features when needed.
- **Manual Install**: You can upload custom addons in Settings.
- 👉 [**Read the Addon Guide**](docs/ADDONS.md) for more details.

## 🚀 Installation


### Pre-built Binaries
Download from the [Releases](https://github.com/FaserF/SwitchCraft/releases) page:

#### Windows Installer (Recommended)
- **`SwitchCraft-Setup.exe`** – Full installer with Start Menu, Desktop shortcuts.
  - **User Scope**: Installs to `%LOCALAPPDATA%` (Default).
  - **Machine Scope**: Run as Admin to install to `%PROGRAMFILES%`.
  - **Silent Install**: `SwitchCraft-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`

#### Portable Executables
- **Windows**: `SwitchCraft-windows.exe` (No Install required)

### Install via Winget
```powershell
winget install FaserF.SwitchCraft
```

### CLI "One-Liner" (PowerShell)
```powershell
iex (irm https://raw.githubusercontent.com/FaserF/SwitchCraft/main/install.ps1)
```

## 💻 Usage

### GUI Mode
Simply run the application without arguments:
```bash
switchcraft
```
Then **Drag & Drop** your installer into the window or click to browse.

### Global CLI Flags
- **`--json`**: Output analysis results in JSON format.
- **`--install-addons=<list>`**: Install specific addons (e.g., `ai,winget` or `all`).
- **`--debug`**: Enable the debug console on startup (if addon is installed).

## 🧩 Addon System (Modular Features)

SwitchCraft now supports a modular addon system to keep the core application lightweight and minimize antivirus false positives.

- **Advanced Analysis & Intune**: Deep inspection of wrappers and direct Intune publication.
- **Winget Store Integration**: Search and deploy from the official Microsoft repository.
- **AI Helper**: Dynamic chat assistant for packaging guidance (Requires Gemini/OpenAI API Key).
- **Debug Console**: Real-time logging console for troubleshooting.

Manage addons via **Settings > Addon Manager** or CLI:
```bash
# Install all recommended addons
switchcraft --install-addons=advanced,winget
```

## ✨ Recently Added Features
- **Batch Processing**: Drag & Drop multiple files to analyze them sequentially.
- **Analysis History**: Keep track of your last 100 analyzed installers.
- **Winget Toggle**: Easily enable/disable store integration to suit your workflow.
- **Enhanced AI**: Support for local AI, Gemini (Free tier), and OpenAI.

## 🛠️ Building from Source
SwitchCraft includes helper scripts to easily build release executables for your platform.

### Windows
Run the PowerShell script to install dependencies and build the EXE:
```powershell
.\scripts\build_release.ps1
```
The executable will be placed in your `Downloads` folder.

### Linux / macOS
Run the shell script:
```bash
./scripts/build_release.sh
```
The binary will be placed in your `Downloads` folder.

## 🤝 Contributing
Open Source under the **MIT License**. PRs are welcome!

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📜 License
MIT © 2025 FaserF

## 🔗 Links
- [GitHub Repository](https://github.com/FaserF/SwitchCraft)
- [Release Downloads](https://github.com/FaserF/SwitchCraft/releases)
- [Silent Install Database](https://silent.ls/)
