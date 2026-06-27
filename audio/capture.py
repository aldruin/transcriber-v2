"""
audio/capture.py — Captura de áudio com VAD silero-vad em loop manual.

Cada `VoiceCapture` lida com UM canal (sistema ou microfone) e roda em uma
thread dedicada. Backend de captura é um de:
  • `sounddevice.InputStream` (callback) — microfone em todos os SOs e
    loopback no Linux/macOS.
  • `soundcard` recorder (polling) — loopback WASAPI no Windows.

VAD (D2): rodamos o modelo silero direto, em chunks de 512 amostras (32 ms
@ 16 kHz). Distinguimos:
  • silêncio "final" (≥ ~300 ms) → fecha a frase (`emit_speech_end`).
  • micro-pausa (~100 ms) com fala já consolidada → emite parcial mantendo a
    fala "aberta" (`emit_partial_speech`). É como pegar o "fraseamento"
    natural (vírgulas, respirações) e mostrar texto sem esperar o ponto final.
"""

from __future__ import annotations

import time
import threading
from collections import deque
import numpy as np
import sounddevice as sd
import torch

from silero_vad import load_silero_vad

from audio.resampler import resample
from audio.win_loopback_compat import (
    patch_soundcard_numpy2,
    ensure_com_initialized,
    com_uninitialize,
)
from config import TARGET_SR

# ── silero-vad: UMA INSTÂNCIA POR CANAL ──────────────────────────────────────
# O modelo silero é stateful (GRU interna). Compartilhar entre threads
# (sistema + microfone) corrompe a hidden state e causa segfault. Cada
# VoiceCapture tem o seu.
def _new_vad_model():
    """Cria uma nova instância do silero-vad com estado próprio."""
    model = load_silero_vad()
    if hasattr(model, "reset_states"):
        model.reset_states()
    return model


# Tamanho de chunk exigido pelo silero-vad em 16 kHz (~32 ms cada).
_VAD_CHUNK_16K  = 512
_VAD_CHUNK_MS   = _VAD_CHUNK_16K * 1000 // TARGET_SR  # ≈ 32 ms

# Limiares VAD (em chunks de 32 ms). Ajustáveis por instância.
_DEFAULT_THRESHOLD       = 0.5
_DEFAULT_FINAL_SIL_MS    = 320   # silêncio que fecha frase
_DEFAULT_PARTIAL_SIL_MS  = 120   # micro-pausa que dispara flush parcial
_DEFAULT_MIN_SPEECH_MS   = 250   # fala mínima pra autorizar flush parcial
_DEFAULT_PRE_PAD_MS      = 96    # contexto antes do "start"


