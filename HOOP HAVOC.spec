# -*- mode: python ; coding: utf-8 -*-

# Cross-platform PyInstaller spec for HOOP HAVOC.
#
# macOS:   pyinstaller "HOOP HAVOC.spec"
#          -> dist/HOOP HAVOC.app
# Windows: .\build_windows.ps1
#          -> dist-windows/HOOP HAVOC/HOOP HAVOC.exe
#
# The Windows build writes to dist-windows/ and build-windows/ on purpose: the
# macOS dist/ and build/ trees are committed to the repository, and reusing them
# would overwrite hundreds of tracked files.

import os
import sys

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"

# Drop an .ico here to brand the Windows executable and taskbar entry.
# Without it PyInstaller falls back to its own default icon, which is fine for
# development but should be replaced before shipping on Steam.
_windows_icon = os.path.join("assets", "icon.ico")
windows_icon = _windows_icon if os.path.isfile(_windows_icon) else None

# Windows executables carry a VERSIONINFO resource shown in the file
# properties dialog. Absent on macOS, where Info.plist covers the same ground.
_version_file = "version_info.txt"
version_file = _version_file if IS_WINDOWS and os.path.isfile(_version_file) else None

# UPX is disabled on Windows: it is not installed by default there, and
# UPX-compressed executables regularly trip antivirus heuristics, which is a
# real problem for a game distributed to players.
use_upx = not IS_WINDOWS


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('lang', 'lang')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HOOP HAVOC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=use_upx,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=windows_icon,
    version=version_file,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=use_upx,
    upx_exclude=[],
    name='HOOP HAVOC',
)

if IS_MACOS:
    app = BUNDLE(
        coll,
        name='HOOP HAVOC.app',
        icon=None,
        bundle_identifier='com.jinhaodu.hoophavoc',
    )
