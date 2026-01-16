# Intune OMA-URI Configuration for SwitchCraft

Use the following settings to configure SwitchCraft via Microsoft Intune Custom Profiles.

## Step 1: ADMX Ingestion (Required)

You **must** first ingest the ADMX file so Intune understands the policy structure.

- **OMA-URI**: `./Device/Vendor/MSFT/Policy/ConfigOperations/ADMXInstall/SwitchCraft/Policy/SwitchCraftPolicy`
- **Data Type**: `String`
- **Value**: [Copy content from SwitchCraft.admx](https://github.com/FaserF/SwitchCraft/blob/main/docs/PolicyDefinitions/SwitchCraft.admx)

## Step 2: Configure Settings

**OMA-URI Prefix**: `./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced`

| Setting | OMA-URI Suffix | Data Type | Value / Description |
| :--- | :--- | :--- | :--- |
| **Debug Mode** | `.../DebugMode_Enf` | Integer | `0` (Disabled), `1` (Enabled) |
| **Update Channel** | `...~Updates_Enf/UpdateChannel_Enf` | String | `<enabled/>` + `<data id="UpdateChannelDropdown" value="stable"/>` |
| **Enable Winget** | `...~General_Enf/EnableWinget_Enf` | Integer | `0` (Disabled), `1` (Enabled) |
| **Language** | `...~General_Enf/Language_Enf` | String | `<enabled/>` + `<data id="LanguageDropdown" value="en"/>` |
| **Git Repo Path** | `...~General_Enf/GitRepoPath_Enf` | String | `<enabled/>` + `<data id="GitRepoPathBox" value="C:\Path"/>` |
| **Company Name** | `...~General_Enf/CompanyName_Enf` | String | `<enabled/>` + `<data id="CompanyNameBox" value="My Company"/>` |
| **AI Provider** | `...~AI_Enf/AIProvider_Enf` | String | `<enabled/>` + `<data id="AIProviderDropdown" value="local"/>` |
| **AI API Key** | `...~AI_Enf/AIKey_Enf` | String | `<enabled/>` + `<data id="AIKeyBox" value="..."/>` |
| **Sign Scripts** | `...~Security_Enf/SignScripts_Enf` | Integer | `0` (Disabled), `1` (Enabled) |
| **Cert Thumbprint** | `...~Security_Enf/CodeSigningCertThumbprint_Enf` | String | `<enabled/>` + `<data id="CodeSigningCertThumbprintBox" value="..."/>` |
| **Graph Tenant ID** | `...~Intune_Enf/GraphTenantId_Enf` | String | `<enabled/>` + `<data id="GraphTenantIdBox" value="..."/>` |
| **Graph Client ID** | `...~Intune_Enf/GraphClientId_Enf` | String | `<enabled/>` + `<data id="GraphClientIdBox" value="..."/>` |
| **Graph Client Secret** | `...~Intune_Enf/GraphClientSecret_Enf` | String | `<enabled/>` + `<data id="GraphClientSecretBox" value="..."/>` |
| **Intune Test Groups** | `...~Intune_Enf/IntuneTestGroups_Enf` | String | `<enabled/>` + `<data id="IntuneTestGroupsBox" value="..."/>` |

> [!IMPORTANT]
> **String Policies** in ADMX are complex XML strings, not simple text values. See the example block below for the correct format.

---

## Copy & Paste Configuration Block

```text
ADMX Ingestion
./Device/Vendor/MSFT/Policy/ConfigOperations/ADMXInstall/SwitchCraft/Policy/SwitchCraftPolicy
String
<Copy contents of SwitchCraft.admx here>

Debug Mode
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced/DebugMode_Enf
Integer
1

Update Channel
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Updates_Enf/UpdateChannel_Enf
String
<enabled/>
<data id="UpdateChannelDropdown" value="stable"/>

Enable Winget
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/EnableWinget_Enf
Integer
1

Language
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/Language_Enf
String
<enabled/>
<data id="LanguageDropdown" value="en"/>

Git Repository Path
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/GitRepoPath_Enf
String
<enabled/>
<data id="GitRepoPathBox" value="C:\ProgramData\SwitchCraft\ConfigRepo"/>

Company Name
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/CompanyName_Enf
String
<enabled/>
<data id="CompanyNameBox" value="My Company"/>

Custom Template Path
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/CustomTemplatePath_Enf
String
<enabled/>
<data id="CustomTemplatePathBox" value="C:\ProgramData\SwitchCraft\Templates"/>

Winget Repo Path
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/WingetRepoPath_Enf
String
<enabled/>
<data id="WingetRepoPathBox" value="C:\ProgramData\SwitchCraft\Winget"/>

Theme
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~General_Enf/Theme_Enf
String
<enabled/>
<data id="ThemeDropdown" value="System"/>

AI Provider
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~AI_Enf/AIProvider_Enf
String
<enabled/>
<data id="AIProviderDropdown" value="local"/>

AI API Key
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~AI_Enf/AIKey_Enf
String
<enabled/>
<data id="AIKeyBox" value="YOUR_API_KEY"/>

Sign Scripts
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Security_Enf/SignScripts_Enf
Integer
1

Code Signing Cert Thumbprint
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Security_Enf/CodeSigningCertThumbprint_Enf
String
<enabled/>
<data id="CodeSigningCertThumbprintBox" value="THUMBPRINT"/>

Graph Tenant ID
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Intune_Enf/GraphTenantId_Enf
String
<enabled/>
<data id="GraphTenantIdBox" value="00000000-0000-0000-0000-000000000000"/>

Graph Client ID
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Intune_Enf/GraphClientId_Enf
String
<enabled/>
<data id="GraphClientIdBox" value="00000000-0000-0000-0000-000000000000"/>

Graph Client Secret
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Intune_Enf/GraphClientSecret_Enf
String
<enabled/>
<data id="GraphClientSecretBox" value="YOUR_SECRET"/>

Intune Test Groups
./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~Intune_Enf/IntuneTestGroups_Enf
String
<enabled/>
<data id="IntuneTestGroupsBox" value="GROUP_ID_1,GROUP_ID_2"/>
```
