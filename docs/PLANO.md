# Plano de Evolução — Multiplataforma + Eficiência

Documento mestre que guia a execução. Toda mudança neste projeto deve respeitar
o que está aqui e atualizar `progress.md` ao concluir cada item.

---

## Objetivo

Tornar o Meeting Transcriber utilizável em **Windows, macOS e Linux** sem
que o usuário precise configurar Stereo Mix manualmente, e melhorar a
eficiência do pipeline de transcrição/diarização.

A promessa final: o colega baixa o binário do SO dele, abre, e em ≤2 cliques
está transcrevendo uma reunião.

---

## Frentes (3 grandes + melhorias menores)

### Frente A — Captura de áudio multiplataforma

**Problema:** hoje depende de Stereo Mix (Windows), loopback PulseAudio (Linux)
ou BlackHole (macOS). Quebra a promessa "baixe e use".

**Decisão a tomar (ver `definicoes.md`):**
- Trocar `sounddevice` por `soundcard`, ou criar camada de abstração que use o
  melhor backend por SO.
- Windows: WASAPI loopback (sem Stereo Mix).
- Linux: pegar `.monitor` automático do sink padrão.
- macOS: continua precisando BlackHole — mas detectamos e instruímos.

**Entregáveis:**
- [ ] `audio/loopback.py`: nova camada que retorna um stream de "saída do sistema"
      independente do SO.
- [ ] `audio/capture.py` adaptado para receber o backend pronto, sem se preocupar
      com qual lib está por baixo.
- [ ] Auto-detect substitui o passo "configurar Stereo Mix" do wizard quando
      possível (Windows/Linux).
- [ ] Wizard só pede instalação de driver virtual quando realmente necessário
      (macOS, ou Windows sem WASAPI).

**Critério de pronto:** rodar `python main.py` em Win/Linux sem nenhuma
configuração prévia de áudio do sistema, e a captura funcionar.

---

### Frente B — Build multiplataforma (CI)

**Problema:** PyInstaller não cross-compila. `app.spec` está amarrado em paths
Windows. Releases hoje só têm `.exe`.

**Entregáveis:**
- [ ] `.github/workflows/release.yml` com matriz `windows-latest /
      macos-latest / ubuntu-latest`.
- [ ] Cada job builda o binário do próprio SO via PyInstaller.
- [ ] Artefatos publicados no GitHub Releases ao push de tag `v*`.
- [ ] `app.spec` revisado para não depender de `os.getcwd()` em build server.

**Critério de pronto:** push de uma tag de teste gera 3 binários
(`MeetingTranscriber-windows.exe`, `MeetingTranscriber-macos.dmg` ou `.app`,
`MeetingTranscriber-linux.AppImage` ou tar) automaticamente.

---

### Frente C — Eficiência do Whisper

**Problema:** default é `medium` + `int8` + `cpu` + `beam=10`. Modelo ~1.5GB,
transcrição lenta em máquinas modestas.

**Entregáveis:**
- [ ] Mudar default para `small` (ou `base`) com `beam_size=5`.
- [ ] Detecção automática de aceleração:
      - CUDA disponível → `device=cuda`, `compute_type=float16`
      - macOS Apple Silicon → tentar `device=auto` (faster-whisper já lida)
      - Fallback CPU → `int8`
- [ ] Configuração avançada na UI permite subir/descer modelo sem editar
      `config.py`.
- [ ] Aviso na 1ª execução: "modelo será baixado (~250 MB)" antes de iniciar.

**Critério de pronto:** em CPU comum (i5 sem GPU), tempo de transcrição de um
chunk de 5s deve ficar ≤2× o tempo real.

---

## Melhorias menores (incorporadas ao plano)

### M1 — VAD universal
- Trocar VAD por RMS por **silero-vad** (modelo ONNX leve).
- Elimina o passo "calibrar threshold" do wizard.
- Remove o `VAD_THRESHOLD_*` da config.

### M2 — Diarização não-bloqueante
- Hoje `diarization.identify()` é chamado dentro do worker do Transcriber e
  bloqueia transcrições.
- Mover para fila própria: o áudio entra simultaneamente em duas filas
  (transcrição + diarização) e os resultados são casados por timestamp.

### M3 — Microfone = "Eu" automático
- Áudio capturado pelo canal microfone é, por definição, o usuário.
- Auto-promover esse falante a perfil "Eu" (ou nome configurado pelo usuário no
  setup) sem precisar do clique manual.

### M4 — Configuração unificada
- Hoje devices/thresholds estão em `config.py` E `settings.json`.
- `config.py` vira só defaults imutáveis; `settings.json` é a única fonte de
  verdade em runtime.

### M5 — Reinício do app no wizard
- `self.destroy() + TranscriberApp()` no `_check_wizard_complete` é frágil.
- Trocar por: o wizard escreve settings e fecha; o `__init__` continua o fluxo
  normal sem precisar destruir o root.

### M6 — VAD redundante
- Hoje rodamos VAD próprio (no `capture.py`) E o `vad_filter=True` do Whisper.
- Manter apenas o silero-vad (M1) e desligar `vad_filter` do Whisper, ou o
  contrário. Definir em `definicoes.md`.

---

## Ordem de execução proposta

```
Fase 0  → Definições (decisões em definicoes.md, sem código)
Fase 1  → M4 (config unificada) + M5 (fix reinício)        [base limpa]
Fase 2  → Frente A (loopback multiplataforma)              [maior impacto]
Fase 3  → M1 + M6 (silero-vad, remove VAD redundante)
Fase 4  → Frente C (Whisper defaults + aceleração)
Fase 5  → M2 (diarização async) + M3 (mic = Eu)
Fase 6  → Frente B (CI multiplataforma)                    [por último]
```

CI por último porque só faz sentido depois que o código roda nos 3 SOs.

---

## Regras de execução

1. **Cada item vira commit isolado** ao final, com mensagem clara. Nunca
   commitar até o usuário pedir.
2. **`progress.md` é atualizado a cada item concluído** — checkbox marcada,
   data, nota curta.
3. **Decisões técnicas vão em `definicoes.md`** antes de virar código. Se o
   código contradiz o doc, atualizar o doc.
4. **Não tocar em código fora do escopo da fase atual** — refactor de
   oportunidade fica de fora.
5. **Testar manualmente** ao fim de cada fase no SO disponível (Windows). Os
   outros SOs validam via CI quando a Frente B estiver pronta.

---

## Arquivos centrais (referência rápida)

- `audio/capture.py`           — captura por canal, VAD, callback
- `audio/resampler.py`         — resample + normalize
- `transcription/transcriber.py` — fila + faster-whisper
- `diarization/__init__.py`    — engine de diarização
- `diarization/embedder.py`    — resemblyzer GE2E
- `diarization/profiles.py`    — perfis persistentes
- `ui/app.py`                  — orquestrador (TranscriberApp)
- `ui/setup_wizard.py`         — wizard 1ª execução
- `ui/os_specific_setup.py`    — instruções por SO
- `config.py`                  — defaults globais
- `app.spec` + `build_exe.py`  — empacotamento PyInstaller
