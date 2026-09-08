"""Suggests which of an organization's risk areas apply to a work order,
from a technician's free-text description of the activity — a starting
point to check against, not an auto-decision: the "Área de risco" wizard
step only pre-checks the suggested boxes, the technician still reviews and
confirms before advancing.
"""

import json

from django.conf import settings
from openai import OpenAI, OpenAIError

PROMPT_TEMPLATE = (
    "Você é um técnico de segurança do trabalho brasileiro. Um técnico descreveu a atividade que vai "
    "realizar. Compare a descrição com a lista de áreas de risco/normas regulamentadoras (NR) cadastradas "
    "para esta unidade e diga quais se aplicam.\n\n"
    'Descrição da atividade: "{activity_description}"\n\n'
    "Áreas de risco disponíveis (id: nome — norma — descrição):\n{areas_list}\n\n"
    "Responda estritamente em JSON, sem nenhum texto fora do JSON, no formato:\n"
    '{{"suggested_ids": [<id>, ...], "reasoning": "<uma frase curta em português explicando a escolha>"}}\n'
    "Só inclua um id se a descrição indicar claramente aquele risco. Se nenhuma área se aplicar claramente, "
    'responda {{"suggested_ids": [], "reasoning": "..."}}.'
)


class RiskSuggestionError(Exception):
    """Raised when the AI call fails or returns something we can't use."""


def suggest_risk_areas(activity_description, risk_areas):
    """`risk_areas` is an iterable of core.models.RiskArea for the permit's
    organization. Returns {"suggested_ids": [int, ...], "reasoning": str}.
    """
    if not settings.OPENAI_API_KEY:
        raise RiskSuggestionError("OPENAI_API_KEY não está configurada.")

    risk_areas = list(risk_areas)
    areas_list = "\n".join(
        f"- {area.id}: {area.name} — {area.regulatory_code} — {area.description}" for area in risk_areas
    )
    prompt = PROMPT_TEMPLATE.format(activity_description=activity_description, areas_list=areas_list)

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=400,
        )
    except OpenAIError as exc:
        raise RiskSuggestionError(f"Falha ao chamar a API de sugestão: {exc}") from exc

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        valid_ids = {area.id for area in risk_areas}
        suggested_ids = [int(item) for item in data.get("suggested_ids", []) if int(item) in valid_ids]
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise RiskSuggestionError(f"Resposta da API em formato inesperado: {exc}") from exc

    return {"suggested_ids": suggested_ids, "reasoning": data.get("reasoning", "")}
