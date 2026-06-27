"""
audio/echo_guard.py — Bus simples para reduzir eco mic↔sistema.

Cenário típico: usuário sem fones de ouvido. O áudio do canal "Sistema"
(WASAPI loopback) sai pelo alto-falante, o microfone capta de volta, e a fala
do interlocutor aparece duplicada — uma vez no canal sistema, outra no canal
microfone.

Solução pragmática (ducking por tempo):
  • Sempre que o canal sistema fecha um chunk de fala, registramos o instante.
  • Antes de aceitar um chunk do microfone, checamos se sistema falou nos
    últimos `window_s` segundos. Se sim, descartamos como provável eco.

Trade-off: enquanto outra pessoa está falando, sua voz não é capturada
(cross-talk perdido). Recomendamos fones para casos onde isso é relevante.

Não cobre:
  • Eco com delay maior que `window_s` (sala muito reverberante).
  • Eco enquanto o sistema está em fala contínua (mic descarta o tempo todo).

Esta é a iteração 1. Se eco continuar escapando, pode-se adicionar checagem
de similaridade de embedding (M3-extra) ou AEC (webrtc-audio-processing).
"""

from __future__ import annotations

import threading
import time


class EchoGuard:
    """Bus thread-safe entre os canais sistema e microfone."""

    def __init__(self, window_s: float = 0.5):
        self._lock = threading.Lock()
        self._last_system_active = 0.0
        self._window_s = window_s
        self._dropped_count = 0

    # ── Sistema marca atividade ────────────────────────────────────────────────

    def mark_system_active(self) -> None:
        """Chamado quando o canal sistema fecha um chunk de fala."""
        with self._lock:
            self._last_system_active = time.time()

    # ── Microfone consulta ─────────────────────────────────────────────────────

    def should_drop_mic(self) -> bool:
        """True se sistema esteve ativo nos últimos `window_s` segundos."""
        with self._lock:
            return (time.time() - self._last_system_active) < self._window_s

    # ── Métricas ──────────────────────────────────────────────────────────────

    def record_drop(self) -> int:
        with self._lock:
            self._dropped_count += 1
            return self._dropped_count

    @property
    def dropped(self) -> int:
        with self._lock:
            return self._dropped_count
