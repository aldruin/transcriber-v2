"""
audio/loopback.py — Detecção de captura do áudio do sistema (D1).

Cada SO usa um caminho diferente:
  • Windows: WASAPI loopback no dispositivo de saída padrão (sem Stereo Mix).
  • Linux:   monitor source do PulseAudio/PipeWire.
  • macOS:   driver virtual instalado pelo usuário (BlackHole).

A função pública `detect_system_audio()` devolve um `LoopbackConfig` pronto
para alimentar `VoiceCapture`. Em caso de falha, levanta `LoopbackError`
com mensagem orientada ao próximo passo.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from typing import Any

import sounddevice as sd


class LoopbackError(RuntimeError):
    """Não foi possível abrir captura do áudio do sistema neste host."""


@dataclass
class LoopbackConfig:
    """
    Configuração para abrir captura do áudio do sistema.

    Para Linux/macOS, `device` aponta para um índice válido do `sounddevice`.
    Para Windows, `device` é None e `soundcard_mic` carrega o objeto Loopback
    do `soundcard` (D1 híbrido).
    """
    device: int | None
    channels: int
    samplerate: int
    extra_settings: Any | None
    label: str
    method: str  # "soundcard" | "monitor" | "virtual"
    soundcard_mic: Any | None = None


def detect_system_audio() -> LoopbackConfig:
    """Devolve a melhor configuração de loopback para o SO atual."""
    system = platform.system()
    if system == "Windows":
        return _detect_windows_wasapi()
    if system == "Linux":
        return _detect_linux_monitor()
    if system == "Darwin":
        return _detect_macos_virtual()
    raise LoopbackError(f"Sistema operacional não suportado: {system}")


# ── Windows: WASAPI loopback via soundcard ───────────────────────────────────

def _detect_windows_wasapi() -> LoopbackConfig:
    try:
        import soundcard as sc
    except ImportError as exc:
        raise LoopbackError(
            "Pacote `soundcard` não instalado. Rode "
            "`pip install soundcard` (ou reinstale via requirements.txt)."
        ) from exc

    try:
        speaker = sc.default_speaker()
    except Exception as exc:
        raise LoopbackError(f"Falha ao consultar saída padrão: {exc}") from exc

    if speaker is None:
        raise LoopbackError("Nenhum dispositivo de saída padrão ativo.")

    try:
        mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
    except Exception as exc:
        raise LoopbackError(
            f"Não foi possível abrir loopback de '{speaker.name}': {exc}"
        ) from exc

    channels = getattr(speaker, "channels", 2) or 2
    # soundcard usa o samplerate do device implicitamente; assumimos 48000.
    samplerate = 48000

    return LoopbackConfig(
        device=None,
        channels=channels,
        samplerate=samplerate,
        extra_settings=None,
        label=f"Sistema · WASAPI loopback ({speaker.name})",
        method="soundcard",
        soundcard_mic=mic,
    )


# ── Linux: PulseAudio/PipeWire monitor ───────────────────────────────────────

def _detect_linux_monitor() -> LoopbackConfig:
    monitors: list[tuple[int, dict]] = []
    for i, dev in enumerate(sd.query_devices()):
        name = (dev.get("name") or "").lower()
        if dev["max_input_channels"] > 0 and (".monitor" in name or "monitor of" in name):
            monitors.append((i, dev))

    if not monitors:
        raise LoopbackError(
            "Nenhum monitor source disponível. Verifique se PulseAudio ou "
            "PipeWire está rodando (`pactl list short sources`)."
        )

    idx, dev = monitors[0]
    return LoopbackConfig(
        device=idx,
        channels=int(dev["max_input_channels"]),
        samplerate=int(dev["default_samplerate"]),
        extra_settings=None,
        label=f"Sistema · {dev['name']}",
        method="monitor",
    )


# ── macOS: BlackHole / Aggregate Device ──────────────────────────────────────

_MAC_VIRTUAL_KEYWORDS = ("blackhole", "soundflower", "aggregate", "loopback")


def _detect_macos_virtual() -> LoopbackConfig:
    candidates: list[tuple[int, dict]] = []
    for i, dev in enumerate(sd.query_devices()):
        name = (dev.get("name") or "").lower()
        if dev["max_input_channels"] > 0 and any(k in name for k in _MAC_VIRTUAL_KEYWORDS):
            candidates.append((i, dev))

    if not candidates:
        raise LoopbackError(
            "Nenhum driver virtual de áudio encontrado. "
            "Instale BlackHole (`brew install blackhole-2ch`) e "
            "configure um Aggregate Device."
        )

    idx, dev = candidates[0]
    return LoopbackConfig(
        device=idx,
        channels=int(dev["max_input_channels"]),
        samplerate=int(dev["default_samplerate"]),
        extra_settings=None,
        label=f"Sistema · {dev['name']}",
        method="virtual",
    )


def is_available() -> bool:
    """True se há caminho viável de captura do sistema."""
    try:
        detect_system_audio()
        return True
    except LoopbackError:
        return False
