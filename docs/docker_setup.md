# SwitchCraft Server (Docker) Guide

SwitchCraft enables you to host your own instance of the application using **Docker**. The containerized version allows you to access SwitchCraft from any browser in your network, complete with a built-in authentication system, Single Sign-On (SSO), and administrative controls.

## 🚀 Quick Start

### 1. Build & Run
You can build the image directly from the source:

```bash
# Build the image
docker build -t switchcraft-web .

# Run the container (Mapping port 8080)
# We map a volume to persist configuration AND user database
docker run -d \
  -p 8080:8080 \
  -v switchcraft_data:/root/.switchcraft \
  --name switchcraft \
  switchcraft-web
```

Access the application at: `http://localhost:8080`

## 🔐 Authentication & User Management

The Docker container includes a full **User Management System**.

### Default Login
- **Username:** `admin`
- **Password:** `admin` (You should change this immediately in the Admin Panel)

### Multi-User Support
The server supports multiple users with distinct roles (`admin` or `user`).
- **Admins** have access to the `/admin` dashboard to manage users and server settings.
- **Users** can access the application tools but cannot modify server settings or other users.

### Single Sign-On (SSO) Setup
SwitchCraft supports OAuth2 login via **GitHub** and **Microsoft Entra ID (Office 365)**.
To enable SSO, you must provide the following environment variables when running the Docker container.

#### 1. Microsoft Entra ID (O365)
Register an App in Azure AD -> App Registrations.
*   **Redirect URI:** `http://<your-domain>:8080/oauth_callback/entra`
*   **API Permissions:** `User.Read` (Delegated)

```bash
docker run -d ... \
  -e SC_ENTRA_CLIENT_ID="<your-client-id>" \
  -e SC_ENTRA_TENANT_ID="<your-tenant-id>" \
  -e SC_ENTRA_CLIENT_SECRET="<your-client-secret>" \
  -e SC_BASE_URL="http://myserver.com:8080" \
  switchcraft-web
```

*Users logging in via Entra for the first time will be **automatically created** as normal users.*

#### 2. GitHub
Register an OAuth App in GitHub Developer Settings.
*   **Callback URL:** `http://<your-domain>:8080/oauth_callback/github`

```bash
docker run -d ... \
  -e SC_GITHUB_CLIENT_ID="<your-client-id>" \
  -e SC_GITHUB_CLIENT_SECRET="<your-client-secret>" \
  switchcraft-web
```

## ⚙️ Administration Dashboard

Access the dashboard at `http://localhost:8080/admin` (Link in Footer).

### Features
1.  **User Management**:
    *   **List Users:** See all registered accounts (Local and SSO).
    *   **Add User:** Manually create accounts with passwords.
    *   **Delete User:** Remove accounts (except the root admin).
2.  **Server Settings**:
    *   **Demo Mode:** Switch app to Read-Only mode.
    *   **Disable Auth:** Allow public access without login (Auto-Login as Guest/Admin).
3.  **Security**:
    *   **Change Password:** Update your own password.
    *   **MFA / 2FA:** Setup Time-based OTP (Google Authenticator) enforcement.

## 💾 Persistence

To keep your users and settings safe, mount the `/root/.switchcraft` volume.

| Path | Purpose |
| :--- | :--- |
| `server/auth_config.json` | Stores Global Server Config (Secret Keys, Demo Mode). |
| `server/users.json` | **User Database** (Usernames, Password Hashes, Roles). |
| `users/<username>/config.json` | (Future) Server-side user profiles. |

## 🌐 Web Architecture Notes

*   **Session Storage:** Login sessions use secure, encrypted cookies valid for 24 hours.
*   **Client Settings:** Currently, app preferences (Theme, etc.) are stored in the **Browser** (LocalStorage) to ensure fast load times. We are working on server-side roaming profiles for the next release.
*   **File Access:** The web version runs in a sandbox. You cannot access the host filesystem directly. Use the Upload/Download features.

## 🛠 Troubleshooting

*   **SSO Redirect Error?** Ensure `SC_BASE_URL` matches exactly the URL you access in the browser (including http/https and port).
*   **Locked Out?**
  *   `docker exec -it switchcraft sh`
  *   Delete `server/users.json` to reset the database (recreating default admin).
  *   Or manually edit `server/users.json` if you know JSON syntax.
