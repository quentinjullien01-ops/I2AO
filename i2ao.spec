# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — I2AO launcher
=================================
Compile uniquement le LANCEUR (launcher.pyw → i2ao.exe).
Le code Python de l'application reste dans src/ et tourne via le venv.
Résultat : exe léger (~15 Mo) au lieu de ~700 Mo si on embarquait tout Streamlit.
"""

block_cipher = None

a = Analysis(
    ['launcher.pyw'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'urllib.request',
        'socket',
        'subprocess',
        'pathlib',
        'ctypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas'],
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
    name='I2AO',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # Pas de fenêtre console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',   # Décommenter si un .ico est présent dans assets/
)
