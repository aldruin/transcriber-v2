# Definições — Vocabulário e Decisões Técnicas

Glossário compartilhado e registro de decisões. Antes de virar código, cada
decisão técnica do `PLANO.md` precisa estar resolvida aqui.

`[PENDENTE]` = ainda em discussão · `[DECIDIDO]` = pode virar código.

---

## Glossário

- **Loopback / Stereo Mix / Monitor source** — captura do que está saindo dos
  alto-falantes do sistema, tratando como se fosse uma entrada (microfone
  virtual). Cada SO faz isso de um jeito.
- **VAD (Voice Activity Detection)** — algoritmo que decide se um pedaço de
  áudio é fala ou silêncio/ruído. Hoje usamos limiar de energia RMS.
- **Embedding de voz** — vetor numérico (256 dimensões no resemblyzer) que
  representa a "impressão digital" da voz de uma pessoa. Vozes parecidas
  produzem vetores próximos (similaridade cosine alta).
- **Diarização** — processo de responder "quem falou quando". Aqui é feito por
  comparação de embeddings com perfis conhecidos e com falantes anônimos da
  sessão.
- **Chunk** — pedaço de áudio fechado pelo VAD entre dois silêncios; unidade
  enviada para o Whisper transcrever.
- **Perfil de voz** — embedding nomeado e persistido em
  `~/.meeting_transcriber/voice_profiles.json`. Sobrevive a sessões.
- **Sessão** — execução desde o "Iniciar" até o "Parar". Falantes anônimos
  (`Falante_1`, `Falante_2`) só existem dentro da sessão.
- **Canal** — identifica de onde veio o áudio: `sistema` (loopback) ou
  `microfone` (entrada física do usuário).

---

## Decisões da Fase 0

### D1 — Backend de captura de áudio
**Status:** `[REVISADO em 2026-05-03]` → **híbrido (sounddevice + soundcard)**

Verificado em runtime: `sounddevice 0.5.5` não expõe a flag de WASAPI loopback
do PortAudio (`WasapiSettings` aceita só `exclusive`/`auto_convert`/
`explicit_sample_format`). A opção C original não é viável.

Solução adotada:
- **Microfone (todos os SOs):** `sounddevice.InputStream` (mantém o stack
  atual).
- **Sistema/loopback:**
  - **Windows:** `soundcard` (WASAPI loopback nativo no dispositivo de saída
    padrão, sem Stereo Mix).
  - **Linux:** `sounddevice.InputStream` apontando para o `*.monitor` do
    sink default (PulseAudio/PipeWire).
  - **macOS:** `sounddevice.InputStream` apontando para BlackHole / Aggregate
    Device. Se ausente, wizard instrui instalação.

Implicação: `requirements.txt` ganha `soundcard>=0.4.3`. `VoiceCapture` ganha
um modo "polling" para alimentar o pipeline a partir do recorder do
`soundcard`.

---

### D2 — VAD
**Status:** `[DECIDIDO]` → **silero-vad**

Modelo ONNX, ~2 MB, multilíngue, sem calibração de threshold por hardware.
Substitui completamente o VAD por RMS atual. Remover `VAD_THRESHOLD_*` e o
passo de "calibração" do wizard.

---

### D3 — VAD redundante (M6)
**Status:** `[DECIDIDO]` → **silero-vad próprio + Whisper sem VAD**

Em `transcription/transcriber.py`, passar `vad_filter=False`. O silero-vad
próprio (D2) já entrega chunks limpos para o Whisper. Comportamento fica mais
previsível e elimina dupla filtragem.

---

### D4 — Modelo Whisper default
**Status:** `[DECIDIDO]` → **small**

| Modelo  | Tamanho | Qualidade pt-BR | Velocidade CPU |
|---------|---------|-----------------|----------------|
| tiny    | 75 MB   | Ruim            | Muito rápida   |
| base    | 142 MB  | OK              | Rápida         |
| **small** | **466 MB** | **Boa**     | **Média**      |
| medium  | 1.5 GB  | Muito boa       | Lenta          |
| large-v3| 3 GB    | Excelente       | Muito lenta    |

`small` como default + seletor na UI (`base`/`small`/`medium`/`large-v3`).
Quem tem GPU sobe livremente.

---

### D5 — Aceleração por hardware
**Status:** `[DECIDIDO]`

Detecção automática em ordem:
1. CUDA disponível (`torch.cuda.is_available()`) → `device=cuda, compute=float16`
2. Fallback → `device=cpu, compute=int8`

macOS Apple Silicon: faster-whisper não suporta Metal direto hoje, vai para
CPU (int8). DirectML (Windows AMD/Intel) e ROCm (Linux AMD) ficam fora do
escopo inicial.

---

### D6 — Empacotamento por SO
**Status:** `[DECIDIDO]`

- **Windows:** `.exe` único (já feito).
- **Linux:** `AppImage` (mais portátil). CI baixa `appimagetool` no job.
- **macOS:** `.app` empacotado em `.dmg` **não assinado**. Usuário libera no
  Gatekeeper na 1ª execução. Code signing fica fora do escopo.

---

### D7 — Nome do perfil do usuário (microfone)
**Status:** `[DECIDIDO]` → **perguntar no wizard, default `"Eu"`**

Adicionar passo no `setup_wizard.py`: campo de texto pré-preenchido com `"Eu"`.
Resultado salvo em `settings.json` como `user_profile_name`. Ao iniciar uma
sessão (M3), o áudio do canal microfone é atribuído a esse nome
automaticamente.

---

### D8 — Empacotar o modelo Whisper no binário?
**Status:** `[DECIDIDO]` → **baixar no 1º uso**

Binário fica leve (~80 MB sem o modelo). O faster-whisper baixa o modelo
escolhido para `~/.cache/huggingface/` na 1ª execução.

Implicações:
- 1ª execução exige internet (~466 MB para `small`).
- O wizard deve avisar antes de baixar (com barra de progresso, idealmente).
- Trocar de modelo nas configurações dispara novo download.

---

## Convenções de código (a manter)

- Imports relativos dentro de cada pacote, absolutos entre pacotes.
- `print(...)` para diagnóstico ainda é aceitável (não migrar para `logging`
  agora; fora do escopo).
- Callbacks de UI sempre via `root.after(0, ...)` — não tocar UI direto de
  threads.
- Toda configuração persistida vai em `~/.meeting_transcriber/` (settings,
  perfis, eventualmente cache de modelo).

---

## Itens fora do escopo (registrar para não esquecer)

- Suporte a DirectML/ROCm.
- Code signing dos binários macOS/Windows.
- Versão web (Flask/FastAPI + frontend).
- Migração para PyQt/PySide.
- Exportação `.docx` / `.srt` (já está no roadmap do README, mas não nesta
  evolução).
- Resumo automático com LLM local (idem).
