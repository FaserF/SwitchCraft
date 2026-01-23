# Winget Explorer

The **Winget Explorer** provides a graphical interface for the Windows Package Manager (winget), allowing you to search, install, and manage applications from the official Microsoft repository.

## Purpose
Winget Explorer simplifies software discovery and deployment by wrapping the command-line `winget` tool in a modern UI. It allows IT professionals to quickly find package IDs, download installers for offline use, or install software directly.

## Interface Overview

### 1. Search Bar
*   **Input**: Enter the name, publisher, or tag of an application.
*   **Search Button**: Executing `winget search`.
*   **Results**: Displays a list of matching packages with:
    *   **Name**: Application name.
    *   **ID**: The unique Package ID (e.g., `Google.Chrome`).
    *   **Version**: Latest available version.
    *   **Source**: Repository source (usually `winget` or `msstore`).

### 2. Package Actions
Clicking on a search result (or using the dots menu) offers:

*   **Install**: Installs the application on your local machine using `winget install`.
*   **Download Installer**: Downloads the raw installer file (`.exe` / `.msi`) to your Downloads folder.
    *   *Useful for packaging apps that don't have direct download links.*
*   **Show Details**: Displays full metadata (Description, Homepage, License, Hash).
*   **Copy ID**: Copies the Package ID to clipboard (e.g., for use in scripts).

### 3. Bulk Operations (Import/Export)
*   **Import (package.json / .xml)**: Allows you to install a list of applications from a WinGet export file.
*   **Export Installed**: Generates a list of all apps installed on your current machine.

## Integration
*   **Analyzer Integration**: Downloaded installers can be sent directly to the **Analyzer** tab for inspection.
*   **Intune Integration**: You can generate Intune apps directly from Winget packages (via the 'Download & Package' workflow).

## Troubleshooting
*   **"Winget not found"**: Ensure App Installer is updated in the Microsoft Store.
*   **Search failed**: Check your internet connection. Some corporate firewalls block the Winget CDN.
