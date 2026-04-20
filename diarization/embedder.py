"""
diarization/embedder.py — Extração de embeddings de voz com resemblyzer.

Responsabilidades:
- Gerar um vetor de 256 dimensões que representa a "impressão digital" de voz
- Calcular similaridade cosine entre embeddings
- Abstrair o resemblyzer para que o resto do código não dependa dele diretamente
"""

from __future__ import annotations
import numpy as np

# Importação lazy para não bloquear a UI se resemblyzer não estiver instalado
_encoder = None

def _get_encoder():
    """Carrega o encoder GE2E na primeira chamada (singleton)."""
    global _encoder
    if _encoder is None:
        try:
            from resemblyzer import VoiceEncoder
            _encoder = VoiceEncoder(device="cpu")
        except Exception as exc:
            print(f"[Embedder] FALHA CRÍTICA ao carregar VoiceEncoder: {exc}")
            import sys
            print(f"[Embedder] sys.path: {sys.path}")
            return None
    return _encoder

def extract_embedding(audio: np.ndarray) -> np.ndarray | None:
    """
    Extrai o embedding de voz de um chunk de áudio.
    """
    encoder = _get_encoder()
    if encoder is None:
        return None
    
    # GE2E precisa de pelo menos ~0.8s para ser confiável
    MIN_SAMPLES = 12_800   # 0.8s × 16000 Hz
    if len(audio) < MIN_SAMPLES:
        return None

    try:
        # resemblyzer espera áudio pré-processado: float64, 16kHz
        audio_f64 = audio.astype(np.float64)

        # embed_utterance lida internamente com janelamento e média
        from resemblyzer import preprocess_wav
        wav = preprocess_wav(audio_f64, source_sr=16_000)
        embedding = encoder.embed_utterance(wav)
        return embedding.astype(np.float32)

    except Exception as exc:
        print(f"[Embedder] Erro ao extrair embedding: {exc}")
        return None

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calcula a similaridade cosine entre dois embeddings.
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-8 or norm_b < 1e-8:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
