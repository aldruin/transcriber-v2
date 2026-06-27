# 🎧 Guia de Configuração Inicial — Meeting Transcriber v2

**Para quem baixou o executável ou roda pelo código.**

> [!IMPORTANT]
> **Você NÃO precisa mais ativar "Stereo Mix" nem configurar dispositivo de áudio do sistema.**
> O app captura automaticamente o que sai pelos seus fones/alto-falantes
> (loopback). A única coisa que você escolhe é o **microfone**.

---

## ⚡ TL;DR

1. Abra o app. Na primeira vez, um assistente rápido aparece.
2. Confira o **áudio do sistema** (detectado automaticamente) e escolha o seu **microfone**.
3. Diga como quer ser identificado (ex.: "Eu").
4. Clique em **▶ Iniciar**. Pronto.

---

## 🔊 Áudio do Sistema — automático

O app usa **loopback** do seu dispositivo de saída padrão para capturar tudo o
que você ouve (Discord, WhatsApp, YouTube, Meet, etc.) — sem Stereo Mix, sem
cabos virtuais, sem driver extra no Windows.

- **Windows** → WASAPI loopback (automático).
- **Linux** → *monitor source* do PulseAudio/PipeWire (automático).
- **macOS** → requer um dispositivo virtual, ex.: [BlackHole](https://github.com/ExistentialAudio/BlackHole)
  (`brew install blackhole-2ch`) e um *Aggregate Device*. É a única plataforma
  que ainda precisa de um passo manual, por limitação do próprio macOS.

> 💡 **Use fones de ouvido sempre que possível.** Sem fones, o som sai pelo
> alto-falante e volta pelo microfone, gerando eco/duplicação na transcrição.
> O app já descarta a maior parte automaticamente (EchoGuard), mas com fones o
> resultado fica nitidamente melhor.

---

## 🎤 Microfone — a única escolha

No assistente (ou em **⚙️ Configurações**), selecione o seu microfone na lista.
Dica: prefira o dispositivo com mais canais/maior qualidade (o app marca com ⭐).

Se você tiver vários microfones e não souber qual é, use o botão **▶ Testar
Nível** nas Configurações: fale e veja a barra reagir.

---

## ▶️ Durante a Reunião

- **▶ Iniciar / ⏹ Parar** — começa/encerra a captura. A transcrição é salva em
  `transcricoes/`.
- **⏸ Pausar** — congela a transcrição (intervalo, conversa privada).
- **🎤 Mic ON/OFF** — silencia **só a sua voz** na transcrição; você continua
  ouvindo e transcrevendo os outros.
- **Renomear falantes** — clique sobre `[Falante_1]` e digite o nome real. O app
  aprende aquela voz e passa a reconhecê-la nas próximas reuniões.

---

## 🆘 Solução de Problemas

### "O medidor de Áudio do Sistema não reage"
- [ ] Toque algo no PC (YouTube, Spotify) enquanto observa.
- [ ] Confirme que há uma **saída de áudio ativa** (fones/alto-falantes conectados).
- [ ] Confira que o Windows está tocando pela saída padrão que você espera
      (ícone de volume → selecionar dispositivo de saída).

### "O medidor de Microfone não reage"
- [ ] Em **⚙️ Configurações**, confirme que selecionou o microfone certo.
- [ ] Teste o microfone no Windows (Som → Entrada → "Testar Microfone").
- [ ] Veja se o microfone não está mudo no `🎤 Mic ON/OFF`.

### "Aparece eco ou a minha fala duplicada"
- [ ] Use **fones de ouvido**. É a causa nº 1 — sem fones, o áudio do alto-falante
      volta pelo microfone.

### "A transcrição traz palavras erradas ou ruído"
- [ ] Em CPU, modelos maiores transcrevem melhor. Em **⚙️ Configurações →
      Modelo**, experimente `medium` (recomendado) ou `large-v3` (se tiver GPU).
- [ ] Fala muito baixa ou ambiente barulhento degrada qualquer transcritor.

---

## 💬 Precisa de Ajuda?

- **GitHub Issues**: https://github.com/aldruin/transcriber-v2/issues
- **Discussões**: https://github.com/aldruin/transcriber-v2/discussions
