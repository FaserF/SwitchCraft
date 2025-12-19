#!/bin/bash
# SwitchCraft Release Builder (Linux/macOS)

set -e # Exit on error

echo "=========================================="
echo "   SwitchCraft Release Builder (Unix)     "
echo "=========================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH."
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
echo "Project Root: $REPO_ROOT"

# 1. Install Dependencies
echo -e "\n[1/4] Installing/Updating Deployment Dependencies..."
# Ensure pip is available
if ! python3 -m pip --version &> /dev/null; then
     echo "Error: pip is missing."
     exit 1
fi

python3 -m pip install --upgrade pyinstaller
python3 -m pip install .

# 2. Build
echo -e "\n[2/4] Building Executable..."
if [ ! -f "switchcraft.spec" ]; then
    echo "Error: switchcraft.spec not found."
    exit 1
fi

python3 -m PyInstaller switchcraft.spec --clean --noconfirm

# 3. Locate Artifact
# PyInstaller on Unix creates no extension or just binary name usually.
# Assuming 'SwitchCraft' (Linux/Mac) or 'SwitchCraft.exe' if cross compiling (not handled),
# or 'SwitchCraft.app' on Mac (if configured for bundle).
# Spec file usually defines name. Default is 'SwitchCraft' on Unix.

BUILT_BIN="$REPO_ROOT/dist/SwitchCraft-windows"
if [ ! -f "$BUILT_BIN" ]; then
    # Fallback check for .exe too just in case
    if [ -f "$REPO_ROOT/dist/SwitchCraft-windows.exe" ]; then
        BUILT_BIN="$REPO_ROOT/dist/SwitchCraft-windows.exe"
    else
        echo "Error: Build output not found at $BUILT_BIN"
        exit 1
    fi
fi

# 4. Move to Downloads
echo -e "\n[3/4] Moving Artifact..."
DOWNLOADS_DIR="$HOME/Downloads"
TARGET_BIN="$DOWNLOADS_DIR/$(basename "$BUILT_BIN")"

cp -f "$BUILT_BIN" "$TARGET_BIN"
chmod +x "$TARGET_BIN"

echo -e "\n[4/4] Done!"
echo "Success! Copied to: $TARGET_BIN"
echo "You can now run it from your Downloads folder."
