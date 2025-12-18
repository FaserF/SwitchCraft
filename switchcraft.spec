# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import customtkinter
import tkinterdnd2
from pathlib import Path

block_cipher = None

# Helper to find package data
def get_package_data(package):
    path = os.path.dirname(package.__file__)
    return (path, os.path.basename(path))

ctk_path, ctk_name = get_package_data(customtkinter)
tkdnd_path, tkdnd_name = get_package_data(tkinterdnd2)

datas = [
    (ctk_path, ctk_name),
    (tkdnd_path, tkdnd_name),
    ('images/switchcraft_logo.png', '.'),
    ('src/switchcraft/assets', 'switchcraft/assets'),
]

a = Analysis(
    ['src/switchcraft/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['PIL._tkinter_finder', 'tkinterdnd2', 'plyer.platforms.win.notification', 'defusedxml'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude sensitive modules to avoid Virus False Positives
    excludes=['py7zr', 'switchcraft_advanced'],
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
    name='SwitchCraft',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True, # GUI mode (Debug: True to see errors)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='images/switchcraft_logo.png', # Assuming we convert png to ico or pyinstaller handles it (it prefers ico)
    version='file_version_info.txt'
)
