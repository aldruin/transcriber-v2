"""
audio/resampler.py — Utilitários de processamento de áudio.

Responsabilidades:
- Resample de qualquer sample rate para TARGET_SR (16kHz)
- Normalização de amplitude (resolve problema de voz baixa)
"""

import numpy as np
from config import TARGET_SR


def resample(audio: np.ndarray, orig_sr: int) -> np.ndarray:
    """
    Converte `audio` de `orig_sr` Hz para TARGET_SR Hz via interpolação linear.

    Args:
        audio:   Array 1-D float32 com amostras de áudio.
        orig_sr: Sample rate original do áudio capturado.

    Returns:
        Array float32 em TARGET_SR Hz.
    """
    if orig_sr == TARGET_SR:
        return audio.astype(np.float32)

    new_len = int(len(audio) * TARGET_SR / orig_sr)
    resampled = np.interp(
        np.linspace(0, len(audio) - 1, new_len),
        np.arange(len(audio)),
        audio,
    )
    return resampled.astype(np.float32)


def normalize_amplitude(audio: np.ndarray) -> np.ndarray:
    """
    Normaliza o áudio para o intervalo [-1, 1].

    Resolve o problema de voz baixa sem alterar o threshold do VAD.
    O epsilon evita divisão por zero em chunks de silêncio puro.

    Args:
        audio: Array float32.

    Returns:
        Array float32 normalizado.
    """
    peak = np.max(np.abs(audio))
    if peak < 1e-6:
        return audio
    return (audio / peak).astype(np.float32)
