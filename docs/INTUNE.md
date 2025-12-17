# ☁️ Enterprise & Intune Integration

SwitchCraft is completely ready for modern management with Microsoft Intune.

## 🚀 All-in-One Automation

Pro-Users can enable the **"All-in-One"** button in the Analyzer result pane to automate the entire deployment chain:

1.  **Generate Script**: Intelligent PowerShell template generation based on analysis.
2.  **Sign Script**: Authenticode signing (auto-detects certs or custom PFX).
3.  **Local Test**: Validates installation/uninstallation locally (requires Admin).
4.  **Package**: Converts the validated script into an `.intunewin` package using the Microsoft Content Prep Tool.
5.  **Upload**: Pushes the app to Microsoft Intune (Graph API) and opens the portal.

## ⚙️ Configuration & Settings

SwitchCraft supports extensive configuration via the GUI or Registry/GPO for enterprise environments.

### Intune API Access
To enable direct uploads, you must register an App in Azure AD (Entra ID) and provide the credentials in Settings:
-   **Tenant ID**
-   **Client ID**
-   **Client Secret**

> [!NOTE]
> Required API Permissions: `DeviceManagementApps.ReadWrite.All`

### Intune Test Groups
You can configure **Test Groups** in Settings. When enabled, newly uploaded apps will be automatically assigned to these groups (Intent: *Available* or *Required*).
-   Add groups by **Name** and **Object ID** (GUID).

### External Tools
-   **IntuneWinAppUtil Path**: SwitchCraft attempts to download the Content Prep Tool automatically. You can specify a custom path in settings if you use a specific version.

### Script Signing
Enforce code signing on all generated scripts for AppLocker/WDAC compliance:
-   **Enable Signing**: Toggles the signing step.
-   **Certificate Path**: Path to a `.pfx` file. If left empty, SwitchCraft attempts to find a valid Code Signing certificate in your User/Machine certificate store.

## 📦 Intune Utility

Even without the automation, you can use the **Intune Utility** tab to:
- Manually create `.intunewin` packages from any folder.
- Generate Install/Uninstall PowerShell scripts from templates.
