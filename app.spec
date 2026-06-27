# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — Meeting Transcriber v2.

Empacota um único binário por SO. Sem cross-compilação: cada plataforma
roda este spec na sua própria runner do GitHub Actions.
"""

import os
import customtkinter
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

project_root = os.path.abspath(".")
ctk_path     = os.path.dirname(customtkinter.__file__)

block_cipher = None

# Submódulos próprios + bibliotecas externas que PyInstaller pode não
# detectar via análise estática.
hidden_imports = (
    collect_submodules("audio")         +
    collect_submodules("diarization")   +
    collect_submodules("transcription") +
    collect_submodules("ui")            +
    [
        "faster_whisper",
        "resemblyzer",
        "sounddevice",
        "soundcard",
        "silero_vad",
        "customtkinter",
        "darkdetect",
        "torch",
        "torchaudio",
        "numpy",
        "settings",
        "config",
    ]
)

# Dados embutidos: assets do customtkinter + modelos/recursos das libs.
datas = [(ctk_path, "customtkinter")]
datas += collect_data_files("faster_whisper")
datas += collect_data_files("resemblyzer")
datas += collect_data_files("silero_vad")

a = Analysis(
    ["main.py"],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="MeetingTranscriberV2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="NONE",
)
