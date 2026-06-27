"""
diagnostico.py — Diagnostico do Meeting Transcriber v2.

Coleta informacoes do ambiente e da captura de audio e imprime um relatorio
que voce pode COPIAR e COLAR ao reportar um problema (util especialmente em
Linux/macOS, onde nao temos como testar tudo). Nao e interativo e nao altera
nada no sistema.

Uso:
    python diagnostico.py
"""

import sys
import platform
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def secao(titulo: str) -> None:
    print("\n" + "=" * 72)
    print(f"  {titulo}")
    print("=" * 72)


def diag_ambiente() -> None:
    secao("AMBIENTE")
    print(f"  SO:     {platform.platform()}")
    print(f"  Python: {sys.version.split()[0]} ({platform.machine()})")


def diag_bibliotecas() -> None:
    import importlib.metadata as md
    secao("BIBLIOTECAS")
    mods = [
        "numpy", "sounddevice", "soundcard", "torch", "torchaudio",
        "faster_whisper", "silero_vad", "resemblyzer", "customtkinter",
    ]
    # Nome do pacote (pip) quando difere do nome do módulo.
    pkg_alias = {"silero_vad": "silero-vad", "faster_whisper": "faster-whisper"}
    for mod in mods:
        try:
            __import__(mod)
        except Exception as exc:
            print(f"  {mod:16s} NAO INSTALADO ({type(exc).__name__})")
            continue
        ver = getattr(sys.modules[mod], "__version__", None)
        if not ver:
            for pkg in (pkg_alias.get(mod, mod), mod, mod.replace("_", "-")):
                try:
                    ver = md.version(pkg)
                    break
                except Exception:
                    continue
        print(f"  {mod:16s} {ver or '(instalado, versao ?)'}")


def diag_gpu() -> None:
    secao("GPU / CUDA (velocidade da transcricao)")
    try:
        import torch
        print(f"  torch build:      {torch.__version__}")
        disponivel = torch.cuda.is_available()
        print(f"  CUDA disponivel:  {disponivel}")
        if disponivel:
            print(f"  GPU:              {torch.cuda.get_device_name(0)}")
            print("  -> O Whisper vai usar a GPU (rapido).")
        else:
            cpu_only = "+cpu" in torch.__version__
            if cpu_only:
                print("  -> torch e CPU-only. Mesmo com GPU NVIDIA, roda na CPU (lento).")
            else:
                print("  -> CUDA indisponivel (driver NVIDIA ausente/desatualizado?).")
            print("     Para usar a GPU, instale o torch com CUDA. Ver README (GPU).")
    except Exception as exc:
        print(f"  erro: {exc}")


def diag_dispositivos() -> None:
    secao("DISPOSITIVOS DE AUDIO")
    try:
        import sounddevice as sd
        devices = sd.query_devices()
    except Exception as exc:
        print(f"  Erro ao consultar dispositivos: {exc}")
        return

    print("  -- Entradas (microfones) --")
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            print(f"  [{i:2d}] {dev['name'][:48]:<48} "
                  f"{dev['max_input_channels']}ch {int(dev['default_samplerate'])}Hz")

    print("  -- Saidas (fonte do loopback do sistema) --")
    for i, dev in enumerate(devices):
        if dev["max_output_channels"] > 0:
            print(f"  [{i:2d}] {dev['name'][:48]:<48} {dev['max_output_channels']}ch")


def diag_loopback() -> None:
    secao("CAPTURA DO AUDIO DO SISTEMA (LOOPBACK)")
    try:
        from audio import loopback
    except Exception as exc:
        print(f"  Erro ao importar o modulo de loopback: {exc}")
        return

    try:
        cfg = loopback.detect_system_audio()
        print(f"  OK: {cfg.label}")
        print(f"      metodo={cfg.method}  canais={cfg.channels}  sr={cfg.samplerate}")
        print("  -> O audio do sistema sera capturado automaticamente.")
    except loopback.LoopbackError as exc:
        print(f"  FALHOU: {exc}")
        so = platform.system()
        if so == "Darwin":
            print("  -> macOS exige um dispositivo virtual. Instale o BlackHole:")
            print("       brew install blackhole-2ch")
            print("     e crie um Aggregate Device. Ver SETUP-GUIDE.md.")
        elif so == "Linux":
            print("  -> Linux: confirme que PulseAudio/PipeWire esta ativo e que")
            print("     existe um '.monitor'. Rode: pactl list short sources")
        else:
            print("  -> Conecte/ative uma saida de audio padrao e tente de novo.")
    except Exception as exc:
        print(f"  Erro inesperado: {exc}")


def main() -> None:
    print("\nMEETING TRANSCRIBER V2 - DIAGNOSTICO")
    print("(copie todo o relatorio abaixo ao reportar um problema)")
    diag_ambiente()
    diag_bibliotecas()
    diag_gpu()
    diag_dispositivos()
    diag_loopback()
    secao("FIM")
    print("  Reporte em: https://github.com/aldruin/transcriber-v2/issues")
    print()


if __name__ == "__main__":
    main()
