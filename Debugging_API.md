# Debugging API & CLI-Only Architecture

## Overview
This document defines the "Debugging API" approach for this project. By decoupling core logic from the interface, we enable high-speed iteration and AI-optimized troubleshooting.

## Architecture
- Core Logic: Independent module containing all functional code.
- GUI Layer: Optional wrapper for visual interaction.
- CLI Layer: Direct interface to the Core Logic for headless operations.

## Build Targets
1. Standard (Default): Includes GUI + CLI. Best for end-users.
2. CLI-Only:
   - Triggered via `--cli-only` build flag.
   - No graphical dependencies or assets.
   - Faster compilation and minimal disk footprint.
   - Used for "Debugging API" workflows.

## AI-Optimized Debugging
The CLI-only version acts as a Debugging API. If a crash or functional error occurs, an AI agent can:
- Execute commands via CLI.
- Parse verbose English logs and stack traces.
- Modify code and re-verify fixes instantly without GUI compilation delays.

## Automated Releases
GitHub Actions is configured to provide:
- `projectname-full-win.exe` (GUI + CLI)
- `projectname-cli-win.exe` (CLI only, optimized for speed)
