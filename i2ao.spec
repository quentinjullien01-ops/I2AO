# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — I2AO (one-folder, tout embarqué)
====================================================
Produit : dist/I2AO/
  I2AO.exe        ← double-clic pour lancer
  _internal/      ← Python + toutes les dépendances
  src/            ← code de l'application
  content/        ← bibliothèques MT, profils BET
  data/           ← données (DCE démo, etc.)
  assets/         ← logo, icônes
  .streamlit/     ← config thème

Usage :
  build.bat       ← compile tout automatiquement
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH)

# ── Données statiques à embarquer ───────────────────────────────────────────

datas = []

# Streamlit : frontend React + assets statiques (obligatoire)
datas += collect_data_files("streamlit", include_py_files=False)

# Plotly : schémas JSON des figures
datas += collect_data_files("plotly", include_py_files=False)

# Altair (dépendance Streamlit)
try:
    datas += collect_data_files("altair", include_py_files=False)
except Exception:
    pass

# Pydantic
try:
    datas += collect_data_files("pydantic", include_py_files=False)
except Exception:
    pass

# Fichiers de l'application elle-même
datas += [
    (str(ROOT / "src"),        "src"),
    (str(ROOT / "content"),    "content"),
    (str(ROOT / "assets"),     "assets"),
    (str(ROOT / ".streamlit"), ".streamlit"),
]
# data/ uniquement s'il existe et n'est pas vide
if (ROOT / "data").exists():
    datas += [(str(ROOT / "data"), "data")]

# ── Imports cachés ──────────────────────────────────────────────────────────

hiddenimports = [
    # Streamlit internals
    "streamlit.web.bootstrap",
    "streamlit.web.server",
    "streamlit.web.cli",
    "streamlit.runtime",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.state",
    "streamlit.components.v1",
    # Pydantic v2
    "pydantic",
    "pydantic.deprecated.class_validators",
    "pydantic_core",
    # Google GenAI
    "google.genai",
    "google.auth",
    "google.auth.transport.requests",
    # PDF
    "pdfplumber",
    "pymupdf",
    "fitz",
    "pytesseract",
    "PIL",
    "PIL.Image",
    # Office
    "docx",
    "openpyxl",
    "openpyxl.styles",
    # Autres
    "yaml",
    "frontmatter",
    "dotenv",
    "plotly.graph_objects",
    "plotly.express",
    # stdlib souvent oublié
    "email.mime.multipart",
    "email.mime.text",
    "importlib.metadata",
    "importlib.resources",
    "pkg_resources",
    "pkg_resources._vendor",
    "pkg_resources.extern",
]

# Collecte automatique des sous-modules Streamlit
hiddenimports += collect_submodules("streamlit")

# ── Analyse ─────────────────────────────────────────────────────────────────

block_cipher = None

a = Analysis(
    [str(ROOT / "launcher.pyw")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "IPython", "jupyter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # one-folder (pas one-file)
    name="I2AO",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,               # UPX désactivé (AV le signale parfois)
    console=False,           # pas de fenêtre console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=str(ROOT / "assets" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="I2AO",
)
