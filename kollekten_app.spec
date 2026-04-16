# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller-Spec für Kollekten-Automation.

Build-Befehl (im Projektroot mit aktiviertem .venv):
    pyinstaller kollekten_app.spec

Ausgabe: dist/Kollekten-Automation/Kollekten-Automation.exe
"""

import sys
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "app_entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "data" / "reference"), "data/reference"),
        (str(ROOT / "app" / "theme"), "app/theme"),
        (str(ROOT / "assets"), "assets"),
        # PWA-Dateien: statische Webseite für Smartphone-Zugriff
        (str(ROOT / "app" / "api" / "static"), "app/api/static"),
    ],
    hiddenimports=[
        # win32com / pywin32
        "win32com.client",
        "win32com.server",
        "pywintypes",
        "win32timezone",
        "win32api",
        "win32con",
        "pythoncom",
        # PySide6
        "PySide6.QtPrintSupport",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        # pystray
        "pystray",
        "PIL",
        "PIL.Image",
        # FastAPI / uvicorn (PWA-Server)
        "fastapi",
        "fastapi.middleware.cors",
        "fastapi.staticfiles",
        "uvicorn",
        "uvicorn.main",
        "uvicorn.config",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "starlette",
        "starlette.applications",
        "starlette.routing",
        "starlette.staticfiles",
        "starlette.responses",
        "anyio",
        "anyio._backends._asyncio",
        # andere
        "openpyxl",
        "requests",
        "pdfplumber",
        "chardet",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "IPython",
        "jupyter",
    ],
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
    exclude_binaries=True,
    name="Kollekten-Automation",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # --windowed: kein Konsolenfenster
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "app.ico"),
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Kollekten-Automation",
)
