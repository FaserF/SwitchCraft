# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import customtkinter
import tkinterdnd2
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_all

# Use collect_all to properly gather all CustomTkinter assets including themes
ctk_datas, ctk_binaries, ctk_hidden_imports = collect_all('customtkinter')
tkdnd_datas, tkdnd_binaries, tkdnd_hidden_imports = collect_all('tkinterdnd2')

# MANUAL COLLECTION to ensure robustness
hidden_imports = ['PIL._tkinter_finder', 'plyer.platforms.win.notification', 'defusedxml', 'winotify', 'switchcraft.services.addon_service']
hidden_imports += list(set(ctk_hidden_imports + tkdnd_hidden_imports))
hidden_imports += collect_submodules('switchcraft')

# Manually walk src/switchcraft to find all modules
src_root = os.path.abspath('src')
if src_root not in sys.path:
    sys.path.insert(0, src_root)

import switchcraft
pkg_path = os.path.dirname(switchcraft.__file__)

for root, dirs, files in os.walk(pkg_path):
    for file in files:
        if file.endswith('.py') and not file == '__init__.py':
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, src_root)
            module_name = rel_path.replace(os.sep, '.').replace('.py', '')
            hidden_imports.append(module_name)
        elif file == '__init__.py':
             full_path = os.path.join(root, file)
             rel_path = os.path.relpath(root, src_root)
             module_name = rel_path.replace(os.sep, '.')
             hidden_imports.append(module_name)

# Combine all datas - CustomTkinter themes are now included via collect_all
datas = ctk_datas + tkdnd_datas + [
    ('src/switchcraft/assets', 'assets'),
]

# Include binaries if any
binaries = ctk_binaries + tkdnd_binaries

a = Analysis(
    ['src/entry.py'], # Legacy uses src/entry.py or src/switchcraft/main.py (via entry.py)
    pathex=[os.path.abspath('src')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports + ['switchcraft.utils', 'switchcraft.utils.config'],
    hookspath=[os.path.abspath('hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['py7zr'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SwitchCraft-Legacy',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/switchcraft/assets/switchcraft_logo.png',
    version='file_version_info_legacy.txt'
)
