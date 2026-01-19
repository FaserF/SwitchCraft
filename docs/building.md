# Building from Source

Build SwitchCraft yourself for development or customization.

## Prerequisites

| Tool | Version | Required |
|------|---------|----------|
| **Python** | 3.10+ | ✅ |
| **Git** | Latest | ✅ |
| **Node.js** | 18+ | For docs only |

## Quick Build

### Windows

```powershell
# Clone the repository
git clone https://github.com/FaserF/SwitchCraft.git
cd SwitchCraft

# Run the build script
.\scripts\build_release.ps1
```

The executable will be placed in your `Downloads` folder.

### Linux / macOS

```bash
# Clone the repository
git clone https://github.com/FaserF/SwitchCraft.git
cd SwitchCraft

# Run the build script
./scripts/build_release.sh
```

## Manual Build Steps

### 1. Set Up Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. Build with PyInstaller

**Modern Edition:**
```powershell
pyinstaller switchcraft_modern.spec
```

**Legacy Edition:**
```powershell
pyinstaller switchcraft_legacy.spec
```

**CLI Only:**
```powershell
pyinstaller switchcraft_cli.spec
```

### 3. Create Installer (Optional)

Requires [Inno Setup](https://jrsoftware.org/isinfo.php):

```powershell
# Modern installer
iscc switchcraft_modern.iss

# Legacy installer
iscc switchcraft_legacy.iss
```

## Development Mode

Run SwitchCraft directly from source for faster iteration:

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run Modern UI
python -m switchcraft.gui_modern.app

# Run Legacy UI
python -m switchcraft.gui.app

# Run CLI
python -m switchcraft.cli
```

## Project Structure

```
SwitchCraft/
├── src/
│   └── switchcraft/
│       ├── core/           # Core analysis logic
│       ├── cli/            # Command-line interface
│       ├── gui/            # Legacy Tkinter UI
│       ├── gui_modern/     # Modern Flet UI
│       └── utils/          # Shared utilities
├── docs/                   # Documentation (VitePress)
├── scripts/                # Build scripts
├── tests/                  # Test suite
└── *.spec                  # PyInstaller specs
```

## Running Tests

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=switchcraft

# Run specific test file
pytest tests/test_analyzer.py
```

## Linting

```powershell
# Check code style
ruff check src/

# Auto-fix issues
ruff check src/ --fix
```

## Building Documentation

```powershell
cd docs
npm install
npm run dev      # Development server (VitePress - secure)
npm run build    # Production build
```

> [!WARNING]
> **Security Note**: The documentation uses VitePress, which handles esbuild securely. If you add custom build scripts using esbuild's `serve` feature directly, be aware of the [CORS security vulnerability](SECURITY.md#-development-server-security). Always restrict CORS to localhost only and never expose the dev server to external networks.

## Troubleshooting

### PyInstaller Issues

**"Module not found" errors:**
```powershell
# Clean build directories
Remove-Item -Recurse -Force build, dist
pyinstaller --clean switchcraft_modern.spec
```

**Antivirus false positives:**
- Add exclusions for the `build/` and `dist/` directories
- Use a code signing certificate for production builds

### Flet Build Issues

**Port already in use:**
```powershell
# Kill existing Flet processes
Get-Process -Name "flet*" | Stop-Process -Force
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

> [!NOTE]
> All PRs must pass CI checks (lint, test, build) before merging.
