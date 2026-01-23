# Detection Tester

The **Detection Tester** allows you to validate Intune detection logic *locally* before uploading to the cloud. This saves massive amounts of time by avoiding the "Upload -> Sync -> Wait -> Fail -> Retry" cycle.

## Supported Detection Types

### 1. File / Folder
Check for the existence or properties of a file.
*   **Path**: e.g., `C:\Program Files\MyApp\app.exe`
*   **Method**: Exists, Date Modified, Version, Size.
    *   *Example*: Check if `app.exe` version is `>= 2.0.0.0`.

### 2. Registry
Check for keys or values in the Windows Registry.
*   **Root**: `HKLM` (System) or `HKCU` (User).
*   **Key Path**: e.g., `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{GUID}`.
*   **Value Name**: e.g., `DisplayVersion`.
*   **Comparison**: String comparison, Integer equals, Exists.

### 3. PowerShell Script
Run a custom script to determine presence.
*   **Logic**: The script must write to `STDOUT` and exit with code `0` to be considered "Detected". Any other exit code or no output means "Not Detected".
*   **Editor**: You can paste your script directly into the tester window.

## Usage
1.  Define your rule.
2.  Click **Test Now**.
3.  **Result**:
    *   **DETECTED (Green)**: The rule passed.
    *   **NOT DETECTED (Orange)**: The rule failed (the app is not considered installed).
    *   **ERROR (Red)**: Logic error (e.g., path not found, syntax error).

## Use Case
Always run your detection rules here after installing the app on your test machine. If SwitchCraft says "DETECTED", Intune will likely say "Installed".
