"""
config.py — Defaults de fábrica do Meeting Transcriber.

Este módulo só guarda VALORES IMUTÁVEIS. A configuração efetiva em runtime
mora em `settings.py` (lê/grava `~/.meeting_transcriber/settings.json`).

Para alterar comportamento sem reinstalar, mexa nas configurações pela UI.
Mexer aqui só altera o que vem "de fábrica" para usuários novos.
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
# `device` e `compute_type` são detectados em runtime pelo `transcriber.py`
# (CUDA → float16; CPU → int8). Aqui ficam apenas valores informativos.
WHISPER_MODEL    = "medium"   # tiny | base | small | medium | large-v3
WHISPER_LANGUAGE = "pt"       # None = detecção automática | "pt" | "en"
WHISPER_BEAM     = 5          # candidatos por passo (maior = melhor, mais lento)

# ── Filtros anti-alucinação ────────────────────────────────────────────────────
# Segmentos com probabilidade de silêncio acima deste valor são descartados
NO_SPEECH_THRESHOLD  = 0.60
# Segmentos com log-prob médio abaixo deste valor são descartados (muito incertos)
AVG_LOGPROB_THRESHOLD = -1.0

# ── VAD (silero-vad faz a decisão) ────────────────────────────────────────────
# Estes valores existem só para o medidor visual da UI mostrar uma referência
# de "abaixo disso não está pegando som". Não dirigem mais o VAD.
VAD_THRESHOLD_SISTEMA   = 0.00005
VAD_THRESHOLD_MICROFONE = 0.00038

# ── Áudio interno ─────────────────────────────────────────────────────────────
TARGET_SR = 16_000   # sample rate esperado pelo Whisper (não altere)

# ── Diarização ────────────────────────────────────────────────────────────────
# Similaridade mínima (cosine) para considerar dois chunks como o MESMO falante.
# Calibrado empiricamente (resemblyzer/GE2E em trechos curtos de fala): a MESMA
# pessoa fica tipicamente em 0.60–0.94 e pessoas DIFERENTES abaixo de ~0.50.
# O valor antigo (0.75) cortava no meio da faixa da própria pessoa e
# super-segmentava (1 voz virava 2–4 "Falante_N"). 0.60 fica no "vale" entre as
# duas distribuições; a reconciliação fina de falantes pode ser delegada ao LLM
# de curadoria. Reajuste com áudio real via tools/calibrar_diarizacao.py.
DIARIZATION_SIMILARITY_THRESHOLD = 0.60
# Número máximo de falantes distintos esperados por sessão
DIARIZATION_MAX_SPEAKERS = 8

# ── Perfis de voz persistentes ────────────────────────────────────────────────
PROFILES_DIR = Path.home() / ".meeting_transcriber"
PROFILES_FILE = PROFILES_DIR / "voice_profiles.json"

# ── Saída ─────────────────────────────────────────────────────────────────────
OUTPUT_DIR = BASE_DIR / "transcricoes"