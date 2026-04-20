# Contribuindo para Meeting Transcriber v2

Obrigado por se interessar em contribuir! 🎉

## Como contribuir

### Reportar Bugs
1. Abra uma [Issue](https://github.com/aldruin/transcriber-v2/issues)
2. Descreva o problema e os passos para reproduzir
3. Inclua a saída esperada vs. a saída real
4. Mencione sua configuração (SO, Python version, dispositivos de áudio)

### Sugerir Melhorias
- Abra uma Issue com tag `enhancement`
- Descreva a funcionalidade e por que seria útil para a comunidade
- Exemplos de uso são bem-vindos

### Submeter Código

1. Faça Fork do projeto
2. Crie uma branch para sua feature:
   ```bash
   git checkout -b feature/nome-da-feature
   ```
3. Faça seus commits com mensagens claras:
   ```bash
   git commit -m 'Adiciona descrição clara da mudança'
   ```
4. Push para a branch:
   ```bash
   git push origin feature/nome-da-feature
   ```
5. Abra um [Pull Request](https://github.com/aldruin/transcriber-v2/pulls)

## Configuração para Desenvolvimento

```bash
# Clonar o repositório
git clone https://github.com/aldruin/transcriber-v2.git
cd transcriber-v2

# Criar ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Rodar o aplicativo
python main.py
```

## Estrutura do Projeto

```
transcriber-v2/
├── audio/           # Captura e processamento de áudio
├── transcription/   # Módulo de transcrição (Whisper)
├── diarization/     # Identificação e perfil de falantes
├── ui/              # Interface gráfica (CustomTkinter)
├── docs/            # Documentação
├── config.py        # Configurações centralizadas
├── main.py          # Entry point
└── diagnostico.py   # Script de diagnóstico de dispositivos
```

## Diretrizes de Código

- Mantenha o código limpo e legível
- Adicione docstrings em funções/classes principais
- Teste suas mudanças antes de submeter
- Siga o estilo de código existente

## Perguntas?

Abra uma discussão em [Discussions](https://github.com/aldruin/transcriber-v2/discussions) ou uma Issue com tag `question`.

---

Agradecemos sua contribuição! 🚀
