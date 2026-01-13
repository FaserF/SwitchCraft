# Frequently Asked Questions

Common questions and answers about SwitchCraft.

## General

### What is SwitchCraft?

SwitchCraft is a comprehensive packaging assistant for IT professionals. It analyzes installers (MSI, EXE) to find silent installation switches, creates Intune packages, and integrates with Winget and Microsoft Graph API.

### Is SwitchCraft free?

Yes! SwitchCraft is open source under the MIT License. You can use it freely in personal and commercial environments.

### Which platforms are supported?

SwitchCraft is primarily designed for **Windows**. While the Modern UI (Flet) can run on macOS and Linux, core features like Intune packaging and Winget require Windows.

| Feature | Windows | macOS/Linux |
|---------|:-------:|:-----------:|
| Modern UI | ✅ | ✅ |
| Installer Analysis | ✅ | ⚠️ Basic |
| Intune Packaging | ✅ | ❌ |
| Winget Store | ✅ | ❌ |

---

## Installation & Setup

### Which edition should I use?

- **Modern** (Flet): Recommended for most users. Latest features, modern UI.
- **Legacy** (Tkinter): For older hardware or if you prefer a traditional interface.
- **CLI**: For automation, scripting, and CI/CD pipelines.

### How do I update SwitchCraft?

- **Installer version**: Check for updates in Settings or download the latest release.
- **Winget**: Run `winget upgrade FaserF.SwitchCraft`
- **Portable**: Download the new version and replace the old executable.

### Why does Windows Defender flag SwitchCraft?

SwitchCraft's analysis features (reading PE headers, spawning processes) can trigger heuristic-based detection. This is a false positive. You can:

1. Add an exclusion for `SwitchCraft.exe`
2. Verify the file hash against the GitHub release
3. Build from source yourself

---

## Analysis & Packaging

### What installer types are supported?

SwitchCraft detects 20+ installer frameworks including:

- MSI (Windows Installer)
- NSIS, Inno Setup, InstallShield
- WiX Burn Bundles
- Vendor-specific (HP, Dell, Lenovo, Intel, NVIDIA)

See [Features](/FEATURES) for the complete list.

### Why can't SwitchCraft find silent switches?

Some installers intentionally disable silent installation. SwitchCraft detects this and shows a warning. Options:

1. Contact the vendor for enterprise deployment options
2. Use a wrapper/transform if supported
3. Consider repackaging with tools like PSADT

### What is "Brute Force" analysis?

When no installer type is detected, SwitchCraft runs the executable with common help arguments (`/?`, `--help`, `-h`, etc.) and analyzes the output for switch patterns.

---

## Intune Integration

### What permissions does the Azure app need?

Minimum required: `DeviceManagementApps.ReadWrite.All`

This allows SwitchCraft to:
- Upload Win32 apps
- Create detection rules
- Assign to groups

### Is the Client Secret stored securely?

Yes. SwitchCraft uses the **Windows Credential Manager** to encrypt and store credentials. They are never stored in plain text or in the Registry.

### Why does Intune upload fail?

Common causes:

1. **Invalid credentials**: Verify Tenant ID, Client ID, and Secret
2. **Expired secret**: Azure app secrets expire. Generate a new one.
3. **Conditional Access**: Ensure the service principal isn't blocked
4. **Network**: Check firewall/proxy settings for Graph API access

---

## Winget

### How do I enable Winget integration?

Go to **Settings > General > Enable Winget Integration**.

### Can I deploy Winget apps to Intune?

Yes! SwitchCraft can generate PowerShell scripts that use Winget on the target device. This provides:

- Always up-to-date installations
- Simplified maintenance
- No need to repackage on each update

---

## Troubleshooting

### SwitchCraft won't start

1. **Check Windows version**: Requires Windows 10 1809+
2. **Install Visual C++ Redistributable**: [Download](https://aka.ms/vs/17/release/vc_redist.x64.exe)
3. **Try portable version**: Isolates the issue from installation problems
4. **Run as Administrator**: Some features require elevation

### Analysis takes too long

- Large files with many nested installers take longer
- Try disabling "Extract and analyze nested files" in Settings
- Ensure 7-Zip is installed for faster extraction

### How do I get logs?

1. Enable **Debug Mode** in Settings > Advanced.
2. Reproduce the issue.
3. Logs are saved to `%APPDATA%\FaserF\SwitchCraft\Logs\` on Windows, or `~/.switchcraft/Logs/` on Linux/macOS.
4. If the app crashes at startup, it automatically generates a **Crash Dump** in the same folder.
5. In the Modern UI crash screen, you can click **"Copy Path"** or **"Open Folder"** to quickly find the log.
6. [Open an issue](https://github.com/FaserF/SwitchCraft/issues) with the log attached.

---

## Data Management

### Where does SwitchCraft store my data?

SwitchCraft is designed to be as clean as possible. It stores data in:
- **Registry**: User settings and preferences.
- **AppData**: History and logs.
- **Keyring**: API keys and secrets (encrypted via system).
- **Home Directory**: Addons and custom extensions.

See the [Installation Guide](/installation#data-storage-locations) for the full list of paths.

### What does "Factory Reset" do?

The Factory Reset option in Settings is a **total wipe** of SwitchCraft data. It will:
1. Delete all Registry keys in `HKCU\Software\FaserF\SwitchCraft`.
2. Purge all secrets and API keys from the system keyring.
3. Delete the history and logs folder.
4. Delete all installed addons.

After a Factory Reset, the next launch will feel like a fresh installation.

---

## Contributing

### How can I contribute?

See the [Building](/building) guide for development setup. We welcome:

- Bug reports and feature requests
- Code contributions via Pull Requests
- Documentation improvements
- Translations

### Where do I report bugs?

Open an issue on [GitHub](https://github.com/FaserF/SwitchCraft/issues). Include:

- SwitchCraft version
- Windows version
- Steps to reproduce
- Relevant logs or screenshots
