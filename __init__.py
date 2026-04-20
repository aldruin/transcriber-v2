"""
diarization/__init__.py — Orquestrador de diarização.

Expõe a classe DiarizationEngine que integra:
- Extração de embeddings (embedder.py)
- Identificação de falantes (profiles.py)

Uso:
    engine = DiarizationEngine()
    name   = engine.identify(audio_chunk)   # "Márcio" ou "Falante_1"
    engine.register("Márcio", audio_chunk)  # salva perfil persistente
"""

from __future__ import annotations

import numpy as np

from diarization.embedder  import extract_embedding
from diarization.profiles  import ProfileManager


class DiarizationEngine:
    """
    Ponto de entrada para diarização de falantes.

    Combina extração de embedding e gerenciamento de perfis em uma
    interface simples para o resto da aplicação.
    """

    def __init__(self):
        self._profiles = ProfileManager()
        self._available = True

        # Testa se resemblyzer está instalado
        try:
            from resemblyzer import VoiceEncoder  # noqa: F401
        except ImportError:
            self._available = False
            print(
                "[Diarização] resemblyzer não instalado. "
                "Instale com: pip install resemblyzer\n"
                "Diarização desativada — transcrição continua normalmente."
            )

    @property
    def available(self) -> bool:
        """True se resemblyzer está instalado e diarização está ativa."""
        return self._available

    def identify(self, audio: np.ndarray) -> str | None:
        """
        Identifica o falante de um chunk de áudio.

        Args:
            audio: Float32 em 16kHz.

        Returns:
            Nome do falante, ou None se não foi possível extrair embedding.
        """
        if not self._available:
            return None

        embedding = extract_embedding(audio)
        if embedding is None:
            return None

        return self._profiles.identify(embedding)

    def register(self, name: str, audio: np.ndarray) -> bool:
        """
        Registra um perfil de voz com nome associado.

        Args:
            name:  Nome do falante.
            audio: Áudio de referência (pelo menos ~2s de fala limpa).

        Returns:
            True se salvo com sucesso, False se falhou.
        """
        if not self._available:
            return False

        embedding = extract_embedding(audio)
        if embedding is None:
            return False

        self._profiles.save_profile(name, embedding)
        return True

    def delete_profile(self, name: str) -> bool:
        return self._profiles.delete_profile(name)

    def list_profiles(self) -> list[str]:
        return self._profiles.list_profiles()

    def reset_session(self) -> None:
        """Deve ser chamado ao iniciar uma nova gravação."""
        self._profiles.reset_session()
