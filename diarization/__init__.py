"""
diarization/__init__.py — Orquestrador de diarização.
"""

from __future__ import annotations
import sys
import os
from collections import deque
import numpy as np

# Força o caminho da pasta atual para que o PyInstaller encontre os submódulos
sys.path.append(os.path.dirname(__file__))

try:
    from diarization.embedder import extract_embedding, cosine_similarity
    from diarization.profiles import ProfileManager
except ImportError:
    # Fallback para quando o PyInstaller achata a estrutura no executável
    try:
        from .embedder import extract_embedding, cosine_similarity
        from .profiles import ProfileManager
    except ImportError:
        import embedder
        import profiles
        extract_embedding = embedder.extract_embedding
        cosine_similarity = embedder.cosine_similarity
        ProfileManager = profiles.ProfileManager

from config import DIARIZATION_SIMILARITY_THRESHOLD

# Segundos de áudio acumulado por canal para contexto de embedding
_CONTEXT_SECONDS = 3.0
_CONTEXT_SAMPLES = int(_CONTEXT_SECONDS * 16_000)   # em 16kHz

# Fração mínima de áudio novo em relação ao buffer para aceitar troca de falante
_MIN_SCORE_TO_SWITCH = DIARIZATION_SIMILARITY_THRESHOLD + 0.05


class DiarizationEngine:
    """
    Identificação de falantes com contexto acumulado e fallback por canal.
    """

    def __init__(self):
        self._profiles  = ProfileManager()
        self._available = True

        # Estado por canal: label → (buffer, último_falante, último_embedding)
        self._channel_buffers  : dict[str, deque]          = {}
        self._last_speaker     : dict[str, str]            = {}
        self._last_embedding   : dict[str, np.ndarray | None] = {}

        try:
            from resemblyzer import VoiceEncoder  # noqa: F401
        except ImportError:
            self._available = False
            print("[Diarização] resemblyzer não instalado.")

    @property
    def available(self) -> bool:
        return self._available

    def _channel_key(self, label: str) -> str:
        return "sistema" if "Sistema" in label else "microfone"

    def _get_buffer(self, key: str) -> deque:
        if key not in self._channel_buffers:
            self._channel_buffers[key] = deque(maxlen=_CONTEXT_SAMPLES)
        return self._channel_buffers[key]

    def _push_audio(self, key: str, audio: np.ndarray) -> np.ndarray:
        buf = self._get_buffer(key)
        buf.extend(audio.tolist())
        return np.array(buf, dtype=np.float32)

    def identify(self, audio: np.ndarray, label: str = "") -> str | None:
        if not self._available:
            return None

        key = self._channel_key(label)
        ctx_audio = self._push_audio(key, audio)
        embedding = extract_embedding(ctx_audio)

        if embedding is None:
            return self._last_speaker.get(key)

        speaker = self._profiles.identify(embedding)
        last_emb = self._last_embedding.get(key)
        if last_emb is not None and self._last_speaker.get(key) is not None:
            continuity_score = cosine_similarity(embedding, last_emb)
            if continuity_score >= _MIN_SCORE_TO_SWITCH:
                speaker = self._last_speaker[key]

        self._last_speaker[key]   = speaker
        self._last_embedding[key] = embedding
        return speaker

    def register(self, name: str, audio: np.ndarray) -> bool:
        if not self._available: return False
        embedding = extract_embedding(audio)
        if embedding is None: return False
        self._profiles.save_profile(name, embedding)
        return True

    def delete_profile(self, name: str) -> bool:
        return self._profiles.delete_profile(name)

    def save_session_speaker(self, session_label: str, new_name: str) -> bool:
        return self._profiles.promote_session_speaker(session_label, new_name)

    def list_profiles(self) -> list[str]:
        return self._profiles.list_profiles()

    def reset_session(self) -> None:
        self._profiles.reset_session()
        self._channel_buffers.clear()
        self._last_speaker.clear()
        self._last_embedding.clear()
