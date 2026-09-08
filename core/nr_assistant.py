"""A chat assistant that answers a field technician's questions about NRs
(Brazilian workplace-safety regulations), grounded first in their own
organization's registered content — the same risk areas, checklists, PPE
lists and document requirements the wizard itself uses — and beyond that,
in the model's general knowledge of the official NR texts, so a question
like "o que a NR-35 exige sobre ancoragem" doesn't get refused just
because it isn't itself a row in this company's checklist.

The two sources are kept distinct in the answer: what THIS company
requires (from its own registered data — authoritative, since it's what
the PET wizard itself enforces) versus general NR knowledge (useful
context, but not a substitute for what's actually configured here). The
prompt tells the model to say so explicitly when it's answering from
general knowledge rather than the company's own data, and to say plainly
when it doesn't know rather than guessing.

Imports permits/workers models locally (not at module level) to avoid a
circular import with core.models, matching core.onboarding's pattern.
"""

import json

from django.conf import settings
from openai import OpenAI, OpenAIError

SYSTEM_PROMPT = (
    "Você é um assistente de segurança do trabalho para técnicos de campo brasileiros, integrado ao "
    "sistema PET Digital, com conhecimento das Normas Regulamentadoras (NRs) brasileiras. Você tem duas "
    "fontes de informação:\n\n"
    "1) O contexto de dados abaixo — as áreas de risco, checklists, EPIs obrigatórios e documentos "
    "exigidos que ESTA empresa específica cadastrou no sistema. Essa é a fonte AUTORITATIVA para "
    "perguntas sobre o que esta empresa exige na prática (é o mesmo dado que o assistente de emissão de "
    "PET usa para bloquear ou liberar uma permissão) — sempre prefira e cite esses dados quando a "
    "pergunta for sobre isso.\n"
    "2) Seu conhecimento geral sobre o conteúdo oficial das NRs (definições, exigências gerais da norma, "
    "boas práticas). Use isso para responder perguntas sobre a norma em si que vão além do que está "
    "cadastrado no sistema desta empresa.\n\n"
    "Ao responder, deixe claro quando a resposta vem do que a empresa cadastrou versus do conhecimento "
    "geral da norma (ex.: 'segundo o que sua empresa cadastrou...' vs 'de forma geral, a NR-35 exige...'). "
    "Se não souber a resposta com confiança em nenhuma das duas fontes, diga isso claramente em vez de "
    "inventar. Responda em português, de forma direta e curta (no máximo um parágrafo curto, ou uma lista "
    "curta quando fizer sentido). Não use markdown.\n\n"
    "Contexto de dados desta empresa:\n{context_json}"
)


class AssistantError(Exception):
    """Raised when the AI call fails or returns something we can't use."""


def _build_context(organization):
    from permits.models import ChecklistItemTemplate, MandatoryPPEItem
    from workers.models import DocumentType

    from .models import RiskArea

    risk_areas = []
    for area in RiskArea.objects.filter(organization=organization):
        checklist_items = list(
            ChecklistItemTemplate.objects.filter(risk_area=area).values_list("description", flat=True)
        )
        ppe_items = list(
            MandatoryPPEItem.objects.filter(risk_area=area).order_by("order").values_list("description", flat=True)
        )
        risk_areas.append(
            {
                "nome": area.name,
                "norma": area.regulatory_code,
                "descricao": area.description,
                "exige_medicao_de_gas": bool(area.required_gas_measurements),
                "medicoes_de_gas_exigidas": area.required_gas_measurements,
                "checklist": checklist_items,
                "epis_obrigatorios": ppe_items,
            }
        )

    document_types = list(
        DocumentType.objects.filter(organization=organization).values_list("code", "name")
    )

    return {
        "empresa": organization.name,
        "areas_de_risco": risk_areas,
        "tipos_de_documento_de_funcionario": [{"codigo": code, "nome": name} for code, name in document_types],
    }


def answer_question(organization, question, history=None):
    """`history` is an optional list of {"role": "user"|"assistant", "content": str}
    from earlier turns in the same conversation (client-held, not stored
    server-side — see core.views.NRAssistantView). Returns the answer text.
    """
    if not settings.OPENAI_API_KEY:
        raise AssistantError("OPENAI_API_KEY não está configurada.")

    context_json = json.dumps(_build_context(organization), ensure_ascii=False)
    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(context_json=context_json)}]
    for turn in (history or [])[-6:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": str(turn["content"])[:2000]})
    messages.append({"role": "user", "content": question})

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_TEXT_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=500,
        )
    except OpenAIError as exc:
        raise AssistantError(f"Falha ao chamar a API do assistente: {exc}") from exc

    answer = response.choices[0].message.content
    if not answer:
        raise AssistantError("Resposta vazia da API.")
    return answer.strip()
