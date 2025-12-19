# CI Architecture & Build System

## Continuous Integration Strategy
This project uses GitHub Actions for automated testing and releases.

### Workflows
- **`release.yml`**: Builds and releases the application.
  - **Standard Build**: Windows (GUI+CLI), Linux, MacOS.
  - **CLI-Only Build**: Dedicated job `build_cli` running on Windows. Uses caching for speed.
- **`test.yml`**: Runs `pytest` and linting.

### Pip Project Structure
The `pyproject.toml` is configured to support a modular installation:
- **Core (Default)**: `pip install .` -> Installs only logic and CLI. Fast, no heavy GUI assets.
- **GUI (Optional)**: `pip install .[gui]` -> Installs `customtkinter`, `pillow`, etc.

### Automated Builds
Every release generates two Windows executables:
1. **`SwitchCraft-windows.exe`**: Full application with GUI.
2. **`SwitchCraft-CLI-windows.exe`**: Lightweight (<15MB), headless tool.

### Running Tests Locally
To test the core logic without GUI dependencies:
```bash
# Install core
pip install .

# Run tests
pytest tests
```
To run full tests including GUI components:
```bash
# Install full
pip install .[gui]

# Run tests
pytest tests
```
