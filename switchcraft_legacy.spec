# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import customtkinter
import tkinterdnd2
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# Helper to find package data
def get_package_data(package):
    path = os.path.dirname(package.__file__)
    return (path, os.path.basename(path))

ctk_path, ctk_name = get_package_data(customtkinter)
tkdnd_path, tkdnd_name = get_package_data(tkinterdnd2)

# MANUAL COLLECTION to ensure robustness
hidden_imports = ['PIL._tkinter_finder', 'tkinterdnd2', 'plyer.platforms.win.notification', 'defusedxml', 'winotify', 'switchcraft.services.addon_service']
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

datas = [
    (ctk_path, ctk_name),
    (tkdnd_path, tkdnd_name),
    ('src/switchcraft/assets', 'assets'),
]

a = Analysis(
    ['src/entry.py'], # Legacy uses src/entry.py or src/switchcraft/main.py (via entry.py)
    pathex=[os.path.abspath('src')],
    binaries=[],
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
