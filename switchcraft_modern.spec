# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# MANUAL COLLECTION for Modern
# We need switchcraft.* and flet
hidden_imports = ['flet', 'flet_desktop', 'defusedxml', 'winotify', 'switchcraft.utils', 'switchcraft.utils.config', 'switchcraft.gui', 'switchcraft.gui_modern']

# Collect submodules but exclude addon modules that are not part of core
all_submodules = collect_submodules('switchcraft')
# Filter out modules that were moved to addons or don't exist
excluded_modules = ['switchcraft.utils.winget', 'switchcraft.gui.views.ai_view', 'switchcraft_winget', 'switchcraft_ai', 'switchcraft_advanced']
hidden_imports += [m for m in all_submodules if not any(m.startswith(ex) for ex in excluded_modules)]

src_root = os.path.abspath('src')
if src_root not in sys.path:
    sys.path.insert(0, src_root)

datas = [
    ('images/switchcraft_logo.png', '.'),
    ('images/switchcraft_logo.ico', '.'),
    ('src/switchcraft/assets', 'assets'),
]

# Analysis for Modern (Flet)
a = Analysis(
    ['src/switchcraft/modern_main.py'],
    pathex=[os.path.abspath('src')],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='SwitchCraft', # Modern (Flet) is now the main 'SwitchCraft'
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Windowed app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='images/switchcraft_logo.ico',
    version='file_version_info.txt'
)
