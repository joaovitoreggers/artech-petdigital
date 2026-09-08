"""Risk-priority scoring for the approval queue (permits.views.ApprovalQueueView).

Ranks pending permits so a manager sees the riskiest ones first instead of
whichever technician happened to submit earliest (FIFO) — the same kind of
triage a safety coordinator would do by hand, just consistent and never
skipped because the queue is long.

This is a transparent weighted formula, not an LLM call: ranking a
structured/numeric signal like "how close is this gas reading to its
limit" is exactly the kind of thing a reproducible calculation does
better than a natural-language model — no hallucination risk, and a
manager can see precisely why something scored the way it did (see
`reasons`). The AI-assisted features elsewhere in this app (PPE photo
verification, document date reading, risk-area suggestion) use the OpenAI
API because they read unstructured photos/text; this one doesn't need it.
"""

from dataclasses import dataclass, field

from django.utils import timezone

from .constants import GAS_LIMITS

# permits.constants.DEFAULT_RISK_AREAS is the platform's starter content
# (core.onboarding seeds every new organization with a copy); organizations
# can rename/edit their own afterwards, so an unrecognized slug just
# contributes no severity weight instead of erroring.
HIGH_SEVERITY_SLUGS = {"confinado", "quente", "altura", "eletrico"}

SEVERITY_WEIGHT = 18
COMBINED_HIGH_SEVERITY_BONUS = 22
GAS_PROXIMITY_WEIGHT = 30
INCIDENT_HISTORY_WEIGHT = 12
MAX_INCIDENT_CONTRIBUTION = 36
WAITING_HOURS_WEIGHT = 1.5
MAX_WAITING_CONTRIBUTION = 18


@dataclass
class PriorityScore:
    value: float
    reasons: list = field(default_factory=list)

    @property
    def level(self):
        if self.value >= 55:
            return "alta"
        if self.value >= 25:
            return "media"
        return "baixa"


def _measurement_proximity(key, value):
    """0.0 (safe) upward, ~1.0+ meaning at/over a limit."""
    limits = GAS_LIMITS[key]
    value = float(value)
    ratios = []
    if limits["max"] is not None and limits["max"]:
        ratios.append(value / float(limits["max"]))
    if limits["min"] is not None:
        ratios.append(float(limits["min"]) / value if value else 2.0)
    return max(ratios) if ratios else 0.0


def _gas_score(permit):
    reading = permit.latest_gas_reading
    if not reading:
        return 0.0, None
    worst_key, worst_ratio = None, 0.0
    for key in permit.required_gas_measurement_keys:
        value = getattr(reading, key)
        if value is None:
            continue
        ratio = _measurement_proximity(key, value)
        if ratio > worst_ratio:
            worst_key, worst_ratio = key, ratio
    if worst_key is None:
        return 0.0, None
    score = min(1.0, worst_ratio) * GAS_PROXIMITY_WEIGHT
    label = GAS_LIMITS[worst_key]["label"]
    if worst_ratio >= 1.0:
        reason = f"Última leitura de {label} já fora do limite"
    elif worst_ratio >= 0.8:
        reason = f"Última leitura de {label} a {round(worst_ratio * 100)}% do limite"
    else:
        return 0.0, None
    return score, reason


def _severity_score(permit, risk_areas):
    slugs = {area.slug for area in risk_areas}
    high = slugs & HIGH_SEVERITY_SLUGS
    if not high:
        return 0.0, None
    score = len(high) * SEVERITY_WEIGHT
    reason = None
    if len(high) >= 2:
        names = ", ".join(sorted(area.name for area in risk_areas if area.slug in high))
        score += COMBINED_HIGH_SEVERITY_BONUS
        reason = f"Combinação de riscos altos: {names}"
    return score, reason


def _incident_history_score(permit, incident_count):
    if incident_count <= 0:
        return 0.0, None
    score = min(MAX_INCIDENT_CONTRIBUTION, incident_count * INCIDENT_HISTORY_WEIGHT)
    plural = "ocorrência" if incident_count == 1 else "ocorrências"
    reason = f"{permit.requested_by} tem {incident_count} {plural} anteriores"
    return score, reason


def _waiting_score(permit):
    hours_waiting = (timezone.now() - permit.created_at).total_seconds() / 3600
    score = min(MAX_WAITING_CONTRIBUTION, hours_waiting * WAITING_HOURS_WEIGHT)
    if hours_waiting >= 4:
        reason = f"Aguardando aprovação há {round(hours_waiting)}h"
        return score, reason
    return score, None


def score_permit(permit, *, incident_count):
    """`incident_count` is passed in (not queried here) so a caller scoring
    a whole queue can compute it once per technician instead of once per
    permit — see score_queue."""
    risk_areas = list(permit.risk_areas.all())
    reasons = []
    total = 0.0

    for score, reason in (
        _severity_score(permit, risk_areas),
        _gas_score(permit),
        _incident_history_score(permit, incident_count),
        _waiting_score(permit),
    ):
        total += score
        if reason:
            reasons.append(reason)

    return PriorityScore(value=round(total, 1), reasons=reasons)


def score_queue(permits):
    """Scores and sorts a queryset/list of pending permits, highest risk
    first. Returns a list (not a queryset) with `.priority` attached to
    each permit."""
    from .models import WorkPermit

    from django.db.models import Count

    permits = list(permits)
    technician_ids = {permit.requested_by_id for permit in permits}
    # Per-technician incident count, computed once for the whole batch.
    incident_counts = {
        row["requested_by_id"]: row["count"]
        for row in WorkPermit.objects.filter(
            requested_by_id__in=technician_ids, status=WorkPermit.Status.INCIDENT
        )
        .values("requested_by_id")
        .annotate(count=Count("id"))
    }

    for permit in permits:
        permit.priority = score_permit(
            permit, incident_count=incident_counts.get(permit.requested_by_id, 0)
        )

    permits.sort(key=lambda permit: permit.priority.value, reverse=True)
    return permits
