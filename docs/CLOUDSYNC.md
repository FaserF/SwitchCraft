# SwitchCraft CloudSync

SwitchCraft uses **GitHub Gists** to securely synchronize your settings across devices.

## How it works

1. **Authentication**: SwitchCraft uses the secure [OAuth 2.0 Device Authorization Grant](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow) flow. You never enter your password directly into SwitchCraft.
2. **Permissions**: We request the minimum necessary permissions:
   - `gist`: To create (if it doesn't exist) and update a private Gist named `switchcraft_settings.json`.
   - `read:user`: To display your GitHub username in the application.
3. **Storage**: Your settings are stored in a **Secret Gist**.
   - Secret Gists are not searchable and are only accessible by you (and anyone you share the direct link with).
   - SwitchCraft only reads/writes the specific file `switchcraft_settings.json`.

## What data is synced?

- **Application Preferences**: Theme, Language, default paths.
- **Intune Configuration**: Tenant ID (if saved), default groups.
- **Winget Settings**: Custom sources lists.
- **API Keys**: **Note:** For security reasons, highly sensitive secrets like Client Secrets may NOT be synced or are encrypted (depending on configuration). We recommend re-entering sensitive credentials on each new device.

## Troubleshooting Login

- If the browser doesn't open automatically, copy the link and code provided in the dialog.
- Ensure you are logged into the correct GitHub account in your default browser.
- If synchronization fails, check your internet connection and ensure GitHub is accessible.

## Data Privacy

SwitchCraft connects directly to GitHub's API. No intermediate servers are used. Your data stays between you and GitHub.
