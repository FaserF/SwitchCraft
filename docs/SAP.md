# SAP Management

SwitchCraft provides specialized tools for managing SAP Installation Servers (`nwsetupadmin`). This tool automates common administrative tasks like merging updates, customizing the GUI appearance, and forcing browser preferences.

## Key Features

- **Automated Update Merging**: Easily integrate SAP GUI patches and add-ons using the `/UpdateServer` command-line interface.
- **Logo Customization**: Automatically distribute custom company logos to all clients by integrated them into the installation server.
- **Edge WebView2 Enforcement**: Force the use of Edge WebView2 as the default browser engine for SAP GUI transactions by patching the `SapGuiSetup.xml` configuration.
- **Guided Multi-Step Wizard**: A specialized UI that walks you through the entire process from server selection to finalized packaging.

## Usage Guide

### 1. Select Installation Server
Point SwitchCraft to the root directory of your SAP Installation Server. The tool will look for `NwSapSetupAdmin.exe` in the `Setup` subfolder.

### 2. Merge Updates
Select one or more SAP update executables. SwitchCraft will execute the merge process in the background, ensuring your server is up to date with the latest patches.

### 3. Customization
- **Edge WebView2**: Check this option to ensure all clients use the modern WebView2 engine.
- **Custom Logo**: Select a `.png` file to be used as the branding logo in the SAP GUI.

### 4. Finalize & Package
Once customized, you can trigger the creation of a **Single-File Installer (SFU)**. This creates a self-extracting executable that contains only the necessary components for a silent, standalone deployment.

## Technical Details

The tool interacts with the SAP Setup infrastructure via:
- **CLI**: `NwSapSetupAdmin.exe` for server updates and SFU compression.
- **XML Patching**: Direct manipulation of `Setup\SapGuiSetup.xml` for specific preference overrides that are not exposed via standard CLI arguments.
