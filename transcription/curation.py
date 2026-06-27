"""
transcription/curation.py — Monta o prompt de curadoria para o usuário COPIAR e
colar no LLM dele (Claude/GPT/etc). Não chama nenhuma API: só gera texto, então
funciona com qualquer provedor e sem API key. As diretrizes (intervenção mínima,
reconciliação de falantes, marcações só na entrada) estão no próprio template.
"""

from __future__ import annotations

# Placeholder inserido quando o usuário não fornece contexto — ele preenche
# depois, dentro do chat do LLM.
CONTEXT_PLACEHOLDER = (
    "[Preencha: quem participa da conversa e como costumam ser chamados, o "
    "assunto/objetivo, e nomes próprios, siglas ou jargões que o reconhecimento "
    "de voz tende a errar. Quanto mais contexto, melhor a correção.]"
)

_PROMPT_TEMPLATE = """\
# PAPEL
Você é meu parceiro na revisão de uma transcrição de conversa falada. Trabalhamos
juntos: o objetivo é uma transcrição fiel e legível, não uma reescrita. Prefira
intervir de menos a intervir de mais.

# CONTEXTO DA CONVERSA
{context}

# COMO ESTE MATERIAL FOI GERADO (para você calibrar a confiança)
- É saída de reconhecimento automático de voz (Whisper), então CONTÉM erros e
  alucinações — palavras trocadas, repetições fantasma e ruído virado texto.
- Cada linha segue o formato:
  `[horário] <canal> [Falante]: texto`
  onde o canal "🔊 Sistema" é o que EU escutei das outras pessoas e
  "🎤 Microfone" sou EU falando.
- A identificação de falantes é automática e IMPERFEITA: a MESMA pessoa pode
  aparecer rotulada como "Falante_1", "Falante_2", "Falante_3"...

# SUA TAREFA
1. Corrija APENAS as alucinações e erros ÓBVIOS do reconhecimento de voz (algo
   que claramente não faz sentido no contexto). NÃO altere o estilo de fala, NÃO
   "melhore" o que já está certo e NUNCA invente conteúdo que não esteja ali.
2. Reconcilie os falantes: se pelo conteúdo e pelo contexto dois ou mais rótulos
   são claramente a mesma pessoa, unifique-os sob um único nome. Se não tiver
   certeza, mantenha separados e aponte isso nas observações.
3. Una as falas fragmentadas (a captura quebra frases em pedaços) em turnos
   naturais de conversa, preservando o sentido original.
4. Use os horários e rótulos de canal apenas para entender a sequência; REMOVA
   essas marcações técnicas da versão final.

# QUANDO ESTIVER EM DÚVIDA
- Não adivinhe. Preserve o trecho original e marque com "[?]".
- É melhor me sinalizar uma incerteza do que entregar uma correção errada.

# FORMATO DA SAÍDA
1. **Conversa revisada** — diálogo limpo em ordem cronológica, no formato
   `Nome: fala` (sem horários nem rótulos de canal).
2. **Resumo** — 3 a 6 tópicos com os pontos principais.
3. **Observações** (apenas se houver) — trechos incertos, correções relevantes
   que você fez e falantes que você suspeita serem a mesma pessoa mas não teve
   certeza.

# TRANSCRIÇÃO BRUTA
<<<TRANSCRICAO
{transcript}
TRANSCRICAO>>>
"""


def build_curation_prompt(transcript: str, context: str | None = None) -> str:
    """
    Monta o prompt de curadoria pronto para colar no LLM.

    Args:
        transcript: texto bruto da transcrição (linhas com horário/canal/falante).
        context:    contexto da conversa. Se vazio/None, insere um placeholder
                    para o usuário preencher no próprio chat do LLM.

    Returns:
        Prompt completo (papel + contexto + material + tarefa + saída).
    """
    ctx = context.strip() if context and context.strip() else CONTEXT_PLACEHOLDER
    return _PROMPT_TEMPLATE.format(context=ctx, transcript=transcript.strip())
