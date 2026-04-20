"""
config.py — Configurações centralizadas do Meeting Transcriber.

Todas as constantes ajustáveis ficam aqui.
Altere este arquivo para calibrar o comportamento sem tocar na lógica.
"""

import sys
from pathlib import Path

# ── Resolução de Caminhos (PyInstaller) ────────────────────────────────────────
def get_base_path():
    """Retorna a raiz do executável ou do script."""
    if getattr(sys, 'frozen', False):
        # Se for executável, retorna a pasta onde o .exe está
        return Path(sys.executable).parent
    return Path(__file__).parent

BASE_DIR = get_base_path()

# ── Modelo Whisper ─────────────────────────────────────────────────────────────
WHISPER_MODEL    = "medium"   # small | medium | large-v3
WHISPER_LANGUAGE = "pt"       # None = detecção automática | "pt" | "en"
WHISPER_BEAM     = 10         # candidatos por passo (maior = melhor, mais lento)
WHISPER_DEVICE   = "cpu"      # "cpu" | "cuda"
WHISPER_COMPUTE  = "int8"     # "int8" (cpu) | "float16" (gpu)

# ── Filtros anti-alucinação ────────────────────────────────────────────────────
# Segmentos com probabilidade de silêncio acima deste valor são descartados
NO_SPEECH_THRESHOLD  = 0.60
# Segmentos com log-prob médio abaixo deste valor são descartados (muito incertos)
AVG_LOGPROB_THRESHOLD = -1.0

# ── VAD (Voice Activity Detection) ────────────────────────────────────────────
# Thresholds de energia RMS por canal — ajuste se o microfone for muito fraco/forte
VAD_THRESHOLD_SISTEMA   = 0.00005  # canal de áudio do sistema (calibrado via diagnostico.py)
VAD_THRESHOLD_MICROFONE = 0.00038  # microfone (calibrado via diagnostico.py)

VAD_SILENCE_MS    = 800    # ms de silêncio para fechar um chunk de fala
VAD_MIN_SPEECH_MS = 250    # duração mínima de fala para não descartar o chunk
VAD_MAX_SPEECH_MS = 15000  # duração máxima antes de forçar flush

# ── Dispositivos de áudio ──────────────────────────────────────────────────────
# Use: python diagnostico.py para descobrir os índices corretos
# Loopback/mixagem estéreo: tente 7, 12 ou 20 se um deles não funcionar
DEVICE_SISTEMA   = 20   # Mixagem estéreo (Realtek HD Audio Stereo input) — 48kHz
DEVICE_MICROFONE = 16   # Microfone (Realtek HD Audio Mic input) — 44100Hz

# ── Áudio interno ─────────────────────────────────────────────────────────────
TARGET_SR = 16_000   # sample rate esperado pelo Whisper (não altere)

# ── Diarização ────────────────────────────────────────────────────────────────
# Similaridade mínima (cosine) para considerar dois chunks do mesmo falante
DIARIZATION_SIMILARITY_THRESHOLD = 0.75
# Número máximo de falantes distintos esperados por sessão
DIARIZATION_MAX_SPEAKERS = 8

# ── Perfis de voz persistentes ────────────────────────────────────────────────
PROFILES_DIR = Path.home() / ".meeting_transcriber"
PROFILES_FILE = PROFILES_DIR / "voice_profiles.json"

# ── Saída ─────────────────────────────────────────────────────────────────────
OUTPUT_DIR = BASE_DIR / "transcricoes"