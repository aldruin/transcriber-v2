"""
audio/capture.py — Captura de áudio com VAD (Voice Activity Detection).

Responsabilidades:
- Capturar áudio de um dispositivo específico em thread dedicada
- Detectar início/fim de fala por energia RMS
- Emitir chunks de áudio completos (frase por frase) via callback
- Expor nível RMS em tempo real para o medidor da UI

Cada instância de VoiceCapture lida com UM canal (sistema ou microfone).
O threshold de energia é configurável por canal para resolver o bug onde
o microfone capturava áudio mas não transcrevia (threshold muito alto).

Notas Windows:
- Dispositivos de loopback (mixagem estéreo) podem ser lentos para abrir
- Erros de dispositivo são logados mas NÃO propagados — o outro canal continua
- input_overflow é ignorado (comum em loopback do Windows)
"""

import time
import threading
import numpy as np
import sounddevice as sd

from audio.resampler import resample
from config import (
    VAD_SILENCE_MS,
    VAD_MIN_SPEECH_MS,
    VAD_MAX_SPEECH_MS,
)


class VoiceCapture:
    """
    Captura contínua de áudio de um dispositivo com VAD baseado em energia RMS.

    Args:
        device_idx:       Índice do dispositivo de áudio (sounddevice).
        label:            Nome do canal ("🔊 Sistema" ou "🎤 Microfone").
        energy_threshold: RMS mínimo para considerar como fala (por canal).
        on_chunk:         Callback ao fechar um chunk de fala.
                          Assinatura: (audio: np.ndarray, timestamp: float, label: str)
        stop_event:       threading.Event sinalizado para encerrar a captura.
        on_level:         Callback opcional com nível RMS para a UI.
                          Assinatura: (label: str, rms: float)
        enabled_fn:       Função opcional () -> bool. Se False, descarta o frame.
                          Usada para o botão Mic ON/OFF.
    """

    def __init__(
        self,
        device_idx: int,
        label: str,
        energy_threshold: float,
        on_chunk,
        stop_event: threading.Event,
        on_level=None,
        enabled_fn=None,
    ):
        self.device_idx       = device_idx
        self.label            = label
        self.energy_threshold = energy_threshold
        self.on_chunk         = on_chunk
        self.stop_event       = stop_event
        self.on_level         = on_level
        self.enabled_fn       = enabled_fn

        # Inspeciona o dispositivo para obter canais e sample rate nativos
        device_info   = sd.query_devices(device_idx)
        self.channels = device_info["max_input_channels"]
        self.orig_sr  = int(device_info["default_samplerate"])

        # Converte durações em frames (amostras)
        self._silence_frames = int(self.orig_sr * VAD_SILENCE_MS / 1000)
        self._min_frames     = int(self.orig_sr * VAD_MIN_SPEECH_MS / 1000)
        self._max_frames     = int(self.orig_sr * VAD_MAX_SPEECH_MS / 1000)

        # Estado interno do VAD
        self._buffer         : list[np.ndarray] = []
        self._silence_count  : int   = 0
        self._in_speech      : bool  = False
        self._speech_start   : float = 0.0

    # ── Lógica VAD ────────────────────────────────────────────────────────────

    def _flush(self) -> None:
        """Finaliza e emite o chunk de fala acumulado, se longo o suficiente."""
        if not self._buffer:
            return

        total_frames  = sum(len(x) for x in self._buffer)
        speech_frames = total_frames - self._silence_count

        print(
            f"[{self.label}] flush — total={total_frames} frames, "
            f"speech={speech_frames}, min_required={self._min_frames}",
            flush=True,
        )

        if speech_frames >= self._min_frames:
            raw   = np.concatenate(self._buffer).astype(np.float32)
            chunk = resample(raw, self.orig_sr)
            print(f"[{self.label}] ✅ chunk enviado ({len(chunk)} samples)", flush=True)
            self.on_chunk(chunk, self._speech_start, self.label)
        else:
            print(f"[{self.label}] ⚠ chunk descartado — muito curto", flush=True)

        self._buffer        = []
        self._silence_count = 0
        self._in_speech     = False

    def _process_frame(self, mono: np.ndarray) -> None:
        """
        Processa um frame de áudio mono:
        - Calcula RMS e emite para a UI
        - Decide se é fala ou silêncio
        - Atualiza o buffer e fecha chunks quando necessário
        """
        rms      = float(np.sqrt(np.mean(mono ** 2)))
        is_voice = rms >= self.energy_threshold

        if self.on_level:
            self.on_level(self.label, rms)

        if is_voice:
            if not self._in_speech:
                self._in_speech     = True
                self._speech_start  = time.time()
                self._buffer        = []
                self._silence_count = 0
                print(f"[{self.label}] 🎙 início de fala (RMS={rms:.5f})", flush=True)
            self._buffer.append(mono.copy())
            self._silence_count = 0

        else:
            if self._in_speech:
                self._buffer.append(mono.copy())
                self._silence_count += len(mono)
                total_frames = sum(len(x) for x in self._buffer)

                should_close = (
                    self._silence_count >= self._silence_frames
                    or total_frames >= self._max_frames
                )
                if should_close:
                    self._flush()

    # ── Loop principal ────────────────────────────────────────────────────────

    def run(self) -> None:
        """
        Inicia a captura em loop bloqueante (deve rodar em thread dedicada).
        Encerra quando stop_event é sinalizado.

        Erros de dispositivo são logados mas NÃO propagados para não
        derrubar o app inteiro quando um dos canais falhar.
        """
        hop_size = int(self.orig_sr * 0.05)   # frames de 50ms

        def audio_callback(indata, frames, t, status):
            # input_overflow é comum em loopback do Windows — ignora silenciosamente
            if status and not status.input_overflow:
                print(f"[{self.label}] status: {status}", flush=True)

            if self.enabled_fn and not self.enabled_fn():
                return

            mono = (
                indata.mean(axis=1)
                if indata.shape[1] > 1
                else indata[:, 0]
            )
            self._process_frame(mono)

        print(
            f"[{self.label}] Abrindo dispositivo {self.device_idx} "
            f"(sr={self.orig_sr}Hz, ch={self.channels})...",
            flush=True,
        )

        try:
            with sd.InputStream(
                device=self.device_idx,
                channels=self.channels,
                samplerate=self.orig_sr,
                callback=audio_callback,
                blocksize=hop_size,
                latency="low",
            ):
                print(f"[{self.label}] ✅ dispositivo aberto com sucesso.", flush=True)
                while not self.stop_event.is_set():
                    time.sleep(0.05)

            self._flush()
            print(f"[{self.label}] Encerrado.", flush=True)

        except KeyboardInterrupt:
            pass   # encerramento normal

        except sd.PortAudioError as exc:
            # Erro específico de dispositivo — loga e continua sem derrubar o app
            print(f"[{self.label}] ❌ Erro PortAudio: {exc}", flush=True)
            print(
                f"[{self.label}] ℹ️  Tente outro índice em config.py — "
                f"rode python diagnostico.py para listar os dispositivos.",
                flush=True,
            )

        except Exception as exc:
            print(f"[{self.label}] ❌ Erro inesperado: {exc}", flush=True)