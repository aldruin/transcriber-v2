"""
main.py — Entry point do Meeting Transcriber v2.

Uso:
    python main.py
"""
import sys
from pathlib import Path

import customtkinter as ctk

# Garante que a raiz do projeto está no path,
# independente de onde o script é chamado.
sys.path.insert(0, str(Path(__file__).parent))

import settings
from ui.app import TranscriberApp
from ui.setup_wizard import SetupWizard


def _run_wizard_blocking() -> None:
    """
    Roda o wizard standalone (antes do app principal existir) e bloqueia até
    o usuário finalizar. Cria um root temporário, escondido.
    """
    root = ctk.CTk()
    root.withdraw()
    wizard = SetupWizard(root)
    root.wait_window(wizard)
    root.destroy()


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    if settings.is_first_run():
        _run_wizard_blocking()

    # Se o usuário fechou o wizard sem completar, sai.
    if settings.is_first_run():
        print("[main] Configuração não foi concluída. Encerrando.")
        return

    app = TranscriberApp()
    app.run()


if __name__ == "__main__":
    main()
