# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# CLI-Only Build Spec
# Goal: Minimal size, fast startup, no GUI dependencies.

src_root = os.path.abspath('src')
if src_root not in sys.path:
    sys.path.insert(0, src_root)

# Collect submodules but force exclude GUI
hidden_imports = collect_submodules('switchcraft')
# Remove any gui modules if collected by accident
hidden_imports = [m for m in hidden_imports if not m.startswith('switchcraft.gui')]

a = Analysis(
    ['src/switchcraft/cli_main.py'],
    pathex=[os.path.abspath('src')],
    binaries=[],
    datas=[
        # Only CLI-relevant assets (e.g. lang files if needed for CLI output? currently minimal)
        # Assuming English enforced, maybe no assets needed?
        # Let's keep minimal assets if needed in future
    ],
    hiddenimports=hidden_imports,
    hookspath=[os.path.abspath('hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'Tkinter',
        'customtkinter',
        'tkinterdnd2',
        'PIL',
        'Pillow',
        'switchcraft.gui',
        'switchcraft.assets', # Exclude images
        'py7zr', # Keep exclude from main if valid
        'matplotlib', 'numpy', 'scipy', 'pandas' # Common heavy libs just in case
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SwitchCraft-CLI', # Distinct name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False, # Set to True for even smaller?
    upx=True, # Compress
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True, # ALWAYS CONSOLE
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='file_version_info.txt'
)
