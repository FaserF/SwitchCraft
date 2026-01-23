# Script Management

The **Script Management** view is a dedicated interface for handling PowerShell scripts within your Intune environment. It supports both Device Management Scripts and Proactive Remediations.

## Functionality

### 1. Upload Scripts
Upload generic PowerShell scripts to be executed on devices.
*   **File Selection**: Pick a `.ps1` file.
*   **Scope**: Choose between System (User) or System context.
*   **Assignment**: (Optional) Assign to All Devices or specific groups immediately.

### 2. Proactive Remediations
Manage detection and remediation script pairs.
*   **Detection Script**: The script that checks if a fix is needed (Exit Code 1 = fix needed).
*   **Remediation Script**: The script that applies the fix.
*   **Frequency**: Schedule how often the remediation runs (hourly, daily).

### 3. Signing Service
*   **Code Signing**: If you have a code signing certificate configured (Settings), use the "Sign Script" tool to digitally sign your `.ps1` files before upload, ensuring execution policy compliance.

## Integration
*   The scripts you view here are synced directly from your **Intune Tenant**.
*   Changes made here (deletions, assignments) are reflected in the cloud immediately.

## Common Use Cases
*   **Deploying Registry Fixes**: Upload a remediation script to enforce registry keys.
*   **Cleanup Tasks**: Run a daily cleanup script on all workstations.
*   **Inventory Collection**: Gather custom data not collected by standard inventory.
