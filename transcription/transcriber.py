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

import time
import queue
import threading
import numpy as np
from faster_whisper import WhisperModel

from audio.resampler import normalize_amplitude
from diarization import DiarizationEngine
from config import (
    NO_SPEECH_THRESHOLD,
    AVG_LOGPROB_THRESHOLD,
    TARGET_SR,
)
import settings


def _detect_device() -> tuple[str, str]:
    """
    Detecta hardware disponível e devolve (device, compute_type) ótimos.

    Ordem (D5):
      1. CUDA → ("cuda", "float16")
      2. fallback CPU → ("cpu", "int8")
    """
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


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

        # Acumulação de blocos: o Whisper transcreve MUITO melhor com áudio
        # contínuo (~10s) do que com frases curtas isoladas — em blocos de 1–4s
        # o avg_logprob despenca e o filtro anti-alucinação corta quase tudo.
        # Juntamos os chunks do VAD por canal até ~block_target_sec, ou quando o
        # canal fica em silêncio por block_idle_sec (a pessoa parou de falar).
        self._block_target_sec = 10.0
        self._block_idle_sec   = 1.5

    # ── Ciclo de vida ──────────────────────────────────────────────────────────

    def load_async(self) -> None:
        """Carrega o modelo Whisper em background."""
        threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self) -> None:
        try:
            cfg = settings.load()
            model_name = cfg.get("whisper_model") or "small"
            device, compute = _detect_device()
            print(
                f"[Whisper] carregando '{model_name}' "
                f"(device={device}, compute={compute})...",
                flush=True,
            )
            self._model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute,
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
        """
        Consome a fila acumulando áudio por canal em blocos maiores antes de
        transcrever. Frases curtas isoladas transcrevem mal no Whisper (falta de
        contexto); juntamos os chunks do VAD até ~block_target_sec, ou quando o
        canal fica em silêncio por block_idle_sec.

        A diarização roda sobre o bloco inteiro (mais áudio = embedding melhor).
        """
        accum: dict[str, dict] = {}  # channel -> {"chunks", "first_ts", "last_add"}

        def flush(channel: str) -> None:
            buf = accum.pop(channel, None)
            if not buf or not buf["chunks"]:
                return
            audio = np.concatenate(buf["chunks"]).astype(np.float32)

            speaker = None
            if self.diarization is not None:
                try:
                    speaker = self.diarization.identify(audio, channel)
                except Exception as exc:
                    print(f"[Transcriber] diarização falhou: {exc}", flush=True)

            try:
                text = self._transcribe_chunk(audio)
            except Exception as exc:
                if self.on_error:
                    self.on_error(exc)
                return

            if text:
                self.on_result(buf["first_ts"], channel, speaker, text)

        while not self._stop_event.is_set() or not self._queue.empty() or accum:
            try:
                timestamp, channel, _spk, audio = self._queue.get(timeout=0.3)
                buf = accum.get(channel)
                if buf is None:
                    buf = {"chunks": [], "first_ts": timestamp, "last_add": time.time()}
                    accum[channel] = buf
                buf["chunks"].append(audio)
                buf["last_add"] = time.time()
                if sum(len(c) for c in buf["chunks"]) / TARGET_SR >= self._block_target_sec:
                    flush(channel)
            except queue.Empty:
                pass

            # Flush por inatividade. Ao parar (fila já drenada), flush imediato
            # para não perder o último trecho.
            draining = self._stop_event.is_set() and self._queue.empty()
            idle_limit = 0.0 if draining else self._block_idle_sec
            now = time.time()
            for channel in list(accum.keys()):
                if now - accum[channel]["last_add"] >= idle_limit:
                    flush(channel)

    def _transcribe_chunk(self, audio: np.ndarray) -> str:
        """
        Transcreve um chunk de áudio e filtra alucinações.

        Returns:
            Texto transcrito limpo, ou string vazia se filtrado/inválido.
        """
        # 1. Normaliza amplitude para resolver voz baixa
        audio = normalize_amplitude(audio)

        # 2. Transcreve com Whisper. VAD é feito a montante (silero, em
        # `audio/capture.py`); aqui desligamos o VAD do Whisper (D3).
        cfg = settings.load()
        segments, _ = self._model.transcribe(
            audio,
            language=cfg.get("whisper_language") or "pt",
            beam_size=int(cfg.get("whisper_beam") or 5),
            vad_filter=False,
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
