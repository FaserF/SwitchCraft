# Registry Reference

SwitchCraft uses the Windows Registry to store user settings and configuration.

## Registry Hierarchy & Precedence

SwitchCraft reads configuration from several locations in order of precedence (highest priority first):

1.  **Machine Policy** (`HKLM\Software\Policies\FaserF\SwitchCraft`) - Enforced by GPO/Intune (Device).
2.  **User Policy** (`HKCU\Software\Policies\FaserF\SwitchCraft`) - Enforced by GPO/Intune (User).
3.  **Intune OMA-URI** (`HKLM\Software\Microsoft\PolicyManager\current\device\FaserF~SwitchCraft`) - Native Intune Policy.
4.  **User Preference** (`HKCU\Software\FaserF\SwitchCraft`) - Default user settings via UI.
5.  **Machine Preference** (`HKLM\Software\FaserF\SwitchCraft`) - Machine-wide defaults.

> [!NOTE]
> Policy keys are read-only for the application. User Preferences are writable by the application.

## Registry Keys (Configuration)

| Value Name | Type | Description | Default |
| :--- | :--- | :--- | :--- |
| `InstallPath` | REG_SZ | Installation directory (set by installer) | - |
| `Version` | REG_SZ | Installed version number | - |
| `DebugMode` | REG_DWORD | Enable verbose logging (1 = enabled, 0 = disabled) | `0` |
| `UpdateChannel` | REG_SZ | Update channel: `stable`, `beta`, or `dev` | `stable` |
| `SkippedVersion` | REG_SZ | Version that user chose to skip updates for | - |
| `ThemeMode` | REG_SZ | UI Theme: `system`, `light`, `dark` | `system` |
| `Language` | REG_SZ | UI Language: `en`, `de` | `en` |
| `CompanyName` | REG_SZ | Company Name used in packaging meta | - |
| `IntuneTenantId` | REG_SZ | Microsoft Entra Tenant ID (GUID) | - |
| `IntuneClientId` | REG_SZ | Application Client ID (GUID) | - |
| `EnableWinget` | REG_DWORD | Enable Winget Store integration (1/0) | `1` |
| `SignScripts` | REG_DWORD | Automatically sign PowerShell scripts (1/0) | `0` |
| `AIProvider` | REG_SZ | AI Backend: `openai`, `gemini`, `local` | `openai` |

## Secure Secrets (Keyring)

Sensitive values like Client Secrets and PATs are stored in the Windows Credential Manager (or encrypted in Registry if policies are used).

| Secret Key | Description |
| :--- | :--- |
| `IntuneClientSecret` | Client Secret for Service Principal authentication |
| `GitHubToken` | OAuth token for Cloud Sync |
| `AIKey` | API Key for OpenAI or Gemini |

### Encrypted Registry Policies
To deploy secrets via GPO, use the `_ENC` suffix and AES encryption (see [CLI Reference](./CLI_Reference.md#config)).
- Example: `IntuneClientSecret_ENC`

## Setting Values via Command Line

### Enable Debug Mode
```powershell
reg add "HKCU\Software\FaserF\SwitchCraft" /v DebugMode /t REG_DWORD /d 1 /f
```

### Set Update Channel to Beta
```powershell
reg add "HKCU\Software\FaserF\SwitchCraft" /v UpdateChannel /t REG_SZ /d "beta" /f
```

### Disable Winget Integration
```powershell
reg add "HKCU\Software\FaserF\SwitchCraft" /v EnableWinget /t REG_DWORD /d 0 /f
```

## Managing via Group Policy

See [ADMX Template](./PolicyDefinitions/README.md) for GPO/Intune deployment documentation.
