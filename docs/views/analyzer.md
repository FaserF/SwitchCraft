# Installer Analyzer

The **Installer Analyzer** is a core component of SwitchCraft designed to inspect installer files (`.exe`, `.msi`, `.msp`) and determine the correct silent installation parameters automatically.

## Purpose
Packaging applications for enterprise deployment (Intune, SCCM) requires knowing how to install software silently (without user interaction). The Analyzer automates the discovery of these "switches" using a combination of:
*   **Signature Matching**: Detecting known installer frameworks (Inno Setup, NSIS, InstallShield, WiX, etc.).
*   **Brute Force Analysis**: Attempting common patterns if signatures fail.
*   **Universal Extraction**: Inspecting internal file structures.
*   **Community Database**: Checking a hash-based cloud database for known switches.

## Interface Overview

### 1. Drag & Drop Zone
*   **Location**: Top of the view.
*   **Function**: Drag any `.exe` or `.msi` file here to immediately start analysis.
*   **Supported Formats**: Executables, MSI Packages, MSP Patches.

### 2. Analysis Results
Once a file is analyzed, the following sections appear:

*   **Primary Info Table**: Displays Product Name, Version, Manufacturer, and Installer Type.
*   **Silent Install Parameters**: The discovered command-line arguments for silent installation (e.g., `/S`, `/VERYSILENT /SUPPRESSMSGBOXES`).
    *   *Click the Copy icon to copy these to your clipboard.*
*   **Silent Uninstall Parameters**: Arguments to remove the application silently.

### 3. Action Buttons
These buttons provide quick workflows based on the analysis:

*   **Auto Deploy (All-in-One)**:
    *   Generates a PowerShell script.
    *   Packages it as `.intunewin`.
    *   Uploads it to your configured Intune tenant (Settings required).
*   **Test Locally (Admin)**:
    *   Runs the installer *with the detected silent switches* on your local machine.
    *   **Note**: Requires Administrator privileges. You may be prompted to restart SwitchCraft as Admin.
*   **Winget Manifest**:
    *   Generates a preliminary Winget Manifest based on the analysis.
    *   Useful for submitting packages to the Windows Package Manager repository.

### 4. Advanced Tools

*   **Generate Intune Script**: Creates a standardized `Install-App.ps1` wrapper script using your templates.
*   **Create .intunewin**: Packages the installer and script into the format required by Microsoft Intune.
*   **Manual Commands**: Shows the raw CMD and PowerShell commands if you need to run them manually in a terminal.
*   **View Detailed Analysis Data**: Opens a raw log of the "Brute Force" and internal analysis logic. Use this if detection seems incorrect.

## Dependencies & Requirements
*   **Advanced Addon**: Required for "Universal Analysis" and deep inspection of complex EXE files.
    *   *If missing, a red warning banner will appear.*
*   **Internet Connection**: Required for Winget lookups and Community Database checks.
*   **Admin Rights**: Required for the "Test Locally" feature.

## Troubleshooting
*   **"Advanced Feature Required"**: Ensure you have installed the "Advanced" addon via **Settings > Help**.
*   **"Silent Installation Disabled"**: Some installers have anti-silent flags. The Analyzer will warn you if this is detected.
*   **Wrong Switches**: If the detected switches don't work, try "View Detailed Analysis Data" to see alternative suggestions, or check the vendor's documentation.
