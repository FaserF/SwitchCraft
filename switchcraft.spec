import os
import customtkinter
import tkinterdnd2
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_all

src_root = os.path.abspath('src')
if src_root not in sys.path:
    sys.path.insert(0, src_root)

block_cipher = None

# Collect all submodules, binaries and data files from the package
sc_datas, sc_binaries, sc_hidden_imports = collect_all('switchcraft')

# MANUAL COLLECTION to ensure robustness
hidden_imports = list(set(sc_hidden_imports + [
    'PIL._tkinter_finder', 'tkinterdnd2', 'plyer.platforms.win.notification',
    'defusedxml', 'winotify', 'switchcraft.services.addon_service',
    'py7zr', 'py7zr.archiveinfo', 'py7zr.compressor', 'py7zr.helpers',
]))

# Helper to find package data
def get_package_data(package):
    path = os.path.dirname(package.__file__)
    return (path, os.path.basename(path))

ctk_path, ctk_name = get_package_data(customtkinter)
tkdnd_path, tkdnd_name = get_package_data(tkinterdnd2)

datas = sc_datas + [
    (ctk_path, ctk_name),
    (tkdnd_path, tkdnd_name),
    ('images/switchcraft_logo.png', '.'),
    ('src/switchcraft/assets', 'assets'),
]

a = Analysis(  # noqa: F821
    ['src/entry.py'],
    pathex=[os.path.abspath('src')],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[os.path.abspath('hooks')],
    hooksconfig={},
    runtime_hooks=[],
    # Excludes - empty for now (py7zr needed by addons at runtime)
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SwitchCraft',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    # Console: Conditional based on environment variable for debugging.
    console=os.environ.get('SWITCHCRAFT_DEBUG_CONSOLE', '0') == '1',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='images/switchcraft_logo.png',  # Assuming we convert png to ico or pyinstaller handles it (it prefers ico)
    version='file_version_info.txt'
)
