# SwitchCraft Addon Guide

SwitchCraft supports an addon system to extend its functionality while keeping the core lightweight and compliant with antivirus heuristics (e.g., by separating Advanced/Intune analysis).

## Installing Addons

### Automatic Installation
SwitchCraft attempts to install addons automatically in the following order:
1.  **Local Cache**: Checks if the addon is present in `addons/` folder.
2.  **Current Release**: Downloads the matching zip from the GitHub Release for your version.
3.  **Main Branch**: Falls back to the latest code from the `main` branch.
4.  **Older Releases**: Scans previous releases for compatible assets.

### Manual Installation
If automatic installation fails, you can:
1.  **Browser Download**: Open the release page and download the addon ZIP manually.
2.  **Custom Upload**: In `Settings -> Help -> Addon Manager`, use the **"Upload Custom Addon"** button to select the downloaded ZIP file.

## Creating Custom Addons

Addons are standard Python packages located in the `addons/` directory.

### Structure
A valid addon ZIP must contain a top-level folder matching `switchcraft_<name>` or have that folder somewhere inside.

**Example Structure:**
```
my_addon.zip
└── switchcraft_myfeature/
    ├── __init__.py      # Required: Entry point
    ├── service.py       # Optional: Logic
    └── gui/
        └── view.py      # Optional: UI components
```

### Development
1.  Clone the SwitchCraft repository.
2.  Create a folder `src/switchcraft_<name>`.
3.  Implement your logic.
4.  To distribute, zip the folder `switchcraft_<name>`.

### Key Addon Types
-   **Advanced**: Provides Intune Graph API and Brute-force analysis tools.
-   **Winget**: Provides Winget CLI wrapper and repository search.
-   **AI**: Provides generic AI assistant interfaces.

## Security Warning
> [!WARNING]
> Only install addons from trusted sources (e.g., the official GitHub repository). Custom addons run with the same privileges as SwitchCraft.
