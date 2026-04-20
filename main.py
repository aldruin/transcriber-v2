"""
main.py — Entry point do Meeting Transcriber v2.

Uso:
    python main.py

Dependências:
    pip install faster-whisper sounddevice numpy resemblyzer customtkinter
"""
import sys
from pathlib import Path
import customtkinter as ctk

# Garante que a raiz do projeto está no path,
# independente de onde o script é chamado.
sys.path.insert(0, str(Path(__file__).parent))

from ui.app import TranscriberApp

def main() -> None:
    # Configuração global do CustomTkinter
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    app = TranscriberApp()
    app.run()

if __name__ == "__main__":
    main()
