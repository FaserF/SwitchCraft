# SwitchCraft ADMX Policy Template

Administrative templates for managing SwitchCraft settings via Group Policy (GPO) or Microsoft Intune.

## Available Policies

| Policy | Category | Description | Registry Value | Type |
|--------|----------|-------------|----------------|------|
| **Enable Debug Logging** | SwitchCraft | Enable/disable verbose debug logging | `DebugMode` | DWORD (0/1) |
| **Update Channel** | Updates | Configure update channel (Stable/Beta/Dev) | `UpdateChannel` | String |
| **Enable Winget** | General | Enable/disable Winget Store integration | `EnableWinget` | DWORD (0/1) |
| **Language** | General | Set application language (en/de) | `Language` | String |
| **Git Repo Path** | General | Path to local Git repository | `GitRepoPath` | String |
| **AI Provider** | AI | Backend provider (local, openai, gemini) | `AIProvider` | String |
| **Sign Scripts** | Security | Enable automatic script signing | `SignScripts` | DWORD (0/1) |
| **Cert Thumbprint** | Security | Thumbprint of Code Signing Certificate | `CodeSigningCertThumbprint` | String |
| **Tenant ID** | Intune | Azure AD Tenant ID | `GraphTenantId` | String |
| **Client ID** | Intune | Azure App Client ID | `GraphClientId` | String |
| **Client Secret** | Intune | Azure App Client Secret (Use with caution) | `GraphClientSecret` | String |

## Installation

### Local Group Policy

1. Copy `SwitchCraft.admx` to `C:\Windows\PolicyDefinitions\`
2. Copy `en-US\SwitchCraft.adml` to `C:\Windows\PolicyDefinitions\en-US\`
3. Copy `de-DE\SwitchCraft.adml` to `C:\Windows\PolicyDefinitions\de-DE\`
4. Open `gpedit.msc` → User Configuration → Administrative Templates → SwitchCraft

### Active Directory (Domain GPO)

1. Copy `SwitchCraft.admx` to `\\domain.local\SYSVOL\domain.local\Policies\PolicyDefinitions\`
2. Copy language folders (`en-US`, `de-DE`) with `.adml` files to the same location
3. Create/edit a GPO and configure under **User Configuration → Administrative Templates → SwitchCraft**

### Microsoft Intune

Method 1: **Settings Catalog** (Recommended for new policies)
1. Create a new Configuration Profile → Settings Catalog
2. Search for the registry path: `HKCU\Software\FaserF\SwitchCraft`
3. Add values manually matching the table above.

Method 2: **Custom OMA-URI** (Preferred for Intune)

SwitchCraft fully supports Intune's custom OMA-URI policies that target the `Software\Policies` keys.
The Base URI is: `./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft`

### Configuration Reference

| Setting | OMA-URI Path Suffix | Data Type | Default | Allowed Values |
|---------|---------------------|-----------|---------|----------------|
| **Debug Mode** | `/DebugMode` | Integer | `0` | `0` (Off), `1` (On) |
| **Update Channel** | `/UpdateChannel` | String | `stable` | `stable` (Standard), `beta`, `Pre-release`, `dev` (Nightly) |
| **Enable Winget** | `/EnableWinget` | Integer | `0` | `0` (Disabled), `1` (Enabled) |
| **Language** | `/Language` | String | `en` | `en` (English), `de` (German) |
| **Git Repo Path** | `/GitRepoPath` | String | *Empty* | Valid filesystem path (e.g. `C:\SwitchCraftConfig`) |
| **AI Provider** | `/AIProvider` | String | `local` | `local` (Ollama), `openai`, `gemini` |
| **Sign Scripts** | `/SignScripts` | Integer | `0` | `0` (Disabled), `1` (Enabled) |
| **Cert Thumbprint** | `/CodeSigningCertThumbprint` | String | *Empty* | SHA1 Certificate Thumbprint |
| **Tenant ID** | `/GraphTenantId` | String | *Empty* | Azure AD Tenant GUID |
| **Client ID** | `/GraphClientId` | String | *Empty* | Azure Application Client GUID |
| **Client Secret** | `/GraphClientSecret` | String | *Empty* | Application Client Secret |
| **Theme** | `/Theme` | String | `System` | `System`, `Light`, `Dark` |
| **Custom Template** | `/CustomTemplatePath` | String | *Empty* | Path to custom templates |
| **Winget Repo** | `/WingetRepoPath` | String | *Empty* | Path to Winget repo |
| **AI Key** | `/AIKey` | String | *Empty* | API Key (Gemini/OpenAI) |
| **Intune Groups** | `/IntuneTestGroups` | String | *Empty* | CSV of Group IDs |

### Complete OMA-URI XML Example

Use this XML structure to bulk import settings. Remove `<Row>` blocks for settings you do not wish to enforce.

```xml
<Data>
  <!-- Debug Mode: 0=Off, 1=On -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/DebugMode</OMAURI>
    <DataType>Integer</DataType>
    <Value>0</Value>
  </Row>

  <!-- Update Channel: stable, beta, dev -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/UpdateChannel</OMAURI>
    <DataType>String</DataType>
    <Value>stable</Value>
  </Row>

  <!-- Enable Winget Integration: 0=Disabled, 1=Enabled -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/EnableWinget</OMAURI>
    <DataType>Integer</DataType>
    <Value>1</Value>
  </Row>

  <!-- Language: en, de -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/Language</OMAURI>
    <DataType>String</DataType>
    <Value>en</Value>
  </Row>

  <!-- Git Repository Path -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/GitRepoPath</OMAURI>
    <DataType>String</DataType>
    <Value>C:\ProgramData\SwitchCraft\ConfigRepo</Value>
  </Row>

  <!-- AI Provider: local, openai, gemini -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/AIProvider</OMAURI>
    <DataType>String</DataType>
    <Value>local</Value>
  </Row>

  <!-- Sign Scripts: 0=Disabled, 1=Enabled -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/SignScripts</OMAURI>
    <DataType>Integer</DataType>
    <Value>1</Value>
  </Row>

  <!-- Code Signing Certificate Thumbprint -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/CodeSigningCertThumbprint</OMAURI>
    <DataType>String</DataType>
    <Value>A1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0</Value>
  </Row>

  <!-- Intune: Tenant ID -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/GraphTenantId</OMAURI>
    <DataType>String</DataType>
    <Value>00000000-0000-0000-0000-000000000000</Value>
  </Row>

  <!-- Intune: Client ID -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/GraphClientId</OMAURI>
    <DataType>String</DataType>
    <Value>00000000-0000-0000-0000-000000000000</Value>
  </Row>

  <!-- Intune: Client Secret -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/GraphClientSecret</OMAURI>
    <DataType>String</DataType>
    <Value>YOUR_CLIENT_SECRET_HERE</Value>
  </Row>
