# Registry Reference

SwitchCraft uses the Windows Registry to store user settings and configuration.

## Registry Hierarchy

SwitchCraft reads configuration from several locations in order of precedence:

1. **Machine Policy** (`HKLM\Software\Policies\FaserF\SwitchCraft`) - Set via GPO/Intune.
2. **User Policy** (`HKCU\Software\Policies\FaserF\SwitchCraft`) - Set via GPO/Intune.
3. **User Preference** (`HKCU\Software\FaserF\SwitchCraft`) - Default user settings via UI.
4. **Machine Preference** (`HKLM\Software\FaserF\SwitchCraft`) - Machine-wide defaults.

Individual settings are merged, with higher-level objects (Policies) overwriting lower-level settings (Preferences).

## Registry Values

| Value Name | Type | Description | Default |
|------------|------|-------------|---------|
| `InstallPath` | REG_SZ | Installation directory (set by installer) | - |
| `Version` | REG_SZ | Installed version number | - |
| `DebugMode` | REG_DWORD | Enable verbose logging (1 = enabled, 0 = disabled) | `0` |
| `UpdateChannel` | REG_SZ | Update channel: `stable`, `beta`, or `dev` | `stable` |
| `SkippedVersion` | REG_SZ | Version that user chose to skip updates for | - |

## Setting Values via Command Line

### Enable Debug Mode
```powershell
reg add "HKCU\Software\FaserF\SwitchCraft" /v DebugMode /t REG_DWORD /d 1 /f
```

### Set Update Channel to Beta
```powershell
reg add "HKCU\Software\FaserF\SwitchCraft" /v UpdateChannel /t REG_SZ /d "beta" /f
```

### Reset Skipped Version
```powershell
reg delete "HKCU\Software\FaserF\SwitchCraft" /v SkippedVersion /f
```

## Managing via Group Policy

See [ADMX Template](./PolicyDefinitions/README.md) for GPO/Intune deployment documentation.
