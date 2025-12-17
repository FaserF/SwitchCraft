# Setting up Intune / Microsoft Graph API

To enable SwitchCraft to upload packages directly to Microsoft Intune, you need to create an **App Registration** in the Azure Portal (Microsoft Entra ID).

## 1. Create App Registration

1. Go to the [Azure Portal](https://portal.azure.com/) > **Microsoft Entra ID**.
2. Select **App registrations** > **New registration**.
3. Name: `SwitchCraft Automation` (or similar).
4. Supported account types: **Accounts in this organizational directory only (Single tenant)**.
5. Click **Register**.

## 2. API Permissions

1. In your new App Registration, go to **API permissions**.
2. Click **Add a permission** > **Microsoft Graph**.
3. Select **Application permissions** (NOT Delegated).
4. Search for and check the following permissions:
   - `DeviceManagementApps.ReadWrite.All` (To create and upload apps)
   - `Group.Read.All` (Optional, if we implement assignment later)
5. Click **Add permissions**.
6. **IMPORTANT**: Click **Grant admin consent for [Your Org]** to activate the permissions.

## 3. Create Client Secret

1. Go to **Certificates & secrets**.
2. Click **New client secret**.
3. Description: `SwitchCraft Key`.
4. Expires: Select a duration (e.g., 12 months).
5. Click **Add**.
6. **COPY THE VALUE IMMEDIATELY**. You will not see it again. This is your **Client Secret**.

## 4. Gather Credentials

You need three values for SwitchCraft Settings:

1. **Tenant ID**: Found on the Overview page of the App Registration ("Directory (tenant) ID").
2. **Client ID**: Found on the Overview page ("Application (client) ID").
3. **Client Secret**: The value you copied in Step 3.

## 5. Configure SwitchCraft

1. Open SwitchCraft > **Settings**.
2. Scroll to **Intune / Graph API**.
3. Enter the **Tenant ID**, **Client ID**, and **Client Secret**.
4. Restart SwitchCraft or switch tabs to save.

Now you can use the **Cloud Upload** feature in the Intune Utility or the **All-in-One** automation flow!
