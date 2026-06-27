"""
build_exe.py — build local com PyInstaller (atalho para devs).

Em produção, os releases multiplataforma saem da pipeline em
`.github/workflows/release.yml`. Este script é só pra build local rápido.
"""

import os
import shutil
import subprocess
import sys


def build():
    print("--- Build local (PyInstaller) ---")

    print("Instalando dependências do requirements.txt + pyinstaller...")
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-r", "requirements.txt",
    ])
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "pyinstaller",
    ])

    for folder in ("build", "dist"):
        if os.path.exists(folder):
            shutil.rmtree(folder)

    print("Executando PyInstaller (alguns minutos)...")
    try:
        subprocess.check_call(["pyinstaller", "--noconfirm", "app.spec"])
        print("\nOK — binário em dist/MeetingTranscriberV2"
              + (".exe" if sys.platform == "win32" else ""))
    except subprocess.CalledProcessError as exc:
        print(f"\nFALHA: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    build()
