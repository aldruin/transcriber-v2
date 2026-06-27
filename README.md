# 🎙️ Meeting Transcriber v2

**Transcrição Inteligente e Diarização de Voz em Tempo Real.**

O **Meeting Transcriber v2** é uma solução avançada de código aberto projetada para capturar, transcrever e identificar falantes em reuniões de forma síncrona. Utilizando modelos de estado da arte em Deep Learning, o sistema separa o áudio do sistema (outros participantes) e do microfone (você), atribuindo identidades persistentes a cada voz.

---

## 📥 Download (Versão Pronta para Uso)

Baixe o binário do seu sistema operacional na [página de Releases](https://github.com/aldruin/transcriber-v2/releases):

- **Windows** — `MeetingTranscriberV2-windows.exe`
- **macOS**   — `MeetingTranscriberV2-macos.dmg` *(requer [BlackHole](https://github.com/ExistentialAudio/BlackHole) para áudio do sistema)*
- **Linux**   — `MeetingTranscriberV2-linux.AppImage`

> [!NOTE]
> No Windows, o app captura o áudio do sistema **automaticamente via WASAPI loopback** — não é mais preciso ativar Stereo Mix. Binários não são assinados; libere no Gatekeeper (macOS) ou no SmartScreen (Windows) na 1ª execução.

---

## ✨ Destaques e Diferenciais

- **Transcrição de Alta Performance**: Alimentado pelo `faster-whisper` (default `small`, com seletor para `tiny`/`base`/`medium`/`large-v3` na UI). Detecta CUDA automaticamente.
- **Diarização Persistente (Assinatura de Voz)**: Identifica quem está falando. O áudio do seu microfone é atribuído automaticamente ao seu perfil ("Eu" por default).
- **Loopback Multiplataforma**: Captura áudio do sistema sem Stereo Mix no Windows (WASAPI), via monitor source no Linux e BlackHole no macOS.
- **VAD com silero-vad**: detecção de fala neural sem calibração de threshold por hardware.
- **Processamento Assíncrono**: filas com transcrição e diarização rodando em paralelo.

---

## 🛠️ Guia de Uso

### 📖 Guia de Configuração Inicial
**Primeira vez?** Veja o [Guia Completo de Configuração](SETUP-GUIDE.md):
- ✅ Áudio do sistema é **automático** (sem Stereo Mix)
- ✅ Como escolher o microfone certo
- ✅ Solução de problemas (troubleshooting)

### 1. Primeira Execução
Na primeira vez, um assistente rápido aparece. O **áudio do sistema é detectado
automaticamente** (loopback do que você escuta) — você só escolhe o seu
**microfone** e como quer ser identificado. Não é preciso ativar Stereo Mix nem
rodar scripts. No macOS, instale o [BlackHole](https://github.com/ExistentialAudio/BlackHole)
(único SO que ainda exige um passo manual).

### 2. Durante a Reunião
- Clique em **▶ Iniciar** para começar a captura.
- Use o botão **⏸ Pausar** se houver um intervalo ou conversa privada que não deve ser transcrita.
- O botão **🎤 Mic ON/OFF** permite que você silencie apenas a sua voz na transcrição enquanto continua ouvindo os outros.

### 3. Ensinando o Sistema (Diarização)
Esta é a parte mais poderosa:
- Quando o sistema identificar uma nova voz, ele exibirá `[Falante_1]`.
- **Clique sobre o nome `[Falante_1]`** na área de texto.
- Digite o nome real da pessoa (ex: "João").
- **Pronto!** O sistema agora "conhece" a voz do João. Todas as falas dele nesta reunião e em **todas as próximas** serão identificadas automaticamente como "João".

---

## 🏗️ Para Desenvolvedores

### Instalação
1. Clone o repositório: `git clone https://github.com/seu-usuario/transcriber-v2.git`
2. Instale as dependências: `pip install -r requirements.txt`
3. Execute: `python main.py`

> 🩺 Problemas? Rode `python diagnostico.py` e cole o relatório completo ao
> abrir uma issue — ele mostra SO, versões, GPU e a detecção de áudio do sistema.

### ⚡ Aceleração por GPU (NVIDIA / CUDA)
O app **detecta a GPU automaticamente** e usa CUDA quando disponível — sem
configuração no código. O detalhe: a versão padrão do `torch` no PyPI é
**CPU-only**, então mesmo com uma placa NVIDIA o Whisper roda na CPU (lento,
sobretudo nos modelos `medium`/`large-v3`). Para habilitar a GPU:

```bash
pip uninstall -y torch torchaudio
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
```

Confirme com `python diagnostico.py` (seção GPU / CUDA → deve dizer
`CUDA disponivel: True`). O driver NVIDIA já costuma estar instalado; **não** é
preciso instalar o CUDA Toolkit completo.

### Como Gerar o Executável (.EXE)
Se você fez alterações no código e deseja gerar um novo executável para distribuir:
1. Certifique-se de ter o `PyInstaller` instalado: `pip install pyinstaller`
2. Execute o script de build customizado:
   ```bash
   python build_exe.py
   ```
3. O executável final será gerado na pasta `dist/MeetingTranscriberV2.exe`.

---

## 🗺️ Roadmap de Evolução

- [x] Processamento de Diarização Assíncrono.
- [x] Persistência de Perfis de Voz.
- [x] Botão de Pausa/Retomar.
- [ ] Suporte a exportação em formato `.docx` e `.srt`.
- [ ] Integração com LLMs Locais (Llama 3) para resumos automáticos.

---

## 📄 Licença
Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

---
<p align="center">
  Desenvolvido com ❤️ para a comunidade de produtividade.
</p>
