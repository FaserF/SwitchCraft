# Intune Store

The **Intune Store** view is a browser for your *existing* deployments in Microsoft Intune. Unlike the **Intune Packager** (which creates apps), this view *manages* them.

## Capabilities
*   **Search**: Instant search across all your Win32Apps, MSIs, and Store Apps in the tenant.
*   **Filters**: Filter by Assigned / Unassigned, or by Status (Error/Success).
*   **App Detail**:
    *   *Overview*: Install counts, versions.
    *   *Assignments*: See which groups are targeted.
    *   *Properties*: Edit name, description, icon, or install command directly.
*   **Delete**: Remove apps from the tenant (with safety confirmation).

## Sync
SwitchCraft caches your Intune app list for performance. If you make changes in the customized Azure Portal, click **Sync** to update the local view.
