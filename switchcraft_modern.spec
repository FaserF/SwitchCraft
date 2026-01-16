# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# MANUAL COLLECTION for Modern
# We need switchcraft.* and flet
hidden_imports = [
    'flet', 'flet_desktop', 'defusedxml', 'winotify', 'requests',
    'xml.parsers.expat', 'pyexpat',
    'switchcraft.utils', 'switchcraft.utils.config', 'switchcraft.utils.app_updater',
    'switchcraft.gui', 'switchcraft.gui_modern',
    'switchcraft.controllers', 'switchcraft.services', 'switchcraft.gui_modern.utils',
    'switchcraft.gui_modern.app',
    # Explicitly include all views for PyInstaller to find them
    'switchcraft.gui_modern.views.crash_view',
    'switchcraft.gui_modern.views.packaging_wizard_view',
    'switchcraft.gui_modern.views.analyzer_view',
    'switchcraft.gui_modern.views.winget_view',
    'switchcraft.gui_modern.views.home_view',
    'switchcraft.gui_modern.views.intune_view',
    'switchcraft.gui_modern.views.settings_view',
    'switchcraft.gui_modern.views.history_view',
    'switchcraft.gui_modern.views.script_upload_view',
    'switchcraft.gui_modern.views.helper_view',
    'switchcraft.gui_modern.views.macos_wizard_view',
    'switchcraft.gui_modern.views.group_manager_view',
    'switchcraft.gui_modern.views.stack_manager_view',
    'switchcraft.gui_modern.views.detection_tester_view',
    'switchcraft.gui_modern.views.intune_store_view',
    'switchcraft.gui_modern.views.library_view',
    'switchcraft.gui_modern.views.dashboard_view',
]

# Collect everything from gui_modern.views explicitly to be safe
try:
    views_submodules = collect_submodules('switchcraft.gui_modern.views')
    hidden_imports += views_submodules
except Exception as e:
    print(f"WARNING: Failed to collect view submodules: {e}")

# Collect all other submodules but exclude addon modules that are not part of core
all_submodules = collect_submodules('switchcraft')
# Filter out modules that were moved to addons or don't exist
excluded_modules = ['switchcraft.utils.winget', 'switchcraft.gui.views.ai_view', 'switchcraft_winget', 'switchcraft_ai', 'switchcraft_advanced', 'switchcraft.utils.updater']
hidden_imports += [m for m in all_submodules if not any(m.startswith(ex) for ex in excluded_modules)]

# Deduplicate
hidden_imports = list(set(hidden_imports))

src_root = os.path.abspath('src')
if src_root not in sys.path:
    sys.path.insert(0, src_root)

datas = [
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
    icon='src/switchcraft/assets/switchcraft_logo.ico',
    version='file_version_info.txt'
)
