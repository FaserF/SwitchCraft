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
> **Minimum Required API Permissions**: `DeviceManagementApps.ReadWrite.All`
>
> **For Group Manager**: Additional permissions required:
> - `Group.Read.All` or `Group.ReadWrite.All`
> - `User.Read.All` (for user search)
> - `GroupMember.ReadWrite.All` (for member management)

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

## 🛒 Intune Store Browser

The **Intune Store** view (Modern UI only) allows you to:
- Browse all your Intune applications with logo display
- View detailed metadata (ID, Publisher, Created Date, App Type)
- See group assignments (Required, Available, Uninstall)
- View install/uninstall command lines
- Launch the Packaging Wizard directly from an existing app
- Search and filter applications

### Using the Intune Store

1. Navigate to **Apps & Devices → Intune Store**
2. Search for applications or browse the list
3. Click on any app to view details
4. Use **"Deploy / Package..."** to create a new version or package

> [!NOTE]
> Requires Microsoft Graph API credentials configured in Settings → Graph API.

## 👥 Entra Group Manager

The **Group Manager** (Modern UI only) provides comprehensive management of Microsoft Entra ID (Azure AD) groups directly from SwitchCraft.

### Features

- **Browse Groups**: View all Entra ID groups in your tenant with search and filter capabilities
- **Create Groups**: Create new Security or Microsoft 365 groups with name and description
- **Delete Groups**: Safely delete groups with confirmation dialog (requires Deletion Mode toggle)
- **Manage Members**: Add and remove users from groups
- **User Search**: Search for users by name or email to add to groups
- **Group Details**: View group ID, type, and description

### Required Permissions

The Group Manager requires additional Graph API permissions beyond the standard Intune permissions:

| Permission | Purpose |
|-----------|---------|
| `Group.Read.All` | Read group information and members |
| `Group.ReadWrite.All` | Create, update, and delete groups |
| `User.Read.All` | Search for users to add to groups |
| `GroupMember.ReadWrite.All` | Add and remove group members |

> [!IMPORTANT]
> These permissions must be granted by an Azure AD administrator. Standard `DeviceManagementApps.ReadWrite.All` is not sufficient for group management.

### Using the Group Manager

1. Navigate to **Apps & Devices → Group Manager**
2. Groups are automatically loaded from your tenant
3. Use the search field to filter groups by name or description
4. Select a group to enable member management

#### Creating a Group

1. Click **"Create Group"**
2. Enter a **Group Name** (required)
3. Optionally add a **Description**
4. Click **"Create"**

The group will be created as a Security group by default.

#### Managing Members

1. Select a group from the list
2. Click **"Manage Members"**
3. View current members with their email addresses
4. Click **"Add Member"** to search and add users
5. Click the remove icon (🗑️) next to a member to remove them

#### Deleting a Group

1. Enable **"Enable Deletion (Danger Zone)"** toggle
2. Select the group you want to delete
3. Click **"Delete Selected"**
4. Confirm the deletion in the dialog

> [!WARNING]
> Group deletion is permanent and cannot be undone. Use with caution.

### Use Cases

- **Test Groups**: Create dedicated groups for testing Intune app deployments
- **Department Groups**: Organize users into groups for targeted deployments
- **Assignment Management**: Quickly add or remove users from deployment groups
- **Group Cleanup**: Remove unused or obsolete groups

### Integration with Intune

Groups created or managed in the Group Manager can be used for:
- **Intune App Assignments**: Assign apps to groups created in Group Manager
- **Test Groups**: Configure in Settings → Intune → Test Groups for automatic assignment
- **Deployment Stacks**: Use groups with Stack Manager for batch deployments

## 🧩 Stack Manager

The **Stack Manager** (Modern UI only) allows you to organize multiple applications into named "stacks" for batch deployment to Intune.

### Features

- **Create Stacks**: Group multiple apps together by name
- **Add Applications**: Add apps to stacks by Winget ID or file path
- **Batch Deployment**: Deploy entire stacks to Intune with one click
- **Stack Management**: Edit, rename, and delete stacks
- **Visual Organization**: Keep track of related applications together

### Using Stack Manager

1. Navigate to **Apps & Devices → Stack Manager**
2. Enter a stack name and click **"Add Stack"**
3. Select the stack and add applications:
   - Enter a Winget Package ID (e.g., `Microsoft.PowerToys`)
   - Or provide a file path to an installer
4. Click **"Save Stack"** to persist your changes
5. Click **"Deploy Stack"** to deploy all apps in the stack to Intune

> [!TIP]
> Stacks are useful for deploying related applications together, such as a "Development Tools" stack or "Security Software" stack.

### Stack Storage

Stacks are stored locally in `data/stacks.json` and persist between sessions. You can:
- Create multiple stacks for different deployment scenarios
- Reuse stacks for repeated deployments
- Organize apps by department, function, or project