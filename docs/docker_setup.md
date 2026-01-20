# SwitchCraft Web App (Docker) Guide

## Overview
SwitchCraft can be deployed as a Dockerized Web Application using Flet. This provides a web-accessible version of the packaging tool.

## Deployment

### Prerequisites
- Docker Engine
- Git

### Build & Run
1. **Build the Image**
   ```bash
   docker build -t switchcraft-web .
   ```

2. **Run the Container**
   ```bash
   docker run -d -p 8080:8080 --name switchcraft switchcraft-web
   ```
   Access the app at `http://localhost:8080`.

## Configuration
The application uses environment variables for configuration in Docker.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SC_AUTH_PROVIDER` | Auth provider (`github`, `entra`, `none`) | `none` |
| `SC_GITHUB_CLIENT_ID` | GitHub App Client ID | - |
| `SC_GITHUB_CLIENT_SECRET` | GitHub App Client Secret | - |
| `SC_SESSION_SECRET` | Secret key for session encryption | (Random) |
| `SC_DISABLE_WINGET_INSTALL` | Set `1` to skip Winget check (Use static fallback) | `0` |

## Limitations vs Desktop
- **Winget Search**: Relies on a static dataset of ~50 popular apps or external APIs. Results may differ from Desktop Winget CLI.
- **Intune Upload**: Requires Azure authentication which may need device code flow.
- **Local Files**: Browser sandbox applies; file upload/download is used instead of direct file system access.

## Troubleshooting
- **No Search Results?** The app uses a fallback static dataset if public APIs are unreachable.
- **Login Fails?** Ensure `SC_GITHUB_CLIENT_ID` and `SECRET` are set correctly if using GitHub auth.
