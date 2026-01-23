# Application Library

The **Library** is your local repository of packaged applications. It mirrors the folder structure defined in your **Git Repository Path** settings.

## Features
*   **Browse**: Navigate through your `Apps` folder structure.
*   **Metadata**: Select an app to see its:
    *   Version
    *   Detect Method (if stored in `metadata.json`)
    *   Install Command
*   **Actions**:
    *   **Edit Script**: Open the `Install-App.ps1` in your default code editor.
    *   **Reveal**: Open the folder in Windows Explorer.
    *   **Repackage**: Send the source files back to the **Intune Packager** to regenerate the `.intunewin` file.

## Structure
SwitchCraft expects a standard structure:
```
/Repo-Root
  /Apps
    /Google Chrome
      /v120.0
        Install-App.ps1
        Chrome.exe
        Chrome.intunewin
```
Keeping this structure allows the Library view to index your content effectively.
