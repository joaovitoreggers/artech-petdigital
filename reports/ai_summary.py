"""Generates a short Portuguese narrative summarizing a period report's key
patterns, for the top of the PDF — something a SESMT coordinator can read
in a few seconds instead of scanning every table first.

Grounded strictly in the report's own computed numbers (never given the
raw permit descriptions), so cross-checking it against the tables below it
is straightforward. Never blocks report generation: reports.services calls
this wrapped in a try/except and simply omits the summary section on any
failure (missing API key, API error, unexpected response shape) — a report
the human still gets to read stands on its own without it.
"""

import json

from django.conf import settings
from openai import OpenAI, OpenAIError

PROMPT_TEMPLATE = (
    "Você é um técnico de segurança do trabalho brasileiro escrevendo o resumo executivo (3 a 5 frases, "
    "em português, sem markdown, sem listas) para o topo de um relatório periódico de PETs (Permissões de "
    "Entrada e Trabalho) de {organization_name}. Destaque os padrões mais relevantes dos dados abaixo: "
    "áreas de risco mais frequentes, ocorrências, alertas/evacuações no período e conformidade "
    "atmosférica. Seja direto, como um alerta para quem só vai ler esse parágrafo. Não invente números "
    "fora dos dados fornecidos.\n\n"
    "Dados do período ({period_start} a {period_end}):\n{data_json}\n\n"
    'Responda estritamente em JSON, sem texto fora do JSON: {{"summary": "<parágrafo em português>"}}'
)


class ExecutiveSummaryError(Exception):
    """Raised when the AI call fails or returns something we can't use."""


def generate_executive_summary(organization, period_start, period_end, report_data):
    if not settings.OPENAI_API_KEY:
        raise ExecutiveSummaryError("OPENAI_API_KEY não está configurada.")

    prompt = PROMPT_TEMPLATE.format(
        organization_name=organization.name,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        data_json=json.dumps(report_data, ensure_ascii=False),
    )

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=400,
        )
    except OpenAIError as exc:
        raise ExecutiveSummaryError(f"Falha ao chamar a API de resumo: {exc}") from exc

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        summary = data["summary"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ExecutiveSummaryError(f"Resposta da API em formato inesperado: {exc}") from exc
    return summary