def _ms_to_chunks(ms: int) -> int:
    """Converte ms em quantidade de chunks de _VAD_CHUNK_MS."""
    return max(1, ms // _VAD_CHUNK_MS)


class VoiceCapture:
    """
    Captura contínua com VAD silero em loop manual.

    Args:
        device_idx:       Índice `sounddevice` (None p/ loopback Windows).
        label:            "🔊 Sistema" ou "🎤 Microfone".
        on_chunk:         Callback `(audio16k, ts, label)`. Áudio em 16 kHz.
        stop_event:       Sinaliza encerramento.
        on_level:         (opcional) `(label, rms)` para o medidor.
        enabled_fn:       (opcional) `() -> bool` (Mic ON/OFF).
        echo_guard:       (opcional) `EchoGuard` compartilhado entre canais.
        channels:         Canais do stream.
        samplerate:       SR nativo do dispositivo.
        extra_settings:   Passado a `sd.InputStream`.
        soundcard_mic:    Mic do `soundcard` (Windows loopback).
        vad_threshold:    Probabilidade mínima p/ considerar fala (0–1).
        final_silence_ms: Silêncio que fecha frase definitivamente.
        partial_silence_ms: Silêncio que dispara flush parcial (micro-pausa).
        min_speech_ms:    Fala mínima antes de aceitar flush parcial.
    """

    def __init__(
        self,
        device_idx: int | None,
        label: str,
        on_chunk,
        stop_event: threading.Event,
        on_level=None,
        enabled_fn=None,
        echo_guard=None,
        channels: int | None = None,
        samplerate: int | None = None,
        extra_settings=None,
        soundcard_mic=None,
        vad_threshold: float = _DEFAULT_THRESHOLD,
        final_silence_ms: int = _DEFAULT_FINAL_SIL_MS,
        partial_silence_ms: int = _DEFAULT_PARTIAL_SIL_MS,
        min_speech_ms: int = _DEFAULT_MIN_SPEECH_MS,
        pre_pad_ms: int = _DEFAULT_PRE_PAD_MS,
    ):
        self.device_idx     = device_idx
        self.label          = label
        self.on_chunk       = on_chunk
        self.stop_event     = stop_event
        self.on_level       = on_level
        self.enabled_fn     = enabled_fn
        self.echo_guard     = echo_guard
        self.extra_settings = extra_settings
        self.soundcard_mic  = soundcard_mic

        if soundcard_mic is None and (channels is None or samplerate is None):
            info       = sd.query_devices(device_idx)
            channels   = channels   or info["max_input_channels"]
            samplerate = samplerate or int(info["default_samplerate"])

        self.channels = channels
        self.orig_sr  = samplerate

        # Modelo VAD próprio do canal (state isolado entre threads).
        self._vad_model = _new_vad_model()
        self._vad_threshold = vad_threshold

        # Limiares em chunks (cada chunk = 32 ms).
        self._final_sil_chunks   = _ms_to_chunks(final_silence_ms)
        self._partial_sil_chunks = _ms_to_chunks(partial_silence_ms)
        self._min_speech_chunks  = _ms_to_chunks(min_speech_ms)
        self._pre_pad_chunks     = _ms_to_chunks(pre_pad_ms)

        # Buffers/estado
        self._vad_carry: list[float] = []
        self._pre_pad: deque[np.ndarray] = deque(maxlen=self._pre_pad_chunks)
        self._speech_chunks: list[np.ndarray] = []
        self._silent_run = 0    # chunks consecutivos de silêncio dentro da fala
        self._speech_run = 0    # chunks de fala acumulados desde o último flush
        self._in_speech = False
        self._speech_start_time = 0.0

    # ── VAD pipeline ──────────────────────────────────────────────────────────

    def _emit_speech_end(self) -> None:
        """Fecha a frase e dispara `on_chunk`."""
        if self._speech_chunks:
            audio = np.concatenate(self._speech_chunks).astype(np.float32)
            self.on_chunk(audio, self._speech_start_time, self.label)
        self._speech_chunks = []
        self._silent_run = 0
        self._speech_run = 0
        self._in_speech = False

    def _emit_partial_speech(self) -> None:
        """
        Emite o que já tem mas mantém a fala "aberta" (próximo segmento parcial
        começa imediatamente). Usado em micro-pausa pra texto aparecer fluido.
        """
        if not self._speech_chunks:
            return
        audio = np.concatenate(self._speech_chunks).astype(np.float32)
        self.on_chunk(audio, self._speech_start_time, self.label)
        self._speech_chunks = []
        self._silent_run = 0
        self._speech_run = 0
        self._speech_start_time = time.time()

    def _consume_vad(self, chunk16k: np.ndarray) -> None:
        """Alimenta um chunk de 512 amostras (16 kHz) ao VAD e atualiza estado."""
        # Pré-padding sempre rolando (mesmo fora de fala).
        self._pre_pad.append(chunk16k)

        try:
            prob = float(self._vad_model(torch.from_numpy(chunk16k), TARGET_SR).item())
        except Exception as exc:
            print(f"[{self.label}] VAD inferência falhou: {exc}", flush=True)
            return

        # Se o estado do silero corromper (prob vira NaN), ele nunca mais
        # detectaria fala. Auto-recupera resetando o estado em vez de morrer.
        if prob != prob:  # NaN
            print(f"[{self.label}] VAD retornou NaN — resetando estado.", flush=True)
            if hasattr(self._vad_model, "reset_states"):
                self._vad_model.reset_states()
            self._vad_carry = []
            return

        is_speech = prob >= self._vad_threshold

        if is_speech:
            if not self._in_speech:
                # Início — inclui pré-padding pra não cortar a primeira sílaba.
                self._in_speech = True
                # Estima o início olhando quantos chunks de pré-pad estamos.
                self._speech_start_time = time.time() - len(self._pre_pad) * (_VAD_CHUNK_MS / 1000.0)
                self._speech_chunks = list(self._pre_pad)
                self._silent_run = 0
                self._speech_run = len(self._pre_pad)
            else:
                self._speech_chunks.append(chunk16k)
                self._silent_run = 0
                self._speech_run += 1
            return

        # Silêncio
        if not self._in_speech:
            return

        self._speech_chunks.append(chunk16k)
        self._silent_run += 1
        self._speech_run += 1

        if self._silent_run >= self._final_sil_chunks:
            self._emit_speech_end()
            return

        if (
            self._silent_run >= self._partial_sil_chunks
            and self._speech_run - self._silent_run >= self._min_speech_chunks
        ):
            # Micro-pausa em ponto natural — aproveita pra emitir parcial.
            self._emit_partial_speech()

    def _process_frame(self, mono_native: np.ndarray) -> None:
        """
        Recebe frame mono no SR nativo, resampleia a 16 kHz, alimenta o VAD em
        chunks de 512 amostras. Emite RMS para a UI em paralelo.
        """
        if self.enabled_fn is not None and not self.enabled_fn():
            if self._in_speech:
                self._emit_speech_end()
            self._vad_carry = []
            self._pre_pad.clear()
            return

        # O 1º buffer do WASAPI às vezes vem com NaN/Inf, e um único NaN corrompe
        # de vez o estado do silero-VAD (para de detectar fala a sessão inteira).
        # Sanitiza aqui, que é o ponto comum aos dois canais.
        mono_native = np.nan_to_num(
            np.asarray(mono_native, dtype=np.float32),
            nan=0.0, posinf=0.0, neginf=0.0,
        )
        np.clip(mono_native, -1.0, 1.0, out=mono_native)

        resampled = resample(mono_native, self.orig_sr).astype(np.float32)

        if self.on_level is not None:
            rms = float(np.sqrt(np.mean(resampled ** 2)))
            self.on_level(self.label, rms)

        self._vad_carry.extend(resampled.tolist())
        while len(self._vad_carry) >= _VAD_CHUNK_16K:
            chunk = np.array(self._vad_carry[:_VAD_CHUNK_16K], dtype=np.float32)
            del self._vad_carry[:_VAD_CHUNK_16K]
            self._consume_vad(chunk)

    # ── Loop principal ────────────────────────────────────────────────────────

    def run(self) -> None:
        """Loop bloqueante; despacha pelo backend. Roda em thread dedicada."""
        if self.soundcard_mic is not None:
            self._run_soundcard()
        else:
            self._run_sounddevice()

    def _run_sounddevice(self) -> None:
        """Captura via `sounddevice.InputStream` (callback)."""
        hop = int(self.orig_sr * 0.05)   # 50 ms

        def cb(indata, frames, t, status):
            if status and not status.input_overflow:
                print(f"[{self.label}] status: {status}", flush=True)
            mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
            self._process_frame(mono.astype(np.float32))

        print(
            f"[{self.label}] abrindo dispositivo {self.device_idx} "
            f"(sr={self.orig_sr}Hz, ch={self.channels})...",
            flush=True,
        )
        try:
            kwargs = dict(
                device=self.device_idx,
                channels=self.channels,
                samplerate=self.orig_sr,
                callback=cb,
                blocksize=hop,
                latency="low",
            )
            if self.extra_settings is not None:
                kwargs["extra_settings"] = self.extra_settings

            with sd.InputStream(**kwargs):
                print(f"[{self.label}] dispositivo aberto.", flush=True)
                while not self.stop_event.is_set():
                    time.sleep(0.05)

            if self._in_speech:
                self._emit_speech_end()
            print(f"[{self.label}] encerrado.", flush=True)

        except KeyboardInterrupt:
            pass
        except sd.PortAudioError as exc:
            print(f"[{self.label}] erro PortAudio: {exc}", flush=True)
        except Exception as exc:
            print(f"[{self.label}] erro inesperado: {exc}", flush=True)

    def _run_soundcard(self) -> None:
        """Captura via `soundcard` (Windows WASAPI loopback, polling)."""
        # WASAPI/soundcard tem duas armadilhas no Windows (ver
        # audio/win_loopback_compat.py); sem estas duas chamadas a captura do
        # áudio do sistema falha silenciosamente:
        #   1. SoundCard 0.4.5 usa np.fromstring (removido no NumPy 2.x).
        #   2. COM precisa ser inicializado NESTA thread (senão Error 0x800401f0).
        patch_soundcard_numpy2()
        ensure_com_initialized()

        hop = int(self.orig_sr * 0.05)
        print(
            f"[{self.label}] abrindo loopback (soundcard, "
            f"sr={self.orig_sr}Hz, ch={self.channels})...",
            flush=True,
        )
        try:
            with self.soundcard_mic.recorder(
                samplerate=self.orig_sr,
                channels=self.channels,
                blocksize=hop,
            ) as rec:
                print(f"[{self.label}] loopback aberto.", flush=True)
                while not self.stop_event.is_set():
                    data = rec.record(numframes=hop)
                    if data.ndim > 1 and data.shape[1] > 1:
                        mono = data.mean(axis=1)
                    else:
                        mono = data[:, 0] if data.ndim > 1 else data
                    # Sanitização do lixo do 1º buffer é feita centralmente em
                    # _process_frame (protege ambos os canais).
                    self._process_frame(mono.astype(np.float32))

            if self._in_speech:
                self._emit_speech_end()
            print(f"[{self.label}] encerrado.", flush=True)

        except KeyboardInterrupt:
            pass
        except Exception as exc:
            print(f"[{self.label}] erro soundcard: {exc}", flush=True)
        finally:
            com_uninitialize()
