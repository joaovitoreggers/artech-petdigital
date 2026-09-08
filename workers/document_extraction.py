"""Reads a certification/document's expiry date from a photo using the
OpenAI vision API, to pre-fill (never auto-submit) WorkerDocument.valid_until
— whoever is registering the worker still reviews and confirms the date
before saving. Mirrors permits.ppe_verification's use of the same API.
"""

import base64
import json
from datetime import date

from django.conf import settings
from openai import OpenAI, OpenAIError

PROMPT_TEMPLATE = (
    "Você é um assistente que lê documentos de certificação/atestado de segurança do trabalho "
    'brasileiro (ex.: ASO, NR-33, NR-35, NR-10...). A foto mostra um documento chamado "{document_label}".\n\n'
    "Encontre a data de validade do documento. Se o documento só mostrar a data de emissão e um prazo de "
    'validade (ex.: "válido por 1 ano"), calcule a data final. Se não for possível determinar a data com '
    "razoável confiança, responda null.\n\n"
    "Responda estritamente em JSON, sem nenhum texto fora do JSON, no formato:\n"
    '{{"valid_until": "AAAA-MM-DD ou null", "confidence": "alta|media|baixa", '
    '"notes": "<uma frase curta em português explicando o que foi lido>"}}'
)


class DocumentExtractionError(Exception):
    """Raised when the AI call fails or returns something we can't use."""


def extract_document_validity(image_bytes, document_label):
    """Returns {"valid_until": date|None, "confidence": str, "notes": str}.
    Raises DocumentExtractionError on any API/parsing failure — callers
    must treat that as "couldn't read it", never as a value to trust.
    """
    if not settings.OPENAI_API_KEY:
        raise DocumentExtractionError("OPENAI_API_KEY não está configurada.")

    prompt = PROMPT_TEMPLATE.format(document_label=document_label)
    encoded_image = base64.b64encode(image_bytes).decode()

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_DOCUMENT_MODEL,
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
            max_tokens=300,
        )
    except OpenAIError as exc:
        raise DocumentExtractionError(f"Falha ao chamar a API de leitura: {exc}") from exc

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise DocumentExtractionError(f"Resposta da API em formato inesperado: {exc}") from exc

    raw_date = data.get("valid_until")
    valid_until = None
    if raw_date and str(raw_date).lower() != "null":
        try:
            valid_until = date.fromisoformat(raw_date)
        except (ValueError, TypeError):
            valid_until = None

    return {
        "valid_until": valid_until,
        "confidence": data.get("confidence", ""),
        "notes": data.get("notes", ""),
    }
