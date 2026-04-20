# Análise do Projeto Transcriber-V2

Este documento registra a evolução da arquitetura do projeto e o histórico de melhorias implementadas.

## 1. Status Atual do Projeto (Abril 2026)

O **transcriber-v2** é uma aplicação robusta de transcrição multicanal com interface moderna e inteligência de diarização dinâmica.

### Componentes Implementados

1.  **Captura (`audio/capture.py`):** Captura multicanal (Sistema/Microfone) com VAD baseado em RMS e feedback visual de waveform.
2.  **Diarização Inteligente (`diarization/`):** 
    *   Uso de **Running Centroid** (média móvel) para estabilizar perfis de voz durante a sessão.
    *   Identificação de falantes conhecidos (persistentes) e desconhecidos (sessão).
3.  **Transcrição (`transcription/transcriber.py`):** Motor baseado em `faster-whisper` com suporte a metadados de canal e falante.
4.  **Interface Moderna (`ui/`):** 
    *   Migração total para **CustomTkinter** (Dark Mode).
    *   **Diarização Dinâmica:** Renomeação de falantes clicando diretamente no nome na tela de log.
    *   Visualizador de ondas de áudio em tempo real.
5.  **Automação de Build (`build_exe.py`):** Script para geração de executável portátil (.exe) com tratamento de dependências críticas.

---

## 2. Demandas em Aberto (Roadmap Open Source)

Estas funcionalidades são prioridades para tornar o projeto uma ferramenta global e profissional.

### I. Internacionalização Dinâmica (i18n)
*   **Interface:** Criar seletor na UI para mudar o idioma dos botões e menus (Ex: PT/EN).
*   **Transcrição (Whisper):** Permitir que o usuário escolha o idioma de entrada (Ex: 'pt', 'en', 'es' ou 'auto') diretamente nas configurações.

### II. Seleção de Performance (Modelos e Hardware)
*   **Modelos:** Permitir escolha entre `tiny`, `small`, `medium` e `large` via UI.
*   **Aceleração:** Seletor entre CPU e GPU (CUDA) para usuários com hardware compatível.

### III. Pós-Processamento com LLMs (Atas e Resumos)
*   **Integração:** Adicionar suporte a APIs (OpenAI, Anthropic) ou local (Ollama) para gerar resumos estruturados das reuniões.
*   **Interface:** Nova aba de "Relatórios" ou botão de "Gerar Resumo".

### IV. Testes Automatizados e CI/CD
*   **Qualidade:** Implementar suíte de testes unitários com `pytest`.
*   **GitHub Actions:** Configurar build automático do executável a cada nova tag/release.

---

## 3. Plano de Execução: Demandas I & II (Próxima Etapa)

O objetivo é centralizar o controle técnico e linguístico do aplicativo na janela de configurações.

### A. Back-end (Motor de Transcrição)
1.  Alterar `Transcriber.__init__` para aceitar `model_size`, `device` e `language` dinâmicos.
2.  Implementar método `reload_model()` para recarregar o Whisper sem reiniciar o app.
3.  Atualizar o loop de transcrição para usar o idioma selecionado.

### B. Front-end (UI & i18n)
1.  **Sistema de Tradução:** Criar `ui/i18n.py` que carrega dicionários de idiomas.
2.  **Configurações:** Expandir `SettingsWindow` com:
    *   Dropdown para Idioma da UI (Português/Inglês).
    *   Dropdown para Idioma da Transcrição (Lista de códigos ISO do Whisper).
    *   Seletor de Modelo (Tiny a Large).
    *   Seletor de Dispositivo (CPU/CUDA/Auto).
3.  **Persistência:** Atualizar `settings.json` para salvar essas novas preferências.

### C. Validação
1.  Testar se a mudança de idioma da interface ocorre instantaneamente.
2.  Verificar se a troca de CPU para GPU (se disponível) reduz a latência de transcrição.
