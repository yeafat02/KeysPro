# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all


ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")
dnd_datas, dnd_binaries, dnd_hiddenimports = collect_all("tkinterdnd2")
datas = ctk_datas + dnd_datas
binaries = ctk_binaries + dnd_binaries
hiddenimports = ctk_hiddenimports + dnd_hiddenimports

analysis = Analysis(
    ["src/keyspro/app.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="KeysPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
