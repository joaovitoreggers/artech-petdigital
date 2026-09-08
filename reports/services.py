import logging
from datetime import timedelta

from django.db.models import Avg, Count, Max, Min, Q
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from dashboard.models import EvacuationEvent
from permits.constants import GAS_LIMITS, gas_limit_display
from permits.models import GasReading, WorkPermit

from . import ai_summary

logger = logging.getLogger(__name__)


def _permits_in_period(organization, period_start, period_end, unit):
    permits = WorkPermit.objects.filter(
        organization=organization, created_at__date__gte=period_start, created_at__date__lte=period_end
    ).exclude(status=WorkPermit.Status.DRAFT)
    if unit:
        permits = permits.filter(unit=unit)
    return permits.select_related("unit").prefetch_related("risk_areas").order_by("created_at")


def _gas_summary_for_permit(work_permit):
    """Min/avg/max per gas measurement, limited to the keys the permit's
    risk areas actually require — a permit that never asked for, say,
    H₂S has no rows for it (not a blank/None row)."""
    readings = work_permit.gas_readings.all()
    if not readings.exists():
        return None

    required_keys = work_permit.required_gas_measurement_keys
    aggregate_kwargs = {}
    for key in required_keys:
        aggregate_kwargs[f"{key}_min"] = Min(key)
        aggregate_kwargs[f"{key}_avg"] = Avg(key)
        aggregate_kwargs[f"{key}_max"] = Max(key)
    aggregates = readings.aggregate(
        total=Count("id"), out_of_limits=Count("id", filter=Q(is_within_limits=False)), **aggregate_kwargs
    )

    rows = []
    for key in required_keys:
        limits = GAS_LIMITS[key]
        avg = aggregates[f"{key}_avg"]
        rows.append(
            {
                "label": f"{limits['label']} ({limits['unit']})",
                "min": aggregates[f"{key}_min"],
                "avg": round(avg, 1) if avg is not None else None,
                "max": aggregates[f"{key}_max"],
                "limit": gas_limit_display(key),
            }
        )
    return {"rows": rows, "total_readings": aggregates["total"], "out_of_limits": aggregates["out_of_limits"]}


def _daily_condition(period_start, period_end, permits):
    from django.db.models.functions import TruncDate

    readings = (
        GasReading.objects.filter(work_permit__in=permits, recorded_at__date__gte=period_start, recorded_at__date__lte=period_end)
        .annotate(day=TruncDate("recorded_at"))
        .values("day")
        .annotate(total=Count("id"), out_of_limits=Count("id", filter=Q(is_within_limits=False)))
    )
    by_day = {row["day"]: row for row in readings}
    days = []
    current = period_start
    while current <= period_end:
        row = by_day.get(current, {"total": 0, "out_of_limits": 0})
        total = row["total"] or 1
        days.append(
            {
                "date": current,
                "height_pct": min(100, row["total"] * 8),
                "out_pct": round((row["out_of_limits"] / total) * 100),
            }
        )
        current += timedelta(days=1)
    return days


def _evacuations_in_period(organization, period_start, period_end, unit):
    events = EvacuationEvent.objects.filter(
        organization=organization,
        triggered_at__date__gte=period_start,
        triggered_at__date__lte=period_end,
    )
    if unit:
        events = events.filter(unit=unit)
    events = events.select_related("unit", "triggered_by").order_by("triggered_at")

    rows = []
    for event in events:
        duration_minutes = None
        if event.ended_at:
            duration_minutes = round((event.ended_at - event.triggered_at).total_seconds() / 60)
        rows.append(
            {
                "event": event,
                "duration_minutes": duration_minutes,
                "status": "concluída" if event.ended_at else "em andamento",
            }
        )
    return rows


def _risk_area_frequency(permits):
    frequency = {}
    for permit in permits:
        for area in permit.risk_areas.all():
            frequency[area.regulatory_code] = frequency.get(area.regulatory_code, 0) + 1
    return frequency


def build_report_context(organization, period_start, period_end, unit, generated_by):
    permits = list(_permits_in_period(organization, period_start, period_end, unit))
    monitored = [
        {"permit": permit, "summary": summary}
        for permit in permits
        if (summary := _gas_summary_for_permit(permit)) is not None
    ]
    total_readings = GasReading.objects.filter(work_permit__in=permits)
    compliance_total = total_readings.count()
    compliance_ok = total_readings.filter(is_within_limits=True).count()
    evacuations = _evacuations_in_period(organization, period_start, period_end, unit)
    summary = {
        "total_permits": len(permits),
        "closed": sum(1 for p in permits if p.status == WorkPermit.Status.CLOSED),
        "incidents": sum(1 for p in permits if p.status == WorkPermit.Status.INCIDENT),
        "compliance": round((compliance_ok / compliance_total) * 100, 1) if compliance_total else 100.0,
        "evacuations": len(evacuations),
    }
    return {
        "organization": organization,
        "period_start": period_start,
        "period_end": period_end,
        "unit": unit,
        "generated_by": generated_by,
        "generated_at": timezone.now(),
        "permits": permits,
        "monitored": monitored,
        "evacuations": evacuations,
        "summary": summary,
        "daily_condition": _daily_condition(period_start, period_end, permits),
        "gas_limits": GAS_LIMITS,
        "ai_executive_summary": _build_ai_executive_summary(
            organization, period_start, period_end, summary, evacuations, permits
        ),
    }


def _build_ai_executive_summary(organization, period_start, period_end, summary, evacuations, permits):
    report_data = {
        "summary": summary,
        "risk_area_frequency": _risk_area_frequency(permits),
        "evacuations": [
            {
                "source": row["event"].get_source_display(),
                "status": row["status"],
                "duration_minutes": row["duration_minutes"],
            }
            for row in evacuations
        ],
    }
    try:
        return ai_summary.generate_executive_summary(organization, period_start, period_end, report_data)
    except ai_summary.ExecutiveSummaryError as exc:
        logger.warning("Resumo executivo por IA indisponível para o relatório: %s", exc)
        return None


def render_report_pdf(context):
    html_string = render_to_string("reports/period_report_pdf.html", context)
    return HTML(string=html_string).write_pdf()
