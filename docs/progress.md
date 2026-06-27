# Progresso — Plano de Evolução

Acompanhamento do plano em `PLANO.md`. Atualizar **ao concluir cada item**:
marcar checkbox, anotar data e uma linha de nota se útil.

Status: `[ ]` pendente · `[~]` em andamento · `[x]` concluído · `[!]` bloqueado

Início: 2026-05-03

---

## Fase 0 — Definições

- [x] D1 — Backend de captura: híbrido (sounddevice + soundcard p/ WASAPI Win; revisado durante a Fase 2)
- [x] D2 — VAD: silero-vad
- [x] D3 — Remover VAD redundante: silero próprio + Whisper sem VAD
- [x] D4 — Modelo default: `small`
- [x] D5 — Aceleração: CUDA float16 → fallback CPU int8
- [x] D6 — Empacotamento: `.exe` / AppImage / `.dmg` não assinado
- [x] D7 — Perfil do usuário: wizard pergunta, default `"Eu"`
- [x] D8 — Modelo: download no 1º uso (não empacota)

---

## Fase 1 — Base limpa

- [x] M4: `settings.py` central, `config.py` só com defaults imutáveis
- [x] M5: wizard rodando antes do `TranscriberApp` (sem destroy/recreate)

---

## Fase 2 — Captura multiplataforma (Frente A)

- [x] `audio/loopback.py` com detecção por SO + `LoopbackConfig`
- [x] Windows: WASAPI loopback via `soundcard` (sounddevice 0.5.5 não expõe a flag — D1 revisado)
- [x] Linux: monitor source automático (PulseAudio/PipeWire)
- [x] macOS: detectar BlackHole/Aggregate/Soundflower
- [x] `VoiceCapture` com dois backends (`_run_sounddevice` + `_run_soundcard`)
- [x] Wizard pula seleção de Stereo Mix quando loopback automático funciona
- [x] `requirements.txt` adiciona `soundcard>=0.4.3`

---

## Fase 3 — VAD universal

- [x] M1: silero-vad integrado em `VoiceCapture` (VADIterator stateful por canal)
- [x] Constantes RMS de janela/silêncio removidas (`config.py` enxuto)
- [x] M6: `vad_filter=False` no Whisper — silero é o único VAD do pipeline
- [x] `requirements.txt` adiciona `silero-vad>=6.0`

---

## Fase 4 — Whisper eficiente (Frente C)

- [x] Default `small` + `beam=5`
- [x] Auto-detect CUDA → float16 / fallback CPU → int8 (`_detect_device`)
- [x] Seletor de modelo em `SettingsWindow` (5 opções, com tamanho/qualidade)
- [x] Aviso "Baixando modelo..." vs "Carregando modelo..." no status inicial

---

## Fase 5 — Diarização e UX

- [x] M2: `_transcribe_loop` paraleliza diarização e transcrição via ThreadPoolExecutor
- [x] M3: canal microfone retorna automaticamente o nome do usuário (default "Eu")
- [x] `ProfileManager.update_user_profile` cria/refina o perfil persistido com média 90/10
- [x] D7: wizard pergunta nome do usuário, salvo em `user_profile_name`

---

## Fase 6 — CI multiplataforma (Frente B)

- [x] `app.spec` portátil (sem `os.getcwd()` aninhado), `hidden_imports` cobre soundcard/silero-vad/torchaudio
- [x] `.github/workflows/release.yml` com matriz Win/Linux/macOS
- [x] Linux empacota AppImage; macOS empacota .app+.dmg; Windows publica .exe
- [x] Job de release agrega artefatos e cria release no GitHub via tag `v*`
- [x] `build_exe.py` simplificado para usar `requirements.txt`
- [x] README atualizado: links por SO, nota sobre WASAPI loopback no Windows, destaques revisados

---

## Notas de execução

(linha por entrada, mais recente em cima)

- 2026-05-03 — Fix: modelo silero é stateful (GRU). Compartilhar entre os dois canais corrompia a hidden state e fechava o app. Cada `VoiceCapture` agora tem instância própria. Try/except adicionado no inferência.
- 2026-05-03 — VAD reescrito com loop manual sobre o modelo silero (sem VADIterator). Distingue silêncio "final" (≥320ms, fecha frase) de "micro-pausa" (~120ms, dispara parcial se fala já tem ≥250ms). Resultado: flush em pontos naturais, não por timer.
- 2026-05-03 — `EchoGuard` (audio/echo_guard.py) implementa ducking por janela de 500ms: chunks do mic são descartados se o sistema falou recentemente. Aviso de "use fones" adicionado ao passo 1 do wizard.
- 2026-05-03 — Ajustes pós-teste do usuário: default volta a `medium` (qualidade), `min_silence_ms` 400→200, `speech_pad_ms` 100→50, e flush incremental a cada 4s de fala contínua. Aviso de "alguns segundos por frase" no boot.
- 2026-05-03 — Fase 6 fechada (pendente teste real em CI). `app.spec` revisado, workflow `release.yml` com matriz 3 SOs, AppImage Linux + .dmg macOS + .exe Windows, job de release publicando via tag `v*`. README pendente até primeira release.
- 2026-05-03 — Fase 5 fechada. Diarização e Whisper rodam em paralelo via ThreadPoolExecutor. Canal microfone retorna automaticamente o `user_profile_name` (D7) e refina o perfil persistido. Wizard ganhou campo de nome.
- 2026-05-03 — Fase 4 fechada. Whisper default agora é `small` com `beam=5`. `_detect_device()` escolhe CUDA/float16 ou CPU/int8. UI ganhou seletor de modelo (tiny/base/small/medium/large-v3) que persiste em `whisper_model`. Status inicial diferencia "Baixando" de "Carregando".
- 2026-05-03 — Fase 3 fechada. VAD do projeto agora é silero-vad streaming (`VADIterator`) operando em 16 kHz com chunks de 512 amostras. Whisper passou a `vad_filter=False`. Plumbing testado; modelo carrega; pipeline não dispara em tom puro (esperado — silero é treinado em fala).
- 2026-05-03 — Fase 2 fechada. Loopback de sistema funciona em Windows (soundcard/WASAPI), Linux (monitor source) e macOS (BlackHole). D1 revisado para híbrido — sounddevice 0.5.5 não expõe flag de WASAPI loopback, soundcard cobre o caso Windows. `VoiceCapture` ganhou backend dual.
- 2026-05-03 — Fase 1 fechada. `settings.py` é a fonte única; `config.py` só guarda defaults. Wizard agora roda standalone via `main.py` antes do app principal — fim do destroy/recreate.
- 2026-05-03 — Fase 0 fechada. Todas as decisões D1–D8 registradas em `definicoes.md`. Pronto para iniciar Fase 1.
- 2026-05-03 — Plano e definições criados. Aguardando decisões da Fase 0.
