# Security

SwitchCraft is designed with enterprise security in mind. This page outlines the security features, potential conflicts, and best practices for using the tool safely.

## 🔐 Credential Protection

Sensitive information, specifically **Microsoft Graph API Client Secrets and Client IDs**, are **never stored in plain text**.

- **System Keyring**: SwitchCraft uses the **Windows Credential Manager** (via the `keyring` library) to encrypt and securely store these credentials locally on your machine.
- **No Registry Leaks**: Unlike standard configuration values, secrets are NOT stored in the Windows Registry, ensuring they cannot be easily read by unauthorized processes or users.

## 🛡️ Automatic Vulnerability Scanning

To ensure the integrity of the tool, SwitchCraft performs an **automatic security check** of its internal Python environment upon every startup.

- **Check Scope**: Scans all installed dependencies against the [OSV.dev](https://osv.dev) database.
- **Alerts**: Notifies the user if any local library has a known security vulnerability (CVE).
- **Transparency**: Provides direct links to vulnerability details and safe usage advice.

## ⚠️ Microsoft Defender & Conditional Access

### Attack Surface Reduction (ASR)
Organizations implementing strict **Attack Surface Reduction (ASR)** rules may observe blocks when SwitchCraft attempts to:
- **Analyze installers**: Requires reading file headers (PE/MSI analysis).
- **Run External Tools**: `IntuneWinAppUtil.exe` is executed as a child process.

**Common ASR Rules that may trigger:**
- *Block executable files from running unless they meet a prevalence, age, or trusted list criterion*
- *Block process creations originating from PSExec and WMI commands* (if utilizing remote features)

**Recommendation:**
If you experience issues, consider adding path exclusions for `SwitchCraft.exe` and the `tools/IntuneWinAppUtil.exe` directory in your Endpoint Security settings.

### Conditional Access
If your organization uses **Conditional Access** policies that restrict access to Microsoft Graph API (Intune) based on device compliance or specific locations, SwitchCraft might fail to upload apps.

- **Device Compliance**: Ensure the machine running SwitchCraft is compliant.
- **MFA**: Since SwitchCraft uses **Client Credentials Flow** (App Identity), it generally bypasses user-interactive MFA. However, ensure the **Service Principal** (Enterprise Application) has not been blocked by specific Conditional Access policies targeting Service Principals.

## 🕵️ Safe Usage Tips

To maximize security when analyzing unknown installers:

1.  **Use Windows Sandbox**: Run SwitchCraft inside [Windows Sandbox](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-overview) to isolate the analysis environment. SwitchCraft allows portable usage which is perfect for this.
2.  **Verify Digital Signatures**: SwitchCraft displays publisher information. Always verify if the installer is signed by a trusted vendor.
3.  **Use Limited Permissions**: When configuring the Graph API, minimal permissions are required (`DeviceManagementApps.ReadWrite.All`). Do not grant `Directory.ReadWrite.All` unless necessary.

## 🛠️ Third-Party Tools & Conflicts

- **Winget-AutoUpdate**: If an app is detected on Winget, we recommend using [Winget-AutoUpdate](https://github.com/Romanitho/Winget-AutoUpdate) for easier maintenance.
- **EDR Solutions**: Some EDRs (CrowdStrike, SentinelOne) might flag the *behavior* of brute-force analysis (rapidly starting/stopping processes) as suspicious. Whitelisting the signing certificate of SwitchCraft is recommended.
