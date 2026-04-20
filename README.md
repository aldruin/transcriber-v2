# 🎙️ Meeting Transcriber v2

**Transcrição Inteligente e Diarização de Voz em Tempo Real.**

O **Meeting Transcriber v2** é uma solução avançada de código aberto projetada para capturar, transcrever e identificar falantes em reuniões de forma síncrona. Utilizando modelos de estado da arte em Deep Learning, o sistema separa o áudio do sistema (outros participantes) e do microfone (você), atribuindo identidades persistentes a cada voz.

---

## 📥 Download (Versão Pronta para Uso)

Não é desenvolvedor? Você pode baixar o executável pronto para Windows e começar a usar agora mesmo, sem precisar instalar o Python.

> [!TIP]
> **[Baixar Meeting Transcriber v2 para Windows](https://github.com/aldruin/transcriber-v2/releases)**  
> *(Nota: Ao rodar pela primeira vez, o Windows pode exibir um alerta de segurança por ser um executável não assinado. Clique em "Mais informações" > "Executar assim mesmo")*

---

## ✨ Destaques e Diferenciais

- **Transcrição de Alta Performance**: Alimentado pelo `faster-whisper`, garantindo precisão superior e velocidade otimizada.
- **Diarização Persistente (Assinatura de Voz)**: Identifica quem está falando. Uma vez que você nomeia um falante, o sistema o reconhece automaticamente em reuniões futuras.
- **Processamento Assíncrono**: Arquitetura baseada em filas que elimina latência na interface e garante que a captura de áudio nunca seja interrompida.
- **Interface Sofisticada**: UI moderna inspirada na paleta *Catppuccin*, com medidores de nível e visualização de ondas em tempo real.

---

## 🛠️ Guia de Uso

### 1. Configuração Inicial (Crucial)
Antes de iniciar a transcrição, você precisa identificar os IDs dos seus dispositivos de áudio.
1. Execute o script de diagnóstico: `python diagnostico.py` (ou abra as configurações na UI).
2. Identifique o ID do seu **Microfone** e o ID do seu **Audio Loopback** (geralmente chamado de "Stereo Mix" ou similar).
3. Configure esses IDs na janela de **Configurações** do aplicativo.

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
1. Clone o repositório: `git clone https://github.com/aldruin/transcriber-v2.git`
2. Instale as dependências: `pip install -r requirements.txt`
3. Execute: `python main.py`

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
