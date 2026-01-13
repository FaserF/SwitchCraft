# Installation

Get SwitchCraft up and running in minutes.

## Recommended: Windows Package Manager (winget)

The easiest way to install SwitchCraft on Windows:

```powershell
winget install FaserF.SwitchCraft
```

This installs the **Modern** edition with automatic updates.

## Manual Download

Download the latest release from [GitHub Releases](https://github.com/FaserF/SwitchCraft/releases/latest).

### Available Editions

| Edition | Download | Best For |
|---------|----------|----------|
| **Modern** (Flet) | [Setup](https://github.com/FaserF/SwitchCraft/releases/latest) / [Portable](https://github.com/FaserF/SwitchCraft/releases/latest) | Most users - Latest features, modern UI |
| **Legacy** (Tkinter) | [Setup](https://github.com/FaserF/SwitchCraft/releases/latest) / [Portable](https://github.com/FaserF/SwitchCraft/releases/latest) | Old hardware - Lightweight, classic stability |
| **CLI** | [Download](https://github.com/FaserF/SwitchCraft/releases/latest) | Automation - Headless, scriptable |

### File Guide

| Filename | Type | Description |
|----------|------|-------------|
| `SwitchCraft-Setup.exe` | Installer | Modern edition with auto-updates |
| `SwitchCraft-windows.exe` | Portable | Modern edition, no installation needed |
| `SwitchCraft-Legacy-Setup.exe` | Installer | Legacy edition |
| `SwitchCraft-Legacy.exe` | Portable | Legacy edition |
| `SwitchCraft-CLI-windows.exe` | CLI | Command-line tool |

## System Requirements

| Requirement | Minimum |
|-------------|---------|
| **OS** | Windows 10 (Build 1809+) or Windows 11 |
| **Architecture** | x64 |
| **RAM** | 4 GB |
| **Disk** | ~150 MB |

### Optional Dependencies

- **7-Zip**: Required for nested installer extraction. [Download](https://7-zip.org)
- **IntuneWinAppUtil**: Auto-downloaded when needed for Intune packaging.

## Portable vs Installer

### Installer (`Setup.exe`)
- ✅ Start menu shortcuts
- ✅ Automatic updates
- ✅ File associations
- ❌ Requires admin rights

### Portable (`.exe`)
- ✅ No installation required
- ✅ Run from USB drive
- ✅ Use in Windows Sandbox
- ❌ No auto-updates

## First Launch

1. **Accept Firewall Prompt** (if shown) - Required for local UI server
2. **Configure Settings** - Set your preferred theme, language, and Intune credentials
3. **Install Addons** - Enable advanced features like AI assistance or Intune integration

> [!TIP]
> Run SwitchCraft as Administrator to enable local installation testing features.

---

## Data Storage Locations

SwitchCraft stores configuration and user data in the following locations.

### Windows

| Type | Location |
| :--- | :--- |
| **User Preferences** | `HKCU\Software\FaserF\SwitchCraft` |
| **GPO/Intune Policies** | `HKCU\Software\Policies\FaserF\SwitchCraft` |
| **Analysis History** | `%APPDATA%\FaserF\SwitchCraft\history.json` |
| **Logs / Crash Dumps** | `%APPDATA%\FaserF\SwitchCraft\Logs\` |
| **Addons** | `%USERPROFILE%\.switchcraft\addons\` |
| **Secrets (API Keys)** | Windows Credential Manager (under "SwitchCraft") |

### Linux / macOS

| Type | Location |
| :--- | :--- |
| **Addons** | `~/.switchcraft/addons/` |
| **Logs** | `~/.switchcraft/Logs/` |
| **Secrets** | System Keyring (libsecret/Keychain) |
