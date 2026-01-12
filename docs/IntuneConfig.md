# Intune OMA-URI Configuration for SwitchCraft

Use the following settings to configure SwitchCraft via Microsoft Intune Custom Profiles.

**OMA-URI Prefix**: `./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft`

| Setting | OMA-URI | Data Type | Value / Description |
| :--- | :--- | :--- | :--- |
| **Debug Mode** | `.../DebugMode` | Integer | `0` (Disabled), `1` (Enabled) |
| **Update Channel** | `.../UpdateChannel` | String | `stable`, `beta`, `dev` |
| **Enable Winget** | `.../EnableWinget` | Integer | `0` (Disabled), `1` (Enabled) |
| **Language** | `.../Language` | String | `en`, `de` |
| **Git Repository Path** | `.../GitRepoPath` | String | Path to local git repo (e.g. `C:\Data\Repo`) |
| **Company Name** | `.../CompanyName` | String | Your Company Name |
| **AI Provider** | `.../AIProvider` | String | `local`, `openai`, `gemini` |
| **AI API Key** | `.../AIKey` | String | Your API Key (OpenAI/Gemini) |
| **Sign Scripts** | `.../SignScripts` | Integer | `0` (Disabled), `1` (Enabled) |
| **Cert Thumbprint** | `.../CodeSigningCertThumbprint` | String | Thumbprint of Code Signing Cert |
| **Graph Tenant ID** | `.../GraphTenantId` | String | Azure AD Tenant ID |
| **Graph Client ID** | `.../GraphClientId` | String | App Registration Client ID |
| **Graph Client Secret** | `.../GraphClientSecret` | String | App Registration Client Secret |
| **Intune Test Groups** | `.../IntuneTestGroups` | String | Comma-separated Group IDs |
| **Custom Template** | `.../CustomTemplatePath` | String | Path to custom templates |
| **Winget Repo Path** | `.../WingetRepoPath` | String | Path to Winget repo |
| **Theme** | `.../Theme` | String | `System`, `Light`, `Dark` |

---

## Copy & Paste Configuration Block

```text
AIProvider
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/AIProvider
String
local

AIKey
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/AIKey
String
<YOUR_API_KEY>

DebugMode
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/DebugMode
Integer
0

EnableWinget
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/EnableWinget
Integer
1

GraphClientId
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/GraphClientId
String
<YOUR_CLIENT_ID>

GraphClientSecret
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/GraphClientSecret
String
<YOUR_CLIENT_SECRET>

GraphTenantId
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/GraphTenantId
String
<YOUR_TENANT_ID>

IntuneTestGroups
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/IntuneTestGroups
String
<GROUP_ID_1,GROUP_ID_2>

Language
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/Language
String
en

SignScripts
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/SignScripts
Integer
0

CodeSigningCertThumbprint
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/CodeSigningCertThumbprint
String
<CERT_THUMBPRINT>

UpdateChannel
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/UpdateChannel
String
stable

GitRepoPath
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/GitRepoPath
String
C:\SwitchCraft\Repo

CompanyName
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/CompanyName
String
My Company

Theme
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/Theme
String
System

CustomTemplatePath
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/CustomTemplatePath
String
C:\SwitchCraft\Templates

WingetRepoPath
./User/Vendor/MSFT/Policy/Config/FaserF~Policy~SwitchCraft/WingetRepoPath
String
C:\SwitchCraft\Winget
```
