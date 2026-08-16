# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# ============================================================
# STREAMLIT
# ============================================================

streamlit_datas, streamlit_binaries, streamlit_hiddenimports = (
    collect_all("streamlit")
)

# ============================================================
# APPLICATION DATA
# ============================================================

app_datas = [
    ("../app.py", "."),
    ("../config.py", "."),
    ("../station_config.py", "."),
    ("../bulletin", "bulletin"),
    ("../core", "core"),
    ("../models", "models"),
    ("../data", "data"),
]

# ============================================================
# ANALYSIS
# ============================================================

a = Analysis(
    ["launcher.py"],

    pathex=[
        ".",
        "..",
    ],

    binaries=streamlit_binaries,

    datas=(
        streamlit_datas
        + app_datas
    ),

    hiddenimports=(
        streamlit_hiddenimports
        + [
            "streamlit.web.bootstrap",
            "streamlit.web.cli",
            "openpyxl",
            "docx",
            "copernicusmarine",
            "xarray",
            "netCDF4",
        ]
    ),

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],

    win_no_prefer_redirects=False,
    win_private_assemblies=False,

    cipher=block_cipher,

    noarchive=False,
)

# ============================================================
# PYZ
# ============================================================

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)

# ============================================================
# EXE
# ============================================================

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,

    name="HaiVanQuangTri",

    debug=False,

    bootloader_ignore_signals=False,

    strip=False,

    upx=False,

    console=False,

    disable_windowed_traceback=False,

    target_arch=None,

    codesign_identity=None,

    entitlements_file=None,

    icon="../HaiVan.ico",
)

# ============================================================
# COLLECT
# ============================================================

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,

    strip=False,
    upx=False,

    name="HaiVanQuangTri",
)