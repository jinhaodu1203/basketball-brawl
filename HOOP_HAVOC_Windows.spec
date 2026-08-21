# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH)

datas = [
    (str(project_root / "assets"), "assets"),
    (str(project_root / "lang"), "lang"),
]

optional_files = [
    "README.md",
    "CRAFTPIX_LICENSE.txt",
    "LATEST_UPDATE.txt",
]

for name in optional_files:
    path = project_root / name
    if path.exists():
        datas.append((str(path), "."))

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
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
    icon='assets\\HOOP_HAVOC.ico',
    exclude_binaries=True,
    name="HOOP HAVOC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="HOOP HAVOC",
)
