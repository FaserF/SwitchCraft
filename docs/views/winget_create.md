# Winget Create

**Winget Create** is an advanced tool for contributing back to the community. It assists in building valid YAML manifests for the Windows Package Manager Community Repository.

## Workflow
1.  **URL**: Paste the direct download URL of the installer.
2.  **Analysis**: The tool downloads the file temporarily to compute the SHA256 hash and detect architecture (x64/x86).
3.  **Metadata**: Fill in required fields:
    *   PackageIdentifier (Publisher.App)
    *   Version
    *   License / Copyright
    *   Short Description
4.  **Validation**: A validation check runs against schema v1.4+ to ensure no errors.
5.  **Export/Submit**:
    *   *Save Local*: Saves the YAML files (singleton or multi-file locale).
    *   *PR Helper*: (Coming Soon) Helps open a Pull Request to the `microsoft/winget-pkgs` repo.

## Tips
*   Always test the URL in a private browser window to ensure it's a direct link (not a redirect page).
*   Use the "Analyzer" first to get silent switches, then paste them here.
