"""Checks a field photo against a permit's mandatory PPE list using the
OpenAI API (see the "Verificação de EPI" wizard step). Replaces the old
yes/no PPE checklist questions: instead of self-declaring, the executing
worker proves each required item is visibly worn in one photo.
"""

import base64
import json

from django.conf import settings
from openai import OpenAI, OpenAIError

PROMPT_TEMPLATE = (
    "Você é um inspetor de segurança do trabalho analisando uma foto tirada em campo antes do início de um "
    "serviço industrial. A foto deve mostrar o(s) trabalhador(es) que vão executar o serviço, usando os "
    "equipamentos de proteção individual (EPIs) exigidos.\n\n"
    "Para cada item da lista de EPIs obrigatórios abaixo, diga se ele está visivelmente sendo usado por "
    "algum trabalhador na foto. Seja rigoroso: só marque como presente (true) um item se ele estiver "
    "claramente visível na foto. Se a foto não mostrar uma pessoa, ou não for possível avaliar um item com "
    "confiança, marque esse item como ausente (false).\n\n"
    "Lista de EPIs obrigatórios:\n{items_list}\n\n"
    "Responda estritamente em JSON, sem nenhum texto fora do JSON, no formato:\n"
    '{{"items": [{{"description": "<texto exato do item>", "present": true|false}}, ...], '
    '"summary": "<uma frase em português explicando o resultado>"}}'
)


class PPEVerificationError(Exception):
    """Raised when the AI call fails or returns something we can't use."""


def verify_ppe_photo(image_bytes, required_items):
    """Checks `image_bytes` (raw JPEG/PNG bytes) against `required_items`
    (list of PPE description strings). Returns a dict:
    {"passed": bool, "items_result": [{"description", "present"}, ...], "summary": str}.
    Raises PPEVerificationError on any API/parsing failure — callers must
    not treat that as a pass.
    """
    if not settings.OPENAI_API_KEY:
        raise PPEVerificationError("OPENAI_API_KEY não está configurada.")

    items_list = "\n".join(f"- {item}" for item in required_items)
    prompt = PROMPT_TEMPLATE.format(items_list=items_list)
    encoded_image = base64.b64encode(image_bytes).decode()

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_PPE_VERIFICATION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}},
                    ],
                }
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=800,
        )
    except OpenAIError as exc:
        raise PPEVerificationError(f"Falha ao chamar a API de verificação: {exc}") from exc

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        items_result = [
            {"description": item["description"], "present": bool(item["present"])}
            for item in data["items"]
        ]
        summary = data.get("summary", "")
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise PPEVerificationError(f"Resposta da API em formato inesperado: {exc}") from exc

    passed = bool(items_result) and all(item["present"] for item in items_result)
    return {"passed": passed, "items_result": items_result, "summary": summary}
