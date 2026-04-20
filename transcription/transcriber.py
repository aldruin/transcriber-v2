"""
transcription/transcriber.py — Motor de transcrição com Whisper.

Responsabilidades:
- Carregar e gerenciar o modelo faster-whisper
- Transcrever chunks de áudio em texto
- Filtrar alucinações por no_speech_prob e avg_logprob
- Normalizar amplitude antes de transcrever (resolve voz baixa)

A transcrição roda em thread separada, consumindo de uma fila,
para não bloquear a captura de áudio.
"""

import queue
import threading
import numpy as np
from datetime import datetime
from faster_whisper import WhisperModel

from audio.resampler import normalize_amplitude
from diarization import DiarizationEngine  # <-- Adicionado
from config import (
    WHISPER_MODEL,
    WHISPER_LANGUAGE,
    WHISPER_BEAM,
    WHISPER_DEVICE,
    WHISPER_COMPUTE,
    NO_SPEECH_THRESHOLD,
    AVG_LOGPROB_THRESHOLD,
)


class Transcriber:
    """
    Consumidor de fila que transcreve áudio em texto usando faster-whisper.

    O modelo é carregado de forma assíncrona para não bloquear a UI.
    Ao transcrever, aplica:
      1. Diarização (quem falou) — Agora assíncrona
      2. Normalização de amplitude (voz baixa)
      3. Filtro de alucinações (no_speech_prob + avg_logprob)

    Args:
        on_result:  Callback chamado com cada transcrição válida.
                    Assinatura: (timestamp: float, label: str, text: str)
        on_ready:   Callback chamado quando o modelo termina de carregar.
        on_error:   Callback chamado em caso de erro de transcrição.
                    Assinatura: (error: Exception)
        diarization: Motor de diarização para identificação de falantes.
    """

    def __init__(self, on_result, on_ready=None, on_error=None, diarization: DiarizationEngine = None):
        self.on_result = on_result
        self.on_ready  = on_ready
        self.on_error  = on_error
        self.diarization = diarization # <-- Adicionado

        self._model      : WhisperModel | None = None
        self._queue      : queue.Queue         = queue.Queue()
        self._stop_event : threading.Event     = threading.Event()
        self._worker     : threading.Thread | None = None

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    def load_async(self) -> None:
        """Carrega o modelo Whisper em background."""
        threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self) -> None:
        try:
            self._model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE,
            )
            if self.on_ready:
                self.on_ready()
        except Exception as exc:
            if self.on_error:
                self.on_error(exc)

    def start(self) -> None:
        """Inicia o loop de transcrição em thread dedicada."""
        self._stop_event.clear()
        self._worker = threading.Thread(
            target=self._transcribe_loop, daemon=True
        )
        self._worker.start()

    def stop(self) -> None:
        """Sinaliza parada e aguarda a fila esvaziar."""
        self._stop_event.set()

    def is_ready(self) -> bool:
        return self._model is not None

    # ── Interface pública ──────────────────────────────────────────────────────

    def enqueue(self, audio: np.ndarray, timestamp: float, channel: str, speaker: str | None = None) -> None:
        """
        Adiciona um chunk de áudio à fila de transcrição.

        Args:
            audio:     Array float32 em 16kHz (já resampleado).
            timestamp: Unix timestamp do início da fala.
            channel:   Identificador do canal (ex: "🔊 Sistema").
            speaker:   Nome do falante identificado (se já conhecido).
        """
        self._queue.put((timestamp, channel, speaker, audio))

    # ── Loop interno ──────────────────────────────────────────────────────────

    def _transcribe_loop(self) -> None:
        """Consome a fila e transcreve cada chunk até stop_event + fila vazia."""
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                # Fila contém: (timestamp, channel, speaker, audio)
                item = self._queue.get(timeout=0.5)
                timestamp, channel, speaker, audio = item
            except queue.Empty:
                continue

            try:
                # Se o falante não foi identificado no envio (comum agora),
                # fazemos a diarização aqui, na thread de transcrição.
                if speaker is None and self.diarization:
                    speaker = self.diarization.identify(audio, label=channel)

                text = self._transcribe_chunk(audio)
                if text:
                    self.on_result(timestamp, channel, speaker, text)
            except Exception as exc:
                if self.on_error:
                    self.on_error(exc)

    def _transcribe_chunk(self, audio: np.ndarray) -> str:
        """
        Transcreve um chunk de áudio e filtra alucinações.

        Returns:
            Texto transcrito limpo, ou string vazia se filtrado/inválido.
        """
        # 1. Normaliza amplitude para resolver voz baixa
        audio = normalize_amplitude(audio)

        # 2. Transcreve com Whisper
        segments, _ = self._model.transcribe(
            audio,
            language=WHISPER_LANGUAGE,
            beam_size=WHISPER_BEAM,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=200,
                speech_pad_ms=100,
            ),
            condition_on_previous_text=False,
        )

        # 3. Filtra segmentos com baixa confiança (alucinações)
        valid_parts: list[str] = []
        for seg in segments:
            if seg.no_speech_prob > NO_SPEECH_THRESHOLD:
                continue   # provavelmente silêncio ou ruído
            if seg.avg_logprob < AVG_LOGPROB_THRESHOLD:
                continue   # muito incerto — descarta
            text = seg.text.strip()
            if text:
                valid_parts.append(text)

        return " ".join(valid_parts)
