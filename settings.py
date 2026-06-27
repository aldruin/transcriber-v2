"""
settings.py — Configurações persistidas em ~/.meeting_transcriber/settings.json.

Esta é a ÚNICA fonte de verdade em runtime. `config.py` provê apenas defaults
imutáveis (valores de fábrica). Toda escrita passa por `save()`; toda leitura
por `load()` ou `get()`.
"""

from __future__ import annotations

import json
from typing import Any

import config

SETTINGS_FILE = config.PROFILES_DIR / "settings.json"

# Defaults. `None` em campos de dispositivo significa "ainda não configurado"
# e dispara o wizard na primeira execução.
_DEFAULTS: dict[str, Any] = {
    "device_sistema":     None,
    "device_microfone":   None,
    "thresh_sistema":     config.VAD_THRESHOLD_SISTEMA,
    "thresh_microfone":   config.VAD_THRESHOLD_MICROFONE,
    "whisper_model":      config.WHISPER_MODEL,
    "whisper_language":   config.WHISPER_LANGUAGE,
    "whisper_beam":       config.WHISPER_BEAM,
    "user_profile_name":  "Eu",
}


def load() -> dict[str, Any]:
    """Retorna defaults + valores persistidos (persistidos têm prioridade)."""
    data = dict(_DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            data.update({k: v for k, v in saved.items() if v is not None})
        except Exception as exc:
            print(f"[settings] Erro ao ler {SETTINGS_FILE}: {exc}")
    return data


def save(updates: dict[str, Any]) -> None:
    """Persiste merge dos updates sobre o que já está salvo (não sobre defaults)."""
    config.PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    existing: dict[str, Any] = {}
    if SETTINGS_FILE.exists():
        try:
            existing = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    merged = {**existing, **updates}
    SETTINGS_FILE.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get(key: str, default: Any = None) -> Any:
    """Atalho para load().get(key, default)."""
    return load().get(key, default)


def is_first_run() -> bool:
    """True se o usuário ainda não passou pelo wizard.

    Detectamos pela existência do arquivo + presença obrigatória do mic.
    `device_sistema` pode ser None legitimamente (loopback automático).
    """
    if not SETTINGS_FILE.exists():
        return True
    saved = load()
    return saved.get("device_microfone") is None