</Data>
```

Method 3: **ADMX Ingestion**
1. Create a new Device Configuration Profile
2. Select "Templates" → "Custom"
3. Upload the ADMX/ADML files using OMA-URI:
   - `./Device/Vendor/MSFT/Policy/ConfigOperations/ADMXInstall/SwitchCraft/Policy/SwitchCraftPolicy`
   - Data type: String
   - Value: Contents of `SwitchCraft.admx`

## Registry Reference & Precedence

SwitchCraft reads configuration with the following precedence order:

1. **Machine Policy** (`HKLM\Software\Policies\FaserF\SwitchCraft`) - *Highest Priority (Intune/GPO)*
2. **User Policy** (`HKCU\Software\Policies\FaserF\SwitchCraft`) - *High Priority (Intune/GPO)*
3. **User Preference** (`HKCU\Software\FaserF\SwitchCraft`) - *User Setting (Overrides Machine Default)*
4. **Machine Preference** (`HKLM\Software\FaserF\SwitchCraft`) - *Admin Default*

This ensures that Policies managed by your organization (via Intune/GPO) always override local user settings.

| Policy | Value Name | Type | Values |
|--------|---------------|------|--------|
| Debug Logging | `DebugMode` | REG_DWORD | `0` = Off, `1` = On |
| Update Channel | `UpdateChannel` | REG_SZ | `stable`, `beta`, `dev` |

## PowerShell Deployment

```powershell
# Enable Debug Mode for all users (requires admin)
$users = Get-ChildItem "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList" |
         ForEach-Object { $_.GetValue("ProfileImagePath") }

foreach ($user in $users) {
    $sid = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\*" |
            Where-Object { $_.ProfileImagePath -eq $user }).PSChildName

    reg load "HKU\$sid" "$user\NTUSER.DAT" 2>$null
    reg add "HKU\$sid\Software\FaserF\SwitchCraft" /v DebugMode /t REG_DWORD /d 1 /f
    reg unload "HKU\$sid" 2>$null
}
```

## File Structure

```
PolicyDefinitions/
├── SwitchCraft.admx      # Policy definitions
├── en-US/
│   └── SwitchCraft.adml  # English strings
├── de-DE/
│   └── SwitchCraft.adml  # German strings
└── README.md             # This file
```
