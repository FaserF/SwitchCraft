# Packaging Wizard

The **Packaging Wizard** is a guided, step-by-step workflow designed for users who want a structured approach to packaging, rather than using individual tools like the Analyzer or Intune Packager separately.

## Workflow

### Step 1: Input
Select your installer file. The Wizard immediately runs a background analysis to pre-fill information for the next steps.

### Step 2: Analysis & Configuration
Review the detected details:
*   **Name & Version**: Extracted from metadata.
*   **Install Arguments**: Detected silent switches.
*   *You can override these values if the detection was incorrect.*

### Step 3: Script Generation
Choose a template (e.g., "Standard EXE", "MSI with Logging"). The Wizard generates an `Install-App.ps1` wrapper script automatically.

### Step 4: Output
Choose your target:
*   **Local Folder**: Just save the script and files.
*   **Intune Package**: Create an `.intunewin` file.
*   **Publish (Optional)**: If configured, upload completely to Intune.

## When to use?
*   **Beginners**: Use the Wizard to ensure you don't miss any steps (like signing scripts or creating uninstall commands).
*   **Routine Updates**: Perfect for quickly packaging a standard update (e.g., new Adobe Reader version) where the workflow is predictable.
