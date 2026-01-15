# Winget Integration 📦

SwitchCraft deeply integrates with **Winget** (Windows Package Manager) to simplify application discovery, analysis, and deployment.

## 🔎 Winget Analyzer Hint

When analyzing any installer (EXE/MSI), SwitchCraft automatically searches Winget for a matching package.
- If a match is found, a **"View on Winget"** button appears in the analysis results.
- This allows you to quickly verify if an upstream package already exists, potentially saving you the effort of packaging it yourself.

## 🏪 Winget Store Tab

The **Winget Store** tab provides a built-in interface to browse the entire Winget catalog.

### Features
1.  **Search**: Find applications by name or ID.
2.  **Deep Details**: View Description, Publisher, License, Hashes, and URLs.
3.  **Local Installation**: Install apps directly on your machine (User or System scope).

### 🚀 Intune Deployment

You can deploy apps from the Winget Store directly to Microsoft Intune with a single click.

#### Method 1: Winget-AutoUpdate (Recommended)
Generates a robust PowerShell script that uses the Winget client on the end-user's machine to install and update the application.
- **Pros**: Always installs the latest version (or specific version pinned); handled by the OS.
- **SwitchCraft Automation**:
    - Generates the `install.ps1` / `uninstall.ps1` script.
    - **Smart Metadata**: Automatically fills the Intune App Name, Description, Publisher, URLs, and Notes based on the Winget manifest.

#### Method 2: Download & Package (Internal)
Classic packaging workflow.
1.  Downloads the actual installer (EXE/MSI) from the vendor.
2.  Sends it to the **Analyzer** tab for inspection.
3.  You can then wrap it into an `.intunewin` file using your custom templates or SwitchCraft's defaults.

## 📝 WingetCreate Manager

The **WingetCreate Manager** (Modern UI only) allows you to create and manage Winget manifests for publishing packages to Microsoft's repository.

### Features
- **Manifest Creation**: Generate Winget manifests from existing packages
- **GitHub Integration**: Create pull requests directly to the winget-pkgs repository
- **Version Management**: Update existing manifests with new versions
- **Validation**: Validate manifests before submission

### Using WingetCreate Manager

1. Navigate to **Tools → WingetCreate Manager**
2. Select a package or enter package details
3. Configure manifest settings (Publisher, Package Identifier, etc.)
4. Generate the manifest
5. Submit to GitHub (requires GitHub token in settings)

> [!NOTE]
> Requires `wingetcreate` CLI tool and GitHub token for repository access.

## ⚙️ Configuration

You can enable/disable Winget integration in **Settings > General > Enable Winget Integration**.
