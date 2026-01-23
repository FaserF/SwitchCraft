# Settings Configuration

The **Settings** view is the control center for SwitchCraft. Proper configuration here unlocks the full potential of Intune integration, AI features, and automation.

## General
*   **Theme**: Toggle between Light, Dark, or System theme.
*   **Language**: (Experimental) Change UI language.
*   **Paths**:
    *   *Git Repository Path*: Location where your local package repository (Apps, IntuneWin files) is stored.
    *   *Templates Path*: Folder containing your custom `Install-App.ps1` templates.

## API & Cloud
*   **Intune / Graph API**:
    *   *Tenant ID*: Your Azure AD Tenant ID.
    *   *Client ID*: The Application ID of your Enterprise App registration.
    *   *Client Secret*: The specific secret for authentication.
    *   *Test Connection**: Verifies that SwitchCraft can talk to your Intune tenant.
*   **OpenAI / AI**:
    *   *API Key*: Your sk-... key or endpoint key.
    *   *Model*: Select the model strategy (e.g., `gpt-4o`, `gpt-3.5-turbo`).

## Updates & Versioning
*   **Channel**: Choose between Stable (recommended) or Beta/Dev (latest features, potentially unstable).
*   **Check Now**: Force a check for application updates.

## Backup & Restore
*   **Export Settings**: Save your configuration (excluding sensitive secrets like API keys, usually) to a JSON file.
*   **Import Settings**: Restore configuration from a file.

> **Note**: API Keys and Secrets are stored securely in your OS credential store (Credential Manager on Windows) efficiently, avoiding plain text storage in config files where possible.
