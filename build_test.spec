# -*- mode: python ; coding: utf-8 -*-
import sys
import os

BASE_DIR = os.getcwd()

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('bin/sing-box.exe', 'bin'),
        ('bin/xray.exe', 'bin'),
        ('bin/wintun.dll', 'bin'),
        ('bin/AmneziaLib.dll', 'bin'),
        ('bin/tunnel.dll', 'bin'),
        ('bin/tunnel_service.exe', 'bin'),
        ('bin/flux.ico', 'bin'),
        ('assets/flags/*.png', 'assets/flags'),
        ('LICENSE', '.'),
        ('THIRD_PARTY_NOTICES.md', '.'),
    ],
    hiddenimports=[
        'core.crypto',
        'core.flags',
        'core.proxy_parser',
        'core.subscription',
        'core.settings_manager',
        'core.config_builder',
        'core.dual_mgr',
        'core.log_utils',
        'ui.main_window',
        'ui.sub_tab',
        'ui.servers_tab',
        'ui.settings_tab',
        'ui.log_tab',
        'ui.tray',
        'ui.styles',
        'ui.animations',
        'ui.toast',
        'ui.widgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'PyQt5',
        'PySide6',
        'pandas',
        'numpy',
        'matplotlib',
        'scipy',
        'PIL',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Flux_test',
    distpath=str(os.path.join(BASE_DIR, 'test_build')),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon='bin/flux.ico',
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    manifest='flux.exe.manifest',
)
