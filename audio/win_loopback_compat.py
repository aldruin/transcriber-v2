"""
audio/win_loopback_compat.py — Correções de ambiente do loopback WASAPI no
Windows via `soundcard`.

Dois problemas conhecidos impedem a captura do áudio do sistema (e eram a
causa raiz do "ninguém consegue configurar"):

1. NumPy 2.x removeu `np.fromstring` em modo binário, que o `SoundCard 0.4.5`
   ainda usa ao montar cada chunk (`mediafoundation.py`). Sem o patch, toda
   captura estoura `ValueError: binary mode of fromstring is removed`.

2. O recorder do `soundcard` usa COM (WASAPI). COM é inicializado POR-THREAD;
   como a captura roda numa thread dedicada, é preciso chamar `CoInitializeEx`
   nela, senão estoura `RuntimeError: Error 0x800401f0` (CO_E_NOTINITIALIZED).

Ambos só se aplicam ao Windows. As funções são no-ops em outros SOs e
idempotentes (seguro chamar várias vezes / em toda thread de captura).
"""

from __future__ import annotations

import platform

_IS_WINDOWS = platform.system() == "Windows"
_numpy_patched = False


def patch_soundcard_numpy2() -> None:
    """
    Reabilita `np.fromstring` (modo binário) delegando para `np.frombuffer`,
    que é o equivalente moderno. Necessário para `SoundCard 0.4.5` + NumPy 2.x.
    Idempotente; no-op fora do Windows.
    """
    global _numpy_patched
    if _numpy_patched or not _IS_WINDOWS:
        return

    import numpy as np

    _orig_fromstring = np.fromstring

    def _fromstring_compat(buffer, dtype=float, count=-1, sep=""):
        # sep == "" → modo binário (o que o soundcard usa). Modo texto (sep != "")
        # ainda existe e é delegado ao original.
        if sep == "":
            # .copy() é essencial: o soundcard recicla o buffer logo depois
            # (_capture_release), então uma view corromperia o áudio (fica
            # "robótico"). O np.fromstring original também copiava.
            arr = np.frombuffer(buffer, dtype=dtype).copy()
            return arr if count < 0 else arr[:count]
        return _orig_fromstring(buffer, dtype=dtype, count=count, sep=sep)

    np.fromstring = _fromstring_compat
    _numpy_patched = True


def ensure_com_initialized() -> None:
    """
    Inicializa COM (apartment-threaded) na thread atual. Deve ser chamada DENTRO
    da thread que abre o recorder do soundcard. No-op fora do Windows.
    """
    if not _IS_WINDOWS:
        return
    import ctypes

    # COINIT_APARTMENTTHREADED = 0x2.
    # Retornos toleráveis: S_OK(0), S_FALSE(1, já inicializado nesta thread),
    # RPC_E_CHANGED_MODE(0x80010106, outra thread pediu modo diferente).
    try:
        ctypes.windll.ole32.CoInitializeEx(None, 0x2)
    except Exception as exc:
        print(f"[win_compat] CoInitializeEx falhou: {exc}", flush=True)


def com_uninitialize() -> None:
    """Encerra COM na thread atual (par de `ensure_com_initialized`)."""
    if not _IS_WINDOWS:
        return
    import ctypes

    try:
        ctypes.windll.ole32.CoUninitialize()
    except Exception:
        pass
