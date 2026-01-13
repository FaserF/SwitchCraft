# SwitchCraft 🧙‍♂️

<img src="images/switchcraft_logo_with_Text.png" width="200" alt="SwitchCraft Logo">

[![GitHub all releases](https://img.shields.io/github/downloads/FaserF/SwitchCraft/total?color=blue&style=flat-square&logo=github&label=Downloads)](https://github.com/FaserF/SwitchCraft/releases)

**SwitchCraft is your comprehensive packaging assistant for IT Professionals. It goes beyond simple switch identification to streamline your entire application packaging workflow.**

<div align="center">
  <img src="images/switchcraft_ui.png" alt="SwitchCraft UI" width="1000" />
</div>

## ⚠️ Platform Support & Limitations

SwitchCraft is primarily designed for **Windows** environments. While the application UI is built with cross-platform frameworks (Python/Flet), many core features rely on Windows-specific APIs (Registry, Explorer, Intune Packaging Tool).

| Feature | Windows | macOS / Linux | Reason / Limitation |
| :--- | :---: | :---: | :--- |
| **Modern UI** | ✅ | ✅ | Runs natively via Flet (Flutter). |
| **Intune Packaging** | ✅ | ❌ | Requires `IntuneWinAppUtil.exe` (Windows binary). |
| **Configuration** | ✅ | ⚠️ | Full support via Registry (GPO/Intune). No local config file support yet. |
| **Winget Store** | ✅ | ❌ | Requires `winget` CLI (Windows native). |
| **System Integration** | ✅ | ⚠️ | Explorer integration, Notifications, and PowerShell features are Windows-only. |
| **Analyze Installer** | ✅ | ✅ | Basic file analysis works, but advanced PE analysis is Windows-native. |

> [!WARNING]
> **macOS and Linux users:** You can run the application to view the interface or analyze simple files, but you **cannot** create Intune packages or use Store features. These builds are essentially "Viewers" and are not actively supported.

## 🚀 Key Features

### 🔍 Analysis & Packaging
- **Smart Installer Analysis**: Deep inspection of MSI, EXE (Inno Setup, NSIS, InstallShield), and custom wrappers.
- **Intune Integration**: Automated creation of `.intunewin` packages and direct publication to Microsoft Intune.
- **Advanced Wrapper Support**: Identification of nested installers and extraction of silent switches.
- **Batch Processing**: Drag & Drop multiple files to analyze them sequentially.
- **Analysis History**: Keep track of your last 100 analyzed installers.
- **Community Database**: Integrated lookup for known silent switches when local analysis fails.
- **Project Stacks**: Group applications into named stacks for one-click batch deployment.
- **Interactive Dashboard**: Visual overview of your packaging activity, statistics, and recent actions.
- **Script Signing**: Automatically sign generated PowerShell scripts with your Code Signing Certificate.
- **Packaging Wizard**: End-to-End workflow from installer to Intune upload in 5 steps.
- **Live Detection Tester**: Verify intended Registry, File, or MSI detection rules locally before uploading.

### 📦 Store & Deployment
- **Winget Store Integration**: Search, analyze, and deploy applications from the official Microsoft repository.
- **Auto-Update Support**: Built-in logic to handle application updates in enterprise environments.
- **Portable & Setup Variants**: Choose between full installation or zero-residue portable executables.
- **Winget Toggle**: Easily enable/disable store integration to suit your workflow.

### 🛠️ Enterprise & Automation
- **Enterprise Configuration**: Full support for Registry-based configuration via GPO or Intune OMA-URI.
- **CLI Mode**: Headless operation for CI/CD pipelines and automation scripts with JSON output.
- **Cloud Sync**: Sync your configuration and settings across devices using GitHub Gists.
- **Modular Addon System**: Extend functionality with optional components like AI analysis or Intune integration.

### 🤖 AI Assistance
- **Enhanced AI Helper**: Dynamic chat assistant for packaging guidance supporting Local AI, Gemini, and OpenAI.

---

 ## 🤝 Contributing to the Community Database

 SwitchCraft maintains a crowdsourced database of silent switches to help everyone package apps faster.

 **How to contribute:**
 1. Go to the [Issues](https://github.com/FaserF/SwitchCraft/issues) tab.
 2. Click **New Issue**.
 3. Select **"Suggest a New Switch"**.
 4. Fill out the form with the App Name, Version, and Silent Switch.

 Once submitted, our automated system will validate the switch and create a Pull Request to merge it into the main database! 🚀

 ---

 ## 📦 Release Artifacts & Variants

SwitchCraft provides multiple editions to suit different environments.

### 🎨 Editions Overview

| Edition | UI Technology | Status | Best For |
| :--- | :--- | :--- | :--- |
| **Modern** | **Flet (Flutter)** | ✅ Active | **Most Users** - Latest features, modern UI. |
| **Legacy** | **Tkinter** | ⚠️ Maintenance | **Old Hardware** - Lightweight, classic stability. |
| **CLI** | **Terminal** | ✅ Active | **Automation** - Headless, scriptable, JSON output. |

### 📂 File Guide (Downloads)

| Filename | Type | Description | Pros / Cons |
| :--- | :--- | :--- | :--- |
| `SwitchCraft-Setup.exe` | **Installer** | Installs **Modern** edition. | ✅ Auto-Updates, Shortcuts / ❌ Requires Install |
| `SwitchCraft-windows.exe` | **Portable** | Standalone **Modern** edition. | ✅ No Install, Portable / ❌ No Auto-Update |
| `SwitchCraft-Legacy-Setup.exe` | **Installer** | Installs **Legacy** edition. | ✅ Classic Stability / ❌ Old UI |
| `SwitchCraft-Legacy.exe` | **Portable** | Standalone **Legacy** edition. | ✅ Ultra-lightweight / ❌ Old UI |
| `SwitchCraft-CLI-windows.exe` | **CLI** | Command-line tool. | ✅ Fast, Scriptable / ❌ No GUI |
| `SwitchCraft-linux` | **Binary** | Portable for **Linux**. | ⚠️ UI Only, no Intune support |
| `SwitchCraft-macos` | **Binary** | Portable for **macOS**. | ⚠️ UI Only, no Intune support |

> [!NOTE]
> **Intune & Winget Support** requires Windows. The Linux and macOS builds are primarily for viewing or platform-agnostic analysis.

---

## 📚 Documentation

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
