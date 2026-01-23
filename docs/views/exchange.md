# Exchange Online

The **Exchange Online** view provides basic management capabilities for Office 365 mailboxes, intended for IT support scenarios often overlapping with device management.

## Capabilities
*   **Mailbox List**: View all user and shared mailboxes.
*   **Properties**: Check quotas, email addresses (SMTP aliases), and litigation hold status.
*   **Permissions**:
    *   *Full Access*: Grant or revoke "Full Access" delegation.
    *   *Send As*: Manage "Send As" permissions.
*   **Shared Mailboxes**: Easily create new shared mailboxes or convert user mailboxes.

## Requirements
*   **Exchange Online PowerShell Module**: SwitchCraft uses the REST-based Exchange Online Management v3 module. It may prompt you to authenticate (Modern Auth) on first use.
*   **Permissions**: The signed-in user must have Exchange Admin or Global Admin roles.
