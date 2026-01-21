# SwitchCraft 🧙‍♂️

<img src="https://github.com/FaserF/SwitchCraft/raw/main/docs/public/screenshots/switchcraft_logo_with_Text.png" width="200" alt="SwitchCraft Logo">

[![GitHub all releases](https://img.shields.io/github/downloads/FaserF/SwitchCraft/total?color=blue&style=flat-square&logo=github&label=Downloads)](https://github.com/FaserF/SwitchCraft/releases)

**SwitchCraft is your comprehensive packaging assistant for IT Professionals. It goes beyond simple switch identification to streamline your entire application packaging workflow.**

<details>
<summary><b>📸 Click to view main UI screenshot</b></summary>

<div align="center">
  <img src="https://github.com/FaserF/SwitchCraft/raw/main/docs/public/screenshots/switchcraft_ui.png" alt="SwitchCraft UI" width="1000" />
</div>

</details>

<details>
<summary><b>📸 Click to view additional screenshots</b></summary>

<div align="center">
  <table>
    <tr>
      <td><img src="https://github.com/FaserF/SwitchCraft/raw/main/docs/public/screenshots/switchcraft_ui_2.png" alt="SwitchCraft Screenshot 2" width="500" /></td>
      <td><img src="https://github.com/FaserF/SwitchCraft/raw/main/docs/public/screenshots/switchcraft_ui_3.png" alt="SwitchCraft Screenshot 3" width="500" /></td>
    </tr>
    <tr>
      <td><img src="https://github.com/FaserF/SwitchCraft/raw/main/docs/public/screenshots/switchcraft_ui_4.png" alt="SwitchCraft Screenshot 4" width="500" /></td>
      <td><img src="https://github.com/FaserF/SwitchCraft/raw/main/docs/public/screenshots/switchcraft_ui_5.png" alt="SwitchCraft Screenshot 5" width="500" /></td>
    </tr>
  </table>
</div>

</details>

## ⚠️ Platform Support & Limitations

SwitchCraft is primarily designed for **Windows** environments. While the application UI is built with cross-platform frameworks (Python/Flet), many core features rely on Windows-specific APIs (Registry, Explorer, Intune Packaging Tool).

| Feature | Windows | macOS / Linux | Web (WASM) | Reason / Limitation |
| :--- | :---: | :---: | :---: | :--- |
| **Modern UI** | ✅ | ✅ | ✅ | Runs natively via Flet (Flutter). |
| **Intune Packaging** | ✅ | ❌ | ❌ | Requires `IntuneWinAppUtil.exe` (Windows binary). |
| **Configuration** | ✅ | ⚠️ | ⚠️ | Registry (Windows) vs Browser Storage (Web). |
| **Winget Store** | ✅ | ❌ | ⚠️ | Windows uses CLI. Web uses API-only search (No Install). |
| **System Integration** | ✅ | ⚠️ | ❌ | Explorer/Notifications are OS-specific. |
| **Analyze Installer** | ✅ | ✅ | ✅ | Basic file analysis works everywhere. |

> [!WARNING]
> **macOS and Linux users:** You can run the application to view the interface or analyze simple files, but you **cannot** create Intune packages or use Store features. These builds are essentially "Viewers" and are not actively supported.

## 🚀 Key Features

### 🔍 Analysis & Packaging
- **Smart Installer Analysis**: Deep inspection of MSI, EXE (Inno Setup, NSIS, InstallShield), and custom wrappers.
- **Intune Integration**: Automated creation of `.intunewin` packages and direct publication to Microsoft Intune.
- **Exchange Online Mail Flow**: Visualize and test your Exchange Online mail flow directly from the dashboard. Track sent/received items and verify service health.
- **Intune Store Browser**: Browse and manage your Intune applications with logo display and detailed metadata.
- **Advanced Wrapper Support**: Identification of nested installers and extraction of silent switches.
- **Batch Processing**: Drag & Drop multiple files to analyze them sequentially.
- **Analysis History**: Keep track of your last 100 analyzed installers.
- **My Library**: Personal collection of analyzed and packaged applications with search and filter capabilities.
- **Community Database**: Integrated lookup for known silent switches when local analysis fails.
- **Project Stacks**: Group applications into named stacks for one-click batch deployment via Stack Manager.
- **Interactive Dashboard**: Visual overview of your packaging activity, statistics, and recent actions.
- **Script Signing**: Automatically sign generated PowerShell scripts with your Code Signing Certificate.
- **Packaging Wizard**: End-to-End workflow from installer to Intune upload in 5 steps.
- **Live Detection Tester**: Verify intended Registry, File, or MSI detection rules locally before uploading.
- **Group Manager**: Comprehensive Entra ID (Azure AD) group management - create, delete, and manage group members with user search.
- **Script Upload**: Upload and manage PowerShell scripts for Intune deployment.

### 📦 Store & Deployment
- **Winget Store Integration**: Search, analyze, and deploy applications from the official Microsoft repository.
- **WingetCreate Manager**: Create and manage Winget manifests for publishing packages to the Microsoft repository.
- **Auto-Update Support**: Built-in logic to handle application updates in enterprise environments.
- **Portable & Setup Variants**: Choose between full installation or zero-residue portable executables.
- **Winget Toggle**: Easily enable/disable store integration to suit your workflow.
- **macOS Packaging Wizard**: Create install.sh scripts and DMG/PKG packages for macOS deployment.

### 🛠️ Enterprise & Automation
- **Enterprise Configuration**: Full support for Registry-based configuration via GPO or Intune OMA-URI.
- **CLI Mode**: Headless operation for CI/CD pipelines and automation scripts with JSON output.
- **Cloud Sync**: Sync your configuration and settings across devices using GitHub Gists.
- **Modular Addon System**: Extend functionality with optional components like AI analysis, Advanced analyzers, or Winget integration.
- **Notification System**: Desktop notifications and in-app notification center for important events.
- **Multi-Language Support**: Full English and German (Du-Form) interface with easy language switching.

### 🤖 AI Assistance
- **Enhanced AI Helper**: Dynamic chat assistant for packaging guidance supporting Local AI, Gemini, and OpenAI.
- **Context-Aware Responses**: AI understands your current installer context and provides relevant suggestions.
- **Copy-to-Clipboard**: Easily copy AI responses and code snippets from the chat interface.

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
| **Web / Docker** | **Flet (WASM)** | ✅ Active | **Zero-Install** - Demo or Self-Hosted. |
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

## 🔧 Troubleshooting

### Crash Dumps & Logs
If SwitchCraft encounters a startup error, it automatically saves a crash dump with detailed information.

| Platform | Location |
| :--- | :--- |
| **Windows** | `%APPDATA%\FaserF\SwitchCraft\Logs\crash_dump_<timestamp>.txt` |
| **Linux/macOS** | `~/.switchcraft/Logs/crash_dump_<timestamp>.txt` |

When reporting issues, please attach the crash dump file to help with debugging.

---

## 📂 Data Storage Locations

SwitchCraft stores data in the following locations. This is useful for backup, cleanup, or troubleshooting.

### Windows

| Type | Location | Description |
| :--- | :--- | :--- |
| **User Preferences** | `HKCU\Software\FaserF\SwitchCraft` | Theme, language, settings (Registry) |
| **Machine Preferences** | `HKLM\Software\FaserF\SwitchCraft` | Admin-configured defaults (Registry) |
| **GPO/Intune Policies** | `HKCU\Software\Policies\FaserF\SwitchCraft` | Enforced user policies (Registry) |
| **Machine Policies** | `HKLM\Software\Policies\FaserF\SwitchCraft` | Enforced machine policies (Registry) |
| **Analysis History** | `%APPDATA%\FaserF\SwitchCraft\history.json` | Last 100 analyzed files |
| **Crash Dumps** | `%APPDATA%\FaserF\SwitchCraft\Logs\*.txt` | Error diagnostics |
| **Addons** | `%USERPROFILE%\.switchcraft\addons\` | Installed addon extensions |
| **Secrets (API Keys)** | Windows Credential Manager | Stored under "SwitchCraft" (secure keyring) |
| **IntuneWinAppUtil** | App working directory or configured path | Downloaded on first Intune package creation |

### Linux / macOS

| Type | Location | Description |
| :--- | :--- | :--- |
| **Addons** | `~/.switchcraft/addons/` | Installed addon extensions |
| **Logs** | `~/.switchcraft/Logs/` | Crash dumps and diagnostics |
| **Secrets** | System Keyring (libsecret/Keychain) | API keys stored securely |

### Factory Reset
To completely remove all SwitchCraft data, use **Settings → Factory Reset** which:
1. Deletes the Registry key at `HKCU\Software\FaserF\SwitchCraft`.
2. Removes all secrets from the system keyring.
3. Deletes the data folder at `%APPDATA%\FaserF\SwitchCraft` (Logs, History, Cache).
4. Deletes the addons folder at `%USERPROFILE%\.switchcraft`.

When reporting issues, please attach the crash dump file to help with debugging.

## 📚 Documentation

Full documentation is available at [SwitchCraft Docs](https://faserf.github.io/SwitchCraft/).

Key topics:
- [Installation Guide](/docs/installation.md)
- [Feature Overview](/docs/FEATURES.md)
- [Intune Integration](/docs/INTUNE.md)
- [Winget Integration](/docs/WINGET.md)
- [Addon System](/docs/ADDONS.md)
- [CLI Reference](/docs/CLI_Reference.md)
- [FAQ](/docs/faq.md)

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


## 🌐 Web Demo

Try the **SwitchCraft Web Demo** directly in your browser without installation:

[**👉 Launch Web Demo**](https://faserf.github.io/SwitchCraft/demo/)

### ⚠️ Limitations (Web Demo)
The Web Demo runs entirely in your browser via Pyodide (WASM). Due to browser security sandboxing:
- **No System Access**: Cannot access your local file system, Registry, or PowerShell.
- **UI Preview Only**: Designed to demonstrate the user interface and basic logic.
- **No Intune/Winget**: Enterprise management features are disabled.

For full functionality, please download the Windows desktop application.

### Docker (Self-Hosted)
For a private web instance with backend capabilities, use Docker:

1. **Build the Image**:
   ```powershell
   .\scripts\build_web.ps1
   ```

2. **Run the Container**:
   ```bash
   docker run -d -p 8080:8080 --name switchcraft-web switchcraft-web
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
