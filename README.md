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
- [**✨ Features & Analysis**](docs/FEATURES.md): Detailed breakdown of supported installers and analysis capabilities.
- [**📦 Winget Store & Integration**](docs/WINGET.md): Using the Winget Store and Auto-Update deployment.
- [**☁️ Enterprise & Intune**](docs/INTUNE.md): Guide to Automation, Intune Uploads, Group Assignments, and Script Signing.
- [**Registry Reference**](docs/Registry.md): Configuration via Registry.
- [**GPO / Policies**](docs/PolicyDefinitions/README.md): ADMX Templates.
- [**🔐 Security Guide**](docs/SECURITY.md): Details on Encryption, ASR, and Safe Usage.

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

### CLI Mode
```bash
# Basic analysis
switchcraft analyze setup.exe

# JSON output for scripting
switchcraft analyze setup.exe --json
```

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
