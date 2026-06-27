"""
transcription/curation.py — Monta o prompt de curadoria para o usuário COPIAR e
colar no LLM dele (Claude/GPT/etc). Não chama nenhuma API: só gera texto, então
funciona com qualquer provedor e sem API key. O prompt é escrito em linguagem
direta e afirmativa (sem markdown), pedindo intervenção mínima: remover as
marcações/marca d'água e corrigir só as alucinações óbvias, preservando o resto.
"""

from __future__ import annotations

# Placeholder inserido quando o usuário não fornece contexto — ele preenche
# depois, no chat do LLM. Traz um exemplo concreto de como descrever.
CONTEXT_PLACEHOLDER = (
    "[Descreva aqui o contexto. Por exemplo: \"É uma reunião de negócios entre mim "
    "e um stakeholder sobre a nova demanda, o projeto novo. Eu me "
    "chamo Ana; o stakeholder é o Bruno.\"]"
)

_PROMPT_TEMPLATE = """\
Gerei esta transcrição com o modelo Whisper (reconhecimento de voz). Seu trabalho é \
curá-la pra mim: tire as marcações que servem de marca d'água — os horários, os \
rótulos "🔊 Sistema" e "🎤 Microfone" e os nomes de canal — e corrija só as \
alucinações óbvias do Whisper, aquelas palavras que claramente não fazem sentido no \
contexto. Fora isso, não mexa: não reescreva o jeito de falar, não melhore o que já \
está certo e não acrescente nada que não tenha sido dito.

Contexto da conversa:
{context}

Uma observação: a marcação de quem fala é automática e às vezes erra — a mesma pessoa \
pode acabar marcada como "Falante_1", "Falante_2" e por aí vai. Se pelo conteúdo ficar \
claro que são a mesma pessoa, junte tudo sob um nome só. E se você ficar em dúvida sobre \
algum trecho, marque com [?] em vez de adivinhar.

Me entregue primeiro a transcrição curada: a conversa limpa, na ordem em que aconteceu, \
sem as marcações. Logo depois, faça um resumo organizado por tópicos com os pontos \
principais da conversa.

Aqui está a transcrição:

{transcript}
"""


def build_curation_prompt(transcript: str, context: str | None = None) -> str:
    """
    Monta o prompt de curadoria pronto para colar no LLM.

    Args:
        transcript: texto bruto da transcrição (linhas com horário/canal/falante).
        context:    contexto da conversa. Se vazio/None, insere um placeholder
                    (com exemplo) para o usuário preencher no próprio chat do LLM.

    Returns:
        Prompt completo, em linguagem afirmativa.
    """
    ctx = context.strip() if context and context.strip() else CONTEXT_PLACEHOLDER
    return _PROMPT_TEMPLATE.format(context=ctx, transcript=transcript.strip())
