# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

entry_script = os.path.join(SPECPATH, "build_entry.py")

# Collect all submodules/data for packages that use dynamic loading
textual_datas, textual_binaries, textual_hidden = collect_all("textual")
pydantic_datas, pydantic_binaries, pydantic_hidden = collect_all("pydantic")

a = Analysis(
    [entry_script],
    pathex=[],
    binaries=pydantic_binaries + textual_binaries,
    datas=textual_datas + pydantic_datas,
    hiddenimports=[
        # internal packages
        "zenve_cli",
        "zenve_adapters",
        "zenve_models",
        "zenve_services",
        "zenve_utils",
        "zenve_config",
        "zenve_db",
        # typer / rich / textual
        "typer",
        "typer.main",
        "rich",
        "rich.console",
        "rich.markup",
        "rich.text",
        "rich.table",
        "rich.panel",
        "rich.progress",
        "rich.syntax",
        "rich.logging",
        # questionary / prompt_toolkit
        "questionary",
        "prompt_toolkit",
        "prompt_toolkit.shortcuts",
        "prompt_toolkit.filters",
        "prompt_toolkit.key_binding",
        # pydantic / pydantic-settings
        "pydantic",
        "pydantic.v1",
        "pydantic_settings",
        # http
        "httpx",
        "httpcore",
        "anyio",
        "anyio.streams",
        # dotenv
        "dotenv",
        # yaml
        "yaml",
        # sqlalchemy (transitive, but needed for import resolution)
        "sqlalchemy",
        "sqlalchemy.dialects.postgresql",
        # jose / bcrypt
        "jose",
        "jose.jwt",
        "bcrypt",
        "cryptography",
        "cryptography.hazmat.primitives",
        *textual_hidden,
        *pydantic_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="zenve",
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
