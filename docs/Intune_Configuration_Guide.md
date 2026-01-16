# SwitchCraft Intune Configuration Guide

This guide describes how to correctly configure SwitchCraft policies using Microsoft Intune Custom Profiles (OMA-URI).

## Common Error: -2016281112 (Remediation Failed)

If you see error `-2016281112` in Intune for your OMA-URI settings, it is likely because the **Data Type** was set incorrectly.

> [!IMPORTANT]
> **Data Type Confusion**:
> - **In the Intune Portal**, you must select **"String"** (or sometimes labeled **"String (XML)"**) from the dropdown.
> - **The Value** must be an **XML snippet** (e.g., `<enabled/>`), NOT a simple text string or number.
>
> **Why?**
> These policies are backed by an ADMX file. In the OMA-URI world, ADMX-backed policies are treated as "String" types that accept an encoded XML payload to configure the specific policy setting. Choosing "Integer" or "Boolean" will fail because the underlying ADMX handler expects a String containing XML.

## ADMX Ingestion (Prerequisite)

Ensure you have ingested the ADMX file first.
- **OMA-URI**: `./Device/Vendor/MSFT/Policy/ConfigOperations/ADMXInstall/SwitchCraft/Policy/SwitchCraftPolicy`
- **Data Type**: String
- **Value**: [Content of SwitchCraft.admx]

## OMA-URI Settings

All settings below use the base path:
`./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced~[Category]/[PolicyName]`

### General Settings
**Category**: `General_Enf`

#### 1. Enable Winget Integration (`EnableWinget_Enf`)
- **OMA-URI**: `...~General_Enf/EnableWinget_Enf`
- **Intune Selection**: String
- **XML Value (Enable)**:
  ```xml
  <enabled/>
  ```
- **XML Value (Disable)**:
  ```xml
  <disabled/>
  ```

#### 2. Company Name (`CompanyName_Enf`)
- **OMA-URI**: `...~General_Enf/CompanyName_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="CompanyNameBox" value="Acme Corp"/>
  ```

#### 3. Git Repository Path (`GitRepoPath_Enf`)
- **OMA-URI**: `...~General_Enf/GitRepoPath_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="GitRepoPathBox" value="C:\SwitchCraft\Repo"/>
  ```

#### 4. Custom Template Path (`CustomTemplatePath_Enf`)
- **OMA-URI**: `...~General_Enf/CustomTemplatePath_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="CustomTemplatePathBox" value="C:\SwitchCraft\Templates"/>
  ```

#### 5. Winget Repository Path (`WingetRepoPath_Enf`)
- **OMA-URI**: `...~General_Enf/WingetRepoPath_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="WingetRepoPathBox" value="C:\SwitchCraft\WingetRepo"/>
  ```

#### 6. Theme (`Theme_Enf`)
- **OMA-URI**: `...~General_Enf/Theme_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="ThemeDropdown" value="Dark"/>
  ```
  *(Valid values: System, Light, Dark)*

---

### Update Settings
**Category**: `Updates_Enf`

#### 1. Update Channel (`UpdateChannel_Enf`)
- **OMA-URI**: `...~Updates_Enf/UpdateChannel_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="UpdateChannelDropdown" value="stable"/>
  ```
  *(Valid values: stable, beta, dev)*

---

### AI Settings
**Category**: `AI_Enf`

#### 1. AI Provider (`AIProvider_Enf`)
- **OMA-URI**: `...~AI_Enf/AIProvider_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="AIProviderDropdown" value="openai"/>
  ```
  *(Valid values: local, openai, gemini)*

#### 2. AI API Key (`AIKey_Enf`)
- **OMA-URI**: `...~AI_Enf/AIKey_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="AIKeyBox" value="sk-your-api-key"/>
  ```

---

### Intune Settings
**Category**: `Intune_Enf`

#### 1. Graph Tenant ID (`GraphTenantId_Enf`)
- **OMA-URI**: `...~Intune_Enf/GraphTenantId_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="GraphTenantIdBox" value="00000000-0000-0000-0000-000000000000"/>
  ```

#### 2. Graph Client ID (`GraphClientId_Enf`)
- **OMA-URI**: `...~Intune_Enf/GraphClientId_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="GraphClientIdBox" value="00000000-0000-0000-0000-000000000000"/>
  ```

#### 3. Graph Client Secret (`GraphClientSecret_Enf`)
- **OMA-URI**: `...~Intune_Enf/GraphClientSecret_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="GraphClientSecretBox" value="your-client-secret"/>
  ```

#### 4. Intune Test Groups (`IntuneTestGroups_Enf`)
- **OMA-URI**: `...~Intune_Enf/IntuneTestGroups_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="IntuneTestGroupsBox" value="GroupID1,GroupID2"/>
  ```

---

### Security Settings
**Category**: `Security_Enf`

#### 1. Sign Scripts (`SignScripts_Enf`)
- **OMA-URI**: `...~Security_Enf/SignScripts_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  ```

#### 2. Code Signing Cert Thumbprint (`CodeSigningCertThumbprint_Enf`)
- **OMA-URI**: `...~Security_Enf/CodeSigningCertThumbprint_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  <data id="CodeSigningCertThumbprintBox" value="THUMBPRINT_HEX_STRING"/>
  ```

---

### Top-Level Settings

#### 1. Debug Mode (`DebugMode_Enf`)
- **OMA-URI**: `./User/Vendor/MSFT/Policy/Config/SwitchCraft~Policy~SwitchCraft~Enforced/DebugMode_Enf`
- **Intune Selection**: String
- **XML Value**:
  ```xml
  <enabled/>
  ```
