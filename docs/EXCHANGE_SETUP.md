# Setting up Exchange Online Management

To enable SwitchCraft to manage Exchange Online (Mail Flow, OOF, Delegation), you need to configure the correct permissions in your **Microsoft Entra ID App Registration**.

## 1. Create/Use App Registration

If you already created an App Registration for Intune, you can reuse it. Otherwise, follow the steps in [INTUNE_SETUP.md](./INTUNE_SETUP.md) to create one.

## 2. API Permissions for Exchange

Exchange management features require specific **Application Permissions** in Microsoft Graph:

### Required Permissions
- `MailboxSettings.ReadWrite` - **CRITICAL**: Required to view and set Out of Office (OOF) messages for any user.
- `Mail.Read.All` - Required to search/list messages in any mailbox (Mail Flow Trace).
- `User.ReadWrite.All` - Required to manage delegates for mailboxes.
- `Directory.Read.All` - Required to resolve user identities.

### Optional Permissions
- `Reports.Read.All` - Required if you use advanced mail traffic reporting (planned features).

## 3. Grant Admin Consent

After adding these permissions, remember to click **Grant admin consent for [Your Org]**. Without this, the application cannot access other users' mailboxes or settings.

## 4. Configuration

Ensure the following values are entered in SwitchCraft **Settings**:
1. **Tenant ID**
2. **Client ID**
3. **Client Secret**

Once configured, the **Exchange Online** view will be fully functional!
