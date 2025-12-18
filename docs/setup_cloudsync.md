# SwitchCraft CloudSync & Backup Setup

This guide explains how to set up and use the CloudSync feature (GitHub Authentication) and the Local Backup system in SwitchCraft.

## 1. CloudSync (GitHub Integration)

SwitchCraft allows you to sync your settings across devices using your GitHub account (via Gists).

### Prerequisites
- A GitHub Account.
- SwitchCraft requires a Client ID to authenticate. Ideally, use the official one provided.

### Authentication Flow (Device Flow)
1. **Initiate Login**: The application will request a "Device Code" from GitHub.
2. **User Authorization**:
   - The app will display a **User Code** (e.g., `ABCD-1234`) and a URL (`https://github.com/login/device`).
   - Open the URL in your browser.
   - Enter the code and authorize the "SwitchCraft" application.
3. **Completion**: Once authorized, SwitchCraft automatically receives an access token and securely stores it in your system keyring.

### Usage
- **Sync Up**: Uploads your current local settings to a private GitHub Gist named `switchcraft_settings.json`.
  - *Note:* If the Gist does not exist, it will be created automatically.
- **Sync Down**: Downloads settings from the Gist and applies them to your current machine.

### Security
- Tokens are stored securely using the OS's Credential Manager/Keyring.
- The Gist created is **Secret** (Private), meaning it's not listed in search engines, but anyone with the link (or your token) can access it.

---

## 2. Local Backup (Import / Export)

You can also manually back up your settings to a local JSON file.

### Export Settings
- Use this feature to save your current configuration to a file (e.g., `switchcraft_backup.json`).
- Useful for archiving or manually transferring settings to air-gapped machines.

### Import Settings
- Load a previously saved JSON file to restore your configuration.
- **Warning**: This will overwrite your current settings with the values from the file.

---

## Developer / DevOps Notes

### Configuration Keys
- **Registry Path**: `HKCU\Software\FaserF\SwitchCraft`
- **Token Storage**: `SwitchCraft_GitHub_Token` in System Keyring.

### Integration in Code
- **AuthService**: Handles the OAuth Device Flow.
- **SyncService**: Manages Gist CRUD operations.
- **BackupService**: Manages local JSON file I/O.

---

## 3. Administrator / Developer Setup

If you are a developer or administrator deploying this feature, you must create a GitHub OAuth App to obtain a **Client ID**.

### Step 1: Create a GitHub OAuth App
1. Go to **GitHub Settings** -> [**Developer settings**](https://github.com/settings/apps).
2. Select **OAuth Apps** -> **New OAuth App**.
3. Fill in the details:
   - **Application Name**: "SwitchCraft" (or your custom name).
   - **Homepage URL**: Your repository URL or website (e.g., `https://github.com/your-org/switchcraft`).
   - **Authorization callback URL**: This is **not used** for the Device Flow, but required by the form. You can use valid URL like `http://localhost:8000/callback` or your homepage.
4. Click **Register application**.

### Step 2: Enable Device Flow
1. Once created, check if there is an option to **"Enable Device Flow"**.
   - *Note:* For standard "OAuth Apps", Device Flow is typically enabled by default. If you created a "GitHub App" (different from "OAuth App"), you must explicitly check "Expire user authorization tokens" and ensure Device Flow usage is allowed.
   - We recommend using a standard **"OAuth App"** for this use case.

### Step 3: Copy Client ID
1. On the App's settings page, copy the **Client ID** (e.g., `Iv1.xxxxxxxxxxxx`).
2. **IMPORTANT**: You do **NOT** need the **Client Secret** for the Device Flow in a public client (native app). The Device Flow is specifically designed to allow users to authenticate without the application needing to hold a secret credential.

### Step 4: Configure Code
1. Open `src/switchcraft/services/auth_service.py`.
2. Locate the `CLIENT_ID` variable in the `AuthService` class:
   ```python
   class AuthService:
       ...
       # Replace with your actual GitHub App Client ID
       CLIENT_ID = "YOUR_CLIENT_ID_HERE"
       ...
   ```
3. Replace the placeholder with your **Client ID**.

### Required Permissions (Scopes)
The application requires the following scopes (already configured in code):
- **`gist`**:
  - **Read/Write access to Gists**.
  - Required to create (`switchcraft_settings.json`) and update it with user settings.
- **`read:user`**:
  - **Read-only access to user profile**.
  - Required to verify identity (get username/avatar) during login.

---

## 4. Security Note (Client Secrets)

> [!IMPORTANT]
> **NEVER include a Client Secret in a public repository or compiled application.**

SwitchCraft uses the **OAuth 2.0 Device Authorization Grant** (RFC 8628). This flow is designed for public clients (like CLIs and Desktop Apps) that cannot securely store secrets.

- **Client ID**: It is **SAFE** to be public. It merely identifies the "SwitchCraft" application to GitHub. It does not grant any access by itself.
- **Client Secret**: It is **NOT USED** in this implementation. Do **NOT** generate one, and if you have one, do **NOT** put it in the code.

The security comes from the fact that the user must manually approve the login in their browser, effectively "granting" the token to the application identified by the Client ID.
