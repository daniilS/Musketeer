# -*- mode: python ; coding: utf-8 -*-
import platform
import sys

from PyInstaller.utils.hooks import collect_all

import musketeer

datas = [("Assets.car", ".")] if sys.platform == "darwin" else []
binaries = []
hiddenimports = ["musketeer"]
tmp_ret = collect_all("musketeer")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]


a = Analysis(
    ["musketeer_loader.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [("O", None, "OPTION"), ("O", None, "OPTION")],
    exclude_binaries=True,
    name="Musketeer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=platform.machine(),
    codesign_identity=None,
    entitlements_file=None,
    icon=["Musketeer.ico" if sys.platform == "win32" else "Musketeer.icns"],
    version="version_info.txt" if sys.platform == "win32" else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Musketeer",
)
app = BUNDLE(
    coll,
    name="Musketeer.app",
    icon="Musketeer.icns",
    bundle_identifier="daniilS.musketeer",
    version=musketeer.__version__,
    info_plist={"CFBundleIconName": "Musketeer"},
)
