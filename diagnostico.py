"""
diagnostico.py — Ferramenta de diagnóstico do Meeting Transcriber v2.

Roda ANTES do main.py para:
1. Listar todos os dispositivos de áudio disponíveis
2. Medir o RMS real de cada dispositivo configurado por 5 segundos
3. Sugerir os thresholds corretos para o config.py

Uso:
    python diagnostico.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import sounddevice as sd

# ── Configuração (espelha o config.py) ───────────────────────────────────────
DEVICE_SISTEMA   = 7
DEVICE_MICROFONE = 16
MEASURE_SECONDS  = 5
# ─────────────────────────────────────────────────────────────────────────────


def listar_dispositivos():
    print("\n" + "=" * 70)
    print("  DISPOSITIVOS DE ÁUDIO DISPONÍVEIS")
    print("=" * 70)
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if dev["max_input_channels"] > 0:
            marker = ""
            if i == DEVICE_SISTEMA:
                marker = "  ← DEVICE_SISTEMA (config)"
            elif i == DEVICE_MICROFONE:
                marker = "  ← DEVICE_MICROFONE (config)"
            print(
                f"  [{i:2d}] {dev['name'][:50]:<50} "
                f"in={dev['max_input_channels']} "
                f"sr={int(dev['default_samplerate'])}Hz"
                f"{marker}"
            )
    print()


def medir_rms(device_idx: int, label: str, segundos: int = MEASURE_SECONDS):
    print(f"  Medindo '{label}' (dispositivo {device_idx}) por {segundos}s...")
    print(f"  {'Fale/reproduza áudio agora':^50}")
    print(f"  {'─' * 50}")

    dev        = sd.query_devices(device_idx)
    channels   = dev["max_input_channels"]
    sr         = int(dev["default_samplerate"])
    hop        = int(sr * 0.05)   # 50ms
    amostras   = []
    rms_values = []

    def callback(indata, frames, t, status):
        if status:
            print(f"    [AVISO] {status}")
        mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
        rms  = float(np.sqrt(np.mean(mono ** 2)))
        rms_values.append(rms)

        # Barra visual em tempo real
        bar_len = int(min(rms / 0.05, 1.0) * 40)
        bar     = "█" * bar_len + "░" * (40 - bar_len)
        print(f"\r  RMS: {rms:.5f}  |{bar}|", end="", flush=True)

    try:
        with sd.InputStream(
            device=device_idx,
            channels=channels,
            samplerate=sr,
            callback=callback,
            blocksize=hop,
        ):
            time.sleep(segundos)
    except Exception as exc:
        print(f"\n  [ERRO] Não foi possível abrir o dispositivo: {exc}")
        return None

    print()  # nova linha após barra

    if not rms_values:
        print("  [ERRO] Nenhum dado capturado.")
        return None

    rms_arr  = np.array(rms_values)
    rms_min  = float(rms_arr.min())
    rms_max  = float(rms_arr.max())
    rms_med  = float(np.median(rms_arr))
    rms_p10  = float(np.percentile(rms_arr, 10))   # ruído de fundo (silêncio)
    rms_p75  = float(np.percentile(rms_arr, 75))   # fala típica

    # Threshold sugerido: um pouco acima do ruído de fundo
    sugestao = round(rms_p10 * 2.5, 5)

    print(f"  Mínimo:   {rms_min:.5f}")
    print(f"  Máximo:   {rms_max:.5f}")
    print(f"  Mediana:  {rms_med:.5f}")
    print(f"  P10 (silêncio): {rms_p10:.5f}")
    print(f"  P75 (fala):     {rms_p75:.5f}")
    print()
    print(f"  ✅ Threshold sugerido para config.py: {sugestao:.5f}")
    print()

    return sugestao


def main():
    print("\n🔍 Meeting Transcriber v2 — Diagnóstico de Áudio")

    listar_dispositivos()

    print("=" * 70)
    print("  MEDIÇÃO DE NÍVEL — SISTEMA")
    print("=" * 70)
    thresh_sis = medir_rms(DEVICE_SISTEMA, "Sistema")

    print("=" * 70)
    print("  MEDIÇÃO DE NÍVEL — MICROFONE (fale normalmente)")
    print("=" * 70)
    thresh_mic = medir_rms(DEVICE_MICROFONE, "Microfone")

    print("=" * 70)
    print("  RESUMO — copie os valores abaixo para o config.py")
    print("=" * 70)
    if thresh_sis is not None:
        print(f"  VAD_THRESHOLD_SISTEMA   = {thresh_sis}")
    if thresh_mic is not None:
        print(f"  VAD_THRESHOLD_MICROFONE = {thresh_mic}")
    print()


if __name__ == "__main__":
    main()