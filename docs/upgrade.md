# Upgrade Guide

This guide explains how to upgrade SwitchCraft to the latest version.

## Automatic Updates

### Installer Version (Setup.exe)

If you installed SwitchCraft using the **Setup.exe** installer, automatic updates are enabled by default:

1. Open **Settings** → **Updates** tab
2. Click **"Check for Updates"**
3. If an update is available, you'll see a notification with release notes
4. Click **"Download & Install"** to upgrade automatically

The installer version checks for updates on startup and can notify you when new versions are available.

### Update Channels

SwitchCraft supports multiple update channels:

- **Stable** (default): Production-ready releases
- **Beta**: Pre-release versions with new features
- **Dev**: Latest development builds (unstable)

You can change the update channel in **Settings** → **Updates**.

## Manual Upgrade Methods

### Windows Package Manager (winget)

If you installed SwitchCraft via winget, upgrade using:

```powershell
winget upgrade FaserF.SwitchCraft
```

To upgrade to a specific channel:

```powershell
# Stable (default)
winget upgrade FaserF.SwitchCraft --source winget

# Check for updates
winget upgrade FaserF.SwitchCraft --include-unknown
```

### Portable Version

For portable installations:

1. **Backup your configuration** (optional but recommended):
   - Settings are stored in `%APPDATA%\SwitchCraft\` or `%LOCALAPPDATA%\SwitchCraft\`
   - Export any custom configurations if needed

2. **Download the latest release**:
   - Visit [GitHub Releases](https://github.com/FaserF/SwitchCraft/releases/latest)
   - Download the appropriate portable executable:
     - `SwitchCraft-windows.exe` (Modern edition)
     - `SwitchCraft-Legacy.exe` (Legacy edition)
     - `SwitchCraft-CLI-windows.exe` (CLI edition)

3. **Replace the old executable**:
   - Close SwitchCraft if it's running
   - Replace the old `.exe` file with the new one
   - Keep the same filename if you have shortcuts configured

4. **Launch the new version**:
   - Your settings and configuration will be preserved automatically

### Installer Version (Manual)

If automatic updates are disabled or fail:

1. **Download the latest installer**:
   - Visit [GitHub Releases](https://github.com/FaserF/SwitchCraft/releases/latest)
   - Download `SwitchCraft-Setup.exe` (Modern) or `SwitchCraft-Legacy-Setup.exe` (Legacy)

2. **Run the installer**:
   - The installer will detect your existing installation
   - Choose to upgrade/repair the existing installation
   - Your settings and data will be preserved

## Upgrade Considerations

### Addon Compatibility

After upgrading, SwitchCraft will attempt to automatically update addons:

- **Automatic**: Addons are checked and updated to match your SwitchCraft version
- **Manual**: If automatic update fails, go to **Settings** → **Help** → **Addon Manager** to update addons manually

### Configuration Migration

SwitchCraft automatically migrates your configuration between versions:

- **Settings**: Preserved automatically
- **Intune Credentials**: Securely stored and migrated
- **History**: Analysis history is preserved
- **Custom Scripts**: User-created scripts remain intact

### Breaking Changes

Major version upgrades may include breaking changes. Check the [Release Notes](https://github.com/FaserF/SwitchCraft/releases) for:

- Deprecated features
- API changes
- Configuration format changes
- Required system updates

## Troubleshooting

### Update Check Fails

If automatic update checks fail:

1. **Check your internet connection**
2. **Verify firewall settings** - SwitchCraft needs access to `api.github.com`
3. **Try manual download** from GitHub Releases
4. **Check proxy settings** if behind a corporate firewall

### Installation Errors

If the upgrade installer fails:

1. **Run as Administrator** - Some upgrades require elevated privileges
2. **Close all SwitchCraft instances** - Ensure no processes are running
3. **Disable antivirus temporarily** - Some AV software blocks installers
4. **Check disk space** - Ensure sufficient free space (minimum 150 MB)

### Version Mismatch

If you see version mismatch errors:

1. **Uninstall the old version** completely
2. **Restart your computer** (recommended)
3. **Install the new version** fresh
4. **Settings will be preserved** in `%APPDATA%\SwitchCraft\`

## Rollback

If you need to rollback to a previous version:

1. **Download the previous release** from [GitHub Releases](https://github.com/FaserF/SwitchCraft/releases)
2. **Uninstall the current version** (optional, but recommended)
3. **Install the previous version**
4. **Your configuration will be preserved** (unless you uninstalled)

> **Note**: Rolling back may cause issues if the previous version uses an older configuration format. Consider backing up your settings first.

## Code Signing Certificate Configuration

When upgrading, if you use custom code signing certificates, note the following configuration precedence:

1. **Thumbprint**: Explicit thumbprint configuration (highest priority)
2. **`CodeSigningCertPath`**: Path to the certificate file (Pfx)
3. **`CertPath`**: Legacy configuration path (for backward compatibility)

If `CodeSigningCertPath` is not configured, the service will check `CertPath` for compatibility. Users migrating from setups where only `CertPath` was used should be aware of this fallback.

## Related Documentation

- [Installation Guide](./installation.md) - Initial installation instructions
- [FAQ](./faq.md) - Common questions about updates
- [Release Notes](https://github.com/FaserF/SwitchCraft/releases) - Detailed changelog for each version
