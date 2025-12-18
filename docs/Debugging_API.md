# Debugging API & CLI-Only Architecture

## Overview
This document defines the "Debugging API" approach for SwitchCraft (formerly referred to as Google Antigravity internally). By decoupling core logic from the interface, we enable high-speed iteration and AI-optimized troubleshooting.

## Architecture
- **Core Logic**: Independent module containing all functional code (Analyzers, Services, Utilities).
- **GUI Layer**: Optional wrapper (`switchcraft.gui`) for visual interaction using CustomTkinter.
- **CLI Layer**: Direct interface (`switchcraft.main`) to the Core Logic for headless operations.

## Build Targets
1. **Standard (Default)**: Includes GUI + CLI. Distributes as `SwitchCraft.exe`. Best for end-users.
2. **CLI-Only**:
   - Triggered via `BUILD_CLI_ONLY=1` environment variable during PyInstaller build.
   - Excludes `switchcraft.gui`, `customtkinter`, `tkinter`, `PIL`, etc.
   - Faster compilation and minimal disk footprint.
   - Used for "Debugging API" workflows.
   - Distributes as `SwitchCraft-CLI.exe`.

## AI-Optimized Debugging (The API)
The CLI-only version acts as a Debugging API. If a crash or functional error occurs, an AI agent can:
1. **Execute commands via CLI**: `SwitchCraft-CLI.exe <installer_path> --json`
2. **Parse verbose English logs**: Structured JSON output ensures machine readability.
3. **Verify Fixes**: Recompile only the CLI target to verify logic changes in seconds.

## Automated Releases
GitHub Actions is configured to provide:
- `SwitchCraft.exe` (GUI + CLI)
- `SwitchCraft-CLI.exe` (CLI only, optimized for speed)

## Usage
### Running CLI Check
```powershell
SwitchCraft-CLI.exe "C:\Path\To\Setup.exe" --json
```

### Diagnostic Mode
```powershell
SwitchCraft-CLI.exe --diagnose
```
(Prints dependency status, config loaded, and environment info)
