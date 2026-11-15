# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app_worker.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['gspread', 'google.oauth2.credentials', 'google.oauth2.service_account', 'google_auth_oauthlib.flow', 'license_manager', 'urllib3'],
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
    a.binaries,
    a.datas,
    [],
    name='CyberFarm',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
