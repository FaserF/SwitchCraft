# SwitchCraft ADMX Policy Template

Administrative templates for managing SwitchCraft settings via Group Policy (GPO) or Microsoft Intune.

> [!TIP]
> **Having issues?** If you see error code **-2016281112** (Remediation Failed) in Intune, see the [GPO Troubleshooting Guide](../GPO_TROUBLESHOOTING.md) for detailed solutions.

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

SwitchCraft fully supports Intune's custom OMA-URI policies that target the `Software\Policies` keys via ADMX Ingestion.

> [!IMPORTANT]
> **CRITICAL CONFIGURATION NOTE**
> When configuring ADMX-backed policies in Intune, you must **ALWAYS** select **String** (or **String (XML)** depending on the portal version) as the Data Type.
>
> **NEVER** use "Integer" or "Boolean", even if the setting logically represents a number or switch. The value field MUST contain the XML payload defined below.

**Step 1: Ingest ADMX**
- OMA-URI: `./Device/Vendor/MSFT/Policy/ConfigOperations/ADMXInstall/switchcraft/Policy/SwitchCraftPolicy`
- Data Type: **String**
- Value: Copy contents of `SwitchCraft.admx`

**Step 2: Configure Policies**
The Base URI is: `./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced`

> [!IMPORTANT]
> **Correct OMA-URI Path Format**: The path is built from the ADMX file's `target prefix` (`switchcraft`) and `namespace` (`FaserF.SwitchCraft`). The namespace dot (`.`) is replaced with a tilde (`~`), resulting in `switchcraft~Policy~FaserF~SwitchCraft~Enforced`.

### Configuration Reference

| Setting | OMA-URI Path Suffix | Intune Data Type | Value Format (XML) |
|---------|---------------------|-----------|----------------|
| **Debug Mode** | `/DebugMode_Enf` | **String** | `<enabled/>` |
| **Update Channel** | `~Updates_Enf/UpdateChannel_Enf` | **String** | `<enabled/><data id="UpdateChannelDropdown" value="stable"/>` |
| **Enable Winget** | `~General_Enf/EnableWinget_Enf` | **String** | `<enabled/>` |
| **Language** | `~General_Enf/Language_Enf` | **String** | `<enabled/><data id="LanguageDropdown" value="en"/>` |
| **Git Repo Path** | `~General_Enf/GitRepoPath_Enf` | **String** | `<enabled/><data id="GitRepoPathBox" value="C:\Path"/>` |
| **AI Provider** | `~AI_Enf/AIProvider_Enf` | **String** | `<enabled/><data id="AIProviderDropdown" value="local"/>` |
| **Sign Scripts** | `~Security_Enf/SignScripts_Enf` | **String** | `<enabled/>` |
| **Cert Thumbprint** | `~Security_Enf/CodeSigningCertThumbprint_Enf` | **String** | `<enabled/><data id="CodeSigningCertThumbprintBox" value="..."/>` |
| **Tenant ID** | `~Intune_Enf/GraphTenantId_Enf` | **String** | `<enabled/><data id="GraphTenantIdBox" value="..."/>` |
| **Client ID** | `~Intune_Enf/GraphClientId_Enf` | **String** | `<enabled/><data id="GraphClientIdBox" value="..."/>` |
| **Client Secret** | `~Intune_Enf/GraphClientSecret_Enf` | **String** | `<enabled/><data id="GraphClientSecretBox" value="..."/>` |

### Complete OMA-URI XML Example

Use this XML structure to bulk import settings. Note that **DataType** is always `String`.

```xml
<Data>
  <!-- ADMX Ingestion -->
  <Row>
    <OMAURI>./Device/Vendor/MSFT/Policy/ConfigOperations/ADMXInstall/switchcraft/Policy/SwitchCraftPolicy</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[ ... COPY ADMX CONTENT HERE ... ]]></Value>
  </Row>

  <!-- Debug Mode -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced/DebugMode_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/>]]></Value>
  </Row>

  <!-- Update Channel -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Updates_Enf/UpdateChannel_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="UpdateChannelDropdown" value="stable"/>]]></Value>
  </Row>

  <!-- Enable Winget -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/EnableWinget_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/>]]></Value>
  </Row>

  <!-- Language -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/Language_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="LanguageDropdown" value="en"/>]]></Value>
  </Row>

  <!-- Git Repository Path -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/GitRepoPath_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="GitRepoPathBox" value="C:\ProgramData\SwitchCraft\ConfigRepo"/>]]></Value>
  </Row>

  <!-- Company Name -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/CompanyName_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="CompanyNameBox" value="My Company"/>]]></Value>
  </Row>

  <!-- Custom Template Path -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/CustomTemplatePath_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="CustomTemplatePathBox" value="C:\ProgramData\SwitchCraft\Templates"/>]]></Value>
  </Row>

  <!-- Winget Repo Path -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/WingetRepoPath_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="WingetRepoPathBox" value="C:\ProgramData\SwitchCraft\Winget"/>]]></Value>
  </Row>

  <!-- Theme -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~General_Enf/Theme_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="ThemeDropdown" value="System"/>]]></Value>
  </Row>

  <!-- AI Provider -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~AI_Enf/AIProvider_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="AIProviderDropdown" value="local"/>]]></Value>
  </Row>

  <!-- AI API Key -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~AI_Enf/AIKey_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="AIKeyBox" value="YOUR_API_KEY"/>]]></Value>
  </Row>

  <!-- Sign Scripts -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Security_Enf/SignScripts_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/>]]></Value>
  </Row>

  <!-- Code Signing Cert Thumbprint -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Security_Enf/CodeSigningCertThumbprint_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="CodeSigningCertThumbprintBox" value="THUMBPRINT"/>]]></Value>
  </Row>

  <!-- Graph Tenant ID -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/GraphTenantId_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="GraphTenantIdBox" value="00000000-0000-0000-0000-000000000000"/>]]></Value>
  </Row>

  <!-- Graph Client ID -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/GraphClientId_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="GraphClientIdBox" value="00000000-0000-0000-0000-000000000000"/>]]></Value>
  </Row>

  <!-- Graph Client Secret -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/GraphClientSecret_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="GraphClientSecretBox" value="YOUR_SECRET"/>]]></Value>
  </Row>

  <!-- Intune Test Groups -->
  <Row>
    <OMAURI>./User/Vendor/MSFT/Policy/Config/switchcraft~Policy~FaserF~SwitchCraft~Enforced~Intune_Enf/IntuneTestGroups_Enf</OMAURI>
    <DataType>String</DataType>
    <Value><![CDATA[<enabled/><data id="IntuneTestGroupsBox" value="GROUP_ID_1,GROUP_ID_2"/>]]></Value>
  </Row>
</Data>

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
