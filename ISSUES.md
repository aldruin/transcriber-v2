# 📋 Issues - Meeting Transcriber v2

Documentação centralizada de problemas, bugs e melhorias identificadas no projeto.

---

## 🔴 Issues em Aberto

### Issue #1: Configuração Inicial Confusa para Novos Usuários (Windows)
**Status**: � Em Progresso (~85%)  
**Prioridade**: 🔥 Alta  
**Tipo**: UX/Documentação  

**Descrição:**
Usuários que baixam o executável no Windows não sabem que precisam:
- Ativar a mixagem estéreo (Stereo Mix) no dispositivo de áudio
- Identificar qual dispositivo configuram como microfone
- Qual é o dispositivo de "loopback" de áudio

**Impacto:**
- Usuários recebem erros ou a aplicação não captura áudio corretamente
- Aumenta a curva de aprendizado e suporte

**Solução Implementada:**
- [x] Criar guia de configuração (`SETUP-GUIDE.md`)
- [x] Melhorar `diagnostico.py` com dicas contextuais
- [x] Auto-detecção de dispositivos (`audio_setup.py`)
- [x] Wizard interativo de primeira execução (`setup_wizard.py`)
- [x] Validação Stereo Mix no Windows
- [x] Testes de áudio automáticos
- [x] Integração com app.py

**Tarefas Restantes:**
- [ ] Testes em ambiente Windows real
- [ ] Coletar feedback de usuários

---

### Issue #2: Suporte Linux/macOS (Tkinter Limitação)
**Status**: 🔴 Aberto  
**Prioridade**: 🟡 Média  
**Tipo**: Feature/Compatibilidade  

**Descrição:**
O aplicativo usa `customtkinter` (baseado em tkinter) que:
- Funciona bem no Windows
- Tem limitações no Linux/macOS (renderização, temas)
- A compilação com PyInstaller gera executáveis apenas para Windows

Usuários em Linux/macOS não têm uma forma fácil de usar a aplicação sem instalar dependências Python manualmente.

**Impacto:**
- Exclui usuários de Linux/macOS da versão "pronta para usar"
- Requer habilidades técnicas para rodar localmente

**Solução Proposta:**
- [ ] Investigar alternativas de GUI multiplataforma (PyQt, PySide, Kivy)
- [ ] Criar builds para Linux/macOS usando PyInstaller
- [ ] Documentar instrução de instalação para desenvolvedores em Linux/macOS
- [ ] Considerar versão web (Flask/FastAPI + frontend JavaScript)

**Tarefas Relacionadas:**
- [ ] Research de alternativas GUI
- [ ] Testes em Linux/macOS
- [ ] Atualizar build pipeline

---

## ✅ Issues Resolvidas

*(Adicione issues resolvidas aqui para histórico)*

---

## 📝 Template para Novas Issues

Ao reportar uma nova issue, use o template abaixo:

```markdown
### Issue #X: [Título Curto]
**Status**: 🔴 Aberto / 🟡 Em Progresso / ✅ Resolvido  
**Prioridade**: 🔥 Alta / 🟡 Média / 🟢 Baixa  
**Tipo**: Bug / Feature / UX / Documentação / Performance  

**Descrição:**
[Descrever o problema detalhadamente]

**Impacto:**
[Como isso afeta os usuários?]

**Solução Proposta:**
- [ ] Tarefa 1
- [ ] Tarefa 2

**Tarefas Relacionadas:**
- [ ] Link/referência
```

---

## 🔗 Links Úteis

- **README.md**: Informações gerais do projeto
- **PROGRESS.md**: Rastreamento de progresso de desenvolvimento
- **SETUP-GUIDE.md**: Guia de configuração para usuários finais
- **GitHub Issues**: [Link para issues no GitHub]

